from __future__ import annotations

import pytest

from dom_healer.dom import parse_html
from dom_healer.semantics import element_family, element_role, is_hidden


def _el(markup: str, selector: str = "#t"):
    return parse_html(f"<html><body>{markup}</body></html>").select_one(selector)


@pytest.mark.parametrize(
    "markup,role",
    [
        ('<div id="t" role="button link">x</div>', "button"),
        ('<div id="t" role="gridcell">x</div>', "cell"),
        ('<div id="t" role="presentation">x</div>', ""),
        ('<input id="t" type="checkbox">', "checkbox"),
        ('<input id="t" type="SUBMIT">', "button"),
        ('<input id="t">', "textbox"),
        ('<input id="t" type="search">', "textbox"),
        ('<input id="t" type="hidden">', ""),
        ('<a id="t" href="/x">x</a>', "link"),
        ('<a id="t">x</a>', ""),
        ('<select id="t"><option>a</option></select>', "combobox"),
        ('<select id="t" multiple><option>a</option></select>', "combobox"),
        ('<div id="t" contenteditable="true">x</div>', "textbox"),
        ("<h2 id='t'>x</h2>", "heading"),
        ("<table><tr><th id='t'>x</th></tr></table>", "header"),
        ("<section id='t'>x</section>", "region"),
        ("<span id='t'>x</span>", ""),
    ],
)
def test_element_role(markup, role):
    assert element_role(_el(markup)) == role


@pytest.mark.parametrize(
    "tag,role,itype,family",
    [
        ("a", "link", "", "clickable"),
        ("div", "checkbox", "", "choice"),
        ("input", "textbox", "text", "text_input"),
        ("select", "combobox", "", "select"),
        ("td", "cell", "", "cell"),
        ("h2", "heading", "", "heading"),
        ("legend", "", "", "heading"),
        ("img", "img", "", "media"),
        ("svg", "", "", "media"),
        ("li", "listitem", "", "list_item"),
        ("dd", "", "", "list_item"),
        ("span", "", "", "text"),
        ("input", "", "hidden", "hidden"),
        ("input", "", "date", "text_input"),
        ("div", "", "", "container"),
    ],
)
def test_element_family(tag, role, itype, family):
    assert element_family(tag, role, itype) == family


@pytest.mark.parametrize(
    "markup,hidden",
    [
        ('<button id="t">x</button>', False),
        ('<button id="t" hidden>x</button>', True),
        ('<div aria-hidden="true"><button id="t">x</button></div>', True),
        ('<div style="color:red; display: none"><button id="t">x</button></div>', True),
        ('<div style="visibility:hidden"><button id="t">x</button></div>', True),
        ('<button id="t" class="btn d-none">x</button>', True),
        ('<button id="t" class="hidden md:flex">x</button>', False),
        ('<input id="t" type="hidden">', True),
        ('<dialog><button id="t">x</button></dialog>', True),
        ('<dialog open><button id="t">x</button></dialog>', False),
        ('<template><button id="t">x</button></template>', True),
    ],
)
def test_is_hidden(markup, hidden):
    el = _el(markup)
    assert el is not None
    assert is_hidden(el) is hidden
