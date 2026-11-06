"""Per-document index: document order, headings, text runs, labels and candidate retrieval.

Building a :class:`PageIndex` is a single pass over the document (cheap); it is
reused for every fingerprint captured from, or located in, the same document.
Candidate retrieval uses C-level tag iteration for the element's functional
family, dictionary lookups in an attribute index built during the same pass,
and a substring search over the collected text runs, followed by a cheap Python
pre-score, so only a few dozen elements ever get a full fingerprint.  (libxml2
XPath attribute predicates turned out to be ~30x slower than ``iter(*tags)``.)
"""

from __future__ import annotations

import heapq
from bisect import bisect_left
from collections.abc import Iterable
from typing import NamedTuple

from lxml import etree

from dom_healer.dom import Document, Element
from dom_healer.fingerprint import (
    OPTIONAL_FIELDS,
    TEST_ATTRS,
    ElementFingerprint,
    build_fingerprint,
    text_without,
)
from dom_healer.semantics import HEADING_TAGS, element_family, element_role, own_hidden
from dom_healer.text import CANONICAL_WORDS, canonical_words, jaccard, normalize_text

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
MAJOR_HEADINGS = frozenset({"h1", "h2"})

#: family -> (tags, explicit roles, input types, presence-only attributes)
_FAMILY_SPECS: dict[str, tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...] | str, tuple[str, ...]]] = {
    "clickable": (("a", "button", "summary"), ("button", "link", "tab", "menuitem"),
                  ("submit", "button", "reset", "image"), ("onclick",)),
    "choice": ((), ("checkbox", "radio", "switch", "menuitemcheckbox", "menuitemradio"), ("checkbox", "radio"), ()),
    "text_input": (("textarea",), ("textbox", "searchbox", "spinbutton"), "text-like", ("contenteditable",)),
    "select": (("select",), ("combobox", "listbox"), (), ()),
    "cell": (("td", "th"), ("cell", "gridcell", "columnheader", "rowheader"), (), ()),
    "heading": (("h1", "h2", "h3", "h4", "h5", "h6", "legend", "caption"), ("heading",), (), ()),
    "media": (("img", "svg", "picture", "video", "canvas"), ("img",), (), ()),
    "list_item": (("li", "option", "dt", "dd"), ("listitem", "option"), (), ()),
}
_NON_TEXT_INPUTS = frozenset({"checkbox", "radio", "submit", "button", "reset", "image", "hidden"})
#: Attributes recorded in the attribute index (plus every ``data-*``).
_INDEXED_ATTRS = frozenset(
    {"id", "name", "role", "aria-label", "placeholder", "title", "alt", "for", "href", "type", "onclick",
     "contenteditable"}
)
_PRESENCE_ATTRS = frozenset({"onclick", "contenteditable"})

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


class Ancestry(NamedTuple):
    """Memoised facts about an element and its ancestors (ancestor-or-self)."""

    tag_path: tuple[str, ...]
    sem_path: tuple[str, ...]
    form: str
    landmark: str
    tokens: tuple[frozenset[str], ...]  # own tokens of this element and its nearest ancestors (<= 6)
    cell: Element | None
    row: Element | None
    table: Element | None


_TOKEN_LEVELS = 6


