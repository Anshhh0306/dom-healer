"""dom-healer: self-healing DOM selectors via structural element fingerprints."""

from dom_healer.dom import Document, ParseError, SelectorError, ensure_document, parse_html, select

__version__ = "0.1.0"

__all__ = ["Document", "ParseError", "SelectorError", "ensure_document", "parse_html", "select", "__version__"]
