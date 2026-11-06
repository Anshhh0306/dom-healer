"""Per-document index: document order, headings, text segments, labels and candidate retrieval.

Building a :class:`PageIndex` is a single pass over the document (cheap); it is
reused for every fingerprint captured from, or located in, the same document.
Candidate retrieval is done with a handful of compiled XPath queries (evaluated
in C by libxml2) followed by a cheap Python pre-score, so only a few dozen
elements ever get a full fingerprint.
"""

from __future__ import annotations

import heapq
import re
from bisect import bisect_left
from collections.abc import Iterable

from lxml import etree

from dom_healer.dom import Document, Element
from dom_healer.fingerprint import (
    TEST_ATTRS,
    ElementFingerprint,
    build_fingerprint,
    direct_text,
    text_without,
)
from dom_healer.semantics import HEADING_TAGS, element_family, element_role
from dom_healer.text import CANONICAL_WORDS, canonical_words, jaccard, normalize_text, text_similarity

#: Elements that are never returned as candidates.
SKIP_TAGS = frozenset(
    {
        "html", "head", "body", "title", "meta", "link", "script", "style", "noscript", "template", "base", "br", "wbr",
        "path", "g", "circle", "rect", "line", "polyline", "polygon", "ellipse", "defs", "use", "symbol", "clippath",
        "lineargradient", "radialgradient", "stop", "mask", "pattern", "filter", "tspan", "desc",
    }
)
_NO_TEXT_TAGS = frozenset({"script", "style", "noscript", "template", "title", "head"})
HEADING_LIKE = HEADING_TAGS | {"legend", "caption"}

_FAMILY_QUERIES: dict[str, etree.XPath] = {
    "clickable": etree.XPath(
        "//a | //button | //summary | //input[@type='submit' or @type='button' or @type='reset' or @type='image']"
        " | //*[@role='button' or @role='link' or @role='tab' or @role='menuitem' or @onclick]"
    ),
    "choice": etree.XPath(
        "//input[@type='checkbox' or @type='radio']"
        " | //*[@role='checkbox' or @role='radio' or @role='switch' or @role='menuitemcheckbox' or @role='menuitemradio']"
    ),
    "text_input": etree.XPath(
        "//input[not(@type='checkbox' or @type='radio' or @type='submit' or @type='button' or @type='reset'"
        " or @type='image' or @type='hidden')] | //textarea"
        " | //*[@role='textbox' or @role='searchbox' or @role='spinbutton' or @contenteditable]"
    ),
    "select": etree.XPath("//select | //*[@role='combobox' or @role='listbox']"),
    "cell": etree.XPath("//td | //th | //*[@role='cell' or @role='gridcell' or @role='columnheader' or @role='rowheader']"),
    "heading": etree.XPath("//h1 | //h2 | //h3 | //h4 | //h5 | //h6 | //legend | //caption | //*[@role='heading']"),
    "media": etree.XPath("//img | //svg | //picture | //video | //canvas | //*[@role='img']"),
    "list_item": etree.XPath("//li | //option | //dt | //dd | //*[@role='listitem' or @role='option']"),
}
_TEXT_QUERY = etree.XPath(
    "//*[text()[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), $w)]]"
)
_ATTR_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")
_ATTR_QUERIES: dict[tuple[str, bool], etree.XPath] = {}

#: Attributes used for retrieval, with their pre-score weight.
_RETRIEVAL_ATTRS = {
    "id": 3.0,
    "name": 3.0,
    "aria-label": 2.5,
    "placeholder": 2.5,
    "title": 1.5,
    "alt": 2.0,
    "for": 1.5,
    "href": 2.0,
}
_REVERSE_CANON: dict[str, set[str]] = {}
for _raw, _canon in CANONICAL_WORDS.items():
    if _canon:
        _REVERSE_CANON.setdefault(_canon, {_canon}).add(_raw)


def _attr_query(name: str, contains: bool = False) -> etree.XPath:
    key = (name, contains)
    query = _ATTR_QUERIES.get(key)
    if query is None:
        expr = f"//*[contains(@{name}, $v)]" if contains else f"//*[@{name}=$v]"
        query = _ATTR_QUERIES[key] = etree.XPath(expr)
    return query


