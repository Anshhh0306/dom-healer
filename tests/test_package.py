from __future__ import annotations

import dom_healer


def test_public_api_exports(old_html, new_html):
    for name in dom_healer.__all__:
        assert hasattr(dom_healer, name), name
    result = dom_healer.heal(old_html, new_html, "#weekly", ranker="heuristic")
    assert result.ok and result.selector == '[name="weekly"]'
