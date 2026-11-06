#!/usr/bin/env python
"""Deterministic generator for the ``ecommerce`` benchmark fixtures.

Writes ``ecommerce-01`` ... ``ecommerce-10`` (``v1.html``, ``v2.html`` and
``targets.json``) next to this script.  Every suite is a different (fictional)
store with its own layout and component structure; ``v2`` is a plausible
redesign of the same page (new CSS strategy, wrappers, reordering, shadow DOM,
decoys, copy and attribute churn).  Ground-truth elements carry
``data-dh-target`` markers in both versions (see ../README.md).

    python benchmarks/fixtures/ecommerce/_build.py          # (re)write all suites
    python benchmarks/fixtures/ecommerce/_build.py 03 07    # only some suites

Output is deterministic: obfuscated class names are derived from SHA-256.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from html import escape as _escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
MARK = "data-dh-target"
CURRENT = ' aria-current="page"'  # attribute snippet for the active nav item


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def e(text: object) -> str:
    """HTML-escape text and attribute values."""
    return _escape(str(text), quote=True)


def gt(tid: str | None) -> str:
    """Ground-truth marker attribute (empty string for non-targets)."""
    return f' {MARK}="{tid}"' if tid else ""


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower().replace("&", "and").replace("é", "e").replace("è", "e")).strip("-")


def money(value: float) -> str:
    return f"${value:,.2f}"


_LOWER = "abcdefghijklmnopqrstuvwxyz"
_ALPHA = _LOWER + _LOWER.upper()
_B62 = _ALPHA + "0123456789"
_B36 = "0123456789" + _LOWER


def _h(seed: str, n: int, alphabet: str = _B62) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return "".join(alphabet[b % len(alphabet)] for b in digest[:n])


def cm(component: str, local: str) -> str:
    """CSS-modules class name (Next.js style): ``Component_local__hash``."""
    return f"{component}_{local}__{_h(component + '.' + local, 5)}"


def emo(label: str) -> str:
    """Emotion class name: ``css-<hash>``."""
    return "css-" + _h("emotion." + label, 7, _B36)


def sc(component: str, variant: str = "") -> str:
    """styled-components class pair: static component id + generated class."""
    return f"sc-{_h('sc.' + component, 6, _ALPHA)} {_h('sc.' + component + '.' + variant, 6, _ALPHA)}"


def ax(*decls: str) -> str:
    """Atomic (StyleX-like) class names, one per CSS declaration."""
    return " ".join("x" + _h("x." + d, 7, _B36) for d in decls)


def ve(*names: str) -> str:
    """vanilla-extract production class names (``_1kq2x6z0`` style), one per style rule."""
    return " ".join("_" + _h("ve." + n, 6, _B36) + str(len(n) % 10) for n in names)


ICONS = {
    "search": "M11 4a7 7 0 1 0 4.2 12.6l4.1 4.1 1.4-1.4-4.1-4.1A7 7 0 0 0 11 4zm0 2a5 5 0 1 1 0 10 5 5 0 0 1 0-10z",
    "cart": "M3 4h2l2.4 10.2a2 2 0 0 0 2 1.6h7.7a2 2 0 0 0 2-1.5L21 8H6.2M9 20h.01M18 20h.01",
    "bag": "M6 7h12l1 13H5L6 7zm3 0V6a3 3 0 0 1 6 0v1",
    "heart": "M12 20s-7-4.4-9.3-8.6C1.2 8.3 3 5 6.4 5c2 0 3.3 1.1 4.1 2.3h3C14.3 6.1 15.6 5 17.6 5 21 5 22.8 8.3 21.3 11.4 19 15.6 12 20 12 20z",
    "user": "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm-8 8a8 8 0 0 1 16 0",
    "chevron-right": "M9 6l6 6-6 6",
    "chevron-left": "M15 6l-6 6 6 6",
    "chevron-down": "M6 9l6 6 6-6",
    "plus": "M12 5v14M5 12h14",
    "minus": "M5 12h14",
    "trash": "M4 7h16M9 7V4h6v3m-8 0 1 13h8l1-13",
    "close": "M6 6l12 12M18 6L6 18",
    "star": "M12 3l2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3l-5.6 2.9 1.1-6.2L3 9.6l6.2-.9z",
    "filter": "M4 6h16M7 12h10M10 18h4",
    "grid": "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z",
    "list": "M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01",
    "truck": "M3 6h11v9H3zM14 9h4l3 3v3h-7zM7 18a2 2 0 1 0 0-.01M17 18a2 2 0 1 0 0-.01",
    "lock": "M6 11h12v9H6zM8 11V8a4 4 0 0 1 8 0v3",
    "share": "M4 12v7h16v-7M12 3v12M8 7l4-4 4 4",
    "check": "M5 12l5 5 9-10",
    "info": "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zm0-11v6m0-9h.01",
    "play": "M8 5v14l11-7z",
    "pin": "M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11zm0-9a2 2 0 1 0 0-4 2 2 0 0 0 0 4z",
    "clock": "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zm0-15v5l3 3",
    "menu": "M4 6h16M4 12h16M4 18h16",
    "more": "M12 5h.01M12 12h.01M12 19h.01",
    "tag": "M3 12V4h8l10 10-8 8L3 12zm5-4h.01",
    "scale": "M7 4v16M17 4v16M3 8h8M13 16h8",
    "scissors": "M6 9a3 3 0 1 0 0-.01M6 21a3 3 0 1 0 0-.01M8.1 8.1 20 20M8.1 15.9 20 4",
    "bolt": "M13 2 4 14h7l-1 8 9-12h-7z",
    "globe": "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM2 12h20M12 2c3 3.5 3 16.5 0 20M12 2c-3 3.5-3 16.5 0 20",
    "mail": "M3 6h18v12H3zM3 7l9 6 9-6",
    "phone": "M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2",
    "return": "M9 14 4 9l5-5M4 9h11a5 5 0 0 1 0 10h-3",
    "shield": "M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z",
    "gift": "M3 9h18v4H3zM5 13h14v8H5zM12 9v12M12 9c-2-4-6-4-6-1.5S9 9 12 9zm0 0c2-4 6-4 6-1.5S15 9 12 9z",
    "leaf": "M5 19c0-9 6-14 15-14 0 9-5 15-14 15M5 19l7-7",
    "mountain": "M2 20 9 7l4 6 3-4 6 11H2z",
    "copy": "M9 9h11v11H9zM5 15H4V4h11v1",
    "edit": "M4 20h4L19 9l-4-4L4 16v4zM14 6l4 4",
    "sliders": "M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0M16 4v4M10 10v4M18 16v4",
    "box": "M3 7l9-4 9 4v10l-9 4-9-4V7zm0 0 9 4 9-4M12 11v10",
    "eye": "M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12zm10 3a3 3 0 1 0 0-6 3 3 0 0 0 0 6z",
}


def icon(name: str, cls: str = "", size: int = 20) -> str:
    """Decorative inline SVG icon (two elements: ``svg`` + ``path``)."""
    c = f' class="{cls}"' if cls else ""
    return (
        f'<svg{c} width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
        f'<path d="{ICONS[name]}"/></svg>'
    )


def page(*, title: str, body: str, css: str = "", head: str = "", lang: str = "en", html_attrs: str = "",
         body_attrs: str = "") -> str:
    style = f"<style>\n{css.strip()}\n</style>\n" if css.strip() else ""
    return (
        "<!doctype html>\n"
        f'<html lang="{lang}"{html_attrs}>\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{e(title)}</title>\n{head}{style}</head>\n<body{body_attrs}>\n{body.strip()}\n</body>\n</html>\n"
    )


def target(tid: str, description: str, css: str, xpath: str, mutations: list[str]) -> dict:
    return {"id": tid, "description": description, "css": css, "xpath": xpath, "mutations": mutations}


# ---------------------------------------------------------------------------
# ecommerce-01 — Ridgeline Outfitters: backpacking-tent listing grid + filters
# ---------------------------------------------------------------------------

# sku, brand, name, price, was, rating, reviews, trail weight, seasons, badge, colours
S01_PRODUCTS = [
    ("AG-FL1", "Alpenglow", "Alpenglow Featherlite 1P Tent", "299.95", None, 4.5, 212, "2 lb 3 oz", "3-season", "New", ("Ember", "Glacier")),
    ("TW-BC4", "Talus Works", "Talus Works Basecamp 4P Tent", "429.00", None, 4.4, 96, "7 lb 12 oz", "3-season", None, ("Slate",)),
    ("RL-ASC2", "Ridgeline", "Ridgeline Ascent 2P Tent", "349.00", None, 4.7, 538, "3 lb 6 oz", "3-season", "Best seller", ("Spruce", "Sandstone")),
    ("NF-RD3", "Northfork", "Northfork Ridge Dome 3P Tent", "259.00", None, 4.3, 77, "5 lb 9 oz", "3-season", None, ("Rust",)),
    ("CC-UT2", "Cairn & Co.", "Cairn & Co. Ultra Trekker 2P Tent", "319.96", "399.95", 4.6, 301, "2 lb 14 oz", "3-season", "20% off", ("Moss", "Fog")),
    ("ST-AR2", "Summit Thread", "Summit Thread Arête 2P Four-Season Tent", "689.00", None, 4.8, 43, "5 lb 2 oz", "4-season", None, ("Signal Orange",)),
    ("AG-FL2", "Alpenglow", "Alpenglow Featherlite 2P Tent", "379.95", None, 4.6, 188, "2 lb 15 oz", "3-season", None, ("Ember", "Glacier")),
    ("RL-TH3", "Ridgeline", "Ridgeline Trailhead 3P Tent", "223.20", "279.00", 4.5, 402, "4 lb 11 oz", "3-season", "20% off", ("Spruce",)),
    ("TW-SH1", "Talus Works", "Talus Works Shelter 1P Trekking Pole Tent", "239.00", None, 4.2, 58, "1 lb 9 oz", "3-season", None, ("Olive",)),
    ("CC-HO2", "Cairn & Co.", "Cairn & Co. Hideout 2P Bikepacking Tent", "329.00", None, 4.4, 121, "3 lb 1 oz", "3-season", "New", ("Fog",)),
    ("NF-MD6", "Northfork", "Northfork Meadow 6P Family Tent", "499.00", None, 4.1, 64, "14 lb 3 oz", "3-season", None, ("Rust", "Slate")),
    ("ST-BV1", "Summit Thread", "Summit Thread Bivy Pro", "189.00", None, 4.0, 31, "1 lb 2 oz", "4-season", None, ("Signal Orange",)),
]
S01_IDS = {p[0]: 1029380 + i * 7 for i, p in enumerate(S01_PRODUCTS)}
S01_BRANDS = [("Alpenglow", 5), ("Cairn & Co.", 4), ("Northfork", 3), ("Ridgeline", 7), ("Summit Thread", 3), ("Talus Works", 2)]
S01_DEPTS = ["Camp & Hike", "Climb", "Cycle", "Water", "Snow", "Run", "Travel", "Men", "Women", "Kids", "Deals"]
S01_FACETS = [
    ("capacity", "Capacity", [("1-person", 6), ("2-person", 11), ("3-person", 4), ("4-person+", 3)]),
    ("season", "Season rating", [("3-season", 21), ("4-season", 3)]),
    ("weight", "Trail weight", [("Under 2 lb", 4), ("2 – 3 lb", 8), ("3 – 4 lb", 6), ("Over 4 lb", 6)]),
    ("features", "Features", [("Freestanding", 15), ("Two doors", 13), ("Trekking-pole pitch", 5), ("Footprint included", 4)]),
]


def _s01_card_v1(p: tuple, tids: dict) -> str:
    sku, brand, name, price, was, rating, reviews, weight, seasons, badge, colours = p
    url = f"/p/{slug(name)}"
    t = tids.get(sku, {})
    badge_html = f'\n      <span class="product-card__badge">{e(badge)}</span>' if badge else ""
    if was:
        price_html = (f'<span class="price price--sale"{gt(t.get("price"))}>${price}</span> '
                      f'<s class="price price--was">${was}</s>')
    else:
        price_html = f'<span class="price"{gt(t.get("price"))}>${price}</span>'
    swatches = "".join(
        f'<li class="swatch" title="{e(c)}"><span class="visually-hidden">{e(c)}</span></li>' for c in colours
    )
    return f"""
  <li class="product-card" data-sku="{sku}">
    <div class="product-card__media">
      <a href="{url}" tabindex="-1"><img class="product-card__img" src="/images/products/{sku.lower()}-1.jpg" alt="{e(name)}" width="320" height="320" loading="lazy"></a>{badge_html}
      <button type="button" class="wishlist-btn" aria-label="Save {e(name)} to wishlist" data-testid="wishlist-{sku}"{gt(t.get("wish"))}>{icon("heart")}</button>
    </div>
    <div class="product-card__body">
      <p class="product-card__brand">{e(brand)}</p>
      <h3 class="product-card__title"><a href="{url}">{e(name)}</a></h3>
      <div class="product-card__rating">
        <span class="stars" style="--rating:{rating}" aria-hidden="true">★★★★★</span>
        <span class="visually-hidden">Rated {rating} out of 5 stars</span>
        <a class="rating-count" href="{url}#reviews">({reviews})</a>
      </div>
      <p class="product-card__price">{price_html}</p>
      <p class="product-card__meta">Trail weight {weight} · {seasons}</p>
      <ul class="swatches" aria-label="{len(colours)} color{'s' if len(colours) > 1 else ''}">{swatches}</ul>
      <button type="button" class="btn btn--secondary product-card__atc" data-testid="atc-{sku}"{gt(t.get("atc"))}>Add to cart</button>
    </div>
  </li>"""


def _s01_card_v2(p: tuple, tids: dict) -> str:
    sku, brand, name, price, was, rating, reviews, weight, seasons, badge, colours = p
    url = f"/p/{slug(name)}"
    t = tids.get(sku, {})
    badge_html = (
        f'\n        <span class="absolute left-3 top-3 rounded-full bg-white px-2.5 py-1 text-xs font-semibold text-emerald-900 shadow-sm">{e(badge)}</span>'
        if badge else ""
    )
    if was:
        price_html = (
            f'<span class="text-base font-bold text-red-700"{gt(t.get("price"))}>${price}</span>'
            f'<span class="text-sm text-stone-500 line-through">${was}</span>'
            f'<span class="text-xs font-semibold text-red-700">Save {round(100 - float(price) / float(was) * 100)}%</span>'
        )
    else:
        price_html = f'<span class="text-base font-bold text-stone-900"{gt(t.get("price"))}>${price}</span>'
    dots = "".join(
        f'<span class="h-3 w-3 rounded-full ring-1 ring-stone-300" title="{e(c)}"></span>' for c in colours
    )
    return f"""
      <div class="flex flex-col" data-product-id="{S01_IDS[sku]}">
        <div class="group relative flex flex-1 flex-col">
          <div class="relative aspect-square overflow-hidden rounded-xl bg-stone-100">
            <img src="https://cdn.ridgelineoutfitters.com/i/{S01_IDS[sku]}/main.webp?w=480" alt="{e(name)}" class="h-full w-full object-cover transition duration-300 group-hover:scale-105" loading="lazy">{badge_html}
          </div>
          <div class="mt-4 flex items-start justify-between gap-3">
            <div class="min-w-0">
              <p class="text-xs font-semibold uppercase tracking-wide text-stone-500">{e(brand)}</p>
              <h3 class="mt-1 text-sm font-semibold leading-snug text-stone-900"><a href="{url}" class="after:absolute after:inset-0">{e(name)}</a></h3>
            </div>
            <button type="button" aria-label="Add {e(name)} to favorites" aria-pressed="false" class="relative z-10 shrink-0 rounded-full p-2 text-stone-400 hover:bg-stone-100 hover:text-rose-600"{gt(t.get("wish"))}>{icon("heart", "h-5 w-5")}</button>
          </div>
          <div class="mt-1 flex items-center gap-1 text-xs text-stone-600">{icon("star", "h-3.5 w-3.5 fill-amber-400 text-amber-400", 14)}<span>{rating}</span><span aria-hidden="true">·</span><span>{reviews} reviews</span></div>
          <div class="mt-2 flex flex-wrap items-baseline gap-x-2">{price_html}</div>
          <p class="mt-1 text-xs text-stone-500">{weight} · {seasons}</p>
          <div class="mt-2 flex gap-1.5">{dots}</div>
          <div class="mt-auto pt-3">
            <button type="button" class="relative z-10 inline-flex w-full items-center justify-center rounded-full bg-emerald-800 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700"{gt(t.get("atc"))}>Add to bag</button>
          </div>
        </div>
      </div>"""


def _s01_mini_card_v2(p: tuple) -> str:
    """Staff-picks rail card (v2 decoy: same product, same price, same CTA)."""
    sku, brand, name, price, was, rating, reviews, *_ = p
    url = f"/p/{slug(name)}"
    price_cls = "text-sm font-bold text-red-700" if was else "text-sm font-bold text-stone-900"
    return f"""
        <li class="relative flex flex-col rounded-xl bg-white p-3 shadow-sm ring-1 ring-emerald-900/5">
          <img src="https://cdn.ridgelineoutfitters.com/i/{S01_IDS[sku]}/main.webp?w=240" alt="" class="aspect-[4/3] w-full rounded-lg object-cover">
          <div class="mt-3 flex items-start justify-between gap-2">
            <a href="{url}" class="text-sm font-semibold leading-snug text-stone-900 hover:underline">{e(name)}</a>
            <button type="button" aria-label="Add {e(name)} to favorites" aria-pressed="false" class="shrink-0 rounded-full p-1.5 text-stone-400 hover:text-rose-600">{icon("heart", "h-4 w-4", 16)}</button>
          </div>
          <p class="mt-1 text-xs text-stone-500">Picked by Maya, Bend OR store</p>
          <p class="mt-2"><span class="{price_cls}">${price}</span></p>
          <button type="button" class="mt-3 inline-flex w-full items-center justify-center rounded-full border border-emerald-800 px-3 py-1.5 text-sm font-semibold text-emerald-900 hover:bg-emerald-50">Add to bag</button>
        </li>"""


def suite01() -> tuple[str, str, dict]:
    tids = {"RL-ASC2": {"atc": "t2", "wish": "t5"}, "CC-UT2": {"price": "t3"}}
    by_sku = {p[0]: p for p in S01_PRODUCTS}

    # ---------------- v1 ----------------
    dept_v1 = "\n".join(
        f'      <li class="dept-nav__item{" is-active" if i == 0 else ""}"><a class="dept-nav__link" href="/c/{slug(d)}">{e(d)}</a></li>'
        for i, d in enumerate(S01_DEPTS)
    )
    brand_opts_v1 = "\n".join(
        f'          <li class="facet__option"><input class="facet__checkbox" type="checkbox" id="brand-{slug(b)}" name="brand" value="{slug(b)}"{gt("t1") if b == "Cairn & Co." else ""}>'
        f'<label class="facet__label" for="brand-{slug(b)}">{e(b)} <span class="facet__count">({n})</span></label></li>'
        for b, n in S01_BRANDS
    )
    other_facets_v1 = "\n".join(
        f"""      <fieldset class="facet" data-facet="{key}">
        <legend class="facet__title">{e(label)}</legend>
        <ul class="facet__options">
{chr(10).join(f'          <li class="facet__option"><input class="facet__checkbox" type="checkbox" id="{key}-{slug(o)}" name="{key}" value="{slug(o)}"><label class="facet__label" for="{key}-{slug(o)}">{e(o)} <span class="facet__count">({n})</span></label></li>' for o, n in opts)}
        </ul>
      </fieldset>"""
        for key, label, opts in S01_FACETS
    )
    cards_v1 = "".join(_s01_card_v1(p, tids) for p in S01_PRODUCTS)
    footer_cols_v1 = [
        ("Help", ["Contact us", "Order status", "Shipping", "Returns & exchanges", "Product recalls", "Gift cards"]),
        ("Membership", ["Join Ridgeline", "Member benefits", "Annual member reward", "Used gear trade-in"]),
        ("Stores & services", ["Find a store", "Classes & events", "Rentals", "Repairs & tune-ups"]),
        ("About us", ["Our story", "Stewardship", "Careers", "Newsroom", "Affiliate program"]),
    ]
    footer_v1 = "\n".join(
        f'      <div class="footer-col"><h3 class="footer-col__title">{e(h)}</h3><ul class="footer-col__links">'
        + "".join(f'<li><a href="/{slug(x)}">{e(x)}</a></li>' for x in links)
        + "</ul></div>"
        for h, links in footer_cols_v1
    )
    body_v1 = f"""
<a class="skip-link" href="#main">Skip to main content</a>
<div class="promo-bar" role="region" aria-label="Promotions">
  <p class="promo-bar__text">Free shipping on orders over $75 · Members earn 10% back on full-price gear · <a href="/membership">Join for $30</a></p>
</div>
<header class="site-header">
  <div class="site-header__inner">
    <a class="site-logo" href="/" aria-label="Ridgeline Outfitters home">{icon("mountain", "site-logo__mark", 32)}<span class="site-logo__text">Ridgeline Outfitters</span></a>
    <form class="site-search" role="search" action="/search">
      <label class="visually-hidden" for="site-search-input">Search</label>
      <input id="site-search-input" class="site-search__input" type="search" name="q" placeholder="Search for great gear &amp; clothing" autocomplete="off">
      <button class="site-search__submit" type="submit" aria-label="Search">{icon("search")}</button>
    </form>
    <ul class="header-actions">
      <li><a class="header-actions__link" href="/stores">{icon("pin")}<span>Find a store</span></a></li>
      <li><a class="header-actions__link" href="/account/sign-in">{icon("user")}<span>Sign in</span></a></li>
      <li><a class="header-actions__link header-actions__cart" href="/cart">{icon("cart")}<span>Cart</span><span class="cart-count">2</span></a></li>
    </ul>
  </div>
  <nav class="dept-nav" aria-label="Shop by department">
    <ul class="dept-nav__list">
{dept_v1}
    </ul>
  </nav>
</header>
<main id="main" class="plp-page">
  <nav class="breadcrumbs" aria-label="Breadcrumb">
    <ol class="breadcrumbs__list">
      <li class="breadcrumbs__item"><a href="/">Home</a></li>
      <li class="breadcrumbs__item"><a href="/c/camp-and-hike">Camp &amp; Hike</a></li>
      <li class="breadcrumbs__item"><a href="/c/camp-and-hike/tents">Tents</a></li>
      <li class="breadcrumbs__item" aria-current="page">Backpacking Tents</li>
    </ol>
  </nav>
  <div class="plp-header">
    <h1 class="plp-header__title">Backpacking Tents</h1>
    <p class="plp-header__count">24 results</p>
    <p class="plp-header__intro">Trail-tested shelters that pack small and pitch fast — from sub-2-lb solo tents to roomy two-door tents for the whole crew.</p>
  </div>
  <div class="plp">
    <aside class="filters-sidebar" aria-label="Filters">
      <div class="filters-sidebar__header">
        <h2 class="filters-sidebar__title">Filter by</h2>
        <a class="filters-clear" href="/c/camp-and-hike/tents/backpacking-tents">Clear all</a>
      </div>
      <form class="filters-form" action="/c/camp-and-hike/tents/backpacking-tents" method="get">
      <div class="facet facet--links" data-facet="category">
        <h3 class="facet__title">Category</h3>
        <ul class="facet__links">
          <li class="is-current"><a href="/c/camp-and-hike/tents/backpacking-tents" aria-current="page">Backpacking Tents (24)</a></li>
          <li><a href="/c/camp-and-hike/tents/camping-tents">Camping Tents (41)</a></li>
          <li><a href="/c/camp-and-hike/tents/ultralight-shelters">Ultralight Shelters (17)</a></li>
          <li><a href="/c/camp-and-hike/tents/bivy-sacks">Bivy Sacks (9)</a></li>
          <li><a href="/c/camp-and-hike/tents/footprints">Tent Footprints (22)</a></li>
        </ul>
      </div>
      <fieldset class="facet" data-facet="brand">
        <legend class="facet__title">Brand</legend>
        <ul class="facet__options">
{brand_opts_v1}
        </ul>
      </fieldset>
      <fieldset class="facet" data-facet="price">
        <legend class="facet__title">Price</legend>
        <div class="price-range">
          <label class="visually-hidden" for="price-min">Minimum price</label>
          <input class="price-range__input" type="number" id="price-min" name="price_min" placeholder="Min" min="0" inputmode="numeric">
          <span class="price-range__sep">to</span>
          <label class="visually-hidden" for="price-max">Maximum price</label>
          <input class="price-range__input" type="number" id="price-max" name="price_max" placeholder="Max" min="0" inputmode="numeric"{gt("t6")}>
          <button type="submit" class="price-range__go">Go</button>
        </div>
      </fieldset>
{other_facets_v1}
      <fieldset class="facet" data-facet="rating">
        <legend class="facet__title">Customer rating</legend>
        <ul class="facet__options">
          <li class="facet__option"><input class="facet__radio" type="radio" id="rating-4" name="rating" value="4"><label class="facet__label" for="rating-4">4 stars &amp; up <span class="facet__count">(19)</span></label></li>
          <li class="facet__option"><input class="facet__radio" type="radio" id="rating-3" name="rating" value="3"><label class="facet__label" for="rating-3">3 stars &amp; up <span class="facet__count">(24)</span></label></li>
        </ul>
      </fieldset>
      <div class="facet facet--toggle"><input class="facet__checkbox" type="checkbox" id="sale-only" name="sale" value="1"><label class="facet__label" for="sale-only">Sale items only (5)</label></div>
      </form>
    </aside>
    <section class="plp-results" aria-label="Products">
      <div class="plp-toolbar">
        <p class="plp-toolbar__showing">Showing 1–12 of 24</p>
        <div class="plp-toolbar__sort">
          <label class="plp-toolbar__label" for="sort-by">Sort by</label>
          <select id="sort-by" name="sort" class="sort-select"{gt("t4")}>
            <option value="featured" selected>Featured</option>
            <option value="bestsellers">Best sellers</option>
            <option value="price-asc">Price: low to high</option>
            <option value="price-desc">Price: high to low</option>
            <option value="rating">Top rated</option>
            <option value="newest">Newest</option>
          </select>
        </div>
        <div class="plp-toolbar__view" role="group" aria-label="Change view">
          <button type="button" class="view-toggle is-active" aria-label="Grid view" aria-pressed="true">{icon("grid")}</button>
          <button type="button" class="view-toggle" aria-label="List view" aria-pressed="false">{icon("list")}</button>
        </div>
      </div>
      <ul class="product-grid">{cards_v1}
      </ul>
      <div class="plp-pagination">
        <p class="plp-pagination__status">You've viewed 12 of 24 products</p>
        <progress class="plp-pagination__bar" value="12" max="24">50%</progress>
        <button type="button" class="btn btn--outline load-more">Load more</button>
      </div>
    </section>
  </div>
  <section class="plp-seo">
    <h2 class="plp-seo__title">How to choose a backpacking tent</h2>
    <p>Start with capacity and weight: solo hikers chasing big miles often go for a 1P or trekking-pole shelter under 2 lb, while a 2P with two doors and two vestibules is the sweet spot for most couples. Three-season tents handle spring through fall; choose a four-season tent for snow loading and exposed alpine camps.</p>
    <p>Not sure? <a href="/learn/backpacking-tent-buying-guide">Read our tent buying guide</a> or chat with a gear specialist at your local store.</p>
  </section>
</main>
<footer class="site-footer">
  <div class="site-footer__signup">
    <h2 class="site-footer__heading">Get trail-ready deals in your inbox</h2>
    <form class="signup-form" action="/newsletter" method="post">
      <label class="visually-hidden" for="footer-email">Email address</label>
      <input id="footer-email" class="signup-form__input" type="email" name="email" placeholder="Email address">
      <button class="btn btn--primary" type="submit">Sign up</button>
    </form>
  </div>
  <div class="site-footer__cols">
{footer_v1}
  </div>
  <div class="site-footer__legal">
    <p>© 2026 Ridgeline Outfitters, Inc.</p>
    <ul class="legal-links"><li><a href="/privacy">Privacy policy</a></li><li><a href="/terms">Terms of use</a></li><li><a href="/accessibility">Accessibility</a></li><li><a href="/privacy/choices">Your privacy choices</a></li></ul>
  </div>
</footer>
"""
    css_v1 = """
