"""Generate robust CSS and XPath selectors for an element, verified to be unique.

Strategies are tried from most to least robust: stable ``id`` → test attributes
(``data-testid`` …) → ``name``/``aria-label``/other stable attributes →
semantic classes → accessible text (XPath only) → anchored (unique ancestor +
relative part) → positional path.

Every candidate is a pair of CSS/XPath strings with identical semantics plus a
fast *matcher* that counts its matches with the page index (attribute buckets,
C-level tag iteration, ordinal-range scoping) instead of compiling and running
a selector per attempt.  The selectors that are finally returned are always
re-checked with the real CSS (cssselect) and XPath (libxml2) engines.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from dom_healer.dom import Document, Element, SelectorError, select
from dom_healer.fingerprint import TEST_ATTRS
from dom_healer.index import PageIndex, get_index
from dom_healer.text import (
    UTILITY_TOKENS,
    identifier_tokens,
    is_obfuscated_class,
    looks_generated,
    looks_random,
)

_ANCHOR_TAGS = ("form", "nav", "main", "header", "footer", "aside", "table", "dialog", "section", "article", "ul", "ol")
_ATTR_PRIORITY = ("name", "aria-label", "placeholder", "title", "alt", "for", "type", "href", "role", "value")
_SAFE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
_XML_SPACE = re.compile(r"[ \t\r\n]+")
_MAX_TEXT = 60


@dataclass(frozen=True)
class SelectorSuggestion:
    """A pair of selectors that uniquely identify an element in a document."""

    css: str
    xpath: str
    css_strategy: str
    xpath_strategy: str

    def to_dict(self) -> dict[str, str]:
        return {
            "css": self.css,
            "xpath": self.xpath,
            "css_strategy": self.css_strategy,
            "xpath_strategy": self.xpath_strategy,
        }


# ---------------------------------------------------------------------------------------
# Escaping
# ---------------------------------------------------------------------------------------


def css_ident(value: str) -> str:
    """Serialise ``value`` as a CSS identifier (CSSOM ``escape()``)."""
    out: list[str] = []
    for i, ch in enumerate(value):
        code = ord(ch)
        if code == 0:
            out.append("\ufffd")
        elif 0x01 <= code <= 0x1F or code == 0x7F or (i == 0 and ch.isdigit()) or (
            i == 1 and ch.isdigit() and value[0] == "-"
        ):
            out.append(f"\\{code:x} ")
        elif i == 0 and ch == "-" and len(value) == 1:
            out.append("\\-")
        elif code >= 0x80 or ch.isalnum() or ch in "-_":
            out.append(ch)
        else:
            out.append("\\" + ch)
    return "".join(out)


def css_string(value: str) -> str:
    """Quote ``value`` as a CSS string."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\a ").replace("\r", "\\d ")
    return f'"{escaped}"'


def xpath_literal(value: str) -> str:
    """Quote ``value`` as an XPath 1.0 string literal (using ``concat`` when needed)."""
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'
    parts = value.split("'")
    return "concat(" + ", \"'\", ".join(f"'{p}'" for p in parts) + ")"


# ---------------------------------------------------------------------------------------
# Candidates
# ---------------------------------------------------------------------------------------

#: matcher(scope) -> elements matched in scope's subtree (scope=None: whole document)
Matcher = Callable[[Element | None], list[Element]]


@dataclass(frozen=True)
class _Candidate:
    css: str | None  # None when the strategy is not expressible in CSS (text matching)
    xpath: str  # always starts with "//" so it can be appended to an anchor's XPath
    strategy: str
    matcher: Matcher


def _xpath_space(text: str) -> str:
    """Whitespace normalisation identical to XPath ``normalize-space()``."""
    return _XML_SPACE.sub(" ", text).strip(" \t\r\n")


def _stable_classes(el: Element) -> list[str]:
    out = []
    for cls in (el.get("class") or "").split():
        if is_obfuscated_class(cls) or not _SAFE_NAME.match(cls):
            continue
        toks = identifier_tokens(cls)
        if toks and not all(t in UTILITY_TOKENS for t in toks):
            out.append(cls)
    return out


def _attr_candidates(el: Element) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for key in TEST_ATTRS:
        value = el.get(key)
        if value and len(value) <= 80:
            out.append((key, value))
    for key in _ATTR_PRIORITY:
        value = el.get(key)
        if value is None or not value.strip() or len(value) > 80 or "\n" in value:
            continue
        if key in ("name", "for") and looks_generated(value):
            continue
        if key == "value" and el.tag not in ("button", "option") and (el.get("type") or "") not in (
            "submit", "button", "reset", "checkbox", "radio",
        ):
            continue
        out.append((key, value))
    for key, value in el.items():
        if (
            key.startswith("data-")
            and key not in TEST_ATTRS
            and _SAFE_NAME.match(key)
            and value
            and len(value) <= 40
            and not looks_random(value)
            and key not in ("data-reactid", "data-v")
        ):
            out.append((key, value))
    return out