class PageIndex:
    """Index over one :class:`~dom_healer.dom.Document`."""

    def __init__(self, doc: Document) -> None:
        self.doc = doc
        ordinal: dict[Element, int] = {}
        heading_ords: list[int] = []
        heading_els: list[Element] = []
        text_ords: list[float] = []
        text_vals: list[str] = []
        ids: dict[str, Element] = {}
        labels: dict[str, Element] = {}
        n = 0
        for el in doc.root.iter(etree.Element):
            ordinal[el] = n
            tag = el.tag
            if tag not in _NO_TEXT_TAGS:
                text = el.text
                if text and not text.isspace():
                    text_ords.append(n)
                    text_vals.append(text)
                if len(el) == 0:
                    tail = el.tail
                    if tail and not tail.isspace():
                        text_ords.append(n + 0.5)
                        text_vals.append(tail)
            if tag in HEADING_LIKE or el.get("role") == "heading":
                heading_ords.append(n)
                heading_els.append(el)
            el_id = el.get("id")
            if el_id and el_id not in ids:
                ids[el_id] = el
            if tag == "label":
                target = el.get("for")
                if target and target not in labels:
                    labels[target] = el
            n += 1
        self.size = n
        self._ordinal = ordinal
        self._heading_ords = heading_ords
        self._heading_els = heading_els
        self._text_ords = text_ords
        self._text_vals = text_vals
        self._ids = ids
        self._labels = labels
        self._roles: dict[Element, str] = {}
        self._headings: dict[int, str] = {}
        self._fingerprints: dict[Element, ElementFingerprint] = {}

    # -- lookups ------------------------------------------------------------------------
    def ordinal(self, el: Element) -> int:
        return self._ordinal[el]

    def position(self, el: Element) -> float:
        """Relative position of ``el`` in document order (0 = first, 1 = last)."""
        return self._ordinal.get(el, 0) / max(1, self.size - 1)

    def by_id(self, value: str) -> Element | None:
        return self._ids.get(value)

    def label_text_for(self, el_id: str) -> str:
        label = self._labels.get(el_id)
        if label is None:
            return ""
        return normalize_text(text_without(label, frozenset({"select", "textarea", "option", "datalist"})), 120)

    def role(self, el: Element) -> str:
        role = self._roles.get(el)
        if role is None:
            role = self._roles[el] = element_role(el)
        return role

    def heading_before(self, el: Element) -> str:
        """Text of the nearest heading-like element that starts before ``el``."""
        i = bisect_left(self._heading_ords, self._ordinal.get(el, 0)) - 1
        if i < 0:
            return ""
        text = self._headings.get(i)
        if text is None:
            text = self._headings[i] = normalize_text(self._heading_els[i].text_content(), 80)
        return text

    def text_before(self, el: Element, segments: int = 2) -> str:
        """The last ``segments`` text runs preceding ``el`` in document order."""
        i = bisect_left(self._text_ords, self._ordinal.get(el, 0))
        if i <= 0:
            return ""
        return normalize_text(" ".join(self._text_vals[max(0, i - segments) : i]), 120)

    def text_after(self, el: Element, segments: int = 2, max_subtree: int = 64) -> str:
        """The first ``segments`` text runs following ``el``'s subtree (empty for large subtrees)."""
        o = self._ordinal.get(el)
        if o is None:
            return ""
        if len(el) == 0:
            end = o + 0.5
        else:
            size = 0
            for _ in el.iter(etree.Element):
                size += 1
                if size > max_subtree:
                    return ""
            end = o + size
        i = bisect_left(self._text_ords, end)
        return normalize_text(" ".join(self._text_vals[i : i + segments]), 120)

    def fingerprint(self, el: Element, selector: str = "") -> ElementFingerprint:
        """Fingerprint of ``el`` (cached per element)."""
        fp = self._fingerprints.get(el)
        if fp is None:
            fp = self._fingerprints[el] = build_fingerprint(el, self)
        if selector and fp.selector != selector:
            fp = ElementFingerprint.from_dict({**fp.to_dict(), "selector": selector})
        return fp

    # -- candidate retrieval -----------------------------------------------------------
    def _retrieval_attrs(self, fp: ElementFingerprint) -> list[tuple[str, str, float, bool]]:
        out: list[tuple[str, str, float, bool]] = []
        if fp.id:
            out.append(("id", fp.id, _RETRIEVAL_ATTRS["id"], False))
        for key, value in fp.attrs.items():
            if not value or len(value) > 100 or not _ATTR_NAME.match(key):
                continue
            if key in _RETRIEVAL_ATTRS:
                out.append((key, value, _RETRIEVAL_ATTRS[key], key == "href"))
            elif key in TEST_ATTRS:
                out.append((key, value, 3.0, False))
            elif key.startswith("data-") and len(value) >= 2:
                out.append((key, value, 1.5, False))
        return out

    def _query_words(self, fp: ElementFingerprint) -> list[str]:
        source = fp.accessible_name or fp.full_text or fp.label
        chosen = sorted((w for w in canonical_words(source) if len(w) >= 3), key=len, reverse=True)[:3]
        out: list[str] = []
        for w in chosen:
            for variant in sorted(_REVERSE_CANON.get(w, {w})):
                if len(variant) >= 3 and variant not in out:
                    out.append(variant)
        return out[:6]

    def candidate_pool(self, fp: ElementFingerprint, extra: Iterable[Element] = ()) -> list[Element]:
        """Union of elements that share *anything* cheap to check with ``fp``."""
        root = self.doc.root
        pool: dict[Element, None] = dict.fromkeys(root.iter(fp.tag))
        family_query = _FAMILY_QUERIES.get(fp.family)
        if family_query is not None:
            pool.update(dict.fromkeys(family_query(root)))
        for key, value, _w, contains in self._retrieval_attrs(fp):
            pool.update(dict.fromkeys(_attr_query(key, contains)(root, v=value)))
        for word in self._query_words(fp):
            for el in _TEXT_QUERY(root, w=word):
                pool[el] = None
                parent = el.getparent()
                for _ in range(2):
                    if parent is None:
                        break
                    if parent.tag == fp.tag or element_family(parent.tag, self.role(parent)) == fp.family:
                        pool[parent] = None
                    parent = parent.getparent()
        pool.update(dict.fromkeys(extra))
        return [el for el in pool if isinstance(el.tag, str) and el.tag not in SKIP_TAGS]

    def prescore(self, fp: ElementFingerprint, el: Element, attrs: list[tuple[str, str, float, bool]],
                 fp_words: frozenset[str]) -> float:
        """Cheap similarity used to cut the pool down before full fingerprinting."""
        score = 0.0
        tag = el.tag
        role = self.role(el)
        if tag == fp.tag:
            score += 1.0
        if role and role == fp.role:
            score += 0.5
        if element_family(tag, role, (el.get("type") or "").lower()) == fp.family:
            score += 1.0
        for key, value, weight, contains in attrs:
            other = el.get(key)
            if other is not None and ((value in other) if contains else other == value):
                score += weight
        if fp_words:
            if tag in ("input", "select", "textarea"):
                own = normalize_text(el.get("aria-label") or el.get("placeholder") or "", 120)
                if not own and el.get("id"):
                    own = self.label_text_for(el.get("id"))
            elif len(el) <= 8:
                own = normalize_text(el.text_content(), 120)
            else:
                own = normalize_text(direct_text(el), 120)
            if own:
                score += 2.0 * jaccard(fp_words, canonical_words(own))
        if fp.heading:
            score += 1.5 * text_similarity(fp.heading, self.heading_before(el))
        score += 0.5 * (1.0 - abs(self.position(el) - fp.position))
        return score

    def candidates(self, fp: ElementFingerprint, k: int = 32, extra: Iterable[Element] = ()) -> list[tuple[Element, float]]:
        """Top-``k`` candidate elements for ``fp`` with their normalised pre-scores."""
        pool = self.candidate_pool(fp, extra)
        if not pool:
            return []
        attrs = self._retrieval_attrs(fp)
        fp_words = canonical_words(fp.accessible_name or fp.full_text or fp.label)
        scored = [(self.prescore(fp, el, attrs, fp_words), -self._ordinal.get(el, 0), el) for el in pool]
        top = heapq.nlargest(k, scored, key=lambda item: (item[0], item[1]))
        best = top[0][0] or 1.0
        return [(el, score / best) for score, _o, el in top]
