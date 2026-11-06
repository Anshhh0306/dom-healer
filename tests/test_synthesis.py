from __future__ import annotations

import pytest

from dom_healer.dom import parse_html, select
from dom_healer.synthesis import (
    SelectorSuggestion,
    css_ident,
    css_string,
    suggest_css,
    suggest_selectors,
    suggest_xpath,
    xpath_literal,
)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("cart", "cart"),
        ("1st", "\\31 st"),
        ("-1x", "-\\31 x"),
        ("-", "\\-"),
        (":r1:", "\\:r1\\:"),
        ("a b", "a\\ b"),
        ("\x01", "\\1 "),
        ("\x00", "�"),
        ("über", "über"),
    ],
)
def test_css_ident(value, expected):
    assert css_ident(value) == expected


def test_css_ident_roundtrip_through_cssselect():
    doc = parse_html('<html><body><p id="1st">a</p><p id=":r1:">b</p><p id="a b">c</p></body></html>')
    for value in ("1st", ":r1:", "a b"):
        assert [e.get("id") for e in select(doc, "#" + css_ident(value))] == [value]


def test_string_literals():
    assert css_string('say "hi"\\\n') == '"say \\"hi\\"\\\\\\a "'
    assert xpath_literal("plain") == "'plain'"
    assert xpath_literal("it's") == '"it\'s"'
    lit = xpath_literal("it's \"quoted\"")
    assert lit.startswith("concat(")
    doc = parse_html("<html><body><b>it's \"quoted\"</b></body></html>")
    assert len(select(doc, f"//b[normalize-space()={lit}]")) == 1


PAGE = """<html><body>
<nav><a href="/a" id="home-link">Home</a><a href="/b" id=":r9:">Shop</a></nav>
<main>
  <form name="login">
    <input name="user" data-testid="username"><input name="pass" type="password">
    <button class="btn-primary css-1x2y3z">Sign in</button><button class="btn-primary css-9q8w7e">Sign in</button>
  </form>
  <section data-region="promo"><div class="x"><span>Deal</span></div><div class="x"><span>Deal</span></div></section>
  <ul><li><em>dup</em></li><li><em>dup</em></li></ul>
  <article><p>Text</p></article><article><p>Text</p></article>
</main></body></html>"""


@pytest.fixture
def doc():
    return parse_html(PAGE)


def _check(doc, el):
    s = suggest_selectors(doc, el)
    assert isinstance(s, SelectorSuggestion)
    assert select(doc, s.css) == [el], s.css
    assert select(doc, s.xpath) == [el], s.xpath
    return s


def test_strategies(doc):
    s = _check(doc, doc.select_one("#home-link"))
    assert (s.css, s.css_strategy, s.xpath_strategy) == ("#home-link", "id", "id")
    s = _check(doc, doc.select_one("[data-testid=username]"))
    assert s.css_strategy == "test-attribute" and s.css == '[data-testid="username"]'
    s = _check(doc, doc.select_one("input[name=pass]"))
    assert s.css == '[name="pass"]' and s.xpath == "//input[@name='pass']"
    s = _check(doc, doc.select_one("nav a:nth-of-type(2)"))  # generated id is skipped
    assert ":r9:" not in s.css and s.css_strategy.startswith("attribute")
    s = _check(doc, doc.select_one("button.css-9q8w7e"))  # duplicate text + utility/hashed classes
    assert "css-9q8w7e" not in s.css
    assert s.to_dict()["css"] == s.css


def test_anchored_and_positional(doc):
    span = doc.select_one("section div:nth-of-type(2) span")
    s = _check(doc, span)
    assert s.css.startswith('[data-region="promo"]') and "position" in s.css_strategy
    em = doc.select_one("li:nth-of-type(2) em")
    s = _check(doc, em)
    assert s.css_strategy in ("anchored:position", "position")
    p = doc.select_one("article:nth-of-type(2) p")
    s = _check(doc, p)
    assert "nth-of-type" in s.css


def test_absolute_fallbacks():
    doc = parse_html("<html><body><div><i>x</i></div><div><i>x</i></div></body></html>")
    el = doc.select("i")[1]
    css, strategy = suggest_css(doc, el)
    xpath, xstrategy = suggest_xpath(doc, el)
    assert strategy == "position" and css.startswith("html > body")
    assert xstrategy == "position" and xpath.startswith("/html/body")
    assert select(doc, css) == [el] and select(doc, xpath) == [el]
