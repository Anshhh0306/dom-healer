"""HTML parsing, the composed-tree model, and selector evaluation.

dom-healer works on a *composed tree*: declarative shadow roots
(``<template shadowrootmode="open">``) are flattened into their host element,
so the children of the shadow root become children of the host.  This mirrors
how shadow-piercing selector engines (e.g. Playwright's CSS engine) see the page
and lets plain CSS/XPath reach elements that live inside shadow DOM.  The
original shadow boundaries are remembered on the :class:`Document` so that they
can still be used as fingerprint signals.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from cssselect import HTMLTranslator
from cssselect import SelectorError as _CssSelectorError
from lxml import etree
from lxml import html as lxml_html

Element = etree._Element

#: Attributes that mark a ``<template>`` as a declarative shadow root.
SHADOW_ROOT_ATTRS = ("shadowrootmode", "shadowroot")


class DomHealerError(Exception):
    """Base class for all dom-healer errors."""


class ParseError(DomHealerError, ValueError):
    """Raised when markup cannot be parsed into a document."""


class SelectorError(DomHealerError, ValueError):
    """Raised for invalid selectors or selectors that do not select elements."""


def _drop_tag(el: Element) -> None:
    """Remove ``el`` but keep its children and text in place (like ``HtmlElement.drop_tag``)."""
    parent = el.getparent()
    if parent is None:  # pragma: no cover - callers only pass attached elements
        return
    previous = el.getprevious()
    if el.text:
        if previous is None:
            parent.text = (parent.text or "") + el.text
        else:
            previous.tail = (previous.tail or "") + el.text
    if el.tail:
        if len(el):
            last = el[-1]
            last.tail = (last.tail or "") + el.tail
        elif previous is None:
            parent.text = (parent.text or "") + el.tail
        else:
            previous.tail = (previous.tail or "") + el.tail
    index = parent.index(el)
    parent[index : index + 1] = el[:]


def _shadow_templates(root: Element) -> list[Element]:
    return [
        t
        for t in root.iter("template")
        if any(t.get(attr) is not None for attr in SHADOW_ROOT_ATTRS) and t.getparent() is not None
    ]


class Document:
    """A parsed HTML document in the composed-tree model.

    Use :func:`parse_html` (or :meth:`Document.from_html`) to build one.  The
    underlying lxml tree is available as :attr:`root`; elements returned by
    dom-healer always belong to this tree.
    """

    __slots__ = ("root", "tree", "_shadow_children", "_shadow_hosts", "_index", "__weakref__")

    def __init__(self, root: Element) -> None:
        self.root: Element = root
        self.tree = root.getroottree()
        self._shadow_children: set[Element] = set()
        self._shadow_hosts: dict[Element, str] = {}
        self._index: Any = None
        self._flatten_shadow_roots()

    # -- construction -------------------------------------------------------------
    @classmethod
    def from_html(cls, markup: str | bytes) -> Document:
        if isinstance(markup, bytes):
            if not markup.strip():
                raise ParseError("cannot parse an empty document")
        elif isinstance(markup, str):
            if not markup.strip():
                raise ParseError("cannot parse an empty document")
            # lxml refuses str input that carries an XML encoding declaration.
            if markup.lstrip().startswith("<?xml"):
                markup = markup.encode("utf-8")
        else:
            raise TypeError(f"expected str or bytes, got {type(markup).__name__}")
        try:
            root = lxml_html.document_fromstring(markup)
        except (etree.ParserError, ValueError) as exc:
            raise ParseError(f"could not parse HTML: {exc}") from exc
        return cls(root)

    def _flatten_shadow_roots(self) -> None:
        # Outer templates are processed first; nested templates simply move along
        # with their parents and are flattened in turn.
        for template in _shadow_templates(self.root):
            host = template.getparent()
            mode = (template.get("shadowrootmode") or template.get("shadowroot") or "open").lower()
            for child in template:
                if isinstance(child.tag, str):
                    self._shadow_children.add(child)
            self._shadow_hosts[host] = mode
            _drop_tag(template)

    # -- shadow DOM bookkeeping -----------------------------------------------------
    @property
    def shadow_hosts(self) -> dict[Element, str]:
        """Mapping of shadow-host element -> shadow root mode (``open``/``closed``)."""
        return dict(self._shadow_hosts)

    def is_shadow_root_child(self, el: Element) -> bool:
        """True if ``el`` was a top-level child of a declarative shadow root."""
        return el in self._shadow_children

    def shadow_host_of(self, el: Element) -> Element | None:
        """Return the nearest shadow host whose shadow tree contains ``el`` (or ``None``)."""
        node: Element | None = el
        while node is not None:
            if node in self._shadow_children:
                return node.getparent()
            node = node.getparent()
        return None

    def shadow_depth(self, el: Element) -> int:
        """Number of shadow-root boundaries between the document root and ``el``."""
        depth = 0
        node: Element | None = el
        while node is not None:
            if node in self._shadow_children:
                depth += 1
            node = node.getparent()
        return depth

    # -- selectors --------------------------------------------------------------------
    def select(self, selector: str) -> list[Element]:
        """Evaluate a CSS or XPath selector against the composed tree."""
        return select(self.root, selector)

    def select_one(self, selector: str) -> Element | None:
        matches = self.select(selector)
        return matches[0] if matches else None

    def absolute_xpath(self, el: Element) -> str:
        """Fully positional XPath of ``el`` (like DevTools' *Copy full XPath*)."""
        return self.tree.getpath(el)

    def __len__(self) -> int:
        return sum(1 for _ in self.root.iter(etree.Element))

    def __repr__(self) -> str:
        return f"<Document elements={len(self)} shadow_hosts={len(self._shadow_hosts)}>"


def parse_html(markup: str | bytes) -> Document:
    """Parse HTML markup into a :class:`Document` (composed-tree model)."""
    return Document.from_html(markup)


def ensure_document(obj: Any) -> Document:
    """Coerce ``obj`` into a :class:`Document`.

    Accepts a :class:`Document`, HTML ``str``/``bytes``, an lxml element/tree
    (declarative shadow templates are flattened *in place*), or a
    BeautifulSoup object (serialised and re-parsed with lxml).
    """
    if isinstance(obj, Document):
        return obj
    if isinstance(obj, (str, bytes)):
        return Document.from_html(obj)
    if isinstance(obj, etree._ElementTree):
        return Document(obj.getroot())
    if isinstance(obj, etree._Element):
        return Document(obj.getroottree().getroot())
    # BeautifulSoup / bs4.Tag (duck-typed so bs4 stays an optional dependency)
    if hasattr(obj, "find_all") and hasattr(obj, "decode"):
        return Document.from_html(str(obj))
    raise TypeError(f"cannot build a Document from {type(obj).__name__}")


# ---------------------------------------------------------------------------------------
# Selector evaluation
# ---------------------------------------------------------------------------------------

_TRANSLATOR = HTMLTranslator()


def classify_selector(selector: str) -> tuple[str, str]:
    """Return ``(kind, expression)`` where kind is ``"css"`` or ``"xpath"``.

    Playwright-style ``css=`` / ``xpath=`` prefixes are understood; otherwise a
    selector starting with ``/``, ``./``, ``..`` or ``(`` is treated as XPath.
    """
    if not isinstance(selector, str):
        raise SelectorError(f"selector must be a string, got {type(selector).__name__}")
    s = selector.strip()
    if not s:
        raise SelectorError("empty selector")
    lowered = s.lower()
    for prefix in ("xpath=", "xpath:"):
        if lowered.startswith(prefix):
            return "xpath", s[len(prefix) :].strip()
    for prefix in ("css=", "css:"):
        if lowered.startswith(prefix):
            return "css", s[len(prefix) :].strip()
    if s.startswith(("/", "./", "..", "(")):
        return "xpath", s
    return "css", s


@lru_cache(maxsize=2048)
def compile_selector(kind: str, expression: str) -> etree.XPath:
    """Compile (and cache) a selector into an lxml XPath evaluator."""
    if not expression:
        raise SelectorError("empty selector")
    if kind == "css":
        try:
            xpath = _TRANSLATOR.css_to_xpath(expression)
        except _CssSelectorError as exc:
            raise SelectorError(f"invalid CSS selector {expression!r}: {exc}") from exc
    elif kind == "xpath":
        xpath = expression
    else:
        raise SelectorError(f"unknown selector kind {kind!r}")
    try:
        return etree.XPath(xpath)
    except etree.XPathSyntaxError as exc:
        raise SelectorError(f"invalid XPath {expression!r}: {exc}") from exc


def select(root: Element | Document, selector: str) -> list[Element]:
    """Evaluate ``selector`` (CSS or XPath) and return matching elements in document order."""
    if isinstance(root, Document):
        root = root.root
    kind, expression = classify_selector(selector)
    evaluator = compile_selector(kind, expression)
    try:
        result = evaluator(root)
    except etree.XPathEvalError as exc:
        raise SelectorError(f"could not evaluate {selector!r}: {exc}") from exc
    if not isinstance(result, list):
        raise SelectorError(f"selector {selector!r} must select elements, got {type(result).__name__}")
    return [node for node in result if isinstance(node, etree._Element) and isinstance(node.tag, str)]
