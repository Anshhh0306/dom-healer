from __future__ import annotations

import pytest
from lxml import etree
from lxml import html as lxml_html

from dom_healer.dom import (
    Document,
    ParseError,
    SelectorError,
    classify_selector,
    compile_selector,
    ensure_document,
    parse_html,
    select,
)

SHADOW = """<!doctype html><html><body>
<div id="a">
  <product-card data-x="1"><template shadowrootmode="open">intro<div class="inner"><h3>Trail</h3>
    <button class="buy">Add</button></div>outro</template><span slot="s">light</span></product-card>
  <x-outer><template shadowrootmode="closed"><x-inner><template shadowroot="open"><b id="deep">deep</b></template>
  </x-inner></template></x-outer>
  <template id="plain"><i>inert</i></template>
</div></body></html>"""


def test_parse_str_bytes_and_errors():
    doc = parse_html("<p>hi</p>")
    assert doc.root.tag == "html"
    assert doc.select_one("p").text == "hi"
    assert parse_html(b"<p>bytes</p>").select_one("p").text == "bytes"
    assert parse_html('<?xml version="1.0" encoding="utf-8"?><html><body><p>x</p></body></html>').select_one("p") is not None
    for bad in ("", "   ", b"", b"  "):
        with pytest.raises(ParseError):
            parse_html(bad)
    with pytest.raises(TypeError):
        Document.from_html(123)  # type: ignore[arg-type]


def test_shadow_roots_are_flattened():
    doc = parse_html(SHADOW)
    button = doc.select_one("product-card > div.inner button.buy")
    assert button is not None
    assert doc.shadow_depth(button) == 1
    assert doc.shadow_host_of(button).tag == "product-card"
    inner = doc.select_one("product-card > div.inner")
    assert doc.is_shadow_root_child(inner)
    assert not doc.is_shadow_root_child(button)
    deep = doc.select_one("#deep")
    assert doc.shadow_depth(deep) == 2
    assert doc.shadow_host_of(deep).tag == "x-inner"
    light = doc.select_one("span[slot]")
    assert doc.shadow_depth(light) == 0 and doc.shadow_host_of(light) is None
    hosts = doc.shadow_hosts
    assert sorted(h.tag for h in hosts) == ["product-card", "x-inner", "x-outer"]
    assert sorted(hosts.values()) == ["closed", "open", "open"]
    # text around the template content is preserved, non-shadow templates are kept
    card = doc.select_one("product-card")
    assert "intro" in card.text_content() and "outro" in card.text_content()
    assert doc.select_one("template#plain") is not None
    assert not doc.select("product-card > template")
    assert len(doc) > 5
    assert "shadow_hosts=3" in repr(doc)


def test_drop_tag_text_handling_for_empty_template():
    doc = parse_html("<div><span>a</span><x-h><template shadowrootmode=open>t</template>tail</x-h></div>")
    host = doc.select_one("x-h")
    assert host.text_content() == "ttail"
    doc2 = parse_html("<div><x-h>lead<template shadowrootmode=open></template>after</x-h></div>")
    assert doc2.select_one("x-h").text_content() == "leadafter"
    doc3 = parse_html("<div><x-h><i>x</i><template shadowrootmode=open>in</template>after</x-h></div>")
    assert doc3.select_one("x-h").text_content() == "xinafter"


def test_classify_selector():
    assert classify_selector("div > a") == ("css", "div > a")
    assert classify_selector("  //a ") == ("xpath", "//a")
    assert classify_selector("(//a)[2]") == ("xpath", "(//a)[2]")
    assert classify_selector("./a") == ("xpath", "./a")
    assert classify_selector("xpath=//a") == ("xpath", "//a")
    assert classify_selector("XPATH://a") == ("xpath", "//a")
    assert classify_selector("css=div") == ("css", "div")
    assert classify_selector("css:div") == ("css", "div")
    with pytest.raises(SelectorError):
        classify_selector("  ")
    with pytest.raises(SelectorError):
        classify_selector(None)  # type: ignore[arg-type]


def test_select_css_and_xpath(old_doc):
    assert [e.text for e in old_doc.select("h3.product-title")] == ["Trail Runner 2", "Summit Kicks", "Mesa Hiker"]
    assert old_doc.select_one("//h3[normalize-space()='Mesa Hiker']").tag == "h3"
    assert old_doc.select_one("css=#cart-link").get("href") == "/cart"
    assert old_doc.select_one("xpath=(//button)[last()]").text == "Subscribe"
    assert old_doc.select_one("#does-not-exist") is None
    # selecting text nodes / attributes yields no elements
    assert old_doc.select("//h3/text()") == []
    assert select(old_doc.root, "//a/@href") == []
    assert select(old_doc, "h1")[0].text == "Trail shoes"


@pytest.mark.parametrize("bad", ["div[", "//div[", "a::b", "count(//div)"])
def test_invalid_selectors(old_doc, bad):
    with pytest.raises(SelectorError):
        old_doc.select(bad)


def test_scalar_and_eval_errors(old_doc):
    with pytest.raises(SelectorError):
        old_doc.select("xpath=count(//div)")
    with pytest.raises(SelectorError):
        old_doc.select("//div[$undefined]")
    with pytest.raises(SelectorError):
        compile_selector("css", "")
    with pytest.raises(SelectorError):
        compile_selector("regex", "x")


def test_ensure_document_variants(old_html):
    doc = parse_html(old_html)
    assert ensure_document(doc) is doc
    assert ensure_document(old_html).select_one("h1") is not None
    assert ensure_document(old_html.encode()).select_one("h1") is not None
    root = lxml_html.document_fromstring(SHADOW)
    from_el = ensure_document(root.find(".//div"))
    assert from_el.root is root
    assert from_el.select_one("product-card > div.inner") is not None  # flattened in place
    tree = etree.ElementTree(lxml_html.document_fromstring("<p>t</p>"))
    assert ensure_document(tree).select_one("p").text == "t"
    bs4 = pytest.importorskip("bs4")
    soup = bs4.BeautifulSoup(old_html, "html.parser")
    assert ensure_document(soup).select_one("#cart-link") is not None
    with pytest.raises(TypeError):
        ensure_document(42)


def test_absolute_xpath_roundtrip(old_doc):
    el = old_doc.select_one("#nl-email")
    path = old_doc.absolute_xpath(el)
    assert path.startswith("/html/body/")
    assert old_doc.select(path) == [el]