class _Synth:
    """Selector synthesis for one element, backed by the page index."""

    def __init__(self, doc: Document, el: Element) -> None:
        self.doc = doc
        self.el = el
        self.index: PageIndex = get_index(doc)
        self._anchor_done = False
        self._anchor: tuple[Element, str, str] | None = None

    # -- matchers ------------------------------------------------------------------
    def _scoped(self, elements: list[Element], scope: Element | None) -> list[Element]:
        if scope is None:
            return elements
        index = self.index
        return [e for e in elements if e is not scope and index.contains(scope, index.ordinal(e))]

    def _attr(self, tag: str | None, key: str, value: str) -> Matcher:
        def match(scope: Element | None) -> list[Element]:
            found = self.index.elements_with(key, value)
            if tag is not None:
                found = [e for e in found if e.tag == tag]
            return self._scoped(found, scope)

        return match

    def _iter(self, scope: Element | None, tag: str) -> list[Element]:
        root = self.doc.root if scope is None else scope
        return [e for e in root.iter(tag) if e is not scope]

    def _classes(self, tag: str, classes: tuple[str, ...]) -> Matcher:
        wanted = set(classes)

        def match(scope: Element | None) -> list[Element]:
            buckets = sorted((self.index.elements_with_class(c) for c in classes), key=len)
            found = [
                e for e in buckets[0] if e.tag == tag and (len(wanted) == 1 or wanted.issubset((e.get("class") or "").split()))
            ]
            return self._scoped(found, scope)

        return match

    def _tag(self, tag: str) -> Matcher:
        return lambda scope: self._iter(scope, tag)

    def _text(self, tag: str, text: str, visible: bool) -> Matcher:
        def shown(e: Element) -> bool:
            node: Element | None = e
            while node is not None:
                if node.get("hidden") is not None or node.get("aria-hidden") == "true":
                    return False
                node = node.getparent()
            return True

        def match(scope: Element | None) -> list[Element]:
            out = [e for e in self._iter(scope, tag) if _xpath_space(e.text_content()) == text]
            return [e for e in out if shown(e)] if visible else out

        return match

    # -- candidate lists ---------------------------------------------------------------
    def local(self, el: Element, with_text: bool = True) -> list[_Candidate]:
        tag = el.tag
        out: list[_Candidate] = []
        el_id = el.get("id")
        if el_id and not looks_generated(el_id):
            out.append(_Candidate(f"#{css_ident(el_id)}", f"//*[@id={xpath_literal(el_id)}]", "id",
                                  self._attr(None, "id", el_id)))
        for key, value in _attr_candidates(el):
            strategy = "test-attribute" if key in TEST_ATTRS else f"attribute:{key}"
            out.append(_Candidate(f"[{key}={css_string(value)}]", f"//*[@{key}={xpath_literal(value)}]", strategy,
                                  self._attr(None, key, value)))
            out.append(_Candidate(f"{tag}[{key}={css_string(value)}]", f"//{tag}[@{key}={xpath_literal(value)}]",
                                  strategy, self._attr(tag, key, value)))
        classes = _stable_classes(el)
        groups = [(c,) for c in classes[:4]] + ([tuple(classes[:3])] if len(classes) >= 2 else [])
        for group in groups:
            css = f"{tag}." + ".".join(css_ident(c) for c in group)
            xpath = f"//{tag}" + "".join(
                f"[contains(concat(' ', normalize-space(@class), ' '), {xpath_literal(' ' + c + ' ')})]" for c in group
            )
            out.append(_Candidate(css, xpath, "class", self._classes(tag, group)))
        if with_text:
            text = _xpath_space(el.text_content())
            if text and len(text) <= _MAX_TEXT:
                lit = xpath_literal(text)
                out.append(_Candidate(None, f"//{tag}[normalize-space()={lit}]", "text", self._text(tag, text, False)))
                out.append(_Candidate(
                    None,
                    f"//{tag}[normalize-space()={lit}][not(ancestor-or-self::*[@hidden or @aria-hidden='true'])]",
                    "visible-text",
                    self._text(tag, text, True),
                ))
        return out

    def unique(self, cand: _Candidate, el: Element, scope: Element | None = None) -> bool:
        found = cand.matcher(scope)
        return len(found) == 1 and found[0] is el

    def anchor(self) -> tuple[Element, str, str] | None:
        """Nearest ancestor with a unique, stable CSS + XPath selector (computed once)."""
        if self._anchor_done:
            return self._anchor
        self._anchor_done = True
        for depth, anc in enumerate(self.el.iterancestors()):
            if depth > 10 or anc.tag in ("body", "html"):
                break
            for cand in self.local(anc, with_text=False):
                if cand.css is not None and self.unique(cand, anc):
                    self._anchor = (anc, cand.css, cand.xpath)
                    return self._anchor
            if anc.tag in _ANCHOR_TAGS and len(self._iter(None, anc.tag)) == 1:
                self._anchor = (anc, anc.tag, f"//{anc.tag}")
                return self._anchor
        return None

    # -- public strategies ---------------------------------------------------------------
    def css(self) -> tuple[str, str]:
        el = self.el
        local = self.local(el, with_text=False)
        for cand in local:
            if cand.css is not None and self.unique(cand, el):
                return cand.css, cand.strategy
        anchor = self.anchor()
        if anchor is not None:
            anc, anc_css, _ = anchor
            for cand in [*local, _Candidate(el.tag, f"//{el.tag}", "tag", self._tag(el.tag))]:
                if cand.css is not None and self.unique(cand, el, scope=anc):
                    return f"{anc_css} {cand.css}", f"anchored:{cand.strategy}"
            return f"{anc_css} > {_relative_css(anc, el)}", "anchored:position"
        return _absolute_css(el), "position"

    def xpath(self) -> tuple[str, str]:
        el = self.el
        local = self.local(el)
        # prefer the tag-qualified form of attribute candidates in XPath ("//input[@name='q']")
        for i in range(len(local) - 1):
            a, b = local[i], local[i + 1]
            if a.strategy == b.strategy and a.xpath.startswith("//*[@") and b.xpath.startswith(f"//{el.tag}[@"):
                local[i], local[i + 1] = b, a
        for cand in local:
            if self.unique(cand, el):
                return cand.xpath, cand.strategy
        anchor = self.anchor()
        if anchor is not None:
            anc, _, anc_xpath = anchor
            for cand in [*local, _Candidate(el.tag, f"//{el.tag}", "tag", self._tag(el.tag))]:
                if self.unique(cand, el, scope=anc):
                    return anc_xpath + cand.xpath, f"anchored:{cand.strategy}"
            return f"{anc_xpath}/{_relative_xpath(anc, el)}", "anchored:position"
        return self.doc.absolute_xpath(el), "position"


