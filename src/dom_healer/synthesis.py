"""Generate robust CSS and XPath selectors for an element, verified to be unique.

Strategies are tried from most to least robust: stable ``id`` → test attributes
(``data-testid`` …) → ``name``/``aria-label``/other stable attributes →
semantic classes → anchored (unique ancestor + relative part) → accessible
text (XPath only) → positional path.  Every emitted selector is evaluated
against the document and must match exactly the target element.
"""

from __future__ import annotations

from dataclasses import dataclass

from dom_healer.dom import Document, Element, SelectorError, select
from dom_healer.fingerprint import TEST_ATTRS
from dom_healer.text import UTILITY_TOKENS, identifier_tokens, is_obfuscated_class, looks_generated

_ANCHOR_TAGS = ("form", "nav", "main", "header", "footer", "aside", "table", "dialog", "section", "article", "ul", "ol")
_ATTR_PRIORITY = ("name", "aria-label", "placeholder", "title", "alt", "for", "type", "href", "role", "value")
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
# Helpers
# ---------------------------------------------------------------------------------------


def _unique(doc: Document, selector: str, el: Element, scope: Element | None = None) -> bool:
    try:
        matches = select(scope if scope is not None else doc.root, selector)
    except SelectorError:  # pragma: no cover - generated selectors are always valid
        return False
    return len(matches) == 1 and matches[0] is el


def _stable_classes(el: Element) -> list[str]:
    out = []
    for cls in (el.get("class") or "").split():
        if is_obfuscated_class(cls) or ":" in cls or "[" in cls or "/" in cls:
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
        if key.startswith("data-") and key not in TEST_ATTRS and value and len(value) <= 40:
            if not looks_generated(value) and key not in ("data-reactid", "data-v"):
                out.append((key, value))
    return out


def _visible_text(el: Element) -> str:
    return " ".join(el.text_content().split())


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


def _local_css(el: Element) -> list[tuple[str, str]]:
    """(css, strategy) options that do not involve ancestors."""
    tag = el.tag
    out: list[tuple[str, str]] = []
    el_id = el.get("id")
    if el_id and not looks_generated(el_id):
        out.append((f"#{css_ident(el_id)}", "id"))
    for key, value in _attr_candidates(el):
        strategy = "test-attribute" if key in TEST_ATTRS else f"attribute:{key}"
        out.append((f"[{key}={css_string(value)}]", strategy))
        out.append((f"{tag}[{key}={css_string(value)}]", strategy))
    classes = _stable_classes(el)
    for cls in classes[:4]:
        out.append((f"{tag}.{css_ident(cls)}", "class"))
    if len(classes) >= 2:
        out.append((f"{tag}." + ".".join(css_ident(c) for c in classes[:3]), "class"))
    return out


def _local_xpath(el: Element) -> list[tuple[str, str]]:
    tag = el.tag
    out: list[tuple[str, str]] = []
    el_id = el.get("id")
    if el_id and not looks_generated(el_id):
        out.append((f"//*[@id={xpath_literal(el_id)}]", "id"))
    for key, value in _attr_candidates(el):
        strategy = "test-attribute" if key in TEST_ATTRS else f"attribute:{key}"
        out.append((f"//{tag}[@{key}={xpath_literal(value)}]", strategy))
    text = _visible_text(el)
    if text and len(text) <= _MAX_TEXT:
        out.append((f"//{tag}[normalize-space()={xpath_literal(text)}]", "text"))
    return out


def _anchor(doc: Document, el: Element) -> tuple[Element, str, str] | None:
    """Nearest ancestor with a unique, stable CSS + XPath selector."""
    for depth, anc in enumerate(el.iterancestors()):
        if depth > 10 or anc.tag in ("body", "html"):
            break
        for css, _ in _local_css(anc):
            if _unique(doc, css, anc):
                xpaths = [x for x, _ in _local_xpath(anc) if _unique(doc, x, anc)]
                if xpaths:
                    return anc, css, xpaths[0]
        if anc.tag in _ANCHOR_TAGS and len(doc.root.xpath(f"//{anc.tag}")) == 1:
            return anc, anc.tag, f"//{anc.tag}"
    return None


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


# ---------------------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------------------


def suggest_css(doc: Document, el: Element) -> tuple[str, str]:
    for css, strategy in _local_css(el):
        if _unique(doc, css, el):
            return css, strategy
    anchor = _anchor(doc, el)
    if anchor is not None:
        anc, anc_css, _ = anchor
        for css, strategy in _local_css(el):
            scoped = f"{anc_css} {css}"
            if _unique(doc, scoped, el):
                return scoped, f"anchored:{strategy}"
        scoped = f"{anc_css} > {_relative_css(anc, el)}"
        if _unique(doc, scoped, el):
            return scoped, "anchored:position"
    return _absolute_css(el), "position"


def suggest_xpath(doc: Document, el: Element) -> tuple[str, str]:
    local = _local_xpath(el)
    for xpath, strategy in local:
        if _unique(doc, xpath, el):
            return xpath, strategy
    anchor = _anchor(doc, el)
    if anchor is not None:
        anc, _, anc_xpath = anchor
        for xpath, strategy in local:
            scoped = anc_xpath + xpath  # "//a[...]" + "//b[...]" -> descendant within anchor
            if _unique(doc, scoped, el):
                return scoped, f"anchored:{strategy}"
        scoped = f"{anc_xpath}/{_relative_xpath(anc, el)}"
        if _unique(doc, scoped, el):
            return scoped, "anchored:position"
    return doc.absolute_xpath(el), "position"


def suggest_selectors(doc: Document, el: Element) -> SelectorSuggestion:
    """Robust, verified-unique CSS and XPath selectors for ``el`` in ``doc``."""
    css, css_strategy = suggest_css(doc, el)
    xpath, xpath_strategy = suggest_xpath(doc, el)
    return SelectorSuggestion(css=css, xpath=xpath, css_strategy=css_strategy, xpath_strategy=xpath_strategy)
