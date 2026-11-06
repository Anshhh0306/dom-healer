from __future__ import annotations

import pytest

from dom_healer.text import (
    canonical_words,
    class_tokens,
    identifier_tokens,
    is_obfuscated_class,
    jaccard,
    lcs_ratio,
    looks_generated,
    looks_random,
    normalize_text,
    text_similarity,
    trigrams,
    words,
)


def test_normalize_text():
    assert normalize_text(None) == ""
    assert normalize_text("") == ""
    assert normalize_text("  Add\n to   CART ") == "add to cart"
    assert normalize_text("x" * 300, limit=10) == "x" * 10


def test_words_and_canonical_words():
    assert words("e-mail address") == ("email", "address")
    assert canonical_words("Add to bag") == frozenset({"add", "cart"})
    assert canonical_words("Log in") == canonical_words("sign in") == frozenset({"sign"})
    assert canonical_words("the") == frozenset()
    assert canonical_words("e mail") == frozenset({"mail"})  # stray "e" dropped


def test_similarity_primitives():
    assert "  a" in trigrams("ab")
    assert jaccard(frozenset(), frozenset()) == 1.0
    assert jaccard(frozenset({"a"}), frozenset()) == 0.0
    assert jaccard(frozenset({"a", "b"}), frozenset({"b", "c"})) == pytest.approx(1 / 3)
    assert text_similarity("", "") == 0.0
    assert text_similarity("abc", "abc") == 1.0
    assert text_similarity("abc", "") == 0.0
    assert text_similarity("add to cart", "add to bag") == 1.0  # canonical synonyms
    assert 0.0 < text_similarity("trail runner 2", "trail runner 3") < 1.0
    assert text_similarity("!!!", "???") == 0.0  # no words -> trigram dice only


def test_lcs_ratio():
    assert lcs_ratio(("a", "b"), ("a", "b")) == 1.0
    assert lcs_ratio((), ("a",)) == 0.0
    assert lcs_ratio(("html", "body", "div", "a"), ("html", "body", "div", "div", "a")) == pytest.approx(8 / 9)
    assert lcs_ratio(("x", "a", "b", "y"), ("x", "b", "a", "y")) == pytest.approx(6 / 8)
    assert lcs_ratio(("a",), ("b",)) == 0.0


@pytest.mark.parametrize(
    "name,expected",
    [
        ("css-1x9f2ab", True),
        ("sc-bdfBwQ", True),
        ("jsx-123", True),
        ("svelte-xyz12", True),
        ("_a3f9c", True),
        ("jss42", True),
        ("kQwYzP", True),
        ("x7Gq2a1", True),
        ("btn-primary", False),
        ("NavBar", False),
        ("product-card", False),
        ("mt-4", False),
        ("h1", False),
    ],
)
def test_is_obfuscated_class(name, expected):
    assert is_obfuscated_class(name) is expected


def test_identifier_and_class_tokens():
    assert identifier_tokens("ProductCard_addToCart__x7Gq2") == ("product", "card", "add", "to", "cart")
    assert identifier_tokens("item-12") == ("item",)
    assert identifier_tokens("a1b2c3") == ()
    toks = class_tokens(("btn", "btn-primary", "css-1x9f2ab", "md:flex", "hover:bg-blue-500", "px-4", "add-to-cart"))
    assert toks == frozenset({"btn", "primary", "add", "to", "cart"})


@pytest.mark.parametrize(
    "value,expected",
    [
        (":r1f:", True),
        ("ember123", True),
        ("input-1234", True),
        ("3f2b8c1e-1d2c-4e5f-9a8b-7c6d5e4f3a2b", True),
        ("field-7f3a", True),
        ("input-12", True),
        ("1st", True),
        ("has space", True),
        ("x" * 70, True),
        ("", True),
        ("checkout-button", False),
        ("email", False),
        ("cart-link", False),
    ],
)
def test_looks_generated(value, expected):
    assert looks_generated(value) is expected


def test_looks_random():
    assert looks_random("MH-300") is False
    assert looks_random("add-to-cart") is False
    assert looks_random(":r4:") is True
    assert looks_random("deadbeefcafebabe") is True
    assert looks_random("") is True
    assert looks_random("y" * 80) is True
