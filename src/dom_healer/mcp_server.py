"""Model Context Protocol server exposing dom-healer to AI agents and IDEs.

Run with ``dom-healer mcp`` (stdio transport).  Requires the ``mcp`` extra:
``pip install "dom-healer[mcp]"``.

Tools:

* ``repair_selector(old_html, new_html, selector, top_k, ranker)``
* ``capture_fingerprint(html, selector)``
* ``locate_element(fingerprint, html, top_k, ranker)``

The tool bodies are plain functions (``repair_selector`` etc.) so they can be
used and tested without an MCP runtime.
"""

from __future__ import annotations

from typing import Any

from dom_healer.dom import parse_html
from dom_healer.fingerprint import ElementFingerprint
from dom_healer.healer import Healer
from dom_healer.healer import capture_fingerprint as _capture

SERVER_INSTRUCTIONS = (
    "dom-healer repairs broken CSS/XPath selectors after a web page changes. "
    "Call repair_selector with the HTML where the selector worked, the current HTML and the selector; "
    "it returns a verified replacement selector, a confidence score and ranked alternatives. "
    "To heal later without keeping old HTML, store capture_fingerprint output and use locate_element."
)


def repair_selector(old_html: str, new_html: str, selector: str, top_k: int = 3, ranker: str = "auto") -> dict[str, Any]:
    """Repair a CSS/XPath selector that worked on old_html so it finds the same element in new_html."""
    fingerprint = _capture(parse_html(old_html), selector)
    result = Healer(parse_html(new_html), ranker=ranker).locate(fingerprint, selector=selector)
    return result.to_dict(top_k=max(1, top_k))


def capture_fingerprint(html: str, selector: str) -> dict[str, Any]:
    """Capture a structural fingerprint (JSON) of the element matched by selector."""
    return _capture(parse_html(html), selector).to_dict()


def locate_element(fingerprint: dict[str, Any], html: str, top_k: int = 3, ranker: str = "auto") -> dict[str, Any]:
    """Locate the element described by a stored fingerprint in html and return a fresh selector."""
    fp = ElementFingerprint.from_dict(fingerprint)
    result = Healer(parse_html(html), ranker=ranker).locate(fp)
    return result.to_dict(top_k=max(1, top_k))


def create_server() -> Any:
    """Build the MCP server (imports the ``mcp`` SDK lazily)."""
    try:
        from mcp.server.mcpserver import MCPServer
    except ImportError as exc:  # pragma: no cover - depends on the optional extra
        raise ImportError('the MCP server needs the "mcp" package: pip install "dom-healer[mcp]"') from exc

    server = MCPServer(name="dom-healer", instructions=SERVER_INSTRUCTIONS)
    server.tool(name="repair_selector")(repair_selector)
    server.tool(name="capture_fingerprint")(capture_fingerprint)
    server.tool(name="locate_element")(locate_element)
    return server


def main() -> None:  # pragma: no cover - blocks on stdio
    create_server().run("stdio")