:root{--rl-green:#1f4d3a;--rl-sand:#f4efe6;--rl-ink:#1d1d1b}
body{margin:0;font-family:"Source Sans 3",system-ui,sans-serif;color:var(--rl-ink)}
.promo-bar{background:var(--rl-green);color:#fff;text-align:center;font-size:14px;padding:6px}
.site-header__inner{display:flex;align-items:center;gap:24px;max-width:1280px;margin:0 auto;padding:12px 24px}
.dept-nav__list{display:flex;gap:28px;list-style:none;margin:0;padding:0 24px}
.plp{display:grid;grid-template-columns:260px 1fr;gap:32px;max-width:1280px;margin:0 auto;padding:0 24px}
.product-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;list-style:none;padding:0}
.product-card{position:relative;border:1px solid #e3ded3;border-radius:6px;padding:12px}
.wishlist-btn{position:absolute;top:12px;right:12px}
.price--sale{color:#b3261e;font-weight:700}.price--was{color:#6b6b6b}
.visually-hidden{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
"""
    v1 = page(
        title="Backpacking Tents | Ridgeline Outfitters",
        head='<meta name="description" content="Shop lightweight backpacking tents from Ridgeline, Alpenglow, Cairn &amp; Co. and more. Free shipping over $75.">\n'
             '<link rel="canonical" href="https://www.ridgelineoutfitters.com/c/camp-and-hike/tents/backpacking-tents">\n',
        css=css_v1, body=body_v1, body_attrs=' class="page-plp"',
    )

    # ---------------- v2 ----------------
    order_v2 = ["RL-TH3", "CC-UT2", "AG-FL1", "RL-ASC2", "ST-AR2", "TW-BC4", "AG-FL2", "CC-HO2", "NF-RD3", "TW-SH1", "NF-MD6", "ST-BV1"]
    cards_v2 = "".join(_s01_card_v2(by_sku[s], tids) for s in order_v2)
    picks_v2 = "".join(_s01_mini_card_v2(by_sku[s]) for s in ("RL-ASC2", "CC-UT2", "TW-SH1", "AG-FL2"))
    brands_by_count = sorted(S01_BRANDS, key=lambda b: (-b[1], b[0]))
    dept_v2 = "".join(
        f'<li><a href="/c/{slug(d)}" class="{"border-b-2 border-emerald-800 pb-3 text-emerald-900" if i == 0 else "pb-3 text-stone-700 hover:text-emerald-800"}">{e(d)}</a></li>'
        for i, d in enumerate(S01_DEPTS)
    )
    mobile_brands = "".join(
        f'<li class="flex items-center gap-3 py-2"><input id="m-brand-{i}" type="checkbox" name="brand" value="{e(b)}" class="h-4 w-4 rounded border-stone-300 text-emerald-700">'
        f'<label for="m-brand-{i}" class="text-sm text-stone-700">{e(b)}</label><span class="ml-auto text-xs text-stone-400">{n}</span></li>'
        for i, (b, n) in enumerate(brands_by_count)
    )
    shadow_brands = "".join(
        f'<li class="ais-RefinementList-item"><label class="ais-RefinementList-label">'
        f'<input class="ais-RefinementList-checkbox" type="checkbox" id=":r1{i}:" name="refinementList[brand][]" value="{e(b)}"{gt("t1") if b == "Cairn & Co." else ""}>'
        f'<span class="ais-RefinementList-labelText">{e(b)}</span><span class="ais-RefinementList-count">{n}</span></label></li>'
        for i, (b, n) in enumerate(brands_by_count)
    )
    shadow_facets = "".join(
        f'<div class="ais-Panel" data-attribute="{key}"><div class="ais-Panel-header"><span>{e(label)}</span></div><div class="ais-Panel-body">'
        f'<ul class="ais-RefinementList-list">'
        + "".join(
            f'<li class="ais-RefinementList-item"><label class="ais-RefinementList-label"><input class="ais-RefinementList-checkbox" type="checkbox" name="refinementList[{key}][]" value="{e(o)}">'
            f'<span class="ais-RefinementList-labelText">{e(o)}</span><span class="ais-RefinementList-count">{n}</span></label></li>'
            for o, n in opts
        )
        + "</ul></div></div>"
        for key, label, opts in S01_FACETS[::-1]
    )
    footer_v2 = "".join(
        f'<div><h3 class="text-sm font-semibold text-white">{e(h)}</h3><ul role="list" class="mt-4 space-y-3">'
        + "".join(f'<li><a href="/{slug(x)}" class="text-sm text-emerald-100/80 hover:text-white">{e(x)}</a></li>' for x in links)
        + "</ul></div>"
        for h, links in [
            ("Shop", ["Camp & Hike", "Climb", "Cycle", "Snow", "Deals", "Gift cards"]),
            ("Customer care", ["Contact us", "Order status", "Shipping", "Returns & exchanges", "Product recalls"]),
            ("Membership", ["Join Ridgeline", "Member benefits", "Used gear trade-in"]),
            ("Company", ["Our story", "Stewardship", "Careers", "Newsroom"]),
        ]
    )
    body_v2 = f"""
<div id="__next">
<div class="bg-emerald-950 px-4 py-2 text-center text-xs font-medium tracking-wide text-emerald-50">Free shipping over $75 — members earn 10% back. <a href="/membership" class="font-semibold underline underline-offset-2">Join today</a></div>
<header class="sticky top-0 z-40 border-b border-stone-200 bg-white/95 backdrop-blur">
  <div class="mx-auto flex h-16 max-w-7xl items-center gap-6 px-4 lg:px-8">
    <button type="button" class="-ml-2 rounded-md p-2 text-stone-700 lg:hidden" aria-label="Open menu">{icon("menu", "h-6 w-6", 24)}</button>
    <a href="/" class="flex shrink-0 items-center gap-2 text-lg font-extrabold tracking-tight text-emerald-900">{icon("mountain", "h-8 w-8", 32)}<span>Ridgeline</span></a>
    <form role="search" action="/search" class="relative hidden flex-1 md:block">
      <input type="search" name="q" aria-label="Search Ridgeline" placeholder="Search tents, jackets, brands…" class="w-full rounded-full border border-stone-300 bg-stone-50 py-2 pl-10 pr-4 text-sm focus:border-emerald-700 focus:ring-emerald-700">
      <span class="pointer-events-none absolute inset-y-0 left-3 flex items-center text-stone-400">{icon("search", "h-5 w-5")}</span>
    </form>
    <div class="ml-auto flex items-center gap-1">
      <a href="/stores" class="hidden items-center gap-1 rounded-full px-3 py-2 text-sm font-medium text-stone-700 hover:bg-stone-100 xl:flex">{icon("pin", "h-5 w-5")}<span>Bend, OR</span></a>
      <a href="/account" class="rounded-full p-2 text-stone-700 hover:bg-stone-100" aria-label="Account">{icon("user", "h-6 w-6", 24)}</a>
      <a href="/cart" class="relative rounded-full p-2 text-stone-700 hover:bg-stone-100" aria-label="Bag, 2 items">{icon("bag", "h-6 w-6", 24)}<span class="absolute -right-0.5 -top-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-emerald-700 text-[11px] font-bold text-white">2</span></a>
    </div>
  </div>
  <nav aria-label="Departments" class="hidden border-t border-stone-100 lg:block">
    <ul class="mx-auto flex max-w-7xl gap-7 px-8 pt-3 text-sm font-semibold">{dept_v2}</ul>
  </nav>
</header>
<main class="mx-auto max-w-7xl px-4 pb-16 lg:px-8">
  <nav aria-label="Breadcrumb" class="pt-6">
    <ol role="list" class="flex flex-wrap items-center gap-1 text-xs text-stone-500">
      <li><a href="/" class="hover:text-stone-800">Home</a></li><li aria-hidden="true">/</li>
      <li><a href="/c/camp-and-hike" class="hover:text-stone-800">Camp &amp; Hike</a></li><li aria-hidden="true">/</li>
      <li><a href="/c/camp-and-hike/tents" class="hover:text-stone-800">Tents</a></li><li aria-hidden="true">/</li>
      <li aria-current="page" class="font-medium text-stone-800">Backpacking Tents</li>
    </ol>
  </nav>
  <div class="flex flex-wrap items-end justify-between gap-4 py-6">
    <div>
      <h1 class="text-3xl font-bold tracking-tight text-stone-900">Backpacking Tents</h1>
      <p class="mt-1 max-w-2xl text-sm text-stone-600">Lightweight shelters that pack small and pitch fast. 24 products.</p>
    </div>
    <button type="button" class="inline-flex items-center gap-2 rounded-full border border-stone-300 px-4 py-2 text-sm font-semibold lg:hidden" aria-controls="mobile-filters">{icon("sliders", "h-4 w-4", 16)}Filters</button>
  </div>
  <section aria-labelledby="staff-picks-heading" class="mb-10 rounded-2xl bg-emerald-50 p-6">
    <div class="flex items-center justify-between">
      <h2 id="staff-picks-heading" class="text-lg font-bold text-emerald-950">Staff picks for thru-hikers</h2>
      <a href="/staff-picks/thru-hiking" class="text-sm font-semibold text-emerald-800 hover:underline">See all picks</a>
    </div>
    <ul role="list" class="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">{picks_v2}
    </ul>
  </section>
  <div class="lg:grid lg:grid-cols-[17rem_minmax(0,1fr)] lg:gap-x-10">
    <div id="mobile-filters" role="dialog" aria-modal="true" aria-label="Filters" class="fixed inset-0 z-50 flex lg:hidden" hidden>
      <div class="ml-auto flex h-full w-full max-w-xs flex-col overflow-y-auto bg-white py-4 shadow-xl">
        <div class="flex items-center justify-between px-4"><h2 class="text-lg font-semibold">Filters</h2><button type="button" class="rounded-md p-2 text-stone-400" aria-label="Close filters">{icon("close", "h-6 w-6", 24)}</button></div>
        <form class="mt-4 border-t border-stone-200 px-4">
          <h3 class="pt-4 text-sm font-semibold text-stone-900">Brand</h3>
          <ul role="list" class="mt-2">{mobile_brands}</ul>
          <h3 class="pt-4 text-sm font-semibold text-stone-900">Price</h3>
          <div class="mt-2 flex items-center gap-2"><input type="number" name="min" placeholder="Min" aria-label="Minimum price" class="w-24 rounded-md border-stone-300 text-sm"><span>–</span><input type="number" name="max" placeholder="Max" aria-label="Maximum price" class="w-24 rounded-md border-stone-300 text-sm"></div>
          <button type="submit" class="mt-6 w-full rounded-full bg-emerald-800 py-2.5 text-sm font-semibold text-white">Show 24 results</button>
        </form>
      </div>
    </div>
    <rl-filter-panel class="hidden lg:block" index="prod_plp_tents" data-category="backpacking-tents">
      <template shadowrootmode="open">
        <style>:host{{display:block;font:14px/1.4 system-ui}}.ais-Panel{{border-top:1px solid #e7e5e4;padding:16px 0}}.ais-Panel-header{{font-weight:600;margin-bottom:8px}}.ais-RefinementList-list{{list-style:none;margin:0;padding:0}}.ais-RefinementList-label{{display:flex;gap:8px;align-items:center;padding:4px 0}}.ais-RefinementList-count{{margin-left:auto;background:#f5f5f4;border-radius:999px;padding:0 8px;font-size:12px}}</style>
        <div class="ais-CurrentRefinements ais-CurrentRefinements--noRefinement"><ul class="ais-CurrentRefinements-list"></ul></div>
        <div class="ais-ClearRefinements"><button type="button" class="ais-ClearRefinements-button ais-ClearRefinements-button--disabled" disabled>Clear filters</button></div>
        <div class="ais-Panel" data-attribute="brand">
          <div class="ais-Panel-header"><span>Brand</span></div>
          <div class="ais-Panel-body"><div class="ais-RefinementList"><ul class="ais-RefinementList-list">{shadow_brands}</ul></div></div>
        </div>
        <div class="ais-Panel" data-attribute="price">
          <div class="ais-Panel-header"><span>Price</span></div>
          <div class="ais-Panel-body"><div class="ais-RangeInput">
            <form class="ais-RangeInput-form">
              <label class="ais-RangeInput-label"><span class="ais-RangeInput-labelText">Min</span><input class="ais-RangeInput-input ais-RangeInput-input--min" type="number" placeholder="$189" min="189" max="689" step="1"></label>
              <span class="ais-RangeInput-separator">to</span>
              <label class="ais-RangeInput-label"><span class="ais-RangeInput-labelText">Max</span><input class="ais-RangeInput-input ais-RangeInput-input--max" type="number" placeholder="$689" min="189" max="689" step="1"{gt("t6")}></label>
              <button class="ais-RangeInput-submit" type="submit">Apply</button>
            </form>
          </div></div>
        </div>
        {shadow_facets}
        <div class="ais-Panel" data-attribute="rating">
          <div class="ais-Panel-header"><span>Rating</span></div>
          <div class="ais-Panel-body"><ul class="ais-RatingMenu-list"><li class="ais-RatingMenu-item"><a class="ais-RatingMenu-link" href="?rating=4" aria-label="4 &amp; up">★★★★☆ &amp; up <span class="ais-RatingMenu-count">19</span></a></li><li class="ais-RatingMenu-item"><a class="ais-RatingMenu-link" href="?rating=3" aria-label="3 &amp; up">★★★☆☆ &amp; up <span class="ais-RatingMenu-count">24</span></a></li></ul></div>
        </div>
        <div class="ais-Panel" data-attribute="on_sale"><div class="ais-Panel-body"><label class="ais-ToggleRefinement-label"><input class="ais-ToggleRefinement-checkbox" type="checkbox"><span class="ais-ToggleRefinement-labelText">On sale</span></label></div></div>
      </template>
    </rl-filter-panel>
    <div>
      <div class="flex flex-wrap items-center justify-between gap-3 border-b border-stone-200 pb-4">
        <p class="text-sm text-stone-600">Showing <span class="font-semibold text-stone-900">12</span> of 24</p>
        <div class="flex items-center gap-2">
          <label for=":R1qm6:" class="text-sm text-stone-600">Sort by</label>
          <select id=":R1qm6:" name="sortBy" class="rounded-full border-stone-300 py-1.5 pl-3 pr-8 text-sm font-medium focus:border-emerald-700 focus:ring-emerald-700"{gt("t4")}>
            <option value="prod_plp_tents" selected>Recommended</option>
            <option value="prod_plp_tents_bestsellers">Best sellers</option>
            <option value="prod_plp_tents_price_asc">Price: Low to High</option>
            <option value="prod_plp_tents_price_desc">Price: High to Low</option>
            <option value="prod_plp_tents_rating">Highest rated</option>
            <option value="prod_plp_tents_new">New arrivals</option>
          </select>
        </div>
      </div>
      <div class="mt-8 grid grid-cols-2 gap-x-4 gap-y-10 lg:grid-cols-3 lg:gap-x-6">{cards_v2}
      </div>
      <div class="mt-12 flex flex-col items-center gap-3">
        <p class="text-sm text-stone-600">12 of 24 products</p>
        <div class="h-1 w-48 overflow-hidden rounded-full bg-stone-200"><div class="h-full w-1/2 bg-emerald-700"></div></div>
        <button type="button" class="rounded-full border border-stone-900 px-6 py-2 text-sm font-semibold hover:bg-stone-900 hover:text-white">Show more</button>
      </div>
    </div>
  </div>
  <section class="mt-16 max-w-3xl text-sm leading-6 text-stone-600">
    <h2 class="text-base font-semibold text-stone-900">How to choose a backpacking tent</h2>
    <p class="mt-2">Start with capacity and weight: solo hikers chasing big miles often go for a 1P or trekking-pole shelter under 2 lb, while a 2P with two doors is the sweet spot for most couples. Choose a four-season tent for snow loading and exposed alpine camps.</p>
    <p class="mt-2"><a href="/learn/backpacking-tent-buying-guide" class="font-semibold text-emerald-800 underline">Read the tent buying guide</a></p>
  </section>
</main>
<footer class="bg-emerald-950" aria-labelledby="footer-heading">
  <h2 id="footer-heading" class="sr-only">Footer</h2>
  <div class="mx-auto max-w-7xl px-6 py-14 lg:px-8">
    <div class="grid grid-cols-2 gap-8 md:grid-cols-4">{footer_v2}</div>
    <div class="mt-12 border-t border-white/10 pt-8 md:flex md:items-center md:justify-between">
      <form class="flex max-w-md gap-2" action="/newsletter" method="post"><input type="email" name="email" aria-label="Email address" placeholder="you@example.com" class="min-w-0 flex-auto rounded-full border-0 bg-white/5 px-4 py-2 text-sm text-white ring-1 ring-white/10"><button type="submit" class="rounded-full bg-emerald-500 px-4 py-2 text-sm font-semibold text-emerald-950">Subscribe</button></form>
      <p class="mt-6 text-xs text-emerald-100/60 md:mt-0">© 2026 Ridgeline Outfitters, Inc. · <a href="/privacy" class="hover:text-white">Privacy</a> · <a href="/terms" class="hover:text-white">Terms</a> · <a href="/accessibility" class="hover:text-white">Accessibility</a></p>
    </div>
  </div>
</footer>
</div>
"""
    v2 = page(
        title="Backpacking Tents | Ridgeline",
        head='<meta name="description" content="Lightweight backpacking tents from Ridgeline, Alpenglow, Cairn &amp; Co. and more.">\n'
             '<link rel="canonical" href="https://www.ridgelineoutfitters.com/c/camp-and-hike/tents/backpacking-tents">\n',
        body=body_v2, html_attrs=' class="h-full scroll-smooth"', body_attrs=' class="min-h-full bg-stone-50 font-sans text-stone-900 antialiased"',
    )

    meta = {
        "title": "Product listing grid with filters sidebar — outdoor gear store",
        "mutations": ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change",
                      "testid-change", "copy-change", "tag-change", "attribute-churn", "structure-move", "insertion"],
        "notes": (
            "v2 migrates the listing to Tailwind utilities and an Algolia InstantSearch filter panel rendered inside "
            "<rl-filter-panel>'s declarative shadow root (brand options re-sorted by count, React useId ids, values now "
            "the brand display name). A hidden mobile filter dialog duplicates the brand checkboxes and Min/Max inputs. "
            "Product cards become nested divs, are re-sorted ('Recommended') and lose data-sku/data-testid; 'Add to cart' "
            "reads 'Add to bag'; wishlist hearts are relabelled 'Add … to favorites'. A new 'Staff picks' rail above the grid "
            "repeats the Ridgeline Ascent 2P and Cairn & Co. Ultra Trekker with identical prices and CTAs."
        ),
        "targets": [
            target("t1", "Brand filter checkbox 'Cairn & Co.' in the filters sidebar",
                   "#brand-cairn-and-co",
                   "//fieldset[@data-facet='brand']//input[@value='cairn-and-co']",
                   ["shadow-dom", "id-change", "attribute-churn", "sibling-reorder", "decoy", "class-obfuscation"]),
            target("t2", "'Add to cart' button of the 'Ridgeline Ascent 2P Tent' product card",
                   "ul.product-grid > li:nth-child(3) button.product-card__atc",
                   "//a[normalize-space()='Ridgeline Ascent 2P Tent']/ancestor::li[contains(@class,'product-card')]//button[normalize-space()='Add to cart']",
                   ["copy-change", "testid-change", "class-obfuscation", "wrapper-divs", "sibling-reorder", "decoy", "tag-change"]),
            target("t3", "Sale price ($319.96) of the 'Cairn & Co. Ultra Trekker 2P Tent' card",
                   "li[data-sku='CC-UT2'] .price--sale",
                   "(//ul[@class='product-grid']/li)[5]//span[@class='price price--sale']",
                   ["class-obfuscation", "attribute-churn", "sibling-reorder", "decoy", "insertion", "wrapper-divs"]),
            target("t4", "'Sort by' dropdown above the product grid",
                   "#sort-by",
                   "//label[normalize-space()='Sort by']/following-sibling::select",
                   ["id-change", "attribute-churn", "class-obfuscation", "copy-change"]),
            target("t5", "Wishlist (heart) icon button of the 'Ridgeline Ascent 2P Tent' card",
                   "[data-testid='wishlist-RL-ASC2']",
                   "//button[@aria-label='Save Ridgeline Ascent 2P Tent to wishlist']",
                   ["testid-change", "attribute-churn", "copy-change", "structure-move", "decoy", "class-obfuscation"]),
            target("t6", "Maximum price input of the price-range filter",
                   ".price-range input[name='price_max']",
                   "//input[@placeholder='Max']",
                   ["shadow-dom", "id-change", "attribute-churn", "copy-change", "class-obfuscation", "decoy", "wrapper-divs"]),
        ],
    }
    return v1, v2, meta


# ---------------------------------------------------------------------------
# ecommerce-02 — Fieldtone Audio: headphones product detail page
# ---------------------------------------------------------------------------

S02_COLORS = [("Midnight Black", "#1c1d21"), ("Sandstone", "#d8c7ad"), ("Fjord Blue", "#3d5a80"), ("Silver Mist", "#c9ccd1")]
S02_COLORS_V2 = [("Midnight Black", "#1c1d21"), ("Silver Mist", "#c9ccd1"), ("Fjord Blue", "#3d5a80"),
                 ("Sandstone", "#d8c7ad"), ("Moss Green", "#5b6b4a")]
S02_IMAGES = [
    ("front", "Front view"),
    ("side", "Side profile showing the touch-sensitive ear cup"),
    ("folded", "Folded flat for travel"),
    ("cushion", "Close-up of the memory-foam ear cushion"),
    ("case", "Stored in the included carrying case"),
    ("worn", "Worn on a morning commute"),
]
# id, title, author, stars, iso date, label, body, helpful yes, helpful no
S02_REVIEWS = [
    ("90122", "Comfortable for long flights", "Dev P.", 5, "2026-10-30", "Oct 30, 2026",
     "Wore these on a 17-hour flight from SFO to Singapore and forgot they were on. The ANC flattens engine drone completely and the battery still showed 40% when we landed.", 41, 3),
    ("88213", "Best noise cancelling under $300", "Marisol K.", 5, "2026-10-14", "Oct 14, 2026",
     "Coming from a five-year-old pair, the difference on my subway commute is night and day. Voices still bleed through a little, but the low rumble is gone. For $279 I don't think anything beats it.", 23, 2),
    ("87410", "Great sound, app is clunky", "Henrik L.", 4, "2026-10-02", "Oct 2, 2026",
     "Tuning is warm with a tight low end and LDAC sounds excellent from my phone. The companion app forgets my EQ preset after firmware updates though, which is annoying.", 19, 4),
    ("91877", "Ear cups get warm", "Tasha W.", 3, "2026-11-01", "Nov 1, 2026",
     "Sound and ANC are great, but the protein-leather cushions get warm after an hour at the gym. Fine for the office, less so for workouts.", 11, 1),
    ("86002", "Multipoint actually works", "Owen R.", 5, "2026-09-21", "Sep 21, 2026",
     "Switches between my laptop and phone without me touching anything. Calls sound clear according to my coworkers.", 9, 0),
]
S02_NEW_REVIEW = ("92340", "Moss Green is gorgeous in person", "Lina S.", 5, "2026-11-04", "Nov 4, 2026",
                  "Ordered the new Moss Green colour and it looks even better than the photos. Same great ANC as my old black pair, and the case is slimmer.", 2, 0)
S02_SPECS = [
    ("Driver", "40 mm dynamic, PEEK diaphragm"),
    ("Frequency response", "4 Hz – 40 kHz"),
    ("Noise cancellation", "Adaptive hybrid ANC, 8 microphones"),
    ("Battery life", "Up to 38 h (ANC on), 52 h (ANC off)"),
    ("Charging", "USB-C, 10 min charge = 5 h playback"),
    ("Bluetooth", "5.4 with multipoint (2 devices)"),
    ("Codecs", "SBC, AAC, LDAC"),
    ("Weight", "254 g"),
]
S02_ACCESSORIES = [
    ("Halcyon Hard Travel Case", "39.00"),
    ("Braided USB-C Cable, 2 m", "19.00"),
    ("Replacement Memory-Foam Ear Cushions", "29.00"),
    ("Walnut Headphone Stand", "59.00"),
]
S02_FEATURES = [
    ("Adaptive ANC", "Eight microphones re-tune cancellation 50,000 times a second."),
    ("38-hour battery", "A full week of commutes on one charge, with ANC on."),
    ("Hi-res wireless", "LDAC streaming up to 990 kbps for detail you can hear."),
    ("Multipoint", "Stay connected to your laptop and phone at the same time."),
    ("All-day comfort", "Memory-foam cushions and a 254 g frame that disappears on your head."),
    ("Fold-flat design", "Packs into a slim case that slides into any carry-on."),
]
S02_JSONLD = (
    '<script type="application/ld+json">{"@context":"https://schema.org","@type":"Product",'
    '"name":"Halcyon Drift ANC Wireless Over-Ear Headphones","brand":{"@type":"Brand","name":"Halcyon"},'
    '"sku":"HAL-DRIFT-ANC","aggregateRating":{"@type":"AggregateRating","ratingValue":"4.6","reviewCount":"1284"},'
    '"offers":{"@type":"Offer","priceCurrency":"USD","price":"279.00","availability":"https://schema.org/InStock"}}</script>\n'
)


def suite02() -> tuple[str, str, dict]:
    # ---------------- v1 ----------------
    nav_items = ["Headphones", "Earbuds", "Speakers", "Turntables", "Hi-Fi", "Accessories", "Deals"]
    nav_v1 = "".join(
        f'<li class="main-nav__item"><a class="main-nav__link{" is-active" if n == "Headphones" else ""}" href="/{slug(n)}">{n}</a></li>'
        for n in nav_items
    )
    thumbs_v1 = "\n".join(
        f'          <li class="gallery__thumb-item"><button type="button" class="gallery__thumb{" is-selected" if i == 0 else ""}" aria-label="View image {i + 1} of 6" aria-controls="gallery-main"{gt("t4") if key == "side" else ""}>'
        f'<img src="/media/drift-anc/midnight-black-{key}_160x160.jpg" alt="" width="80" height="80"></button></li>'
        for i, (key, _alt) in enumerate(S02_IMAGES)
    )
    swatches_v1 = "\n".join(
        f'          <input type="radio" class="swatch-input" name="color" id="color-{slug(c)}" value="{slug(c)}"{" checked" if i == 0 else ""}{gt("t1") if c == "Fjord Blue" else ""}>'
        f'<label class="swatch" for="color-{slug(c)}" style="--swatch:{hexv}" title="{c}"><span class="visually-hidden">{c}</span></label>'
        for i, (c, hexv) in enumerate(S02_COLORS)
    )
    features_v1 = "".join(
        f'<li class="feature-list__item">{icon("check", "feature-list__icon")}<h3 class="feature-list__title">{t}</h3><p class="feature-list__text">{d}</p></li>'
        for t, d in S02_FEATURES
    )
    specs_v1 = "".join(f"<tr><th scope=\"row\">{k}</th><td>{v}</td></tr>" for k, v in S02_SPECS)

    def review_v1(r: tuple) -> str:
        rid, title, author, stars, iso, label, body, yes, no = r
        return f"""
        <li class="review" id="review-{rid}">
          <div class="review__stars" aria-label="{stars} out of 5 stars">{"★" * stars}{"☆" * (5 - stars)}</div>
          <h3 class="review__title">{e(title)}</h3>
          <p class="review__meta"><span class="review__author">{author}</span> · <span class="review__badge">Verified buyer</span> · <time datetime="{iso}">{label}</time></p>
          <p class="review__body">{e(body)}</p>
          <div class="review__footer">
            <span class="review__prompt">Was this review helpful?</span>
            <button type="button" class="review__helpful"{gt("t5") if rid == "88213" else ""}>Yes ({yes})</button>
            <button type="button" class="review__unhelpful">No ({no})</button>
            <a class="review__report" href="/reviews/{rid}/report">Report</a>
          </div>
        </li>"""

    reviews_v1 = "".join(review_v1(r) for r in S02_REVIEWS)
    hist = [(5, 74), (4, 16), (3, 6), (2, 2), (1, 2)]
    hist_v1 = "".join(
        f'<li class="histogram__row"><span class="histogram__label">{s} stars</span><meter class="histogram__bar" min="0" max="100" value="{p}">{p}%</meter><span class="histogram__pct">{p}%</span></li>'
        for s, p in hist
    )
    acc_v1 = "".join(
        f'<li class="rec-card"><img class="rec-card__img" src="/media/accessories/{slug(n)}_320.jpg" alt="{e(n)}" width="160" height="160">'
        f'<a class="rec-card__name" href="/products/{slug(n)}">{e(n)}</a><span class="rec-card__price">${p}</span>'
        f'<button type="button" class="rec-card__quick">Quick view</button></li>'
        for n, p in S02_ACCESSORIES
    )
    footer_v1 = "".join(
        f'<div class="footer__col"><h2 class="footer__title">{h}</h2><ul class="footer__links">'
        + "".join(f'<li><a href="/{slug(x)}">{e(x)}</a></li>' for x in links) + "</ul></div>"
        for h, links in [
            ("Shop", ["Headphones", "Earbuds", "Speakers", "Turntables", "Gift cards", "Refurbished"]),
            ("Support", ["Help center", "Order status", "Shipping & delivery", "Returns", "Warranty", "Product manuals"]),
            ("Fieldtone", ["About us", "Listening rooms", "Careers", "Affiliates", "Accessibility"]),
        ]
    )
    body_v1 = f"""
<header class="header">
  <div class="header__top">
    <p class="header__announcement">Free 2-day shipping &amp; a 60-night trial on all headphones</p>
    <ul class="header__utility"><li><a href="/help">Help</a></li><li><a href="/listening-rooms">Listening rooms</a></li><li><a href="/trade-in">Trade-in</a></li></ul>
  </div>
  <div class="header__main">
    <a class="header__logo" href="/">fieldtone</a>
    <nav class="header__nav" aria-label="Main"><ul class="main-nav">{nav_v1}</ul></nav>
    <div class="header__icons">
      <button type="button" class="header__icon" aria-label="Search">{icon("search")}</button>
      <a class="header__icon" href="/account" aria-label="Account">{icon("user")}</a>
      <a class="header__icon header__cart" href="/cart" aria-label="Cart, 0 items">{icon("bag")}<span class="header__cart-count">0</span></a>
    </div>
  </div>
</header>
<main class="main" id="MainContent">
  <nav class="breadcrumb" aria-label="Breadcrumb">
    <a href="/">Home</a> <span aria-hidden="true">›</span> <a href="/headphones">Headphones</a> <span aria-hidden="true">›</span> <a href="/headphones/over-ear">Over-ear</a> <span aria-hidden="true">›</span> <span aria-current="page">Halcyon Drift ANC</span>
  </nav>
  <div class="pdp">
    <div class="pdp-gallery">
      <figure class="gallery__main" id="gallery-main">
        <img src="/media/drift-anc/midnight-black-front_1200x1200.jpg" alt="Halcyon Drift ANC in Midnight Black, front view" width="600" height="600">
        <figcaption class="visually-hidden">Front view</figcaption>
      </figure>
      <ul class="gallery__thumbs">
{thumbs_v1}
      </ul>
    </div>
    <div class="pdp-info">
      <a class="pdp-info__brand" href="/brands/halcyon">Halcyon</a>
      <h1 class="pdp-info__title">Drift ANC Wireless Over-Ear Headphones</h1>
      <div class="pdp-info__rating"><span class="stars" aria-hidden="true">★★★★★</span><span class="visually-hidden">4.6 out of 5 stars</span> <a class="pdp-info__reviews-link" href="#reviews">4.6 (1,284 reviews)</a></div>
      <div class="price"><span class="price__current"{gt("t3")}>$279.00</span> <s class="price__compare">$349.00</s> <span class="price__badge">Save $70</span></div>
      <p class="pdp-info__installments">or 4 interest-free payments of $69.75 with <strong>Splitpay</strong></p>
      <form id="product-form" class="product-form" action="/cart/add" method="post">
        <input type="hidden" name="id" value="44120381">
        <fieldset id="color-picker" class="variant-picker">
          <legend class="variant-picker__legend">Color: <span class="variant-picker__value">Midnight Black</span></legend>
          <div class="variant-picker__swatches">
{swatches_v1}
          </div>
        </fieldset>
        <div class="product-form__field">
          <label class="product-form__label" for="edition">Edition</label>
          <select class="product-form__select" id="edition" name="edition">
            <option value="standard" selected>Standard</option>
            <option value="travel">Travel bundle (hard case + airplane adapter) – $309.00</option>
          </select>
        </div>
        <div class="product-form__field product-form__qty">
          <label class="product-form__label" for="quantity">Quantity</label>
          <div class="qty">
            <button type="button" class="qty__btn qty__btn--minus" aria-label="Decrease quantity">−</button>
            <input class="qty__input" id="quantity" type="number" name="quantity" value="1" min="1" max="5">
            <button type="button" class="qty__btn qty__btn--plus" aria-label="Increase quantity">+</button>
          </div>
        </div>
        <div class="product-form__buttons">
          <button type="submit" id="add-to-cart" class="btn btn--primary add-to-cart" name="add"{gt("t2")}>Add to cart</button>
          <button type="button" class="btn btn--secondary buy-now">Buy it now</button>
        </div>
        <button type="button" class="link-button wishlist-link">{icon("heart", "link-button__icon", 16)} Add to wishlist</button>
      </form>
      <ul class="pdp-perks">
        <li class="pdp-perks__item">{icon("truck", "pdp-perks__icon")}Free 2-day shipping — order within 3 hrs 12 mins</li>
        <li class="pdp-perks__item">{icon("return", "pdp-perks__icon")}60-night trial with free returns</li>
        <li class="pdp-perks__item">{icon("shield", "pdp-perks__icon")}2-year Fieldtone warranty</li>
      </ul>
    </div>
  </div>
  <nav class="pdp-tabs" aria-label="Product information">
    <a href="#overview" class="pdp-tabs__link is-active">Overview</a>
    <a href="#specs" class="pdp-tabs__link">Specifications</a>
    <a href="#in-the-box" class="pdp-tabs__link">In the box</a>
    <a href="#reviews" class="pdp-tabs__link"{gt("t6")}>Reviews (1,284)</a>
  </nav>
  <section id="overview" class="pdp-section">
    <h2 class="pdp-section__title">Overview</h2>
    <p>Drift ANC pairs Halcyon's quietest noise cancelling yet with a warm, detailed 40 mm driver and a battery that outlasts a week of commutes. Fold them flat, drop them in the case and go.</p>
    <ul class="feature-list">{features_v1}</ul>
  </section>
  <section id="specs" class="pdp-section">
    <h2 class="pdp-section__title">Specifications</h2>
    <table class="spec-table"><tbody>{specs_v1}</tbody></table>
  </section>
  <section id="in-the-box" class="pdp-section">
    <h2 class="pdp-section__title">In the box</h2>
    <ul class="box-list"><li>Drift ANC headphones</li><li>Soft carrying case</li><li>USB-C charging cable (1 m)</li><li>3.5 mm audio cable (1.2 m)</li><li>Quick start guide</li></ul>
  </section>
  <section id="reviews" class="pdp-section reviews">
    <div class="reviews__header">
      <h2 class="pdp-section__title">Customer reviews</h2>
      <button type="button" class="btn btn--outline reviews__write">Write a review</button>
    </div>
    <div class="reviews__summary">
      <p class="reviews__average"><span class="reviews__score">4.6</span> out of 5</p>
      <p class="reviews__count">Based on 1,284 reviews</p>
      <ul class="histogram">{hist_v1}</ul>
    </div>
    <div class="reviews__toolbar">
      <label for="review-sort">Sort by</label>
      <select id="review-sort" class="reviews__sort"><option selected>Most helpful</option><option>Most recent</option><option>Highest rating</option><option>Lowest rating</option></select>
    </div>
    <ol class="review-list">{reviews_v1}
    </ol>
    <nav class="reviews__pagination" aria-label="Review pages"><a href="?page=1" aria-current="page">1</a> <a href="?page=2">2</a> <a href="?page=3">3</a> <span>…</span> <a href="?page=257">257</a> <a href="?page=2" rel="next">Next</a></nav>
  </section>
  <section class="recommendations">
    <h2 class="recommendations__title">Pairs well with</h2>
    <ul class="rec-list">{acc_v1}</ul>
  </section>
</main>
<footer class="footer">
  <div class="footer__inner">
    <div class="footer__brand"><a class="footer__logo" href="/">fieldtone</a><p>Independent audio specialists since 2009.</p></div>
    {footer_v1}
    <form class="footer__newsletter" action="/subscribe" method="post"><label for="nl-email">Get early access to sales</label><input id="nl-email" type="email" name="email" placeholder="Email"><button type="submit">Join</button></form>
  </div>
  <p class="footer__legal">© 2026 Fieldtone Audio LLC · <a href="/privacy">Privacy</a> · <a href="/terms">Terms</a></p>
</footer>
"""
    css_v1 = """
body{margin:0;font:16px/1.5 "Inter",system-ui,sans-serif;color:#141414}
.header__main{display:flex;align-items:center;gap:32px;padding:16px 40px;border-bottom:1px solid #eee}
.main-nav{display:flex;gap:24px;list-style:none;margin:0;padding:0}
.pdp{display:grid;grid-template-columns:1.2fr 1fr;gap:48px;padding:24px 40px}
.gallery__thumbs{display:flex;gap:8px;list-style:none;padding:0}
.gallery__thumb.is-selected{outline:2px solid #141414}
.price__current{font-size:28px;font-weight:700}.price__compare{color:#777}
.swatch-input{position:absolute;opacity:0}.swatch{display:inline-block;width:32px;height:32px;border-radius:50%;background:var(--swatch)}
.btn--primary{background:#141414;color:#fff;padding:14px 28px;border-radius:999px}
.pdp-tabs{display:flex;gap:24px;border-bottom:1px solid #ddd;padding:0 40px}
.visually-hidden{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
"""
    v1 = page(
        title="Halcyon Drift ANC Wireless Over-Ear Headphones – Fieldtone Audio",
        head='<meta name="description" content="Halcyon Drift ANC: adaptive noise cancelling, 38-hour battery, LDAC. Free 2-day shipping.">\n'
             '<link rel="canonical" href="https://www.fieldtone.com/products/halcyon-drift-anc">\n' + S02_JSONLD,
        css=css_v1, body=body_v1, body_attrs=' class="template-product"',
    )

    # ---------------- v2 ----------------
    images_v2 = [("video", "Play video: Drift ANC in 60 seconds")] + S02_IMAGES
    thumbs_v2 = "\n".join(
        f'            <button type="button" role="tab" aria-selected="{"true" if i == 1 else "false"}" '
        f'aria-label="{"Play video: Drift ANC in 60 seconds" if key == "video" else f"Image {i + 1} of 7: {alt}"}" class="{emo("thumb")}"'
        f'{gt("t4") if key == "side" else ""}>'
        f'<img src="https://cdn.fieldtone.com/media/drift-anc/midnight-black-{"video-poster" if key == "video" else key}.jpg?w=160&amp;fm=webp" alt="" class="{emo("thumb-img")}">'
        + (f'<span class="{emo("thumb-play")}">{icon("play", emo("thumb-play-icon"), 16)}</span>' if key == "video" else "")
        + "</button>"
        for i, (key, alt) in enumerate(images_v2)
    )
    swatches_v2 = "".join(
        f'<label class="picker__option" title="{c}"><input type="radio" class="picker__radio" name="Color" value="{c}"'
        f'{" checked" if i == 0 else ""}{gt("t1") if c == "Fjord Blue" else ""}>'
        f'<span class="picker__chip" style="--chip:{hexv}"></span><span class="picker__name">{c}</span>'
        + ('<span class="picker__tag">New</span>' if c == "Moss Green" else "")
        + "</label>"
        for i, (c, hexv) in enumerate(S02_COLORS_V2)
    )
    nav_v2 = "".join(
        f'<li class="{emo("navitem")}"><a href="/shop/{slug(n)}" class="{emo("navlink-active") if n == "Headphones" else emo("navlink")}">{n}</a></li>'
        for n in ["Headphones", "Earbuds", "Speakers", "Turntables", "Hi-Fi", "Accessories", "Gift guide", "Deals"]
    )
    features_v2 = "".join(
        f'<div class="{emo("feature")}"><div class="{emo("feature-icon")}">{icon("check")}</div><div><p class="{emo("feature-title")}">{t}</p><p class="{emo("feature-text")}">{d}</p></div></div>'
        for t, d in S02_FEATURES
    )
    specs_v2 = "".join(
        f'<div class="{emo("spec-row")}"><dt class="{emo("spec-term")}">{k}</dt><dd class="{emo("spec-value")}">{v}</dd></div>'
        for k, v in S02_SPECS
    )

    def review_v2(r: tuple) -> str:
        rid, title, author, stars, iso, label, body, yes, no = r
        return f"""
          <article class="rw-review" data-review-id="r_{rid}">
            <header class="rw-review__header">
              <span class="rw-stars" role="img" aria-label="Rated {stars} out of 5">{"★" * stars}{"☆" * (5 - stars)}</span>
              <h3 class="rw-review__title">{e(title)}</h3>
            </header>
            <div class="rw-review__byline"><strong class="rw-review__author">{author}</strong><span class="rw-chip">{icon("check", "rw-chip__icon", 12)}Verified purchase</span><time class="rw-review__date" datetime="{iso}">{label}</time></div>
            <p class="rw-review__body">{e(body)}</p>
            <footer class="rw-review__footer">
              <span class="rw-review__ask">Helpful?</span>
              <button type="button" class="rw-vote rw-vote--up"{gt("t5") if rid == "88213" else ""}><span>Helpful</span> <span class="rw-vote__count">({yes})</span></button>
              <button type="button" class="rw-vote rw-vote--down"><span>Not helpful</span> <span class="rw-vote__count">({no})</span></button>
            </footer>
          </article>"""

    reviews_sorted = sorted([S02_NEW_REVIEW] + S02_REVIEWS, key=lambda r: r[4], reverse=True)
    reviews_v2 = "".join(review_v2(r) for r in reviews_sorted)
    hist_v2 = "".join(
        f'<li class="rw-hist__row"><button type="button" class="rw-hist__filter">{s} ★</button><span class="rw-hist__track"><span class="rw-hist__fill" style="width:{p}%"></span></span><span class="rw-hist__pct">{p}%</span></li>'
        for s, p in hist
    )
    acc_v2 = "".join(
        f'<li class="{emo("acc-card")}"><img src="https://cdn.fieldtone.com/media/accessories/{slug(n)}.jpg?w=320&amp;fm=webp" alt="" class="{emo("acc-img")}">'
        f'<div class="{emo("acc-body")}"><a href="/products/{slug(n)}" class="{emo("acc-name")}">{e(n)}</a><span class="{emo("acc-price")}">${p}</span></div>'
        f'<button type="button" class="{emo("acc-add")}">Add to cart</button></li>'
        for n, p in S02_ACCESSORIES
    )
    body_v2 = f"""
<div id="__fieldtone">
<div class="{emo("sticky-bar")}" role="region" aria-label="Quick buy" data-visible="false">
  <div class="{emo("sticky-inner")}">
    <img src="https://cdn.fieldtone.com/media/drift-anc/midnight-black-front.jpg?w=96&amp;fm=webp" alt="" class="{emo("sticky-img")}">
    <div class="{emo("sticky-text")}"><p class="{emo("sticky-name")}">Halcyon Drift ANC</p><p class="{emo("sticky-variant")}">Midnight Black · Standard</p></div>
    <span class="{emo("sticky-price")}">$279.00</span>
    <button type="button" id="sticky-add-to-cart" class="{emo("sticky-cta")}">Add to cart</button>
  </div>
</div>
<div class="{emo("promo")}"><p class="{emo("promo-text")}">Holiday returns extended to Jan 31 · Free 2-day shipping</p></div>
<header class="{emo("header")}">
  <div class="{emo("header-row")}">
    <button type="button" class="{emo("burger")}" aria-label="Menu">{icon("menu")}</button>
    <a href="/" class="{emo("logo")}" aria-label="Fieldtone home"><span class="{emo("logo-word")}">fieldtone</span></a>
    <nav aria-label="Primary" class="{emo("nav")}"><ul class="{emo("navlist")}">{nav_v2}</ul></nav>
    <div class="{emo("header-actions")}">
      <form role="search" action="/search" class="{emo("search")}"><input type="search" name="q" placeholder="Search headphones, speakers…" aria-label="Search" class="{emo("search-input")}"></form>
      <a href="/account" class="{emo("icon-btn")}" aria-label="Your account">{icon("user")}</a>
      <a href="/cart" class="{emo("icon-btn")}" aria-label="Cart (0)">{icon("bag")}</a>
    </div>
  </div>
</header>
<main class="{emo("main")}">
  <ol class="{emo("crumbs")}" aria-label="Breadcrumb"><li><a href="/">Home</a></li><li><a href="/shop/headphones">Headphones</a></li><li aria-current="page">Drift ANC</li></ol>
  <div class="{emo("pdp-grid")}">
    <section class="{emo("media")}" aria-label="Product media">
      <div class="{emo("media-layout")}">
        <div class="{emo("thumb-rail")}">
          <div class="{emo("thumb-scroll")}" role="tablist" aria-label="Product images" aria-orientation="vertical">
{thumbs_v2}
          </div>
        </div>
        <div class="{emo("stage")}"><img src="https://cdn.fieldtone.com/media/drift-anc/midnight-black-front.jpg?w=1200&amp;fm=webp" alt="Halcyon Drift ANC in Midnight Black, front view" class="{emo("stage-img")}"></div>
      </div>
    </section>
    <section class="{emo("buybox")}" aria-labelledby="product-title">
      <div class="{emo("title-block")}">
        <p class="{emo("eyebrow")}"><a href="/brands/halcyon">Halcyon</a> · Over-ear</p>
        <h1 id="product-title" class="{emo("title")}">Drift ANC Wireless Headphones</h1>
        <a href="#reviews" class="{emo("rating-link")}"><span aria-hidden="true">★★★★★</span> 4.6 · 1,284 reviews</a>
      </div>
      <div class="{emo("price-block")}">
        <p class="{emo("price-row")}"><span class="{emo("price-now")}"{gt("t3")}>$279.00</span><span class="{emo("price-was")}"><span class="{emo("sr")}">Regular price</span><s>$349.00</s></span><span class="{emo("price-save")}">−20%</span></p>
        <p class="{emo("bnpl")}">Pay in 4 interest-free installments of $69.75 with Splitpay. <a href="/splitpay">Learn more</a></p>
      </div>
      <form action="/cart/add" method="post" class="{emo("form")}" data-product-id="8812004">
        <input type="hidden" name="id" value="44120381">
        <ft-variant-picker option="Color" class="{emo("variant-host")}">
          <template shadowrootmode="open">
            <style>:host{{display:block}}fieldset{{border:0;margin:0;padding:0}}.picker__options{{display:flex;flex-wrap:wrap;gap:10px}}.picker__radio{{position:absolute;opacity:0}}.picker__chip{{display:block;width:36px;height:36px;border-radius:50%;background:var(--chip)}}.picker__name{{font-size:12px}}</style>
            <fieldset class="picker" part="fieldset">
              <legend class="picker__legend">Colour — <span class="picker__selected">Midnight Black</span></legend>
              <div class="picker__options">{swatches_v2}</div>
            </fieldset>
          </template>
        </ft-variant-picker>
        <div class="{emo("edition")}" role="radiogroup" aria-label="Edition">
          <label class="{emo("edition-card")}"><input type="radio" name="edition" value="standard" checked class="{emo("edition-radio")}"><span class="{emo("edition-name")}">Standard</span><span class="{emo("edition-price")}">$279.00</span></label>
          <label class="{emo("edition-card")}"><input type="radio" name="edition" value="travel" class="{emo("edition-radio")}"><span class="{emo("edition-name")}">Travel bundle</span><span class="{emo("edition-price")}">$309.00</span></label>
        </div>
        <div class="{emo("cta-row")}">
          <div class="{emo("qty")}"><button type="button" aria-label="Decrease" class="{emo("qty-btn")}">{icon("minus", "", 16)}</button><input type="text" inputmode="numeric" name="quantity" value="1" aria-label="Quantity" class="{emo("qty-input")}"><button type="button" aria-label="Increase" class="{emo("qty-btn")}">{icon("plus", "", 16)}</button></div>
          <div class="{emo("cta-wrap")}"><button type="submit" id="add-to-cart" name="add" class="{emo("cta-primary")}"{gt("t2")}>Add to cart</button></div>
        </div>
        <button type="button" class="{emo("cta-express")}">Express checkout</button>
        <button type="button" class="{emo("save")}" aria-label="Save to wishlist">{icon("heart")}</button>
      </form>
      <ul class="{emo("perks")}">
        <li class="{emo("perk")}">{icon("truck")}<span>Free 2-day shipping</span></li>
        <li class="{emo("perk")}">{icon("return")}<span>60-night trial</span></li>
        <li class="{emo("perk")}">{icon("shield")}<span>2-year warranty</span></li>
      </ul>
    </section>
  </div>
  <div class="{emo("tabs")}" role="tablist" aria-label="Product details">
    <button type="button" role="tab" aria-selected="true" aria-controls="panel-overview" class="{emo("tab-active")}">Overview</button>
    <button type="button" role="tab" aria-selected="false" aria-controls="reviews" class="{emo("tab")}"{gt("t6")}>Reviews <span class="{emo("tab-count")}">1,284</span></button>
    <button type="button" role="tab" aria-selected="false" aria-controls="panel-specs" class="{emo("tab")}">Tech specs</button>
    <button type="button" role="tab" aria-selected="false" aria-controls="panel-box" class="{emo("tab")}">What's in the box</button>
  </div>
  <section id="panel-overview" role="tabpanel" class="{emo("panel")}">
    <h2 class="{emo("panel-title")}">Quiet, tuned, ready for the long haul</h2>
    <p class="{emo("panel-lead")}">Drift ANC pairs Halcyon's quietest noise cancelling yet with a warm, detailed 40 mm driver and a battery that outlasts a week of commutes.</p>
    <div class="{emo("feature-grid")}">{features_v2}</div>
  </section>
  <section id="panel-specs" role="tabpanel" class="{emo("panel")}" hidden>
    <h2 class="{emo("panel-title")}">Tech specs</h2>
    <dl class="{emo("spec-list")}">{specs_v2}</dl>
  </section>
  <section id="panel-box" role="tabpanel" class="{emo("panel")}" hidden>
    <h2 class="{emo("panel-title")}">What's in the box</h2>
    <ul class="{emo("box")}"><li>Drift ANC headphones</li><li>Slim travel case</li><li>USB-C cable (1 m)</li><li>3.5 mm audio cable (1.2 m)</li></ul>
  </section>
  <section class="{emo("accessories")}" aria-labelledby="acc-heading">
    <h2 id="acc-heading" class="{emo("section-title")}">Complete the setup</h2>
    <ul class="{emo("acc-list")}">{acc_v2}</ul>
  </section>
  <section id="reviews" class="{emo("reviews-slot")}" aria-label="Customer reviews">
    <ft-reviews product="HAL-DRIFT-ANC" locale="en-US">
      <template shadowrootmode="open">
        <style>:host{{display:block;font:15px/1.5 system-ui}}.rw-review{{border-top:1px solid #e5e5e5;padding:20px 0}}.rw-vote{{border:1px solid #ccc;border-radius:999px;padding:4px 12px;background:none}}</style>
        <div class="rw-widget">
          <div class="rw-summary">
            <h2 class="rw-summary__title">Reviews</h2>
            <p class="rw-summary__avg"><span class="rw-summary__score">4.6</span><span class="rw-stars" aria-hidden="true">★★★★★</span><span class="rw-summary__count">1,284 reviews</span></p>
            <ul class="rw-hist">{hist_v2}</ul>
            <button type="button" class="rw-btn rw-btn--primary">Write a review</button>
          </div>
          <div class="rw-toolbar"><label class="rw-toolbar__label" for="rw-sort">Sort</label><select id="rw-sort" class="rw-select"><option selected>Most recent</option><option>Most helpful</option><option>Highest rated</option><option>Lowest rated</option><option>With photos</option></select></div>
          <div class="rw-list">{reviews_v2}
          </div>
          <button type="button" class="rw-btn rw-btn--more">Show more reviews</button>
        </div>
      </template>
    </ft-reviews>
  </section>
</main>
<footer class="{emo("footer")}">
  <div class="{emo("footer-grid")}">
    <div><p class="{emo("footer-logo")}">fieldtone</p><p class="{emo("footer-tag")}">Independent audio specialists since 2009.</p></div>
    <nav aria-label="Support" class="{emo("footer-nav")}"><a href="/help">Help center</a><a href="/orders">Order status</a><a href="/returns">Returns</a><a href="/warranty">Warranty</a><a href="/manuals">Manuals</a></nav>
    <nav aria-label="Company" class="{emo("footer-nav")}"><a href="/about">About</a><a href="/listening-rooms">Listening rooms</a><a href="/careers">Careers</a><a href="/accessibility">Accessibility</a></nav>
    <form action="/subscribe" method="post" class="{emo("footer-form")}"><input type="email" name="email" placeholder="Your email" aria-label="Email" class="{emo("footer-input")}"><button type="submit" class="{emo("footer-submit")}">Sign up</button></form>
  </div>
  <p class="{emo("legal")}">© 2026 Fieldtone Audio LLC · <a href="/privacy">Privacy</a> · <a href="/terms">Terms</a> · <a href="/cookies">Cookie settings</a></p>
</footer>
</div>
"""
    css_v2 = f"""
.{emo("sticky-bar")}{{position:fixed;top:0;left:0;right:0;z-index:50;background:#fff;box-shadow:0 2px 12px rgba(0,0,0,.08);transform:translateY(-100%)}}
.{emo("pdp-grid")}{{display:grid;grid-template-columns:minmax(0,7fr) minmax(0,5fr);gap:56px;padding:24px 48px}}
.{emo("thumb")}{{display:block;width:72px;height:72px;border-radius:12px;overflow:hidden;border:2px solid transparent}}
.{emo("cta-primary")}{{flex:1;background:#111;color:#fff;border-radius:999px;padding:16px 24px;font-weight:600}}
.{emo("price-now")}{{font-size:30px;font-weight:700;letter-spacing:-.01em}}
"""
    v2 = page(
        title="Drift ANC Wireless Headphones | Halcyon | Fieldtone",
        head='<meta name="description" content="Adaptive noise cancelling, 38-hour battery and LDAC hi-res wireless.">\n'
             '<link rel="canonical" href="https://www.fieldtone.com/products/halcyon-drift-anc">\n' + S02_JSONLD,
        css=css_v2, body=body_v2,
    )

    meta = {
        "title": "Product detail page — headphones audio store",
        "mutations": ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change",
                      "copy-change", "tag-change", "attribute-churn", "structure-move", "insertion"],
        "notes": (
            "v2 is a React rebuild styled with Emotion (css-* hashes). A fixed 'Quick buy' bar is injected at the top "
            "of <body> with its own price and 'Add to cart' button; the accessory rail gains 'Add to cart' buttons. "
            "Colour swatches move into <ft-variant-picker>'s shadow root (option names as values, new 'Moss Green' "
            "colour, different order). The gallery thumbnails become a vertical tablist with a video thumbnail "
            "inserted first. Info links become role=tab buttons in a new order, and the reviews move into the "
            "third-party <ft-reviews> shadow root, re-sorted by 'Most recent' with a new review on top and "
            "'Helpful (n)' vote buttons."
        ),
        "targets": [
            target("t1", "'Fjord Blue' colour swatch radio input",
                   "#color-fjord-blue",
                   "//fieldset[@id='color-picker']//input[@value='fjord-blue']",
                   ["shadow-dom", "id-change", "attribute-churn", "sibling-reorder", "insertion", "class-obfuscation"]),
            target("t2", "Main 'Add to cart' button in the product form",
                   "form#product-form button.add-to-cart",
                   "//button[normalize-space()='Add to cart']",
                   ["decoy", "class-obfuscation", "wrapper-divs", "structure-move"]),
            target("t3", "Current price ($279.00) in the buy box",
                   ".pdp-info .price__current",
                   "//div[@class='price']/span[1]",
                   ["class-obfuscation", "decoy", "wrapper-divs", "tag-change"]),
            target("t4", "Gallery thumbnail showing the side-profile image",
                   ".gallery__thumbs li:nth-child(2) > button",
                   "//ul[@class='gallery__thumbs']/li[2]/button",
                   ["insertion", "sibling-reorder", "attribute-churn", "copy-change", "class-obfuscation", "structure-move"]),
            target("t5", "'Yes (23)' helpful-vote button on Marisol K.'s review 'Best noise cancelling under $300'",
                   "#review-88213 .review__helpful",
                   "//li[.//h3[normalize-space()='Best noise cancelling under $300']]//button[starts-with(normalize-space(),'Yes')]",
                   ["shadow-dom", "copy-change", "sibling-reorder", "insertion", "id-change", "tag-change"]),
            target("t6", "'Reviews (1,284)' tab in the product information tabs",
                   ".pdp-tabs a[href='#reviews']",
                   "//nav[@class='pdp-tabs']/a[4]",
                   ["tag-change", "sibling-reorder", "copy-change", "class-obfuscation"]),
        ],
    }
    return v1, v2, meta


# ---------------------------------------------------------------------------
# ecommerce-03 — Hearthstone Kitchen Supply: shopping cart
# ---------------------------------------------------------------------------

# line id, sku, name, option label, option value, unit price, qty, stock note
S03_LINES = [
    ("41823117", "HK-DO55-CER", "Enameled Cast-Iron Dutch Oven, 5.5 qt", "Color", "Cerise", 179.95, 1, "In stock — ships in 1–2 business days"),
    ("41823118", "HK-SK26", "Pre-Seasoned Cast-Iron Skillet, 26 cm", "Size", "26 cm", 44.95, 2, "In stock — ships in 1–2 business days"),
    ("41823119", "HK-BB3", "Bamboo Cutting Board Set (3-Piece)", "Finish", "Natural", 39.00, 1, "Only 4 left"),
    ("41823120", "HK-CK20", "Carbon-Steel Chef Knife, 20 cm", "Handle", "Walnut", 129.00, 1, "In stock — ships in 1–2 business days"),
]
S03_RECS = [("Cast-Iron Handle Sleeve", 12.00), ("Chainmail Scrubber", 18.00), ("Seasoning Oil, 8 oz", 14.00), ("Walnut Knife Block", 79.00)]
S03_SAVED = [("Linen Apron, Slate", 36.00), ("Ceramic Pie Dish, 9 in", 42.00)]


def suite03() -> tuple[str, str, dict]:
    subtotal = sum(p * q for *_x, p, q, _s in S03_LINES)
    n_items = sum(q for *_x, q, _s in S03_LINES)
    sub_s = money(subtotal)
    nav = ["Cookware", "Bakeware", "Cutlery", "Tools & Gadgets", "Tabletop", "Pantry", "Sale"]

    # ---------------- v1 ----------------
    def row_v1(i: int, line: tuple) -> str:
        lid, sku, name, opt, val, price, qty, stock = line
        url = f"/products/{slug(name)}"
        return f"""
          <tr class="cart-item" id="cart-row-{i}" data-line-id="{lid}">
            <td class="cart-item__product">
              <div class="cart-item__media"><img src="/cdn/shop/files/{sku.lower()}_160x160.jpg" alt="{e(name)}" width="80" height="80"></div>
              <div class="cart-item__details">
                <a class="cart-item__name" href="{url}">{e(name)}</a>
                <dl class="cart-item__options"><dt>{opt}:</dt><dd>{e(val)}</dd></dl>
                <p class="cart-item__sku">SKU {sku}</p>
                <p class="cart-item__stock">{e(stock)}</p>
                <div class="cart-item__actions"><a class="remove-link" href="/cart/change?line={i}&amp;quantity=0"{gt("t3") if lid == "41823119" else ""}>Remove</a> <span aria-hidden="true">|</span> <a class="save-link" href="/cart/save?line={i}">Save for later</a></div>
              </div>
            </td>
            <td class="cart-item__price">{money(price)}</td>
            <td class="cart-item__qty">
              <div class="qty-stepper">
                <button type="button" class="qty-minus" aria-label="Decrease quantity for {e(name)}">−</button>
                <input class="qty-input" type="number" name="updates[]" id="updates_{lid}" value="{qty}" min="0" aria-label="Quantity for {e(name)}"{gt("t1") if lid == "41823118" else ""}>
                <button type="button" class="qty-plus" aria-label="Increase quantity for {e(name)}"{gt("t2") if lid == "41823117" else ""}>+</button>
              </div>
            </td>
            <td class="cart-item__total">{money(price * qty)}</td>
          </tr>"""

    rows_v1 = "".join(row_v1(i + 1, line) for i, line in enumerate(S03_LINES))
    recs_v1 = "".join(
        f'<li class="rec"><img class="rec__img" src="/cdn/shop/files/{slug(n)}_240x240.jpg" alt="{e(n)}" width="120" height="120">'
        f'<a class="rec__name" href="/products/{slug(n)}">{e(n)}</a><span class="rec__price">{money(p)}</span>'
        f'<button type="button" class="btn btn--small rec__add">Add</button></li>'
        for n, p in S03_RECS
    )
    nav_v1 = "".join(f'<li class="site-nav__item"><a class="site-nav__link" href="/collections/{slug(n)}">{e(n)}</a></li>' for n in nav)
    body_v1 = f"""
<div class="announcement"><p>Free shipping on orders $99+ · Lifetime warranty on cast iron</p></div>
<header class="site-header">
  <div class="site-header__main container">
    <a class="site-header__logo" href="/">Hearthstone <span class="site-header__logo-sub">Kitchen Supply</span></a>
    <nav class="site-nav" aria-label="Main navigation"><ul class="site-nav__list">{nav_v1}</ul></nav>
    <div class="site-header__actions">
      <a class="site-header__icon" href="/search" aria-label="Search">{icon("search")}</a>
      <a class="site-header__icon" href="/account/login">Sign in</a>
      <a class="site-header__icon site-header__cart is-active" href="/cart" aria-label="Cart, {n_items} items">{icon("cart")}<span class="cart-bubble">{n_items}</span></a>
    </div>
  </div>
</header>
<main id="main" class="cart-page container">
  <div class="cart-page__header">
    <h1 class="cart-page__title">Your cart</h1>
    <a class="cart-page__continue" href="/collections/all">Continue shopping</a>
  </div>
  <div class="free-shipping-meter" role="status">
    <p class="free-shipping-meter__text">{icon("truck", "free-shipping-meter__icon")} You've unlocked <strong>free standard shipping</strong>!</p>
    <div class="free-shipping-meter__bar"><span class="free-shipping-meter__fill" style="width:100%"></span></div>
  </div>
  <div class="cart-layout">
    <form class="cart-form" id="cart-form" action="/cart" method="post">
      <table class="cart-items" id="cart">
        <caption class="visually-hidden">Items in your cart</caption>
        <thead><tr><th scope="col">Product</th><th scope="col">Price</th><th scope="col">Quantity</th><th scope="col">Total</th></tr></thead>
        <tbody>{rows_v1}
        </tbody>
      </table>
      <div class="cart-extras">
        <div class="cart-extras__gift"><input type="checkbox" id="gift-order" name="attributes[gift]" value="yes"><label for="gift-order">This order is a gift — hide prices on the packing slip</label></div>
        <div class="cart-extras__note"><label for="cart-note">Order note</label><textarea id="cart-note" name="note" rows="3" placeholder="Anything we should know about your order?"></textarea></div>
        <button type="submit" class="btn btn--link cart-form__update" name="update">Update cart</button>
      </div>
    </form>
    <aside class="order-summary" aria-labelledby="summary-title">
      <h2 class="order-summary__title" id="summary-title">Order summary</h2>
      <form class="promo-form" action="/discount" method="post">
        <label class="promo-form__label" for="promo-code">Promo code</label>
        <input id="promo-code" class="promo-form__input" type="text" name="discount" placeholder="Enter promo code" autocomplete="off"{gt("t4")}>
        <button type="submit" class="btn btn--outline promo-form__apply"{gt("t5")}>Apply</button>
      </form>
      <dl class="summary">
        <dt>Subtotal ({n_items} items)</dt><dd>{sub_s}</dd>
        <dt>Shipping</dt><dd>Free</dd>
        <dt>Estimated tax</dt><dd>Calculated at checkout</dd>
        <dt class="summary__total-label">Estimated total</dt><dd class="summary-total"{gt("t6")}>{sub_s}</dd>
      </dl>
      <a class="btn btn--primary btn--block checkout-btn" href="/checkout">Checkout</a>
      <p class="order-summary__or">or check out with</p>
      <div class="express-checkout"><button type="button" class="express-btn express-btn--wallet">Pay with Wallet</button><button type="button" class="express-btn express-btn--later">Pay in 4</button></div>
      <ul class="payment-icons" aria-label="Payment methods we accept"><li>Visa</li><li>Mastercard</li><li>American Express</li><li>Discover</li></ul>
      <p class="order-summary__guarantee">{icon("shield", "order-summary__icon")} 90-day returns · Lifetime warranty on cast iron</p>
    </aside>
  </div>
  <section class="recommendations" aria-labelledby="recs-title">
    <h2 class="recommendations__title" id="recs-title">Complete your kitchen</h2>
    <ul class="recommendations__list">{recs_v1}</ul>
  </section>
</main>
<footer class="site-footer">
  <div class="site-footer__grid container">
    <div class="site-footer__col"><h2>Customer care</h2><ul><li><a href="/pages/contact">Contact us</a></li><li><a href="/pages/shipping">Shipping</a></li><li><a href="/pages/returns">Returns</a></li><li><a href="/pages/warranty">Warranty</a></li><li><a href="/pages/care-guides">Care guides</a></li></ul></div>
    <div class="site-footer__col"><h2>About</h2><ul><li><a href="/pages/our-story">Our story</a></li><li><a href="/pages/foundry">The foundry</a></li><li><a href="/blogs/recipes">Recipes</a></li><li><a href="/pages/wholesale">Wholesale</a></li></ul></div>
    <div class="site-footer__col"><h2>Visit</h2><p>412 Foundry Row, Asheville, NC 28801</p><p>Mon–Sat 10am–6pm</p><p><a href="tel:+18005550142">1-800-555-0142</a></p></div>
  </div>
  <p class="site-footer__legal">© 2026 Hearthstone Kitchen Supply · <a href="/policies/privacy-policy">Privacy policy</a> · <a href="/policies/terms-of-service">Terms of service</a></p>
</footer>
"""
    css_v1 = """
body{margin:0;font:16px/1.5 Georgia,"Times New Roman",serif;color:#2b2622;background:#fbf8f4}
.container{max-width:1180px;margin:0 auto;padding:0 24px}
.cart-layout{display:grid;grid-template-columns:1fr 360px;gap:40px}
.cart-items{width:100%;border-collapse:collapse}.cart-items th{text-align:left;border-bottom:1px solid #ddd2c4}
.qty-stepper{display:inline-flex;border:1px solid #c9bba8;border-radius:4px}.qty-input{width:48px;text-align:center}
.order-summary{background:#fff;border:1px solid #e8dfd3;padding:24px;border-radius:8px}
.summary{display:grid;grid-template-columns:1fr auto;gap:8px}.summary-total{font-weight:700;font-size:20px}
.checkout-btn{display:block;background:#8c2f1b;color:#fff;text-align:center;padding:14px;border-radius:4px}
.visually-hidden{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
"""
    v1 = page(title="Your Shopping Cart – Hearthstone Kitchen Supply", css=css_v1, body=body_v1,
              body_attrs=' class="template-cart"')

    # ---------------- v2 ----------------
    def line_v2(line: tuple) -> str:
        lid, sku, name, opt, val, price, qty, stock = line
        url = f"/products/{slug(name)}"
        plan = ""
        if lid == "41823117":
            plan = (f'\n            <div class="{cm("ProtectionPlan", "root")}"><input type="checkbox" id="plan-{lid}" class="{cm("ProtectionPlan", "check")}">'
                    f'<label for="plan-{lid}" class="{cm("ProtectionPlan", "label")}">Add 3-year accident protection for $14.99</label></div>')
        return f"""
        <li class="{cm("CartLine", "root")}" data-key="{lid}:{_h(sku, 8, _B36)}">
          <a href="{url}" class="{cm("CartLine", "media")}" tabindex="-1"><img src="https://cdn.hearthstonekitchen.com/products/{sku.lower()}.jpg?width=200" alt="" class="{cm("CartLine", "image")}"></a>
          <div class="{cm("CartLine", "body")}">
            <div class="{cm("CartLine", "header")}">
              <div class="{cm("CartLine", "info")}">
                <a href="{url}" class="{cm("CartLine", "title")}">{e(name)}</a>
                <p class="{cm("CartLine", "variant")}">{e(val)}</p>
                <p class="{cm("CartLine", "stock")}">{e(stock)}</p>
              </div>
              <div class="{cm("CartLine", "prices")}"><span class="{cm("CartLine", "lineTotal")}">{money(price * qty)}</span><span class="{cm("CartLine", "unit")}">{money(price)} each</span></div>
            </div>
            <div class="{cm("CartLine", "controls")}">
              <div class="{cm("CartLine", "qty")}">
                <div class="{cm("QuantitySelector", "root")}" role="group" aria-label="Quantity">
                  <button type="button" class="{cm("QuantitySelector", "button")}" aria-label="Remove one {e(name)}">{icon("minus", cm("QuantitySelector", "icon"), 16)}</button>
                  <input type="text" inputmode="numeric" pattern="[0-9]*" name="quantity" id=":r{_h(lid, 2, _B36)}:" value="{qty}" aria-label="Quantity, {e(name)}" class="{cm("QuantitySelector", "input")}"{gt("t1") if lid == "41823118" else ""}>
                  <button type="button" class="{cm("QuantitySelector", "button")}" aria-label="Add one {e(name)}"{gt("t2") if lid == "41823117" else ""}>{icon("plus", cm("QuantitySelector", "icon"), 16)}</button>
                </div>
              </div>
              <button type="button" class="{cm("CartLine", "action")}">Save for later</button>
              <button type="button" class="{cm("CartLine", "action")}"{gt("t3") if lid == "41823119" else ""}>{icon("trash", cm("CartLine", "actionIcon"), 16)}Remove</button>
            </div>{plan}
          </div>
        </li>"""

    order_v2 = ["41823120", "41823119", "41823117", "41823118"]
    by_id = {line[0]: line for line in S03_LINES}
    lines_v2 = "".join(line_v2(by_id[i]) for i in order_v2)
    saved_v2 = "".join(
        f'<li class="{cm("SavedItem", "root")}"><img src="https://cdn.hearthstonekitchen.com/products/{slug(n)}.jpg?width=160" alt="" class="{cm("SavedItem", "image")}">'
        f'<div class="{cm("SavedItem", "info")}"><a href="/products/{slug(n)}" class="{cm("SavedItem", "title")}">{e(n)}</a><span class="{cm("SavedItem", "price")}">{money(p)}</span></div>'
        f'<div class="{cm("SavedItem", "actions")}"><button type="button" class="{cm("SavedItem", "move")}">Move to cart</button>'
        f'<button type="button" class="{cm("CartLine", "action")}">{icon("trash", cm("CartLine", "actionIcon"), 16)}Remove</button></div></li>'
        for n, p in S03_SAVED
    )
    recs_v2 = "".join(
        f'<div class="{cm("ProductTile", "root")}"><img src="https://cdn.hearthstonekitchen.com/products/{slug(n)}.jpg?width=240" alt="" class="{cm("ProductTile", "image")}">'
        f'<a href="/products/{slug(n)}" class="{cm("ProductTile", "title")}">{e(n)}</a><span class="{cm("ProductTile", "price")}">{money(p)}</span>'
        f'<button type="button" class="{cm("ProductTile", "add")}">Add to cart</button></div>'
        for n, p in S03_RECS
    )
    nav_v2 = "".join(f'<a href="/shop/{slug(n)}" class="{cm("Header", "navLink")}">{e(n)}</a>' for n in ["Shop all", "Cookware", "Cutlery", "Bakeware", "Tools & Gadgets", "Tabletop", "Pantry", "Sale"])
    body_v2 = f"""
<div id="__next">
<div class="{cm("Announcement", "root")}"><p class="{cm("Announcement", "text")}">Free shipping on orders $99+ · Lifetime warranty on cast iron</p></div>
<header class="{cm("Header", "root")}">
  <div class="{cm("Header", "inner")}">
    <a href="/" class="{cm("Header", "logo")}" aria-label="Hearthstone Kitchen Supply">{icon("leaf", cm("Header", "logoMark"), 28)}<span class="{cm("Header", "wordmark")}">Hearthstone</span></a>
    <nav aria-label="Shop" class="{cm("Header", "nav")}">{nav_v2}</nav>
    <div class="{cm("Header", "actions")}">
      <button type="button" class="{cm("Header", "iconButton")}" aria-label="Open search">{icon("search")}</button>
      <a href="/account" class="{cm("Header", "iconButton")}" aria-label="Account">{icon("user")}</a>
      <a href="/cart" class="{cm("Header", "iconButton")}" aria-label="Cart ({n_items})" aria-current="page">{icon("cart")}<span class="{cm("Header", "badge")}">{n_items}</span></a>
    </div>
  </div>
</header>
<main class="{cm("CartPage", "root")}">
  <div class="{cm("CartPage", "heading")}">
    <h1 class="{cm("CartPage", "title")}">Cart <span class="{cm("CartPage", "count")}">({n_items})</span></h1>
    <p class="{cm("CartPage", "note")}">Items in your cart are not reserved. <a href="/shop">Keep shopping</a></p>
  </div>
  <div class="{cm("CartPage", "grid")}">
    <div class="{cm("CartPage", "main")}">
      <div class="{cm("ShippingMeter", "root")}" role="status"><span class="{cm("ShippingMeter", "label")}">{icon("truck", cm("ShippingMeter", "icon"))}Free standard shipping unlocked</span><span class="{cm("ShippingMeter", "track")}"><span class="{cm("ShippingMeter", "fill")}"></span></span></div>
      <section aria-label="Cart items" class="{cm("CartLines", "root")}">
        <ul class="{cm("CartLines", "list")}">{lines_v2}
        </ul>
      </section>
      <section aria-labelledby="saved-heading" class="{cm("SavedForLater", "root")}">
        <h2 id="saved-heading" class="{cm("SavedForLater", "title")}">Saved for later ({len(S03_SAVED)})</h2>
        <ul class="{cm("SavedForLater", "list")}">{saved_v2}</ul>
      </section>
      <div class="{cm("CartOptions", "root")}">
        <label class="{cm("CartOptions", "gift")}"><input type="checkbox" name="gift" class="{cm("CartOptions", "check")}"> Send as a gift (no prices on the packing slip)</label>
        <label class="{cm("CartOptions", "noteLabel")}" for="order-note">Add a note to your order</label>
        <textarea id="order-note" name="note" rows="2" class="{cm("CartOptions", "note")}"></textarea>
      </div>
    </div>
    <div class="{cm("CartPage", "aside")}">
      <div class="{cm("CartPage", "sticky")}">
        <hs-order-summary currency="USD" item-count="{n_items}">
          <template shadowrootmode="open">
            <style>:host{{display:block;background:#fff;border-radius:16px;padding:24px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}.row{{display:flex;justify-content:space-between;padding:6px 0}}.total{{display:flex;justify-content:space-between;font-weight:700;font-size:1.25rem;border-top:1px solid #eee;padding-top:12px}}.sr{{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}}</style>
            <section class="summary" aria-labelledby="os-title">
              <h2 id="os-title" class="summary__title">Summary</h2>
              <div class="summary__rows">
                <div class="row"><span>Subtotal · {n_items} items</span><span>{sub_s}</span></div>
                <div class="row"><span>Shipping</span><span>Free</span></div>
                <div class="row"><span>Tax</span><span>Calculated at checkout</span></div>
              </div>
              <details class="codes" open>
                <summary class="codes__toggle">Gift card or promo code</summary>
                <form class="code-form" data-kind="gift-card" action="/cart/gift-card" method="post">
                  <label class="sr" for="gc-number">Gift card number</label>
                  <input id="gc-number" class="code-form__input" type="text" name="giftCard" placeholder="Gift card number" autocomplete="off">
                  <button type="submit" class="code-form__button">Apply</button>
                </form>
                <form class="code-form" data-kind="discount" action="/cart/discount" method="post">
                  <label class="sr" for=":r9:">Promo code</label>
                  <div class="code-form__field"><input id=":r9:" class="code-form__input" type="text" name="discountCode" placeholder="Promo code" autocomplete="off" spellcheck="false"{gt("t4")}></div>
                  <button type="submit" class="code-form__button"{gt("t5")}>Apply</button>
                </form>
              </details>
              <div class="total"><span class="total__label">Estimated total</span><span class="total__value"{gt("t6")}>{sub_s}</span></div>
              <a class="checkout" href="/checkouts/new">Check out securely</a>
              <div class="express"><button type="button" class="express__btn">Wallet Pay</button><button type="button" class="express__btn">Pay in 4</button></div>
              <p class="fineprint">90-day returns · Lifetime warranty on cast iron</p>
            </section>
          </template>
        </hs-order-summary>
      </div>
    </div>
  </div>
  <section class="{cm("Recommendations", "root")}" aria-labelledby="recs-heading">
    <h2 id="recs-heading" class="{cm("Recommendations", "title")}">Customers also bought</h2>
    <div class="{cm("Recommendations", "rail")}">{recs_v2}</div>
  </section>
</main>
<div class="{cm("MobileCheckoutBar", "root")}" aria-hidden="false">
  <div class="{cm("MobileCheckoutBar", "summary")}"><span class="{cm("MobileCheckoutBar", "label")}">Estimated total</span><span class="{cm("MobileCheckoutBar", "value")}">{sub_s}</span></div>
  <a href="/checkouts/new" class="{cm("MobileCheckoutBar", "cta")}">Check out</a>
</div>
<footer class="{cm("Footer", "root")}">
  <div class="{cm("Footer", "grid")}">
    <nav aria-label="Help" class="{cm("Footer", "col")}"><h2 class="{cm("Footer", "heading")}">Help</h2><a href="/help/contact">Contact</a><a href="/help/shipping">Shipping</a><a href="/help/returns">Returns</a><a href="/help/warranty">Warranty</a></nav>
    <nav aria-label="Company" class="{cm("Footer", "col")}"><h2 class="{cm("Footer", "heading")}">Company</h2><a href="/about">Our story</a><a href="/foundry">The foundry</a><a href="/recipes">Recipes</a><a href="/wholesale">Wholesale</a></nav>
    <div class="{cm("Footer", "col")}"><h2 class="{cm("Footer", "heading")}">Visit</h2><p>412 Foundry Row, Asheville, NC 28801</p><p><a href="tel:+18005550142">1-800-555-0142</a></p></div>
  </div>
  <p class="{cm("Footer", "legal")}">© 2026 Hearthstone Kitchen Supply · <a href="/privacy">Privacy</a> · <a href="/terms">Terms</a></p>
</footer>
</div>
"""
    css_v2 = f"""
.{cm("CartPage", "grid")}{{display:grid;grid-template-columns:minmax(0,1fr) 380px;gap:48px}}
.{cm("CartLine", "root")}{{display:grid;grid-template-columns:96px 1fr;gap:16px;padding:20px 0;border-bottom:1px solid #eee5da}}
.{cm("QuantitySelector", "root")}{{display:inline-flex;align-items:center;border:1px solid #d9cfc2;border-radius:999px}}
.{cm("MobileCheckoutBar", "root")}{{position:fixed;bottom:0;left:0;right:0;display:none}}
@media (max-width:768px){{.{cm("MobileCheckoutBar", "root")}{{display:flex}}}}
"""
    v2 = page(title="Cart (5) | Hearthstone Kitchen Supply", css=css_v2, body=body_v2)

    meta = {
        "title": "Shopping cart — cast-iron & kitchenware store",
        "mutations": ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change",
                      "copy-change", "tag-change", "attribute-churn", "structure-move", "insertion"],
        "notes": (
            "v2 is a Next.js rebuild with CSS-modules hashes. The cart <table> becomes a <ul> of CartLine cards, "
            "ordered most-recently-added first; quantity steppers become a QuantitySelector with text inputs, new "
            "React ids and reworded aria-labels; 'Remove' links become icon+text buttons. A 'Saved for later' list "
            "(more 'Remove' buttons), a protection-plan upsell and a mobile checkout bar repeating the estimated total "
            "are added. The order summary moves into <hs-order-summary>'s shadow root, where a gift-card form with its "
            "own 'Apply' button now precedes the promo-code form and the subtotal shows the same amount as the total."
        ),
        "targets": [
            target("t1", "Quantity input of the 'Pre-Seasoned Cast-Iron Skillet, 26 cm' line item",
                   "table.cart-items tbody tr:nth-child(2) input.qty-input",
                   "//table[@id='cart']/tbody/tr[2]//input[@name='updates[]']",
                   ["tag-change", "class-obfuscation", "sibling-reorder", "id-change", "attribute-churn", "copy-change", "wrapper-divs"]),
            target("t2", "Increase-quantity (+) button of the 'Enameled Cast-Iron Dutch Oven, 5.5 qt' line",
                   "tr[data-line-id='41823117'] .qty-plus",
                   "//button[@aria-label='Increase quantity for Enameled Cast-Iron Dutch Oven, 5.5 qt']",
                   ["attribute-churn", "copy-change", "class-obfuscation", "sibling-reorder", "wrapper-divs"]),
            target("t3", "'Remove' action of the 'Bamboo Cutting Board Set (3-Piece)' line",
                   "#cart-row-3 a.remove-link",
                   "//tr[contains(.,'Bamboo Cutting Board Set')]//a[normalize-space()='Remove']",
                   ["tag-change", "decoy", "sibling-reorder", "class-obfuscation", "id-change"]),
            target("t4", "Promo code text input in the order summary",
                   "#promo-code",
                   "//form[@class='promo-form']/input[@name='discount']",
                   ["shadow-dom", "id-change", "attribute-churn", "copy-change", "structure-move", "wrapper-divs", "class-obfuscation"]),
            target("t5", "'Apply' button of the promo code form",
                   ".promo-form button[type='submit']",
                   "//button[normalize-space()='Apply']",
                   ["shadow-dom", "decoy", "class-obfuscation", "insertion"]),
            target("t6", "Estimated total amount in the order summary",
                   ".order-summary dd.summary-total",
                   "//dl[@class='summary']/dd[last()]",
                   ["shadow-dom", "tag-change", "decoy", "class-obfuscation"]),
        ],
    }
    return v1, v2, meta


# ---------------------------------------------------------------------------
# ecommerce-04 — Tailwag Pet Supply: checkout review & place order
# ---------------------------------------------------------------------------

# name, unit price, qty, note, image key
S04_ITEMS = [
    ("Grain-Free Salmon & Sweet Potato Dry Dog Food, 24 lb", 64.99, 1, "Autoship every 4 weeks", "salmon-kibble-24lb"),
    ("Orthopedic Memory Foam Dog Bed, Large – Charcoal", 89.99, 1, "Ships separately", "ortho-bed-l-charcoal"),
    ("Dental Chew Sticks, 30 count", 18.49, 2, "", "dental-sticks-30"),
    ("Reflective No-Pull Harness, Medium – Coral", 24.99, 1, "", "harness-m-coral"),
]
# key, v1 label, v2 label, eta, price, v1 value, v2 value
S04_RATES = [
    ("standard", "Standard (5–7 business days)", "Standard · 5–7 business days", "Arrives Thu, Nov 12 – Mon, Nov 16", "Free", "standard", "USPS_GROUND"),
    ("expedited", "Expedited (2–3 business days)", "Express · 2–3 business days", "Arrives Mon, Nov 9 – Tue, Nov 10", "$9.99", "expedited", "UPS_2DAY"),
    ("nextday", "Next business day", "Next day · order by 3 PM", "Arrives Fri, Nov 6", "$24.99", "next_day", "UPS_NDA"),
]


def suite04() -> tuple[str, str, dict]:
    subtotal = sum(p * q for _n, p, q, _note, _img in S04_ITEMS)
    n_items = sum(q for _n, _p, q, _note, _img in S04_ITEMS)
    total_s = money(subtotal)

    # ---------------- v1 ----------------
    rates_v1 = "\n".join(
        f'          <div class="shipping-option{" is-selected" if key == "standard" else ""}">'
        f'<input type="radio" name="shipping_method" id="ship-{key}" value="{v1val}"{" checked" if key == "standard" else ""}{gt("t1") if key == "expedited" else ""}>'
        f'<label for="ship-{key}"><span class="shipping-option__name">{label1}</span><span class="shipping-option__eta">{eta}</span>'
        f'<span class="shipping-option__price">{price}</span></label></div>'
        for key, label1, _l2, eta, price, v1val, _v2 in S04_RATES
    )
    items_v1 = "\n".join(
        f'          <li class="review-item"><img class="review-item__img" src="/assets/products/{img}_120.jpg" alt="" width="60" height="60">'
        f'<div class="review-item__info"><p class="review-item__name">{e(n)}</p><p class="review-item__meta">Qty {q}{" · " + note if note else ""}</p>'
        f'<p class="review-item__seller">Sold &amp; shipped by Tailwag · Item #{_h(img, 6, "0123456789")}</p></div>'
        f'<p class="review-item__price">{money(p * q)}</p></li>'
        for n, p, q, note, img in S04_ITEMS
    )
    body_v1 = f"""
<header class="checkout-header">
  <div class="checkout-header__inner">
    <a class="checkout-header__logo" href="/">{icon("heart", "checkout-header__mark", 28)}<span>Tailwag</span></a>
    <p class="checkout-header__secure">{icon("lock", "checkout-header__lock", 16)} Secure checkout</p>
    <a class="checkout-header__help" href="/help/chat">{icon("phone", "checkout-header__help-icon", 16)}Questions? Chat with us</a>
  </div>
</header>
<main class="checkout">
  <ol class="checkout-steps" aria-label="Checkout progress">
    <li class="checkout-steps__step is-complete">{icon("check", "checkout-steps__icon", 14)}<a href="/checkout/shipping">1. Shipping</a></li>
    <li class="checkout-steps__step is-complete">{icon("check", "checkout-steps__icon", 14)}<a href="/checkout/payment">2. Payment</a></li>
    <li class="checkout-steps__step is-current" aria-current="step">3. Review</li>
  </ol>
  <form id="checkout-form" class="checkout-grid" action="/checkout/place-order" method="post">
    <div class="checkout-main">
      <h1 class="checkout-title">Review your order</h1>
      <section class="review-section review-section--shipping" aria-labelledby="ship-addr-title">
        <div class="review-section__header"><h2 class="review-section__title" id="ship-addr-title">Shipping address</h2><a class="edit-link" href="/checkout/shipping"{gt("t4")}>Edit</a></div>
        <address class="review-section__body">Jordan Alvarez<br>2187 Larkspur Lane, Apt 4B<br>Portland, OR 97214<br>(503) 555-0187</address>
      </section>
      <section class="review-section review-section--payment" aria-labelledby="payment-title">
        <div class="review-section__header"><h2 class="review-section__title" id="payment-title">Payment method</h2><a class="edit-link" href="/checkout/payment">Edit</a></div>
        <div class="review-section__body"><p>Visa ending in 4242 · Expires 08/28</p><p>Billing address: Same as shipping address</p></div>
      </section>
      <section class="review-section review-section--delivery" aria-labelledby="ship-method-title">
        <div class="review-section__header"><h2 class="review-section__title" id="ship-method-title">Shipping method</h2></div>
        <fieldset class="shipping-options">
          <legend class="visually-hidden">Choose a shipping method</legend>
{rates_v1}
        </fieldset>
        <p class="review-section__hint">{icon("info", "review-section__hint-icon", 16)} Orders placed after 3 PM PT ship the next business day.</p>
      </section>
      <section class="review-section review-section--items" aria-labelledby="items-title">
        <div class="review-section__header"><h2 class="review-section__title" id="items-title">Items ({n_items})</h2><a class="edit-link" href="/cart">Edit cart</a></div>
        <ul class="review-items">
{items_v1}
        </ul>
        <p class="review-section__delivery">{icon("truck", "review-section__hint-icon", 16)} Estimated delivery: <strong>Thu, Nov 12 – Mon, Nov 16</strong> with Standard shipping</p>
      </section>
      <section class="review-section review-section--gift" aria-labelledby="gift-title">
        <h2 class="review-section__title" id="gift-title">Gift options</h2>
        <div class="gift-option"><input type="checkbox" id="is-gift" name="is_gift" value="1"><label for="is-gift">This order contains a gift — hide prices on the packing slip</label></div>
        <div class="gift-option gift-option--message" hidden><label for="gift-message">Gift message</label><input type="text" id="gift-message" name="gift_message" maxlength="120" placeholder="Happy Gotcha Day, Biscuit!"></div>
      </section>
      <section class="review-section review-section--notes" aria-labelledby="notes-title">
        <h2 class="review-section__title" id="notes-title">Order notes <span class="optional">(optional)</span></h2>
        <label class="visually-hidden" for="order-notes">Delivery instructions</label>
        <textarea id="order-notes" name="order_note" rows="3" maxlength="250" placeholder="Delivery instructions, e.g. leave with the front desk"{gt("t6")}></textarea>
      </section>
    </div>
    <aside class="checkout-summary" aria-labelledby="summary-title">
      <h2 class="checkout-summary__title" id="summary-title">Order summary</h2>
      <details class="promo">
        <summary class="promo__toggle">Have a promo code?</summary>
        <div class="promo__body"><label class="visually-hidden" for="promo-input">Promo code</label><input type="text" id="promo-input" name="promo" placeholder="Promo code"><button type="button" class="promo__apply">Apply</button></div>
      </details>
      <table class="summary-table">
        <tbody>
          <tr><th scope="row">Subtotal ({n_items} items)</th><td>{total_s}</td></tr>
          <tr><th scope="row">Shipping</th><td>Free</td></tr>
          <tr><th scope="row">Estimated tax</th><td>$0.00</td></tr>
          <tr class="total-row"><th scope="row">Order total</th><td id="order-total"{gt("t5")}>{total_s}</td></tr>
        </tbody>
      </table>
      <div class="terms-check"><input type="checkbox" id="accept-terms" name="terms" value="1" required data-qa="terms-checkbox"{gt("t3")}><label for="accept-terms">I agree to the <a href="/terms">Terms &amp; Conditions</a> and <a href="/returns">Return Policy</a></label></div>
      <button type="submit" class="btn-place-order" id="place-order-btn" data-qa="place-order-button"{gt("t2")}>Place order</button>
      <p class="checkout-summary__fine">By placing your order you'll be charged {total_s} to your Visa ending in 4242.</p>
      <a class="checkout-summary__back" href="/checkout/payment">‹ Return to payment</a>
      <div class="checkout-summary__rewards">{icon("gift", "checkout-summary__rewards-icon", 18)} You'll earn <strong>216 Wag Points</strong> with this order.</div>
      <ul class="trust-badges"><li>{icon("lock", "", 16)} 256-bit SSL encryption</li><li>{icon("return", "", 16)} 365-day returns</li><li>{icon("phone", "", 16)} 24/7 vet-tech support</li></ul>
      <div class="order-help">
        <h3 class="order-help__title">Order help</h3>
        <details class="order-help__item"><summary>When will I be charged?</summary><p>Your card is authorized now and charged when your order ships. Autoship items are charged on each delivery.</p></details>
        <details class="order-help__item"><summary>Can I change my Autoship schedule?</summary><p>Yes — skip, delay or cancel any time from <a href="/account/autoship">My Autoship</a>.</p></details>
        <details class="order-help__item"><summary>What is your return policy?</summary><p>Not the right fit? Return most items within 365 days. <a href="/returns">See details</a>.</p></details>
      </div>
    </aside>
  </form>
</main>
<footer class="checkout-footer">
  <ul class="checkout-footer__links"><li><a href="/privacy">Privacy policy</a></li><li><a href="/terms">Terms of use</a></li><li><a href="/returns">Return policy</a></li><li><a href="/shipping">Shipping policy</a></li><li><a href="/accessibility">Accessibility</a></li></ul>
  <p class="checkout-footer__help">Need help? Call <a href="tel:+18885550199">1-888-555-0199</a> — our pet care team is available 24/7.</p>
  <ul class="checkout-footer__payments" aria-label="Accepted payment methods"><li class="pay-badge pay-badge--visa">Visa</li><li class="pay-badge pay-badge--mc">Mastercard</li><li class="pay-badge pay-badge--amex">American Express</li><li class="pay-badge pay-badge--discover">Discover</li><li class="pay-badge pay-badge--wallet">Wallet Pay</li><li class="pay-badge pay-badge--gift">Tailwag Gift Card</li></ul>
  <p class="checkout-footer__copy">© 2026 Tailwag Pet Supply, Inc. · Pharmacy services provided by Tailwag Pharmacy, LLC.</p>
</footer>
"""
    css_v1 = """
body{margin:0;font:15px/1.5 "Nunito Sans",Arial,sans-serif;color:#23303a;background:#f6f8f9}
.checkout-header__inner{display:flex;justify-content:space-between;align-items:center;padding:14px 32px;background:#fff;border-bottom:1px solid #e1e7eb}
.checkout-steps{display:flex;gap:24px;list-style:none;padding:16px 32px;margin:0}.checkout-steps__step.is-current{font-weight:700;color:#0d6e6e}
.checkout-grid{display:grid;grid-template-columns:1fr 380px;gap:32px;padding:0 32px}
.review-section{background:#fff;border-radius:8px;padding:20px;margin-bottom:16px}
.shipping-option{display:flex;gap:12px;padding:12px;border:1px solid #d6dee3;border-radius:6px;margin-bottom:8px}
.btn-place-order{width:100%;padding:16px;border:0;border-radius:6px;background:#f2a900;font-weight:800;font-size:17px}
.visually-hidden{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
"""
    v1 = page(title="Checkout – Review your order | Tailwag", css=css_v1, body=body_v1, body_attrs=' class="checkout-page"')

    # ---------------- v2 ----------------
    rates_order_v2 = ["nextday", "expedited", "standard"]
    by_key = {r[0]: r for r in S04_RATES}
    rates_v2 = "".join(
        f'<label class="rate{" rate--selected" if key == "standard" else ""}">'
        f'<input class="rate__radio" type="radio" name="shippingRateHandle" id=":r{i + 3}:" value="{v2val}"{" checked" if key == "standard" else ""}{gt("t1") if key == "expedited" else ""}>'
        f'<span class="rate__text"><span class="rate__title">{label2}</span><span class="rate__eta">{eta}</span></span>'
        f'<span class="rate__price">{price}</span></label>'
        for i, (key, _l1, label2, eta, price, _v1, v2val) in enumerate(by_key[k] for k in rates_order_v2)
    )
    items_v2 = "".join(
        f'<li class="{sc("LineItem")}"><div class="{sc("Thumb")}"><img src="https://img.tailwag.com/catalog/{img}.webp?w=96" alt="" class="{sc("ThumbImg")}">'
        f'<span class="{sc("QtyBubble")}">{q}</span></div><div class="{sc("LineInfo")}"><p class="{sc("LineName")}">{e(n)}</p>'
        + (f'<p class="{sc("LineNote")}">{e(note)}</p>' if note else "")
        + f'<p class="{sc("LineSeller")}">Ships from Tailwag · #{_h(img, 6, "0123456789")}</p>'
        + f'</div><span class="{sc("LinePrice")}">{money(p * q)}</span></li>'
        for n, p, q, note, img in S04_ITEMS
    )

    def block(title: str, body: str, change_href: str | None, aria: str, tid: str | None = None, extra: str = "") -> str:
        change = (f'<a href="{change_href}" class="{sc("ChangeLink")}" aria-label="{aria}"{gt(tid)}>Change</a>'
                  if change_href else "")
        return f"""
        <section class="{sc("ReviewBlock")}">
          <div class="{sc("ReviewBlockHead")}"><h2 class="{sc("ReviewBlockTitle")}">{title}</h2>{change}</div>
          <div class="{sc("ReviewBlockBody")}">{body}</div>{extra}
        </section>"""

    blocks_v2 = (
        block("Contact", '<p>jordan.alvarez@example.com</p><p>Order updates by text to (503) 555-0187</p>', "/checkout/contact", "Change contact information")
        + block("Ship to", "<p>Jordan Alvarez, 2187 Larkspur Lane, Apt 4B, Portland, OR 97214</p>", "/checkout/shipping", "Change shipping address", "t4")
        + block("Delivery method", f"""
            <tw-shipping-rates country="US" postal-code="97214">
              <template shadowrootmode="open">
                <style>:host{{display:block}}.rates{{display:grid;gap:8px}}.rate{{display:grid;grid-template-columns:auto 1fr auto;gap:12px;align-items:center;padding:14px 16px;border:1px solid #cfd8dc;border-radius:10px}}.rate--selected{{border-color:#0d6e6e;box-shadow:0 0 0 1px #0d6e6e}}</style>
                <div class="rates" role="radiogroup" aria-label="Delivery method">{rates_v2}</div>
                <p class="rates__note">Cut-off for same-day dispatch is 3 PM PT.</p>
              </template>
            </tw-shipping-rates>""", None, "")
        + block("Payment", '<p>Visa •••• 4242 · exp 08/28</p><p>Billing address same as shipping</p>', "/checkout/payment", "Change payment method")
    )
    body_v2 = f"""
<div id="root">
<header class="{sc("CheckoutHeader")}">
  <a href="/" class="{sc("Brand")}" aria-label="Tailwag home">{icon("heart", sc("BrandMark"), 28)}<span class="{sc("BrandName")}">tailwag</span></a>
  <div class="{sc("HeaderRight")}"><span class="{sc("Secure")}">{icon("lock", "", 16)}Secure checkout</span><a href="/cart" class="{sc("CartLink")}" aria-label="Back to cart">{icon("cart")}</a></div>
</header>
<button type="button" class="{sc("SummaryToggle")}" aria-expanded="false" aria-controls="order-summary"><span class="{sc("SummaryToggleLabel")}">Show order summary</span><span class="{sc("SummaryToggleTotal")}">{total_s}</span></button>
<form id="checkout" action="/checkouts/c/8f1e27b4/complete" method="post" hidden></form>
<main class="{sc("Layout")}">
  <div class="{sc("Primary")}">
    <nav aria-label="Breadcrumb" class="{sc("Crumbs")}"><a href="/cart">Cart</a><span aria-hidden="true">›</span><a href="/checkout/shipping">Information</a><span aria-hidden="true">›</span><a href="/checkout/payment">Payment</a><span aria-hidden="true">›</span><span aria-current="step">Review</span></nav>
    <h1 class="{sc("PageTitle")}">Almost there — review &amp; pay</h1>
    <div class="{sc("Notice")}" role="note">{icon("truck", "", 18)}<p>Free standard shipping applied. Upgrade below for faster delivery.</p></div>
    <div class="{sc("Blocks")}">{blocks_v2}
    </div>
    <div class="{sc("GiftRow")}"><label class="{sc("SwitchLabel")}"><input type="checkbox" role="switch" name="isGift" class="{sc("Switch")}"><span>Sending a gift? Hide prices on the packing slip</span></label></div>
    <details class="{sc("Collapsible")}">
      <summary class="{sc("CollapsibleSummary")}">Add delivery instructions</summary>
      <div class="{sc("CollapsibleBody")}">
        <label for=":r7:" class="{sc("FieldLabel")}">Delivery instructions</label>
        <div class="{sc("TextAreaWrap")}"><textarea id=":r7:" name="deliveryInstructions" rows="3" maxlength="250" placeholder="Gate code, where to leave packages…" class="{sc("TextArea")}"{gt("t6")}></textarea></div>
        <p class="{sc("FieldHint")}">Visible to the courier. Max 250 characters.</p>
      </div>
    </details>
    <a href="/checkout/payment" class="{sc("BackLink")}">{icon("chevron-left", "", 16)}Return to payment</a>
  </div>
  <aside id="order-summary" class="{sc("Summary")}" aria-label="Order summary">
    <ul class="{sc("LineItems")}">{items_v2}</ul>
    <form class="{sc("DiscountForm")}" action="/checkout/discount" method="post"><input type="text" name="code" placeholder="Discount code or gift card" aria-label="Discount code or gift card" class="{sc("DiscountInput")}"><button type="submit" class="{sc("DiscountButton")}">Apply</button></form>
    <div class="{sc("Totals")}">
      <p class="{sc("TotalsRow")}"><span>Subtotal</span><span>{total_s}</span></p>
      <p class="{sc("TotalsRow")}"><span>Shipping</span><span>Free</span></p>
      <p class="{sc("TotalsRow")}"><span>Taxes</span><span>$0.00</span></p>
      <p class="{sc("TotalsRow", "grand")}"><span class="{sc("GrandLabel")}">Total <small>USD</small></span><span class="{sc("GrandValue")}"{gt("t5")}>{total_s}</span></p>
    </div>
    <div class="{sc("Consent")}">
      <input type="checkbox" id="terms-:r8:" name="acceptTerms" class="{sc("ConsentBox")}"{gt("t3")}>
      <label for="terms-:r8:" class="{sc("ConsentLabel")}">I agree to Tailwag's <a href="/legal/terms-of-sale">Terms of Sale</a> and <a href="/legal/returns">Return Policy</a>.</label>
    </div>
    <div class="{sc("PayWrap")}"><div class="{sc("PayInner")}"><button type="submit" form="checkout" class="{sc("PayButton")}" data-qa="checkout-pay-button"{gt("t2")}>Place your order</button></div></div>
    <p class="{sc("Fine")}">You'll be charged {total_s} on Visa •••• 4242. You'll earn 216 Wag Points.</p>
    <ul class="{sc("Badges")}"><li class="{sc("Badge")}">{icon("lock", "", 16)}<span>Encrypted checkout</span></li><li class="{sc("Badge")}">{icon("return", "", 16)}<span>365-day returns</span></li><li class="{sc("Badge")}">{icon("phone", "", 16)}<span>24/7 pet care team</span></li></ul>
    <section class="{sc("Help")}" aria-labelledby="help-title">
      <h3 id="help-title" class="{sc("HelpTitle")}">Questions about your order?</h3>
      <details class="{sc("HelpItem")}"><summary>When is my card charged?</summary><p>We authorize your card now and charge it when your order ships.</p></details>
      <details class="{sc("HelpItem")}"><summary>Can I change Autoship later?</summary><p>Skip, delay or cancel any time in <a href="/account/autoship">My Autoship</a>.</p></details>
      <details class="{sc("HelpItem")}"><summary>Returns</summary><p>Most items can be returned within 365 days.</p></details>
    </section>
  </aside>
</main>
<div class="{sc("MobilePayBar")}" role="region" aria-label="Pay">
  <span class="{sc("MobilePayTotal")}">{total_s}</span>
  <button type="submit" form="checkout" class="{sc("PayButton", "compact")}" data-qa="mobile-pay-button">Place your order</button>
</div>
<footer class="{sc("Footer")}">
  <nav aria-label="Policies" class="{sc("FooterNav")}"><a href="/legal/refunds">Refund policy</a><a href="/legal/shipping">Shipping policy</a><a href="/legal/privacy">Privacy policy</a><a href="/legal/terms-of-sale">Terms of sale</a></nav>
  <p class="{sc("FooterHelp")}">Questions? <a href="/help/chat">Chat with a pet care expert</a> or call 1-888-555-0199.</p>
  <ul class="{sc("PayIcons")}" aria-label="Payment methods">{"".join(f'<li class="{sc("PayIcon")}" title="{m}"><span class="{sc("VisuallyHidden")}">{m}</span></li>' for m in ("Visa", "Mastercard", "American Express", "Discover", "Wallet Pay", "Tailwag Gift Card"))}</ul>
</footer>
</div>
"""
    v2 = page(title="Review & pay – Tailwag checkout", body=body_v2,
              head='<style data-styled="active" data-styled-version="6.1.13">.' + sc("PayButton").split()[1]
                   + '{width:100%;padding:18px;border:0;border-radius:12px;background:#ffb703;font-weight:800}</style>\n')

    meta = {
        "title": "Checkout review & place order — pet supply store",
        "mutations": ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change",
                      "testid-change", "copy-change", "attribute-churn", "structure-move", "insertion", "tag-change"],
        "notes": (
            "v2 is a styled-components checkout (sc-* class pairs) with a Shopify-like layout: a new 'Contact' block "
            "is inserted, 'Shipping address' becomes 'Ship to' and every block gets a 'Change' link. Shipping rates "
            "move into <tw-shipping-rates>'s shadow root, ordered fastest-first with carrier codes as values and React "
            "ids. The summary table becomes paragraphs; terms consent and the pay button get new ids/copy, and a "
            "mobile pay bar plus an order-summary toggle repeat the total and the 'Place your order' button; data-qa "
            "hooks are renamed or dropped. Order "
            "notes move into a collapsed 'Add delivery instructions' disclosure."
        ),
        "targets": [
            target("t1", "'Expedited (2–3 business days)' shipping-method radio",
                   "#ship-expedited",
                   "//input[@name='shipping_method'][@value='expedited']",
                   ["shadow-dom", "id-change", "attribute-churn", "copy-change", "sibling-reorder"]),
            target("t2", "'Place order' submit button in the order summary",
                   "button[data-qa='place-order-button']",
                   "//button[normalize-space()='Place order']",
                   ["copy-change", "id-change", "testid-change", "decoy", "wrapper-divs", "class-obfuscation"]),
            target("t3", "Terms & Conditions consent checkbox",
                   "#accept-terms",
                   "//label[contains(.,'Terms')]/preceding-sibling::input[@type='checkbox']",
                   ["id-change", "testid-change", "attribute-churn", "copy-change", "class-obfuscation"]),
            target("t4", "'Edit' link of the shipping address section",
                   ".review-section--shipping .edit-link",
                   "//section[.//h2[normalize-space()='Shipping address']]//a[normalize-space()='Edit']",
                   ["copy-change", "decoy", "class-obfuscation", "insertion", "sibling-reorder"]),
            target("t5", "Order total amount ($216.95) in the summary",
                   "#order-total",
                   "//tr[@class='total-row']/td",
                   ["tag-change", "id-change", "decoy", "class-obfuscation", "structure-move"]),
            target("t6", "Order notes / delivery instructions textarea",
                   "textarea[name='order_note']",
                   "//section[contains(@class,'review-section--notes')]//textarea",
                   ["id-change", "attribute-churn", "structure-move", "wrapper-divs", "copy-change"]),
        ],
    }
    return v1, v2, meta


# ---------------------------------------------------------------------------
# ecommerce-05 — Bazaarly marketplace: search results with facets & pagination
# ---------------------------------------------------------------------------

# asin, title, price, list price, rating, reviews, bought, sponsored
S05_RESULTS = [
    ("B0CBRV1234", "Brevio Bambino Compact Espresso Maker with Steam Wand, Brushed Steel", "249.95", None, 4.4, "8,211", "2K+", True),
    ("B0C9ORS771", "Orsini Milano Semi-Automatic Espresso Machine with Built-in Grinder, Stainless Steel", "449.00", "599.00", 4.5, "3,042", "1K+", False),
    ("B0B7CLM015", "Caffè Lume Classico 15-Bar Pump Espresso Machine, Black", "129.99", None, 4.2, "12,470", "4K+", False),
    ("B0D4XKQ2PZ", "Vellora Duetto Dual Boiler Espresso Machine with PID Control", "599.99", "749.99", 4.7, "1,126", "500+", False),
    ("B0BNRD5521", "Nordbrew Capsule Espresso Machine with Milk Frother, Graphite", "179.00", None, 4.3, "5,880", "1K+", False),
    ("B0CBLV0904", "Bellanca Leva Manual Lever Espresso Maker", "389.00", None, 4.6, "402", "100+", False),
    ("B0AKFH1313", "Kaffeehaus Super-Automatic Espresso Machine, 13 Grind Settings", "699.00", "899.00", 4.1, "2,233", "300+", False),
    ("B0DDLV7788", "Dolcevita Retro Espresso Machine, Pastel Mint", "219.99", None, 4.0, "967", "200+", False),
    ("B0CBPC3290", "Bellanca Piccolo Single-Boiler Espresso Machine", "329.00", None, 4.4, "288", "50+", False),
    ("B0C9ORV452", "Orsini Venezia Espresso & Cappuccino Maker", "279.00", None, 4.3, "1,904", "400+", False),
    ("B0B7CLD611", "Caffè Lume Doppio Espresso Machine with Grinder", "349.99", None, 4.2, "733", "100+", False),
    ("B0D4VSS120", "Vellora Solo Single Boiler Espresso Machine", "399.99", None, 4.5, "611", "200+", False),
]
# listing titles edited by sellers between the two crawls
S05_V2_TITLES = {"B0C9ORS771": "Orsini Milano Espresso Machine with Conical Burr Grinder, Semi-Automatic, Stainless Steel"}
S05_BRANDS_V1 = ["Brevio", "Orsini", "Caffè Lume", "Bellanca", "Vellora", "Nordbrew", "Kaffeehaus", "Dolcevita"]
S05_BRANDS_V2 = ["Brevio", "Caffè Lume", "Nordbrew", "Orsini", "Kaffeehaus", "Vellora", "Bellanca", "Dolcevita"]
S05_TYPES = ["Semi-Automatic", "Super-Automatic", "Manual Lever", "Capsule", "Stovetop"]
S05_FEATURES = ["Built-in Grinder", "Milk Frother", "Dual Boiler", "PID Temperature Control", "Programmable"]
S05_PRICES = ["Under $100", "$100 to $200", "$200 to $500", "$500 & Above"]


def suite05() -> tuple[str, str, dict]:
    by_asin = {r[0]: r for r in S05_RESULTS}
    duetto = "B0D4XKQ2PZ"
    milano = "B0C9ORS771"

    # ---------------- v1 ----------------
    def price_v1(price: str, tid: str | None = None) -> str:
        whole, frac = price.split(".")
        return (f'<span class="a-price"{gt(tid)}><span class="a-price-symbol">$</span><span class="a-price-whole">{whole}.</span>'
                f'<span class="a-price-fraction">{frac}</span></span>')

    def result_v1(i: int, r: tuple) -> str:
        asin, title, price, was, rating, reviews, bought, sponsored = r
        url = f"/{slug(title)[:48]}/dp/{asin}"
        spon = '<span class="s-sponsored-label">Sponsored</span>' if sponsored else ""
        was_html = f' <span class="s-list-price">List: <s>${was}</s></span>' if was else ""
        return f"""
      <div class="s-result-item" data-component-type="s-search-result" data-asin="{asin}" data-index="{i}">
        <div class="s-result-item__inner">
          <div class="s-image-container"><a href="{url}"><img class="s-image" src="https://m.bazaarly-static.com/images/I/{asin}._AC_UL320_.jpg" alt="{e(title)}" width="160" height="160"></a></div>
          <div class="s-details">
            {spon}
            <h2 class="s-title"><a class="s-title-link" href="{url}"{gt("t5") if asin == milano else ""}>{e(title)}</a></h2>
            <div class="s-rating"><span class="a-icon-star" aria-label="{rating} out of 5 stars">★★★★★</span> <a class="s-rating-count" href="{url}#customerReviews">{reviews}</a></div>
            <p class="s-bought">{bought} bought in past month</p>
            <div class="s-price-block"><a class="s-price-link" href="{url}">{price_v1(price, "t6" if asin == duetto else None)}</a>{was_html}</div>
            <p class="s-delivery">FREE delivery <strong>Sat, Nov 7</strong></p>
            <p class="s-delivery s-delivery--fast">Or fastest delivery <strong>Tomorrow, Nov 6</strong></p>
            <div class="s-actions"><button type="button" class="a-button a-button-add" name="submit.addToCart"{gt("t4") if asin == duetto else ""}>Add to cart</button></div>
          </div>
        </div>
      </div>"""

    results_v1 = "".join(result_v1(i + 1, r) for i, r in enumerate(S05_RESULTS))
    brands_v1 = "".join(
        f'<li class="s-refinements__item"><label class="s-checkbox"><input type="checkbox" name="rh_brand" value="{e(b)}"{gt("t1") if b == "Bellanca" else ""}>'
        f'<span class="s-checkbox__label">{e(b)}</span></label></li>'
        for b in S05_BRANDS_V1
    )

    def checks_v1(key: str, opts: list[str]) -> str:
        return "".join(
            f'<li class="s-refinements__item"><label class="s-checkbox"><input type="checkbox" name="rh_{key}" value="{slug(o)}"><span class="s-checkbox__label">{e(o)}</span></label></li>'
            for o in opts
        )

    prices_v1 = "".join(f'<li class="s-refinements__item"><a class="s-refinements__link" href="/s?k=espresso+machine&amp;rh=p_36%3A{slug(o)}">{e(o)}</a></li>' for o in S05_PRICES)
    depts = ["Espresso Machines", "Super-Automatic Espresso Machines", "Stovetop Espresso Pots", "Coffee Grinders", "Milk Frothers", "Espresso Machine Accessories"]
    depts_v1 = "".join(f'<li class="s-refinements__item"><a class="s-refinements__link" href="/s?k=espresso+machine&amp;n={slug(d)}">{e(d)}</a></li>' for d in depts)
    pages_v1 = "".join(f'<li><a class="s-pagination-item s-pagination-button" href="/s?k=espresso+machine&amp;page={n}" aria-label="Go to page {n}">{n}</a></li>' for n in (2, 3))
    related = ["espresso machine with grinder", "espresso machine for home", "dual boiler espresso machine", "espresso machine under 200", "espresso tamper", "milk frothing pitcher"]
    related_v1 = "".join(f'<li><a href="/s?k={e(r.replace(" ", "+"))}">{e(r)}</a></li>' for r in related)
    body_v1 = f"""
<header id="navbar" class="nav-header">
  <div class="nav-belt">
    <a class="nav-logo" href="/ref=nav_logo" aria-label="Bazaarly">bazaarly<span class="nav-logo__tld">.com</span></a>
    <a class="nav-deliver" href="/gp/delivery/ajax/address-change"><span class="nav-deliver__line1">Deliver to Sam</span><span class="nav-deliver__line2">Denver 80205</span></a>
    <form class="nav-search" role="search" action="/s" method="get">
      <select class="nav-search__dropdown" name="i" aria-label="Search in">
        <option value="aps">All Departments</option><option value="appliances">Appliances</option><option value="garden">Home &amp; Kitchen</option><option value="kitchen" selected>Kitchen &amp; Dining</option><option value="grocery">Grocery &amp; Gourmet Food</option>
      </select>
      <input class="nav-search__input" id="twotabsearchtextbox" type="text" name="k" value="espresso machine" aria-label="Search Bazaarly" autocomplete="off">
      <button class="nav-search__submit" type="submit" aria-label="Go">{icon("search")}</button>
    </form>
    <div class="nav-tools">
      <a class="nav-tools__link" href="/gp/css/homepage.html"><span class="nav-line-1">Hello, Sam</span><span class="nav-line-2">Account &amp; Lists</span></a>
      <a class="nav-tools__link" href="/gp/css/order-history"><span class="nav-line-1">Returns</span><span class="nav-line-2">&amp; Orders</span></a>
      <a class="nav-tools__cart" href="/gp/cart/view.html" aria-label="3 items in cart">{icon("cart")}<span class="nav-cart-count">3</span><span class="nav-line-2">Cart</span></a>
    </div>
  </div>
  <div class="nav-main">
    <a class="nav-main__all" href="/gp/site-directory">{icon("menu", "", 16)} All</a>
    <a class="nav-main__link" href="/deals">Today's Deals</a>
    <a class="nav-main__link" href="/gp/help/customer/display.html">Customer Service</a>
    <a class="nav-main__link" href="/registries">Registry</a>
    <a class="nav-main__link" href="/gift-cards">Gift Cards</a>
    <a class="nav-main__link" href="/sell">Sell</a>
  </div>
</header>
<div class="s-result-info-bar">
  <h1 class="s-result-info-bar__text"><span>1-24 of over 3,000 results for</span> <span class="s-query">"espresso machine"</span></h1>
  <form id="sort-form" class="s-sort" action="/s" method="get">
    <label class="s-sort__label" for="s-result-sort-select">Sort by:</label>
    <select id="s-result-sort-select" class="s-sort__select" name="s"{gt("t2")}>
      <option value="relevanceblender" selected>Featured</option>
      <option value="price-asc-rank">Price: Low to High</option>
      <option value="price-desc-rank">Price: High to Low</option>
      <option value="review-rank">Avg. Customer Review</option>
      <option value="date-desc-rank">Newest Arrivals</option>
      <option value="exact-aware-popularity-rank">Best Sellers</option>
    </select>
  </form>
</div>
<div class="s-layout">
  <div id="s-refinements" class="s-refinements" role="navigation" aria-label="Refinements">
    <div class="s-refinements__group" id="facet-department"><h2 class="s-refinements__title">Department</h2><ul class="s-refinements__list">{depts_v1}</ul></div>
    <div class="s-refinements__group" id="facet-reviews"><h2 class="s-refinements__title">Customer Reviews</h2><ul class="s-refinements__list"><li class="s-refinements__item"><a class="s-refinements__link" href="/s?k=espresso+machine&amp;rh=p_72%3A4" aria-label="4 Stars &amp; Up">★★★★☆ &amp; Up</a></li></ul></div>
    <div class="s-refinements__group" id="facet-brand"><h2 class="s-refinements__title">Brand</h2><ul class="s-refinements__list">{brands_v1}</ul><a class="s-see-more" href="#facet-brand">See more</a></div>
    <div class="s-refinements__group" id="facet-price">
      <h2 class="s-refinements__title">Price</h2><ul class="s-refinements__list">{prices_v1}</ul>
      <form class="s-price-range" action="/s"><input type="number" name="low-price" placeholder="$ Min" aria-label="Minimum price"><input type="number" name="high-price" placeholder="$ Max" aria-label="Maximum price"><button type="submit" class="a-button a-button-small">Go</button></form>
    </div>
    <div class="s-refinements__group" id="facet-type"><h2 class="s-refinements__title">Espresso Machine Type</h2><ul class="s-refinements__list">{checks_v1("type", S05_TYPES)}</ul></div>
    <div class="s-refinements__group" id="facet-features"><h2 class="s-refinements__title">Special Features</h2><ul class="s-refinements__list">{checks_v1("feature", S05_FEATURES)}</ul></div>
    <div class="s-refinements__group" id="facet-deals"><h2 class="s-refinements__title">Deals &amp; Discounts</h2><ul class="s-refinements__list"><li class="s-refinements__item"><a class="s-refinements__link" href="/s?k=espresso+machine&amp;deals=all">All Discounts</a></li><li class="s-refinements__item"><a class="s-refinements__link" href="/s?k=espresso+machine&amp;deals=today">Today's Deals</a></li></ul></div>
  </div>
  <div class="s-main">
    <div class="s-results-header"><h2 class="s-results-header__title">Results</h2><p class="s-results-header__note">Check each product page for other buying options. Price and other details may vary based on product size and color.</p></div>
    <div class="s-main-slot">{results_v1}
    </div>
    <div class="s-pagination-container" role="navigation" aria-label="pagination">
      <ul class="s-pagination">
        <li><span class="s-pagination-item s-pagination-previous s-pagination-disabled" aria-disabled="true">Previous</span></li>
        <li><span class="s-pagination-item s-pagination-selected" aria-current="page">1</span></li>
        {pages_v1}
        <li><span class="s-pagination-item s-pagination-ellipsis">…</span></li>
        <li><a class="s-pagination-item s-pagination-button" href="/s?k=espresso+machine&amp;page=20" aria-label="Go to page 20">20</a></li>
        <li><a class="s-pagination-item s-pagination-next" href="/s?k=espresso+machine&amp;page=2"{gt("t3")}>Next</a></li>
      </ul>
    </div>
    <div class="s-related"><h2 class="s-related__title">Related searches</h2><ul class="s-related__list">{related_v1}</ul></div>
    <div class="s-help"><h2 class="s-help__title">Need help?</h2><p>Visit the <a href="/gp/help/customer/display.html">help section</a> or <a href="/gp/help/contact-us">contact us</a>.</p></div>
  </div>
</div>
<footer class="nav-footer">
  <a class="nav-footer__back" href="#navbar">Back to top</a>
  <div class="nav-footer__cols">
    <div class="nav-footer__col"><h3>Get to Know Us</h3><ul><li><a href="/careers">Careers</a></li><li><a href="/press">Press Center</a></li><li><a href="/sustainability">Sustainability</a></li><li><a href="/investors">Investor Relations</a></li></ul></div>
    <div class="nav-footer__col"><h3>Make Money with Us</h3><ul><li><a href="/sell">Sell on Bazaarly</a></li><li><a href="/affiliates">Become an Affiliate</a></li><li><a href="/advertise">Advertise Your Products</a></li></ul></div>
    <div class="nav-footer__col"><h3>Let Us Help You</h3><ul><li><a href="/gp/css/homepage.html">Your Account</a></li><li><a href="/gp/css/order-history">Your Orders</a></li><li><a href="/shipping">Shipping Rates &amp; Policies</a></li><li><a href="/returns">Returns &amp; Replacements</a></li><li><a href="/gp/help/customer/display.html">Help</a></li></ul></div>
  </div>
  <p class="nav-footer__copy">© 2014-2026, Bazaarly.com, Inc. or its affiliates · <a href="/privacy">Privacy Notice</a> · <a href="/conditions">Conditions of Use</a></p>
</footer>
"""
    css_v1 = """
body{margin:0;font:14px/20px Arial,sans-serif;color:#0f1111;background:#fff}
.nav-belt{display:flex;align-items:center;gap:16px;background:#1b2a35;color:#fff;padding:8px 16px}
.nav-search{display:flex;flex:1}.nav-search__input{flex:1;padding:8px}
.nav-main{display:flex;gap:16px;background:#253844;color:#fff;padding:6px 16px}
.s-layout{display:grid;grid-template-columns:240px 1fr;gap:24px;padding:0 16px}
.s-result-item__inner{display:grid;grid-template-columns:200px 1fr;gap:16px;border-bottom:1px solid #ddd;padding:16px 0}
.a-price{font-size:28px}.a-price-symbol,.a-price-fraction{font-size:13px;vertical-align:top}
.a-button-add{background:#ffd814;border:1px solid #fcd200;border-radius:20px;padding:6px 14px}
.s-pagination{display:flex;gap:8px;list-style:none;justify-content:center}
"""
    v1 = page(title="Bazaarly.com : espresso machine", css=css_v1, body=body_v1, body_attrs=' class="a-m-us s-search"')

    # ---------------- v2 ----------------
    order_v2 = [milano, "B0CBRV1234", "B0B7CLM015", "B0BNRD5521", "B0CBLV0904", "B0AKFH1313", duetto,
                "B0DDLV7788", "B0C9ORV452", "B0CBPC3290", "B0B7CLD611", "B0D4VSS120"]

    def card_v2(i: int, r: tuple) -> str:
        asin, title, price, was, rating, reviews, bought, sponsored = r
        url = f"/dp/{asin}?ref=sr_1_{i}"
        spon = f'<span class="{ve("badgeSponsored")}">Sponsored</span>' if sponsored else ""
        was_html = f'<span class="{ve("listPrice")}">List <s>${was}</s></span>' if was else ""
        deal = f'<span class="{ve("dealBadge")}">Limited time deal</span>' if was else ""
        return f"""
        <div class="{ve("cell")}" data-index="{i}" data-product-id="{asin}">
          <div class="{ve("card", "cardHover")}">
            <a href="{url}" class="{ve("cardMedia")}" tabindex="-1"><img src="https://m.bazaarly-static.com/images/I/{asin}._AC_SX300_.webp" alt="" class="{ve("cardImg")}" loading="lazy"></a>
            <div class="{ve("cardBody")}">
              {spon}{deal}
              <h3 class="{ve("cardTitle")}"><a href="{url}" class="{ve("cardLink")}"{gt("t5") if asin == milano else ""}>{e(S05_V2_TITLES.get(asin, title))}</a></h3>
              <div class="{ve("ratingRow")}"><span class="{ve("stars")}" role="img" aria-label="Rated {rating} out of 5">★★★★★</span><span class="{ve("ratingCount")}">({reviews})</span></div>
              <p class="{ve("socialProof")}">{bought} bought in past month</p>
              <p class="{ve("priceRow")}"><span class="{ve("price")}"{gt("t6") if asin == duetto else ""}>${price}</span>{was_html}</p>
              <p class="{ve("delivery")}">{icon("truck", ve("deliveryIcon"), 14)}Free delivery <b>Sat, Nov 7</b></p>
              <div class="{ve("actions")}"><div class="{ve("actionsInner")}"><button type="button" class="{ve("addBtn", "btnPrimary")}" data-action="add-to-cart"{gt("t4") if asin == duetto else ""}>Add to cart</button></div></div>
            </div>
          </div>
        </div>"""

    cards_v2 = "".join(card_v2(i + 1, by_asin[a]) for i, a in enumerate(order_v2))
    spon_v2 = "".join(
        f'<li class="{ve("sponsoredItem")}"><img src="https://m.bazaarly-static.com/images/I/{a}._AC_SX200_.webp" alt="" class="{ve("sponsoredImg")}">'
        f'<a href="/dp/{a}?ref=sb_sp" class="{ve("sponsoredTitle")}">{e(by_asin[a][1])}</a>'
        f'<span class="{ve("price")}">${by_asin[a][2]}</span>'
        f'<button type="button" class="{ve("addBtn", "btnSecondary")}" data-action="add-to-cart">Add to cart</button></li>'
        for a in (duetto, "B0CBPC3290", "B0AKFH1313")
    )
    drawer_brands = "".join(
        f'<li class="{ve("drawerOption")}"><input type="checkbox" id="all-brand-{i}" name="brand" value="{e(b)}" class="{ve("checkbox")}"><label for="all-brand-{i}">{e(b)}</label></li>'
        for i, b in enumerate(S05_BRANDS_V2)
    )
    pop_brands = "".join(
        f'<li class="{ve("popOption")}"><label class="{ve("popLabel")}"><input type="checkbox" id="brand-opt-{i}" name="brand" value="{e(b)}" class="{ve("checkbox")}"{gt("t1") if b == "Bellanca" else ""}><span>{e(b)}</span></label></li>'
        for i, b in enumerate(S05_BRANDS_V2)
    )

    def pop_checks(key: str, opts: list[str]) -> str:
        return "".join(
            f'<li class="{ve("popOption")}"><label class="{ve("popLabel")}"><input type="checkbox" name="{key}" value="{e(o)}" class="{ve("checkbox")}"><span>{e(o)}</span></label></li>'
            for o in opts
        )

    def pop(label: str, inner: str) -> str:
        return (f'<details class="{ve("filterPop")}"><summary class="{ve("chip")}">{label}{icon("chevron-down", ve("chipIcon"), 14)}</summary>'
                f'<div class="{ve("popPanel")}"><ul class="{ve("popList")}">{inner}</ul>'
                f'<div class="{ve("popFooter")}"><button type="button" class="{ve("linkBtn")}">Clear</button><button type="button" class="{ve("btnPrimary")}">Show results</button></div></div></details>')

    price_opts = "".join(f'<li class="{ve("popOption")}"><a href="/s?k=espresso+machine&amp;price={slug(o)}" class="{ve("popLink")}">{e(o)}</a></li>' for o in S05_PRICES)
    pages_v2 = "".join(f'<a href="/s?k=espresso+machine&amp;page={n}" class="{ve("pageLink")}" aria-label="Page {n}">{n}</a>' for n in (2, 3, 4))
    related_v2 = "".join(f'<a href="/s?k={e(r.replace(" ", "+"))}" class="{ve("relatedChip")}">{e(r)}</a>' for r in related)
    body_v2 = f"""
<div id="app">
<header class="{ve("header")}">
  <div class="{ve("headerRow")}">
    <a href="/" class="{ve("logo")}" aria-label="Bazaarly home">bazaarly</a>
    <button type="button" class="{ve("location")}"><span class="{ve("locationSmall")}">Delivering to Denver 80205</span><span class="{ve("locationBig")}">Update location</span></button>
    <form role="search" action="/s" class="{ve("search")}">
      <input type="search" name="k" value="espresso machine" aria-label="Search Bazaarly" class="{ve("searchInput")}" autocomplete="off">
      <button type="submit" class="{ve("searchBtn")}" aria-label="Search">{icon("search")}</button>
    </form>
    <nav aria-label="Account" class="{ve("account")}">
      <a href="/account" class="{ve("accountLink")}">Hi, Sam</a>
      <a href="/orders" class="{ve("accountLink")}">Orders</a>
      <a href="/cart" class="{ve("cartLink")}" aria-label="Cart, 3 items">{icon("cart")}<span class="{ve("cartCount")}">3</span></a>
    </nav>
  </div>
  <nav aria-label="Shortcuts" class="{ve("subnav")}"><a href="/deals">Deals</a><a href="/registries">Registry</a><a href="/gift-cards">Gift cards</a><a href="/help">Help</a><a href="/sell">Sell</a></nav>
</header>
<div id="all-filters" role="dialog" aria-modal="true" aria-label="All filters" class="{ve("drawer")}" hidden>
  <div class="{ve("drawerHead")}"><h2 class="{ve("drawerTitle")}">All filters</h2><button type="button" class="{ve("iconBtn")}" aria-label="Close">{icon("close")}</button></div>
  <h3 class="{ve("drawerSection")}">Brand</h3><ul class="{ve("drawerList")}">{drawer_brands}</ul>
  <h3 class="{ve("drawerSection")}">Type</h3><ul class="{ve("drawerList")}">{pop_checks("type", S05_TYPES)}</ul>
  <button type="button" class="{ve("btnPrimary")}">Show 3,000+ results</button>
</div>
<main class="{ve("main")}">
  <div class="{ve("filterBar")}" role="toolbar" aria-label="Filters">
    <button type="button" class="{ve("chip", "chipStrong")}" aria-controls="all-filters">{icon("sliders", ve("chipIcon"), 14)}All filters</button>
    {pop("Brand", pop_brands)}
    {pop("Price", price_opts)}
    {pop("Type", pop_checks("type", S05_TYPES))}
    {pop("Features", pop_checks("feature", S05_FEATURES))}
    <a href="/s?k=espresso+machine&amp;rating=4" class="{ve("chip")}">4★ &amp; up</a>
    <a href="/s?k=espresso+machine&amp;delivery=tomorrow" class="{ve("chip")}">Get it by tomorrow</a>
    <div class="{ve("sortSlot")}">
      <bz-sort-menu value="relevance">
        <template shadowrootmode="open">
          <style>:host{{display:inline-flex;align-items:center;gap:8px;font:14px system-ui}}select{{border:1px solid #c7cdd1;border-radius:999px;padding:6px 28px 6px 12px}}</style>
          <label class="sort-label" for="sort">Sort by</label>
          <select id="sort" name="sort" class="sort-select"{gt("t2")}>
            <option value="relevance" selected>Relevance</option>
            <option value="price_asc">Price: low to high</option>
            <option value="price_desc">Price: high to low</option>
            <option value="rating">Avg. customer review</option>
            <option value="newest">Newest arrivals</option>
            <option value="bestsellers">Best sellers</option>
          </select>
        </template>
      </bz-sort-menu>
    </div>
  </div>
  <div class="{ve("resultsHead")}">
    <h1 class="{ve("resultsTitle")}">Results for <q>espresso machine</q></h1>
    <p class="{ve("resultsCount")}">Over 3,000 results</p>
    <div class="{ve("miniPager")}"><span>Page 1 of 20</span><a href="/s?k=espresso+machine&amp;page=2" class="{ve("miniPagerLink")}" rel="next">Next</a></div>
  </div>
  <section class="{ve("sponsoredRail")}" aria-label="Sponsored">
    <p class="{ve("sponsoredHead")}">Sponsored · Top-rated dual-boiler &amp; lever machines</p>
    <ul class="{ve("sponsoredList")}">{spon_v2}</ul>
  </section>
  <div class="{ve("grid")}">{cards_v2}
  </div>
  <nav aria-label="Pagination" class="{ve("pager")}">
    <a class="{ve("pageLink", "pageDisabled")}" aria-disabled="true">Previous</a>
    <a class="{ve("pageLink", "pageCurrent")}" aria-current="page">1</a>{pages_v2}
    <span class="{ve("pageEllipsis")}">…</span>
    <a href="/s?k=espresso+machine&amp;page=20" class="{ve("pageLink")}" aria-label="Page 20">20</a>
    <a href="/s?k=espresso+machine&amp;page=2" class="{ve("pageLink", "pageNext")}" rel="next"{gt("t3")}>Next</a>
  </nav>
  <section class="{ve("related")}" aria-labelledby="related-h"><h2 id="related-h" class="{ve("relatedTitle")}">Related searches</h2><div class="{ve("relatedList")}">{related_v2}</div></section>
</main>
<footer class="{ve("footer")}">
  <a href="#app" class="{ve("backTop")}">Back to top</a>
  <div class="{ve("footerCols")}">
    <nav aria-label="About" class="{ve("footerCol")}"><a href="/careers">Careers</a><a href="/press">Press</a><a href="/sustainability">Sustainability</a></nav>
    <nav aria-label="Sell" class="{ve("footerCol")}"><a href="/sell">Sell on Bazaarly</a><a href="/affiliates">Affiliates</a><a href="/advertise">Advertise</a></nav>
    <nav aria-label="Help" class="{ve("footerCol")}"><a href="/account">Your account</a><a href="/orders">Your orders</a><a href="/returns">Returns</a><a href="/help">Help</a></nav>
  </div>
  <p class="{ve("copyright")}">© 2014–2026 Bazaarly.com, Inc. · <a href="/privacy">Privacy</a> · <a href="/conditions">Conditions of use</a></p>
</footer>
</div>
"""
    v2 = page(title='"espresso machine" – Bazaarly search', body=body_v2,
              css=f'.{ve("grid").split()[0]}{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:20px}}'
                  f'.{ve("filterBar").split()[0]}{{display:flex;gap:8px;flex-wrap:wrap;align-items:center;position:sticky;top:0}}')

    meta = {
        "title": "Search results with faceted filters, sort and pagination — general marketplace",
        "mutations": ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change",
                      "copy-change", "tag-change", "attribute-churn", "structure-move", "insertion"],
        "notes": (
            "v2 replaces the left refinement column with a sticky filter bar of <details> popovers (brands re-ordered "
            "by popularity, new ids) plus a hidden 'All filters' dialog that duplicates the brand checkboxes. Sort "
            "moves into <bz-sort-menu>'s shadow root with new name/values and 'Relevance' copy. Results switch from "
            "list rows to a grid of cards with vanilla-extract hashed classes; data-asin becomes data-product-id and "
            "data-index is renumbered after re-ranking (index 4 is now a different product); the seller has also "
            "re-worded the Orsini Milano listing title. A sponsored rail repeats "
            "the Vellora Duetto with its price and an 'Add to cart' button, and a compact 'Page 1 of 20 · Next' pager is "
            "inserted above the results."
        ),
        "targets": [
            target("t1", "'Bellanca' checkbox in the Brand facet",
                   "#facet-brand li:nth-child(4) input[type='checkbox']",
                   "//div[@id='facet-brand']//li[.//span[normalize-space()='Bellanca']]//input",
                   ["structure-move", "sibling-reorder", "decoy", "id-change", "class-obfuscation", "wrapper-divs"]),
            target("t2", "'Sort by' dropdown in the results header",
                   "#s-result-sort-select",
                   "//form[@id='sort-form']//select[@name='s']",
                   ["shadow-dom", "id-change", "attribute-churn", "copy-change", "structure-move"]),
            target("t3", "'Next' page link of the pagination below the results",
                   ".s-pagination a.s-pagination-next",
                   "//a[normalize-space()='Next']",
                   ["decoy", "class-obfuscation", "tag-change", "insertion"]),
            target("t4", "'Add to cart' button of the 'Vellora Duetto Dual Boiler Espresso Machine' result",
                   "div[data-asin='B0D4XKQ2PZ'] button.a-button-add",
                   "//div[@data-index='4']//button[normalize-space()='Add to cart']",
                   ["attribute-churn", "sibling-reorder", "decoy", "class-obfuscation", "wrapper-divs"]),
            target("t5", "Title link of the 'Orsini Milano Semi-Automatic Espresso Machine with Built-in Grinder' result",
                   ".s-main-slot > div:nth-child(2) h2 a",
                   "//a[@class='s-title-link'][contains(.,'Orsini Milano')]",
                   ["sibling-reorder", "copy-change", "tag-change", "class-obfuscation", "structure-move"]),
            target("t6", "Price ($599.99) of the 'Vellora Duetto' result",
                   "div[data-asin='B0D4XKQ2PZ'] .a-price",
                   "//h2[contains(.,'Vellora Duetto')]/ancestor::div[@data-component-type='s-search-result']//span[@class='a-price']",
                   ["class-obfuscation", "attribute-churn", "decoy", "tag-change", "sibling-reorder"]),
        ],
    }
    return v1, v2, meta


# ---------------------------------------------------------------------------
# ecommerce-06 — Maison Lune: fashion category landing with mega-menu
# ---------------------------------------------------------------------------


def vm(local: str) -> str:
    """Vite CSS-modules class name: ``_local_hash_line``."""
    return f"_{local}_{_h('vite.' + local, 5, _B36)}_{int(_h('line.' + local, 2, '0123456789')) + 3}"


S06_MEGA_WOMEN = [
    ("Clothing", ["Dresses", "Tops & Blouses", "Knitwear", "Jeans", "Trousers", "Coats & Jackets", "Skirts"]),
    ("Shoes", ["Boots", "Sneakers", "Flats", "Heels", "Sandals"]),
    ("Accessories", ["Bags", "Scarves", "Jewelry", "Belts", "Hats & Gloves"]),
]
S06_MEGA_MEN = [
    ("Clothing", ["T-Shirts", "Shirts", "Knitwear", "Jeans", "Trousers", "Coats & Jackets"]),
    ("Shoes", ["Boots", "Sneakers", "Loafers"]),
    ("Accessories", ["Bags", "Belts", "Hats & Scarves"]),
]
S06_FEATURED = ["The Autumn Edit", "Cashmere Shop", "Occasionwear", "Responsibly Made"]
S06_NEW_IN = [
    ("Ribbed Merino Crewneck", "128.00", 4), ("Wool-Blend Wrap Coat", "248.00", 3), ("Satin Slip Midi Skirt", "98.00", 2),
    ("Cropped Wide-Leg Jeans", "118.00", 2), ("Leather Chelsea Boots", "228.00", 2), ("Cashmere Rib Beanie", "68.00", 5),
    ("Oversized Poplin Shirt", "88.00", 3), ("Quilted Shoulder Bag", "158.00", 2),
]
S06_BEST = [
    ("Everyday Cotton Tee", "38.00", 6), ("High-Rise Straight Jeans", "118.00", 3), ("Cashmere Crew Sweater", "178.00", 5),
    ("Classic Trench Coat", "298.00", 2), ("Leather Ballet Flats", "128.00", 3), ("Silk Twill Scarf", "78.00", 4),
    ("Merino Cardigan", "138.00", 3), ("Pleated Wide-Leg Trousers", "108.00", 2),
]
S06_TILES = ["Dresses", "Knitwear", "Coats & Jackets", "Denim", "Boots", "Bags"]


def suite06() -> tuple[str, str, dict]:
    # ---------------- v1 ----------------
    def mega_v1(menu_id: str, base: str, cols: list, promo: str, tid_link: str | None = None) -> str:
        out = []
        for title, links in cols:
            lis = "".join(
                f'<li><a href="/{base}/{slug(title)}/{slug(x)}"{gt("t1") if (tid_link and title == "Clothing" and x == tid_link) else ""}>{e(x)}</a></li>'
                for x in links
            )
            out.append(f'<div class="mega-col"><h3 class="mega-col__title">{title}</h3><ul class="mega-links">{lis}</ul></div>')
        feat = "".join(f'<li><a href="/{base}/{slug(x)}">{e(x)}</a></li>' for x in S06_FEATURED)
        out.append(f'<div class="mega-col mega-col--featured"><h3 class="mega-col__title">Featured</h3><ul class="mega-links">{feat}</ul></div>')
        out.append(f'<a class="mega-promo" href="/{base}/sale"><img class="mega-promo__img" src="/cdn/shop/files/{base}-promo_600.jpg" alt="" width="300" height="380"><span class="mega-promo__label">{promo}</span></a>')
        return f'<div class="mega-menu" id="{menu_id}"><div class="mega-menu__inner">{"".join(out)}</div></div>'

    def tile_v1(name: str, price: str, colours: int, tid: str | None = None) -> str:
        url = f"/products/{slug(name)}"
        return (f'<li class="product-tile"><div class="product-tile__media"><a href="{url}" tabindex="-1"><img class="product-tile__img" src="/cdn/shop/products/{slug(name)}_720x.jpg" alt="{e(name)}" width="360" height="480" loading="lazy"></a>'
                f'<button type="button" class="product-tile__wishlist" aria-label="Add {e(name)} to wishlist">{icon("heart", "", 18)}</button></div>'
                f'<div class="product-tile__info"><h3 class="product-tile__name"><a href="{url}">{e(name)}</a></h3>'
                f'<p class="product-tile__price"><span class="price"{gt(tid)}>${price}</span></p><p class="product-tile__colors">+{colours} colors</p></div></li>')

    def carousel_v1(cid: str, heading_id: str, title: str, items: list, href: str, next_tid: str | None = None,
                    price_tid_for: str | None = None) -> str:
        tiles = "".join(tile_v1(n, p, c, "t4" if n == price_tid_for else None) for n, p, c in items)
        return f"""
  <section class="carousel" id="{cid}" aria-labelledby="{heading_id}">
    <div class="carousel__header">
      <h2 class="section-title" id="{heading_id}">{title}</h2>
      <a class="carousel__view-all" href="{href}">View all</a>
      <div class="carousel__controls">
        <button type="button" class="carousel__prev" aria-label="Previous" disabled>{icon("chevron-left")}</button>
        <button type="button" class="carousel__next" aria-label="Next"{gt(next_tid)}>{icon("chevron-right")}</button>
      </div>
    </div>
    <ul class="carousel__track">{tiles}</ul>
  </section>"""

    tiles_v1 = "".join(
        f'<li class="category-tiles__item"><a class="tile" href="/women/{slug(t)}"><img class="tile__img" src="/cdn/shop/collections/women-{slug(t)}_600.jpg" alt="" width="300" height="400"><span class="tile__label">{e(t)}</span></a></li>'
        for t in S06_TILES
    )
    simple_nav = "".join(
        f'<li class="main-nav__item{" main-nav__item--sale" if n == "Sale" else ""}"><a class="main-nav__link" href="/{slug(n)}">{n}</a></li>'
        for n in ["Kids", "Home", "Gifts", "Sale"]
    )
    footer_cols = [
        ("Customer care", ["Contact us", "Shipping", "Returns & exchanges", "Size guide", "FAQ", "Track your order"]),
        ("About Maison Lune", ["Our story", "Responsibility", "Stores", "Careers", "Press"]),
        ("Legal", ["Terms & conditions", "Privacy policy", "Cookie preferences", "Accessibility"]),
    ]
    footer_v1 = "".join(
        f'<div class="footer__col"><h2 class="footer__heading">{h}</h2><ul class="footer__list">'
        + "".join(f'<li><a class="footer__link" href="/pages/{slug(x)}">{e(x)}</a></li>' for x in links) + "</ul></div>"
        for h, links in footer_cols
    )
    body_v1 = f"""
<div class="announcement-bar" role="region" aria-label="Announcements">
  <ul class="announcement-bar__list">
    <li class="announcement-bar__item">Free shipping on orders over $150</li>
    <li class="announcement-bar__item">Free returns within 30 days</li>
    <li class="announcement-bar__item">New: The Autumn Edit has landed</li>
  </ul>
</div>
<header class="header">
  <div class="header__top">
    <div class="header__left">
      <button type="button" class="header__icon header__icon--menu" aria-label="Menu">{icon("menu")}</button>
      <a class="header__locale" href="/localization">United States (USD $)</a>
    </div>
    <a class="header__logo" href="/">MAISON LUNE</a>
    <div class="header__right">
      <button type="button" class="header__icon header__icon--search" aria-label="Search">{icon("search")}</button>
      <a class="header__icon header__icon--account" href="/account" aria-label="Account">{icon("user")}</a>
      <a class="header__icon header__icon--wishlist" href="/wishlist" aria-label="Wishlist">{icon("heart")}</a>
      <a class="header__icon header__icon--bag" href="/cart" aria-label="Bag, 2 items"{gt("t6")}>{icon("bag")}<span class="header__bag-count">2</span></a>
    </div>
  </div>
  <nav class="main-nav" aria-label="Primary">
    <ul class="main-nav__list">
      <li class="main-nav__item"><a class="main-nav__link" href="/new-in">New In</a></li>
      <li class="main-nav__item main-nav__item--has-mega" id="nav-women">
        <a class="main-nav__link is-active" href="/women" aria-expanded="false" aria-controls="mega-women">Women</a>
        {mega_v1("mega-women", "women", S06_MEGA_WOMEN, "Up to 40% off knitwear", "Knitwear")}
      </li>
      <li class="main-nav__item main-nav__item--has-mega" id="nav-men">
        <a class="main-nav__link" href="/men" aria-expanded="false" aria-controls="mega-men">Men</a>
        {mega_v1("mega-men", "men", S06_MEGA_MEN, "The overshirt edit")}
      </li>
      {simple_nav}
    </ul>
  </nav>
</header>
<main id="MainContent" class="collection-landing">
  <nav class="breadcrumbs" aria-label="Breadcrumbs"><ol class="breadcrumbs__list"><li><a href="/">Home</a></li><li aria-current="page">Women</li></ol></nav>
  <section class="hero">
    <div class="hero__media"><img class="hero__img" src="/cdn/shop/files/autumn-edit-hero_2400x.jpg" alt="Model in a camel wrap coat walking through a park" width="1200" height="640"></div>
    <div class="hero__content">
      <p class="hero__eyebrow">New season</p>
      <h1 class="hero__title">The Autumn Edit</h1>
      <p class="hero__text">Soft tailoring, chunky knits and the coat you'll wear on repeat.</p>
      <div class="hero__ctas"><a class="btn btn--light hero__cta" href="/women/autumn-edit"{gt("t2")}>Shop the edit</a><a class="hero__secondary" href="/lookbook/autumn-2026">Explore the lookbook</a></div>
    </div>
  </section>
  <section class="category-tiles" aria-labelledby="cat-title">
    <h2 class="section-title" id="cat-title">Shop by category</h2>
    <ul class="category-tiles__grid">{tiles_v1}</ul>
  </section>
{carousel_v1("carousel-new-in", "new-in-heading", "New In", S06_NEW_IN, "/women/new-in", "t3", "Wool-Blend Wrap Coat")}
  <section class="promo-banners">
    <div class="promo-banner promo-banner--knit"><img class="promo-banner__img" src="/cdn/shop/files/knit-sale_1200x.jpg" alt="" width="600" height="400"><div class="promo-banner__content"><h2 class="promo-banner__title">Up to 40% off knitwear</h2><p>Merino, cashmere and alpaca blends — this week only.</p><a class="btn btn--dark" href="/women/sale/knitwear">Shop sale</a></div></div>
    <div class="promo-banner promo-banner--alterations"><div class="promo-banner__content"><h2 class="promo-banner__title">Complimentary alterations</h2><p>Free hemming on all full-price trousers and jeans, in store or by mail.</p><a class="btn btn--outline" href="/pages/alterations">Learn more</a></div></div>
  </section>
{carousel_v1("carousel-bestsellers", "bestsellers-heading", "Bestsellers", S06_BEST, "/women/bestsellers")}
  <section class="editorial" aria-labelledby="journal-title">
    <h2 class="section-title" id="journal-title">From the Journal</h2>
    <div class="editorial__grid">
      <article class="editorial-card"><img class="editorial-card__img" src="/cdn/shop/articles/wrap-coat-styling_800x.jpg" alt="" width="400" height="300"><h3 class="editorial-card__title"><a href="/blogs/journal/how-to-style-a-wrap-coat">Three ways to style a wrap coat</a></h3><p class="editorial-card__meta">Style notes · 4 min read</p></article>
      <article class="editorial-card"><img class="editorial-card__img" src="/cdn/shop/articles/cashmere-care_800x.jpg" alt="" width="400" height="300"><h3 class="editorial-card__title"><a href="/blogs/journal/cashmere-care-guide">The cashmere care guide</a></h3><p class="editorial-card__meta">Care · 6 min read</p></article>
      <article class="editorial-card"><img class="editorial-card__img" src="/cdn/shop/articles/mill-visit_800x.jpg" alt="" width="400" height="300"><h3 class="editorial-card__title"><a href="/blogs/journal/visiting-our-wool-mill">Inside our wool mill in Biella</a></h3><p class="editorial-card__meta">Responsibility · 8 min read</p></article>
    </div>
  </section>
  <section class="newsletter" aria-labelledby="newsletter-title">
    <h2 class="newsletter__title" id="newsletter-title">Join the Maison Lune list</h2>
    <p class="newsletter__text">Sign up for 10% off your first order, early access to sales and new-season edits.</p>
    <form id="newsletter-form" class="newsletter__form" action="/contact#newsletter" method="post">
      <input type="hidden" name="contact[tags]" value="newsletter">
      <label class="visually-hidden" for="newsletter-email">Email</label>
      <input class="newsletter__input" id="newsletter-email" type="email" name="contact[email]" placeholder="Enter your email" required{gt("t5")}>
      <button type="submit" class="btn btn--dark newsletter__submit">Sign up</button>
    </form>
    <p class="newsletter__legal">By signing up you agree to our <a href="/policies/privacy-policy">Privacy Policy</a>.</p>
  </section>
</main>
<footer class="footer">
  <div class="footer__grid">{footer_v1}
    <div class="footer__col footer__col--social"><h2 class="footer__heading">Follow us</h2><ul class="footer__social"><li><a href="https://instagram.example/maisonlune" aria-label="Instagram">IG</a></li><li><a href="https://pinterest.example/maisonlune" aria-label="Pinterest">PI</a></li><li><a href="https://tiktok.example/@maisonlune" aria-label="TikTok">TT</a></li></ul></div>
  </div>
  <div class="footer__bottom">
    <form class="footer__localization" action="/localization" method="post"><label for="footer-country">Country/region</label><select id="footer-country" name="country_code"><option value="US" selected>United States (USD $)</option><option value="CA">Canada (CAD $)</option><option value="GB">United Kingdom (GBP £)</option><option value="FR">France (EUR €)</option></select></form>
    <p class="footer__copyright">© 2026 Maison Lune</p>
  </div>
</footer>
"""
    css_v1 = """
body{margin:0;font:15px/1.6 "Cormorant Garamond","Helvetica Neue",sans-serif;color:#1a1a1a}
.announcement-bar{background:#1a1a1a;color:#f3eee7;text-align:center;font-size:12px;letter-spacing:.08em}
.header__top{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;padding:16px 40px}
.header__logo{font-size:28px;letter-spacing:.3em;text-decoration:none;color:inherit}
.main-nav__list{display:flex;justify-content:center;gap:32px;list-style:none;margin:0;padding:0}
.mega-menu{position:absolute;left:0;right:0;display:none;background:#fff}
.main-nav__item--has-mega:hover .mega-menu{display:block}
.mega-menu__inner{display:grid;grid-template-columns:repeat(4,1fr) 300px;gap:32px;padding:32px 40px}
.carousel__track{display:grid;grid-auto-flow:column;grid-auto-columns:23%;gap:16px;overflow-x:auto;list-style:none;padding:0}
.visually-hidden{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
"""
    v1 = page(title="Women's Clothing, Shoes & Accessories | Maison Lune", css=css_v1, body=body_v1,
              head='<meta name="description" content="Discover the Autumn Edit: soft tailoring, cashmere and outerwear for women.">\n',
              body_attrs=' class="template-collection collection-women"')

    # ---------------- v2 ----------------
    women_cols_v2 = [
        ("Clothing", ["Coats & Jackets", "Knitwear", "Dresses", "Tops & Shirts", "Jeans", "Trousers & Skirts"]),
        ("Shoes", ["Boots", "Sneakers", "Flats & Loafers", "Heels"]),
        ("Accessories", ["Bags", "Scarves & Wraps", "Jewelry", "Belts"]),
    ]
    men_cols_v2 = [
        ("Clothing", ["Coats & Jackets", "Knitwear", "Shirts", "T-Shirts", "Jeans", "Trousers"]),
        ("Shoes & Accessories", ["Boots", "Sneakers", "Bags", "Belts"]),
    ]

    def mega_v2(key: str, cols: list, tid_link: str | None = None) -> str:
        feat = "".join(f'<li class="mega__item"><a class="mega__link" href="/{key}/{slug(x)}">{e(x)}</a></li>' for x in S06_FEATURED)
        parts = [f'<div class="mega__group mega__group--featured"><p class="mega__heading">Featured</p><ul class="mega__list">{feat}</ul></div>']
        for title, links in cols:
            lis = "".join(
                f'<li class="mega__item"><a class="mega__link" href="/{key}/{slug(x)}"{gt("t1") if (tid_link and x == tid_link) else ""}>{e(x)}</a></li>'
                for x in links
            )
            parts.append(f'<div class="mega__group"><p class="mega__heading">{title}</p><ul class="mega__list">{lis}</ul></div>')
        return f'<div class="mega" data-menu="{key}" hidden><div class="mega__wrap"><div class="mega__columns">{"".join(parts)}</div></div></div>'

    def tile_v2(name: str, price: str, colours: int, tid: str | None = None, badge: str = "") -> str:
        url = f"/products/{slug(name)}?variant=4{_h(name, 7, '0123456789')}"
        b = f'<span class="{vm("badge")}">{badge}</span>' if badge else ""
        return (f'<div class="{vm("slide")}" role="group" aria-roledescription="slide"><div class="{vm("card")}">'
                f'<div class="{vm("cardMedia")}"><img src="https://cdn.maisonlune.com/products/{slug(name)}.jpg?width=540" alt="" class="{vm("cardImg")}" loading="lazy">{b}'
                f'<button type="button" class="{vm("wish")}" aria-label="Save {e(name)}">{icon("heart", "", 18)}</button></div>'
                f'<a href="{url}" class="{vm("cardTitle")}">{e(name)}</a>'
                f'<div class="{vm("cardMeta")}"><span class="{vm("cardPrice")}"{gt(tid)}>${price}</span><span class="{vm("cardSwatches")}">{colours} colors</span></div>'
                f'</div></div>')

    def carousel_v2(title: str, items: list, href: str, next_tid: str | None = None, price_tid_for: str | None = None,
                    badges: dict | None = None) -> str:
        sid = slug(title)
        slides = "".join(tile_v2(n, p, c, "t4" if n == price_tid_for else None, (badges or {}).get(n, "")) for n, p, c in items)
        return f"""
  <section class="{vm("rail")}" aria-labelledby="{sid}-title" data-rail="{sid}">
    <div class="{vm("railHead")}">
      <h2 id="{sid}-title" class="{vm("railTitle")}">{title}</h2>
      <div class="{vm("railNav")}">
        <button type="button" class="{vm("railArrow")}" aria-label="Previous slide" disabled>{icon("chevron-left")}</button>
        <button type="button" class="{vm("railArrow")}" aria-label="Next slide"{gt(next_tid)}>{icon("chevron-right")}</button>
      </div>
    </div>
    <div class="{vm("railViewport")}"><div class="{vm("railTrack")}">{slides}</div></div>
    <a href="{href}" class="{vm("railMore")}">Shop all {title.lower()}</a>
  </section>"""

    best_v2 = [S06_BEST[0], S06_NEW_IN[1], S06_BEST[2], S06_BEST[1]] + S06_BEST[3:]
    new_v2 = [S06_NEW_IN[i] for i in (4, 0, 2, 1, 7, 3, 5, 6)] + [("Faux-Shearling Bomber Jacket", "198.00", 2)]
    mobile_women = "".join(f'<li><a href="/women/{slug(x)}" class="{vm("drawerLink")}">{e(x)}</a></li>' for x in women_cols_v2[0][1])
    tiles_v2 = "".join(
        f'<a href="/women/{slug(t)}" class="{vm("catTile")}"><img src="https://cdn.maisonlune.com/collections/women-{slug(t)}.jpg?width=480" alt="" class="{vm("catImg")}"><span class="{vm("catLabel")}">{e(t)}</span></a>'
        for t in ["Knitwear", "Coats & Jackets", "Dresses", "Denim", "Boots", "Bags", "Cashmere"]
    )
    body_v2 = f"""
<div id="app">
<div class="{vm("marquee")}" aria-label="Announcements"><p class="{vm("marqueeItem")}">Free shipping over $150</p><p class="{vm("marqueeItem")}">30-day free returns</p><p class="{vm("marqueeItem")}">Complimentary alterations on full-price trousers</p></div>
<div id="mobile-menu" class="{vm("drawer")}" role="dialog" aria-label="Menu" hidden>
  <button type="button" class="{vm("drawerClose")}" aria-label="Close menu">{icon("close")}</button>
  <details class="{vm("drawerGroup")}" open><summary class="{vm("drawerSummary")}">Women</summary><ul class="{vm("drawerList")}">{mobile_women}</ul></details>
  <details class="{vm("drawerGroup")}"><summary class="{vm("drawerSummary")}">Men</summary><ul class="{vm("drawerList")}"><li><a href="/men/knitwear" class="{vm("drawerLink")}">Knitwear</a></li><li><a href="/men/shirts" class="{vm("drawerLink")}">Shirts</a></li></ul></details>
</div>
<header class="{vm("header")}">
  <div class="{vm("headerBar")}">
    <button type="button" class="{vm("menuBtn")}" aria-controls="mobile-menu" aria-label="Open menu">{icon("menu")}</button>
    <a href="/" class="{vm("logo")}" aria-label="Maison Lune">MAISON LUNE</a>
    <div class="{vm("utilities")}">
      <button type="button" class="{vm("utilityBtn")}" aria-label="Search">{icon("search")}</button>
      <a href="/account/login" class="{vm("utilityBtn")}" aria-label="Sign in">{icon("user")}</a>
      <a href="/wishlist" class="{vm("utilityBtn")}" aria-label="Saved items">{icon("heart")}</a>
      <button type="button" class="{vm("utilityBtn")}" aria-label="Open bag (2 items)" aria-controls="bag-drawer" aria-haspopup="dialog"{gt("t6")}>{icon("bag")}<span class="{vm("bagCount")}">2</span></button>
    </div>
  </div>
  <ml-mega-nav>
    <template shadowrootmode="open">
      <style>:host{{display:block;border-top:1px solid #ece7df}}.nav__list{{display:flex;justify-content:center;gap:28px;list-style:none;margin:0;padding:0}}.mega[hidden]{{display:none}}.mega__columns{{display:grid;grid-template-columns:repeat(4,1fr);gap:40px;padding:32px 48px}}</style>
      <nav class="nav" aria-label="Main menu">
        <ul class="nav__list">
          <li class="nav__item"><a class="nav__link" href="/new-in">New In</a></li>
          <li class="nav__item nav__item--mega"><button type="button" class="nav__trigger" aria-expanded="false">Women</button>{mega_v2("women", women_cols_v2, "Knitwear")}</li>
          <li class="nav__item nav__item--mega"><button type="button" class="nav__trigger" aria-expanded="false">Men</button>{mega_v2("men", men_cols_v2)}</li>
          <li class="nav__item"><a class="nav__link" href="/kids">Kids</a></li>
          <li class="nav__item"><a class="nav__link" href="/home">Home</a></li>
          <li class="nav__item"><a class="nav__link" href="/gift-guide">Gift Guide</a></li>
          <li class="nav__item"><a class="nav__link nav__link--sale" href="/sale">Sale</a></li>
        </ul>
      </nav>
    </template>
  </ml-mega-nav>
</header>
<main class="{vm("page")}">
  <section class="{vm("hero")}">
    <div class="{vm("heroMedia")}"><video class="{vm("heroVideo")}" autoplay muted loop playsinline poster="https://cdn.maisonlune.com/campaign/autumn-26-poster.jpg"></video></div>
    <div class="{vm("heroOverlay")}">
      <div class="{vm("heroCopy")}">
        <h1 class="{vm("heroTitle")}">The Autumn Edit</h1>
        <p class="{vm("heroText")}">Soft tailoring, chunky knits and the coat you'll wear on repeat.</p>
        <div class="{vm("heroActions")}"><a href="/women/autumn-edit" class="{vm("button")} {vm("buttonLight")}"{gt("t2")}>Discover the edit</a><a href="/lookbook/autumn-2026" class="{vm("textLink")}">Watch the film</a></div>
      </div>
    </div>
  </section>
  <section class="{vm("cats")}" aria-label="Categories"><div class="{vm("catScroller")}">{tiles_v2}</div></section>
{carousel_v2("Bestsellers", best_v2, "/women/bestsellers", badges={"Wool-Blend Wrap Coat": "Bestseller"})}
  <section class="{vm("split")}">
    <div class="{vm("splitMedia")}"><img src="https://cdn.maisonlune.com/campaign/party-edit.jpg?width=900" alt="Sequinned midi dress on a model" class="{vm("splitImg")}"></div>
    <div class="{vm("splitCopy")}"><p class="{vm("eyebrow")}">Coming up</p><h2 class="{vm("splitTitle")}">The Party Edit</h2><p class="{vm("splitText")}">Velvet, sequins and satin for the season of celebrations.</p><a href="/women/party-edit" class="{vm("button")} {vm("buttonDark")}">Shop the edit</a></div>
  </section>
{carousel_v2("New In", new_v2, "/women/new-in", "t3", "Wool-Blend Wrap Coat", badges={"Faux-Shearling Bomber Jacket": "Just in"})}
  <section class="{vm("banner")}"><h2 class="{vm("bannerTitle")}">Up to 40% off knitwear</h2><p class="{vm("bannerText")}">Merino, cashmere and alpaca blends — this week only.</p><a href="/women/sale/knitwear" class="{vm("button")} {vm("buttonDark")}">Shop sale</a></section>
  <section class="{vm("journal")}" aria-labelledby="journal-h">
    <h2 id="journal-h" class="{vm("railTitle")}">Journal</h2>
    <div class="{vm("journalGrid")}">
      <a href="/journal/how-to-style-a-wrap-coat" class="{vm("story")}"><img src="https://cdn.maisonlune.com/journal/wrap-coat.jpg?width=600" alt="" class="{vm("storyImg")}"><span class="{vm("storyTitle")}">Three ways to style a wrap coat</span></a>
      <a href="/journal/cashmere-care-guide" class="{vm("story")}"><img src="https://cdn.maisonlune.com/journal/cashmere.jpg?width=600" alt="" class="{vm("storyImg")}"><span class="{vm("storyTitle")}">The cashmere care guide</span></a>
      <a href="/journal/visiting-our-wool-mill" class="{vm("story")}"><img src="https://cdn.maisonlune.com/journal/mill.jpg?width=600" alt="" class="{vm("storyImg")}"><span class="{vm("storyTitle")}">Inside our wool mill in Biella</span></a>
    </div>
  </section>
</main>
<div class="{vm("modal")}" role="dialog" aria-modal="true" aria-labelledby="popup-title" hidden>
  <div class="{vm("modalCard")}">
    <button type="button" class="{vm("modalClose")}" aria-label="Close">{icon("close")}</button>
    <h2 id="popup-title" class="{vm("modalTitle")}">Take 10% off your first order</h2>
    <form action="/api/subscribe" method="post" class="{vm("modalForm")}"><input type="email" name="email" placeholder="Email address" aria-label="Email address" class="{vm("input")}"><button type="submit" class="{vm("button")} {vm("buttonDark")}">Unlock 10% off</button></form>
  </div>
</div>
<footer class="{vm("footer")}">
  <div class="{vm("footerNewsletter")}">
    <h2 class="{vm("footerTitle")}">Join the Maison Lune list</h2>
    <p class="{vm("footerText")}">10% off your first order, early access to sales and new-season edits.</p>
    <form action="/api/subscribe" method="post" class="{vm("footerForm")}">
      <div class="{vm("field")}"><label for="email-:R2l6:" class="{vm("srOnly")}">Email address</label><input id="email-:R2l6:" type="email" name="email" placeholder="Email address" autocomplete="email" class="{vm("input")}"{gt("t5")}></div>
      <button type="submit" class="{vm("button")} {vm("buttonDark")}">Subscribe</button>
    </form>
  </div>
  <div class="{vm("footerLinks")}">
    <nav aria-label="Help" class="{vm("footerCol")}"><a href="/help/contact">Contact us</a><a href="/help/shipping">Shipping</a><a href="/help/returns">Returns &amp; exchanges</a><a href="/help/size-guide">Size guide</a><a href="/orders/track">Track your order</a></nav>
    <nav aria-label="About" class="{vm("footerCol")}"><a href="/about">Our story</a><a href="/responsibility">Responsibility</a><a href="/stores">Stores</a><a href="/careers">Careers</a></nav>
    <nav aria-label="Legal" class="{vm("footerCol")}"><a href="/legal/terms">Terms</a><a href="/legal/privacy">Privacy</a><a href="/legal/cookies">Cookies</a><a href="/accessibility">Accessibility</a></nav>
  </div>
  <p class="{vm("copyright")}">© 2026 Maison Lune · United States (USD $)</p>
</footer>
</div>
"""
    v2 = page(title="Women | Maison Lune", body=body_v2,
              css=f'.{vm("railTrack")}{{display:flex;gap:16px;overflow-x:auto;scroll-snap-type:x mandatory}}.{vm("slide")}{{flex:0 0 23%}}')

    meta = {
        "title": "Category landing with mega-menu, promo banners and product carousels — fashion store",
        "mutations": ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change",
                      "copy-change", "tag-change", "attribute-churn", "structure-move", "insertion"],
        "notes": (
            "v2 is a headless (Vite + CSS modules) rebuild. The primary navigation and mega-menus move into "
            "<ml-mega-nav>'s shadow root with a 'Featured' column first, re-ordered Clothing links and new URLs; a "
            "hidden mobile drawer and the Men menu also contain 'Knitwear' links. The hero CTA now reads 'Discover the "
            "edit' while a new 'Party Edit' module reuses 'Shop the edit'. Bestsellers now precedes New In and also "
            "features the Wool-Blend Wrap Coat at the same price; carousel arrows are relabelled 'Next slide'. The bag "
            "icon link becomes a drawer-toggle button, and the newsletter form moves to the footer (a hidden popup adds "
            "another email field)."
        ),
        "targets": [
            target("t1", "'Knitwear' link in the Women → Clothing column of the mega-menu",
                   "#mega-women .mega-col:first-child a[href='/women/clothing/knitwear']",
                   "//li[@id='nav-women']//div[@class='mega-col'][1]//a[normalize-space()='Knitwear']",
                   ["shadow-dom", "sibling-reorder", "decoy", "attribute-churn", "class-obfuscation", "structure-move"]),
            target("t2", "Hero call-to-action link of 'The Autumn Edit'",
                   ".hero .hero__cta",
                   "//a[normalize-space()='Shop the edit']",
                   ["copy-change", "decoy", "class-obfuscation", "wrapper-divs", "insertion"]),
            target("t3", "'Next' arrow button of the New In carousel",
                   "#carousel-new-in .carousel__next",
                   "//section[@aria-labelledby='new-in-heading']//button[@aria-label='Next']",
                   ["attribute-churn", "copy-change", "id-change", "sibling-reorder", "decoy", "class-obfuscation"]),
            target("t4", "Price ($248.00) of the 'Wool-Blend Wrap Coat' tile in the New In carousel",
                   "#carousel-new-in li:nth-child(2) .price",
                   "//h3[normalize-space()='Wool-Blend Wrap Coat']/following-sibling::p/span[@class='price']",
                   ["decoy", "sibling-reorder", "tag-change", "class-obfuscation", "wrapper-divs"]),
            target("t5", "Email input of the newsletter sign-up form",
                   "#newsletter-email",
                   "//form[@id='newsletter-form']//input[@type='email']",
                   ["id-change", "attribute-churn", "copy-change", "structure-move", "decoy", "wrapper-divs"]),
            target("t6", "Shopping bag icon in the header (shows 2 items)",
                   "a.header__icon--bag",
                   "//a[@aria-label='Bag, 2 items']",
                   ["tag-change", "attribute-churn", "copy-change", "class-obfuscation"]),
        ],
    }
    return v1, v2, meta


# ---------------------------------------------------------------------------
# ecommerce-07 — GreenBasket: grocery aisle with quantity steppers + mini-cart
# ---------------------------------------------------------------------------

S07_DEPTS_V1 = ["Produce", "Dairy & Eggs", "Meat & Seafood", "Bakery", "Deli", "Pantry", "Frozen", "Snacks",
                "Beverages", "Household", "Baby", "Pets"]
S07_DEPTS_V2 = ["Produce", "Dairy & Eggs", "Bakery & Bread", "Meat & Seafood", "Deli & Prepared", "Frozen", "Pantry",
                "Snacks", "Beverages", "Household", "Baby", "Pets"]
# shelf -> [(sku, name, size, price, unit price, badge)]
S07_SHELVES = {
    "Milk": [
        ("70014", "Organic Whole Milk", "1 gal", "6.49", "$0.05/fl oz", "Organic"),
        ("70022", "2% Reduced Fat Milk", "1 gal", "4.29", "$0.03/fl oz", ""),
        ("70031", "Lactose-Free Whole Milk", "52 fl oz", "4.79", "$0.09/fl oz", ""),
        ("70045", "Oat Milk Barista Edition", "32 fl oz", "4.99", "$0.16/fl oz", "Plant-based"),
        ("70052", "Unsweetened Almond Milk", "64 fl oz", "3.49", "$0.05/fl oz", "Plant-based"),
        ("70068", "Chocolate Whole Milk", "1/2 gal", "3.29", "$0.05/fl oz", ""),
    ],
    "Yogurt": [
        ("51200", "Greek Yogurt Plain", "32 oz", "5.99", "$0.19/oz", ""),
        ("51214", "Vanilla Bean Whole Milk Yogurt", "32 oz", "4.49", "$0.14/oz", ""),
        ("51227", "Strawberry Greek Yogurt Cups", "4 × 5.3 oz", "5.29", "$0.25/oz", ""),
        ("51239", "Icelandic Skyr Plain", "5.3 oz", "1.99", "$0.38/oz", ""),
        ("51246", "Coconut Yogurt Alternative", "16 oz", "5.49", "$0.34/oz", "Plant-based"),
        ("51251", "Plain Kefir", "32 fl oz", "4.29", "$0.13/fl oz", ""),
    ],
    "Eggs": [
        ("60311", "Large Brown Eggs", "12 ct", "4.49", "$0.37/ct", ""),
        ("60318", "Large White Eggs", "18 ct", "5.29", "$0.29/ct", ""),
        ("60325", "Pasture-Raised Large Eggs", "12 ct", "7.99", "$0.67/ct", "Pasture-raised"),
        ("60332", "Organic Free-Range Eggs", "12 ct", "6.49", "$0.54/ct", "Organic"),
        ("60347", "Liquid Egg Whites", "16 oz", "3.99", "$0.25/oz", ""),
    ],
    "Cheese": [
        ("64410", "Sharp Cheddar Block", "8 oz", "3.99", "$0.50/oz", ""),
        ("64428", "Fresh Mozzarella Ball", "8 oz", "4.49", "$0.56/oz", ""),
        ("64433", "Grated Parmesan", "5 oz", "4.99", "$1.00/oz", ""),
        ("64447", "Double Cream Brie", "7 oz", "6.99", "$1.00/oz", ""),
        ("64451", "Crumbled Feta", "6 oz", "3.79", "$0.63/oz", ""),
        ("64466", "Sliced Swiss", "8 oz", "4.29", "$0.54/oz", ""),
    ],
}
S07_IN_CART = {"51200": 1, "64410": 1}
# (sku, name, size, price, qty)
S07_CART = [
    ("11020", "Honeycrisp Apples", "3 lb bag", 6.99, 1),
    ("51200", "Greek Yogurt Plain", "32 oz", 5.99, 1),
    ("64410", "Sharp Cheddar Block", "8 oz", 3.99, 1),
    ("80115", "Sourdough Boule", "24 oz", 6.49, 1),
    ("12007", "Organic Baby Spinach", "5 oz", 3.99, 2),
]


def suite07() -> tuple[str, str, dict]:
    subtotal = sum(p * q for *_x, p, q in S07_CART)
    count = sum(q for *_x, q in S07_CART)
    sub_s = money(subtotal)
    to_free = money(35 - subtotal)

    # ---------------- v1 ----------------
    def tile_v1(item: tuple) -> str:
        sku, name, size, price, unit, badge = item
        b = f'<span class="badge badge--{slug(badge)}">{badge}</span>' if badge else ""
        if sku in S07_IN_CART:
            action = (f'<div class="stepper"><button type="button" class="stepper__dec" aria-label="Decrease quantity">{icon("minus", "", 16)}</button>'
                      f'<span class="stepper__count" aria-live="polite">{S07_IN_CART[sku]} in cart</span>'
                      f'<button type="button" class="stepper__inc" aria-label="Increase quantity"{gt("t2") if sku == "51200" else ""}>{icon("plus", "", 16)}</button></div>')
        else:
            action = f'<button type="button" class="add-btn" data-testid="add-to-cart-btn"{gt("t1") if sku == "70014" else ""}>Add</button>'
        return f"""
        <li class="product-tile" id="tile-{sku}" data-sku="{sku}" data-testid="product-tile-{sku}">
          <div class="product-tile__image"><img src="/img/products/{sku}_300.jpg" alt="{e(name)}, {e(size)}" width="150" height="150" loading="lazy">{b}</div>
          <div class="tile-price"><span class="price">${price}</span><span class="unit-price"{gt("t3") if sku == "60311" else ""}>{unit}</span></div>
          <h3 class="tile-name">{e(name)}</h3>
          <p class="tile-size">{e(size)}</p>
          <div class="tile-actions">{action}</div>
        </li>"""

    shelves_v1 = "".join(
        f"""
      <section class="shelf" id="shelf-{slug(shelf)}" aria-labelledby="shelf-{slug(shelf)}-title">
        <div class="shelf__header"><h2 class="shelf__title" id="shelf-{slug(shelf)}-title">{shelf}</h2><a class="shelf__see-all" href="/aisle/dairy-eggs/{slug(shelf)}">See all</a></div>
        <ul class="shelf__items">{"".join(tile_v1(i) for i in items)}
        </ul>
      </section>"""
        for shelf, items in S07_SHELVES.items()
    )
    depts_v1 = "\n".join(
        f'      <li class="aisle-nav__item{" is-active" if d == "Dairy & Eggs" else ""}"><a class="aisle-nav__link" href="/aisle/{slug(d)}"{gt("t6") if d == "Bakery" else ""}{CURRENT if d == "Dairy & Eggs" else ""}>{e(d)}</a></li>'
        for d in S07_DEPTS_V1
    )
    cart_v1 = "".join(
        f"""
        <li class="mini-cart__item">
          <img class="mini-cart__img" src="/img/products/{sku}_120.jpg" alt="" width="48" height="48">
          <div class="mini-cart__info"><p class="mini-cart__name">{e(name)}</p><p class="mini-cart__size">{e(size)}</p><p class="mini-cart__price">{money(price * qty)}</p></div>
          <div class="stepper stepper--small"><button type="button" class="stepper__dec" aria-label="Decrease quantity">{icon("minus", "", 14)}</button><span class="stepper__count">{qty}</span><button type="button" class="stepper__inc" aria-label="Increase quantity">{icon("plus", "", 14)}</button></div>
          <button type="button" class="remove-btn" title="Remove" aria-label="Remove"{gt("t5") if sku == "64410" else ""}>{icon("trash", "", 16)}</button>
        </li>"""
        for sku, name, size, price, qty in S07_CART
    )
    chips_v1 = "".join(
        f'<li><a class="chip{" chip--active" if c == "All" else ""}" href="/aisle/dairy-eggs{"" if c == "All" else "/" + slug(c)}">{e(c)}</a></li>'
        for c in ["All", "Milk", "Yogurt", "Eggs", "Cheese", "Butter & Cream", "Plant-based"]
    )
    body_v1 = f"""
<header class="gb-header">
  <div class="gb-header__inner">
    <a class="gb-header__logo" href="/">{icon("leaf", "gb-header__leaf", 28)}<span>GreenBasket</span></a>
    <button type="button" class="delivery-slot">{icon("truck", "delivery-slot__icon", 18)}<span class="delivery-slot__label">Delivery · Today 4–5 PM</span><span class="delivery-slot__address">11 Pine St, Apt 2</span></button>
    <form class="gb-search" role="search" action="/search"><label class="visually-hidden" for="gb-search-input">Search products</label><input id="gb-search-input" type="search" name="q" placeholder="Search 30,000+ products"><button type="submit" aria-label="Search">{icon("search")}</button></form>
    <a class="gb-header__account" href="/account">Hi, Priya</a>
    <button type="button" class="cart-toggle" aria-controls="mini-cart" aria-expanded="true">{icon("cart")}<span class="cart-toggle__count">{count}</span><span class="cart-toggle__total">{sub_s}</span></button>
  </div>
</header>
<div class="gb-layout">
  <nav class="aisle-nav" aria-label="Aisles">
    <h2 class="aisle-nav__title">Shop aisles</h2>
    <ul class="aisle-nav__list">
{depts_v1}
    </ul>
    <div class="aisle-nav__promo"><p>New customers: <strong>$0 delivery fee</strong> on your first 3 orders.</p></div>
  </nav>
  <main class="aisle" id="main">
    <nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">Home</a> / <span aria-current="page">Dairy &amp; Eggs</span></nav>
    <div class="aisle__header"><h1 class="aisle__title">Dairy &amp; Eggs</h1><p class="aisle__count">128 items</p></div>
    <ul class="subaisle-chips">{chips_v1}</ul>
    <div class="aisle__deal"><p><strong>Deal:</strong> Buy 2 Greek yogurts, save $1.00</p></div>
{shelves_v1}
  </main>
  <aside id="mini-cart" class="mini-cart is-open" role="dialog" aria-modal="false" aria-labelledby="mini-cart-title">
    <div class="mini-cart__header"><h2 class="mini-cart__title" id="mini-cart-title">Your cart ({count})</h2><button type="button" class="mini-cart__close" aria-label="Close cart">{icon("close")}</button></div>
    <div class="mini-cart__progress"><p>Add <strong>{to_free}</strong> to get free delivery</p><div class="progress"><span class="progress__fill" style="width:90%"></span></div></div>
    <ul class="mini-cart__items">{cart_v1}
    </ul>
    <div class="mini-cart__footer">
      <dl class="mini-cart__totals"><dt>Subtotal</dt><dd>{sub_s}</dd></dl>
      <p class="mini-cart__note">Delivery and service fees are calculated at checkout.</p>
      <a class="btn-checkout" href="/checkout" data-testid="mini-cart-checkout"{gt("t4")}>Checkout</a>
      <a class="mini-cart__view" href="/cart">View full cart</a>
    </div>
  </aside>
</div>
<footer class="gb-footer">
  <div class="gb-footer__cols">
    <div><h2>GreenBasket</h2><ul><li><a href="/about">About us</a></li><li><a href="/careers">Careers</a></li><li><a href="/sustainability">Sustainability</a></li><li><a href="/press">Press</a></li></ul></div>
    <div><h2>Help</h2><ul><li><a href="/help/delivery">Delivery areas &amp; times</a></li><li><a href="/help/substitutions">Substitutions</a></li><li><a href="/help/refunds">Refunds</a></li><li><a href="/help/contact">Contact us</a></li></ul></div>
    <div><h2>More ways to shop</h2><ul><li><a href="/pickup">Store pickup</a></li><li><a href="/plus">GreenBasket+</a></li><li><a href="/gift-cards">Gift cards</a></li><li><a href="/snap">SNAP/EBT</a></li></ul></div>
  </div>
  <p class="gb-footer__legal">© 2026 GreenBasket Inc. · <a href="/terms">Terms</a> · <a href="/privacy">Privacy</a> · Prices may differ from in-store.</p>
</footer>
"""
    css_v1 = """
body{margin:0;font:15px/1.45 "Rubik",system-ui,sans-serif;color:#1e2a22;background:#f7faf7}
.gb-header__inner{display:flex;align-items:center;gap:20px;padding:12px 24px;background:#fff;border-bottom:1px solid #dfe8e1}
.gb-layout{display:grid;grid-template-columns:220px 1fr 360px;gap:24px}
.aisle-nav__list{list-style:none;padding:0}.aisle-nav__item.is-active a{font-weight:700;color:#1d7a3e}
.shelf__items{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;list-style:none;padding:0}
.product-tile{background:#fff;border-radius:10px;padding:10px}.unit-price{display:block;font-size:12px;color:#5b6b60}
.add-btn{width:100%;border:1px solid #1d7a3e;color:#1d7a3e;border-radius:999px;background:#fff}
.mini-cart{position:sticky;top:0;height:100vh;background:#fff;border-left:1px solid #dfe8e1;padding:16px}
.btn-checkout{display:block;background:#1d7a3e;color:#fff;text-align:center;padding:12px;border-radius:999px}
.visually-hidden{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
"""
    v1 = page(title="Dairy & Eggs – GreenBasket grocery delivery", css=css_v1, body=body_v1, body_attrs=' class="page-aisle"')

    # ---------------- v2 ----------------
    C = {
        "tile": ax("display:flex", "flex-direction:column", "gap:6px", "padding:12px", "border-radius:14px", "background:#fff", "position:relative"),
        "img": ax("width:100%", "aspect-ratio:1", "object-fit:contain"),
        "priceRow": ax("display:flex", "align-items:baseline", "gap:6px"),
        "price": ax("font-size:17px", "font-weight:700"),
        "unit": ax("font-size:12px", "color:#5b6b60"),
        "name": ax("font-size:14px", "line-height:1.3", "margin:0"),
        "size": ax("font-size:12px", "color:#7a877e", "margin:0"),
        "add": ax("border-radius:999px", "background:#1d7a3e", "color:#fff", "padding:8px 12px", "font-weight:600"),
        "stepper": ax("display:flex", "align-items:center", "justify-content:space-between", "border-radius:999px", "background:#e8f4ec"),
        "stepBtn": ax("width:32px", "height:32px", "border-radius:50%", "display:grid", "place-items:center"),
        "badge": ax("position:absolute", "top:8px", "left:8px", "font-size:11px", "background:#fff3c4"),
        "grid": ax("display:grid", "grid-template-columns:repeat(auto-fill,minmax(160px,1fr))", "gap:12px"),
        "shelf": ax("margin-top:32px"),
        "shelfHead": ax("display:flex", "justify-content:space-between", "align-items:center"),
        "h2": ax("font-size:20px", "font-weight:700", "margin:0"),
        "link": ax("color:#1d7a3e", "font-weight:600"),
        "tab": ax("white-space:nowrap", "padding:10px 14px", "border-radius:999px", "color:#1e2a22"),
        "tabActive": ax("white-space:nowrap", "padding:10px 14px", "border-radius:999px", "background:#1e2a22", "color:#fff"),
        "wrap": ax("display:contents"),
    }

    def tile_v2(item: tuple, tids: bool = True) -> str:
        sku, name, size, price, unit, badge = item
        b = f'<span class="{C["badge"]}">{badge}</span>' if badge else ""
        if sku in S07_IN_CART:
            action = (f'<div class="{C["stepper"]}" role="group" aria-label="Quantity of {e(name)}">'
                      f'<button type="button" class="{C["stepBtn"]}" aria-label="Decrease {e(name)} quantity">{icon("minus", "", 16)}</button>'
                      f'<span class="{C["unit"]}">{S07_IN_CART[sku]}</span>'
                      f'<button type="button" class="{C["stepBtn"]}" aria-label="Increase {e(name)} quantity"{gt("t2") if (tids and sku == "51200") else ""}>{icon("plus", "", 16)}</button></div>')
        else:
            action = f'<button type="button" class="{C["add"]}" data-testid="ItemCard-addButton"{gt("t1") if (tids and sku == "70014") else ""}>Add to cart</button>'
        return f"""
          <div class="{C["tile"]}" role="listitem" data-item-id="itm_{_h(sku, 10, _B36)}" data-testid="ItemCard">
            <div class="{C["wrap"]}"><img src="https://img.greenbasket.com/p/{sku}.webp?w=320" alt="" class="{C["img"]}" loading="lazy">{b}</div>
            <div class="{C["priceRow"]}"><span class="{C["price"]}">${price}</span><span class="{C["unit"]}"{gt("t3") if (tids and sku == "60311") else ""}>{unit}</span></div>
            <h3 class="{C["name"]}">{e(name)}</h3>
            <p class="{C["size"]}">{e(size)}</p>
            <div class="{C["wrap"]}"><div class="{C["wrap"]}">{action}</div></div>
          </div>"""

    eggs = {i[0]: i for i in S07_SHELVES["Eggs"]}
    shelves_v2_order = [
        ("Eggs", [eggs["60325"], ("60309", "Large White Eggs", "12 ct", "4.49", "$0.37/ct", ""), eggs["60311"], eggs["60318"], eggs["60332"], eggs["60347"]]),
        ("Milk & Milk Alternatives", [S07_SHELVES["Milk"][i] for i in (1, 0, 4, 3, 2, 5)]),
        ("Yogurt & Kefir", [S07_SHELVES["Yogurt"][i] for i in (0, 3, 1, 2, 5, 4)]),
        ("Cheese", [S07_SHELVES["Cheese"][i] for i in (0, 2, 1, 4, 3, 5)]),
    ]
    shelves_v2 = "".join(
        f"""
      <section class="{C["shelf"]}" aria-labelledby="s-{slug(title)}">
        <div class="{C["shelfHead"]}"><h2 id="s-{slug(title)}" class="{C["h2"]}">{e(title)}</h2><a href="/store/dairy-eggs/{slug(title)}" class="{C["link"]}">View all</a></div>
        <div class="{C["grid"]}" role="list">{"".join(tile_v2(i) for i in items)}
        </div>
      </section>"""
        for title, items in shelves_v2_order
    )
    usuals = [S07_SHELVES["Milk"][0], S07_SHELVES["Yogurt"][1], S07_SHELVES["Eggs"][3], S07_SHELVES["Cheese"][1]]
    usuals_v2 = "".join(tile_v2(i, tids=False) for i in usuals)
    tabs_v2 = "".join(
        f'<a href="/store/{slug(d)}" class="{C["tabActive"] if d == "Dairy & Eggs" else C["tab"]}"{CURRENT if d == "Dairy & Eggs" else ""}{gt("t6") if d == "Bakery & Bread" else ""}>{e(d)}</a>'
        for d in S07_DEPTS_V2
    )
    drawer_depts = "".join(f'<li><a href="/store/{slug(d)}" class="{C["link"]}">{e(d)}</a></li>' for d in S07_DEPTS_V2)
    cart_order_v2 = ["12007", "80115", "64410", "51200", "11020"]
    by_sku = {c[0]: c for c in S07_CART}
    lines_v2 = "".join(
        f"""
            <li class="line">
              <img class="line__img" src="https://img.greenbasket.com/p/{sku}.webp?w=96" alt="">
              <div class="line__info"><span class="line__name">{e(name)}</span><span class="line__size">{e(size)}</span></div>
              <div class="line__qty" role="group" aria-label="Quantity of {e(name)}"><button type="button" class="line__step" aria-label="Decrease {e(name)} quantity">−</button><output class="line__count">{qty}</output><button type="button" class="line__step" aria-label="Increase {e(name)} quantity">+</button></div>
              <span class="line__price">{money(price * qty)}</span>
              <button type="button" class="line__remove" aria-label="Remove {e(name)}, {e(size)}"{gt("t5") if sku == "64410" else ""}><svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="{ICONS["trash"]}"/></svg></button>
            </li>"""
        for sku, name, size, price, qty in (by_sku[s] for s in cart_order_v2)
    )
    body_v2 = f"""
<div id="gb-root">
<header class="{ax("position:sticky", "top:0", "z-index:20", "background:#fff", "box-shadow:0 1px 0 #dfe8e1")}">
  <div class="{ax("display:flex", "align-items:center", "gap:16px", "padding:10px 20px")}">
    <button type="button" class="{ax("display:none", "padding:8px")}" aria-label="All departments" aria-controls="dept-drawer">{icon("menu")}</button>
    <a href="/" class="{ax("display:flex", "align-items:center", "gap:6px", "font-weight:800", "color:#1d7a3e")}" aria-label="GreenBasket home">{icon("leaf", "", 26)}<span>greenbasket</span></a>
    <form role="search" action="/search" class="{ax("flex:1", "position:relative")}"><input type="search" name="q" placeholder="Search groceries" aria-label="Search groceries" class="{ax("width:100%", "border-radius:999px", "padding:10px 16px", "background:#f1f5f2")}"></form>
    <button type="button" class="{ax("display:flex", "flex-direction:column", "font-size:12px", "text-align:left")}"><span>Delivering to 11 Pine St</span><b>Today, 4–5 PM</b></button>
    <a href="/account" class="{ax("padding:8px", "border-radius:50%")}" aria-label="Account">{icon("user")}</a>
    <button type="button" class="{ax("display:flex", "gap:6px", "align-items:center", "padding:8px 14px", "border-radius:999px", "background:#1d7a3e", "color:#fff")}" aria-controls="cart-drawer" aria-label="Cart, {count} items, {sub_s}">{icon("cart")}<span>{count}</span></button>
  </div>
  <nav aria-label="Departments" class="{ax("display:flex", "gap:4px", "overflow-x:auto", "padding:6px 20px")}">{tabs_v2}</nav>
</header>
<div id="dept-drawer" class="{ax("position:fixed", "inset:0", "background:#fff")}" role="dialog" aria-label="All departments" hidden>
  <h2 class="{C["h2"]}">All departments</h2>
  <ul class="{ax("list-style:none", "padding:0", "display:grid", "gap:12px")}">{drawer_depts}</ul>
</div>
<main class="{ax("max-width:1280px", "margin:0 auto", "padding:16px 20px 48px")}">
  <ol class="{ax("display:flex", "gap:6px", "font-size:13px", "list-style:none", "padding:0")}" aria-label="Breadcrumb"><li><a href="/">Home</a></li><li aria-hidden="true">›</li><li aria-current="page">Dairy &amp; Eggs</li></ol>
  <div class="{ax("display:flex", "align-items:baseline", "gap:12px")}"><h1 class="{ax("font-size:28px", "font-weight:800", "margin:0")}">Dairy &amp; Eggs</h1><span class="{C["unit"]}">128 items</span></div>
  <div class="{ax("margin-top:12px", "padding:12px 16px", "border-radius:12px", "background:#fff3c4")}"><p>Buy 2 Greek yogurts, save $1.00 · Ends Sunday</p></div>
  <section class="{C["shelf"]}" aria-labelledby="usuals-h">
    <div class="{C["shelfHead"]}"><h2 id="usuals-h" class="{C["h2"]}">Your usuals</h2><a href="/account/purchases" class="{C["link"]}">Past purchases</a></div>
    <div class="{C["grid"]}" role="list">{usuals_v2}
    </div>
  </section>
{shelves_v2}
</main>
<gb-cart-drawer id="cart-drawer" open placement="right">
  <template shadowrootmode="open">
    <style>:host{{position:fixed;top:0;right:0;bottom:0;width:380px;background:#fff;box-shadow:-8px 0 24px rgba(0,0,0,.08);display:flex;flex-direction:column}}.line{{display:grid;grid-template-columns:48px 1fr auto auto auto;gap:10px;align-items:center;padding:10px 0}}.checkout{{display:flex;justify-content:space-between;width:100%;border-radius:999px;background:#1d7a3e;color:#fff;padding:14px 18px;font-weight:700}}</style>
    <div class="drawer">
      <header class="drawer__head"><h2 class="drawer__title">Cart</h2><span class="drawer__count">{count} items</span><button type="button" class="drawer__close" aria-label="Close cart">×</button></header>
      <div class="drawer__meter" role="status"><span>You're {to_free} away from free delivery</span><progress max="35" value="{subtotal:.2f}"></progress></div>
      <ul class="drawer__lines">{lines_v2}
      </ul>
      <footer class="drawer__foot">
        <p class="drawer__fees">Fees and taxes calculated at checkout</p>
        <button type="button" class="checkout"{gt("t4")}>Go to checkout <span class="checkout__total">{sub_s}</span></button>
        <a href="/cart" class="drawer__full">View cart</a>
      </footer>
    </div>
  </template>
</gb-cart-drawer>
<footer class="{ax("background:#1e2a22", "color:#e6efe8", "padding:40px 20px")}">
  <div class="{ax("display:grid", "grid-template-columns:repeat(3,1fr)", "gap:24px")}">
    <nav aria-label="Company"><a href="/about">About</a> · <a href="/careers">Careers</a> · <a href="/sustainability">Sustainability</a></nav>
    <nav aria-label="Help"><a href="/help/delivery">Delivery areas</a> · <a href="/help/substitutions">Substitutions</a> · <a href="/help/refunds">Refunds</a> · <a href="/help/contact">Contact</a></nav>
    <nav aria-label="Shop"><a href="/pickup">Pickup</a> · <a href="/plus">GreenBasket+</a> · <a href="/gift-cards">Gift cards</a> · <a href="/snap">SNAP/EBT</a></nav>
  </div>
  <p class="{ax("margin-top:24px", "font-size:12px", "opacity:.7")}">© 2026 GreenBasket Inc. Prices may differ from in-store.</p>
</footer>
</div>
"""
    v2 = page(title="Dairy & Eggs | GreenBasket", body=body_v2,
              head='<link rel="preconnect" href="https://img.greenbasket.com">\n')

    meta = {
        "title": "Grocery delivery aisle with quantity steppers and mini-cart drawer",
        "mutations": ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change",
                      "testid-change", "copy-change", "tag-change", "attribute-churn", "structure-move", "insertion"],
        "notes": (
            "v2 switches to atomic (StyleX-like) class names. The left aisle list becomes a horizontal department tab "
            "bar with merged/renamed departments ('Bakery' → 'Bakery & Bread') plus a hidden 'All departments' drawer "
            "repeating the links. Shelves are renamed and re-ordered (Eggs first), tiles lose ids/data-sku and are "
            "re-ordered (per-SKU data-testids collapse to a generic 'ItemCard'); 'Add' becomes 'Add to cart'; stepper "
            "buttons get product-specific labels. A 'Your usuals' "
            "rail repeats Organic Whole Milk, and a new 'Large White Eggs, 12 ct' tile has the same unit price as the "
            "brown eggs. The mini-cart moves into <gb-cart-drawer>'s shadow root with lines newest-first, icon-only "
            "remove buttons labelled per product and a 'Go to checkout' button."
        ),
        "targets": [
            target("t1", "'Add' button on the 'Organic Whole Milk, 1 gal' tile",
                   "[data-testid='product-tile-70014'] [data-testid='add-to-cart-btn']",
                   "//li[.//h3[normalize-space()='Organic Whole Milk']]//button[normalize-space()='Add']",
                   ["copy-change", "testid-change", "decoy", "class-obfuscation", "attribute-churn", "wrapper-divs", "sibling-reorder"]),
            target("t2", "Increase-quantity (+) button on the 'Greek Yogurt Plain, 32 oz' tile (already in cart)",
                   "#tile-51200 .stepper__inc",
                   "//li[@data-sku='51200']//button[@aria-label='Increase quantity']",
                   ["attribute-churn", "id-change", "class-obfuscation", "sibling-reorder", "wrapper-divs"]),
            target("t3", "Unit price label ($0.37/ct) of the 'Large Brown Eggs, 12 ct' tile",
                   "#tile-60311 .unit-price",
                   "//h3[normalize-space()='Large Brown Eggs']/preceding-sibling::div[@class='tile-price']/span[@class='unit-price']",
                   ["decoy", "id-change", "class-obfuscation", "sibling-reorder", "insertion"]),
            target("t4", "'Checkout' button in the mini-cart drawer",
                   "#mini-cart .btn-checkout",
                   "//aside[@id='mini-cart']//a[normalize-space()='Checkout']",
                   ["shadow-dom", "tag-change", "copy-change", "class-obfuscation", "id-change", "testid-change"]),
            target("t5", "Remove (trash) icon button of the 'Sharp Cheddar Block, 8 oz' line in the mini-cart",
                   "#mini-cart li:nth-child(3) .remove-btn",
                   "(//aside[@id='mini-cart']//button[@title='Remove'])[3]",
                   ["shadow-dom", "sibling-reorder", "attribute-churn", "class-obfuscation"]),
            target("t6", "'Bakery' link in the aisle navigation",
                   ".aisle-nav li:nth-child(4) > a",
                   "//nav[@aria-label='Aisles']//a[normalize-space()='Bakery']",
                   ["copy-change", "structure-move", "sibling-reorder", "decoy", "class-obfuscation", "attribute-churn"]),
        ],
    }
    return v1, v2, meta


# ---------------------------------------------------------------------------
# ecommerce-08 — Harbor Lane Home: account order history with order cards
# ---------------------------------------------------------------------------

# order id, placed (long), placed short, total, status, status note, items [(sku, title, price)], kind
S08_ORDERS = [
    ("HL-114-8823901", "November 2, 2026", "Nov 2", "$276.79", "Arriving Friday", "Shipped via Harbor Freight Ground · Out for delivery Nov 6",
     [("LSS-Q-FOG", "Stonewashed Linen Sheet Set, Queen – Fog", "$189.00"), ("WWT-4-WHT", "Waffle-Weave Bath Towels, Set of 4 – White", "$64.00")], "transit"),
    ("HL-114-7781234", "October 19, 2026", "Oct 19", "$86.40", "Delivered October 24", "Your package was left near the front door.",
     [("CTL-LIN-IVY", "Ceramic Table Lamp with Linen Shade", "$79.00")], "returnable"),
    ("HL-113-6650912", "September 28, 2026", "Sep 28", "$268.92", "Delivered October 3", "Return window closed on November 2, 2026.",
     [("LDC-Q-OAT", "Linen Duvet Cover Set, Queen – Oat", "$219.00"), ("DAP-STD-2", "Down-Alternative Pillows, Standard (Set of 2)", "$29.00")], "closed"),
    ("HL-113-5521847", "August 14, 2026", "Aug 14", "$142.17", "Delivered August 19", "Return window closed on September 18, 2026.",
     [("AWS-BRD-L", "Acacia Wood Serving Board", "$48.00"), ("HGS-MUG-4", "Hand-Glazed Stoneware Mugs, Set of 4", "$56.00"), ("LNP-6-SAG", "Linen Napkins, Set of 6 – Sage", "$26.00")], "closed"),
]
S08_NEW_ORDER = ("HL-114-9012775", "November 4, 2026", "Nov 4", "$26.16", "Delivered today", "Delivered by Harbor Lane Local Courier at 11:42 AM.",
                 [("BTC-6-NAT", "Beeswax Taper Candles, Set of 6", "$24.00")], "returnable")
S08_DEPTS = ["Furniture", "Bedding", "Bath", "Kitchen & Dining", "Decor", "Lighting", "Rugs", "Outdoor", "Sale"]


def pd(*tokens: str) -> str:
    """Panda-CSS style atomic utility classes (``d_flex``, ``gap_4``, ``c_gray.600``)."""
    return " ".join(tokens)


def suite08() -> tuple[str, str, dict]:
    # ---------------- v1 ----------------
    def card_v1(order: tuple) -> str:
        oid, placed, _short, total, status, note, items, kind = order
        lis = "".join(
            f"""
              <li class="order-item" data-item-sku="{sku}">
                <img class="order-item__img" src="/media/catalog/{sku.lower()}_160.jpg" alt="" width="80" height="80">
                <div class="order-item__info">
                  <a class="order-item__title" href="/p/{slug(title)}">{e(title)}</a>
                  <p class="order-item__price">{price}</p>
                  {'<p class="order-item__return">Return eligible through November 23, 2026</p>' if kind == "returnable" else ""}
                  <div class="order-item__actions"><button type="button" class="buy-again-btn"{gt("t3") if sku == "LDC-Q-OAT" else ""}>{icon("return", "buy-again-btn__icon", 16)} Buy it again</button><a class="order-item__view" href="/p/{slug(title)}">View your item</a></div>
                </div>
              </li>"""
            for sku, title, price in items
        )
        actions = []
        if kind == "transit":
            actions.append(f'<a class="action-link action-link--primary btn-track" href="/account/orders/{oid}/track"{gt("t1") if oid == "HL-114-8823901" else ""}>Track package</a>')
            actions.append(f'<a class="action-link" href="/account/orders/{oid}/problem">Problem with order</a>')
        if kind == "returnable":
            actions.append(f'<a class="action-link action-link--primary" href="/account/orders/{oid}/track">Track package</a>')
            actions.append(f'<a class="action-link return-link" href="/account/orders/{oid}/return"{gt("t2") if oid == "HL-114-7781234" else ""}>Return or replace items</a>')
        actions.append(f'<a class="action-link" href="/account/orders/{oid}/review">Write a product review</a>')
        actions.append(f'<a class="action-link" href="/help/orders/{oid}">Get product support</a>')
        return f"""
        <div class="order-card" id="order-{oid}" data-order-id="{oid}">
          <div class="order-card__header">
            <div class="order-header__col"><span class="label">Order placed</span><span class="value">{placed}</span></div>
            <div class="order-header__col order-total"><span class="label">Total</span><span class="value"{gt("t5") if oid == "HL-114-7781234" else ""}>{total}</span></div>
            <div class="order-header__col"><span class="label">Ship to</span><span class="value"><a class="ship-to-link" href="#ship-{oid}">Dana Whitfield</a></span></div>
            <div class="order-header__col order-header__col--right"><span class="label">Order # {oid}</span><span class="value"><a href="/account/orders/{oid}">View order details</a> | <a href="/account/orders/{oid}/invoice">Invoice</a></span></div>
          </div>
          <div class="order-card__body">
            <div class="shipment">
              <h3 class="shipment__status shipment__status--{kind}">{status}</h3>
              <p class="shipment__note">{note}</p>
              <ul class="order-items">{lis}
              </ul>
            </div>
            <div class="order-card__actions">{"".join(actions)}</div>
          </div>
        </div>"""

    cards_v1 = "".join(card_v1(o) for o in S08_ORDERS)
    depts_v1 = "".join(f'<li class="hl-nav__item"><a class="hl-nav__link" href="/c/{slug(d)}">{e(d)}</a></li>' for d in S08_DEPTS)
    acct_links = ["Orders & returns", "Addresses", "Payment methods", "Harbor Rewards", "Registry & lists", "Account settings", "Sign out"]
    acct_v1 = "".join(
        f'<li class="account-nav__item{" is-active" if i == 0 else ""}"><a class="account-nav__link" href="/account/{slug(x)}"{CURRENT if i == 0 else ""}>{e(x)}</a></li>'
        for i, x in enumerate(acct_links)
    )
    body_v1 = f"""
<header class="hl-header">
  <div class="hl-header__promo"><p>Free shipping on furniture over $499 · Members save an extra 10% this week</p></div>
  <div class="hl-header__main">
    <a class="hl-logo" href="/">Harbor Lane <span class="hl-logo__sub">Home</span></a>
    <form class="hl-search" role="search" action="/search"><label class="visually-hidden" for="hl-search-q">Search</label><input id="hl-search-q" type="search" name="q" placeholder="Search furniture, bedding, decor…"><button type="submit" class="hl-search__btn">Search</button></form>
    <div class="hl-header__account">
      <a class="hl-account-link" href="/account">{icon("user", "", 18)}<span>Hi, Dana</span></a>
      <a class="hl-cart-link" href="/cart" aria-label="Cart, 1 item">{icon("cart", "", 20)}<span class="hl-cart-link__count">1</span></a>
    </div>
  </div>
  <nav class="hl-nav" aria-label="Departments"><ul class="hl-nav__list">{depts_v1}</ul></nav>
</header>
<main class="account-page">
  <nav class="account-breadcrumb" aria-label="Breadcrumb"><a href="/account">Your Account</a> <span aria-hidden="true">›</span> <span aria-current="page">Your Orders</span></nav>
  <div class="account-layout">
    <aside class="account-nav" aria-label="Account">
      <h2 class="account-nav__title">My account</h2>
      <ul class="account-nav__list">{acct_v1}</ul>
      <div class="account-nav__rewards"><p class="rewards__label">Harbor Rewards</p><p class="rewards__points">1,240 points</p><a href="/account/harbor-rewards">Redeem</a></div>
    </aside>
    <section class="orders" aria-labelledby="orders-title">
      <div class="orders__header">
        <h1 class="orders__title" id="orders-title">Your orders</h1>
        <form class="orders-search" action="/account/orders/search" method="get" role="search">
          <label class="visually-hidden" for="search-orders-input">Search all orders</label>
          <input id="search-orders-input" type="search" name="search" placeholder="Search all orders"{gt("t6")}>
          <button type="submit" class="orders-search__btn">Search orders</button>
        </form>
      </div>
      <ul class="order-tabs" role="tablist">
        <li class="order-tabs__item"><a class="order-tabs__link is-active" href="/account/orders" role="tab" aria-selected="true">Orders</a></li>
        <li class="order-tabs__item"><a class="order-tabs__link" href="/account/orders/buy-again" role="tab" aria-selected="false">Buy Again</a></li>
        <li class="order-tabs__item"><a class="order-tabs__link" href="/account/orders/open" role="tab" aria-selected="false">Not Yet Shipped</a></li>
        <li class="order-tabs__item"><a class="order-tabs__link" href="/account/orders/cancelled" role="tab" aria-selected="false">Cancelled Orders</a></li>
      </ul>
      <div class="orders__filter">
        <p class="orders__count"><strong>4 orders</strong> placed in</p>
        <label class="visually-hidden" for="time-filter">Filter orders by date</label>
        <select class="orders__select" id="time-filter" name="timeFilter"{gt("t4")}>
          <option value="last30">last 30 days</option>
          <option value="months-3" selected>past 3 months</option>
          <option value="year-2026">2026</option>
          <option value="year-2025">2025</option>
          <option value="year-2024">2024</option>
          <option value="archived">Archived orders</option>
        </select>
      </div>
      <div class="orders__list">{cards_v1}
      </div>
      <nav class="orders__pagination" aria-label="Order pages"><span class="is-current" aria-current="page">1</span> <a href="/account/orders?page=2">2</a> <a href="/account/orders?page=2" rel="next">Next →</a></nav>
    </section>
  </div>
</main>
<footer class="hl-footer">
  <div class="hl-footer__cols">
    <div class="hl-footer__col"><h2>Customer service</h2><ul><li><a href="/help">Help center</a></li><li><a href="/help/delivery">Delivery &amp; assembly</a></li><li><a href="/help/returns">Returns</a></li><li><a href="/help/protection">Furniture protection plans</a></li></ul></div>
    <div class="hl-footer__col"><h2>Harbor Lane</h2><ul><li><a href="/about">About us</a></li><li><a href="/showrooms">Showrooms</a></li><li><a href="/design-services">Free design services</a></li><li><a href="/trade">Trade program</a></li></ul></div>
    <div class="hl-footer__col"><h2>Stay in touch</h2><p>Get design inspiration and member-only offers.</p><a class="hl-footer__signup" href="/newsletter">Sign up for emails</a></div>
  </div>
  <p class="hl-footer__legal">© 2026 Harbor Lane Home, Inc. · <a href="/privacy">Privacy</a> · <a href="/terms">Terms</a> · <a href="/accessibility">Accessibility</a></p>
</footer>
"""
    css_v1 = """
body{margin:0;font:15px/1.5 "Lato",Helvetica,Arial,sans-serif;color:#2d2a26;background:#faf8f5}
.hl-header__main{display:flex;align-items:center;gap:24px;padding:16px 32px;background:#fff}
.hl-nav__list{display:flex;gap:24px;list-style:none;margin:0;padding:8px 32px;border-top:1px solid #ece6dd}
.account-layout{display:grid;grid-template-columns:220px 1fr;gap:32px;padding:0 32px}
.order-card{border:1px solid #ddd5ca;border-radius:8px;margin-bottom:20px;background:#fff}
.order-card__header{display:grid;grid-template-columns:1fr 1fr 1fr 2fr;gap:16px;padding:12px 16px;background:#f3efe9;font-size:13px}
.order-card__actions{display:flex;flex-direction:column;gap:8px;min-width:220px}
.action-link{display:block;text-align:center;border:1px solid #c9bfb2;border-radius:6px;padding:8px}
.action-link--primary{background:#2d4b5a;color:#fff}
.visually-hidden{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
"""
    v1 = page(title="Your Orders | Harbor Lane Home", css=css_v1, body=body_v1, body_attrs=' class="account orders-page"')

    # ---------------- v2 ----------------
    def card_v2(order: tuple) -> str:
        oid, placed, short, total, status, note, items, kind = order
        lis = "".join(
            f"""
              <li class="item">
                <img class="item__img" src="https://images.harborlane.com/catalog/{sku.lower()}.jpg?w=160" alt="">
                <div class="item__text"><a class="item__name" href="/p/{slug(title)}">{e(title)}</a><span class="item__price">{price}</span>{'<span class="item__note">Eligible for return until Nov 23, 2026</span>' if kind == "returnable" else ""}</div>
                <div class="item__actions"><button type="button" class="action action--accent"{gt("t3") if sku == "LDC-Q-OAT" else ""}><svg class="action__icon" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="{ICONS["return"]}"/></svg>Buy again</button><a class="action" href="/p/{slug(title)}">View item</a></div>
              </li>"""
            for sku, title, price in items
        )
        actions = []
        if kind in ("transit", "returnable"):
            actions.append(f'<button type="button" class="action action--primary" data-href="/orders/{oid}/tracking"{gt("t1") if oid == "HL-114-8823901" else ""}>Track shipment</button>')
        if kind == "returnable":
            actions.append(f'<a class="action" href="/orders/{oid}/returns/new"{gt("t2") if oid == "HL-114-7781234" else ""}>Return or replace items</a>')
        if kind == "transit":
            actions.append(f'<a class="action" href="/help/orders/{oid}">Report a problem</a>')
        actions.append(f'<a class="action" href="/orders/{oid}/reviews">Review your purchase</a>')
        return f"""
        <hl-order-card order-id="{oid}" status="{kind}">
          <template shadowrootmode="open">
            <style>:host{{display:block;margin-bottom:16px}}.card{{border-radius:16px;background:#fff;box-shadow:0 1px 2px rgba(0,0,0,.06)}}.meta{{display:flex;gap:32px;margin:0}}.action{{display:inline-flex;align-items:center;gap:6px;border:1px solid #d6cec3;border-radius:999px;padding:8px 14px}}.action--primary{{background:#1f3a47;color:#fff}}</style>
            <article class="card" aria-label="Order placed {placed}">
              <header class="card__head">
                <dl class="meta">
                  <div class="meta__item"><dt>Order placed</dt><dd>{placed}</dd></div>
                  <div class="meta__item"><dt>Total</dt><dd{gt("t5") if oid == "HL-114-7781234" else ""}>{total}</dd></div>
                  <div class="meta__item"><dt>Ship to</dt><dd>Dana W.</dd></div>
                </dl>
                <div class="card__ids"><span class="card__number">#{oid}</span><a href="/orders/{oid}">Details</a><a href="/orders/{oid}/invoice.pdf">Invoice</a></div>
              </header>
              <div class="card__body">
                <div class="card__status"><p class="status status--{kind}">{status}</p><p class="status__note">{note}</p></div>
                <div class="card__grid">
                  <ul class="items">{lis}
                  </ul>
                  <div class="card__actions">{"".join(actions)}</div>
                </div>
              </div>
            </article>
          </template>
        </hl-order-card>"""

    cards_v2 = "".join(card_v2(o) for o in [S08_NEW_ORDER] + S08_ORDERS)
    rail = [("LDC-Q-OAT", "Linen Duvet Cover Set, Queen – Oat", "$219.00"), ("WWT-4-WHT", "Waffle-Weave Bath Towels, Set of 4 – White", "$64.00"),
            ("HGS-MUG-4", "Hand-Glazed Stoneware Mugs, Set of 4", "$56.00"), ("BTC-6-NAT", "Beeswax Taper Candles, Set of 6", "$24.00")]
    rail_v2 = "".join(
        f'<li class="{pd("d_flex", "flex-d_column", "gap_2", "p_3", "bg_white", "rounded_xl", "min-w_48")}"><img src="https://images.harborlane.com/catalog/{sku.lower()}.jpg?w=200" alt="" class="{pd("w_full", "aspect_square", "object_cover", "rounded_lg")}">'
        f'<a href="/p/{slug(t)}" class="{pd("fs_sm", "fw_medium", "line-clamp_2")}">{e(t)}</a><span class="{pd("fs_sm", "c_gray.600")}">{p}</span>'
        f'<button type="button" class="{pd("d_inline-flex", "jc_center", "rounded_full", "bdr_1px_solid", "px_3", "py_1.5", "fs_sm", "fw_semibold")}">Buy again</button></li>'
        for sku, t, p in rail
    )
    depts_v2 = "".join(f'<a href="/shop/{slug(d)}" class="{pd("fs_sm", "fw_medium", "c_slate.800", "hover:c_teal.700")}">{e(d)}</a>' for d in ["New", "Furniture", "Bedding", "Bath", "Kitchen", "Decor", "Lighting", "Rugs", "Outdoor", "Sale"])
    acct_v2 = "".join(
        f'<a href="/account/{slug(x)}" class="{pd("d_block", "px_3", "py_2", "rounded_md", "bg_slate.100" if i == 0 else "bg_transparent")}"{CURRENT if i == 0 else ""}>{e(x)}</a>'
        for i, x in enumerate(["Orders", "Returns", "Addresses", "Wallet", "Harbor Rewards", "Lists & registry", "Settings"])
    )
    body_v2 = f"""
<div id="root">
<div class="{pd("bg_teal.900", "c_white", "fs_xs", "ta_center", "py_2")}">Members save an extra 10% this week · Free shipping on furniture over $499</div>
<header class="{pd("pos_sticky", "top_0", "z_20", "bg_white", "bdr-b_1px_solid", "bdr-c_stone.200")}">
  <div class="{pd("d_flex", "ai_center", "gap_6", "px_8", "py_3")}">
    <a href="/" class="{pd("fs_xl", "fw_bold", "ls_tight", "c_teal.900")}">harbor lane</a>
    <form role="search" action="/search" class="{pd("flex_1", "pos_relative")}"><input type="search" name="q" aria-label="Search Harbor Lane" placeholder="What are you looking for?" class="{pd("w_full", "rounded_full", "bg_stone.100", "px_5", "py_2.5")}"></form>
    <a href="/account" class="{pd("d_flex", "ai_center", "gap_2", "fs_sm")}">{icon("user", "", 18)}<span>Dana</span></a>
    <a href="/cart" class="{pd("pos_relative", "p_2")}" aria-label="Cart (1)">{icon("cart", "", 20)}</a>
  </div>
  <nav aria-label="Shop" class="{pd("d_flex", "gap_6", "px_8", "pb_3", "overflow-x_auto")}">{depts_v2}</nav>
</header>
<main class="{pd("maxW_7xl", "mx_auto", "px_8", "py_8", "d_grid", "gridTemplateColumns_240px_1fr", "gap_10")}">
  <nav aria-label="Account" class="{pd("d_flex", "flex-d_column", "gap_1", "fs_sm")}">{acct_v2}</nav>
  <div class="{pd("d_flex", "flex-d_column", "gap_6")}">
    <div class="{pd("d_flex", "flex-wrap_wrap", "ai_center", "jc_space-between", "gap_4")}">
      <h1 class="{pd("fs_3xl", "fw_semibold", "ls_tight")}">Orders &amp; returns</h1>
      <div class="{pd("d_flex", "ai_center", "gap_3")}">
        <form action="/account/orders/search" method="get" role="search" class="{pd("pos_relative")}">
          <span class="{pd("pos_absolute", "left_3", "top_2.5", "c_stone.400")}">{icon("search", "", 16)}</span>
          <input type="search" name="q" id="orders-q" aria-label="Search orders" placeholder="Search orders, items or tracking #" class="{pd("rounded_full", "bdr_1px_solid", "pl_9", "pr_4", "py_2", "fs_sm", "w_72")}"{gt("t6")}>
        </form>
        <div class="{pd("d_flex", "ai_center", "gap_2")}">
          <label for="orders-range" class="{pd("fs_sm", "c_stone.600")}">Showing</label>
          <select id="orders-range" name="timeFilter" class="{pd("rounded_full", "bdr_1px_solid", "px_4", "py_2", "fs_sm")}"{gt("t4")}>
            <option value="30d">Last 30 days</option>
            <option value="3m" selected>Last 3 months</option>
            <option value="2026">2026</option>
            <option value="2025">2025</option>
            <option value="2024">2024</option>
            <option value="archived">Archived</option>
          </select>
        </div>
      </div>
    </div>
    <div role="tablist" aria-label="Order views" class="{pd("d_flex", "gap_2", "bdr-b_1px_solid", "bdr-c_stone.200")}">
      <a role="tab" aria-selected="true" href="/account/orders" class="{pd("px_4", "py_2", "bdr-b_2px_solid", "fw_semibold")}">All orders <span class="{pd("fs_xs", "c_stone.500")}">5</span></a>
      <a role="tab" aria-selected="false" href="/account/orders/open" class="{pd("px_4", "py_2", "c_stone.600")}">In progress</a>
      <a role="tab" aria-selected="false" href="/account/orders/returns" class="{pd("px_4", "py_2", "c_stone.600")}">Returns</a>
      <a role="tab" aria-selected="false" href="/account/orders/cancelled" class="{pd("px_4", "py_2", "c_stone.600")}">Cancelled</a>
    </div>
    <section aria-labelledby="buy-again-h" class="{pd("bg_stone.50", "rounded_2xl", "p_5")}">
      <div class="{pd("d_flex", "jc_space-between", "ai_center")}"><h2 id="buy-again-h" class="{pd("fs_lg", "fw_semibold")}">Buy again</h2><a href="/account/orders/buy-again" class="{pd("fs_sm", "td_underline")}">See all</a></div>
      <ul class="{pd("d_flex", "gap_4", "mt_4", "overflow-x_auto")}">{rail_v2}</ul>
    </section>
    <div class="{pd("d_flex", "flex-d_column")}">{cards_v2}
    </div>
    <nav aria-label="Pagination" class="{pd("d_flex", "jc_center", "gap_2")}"><a aria-current="page" class="{pd("px_3", "py_1", "rounded_md", "bg_teal.900", "c_white")}">1</a><a href="/account/orders?page=2" class="{pd("px_3", "py_1", "rounded_md")}">2</a><a href="/account/orders?page=2" class="{pd("px_3", "py_1", "rounded_md")}" rel="next">Next</a></nav>
  </div>
</main>
<footer class="{pd("bg_stone.900", "c_stone.200", "px_8", "py_12")}">
  <div class="{pd("d_grid", "gridTemplateColumns_repeat(3,1fr)", "gap_8")}">
    <nav aria-label="Help" class="{pd("d_flex", "flex-d_column", "gap_2")}"><a href="/help">Help center</a><a href="/help/delivery">Delivery &amp; assembly</a><a href="/help/returns">Returns</a></nav>
    <nav aria-label="Company" class="{pd("d_flex", "flex-d_column", "gap_2")}"><a href="/about">About</a><a href="/showrooms">Showrooms</a><a href="/design-services">Design services</a><a href="/trade">Trade</a></nav>
    <form action="/newsletter" method="post" class="{pd("d_flex", "gap_2")}"><input type="email" name="email" placeholder="Email address" aria-label="Email address" class="{pd("flex_1", "rounded_full", "px_4", "py_2")}"><button type="submit" class="{pd("rounded_full", "bg_white", "c_stone.900", "px_4", "py_2")}">Sign up</button></form>
  </div>
  <p class="{pd("mt_8", "fs_xs", "c_stone.400")}">© 2026 Harbor Lane Home, Inc. · Privacy · Terms · Accessibility</p>
</footer>
</div>
"""
    v2 = page(title="Orders & returns · Harbor Lane", body=body_v2)

    meta = {
        "title": "Account order history with order cards — home furnishings store",
        "mutations": ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change",
                      "copy-change", "tag-change", "attribute-churn", "structure-move", "insertion"],
        "notes": (
            "v2 renders each order as an <hl-order-card> web component with its own declarative shadow root (header "
            "becomes a <dl>, ids and data-order-id disappear) inside a Panda-CSS utility-class page. A newer order "
            "(delivered today, with its own 'Track shipment' and 'Return or replace items' actions) is inserted at the "
            "top, so positional selectors shift. 'Track package' links become 'Track shipment' buttons, 'Buy it "
            "again' becomes 'Buy again', and a new 'Buy again' rail repeats the Linen Duvet Cover Set. The search box "
            "and date filter move into the page header with new ids/copy (the backend parameter names partly survive)."
        ),
        "targets": [
            target("t1", "'Track package' action of order HL-114-8823901 (arriving Friday)",
                   "#order-HL-114-8823901 a.btn-track",
                   "//div[@data-order-id='HL-114-8823901']//a[normalize-space()='Track package']",
                   ["shadow-dom", "tag-change", "copy-change", "decoy", "id-change", "attribute-churn"]),
            target("t2", "'Return or replace items' action of order HL-114-7781234 (table lamp)",
                   "div[data-order-id='HL-114-7781234'] .return-link",
                   "(//a[normalize-space()='Return or replace items'])[1]",
                   ["shadow-dom", "insertion", "decoy", "sibling-reorder", "attribute-churn", "class-obfuscation"]),
            target("t3", "'Buy it again' button of the 'Linen Duvet Cover Set, Queen – Oat' item (order HL-113-6650912)",
                   "li[data-item-sku='LDC-Q-OAT'] .buy-again-btn",
                   "//a[contains(.,'Linen Duvet Cover Set')]/ancestor::li[1]//button[contains(.,'Buy it again')]",
                   ["shadow-dom", "copy-change", "decoy", "attribute-churn", "class-obfuscation"]),
            target("t4", "Order date-range filter dropdown ('past 3 months')",
                   "#time-filter",
                   "//select[@name='timeFilter']",
                   ["id-change", "copy-change", "structure-move", "class-obfuscation"]),
            target("t5", "Order total ($86.40) in the header of order HL-114-7781234",
                   "#order-HL-114-7781234 .order-total .value",
                   "//div[@data-order-id='HL-114-7781234']//div[contains(@class,'order-total')]/span[2]",
                   ["shadow-dom", "tag-change", "id-change", "class-obfuscation", "sibling-reorder"]),
            target("t6", "'Search all orders' input",
                   "#search-orders-input",
                   "//form[@action='/account/orders/search']//input[@type='search']",
                   ["id-change", "attribute-churn", "copy-change", "wrapper-divs", "structure-move"]),
        ],
    }
    return v1, v2, meta


# ---------------------------------------------------------------------------
# ecommerce-09 — Hollis & Wren: wishlist / saved-for-later lists
# ---------------------------------------------------------------------------

# id, name, price, was, badge, added
S09_ITEMS = [
    ("88190", 'Linen Throw Pillow Cover, 20" – Terracotta', "34.00", None, "", "October 30, 2026"),
    ("88213", "Stoneware Pour-Over Coffee Set", "54.00", "64.00", "Price dropped", "October 28, 2026"),
    ("88231", "Brass Taper Candle Holders, Set of 3", "42.00", None, "", "October 21, 2026"),
    ("88245", "Hand-Thrown Ceramic Vase, Sage", "68.00", None, "", "October 12, 2026"),
    ("88262", "Chunky Knit Throw Blanket, Oatmeal", "89.00", None, "Bestseller", "October 3, 2026"),
    ("88270", "Olive Wood Salad Servers", "26.00", None, "", "September 26, 2026"),
    ("88288", "Woven Seagrass Storage Basket, Large", "48.00", None, "Only 3 left", "September 19, 2026"),
    ("88301", "Botanical Print Set, 11×14 (Set of 2)", "72.00", None, "", "September 2, 2026"),
]
S09_NEW_ITEM = ("88334", "Ribbed Glass Tumblers, Set of 4", "36.00", None, "New", "November 4, 2026")
S09_SAVED = [("Rattan Pendant Light, 18 in", "129.00"), ("Cotton Waffle Robe, Size M", "58.00"), ("Marble Mortar & Pestle", "38.00")]
S09_LISTS = [("Wishlist", 8, "WL-55821"), ("Birthday ideas for Mom", 5, "WL-55902"), ("Kitchen refresh", 7, "WL-56017"), ("Housewarming gifts", 3, "WL-56240")]


def tw(*classes: str) -> str:
    """Tailwind utilities with the ``tw-`` prefix (prefix configured to avoid legacy CSS clashes)."""
    return " ".join("tw-" + c if not c.startswith(("hover:", "md:", "lg:", "focus:")) else c.split(":")[0] + ":tw-" + c.split(":")[1] for c in classes)


def suite09() -> tuple[str, str, dict]:
    nav = ["New", "Home Decor", "Kitchen & Dining", "Bed & Bath", "Garden", "Gifts", "Sale"]

    # ---------------- v1 ----------------
    def item_v1(it: tuple) -> str:
        iid, name, price, was, badge, added = it
        url = f"/products/{slug(name)}"
        b = f'<span class="wishlist-item__badge wishlist-item__badge--{slug(badge)}">{badge}</span>' if badge else ""
        was_html = f' <s class="price-was">${was}</s>' if was else ""
        return f"""
          <li class="wishlist-item" data-item-id="{iid}">
            <div class="wishlist-item__media"><a href="{url}" tabindex="-1"><img class="wishlist-item__img" src="/media/products/{iid}_400.jpg" alt="{e(name)}" width="200" height="200"></a>{b}</div>
            <div class="wishlist-item__body">
              <a class="item-name" href="{url}">{e(name)}</a>
              <p class="wishlist-item__price"><span class="price-now"{gt("t6") if iid == "88213" else ""}>${price}</span>{was_html}</p>
              <p class="wishlist-item__added">Added {added}</p>
              <div class="wishlist-item__actions">
                <button type="button" class="button button--primary move-to-cart" data-test="move-to-cart"{gt("t2") if iid == "88213" else ""}>Move to cart</button>
                <button type="button" class="remove-item" aria-label="Remove {e(name)} from list"{gt("t3") if iid == "88245" else ""}>{icon("close", "", 16)}</button>
              </div>
            </div>
          </li>"""

    items_v1 = "".join(item_v1(i) for i in S09_ITEMS)
    lists_v1 = "".join(
        f'<li class="lists-nav__item{" is-active" if i == 0 else ""}"><a class="lists-nav__link" href="/lists/{lid}"{gt("t5") if name == "Kitchen refresh" else ""}>{e(name)} <span class="lists-nav__count">({n})</span></a></li>'
        for i, (name, n, lid) in enumerate(S09_LISTS)
    )
    saved_v1 = "".join(
        f'<li class="saved-item"><img class="saved-item__img" src="/media/products/{slug(n)}_200.jpg" alt="" width="100" height="100"><div class="saved-item__info"><a class="saved-item__name" href="/products/{slug(n)}">{e(n)}</a><span class="saved-item__price">${p}</span></div>'
        f'<button type="button" class="button button--secondary move-to-cart">Move to cart</button><button type="button" class="saved-item__delete">Delete</button></li>'
        for n, p in S09_SAVED
    )
    nav_v1 = "".join(f'<li class="site-nav__item"><a class="site-nav__link" href="/collections/{slug(x)}">{e(x)}</a></li>' for x in nav)
    body_v1 = f"""
<header class="site-header">
  <div class="site-header__bar"><p>Free shipping on orders over $75 · Gift wrap available at checkout</p></div>
  <div class="site-header__main">
    <a class="site-header__logo" href="/">Hollis <span class="amp">&amp;</span> Wren</a>
    <nav class="site-nav" aria-label="Shop"><ul class="site-nav__list">{nav_v1}</ul></nav>
    <div class="site-header__icons">
      <a class="site-header__icon" href="/search" aria-label="Search">{icon("search")}</a>
      <a class="site-header__icon" href="/account" aria-label="Account">{icon("user")}</a>
      <a class="site-header__icon is-active" href="/lists" aria-label="Wishlist, 8 items">{icon("heart")}<span class="site-header__badge">8</span></a>
      <a class="site-header__icon" href="/cart" aria-label="Cart, 2 items">{icon("bag")}<span class="site-header__badge">2</span></a>
    </div>
  </div>
</header>
<main class="lists-page">
  <div class="lists-layout">
    <aside class="lists-sidebar">
      <h2 class="lists-sidebar__title">Your lists</h2>
      <nav class="lists-nav" aria-label="Your lists"><ul class="lists-nav__list">{lists_v1}</ul></nav>
      <button type="button" class="button button--text create-list">{icon("plus", "", 16)} Create a new list</button>
      <div class="lists-sidebar__tip"><h3>Tip</h3><p>Turn on price-drop alerts and we'll email you when something on your list goes on sale.</p></div>
    </aside>
    <section class="list-detail" aria-labelledby="list-title">
      <div class="list-header">
        <div class="list-header__title">
          <h1 class="list-header__name" id="list-title">Wishlist</h1>
          <p class="list-meta">8 items · Private · Created March 3, 2026</p>
        </div>
        <div class="list-header__actions">
          <hw-share-button list-id="WL-55821">
            <template shadowrootmode="open">
              <style>:host{{display:inline-block}}.share-btn{{display:inline-flex;gap:6px;align-items:center;border:1px solid #2f3b33;border-radius:4px;padding:8px 14px;background:#fff}}</style>
              <button type="button" id="share-list-btn" class="share-btn" part="button"{gt("t1")}><svg class="share-btn__icon" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="{ICONS["share"]}"/></svg>Share list</button>
            </template>
          </hw-share-button>
          <button type="button" class="button button--secondary add-all">Add all to cart</button>
          <button type="button" class="icon-button" aria-label="More list options">{icon("more")}</button>
        </div>
      </div>
      <div class="list-toolbar">
        <div class="list-toolbar__field"><label for="list-privacy">Privacy</label><select id="list-privacy" name="privacy" class="list-toolbar__select"{gt("t4")}><option value="private" selected>Private — only you</option><option value="shared">Shared — anyone with the link</option><option value="public">Public — searchable</option></select></div>
        <div class="list-toolbar__field"><label for="list-sort">Sort by</label><select id="list-sort" name="sort" class="list-toolbar__select"><option selected>Date added</option><option>Price: low to high</option><option>Price: high to low</option><option>Priority</option></select></div>
        <div class="list-toolbar__field list-toolbar__field--check"><input type="checkbox" id="in-stock-only" name="in_stock"><label for="in-stock-only">In stock only</label></div>
        <div class="list-toolbar__field list-toolbar__field--check"><input type="checkbox" id="price-alerts" name="price_alerts" checked><label for="price-alerts">Price-drop alerts</label></div>
      </div>
      <ul class="wishlist-grid">{items_v1}
      </ul>
    </section>
  </div>
  <section class="saved-for-later" aria-labelledby="saved-title">
    <h2 class="saved-for-later__title" id="saved-title">Saved for later (3)</h2>
    <p class="saved-for-later__note">Items you saved from your cart.</p>
    <ul class="saved-for-later__list">{saved_v1}</ul>
  </section>
  <div id="share-dialog" class="dialog" role="dialog" aria-modal="true" aria-labelledby="share-dialog-title" hidden>
    <h2 id="share-dialog-title">Share "Wishlist"</h2>
    <p>Anyone with this link can view your list.</p>
    <label class="visually-hidden" for="share-url">List link</label><input id="share-url" type="text" readonly value="https://hollisandwren.com/lists/WL-55821?share=7f3a91">
    <button type="button" class="button button--primary">Copy link</button>
    <button type="button" class="button button--text dialog__close">Close</button>
  </div>
</main>
<footer class="site-footer">
  <div class="site-footer__cols">
    <div class="site-footer__col"><h2>Help</h2><ul><li><a href="/pages/contact">Contact</a></li><li><a href="/pages/shipping">Shipping</a></li><li><a href="/pages/returns">Returns</a></li><li><a href="/pages/gift-cards">Gift cards</a></li></ul></div>
    <div class="site-footer__col"><h2>About</h2><ul><li><a href="/pages/makers">Our makers</a></li><li><a href="/pages/stores">Stores</a></li><li><a href="/pages/careers">Careers</a></li></ul></div>
    <div class="site-footer__col"><h2>Newsletter</h2><form action="/newsletter" method="post"><label class="visually-hidden" for="footer-email">Email</label><input id="footer-email" type="email" name="email" placeholder="Your email"><button type="submit" class="button button--primary">Subscribe</button></form></div>
  </div>
  <p class="site-footer__legal">© 2026 Hollis &amp; Wren · <a href="/policies/privacy">Privacy</a> · <a href="/policies/terms">Terms</a></p>
</footer>
"""
    css_v1 = """
body{margin:0;font:15px/1.55 "Libre Franklin",Arial,sans-serif;color:#2f3b33;background:#fffdf9}
.site-header__main{display:flex;align-items:center;justify-content:space-between;padding:18px 36px}
.lists-layout{display:grid;grid-template-columns:240px 1fr;gap:36px;padding:24px 36px}
.list-header{display:flex;justify-content:space-between;align-items:flex-start}
.wishlist-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;list-style:none;padding:0}
.wishlist-item{position:relative;border:1px solid #ece4d8;border-radius:6px;padding:12px}
.remove-item{position:absolute;top:8px;right:8px;border:0;background:#fff;border-radius:50%}
.price-now{font-weight:700}.price-was{color:#8a8a8a}
.visually-hidden{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
"""
    v1 = page(title="Your Lists – Wishlist | Hollis & Wren", css=css_v1, body=body_v1, body_attrs=' class="template-lists"')

    # ---------------- v2 ----------------
    def item_v2(it: tuple) -> str:
        iid, name, price, was, badge, added = it
        url = f"/p/{slug(name)}"
        b = f'<span class="{tw("absolute", "left-2", "top-2", "rounded-full", "bg-white/90", "px-2", "py-0.5", "text-[11px]", "font-semibold")}">{badge}</span>' if badge else ""
        was_html = (f'<s class="{tw("text-sm", "text-stone-400")}">${was}</s><span class="{tw("text-xs", "font-semibold", "text-emerald-700")}">You save ${float(was) - float(price):.2f}</span>'
                    if was else "")
        return f"""
          <article class="{tw("group", "relative", "flex", "flex-col", "rounded-2xl", "bg-white", "p-3", "shadow-sm")}" data-wishlist-entry="{_h(iid, 12, _B36)}">
            <div class="{tw("relative", "overflow-hidden", "rounded-xl")}"><img src="https://cdn.hollisandwren.com/p/{iid}.jpg?w=420" alt="" class="{tw("aspect-square", "w-full", "object-cover")}">{b}
              <button type="button" class="{tw("absolute", "right-2", "top-2", "rounded-full", "bg-white", "p-1.5", "shadow")}" aria-label="Delete {e(name)}"{gt("t3") if iid == "88245" else ""}>{icon("trash", "", 16)}</button>
            </div>
            <div class="{tw("mt-3", "flex", "flex-1", "flex-col", "gap-1")}">
              <h3 class="{tw("text-sm", "font-medium", "leading-snug")}"><a href="{url}" class="{tw("hover:underline")}">{e(name)}</a></h3>
              <div class="{tw("flex", "flex-wrap", "items-baseline", "gap-2")}"><span class="{tw("text-base", "font-semibold")}"{gt("t6") if iid == "88213" else ""}>${price}</span>{was_html}</div>
              <p class="{tw("text-xs", "text-stone-500")}">Saved {added.replace(", 2026", "")}</p>
              <div class="{tw("mt-auto", "pt-3")}"><button type="button" class="{tw("w-full", "rounded-full", "bg-stone-900", "py-2", "text-sm", "font-semibold", "text-white")}" data-test="wishlist-add-to-cart"{gt("t2") if iid == "88213" else ""}>Add to cart</button></div>
            </div>
          </article>"""

    items_sorted = sorted(S09_ITEMS + [S09_NEW_ITEM], key=lambda i: float(i[2]))
    items_v2 = "".join(item_v2(i) for i in items_sorted)
    lists_order_v2 = [S09_LISTS[0], S09_LISTS[2], S09_LISTS[1], S09_LISTS[3]]
    tabs_v2 = "".join(
        f'<a href="/account/lists/{lid.lower()}" class="{tw("inline-flex", "items-center", "gap-2", "whitespace-nowrap", "rounded-full", "px-4", "py-2", "text-sm", "bg-stone-900" if i == 0 else "bg-white", "text-white" if i == 0 else "text-stone-700")}"'
        f'{CURRENT if i == 0 else ""}{gt("t5") if name == "Kitchen refresh" else ""}>{e(name)} <span class="{tw("rounded-full", "bg-stone-100", "px-1.5", "text-xs", "text-stone-600")}">{n + (1 if name == "Wishlist" else 0)}</span></a>'
        for i, (name, n, lid) in enumerate(lists_order_v2)
    )
    drawer_lists = "".join(
        f'<li><a href="/account/lists/{lid.lower()}" class="{tw("block", "py-2")}">{e(name)} <span class="{tw("text-xs", "text-stone-500")}">{n + (1 if name == "Wishlist" else 0)}</span></a></li>'
        for name, n, lid in lists_order_v2
    )
    saved_v2 = "".join(
        f'<li class="{tw("flex", "items-center", "gap-4", "py-3")}"><img src="https://cdn.hollisandwren.com/p/{slug(n)}.jpg?w=160" alt="" class="{tw("h-16", "w-16", "rounded-lg", "object-cover")}">'
        f'<div class="{tw("flex-1")}"><a href="/p/{slug(n)}" class="{tw("text-sm", "font-medium")}">{e(n)}</a><p class="{tw("text-sm", "text-stone-600")}">${p}</p></div>'
        f'<button type="button" class="{tw("rounded-full", "border", "border-stone-900", "px-4", "py-1.5", "text-sm", "font-semibold")}">Add to cart</button>'
        f'<button type="button" class="{tw("p-2", "text-stone-500")}" aria-label="Delete {e(n)}">{icon("trash", "", 16)}</button></li>'
        for n, p in S09_SAVED
    )
    nav_v2 = "".join(f'<a href="/shop/{slug(x)}" class="{tw("text-sm", "font-medium", "hover:text-emerald-800")}">{e(x)}</a>' for x in ["New", "Decor", "Kitchen", "Bed & Bath", "Garden", "Gifts", "Sale"])
    body_v2 = f"""
<div id="__hw">
<header class="{tw("border-b", "border-stone-200", "bg-[#fffdf9]")}">
  <div class="{tw("mx-auto", "flex", "max-w-6xl", "items-center", "gap-8", "px-6", "py-4")}">
    <a href="/" class="{tw("font-serif", "text-2xl", "tracking-tight")}">Hollis &amp; Wren</a>
    <nav aria-label="Primary" class="{tw("hidden", "gap-6")} md:tw-flex">{nav_v2}</nav>
    <div class="{tw("ml-auto", "flex", "items-center", "gap-2")}">
      <button type="button" class="{tw("rounded-full", "p-2")}" aria-label="Search">{icon("search")}</button>
      <a href="/account" class="{tw("rounded-full", "p-2")}" aria-label="Account">{icon("user")}</a>
      <a href="/account/lists" class="{tw("relative", "rounded-full", "p-2")}" aria-label="Saved lists">{icon("heart")}</a>
      <a href="/cart" class="{tw("relative", "rounded-full", "p-2")}" aria-label="Cart (2)">{icon("bag")}</a>
    </div>
  </div>
</header>
<div id="lists-drawer" class="{tw("fixed", "inset-0", "z-50", "bg-white", "p-6")}" role="dialog" aria-label="Your lists" hidden>
  <h2 class="{tw("text-lg", "font-semibold")}">Your lists</h2>
  <ul class="{tw("mt-4", "divide-y")}">{drawer_lists}</ul>
</div>
<main class="{tw("mx-auto", "max-w-6xl", "px-6", "py-8")}">
  <div class="{tw("rounded-xl", "bg-emerald-50", "px-4", "py-3", "text-sm", "text-emerald-900")}" role="status">{icon("tag", "", 16)} Good news — <a href="/p/stoneware-pour-over-coffee-set" class="{tw("font-semibold", "underline")}">Stoneware Pour-Over Coffee Set</a> dropped to <span class="{tw("font-semibold")}">$54.00</span></div>
  <div class="{tw("mt-6", "flex", "items-center", "justify-between", "gap-4")}">
    <h1 class="{tw("font-serif", "text-3xl")}">Saved lists</h1>
    <button type="button" class="{tw("rounded-full", "border", "border-stone-300", "px-4", "py-2", "text-sm")}">{icon("plus", "", 16)} New list</button>
  </div>
  <nav aria-label="Lists" class="{tw("mt-4", "flex", "gap-2", "overflow-x-auto")}">{tabs_v2}<button type="button" class="{tw("rounded-full", "px-3", "py-2", "text-sm")} md:tw-hidden" aria-controls="lists-drawer">All lists</button></nav>
  <section class="{tw("mt-8")}" aria-labelledby="wl-title">
    <div class="{tw("flex", "flex-wrap", "items-end", "justify-between", "gap-4")}">
      <div>
        <h2 id="wl-title" class="{tw("text-xl", "font-semibold")}">Wishlist</h2>
        <p class="{tw("text-sm", "text-stone-500")}">9 items · Only you can see this list</p>
      </div>
      <div class="{tw("flex", "items-center", "gap-2")}">
        <button type="button" class="{tw("inline-flex", "items-center", "gap-2", "rounded-full", "bg-stone-900", "px-4", "py-2", "text-sm", "font-semibold", "text-white")}" aria-haspopup="dialog"{gt("t1")}>{icon("share", "", 16)}Share</button>
        <button type="button" class="{tw("rounded-full", "border", "border-stone-300", "px-4", "py-2", "text-sm")}">Add all to cart</button>
        <div class="{tw("relative")}">
          <button type="button" class="{tw("rounded-full", "p-2")}" aria-label="List options" aria-expanded="false">{icon("more")}</button>
          <div role="menu" class="{tw("absolute", "right-0", "mt-2", "w-48", "rounded-xl", "bg-white", "shadow-lg")}" hidden>
            <button type="button" role="menuitem" class="{tw("block", "w-full", "px-4", "py-2", "text-left")}">Share list</button>
            <button type="button" role="menuitem" class="{tw("block", "w-full", "px-4", "py-2", "text-left")}">Rename list</button>
            <button type="button" role="menuitem" class="{tw("block", "w-full", "px-4", "py-2", "text-left", "text-red-700")}">Delete list</button>
          </div>
        </div>
      </div>
    </div>
    <div class="{tw("mt-4", "flex", "flex-wrap", "items-center", "gap-4")}">
      <hw-list-settings list-id="WL-55821">
        <template shadowrootmode="open">
          <style>:host{{display:inline-flex;gap:8px;align-items:center;font:14px system-ui}}select{{border:1px solid #d6d3d1;border-radius:999px;padding:6px 28px 6px 12px}}</style>
          <label class="settings__label" for="visibility">Who can see this list</label>
          <span class="settings__control"><select id="visibility" name="visibility" class="settings__select"{gt("t4")}><option value="PRIVATE" selected>Only me</option><option value="LINK">Anyone with the link</option><option value="PUBLIC">Everyone (public)</option></select></span>
        </template>
      </hw-list-settings>
      <label class="{tw("flex", "items-center", "gap-2", "text-sm")}">Sort <select name="sort" class="{tw("rounded-full", "border-stone-300", "text-sm")}"><option>Recently saved</option><option selected>Price: low to high</option><option>Price: high to low</option></select></label>
      <label class="{tw("flex", "items-center", "gap-2", "text-sm")}"><input type="checkbox" role="switch" name="alerts" checked> Price-drop alerts</label>
    </div>
    <div class="{tw("mt-6", "grid", "grid-cols-2", "gap-4")} md:tw-grid-cols-3 lg:tw-grid-cols-4">{items_v2}
    </div>
  </section>
  <section class="{tw("mt-12", "rounded-2xl", "bg-white", "p-6")}" aria-labelledby="sfl-title">
    <h2 id="sfl-title" class="{tw("text-lg", "font-semibold")}">Saved for later <span class="{tw("text-stone-500")}">3</span></h2>
    <ul class="{tw("mt-2", "divide-y", "divide-stone-100")}">{saved_v2}</ul>
  </section>
</main>
<footer class="{tw("mt-16", "bg-stone-900", "px-6", "py-12", "text-stone-300")}">
  <div class="{tw("mx-auto", "grid", "max-w-6xl", "grid-cols-3", "gap-8")}">
    <nav aria-label="Help" class="{tw("flex", "flex-col", "gap-2", "text-sm")}"><a href="/help/contact">Contact</a><a href="/help/shipping">Shipping</a><a href="/help/returns">Returns</a></nav>
    <nav aria-label="About" class="{tw("flex", "flex-col", "gap-2", "text-sm")}"><a href="/makers">Our makers</a><a href="/stores">Stores</a><a href="/careers">Careers</a></nav>
    <form action="/newsletter" method="post" class="{tw("flex", "gap-2")}"><input type="email" name="email" placeholder="Email" aria-label="Email" class="{tw("flex-1", "rounded-full", "px-4", "text-stone-900")}"><button type="submit" class="{tw("rounded-full", "bg-white", "px-4", "py-2", "text-stone-900")}">Join</button></form>
  </div>
  <p class="{tw("mx-auto", "mt-8", "max-w-6xl", "text-xs")}">© 2026 Hollis &amp; Wren</p>
</footer>
</div>
"""
    v2 = page(title="Saved lists · Hollis & Wren", body=body_v2)

    meta = {
        "title": "Wishlist / saved-for-later page — home & gifts store",
        "mutations": ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change",
                      "testid-change", "copy-change", "tag-change", "attribute-churn", "structure-move", "insertion"],
        "notes": (
            "v1 renders 'Share list' inside the <hw-share-button> web component's shadow root; v2 drops that component "
            "and renders a plain light-DOM 'Share' button (a hidden kebab menu still has a 'Share list' item), while "
            "the privacy select moves into the new <hw-list-settings> shadow root with new name/values/copy. The page "
            "is rebuilt with prefixed Tailwind (tw-*): the sidebar of lists becomes a row of pill links (re-ordered, "
            "counts updated, a hidden mobile drawer repeats them), items become <article> cards sorted by price with "
            "a newly saved item, 'Move to cart' becomes 'Add to cart' (also used in 'Saved for later') with a renamed "
            "data-test hook, the remove 'x' "
            "becomes a trash button labelled 'Delete …', and a price-drop banner repeats the coffee set's new price."
        ),
        "targets": [
            target("t1", "'Share list' button in the list header",
                   "#share-list-btn",
                   "//hw-share-button//button[normalize-space()='Share list']",
                   ["shadow-dom", "structure-move", "copy-change", "id-change", "decoy", "class-obfuscation"]),
            target("t2", "'Move to cart' button of the 'Stoneware Pour-Over Coffee Set' wishlist item",
                   "li[data-item-id='88213'] [data-test='move-to-cart']",
                   "//li[.//a[normalize-space()='Stoneware Pour-Over Coffee Set']]//button[normalize-space()='Move to cart']",
                   ["copy-change", "testid-change", "tag-change", "decoy", "attribute-churn", "sibling-reorder", "class-obfuscation"]),
            target("t3", "Remove (×) icon button of the 'Hand-Thrown Ceramic Vase, Sage' item",
                   ".wishlist-grid > li:nth-child(4) .remove-item",
                   "//button[@aria-label='Remove Hand-Thrown Ceramic Vase, Sage from list']",
                   ["attribute-churn", "copy-change", "sibling-reorder", "insertion", "class-obfuscation", "structure-move"]),
            target("t4", "List privacy dropdown ('Private — only you')",
                   "select#list-privacy",
                   "//select[@name='privacy']",
                   ["shadow-dom", "id-change", "attribute-churn", "copy-change", "structure-move"]),
            target("t5", "'Kitchen refresh' link in the 'Your lists' navigation",
                   ".lists-nav li:nth-child(3) a",
                   "//nav[@aria-label='Your lists']//a[contains(.,'Kitchen refresh')]",
                   ["structure-move", "sibling-reorder", "decoy", "attribute-churn", "class-obfuscation"]),
            target("t6", "Current price ($54.00) of the 'Stoneware Pour-Over Coffee Set' item",
                   "li[data-item-id='88213'] .price-now",
                   "//a[normalize-space()='Stoneware Pour-Over Coffee Set']/following::span[@class='price-now'][1]",
                   ["decoy", "class-obfuscation", "attribute-churn", "sibling-reorder", "wrapper-divs"]),
        ],
    }
    return v1, v2, meta


# ---------------------------------------------------------------------------
# ecommerce-10 — Ampere Electronics: deals & comparison page
# ---------------------------------------------------------------------------

# sku, title, specs, price, was, rating, reviews, coupon (id, text) or None, category
S10_DEALS = [
    ("LBP14-512", "Lumen Book Pro 14 (2026) – 16GB RAM, 512GB SSD", '14.2" 3K OLED 120Hz · 8-core 5.1 GHz · 16GB · 512GB', 999.99, 1199.99, 4.7, 842, None, "laptops"),
    ("ATAB11-128", "Arcadia Tab 11 Wi-Fi, 128GB – Graphite", '11" 2.5K LCD · 8GB · 128GB · pen support', 249.99, 329.99, 4.5, 2310, ("CPN-7731", "Extra $20 off with coupon"), "tablets"),
    ("NA13-256", "Nimbus Air 13 Laptop – 8GB RAM, 256GB SSD", '13.3" FHD IPS · 4-core 4.3 GHz · 8GB · 256GB', 649.99, 799.99, 4.3, 1127, None, "laptops"),
    ("V32-4KC", 'Vantage 32" 4K UHD USB-C Monitor', '32" 4K IPS · 65W USB-C · HDR400', 379.99, 499.99, 4.6, 655, ("CPN-7740", "Extra $30 off with coupon"), "monitors"),
    ("PULSE-ANC", "Pulse ANC Earbuds Pro – Midnight", "Adaptive ANC · 36 h with case · IPX5", 129.99, 179.99, 4.4, 3402, None, "audio"),
    ("ATAB11P-256", "Arcadia Tab 11 Pro, 256GB – Silver", '11" 120Hz OLED · 12GB · 256GB', 449.99, 549.99, 4.6, 918, None, "tablets"),
    ("LBA15-1TB", "Lumen Book Air 15 – 16GB RAM, 1TB SSD", '15.3" 2.8K · 10-core · 16GB · 1TB', 1099.99, 1349.99, 4.8, 377, ("CPN-7758", "Extra $50 off with coupon"), "laptops"),
    ("HALO-10", 'Halo Smart Display 10"', '10" HD touchscreen · built-in assistant · camera shutter', 89.99, 149.99, 4.2, 5120, None, "smart-home"),
    ("V24-FHD", 'Vantage 24" FHD 100Hz Monitor', '24" FHD IPS · 100Hz · HDMI/DP', 99.99, 149.99, 4.4, 2874, None, "monitors"),
    ("STRATA-16", 'Strata Gaming Laptop 16" – RTX-class GPU, 1TB', '16" QHD+ 240Hz · 16-core 5.8 GHz · 32GB · 1TB', 1299.99, 1599.99, 4.5, 264, ("CPN-7769", "Extra $75 off with coupon"), "laptops"),
]
S10_COMPARED = {"LBP14-512", "NA13-256"}
S10_TABS_V1 = [("all", "All deals"), ("laptops", "Laptops"), ("tablets", "Tablets"), ("monitors", "Monitors"), ("audio", "Audio"), ("smart-home", "Smart Home")]
S10_TABS_V2 = [("all", "All deals"), ("laptops", "Laptops"), ("monitors", "Monitors"), ("tvs", "TVs"), ("tablets", "Tablets"), ("audio", "Audio"), ("gaming", "Gaming"), ("smart-home", "Smart Home")]
S10_SPECS = [
    ("Deal price", "$999.99", "$649.99", "$1,299.99"),
    ("Display", '14.2" 3K OLED, 120Hz', '13.3" FHD IPS, 60Hz', '16" QHD+, 240Hz'),
    ("Processor", "8-core, up to 5.1 GHz", "4-core, up to 4.3 GHz", "16-core, up to 5.8 GHz"),
    ("Memory", "16GB LPDDR5X", "8GB LPDDR5", "32GB DDR5"),
    ("Storage", "512GB SSD", "256GB SSD", "1TB SSD"),
    ("Battery", "Up to 15 h", "Up to 12 h", "Up to 6 h"),
    ("Weight", "3.0 lb", "2.6 lb", "5.5 lb"),
]


def mui(*names: str, css: str | None = None) -> str:
    """MUI v5 style: stable ``Mui*`` state/slot classes plus an emotion hash."""
    return " ".join(names) + " " + emo("mui." + (css or ".".join(names)))


def suite10() -> tuple[str, str, dict]:
    by_sku = {d[0]: d for d in S10_DEALS}
    cats = ["Laptops", "Tablets", "Monitors", "TV & Home Theater", "Audio", "Cameras", "Gaming", "Smart Home", "Deals"]

    # ---------------- v1 ----------------
    def card_v1(d: tuple) -> str:
        sku, title, specs, price, was, rating, reviews, coupon, _cat = d
        url = f"/p/{slug(title)[:40]}/{sku.lower()}"
        coupon_html = ""
        if coupon:
            cid, text = coupon
            coupon_html = (f'<div class="coupon"><span class="coupon__text">{icon("tag", "coupon__icon", 14)}{text}</span>'
                           f'<button type="button" class="coupon-clip" data-coupon-id="{cid}"{gt("t2") if sku == "ATAB11-128" else ""}>Clip coupon</button></div>')
        checked = " checked" if sku in S10_COMPARED else ""
        return f"""
      <article class="deal-card" id="deal-{sku}" data-sku="{sku}" data-category="{_cat}">
        <span class="deal-card__badge">Save {money(was - price).replace(".00", "")}</span>
        <img class="deal-card__img" src="/images/products/{sku.lower()}_400.jpg" alt="{e(title)}" width="200" height="200" loading="lazy">
        <h3 class="deal-card__title"><a href="{url}">{e(title)}</a></h3>
        <p class="deal-card__specs">{e(specs)}</p>
        <div class="deal-card__rating"><span class="stars" aria-hidden="true">★★★★★</span><span class="deal-card__reviews">{rating} ({reviews:,})</span></div>
        <p class="deal-card__price"><span class="price-now"{gt("t6") if sku == "LBP14-512" else ""}>{money(price)}</span> <s class="price-was">{money(was)}</s></p>
        {coupon_html}
        <div class="deal-card__footer">
          <label class="compare" for="compare-{sku}"><input type="checkbox" class="compare__checkbox" id="compare-{sku}" name="compare" value="{sku}"{checked}{gt("t1") if sku == "LBP14-512" else ""}> Compare</label>
          <button type="button" class="btn btn--primary btn--small">Add to cart</button>
        </div>
      </article>"""

    cards_v1 = "".join(card_v1(d) for d in S10_DEALS)
    tabs_v1 = "".join(
        f'<button type="button" role="tab" class="deal-tabs__tab{" is-active" if key == "all" else ""}" data-tab="{key}" aria-selected="{"true" if key == "all" else "false"}"{gt("t5") if key == "monitors" else ""}>{label}</button>'
        for key, label in S10_TABS_V1
    )
    cats_v1 = "".join(f'<li class="cat-nav__item"><a class="cat-nav__link" href="/c/{slug(c)}">{e(c)}</a></li>' for c in cats)
    tray_items = "".join(
        f'<li class="compare-tray__item"><img src="/images/products/{s.lower()}_80.jpg" alt="" width="40" height="40"><span class="compare-tray__name">{e(by_sku[s][1].split(" –")[0])}</span>'
        f'<button type="button" class="compare-tray__remove" aria-label="Remove {e(by_sku[s][1].split(" –")[0])} from compare">{icon("close", "", 14)}</button></li>'
        for s in ("LBP14-512", "NA13-256")
    )
    spec_rows_v1 = "".join(f'<tr><th scope="row">{e(r[0])}</th><td>{e(r[1])}</td><td>{e(r[2])}</td><td>{e(r[3])}</td></tr>' for r in S10_SPECS)
    flash = by_sku["V24-FHD"]
    body_v1 = f"""
<div class="top-banner"><p>Early Black Friday deals are live — prices good through Nov 9. <a href="/black-friday/ad">See the ad</a></p></div>
<header class="site-header">
  <div class="site-header__row">
    <a class="logo" href="/">ampere<span class="logo__dot">.</span></a>
    <form class="search" role="search" action="/search"><input type="search" name="q" placeholder="Search laptops, TVs, headphones…" aria-label="Search Ampere"><button type="submit" class="search__btn" aria-label="Search">{icon("search")}</button></form>
    <a class="header-link" href="/stores">{icon("pin", "", 18)}<span>Stores</span></a>
    <a class="header-link" href="/orders/track">{icon("truck", "", 18)}<span>Track order</span></a>
    <a class="header-link" href="/account">{icon("user", "", 18)}<span>Account</span></a>
    <a class="header-link header-link--cart" href="/cart" aria-label="Cart, 0 items">{icon("cart", "", 20)}</a>
  </div>
  <nav class="cat-nav" aria-label="Categories"><ul class="cat-nav__list">{cats_v1}</ul></nav>
</header>
<main class="deals-page">
  <div class="deals-hero">
    <h1 class="deals-hero__title">Early Black Friday Deals</h1>
    <p class="deals-hero__sub">Doorbuster prices on laptops, tablets and monitors. New deals drop daily at 9 AM ET.</p>
  </div>
  <section class="flash-deal" aria-labelledby="flash-title">
    <div class="flash-deal__head">
      <p class="flash-deal__label">{icon("bolt", "flash-deal__icon", 18)} Flash deal</p>
      <flash-countdown ends="2026-11-05T23:59:59-05:00">
        <template shadowrootmode="open">
          <style>:host{{display:inline-block}}.countdown{{display:inline-flex;gap:4px;align-items:center;font:600 18px ui-monospace,monospace}}.countdown__unit{{background:#111;color:#fff;border-radius:4px;padding:2px 6px}}</style>
          <div id="flash-countdown" class="countdown" role="timer" aria-live="off" aria-label="Time remaining"{gt("t3")}>
            <span class="countdown__label">Ends in</span>
            <span class="countdown__unit countdown__hours">02</span><span class="countdown__sep">:</span><span class="countdown__unit countdown__minutes">41</span><span class="countdown__sep">:</span><span class="countdown__unit countdown__seconds">17</span>
          </div>
        </template>
      </flash-countdown>
    </div>
    <div class="flash-deal__product">
      <img class="flash-deal__img" src="/images/products/v27-qhd_600.jpg" alt='Vantage 27" QHD gaming monitor' width="300" height="300">
      <div class="flash-deal__info">
        <h2 class="flash-deal__name" id="flash-title">Vantage 27" QHD 180Hz IPS Gaming Monitor</h2>
        <p class="flash-deal__price"><span class="price-now">$229.99</span> <s class="price-was">$379.99</s> <span class="flash-deal__save">Save $150</span></p>
        <div class="flash-deal__claimed"><progress value="68" max="100">68%</progress><span>68% claimed</span></div>
        <button type="button" class="btn btn--primary">Add to cart</button>
      </div>
    </div>
  </section>
  <div class="deal-tabs" role="tablist" aria-label="Deal categories">{tabs_v1}</div>
  <div class="deal-toolbar">
    <p class="deal-toolbar__count">Showing {len(S10_DEALS)} of 148 deals</p>
    <label for="deal-sort">Sort</label>
    <select id="deal-sort" name="sort"><option selected>Featured</option><option>Biggest savings</option><option>Price: low to high</option><option>Price: high to low</option><option>Customer rating</option></select>
  </div>
  <div class="deal-grid">{cards_v1}
  </div>
  <section class="compare-table-section" aria-labelledby="ct-title">
    <h2 class="compare-table-section__title" id="ct-title">Compare top laptop deals</h2>
    <table class="compare-table">
      <thead><tr><th scope="col">Spec</th><th scope="col">Lumen Book Pro 14 (2026)</th><th scope="col">Nimbus Air 13</th><th scope="col">Strata Gaming 16"</th></tr></thead>
      <tbody>{spec_rows_v1}</tbody>
    </table>
  </section>
  <section class="deal-faq" aria-labelledby="faq-title">
    <h2 id="faq-title">Black Friday FAQ</h2>
    <details><summary>Do you offer price matching?</summary><p>Yes. We match qualifying prices from major retailers through Dec 24, 2026.</p></details>
    <details><summary>When do coupons expire?</summary><p>Clipped coupons apply automatically at checkout and expire when the deal ends.</p></details>
    <details><summary>What is the holiday return policy?</summary><p>Most items bought Nov 1 – Dec 31 can be returned until Jan 15, 2027.</p></details>
  </section>
</main>
<div id="compare-tray" class="compare-tray" role="region" aria-label="Compare products">
  <p class="compare-tray__count">Compare (2 of 4)</p>
  <ul class="compare-tray__items">{tray_items}<li class="compare-tray__slot">Add a product</li><li class="compare-tray__slot">Add a product</li></ul>
  <a class="compare-tray__clear" href="#clear-compare">Clear all</a>
  <button type="button" class="btn btn--primary compare-tray__cta"{gt("t4")}>Compare now</button>
</div>
<footer class="site-footer">
  <div class="site-footer__cols">
    <div><h2>Support</h2><ul><li><a href="/help">Help center</a></li><li><a href="/orders/track">Order status</a></li><li><a href="/returns">Returns &amp; exchanges</a></li><li><a href="/price-match">Price match guarantee</a></li></ul></div>
    <div><h2>Services</h2><ul><li><a href="/protection">Ampere Protect plans</a></li><li><a href="/trade-in">Trade-in</a></li><li><a href="/installation">Installation</a></li><li><a href="/financing">Financing</a></li></ul></div>
    <div><h2>Company</h2><ul><li><a href="/about">About Ampere</a></li><li><a href="/careers">Careers</a></li><li><a href="/sustainability">E-waste recycling</a></li></ul></div>
  </div>
  <p class="site-footer__legal">© 2026 Ampere Electronics, Inc. Prices and offers valid in the US only. · <a href="/privacy">Privacy</a> · <a href="/terms">Terms</a></p>
</footer>
"""
    css_v1 = """
body{margin:0;font:14px/1.45 "Roboto",Arial,sans-serif;color:#141821;background:#f3f5f8}
.site-header__row{display:flex;align-items:center;gap:20px;padding:12px 24px;background:#0b1f3a;color:#fff}
.flash-deal{display:grid;grid-template-columns:1fr;gap:12px;background:#fff;border:2px solid #ff4d2d;border-radius:12px;padding:20px;margin:16px 24px}
.deal-tabs{display:flex;gap:8px;padding:0 24px}.deal-tabs__tab.is-active{background:#0b1f3a;color:#fff}
.deal-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:16px;padding:16px 24px}
.deal-card{position:relative;background:#fff;border-radius:10px;padding:14px}
.price-now{font-size:20px;font-weight:700;color:#c8102e}.price-was{color:#6b7280}
.coupon{display:flex;justify-content:space-between;align-items:center;background:#fff7e6;border:1px dashed #f0b44c;padding:6px 8px}
.compare-tray{position:fixed;left:0;right:0;bottom:0;display:flex;align-items:center;gap:16px;background:#fff;box-shadow:0 -4px 16px rgba(0,0,0,.1);padding:10px 24px}
.compare-table{width:100%;border-collapse:collapse;background:#fff}
"""
    v1 = page(title="Early Black Friday Deals on Laptops, Tablets & Monitors | Ampere", css=css_v1, body=body_v1,
              body_attrs=' class="page-deals"')

    # ---------------- v2 ----------------
    def card_v2(d: tuple) -> str:
        sku, title, specs, price, was, rating, reviews, coupon, _cat = d
        url = f"/product/{slug(title)[:40]}?skuId={_h(sku, 7, '0123456789')}"
        coupon_html = ""
        if coupon:
            cid, text = coupon
            coupon_html = (f'<div class="{emo("coupon-row")}"><span class="{mui("MuiTypography-root", "MuiTypography-caption")}">{text}</span>'
                           f'<button type="button" class="{mui("MuiButtonBase-root", "MuiButton-root", "MuiButton-outlined", "MuiButton-sizeSmall")}" data-coupon-id="{cid}"{gt("t2") if sku == "ATAB11-128" else ""}>Clip coupon</button></div>')
        checked = " checked" if sku in S10_COMPARED else ""
        return f"""
        <div class="{mui("MuiGrid2-root", "MuiGrid2-grid-xs-6", "MuiGrid2-grid-md-4", "MuiGrid2-grid-lg-3", css="grid-item")}">
          <div class="{mui("MuiPaper-root", "MuiPaper-elevation", "MuiCard-root", css="deal-card")}" data-product-id="{_h(sku, 7, '0123456789')}">
            <span class="{mui("MuiChip-root", "MuiChip-filled", "MuiChip-colorError", css="chip")}"><span class="MuiChip-label">−{round((was - price) / was * 100)}%</span></span>
            <img class="{mui("MuiCardMedia-root", "MuiCardMedia-img")}" src="https://assets.ampere.shop/catalog/{sku.lower()}.webp?w=360" alt="" loading="lazy">
            <div class="{mui("MuiCardContent-root")}">
              <a href="{url}" class="{mui("MuiTypography-root", "MuiTypography-subtitle2", "MuiLink-root", "MuiLink-underlineHover")}">{e(title)}</a>
              <p class="{mui("MuiTypography-root", "MuiTypography-body2", css="specs")}">{e(specs)}</p>
              <span class="{mui("MuiRating-root", "MuiRating-sizeSmall", "MuiRating-readOnly")}" role="img" aria-label="{rating} Stars">★★★★★</span><span class="{mui("MuiTypography-root", "MuiTypography-caption", css="reviews")}">{reviews:,} reviews</span>
              <div class="{emo("price-row")}"><span class="{mui("MuiTypography-root", "MuiTypography-h6", css="price")}"{gt("t6") if sku == "LBP14-512" else ""}>{money(price)}</span><s class="{mui("MuiTypography-root", "MuiTypography-caption", css="was")}">{money(was)}</s></div>
              {coupon_html}
            </div>
            <div class="{mui("MuiCardActions-root", "MuiCardActions-spacing")}">
              <label class="{mui("MuiFormControlLabel-root", "MuiFormControlLabel-labelPlacementEnd")}"><span class="{mui("MuiButtonBase-root", "MuiCheckbox-root", "MuiCheckbox-sizeSmall", css="checkbox")}"><input class="{mui("PrivateSwitchBase-input", css="switchbase")}" type="checkbox" name="compare" value="{_h(sku, 7, '0123456789')}"{checked} data-indeterminate="false"{gt("t1") if sku == "LBP14-512" else ""}></span><span class="{mui("MuiTypography-root", "MuiTypography-body2", "MuiFormControlLabel-label")}">Add to compare</span></label>
              <button type="button" class="{mui("MuiButtonBase-root", "MuiButton-root", "MuiButton-contained", "MuiButton-sizeSmall", "MuiButton-fullWidth")}">Add to cart</button>
            </div>
          </div>
        </div>"""

    order_v2 = sorted(S10_DEALS, key=lambda d: (-(d[4] - d[3]), d[0]))
    cards_v2 = "".join(card_v2(d) for d in order_v2)
    tabs_v2 = "".join(
        f'<a role="tab" href="/deals/{"black-friday" if key == "all" else key}" aria-selected="{"true" if key == "all" else "false"}" class="{mui("MuiButtonBase-root", "MuiTab-root", "MuiTab-textColorPrimary", *(["Mui-selected"] if key == "all" else []), css="tab")}"{gt("t5") if key == "monitors" else ""}>{label}</a>'
        for key, label in S10_TABS_V2
    )
    top_rail = "".join(
        f'<li class="{emo("rail-item")}"><img src="https://assets.ampere.shop/catalog/{s.lower()}.webp?w=200" alt="" class="{emo("rail-img")}"><a href="/product/{slug(by_sku[s][1])[:40]}" class="{emo("rail-name")}">{e(by_sku[s][1])}</a>'
        f'<span class="{mui("MuiTypography-root", "MuiTypography-h6", css="price")}">{money(by_sku[s][3])}</span></li>'
        for s in ("LBP14-512", "ATAB11P-256", "V32-4KC", "PULSE-ANC")
    )
    cat_tiles = "".join(
        f'<a href="/deals/{slug(c)}" class="{emo("cat-tile")}"><img src="https://assets.ampere.shop/tiles/{slug(c)}.webp?w=160" alt="" class="{emo("cat-img")}">{c}</a>'
        for c in ["Laptops", "Monitors", "Tablets", "TVs", "Headphones", "Smart Home"]
    )
    spec_rows_v2 = "".join(
        f'<div role="row" class="{emo("spec-row")}"><span role="rowheader" class="{emo("spec-head")}">{e(r[0])}</span><span role="cell">{e(r[1])}</span><span role="cell">{e(r[2])}</span><span role="cell">{e(r[3])}</span></div>'
        for r in S10_SPECS
    )
    dock_items = "".join(
        f'<li class="dock__item"><img src="https://assets.ampere.shop/catalog/{s.lower()}.webp?w=80" alt="" class="dock__thumb"><span class="dock__name">{e(by_sku[s][1].split(" –")[0])}</span>'
        f'<button type="button" class="dock__remove" aria-label="Remove {e(by_sku[s][1].split(" –")[0])}">×</button></li>'
        for s in ("NA13-256", "LBP14-512")
    )
    nav_v2 = "".join(f'<a href="/c/{slug(c)}" class="{emo("nav-link")}">{e(c)}</a>' for c in ["Deals", "Laptops", "Monitors", "TVs", "Tablets", "Audio", "Cameras", "Gaming", "Smart Home"])
    body_v2 = f"""
<div id="__next">
<div class="{mui("MuiAlert-root", "MuiAlert-filledWarning", css="banner")}" role="alert"><div class="MuiAlert-message">Early Black Friday: prices good through Sun, Nov 9 · <a href="/black-friday/ad">Browse the ad</a></div></div>
<header class="{mui("MuiAppBar-root", "MuiAppBar-positionSticky", "MuiAppBar-colorPrimary", css="appbar")}">
  <div class="{mui("MuiToolbar-root", "MuiToolbar-regular", css="toolbar")}">
    <a href="/" class="{emo("logo")}" aria-label="Ampere home">ampere<span class="{emo("logo-dot")}">.</span></a>
    <form role="search" action="/search" class="{emo("search")}"><div class="{mui("MuiInputBase-root", "MuiOutlinedInput-root", css="search-root")}"><input type="search" name="q" placeholder="What can we help you find?" aria-label="Search Ampere" class="{mui("MuiInputBase-input", "MuiOutlinedInput-input", css="search-input")}"></div></form>
    <a href="/stores" class="{mui("MuiButtonBase-root", "MuiButton-root", "MuiButton-text", css="hdr-btn")}">Stores</a>
    <a href="/account" class="{mui("MuiButtonBase-root", "MuiIconButton-root", css="hdr-icon")}" aria-label="Account">{icon("user")}</a>
    <a href="/cart" class="{mui("MuiButtonBase-root", "MuiIconButton-root", css="hdr-icon")}" aria-label="Cart">{icon("cart")}<span class="{mui("MuiBadge-badge", "MuiBadge-invisible", css="badge")}">0</span></a>
  </div>
  <nav aria-label="Departments" class="{emo("nav")}">{nav_v2}</nav>
</header>
<main class="{mui("MuiContainer-root", "MuiContainer-maxWidthXl", css="container")}">
  <h1 class="{mui("MuiTypography-root", "MuiTypography-h3", css="page-title")}">Black Friday Deals</h1>
  <p class="{mui("MuiTypography-root", "MuiTypography-body1", css="page-sub")}">New doorbusters drop every morning at 9 AM ET. Prices good through Nov 9.</p>
  <section class="{emo("dotd")}" aria-labelledby="dotd-title">
    <div class="{emo("dotd-head")}"><h2 id="dotd-title" class="{mui("MuiTypography-root", "MuiTypography-h5")}">Deal of the Day</h2>
      <div class="{emo("timer")}" role="timer" aria-label="Deal of the Day ends in"><span class="{emo("timer-label")}">Ends in</span> <span class="{emo("timer-seg")}">14h</span> <span class="{emo("timer-seg")}">12m</span> <span class="{emo("timer-seg")}">09s</span></div>
    </div>
    <div class="{emo("dotd-body")}"><img src="https://assets.ampere.shop/catalog/halo-10.webp?w=320" alt="" class="{emo("dotd-img")}"><div><a href="/product/halo-smart-display-10" class="{emo("dotd-name")}">Halo Smart Display 10"</a><p class="{emo("dotd-price")}"><span class="{mui("MuiTypography-root", "MuiTypography-h6", css="price")}">$89.99</span> <s>$149.99</s></p><button type="button" class="{mui("MuiButtonBase-root", "MuiButton-root", "MuiButton-contained")}">Add to cart</button></div></div>
  </section>
  <section class="{emo("flash")}" aria-labelledby="flash-h">
    <div class="{emo("flash-head")}">
      <span class="{mui("MuiChip-root", "MuiChip-filled", "MuiChip-colorError", css="flash-chip")}"><span class="MuiChip-label">Flash deal</span></span>
      <div class="{emo("timer")}" role="timer" aria-live="off" aria-label="Flash deal ends in"{gt("t3")}><span class="{emo("timer-label")}">Ends in</span> <span class="{emo("timer-seg")}">02h</span> <span class="{emo("timer-seg")}">41m</span> <span class="{emo("timer-seg")}">17s</span></div>
    </div>
    <div class="{emo("flash-body")}">
      <img src="https://assets.ampere.shop/catalog/v27-qhd.webp?w=480" alt="" class="{emo("flash-img")}">
      <div>
        <h2 id="flash-h" class="{mui("MuiTypography-root", "MuiTypography-h5")}">Vantage 27" QHD 180Hz IPS Gaming Monitor</h2>
        <p class="{emo("flash-price")}"><span class="{mui("MuiTypography-root", "MuiTypography-h4", css="flash-now")}">$229.99</span> <s>$379.99</s> <span class="{emo("flash-save")}">You save $150</span></p>
        <div class="{mui("MuiLinearProgress-root", "MuiLinearProgress-determinate", css="progress")}" role="progressbar" aria-valuenow="68" aria-valuemin="0" aria-valuemax="100"><span class="{mui("MuiLinearProgress-bar", css="progress-bar")}"></span></div>
        <p class="{mui("MuiTypography-root", "MuiTypography-caption")}">68% claimed</p>
        <button type="button" class="{mui("MuiButtonBase-root", "MuiButton-root", "MuiButton-contained", "MuiButton-sizeLarge")}">Add to cart</button>
      </div>
    </div>
  </section>
  <section class="{emo("rail")}" aria-labelledby="top-h"><h2 id="top-h" class="{mui("MuiTypography-root", "MuiTypography-h6")}">Top deals right now</h2><ul class="{emo("rail-list")}">{top_rail}</ul></section>
  <div class="{mui("MuiTabs-root", css="tabs")}"><div class="{mui("MuiTabs-scroller", "MuiTabs-scrollableX", css="tabs-scroller")}"><div class="{mui("MuiTabs-flexContainer", css="tabs-flex")}" role="tablist" aria-label="Shop deals by category">{tabs_v2}</div><span class="{mui("MuiTabs-indicator", css="tabs-indicator")}"></span></div></div>
  <div class="{emo("toolbar")}"><p class="{mui("MuiTypography-root", "MuiTypography-body2")}">{len(S10_DEALS)} of 148 deals · sorted by biggest savings</p><div class="{mui("MuiFormControl-root", css="sort")}"><label for="sort-:r2:" class="{mui("MuiFormLabel-root", "MuiInputLabel-root", css="sort-label")}">Sort</label><select id="sort-:r2:" name="sort" class="{mui("MuiNativeSelect-select", "MuiInputBase-input", css="sort-select")}"><option selected>Biggest savings</option><option>Featured</option><option>Price: low to high</option><option>Price: high to low</option><option>Top rated</option></select></div></div>
  <div class="{mui("MuiGrid2-root", "MuiGrid2-container", "MuiGrid2-direction-xs-row", "MuiGrid2-spacing-xs-2", css="grid")}">{cards_v2}
  </div>
  <section class="{emo("compare")}" aria-labelledby="cmp-h">
    <h2 id="cmp-h" class="{mui("MuiTypography-root", "MuiTypography-h5")}">Laptop deals, side by side</h2>
    <div role="table" aria-labelledby="cmp-h" class="{emo("spec-table")}">
      <div role="row" class="{emo("spec-row")}"><span role="columnheader">Spec</span><span role="columnheader">Lumen Book Pro 14</span><span role="columnheader">Nimbus Air 13</span><span role="columnheader">Strata Gaming 16"</span></div>
      {spec_rows_v2}
    </div>
  </section>
  <section class="{emo("cats")}" aria-labelledby="cats-h"><h2 id="cats-h" class="{mui("MuiTypography-root", "MuiTypography-h6")}">Shop deals by category</h2><div class="{emo("cat-grid")}">{cat_tiles}</div></section>
  <section class="{emo("faq")}" aria-labelledby="faq-h">
    <h2 id="faq-h" class="{mui("MuiTypography-root", "MuiTypography-h6")}">Questions</h2>
    <details class="{mui("MuiAccordion-root", css="acc")}"><summary class="{mui("MuiAccordionSummary-root", css="acc-sum")}">Price match</summary><p>We match qualifying prices from major retailers through Dec 24, 2026.</p></details>
    <details class="{mui("MuiAccordion-root", css="acc")}"><summary class="{mui("MuiAccordionSummary-root", css="acc-sum")}">Coupons</summary><p>Clipped coupons apply automatically at checkout.</p></details>
    <details class="{mui("MuiAccordion-root", css="acc")}"><summary class="{mui("MuiAccordionSummary-root", css="acc-sum")}">Holiday returns</summary><p>Returns accepted until Jan 15, 2027 for most purchases.</p></details>
  </section>
</main>
<amp-compare-dock max="4" count="2">
  <template shadowrootmode="open">
    <style>:host{{position:fixed;left:0;right:0;bottom:0;z-index:1200}}.dock{{display:flex;align-items:center;gap:16px;background:#0b1f3a;color:#fff;padding:12px 24px}}.dock__cta{{border:0;border-radius:999px;background:#ffd23f;color:#0b1f3a;font-weight:700;padding:10px 20px}}</style>
    <section class="dock" aria-label="Product comparison">
      <h2 class="dock__title">Compare up to 4</h2>
      <ul class="dock__items">{dock_items}<li class="dock__empty">Empty slot</li><li class="dock__empty">Empty slot</li></ul>
      <div class="dock__actions"><button type="button" class="dock__clear">Remove all</button><button type="button" class="dock__cta"{gt("t4")}>Compare 2 items</button></div>
    </section>
  </template>
</amp-compare-dock>
<footer class="{emo("footer")}">
  <div class="{emo("footer-grid")}">
    <nav aria-label="Support" class="{emo("footer-col")}"><a href="/help">Help center</a><a href="/orders/track">Order status</a><a href="/returns">Returns</a><a href="/price-match">Price match</a></nav>
    <nav aria-label="Services" class="{emo("footer-col")}"><a href="/protection">Ampere Protect</a><a href="/trade-in">Trade-in</a><a href="/installation">Installation</a><a href="/financing">Financing</a></nav>
    <nav aria-label="Company" class="{emo("footer-col")}"><a href="/about">About</a><a href="/careers">Careers</a><a href="/sustainability">Recycling</a></nav>
  </div>
  <p class="{emo("legal")}">© 2026 Ampere Electronics, Inc. · US offers only · <a href="/privacy">Privacy</a> · <a href="/terms">Terms</a></p>
</footer>
</div>
"""
    v2 = page(title="Black Friday Deals 2026 | Ampere", body=body_v2,
              head='<meta name="emotion-insertion-point" content="">\n')

    meta = {
        "title": "Deals & comparison page with flash-deal countdown and coupons — electronics store",
        "mutations": ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change",
                      "copy-change", "tag-change", "attribute-churn", "structure-move", "insertion"],
        "notes": (
            "v1 renders the flash-deal countdown inside the <flash-countdown> web component's shadow root; v2 is a "
            "MUI v5 (Mui* + emotion css-*) rebuild that renders the countdown in light DOM and inserts a 'Deal of the "
            "Day' section with its own role=timer countdown above it. The compare tray moves into "
            "<amp-compare-dock>'s shadow root ('Compare now' → 'Compare 2 items'). Deal cards become MUI Grid/Card "
            "markup sorted by biggest savings, lose ids/data-sku (coupon ids survive as analytics attributes), "
            "'Compare' becomes 'Add to compare'. Category tabs become role=tab links in a new order, a 'Shop deals by "
            "category' block repeats 'Monitors', and a 'Top deals right now' rail repeats the Lumen Book Pro 14 price."
        ),
        "targets": [
            target("t1", "'Compare' checkbox of the 'Lumen Book Pro 14 (2026)' deal card (checked)",
                   "#compare-LBP14-512",
                   "//article[@data-sku='LBP14-512']//input[@type='checkbox']",
                   ["id-change", "attribute-churn", "copy-change", "wrapper-divs", "sibling-reorder", "class-obfuscation"]),
            target("t2", "'Clip coupon' button of the 'Arcadia Tab 11 Wi-Fi, 128GB' deal",
                   "article[data-sku='ATAB11-128'] .coupon-clip",
                   "//button[@data-coupon-id='CPN-7731']",
                   ["class-obfuscation", "attribute-churn", "sibling-reorder", "decoy", "wrapper-divs"]),
            target("t3", "Flash-deal countdown timer ('Ends in 02:41:17')",
                   "#flash-countdown",
                   "//div[@role='timer']",
                   ["shadow-dom", "structure-move", "id-change", "insertion", "decoy", "copy-change"]),
            target("t4", "'Compare now' button in the compare tray",
                   "#compare-tray .compare-tray__cta",
                   "//button[normalize-space()='Compare now']",
                   ["shadow-dom", "copy-change", "id-change", "class-obfuscation", "structure-move"]),
            target("t5", "'Monitors' category tab above the deal grid",
                   ".deal-tabs button[data-tab='monitors']",
                   "//div[@role='tablist']/button[4]",
                   ["tag-change", "sibling-reorder", "decoy", "class-obfuscation", "wrapper-divs", "insertion"]),
            target("t6", "Deal price ($999.99) of the 'Lumen Book Pro 14 (2026)' card",
                   "#deal-LBP14-512 .price-now",
                   "//article[@data-sku='LBP14-512']//span[@class='price-now']",
                   ["decoy", "id-change", "attribute-churn", "class-obfuscation", "sibling-reorder"]),
        ],
    }
    return v1, v2, meta


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------

SUITES = {
    "01": suite01,
    "02": suite02,
    "03": suite03,
    "04": suite04,
    "05": suite05,
    "06": suite06,
    "07": suite07,
    "08": suite08,
    "09": suite09,
    "10": suite10,
}


def write_suite(num: str, v1: str, v2: str, meta: dict) -> None:
    sid = f"ecommerce-{num}"
    out = HERE / sid
    out.mkdir(exist_ok=True)
    expected = sorted(t["id"] for t in meta["targets"])
    for name, markup in (("v1.html", v1), ("v2.html", v2)):
        found = sorted(re.findall(MARK + r'="(t\d+)"', markup))
        if found != expected or len(re.findall(MARK + r"\s*=", markup)) != len(expected):
            raise SystemExit(f"{sid}/{name}: markers {found} != targets {expected}")
        (out / name).write_text(markup, encoding="utf-8")
    data = {"suite": sid, "category": "ecommerce", **meta}
    (out / "targets.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    wanted = argv or list(SUITES)
    for num in wanted:
        v1, v2, meta = SUITES[num]()
        write_suite(num, v1, v2, meta)
        print(f"wrote ecommerce-{num}: v1={len(v1):,} B, v2={len(v2):,} B, {len(meta['targets'])} targets")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
