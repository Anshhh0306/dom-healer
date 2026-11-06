from __future__ import annotations

import pytest

from dom_healer.dom import parse_html, select
from dom_healer.fingerprint import ElementFingerprint
from dom_healer.healer import (
    STATUS_HEALED,
    STATUS_LOW_CONFIDENCE,
    STATUS_NOT_FOUND,
    STATUS_VALID,
    ElementNotFoundError,
    Healer,
    HealResult,
    capture_fingerprint,
    heal,
    locate,
)
from dom_healer.rankers import HeuristicRanker

# (selector on v1, a v2 selector that identifies the same logical element)
CASES = [
    ("button[data-testid='add-SK-200']", "product-card button"),
    ("div.product-card:nth-child(1) .add-to-cart", "div[data-sku='TR-100'] button"),
    ("#cart-link", "nav a[href^='/cart']"),
    ("#nl-email", "input[name=email]"),
    ("#weekly", "input[name=weekly]"),
    ("form#newsletter button[type=submit]", "form button[type=submit]"),
    ("table.orders tbody tr:nth-child(1) td.status", "//div[@role='row'][span[1]='#1001']/span[3]"),
    ("//tr[td[1]='#1002']//a[@class='view']", "a[href='/o/1002']"),
    ("span.price", "div[data-sku='TR-100'] > span"),
]


@pytest.mark.parametrize("ranker", ["heuristic", "linear"])
@pytest.mark.parametrize("old_selector,new_selector", CASES)
def test_heals_mutated_page(old_html, new_html, old_selector, new_selector, ranker):
    reference = parse_html(new_html)
    expected = select(reference, new_selector)
    assert len(expected) == 1
    result = heal(old_html, new_html, old_selector, ranker=ranker)
    if ranker == "heuristic":  # the default ranker is also confident on all of these
        assert result.ok, result.to_dict()
        assert result.status == STATUS_HEALED
    # the healed selectors resolve to exactly the predicted element
    new_doc = result.candidates[0].document
    assert select(new_doc, result.selector) == [result.element]
    assert select(new_doc, result.xpath) == [result.element]
    # and that element is the same logical element as the hand-written v2 selector
    assert new_doc.absolute_xpath(result.element) == reference.absolute_xpath(expected[0])


def test_valid_when_selector_still_works(old_html, new_html):
    result = heal(old_html, new_html, "//h3[text()='Mesa Hiker']", ranker="heuristic")
    assert result.status == STATUS_VALID and result.strategy == "original"
    assert result.selector == "//h3[text()='Mesa Hiker']"
    assert result.original_matches == 1


def test_valid_with_ambiguous_original_gets_new_selector(old_html):
    page = old_html.replace('<h1>Trail shoes</h1>', '<h1>Trail shoes</h1><h1>Sale</h1>')
    result = heal(old_html, page, "h1", ranker="heuristic")
    assert result.status == STATUS_VALID and result.original_matches == 2
    assert result.strategy != "original"
    assert select(result.best.document, result.selector) == [result.element]


def test_low_confidence_and_not_found(old_html, new_html):
    healer = Healer(new_html, ranker="heuristic", min_confidence=0.99)
    fp = capture_fingerprint(old_html, "#nl-email")
    result = healer.locate(fp, selector="#nl-email")
    assert result.status == STATUS_LOW_CONFIDENCE and not result.ok
    empty = Healer("<html><body><p>nothing here</p></body></html>", ranker="heuristic")
    missing = empty.locate(ElementFingerprint(tag="video", family="media"))
    assert missing.status == STATUS_NOT_FOUND
    assert missing.element is None and missing.best is None and missing.confidence == 0.0
    assert missing.to_dict()["candidates"] == []
    assert set(missing.timings_ms) >= {"retrieval", "features", "ranking"}


def test_repair_and_locate_inputs(old_html, new_html):
    healer = Healer(parse_html(new_html), ranker=HeuristicRanker())
    by_html = healer.repair("#weekly", old_html)
    fp = capture_fingerprint(old_html, "#weekly")
    by_fp = healer.repair("#weekly", fp)
    assert by_html.element is by_fp.element
    assert locate(fp.to_json(), new_html, ranker="heuristic").ok
    assert locate(fp.to_dict(), new_html, ranker="heuristic").ok
    assert locate(fp, new_html, ranker="heuristic").ok
    # an invalid stored selector is ignored rather than raised
    fp2 = ElementFingerprint.from_dict({**fp.to_dict(), "selector": "div["})
    assert healer.locate(fp2).ok


def test_result_serialisation(old_html, new_html):
    result = heal(old_html, new_html, "#nl-email", ranker="heuristic")
    data = result.to_dict(top_k=2, with_fingerprint=True)
    assert data["status"] == STATUS_HEALED and data["ok"] is True
    assert len(data["candidates"]) == 2
    first = data["candidates"][0]
    assert {"css", "xpath", "css_strategy", "absolute_xpath", "summary", "score"} <= set(first)
    assert data["fingerprint"]["tag"] == "input"
    assert data["timings_ms"]["total"] >= 0
    cand = result.best
    assert cand.css == cand.selectors.css and cand.xpath == cand.selectors.xpath
    assert "absolute_xpath" in cand.to_dict(with_selectors=False)
    assert isinstance(result, HealResult)


def test_errors(old_html, new_html):
    with pytest.raises(ElementNotFoundError):
        heal(old_html, new_html, "#missing")
    with pytest.raises(ValueError):
        Healer(new_html, max_candidates=0)
    no_synth = Healer(new_html, ranker="heuristic").locate(capture_fingerprint(old_html, "#weekly"), synthesize=False)
    assert no_synth.selector is None and no_synth.element is not None


def test_bs4_input(old_html, new_html):
    bs4 = pytest.importorskip("bs4")
    result = heal(bs4.BeautifulSoup(old_html, "html.parser"), bs4.BeautifulSoup(new_html, "html.parser"), "#weekly",
                  ranker="heuristic")
    assert result.ok and result.element.get("name") == "weekly"
