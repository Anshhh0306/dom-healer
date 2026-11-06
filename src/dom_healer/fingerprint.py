"""Structural element fingerprints.

An :class:`ElementFingerprint` is a small, JSON-serialisable description of an
element that does not depend on the exact selector used to find it: tag and
ARIA role, stable attributes (``data-*``, ``aria-*``, ``name``, ``type``, …),
visible text and accessible name, the label/heading/row/column context it
appears in, its tag path / semantic path / depth, and its sibling
neighbourhood.  Fingerprints are captured while a selector still works and are
compared against candidate elements once it breaks.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

from lxml import etree

from dom_healer.semantics import (
    FORM_CONTROL_TAGS,
    STRUCTURAL_ROLES,
    element_family,
)
from dom_healer.text import (
    class_tokens,
    identifier_tokens,
    looks_generated,
    looks_random,
    normalize_text,
    words,
)

if TYPE_CHECKING:  # pragma: no cover
    from dom_healer.index import PageIndex

Element = etree._Element

FINGERPRINT_VERSION = 1

#: Attributes recorded in ``ElementFingerprint.attrs`` besides all ``data-*``/``aria-*``.
STABLE_ATTRS = frozenset(
    {
        "name", "type", "role", "placeholder", "title", "alt", "href", "src", "for", "action", "method", "rel",
        "target", "autocomplete", "inputmode", "pattern", "min", "max", "step", "maxlength", "accept", "multiple",
        "required", "readonly", "disabled", "colspan", "rowspan", "scope", "label", "datetime", "download", "value",
    }
)
#: Attributes whose value is user data for text-like inputs (ignored there).
_VALUE_IS_DATA = frozenset({"text", "email", "search", "tel", "url", "password", "number", "date", "datetime-local",
                            "month", "week", "time", ""})
TEST_ATTRS = ("data-testid", "data-test", "data-test-id", "data-qa", "data-cy", "data-automation-id", "data-e2e",
              "data-test-selector", "data-hook")
_WRAPPER_TAGS = frozenset({"div", "span", "section", "article", "label", "p", "em", "strong", "b", "i", "small"})
_TEXT_SKIP = frozenset({"script", "style", "noscript", "template"})
_ANCESTOR_TOKEN_LEVELS = 6


@dataclass
class ElementFingerprint:
    """Selector-independent description of an element (see module docstring)."""

    tag: str
    role: str = ""
    family: str = ""
    id: str = ""
    classes: list[str] = field(default_factory=list)
    attrs: dict[str, str] = field(default_factory=dict)
    text: str = ""
    full_text: str = ""
    accessible_name: str = ""
    label: str = ""
    heading: str = ""
    context: str = ""
    next_context: str = ""
    container: str = ""
    row: str = ""
    column_header: str = ""
    form: str = ""
    landmark: str = ""
    tag_path: list[str] = field(default_factory=list)
    semantic_path: list[str] = field(default_factory=list)
    ancestor_tokens: list[str] = field(default_factory=list)
    parent: str = ""
    prev_sibling: str = ""
    next_sibling: str = ""
    sibling_index: int = 0
    sibling_count: int = 1
    children: list[str] = field(default_factory=list)
    depth: int = 0
    position: float = 0.0
    hidden: bool = False
    shadow_depth: int = 0
    selector: str = ""
    version: int = FINGERPRINT_VERSION

    # -- serialisation ---------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, **kwargs: Any) -> str:
        kwargs.setdefault("ensure_ascii", False)
        return json.dumps(self.to_dict(), **kwargs)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ElementFingerprint:
        if not isinstance(data, dict) or not data.get("tag"):
            raise ValueError("fingerprint data must be a mapping with a non-empty 'tag'")
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    @classmethod
    def from_json(cls, payload: str) -> ElementFingerprint:
        return cls.from_dict(json.loads(payload))

    # -- derived views -------------------------------------------------------------------
    def test_attrs(self) -> dict[str, str]:
        return {k: self.attrs[k] for k in TEST_ATTRS if k in self.attrs}

    def summary(self) -> str:
        """Short human-readable description (for logs and CLI output)."""
        bits = [self.tag]
        if self.role and self.role != self.tag:
            bits.append(f"role={self.role}")
        name = self.accessible_name or self.text
        if name:
            bits.append(repr(name[:40]))
        if self.heading:
            bits.append(f"under {self.heading[:30]!r}")
        if self.row:
            bits.append(f"row {self.row[:30]!r}")
        return " ".join(bits)


# ---------------------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------------------


def direct_text(el: Element) -> str:
    """Text that belongs directly to ``el`` (its ``.text`` plus its children's tails)."""
    if el.tag in _TEXT_SKIP:
        return ""
    parts = [el.text] if el.text else []
    for child in el:
        if child.tail:
            parts.append(child.tail)
    return " ".join(parts)


def text_without(el: Element, skip: frozenset[str]) -> str:
    """Text content of ``el`` excluding descendants whose tag is in ``skip`` (tails are kept)."""
    out: list[str] = []

    def walk(node: Element) -> None:
        if node.text and node.tag not in _TEXT_SKIP:
            out.append(node.text)
        for child in node:
            if isinstance(child.tag, str) and child.tag not in skip and child.tag not in _TEXT_SKIP:
                walk(child)
            if child.tail:
                out.append(child.tail)

    walk(el)
    return " ".join(out)


def _norm_url(value: str) -> str:
    try:
        parts = urlsplit(value)
    except ValueError:  # pragma: no cover - extremely malformed URLs
        return value
    return (parts.path or "") + (("#" + parts.fragment) if parts.fragment and not parts.path else "")


def stable_attrs(el: Element) -> dict[str, str]:
    """Attributes that tend to carry identity rather than styling."""
    out: dict[str, str] = {}
    input_type = (el.get("type") or "").lower() if el.tag == "input" else None
    for key, value in el.items():
        key = key.lower()
        if key.startswith(("data-", "aria-")) or key in STABLE_ATTRS:
            if key == "value" and (el.tag in ("textarea", "select") or (input_type is not None and input_type in _VALUE_IS_DATA)):
                continue
            if key in ("href", "src", "action"):
                value = _norm_url(value)
            value = " ".join(value.split())
            out[key] = value.lower() if key == "type" else value[:120]
    return out


def _is_wrapper(node: Element, index: PageIndex) -> bool:
    tag = node.tag
    if tag not in _WRAPPER_TAGS and "-" not in tag:
        return False
    if index.role(node) in STRUCTURAL_ROLES:
        return False
    if node.text and node.text.strip():
        return False
    elements = [c for c in node if isinstance(c.tag, str)]
    if len(elements) != 1:
        return False
    return not any(c.tail and c.tail.strip() for c in node)


def _collapse_down(node: Element, index: PageIndex, limit: int = 3) -> Element:
    for _ in range(limit):
        if not _is_wrapper(node, index):
            break
        node = next(c for c in node if isinstance(c.tag, str))
    return node


def _signature(node: Element | None, index: PageIndex) -> str:
    if node is None:
        return ""
    node = _collapse_down(node, index)
    return f"{node.tag}|{normalize_text(node.text_content(), 40)}"


def _element_siblings(node: Element) -> list[Element]:
    parent = node.getparent()
    if parent is None:
        return [node]
    return [c for c in parent if isinstance(c.tag, str)]


def _form_signature(form: Element) -> str:
    toks: list[str] = []
    for attr in ("id", "name"):
        value = form.get(attr)
        if value and not looks_generated(value):
            toks.extend(identifier_tokens(value))
    action = form.get("action")
    if action:
        toks.extend(identifier_tokens(_norm_url(action)))
    label = form.get("aria-label")
    if label:
        toks.extend(words(normalize_text(label)))
    toks.extend(sorted(class_tokens(tuple((form.get("class") or "").split()))))
    return " ".join(dict.fromkeys(toks))


def _ancestor_tokens(node: Element, index: PageIndex, out: set[str]) -> None:
    value = node.get("id")
    if value and not looks_generated(value):
        out.update(identifier_tokens(value))
    cls = node.get("class")
    if cls:
        out.update(class_tokens(tuple(cls.split())))
    for key, value in node.items():
        if key.startswith("data-") and key not in ("data-reactroot",):
            out.update(identifier_tokens(key[5:]))
            if value and len(value) <= 40 and not looks_random(value):
                out.update(identifier_tokens(value))
        elif key == "aria-label":
            out.update(words(normalize_text(value)))
    role = index.role(node)
    if role:
        out.add("role:" + role)


def accessible_name(el: Element, index: PageIndex) -> tuple[str, str]:
    """Approximate accessible name and associated label text of ``el``.

    Returns ``(name, label)`` where ``label`` is the text of an associated
    ``<label>`` / ``aria-labelledby`` target (empty if none).
    """
    label = ""
    labelledby = el.get("aria-labelledby")
    if labelledby:
        texts = []
        for ref in labelledby.split():
            target = index.by_id(ref)
            if target is not None:
                texts.append(target.text_content())
        label = normalize_text(" ".join(texts), 120)
    tag = el.tag
    if not label and tag in FORM_CONTROL_TAGS:
        el_id = el.get("id")
        if el_id:
            label = index.label_text_for(el_id)
        if not label:
            for anc in el.iterancestors():
                if anc.tag == "label":
                    label = normalize_text(text_without(anc, frozenset({"select", "textarea", "option", "datalist"})), 120)
                    break
                if anc.tag in ("form", "body", "fieldset", "table"):
                    break
    aria_label = el.get("aria-label")
    if aria_label and aria_label.strip():
        return normalize_text(aria_label, 120), label
    if label:
        return label, label
    if tag == "input":
        input_type = (el.get("type") or "text").lower()
        if input_type in ("submit", "button", "reset"):
            return normalize_text(el.get("value") or input_type, 120), label
        if input_type == "image":
            return normalize_text(el.get("alt") or el.get("title") or "", 120), label
    if tag in FORM_CONTROL_TAGS:
        return normalize_text(el.get("placeholder") or el.get("title") or "", 120), label
    if tag == "img":
        return normalize_text(el.get("alt") or el.get("title") or "", 120), label
    name = normalize_text(el.text_content(), 120) if tag not in _TEXT_SKIP else ""
    if not name:
        img = next((c for c in el.iter("img") if c.get("alt")), None)
        if img is not None:
            name = normalize_text(img.get("alt"), 120)
    if not name:
        name = normalize_text(el.get("title") or "", 120)
    return name, label


def _table_context(cell: Element, row: Element, table: Element | None, index: PageIndex) -> tuple[str, str]:
    cells = index.row_cells(row)
    col = next((i for i, c in enumerate(cells) if c is cell), -1)
    row_text = " | ".join(t for t in (index.node_text(c, 60) for c in cells if c is not cell) if t)
    header = ""
    if table is not None and col >= 0:
        hcells = index.header_cells(table)
        if hcells is not None and hcells is not cells and col < len(hcells):
            header = index.node_text(hcells[col], 60)
    return normalize_text(row_text, 200), header


def _container_text(el: Element, own_len: int, index: PageIndex, levels: int = 6) -> str:
    """Text of the nearest ancestor that holds text besides ``el`` (card, line item, field group)."""
    node = el
    for _ in range(levels):
        parent = node.getparent()
        if parent is None or parent.tag in ("body", "html"):
            break
        text = index.node_text(parent)
        if len(text) > own_len + 12:
            return text
        node = parent
    return ""


def build_fingerprint(el: Element, index: PageIndex, selector: str = "") -> ElementFingerprint:
    """Capture the fingerprint of ``el`` (an element of ``index.doc``)."""
    tag = el.tag
    role = index.role(el)
    attrs = stable_attrs(el)
    input_type = attrs.get("type", "") if tag == "input" else ""
    classes = (el.get("class") or "").split()

    # Ancestor information is memoised per node in the index (candidates share most ancestors).
    parent_el = el.getparent()
    if parent_el is not None:
        anc = index.ancestry(parent_el)
        tag_path = [*anc.tag_path, tag]
        sem_path = list(anc.sem_path)
        anc_tokens: set[str] = set().union(*anc.tokens) if anc.tokens else set()
        form_sig, landmark = anc.form, anc.landmark
        cell = el if role in ("cell", "header") else anc.cell
    else:
        tag_path, sem_path, anc_tokens, form_sig, landmark = [tag], [], set(), "", ""
        cell = el if role in ("cell", "header") else None
    row = table = None
    if cell is not None:
        cell_parent = cell.getparent()
        row = index.ancestry(cell_parent).row if cell_parent is not None else None
        if row is not None:
            row_parent = row.getparent()
            table = index.ancestry(row_parent).table if row_parent is not None else None
    depth = len(tag_path) - 1

    name, label = accessible_name(el, index)

    # Wrapper-insensitive sibling neighbourhood.
    node = el
    for _ in range(3):
        parent = node.getparent()
        if parent is None or parent is index.doc.root or not _is_wrapper(parent, index):
            break
        node = parent
    siblings = _element_siblings(node)
    pos = next(i for i, s in enumerate(siblings) if s is node)
    same = [s for s in siblings if s.tag == node.tag]
    same_pos = next(i for i, s in enumerate(same) if s is node)
    parent = node.getparent()
    parent_sig = ""
    if parent is not None:
        parent_sig = " ".join([parent.tag, *sorted(class_tokens(tuple((parent.get("class") or "").split())))])

    row_text, header = ("", "")
    if cell is not None and row is not None:
        row_text, header = _table_context(cell, row, table, index)

    full_text = index.node_text(el, 200) if tag not in _TEXT_SKIP else ""
    container = _container_text(el, len(full_text), index)
    return ElementFingerprint(
        tag=tag,
        role=role,
        family=element_family(tag, role, input_type),
        id=el.get("id") or "",
        classes=classes,
        attrs=attrs,
        text=normalize_text(direct_text(el), 200),
        full_text=full_text,
        accessible_name=name,
        label=label,
        heading=index.heading_before(el),
        context=index.text_before(el),
        next_context=index.text_after(el),
        container=container,
        row=row_text,
        column_header=header,
        form=form_sig,
        landmark=landmark,
        tag_path=tag_path,
        semantic_path=sem_path,
        ancestor_tokens=sorted(anc_tokens),
        parent=parent_sig,
        prev_sibling=_signature(siblings[pos - 1], index) if pos > 0 else "",
        next_sibling=_signature(siblings[pos + 1], index) if pos + 1 < len(siblings) else "",
        sibling_index=same_pos,
        sibling_count=len(same),
        children=[c.tag for c in el if isinstance(c.tag, str)][:12],
        depth=depth,
        position=index.position(el),
        hidden=index.hidden(el),
        shadow_depth=index.doc.shadow_depth(el),
        selector=selector,
    )