class PageIndex:
    """Index over one :class:`~dom_healer.dom.Document`."""

    def __init__(self, doc: Document) -> None:
        self.doc = doc
        ordinal: dict[Element, int] = {}
        heading_ords: list[int] = []
        heading_els: list[Element] = []
        text_ords: list[float] = []
        text_vals: list[str] = []
        text_owner: list[Element] = []
        ids: dict[str, Element] = {}
        labels: dict[str, Element] = {}
        attr_index: dict[tuple[str, str], list[Element]] = {}
        n = 0
        for el in doc.root.iter(etree.Element):
            ordinal[el] = n
            tag = el.tag
            if tag not in _NO_TEXT_TAGS:
                text = el.text
                if text and not text.isspace():
                    text_ords.append(n)
                    text_vals.append(text)
                    text_owner.append(el)
                if len(el) == 0:
                    tail = el.tail
                    if tail and not tail.isspace():
                        text_ords.append(n + 0.5)
                        text_vals.append(tail)
                        text_owner.append(el.getparent())
            role_attr = None
            for key, value in el.items():
                if key in _INDEXED_ATTRS or key[:5] == "data-":
                    if key in _PRESENCE_ATTRS:
                        value = ""
                    bucket = attr_index.get((key, value))
                    if bucket is None:
                        attr_index[(key, value)] = [el]
                    else:
                        bucket.append(el)
                    if key == "id":
                        if value and value not in ids:
                            ids[value] = el
                    elif key == "role":
                        role_attr = value
                    elif key == "for" and tag == "label" and value and value not in labels:
                        labels[value] = el
            if tag in HEADING_LIKE or role_attr == "heading":
                heading_ords.append(n)
                heading_els.append(el)
            n += 1
        self.size = n
        self._ordinal = ordinal
        self._heading_ords = heading_ords
        self._heading_els = heading_els
        self._text_ords = text_ords
        self._text_vals = text_vals
        self._text_owner = text_owner
        self._text_low: list[str] | None = None
        self._seg_words: dict[int, frozenset[str]] = {}
        self._heading_words: dict[int, frozenset[str]] = {}
        self._ids = ids
        self._labels = labels
        self._attr_index = attr_index
        self._href_index: dict[str, list[Element]] | None = None
        self._class_index: dict[str, list[Element]] | None = None
        self._roles: dict[Element, str] = {}
        self._headings: dict[int, str] = {}
        self._fingerprints: dict[Element, ElementFingerprint] = {}
        self._node_text: dict[Element, str] = {}
        self._anc_tokens: dict[Element, frozenset[str]] = {}
        self._row_cells: dict[Element, list[Element]] = {}
        self._header_cells: dict[Element, list[Element] | None] = {}
        self._subtree_end: dict[Element, int] = {}
        self._hidden: dict[Element, bool] = {}
        self._hidden_anc: dict[Element, bool] = {}
        self._ancestry: dict[Element, Ancestry] = {}

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

    def node_text(self, el: Element, limit: int = 300) -> str:
        """Normalised ``text_content()`` of ``el`` (cached)."""
        text = self._node_text.get(el)
        if text is None:
            text = self._node_text[el] = normalize_text(el.text_content(), limit)
        return text

    def ancestor_tokens(self, node: Element) -> frozenset[str]:
        """Identity tokens contributed by one ancestor (cached; see ``fingerprint._ancestor_tokens``)."""
        toks = self._anc_tokens.get(node)
        if toks is None:
            from dom_healer.fingerprint import _ancestor_tokens

            out: set[str] = set()
            _ancestor_tokens(node, self, out)
            toks = self._anc_tokens[node] = frozenset(out)
        return toks

    def ancestry(self, el: Element) -> Ancestry:
        """Memoised ancestor-or-self facts for ``el`` (computed top-down, iteratively)."""
        info = self._ancestry.get(el)
        if info is not None:
            return info
        chain = []
        node: Element | None = el
        while node is not None and node not in self._ancestry:
            chain.append(node)
            node = node.getparent()
        parent_info = self._ancestry[node] if node is not None else None
        from dom_healer.fingerprint import _form_signature
        from dom_healer.semantics import LANDMARK_ROLES, STRUCTURAL_ROLES

        for current in reversed(chain):
            tag = current.tag
            role = self.role(current)
            if parent_info is None:
                tag_path: tuple[str, ...] = (tag,)
                sem_path: tuple[str, ...] = ()
                form = landmark = ""
                tokens: tuple[frozenset[str], ...] = ()
                cell = row = table = None
            else:
                tag_path = (*parent_info.tag_path, tag)
                sem_path = parent_info.sem_path
                form, landmark = parent_info.form, parent_info.landmark
                tokens = parent_info.tokens[: _TOKEN_LEVELS - 1]
                cell, row, table = parent_info.cell, parent_info.row, parent_info.table
            if role in STRUCTURAL_ROLES:
                sem_path = (*sem_path, role)
            if tag == "form" or role in ("form", "search"):
                form = _form_signature(current) or tag
            if role in LANDMARK_ROLES:
                landmark = role
            if role in ("cell", "header"):
                cell = current
            elif role == "row":
                row = current
            elif role == "table":
                table = current
            parent_info = self._ancestry[current] = Ancestry(
                tag_path, sem_path, form, landmark, (self.ancestor_tokens(current), *tokens), cell, row, table
            )
        return parent_info

    def row_cells(self, row: Element) -> list[Element]:
        cells = self._row_cells.get(row)
        if cells is None:
            cells = self._row_cells[row] = [
                c for c in row.iter() if c is not row and isinstance(c.tag, str) and self.role(c) in ("cell", "header")
            ]
        return cells

    def header_cells(self, table: Element) -> list[Element] | None:
        """Cells of the first row of ``table`` that consists mostly of header cells."""
        if table in self._header_cells:
            return self._header_cells[table]
        found = None
        for row in table.iter():
            if not isinstance(row.tag, str) or self.role(row) != "row":
                continue
            cells = self.row_cells(row)
            if cells and sum(1 for c in cells if self.role(c) == "header") >= 0.6 * len(cells):
                found = cells
                break
        self._header_cells[table] = found
        return found

    def _heading_text(self, j: int) -> str:
        text = self._headings.get(j)
        if text is None:
            text = self._headings[j] = normalize_text(self._heading_els[j].text_content(), 80)
        return text

    def context_words(self, el: Element, segments: int = 2) -> frozenset[str]:
        """Canonical words of the text runs preceding ``el`` (word sets cached per run)."""
        i = bisect_left(self._text_ords, self._ordinal.get(el, 0))
        out: frozenset[str] = frozenset()
        for j in range(max(0, i - segments), i):
            ws = self._seg_words.get(j)
            if ws is None:
                ws = self._seg_words[j] = canonical_words(normalize_text(self._text_vals[j], 120))
            out = out | ws
        return out

    def heading_words(self, el: Element) -> frozenset[str]:
        j = self._heading_index(el)
        if j < 0:
            return frozenset()
        ws = self._heading_words.get(j)
        if ws is None:
            ws = self._heading_words[j] = canonical_words(self._heading_text(j))
        return ws

    def heading_before(self, el: Element, lookback: int = 12) -> str:
        """Text of the nearest *in-scope* heading that starts before ``el``.

        A heading is in scope if its parent or grandparent also contains ``el``
        (a card title for the card's button, a section heading for the section's
        fields) -- titles of sibling cards are skipped.  If no heading is in
        scope, the nearest preceding ``h1``/``h2`` is used.
        """
        j = self._heading_index(el, lookback)
        return self._heading_text(j) if j >= 0 else ""

    def _heading_index(self, el: Element, lookback: int = 12) -> int:
        i = bisect_left(self._heading_ords, self._ordinal.get(el, 0)) - 1
        if i < 0:
            return -1
        o = self._ordinal.get(el, 0)
        major = -1
        for j in range(i, max(-1, i - lookback), -1):
            heading = self._heading_els[j]
            parent = heading.getparent()
            if parent is None:
                continue
            grandparent = parent.getparent()
            if self.contains(heading, o) or self.contains(parent, o) or (
                grandparent is not None and self.contains(grandparent, o)
            ):
                return j
            if major < 0 and heading.tag in MAJOR_HEADINGS:
                major = j
        return major

    def contains(self, node: Element, ordinal: int) -> bool:
        """True if the element at document position ``ordinal`` lies inside ``node``'s subtree."""
        start = self._ordinal.get(node)
        if start is None:
            return False
        end = self._subtree_end.get(node)
        if end is None:
            end = self._subtree_end[node] = start + sum(1 for _ in node.iter(etree.Element))
        return start <= ordinal < end

    def hidden(self, el: Element) -> bool:
        """Memoised :func:`~dom_healer.semantics.is_hidden` (ancestors are shared between candidates)."""
        value = self._hidden.get(el)
        if value is None:
            parent = el.getparent()
            value = own_hidden(el, first=True) or (parent is not None and self._hidden_ancestor(parent))
            self._hidden[el] = value
        return value

    def _hidden_ancestor(self, el: Element) -> bool:
        value = self._hidden_anc.get(el)
        if value is None:
            parent = el.getparent()
            value = own_hidden(el, first=False) or (parent is not None and self._hidden_ancestor(parent))
            self._hidden_anc[el] = value
        return value

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

    def fingerprint(self, el: Element, selector: str = "", need: frozenset[str] | None = None) -> ElementFingerprint:
        """Fingerprint of ``el`` (cached per element).

        ``need`` (candidate scoring only) lists the optional context fields that
        must be present; others may be skipped.  ``None`` means "everything".
        """
        fp = self._fingerprints.get(el)
        if fp is not None:
            skipped = fp.__dict__.get("_skipped", frozenset())
            if skipped and (need is None or skipped & need):
                fp = None  # a later query needs a field this cached copy skipped
        if fp is None:
            skip = frozenset() if need is None else OPTIONAL_FIELDS - need
            fp = self._fingerprints[el] = build_fingerprint(el, self, skip=skip)
        if selector and fp.selector != selector:
            fp = ElementFingerprint.from_dict({**fp.to_dict(), "selector": selector})
        return fp

    # -- candidate retrieval -----------------------------------------------------------
    def _retrieval_attrs(self, fp: ElementFingerprint) -> list[tuple[str, str, float, bool]]:
        out: list[tuple[str, str, float, bool]] = []
        if fp.id:
            out.append(("id", fp.id, _RETRIEVAL_ATTRS["id"], False))
        for key, value in fp.attrs.items():
            if not value or len(value) > 100:
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

    def _text_matches(self, query_words: list[str]) -> list[Element]:
        """Owners of text runs containing any of ``query_words`` (case-insensitive substring)."""
        if self._text_low is None:
            self._text_low = [t.lower() for t in self._text_vals]
        return [
            owner
            for owner, low in zip(self._text_owner, self._text_low)
            if owner is not None and any(w in low for w in query_words)
        ]

    def elements_with_class(self, name: str) -> list[Element]:
        """Elements whose ``class`` attribute contains the token ``name`` (index built lazily)."""
        if self._class_index is None:
            index: dict[str, list[Element]] = {}
            for el in self.doc.root.iter(etree.Element):
                classes = el.get("class")
                if classes:
                    for token in classes.split():
                        index.setdefault(token, []).append(el)
            self._class_index = index
        return self._class_index.get(name, [])

    def elements_with(self, key: str, value: str = "") -> list[Element]:
        """Elements whose attribute ``key`` equals ``value`` (presence for onclick/contenteditable)."""
        return list(self._attr_index.get((key, value), ()))

    def _href_matches(self, path: str) -> list[Element]:
        if self._href_index is None:
            from dom_healer.fingerprint import _norm_url

            index: dict[str, list[Element]] = {}
            for (key, value), elements in self._attr_index.items():
                if key == "href":
                    index.setdefault(_norm_url(value), []).extend(elements)
            self._href_index = index
        return self._href_index.get(path, [])

    def _family_members(self, fp: ElementFingerprint) -> list[Element]:
        root = self.doc.root
        spec = _FAMILY_SPECS.get(fp.family)
        if spec is None:
            return list(root.iter(fp.tag))
        tags, roles, input_types, presence = spec
        out = list(root.iter(fp.tag, *tags)) if fp.tag not in tags else list(root.iter(*tags))
        for role in roles:
            out.extend(self._attr_index.get(("role", role), ()))
        if input_types == "text-like":
            out.extend(el for el in root.iter("input") if (el.get("type") or "text").lower() not in _NON_TEXT_INPUTS)
        else:
            for input_type in input_types:
                out.extend(el for el in self._attr_index.get(("type", input_type), ()) if el.tag == "input")
        for key in presence:
            out.extend(self._attr_index.get((key, ""), ()))
        return out

    def candidate_pool(self, fp: ElementFingerprint, extra: Iterable[Element] = ()) -> list[Element]:
        """Union of elements that share *anything* cheap to check with ``fp``."""
        return [el for el in self._pool(fp, extra) if isinstance(el.tag, str) and el.tag not in SKIP_TAGS]

    def _pool(self, fp: ElementFingerprint, extra: Iterable[Element] = ()) -> dict[Element, bool]:
        """Pool as ``{element: shares_text_with_fp}``."""
        pool: dict[Element, bool] = dict.fromkeys(self._family_members(fp), False)
        for key, value, _w, contains in self._retrieval_attrs(fp):
            if contains:  # href: compare normalised paths
                pool.update(dict.fromkeys(self._href_matches(value), False))
            else:
                pool.update(dict.fromkeys(self._attr_index.get((key, value), ()), False))
        query_words = self._query_words(fp)
        if query_words:
            for el in self._text_matches(query_words):
                pool[el] = True
                parent = el.getparent()
                for _ in range(2):
                    if parent is None:
                        break
                    if parent.tag == fp.tag or element_family(parent.tag, self.role(parent)) == fp.family:
                        pool[parent] = True
                    parent = parent.getparent()
        for el in extra:
            pool[el] = True
        return pool

    def prescore(self, fp: ElementFingerprint, el: Element, attrs: list[tuple[str, str, float, bool]],
                 fp_words: frozenset[str], fp_heading: frozenset[str] = frozenset(),
                 fp_context: frozenset[str] = frozenset()) -> float:
        """Cheap similarity used to cut the pool down before full fingerprinting."""
        return self._structural_score(fp, el, attrs, fp_heading, fp_context) + self._text_score(el, fp_words)

    def _structural_score(self, fp: ElementFingerprint, el: Element, attrs: list[tuple[str, str, float, bool]],
                          fp_heading: frozenset[str], fp_context: frozenset[str]) -> float:
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
        if fp_heading:
            score += 1.0 * jaccard(fp_heading, self.heading_words(el))
        if fp_context:
            score += 1.0 * jaccard(fp_context, self.context_words(el))
        return score + 0.5 * (1.0 - abs(self.position(el) - fp.position))

    def _text_score(self, el: Element, fp_words: frozenset[str]) -> float:
        if not fp_words:
            return 0.0
        own = el.get("aria-label")
        tag = el.tag
        if own:
            own = normalize_text(own, 120)
        elif tag in ("input", "select", "textarea"):
            own = normalize_text(el.get("placeholder") or "", 120)
            if el.get("id"):
                own = self.label_text_for(el.get("id")) or own
        else:
            own = self.node_text(el, 120) if len(el) <= 8 else ""
        return 2.0 * jaccard(fp_words, canonical_words(own)) if own else 0.0

    def candidates(
        self,
        fp: ElementFingerprint,
        k: int = 24,
        extra: Iterable[Element] = (),
        k_min: int = 12,
        ratio: float = 0.6,
        phase1_keep: int = 256,
    ) -> list[tuple[Element, float]]:
        """Candidate elements for ``fp`` with their normalised pre-scores (best first).

        Keeps the top ``k_min`` plus any further candidates (up to ``k``) whose
        pre-score is at least ``ratio`` x the best one.  ``phase1_keep`` bounds how
        many pool members get the text pre-score on pathological (huge) pools.
        """
        pool = self._pool(fp, extra)
        attrs = self._retrieval_attrs(fp)
        fp_words = canonical_words(fp.accessible_name or fp.full_text or fp.label)
        fp_heading = canonical_words(fp.heading)
        fp_context = canonical_words(fp.context)
        # Phase 1: structural score for the whole pool (text-sharing elements get a bonus so they survive).
        phase1 = [
            (self._structural_score(fp, el, attrs, fp_heading, fp_context) + (1.0 if shares_text else 0.0),
             -self._ordinal.get(el, 0), el, shares_text)
            for el, shares_text in pool.items()
            if isinstance(el.tag, str) and el.tag not in SKIP_TAGS
        ]
        if not phase1:
            return []
        if len(phase1) > phase1_keep:
            phase1 = heapq.nlargest(phase1_keep, phase1, key=lambda item: (item[0], item[1]))
        # Phase 2: add the (more expensive) text similarity for the survivors.
        scored = [
            (s1 - (1.0 if shares_text else 0.0) + self._text_score(el, fp_words), o, el)
            for s1, o, el, shares_text in phase1
        ]
        top = heapq.nlargest(k, scored, key=lambda item: (item[0], item[1]))
        best = top[0][0] or 1.0
        return [(el, score / best) for i, (score, _o, el) in enumerate(top) if i < k_min or score >= ratio * best]


def get_index(doc: Document) -> PageIndex:
    """Return the (cached) :class:`PageIndex` of ``doc``.

    The index is built on first use; do not mutate the tree afterwards.
    """
    index = doc._index
    if index is None:
        index = doc._index = PageIndex(doc)
    return index
