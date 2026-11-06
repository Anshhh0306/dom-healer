from __future__ import annotations

import asyncio
import json

import pytest

from dom_healer import mcp_server


def test_tool_functions(old_html, new_html):
    repaired = mcp_server.repair_selector(old_html, new_html, "#nl-email", top_k=2, ranker="heuristic")
    assert repaired["ok"] and repaired["selector"] == '[name="email"]'
    assert len(repaired["candidates"]) == 2
    fp = mcp_server.capture_fingerprint(old_html, "#weekly")
    assert fp["tag"] == "input"
    located = mcp_server.locate_element(fp, new_html, top_k=0)
    assert located["ok"] and len(located["candidates"]) == 1


def test_mcp_server_registration(old_html, new_html):
    pytest.importorskip("mcp")
    server = mcp_server.create_server()

    async def scenario():
        tools = {t.name: t for t in await server.list_tools()}
        assert set(tools) == {"repair_selector", "capture_fingerprint", "locate_element"}
        assert "old_html" in tools["repair_selector"].input_schema["properties"]
        result = await server.call_tool(
            "repair_selector", {"old_html": old_html, "new_html": new_html, "selector": "#weekly"}
        )
        payload = json.loads(result.content[0].text)
        assert payload["selector"] == '[name="weekly"]'

    asyncio.run(scenario())
