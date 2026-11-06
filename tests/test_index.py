from __future__ import annotations

from dom_healer.dom import parse_html
from dom_healer.fingerprint import ElementFingerprint
from dom_healer.healer import capture_fingerprint, get_index
from dom_healer.index import PageIndex


def test_order_lookup_and_text_windows(old_doc):
    index = PageIndex(old_doc)
    assert index.size == len(old_doc)
    first = old_doc.root
    assert index.ordinal(first) == 0 and index.position(first) == 0.0
    email = old_doc.select_one("#nl-email")
    assert 0 < index.position(email) < 1
    assert index.by_id("nl-email") is email
    assert index.by_id("nope") is None
    assert index.label_text_for("nl-email") == "email"
    assert index.label_text_for("nope") == ""
    assert index.text_before(email) == "$140 add to cart email" or "email" in index.text_before(email)
    assert "weekly digest" in index.text_after(email)
    # elements with no preceding text / not in the index
    assert index.text_before(old_doc.root) == ""
    assert index.text_after(parse_html("<p>x</p>").select_one("p")) == ""
    # big subtrees are skipped for the "after" window
    assert index.text_after(old_doc.select_one("main"), max_subtree=3) == ""
    assert index.text_after(old_doc.select_one("form")) == "order status"


def test_heading_scope(old_doc, new_doc):
    old_index, new_index = get_index(old_doc), get_index(new_doc)
    assert old_index.heading_before(old_doc.select_one("button[data-testid=add-SK-200]")) == "summit kicks"
    # form is not inside any product card -> falls back to the page heading
    assert old_index.heading_before(old_doc.select_one("#nl-email")) == "trail shoes"
    assert new_index.heading_before(new_doc.select_one("#\\:r3\\:")) == "trail shoes"
    assert old_index.heading_before(old_doc.select_one("nav a")) == ""


def test_fingerprint_cache(old_doc):
    index = get_index(old_doc)
    el = old_doc.select_one("h1")
    assert index.fingerprint(el) is index.fingerprint(el)


def test_candidate_retrieval(old_doc, new_doc):
    fp = capture_fingerprint(old_doc, "button[data-testid=add-SK-200]")
    index = get_index(new_doc)
    pool = index.candidate_pool(fp)
    buttons = [el for el in pool if el.tag == "button"]
    assert len(buttons) == 5  # 3 visible + hidden decoy + subscribe
    cands = index.candidates(fp, k=4)
    assert len(cands) == 4
    assert cands[0][1] == 1.0 and all(0 <= s <= 1.0 for _, s in cands)
    # synonym expansion: "cart" also searches "bag"
    assert "bag" in index._query_words(fp)


def test_retrieval_with_attributes_and_extra(old_doc, new_doc):
    fp = capture_fingerprint(old_doc, "#cart-link")
    index = get_index(new_doc)
    extra = [new_doc.select_one("footer p")]
    pool = index.candidate_pool(fp, extra=extra)
    assert extra[0] in pool
    assert any(el.get("href") == "/cart?ref=nav" for el in pool)


def test_no_candidates():
    doc = parse_html("<html><body><p>only text</p></body></html>")
    fp = ElementFingerprint(tag="video", family="media", accessible_name="intro clip")
    assert get_index(doc).candidates(fp) == []
