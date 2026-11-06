from __future__ import annotations

import json

import pytest

from dom_healer.dom import parse_html
from dom_healer.fingerprint import ElementFingerprint, direct_text, stable_attrs, text_without
from dom_healer.healer import capture_element, capture_fingerprint, get_index

FORM = """<!doctype html><html><body>
<main>
<h2>Account</h2>
<form id="signup" name="signup" action="/account/create?x=1" aria-label="Create account" class="form-card">
  <label for="em">E-mail</label><input id="em" name="email" type="email" value="typed@x.io" placeholder="you@x.io">
  <label>Country <select name="country"><option>France</option><option>Spain</option></select></label>
  <span id="pw-label">Password</span><input type="password" aria-labelledby="pw-label missing">
  <input type="text" aria-label="Promo code" name="promo">
  <input type="text" placeholder="Nickname">
  <input type="submit" value="Create account">
  <input type="image" alt="Go" src="/go.png?v=2">
  <input type="reset">
  <textarea title="Bio"></textarea>
  <button type="button"><img src="/x.svg" alt="Close dialog"></button>
  <button type="button" title="Help"></button>
  <a href="https://example.com/terms#top" data-track="terms">Terms</a>
  <img src="/logo.png" title="Logo">
  <p>Text <b>bold</b> tail</p>
</form>
</main>
<div role="grid">
  <div role="row"><div role="columnheader">Name</div><div role="columnheader">Qty</div></div>
  <div role="row"><div role="rowheader">Widget</div><div role="gridcell"><span id="qty">4</span></div></div>
</div>
<table><tr><td>a</td><td>b</td></tr><tr><td>c</td><td id="nohead">d</td></tr></table>
</body></html>"""


@pytest.fixture
def doc():
    return parse_html(FORM)


def fp(doc, selector):
    return capture_fingerprint(doc, selector)


def test_label_and_accessible_name_variants(doc):
    email = fp(doc, "#em")
    assert email.label == "e-mail" and email.accessible_name == "e-mail"
    assert "value" not in email.attrs  # user data is not part of the identity
    assert email.form and "signup" in email.form and "create" in email.form
    assert email.landmark == "form"
    assert email.semantic_path == ["main", "form"]
    assert email.heading == "account"

    country = fp(doc, "select[name=country]")
    assert country.label == "country"  # option text excluded
    assert fp(doc, "input[type=password]").accessible_name == "password"
    assert fp(doc, "input[name=promo]").accessible_name == "promo code"
    assert fp(doc, "input[placeholder=Nickname]").accessible_name == "nickname"
    assert fp(doc, "input[type=submit]").accessible_name == "create account"
    assert fp(doc, "input[type=reset]").accessible_name == "reset"
    image = fp(doc, "input[type=image]")
    assert image.accessible_name == "go" and image.attrs["src"] == "/go.png"
    assert fp(doc, "textarea").accessible_name == "bio"
    assert fp(doc, "//button[img]").accessible_name == "close dialog"
    assert fp(doc, "button[title=Help]").accessible_name == "help"
    link = fp(doc, "a")
    assert link.attrs["href"] == "/terms" and link.attrs["data-track"] == "terms"
    assert fp(doc, "img[title=Logo]").accessible_name == "logo"


def test_text_helpers(doc):
    p = doc.select_one("p")
    assert " ".join(direct_text(p).split()) == "Text tail"
    assert "bold" not in text_without(p, frozenset({"b"}))
    assert direct_text(doc.select_one("//style") or parse_html("<style>x</style>").select_one("style")) == ""


def test_table_and_grid_context(doc):
    qty = fp(doc, "#qty")
    assert qty.row == "widget"
    assert qty.column_header == "qty"
    assert qty.semantic_path[-2:] == ["row", "cell"]
    cell = fp(doc, "#nohead")
    assert cell.row == "c" and cell.column_header == ""


def test_sibling_context_and_wrappers():
    doc = parse_html("<html><body><ul><li><a>One</a></li><li><div><a id='t'>Two</a></div></li><li><a>Three</a></li>"
                     "</ul></body></html>")
    two = fp(doc, "#t")
    assert two.sibling_count == 1 and two.prev_sibling == ""  # wrapper collapsed, li is structural
    li = fp(doc, "li:nth-child(2)")
    assert li.sibling_index == 1 and li.sibling_count == 3
    assert li.prev_sibling == "li|one" and li.next_sibling == "li|three"
    assert li.children == ["div"]


def test_hidden_and_shadow_flags():
    doc = parse_html("<html><body><x-card><template shadowrootmode='open'><button id='b' hidden>x</button>"
                     "</template></x-card></body></html>")
    f = fp(doc, "#b")
    assert f.hidden is True and f.shadow_depth == 1


def test_serialisation_roundtrip(doc):
    f = fp(doc, "#em")
    again = ElementFingerprint.from_json(f.to_json())
    assert again == f
    data = json.loads(f.to_json(indent=2))
    data["unknown_future_field"] = 1
    assert ElementFingerprint.from_dict(data).tag == "input"
    with pytest.raises(ValueError):
        ElementFingerprint.from_dict({"role": "button"})
    with pytest.raises(ValueError):
        ElementFingerprint.from_dict([])  # type: ignore[arg-type]


def test_summary_and_test_attrs():
    f = ElementFingerprint(tag="button", role="button", accessible_name="add to cart", heading="trail runner",
                           row="#1001 shipped", attrs={"data-testid": "add", "name": "x"})
    s = f.summary()
    assert "add to cart" in s and "trail runner" in s and "#1001" in s
    assert f.test_attrs() == {"data-testid": "add"}
    assert ElementFingerprint(tag="div").summary() == "div"
    assert "role=link" in ElementFingerprint(tag="a", role="link").summary()


def test_stable_attrs_filters(doc):
    attrs = stable_attrs(doc.select_one("form"))
    assert attrs["action"] == "/account/create"
    assert "class" not in attrs and "id" not in attrs
    btn = parse_html("<button type='SUBMIT' value='go' onclick='x()' style='a'>x</button>").select_one("button")
    assert stable_attrs(btn) == {"type": "submit", "value": "go"}


def test_capture_element_and_selector_override(doc):
    el = doc.select_one("#em")
    f1 = capture_element(doc, el)
    assert f1.selector == ""
    f2 = get_index(doc).fingerprint(el, "#em")
    assert f2.selector == "#em" and f2.tag == f1.tag
