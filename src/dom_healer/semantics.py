"""ARIA roles, element families, landmarks and visibility heuristics."""

from __future__ import annotations

import re

from lxml import etree

Element = etree._Element

HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
FORM_CONTROL_TAGS = frozenset({"input", "select", "textarea"})

_INPUT_ROLES = {
    "button": "button",
    "submit": "button",
    "reset": "button",
    "image": "button",
    "checkbox": "checkbox",
    "radio": "radio",
    "range": "slider",
    "number": "spinbutton",
    "search": "searchbox",
    "hidden": "",
    "file": "button",
    "color": "button",
}

_TAG_ROLES = {
    "button": "button",
    "summary": "button",
    "nav": "navigation",
    "main": "main",
    "aside": "complementary",
    "form": "form",
    "search": "search",
    "table": "table",
    "thead": "rowgroup",
    "tbody": "rowgroup",
    "tfoot": "rowgroup",
    "tr": "row",
    "td": "cell",
    "th": "columnheader",
    "ul": "list",
    "ol": "list",
    "menu": "list",
    "li": "listitem",
    "dl": "list",
    "dialog": "dialog",
    "article": "article",
    "img": "img",
    "select": "combobox",
    "textarea": "textbox",
    "option": "option",
    "progress": "progressbar",
    "meter": "meter",
    "fieldset": "group",
    "details": "group",
    "output": "status",
    "header": "banner",
    "footer": "contentinfo",
    "section": "region",
    "hr": "separator",
    "h1": "heading",
    "h2": "heading",
    "h3": "heading",
    "h4": "heading",
    "h5": "heading",
    "h6": "heading",
}

#: Roles that are treated as equivalent when comparing elements across versions.
ROLE_CANON = {
    "gridcell": "cell",
    "rowheader": "header",
    "columnheader": "header",
    "grid": "table",
    "treegrid": "table",
    "searchbox": "textbox",
    "listbox": "combobox",
    "switch": "checkbox",
    "menuitemcheckbox": "checkbox",
    "menuitemradio": "radio",
    "menuitem": "button",
    "presentation": "",
    "none": "",
}

LANDMARK_ROLES = frozenset(
    {"banner", "navigation", "main", "complementary", "contentinfo", "form", "search", "region", "dialog", "alertdialog"}
)

#: Roles kept in the "semantic path" (structure that survives wrapper/class churn).
STRUCTURAL_ROLES = LANDMARK_ROLES | frozenset(
    {"table", "row", "rowgroup", "cell", "header", "list", "listitem", "article", "group", "tablist", "tabpanel", "menu",
     "menubar", "toolbar", "radiogroup", "combobox", "heading"}
)


def element_role(el: Element) -> str:
    """Explicit ARIA role, or an approximation of the implicit role (canonicalised)."""
    explicit = el.get("role")
    if explicit:
        role = explicit.split()[0].lower()
        return ROLE_CANON.get(role, role)
    tag = el.tag
    if tag == "input":
        role = _INPUT_ROLES.get((el.get("type") or "text").lower(), "textbox")
    elif tag in ("a", "area"):
        role = "link" if el.get("href") is not None else ""
    else:
        role = _TAG_ROLES.get(tag, "")
    if tag == "select" and (el.get("multiple") is not None or (el.get("size") or "1") not in ("", "0", "1")):
        role = "combobox"
    if el.get("contenteditable") in ("", "true"):
        role = "textbox"
    return ROLE_CANON.get(role, role)


def element_family(tag: str, role: str, input_type: str = "") -> str:
    """Coarse functional family used to compare elements whose tag changed."""
    if role in ("button", "link", "tab", "menuitem"):
        return "clickable"
    if role in ("checkbox", "radio"):
        return "choice"
    if role in ("textbox", "spinbutton", "slider"):
        return "text_input"
    if role == "combobox":
        return "select"
    if role in ("cell", "header"):
        return "cell"
    if role == "heading" or tag in ("legend", "caption"):
        return "heading"
    if role == "img" or tag in ("img", "svg", "picture", "video", "canvas"):
        return "media"
    if role in ("listitem", "option") or tag in ("dt", "dd"):
        return "list_item"
    if tag in ("p", "span", "strong", "b", "em", "i", "small", "label", "code", "time", "abbr", "mark", "output", "data",
               "sup", "sub", "del", "ins", "s", "u", "bdi", "q", "cite"):
        return "text"
    if tag == "input":
        return "text_input" if input_type != "hidden" else "hidden"
    return "container"


_HIDDEN_STYLE = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden", re.I)
_HIDDEN_CLASSES = frozenset({"hidden", "d-none", "is-hidden", "invisible", "display-none", "hide", "u-hidden"})
_RESPONSIVE_SHOW = re.compile(r"(?:^|\s)(?:sm|md|lg|xl|2xl):(?:block|flex|grid|inline|inline-block|inline-flex|table)(?:\s|$)")


def own_hidden(node: Element, first: bool = True) -> bool:
    """Does ``node`` itself hide its subtree?  (``first``: ``node`` is the element being tested.)"""
    if node.get("hidden") is not None or node.get("aria-hidden") == "true":
        return True
    style = node.get("style")
    if style and _HIDDEN_STYLE.search(style):
        return True
    cls = node.get("class")
    if cls and not _HIDDEN_CLASSES.isdisjoint(cls.split()) and not _RESPONSIVE_SHOW.search(cls):
        return True
    tag = node.tag
    if first and tag == "input" and (node.get("type") or "").lower() == "hidden":
        return True
    return (tag == "dialog" and node.get("open") is None) or tag == "template"


def is_hidden(el: Element) -> bool:
    """Best-effort static visibility check (no CSS engine): hidden attrs, inline styles, common classes."""
    node: Element | None = el
    first = True
    while node is not None:
        if own_hidden(node, first):
            return True
        first = False
        node = node.getparent()
    return False