# ---------------------------------------------------------------------------------------
# Positional helpers
# ---------------------------------------------------------------------------------------


def _nth_of_type(el: Element) -> str:
    parent = el.getparent()
    tag = el.tag
    if parent is None:
        return tag
    same = [c for c in parent if c.tag == tag]
    if len(same) == 1:
        return tag
    return f"{tag}:nth-of-type({same.index(el) + 1})"


def _xpath_step(el: Element) -> str:
    parent = el.getparent()
    tag = el.tag
    if parent is None:
        return tag
    same = [c for c in parent if c.tag == tag]
    return tag if len(same) == 1 else f"{tag}[{same.index(el) + 1}]"


def _relative_css(anchor: Element, el: Element) -> str:
    steps = []
    node = el
    while node is not None and node is not anchor:
        steps.append(_nth_of_type(node))
        node = node.getparent()
    return " > ".join(reversed(steps))


def _relative_xpath(anchor: Element, el: Element) -> str:
    steps = []
    node = el
    while node is not None and node is not anchor:
        steps.append(_xpath_step(node))
        node = node.getparent()
    return "/".join(reversed(steps))


def _absolute_css(el: Element) -> str:
    steps = []
    node: Element | None = el
    while node is not None:
        steps.append(_nth_of_type(node))
        node = node.getparent()
    return " > ".join(reversed(steps))


def _verified(doc: Document, selector: str, el: Element) -> bool:
    try:
        matches = select(doc, selector)
    except SelectorError:  # pragma: no cover - generated selectors are always valid
        return False
    return len(matches) == 1 and matches[0] is el


# ---------------------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------------------


def suggest_css(doc: Document, el: Element) -> tuple[str, str]:
    """Most robust unique CSS selector for ``el`` and the strategy that produced it."""
    css, strategy = _Synth(doc, el).css()
    if not _verified(doc, css, el):  # pragma: no cover - safety net; matchers mirror CSS semantics
        return _absolute_css(el), "position"
    return css, strategy


def suggest_xpath(doc: Document, el: Element) -> tuple[str, str]:
    """Most robust unique XPath for ``el`` and the strategy that produced it."""
    xpath, strategy = _Synth(doc, el).xpath()
    if not _verified(doc, xpath, el):  # pragma: no cover - safety net; matchers mirror XPath semantics
        return doc.absolute_xpath(el), "position"
    return xpath, strategy


def suggest_selectors(doc: Document, el: Element) -> SelectorSuggestion:
    """Robust, verified-unique CSS and XPath selectors for ``el`` in ``doc``."""
    synth = _Synth(doc, el)
    css, css_strategy = synth.css()
    if not _verified(doc, css, el):  # pragma: no cover - safety net
        css, css_strategy = _absolute_css(el), "position"
    xpath, xpath_strategy = synth.xpath()
    if not _verified(doc, xpath, el):  # pragma: no cover - safety net
        xpath, xpath_strategy = doc.absolute_xpath(el), "position"
    return SelectorSuggestion(css=css, xpath=xpath, css_strategy=css_strategy, xpath_strategy=xpath_strategy)
