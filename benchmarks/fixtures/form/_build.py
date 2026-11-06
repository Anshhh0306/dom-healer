#!/usr/bin/env python
"""Generator for the ``form`` benchmark fixtures (form-01 ... form-10).

    .venv/bin/python benchmarks/fixtures/form/_build.py             # rebuild every suite
    .venv/bin/python benchmarks/fixtures/form/_build.py form-03     # rebuild one suite

Every page is authored by hand below as literal markup.  The helpers only
expand repetitive bits (option lists, link lists, rating grids) so that v1 and
v2 of a suite share the same copy and data, and they turn class *tokens* such
as ``~Field.input`` into the class names a CSS toolchain would emit for the
redesign (CSS modules, styled-components, emotion, Stitches, StyleX,
vanilla-extract, Svelte scoping).  Output is fully deterministic.

Ground truth: ``data-dh-target="tN"`` marks each target in both pages (see
../README.md).  The css/xpath selectors in targets.json are written against v1.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections.abc import Callable
from html import escape
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITES: dict[str, Callable[[], tuple[str, str, dict]]] = {}

_ALNUM = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
_B36 = "0123456789abcdefghijklmnopqrstuvwxyz"
_LETTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def suite(name: str):
    def deco(fn):
        SUITES[name] = fn
        return fn

    return deco


# --------------------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------------------
def h(seed: str, n: int = 6, alphabet: str = _ALNUM) -> str:
    """Deterministic hash-looking string (stands in for a bundler's content hash)."""
    num = int.from_bytes(hashlib.sha256(seed.encode("utf-8")).digest(), "big")
    out = []
    for _ in range(n):
        num, r = divmod(num, len(alphabet))
        out.append(alphabet[r])
    return "".join(out)


def T(tid: str) -> str:
    """Ground-truth marker attribute (the harness strips it before matching)."""
    return f' data-dh-target="{tid}"'


def esc(text: str) -> str:
    return escape(text, quote=True)


def opts(items, selected=None) -> str:
    """<option> list; items are labels or (value, label) pairs."""
    out = []
    for it in items:
        value, label = it if isinstance(it, tuple) else (it, it)
        sel = " selected" if selected is not None and value == selected else ""
        out.append(f'<option value="{esc(value)}"{sel}>{esc(label)}</option>')
    return "\n".join(out)


def links(items, li: str = "", a: str = "") -> str:
    """<li><a> list; ``li``/``a`` are extra attribute strings such as ' class="x"'."""
    return "\n".join(f'<li{li}><a{a} href="{esc(href)}">{esc(text)}</a></li>' for text, href in items)


def columns(cols, tpl: str, li: str = "", a: str = "") -> str:
    """Footer link columns.  ``tpl`` is a str.format template using {i}, {title}, {links}."""
    return "\n".join(tpl.format(i=i, title=esc(title), links=links(items, li, a)) for i, (title, items) in enumerate(cols, 1))


def document(*, title: str, body: str, head: str = "", lang: str = "en", html_attrs: str = "", body_attrs: str = "") -> str:
    return (
        "<!doctype html>\n"
        f'<html lang="{lang}"{html_attrs}>\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{title}</title>\n{head.strip()}\n</head>\n<body{body_attrs}>\n{body.strip()}\n</body>\n</html>\n"
    )


# --------------------------------------------------------------------------------------
# class-name toolchains used by the v2 redesigns
# --------------------------------------------------------------------------------------
_CLASS_RE = re.compile(r'(?<![\w-])class="([^"]*)"')


def expand_classes(markup: str, strategy: Callable[[str], str]) -> str:
    """Replace every ``~token`` inside class attributes with ``strategy(token)``."""

    def repl(m: re.Match) -> str:
        out: list[str] = []
        for tok in m.group(1).split():
            for cls in (strategy(tok[1:]) if tok.startswith("~") else tok).split():
                if cls not in out:
                    out.append(cls)
        return 'class="' + " ".join(out) + '"'

    return _CLASS_RE.sub(repl, markup)


def css_modules(salt: str):
    """~Component.local -> Component_local__AbC12 (Next.js CSS modules)."""

    def strategy(tok: str) -> str:
        comp, _, local = tok.partition(".")
        return f"{comp}_{local or 'root'}__{h(salt + tok, 5)}"

    return strategy


def styled_components(salt: str):
    """~Comp / ~Comp:variant -> 'sc-<componentId> <styleHash>' (styled-components v5)."""

    def strategy(tok: str) -> str:
        comp = tok.split(":", 1)[0]
        return f"sc-{h(salt + 'cid' + comp, 6, _LETTERS)} {h(salt + 'css' + tok, 6, _LETTERS)}"

    return strategy


def emotion(salt: str):
    """~label -> css-<hash> (emotion / MUI production class names)."""

    def strategy(tok: str) -> str:
        return "css-" + h(salt + tok, 7, _B36)

    return strategy


def stitches(salt: str):
    """~Comp -> c-XXXXXX ; ~Comp:variant-x -> base + 'c-XXXXXX-YYYYYY-variant-x' (Stitches)."""

    def strategy(tok: str) -> str:
        comp, _, variant = tok.partition(":")
        base = "c-" + h(salt + comp, 6, _LETTERS)
        if not variant:
            return base
        return f"{base} {base}-{h(salt + tok, 6, _LETTERS)}-{variant}"

    return strategy


def svelte(salt: str):
    """~Component:cls -> 'cls svelte-hash' (Svelte scoped styles)."""

    def strategy(tok: str) -> str:
        comp, _, cls = tok.partition(":")
        scope = "svelte-" + h(salt + comp, 7, _B36)
        return f"{cls} {scope}" if cls else scope

    return strategy


def stylex(table: dict[str, str]):
    """~name -> one atomic class per CSS declaration in table[name] (StyleX)."""

    def atom(decl: str) -> str:
        return "x" + h("stylex:" + decl, 7, _B36)

    def strategy(tok: str) -> str:
        return " ".join(atom(d.strip()) for d in table[tok].split(";") if d.strip())

    return strategy


def vanilla_extract(salt: str):
    """~file.local -> file_local__hash7N (vanilla-extract debug identifiers)."""

    def strategy(tok: str) -> str:
        file, _, local = tok.partition(".")
        return f"{file}_{local}__{h(salt + file, 7, _B36)}{int(h(salt + tok, 3, '0123456789')) % 10}"

    return strategy


# --------------------------------------------------------------------------------------
# icons (feather-style strokes) and brand marks
# --------------------------------------------------------------------------------------
ICONS = {
    "eye": '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
    "alert": '<circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "chev-down": '<path d="m6 9 6 6 6-6"/>',
    "chev-right": '<path d="m9 18 6-6-6-6"/>',
    "chev-left": '<path d="m15 18-6-6 6-6"/>',
    "x": '<path d="M18 6 6 18M6 6l12 12"/>',
    "menu": '<path d="M3 12h18M3 6h18M3 18h18"/>',
    "upload": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5M12 3v12"/>',
    "calendar": '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "minus": '<path d="M5 12h14"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
    "lock": '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>',
    "bell": '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
    "user": '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    "star": '<path d="m12 2 3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01z"/>',
    "clip": '<path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>',
    "arrow-left": '<path d="M19 12H5M12 19l-7-7 7-7"/>',
    "arrow-right": '<path d="M5 12h14M12 5l7 7-7 7"/>',
    "pin": '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>',
    "heart": '<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78L12 21.23l8.84-8.84a5.5 5.5 0 0 0 0-7.78z"/>',
    "trash": '<path d="M3 6h18M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6M10 11v6M14 11v6M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>',
    "globe": '<circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
    "phone": '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.8 19.8 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.12 4.18 2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z"/>',
    "mail": '<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><path d="m22 6-10 7L2 6"/>',
    "external": '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14 21 3"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "home": '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/>',
    "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>',
    "chat": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    "map": '<path d="m1 6 7-4 8 4 7-4v16l-7 4-8-4-7 4z"/><path d="M8 2v16M16 6v16"/>',
    "sliders": '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/>',
    "car": '<path d="M5 17H3v-5l2-5h14l2 5v5h-2"/><circle cx="7.5" cy="17" r="2"/><circle cx="16.5" cy="17" r="2"/>',
    "wifi": '<path d="M5 12.55a11 11 0 0 1 14.08 0M1.42 9a16 16 0 0 1 21.16 0M8.53 16.11a6 6 0 0 1 6.95 0M12 20h.01"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "help": '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3M12 17h.01"/>',
}

BRANDS = {
    "google": (
        '<path d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.7-1.57 2.68-3.88 2.68-6.62z" fill="#4285F4"/>'
        '<path d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.8.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.33A9 9 0 0 0 9 18z" fill="#34A853"/>'
        '<path d="M3.97 10.72A5.4 5.4 0 0 1 3.68 9c0-.6.1-1.18.29-1.72V4.95H.96A9 9 0 0 0 0 9c0 1.45.35 2.83.96 4.05z" fill="#FBBC05"/>'
        '<path d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58A9 9 0 0 0 .96 4.95l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58z" fill="#EA4335"/>'
    ),
    "github": (
        '<path fill="currentColor" d="M9 .2a9 9 0 0 0-2.85 17.54c.45.08.62-.2.62-.43v-1.53c-2.5.55-3.03-1.2-3.03-1.2-.41-1.04-1-1.32-1-1.32'
        '-.82-.56.06-.55.06-.55.9.07 1.38.93 1.38.93.8 1.38 2.11.98 2.62.75.08-.58.32-.98.57-1.2-2-.23-4.1-1-4.1-4.45 0-.98.35-1.79.93-2.42'
        '-.1-.23-.4-1.14.08-2.38 0 0 .76-.24 2.48.92a8.6 8.6 0 0 1 4.5 0c1.72-1.16 2.47-.92 2.47-.92.5 1.24.19 2.15.1 2.38.57.63.92 1.44.92 2.42'
        ' 0 3.46-2.1 4.22-4.1 4.44.32.28.61.83.61 1.67v2.48c0 .24.16.52.62.43A9 9 0 0 0 9 .2z"/>'
    ),
    "microsoft": (
        '<rect x="1" y="1" width="7.5" height="7.5" fill="#F25022"/><rect x="9.5" y="1" width="7.5" height="7.5" fill="#7FBA00"/>'
        '<rect x="1" y="9.5" width="7.5" height="7.5" fill="#00A4EF"/><rect x="9.5" y="9.5" width="7.5" height="7.5" fill="#FFB900"/>'
    ),
}


def icon(name: str, cls: str = "", size: int = 20) -> str:
    c = f' class="{cls}"' if cls else ""
    return (
        f'<svg{c} width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>'
    )


def brand(name: str, cls: str = "", size: int = 18) -> str:
    c = f' class="{cls}"' if cls else ""
    return f'<svg{c} width="{size}" height="{size}" viewBox="0 0 18 18" aria-hidden="true">{BRANDS[name]}</svg>'


def target(tid: str, description: str, css: str, xpath: str, mutations: list[str]) -> dict:
    return {"id": tid, "description": description, "css": css, "xpath": xpath, "mutations": mutations}


def meta(name: str, title: str, mutations: list[str], notes: str, targets: list[dict]) -> dict:
    return {"suite": name, "category": "form", "title": title, "mutations": mutations, "notes": notes, "targets": targets}


# ======================================================================================
# form-01 - Quillstack: workspace login with SSO providers
# ======================================================================================
@suite("form-01")
def form01():
    nav = [("Product", "/product"), ("Solutions", "/solutions"), ("Templates", "/templates"),
           ("Customers", "/customers"), ("Pricing", "/pricing"), ("Docs", "https://docs.quillstack.io")]
    cols = [
        ("Product", [("Features", "/features"), ("Integrations", "/integrations"), ("Templates", "/templates"),
                     ("What's new", "/changelog"), ("Desktop & mobile apps", "/download")]),
        ("Company", [("About us", "/about"), ("Careers", "/careers"), ("Blog", "/blog"), ("Press kit", "/press"),
                     ("Contact us", "/contact")]),
        ("Resources", [("Help center", "https://help.quillstack.io"), ("API reference", "https://docs.quillstack.io/api"),
                       ("Community forum", "https://community.quillstack.io"), ("Webinars", "/webinars"),
                       ("System status", "https://status.quillstack.io")]),
        ("Legal", [("Terms of service", "/legal/terms"), ("Privacy policy", "/legal/privacy"), ("Security", "/security"),
                   ("Cookie settings", "/legal/cookies"), ("Data processing addendum", "/legal/dpa")]),
    ]
    locales = [("en", "English"), ("de", "Deutsch"), ("fr", "Français"), ("es", "Español"), ("ja", "日本語"),
               ("pt-BR", "Português (Brasil)")]
    social = [("X", "https://x.com/quillstack"), ("LinkedIn", "https://www.linkedin.com/company/quillstack"),
              ("YouTube", "https://www.youtube.com/@quillstack"), ("GitHub", "https://github.com/quillstack")]
    logo_svg = ('<svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true"><rect width="28" height="28" rx="7" '
                'fill="#4338ca"/><path d="M8 19 15 8l5 4-7 11H8z" fill="#fff"/></svg>')
    customers = ["Northbeam", "Ardent Health", "Larkfield", "Polymer Labs", "Tidewater", "Cobalt Freight"]

    # ---------------------------------------------------------------- v1: BEM + utility classes
    v1_css = """
  :root { --brand: #4338ca; --ink: #1f2933; --muted: #616e7c; --line: #e4e7eb; --danger: #cf1124; }
  * { box-sizing: border-box; }
  body { margin: 0; font: 15px/1.5 "Inter", system-ui, sans-serif; color: var(--ink); background: #f5f7fa; }
  .container { max-width: 1120px; margin: 0 auto; padding: 0 24px; }
  .announcement-bar { background: #312e81; color: #e0e7ff; text-align: center; font-size: 13px; padding: 8px; }
  .site-header { background: #fff; border-bottom: 1px solid var(--line); }
  .site-header__inner { display: flex; align-items: center; gap: 32px; height: 64px; }
  .site-nav__list { display: flex; gap: 24px; list-style: none; margin: 0; padding: 0; }
  .auth-layout { display: grid; grid-template-columns: minmax(0, 440px) minmax(0, 1fr); gap: 64px; max-width: 1120px; margin: 48px auto; padding: 0 24px; }
  .auth-card { background: #fff; border-radius: 12px; padding: 40px; box-shadow: 0 1px 3px rgba(15, 23, 42, .08); }
  .btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; border-radius: 6px; font-weight: 600; cursor: pointer; }
  .btn--sso { width: 100%; border: 1px solid var(--line); background: #fff; padding: 10px 16px; margin-bottom: 8px; }
  .btn-primary { background: var(--brand); color: #fff; border: 0; padding: 12px 16px; }
  .btn-block { width: 100%; }
  .divider { display: flex; align-items: center; gap: 12px; color: var(--muted); margin: 24px 0; }
  .form-group { margin-bottom: 20px; }
  .form-group__row { display: flex; justify-content: space-between; }
  .form-control { width: 100%; padding: 10px 12px; border: 1px solid #cbd2d9; border-radius: 6px; }
  .form-control--error { border-color: var(--danger); }
  .alert--error { display: flex; gap: 12px; padding: 12px 16px; background: #ffe3e3; color: #8a041a; border-radius: 8px; }
  .site-footer { background: #1f2933; color: #cbd2d9; padding: 48px 0 24px; margin-top: 64px; }
  .sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
"""

    def sso_v1(provider: str, label: str, mark: str = "") -> str:
        return (
            f'<button type="button" class="btn btn--sso btn--{provider}" data-testid="sso-{provider}" '
            f'data-provider="{provider}"{mark}>\n          {brand(provider, "btn__icon")}\n'
            f'          <span class="btn__label">Sign in with {label}</span>\n        </button>'
        )

    v1_body = f"""
<a class="skip-link sr-only" href="#main">Skip to content</a>
<div class="announcement-bar" role="region" aria-label="Announcement">
  <p class="announcement-bar__text">Quillstack 4.2 is here: AI page summaries, offline editing and a much faster search.
    <a class="announcement-bar__link" href="/blog/quillstack-4-2">Read the release notes</a></p>
</div>
<header class="site-header">
  <div class="site-header__inner container">
    <a class="site-header__logo" href="/" aria-label="Quillstack home">
      {logo_svg}
      <span class="logo__wordmark">Quillstack</span>
    </a>
    <nav class="site-nav" aria-label="Main">
      <ul class="site-nav__list">
{links(nav, ' class="site-nav__item"', ' class="site-nav__link"')}
      </ul>
    </nav>
    <div class="site-header__actions">
      <a class="site-header__link" href="/contact-sales">Contact sales</a>
      <a class="btn btn--outline btn--sm" href="/signup">Start free trial</a>
    </div>
  </div>
</header>
<main id="main" class="auth-layout">
  <section class="auth-card" aria-labelledby="auth-title">
    <header class="auth-card__header">
      <h1 id="auth-title" class="auth-card__title">Sign in to Quillstack</h1>
      <p class="auth-card__subtitle">Welcome back! Pick up right where your team left off.</p>
    </header>
    <div class="sso-buttons" role="group" aria-label="Sign in with a provider">
        {sso_v1("google", "Google")}
        {sso_v1("github", "GitHub", T("t5"))}
        {sso_v1("microsoft", "Microsoft")}
    </div>
    <div class="divider" role="separator"><span class="divider__text">or sign in with e-mail</span></div>
    <div class="alert alert--error" role="alert" id="login-error">
      {icon("alert", "alert__icon")}
      <p class="alert__text">The e-mail or password you entered is incorrect. You have <strong>4 attempts</strong> left before your account is temporarily locked.</p>
    </div>
    <form id="login-form" class="auth-form" action="/session" method="post" novalidate>
      <input type="hidden" name="authenticity_token" value="Jx3Uq9mV0tYb8rKc2nW5eLh7sPfA1dZo4gTi6uQyXk">
      <input type="hidden" name="return_to" value="/w/northbeam/home">
      <div class="form-group">
        <label class="form-label" for="login-email">E-mail</label>
        <input class="form-control" id="login-email" type="email" name="email" value="dana.whitfield@northbeam.io" autocomplete="username" placeholder="you@company.com" required{T("t1")}>
        <p class="form-hint">Use the e-mail address you signed up with.</p>
      </div>
      <div class="form-group">
        <div class="form-group__row">
          <label class="form-label" for="login-password">Password</label>
          <a class="link-forgot" href="/password/new"{T("t4")}>Forgot password?</a>
        </div>
        <div class="input-group">
          <input class="form-control form-control--error" id="login-password" type="password" name="password" autocomplete="current-password" aria-invalid="true" aria-describedby="login-error" required{T("t2")}>
          <button type="button" class="input-group__btn" aria-label="Show password" aria-pressed="false">{icon("eye", size=18)}</button>
        </div>
      </div>
      <div class="form-check">
        <input class="form-check__input" type="checkbox" id="remember-me" name="remember" value="1"{T("t3")}>
        <label class="form-check__label" for="remember-me">Remember me for 30 days</label>
      </div>
      <button type="submit" class="btn btn-primary btn-block" data-testid="login-submit"{T("t6")}>Sign in</button>
    </form>
    <p class="auth-card__alt">Does your company use SAML? <a class="auth-card__link" href="/sso">Sign in with single sign-on</a></p>
    <p class="auth-card__footer">New to Quillstack? <a class="auth-card__link" href="/signup">Start a 14-day free trial</a></p>
  </section>
  <aside class="auth-aside" aria-label="Why teams choose Quillstack">
    <figure class="quote">
      <blockquote class="quote__text">
        <p>&ldquo;We moved 1,400 pages of specs out of shared drives and into Quillstack over a weekend. New engineers are productive in days, not weeks.&rdquo;</p>
      </blockquote>
      <figcaption class="quote__author">
        <span class="avatar" aria-hidden="true">PR</span>
        <span class="quote__name">Priya Raman</span>
        <span class="quote__role">VP Engineering, Northbeam</span>
      </figcaption>
    </figure>
    <ul class="feature-list">
      <li class="feature-list__item">{icon("check", "feature-list__icon", 16)}<span>Docs, wikis and runbooks in one searchable place</span></li>
      <li class="feature-list__item">{icon("check", "feature-list__icon", 16)}<span>Real-time co-editing with comments and suggestions</span></li>
      <li class="feature-list__item">{icon("check", "feature-list__icon", 16)}<span>SOC 2 Type II, SAML SSO and SCIM provisioning</span></li>
      <li class="feature-list__item">{icon("check", "feature-list__icon", 16)}<span>Integrations with Slack, Jira, GitHub and Figma</span></li>
    </ul>
    <p class="logo-cloud__title">Trusted by 9,000+ teams</p>
    <ul class="logo-cloud">
{chr(10).join(f'      <li class="logo-cloud__item">{c}</li>' for c in customers)}
    </ul>
  </aside>
</main>
<footer class="site-footer">
  <div class="site-footer__grid container">
    <div class="site-footer__brand">
      <a class="site-footer__logo" href="/">{logo_svg}<span>Quillstack</span></a>
      <p class="site-footer__tagline">Write it down once. Find it forever.</p>
    </div>
{columns(cols, '''    <nav class="site-footer__col" aria-labelledby="footer-col-{i}">
      <h2 id="footer-col-{i}" class="site-footer__heading">{title}</h2>
      <ul class="site-footer__list">
{links}
      </ul>
    </nav>''', ' class="site-footer__item"', ' class="site-footer__link"')}
  </div>
  <div class="site-footer__bottom container">
    <p class="site-footer__copy">&copy; 2026 Quillstack, Inc. &middot; 548 Market St, San Francisco, CA 94104</p>
    <div class="lang-switcher">
      <label class="sr-only" for="footer-locale">Language</label>
      <select id="footer-locale" class="lang-switcher__select" name="locale">
{opts(locales, "en")}
      </select>
    </div>
    <ul class="social-links">
{chr(10).join(f'      <li class="social-links__item"><a class="social-links__link" href="{u}" aria-label="Quillstack on {n}">{icon("external", size=16)}</a></li>' for n, u in social)}
    </ul>
  </div>
</footer>
<div class="cookie-banner" role="region" aria-label="Cookie notice">
  <p class="cookie-banner__text">We use cookies to keep you signed in and to understand how Quillstack is used. <a href="/legal/cookies">Learn more</a></p>
  <div class="cookie-banner__actions">
    <button type="button" class="btn btn--ghost btn--sm">Reject optional</button>
    <button type="button" class="btn btn--outline btn--sm">Accept all</button>
  </div>
</div>
"""
    v1 = document(
        title="Sign in · Quillstack",
        head=f"""<meta name="description" content="Sign in to your Quillstack workspace to write, organise and share your team's knowledge.">
<meta name="theme-color" content="#4338ca">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<style>{v1_css}</style>""",
        body=v1_body,
        body_attrs=' class="page page--auth"',
    )

    # ---------------------------------------------------------------- v2: Stitches + web components
    shadow_css = (":host{display:block}.list{display:grid;gap:8px}.provider{display:flex;align-items:center;"
                  "justify-content:center;gap:10px;height:44px;width:100%;border:1px solid #d6d9de;border-radius:8px;"
                  "background:#fff;font:600 14px/1 system-ui;color:#111827;cursor:pointer}.provider:hover{background:#f9fafb}"
                  ".logo{width:18px;height:18px}")
    names = {"google": "Google", "github": "GitHub", "microsoft": "Microsoft"}

    def providers(intent: str, order: list[str], mark: dict[str, str]) -> str:
        btns = "\n".join(
            f'          <button type="button" class="provider" part="provider provider-{p}" data-provider="{p}"{mark.get(p, "")}>'
            f'{brand(p, "logo")}<span class="provider__label">Continue with {names[p]}</span></button>'
            for p in order
        )
        return f"""<qs-sso-providers intent="{intent}" class="~Providers">
      <template shadowrootmode="open">
        <style>{shadow_css}</style>
        <div class="list" part="list" role="group" aria-label="Continue with a provider">
{btns}
        </div>
      </template>
    </qs-sso-providers>"""

    cookie_css = (":host{position:fixed;inset:auto 16px 16px auto;max-width:360px;z-index:50}"
                  ".panel{background:#0f172a;color:#e2e8f0;border-radius:12px;padding:16px;font:14px/1.5 system-ui}"
                  ".actions{display:flex;gap:8px;margin-top:12px}.btn{border-radius:6px;padding:6px 12px}")
    nav_v2 = [nav[0], nav[2], nav[3], nav[1], nav[5], nav[4]]
    cols_v2 = [cols[2], cols[0], cols[1], cols[3]]
    v2_body = f"""
<div id="__next">
<div class="~Shell">
  <div class="~Banner" role="region" aria-label="Announcement">
    <span class="~Badge:tone-violet">New</span>
    <p class="~Banner.text">AI page summaries and offline editing just landed in Quillstack 4.2.</p>
    <a class="~Link:tone-inverse" href="/blog/quillstack-4-2">See what's new</a>
  </div>
  <header class="~Header">
    <div class="~Header.inner">
      <a href="/" class="~Logo" aria-label="Quillstack home">{logo_svg}<span class="~Logo.word">Quillstack</span></a>
      <nav aria-label="Primary" class="~Nav">
        <ul class="~Nav.list">
{links(nav_v2, ' class="~Nav.item"', ' class="~Nav.link"')}
        </ul>
      </nav>
      <div class="~Header.actions">
        <a class="~Link:size-sm" href="/contact-sales">Talk to sales</a>
        <a class="~Button:variant-outline ~Button:size-sm" href="/signup">Get started free</a>
        <button type="button" class="~IconButton" aria-label="Open menu" aria-expanded="false" aria-controls="mobile-menu">{icon("menu")}</button>
      </div>
    </div>
    <div id="mobile-menu" class="~MobileMenu" hidden>
      <ul class="~MobileMenu.list">
{links(nav_v2, ' class="~MobileMenu.item"', ' class="~MobileMenu.link"')}
      </ul>
      <a class="~Button:variant-solid ~Button:size-md" href="/signup">Get started free</a>
    </div>
  </header>
  <main class="~Main" id="content">
    <div class="~Split">
      <aside class="~Story" aria-label="Customer story">
        <figure class="~Quote">
          <blockquote class="~Quote.text"><p>&ldquo;We moved 1,400 pages of specs out of shared drives and into Quillstack over a weekend.&rdquo;</p></blockquote>
          <figcaption class="~Quote.author"><span class="~Avatar" aria-hidden="true">PR</span><span>Priya Raman, VP Engineering at Northbeam</span></figcaption>
        </figure>
        <ul class="~Logos" aria-label="Customers">
{chr(10).join(f'          <li class="~Logos.item">{c}</li>' for c in customers[::-1])}
        </ul>
        <section class="~Help" aria-labelledby="help-title">
          <h2 id="help-title" class="~Help.title">Trouble logging in?</h2>
          <ul class="~Help.list">
            <li class="~Help.item"><a class="~Link:size-sm" href="/help/reset-password">Forgot your password?</a></li>
            <li class="~Help.item"><a class="~Link:size-sm" href="/help/locked-account">My account is locked</a></li>
            <li class="~Help.item"><a class="~Link:size-sm" href="/help/sso">Logging in with SAML SSO</a></li>
            <li class="~Help.item"><a class="~Link:size-sm" href="https://status.quillstack.io">Check system status</a></li>
          </ul>
        </section>
      </aside>
      <div class="~Card">
        <div class="~Card.header">
          <h1 id=":R1d6:" class="~Heading:size-xl">Log in to Quillstack</h1>
          <p class="~Text:tone-muted">Welcome back &mdash; your workspace is right where you left it.</p>
        </div>
        <div role="tablist" aria-label="Choose how to continue" class="~Tabs">
          <button type="button" role="tab" id="auth-tab-login" aria-selected="true" aria-controls="auth-panel-login" class="~Tabs.trigger:state-active">Log in</button>
          <button type="button" role="tab" id="auth-tab-signup" aria-selected="false" aria-controls="auth-panel-signup" tabindex="-1" class="~Tabs.trigger">Sign up</button>
        </div>
        <div role="tabpanel" id="auth-panel-login" aria-labelledby="auth-tab-login" class="~Tabs.panel">
          <form class="~Form" action="/api/auth/session" method="post" novalidate data-test="login-form">
            <input type="hidden" name="csrfToken" value="5c1b0e8f6a2d4c7b9e3f1a6d8c2b4e7f">
            <input type="hidden" name="callbackUrl" value="/w/northbeam/home">
            <div class="~Honeypot" aria-hidden="true">
              <label for="qs-website">Website</label>
              <input type="text" id="qs-website" name="website" tabindex="-1" autocomplete="off">
            </div>
            <div class="~Callout:tone-danger" role="alert">
              {icon("alert", "~Callout.icon")}
              <div class="~Callout.body">
                <p class="~Callout.title">That email and password combination didn't work.</p>
                <p class="~Callout.text">4 attempts left before we lock your account for 15 minutes.</p>
              </div>
            </div>
            <div class="~Field">
              <div class="~Field.labelRow"><label class="~Label" for=":r3:">Email address</label></div>
              <div class="~InputWrapper">
                <input id=":r3:" class="~Input" type="email" name="email" value="dana.whitfield@northbeam.io" placeholder="name@work-email.com" autocomplete="username webauthn" required{T("t1")}>
              </div>
            </div>
            <div class="~Field">
              <div class="~Field.labelRow"><label class="~Label" for=":r4:">Password</label></div>
              <div class="~InputWrapper:state-invalid">
                <input id=":r4:" class="~Input" type="password" name="password" autocomplete="current-password" aria-invalid="true" required{T("t2")}>
                <button type="button" class="~IconButton:size-sm" aria-label="Show password" aria-pressed="false">{icon("eye", size=18)}</button>
              </div>
            </div>
            <div class="~Row:justify-between">
              <a class="~Link:size-sm" href="/password/reset"{T("t4")}>Forgot your password?</a>
              <div class="~Checkbox">
                <input type="checkbox" id=":r5:" name="remember_me" value="true" class="~Checkbox.input"{T("t3")}>
                <label for=":r5:" class="~Checkbox.label">Keep me logged in</label>
              </div>
            </div>
            <button type="submit" class="~Button:variant-solid ~Button:size-lg" data-test="auth-submit"{T("t6")}>Log in</button>
          </form>
          <div class="~Divider" role="separator"><span class="~Divider.label">or continue with</span></div>
    {providers("login", ["microsoft", "google", "github"], {"github": T("t5")})}
          <p class="~Text:size-sm">Company uses SAML? <a class="~Link" href="/sso">Log in with SSO</a></p>
        </div>
        <div role="tabpanel" id="auth-panel-signup" aria-labelledby="auth-tab-signup" class="~Tabs.panel" hidden>
    {providers("signup", ["google", "github", "microsoft"], {})}
          <div class="~Divider" role="separator"><span class="~Divider.label">or sign up with email</span></div>
          <form class="~Form" action="/api/auth/signup" method="post" novalidate>
            <div class="~Field">
              <label class="~Label" for=":r6:">Work email</label>
              <div class="~InputWrapper"><input id=":r6:" class="~Input" type="email" name="email" autocomplete="email" placeholder="name@work-email.com"></div>
            </div>
            <div class="~Field">
              <label class="~Label" for=":r7:">Full name</label>
              <div class="~InputWrapper"><input id=":r7:" class="~Input" type="text" name="name" autocomplete="name"></div>
            </div>
            <div class="~Field">
              <label class="~Label" for=":r8:">Create a password</label>
              <div class="~InputWrapper"><input id=":r8:" class="~Input" type="password" name="password" autocomplete="new-password"></div>
              <p class="~Hint">At least 10 characters, including a number.</p>
            </div>
            <div class="~Checkbox">
              <input type="checkbox" id=":r9:" name="marketing" value="true" class="~Checkbox.input">
              <label for=":r9:" class="~Checkbox.label">Send me product tips and news</label>
            </div>
            <button type="submit" class="~Button:variant-solid ~Button:size-lg">Create account</button>
            <p class="~Text:size-xs">By signing up you agree to our <a class="~Link" href="/legal/terms">Terms</a> and <a class="~Link" href="/legal/privacy">Privacy policy</a>.</p>
          </form>
        </div>
      </div>
    </div>
  </main>
  <footer class="~Footer">
    <div class="~Footer.grid">
{columns(cols_v2, '''      <div class="~Footer.col">
        <h3 class="~Footer.heading">{title}</h3>
        <ul class="~Footer.list">
{links}
        </ul>
      </div>''', ' class="~Footer.item"', ' class="~Footer.link"')}
    </div>
    <div class="~Footer.bottom">
      <a href="/" class="~Logo:size-sm" aria-label="Quillstack home">{logo_svg}</a>
      <p class="~Text:size-xs">&copy; 2026 Quillstack, Inc. All rights reserved.</p>
      <label class="~VisuallyHidden" for="locale-picker">Language</label>
      <select id="locale-picker" class="~Select" name="locale">
{opts(locales, "en")}
      </select>
    </div>
  </footer>
</div>
</div>
<qs-cookie-consent>
  <template shadowrootmode="open">
    <style>{cookie_css}</style>
    <div class="panel" role="dialog" aria-label="Cookie preferences">
      <p>We use cookies to keep you logged in and to improve Quillstack. <a href="/legal/cookies">Cookie policy</a></p>
      <div class="actions"><button type="button" class="btn">Manage</button><button type="button" class="btn">Reject optional</button><button type="button" class="btn">Accept all</button></div>
    </div>
  </template>
</qs-cookie-consent>
"""
    stitches_css = ("--sxs{--sxs:0 t-dkFnaA}@media{:root,.t-dkFnaA{--colors-violet9:#6e56cf;--colors-slate12:#11181c;"
                    "--radii-md:8px;--space-4:16px}}--sxs{--sxs:2 c-PJLV}@media{.c-PJLV{display:block}}")
    v2 = document(
        title="Log in | Quillstack",
        head=f"""<meta name="description" content="Log in to Quillstack.">
<meta name="theme-color" content="#0f172a">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<style id="stitches">{stitches_css}</style>""",
        body=expand_classes(v2_body, stitches("quillstack")),
    )

    m = meta(
        "form-01",
        "Workspace login with SSO providers — Quillstack",
        ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change", "testid-change",
         "copy-change", "attribute-churn", "structure-move", "insertion"],
        "v2 moves the auth card to a Stitches design system (c-xxxxxx hashed classes) with React useId ids (':r3:'). "
        "The email/password form now comes before the SSO block; the SSO buttons move into a <qs-sso-providers> "
        "declarative shadow root and are reordered (Microsoft, Google, GitHub). 'Remember me' and 'Forgot password?' are "
        "swapped into one row under the password. Decoys: a 'Log in' / 'Sign up' tab bar (the 'Log in' tab is a button "
        "with the same text as the submit), a hidden sign-up tab panel with its own email/password inputs and a second "
        "<qs-sso-providers> (another 'Continue with GitHub'), a 'Trouble logging in?' help box with a 'Forgot your "
        "password?' link placed before the form, a honeypot text input and a hidden mobile menu. Copy changes: "
        "'Sign in' -> 'Log in', 'E-mail' -> 'Email address', 'Remember me for 30 days' -> 'Keep me logged in'.",
        [
            target("t1", "Email input of the login form",
                   "#login-email", "//form[@id='login-form']//input[@name='email']",
                   ["class-obfuscation", "wrapper-divs", "id-change", "copy-change", "attribute-churn", "decoy"]),
            target("t2", "Password input of the login form",
                   "form#login-form input[type='password']", "//input[@autocomplete='current-password']",
                   ["class-obfuscation", "wrapper-divs", "id-change", "decoy"]),
            target("t3", "'Remember me' checkbox under the password field",
                   ".form-check > input[name='remember']", "//input[@type='checkbox' and @id='remember-me']",
                   ["class-obfuscation", "id-change", "attribute-churn", "copy-change", "sibling-reorder", "wrapper-divs"]),
            target("t4", "'Forgot password?' link of the login form",
                   "a.link-forgot", "//a[normalize-space()='Forgot password?']",
                   ["class-obfuscation", "copy-change", "sibling-reorder", "structure-move", "decoy"]),
            target("t5", "'Sign in with GitHub' SSO button",
                   "[data-testid='sso-github']", "//button[contains(., 'Sign in with GitHub')]",
                   ["shadow-dom", "testid-change", "copy-change", "sibling-reorder", "structure-move", "decoy",
                    "class-obfuscation"]),
            target("t6", "Primary 'Sign in' submit button of the login form",
                   "#login-form button.btn-primary", "//button[@type='submit' and normalize-space()='Sign in']",
                   ["class-obfuscation", "testid-change", "copy-change", "decoy"]),
        ],
    )
    return v1, v2, m


# ======================================================================================
# shared reference data
# ======================================================================================
US_STATES = [
    ("AL", "Alabama"), ("AK", "Alaska"), ("AZ", "Arizona"), ("AR", "Arkansas"), ("CA", "California"), ("CO", "Colorado"),
    ("CT", "Connecticut"), ("DE", "Delaware"), ("DC", "District of Columbia"), ("FL", "Florida"), ("GA", "Georgia"),
    ("HI", "Hawaii"), ("ID", "Idaho"), ("IL", "Illinois"), ("IN", "Indiana"), ("IA", "Iowa"), ("KS", "Kansas"),
    ("KY", "Kentucky"), ("LA", "Louisiana"), ("ME", "Maine"), ("MD", "Maryland"), ("MA", "Massachusetts"),
    ("MI", "Michigan"), ("MN", "Minnesota"), ("MS", "Mississippi"), ("MO", "Missouri"), ("MT", "Montana"),
    ("NE", "Nebraska"), ("NV", "Nevada"), ("NH", "New Hampshire"), ("NJ", "New Jersey"), ("NM", "New Mexico"),
    ("NY", "New York"), ("NC", "North Carolina"), ("ND", "North Dakota"), ("OH", "Ohio"), ("OK", "Oklahoma"),
    ("OR", "Oregon"), ("PA", "Pennsylvania"), ("RI", "Rhode Island"), ("SC", "South Carolina"), ("SD", "South Dakota"),
    ("TN", "Tennessee"), ("TX", "Texas"), ("UT", "Utah"), ("VT", "Vermont"), ("VA", "Virginia"), ("WA", "Washington"),
    ("WV", "West Virginia"), ("WI", "Wisconsin"), ("WY", "Wyoming"),
]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]


# ======================================================================================
# form-02 - Harvest Lane grocery delivery: multi-section account registration
# ======================================================================================
@suite("form-02")
def form02():
    nav = [("Shop", "/shop"), ("Weekly deals", "/deals"), ("Recipes", "/recipes"), ("Delivery areas", "/delivery")]
    cols = [
        ("Shop", [("Produce", "/shop/produce"), ("Dairy & eggs", "/shop/dairy"), ("Meat & seafood", "/shop/meat"),
                  ("Bakery", "/shop/bakery"), ("Pantry", "/shop/pantry")]),
        ("Company", [("Our farms", "/farms"), ("Careers", "/careers"), ("Press", "/press"), ("Sustainability", "/sustainability")]),
        ("Help", [("Help center", "/help"), ("Delivery & returns", "/help/delivery"), ("Contact us", "/contact"),
                  ("Accessibility", "/accessibility")]),
    ]
    benefits = [
        ("Same-day delivery", "Order by 2 pm for delivery tonight across Greater Austin."),
        ("Local first", "More than 140 Texas farms, ranches and bakeries in one cart."),
        ("No surprise fees", "Free delivery on orders over $35 with a Lane+ membership."),
        ("Easy substitutions", "Approve swaps by text, or tell us to skip the item."),
    ]
    areas = ["Austin", "Round Rock", "Pflugerville", "Cedar Park", "Georgetown", "San Marcos", "Kyle", "Leander"]
    leaf = ('<svg width="30" height="30" viewBox="0 0 30 30" aria-hidden="true"><circle cx="15" cy="15" r="15" fill="#198754"/>'
            '<path d="M9 20c0-7 5-11 12-11-1 7-5 11-12 11zm0 0 6-6" stroke="#fff" stroke-width="1.6" fill="none"/></svg>')

    # ---------------------------------------------------------------- v1: Bootstrap 5
    v1_css = """
  body { font-family: "Nunito Sans", system-ui, sans-serif; background: #f8f9fa; }
  .card > legend.card-header { float: none; width: 100%; margin: 0; font-size: 1.1rem; }
  fieldset.card { padding: 0; }
  .form-text { font-size: .825rem; }
  .password-rules li { display: flex; gap: .4rem; align-items: center; }
  .benefit { display: flex; gap: .75rem; margin-bottom: 1rem; }
"""
    rules = [("text-success", "check", "At least 8 characters"), ("text-success", "check", "One number"),
             ("text-success", "check", "One uppercase letter"), ("text-muted", "info", "One symbol (! @ # $ %)")]
    v1_rules = "\n".join(f'<li class="{c}">{icon(i, size=14)} {t}</li>' for c, i, t in rules)
    v1_body = f"""
<div class="bg-success text-white text-center small py-2">Free delivery on your first 3 orders over $35 &mdash; use code <strong>FRESH3</strong> at checkout</div>
<nav class="navbar navbar-expand-lg navbar-light bg-white border-bottom">
  <div class="container">
    <a class="navbar-brand d-flex align-items-center gap-2" href="/">{leaf}<span class="fw-bold">Harvest Lane</span></a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#mainNav" aria-controls="mainNav" aria-expanded="false" aria-label="Toggle navigation"><span class="navbar-toggler-icon"></span></button>
    <div class="collapse navbar-collapse" id="mainNav">
      <form class="d-flex mx-lg-4 flex-grow-1" role="search" action="/search">
        <input class="form-control me-2" type="search" name="q" placeholder="Search 12,000+ groceries" aria-label="Search">
        <button class="btn btn-outline-success" type="submit">Search</button>
      </form>
      <ul class="navbar-nav ms-auto mb-2 mb-lg-0">
{links(nav, ' class="nav-item"', ' class="nav-link"')}
        <li class="nav-item"><a class="nav-link" href="/login">Sign in</a></li>
        <li class="nav-item"><a class="nav-link position-relative" href="/cart" aria-label="Cart, 0 items">{icon("home", size=18)}<span class="badge rounded-pill bg-success">0</span></a></li>
      </ul>
    </div>
  </div>
</nav>
<main class="container my-5">
  <nav aria-label="breadcrumb">
    <ol class="breadcrumb">
      <li class="breadcrumb-item"><a href="/">Home</a></li>
      <li class="breadcrumb-item active" aria-current="page">Create account</li>
    </ol>
  </nav>
  <div class="row g-5">
    <div class="col-lg-8">
      <h1 class="h2 mb-1">Create your Harvest Lane account</h1>
      <p class="text-muted mb-4">Groceries from local farms, delivered in as little as two hours. Already have an account? <a href="/login">Sign in</a></p>
      <div class="alert alert-danger d-flex align-items-center gap-2" role="alert">{icon("alert", size=18)}<div>Please correct the highlighted field below.</div></div>
      <form id="registration-form" class="needs-validation" action="/account/register" method="post" novalidate>
        <input type="hidden" name="_csrf" value="b7f2c9e1-4d3a-4e6b-9f0c-2a8d5e7b1c34">
        <fieldset id="personal-info" class="card mb-4">
          <legend class="card-header h5">1. Personal information</legend>
          <div class="card-body">
            <div class="row g-3">
              <div class="col-md-6">
                <label for="reg-first-name" class="form-label">First name</label>
                <input type="text" class="form-control" id="reg-first-name" name="first_name" autocomplete="given-name" value="Marisol" required>
                <div class="invalid-feedback">Please enter your first name.</div>
              </div>
              <div class="col-md-6">
                <label for="reg-last-name" class="form-label">Last name</label>
                <input type="text" class="form-control" id="reg-last-name" name="last_name" autocomplete="family-name" value="Okafor" required>
                <div class="invalid-feedback">Please enter your last name.</div>
              </div>
              <div class="col-md-6">
                <label for="reg-email" class="form-label">Email</label>
                <input type="email" class="form-control" id="reg-email" name="email" autocomplete="email" placeholder="name@example.com" value="marisol.okafor@fastmail.com" required{T("t1")}>
                <div class="form-text">We'll send your order confirmations here.</div>
                <div class="invalid-feedback">Please enter a valid email address.</div>
              </div>
              <div class="col-md-6">
                <label for="reg-phone" class="form-label">Mobile phone</label>
                <input type="tel" class="form-control" id="reg-phone" name="phone" autocomplete="tel" placeholder="(555) 555-0123" value="(512) 555-0147">
                <div class="form-text">For delivery updates by text message.</div>
              </div>
              <div class="col-12">
                <span class="form-label d-block" id="dob-label">Date of birth</span>
                <div class="row g-2">
                  <div class="col-5"><select class="form-select" name="dob_month" aria-labelledby="dob-label" aria-label="Month"><option value="">Month</option>
{opts([(f"{i:02d}", m) for i, m in enumerate(MONTHS, 1)], "07")}
                  </select></div>
                  <div class="col-3"><input type="text" class="form-control" name="dob_day" inputmode="numeric" maxlength="2" placeholder="DD" aria-label="Day" value="23"></div>
                  <div class="col-4"><input type="text" class="form-control" name="dob_year" inputmode="numeric" maxlength="4" placeholder="YYYY" aria-label="Year" value="1991"></div>
                </div>
                <div class="form-text">You must be 21 or older to order beer and wine.</div>
              </div>
            </div>
          </div>
        </fieldset>
        <fieldset id="delivery-address" class="card mb-4">
          <legend class="card-header h5">2. Delivery address</legend>
          <div class="card-body">
            <div class="row g-3">
              <div class="col-12">
                <label for="reg-address1" class="form-label">Street address</label>
                <input type="text" class="form-control" id="reg-address1" name="address_line1" autocomplete="address-line1" value="2207 E Cesar Chavez St" required>
              </div>
              <div class="col-12">
                <label for="reg-address2" class="form-label">Apartment, suite, etc. <span class="text-muted">(optional)</span></label>
                <input type="text" class="form-control" id="reg-address2" name="address_line2" autocomplete="address-line2" value="Apt 3B">
              </div>
              <div class="col-md-5">
                <label for="reg-city" class="form-label">City</label>
                <input type="text" class="form-control" id="reg-city" name="city" autocomplete="address-level2" value="Austin" required>
              </div>
              <div class="col-md-4">
                <label for="reg-state" class="form-label">State</label>
                <select class="form-select" id="reg-state" name="state" autocomplete="address-level1" required{T("t2")}>
<option value="">Choose&hellip;</option>
{opts(US_STATES, "TX")}
                </select>
              </div>
              <div class="col-md-3">
                <label for="reg-zip" class="form-label">ZIP code</label>
                <input type="text" class="form-control" id="reg-zip" name="zip" inputmode="numeric" autocomplete="postal-code" value="78702" required>
              </div>
              <div class="col-12">
                <label for="reg-instructions" class="form-label">Delivery instructions <span class="text-muted">(optional)</span></label>
                <textarea class="form-control" id="reg-instructions" name="delivery_instructions" rows="2" placeholder="Gate code, where to leave the bags, dogs to watch out for&hellip;"></textarea>
              </div>
            </div>
          </div>
        </fieldset>
        <fieldset id="account-security" class="card mb-4">
          <legend class="card-header h5">3. Create a password</legend>
          <div class="card-body">
            <div class="row g-3">
              <div class="col-md-6">
                <label for="reg-password" class="form-label">Password</label>
                <input type="password" class="form-control is-valid" id="reg-password" name="password" autocomplete="new-password" aria-describedby="password-rules" required>
              </div>
              <div class="col-md-6">
                <label for="reg-password-confirm" class="form-label">Confirm password</label>
                <input type="password" class="form-control is-invalid" id="reg-password-confirm" name="password_confirmation" autocomplete="new-password" aria-invalid="true" required{T("t3")}>
                <div class="invalid-feedback"{T("t4")}>Passwords do not match.</div>
              </div>
              <div class="col-12">
                <ul id="password-rules" class="password-rules list-unstyled small mb-0">
{v1_rules}
                </ul>
              </div>
            </div>
          </div>
        </fieldset>
        <fieldset id="terms-section" class="card mb-4">
          <legend class="card-header h5">4. Almost done</legend>
          <div class="card-body">
            <div class="form-check mb-2">
              <input class="form-check-input" type="checkbox" id="reg-terms" name="terms" value="1" required{T("t5")}>
              <label class="form-check-label" for="reg-terms">I agree to the <a href="/terms">Terms of Service</a> and <a href="/privacy">Privacy Policy</a></label>
              <div class="invalid-feedback">You must accept the terms to create an account.</div>
            </div>
            <div class="form-check">
              <input class="form-check-input" type="checkbox" id="reg-marketing" name="marketing_opt_in" value="1" checked>
              <label class="form-check-label" for="reg-marketing">Email me weekly deals, seasonal recipes and new-farm announcements</label>
            </div>
          </div>
        </fieldset>
        <div class="d-grid">
          <button type="submit" class="btn btn-success btn-lg"{T("t6")}>Create account</button>
        </div>
        <p class="small text-muted mt-3 text-center">By creating an account you confirm that you are at least 18 years old.</p>
      </form>
    </div>
    <div class="col-lg-4">
      <aside class="card border-0 bg-light">
        <div class="card-body">
          <h2 class="h5 mb-3">Why join Harvest Lane?</h2>
{chr(10).join(f'          <div class="benefit">{icon("check", "text-success flex-shrink-0", 18)}<div><h3 class="h6 mb-0">{t}</h3><p class="small text-muted mb-0">{d}</p></div></div>' for t, d in benefits)}
          <hr>
          <h3 class="h6">We deliver to</h3>
          <ul class="list-inline small">
{chr(10).join(f'            <li class="list-inline-item">{a}</li>' for a in areas)}
          </ul>
          <div class="alert alert-success small mb-0">New members get <strong>$20 off</strong> their first order of $60 or more.</div>
        </div>
      </aside>
    </div>
  </div>
</main>
<footer class="bg-dark text-white-50 py-5 mt-5">
  <div class="container">
    <div class="row g-4">
      <div class="col-md-4">
        <h2 class="h5 text-white">Harvest Lane</h2>
        <p class="small">Fresh groceries from more than 140 Texas farms and makers, delivered to your door.</p>
      </div>
{columns(cols, '''      <div class="col-6 col-md-2">
        <h3 class="h6 text-white">{title}</h3>
        <ul class="list-unstyled small">
{links}
        </ul>
      </div>''', ' class="mb-1"', ' class="link-light"')}
      <div class="col-6 col-md-2">
        <h3 class="h6 text-white">Get the app</h3>
        <ul class="list-unstyled small">
          <li class="mb-1"><a class="link-light" href="https://apps.apple.com/app/harvest-lane/id1488201">App Store</a></li>
          <li class="mb-1"><a class="link-light" href="https://play.google.com/store/apps/details?id=com.harvestlane">Google Play</a></li>
        </ul>
      </div>
    </div>
    <hr class="border-secondary">
    <div class="d-flex flex-wrap justify-content-between small">
      <span>&copy; 2026 Harvest Lane Market, LLC &middot; Austin, Texas</span>
      <ul class="list-inline mb-0">
        <li class="list-inline-item"><a class="link-light" href="/privacy">Privacy</a></li>
        <li class="list-inline-item"><a class="link-light" href="/terms">Terms</a></li>
        <li class="list-inline-item"><a class="link-light" href="/privacy/choices">Your privacy choices</a></li>
      </ul>
    </div>
  </div>
</footer>
"""
    v1 = document(
        title="Create an account | Harvest Lane",
        head=f"""<meta name="description" content="Create a Harvest Lane account for same-day grocery delivery from local Texas farms.">
<style>{v1_css}</style>""",
        body=v1_body,
        body_attrs=' class="d-flex flex-column min-vh-100"',
    )

    # ---------------------------------------------------------------- v2: Next.js + CSS modules
    rules_css = (":host{display:block;margin-top:8px;font:13px/1.4 system-ui}.meter{display:flex;gap:4px}"
                 ".bar{flex:1;height:4px;border-radius:2px;background:#e5e7eb}.bar.on{background:#15803d}"
                 ".rules{list-style:none;margin:8px 0 0;padding:0;columns:2}.ok{color:#15803d}.todo{color:#6b7280}")
    rules_v2 = [("ok", "8+ characters"), ("ok", "A number"), ("ok", "An uppercase letter"), ("todo", "A symbol")]
    nav_v2 = [nav[1], nav[0], nav[3], nav[2]]
    cols_v2 = [cols[2], cols[0], cols[1]]
    eye = icon("eye", size=18)
    v2_body = f"""
<div class="~PromoBar.root" role="region" aria-label="New member offer">
  <p class="~PromoBar.text"><strong>$20 off</strong> your first order of $60+ &mdash; we'll email you the code.</p>
  <form class="~PromoBar.form" action="/api/promo-code" method="post">
    <label class="~VisuallyHidden.root" for="promo-email">Email</label>
    <input id="promo-email" class="~PromoBar.input" type="email" name="email" placeholder="you@example.com" autocomplete="email">
    <button type="submit" class="~PromoBar.button">Get my code</button>
  </form>
  <button type="button" class="~PromoBar.close" aria-label="Dismiss offer">{icon("x", size=16)}</button>
</div>
<header class="~SiteHeader.root">
  <div class="~SiteHeader.inner">
    <a class="~SiteHeader.logo" href="/" aria-label="Harvest Lane home">{leaf}<span class="~SiteHeader.wordmark">Harvest Lane</span></a>
    <form class="~SearchBox.root" role="search" action="/search">
      <span class="~SearchBox.icon">{icon("search", size=18)}</span>
      <input class="~SearchBox.input" type="search" name="q" placeholder="Search groceries, recipes and farms" aria-label="Search">
    </form>
    <nav class="~SiteHeader.nav" aria-label="Main">
      <ul class="~SiteHeader.navList">
{links(nav_v2, ' class="~SiteHeader.navItem"', ' class="~SiteHeader.navLink"')}
      </ul>
    </nav>
    <a class="~SiteHeader.account" href="/login">{icon("user", size=18)}<span>Sign in</span></a>
    <a class="~SiteHeader.cart" href="/cart" aria-label="Cart, 0 items">{icon("home", size=18)}<span class="~SiteHeader.cartCount">0</span></a>
  </div>
</header>
<main class="~RegisterPage.main">
  <nav aria-label="Breadcrumb" class="~Breadcrumbs.root">
    <ol class="~Breadcrumbs.list">
      <li class="~Breadcrumbs.item"><a href="/">Home</a></li>
      <li class="~Breadcrumbs.item" aria-current="page">Create account</li>
    </ol>
  </nav>
  <div class="~RegisterPage.layout">
    <section class="~RegisterPage.card" aria-labelledby="register-title">
      <header class="~RegisterPage.header">
        <p class="~RegisterPage.eyebrow">Join 48,000 Texas households</p>
        <h1 id="register-title" class="~Heading.h1">Create an account</h1>
        <p class="~RegisterPage.lede">Already shopping with us? <a class="~TextLink.root" href="/login">Sign in</a></p>
      </header>
      <div class="~ErrorSummary.root" role="alert" tabindex="-1">
        <h2 class="~ErrorSummary.title">There's a problem with 1 field</h2>
        <ul class="~ErrorSummary.list"><li><a href="#:r6:">Re-enter your password so both entries match</a></li></ul>
      </div>
      <form class="~RegisterForm.form" action="/api/account" method="post" novalidate>
        <input type="hidden" name="csrfToken" value="1f6d0c9a7e3b45d2a8c1e0f9b4d7a2c6">
        <section class="~RegisterForm.section" aria-labelledby="sec-login">
          <div class="~RegisterForm.sectionHeader"><span class="~RegisterForm.stepBadge">1</span><h2 id="sec-login" class="~RegisterForm.sectionTitle">Your login</h2></div>
          <div class="~Field.root">
            <label class="~Field.label" for=":r1:">Email address</label>
            <div class="~Field.control">
              <input id=":r1:" class="~TextInput.input" type="email" name="email" autocomplete="email" placeholder="you@example.com" value="marisol.okafor@fastmail.com" aria-describedby=":r1:-hint" required{T("t1")}>
            </div>
            <p id=":r1:-hint" class="~Field.hint">Order confirmations and receipts go here.</p>
          </div>
          <div class="~RegisterForm.row">
            <div class="~Field.root">
              <label class="~Field.label" for=":r5:">Password</label>
              <div class="~Field.control">
                <input id=":r5:" class="~TextInput.input ~TextInput.valid" type="password" name="password" autocomplete="new-password" aria-describedby=":r5:-rules" required>
                <button type="button" class="~TextInput.reveal" aria-label="Show password">{eye}</button>
              </div>
              <hl-password-rules id=":r5:-rules" for=":r5:">
                <template shadowrootmode="open">
                  <style>{rules_css}</style>
                  <div class="meter" part="meter" aria-hidden="true"><span class="bar on"></span><span class="bar on"></span><span class="bar on"></span><span class="bar"></span></div>
                  <p class="strength" part="label">Strength: good</p>
                  <ul class="rules">
{chr(10).join(f'                    <li class="{c}">{t}</li>' for c, t in rules_v2)}
                  </ul>
                </template>
              </hl-password-rules>
            </div>
            <div class="~Field.root ~Field.invalid">
              <label class="~Field.label" for=":r6:">Re-enter password</label>
              <div class="~Field.control">
                <input id=":r6:" class="~TextInput.input ~TextInput.invalid" type="password" name="confirmPassword" autocomplete="new-password" aria-invalid="true" aria-describedby=":r6:-error" required{T("t3")}>
                <button type="button" class="~TextInput.reveal" aria-label="Show password">{eye}</button>
              </div>
              <div id=":r6:-error" class="~Field.error"{T("t4")}>Passwords don't match</div>
            </div>
          </div>
        </section>
        <section class="~RegisterForm.section" aria-labelledby="sec-about">
          <div class="~RegisterForm.sectionHeader"><span class="~RegisterForm.stepBadge">2</span><h2 id="sec-about" class="~RegisterForm.sectionTitle">About you</h2></div>
          <div class="~RegisterForm.row">
            <div class="~Field.root">
              <label class="~Field.label" for=":r2:">First name</label>
              <div class="~Field.control"><input id=":r2:" class="~TextInput.input" type="text" name="firstName" autocomplete="given-name" value="Marisol" required></div>
            </div>
            <div class="~Field.root">
              <label class="~Field.label" for=":r3:">Last name</label>
              <div class="~Field.control"><input id=":r3:" class="~TextInput.input" type="text" name="lastName" autocomplete="family-name" value="Okafor" required></div>
            </div>
          </div>
          <div class="~RegisterForm.row">
            <div class="~Field.root">
              <label class="~Field.label" for=":r4:">Mobile number</label>
              <div class="~Field.control"><span class="~TextInput.prefix">+1</span><input id=":r4:" class="~TextInput.input" type="tel" name="phone" autocomplete="tel-national" value="512 555 0147"></div>
              <p class="~Field.hint">We text you when your shopper is on the way.</p>
            </div>
            <div class="~Field.root">
              <label class="~Field.label" for=":r7:">Date of birth</label>
              <div class="~Field.control"><input id=":r7:" class="~TextInput.input" type="text" name="dateOfBirth" inputmode="numeric" placeholder="MM/DD/YYYY" value="07/23/1991"></div>
              <p class="~Field.hint">21+ to add beer and wine to your cart.</p>
            </div>
          </div>
        </section>
        <section class="~RegisterForm.section" aria-labelledby="sec-address">
          <div class="~RegisterForm.sectionHeader"><span class="~RegisterForm.stepBadge">3</span><h2 id="sec-address" class="~RegisterForm.sectionTitle">Where should we deliver?</h2></div>
          <div class="~Field.root">
            <label class="~Field.label" for=":r8:">Street address</label>
            <div class="~Field.control"><input id=":r8:" class="~TextInput.input" type="text" name="address.line1" autocomplete="address-line1" value="2207 E Cesar Chavez St" role="combobox" aria-autocomplete="list" aria-expanded="false" required></div>
          </div>
          <div class="~Field.root">
            <label class="~Field.label" for=":r9:">Apt, suite or unit <span class="~Field.optional">Optional</span></label>
            <div class="~Field.control"><input id=":r9:" class="~TextInput.input" type="text" name="address.line2" autocomplete="address-line2" value="Apt 3B"></div>
          </div>
          <div class="~RegisterForm.row3">
            <div class="~Field.root">
              <label class="~Field.label" for=":ra:">ZIP code</label>
              <div class="~Field.control"><input id=":ra:" class="~TextInput.input" type="text" name="address.postalCode" inputmode="numeric" autocomplete="postal-code" value="78702" required></div>
            </div>
            <div class="~Field.root">
              <label class="~Field.label" for=":rb:">City</label>
              <div class="~Field.control"><input id=":rb:" class="~TextInput.input" type="text" name="address.city" autocomplete="address-level2" value="Austin" required></div>
            </div>
            <div class="~Field.root">
              <label class="~Field.label" for=":rc:">State</label>
              <div class="~Select.root">
                <select id=":rc:" class="~Select.select" name="address.state" autocomplete="address-level1" required{T("t2")}>
<option value="" disabled>Select a state</option>
{opts(US_STATES, "TX")}
                </select>
                <span class="~Select.chevron">{icon("chev-down", size=16)}</span>
              </div>
            </div>
          </div>
          <div class="~Field.root">
            <label class="~Field.label" for=":rd:">Notes for your shopper <span class="~Field.optional">Optional</span></label>
            <div class="~Field.control"><textarea id=":rd:" class="~TextArea.input" name="address.instructions" rows="3" placeholder="Gate code, where to leave the bags&hellip;"></textarea></div>
          </div>
        </section>
        <section class="~RegisterForm.section" aria-labelledby="sec-prefs">
          <div class="~RegisterForm.sectionHeader"><span class="~RegisterForm.stepBadge">4</span><h2 id="sec-prefs" class="~RegisterForm.sectionTitle">Preferences</h2></div>
          <div class="~Checkbox.root">
            <input id=":re:" class="~Checkbox.input" type="checkbox" name="marketingOptIn" value="true" checked>
            <label class="~Checkbox.label" for=":re:">Send me weekly deals and seasonal recipes</label>
          </div>
          <div class="~Checkbox.root">
            <input id=":rf:" class="~Checkbox.input" type="checkbox" name="acceptTerms" value="true" required{T("t5")}>
            <label class="~Checkbox.label" for=":rf:">I agree to the Harvest Lane <a class="~TextLink.root" href="/terms">Terms of Service</a> and <a class="~TextLink.root" href="/privacy">Privacy Notice</a></label>
          </div>
        </section>
        <div class="~RegisterForm.actions">
          <button type="submit" class="~Button.root ~Button.primary ~Button.block"{T("t6")}>Create account</button>
          <p class="~RegisterForm.fineprint">You must be 18 or older to create an account.</p>
        </div>
      </form>
    </section>
    <aside class="~RegisterPage.aside" aria-label="Member benefits">
      <h2 class="~RegisterPage.asideTitle">Why shoppers love Harvest Lane</h2>
      <ul class="~Benefits.list">
{chr(10).join(f'        <li class="~Benefits.item">{icon("check", "~Benefits.icon", 18)}<div><h3 class="~Benefits.title">{t}</h3><p class="~Benefits.text">{d}</p></div></li>' for t, d in benefits[::-1])}
      </ul>
      <h3 class="~RegisterPage.asideSubtitle">Delivering across Central Texas</h3>
      <p class="~RegisterPage.areas">{", ".join(sorted(areas))}</p>
    </aside>
  </div>
</main>
<div class="~StickyCta.root" role="region" aria-label="Create account">
  <p class="~StickyCta.text">Free delivery on your first 3 orders</p>
  <button type="button" class="~Button.root ~Button.primary">Create account</button>
</div>
<footer class="~SiteFooter.root">
  <div class="~SiteFooter.grid">
{columns(cols_v2, '''    <div class="~SiteFooter.col">
      <h2 class="~SiteFooter.heading">{title}</h2>
      <ul class="~SiteFooter.list">
{links}
      </ul>
    </div>''', ' class="~SiteFooter.item"', ' class="~SiteFooter.link"')}
  </div>
  <div class="~SiteFooter.legal">
    <p>&copy; 2026 Harvest Lane Market, LLC</p>
    <a class="~SiteFooter.link" href="/privacy">Privacy</a>
    <a class="~SiteFooter.link" href="/terms">Terms</a>
    <a class="~SiteFooter.link" href="/privacy/choices">Your privacy choices</a>
  </div>
</footer>
<div aria-live="polite" aria-atomic="true" class="~VisuallyHidden.root">Passwords don't match</div>
"""
    v2 = document(
        title="Create an account — Harvest Lane",
        head="""<meta name="description" content="Sign up for same-day grocery delivery from local Texas farms.">
<meta name="next-head-count" content="4">""",
        body=expand_classes(v2_body, css_modules("harvestlane")),
        body_attrs=' class="__className_3a0388 __variable_9f5e1c"',
    )

    m = meta(
        "form-02",
        "Multi-section account registration — Harvest Lane grocery delivery",
        ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change", "copy-change",
         "attribute-churn", "structure-move", "insertion", "tag-change"],
        "v1 is a Bootstrap 5 form with four numbered fieldsets. v2 is a Next.js rewrite with CSS-module class names "
        "(Field_label__xxxxx), React useId ids (':r6:') and react-hook-form style names (confirmPassword, address.state, "
        "acceptTerms). Sections are reordered (login details first, email moved out of 'Personal information'), the "
        "address row becomes ZIP / City / State, and the marketing opt-in now precedes the terms checkbox. The password "
        "rules list moves into a <hl-password-rules> declarative shadow root. Decoys: a promo bar email form above the "
        "header, a second password input next to the confirmation, a sticky mobile 'Create account' bar and an "
        "aria-live announcer that repeats the 'Passwords don't match' error.",
        [
            target("t1", "Email input of the registration form",
                   "#reg-email", "//fieldset[@id='personal-info']//input[@type='email']",
                   ["class-obfuscation", "wrapper-divs", "id-change", "copy-change", "structure-move", "sibling-reorder",
                    "decoy"]),
            target("t2", "State select of the delivery address",
                   "select#reg-state", "//select[@name='state']",
                   ["class-obfuscation", "wrapper-divs", "id-change", "attribute-churn", "sibling-reorder"]),
            target("t3", "Confirm-password input",
                   "input[name='password_confirmation']",
                   "//label[normalize-space()='Confirm password']/following-sibling::input",
                   ["class-obfuscation", "wrapper-divs", "id-change", "attribute-churn", "copy-change", "decoy"]),
            target("t4", "'Passwords do not match' validation message under the confirm-password field",
                   "#reg-password-confirm ~ .invalid-feedback",
                   "//div[@class='invalid-feedback' and contains(., 'do not match')]",
                   ["class-obfuscation", "copy-change", "id-change", "decoy"]),
            target("t5", "Terms of Service agreement checkbox",
                   "#reg-terms", "//input[@type='checkbox'][@name='terms']",
                   ["class-obfuscation", "id-change", "attribute-churn", "sibling-reorder", "copy-change"]),
            target("t6", "'Create account' submit button",
                   "form#registration-form .btn-success", "//button[normalize-space()='Create account']",
                   ["class-obfuscation", "wrapper-divs", "decoy"]),
        ],
    )
    return v1, v2, m


# ======================================================================================
# form-03 - Copperline Coffee Roasters: checkout (shipping + payment)
# ======================================================================================
@suite("form-03")
def form03():
    items = [
        ("Ethiopia Guji Natural", "340 g / Whole bean", 2, "$39.00", "#b45309"),
        ("Night Shift Espresso Blend", "1 kg / Espresso grind", 1, "$41.00", "#44403c"),
        ("Copperline Ceramic Dripper", "Matte white", 1, "$28.00", "#d6d3d1"),
    ]
    policies = [("Refund policy", "/policies/refund-policy"), ("Shipping policy", "/policies/shipping-policy"),
                ("Privacy policy", "/policies/privacy-policy"), ("Terms of service", "/policies/terms-of-service")]
    rates = [("standard", "Standard (5–7 business days)", "$6.90"), ("expedited", "Expedited (2–3 business days)", "$14.50"),
             ("pickup", "Pickup at our Portland roastery", "Free")]

    def thumb(color: str) -> str:
        return (f'<svg width="64" height="64" viewBox="0 0 64 64" aria-hidden="true"><rect width="64" height="64" rx="8" fill="#f5f5f4"/>'
                f'<rect x="18" y="12" width="28" height="40" rx="4" fill="{color}"/></svg>')

    # ---------------------------------------------------------------- v1: classic hosted checkout
    v1_css = """
  body { margin: 0; font: 14px/1.5 -apple-system, "Segoe UI", Roboto, sans-serif; color: #333; }
  .wrap { display: flex; max-width: 1080px; margin: 0 auto; }
  .main { flex: 1 1 58%; padding: 56px 66px 0 0; }
  .sidebar { flex: 1 1 42%; padding: 56px 0 0 44px; background: #fafafa; border-left: 1px solid #e1e1e1; }
  .field { float: left; width: 100%; padding: .42857em; box-sizing: border-box; }
  .field--half { width: 50%; } .field--three-eights { width: 37.5%; } .field--quarter { width: 25%; }
  .field__input { width: 100%; border: 1px solid #d9d9d9; border-radius: 5px; padding: .94em .8em; box-sizing: border-box; }
  .field__label { display: block; font-size: .857em; color: #737373; }
  .content-box { border: 1px solid #d9d9d9; border-radius: 5px; }
  .content-box__row { padding: 1.14em; border-top: 1px solid #d9d9d9; }
  .btn { background: #8a4b1f; color: #fff; border: 0; border-radius: 5px; padding: 1.4em 1.7em; font-weight: 500; }
  .visually-hidden { position: absolute !important; clip: rect(0 0 0 0); width: 2px; height: 2px; overflow: hidden; }
  .payment-due__price { font-size: 1.714em; letter-spacing: -.04em; }
"""

    def v1_field(fid: str, name: str, label: str, width: str = "", value: str = "", extra: str = "", required: bool = True,
                 mark: str = "", itype: str = "text") -> str:
        cls = "field" + (" field--required" if required else "") + (f" field--{width}" if width else "")
        val = f' value="{esc(value)}"' if value else ""
        return (f'<div class="{cls}">\n  <div class="field__input-wrapper">\n'
                f'    <label class="field__label field__label--visible" for="{fid}">{label}</label>\n'
                f'    <input placeholder="{esc(label)}" class="field__input" size="30" type="{itype}" name="{name}" id="{fid}"{val}{extra}{mark}>\n'
                f'  </div>\n</div>')

    def v1_state_select(fid: str, name: str, selected: str) -> str:
        return (f'<div class="field field--required field--three-eights field--show-floating-label">\n'
                f'  <div class="field__input-wrapper field__input-wrapper--select">\n'
                f'    <label class="field__label field__label--visible" for="{fid}">State</label>\n'
                f'    <select class="field__input field__input--select" name="{name}" id="{fid}" autocomplete="shipping address-level1">\n'
                f'<option disabled value="">State</option>\n{opts(US_STATES, selected)}\n    </select>\n  </div>\n</div>')

    rate_rows = "\n".join(
        f'''<div class="content-box__row">
  <div class="radio-wrapper">
    <div class="radio__input"><input class="input-radio" type="radio" value="copperline-{key}" name="checkout[shipping_rate][id]" id="checkout_shipping_rate_id_{key}"{" checked" if key == "standard" else ""}></div>
    <label class="radio__label" for="checkout_shipping_rate_id_{key}"><span class="radio__label__primary">{label}</span><span class="radio__accessory"><span class="content-box__emphasis">{price}</span></span></label>
  </div>
</div>''' for key, label, price in rates)

    v1_products = "\n".join(
        f'''<tr class="product">
  <td class="product__image"><div class="product-thumbnail"><div class="product-thumbnail__wrapper">{thumb(c)}</div><span class="product-thumbnail__quantity" aria-hidden="true">{q}</span></div></td>
  <th class="product__description" scope="row"><span class="product__description__name order-summary__emphasis">{n}</span><span class="product__description__variant order-summary__small-text">{v}</span></th>
  <td class="product__quantity"><span class="visually-hidden">{q}</span></td>
  <td class="product__price"><span class="order-summary__emphasis">{p}</span></td>
</tr>''' for n, v, q, p, c in items)

    totals = [("Subtotal", "$108.00", "subtotal"), ("Shipping", "$6.90", "shipping"), ("Estimated taxes", "$11.78", "taxes")]
    v1_totals = "\n".join(
        f'<tr class="total-line total-line--{k}"><th class="total-line__name" scope="row">{n}</th>'
        f'<td class="total-line__price"><span class="order-summary__emphasis">{p}</span></td></tr>' for n, p, k in totals)

    v1_body = f"""
<a class="skip-to-content" href="#main-header">Skip to content</a>
<header class="banner" role="banner">
  <div class="wrap">
    <a class="logo logo--left" href="https://copperlinecoffee.com"><span class="logo__text heading-1">Copperline Coffee Roasters</span></a>
  </div>
</header>
<aside class="order-summary-toggle-wrapper" role="complementary">
  <button type="button" class="order-summary-toggle order-summary-toggle--show" aria-expanded="false" aria-controls="order-summary">
    <span class="order-summary-toggle__inner">
      <span class="order-summary-toggle__icon-wrapper">{icon("home", "order-summary-toggle__icon", 18)}</span>
      <span class="order-summary-toggle__text order-summary-toggle__text--show"><span>Show order summary</span></span>
      <span class="order-summary-toggle__total-recap total-recap"><span class="total-recap__final-price">$126.68</span></span>
    </span>
  </button>
</aside>
<div class="content">
  <div class="wrap">
    <div class="main">
      <header class="main__header" role="banner">
        <nav aria-label="Breadcrumb">
          <ol class="breadcrumb">
            <li class="breadcrumb__item breadcrumb__item--completed"><a class="breadcrumb__link" href="https://copperlinecoffee.com/cart">Cart</a>{icon("chev-right", "breadcrumb__chevron-icon", 10)}</li>
            <li class="breadcrumb__item breadcrumb__item--current" aria-current="step"><span class="breadcrumb__text">Information &amp; payment</span>{icon("chev-right", "breadcrumb__chevron-icon", 10)}</li>
            <li class="breadcrumb__item breadcrumb__item--blank"><span class="breadcrumb__text">Review</span></li>
          </ol>
        </nav>
      </header>
      <main class="main__content" role="main">
        <div class="step" data-step="contact_information">
          <form class="edit_checkout" id="checkout-form" action="/41820389/checkouts/7d1f2b9c40e5a8f3" accept-charset="UTF-8" method="post" novalidate>
            <input type="hidden" name="_method" value="patch">
            <input type="hidden" name="authenticity_token" value="pT3x0aQ+Lw8vJ1Y2mZ5cQe9sVbHk4rN7oD6uW2yF1gA=">
            <div class="step__sections">
              <div class="section section--contact-information">
                <div class="section__header">
                  <div class="layout-flex layout-flex--wrap">
                    <h2 class="section__title layout-flex__item layout-flex__item--stretch" id="main-header" tabindex="-1">Contact information</h2>
                    <p class="layout-flex__item"><span aria-hidden="true">Already have an account?</span> <a href="/account/login?checkout_url=%2F41820389%2Fcheckouts">Log in</a></p>
                  </div>
                </div>
                <div class="section__content">
                  <div class="fieldset">
                    <div class="field field--required">
                      <div class="field__input-wrapper">
                        <label class="field__label field__label--visible" for="checkout_email">Email</label>
                        <input placeholder="Email" autocomplete="shipping email" class="field__input" size="30" type="email" name="checkout[email]" id="checkout_email" value="theo.lindqvist@protonmail.com">
                      </div>
                    </div>
                  </div>
                  <div class="checkbox-wrapper">
                    <div class="checkbox__input"><input class="input-checkbox" type="checkbox" value="1" name="checkout[buyer_accepts_marketing]" id="checkout_buyer_accepts_marketing"></div>
                    <label class="checkbox__label" for="checkout_buyer_accepts_marketing">Email me with news and offers</label>
                  </div>
                </div>
              </div>
              <div class="section section--shipping-address">
                <div class="section__header"><h2 class="section__title">Shipping address</h2></div>
                <div class="section__content">
                  <div class="fieldset">
                    <div class="address-fields">
                      <div class="field field--required field--show-floating-label">
                        <div class="field__input-wrapper field__input-wrapper--select">
                          <label class="field__label field__label--visible" for="checkout_shipping_address_country">Country/region</label>
                          <select class="field__input field__input--select" name="checkout[shipping_address][country]" id="checkout_shipping_address_country" autocomplete="shipping country">
                            <option value="United States" selected>United States</option>
                            <option value="Canada">Canada</option>
                          </select>
                        </div>
                      </div>
{v1_field("checkout_shipping_address_first_name", "checkout[shipping_address][first_name]", "First name (optional)", "half", "Theo", ' autocomplete="shipping given-name"', False)}
{v1_field("checkout_shipping_address_last_name", "checkout[shipping_address][last_name]", "Last name", "half", "Lindqvist", ' autocomplete="shipping family-name"')}
{v1_field("checkout_shipping_address_company", "checkout[shipping_address][company]", "Company (optional)", "", "", ' autocomplete="shipping organization"', False)}
{v1_field("checkout_shipping_address_address1", "checkout[shipping_address][address1]", "Address", "", "4127 Fremont Ave N", ' autocomplete="shipping address-line1"')}
{v1_field("checkout_shipping_address_address2", "checkout[shipping_address][address2]", "Apartment, suite, etc. (optional)", "", "", ' autocomplete="shipping address-line2"', False)}
{v1_field("checkout_shipping_address_city", "checkout[shipping_address][city]", "City", "three-eights", "Seattle", ' autocomplete="shipping address-level2"')}
{v1_state_select("checkout_shipping_address_province", "checkout[shipping_address][province]", "WA")}
{v1_field("checkout_shipping_address_zip", "checkout[shipping_address][zip]", "ZIP code", "quarter", "98103", ' autocomplete="shipping postal-code" inputmode="numeric"', True, T("t1"))}
{v1_field("checkout_shipping_address_phone", "checkout[shipping_address][phone]", "Phone (optional)", "", "", ' autocomplete="shipping tel"', False, itype="tel")}
                    </div>
                  </div>
                </div>
              </div>
              <div class="section section--shipping-method">
                <div class="section__header"><h2 class="section__title">Shipping method</h2></div>
                <div class="section__content">
                  <div class="content-box">
{rate_rows}
                  </div>
                </div>
              </div>
              <div class="section section--payment-method">
                <div class="section__header">
                  <h2 class="section__title">Payment</h2>
                  <p class="section__text">All transactions are secure and encrypted.</p>
                </div>
                <div class="section__content">
                  <fieldset class="content-box">
                    <legend class="visually-hidden">Choose a payment method</legend>
                    <div class="radio-wrapper content-box__row">
                      <div class="radio__input"><input class="input-radio" type="radio" value="credit_card" name="checkout[payment_gateway]" id="checkout_payment_gateway_card" checked></div>
                      <label class="radio__label" for="checkout_payment_gateway_card"><span class="radio__label__primary">Credit card</span>
                        <span class="radio__label__accessory"><span class="payment-icon payment-icon--visa">Visa</span> <span class="payment-icon payment-icon--master">Mastercard</span> <span class="payment-icon payment-icon--american-express">American Express</span></span></label>
                    </div>
                    <div class="radio-wrapper content-box__row content-box__row--secondary card-fields-container" id="payment-gateway-subfields-card">
                      <div class="fieldset payment-fields" data-credit-card-fields>
                        <div class="field field--required">
                          <div class="field__input-wrapper field__input-wrapper--icon-right">
                            <label class="field__label field__label--visible" for="checkout_credit_card_number">Card number</label>
                            <input class="field__input field__input--credit-card" id="checkout_credit_card_number" name="checkout[credit_card][number]" type="text" inputmode="numeric" autocomplete="cc-number" placeholder="Card number"{T("t2")}>
                            <div class="field__icon">{icon("lock", "field__icon-svg", 14)}</div>
                          </div>
                        </div>
                        <div class="field field--required">
                          <div class="field__input-wrapper">
                            <label class="field__label field__label--visible" for="checkout_credit_card_name">Name on card</label>
                            <input class="field__input" id="checkout_credit_card_name" name="checkout[credit_card][name]" type="text" autocomplete="cc-name" placeholder="Name on card" value="Theo Lindqvist">
                          </div>
                        </div>
                        <div class="field field--required field--half field--expiry">
                          <div class="field__input-wrapper">
                            <label class="field__label field__label--visible" for="checkout_credit_card_expiry">Expiration date (MM / YY)</label>
                            <input class="field__input" id="checkout_credit_card_expiry" name="checkout[credit_card][expiry]" type="text" inputmode="numeric" autocomplete="cc-exp" placeholder="Expiration date (MM / YY)"{T("t3")}>
                          </div>
                        </div>
                        <div class="field field--required field--half field--cvv">
                          <div class="field__input-wrapper field__input-wrapper--icon-right">
                            <label class="field__label field__label--visible" for="checkout_credit_card_verification_value">Security code</label>
                            <input class="field__input" id="checkout_credit_card_verification_value" name="checkout[credit_card][verification_value]" type="text" inputmode="numeric" autocomplete="cc-csc" placeholder="Security code">
                            <div class="field__icon">{icon("help", "field__icon-svg", 14)}</div>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div class="radio-wrapper content-box__row">
                      <div class="radio__input"><input class="input-radio" type="radio" value="paypal" name="checkout[payment_gateway]" id="checkout_payment_gateway_paypal"></div>
                      <label class="radio__label" for="checkout_payment_gateway_paypal"><span class="radio__label__primary">PayPal</span></label>
                    </div>
                  </fieldset>
                </div>
              </div>
              <div class="section section--billing-address">
                <div class="section__header">
                  <h2 class="section__title">Billing address</h2>
                  <p class="section__text">Select the address that matches your card or payment method.</p>
                </div>
                <div class="section__content">
                  <div class="checkbox-wrapper billing-toggle">
                    <div class="checkbox__input"><input class="input-checkbox" type="checkbox" id="billing_same_as_shipping" name="checkout[billing_same_as_shipping]" value="1" checked{T("t4")}></div>
                    <label class="checkbox__label" for="billing_same_as_shipping">Same as shipping address</label>
                  </div>
                  <div class="billing-address-fields" hidden>
{v1_field("checkout_billing_address_last_name", "checkout[billing_address][last_name]", "Last name", "half", "", ' autocomplete="billing family-name"')}
{v1_field("checkout_billing_address_address1", "checkout[billing_address][address1]", "Address", "", "", ' autocomplete="billing address-line1"')}
{v1_field("checkout_billing_address_city", "checkout[billing_address][city]", "City", "three-eights", "", ' autocomplete="billing address-level2"')}
{v1_field("checkout_billing_address_zip", "checkout[billing_address][zip]", "ZIP code", "quarter", "", ' autocomplete="billing postal-code"')}
                  </div>
                </div>
              </div>
            </div>
            <div class="step__footer">
              <button name="button" type="submit" id="continue_button" class="step__footer__continue-btn btn" aria-busy="false"{T("t5")}><span class="btn__content">Pay now</span></button>
              <a class="step__footer__previous-link" href="https://copperlinecoffee.com/cart">{icon("chev-left", "previous-link__icon", 10)}<span class="step__footer__previous-link-content">Return to cart</span></a>
            </div>
          </form>
        </div>
      </main>
      <footer class="main__footer" role="contentinfo">
        <ul class="policy-list">
{links(policies, ' class="policy-list__item"', '')}
        </ul>
      </footer>
    </div>
    <aside class="sidebar" id="order-summary" role="complementary">
      <div class="sidebar__header"><h2 class="visually-hidden">Order summary</h2></div>
      <div class="sidebar__content">
        <div class="order-summary">
          <div class="order-summary__section order-summary__section--product-list">
            <table class="product-table">
              <caption class="visually-hidden">Shopping cart</caption>
              <thead class="product-table__header"><tr><th scope="col"><span class="visually-hidden">Product image</span></th><th scope="col"><span class="visually-hidden">Description</span></th><th scope="col"><span class="visually-hidden">Quantity</span></th><th scope="col"><span class="visually-hidden">Price</span></th></tr></thead>
              <tbody>
{v1_products}
              </tbody>
            </table>
          </div>
          <div class="order-summary__section order-summary__section--discount">
            <form class="edit_checkout" action="/41820389/checkouts/7d1f2b9c40e5a8f3/discount" method="post">
              <div class="field">
                <div class="field__input-btn-wrapper">
                  <div class="field__input-wrapper">
                    <label class="field__label" for="checkout_reduction_code">Gift card or discount code</label>
                    <input placeholder="Gift card or discount code" class="field__input" type="text" name="checkout[reduction_code]" id="checkout_reduction_code">
                  </div>
                  <button name="button" type="submit" class="field__input-btn btn btn--disabled" disabled>Apply</button>
                </div>
              </div>
            </form>
          </div>
          <div class="order-summary__section order-summary__section--total-lines">
            <table class="total-line-table">
              <caption class="visually-hidden">Cost summary</caption>
              <thead><tr><th scope="col"><span class="visually-hidden">Description</span></th><th scope="col"><span class="visually-hidden">Price</span></th></tr></thead>
              <tbody class="total-line-table__tbody">
{v1_totals}
              </tbody>
              <tfoot class="total-line-table__footer">
                <tr class="total-line">
                  <th class="total-line__name payment-due-label" scope="row"><span class="payment-due-label__total">Total</span></th>
                  <td class="total-line__price payment-due"><span class="payment-due__currency">USD</span> <span class="payment-due__price"{T("t6")}>$126.68</span></td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      </div>
    </aside>
  </div>
</div>
"""
    v1 = document(
        title="Information &amp; payment - Copperline Coffee Roasters - Checkout",
        head=f"""<meta name="referrer" content="origin">
<style>{v1_css}</style>""",
        body=v1_body,
    )

    # ---------------------------------------------------------------- v2: styled-components one-page checkout
    pay_css = (":host{display:block;margin-top:12px}.form{display:grid;gap:12px}.row{display:grid;grid-template-columns:1fr 1fr;"
               "gap:12px}.label{display:block;font:500 13px/1.4 system-ui;color:#30313d;margin-bottom:4px}.input-wrap{position:relative}"
               ".input{width:100%;box-sizing:border-box;padding:12px;border:1px solid #e6e6e6;border-radius:6px;font:16px system-ui}"
               ".input:focus{outline:2px solid #8a4b1f}.brands{position:absolute;right:10px;top:10px;display:flex;gap:4px}")
    card_brand = ('<svg width="24" height="16" viewBox="0 0 24 16" aria-hidden="true"><rect width="24" height="16" rx="2" '
                  'fill="#1a1f71"/><path d="M6 11 8 5h2l-2 6zm5 0 1-6h2l-1 6z" fill="#fff"/></svg>')

    def v2_input(fid: str, name: str, label: str, value: str = "", extra: str = "", mark: str = "", optional: bool = False,
                 itype: str = "text") -> str:
        val = f' value="{esc(value)}"' if value else ""
        opt = " (optional)" if optional else ""
        return (f'<div class="~FieldWrapper">\n  <div class="~FloatingField">\n'
                f'    <input id="{fid}" class="~TextInput" name="{name}" type="{itype}" placeholder="{esc(label)}{opt}"{val}{extra}{mark}>\n'
                f'    <label class="~FloatingLabel" for="{fid}">{label}{opt}</label>\n  </div>\n</div>')

    def v2_state(fid: str, name: str, selected: str) -> str:
        return (f'<div class="~FieldWrapper">\n  <div class="~SelectField">\n'
                f'    <label class="~FloatingLabel:static" for="{fid}">State</label>\n'
                f'    <select id="{fid}" class="~NativeSelect" name="{name}" autocomplete="address-level1">\n{opts(US_STATES, selected)}\n    </select>\n'
                f'    <span class="~SelectChevron">{icon("chev-down", size=14)}</span>\n  </div>\n</div>')

    v2_items = "\n".join(
        f'''<li class="~LineItem">
  <div class="~LineItem:thumb">{thumb(c)}<span class="~QuantityBadge" aria-label="Quantity">{q}</span></div>
  <div class="~LineItem:details"><p class="~LineItem:title">{n}</p><p class="~LineItem:variant">{v}</p></div>
  <p class="~LineItem:price">{p}</p>
</li>''' for n, v, q, p, c in items[::-1])

    v2_rates = "\n".join(
        f'''<label class="~RateOption{':selected' if key == 'standard' else ''}" for="shipping-{key}">
  <input type="radio" id="shipping-{key}" name="shippingRate" value="{key}"{" checked" if key == "standard" else ""} class="~RadioInput">
  <span class="~RateOption:label">{label}</span><span class="~RateOption:price">{price}</span>
</label>''' for key, label, price in [("expedited", "2-day shipping (UPS 2nd Day Air)", "$14.50"),
                                       ("standard", "Ground (5 to 7 business days)", "$6.90")])

    v2_body = f"""
<div id="app">
<header class="~CheckoutHeader">
  <div class="~CheckoutHeader:inner">
    <a class="~BrandLink" href="https://copperlinecoffee.com" aria-label="Copperline Coffee Roasters">
      <svg width="34" height="34" viewBox="0 0 34 34" aria-hidden="true"><circle cx="17" cy="17" r="16" fill="#8a4b1f"/><path d="M11 22c4-1 8-6 12-11" stroke="#fde68a" stroke-width="2.5" fill="none"/></svg>
      <span class="~BrandLink:text">Copperline</span>
    </a>
    <p class="~SecureBadge">{icon("lock", size=14)}<span>Secure checkout</span></p>
    <a class="~CartLink" href="https://copperlinecoffee.com/cart" aria-label="Back to cart">{icon("home", size=20)}</a>
  </div>
</header>
<div class="~SummaryToggleBar">
  <button type="button" class="~SummaryToggle" aria-expanded="false" aria-controls="order-summary">
    <span class="~SummaryToggle:label">Show order summary</span>{icon("chev-down", size=14)}
    <strong class="~SummaryToggle:total">$126.68</strong>
  </button>
</div>
<div class="~Layout">
  <main class="~MainColumn" id="checkout-main-column">
    <form id="checkout-main" class="~CheckoutForm" action="/checkouts/cn/Z2NwLXVzLWVhc3QxOjAxSjk3/submit" method="post" novalidate>
      <input type="hidden" name="checkoutToken" value="Z2NwLXVzLWVhc3QxOjAxSjk3WDBQS0NKR1E">
      <section class="~ExpressCheckout" aria-labelledby="express-title">
        <h2 id="express-title" class="~SectionTitle:centered">Express checkout</h2>
        <div class="~ExpressCheckout:buttons">
          <button type="button" class="~WalletButton:shop" aria-label="Pay with Shop Pay">Shop Pay</button>
          <button type="button" class="~WalletButton:paypal" aria-label="Pay with PayPal">PayPal</button>
          <button type="button" class="~WalletButton:gpay" aria-label="Pay with Google Pay">G Pay</button>
        </div>
        <p class="~OrDivider"><span>OR</span></p>
      </section>
      <section class="~Section" aria-labelledby="contact-title">
        <div class="~SectionHeader">
          <h2 id="contact-title" class="~SectionTitle">Contact</h2>
          <a class="~InlineLink" href="/account/login?return_to=%2Fcheckouts%2Fcn">Log in</a>
        </div>
        <div class="~FieldWrapper">
          <div class="~FloatingField">
            <input id="email" class="~TextInput" name="email" type="email" autocomplete="email" placeholder="Email" value="theo.lindqvist@protonmail.com">
            <label class="~FloatingLabel" for="email">Email</label>
          </div>
        </div>
        <div class="~CheckboxRow">
          <input type="checkbox" id="marketing_opt_in" name="marketing_opt_in" class="~CheckboxInput">
          <label for="marketing_opt_in">Email me with news and offers</label>
        </div>
      </section>
      <section class="~Section" aria-labelledby="delivery-title">
        <h2 id="delivery-title" class="~SectionTitle">Delivery</h2>
        <div class="~SegmentedChoice" role="radiogroup" aria-label="Choose a delivery method">
          <label class="~SegmentedChoice:option-selected"><input type="radio" name="deliveryStrategy" value="SHIPPING" checked class="~RadioInput"><span>Ship</span></label>
          <label class="~SegmentedChoice:option"><input type="radio" name="deliveryStrategy" value="PICK_UP" class="~RadioInput"><span>Pick up in Portland</span></label>
        </div>
        <div class="~FieldWrapper">
          <div class="~SelectField">
            <label class="~FloatingLabel:static" for="Select0">Country/Region</label>
            <select id="Select0" class="~NativeSelect" name="countryCode" autocomplete="shipping country"><option value="US" selected>United States</option><option value="CA">Canada</option></select>
            <span class="~SelectChevron">{icon("chev-down", size=14)}</span>
          </div>
        </div>
        <div class="~FieldRow">
{v2_input("TextField0", "firstName", "First name", "Theo", ' autocomplete="shipping given-name"', optional=True)}
{v2_input("TextField1", "lastName", "Last name", "Lindqvist", ' autocomplete="shipping family-name"')}
        </div>
{v2_input("TextField2", "company", "Company", "", ' autocomplete="shipping organization"', optional=True)}
{v2_input("shipping-address1", "address1", "Address", "4127 Fremont Ave N", ' autocomplete="shipping address-line1" role="combobox" aria-expanded="false" aria-autocomplete="list"')}
{v2_input("TextField3", "address2", "Apartment, suite, etc.", "", ' autocomplete="shipping address-line2"', optional=True)}
        <div class="~FieldRow:three">
{v2_input("TextField4", "postalCode", "ZIP code", "98103", ' autocomplete="shipping postal-code" inputmode="numeric"', T("t1"))}
{v2_input("TextField5", "city", "City", "Seattle", ' autocomplete="shipping address-level2"')}
{v2_state("Select1", "zone", "WA")}
        </div>
{v2_input("TextField6", "phone", "Phone", "", ' autocomplete="shipping tel"', optional=True, itype="tel")}
        <div class="~CheckboxRow">
          <input type="checkbox" id="save_shipping_information" name="save_shipping_information" class="~CheckboxInput">
          <label for="save_shipping_information">Save this information for next time</label>
        </div>
      </section>
      <section class="~Section" aria-labelledby="shipping-method-title">
        <h2 id="shipping-method-title" class="~SectionTitle">Shipping method</h2>
        <div class="~RateList">
{v2_rates}
        </div>
      </section>
      <section class="~Section" aria-labelledby="payment-title">
        <h2 id="payment-title" class="~SectionTitle">Payment</h2>
        <p class="~SectionText">All transactions are secure and encrypted.</p>
        <fieldset class="~PaymentMethods">
          <legend class="~VisuallyHidden">Choose a payment method</legend>
          <div class="~PaymentOption:selected">
            <div class="~PaymentOption:header">
              <input type="radio" id="basic-creditCards" name="paymentMethod" value="credit_card" checked class="~RadioInput">
              <label for="basic-creditCards" class="~PaymentOption:label">Credit card</label>
              <span class="~CardBrands">{card_brand}{card_brand}{card_brand}</span>
            </div>
            <div class="~PaymentOption:body">
              <cl-payment-element class="~PaymentElement" data-client-secret="pi_3QdX2kL9vR8sT1_secret_8Kq">
                <template shadowrootmode="open">
                  <style>{pay_css}</style>
                  <div class="form" part="form">
                    <div class="field number">
                      <label class="label" for="Field-numberInput">Card number</label>
                      <div class="input-wrap"><input id="Field-numberInput" class="input" name="number" type="text" inputmode="numeric" autocomplete="cc-number" placeholder="1234 1234 1234 1234" aria-invalid="false"{T("t2")}><div class="brands">{card_brand}</div></div>
                    </div>
                    <div class="row">
                      <div class="field expiry">
                        <label class="label" for="Field-expiryInput">Expiration date</label>
                        <div class="input-wrap"><input id="Field-expiryInput" class="input" name="expiry" type="text" inputmode="numeric" autocomplete="cc-exp" placeholder="MM / YY" aria-invalid="false"{T("t3")}></div>
                      </div>
                      <div class="field cvc">
                        <label class="label" for="Field-cvcInput">Security code</label>
                        <div class="input-wrap"><input id="Field-cvcInput" class="input" name="cvc" type="text" inputmode="numeric" autocomplete="cc-csc" placeholder="CVC" aria-invalid="false"></div>
                      </div>
                    </div>
                    <div class="field name">
                      <label class="label" for="Field-nameInput">Name on card</label>
                      <div class="input-wrap"><input id="Field-nameInput" class="input" name="name" type="text" autocomplete="cc-name" value="Theo Lindqvist"></div>
                    </div>
                  </div>
                </template>
              </cl-payment-element>
              <fieldset class="~BillingChoice">
                <legend class="~BillingChoice:legend">Billing address</legend>
                <div class="~RadioRow">
                  <input type="radio" id="billing-same" name="billingAddressChoice" value="same" checked class="~RadioInput"{T("t4")}>
                  <label for="billing-same">Same as shipping address</label>
                </div>
                <div class="~RadioRow">
                  <input type="radio" id="billing-different" name="billingAddressChoice" value="different" class="~RadioInput">
                  <label for="billing-different">Use a different billing address</label>
                </div>
                <div class="~BillingFields" hidden>
{v2_input("TextField7", "lastName", "Last name", "", ' autocomplete="billing family-name"')}
{v2_input("TextField8", "address1", "Address", "", ' autocomplete="billing address-line1"')}
{v2_input("TextField9", "postalCode", "ZIP code", "", ' autocomplete="billing postal-code" inputmode="numeric"')}
{v2_input("TextField10", "city", "City", "", ' autocomplete="billing address-level2"')}
                </div>
              </fieldset>
            </div>
          </div>
          <div class="~PaymentOption">
            <div class="~PaymentOption:header">
              <input type="radio" id="basic-paypal" name="paymentMethod" value="paypal" class="~RadioInput">
              <label for="basic-paypal" class="~PaymentOption:label">PayPal</label>
            </div>
          </div>
          <div class="~PaymentOption">
            <div class="~PaymentOption:header">
              <input type="radio" id="basic-affirm" name="paymentMethod" value="affirm" class="~RadioInput">
              <label for="basic-affirm" class="~PaymentOption:label">Pay over time with Affirm</label>
            </div>
          </div>
        </fieldset>
      </section>
      <div class="~SubmitRow">
        <button type="submit" id="checkout-pay-button" class="~PrimaryButton"{T("t5")}><span class="~PrimaryButton:label">Pay now</span></button>
      </div>
    </form>
    <footer class="~PolicyFooter">
      <ul class="~PolicyFooter:list">
{links(policies[::-1], ' class="~PolicyFooter:item"', ' class="~PolicyFooter:link"')}
      </ul>
    </footer>
  </main>
  <aside id="order-summary" class="~SummaryColumn" aria-label="Order summary">
    <ul class="~LineItems">
{v2_items}
    </ul>
    <div class="~DiscountRow">
      <div class="~FloatingField">
        <input id="ReductionsInput0" class="~TextInput" name="reductions" type="text" placeholder="Discount code or gift card">
        <label class="~FloatingLabel" for="ReductionsInput0">Discount code or gift card</label>
      </div>
      <button type="button" class="~SecondaryButton" disabled>Apply</button>
    </div>
    <dl class="~Totals">
      <div class="~TotalRow"><dt>Subtotal &middot; 4 items</dt><dd>$108.00</dd></div>
      <div class="~TotalRow"><dt>Shipping</dt><dd>$6.90</dd></div>
      <div class="~TotalRow"><dt>Estimated taxes</dt><dd>$11.78</dd></div>
      <div class="~TotalRow:grand"><dt>Total</dt><dd><abbr class="~Currency" title="United States dollars">USD</abbr> <strong class="~GrandTotal"{T("t6")}>$126.68</strong></dd></div>
    </dl>
  </aside>
</div>
<div class="~MobilePayBar" role="region" aria-label="Pay">
  <strong class="~MobilePayBar:total">$126.68</strong>
  <button type="submit" form="checkout-main" class="~PrimaryButton">Pay now</button>
</div>
</div>
"""
    v2 = document(
        title="Checkout - Copperline Coffee Roasters",
        head="""<meta name="robots" content="noindex">
<style data-styled="active" data-styled-version="5.3.11"></style>""",
        body=expand_classes(v2_body, styled_components("copperline")),
    )

    m = meta(
        "form-03",
        "Checkout: shipping address + card payment — Copperline Coffee Roasters",
        ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change", "copy-change",
         "attribute-churn", "structure-move", "insertion", "tag-change"],
        "v1 is a classic hosted checkout (field__input / total-line-table markup, Rails-style checkout[...] names). v2 is "
        "a one-page styled-components checkout (sc-xxxxxx classes, short names like postalCode/zone). The card fields "
        "move into a <cl-payment-element> declarative shadow root with new ids/placeholders ('MM / YY'); the billing "
        "checkbox becomes a 'Same as shipping address' / 'Use a different billing address' radio pair inside the "
        "payment block; ZIP code now precedes City/State; the order-summary tables become a list and a <dl>. Decoys: "
        "hidden billing fields reusing name=postalCode, an express-checkout wallet row, a mobile order-summary toggle "
        "and a sticky mobile pay bar that both repeat the $126.68 total, and a second 'Pay now' button.",
        [
            target("t1", "ZIP code input of the shipping address",
                   "#checkout_shipping_address_zip", "//input[@name='checkout[shipping_address][zip]']",
                   ["class-obfuscation", "wrapper-divs", "id-change", "attribute-churn", "sibling-reorder", "decoy"]),
            target("t2", "Card number input",
                   "#checkout_credit_card_number", "//input[@autocomplete='cc-number']",
                   ["shadow-dom", "class-obfuscation", "id-change", "attribute-churn", "structure-move"]),
            target("t3", "Card expiration date (MM / YY) input",
                   ".field--expiry .field__input", "//input[@placeholder='Expiration date (MM / YY)']",
                   ["shadow-dom", "class-obfuscation", "id-change", "attribute-churn", "copy-change", "structure-move"]),
            target("t4", "'Same as shipping address' billing control (checkbox in v1, radio in v2)",
                   "input#billing_same_as_shipping", "//div[@class='checkbox-wrapper billing-toggle']//input[@type='checkbox']",
                   ["class-obfuscation", "wrapper-divs", "id-change", "attribute-churn", "structure-move", "decoy"]),
            target("t5", "'Pay now' submit button",
                   ".step__footer__continue-btn", "//button[normalize-space()='Pay now']",
                   ["class-obfuscation", "id-change", "decoy"]),
            target("t6", "Order total amount ($126.68) in the order summary",
                   ".total-line-table .payment-due__price", "//tfoot//span[contains(@class,'payment-due__price')]",
                   ["class-obfuscation", "tag-change", "structure-move", "decoy"]),
        ],
    )
    return v1, v2, m


# ======================================================================================
# form-04 - Meridian Robotics careers: job application
# ======================================================================================
@suite("form-04")
def form04():
    title = "Senior Embedded Software Engineer"
    about = ("Meridian Robotics builds autonomous inspection robots that crawl, climb and fly through bridges, tunnels and "
             "power plants so people don't have to. Our robots have inspected more than 2,300 structures across North "
             "America for state DOTs, utilities and rail operators.")
    duties = [
        "Own firmware for the motor-control and sensor-fusion boards on our Crawler and Kestrel platforms",
        "Design and review real-time software on Zephyr RTOS and embedded Linux (Yocto)",
        "Bring up new boards with our electrical engineers, from first power-on to field release",
        "Build hardware-in-the-loop test rigs and run them in CI on every merge",
        "Mentor engineers and help set the technical direction of the embedded team",
    ]
    reqs = [
        "6+ years writing production C or C++ for microcontrollers (ARM Cortex-M, STM32, NXP i.MX RT)",
        "Deep familiarity with RTOS concepts, interrupts, DMA and low-power design",
        "Comfort with oscilloscopes, logic analyzers and reading schematics",
        "Experience with CAN, SPI, I²C, UART and Ethernet-based protocols",
        "You have shipped over-the-air update mechanisms for a fleet of devices",
        "Clear written communication; you document decisions as you go",
    ]
    nice = ["Rust on embedded targets", "Field-oriented motor control (FOC)", "Functional safety (IEC 61508, ISO 13849)"]
    perks = [
        "Medical, dental and vision insurance with 100% of employee premiums covered",
        "401(k) with a 4% company match",
        "16 weeks of paid parental leave",
        "$2,000 yearly learning budget",
        "Hybrid schedule: in our Strip District office Tuesday to Thursday",
    ]
    hear = ["LinkedIn", "Indeed", "Employee referral", "Meridian website", "University career fair", "Other"]
    process = [
        "30-minute intro call with a recruiter",
        "60-minute technical conversation with an embedded engineer (no whiteboard puzzles)",
        "Take-home exercise: review a short driver patch, about 2 hours",
        "Onsite in Pittsburgh: lab session, system design and lunch with the team",
    ]
    similar = [("Embedded Software Engineer II", "/meridian/4718117"), ("Firmware Engineer, Power Systems", "/meridian/4720931"),
               ("Staff Robotics Software Engineer", "/meridian/4699020"), ("Hardware Test Engineer", "/meridian/4722405")]
    logo = ('<svg width="40" height="40" viewBox="0 0 40 40" aria-hidden="true"><rect width="40" height="40" rx="10" fill="#0e7490"/>'
            '<path d="M9 28V12l11 9 11-9v16" stroke="#ecfeff" stroke-width="3" fill="none"/></svg>')
    gender = [("1", "Male"), ("2", "Female"), ("3", "Decline To Self Identify")]
    hispanic = [("1", "Yes"), ("2", "No"), ("3", "Decline To Self Identify")]
    veteran = [("1", "I am not a protected veteran"),
               ("2", "I identify as one or more of the classifications of protected veteran"),
               ("3", "I don't wish to answer")]
    disability = [("1", "Yes, I have a disability (or previously had a disability)"),
                  ("2", "No, I do not have a disability"), ("3", "I do not want to answer")]

    def ul(items: list[str]) -> str:
        return "<ul>\n" + "\n".join(f"<li>{esc(i)}</li>" for i in items) + "\n</ul>"

    # ---------------------------------------------------------------- v1: hosted job board (ids + Rails names)
    v1_css = """
  body { margin: 0; font: 15px/1.6 Georgia, "Times New Roman", serif; color: #222; background: #fff; }
  #wrapper { max-width: 760px; margin: 0 auto; padding: 32px 20px; }
  #header .app-title { font-size: 28px; margin: 12px 0 0; color: #0e7490; }
  #header .company-name { color: #555; }
  #application { border-top: 2px solid #0e7490; margin-top: 40px; padding-top: 24px; }
  .field { margin-bottom: 18px; }
  .field label { display: block; font-weight: bold; margin-bottom: 4px; }
  .field input[type=text], .field input[type=email], .field input[type=tel], .field select, .field textarea { width: 100%; max-width: 420px; padding: 6px; }
  .asterisk { color: #c00; }
  .attach-or-paste .link-container a { color: #0e7490; }
  .drop-zone { border: 1px dashed #aaa; padding: 8px; color: #777; max-width: 420px; }
  #submit_app { background: #0e7490; color: #fff; border: 0; padding: 10px 24px; font-size: 16px; cursor: pointer; }
"""

    def v1_select(fid: str, name: str, label: str, choices, mark: str = "", required: bool = False) -> str:
        star = ' <span class="asterisk">*</span>' if required else ""
        return (f'<div class="field">\n  <label for="{fid}">{esc(label)}{star}</label>\n'
                f'  <select id="{fid}" name="{name}"{mark}>\n<option value="">Please select</option>\n{opts(choices)}\n  </select>\n</div>')

    def attach_links(field: str) -> str:
        return (f'<div class="link-container">\n'
                f'  <a class="link-button" data-source="attach" data-field="{field}" href="#">Attach</a>,\n'
                f'  <a class="link-button" data-source="dropbox" data-field="{field}" href="#">Dropbox</a>,\n'
                f'  <a class="link-button" data-source="google-drive" data-field="{field}" href="#">Google Drive</a>, or\n'
                f'  <a class="link-button" data-source="paste" data-field="{field}" href="#">enter manually</a>\n</div>')

    v1_body = f"""
<div id="wrapper">
  <div id="app_body">
    <div id="header">
      <a href="https://meridianrobotics.com" class="logo-link" aria-label="Meridian Robotics">{logo}</a>
      <h1 class="app-title">{title}</h1>
      <span class="company-name">at Meridian Robotics</span>
      <div class="location">Pittsburgh, PA (Hybrid)</div>
    </div>
    <div id="content">
      <p><strong>About Meridian</strong></p>
      <p>{esc(about)}</p>
      <p><strong>What you'll do</strong></p>
{ul(duties)}
      <p><strong>What we're looking for</strong></p>
{ul(reqs)}
      <p><strong>Nice to have</strong></p>
{ul(nice)}
      <p><strong>Compensation</strong></p>
      <p>The base salary range for this role is $165,000&ndash;$205,000 per year, plus equity and an annual bonus. Final offers depend on experience and location.</p>
      <p><strong>Benefits</strong></p>
{ul(perks)}
      <p><strong>Our interview process</strong></p>
{"<ol>" + chr(10).join(f"<li>{esc(i)}</li>" for i in process) + "</ol>"}
      <p><em>Meridian Robotics is an equal opportunity employer. We welcome applicants of every background and do not discriminate on the basis of race, religion, color, national origin, gender, sexual orientation, age, marital status, veteran status or disability status.</em></p>
    </div>
    <div id="application">
      <div class="heading">
        <h2>Apply for this Job</h2>
        <div class="required-fields"><span class="asterisk">*</span> Required</div>
      </div>
      <form id="application_form" action="https://boards.meridianrobotics.com/embed/job_app?token=4718203" method="post" enctype="multipart/form-data" accept-charset="UTF-8" novalidate>
        <input type="hidden" name="utf8" value="&#x2713;">
        <input type="hidden" name="authenticity_token" value="gR8kq2Zp0WvYx7Lm4NcT1sBa9Ue3HdJf6OiQy5Vr">
        <input type="hidden" name="job_application[job_id]" value="4718203">
        <div id="main_fields">
          <div class="field">
            <label for="first_name">First Name <span class="asterisk">*</span></label>
            <input type="text" id="first_name" name="job_application[first_name]" autocomplete="given-name" maxlength="255" aria-required="true" value="Nadia">
          </div>
          <div class="field">
            <label for="last_name">Last Name <span class="asterisk">*</span></label>
            <input type="text" id="last_name" name="job_application[last_name]" autocomplete="family-name" maxlength="255" aria-required="true" value="Haddad">
          </div>
          <div class="field">
            <label for="email">Email <span class="asterisk">*</span></label>
            <input type="email" id="email" name="job_application[email]" autocomplete="email" maxlength="255" aria-required="true" value="nadia.haddad@hey.com"{T("t6")}>
          </div>
          <div class="field">
            <label for="phone">Phone</label>
            <input type="tel" id="phone" name="job_application[phone]" autocomplete="tel" maxlength="255" value="+1 412 555 0186">
          </div>
          <div class="field">
            <label for="job_application_location">Location (City)</label>
            <input type="text" id="job_application_location" name="job_application[location]" autocomplete="off" value="Pittsburgh, Pennsylvania, United States">
            <a href="#" class="locate-me">Locate me</a>
          </div>
          <div id="resume_fieldset" class="field">
            <label id="resume_label">Resume/CV <span class="asterisk">*</span></label>
            <div class="attach-or-paste" data-field="resume">
              <input type="file" id="resume_file" name="job_application[resume]" class="visible-resume-upload" accept=".pdf,.doc,.docx,.txt,.rtf" aria-labelledby="resume_label"{T("t1")}>
{attach_links("resume")}
              <div class="drop-zone">Drop files here</div>
              <span class="accepted-filetypes">(File types: pdf, doc, docx, txt, rtf)</span>
            </div>
          </div>
          <div id="cover_letter_fieldset" class="field">
            <label id="cover_letter_label">Cover Letter</label>
            <div class="attach-or-paste" data-field="cover_letter">
              <input type="file" id="cover_letter_file" name="job_application[cover_letter]" accept=".pdf,.doc,.docx,.txt,.rtf" aria-labelledby="cover_letter_label">
{attach_links("cover_letter")}
              <textarea id="cover_letter_text" name="job_application[cover_letter_text]" rows="8" aria-labelledby="cover_letter_label"{T("t3")}></textarea>
            </div>
          </div>
        </div>
        <div id="custom_fields">
          <div class="field">
            <label for="job_application_answers_attributes_0_text_value">LinkedIn Profile</label>
            <input type="text" id="job_application_answers_attributes_0_text_value" name="job_application[answers_attributes][0][text_value]" autocomplete="url" value="https://www.linkedin.com/in/nadiahaddad"{T("t2")}>
            <input type="hidden" name="job_application[answers_attributes][0][question_id]" value="61827301">
          </div>
          <div class="field">
            <label for="job_application_answers_attributes_1_text_value">Website</label>
            <input type="text" id="job_application_answers_attributes_1_text_value" name="job_application[answers_attributes][1][text_value]" autocomplete="url" value="https://nadiahaddad.dev">
            <input type="hidden" name="job_application[answers_attributes][1][question_id]" value="61827302">
          </div>
{v1_select("job_application_answers_attributes_2_boolean_value", "job_application[answers_attributes][2][boolean_value]", "Are you legally authorized to work in the United States?", [("1", "Yes"), ("0", "No")], required=True)}
{v1_select("job_application_answers_attributes_3_boolean_value", "job_application[answers_attributes][3][boolean_value]", "Will you now or in the future require sponsorship for employment visa status (e.g. H-1B visa status)?", [("1", "Yes"), ("0", "No")], required=True)}
{v1_select("job_application_answers_attributes_4_answer_selected_options_attributes_0_question_option_id", "job_application[answers_attributes][4][answer_selected_options_attributes][0][question_option_id]", "How did you hear about this job?", [(str(70110 + i), o) for i, o in enumerate(hear)])}
{v1_select("job_application_answers_attributes_5_boolean_value", "job_application[answers_attributes][5][boolean_value]", "Are you able to work from our Pittsburgh office Tuesday to Thursday?", [("1", "Yes"), ("0", "No")], required=True)}
          <div class="field">
            <label for="job_application_answers_attributes_6_text_value">When could you start?</label>
            <input type="text" id="job_application_answers_attributes_6_text_value" name="job_application[answers_attributes][6][text_value]" placeholder="e.g. 4 weeks after an offer">
          </div>
          <div class="field">
            <label for="job_application_answers_attributes_7_text_value">Pronouns</label>
            <input type="text" id="job_application_answers_attributes_7_text_value" name="job_application[answers_attributes][7][text_value]" placeholder="Optional">
          </div>
        </div>
        <div id="eeoc_fields">
          <div class="eeoc-description">
            <h3>U.S. Equal Employment Opportunity Information (Completion is voluntary and will not subject you to adverse treatment)</h3>
            <p>Our company values diversity. To ensure that we comply with reporting requirements and to learn more about how we can increase diversity in our candidate pool, we invite you to voluntarily provide demographic information in a confidential survey at the end of this application. Providing this information is optional. It will not be accessible or used in the hiring process, and has no effect on your opportunity for employment.</p>
          </div>
{v1_select("job_application_gender", "job_application[gender]", "Gender", gender)}
{v1_select("job_application_hispanic_ethnicity", "job_application[hispanic_ethnicity]", "Are you Hispanic/Latino?", hispanic)}
{v1_select("job_application_veteran_status", "job_application[veteran_status]", "Veteran Status", veteran, T("t4"))}
{v1_select("job_application_disability_status", "job_application[disability_status]", "Disability Status", disability)}
          <div class="eeoc-definitions">
            <p>Form CC-305 &middot; OMB Control Number 1250-0005 &middot; Expires 04/30/2026. <a href="https://www.dol.gov/agencies/ofccp/self-id-forms" target="_blank" rel="noopener">Read more about the voluntary self-identification of disability form</a></p>
          </div>
        </div>
        <div id="submit_buttons">
          <input type="submit" id="submit_app" value="Submit Application"{T("t5")}>
        </div>
      </form>
    </div>
  </div>
  <div id="footer">
    <p>Powered by <a href="https://boards.meridianrobotics.com/">Meridian Careers</a></p>
    <p><a href="https://meridianrobotics.com/privacy">Read our Privacy Policy</a></p>
  </div>
</div>
"""
    v1 = document(
        title=f"Job Application for {title} at Meridian Robotics",
        head=f"""<meta name="description" content="Meridian Robotics is hiring a {title} in Pittsburgh, PA.">
<style>{v1_css}</style>""",
        body=v1_body,
    )

    # ---------------------------------------------------------------- v2: Ashby-style board, emotion classes
    upload_css = (":host{display:block}.dropzone{border:1.5px dashed #94a3b8;border-radius:12px;padding:20px;text-align:center;"
                  "font:14px/1.5 system-ui;color:#334155}.title{display:block;font-weight:600;color:#0f172a}.req{color:#dc2626}"
                  ".hint,.types{color:#64748b;font-size:13px;margin:4px 0}.actions{display:flex;justify-content:center;gap:6px;"
                  "align-items:center;margin:12px 0}.cta{color:#0e7490;font-weight:600}.file{position:absolute;inset:0;opacity:0;cursor:pointer}")

    def upload(name: str, title_text: str, hint: str, required: bool, mark: str = "") -> str:
        req = ' <span class="req" aria-hidden="true">*</span>' if required else ""
        return f"""<ats-file-upload name="{name}" accept=".pdf,.doc,.docx,.odt,.rtf"{" required" if required else ""} class="~UploadHost">
            <template shadowrootmode="open">
              <style>{upload_css}</style>
              <div class="dropzone" part="dropzone">
                <label class="title" for="file-input">{title_text}{req}</label>
                <p class="hint">{hint}</p>
                <div class="actions">{icon("upload", "icon", 18)}<span class="cta">Upload file</span><span class="or">or drag and drop here</span></div>
                <input id="file-input" class="file" type="file" name="{name}" accept=".pdf,.doc,.docx,.odt,.rtf" aria-describedby="types"{mark}>
                <p id="types" class="types">PDF, DOC, DOCX, ODT or RTF, up to 10 MB</p>
              </div>
            </template>
          </ats-file-upload>"""

    def entry(fid: str, label: str, control: str, required: bool = False, hint: str = "") -> str:
        req = '<span class="~RequiredMark" aria-hidden="true">*</span>' if required else ""
        hint_html = f'\n          <p class="~FieldHint">{hint}</p>' if hint else ""
        return f"""<div class="~FieldEntry">
          <label class="~FieldLabel" for="{fid}">{label}{req}</label>
          <div class="~InputShell">{control}</div>{hint_html}
        </div>"""

    def combo(key: str, label: str, mark: str = "") -> str:
        return f"""<div class="~FieldEntry">
            <span class="~FieldLabel" id="eeo-{key}-label">{label}</span>
            <button type="button" class="~ComboTrigger" role="combobox" aria-haspopup="listbox" aria-expanded="false" aria-controls="eeo-{key}-listbox" aria-labelledby="eeo-{key}-label"{mark}>Select&hellip;{icon("chev-down", "~ComboChevron", 16)}</button>
            <input type="hidden" name="eeo[{key}]" value="">
          </div>"""

    def yes_no(key: str, legend: str) -> str:
        return f"""<fieldset class="~FieldEntry">
          <legend class="~FieldLabel">{legend}<span class="~RequiredMark" aria-hidden="true">*</span></legend>
          <div class="~RadioRow"><label class="~RadioOption"><input type="radio" name="{key}" value="yes" class="~RadioInput"> Yes</label><label class="~RadioOption"><input type="radio" name="{key}" value="no" class="~RadioInput"> No</label></div>
        </fieldset>"""

    v2_body = f"""
<div id="root">
<div class="~AppShell">
  <header class="~BoardHeader">
    <a class="~BoardBrand" href="https://jobs.meridianrobotics.com">{logo}<span class="~BoardBrandName">Meridian Robotics</span></a>
    <nav class="~BoardNav" aria-label="Careers">
      <a class="~BoardNavLink" href="https://jobs.meridianrobotics.com">All open roles (24)</a>
      <a class="~BoardNavLink" href="https://meridianrobotics.com/life">Life at Meridian</a>
      <a class="~BoardNavLink" href="https://meridianrobotics.com/benefits">Benefits</a>
    </nav>
  </header>
  <div class="~JobLayout">
    <aside class="~JobSidebar" aria-label="Job details">
      <dl class="~FactList">
        <div class="~Fact"><dt class="~FactTerm">Location</dt><dd class="~FactValue">Pittsburgh, PA &middot; Hybrid</dd></div>
        <div class="~Fact"><dt class="~FactTerm">Employment type</dt><dd class="~FactValue">Full time</dd></div>
        <div class="~Fact"><dt class="~FactTerm">Department</dt><dd class="~FactValue">Autonomy &amp; Embedded Systems</dd></div>
        <div class="~Fact"><dt class="~FactTerm">Compensation</dt><dd class="~FactValue">$165K &ndash; $205K &bull; Offers equity</dd></div>
      </dl>
      <section class="~AlertCard" aria-labelledby="alerts-title">
        <h2 id="alerts-title" class="~AlertTitle">Get notified about new roles</h2>
        <p class="~AlertText">One email a week with new openings in Embedded Systems.</p>
        <form class="~AlertForm" action="/api/job-alerts" method="post">
          <label class="~SrOnly" for="alert-email">Email</label>
          <input id="alert-email" class="~TextInput" type="email" name="email" placeholder="Email address" autocomplete="email">
          <button type="submit" class="~ButtonSecondary">Subscribe</button>
        </form>
      </section>
      <section class="~SimilarRoles" aria-labelledby="similar-title">
        <h2 id="similar-title" class="~SimilarTitle">Similar roles</h2>
        <ul class="~SimilarList">
{links(similar, ' class="~SimilarItem"', ' class="~SimilarLink"')}
        </ul>
      </section>
      <div class="~ShareRow">
        <span class="~ShareLabel">Share this job</span>
        <button type="button" class="~IconButton" aria-label="Copy link">{icon("external", size=16)}</button>
        <button type="button" class="~IconButton" aria-label="Share by email">{icon("mail", size=16)}</button>
      </div>
    </aside>
    <main class="~JobMain">
      <h1 class="~JobTitle">{title}</h1>
      <div class="~Tabs" role="tablist" aria-label="Job posting">
        <a class="~Tab" role="tab" aria-selected="false" href="/meridian/4718203">Overview</a>
        <a class="~TabActive" role="tab" aria-selected="true" href="/meridian/4718203/application">Application</a>
      </div>
      <form class="~ApplicationForm" action="/api/non-user-graphql?op=ApiSubmitSingleApplicationFormAction" method="post" enctype="multipart/form-data" novalidate>
        <input type="hidden" name="jobPostingId" value="8c1d2f4e-6b7a-4c3d-9e2f-1a0b5c6d7e8f">
        <div class="~FieldEntry">
          {upload("resume", "Resume", "Upload your resume and we'll autofill the rest of the form.", True, T("t1"))}
        </div>
        {entry(":R2kq:", "Name", '<input id=":R2kq:" class="~TextInput" type="text" name="name" autocomplete="name" value="Nadia Haddad" required>', True)}
        {entry(":R4kq:", "Email", '<input id=":R4kq:" class="~TextInput" type="email" name="email" autocomplete="email" value="nadia.haddad@hey.com" required' + T("t6") + '>', True)}
        {entry(":R6kq:", "Phone", '<input id=":R6kq:" class="~TextInput" type="tel" name="phone" autocomplete="tel" value="+1 412 555 0186">')}
        {entry(":R8kq:", "Current location", '<input id=":R8kq:" class="~TextInput" type="text" name="location" role="combobox" aria-autocomplete="list" aria-expanded="false" value="Pittsburgh, PA, USA">')}
        <fieldset class="~Group">
          <legend class="~GroupLegend">Links</legend>
          {entry(":Rakq:", "LinkedIn profile URL", '<input id=":Rakq:" class="~TextInput" type="url" name="urls[LinkedIn]" placeholder="https://www.linkedin.com/in/your-name" value="https://www.linkedin.com/in/nadiahaddad"' + T("t2") + '>')}
          {entry(":Rckq:", "GitHub URL", '<input id=":Rckq:" class="~TextInput" type="url" name="urls[GitHub]" placeholder="https://github.com/your-handle">')}
          {entry(":Rekq:", "Portfolio or personal site", '<input id=":Rekq:" class="~TextInput" type="url" name="urls[Portfolio]" value="https://nadiahaddad.dev">')}
        </fieldset>
        {entry(":Rgkq:", "Cover letter", '<textarea id=":Rgkq:" class="~TextArea" name="comments" rows="7" placeholder="Tell us why you are excited about Meridian, or paste a cover letter."' + T("t3") + '></textarea>', hint="Optional, but our hiring managers read every one.")}
        <div class="~FieldEntry">
          {upload("attachments", "Work samples", "Optional: design docs, schematics or code samples you are proud of.", False)}
        </div>
        {yes_no("workAuthorization", "Are you legally authorized to work in the United States?")}
        {yes_no("visaSponsorship", "Will you now or in the future require visa sponsorship?")}
        {yes_no("onsiteHybrid", "Can you work from our Pittsburgh office Tuesday to Thursday?")}
        {entry(":Rmkq:", "Earliest start date", '<input id=":Rmkq:" class="~TextInput" type="text" name="startDate" placeholder="e.g. 4 weeks after an offer">')}
        {entry(":Rokq:", "Pronouns", '<input id=":Rokq:" class="~TextInput" type="text" name="pronouns" placeholder="Optional">')}
        <div class="~FieldEntry">
          <label class="~FieldLabel" for=":Rikq:">How did you hear about us?</label>
          <div class="~InputShell"><select id=":Rikq:" class="~NativeSelect" name="source"><option value="">Select&hellip;</option>
{opts(sorted(hear))}
          </select></div>
        </div>
        <section class="~EeoSection" aria-labelledby="eeo-title">
          <h2 id="eeo-title" class="~EeoTitle">Voluntary self-identification</h2>
          <p class="~EeoText">Completing this section is optional and will not affect your application. Answers are stored separately from your application and are never shown to the hiring team.</p>
          {combo("gender", "Gender")}
          {combo("race", "Race")}
          {combo("disability", "Disability status")}
          {combo("veteran", "Veteran status", T("t4"))}
        </section>
        <div class="~SubmitRow">
          <button type="submit" class="~ButtonPrimary"{T("t5")}>Submit application</button>
          <p class="~FinePrint">By submitting, you agree to Meridian's <a href="https://meridianrobotics.com/privacy">candidate privacy notice</a>.</p>
        </div>
      </form>
      <div class="~ModalBackdrop" hidden>
        <div class="~Modal" role="dialog" aria-modal="true" aria-labelledby="review-title">
          <h2 id="review-title" class="~ModalTitle">Review your application</h2>
          <p class="~ModalText">You won't be able to edit your answers after you submit.</p>
          <div class="~ModalActions">
            <button type="button" class="~ButtonSecondary">Keep editing</button>
            <button type="button" class="~ButtonPrimary">Submit application</button>
          </div>
        </div>
      </div>
    </main>
  </div>
  <footer class="~BoardFooter">
    <p class="~BoardFooterText">Powered by Meridian Careers</p>
    <a class="~BoardFooterLink" href="https://meridianrobotics.com/privacy">Privacy policy</a>
    <a class="~BoardFooterLink" href="https://meridianrobotics.com/accessibility">Accessibility</a>
  </footer>
</div>
</div>
"""
    v2 = document(
        title=f"{title} @ Meridian Robotics",
        head="""<meta name="description" content="Apply to join the Autonomy &amp; Embedded Systems team at Meridian Robotics.">
<style data-emotion="css" data-s=""></style>""",
        body=expand_classes(v2_body, emotion("meridian")),
    )

    m = meta(
        "form-04",
        "Job application: résumé upload, links, cover letter and EEO questions — Meridian Robotics",
        ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change", "copy-change",
         "attribute-churn", "structure-move", "insertion", "tag-change"],
        "v1 is a classic hosted job board (job description + application form with Rails-style job_application[...] "
        "names, attach-or-paste résumé widget, native EEO selects, input[type=submit]). v2 moves to an applicant-"
        "tracking UI with emotion css-xxxxxxx classes and generated ids: the description sits on another tab, the "
        "résumé upload moves to the top inside an <ats-file-upload> declarative shadow root, links are grouped in a "
        "fieldset (urls[LinkedIn]), the cover letter becomes name=comments, the EEO selects become combobox buttons "
        "that all read 'Select…' (Race added, Disability now before Veteran) and the submit becomes a <button>. "
        "Decoys: a job-alert email form in the sidebar before the application, a second <ats-file-upload> for work "
        "samples and a hidden review dialog with another 'Submit application' button.",
        [
            target("t1", "Résumé/CV file input",
                   "#resume_file", "//input[@type='file' and @name='job_application[resume]']",
                   ["shadow-dom", "class-obfuscation", "id-change", "attribute-churn", "copy-change", "sibling-reorder",
                    "structure-move", "wrapper-divs", "decoy"]),
            target("t2", "LinkedIn profile URL input",
                   "#job_application_answers_attributes_0_text_value",
                   "//label[contains(., 'LinkedIn Profile')]/following-sibling::input[@type='text']",
                   ["class-obfuscation", "id-change", "attribute-churn", "copy-change", "wrapper-divs", "sibling-reorder"]),
            target("t3", "Cover letter textarea",
                   "textarea#cover_letter_text", "//textarea[@name='job_application[cover_letter_text]']",
                   ["class-obfuscation", "id-change", "attribute-churn", "wrapper-divs", "sibling-reorder"]),
            target("t4", "Veteran status EEO dropdown (native select in v1, combobox button in v2)",
                   "select#job_application_veteran_status", "//label[text()='Veteran Status']/following-sibling::select",
                   ["tag-change", "class-obfuscation", "id-change", "attribute-churn", "copy-change", "sibling-reorder",
                    "decoy"]),
            target("t5", "'Submit Application' button",
                   "#submit_app", "//input[@type='submit' and @value='Submit Application']",
                   ["tag-change", "copy-change", "id-change", "decoy", "class-obfuscation"]),
            target("t6", "Email input of the application form",
                   "#email", "//label[@for='email']/following-sibling::input",
                   ["class-obfuscation", "id-change", "attribute-churn", "wrapper-divs", "decoy"]),
        ],
    )
    return v1, v2, m


# ======================================================================================
# form-05 - Driftwood photo community: account preferences / settings
# ======================================================================================
@suite("form-05")
def form05():
    languages = [("en", "English (US)"), ("en-GB", "English (UK)"), ("de", "Deutsch"), ("es", "Español"), ("fr", "Français"),
                 ("it", "Italiano"), ("ja", "日本語"), ("ko", "한국어"), ("nl", "Nederlands"), ("pt-BR", "Português (Brasil)"),
                 ("sv", "Svenska"), ("zh-CN", "简体中文")]
    zones = [
        ("Pacific/Honolulu", "(GMT-10:00) Hawaii", "am"), ("America/Anchorage", "(GMT-09:00) Alaska", "am"),
        ("America/Los_Angeles", "(GMT-08:00) Pacific Time (US & Canada)", "am"), ("America/Phoenix", "(GMT-07:00) Arizona", "am"),
        ("America/Denver", "(GMT-07:00) Mountain Time (US & Canada)", "am"),
        ("America/Chicago", "(GMT-06:00) Central Time (US & Canada)", "am"), ("America/Mexico_City", "(GMT-06:00) Mexico City", "am"),
        ("America/New_York", "(GMT-05:00) Eastern Time (US & Canada)", "am"), ("America/Bogota", "(GMT-05:00) Bogota", "am"),
        ("America/Halifax", "(GMT-04:00) Atlantic Time (Canada)", "am"), ("America/Sao_Paulo", "(GMT-03:00) Brasilia", "am"),
        ("America/Argentina/Buenos_Aires", "(GMT-03:00) Buenos Aires", "am"), ("Atlantic/Azores", "(GMT-01:00) Azores", "eu"),
        ("Europe/London", "(GMT+00:00) London", "eu"), ("Europe/Lisbon", "(GMT+00:00) Lisbon", "eu"),
        ("Europe/Berlin", "(GMT+01:00) Berlin", "eu"), ("Europe/Paris", "(GMT+01:00) Paris", "eu"),
        ("Europe/Stockholm", "(GMT+01:00) Stockholm", "eu"), ("Africa/Lagos", "(GMT+01:00) West Central Africa", "eu"),
        ("Europe/Athens", "(GMT+02:00) Athens", "eu"), ("Africa/Cairo", "(GMT+02:00) Cairo", "eu"),
        ("Europe/Istanbul", "(GMT+03:00) Istanbul", "eu"), ("Africa/Nairobi", "(GMT+03:00) Nairobi", "eu"),
        ("Asia/Dubai", "(GMT+04:00) Abu Dhabi", "ap"), ("Asia/Karachi", "(GMT+05:00) Karachi", "ap"),
        ("Asia/Kolkata", "(GMT+05:30) Mumbai, New Delhi", "ap"), ("Asia/Bangkok", "(GMT+07:00) Bangkok", "ap"),
        ("Asia/Singapore", "(GMT+08:00) Singapore", "ap"), ("Asia/Shanghai", "(GMT+08:00) Beijing", "ap"),
        ("Asia/Tokyo", "(GMT+09:00) Tokyo", "ap"), ("Asia/Seoul", "(GMT+09:00) Seoul", "ap"),
        ("Australia/Sydney", "(GMT+10:00) Sydney", "ap"), ("Pacific/Auckland", "(GMT+12:00) Auckland", "ap"),
    ]
    notif = [  # key, label, description, email, push
        ("comments", "Comments on your photos", "When someone comments on a photo you posted.", True, True),
        ("followers", "New followers", "When someone starts following you.", False, True),
        ("mentions", "Mentions", "When someone @mentions you in a comment or caption.", True, True),
        ("favorites", "Favorites", "When someone adds one of your photos to their favorites.", False, False),
        ("featured", "Featured on Discover", "When one of your photos is picked by our curators.", True, True),
        ("digest", "Weekly digest", "Your stats plus the best new photos from people you follow.", True, False),
        ("news", "Product news & tips", "New features, photo challenges and the occasional offer.", False, False),
    ]
    settings_nav = [("Profile", "/settings/profile"), ("Password & security", "/settings/security"),
                    ("Preferences", "/settings/preferences"), ("Privacy", "/settings/privacy"),
                    ("Billing & plan", "/settings/billing"), ("Connected apps", "/settings/apps"),
                    ("Export data", "/settings/export")]
    footer_links = [("About", "/about"), ("Blog", "/blog"), ("Help", "/help"), ("Community guidelines", "/guidelines"),
                    ("Terms", "/terms"), ("Privacy", "/privacy"), ("API", "/developers")]
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    logo = ('<svg width="30" height="30" viewBox="0 0 30 30" aria-hidden="true"><circle cx="15" cy="15" r="14" fill="#7c3aed"/>'
            '<path d="M6 19c4-3 8-3 12 0s6 1 7-1" stroke="#fff" stroke-width="2" fill="none"/></svg>')
    token = "Wq7T2mKz9rVb4Xc1LpN8sYd3Hf6Jg0Ae5uOiBkRtMn"

    # ---------------------------------------------------------------- v1: server-rendered Rails views
    v1_css = """
  body { margin: 0; font: 14px/1.5 "Source Sans 3", system-ui, sans-serif; color: #1c1917; background: #fafaf9; }
  .app-header { background: #fff; border-bottom: 1px solid #e7e5e4; }
  .app-header__inner { display: flex; align-items: center; gap: 20px; max-width: 1200px; margin: 0 auto; padding: 10px 24px; }
  .settings-layout { display: grid; grid-template-columns: 220px 1fr; gap: 40px; max-width: 1200px; margin: 32px auto; padding: 0 24px; }
  .settings-nav__list { list-style: none; padding: 0; }
  .settings-nav__item--active .settings-nav__link { font-weight: 700; color: #7c3aed; }
  .settings-section { background: #fff; border: 1px solid #e7e5e4; border-radius: 8px; padding: 24px; margin-bottom: 24px; }
  .settings-section--danger { border-color: #fca5a5; }
  .notify-matrix { width: 100%; border-collapse: collapse; }
  .notify-matrix th, .notify-matrix td { padding: 10px 8px; border-bottom: 1px solid #f5f5f4; text-align: left; }
  .switch { position: relative; display: inline-block; width: 36px; height: 20px; }
  .switch__input { opacity: 0; width: 0; height: 0; }
  .switch__slider { position: absolute; inset: 0; background: #d6d3d1; border-radius: 20px; }
  .switch__input:checked + .switch__slider { background: #7c3aed; }
  .button { display: inline-block; border-radius: 6px; padding: 8px 14px; font-weight: 600; border: 1px solid transparent; }
  .button--primary { background: #7c3aed; color: #fff; }
  .button--danger { background: #dc2626; color: #fff; }
  .visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
"""

    def v1_switch(key: str, channel: str, on: bool, mark: str = "") -> str:
        name = f"notify[{key}][{channel}]"
        return (f'<td><input type="hidden" name="{name}" value="0">'
                f'<label class="switch"><input type="checkbox" class="switch__input" value="1" name="{name}" id="notify-{key}-{channel}"'
                f'{" checked" if on else ""}{mark}><span class="switch__slider" aria-hidden="true"></span>'
                f'<span class="visually-hidden">{channel.capitalize()}</span></label></td>')

    v1_rows = "\n".join(
        f'<tr class="notify-matrix__row"><th scope="row" class="notify-matrix__event">{esc(label)}<span class="notify-matrix__help">{esc(desc)}</span></th>'
        f'{v1_switch(key, "email", em)}{v1_switch(key, "push", pu, T("t1") if key == "mentions" else "")}</tr>'
        for key, label, desc, em, pu in notif)
    v1_nav = "\n".join(
        f'<li class="settings-nav__item{" settings-nav__item--active" if href.endswith("preferences") else ""}">'
        f'<a class="settings-nav__link" href="{href}"{" aria-current=" + chr(34) + "page" + chr(34) if href.endswith("preferences") else ""}'
        f'{T("t6") if href.endswith("billing") else ""}>{esc(text)}</a></li>'
        for text, href in settings_nav)
    v1_body = f"""
<header class="app-header">
  <div class="app-header__inner">
    <a class="app-header__logo" href="/">{logo}<span class="app-header__wordmark">Driftwood</span></a>
    <form class="app-search" action="/search" role="search">
      <label class="visually-hidden" for="q">Search photos</label>
      <input id="q" class="app-search__input" type="search" name="q" placeholder="Search photos, people or places">
    </form>
    <nav class="app-header__nav" aria-label="Primary">
      <a class="app-header__link" href="/discover">Discover</a>
      <a class="app-header__link" href="/following">Following</a>
      <a class="app-header__link" href="/groups">Groups</a>
    </nav>
    <a class="button button--primary button--small" href="/upload">Upload</a>
    <a class="app-header__icon" href="/notifications" aria-label="Notifications (3 unread)">{icon("bell", size=18)}<span class="app-header__badge">3</span></a>
    <details class="user-menu">
      <summary class="user-menu__toggle"><span class="avatar avatar--small">EM</span><span class="visually-hidden">Account menu</span></summary>
      <ul class="user-menu__list">
        <li><a href="/@elena.marsh">Your profile</a></li>
        <li><a href="/settings/profile">Settings</a></li>
        <li><a href="/logout" data-method="delete" rel="nofollow">Log out</a></li>
      </ul>
    </details>
  </div>
</header>
<div class="settings-layout">
  <aside class="settings-sidebar">
    <h2 class="settings-sidebar__title">Settings</h2>
    <nav class="settings-nav" aria-label="Settings">
      <ul class="settings-nav__list">
{v1_nav}
      </ul>
    </nav>
  </aside>
  <main class="settings-main">
    <div class="flash flash--notice" role="status">Your profile photo was updated.</div>
    <h1 class="settings-main__title">Preferences</h1>
    <form id="preferences-form" class="settings-form edit_user" action="/settings/preferences" method="post" accept-charset="UTF-8">
      <input type="hidden" name="_method" value="patch">
      <input type="hidden" name="authenticity_token" value="{token}">
      <section class="settings-section" id="notifications">
        <h2 class="settings-section__title">Notifications</h2>
        <p class="settings-section__description">Choose how you hear about activity on your photos.</p>
        <table class="notify-matrix">
          <thead><tr><th scope="col">Activity</th><th scope="col">Email</th><th scope="col">Push</th></tr></thead>
          <tbody>
{v1_rows}
          </tbody>
        </table>
        <div class="settings-field">
          <label class="settings-field__label" for="user_digest_day">Send my weekly digest on</label>
          <select id="user_digest_day" class="settings-field__select" name="user[digest_day]">
{opts([d.lower() for d in days], "sunday")}
          </select>
        </div>
      </section>
      <section class="settings-section" id="language-region">
        <h2 class="settings-section__title">Language &amp; region</h2>
        <div class="settings-field">
          <label class="settings-field__label" for="pref-language">Language</label>
          <select id="pref-language" class="settings-field__select" name="user[locale]"{T("t2")}>
{opts(languages, "en")}
          </select>
          <p class="settings-field__hint">Used for menus, emails and notifications.</p>
        </div>
        <div class="settings-field">
          <label class="settings-field__label" for="pref-timezone">Time zone</label>
          <select id="pref-timezone" class="settings-field__select timezone-select" name="user[time_zone]"{T("t3")}>
{opts([(v, lbl) for v, lbl, _ in zones], "America/Los_Angeles")}
          </select>
          <p class="settings-field__hint">Upload dates and digest emails use this time zone.</p>
        </div>
        <fieldset class="settings-field">
          <legend class="settings-field__label">Date format</legend>
          <label class="radio"><input type="radio" name="user[date_format]" value="us" checked> 11/05/2026</label>
          <label class="radio"><input type="radio" name="user[date_format]" value="eu"> 05/11/2026</label>
          <label class="radio"><input type="radio" name="user[date_format]" value="iso"> 2026-11-05</label>
        </fieldset>
        <div class="settings-field settings-field--checkbox">
          <input type="hidden" name="user[clock_24h]" value="0">
          <input type="checkbox" id="user_clock_24h" name="user[clock_24h]" value="1">
          <label for="user_clock_24h">Use 24-hour time</label>
        </div>
      </section>
      <div class="settings-actions">
        <button type="submit" class="button button--primary"{T("t5")}>Save preferences</button>
        <a class="button button--link" href="/settings/preferences">Cancel</a>
      </div>
    </form>
    <section class="settings-section settings-section--danger" id="danger-zone">
      <h2 class="settings-section__title">Danger zone</h2>
      <div class="danger-row">
        <div class="danger-row__text"><h3 class="danger-row__title">Export your photos</h3><p>Download a ZIP of every original you've uploaded (4.2 GB).</p></div>
        <a class="button button--secondary" href="/settings/export">Request export</a>
      </div>
      <div class="danger-row">
        <div class="danger-row__text"><h3 class="danger-row__title">Deactivate account</h3><p>Hide your profile and photos until you log in again.</p></div>
        <button type="button" class="button button--secondary" data-confirm="Deactivate your account?">Deactivate</button>
      </div>
      <div class="danger-row">
        <div class="danger-row__text"><h3 class="danger-row__title">Delete account</h3><p>Permanently delete your account, 1,284 photos and 37 albums. This cannot be undone.</p></div>
        <form class="button_to" action="/account" method="post">
          <input type="hidden" name="_method" value="delete">
          <input type="hidden" name="authenticity_token" value="{token}">
          <button type="submit" class="button button--danger" id="delete-account-btn" data-confirm="Are you sure? This permanently deletes your account."{T("t4")}>Delete account</button>
        </form>
      </div>
    </section>
  </main>
</div>
<footer class="app-footer">
  <ul class="app-footer__links">
{links(footer_links, ' class="app-footer__item"', ' class="app-footer__link"')}
  </ul>
  <p class="app-footer__copy">&copy; 2026 Driftwood Photo Co.</p>
</footer>
"""
    v1 = document(
        title="Preferences · Settings · Driftwood",
        head=f"""<meta name="csrf-param" content="authenticity_token">
<meta name="csrf-token" content="{token}">
<style>{v1_css}</style>""",
        body=v1_body,
    )

    # ---------------------------------------------------------------- v2: Next.js + Tailwind UI + Headless UI
    sel_cls = ("col-start-1 row-start-1 w-full appearance-none rounded-md bg-white py-1.5 pl-3 pr-8 text-base text-gray-900 "
               "outline outline-1 -outline-offset-1 outline-gray-300 focus:outline-2 focus:-outline-offset-2 "
               "focus:outline-indigo-600 sm:text-sm/6")
    chev = ('<svg class="pointer-events-none col-start-1 row-start-1 mr-2 size-5 self-center justify-self-end text-gray-500 '
            'sm:size-4" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" '
            'd="M4.22 6.22a.75.75 0 0 1 1.06 0L8 8.94l2.72-2.72a.75.75 0 1 1 1.06 1.06l-3.25 3.25a.75.75 0 0 1-1.06 0L4.22 7.28a.75.75 0 0 1 0-1.06Z"/></svg>')

    sw_n = iter(range(20, 80))

    def switch(key: str, channel: str, on: bool, mark: str = "") -> str:
        bg = "bg-indigo-600" if on else "bg-gray-200"
        knob = "translate-x-5" if on else "translate-x-0"
        return (f'<button type="button" id="headlessui-switch-:r{next(sw_n):x}:" role="switch" aria-checked="{"true" if on else "false"}" '
                f'aria-labelledby="notif-{key}-label notif-{key}-{channel}" '
                f'class="group relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent {bg} '
                f'transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:ring-offset-2"{mark}>'
                f'<span class="sr-only" id="notif-{key}-{channel}">{channel.capitalize()}</span>'
                f'<span aria-hidden="true" class="pointer-events-none inline-block size-5 {knob} transform rounded-full bg-white shadow '
                f'ring-0 transition duration-200 ease-in-out"></span></button>')

    order = ["mentions", "comments", "featured", "followers", "favorites", "digest", "news"]
    by_key = {n[0]: n for n in notif}
    in_app = {"mentions": True, "comments": True, "featured": True, "followers": True, "favorites": True, "digest": False, "news": False}
    v2_rows = "\n".join(
        f'''<li class="flex items-center justify-between gap-x-6 py-5">
  <div class="min-w-0"><p class="text-sm/6 font-semibold text-gray-900" id="notif-{k}-label">{esc(by_key[k][1])}</p><p class="mt-1 text-xs/5 text-gray-500">{esc(by_key[k][2])}</p></div>
  <div class="flex shrink-0 items-center gap-x-8">
    {switch(k, "push", by_key[k][4], T("t1") if k == "mentions" else "")}
    {switch(k, "email", by_key[k][3])}
    {switch(k, "in-app", in_app[k])}
  </div>
</li>''' for k in order)
    groups = [("Americas", "am"), ("Europe & Africa", "eu"), ("Asia & Pacific", "ap")]
    tz_opts = "\n".join(
        f'<optgroup label="{esc(g)}">\n' + opts([(v, lbl) for v, lbl, r in zones if r == code], "America/Los_Angeles") + "\n</optgroup>"
        for g, code in groups)
    sec_nav = [("Profile", "/settings/profile"), ("Preferences", "/settings/preferences"), ("Security", "/settings/security"),
               ("Plans & billing", "/settings/billing"), ("Privacy", "/settings/privacy"), ("Integrations", "/settings/integrations"),
               ("Export", "/settings/export")]
    v2_secnav = "\n".join(
        f'<li><a href="{href}" class="{"text-indigo-600" if href.endswith("preferences") else "hover:text-gray-900"}"'
        f'{" aria-current=" + chr(34) + "page" + chr(34) if href.endswith("preferences") else ""}{T("t6") if href.endswith("billing") else ""}>{esc(t)}</a></li>'
        for t, href in sec_nav)
    app_nav = [("Home", "/home", "home"), ("Discover", "/discover", "globe"), ("Following", "/following", "heart"),
               ("Groups", "/groups", "user"), ("Your uploads", "/uploads", "upload"), ("Stats", "/stats", "sliders")]
    v2_appnav = "\n".join(
        f'<li><a href="{href}" class="group flex gap-x-3 rounded-md p-2 text-sm/6 font-semibold text-gray-400 hover:bg-gray-800 '
        f'hover:text-white">{icon(ic, "size-6 shrink-0")}{t}</a></li>' for t, href, ic in app_nav)
    danger_css = (":host{display:block}.zone{border:1px solid #fecaca;border-radius:12px;background:#fff}"
                  ".row{display:flex;align-items:center;justify-content:space-between;gap:24px;padding:16px 20px;"
                  "border-top:1px solid #fee2e2}.row:first-child{border-top:0}.title{margin:0;font:600 14px/1.5 system-ui;color:#111827}"
                  ".desc{margin:2px 0 0;font:13px/1.5 system-ui;color:#6b7280}.btn{border-radius:6px;padding:8px 12px;"
                  "font:600 13px system-ui;cursor:pointer;white-space:nowrap}.secondary{background:#fff;border:1px solid #d1d5db;"
                  "color:#111827}.danger{background:#dc2626;border:0;color:#fff}")
    v2_body = f"""
<div id="headlessui-portal-root">
  <div id="headlessui-dialog-:r1n:" role="dialog" aria-modal="true" aria-labelledby="delete-dialog-title" class="relative z-50" hidden>
    <div class="fixed inset-0 bg-gray-500/75 transition-opacity" aria-hidden="true"></div>
    <div class="fixed inset-0 z-10 w-screen overflow-y-auto">
      <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
        <div class="relative transform overflow-hidden rounded-lg bg-white px-4 pb-4 pt-5 text-left shadow-xl sm:my-8 sm:w-full sm:max-w-lg sm:p-6">
          <div class="sm:flex sm:items-start">
            <div class="mx-auto flex size-12 shrink-0 items-center justify-center rounded-full bg-red-100 sm:mx-0 sm:size-10">{icon("alert", "size-6 text-red-600")}</div>
            <div class="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left">
              <h3 id="delete-dialog-title" class="text-base font-semibold text-gray-900">Delete your Driftwood account?</h3>
              <div class="mt-2"><p class="text-sm text-gray-500">All 1,284 photos and 37 albums will be permanently removed. This action cannot be undone.</p></div>
            </div>
          </div>
          <div class="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse">
            <button type="button" class="inline-flex w-full justify-center rounded-md bg-red-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-red-500 sm:ml-3 sm:w-auto">Delete account</button>
            <button type="button" class="mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 sm:mt-0 sm:w-auto">Cancel</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
<div id="__next">
  <div class="relative z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation" hidden>
    <div class="fixed inset-0 bg-gray-900/80" aria-hidden="true"></div>
    <div class="fixed inset-0 flex">
      <div class="relative mr-16 flex w-full max-w-xs flex-1">
        <div class="flex grow flex-col gap-y-5 overflow-y-auto bg-gray-900 px-6 pb-2">
          <div class="flex h-16 shrink-0 items-center">{logo}</div>
          <nav class="flex flex-1 flex-col" aria-label="Mobile"><ul role="list" class="-mx-2 space-y-1">
{v2_appnav}
          </ul></nav>
        </div>
      </div>
    </div>
  </div>
  <div class="hidden lg:fixed lg:inset-y-0 lg:z-50 lg:flex lg:w-72 lg:flex-col">
    <div class="flex grow flex-col gap-y-5 overflow-y-auto bg-gray-900 px-6">
      <div class="flex h-16 shrink-0 items-center gap-x-3">{logo}<span class="text-sm font-semibold text-white">Driftwood</span></div>
      <nav class="flex flex-1 flex-col" aria-label="App"><ul role="list" class="-mx-2 space-y-1">
{v2_appnav}
      </ul></nav>
    </div>
  </div>
  <div class="lg:pl-72">
    <div class="sticky top-0 z-40 flex h-16 shrink-0 items-center gap-x-6 border-b border-gray-200 bg-white px-4 shadow-sm sm:px-6 lg:px-8">
      <button type="button" class="-m-2.5 p-2.5 text-gray-700 lg:hidden"><span class="sr-only">Open sidebar</span>{icon("menu", "size-5")}</button>
      <form class="grid flex-1 grid-cols-1" action="/search" method="get">
        <input type="search" name="q" aria-label="Search" class="col-start-1 row-start-1 block size-full bg-white pl-8 text-base text-gray-900 outline-none placeholder:text-gray-400 sm:text-sm/6" placeholder="Search photos, people, places">
        {icon("search", "pointer-events-none col-start-1 row-start-1 size-5 self-center text-gray-400")}
      </form>
      <a href="/notifications" class="-m-2.5 p-2.5 text-gray-400 hover:text-gray-500"><span class="sr-only">View notifications</span>{icon("bell", "size-6")}</a>
      <div class="relative">
        <button type="button" class="-m-1.5 flex items-center p-1.5" id="user-menu-button" aria-expanded="false" aria-haspopup="true"><span class="sr-only">Open user menu</span><span class="inline-flex size-8 items-center justify-center rounded-full bg-violet-100 text-xs font-medium text-violet-700">EM</span></button>
        <div class="absolute right-0 z-10 mt-2.5 w-40 origin-top-right rounded-md bg-white py-2 shadow-lg ring-1 ring-gray-900/5" role="menu" aria-labelledby="user-menu-button" hidden>
          <a href="/@elena.marsh" class="block px-3 py-1 text-sm/6 text-gray-900" role="menuitem">Your profile</a>
          <a href="/settings/billing" class="block px-3 py-1 text-sm/6 text-gray-900" role="menuitem">Plans &amp; billing</a>
          <a href="/logout" class="block px-3 py-1 text-sm/6 text-gray-900" role="menuitem">Sign out</a>
        </div>
      </div>
    </div>
    <main>
      <h1 class="sr-only">Account settings</h1>
      <header class="border-b border-gray-200">
        <nav class="flex overflow-x-auto py-4" aria-label="Account settings">
          <ul role="list" class="flex min-w-full flex-none gap-x-6 px-4 text-sm/6 font-semibold text-gray-500 sm:px-6 lg:px-8">
{v2_secnav}
          </ul>
        </nav>
      </header>
      <div class="rounded-md bg-green-50 p-4 mx-4 mt-6 sm:mx-6 lg:mx-8" role="status"><p class="text-sm font-medium text-green-800">Profile photo updated.</p></div>
      <form id="preferences" class="divide-y divide-gray-200" action="/api/settings/preferences" method="post">
        <div class="grid max-w-7xl grid-cols-1 gap-x-8 gap-y-10 px-4 py-16 sm:px-6 md:grid-cols-3 lg:px-8">
          <div>
            <h2 class="text-base/7 font-semibold text-gray-900">Language &amp; region</h2>
            <p class="mt-1 text-sm/6 text-gray-500">Pick the language for menus and emails, and the time zone used for upload dates.</p>
          </div>
          <div class="grid grid-cols-1 gap-x-6 gap-y-8 sm:max-w-xl sm:grid-cols-6 md:col-span-2">
            <div class="sm:col-span-3">
              <label for="locale" class="block text-sm/6 font-medium text-gray-900">Display language</label>
              <div class="mt-2 grid grid-cols-1">
                <select id="locale" name="locale" autocomplete="language" class="{sel_cls}"{T("t2")}>
{opts(languages, "en")}
                </select>
                {chev}
              </div>
            </div>
            <div class="sm:col-span-3">
              <label for="timezone" class="block text-sm/6 font-medium text-gray-900">Time zone</label>
              <div class="mt-2 grid grid-cols-1">
                <select id="timezone" name="user[time_zone]" class="{sel_cls}"{T("t3")}>
{tz_opts}
                </select>
                {chev}
              </div>
            </div>
            <fieldset class="sm:col-span-6">
              <legend class="text-sm/6 font-semibold text-gray-900">Date format</legend>
              <div class="mt-3 flex gap-x-6">
                <label class="flex items-center gap-x-2 text-sm/6 text-gray-900"><input type="radio" name="dateFormat" value="iso" class="size-4 border-gray-300 text-indigo-600"> 2026-11-05</label>
                <label class="flex items-center gap-x-2 text-sm/6 text-gray-900"><input type="radio" name="dateFormat" value="us" checked class="size-4 border-gray-300 text-indigo-600"> Nov 5, 2026</label>
                <label class="flex items-center gap-x-2 text-sm/6 text-gray-900"><input type="radio" name="dateFormat" value="eu" class="size-4 border-gray-300 text-indigo-600"> 5 Nov 2026</label>
              </div>
            </fieldset>
          </div>
        </div>
        <div class="grid max-w-7xl grid-cols-1 gap-x-8 gap-y-10 px-4 py-16 sm:px-6 md:grid-cols-3 lg:px-8">
          <div>
            <h2 class="text-base/7 font-semibold text-gray-900">Notifications</h2>
            <p class="mt-1 text-sm/6 text-gray-500">We'll always email you about security and billing. Choose what else you want to hear about.</p>
          </div>
          <div class="md:col-span-2">
            <div class="flex justify-end gap-x-8 pr-1 text-xs font-medium uppercase tracking-wide text-gray-500" aria-hidden="true"><span>Push</span><span>Email</span><span>In-app</span></div>
            <ul role="list" class="divide-y divide-gray-100">
{v2_rows}
            </ul>
            <div class="mt-6 sm:max-w-xs">
              <label for="digestDay" class="block text-sm/6 font-medium text-gray-900">Weekly digest day</label>
              <div class="mt-2 grid grid-cols-1">
                <select id="digestDay" name="digestDay" class="{sel_cls}">
{opts([d.lower() for d in days], "sunday")}
                </select>
                {chev}
              </div>
            </div>
            <div class="mt-8 flex items-center justify-end gap-x-6">
              <a href="/settings/preferences" class="text-sm/6 font-semibold text-gray-900">Cancel</a>
              <button type="submit" class="rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"{T("t5")}>Save changes</button>
            </div>
          </div>
        </div>
      </form>
      <div class="grid max-w-7xl grid-cols-1 gap-x-8 gap-y-10 border-t border-gray-200 px-4 py-16 sm:px-6 md:grid-cols-3 lg:px-8">
        <div>
          <h2 class="text-base/7 font-semibold text-gray-900">Delete account</h2>
          <p class="mt-1 text-sm/6 text-gray-500">No longer want to use Driftwood? Export your originals first: deleting is permanent.</p>
        </div>
        <dw-danger-zone class="md:col-span-2" account="elena.marsh">
          <template shadowrootmode="open">
            <style>{danger_css}</style>
            <div class="zone" part="zone">
              <div class="row"><div><p class="title">Export your photos</p><p class="desc">A ZIP of every original you've uploaded (4.2 GB).</p></div><a class="btn secondary" href="/settings/export">Request export</a></div>
              <div class="row"><div><p class="title">Deactivate account</p><p class="desc">Hide your profile and photos until you log in again.</p></div><button type="button" class="btn secondary">Deactivate</button></div>
              <div class="row"><div><p class="title">Delete account</p><p class="desc">Permanently delete your account, 1,284 photos and 37 albums.</p></div><button type="button" class="btn danger" aria-haspopup="dialog" aria-controls="headlessui-dialog-:r1n:"{T("t4")}>Delete account</button></div>
            </div>
          </template>
        </dw-danger-zone>
      </div>
    </main>
    <footer class="border-t border-gray-200 px-4 py-8 sm:px-6 lg:px-8">
      <ul role="list" class="flex flex-wrap gap-x-6 gap-y-2 text-sm/6 text-gray-500">
{links(footer_links[::-1], "", ' class="hover:text-gray-900"')}
      </ul>
      <p class="mt-4 text-xs/5 text-gray-400">&copy; 2026 Driftwood Photo Co. All rights reserved.</p>
    </footer>
  </div>
  <div class="pointer-events-none fixed inset-x-0 bottom-0 z-40 px-6 pb-6" role="region" aria-label="Unsaved changes">
    <div class="pointer-events-auto ml-auto flex max-w-xl items-center justify-between gap-x-6 rounded-xl bg-gray-900 px-6 py-3 shadow-lg">
      <p class="text-sm/6 text-white">You have unsaved changes</p>
      <div class="flex gap-x-3">
        <button type="reset" form="preferences" class="rounded-md px-3 py-1.5 text-sm font-semibold text-white hover:bg-white/10">Discard</button>
        <button type="submit" form="preferences" class="rounded-md bg-indigo-500 px-3 py-1.5 text-sm font-semibold text-white hover:bg-indigo-400">Save changes</button>
      </div>
    </div>
  </div>
</div>
"""
    v2 = document(
        title="Preferences | Driftwood",
        head="""<meta name="description" content="Manage your Driftwood notification, language and account settings.">
<style>*,::before,::after{box-sizing:border-box;border:0 solid #e5e7eb}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border-width:0}</style>""",
        body=v2_body,
        html_attrs=' class="h-full bg-white"',
        body_attrs=' class="h-full"',
    )

    m = meta(
        "form-05",
        "Account preferences: notification toggles, language & time zone, danger zone — Driftwood",
        ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change", "copy-change",
         "attribute-churn", "structure-move", "insertion", "tag-change"],
        "v1 is a server-rendered settings page (semantic BEM-ish classes, Rails check_box hidden inputs, a notification "
        "table with Email/Push columns, a 'Danger zone' section). v2 is a Tailwind UI rewrite: the settings sidebar "
        "becomes a horizontal secondary nav (reordered, 'Billing & plan' -> 'Plans & billing'), 'Language & region' "
        "now comes before 'Notifications', the notification table becomes a list of Headless UI role=switch buttons "
        "with rows reordered and columns Push/Email/In-app, the time-zone select gains optgroups, and the danger zone "
        "moves into a <dw-danger-zone> declarative shadow root. Decoys: a portal-rendered confirmation dialog with its "
        "own 'Delete account' button placed before the app root, a user menu with another 'Plans & billing' link, a "
        "'Push' switch on every row and a sticky 'You have unsaved changes' bar with a second 'Save changes' button.",
        [
            target("t1", "Push-notification toggle of the 'Mentions' row",
                   "table.notify-matrix tbody tr:nth-child(3) td:nth-child(3) input[type='checkbox']",
                   "//input[@type='checkbox' and @name='notify[mentions][push]']",
                   ["tag-change", "class-obfuscation", "sibling-reorder", "id-change", "attribute-churn", "decoy",
                    "insertion"]),
            target("t2", "Language select",
                   "#pref-language", "//select[@name='user[locale]']",
                   ["class-obfuscation", "id-change", "attribute-churn", "copy-change", "wrapper-divs", "sibling-reorder"]),
            target("t3", "Time zone select",
                   "select.timezone-select", "//select[@name='user[time_zone]']",
                   ["class-obfuscation", "id-change", "wrapper-divs", "structure-move"]),
            target("t4", "'Delete account' button in the danger zone",
                   "#danger-zone .button--danger", "//section[@id='danger-zone']//button[normalize-space()='Delete account']",
                   ["shadow-dom", "class-obfuscation", "id-change", "attribute-churn", "structure-move", "decoy"]),
            target("t5", "'Save preferences' submit button of the preferences form",
                   ".settings-actions .button--primary", "//button[text()='Save preferences']",
                   ["class-obfuscation", "copy-change", "structure-move", "decoy"]),
            target("t6", "'Billing & plan' link in the settings navigation",
                   ".settings-nav__item:nth-child(5) a",
                   "//nav[@aria-label='Settings']//a[normalize-space()='Billing & plan']",
                   ["class-obfuscation", "copy-change", "sibling-reorder", "structure-move", "attribute-churn", "decoy"]),
        ],
    )
    return v1, v2, m


# ======================================================================================
# form-06 - Voltaic Home (home batteries): contact / support request
# ======================================================================================
@suite("form-06")
def form06():
    topics = [("billing", "Billing & payments"), ("installation", "Installation & scheduling"),
              ("performance", "Battery performance"), ("app", "App & connectivity"), ("warranty", "Warranty claim"),
              ("other", "Something else")]
    articles = [("Recovering after a power outage", "/articles/360021"),
                ("Why isn't my battery charging to 100%?", "/articles/360033"),
                ("Reconnecting the gateway to Wi-Fi", "/articles/360009"),
                ("Understanding your warranty", "/articles/360041"),
                ("Updating firmware from the app", "/articles/360052")]
    nav = [("Batteries", "https://voltaichome.com/batteries"), ("Solar", "https://voltaichome.com/solar"),
           ("Voltaic app", "https://voltaichome.com/app"), ("Installers", "https://voltaichome.com/installers")]
    cols = [
        ("Products", [("Home Battery 2", "https://voltaichome.com/battery-2"), ("Solar roof tiles", "https://voltaichome.com/solar"),
                      ("Gateway", "https://voltaichome.com/gateway"), ("EV charger", "https://voltaichome.com/ev")]),
        ("Support", [("Help center", "/"), ("Warranty", "/warranty"), ("Recalls", "/recalls"), ("System status", "https://status.voltaichome.com")]),
        ("Company", [("About", "https://voltaichome.com/about"), ("Careers", "https://voltaichome.com/careers"),
                     ("Newsroom", "https://voltaichome.com/news")]),
        ("Legal", [("Privacy", "https://voltaichome.com/privacy"), ("Terms", "https://voltaichome.com/terms"),
                   ("Accessibility", "https://voltaichome.com/accessibility")]),
    ]
    tiles = [("Billing & payments", "Invoices, financing and refunds", "/categories/billing", "file"),
             ("Installation", "Scheduling, permits and site visits", "/categories/installation", "home"),
             ("Battery & backup", "Charging, backup reserve, status lights", "/categories/battery", "shield"),
             ("Voltaic app", "Pairing, notifications and energy reports", "/categories/app", "wifi"),
             ("Warranty & repairs", "Coverage, claims and replacements", "/categories/warranty", "check"),
             ("Moving home", "Transferring ownership of a system", "/categories/moving", "pin")]
    bolt = ('<svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true"><rect width="28" height="28" rx="6" fill="#facc15"/>'
            '<path d="m15 4-8 12h6l-2 8 8-12h-6z" fill="#1f2937"/></svg>')
    token = "Zt5q1Kd8xP0aW3mRb7Lc9VnE2hJs6UgY4oFiTe"

    # ---------------------------------------------------------------- v1: Foundation 6
    v1_css = """
  body { font-family: "Work Sans", Helvetica, Arial, sans-serif; color: #1f2937; }
  .support-hero { background: #111827; color: #f9fafb; padding: 48px 0; text-align: center; }
  .contact-form label { font-weight: 600; }
  .form-error.is-visible { display: block; color: #b91c1c; }
  .is-invalid-input { border-color: #b91c1c; background: #fef2f2; }
  .priority-field label { display: inline-block; margin-right: 1rem; font-weight: 400; }
  .article-list li { padding: .35rem 0; border-bottom: 1px solid #f3f4f6; }
  .footer { background: #f9fafb; margin-top: 4rem; padding: 3rem 0 2rem; font-size: .875rem; }
"""
    v1_body = f"""
<div class="top-bar-container">
  <div class="top-bar" id="main-menu">
    <div class="top-bar-left">
      <ul class="dropdown menu" data-dropdown-menu>
        <li class="menu-text"><a class="logo" href="https://voltaichome.com">{bolt} Voltaic Home</a></li>
{links(nav)}
        <li class="is-active"><a href="/">Support</a></li>
      </ul>
    </div>
    <div class="top-bar-right">
      <form class="menu search-menu" action="/search" role="search">
        <input type="search" name="query" placeholder="Search help articles" aria-label="Search help articles">
        <button type="submit" class="button">Search</button>
      </form>
      <ul class="menu"><li><a href="/my-requests">My requests</a></li></ul>
    </div>
  </div>
</div>
<div class="hero-section support-hero">
  <div class="hero-section-text">
    <h1>How can we help?</h1>
    <p>Our support team usually replies within 4 business hours.</p>
  </div>
</div>
<div class="grid-container">
  <section class="topic-tiles" aria-labelledby="browse-title">
    <h2 id="browse-title" class="show-for-sr">Browse by topic</h2>
    <div class="grid-x grid-margin-x small-up-2 medium-up-3">
{chr(10).join(f'      <div class="cell"><a class="card topic-tile" href="{u}"><div class="card-section">{icon(ic, "topic-tile__icon", 22)}<h3 class="topic-tile__title">{esc(t)}</h3><p class="topic-tile__text">{d}</p></div></a></div>' for t, d, u, ic in tiles)}
    </div>
  </section>
  <nav aria-label="You are here:" role="navigation">
    <ul class="breadcrumbs">
      <li><a href="/">Support</a></li>
      <li><a href="/contact">Contact us</a></li>
      <li><span class="show-for-sr">Current: </span>Submit a request</li>
    </ul>
  </nav>
  <div class="grid-x grid-margin-x">
    <main class="cell medium-8">
      <h2>Submit a request</h2>
      <div class="callout warning" data-closable>
        <h5>Storm season notice</h5>
        <p>If your Home Battery shows a red status light after an outage, see <a href="/articles/360021">Recovering after a power outage</a> before you submit a request.</p>
        <button class="close-button" aria-label="Dismiss alert" type="button" data-close><span aria-hidden="true">&times;</span></button>
      </div>
      <form id="new_ticket" class="contact-form" action="/requests" method="post" enctype="multipart/form-data" data-abide novalidate>
        <input type="hidden" name="utf8" value="&#x2713;">
        <input type="hidden" name="authenticity_token" value="{token}">
        <div class="grid-x grid-padding-x">
          <div class="cell medium-6">
            <label for="ticket-name">Your name
              <input type="text" id="ticket-name" name="ticket[requester_name]" autocomplete="name" value="Hiroshi Tanaka" required>
            </label>
          </div>
          <div class="cell medium-6">
            <label for="ticket-email">Email address
              <input type="email" id="ticket-email" name="ticket[requester_email]" autocomplete="email" value="h.tanaka@sonicmail.net" required>
            </label>
          </div>
          <div class="cell medium-6">
            <label for="support-topic">What can we help with?
              <select id="support-topic" name="ticket[topic]" required{T("t1")}>
                <option value="">Choose a topic&hellip;</option>
{opts(topics, "performance")}
              </select>
            </label>
          </div>
          <div class="cell medium-6">
            <label for="order-number">Order number
              <input type="text" id="order-number" name="ticket[order_number]" placeholder="e.g. VH-104233" pattern="^VH-[0-9]{{6}}$" value="VH-10423" class="is-invalid-input" aria-invalid="true" aria-describedby="order-number-error order-number-help"{T("t2")}>
            </label>
            <span class="form-error is-visible" id="order-number-error">Order numbers start with VH- followed by 6 digits.</span>
            <p class="help-text" id="order-number-help"><a class="order-help-link" href="/articles/360014"{T("t5")}>Where do I find my order number?</a></p>
          </div>
          <div class="cell">
            <label for="ticket-subject">Subject
              <input type="text" id="ticket-subject" name="ticket[subject]" value="Battery stuck at 20% since the October firmware update">
            </label>
          </div>
          <div class="cell message-field">
            <label for="ticket-description">Describe the issue
              <textarea id="ticket-description" name="ticket[description]" rows="7" placeholder="What happened, when it started, and what you've tried so far" required{T("t3")}></textarea>
            </label>
            <p class="help-text">Please don't include passwords or full card numbers.</p>
          </div>
          <div class="cell">
            <label class="attachments-label" for="ticket-attachments">Attachments <span class="optional">(optional)</span></label>
            <input type="file" id="ticket-attachments" name="ticket[attachments][]" multiple accept="image/*,.pdf,.log,.txt" class="show-for-sr">
            <label for="ticket-attachments" class="button hollow small">{icon("clip", size=14)} Add files</label>
            <p class="help-text">Up to 5 files, 20 MB each. A photo of the battery's status light helps a lot.</p>
          </div>
          <fieldset class="cell priority-field">
            <legend>How urgent is this?</legend>
            <input type="radio" name="ticket[priority]" value="low" id="priority-low"><label for="priority-low">Low &ndash; general question</label>
            <input type="radio" name="ticket[priority]" value="normal" id="priority-normal" checked><label for="priority-normal">Normal &ndash; something isn't working right</label>
            <input type="radio" name="ticket[priority]" value="urgent" id="priority-urgent"{T("t4")}><label for="priority-urgent">Urgent &ndash; no power or a safety concern</label>
          </fieldset>
          <div class="cell">
            <input type="checkbox" id="ticket-copy" name="ticket[cc_me]" value="1" checked><label for="ticket-copy">Email me a copy of this request</label>
          </div>
          <div class="cell">
            <button type="submit" class="button expanded"{T("t6")}>Send request</button>
          </div>
        </div>
      </form>
    </main>
    <aside class="cell medium-4">
      <div class="card">
        <div class="card-divider"><h3>Before you contact us</h3></div>
        <div class="card-section">
          <ul class="no-bullet article-list">
{links(articles)}
          </ul>
        </div>
      </div>
      <div class="card">
        <div class="card-divider"><h3>Talk to a person</h3></div>
        <div class="card-section">
          <p><strong>1-888-555-0136</strong><br>Mon&ndash;Fri 7 am&ndash;7 pm PT, Sat 8 am&ndash;4 pm PT</p>
          <p class="system-status"><span class="badge success" aria-hidden="true">&#9679;</span> All systems operational</p>
        </div>
      </div>
    </aside>
  </div>
</div>
<footer class="footer">
  <div class="grid-container">
    <div class="grid-x grid-margin-x">
{columns(cols, '''      <div class="cell small-6 medium-3">
        <h4 class="footer-heading">{title}</h4>
        <ul class="menu vertical">
{links}
        </ul>
      </div>''')}
    </div>
    <p class="copyright">&copy; 2026 Voltaic Home Energy, Inc. &middot; 1200 Folsom St, Sacramento, CA</p>
  </div>
</footer>
"""
    v1 = document(
        title="Submit a request – Voltaic Home Support",
        head=f"""<meta name="description" content="Contact Voltaic Home support about your battery, solar or app.">
<style>{v1_css}</style>""",
        body=v1_body,
        html_attrs=' class="no-js"',
    )

    # ---------------------------------------------------------------- v2: React + MUI v5
    def lbl(fid: str, text: str, required: bool, error: bool = False, shrink: bool = True) -> str:
        cls = ("MuiFormLabel-root MuiInputLabel-root MuiInputLabel-formControl MuiInputLabel-animated"
               + (" MuiInputLabel-shrink" if shrink else "") + " MuiInputLabel-sizeMedium MuiInputLabel-outlined MuiFormLabel-colorPrimary"
               + (" Mui-error" if error else "") + (" Mui-required" if required else "") + " ~inputLabel")
        star = '<span aria-hidden="true" class="MuiFormLabel-asterisk MuiInputLabel-asterisk ~asterisk"> *</span>' if required else ""
        return f'<label class="{cls}" data-shrink="{str(shrink).lower()}" for="{fid}" id="{fid}-label">{text}{star}</label>'

    def notched(text: str, required: bool) -> str:
        return (f'<fieldset aria-hidden="true" class="MuiOutlinedInput-notchedOutline ~notched"><legend class="~legend">'
                f'<span>{text}{" *" if required else ""}</span></legend></fieldset>')

    def text_field(fid: str, name: str, label: str, value: str = "", placeholder: str = "", required: bool = False,
                   error: bool = False, helper: str = "", itype: str = "text", mark: str = "", extra_helper: str = "",
                   multiline: bool = False, rows: int = 6) -> str:
        err = " Mui-error" if error else ""
        desc = f' aria-describedby="{fid}-helper-text"' if helper else ""
        val = f' value="{esc(value)}"' if value else ""
        ph = f' placeholder="{esc(placeholder)}"' if placeholder else ""
        if multiline:
            control = (f'<textarea aria-invalid="false" id="{fid}" name="{name}" rows="{rows}"{ph}{desc} '
                       f'class="MuiInputBase-input MuiOutlinedInput-input MuiInputBase-inputMultiline ~inputMultiline"{" required" if required else ""}{mark}></textarea>'
                       f'<textarea aria-hidden="true" class="MuiInputBase-input MuiOutlinedInput-input MuiInputBase-inputMultiline ~inputMultiline" '
                       f'readonly tabindex="-1" style="visibility:hidden;position:absolute;overflow:hidden;height:0;top:0;left:0;'
                       f'transform:translateZ(0);padding:0;width:100%"></textarea>')
        else:
            control = (f'<input aria-invalid="{str(error).lower()}" id="{fid}" name="{name}" type="{itype}"{ph}{val}{desc} '
                       f'class="MuiInputBase-input MuiOutlinedInput-input ~input"{" required" if required else ""}{mark}>')
        helper_html = ""
        if helper:
            helper_html = (f'<p class="MuiFormHelperText-root{err} MuiFormHelperText-sizeMedium MuiFormHelperText-contained'
                           f'{" Mui-required" if required else ""} ~helperText" id="{fid}-helper-text">{helper}</p>')
        root = "MuiInputBase-root MuiOutlinedInput-root MuiInputBase-colorPrimary" + err + " MuiInputBase-fullWidth MuiInputBase-formControl" + (
            " MuiInputBase-multiline" if multiline else "") + " ~inputRoot"
        return (f'<div class="MuiFormControl-root MuiFormControl-fullWidth MuiTextField-root ~textField">'
                f'{lbl(fid, label, required, error, bool(value or placeholder))}<div class="{root}">{control}{notched(label, required)}</div>'
                f'{helper_html}{extra_helper}</div>')

    def select_field(key: str, name: str, label: str, value: str, display: str, required: bool, mark: str = "") -> str:
        return (f'<div class="MuiFormControl-root MuiFormControl-fullWidth ~formControl">'
                f'{lbl(key + "-select", label, required)}'
                f'<div class="MuiInputBase-root MuiOutlinedInput-root MuiInputBase-colorPrimary MuiInputBase-fullWidth MuiInputBase-formControl ~inputRoot">'
                f'<div tabindex="0" role="combobox" aria-controls=":{key}-listbox:" aria-expanded="false" aria-haspopup="listbox" '
                f'aria-labelledby="{key}-select-label {key}-select" id="{key}-select" class="MuiSelect-select MuiSelect-outlined MuiInputBase-input MuiOutlinedInput-input ~select"{mark}>{display}</div>'
                f'<input aria-invalid="false" name="{name}" aria-hidden="true" tabindex="-1" class="MuiSelect-nativeInput ~nativeInput" value="{value}">'
                f'<svg class="MuiSvgIcon-root MuiSvgIcon-fontSizeMedium MuiSelect-icon MuiSelect-iconOutlined ~selectIcon" focusable="false" aria-hidden="true" viewBox="0 0 24 24" data-testid="ArrowDropDownIcon"><path d="M7 10l5 5 5-5z"></path></svg>'
                f'{notched(label, required)}</div></div>')

    def radio(value: str, label: str, checked: bool = False, mark: str = "") -> str:
        cls = "MuiButtonBase-root MuiRadio-root MuiRadio-colorPrimary PrivateSwitchBase-root" + (" Mui-checked" if checked else "") + " ~radio"
        return (f'<label class="MuiFormControlLabel-root MuiFormControlLabel-labelPlacementEnd ~controlLabel">'
                f'<span class="{cls}"><input class="PrivateSwitchBase-input ~switchInput" name="priority" type="radio" value="{value}"'
                f'{" checked" if checked else ""}{mark}><span class="~radioIcons">'
                f'<svg class="MuiSvgIcon-root MuiSvgIcon-fontSizeMedium ~svgIcon" focusable="false" aria-hidden="true" viewBox="0 0 24 24" data-testid="RadioButtonUncheckedIcon"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8z"></path></svg>'
                f'<svg class="MuiSvgIcon-root MuiSvgIcon-fontSizeMedium ~svgIconChecked" focusable="false" aria-hidden="true" viewBox="0 0 24 24" data-testid="RadioButtonCheckedIcon"><path d="M8.465 8.465C9.37 7.56 10.62 7 12 7C14.76 7 17 9.24 17 12C17 13.38 16.44 14.63 15.535 15.535C14.63 16.44 13.38 17 12 17C9.24 17 7 14.76 7 12C7 10.62 7.56 9.37 8.465 8.465Z"></path></svg>'
                f'</span></span><span class="MuiTypography-root MuiTypography-body1 MuiFormControlLabel-label ~body1">{label}</span></label>')

    def mui_button(text: str, variant: str = "contained", extra_cls: str = "", attrs: str = "") -> str:
        v = variant.capitalize()
        return (f'<button class="MuiButtonBase-root MuiButton-root MuiButton-{variant} MuiButton-{variant}Primary MuiButton-sizeMedium '
                f'MuiButton-{variant}SizeMedium MuiButton-colorPrimary{extra_cls} ~button{v}" tabindex="0"{attrs}>{text}'
                f'<span class="MuiTouchRipple-root ~ripple"></span></button>')

    help_link = (f'<a class="MuiTypography-root MuiTypography-body2 MuiLink-root MuiLink-underlineHover ~helpLink" '
                 f'href="/articles/360014"{T("t5")}>Where can I find my order number?</a>')
    chat_css = (":host{position:fixed;right:20px;bottom:20px;z-index:1300;font:14px/1.4 system-ui}.launcher{display:flex;"
                "align-items:center;gap:8px;border:0;border-radius:999px;background:#111827;color:#fff;padding:12px 18px;"
                "cursor:pointer}.panel{width:340px;border-radius:16px;background:#fff;box-shadow:0 12px 32px rgba(0,0,0,.18);"
                "padding:16px}.composer{display:flex;gap:8px;margin-top:12px}.composer textarea{flex:1;border:1px solid #d1d5db;"
                "border-radius:10px;padding:8px}.send{border:0;border-radius:10px;background:#facc15;padding:0 14px}")
    v2_body = f"""
<div id="root">
<header class="MuiPaper-root MuiPaper-elevation MuiPaper-elevation0 MuiAppBar-root MuiAppBar-colorInherit MuiAppBar-positionSticky ~appBar">
  <div class="MuiToolbar-root MuiToolbar-gutters MuiToolbar-regular ~toolbar">
    <a class="MuiTypography-root MuiTypography-h6 MuiLink-root MuiLink-underlineNone ~brand" href="https://voltaichome.com">{bolt}<span>Voltaic Home</span><span class="MuiChip-root MuiChip-filled MuiChip-sizeSmall ~chip"><span class="MuiChip-label MuiChip-labelSmall ~chipLabel">Support</span></span></a>
    <nav class="~navGroup" aria-label="Main">
{chr(10).join(f'      <a class="MuiButtonBase-root MuiButton-root MuiButton-text MuiButton-textInherit ~navButton" tabindex="0" href="{u}">{t}</a>' for t, u in nav[::-1])}
    </nav>
    <form class="~searchForm" action="/search" role="search">
      <div class="MuiInputBase-root MuiInputBase-colorPrimary ~searchInputRoot"><input type="search" name="query" placeholder="Search help articles" aria-label="Search help articles" class="MuiInputBase-input ~searchInput"></div>
    </form>
    <a class="MuiButtonBase-root MuiButton-root MuiButton-outlined MuiButton-outlinedInherit ~navButton" tabindex="0" href="/my-requests">My requests</a>
  </div>
</header>
<main class="MuiContainer-root MuiContainer-maxWidthLg ~container">
  <nav aria-label="breadcrumb" class="MuiTypography-root MuiTypography-body1 MuiBreadcrumbs-root ~breadcrumbs">
    <ol class="MuiBreadcrumbs-ol ~breadcrumbsOl">
      <li class="MuiBreadcrumbs-li"><a class="MuiTypography-root MuiTypography-inherit MuiLink-root MuiLink-underlineHover ~crumb" href="/">Support</a></li>
      <li aria-hidden="true" class="MuiBreadcrumbs-separator ~separator">/</li>
      <li class="MuiBreadcrumbs-li"><p class="MuiTypography-root MuiTypography-body1 ~crumbCurrent">Contact support</p></li>
    </ol>
  </nav>
  <section class="~tileSection" aria-label="Browse by topic">
    <div class="MuiGrid2-root MuiGrid2-container MuiGrid2-spacing-xs-2 ~grid">
{chr(10).join(f'      <div class="MuiGrid2-root MuiGrid2-grid-xs-6 MuiGrid2-grid-md-2 ~gridItem"><a class="MuiPaper-root MuiPaper-outlined MuiPaper-rounded MuiCard-root ~tileCard" href="{u}"><span class="MuiCardActionArea-focusHighlight ~focusHighlight"></span>{icon(ic, "MuiSvgIcon-root", 22)}<span class="MuiTypography-root MuiTypography-subtitle2 ~tileTitle">{esc(t)}</span></a></div>' for t, d, u, ic in [tiles[2], tiles[3], tiles[0], tiles[4], tiles[1], tiles[5]])}
    </div>
  </section>
  <div class="MuiGrid2-root MuiGrid2-container MuiGrid2-direction-xs-row MuiGrid2-spacing-xs-4 ~grid">
    <div class="MuiGrid2-root MuiGrid2-direction-xs-row MuiGrid2-grid-xs-12 MuiGrid2-grid-md-8 ~gridItem">
      <div class="MuiPaper-root MuiPaper-outlined MuiPaper-rounded MuiCard-root ~card">
        <div class="MuiCardContent-root ~cardContent">
          <h1 class="MuiTypography-root MuiTypography-h4 MuiTypography-gutterBottom ~h4">Contact support</h1>
          <p class="MuiTypography-root MuiTypography-body1 ~body1">Tell us what's going on and a specialist will reply within 4 business hours.</p>
          <div class="MuiPaper-root MuiPaper-elevation MuiPaper-rounded MuiPaper-elevation0 MuiAlert-root MuiAlert-colorWarning MuiAlert-standardWarning MuiAlert-standard ~alert" role="alert">
            <div class="MuiAlert-icon ~alertIcon">{icon("alert", "MuiSvgIcon-root", 22)}</div>
            <div class="MuiAlert-message ~alertMessage"><div class="MuiTypography-root MuiTypography-body1 MuiTypography-gutterBottom MuiAlertTitle-root ~alertTitle">Storm season</div>Red status light after an outage? Try <a href="/articles/360021">Recovering after a power outage</a> first.</div>
          </div>
          <form id="support-request" class="~form" action="/api/support/requests" method="post" enctype="multipart/form-data" novalidate>
            <div class="MuiStack-root ~stack">
              <h2 class="MuiTypography-root MuiTypography-subtitle1 ~subtitle">About your system</h2>
              <div class="MuiStack-root ~stackRow">
                {select_field("product", "product", "Product", "battery-2", "Voltaic Home Battery 2", True)}
                {select_field("topic", "topic", "Topic", "performance", "Battery performance", True, T("t1"))}
              </div>
              {text_field(":r5:", "orderNumber", "Order or serial number", "VH-10423", "VH-104233 or VHB2-…", True, True, "Use the format VH-123456 (six digits after VH-).", mark=T("t2"), extra_helper='<div class="~helpLinkRow">' + icon("help", "MuiSvgIcon-root", 16) + help_link + "</div>")}
              <h2 class="MuiTypography-root MuiTypography-subtitle1 ~subtitle">What's happening?</h2>
              {text_field(":r7:", "subject", "Subject", "Battery stuck at 20% since the October firmware update", required=True)}
              {text_field(":r9:", "description", "Describe the issue", placeholder="What happened, when it started and what you've tried", required=True, helper="Please don't include passwords or full card numbers.", mark=T("t3"), multiline=True)}
              <div class="MuiFormControl-root ~formControl">
                <label class="MuiFormLabel-root MuiFormLabel-colorPrimary ~formLabel" id="priority-label">How urgent is this?</label>
                <div role="radiogroup" aria-labelledby="priority-label" class="MuiFormGroup-root ~radioGroup">
                  {radio("urgent", "Urgent: no power or a safety concern", mark=T("t4"))}
                  {radio("high", "High: the battery isn't backing up my home")}
                  {radio("normal", "Normal: something isn't working right", True)}
                  {radio("low", "Low: general question")}
                </div>
              </div>
              <div class="~uploadRow">
                <label class="MuiButtonBase-root MuiButton-root MuiButton-outlined MuiButton-outlinedPrimary MuiButton-sizeMedium ~buttonOutlined" role="button" tabindex="0"><span class="MuiButton-icon MuiButton-startIcon MuiButton-iconSizeMedium ~startIcon">{icon("upload", size=18)}</span>Upload files<input class="~visuallyHiddenInput" type="file" name="attachments" multiple accept="image/*,.pdf,.log,.txt"></label>
                <p class="MuiTypography-root MuiTypography-caption ~caption">Up to 5 files, 20 MB each. A photo of the status light helps a lot.</p>
              </div>
              <h2 class="MuiTypography-root MuiTypography-subtitle1 ~subtitle">How can we reach you?</h2>
              <div class="MuiStack-root ~stackRow">
                {text_field(":rb:", "name", "Full name", "Hiroshi Tanaka", required=True)}
                {text_field(":rd:", "email", "Email", "h.tanaka@sonicmail.net", required=True, itype="email")}
              </div>
              <label class="MuiFormControlLabel-root MuiFormControlLabel-labelPlacementEnd ~controlLabel"><span class="MuiButtonBase-root MuiCheckbox-root MuiCheckbox-colorPrimary PrivateSwitchBase-root Mui-checked ~checkbox"><input class="PrivateSwitchBase-input ~switchInput" type="checkbox" name="ccMe" checked></span><span class="MuiTypography-root MuiTypography-body1 MuiFormControlLabel-label ~body1">Send me a copy of this request</span></label>
              {mui_button("Submit request", "contained", " MuiButton-fullWidth MuiButton-sizeLarge", ' type="submit"' + T("t6"))}
            </div>
          </form>
        </div>
      </div>
    </div>
    <div class="MuiGrid2-root MuiGrid2-direction-xs-row MuiGrid2-grid-xs-12 MuiGrid2-grid-md-4 ~gridItem">
      <aside class="MuiStack-root ~stack" aria-label="Help">
        <div class="MuiPaper-root MuiPaper-outlined MuiPaper-rounded MuiCard-root ~card">
          <div class="MuiCardHeader-root ~cardHeader"><div class="MuiCardHeader-content ~cardHeaderContent"><span class="MuiTypography-root MuiTypography-h6 MuiCardHeader-title ~cardTitle">Popular answers</span></div></div>
          <ul class="MuiList-root MuiList-padding ~list">
{chr(10).join(f'            <li class="MuiListItem-root MuiListItem-gutters ~listItem"><a class="MuiTypography-root MuiLink-root MuiLink-underlineHover ~listLink" href="{u}">{esc(t)}</a></li>' for t, u in [articles[1], ("Where can I find my order number?", "/articles/360014"), articles[0], articles[2], articles[4]])}
          </ul>
        </div>
        <div class="MuiPaper-root MuiPaper-outlined MuiPaper-rounded MuiCard-root ~card">
          <div class="MuiCardContent-root ~cardContent">
            <h2 class="MuiTypography-root MuiTypography-h6 ~cardTitle">Prefer to talk?</h2>
            <p class="MuiTypography-root MuiTypography-body1 ~body1"><strong>1-888-555-0136</strong></p>
            <p class="MuiTypography-root MuiTypography-body2 ~body2">Mon&ndash;Fri 7 am&ndash;7 pm PT &middot; Sat 8 am&ndash;4 pm PT</p>
            <div class="MuiChip-root MuiChip-outlined MuiChip-colorSuccess ~chipOutlined"><span class="MuiChip-label ~chipLabel">All systems operational</span></div>
          </div>
        </div>
      </aside>
    </div>
  </div>
</main>
<footer class="~footer">
  <div class="MuiContainer-root MuiContainer-maxWidthLg ~container">
    <div class="MuiGrid2-root MuiGrid2-container ~grid">
{columns(cols[::-1], '''      <div class="MuiGrid2-root MuiGrid2-grid-xs-6 MuiGrid2-grid-md-3 ~gridItem">
        <h2 class="MuiTypography-root MuiTypography-overline ~overline">{title}</h2>
        <ul class="~footerList">
{links}
        </ul>
      </div>''', ' class="~footerItem"', ' class="MuiTypography-root MuiLink-root MuiLink-underlineHover ~footerLink"')}
    </div>
    <p class="MuiTypography-root MuiTypography-caption ~caption">&copy; 2026 Voltaic Home Energy, Inc.</p>
  </div>
</footer>
</div>
<div role="presentation" class="MuiDialog-root MuiModal-root ~dialogRoot" hidden>
  <div aria-hidden="true" class="MuiBackdrop-root MuiModal-backdrop ~backdrop"></div>
  <div class="MuiDialog-container MuiDialog-scrollPaper ~dialogContainer" role="presentation" tabindex="-1">
    <div class="MuiPaper-root MuiPaper-elevation MuiPaper-rounded MuiPaper-elevation24 MuiDialog-paper MuiDialog-paperScrollPaper MuiDialog-paperWidthSm ~dialogPaper" role="dialog" aria-labelledby="urgent-dialog-title">
      <h2 class="MuiTypography-root MuiTypography-h6 MuiDialogTitle-root ~dialogTitle" id="urgent-dialog-title">Submit as urgent?</h2>
      <div class="MuiDialogContent-root ~dialogContent"><p class="MuiTypography-root MuiTypography-body1 MuiDialogContentText-root ~dialogText">Urgent requests page our on-call team. If you smell burning or see smoke, leave the area and call 911 first.</p></div>
      <div class="MuiDialogActions-root MuiDialogActions-spacing ~dialogActions">
        {mui_button("Cancel", "text", "", ' type="button"')}
        {mui_button("Submit request", "contained", "", ' type="button"')}
      </div>
    </div>
  </div>
</div>
<vh-support-chat greeting="Hi Hiroshi">
  <template shadowrootmode="open">
    <style>{chat_css}</style>
    <div class="panel" part="panel" role="dialog" aria-label="Chat with Voltaic support" hidden>
      <p class="greeting">Hi Hiroshi! A specialist usually replies in about 3 minutes.</p>
      <form class="composer"><textarea name="message" rows="2" placeholder="Type your message&hellip;" aria-label="Message"></textarea><button type="submit" class="send">Send</button></form>
    </div>
    <button type="button" class="launcher" part="launcher" aria-expanded="false">{icon("chat", size=18)}<span>Chat with us</span></button>
  </template>
</vh-support-chat>
"""
    v2 = document(
        title="Contact support | Voltaic Home",
        head="""<meta name="description" content="Get help with your Voltaic Home Battery, solar or app.">
<meta name="emotion-insertion-point" content="">""",
        body=expand_classes(v2_body, emotion("voltaic-mui")),
    )

    m = meta(
        "form-06",
        "Support request form: topic, order number, message, attachments, priority — Voltaic Home",
        ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change", "copy-change",
         "attribute-churn", "structure-move", "insertion", "tag-change"],
        "v1 is a Foundation 6 page (grid-x/cell, labels wrapping inputs, ticket[...] names). v2 is a React + MUI v5 "
        "rebuild: MuiTextField/MuiSelect markup with css-xxxxxxx emotion classes and ':r5:' ids, notched-outline "
        "<legend><span> copies of every label, the topic select becomes a role=combobox div with a hidden native input, "
        "the description gets MUI's hidden autosize <textarea> twin, and fields are regrouped (product/topic first, "
        "contact details last, priority before attachments, priorities reordered with 'High' added). Decoys: a new "
        "'Product' combobox, a 'Popular answers' card repeating the order-number help link, a hidden MUI dialog with a "
        "second 'Submit request' button, and a <vh-support-chat> widget (declarative shadow root) with its own textarea "
        "and send button.",
        [
            target("t1", "Topic dropdown ('What can we help with?')",
                   "#support-topic", "//select[@name='ticket[topic]']",
                   ["tag-change", "class-obfuscation", "id-change", "attribute-churn", "copy-change", "wrapper-divs",
                    "sibling-reorder", "decoy"]),
            target("t2", "Order number input",
                   "input#order-number", "//input[@placeholder='e.g. VH-104233']",
                   ["class-obfuscation", "id-change", "attribute-churn", "copy-change", "wrapper-divs", "sibling-reorder"]),
            target("t3", "Issue description textarea",
                   ".message-field textarea", "//textarea[@id='ticket-description']",
                   ["class-obfuscation", "id-change", "attribute-churn", "wrapper-divs", "decoy"]),
            target("t4", "'Urgent' priority radio button",
                   "input[name='ticket[priority]'][value='urgent']", "//input[@type='radio' and @value='urgent']",
                   ["class-obfuscation", "id-change", "attribute-churn", "sibling-reorder", "wrapper-divs", "copy-change"]),
            target("t5", "'Where do I find my order number?' help link under the order number field",
                   "a.order-help-link", "//a[normalize-space()='Where do I find my order number?']",
                   ["class-obfuscation", "copy-change", "wrapper-divs", "decoy"]),
            target("t6", "'Send request' submit button",
                   "#new_ticket .button.expanded", "//button[normalize-space()='Send request']",
                   ["class-obfuscation", "copy-change", "decoy"]),
        ],
    )
    return v1, v2, m


# ======================================================================================
# form-07 - Skyward Air: post-flight customer-satisfaction survey
# ======================================================================================
@suite("form-07")
def form07():
    stages = [("booking", "Booking on skywardair.com"), ("checkin", "Airport check-in"), ("boarding", "Security & boarding"),
              ("seat", "Seat comfort"), ("clean", "Cabin cleanliness"), ("crew", "Crew friendliness"),
              ("wifi", "Wi-Fi & entertainment"), ("snacks", "Snacks & beverages")]
    scale = [("1", "Very dissatisfied"), ("2", "Dissatisfied"), ("3", "Neutral"), ("4", "Satisfied"), ("5", "Very satisfied"),
             ("na", "Not applicable")]
    issues = [("delay", "My flight was delayed by more than 30 minutes"), ("bag", "My checked bag was delayed or damaged"),
              ("rebooked", "I was rebooked or moved to a different seat"), ("assist", "I needed special assistance"),
              ("none", "None of these")]
    plane = ('<svg width="32" height="32" viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="16" r="16" fill="#0369a1"/>'
             '<path d="M7 18 25 9l-4 14-5-4-3 4v-5z" fill="#e0f2fe"/></svg>')
    footer_links = [("skywardair.com", "https://skywardair.com"), ("Help", "https://skywardair.com/help"),
                    ("Accessibility", "https://skywardair.com/accessibility"), ("Unsubscribe from surveys", "/s/SW1482/unsubscribe")]

    # ---------------------------------------------------------------- v1: classic survey tool (tables + radios)
    v1_css = """
  body { margin: 0; font: 16px/1.5 Arial, Helvetica, sans-serif; color: #1e293b; background: #f1f5f9; }
  .survey-header { background: #0369a1; color: #fff; }
  .survey-header__inner, .survey-container { max-width: 860px; margin: 0 auto; padding: 16px 24px; }
  .survey-question { background: #fff; border: 1px solid #cbd5e1; border-radius: 4px; padding: 20px 24px; margin: 0 0 20px; }
  .question-text { font-size: 18px; font-weight: bold; margin: 0 0 12px; }
  .matrix-table { width: 100%; border-collapse: collapse; font-size: 14px; }
  .matrix-table th, .matrix-table td { border-bottom: 1px solid #e2e8f0; padding: 8px 4px; text-align: center; }
  .matrix-label { text-align: left !important; font-weight: normal; }
  .nps-options { display: flex; gap: 4px; list-style: none; padding: 0; margin: 8px 0; }
  .nps-option label { display: block; width: 36px; padding: 6px 0; text-align: center; border: 1px solid #94a3b8; }
  .choice { display: block; margin: 6px 0; }
  .btn { border: 0; border-radius: 3px; padding: 10px 20px; font-size: 16px; cursor: pointer; }
  .btn-submit { background: #0369a1; color: #fff; } .btn-prev { background: #e2e8f0; }
  .sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
"""
    v1_head = "".join(f'<th scope="col">{lbl}</th>' for _, lbl in scale)
    v1_rows = "\n".join(
        f'<tr class="matrix-row"><th scope="row" class="matrix-label">{esc(text)}</th>'
        + "".join(f'<td class="matrix-cell"><input type="radio" name="q4_{key}" value="{v}" aria-label="{esc(text)}: {lbl}"'
                  f'{T("t1") if (key, v) == ("seat", "2") else ""}{" checked" if (key, v) in {("booking", "4"), ("checkin", "5"), ("boarding", "3"), ("crew", "5"), ("wifi", "na")} else ""}></td>'
                  for v, lbl in scale)
        + "</tr>" for key, text in stages)
    v1_nps = "\n".join(
        f'<li class="nps-option"><input type="radio" id="nps-{i}" name="q5_nps" value="{i}"{T("t2") if i == 9 else ""}><label for="nps-{i}">{i}</label></li>'
        for i in range(11))
    v1_issues = "\n".join(
        f'<label class="choice"><input type="checkbox" id="q7-{key}" name="q7[]" value="{key}"{T("t6") if key == "bag" else ""}> {esc(text)}</label>'
        for key, text in issues)
    v1_body = f"""
<header class="survey-header">
  <div class="survey-header__inner">
    <a class="survey-header__logo" href="https://skywardair.com">{plane}<span>Skyward Air</span></a>
    <span class="survey-header__title">Customer feedback</span>
    <form class="survey-header__lang" action="/s/SW1482/lang" method="get">
      <label for="survey-lang" class="sr-only">Language</label>
      <select id="survey-lang" name="lang"><option value="en" selected>English</option><option value="es">Español</option><option value="fr">Français</option></select>
    </form>
  </div>
</header>
<main class="survey-container">
  <section class="flight-card" aria-label="Your flight">
    <p class="flight-card__greeting">Thanks for flying with us, Morgan. This survey takes about 3 minutes.</p>
    <dl class="flight-card__details">
      <div class="flight-card__item"><dt>Flight</dt><dd>SW 1482</dd></div>
      <div class="flight-card__item"><dt>Route</dt><dd>Denver (DEN) &rarr; Portland (PDX)</dd></div>
      <div class="flight-card__item"><dt>Date</dt><dd>Wed, Oct 14, 2026</dd></div>
      <div class="flight-card__item"><dt>Seat</dt><dd>14C &middot; Main Cabin</dd></div>
    </dl>
  </section>
  <div class="progress" role="progressbar" aria-valuenow="2" aria-valuemin="1" aria-valuemax="2" aria-label="Survey progress">
    <div class="progress__bar" style="width: 100%"></div>
    <span class="progress__label">Page 2 of 2</span>
  </div>
  <form id="survey-form" class="survey-form" action="/s/SW1482/responses" method="post">
    <input type="hidden" name="response_id" value="R_3mX9qL2vT8kP1aZ">
    <input type="hidden" name="page" value="2">
    <div class="survey-question" id="q4">
      <h2 class="question-text"><span class="question-number">4.</span> How satisfied were you with each part of your journey?</h2>
      <table class="matrix-table">
        <thead><tr><th scope="col"><span class="sr-only">Journey stage</span></th>{v1_head}</tr></thead>
        <tbody>
{v1_rows}
        </tbody>
      </table>
    </div>
    <fieldset class="survey-question nps-question" id="q5">
      <legend class="question-text"{T("t5")}><span class="question-number">5.</span> How likely are you to recommend Skyward Air to a friend or colleague?</legend>
      <div class="nps-scale">
        <span class="nps-anchor nps-anchor--low">Not at all likely</span>
        <ol class="nps-options">
{v1_nps}
        </ol>
        <span class="nps-anchor nps-anchor--high">Extremely likely</span>
      </div>
    </fieldset>
    <div class="survey-question" id="q6">
      <label class="question-text" for="q6-text"><span class="question-number">6.</span> What is the main reason for your score?</label>
      <textarea id="q6-text" name="q6_reason" rows="5" maxlength="2000" placeholder="Optional"{T("t3")}></textarea>
      <p class="char-count">0 / 2000</p>
    </div>
    <fieldset class="survey-question" id="q7">
      <legend class="question-text"><span class="question-number">7.</span> Did any of these happen on your trip? <span class="question-hint">(Select all that apply)</span></legend>
{v1_issues}
    </fieldset>
    <fieldset class="survey-question" id="q8">
      <legend class="question-text"><span class="question-number">8.</span> May we contact you about your feedback?</legend>
      <label class="choice"><input type="radio" name="q8_contact" value="yes"> Yes, email me at m.oduya@example.net</label>
      <label class="choice"><input type="radio" name="q8_contact" value="no" checked> No, thanks</label>
    </fieldset>
    <div class="survey-nav">
      <button type="submit" name="nav" value="back" class="btn btn-prev" formnovalidate>Back</button>
      <button type="submit" name="nav" value="submit" class="btn btn-submit"{T("t4")}>Submit survey</button>
    </div>
  </form>
  <p class="survey-privacy">Your answers are confidential and are only used to improve our service. <a href="https://skywardair.com/privacy">Privacy policy</a></p>
</main>
<footer class="survey-footer">
  <p>Powered by Skyward Listens &middot; &copy; 2026 Skyward Air, Inc.</p>
  <ul class="survey-footer__links">
{links(footer_links)}
  </ul>
</footer>
"""
    v1 = document(
        title="Skyward Air – Tell us about your flight",
        head=f"""<meta name="robots" content="noindex, nofollow">
<style>{v1_css}</style>""",
        body=v1_body,
    )

    # ---------------------------------------------------------------- v2: SvelteKit + <sw-rating-scale>
    scale_css = (":host{display:block}.scale{font:15px/1.4 system-ui}.label{margin:0 0 12px;font-weight:600}"
                 ".options{display:grid;grid-template-columns:repeat(11,1fr);gap:6px}.option{height:44px;border:1px solid #94a3b8;"
                 "border-radius:8px;background:#fff;font:600 15px system-ui;cursor:pointer}.option[aria-checked=true]{background:#0369a1;"
                 "color:#fff;border-color:#0369a1}.anchors{display:flex;justify-content:space-between;margin-top:6px;font-size:13px;color:#64748b}")

    def rating(name: str, question_id: str, question: str, mark9: str = "", qmark: str = "") -> str:
        btns = "\n".join(
            f'              <button type="button" role="radio" aria-checked="false" class="option" part="option" data-value="{i}" '
            f'tabindex="{0 if i == 0 else -1}"{mark9 if i == 9 else ""}>{i}</button>' for i in range(11))
        return f"""<sw-rating-scale name="{name}" min="0" max="10" class="~Question:scale">
          <template shadowrootmode="open">
            <style>{scale_css}</style>
            <div class="scale" role="radiogroup" aria-labelledby="label" part="scale">
              <p class="label" id="label"><slot name="question"></slot></p>
              <div class="options">
{btns}
              </div>
              <div class="anchors" aria-hidden="true"><span>Not at all likely</span><span>Extremely likely</span></div>
            </div>
          </template>
          <h2 slot="question" id="{question_id}" class="~Question:title"{qmark}>{question}</h2>
          <input type="hidden" name="{name}" value="">
        </sw-rating-scale>"""

    order = ["crew", "boarding", "seat", "clean", "checkin", "booking", "wifi", "snacks", "baggage"]
    labels = dict(stages) | {"baggage": "Baggage delivery"}
    v2_scale = [scale[4], scale[3], scale[2], scale[1], scale[0], ("na", "N/A")]
    preset = {("booking", "4"), ("checkin", "5"), ("boarding", "3"), ("crew", "5"), ("wifi", "na")}
    v2_rows = "\n".join(
        f'''<div class="~Likert:row" role="radiogroup" aria-labelledby="st-{key}">
          <span class="~Likert:statement" id="st-{key}">{esc(labels[key])}</span>
          <div class="~Likert:options">
{chr(10).join(f'            <label class="~Likert:option"><input class="~Likert:input" type="radio" name="journey[{key}]" value="{v}"{" checked" if (key, v) in preset else ""}{T("t1") if (key, v) == ("seat", "2") else ""}><span class="~Likert:pill">{lbl}</span></label>' for v, lbl in v2_scale)}
          </div>
        </div>''' for key in order)
    v2_issues = [("rebooked", "I was rebooked or moved to a different seat"), ("bag", "My checked luggage arrived late or was damaged"),
                 ("delay", "My flight was delayed by more than 30 minutes"), ("wifi", "In-flight Wi-Fi didn't work"),
                 ("assist", "I needed special assistance"), ("none", "None of these")]
    v2_choices = "\n".join(
        f'          <label class="~Choice:tile"><input type="checkbox" class="~Choice:input" id="q7-{k}" name="issues" value="{k}"'
        f'{T("t6") if k == "bag" else ""}><span class="~Choice:text">{esc(t)}</span></label>' for k, t in v2_issues)
    v2_body = f"""
<div id="svelte" style="display: contents">
<header class="~Header:bar">
  <a class="~Header:brand" href="https://skywardair.com">{plane}<span class="~Header:name">Skyward Air</span></a>
  <p class="~Header:trip">SW 1482 &middot; DEN &rarr; PDX &middot; Oct 14</p>
  <div class="~Header:locales" role="group" aria-label="Language">
    <button type="button" class="~Header:locale-active" aria-pressed="true">EN</button>
    <button type="button" class="~Header:locale" aria-pressed="false">ES</button>
    <button type="button" class="~Header:locale" aria-pressed="false">FR</button>
  </div>
</header>
<main class="~Survey:page">
  <div class="~Progress:track" role="progressbar" aria-valuenow="2" aria-valuemin="1" aria-valuemax="2" aria-label="Survey progress"><div class="~Progress:fill" style="width: 100%"></div></div>
  <p class="~Progress:caption">Last page &mdash; about a minute to go</p>
  <form class="~Survey:form" action="/api/responses/R_3mX9qL2vT8kP1aZ" method="post">
    <section class="~Question:card" aria-labelledby="journey-title">
      <h2 id="journey-title" class="~Question:title">How was each part of your journey?</h2>
      <p class="~Question:hint">Pick one answer per row. Choose N/A for anything you didn't use.</p>
      <div class="~Likert:grid">
{v2_rows}
      </div>
    </section>
    <section class="~Question:card" aria-labelledby="again-q">
        {rating("fly_again", "again-q", "How likely are you to choose Skyward Air for your next trip?")}
    </section>
    <section class="~Question:card" aria-labelledby="nps-q">
        {rating("nps", "nps-q", "How likely is it that you would recommend Skyward Air to a friend or colleague?", T("t2"), T("t5"))}
    </section>
    <section class="~Question:card" aria-labelledby="reason-label">
      <label id="reason-label" class="~Question:title" for="reason">Tell us more about your score <span class="~Question:optional">(optional)</span></label>
      <textarea id="reason" class="~TextArea:field" name="nps_reason" rows="5" maxlength="2000" placeholder="What went well? What could we do better?"{T("t3")}></textarea>
      <p class="~TextArea:count" aria-live="polite">0/2000</p>
    </section>
    <section class="~Question:card" aria-labelledby="issues-title">
      <h2 id="issues-title" class="~Question:title">Did any of these happen on your trip?</h2>
      <p class="~Question:hint">Select all that apply</p>
      <div class="~Choice:grid">
{v2_choices}
      </div>
    </section>
    <section class="~Question:card" aria-labelledby="contact-title">
      <h2 id="contact-title" class="~Question:title">Can we follow up with you?</h2>
      <label class="~Toggle:wrap"><input type="checkbox" role="switch" class="~Toggle:input" name="contact_ok" value="yes"><span class="~Toggle:track"></span><span class="~Toggle:label">Yes, email me at m.oduya@example.net</span></label>
    </section>
    <div class="~Survey:actions">
      <a class="~Button:secondary" href="/s/SW1482?page=1">Back</a>
      <button type="submit" class="~Button:primary"{T("t4")}>Submit feedback</button>
    </div>
  </form>
  <p class="~Survey:privacy">Your answers are confidential. <a href="https://skywardair.com/privacy">How we use survey data</a></p>
</main>
<footer class="~Footer:bar">
  <ul class="~Footer:links">
{links(footer_links[::-1], ' class="~Footer:item"', ' class="~Footer:link"')}
  </ul>
  <p class="~Footer:copy">&copy; 2026 Skyward Air, Inc. Survey platform by Skyward Listens.</p>
</footer>
<div class="~FeedbackTab:root">
  <button type="button" class="~FeedbackTab:tab" aria-expanded="false" aria-controls="site-feedback">Website feedback</button>
  <div id="site-feedback" class="~FeedbackTab:panel" role="dialog" aria-label="Website feedback" hidden>
    <p class="~FeedbackTab:prompt">How easy was this page to use?</p>
    <div class="~FeedbackTab:faces" role="radiogroup" aria-label="Ease of use">
      <button type="button" role="radio" aria-checked="false" class="~FeedbackTab:face" aria-label="Very hard">1</button>
      <button type="button" role="radio" aria-checked="false" class="~FeedbackTab:face" aria-label="Hard">2</button>
      <button type="button" role="radio" aria-checked="false" class="~FeedbackTab:face" aria-label="Okay">3</button>
      <button type="button" role="radio" aria-checked="false" class="~FeedbackTab:face" aria-label="Easy">4</button>
      <button type="button" role="radio" aria-checked="false" class="~FeedbackTab:face" aria-label="Very easy">5</button>
    </div>
    <textarea class="~FeedbackTab:comment" name="site_comment" rows="3" placeholder="Anything we should fix on this page?" aria-label="Comment"></textarea>
    <button type="button" class="~FeedbackTab:submit">Submit feedback</button>
  </div>
</div>
</div>
"""
    v2 = document(
        title="Your flight to Portland | Skyward Air feedback",
        head="""<meta name="robots" content="noindex, nofollow">
<link rel="modulepreload" href="/_app/immutable/entry/start.4f1c2a9e.js">""",
        body=expand_classes(v2_body, svelte("skyward")),
    )

    m = meta(
        "form-07",
        "Post-flight satisfaction survey: Likert grid, NPS 0–10, comments — Skyward Air",
        ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change", "copy-change",
         "attribute-churn", "structure-move", "insertion", "tag-change"],
        "v1 is a classic survey-tool page: a <table> Likert matrix (rows = journey stages, columns Very dissatisfied … "
        "Not applicable), an NPS fieldset of 11 radio inputs, numbered questions. v2 is a SvelteKit rewrite with "
        "renamed classes plus svelte-xxxxxxx scoping: each Likert row becomes a role=radiogroup card with pill labels, "
        "statements are reordered, the scale is reversed (Very satisfied first) and a 'Baggage delivery' row is added; "
        "the NPS question becomes a <sw-rating-scale> declarative shadow root with role=radio buttons and its question "
        "is a slotted <h2> with reworded copy. Decoys: an inserted 0–10 'choose Skyward Air for your next trip' scale "
        "(same component, another '9' button) placed before the NPS question, reordered checkbox tiles, and a site-wide "
        "'Website feedback' widget with its own textarea and 'Submit feedback' button.",
        [
            target("t1", "'Dissatisfied' radio in the 'Seat comfort' row of the satisfaction grid",
                   "table.matrix-table tbody tr:nth-child(4) td:nth-child(3) input",
                   "//input[@name='q4_seat' and @value='2']",
                   ["class-obfuscation", "tag-change", "sibling-reorder", "wrapper-divs", "attribute-churn", "insertion"]),
            target("t2", "NPS score '9' option",
                   "#nps-9", "//fieldset[@id='q5']//input[@value='9']",
                   ["shadow-dom", "tag-change", "id-change", "class-obfuscation", "decoy", "insertion"]),
            target("t3", "Free-text 'reason for your score' textarea",
                   "textarea[name='q6_reason']", "//textarea[@id='q6-text']",
                   ["class-obfuscation", "id-change", "attribute-churn", "copy-change", "decoy"]),
            target("t4", "'Submit survey' button",
                   ".survey-nav .btn-submit", "//button[normalize-space()='Submit survey']",
                   ["class-obfuscation", "copy-change", "decoy", "wrapper-divs"]),
            target("t5", "NPS question text ('How likely are you to recommend Skyward Air…')",
                   "#q5 > legend", "//legend[contains(., 'recommend Skyward Air')]",
                   ["tag-change", "copy-change", "class-obfuscation", "structure-move", "insertion"]),
            target("t6", "'My checked bag was delayed or damaged' checkbox",
                   "#q7-bag", "//label[contains(., 'checked bag')]/input",
                   ["class-obfuscation", "attribute-churn", "copy-change", "sibling-reorder", "insertion"]),
        ],
    )
    return v1, v2, m


# ======================================================================================
# form-08 - The Linden Hotel, Edinburgh: room booking form
# ======================================================================================
@suite("form-08")
def form08():
    rooms = [  # code, slug, name, description, size, sleeps, view, price, colour
        ("CDB", "classic-double", "Classic Double", "A cosy double overlooking the Royal Terrace gardens.", "22 m²", "Sleeps 2",
         "Garden view", "£189", "#a8a29e"),
        ("SKG", "superior-king", "Superior King", "More space, a king bed and a writing desk by the window.", "28 m²", "Sleeps 2",
         "City view", "£229", "#78716c"),
        ("JRS", "junior-suite", "Junior Suite", "Separate sitting area, king bed and a rainfall shower.", "38 m²", "Sleeps 3",
         "Calton Hill view", "£289", "#57534e"),
        ("LDS", "linden-suite", "Linden Suite", "Two rooms, a freestanding bath and a private terrace.", "55 m²", "Sleeps 4",
         "Terrace", "£420", "#44403c"),
    ]
    nav = [("Rooms & Suites", "/rooms"), ("Dining", "/dining"), ("Spa", "/spa"), ("Offers", "/offers"),
           ("Weddings & Events", "/events"), ("Gallery", "/gallery"), ("Contact", "/contact")]
    titles = ["Mr", "Mrs", "Ms", "Mx", "Dr"]
    arrivals = ["Before 12:00", "12:00 – 15:00", "15:00 – 18:00", "18:00 – 21:00", "After 21:00"]
    explore = [("Rooms & Suites", "/rooms"), ("Dining at Rowan", "/dining"), ("The Spa", "/spa"), ("Offers", "/offers"),
               ("Gift vouchers", "/vouchers")]
    info = [("FAQs", "/faq"), ("Getting here", "/getting-here"), ("Accessibility", "/accessibility"), ("Careers", "/careers"),
            ("Press", "/press")]
    legal = [("Privacy", "/privacy"), ("Cookies", "/cookies"), ("Terms", "/terms")]
    crest = ('<svg width="36" height="36" viewBox="0 0 36 36" aria-hidden="true"><circle cx="18" cy="18" r="17" fill="none" '
             'stroke="#14532d" stroke-width="2"/><path d="M18 7c-6 6-6 14 0 22 6-8 6-16 0-22zm0 4v18" stroke="#14532d" fill="none"/></svg>')

    def bed(colour: str) -> str:
        return (f'<svg width="96" height="64" viewBox="0 0 96 64" aria-hidden="true"><rect width="96" height="64" rx="6" fill="{colour}"/>'
                '<path d="M14 46V26h20a10 10 0 0 1 10 10v10M14 40h68v6" stroke="#fff" stroke-width="3" fill="none"/></svg>')

    # ---------------------------------------------------------------- v1: hand-rolled BEM booking engine
    v1_css = """
  body { margin: 0; font: 16px/1.55 "Lora", Georgia, serif; color: #1c1917; background: #fbf8f3; }
  .container { max-width: 1180px; margin: 0 auto; padding: 0 24px; }
  .utility-bar { background: #14532d; color: #ecfdf5; font: 13px/1 system-ui; padding: 8px 0; }
  .site-header__inner { display: flex; align-items: center; justify-content: space-between; height: 76px; }
  .main-nav__list { display: flex; gap: 22px; list-style: none; margin: 0; padding: 0; }
  .booking__layout { display: grid; grid-template-columns: 1fr 340px; gap: 40px; align-items: start; }
  .form-section { border: 0; border-top: 1px solid #e7e0d4; padding: 24px 0; margin: 0; }
  .form-row { display: flex; gap: 16px; align-items: flex-end; }
  .stepper { display: flex; align-items: center; gap: 8px; }
  .stepper__btn { width: 36px; height: 36px; border-radius: 50%; border: 1px solid #a8a29e; background: #fff; }
  .room-card { display: grid; grid-template-columns: 96px 1fr 140px; gap: 16px; padding: 16px; border: 1px solid #e7e0d4; margin-bottom: 12px; background: #fff; }
  .room-card__amount { font-size: 22px; }
  .booking-summary { position: sticky; top: 96px; background: #fff; border: 1px solid #e7e0d4; padding: 24px; }
  .btn { display: inline-block; padding: 12px 20px; border-radius: 2px; font: 600 15px system-ui; }
  .btn--primary { background: #14532d; color: #fff; border: 0; } .btn--block { width: 100%; }
"""
    v1_cards = "\n".join(
        f'''<article class="room-card" data-room="{code}">
  <div class="room-card__media">{bed(col)}</div>
  <div class="room-card__body">
    <h3 class="room-card__name">{name}</h3>
    <p class="room-card__desc">{desc}</p>
    <ul class="room-card__features"><li>{size}</li><li>{sleeps}</li><li>{view}</li></ul>
  </div>
  <div class="room-card__price">
    <span class="room-card__amount">{price}</span><span class="room-card__per">per night</span>
    <label class="room-card__select"><input type="radio" name="room_type" value="{code}" id="room-{code}"{" checked" if code == "JRS" else ""}{T("t3") if code == "JRS" else ""}> Select</label>
  </div>
</article>''' for code, _, name, desc, size, sleeps, view, price, col in rooms)

    def v1_stepper(key: str, label: str, singular: str, value: int, lo: int, hi: int, mark: str = "", hint: str = "") -> str:
        return f'''<div class="form-field stepper stepper--{key}" data-field="{key}">
            <span class="stepper__label" id="{key}-label">{label}{hint}</span>
            <button type="button" class="stepper__btn stepper__btn--minus" aria-label="Remove {singular}"{" disabled" if value <= lo else ""}>{icon("minus", size=16)}</button>
            <input type="number" id="{key}" name="{key}" value="{value}" min="{lo}" max="{hi}" readonly aria-labelledby="{key}-label">
            <button type="button" class="stepper__btn stepper__btn--plus" aria-label="Add {singular}"{mark}>{icon("plus", size=16)}</button>
          </div>'''

    v1_body = f"""
<div class="utility-bar">
  <div class="container utility-bar__inner">
    <span class="utility-bar__text">Free cancellation up to 48 hours before arrival on flexible rates</span>
    <a class="utility-bar__phone" href="tel:+441315550192">+44 131 555 0192</a>
    <ul class="lang-list">
      <li class="lang-list__item"><a href="/en/book" aria-current="true">EN</a></li>
      <li class="lang-list__item"><a href="/fr/book">FR</a></li>
      <li class="lang-list__item"><a href="/de/book">DE</a></li>
    </ul>
  </div>
</div>
<header class="site-header">
  <div class="container site-header__inner">
    <a class="brand" href="/">{crest}<span class="brand__name">The Linden</span><span class="brand__tag">Edinburgh</span></a>
    <nav class="main-nav" aria-label="Main navigation">
      <ul class="main-nav__list">
{links(nav, ' class="main-nav__item"', ' class="main-nav__link"')}
      </ul>
    </nav>
    <a class="btn btn--outline header-cta" href="/book">Book now</a>
  </div>
</header>
<main class="booking container">
  <ol class="booking-steps">
    <li class="booking-steps__step booking-steps__step--current">1. Stay details</li>
    <li class="booking-steps__step">2. Payment</li>
    <li class="booking-steps__step">3. Confirmation</li>
  </ol>
  <h1 class="booking__title">Book your stay</h1>
  <div class="booking__layout">
    <form id="booking-form" class="booking-form" action="/reservations" method="post">
      <input type="hidden" name="property_code" value="LDN-EDI">
      <input type="hidden" name="rate_plan" value="BAR">
      <fieldset class="form-section form-section--dates">
        <legend class="form-section__title">Dates &amp; guests</legend>
        <div class="form-row">
          <div class="form-field">
            <label for="checkin">Check-in</label>
            <input type="date" id="checkin" name="arrival_date" value="2026-12-18" min="2026-11-05" required{T("t1")}>
          </div>
          <div class="form-field">
            <label for="checkout">Check-out</label>
            <input type="date" id="checkout" name="departure_date" value="2026-12-22" min="2026-11-06" required>
          </div>
          <p class="form-row__note">4 nights</p>
        </div>
        <div class="form-row">
          {v1_stepper("adults", "Adults", "adult", 2, 1, 4, T("t2"))}
          {v1_stepper("children", "Children", "child", 0, 0, 3, "", " <small>(2&ndash;12)</small>")}
          <div class="form-field">
            <label for="rooms">Rooms</label>
            <select id="rooms" name="rooms">{opts(["1", "2", "3", "4"], "1")}</select>
          </div>
        </div>
        <div class="form-field form-field--promo">
          <label for="promo">Promo or corporate code <span class="optional">(optional)</span></label>
          <input type="text" id="promo" name="promo_code" autocomplete="off">
        </div>
      </fieldset>
      <fieldset class="form-section form-section--rooms">
        <legend class="form-section__title">Choose your room</legend>
        <div class="room-list">
{v1_cards}
        </div>
        <div class="rate-options">
          <label class="rate-option"><input type="radio" name="rate" value="flex" checked> <strong>Flexible rate</strong> &ndash; free cancellation until 48 hours before arrival</label>
          <label class="rate-option"><input type="radio" name="rate" value="advance"> <strong>Advance purchase</strong> &ndash; non-refundable, save 15%</label>
        </div>
      </fieldset>
      <fieldset class="form-section form-section--guest">
        <legend class="form-section__title">Guest details</legend>
        <div class="form-row">
          <div class="form-field form-field--title">
            <label for="guest-title">Title</label>
            <select id="guest-title" name="guest[title]">{opts(titles, "Ms")}</select>
          </div>
          <div class="form-field">
            <label for="guest-first">First name</label>
            <input type="text" id="guest-first" name="guest[first_name]" autocomplete="given-name" value="Aisha" required>
          </div>
          <div class="form-field">
            <label for="guest-last">Last name</label>
            <input type="text" id="guest-last" name="guest[last_name]" autocomplete="family-name" value="Rahman" required>
          </div>
        </div>
        <div class="form-row">
          <div class="form-field">
            <label for="guest-email">Email</label>
            <input type="email" id="guest-email" name="guest[email]" autocomplete="email" value="aisha.rahman@outlook.com" required>
          </div>
          <div class="form-field">
            <label for="guest-phone">Phone</label>
            <input type="tel" id="guest-phone" name="guest[phone]" autocomplete="tel" value="+44 7700 900461">
          </div>
          <div class="form-field">
            <label for="arrival-time">Estimated arrival</label>
            <select id="arrival-time" name="arrival_time">{opts(arrivals, "15:00 – 18:00")}</select>
          </div>
        </div>
        <div class="form-field">
          <label for="special-requests">Special requests</label>
          <textarea id="special-requests" class="special-requests" name="special_requests" rows="4" placeholder="e.g. early check-in, extra pillows, celebrating an anniversary"{T("t4")}></textarea>
          <p class="form-field__hint">Requests are subject to availability and can't be guaranteed.</p>
        </div>
        <label class="checkbox"><input type="checkbox" name="accept_policy" value="1" required> I have read the <a href="/policies">cancellation policy</a></label>
      </fieldset>
    </form>
    <aside class="booking-summary" aria-labelledby="summary-title">
      <h2 id="summary-title" class="booking-summary__title">Your stay</h2>
      <dl class="summary-list">
        <dt>Dates</dt><dd>Fri 18 Dec &ndash; Tue 22 Dec 2026</dd>
        <dt>Guests</dt><dd>2 adults</dd>
        <dt>Room</dt><dd>Junior Suite, flexible rate</dd>
        <dt>4 nights &times; &pound;289.00</dt><dd>&pound;1,156.00</dd>
        <dt>Edinburgh Visitor Levy (5%)</dt><dd>&pound;57.80</dd>
      </dl>
      <dl class="summary-total">
        <dt>Total</dt><dd class="summary-total__amount"{T("t6")}>&pound;1,213.80</dd>
      </dl>
      <p class="booking-summary__note">Includes VAT. Pay nothing today on flexible rates.</p>
      <button type="submit" form="booking-form" class="btn btn--primary btn--block btn-book"{T("t5")}>Book now</button>
      <ul class="booking-summary__perks">
        <li>Best rate guaranteed when you book direct</li>
        <li>Free Wi-Fi and late checkout until 12:00</li>
      </ul>
    </aside>
  </div>
</main>
<footer class="site-footer">
  <div class="container site-footer__grid">
    <div class="site-footer__col">
      <h2 class="site-footer__heading">The Linden Hotel</h2>
      <address>14 Royal Terrace<br>Edinburgh EH7 5AB<br>Scotland</address>
      <p><a href="tel:+441315550192">+44 131 555 0192</a><br><a href="mailto:stay@thelindenhotel.co.uk">stay@thelindenhotel.co.uk</a></p>
    </div>
    <div class="site-footer__col">
      <h2 class="site-footer__heading">Explore</h2>
      <ul class="site-footer__list">
{links(explore)}
      </ul>
    </div>
    <div class="site-footer__col">
      <h2 class="site-footer__heading">Information</h2>
      <ul class="site-footer__list">
{links(info)}
      </ul>
    </div>
    <div class="site-footer__col">
      <h2 class="site-footer__heading">Newsletter</h2>
      <form class="newsletter" action="/newsletter" method="post">
        <label for="nl-email">Seasonal offers, straight to your inbox</label>
        <input id="nl-email" type="email" name="email" placeholder="Email address">
        <button type="submit" class="btn btn--small">Sign up</button>
      </form>
    </div>
  </div>
  <div class="container site-footer__legal">
    <p>&copy; 2026 The Linden Hotel Ltd. Registered in Scotland SC412907.</p>
    <ul class="site-footer__legal-links">
{links(legal)}
    </ul>
  </div>
</footer>
"""
    v1 = document(
        title="Book your stay | The Linden Hotel, Edinburgh",
        head=f"""<meta name="description" content="Book direct at The Linden, a boutique hotel on Edinburgh's Royal Terrace.">
<style>{v1_css}</style>""",
        body=v1_body,
        lang="en-GB",
    )

    # ---------------------------------------------------------------- v2: React + StyleX atomic CSS
    S = {
        "body": "margin:0;font-family:Lora,Georgia,serif;color:#1c1917;background-color:#fbf8f3",
        "header": "position:sticky;top:0;z-index:20;background-color:#fbf8f3;border-bottom:1px solid #e7e0d4",
        "headerInner": "display:flex;align-items:center;justify-content:space-between;max-width:1200px;margin-inline:auto;padding-inline:24px;height:72px",
        "brand": "display:flex;align-items:center;gap:10px;color:inherit;text-decoration:none",
        "brandName": "font-size:22px;letter-spacing:.04em",
        "nav": "display:none;@media (min-width:960px){display:block}",
        "navList": "display:flex;gap:24px;list-style:none;margin:0;padding:0",
        "navItem": "font-family:system-ui;font-size:14px",
        "navLink": "color:inherit;text-decoration:none;text-underline-offset:4px",
        "headerCta": "font-family:system-ui;font-size:14px;font-weight:600;border:1px solid currentColor;padding:10px 16px;color:#14532d",
        "banner": "background-color:#14532d;color:#ecfdf5;text-align:center;font-family:system-ui;font-size:13px;padding:8px",
        "main": "max-width:1200px;margin-inline:auto;padding-inline:24px;padding-block:32px",
        "steps": "font-family:system-ui;font-size:13px;margin-bottom:16px",
        "stepsList": "display:flex;gap:24px;list-style:none;margin:0;padding:0",
        "step": "color:#78716c",
        "stepCurrent": "color:#14532d;font-weight:600",
        "title": "font-size:34px;font-weight:400;margin:0 0 24px",
        "layout": "display:grid;grid-template-columns:1fr;gap:40px;@media (min-width:960px){grid-template-columns:1fr 360px}",
        "form": "display:flex;flex-direction:column;gap:8px",
        "section": "padding-block:24px;border-top:1px solid #e7e0d4",
        "sectionTitle": "font-size:22px;font-weight:400;margin:0 0 16px",
        "dateRange": "display:block;margin-bottom:8px",
        "guestList": "display:flex;flex-direction:column;border:1px solid #e7e0d4;background-color:#fff",
        "guestRow": "display:flex;align-items:center;justify-content:space-between;padding:14px 16px;border-bottom:1px solid #f0ebe3",
        "guestLabel": "margin:0;font-family:system-ui;font-weight:600",
        "guestHint": "margin:0;font-family:system-ui;font-size:13px;color:#78716c",
        "stepper": "display:flex;align-items:center;gap:12px",
        "stepperBtn": "display:grid;place-items:center;width:36px;height:36px;border-radius:999px;border:1px solid #a8a29e;background-color:#fff;cursor:pointer",
        "stepperValue": "min-width:20px;text-align:center;font-family:system-ui;font-weight:600",
        "row": "display:flex;flex-wrap:wrap;gap:16px;margin-top:16px",
        "field": "display:flex;flex-direction:column;gap:6px;flex:1 1 200px",
        "label": "font-family:system-ui;font-size:14px;font-weight:600",
        "input": "font-family:system-ui;font-size:16px;padding:12px;border:1px solid #d6d3d1;border-radius:4px;background-color:#fff",
        "textarea": "font-family:system-ui;font-size:16px;padding:12px;border:1px solid #d6d3d1;border-radius:4px;background-color:#fff;resize:vertical;min-height:110px",
        "hint": "margin:0;font-family:system-ui;font-size:13px;color:#78716c",
        "details": "margin-top:12px;font-family:system-ui;font-size:14px",
        "roomGrid": "display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(240px,1fr))",
        "roomCard": "position:relative;display:flex;flex-direction:column;gap:6px;padding:16px;border:1px solid #e7e0d4;background-color:#fff;cursor:pointer",
        "roomRadio": "position:absolute;top:16px;right:16px;accent-color:#14532d",
        "roomMedia": "display:block;margin-bottom:6px",
        "roomName": "font-size:19px",
        "roomMeta": "font-family:system-ui;font-size:13px;color:#57534e",
        "roomPrice": "font-size:20px;margin-top:auto",
        "roomPer": "font-family:system-ui;font-size:13px;color:#78716c",
        "rates": "display:flex;flex-direction:column;gap:8px;margin-top:16px;font-family:system-ui;font-size:14px",
        "extras": "display:flex;flex-direction:column;gap:8px;margin-bottom:16px;font-family:system-ui;font-size:14px",
        "check": "display:flex;align-items:center;gap:8px",
        "consent": "display:flex;align-items:center;gap:8px;margin-top:16px;font-family:system-ui;font-size:14px",
        "summary": "position:sticky;top:96px;padding:24px;background-color:#fff;border:1px solid #e7e0d4",
        "sumTitle": "font-size:22px;font-weight:400;margin:0 0 12px",
        "sumRow": "display:flex;justify-content:space-between;gap:12px;padding-block:6px;font-family:system-ui;font-size:14px",
        "sumTotal": "display:flex;justify-content:space-between;padding-block:14px;margin-top:8px;border-top:1px solid #e7e0d4;font-size:20px",
        "sumAmount": "font-weight:600;font-variant-numeric:tabular-nums",
        "primaryBtn": "display:block;width:100%;padding:14px 20px;border:0;border-radius:2px;background-color:#14532d;color:#fff;font-family:system-ui;font-weight:600;font-size:15px;cursor:pointer",
        "note": "margin:8px 0 0;font-family:system-ui;font-size:13px;color:#57534e;text-align:center",
        "footer": "margin-top:64px;padding-block:48px;background-color:#1c1917;color:#e7e5e4;font-family:system-ui;font-size:14px",
        "footerGrid": "display:grid;gap:32px;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));max-width:1200px;margin-inline:auto;padding-inline:24px",
        "footerHeading": "font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:#a8a29e;margin:0 0 12px",
        "footerList": "list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:6px",
        "footerLink": "color:#e7e5e4;text-decoration:none",
        "mobileBar": "position:fixed;inset-inline:0;bottom:0;display:flex;align-items:center;justify-content:space-between;padding:12px 16px;background-color:#fff;border-top:1px solid #e7e0d4;@media (min-width:960px){display:none}",
        "mobileBarLabel": "font-family:system-ui;font-size:12px;color:#78716c",
        "mobileBarAmount": "font-weight:600;font-variant-numeric:tabular-nums",
        "mobileBarBtn": "padding:12px 20px;border:0;border-radius:2px;background-color:#14532d;color:#fff;font-family:system-ui;font-weight:600;cursor:pointer",
    }
    date_css = (":host{display:block}.range{display:flex;align-items:flex-end;gap:12px;flex-wrap:wrap}.field{display:flex;"
                "flex-direction:column;gap:6px}.label{font:600 14px system-ui}.input{font:16px system-ui;padding:12px;"
                "border:1px solid #d6d3d1;border-radius:4px;background:#fff}.arrow{padding-bottom:12px;color:#78716c}"
                ".nights{margin:0 0 12px;font:14px system-ui;color:#57534e}")

    def guest_row(key: str, label: str, hint: str, value: int, lo: int, mark: str = "") -> str:
        return f'''<div class="~guestRow">
            <div><p class="~guestLabel" id="g-{key}">{label}</p><p class="~guestHint">{hint}</p></div>
            <div class="~stepper" role="group" aria-labelledby="g-{key}">
              <button type="button" class="~stepperBtn" aria-label="Decrease {key}"{" disabled" if value <= lo else ""}>{icon("minus", size=16)}</button>
              <output class="~stepperValue" aria-live="polite">{value}</output>
              <button type="button" class="~stepperBtn" aria-label="Increase {key}"{mark}>{icon("plus", size=16)}</button>
            </div>
            <input type="hidden" name="guests.{key}" value="{value}">
          </div>'''

    v2_rooms = "\n".join(
        f'''<label class="~roomCard" for="rt-{slug}">
            <input type="radio" class="~roomRadio" id="rt-{slug}" name="roomType" value="{slug}"{" checked" if code == "JRS" else ""}{T("t3") if code == "JRS" else ""}>
            <span class="~roomMedia">{bed(col)}</span>
            <span class="~roomName">{name}</span>
            <span class="~roomMeta">{size} &middot; {sleeps} &middot; {view}</span>
            <span class="~roomPrice">{price} <span class="~roomPer">/ night</span></span>
          </label>''' for code, slug, name, desc, size, sleeps, view, price, col in [rooms[3], rooms[2], rooms[1], rooms[0]])
    v2_body = f"""
<div id="root">
<header class="~header">
  <div class="~headerInner">
    <a class="~brand" href="/">{crest}<span class="~brandName">The Linden</span></a>
    <nav class="~nav" aria-label="Primary">
      <ul class="~navList">
{links([nav[0], nav[3], nav[1], nav[2], nav[5], nav[4], nav[6]], ' class="~navItem"', ' class="~navLink"')}
      </ul>
    </nav>
    <a class="~headerCta" href="/book">Book a room</a>
  </div>
</header>
<div class="~banner" role="note">Book direct: save 10% with code DIRECT10 and enjoy free late checkout</div>
<main class="~main">
  <nav class="~steps" aria-label="Booking progress">
    <ol class="~stepsList">
      <li class="~step ~stepCurrent" aria-current="step">Your stay</li>
      <li class="~step">Payment</li>
      <li class="~step">Confirmed</li>
    </ol>
  </nav>
  <h1 class="~title">Reserve your room</h1>
  <div class="~layout">
    <form id="reservation" class="~form" action="/api/reservations" method="post">
      <input type="hidden" name="propertyId" value="LDN-EDI">
      <section class="~section" aria-labelledby="s-dates">
        <h2 id="s-dates" class="~sectionTitle">When are you staying?</h2>
        <lh-date-range class="~dateRange" nights="4" locale="en-GB">
          <template shadowrootmode="open">
            <style>{date_css}</style>
            <div class="range" part="range">
              <div class="field"><label class="label" for="start">Arrive</label><input id="start" class="input" type="date" name="checkIn" value="2026-12-18" min="2026-11-05" required{T("t1")}></div>
              <span class="arrow" aria-hidden="true">&rarr;</span>
              <div class="field"><label class="label" for="end">Depart</label><input id="end" class="input" type="date" name="checkOut" value="2026-12-22" min="2026-11-06" required></div>
              <p class="nights" aria-live="polite">4 nights</p>
            </div>
          </template>
        </lh-date-range>
      </section>
      <section class="~section" aria-labelledby="s-guests">
        <h2 id="s-guests" class="~sectionTitle">Who's coming?</h2>
        <div class="~guestList">
          {guest_row("adults", "Adults", "Ages 13 and over", 2, 1, T("t2"))}
          {guest_row("children", "Children", "Ages 2 to 12", 0, 0)}
          {guest_row("infants", "Infants", "Under 2, cots on request", 0, 0)}
        </div>
        <div class="~row">
          <div class="~field">
            <label class="~label" for="rooms-count">Rooms</label>
            <select id="rooms-count" class="~input" name="rooms">{opts(["1", "2", "3", "4"], "1")}</select>
          </div>
        </div>
        <details class="~details">
          <summary>Have a promo or corporate code?</summary>
          <input type="text" class="~input" name="promoCode" aria-label="Promo or corporate code" autocomplete="off">
        </details>
      </section>
      <section class="~section" aria-labelledby="s-room">
        <h2 id="s-room" class="~sectionTitle">Choose your room</h2>
        <div class="~roomGrid" role="radiogroup" aria-labelledby="s-room">
{v2_rooms}
        </div>
        <div class="~rates" role="radiogroup" aria-label="Rate">
          <label class="~check"><input type="radio" name="ratePlan" value="advance"> Advance purchase: non-refundable, save 15%</label>
          <label class="~check"><input type="radio" name="ratePlan" value="flex" checked> Flexible: free cancellation until 48 hours before arrival</label>
        </div>
      </section>
      <section class="~section" aria-labelledby="s-special">
        <h2 id="s-special" class="~sectionTitle">Make it special</h2>
        <div class="~extras">
          <label class="~check"><input type="checkbox" name="extras" value="early-checkin"> Early check-in from 11:00 (&pound;25)</label>
          <label class="~check"><input type="checkbox" name="extras" value="champagne"> Champagne on arrival (&pound;65)</label>
          <label class="~check"><input type="checkbox" name="extras" value="parking"> Parking (&pound;20 per night)</label>
        </div>
        <div class="~field">
          <label class="~label" for="requests">Anything else we should know?</label>
          <textarea id="requests" class="~textarea" name="special_requests" rows="4" placeholder="Celebrating something? Need a cot or extra pillows? Tell us here."{T("t4")}></textarea>
          <p class="~hint">We'll do our best, but requests depend on availability.</p>
        </div>
      </section>
      <section class="~section" aria-labelledby="s-guest">
        <h2 id="s-guest" class="~sectionTitle">Lead guest</h2>
        <div class="~row">
          <div class="~field"><label class="~label" for="g-first">First name</label><input id="g-first" class="~input" name="guest.firstName" autocomplete="given-name" value="Aisha" required></div>
          <div class="~field"><label class="~label" for="g-last">Last name</label><input id="g-last" class="~input" name="guest.lastName" autocomplete="family-name" value="Rahman" required></div>
        </div>
        <div class="~row">
          <div class="~field"><label class="~label" for="g-email">Email</label><input id="g-email" class="~input" type="email" name="guest.email" autocomplete="email" value="aisha.rahman@outlook.com" required></div>
          <div class="~field"><label class="~label" for="g-phone">Mobile</label><input id="g-phone" class="~input" type="tel" name="guest.phone" autocomplete="tel" value="+44 7700 900461"></div>
          <div class="~field"><label class="~label" for="g-arrival">Arriving around</label><select id="g-arrival" class="~input" name="guest.arrivalTime">{opts(arrivals, "15:00 – 18:00")}</select></div>
        </div>
        <label class="~consent"><input type="checkbox" name="acceptPolicy" required> I agree to the <a href="/policies">booking and cancellation policy</a></label>
      </section>
    </form>
    <aside class="~summary" aria-labelledby="sum-title">
      <h2 id="sum-title" class="~sumTitle">Your stay</h2>
      <div class="~sumRow"><span>Fri 18 Dec &rarr; Tue 22 Dec</span><span>4 nights</span></div>
      <div class="~sumRow"><span>Guests</span><span>2 adults</span></div>
      <div class="~sumRow"><span>Junior Suite &middot; Flexible</span><span>&pound;1,156.00</span></div>
      <div class="~sumRow"><span>Visitor levy (5%)</span><span>&pound;57.80</span></div>
      <div class="~sumTotal"><span>Total</span><span class="~sumAmount"{T("t6")}>&pound;1,213.80</span></div>
      <button type="submit" form="reservation" class="~primaryBtn"{T("t5")}>Reserve</button>
      <p class="~note">You won't be charged yet.</p>
    </aside>
  </div>
</main>
<footer class="~footer">
  <div class="~footerGrid">
    <div>
      <h2 class="~footerHeading">Information</h2>
      <ul class="~footerList">
{links(info, "", ' class="~footerLink"')}
      </ul>
    </div>
    <div>
      <h2 class="~footerHeading">Explore</h2>
      <ul class="~footerList">
{links(explore, "", ' class="~footerLink"')}
      </ul>
    </div>
    <div>
      <h2 class="~footerHeading">Visit us</h2>
      <address>14 Royal Terrace, Edinburgh EH7 5AB</address>
      <p><a class="~footerLink" href="tel:+441315550192">+44 131 555 0192</a></p>
    </div>
    <div>
      <h2 class="~footerHeading">Legal</h2>
      <ul class="~footerList">
{links(legal, "", ' class="~footerLink"')}
      </ul>
    </div>
  </div>
</footer>
<div class="~mobileBar" role="region" aria-label="Booking total">
  <div><span class="~mobileBarLabel">Total for 4 nights</span><br><span class="~mobileBarAmount">&pound;1,213.80</span></div>
  <button type="submit" form="reservation" class="~mobileBarBtn">Reserve</button>
</div>
</div>
"""
    v2 = document(
        title="Reserve | The Linden, Edinburgh",
        head="""<meta name="description" content="Reserve a room at The Linden, Royal Terrace, Edinburgh.">
<link rel="icon" href="/favicon.ico">""",
        body=expand_classes(v2_body, stylex(S)),
        lang="en-GB",
        body_attrs=f' class="{stylex(S)("body")}"',
    )

    m = meta(
        "form-08",
        "Hotel booking form: dates, guest steppers, room type, special requests — The Linden Hotel",
        ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change", "copy-change",
         "attribute-churn", "structure-move", "insertion", "tag-change"],
        "v1 is a hand-written BEM booking page (date inputs with arrival_date/departure_date, +/- steppers labelled "
        "'Add adult', <article> room cards with radios, a <dl> price summary). v2 is a React rebuild with StyleX atomic "
        "classes (x1abc23d ...): the dates move into an <lh-date-range> declarative shadow root (labels 'Arrive'/'Depart', "
        "names checkIn/checkOut), guests become a list of rows with 'Increase adults'/'Decrease adults' icon buttons "
        "(Infants added), room cards become whole-card <label>s sorted by price descending with slug values, special "
        "requests move up into a new 'Make it special' section, and the summary becomes div rows. Decoys: identical "
        "icon-only stepper buttons for children and infants, a sticky mobile bar repeating the £1,213.80 total and a "
        "second 'Reserve' button, a header 'Book a room' link.",
        [
            target("t1", "Check-in date input",
                   "#checkin", "//input[@name='arrival_date']",
                   ["shadow-dom", "class-obfuscation", "id-change", "attribute-churn", "copy-change", "wrapper-divs"]),
            target("t2", "Icon-only '+' button that adds an adult guest",
                   ".stepper--adults .stepper__btn--plus", "//button[@aria-label='Add adult']",
                   ["class-obfuscation", "attribute-churn", "copy-change", "wrapper-divs", "decoy", "insertion"]),
            target("t3", "'Junior Suite' room-type radio button",
                   "input[name='room_type'][value='JRS']",
                   "//h3[text()='Junior Suite']/ancestor::article//input[@type='radio']",
                   ["class-obfuscation", "id-change", "attribute-churn", "sibling-reorder", "tag-change", "wrapper-divs"]),
            target("t4", "Special requests textarea",
                   "textarea#special-requests", "//textarea[@name='special_requests']",
                   ["class-obfuscation", "id-change", "copy-change", "structure-move", "sibling-reorder"]),
            target("t5", "'Book now' submit button in the stay summary",
                   ".booking-summary button[type='submit']", "//aside//button[normalize-space()='Book now']",
                   ["class-obfuscation", "copy-change", "decoy"]),
            target("t6", "Total price (£1,213.80) in the stay summary",
                   ".booking-summary .summary-total dd", "//dt[text()='Total']/following-sibling::dd",
                   ["class-obfuscation", "tag-change", "structure-move", "decoy"]),
        ],
    )
    return v1, v2, m


# ======================================================================================
# form-09 - Shieldline auto insurance: quote wizard, step 2 of 4 (vehicle)
# ======================================================================================
def ng(markup: str, cid: str) -> str:
    """Add Angular's emulated-encapsulation attribute to every start tag of ``markup``."""
    return re.sub(r"<([a-z][a-z0-9-]*)(?=[\s>/])", lambda m: f'<{m.group(1)} _ngcontent-ng-c{cid}=""', markup)


@suite("form-09")
def form09():
    years = [str(y) for y in range(2027, 2004, -1)]
    makes = ["Acura", "Audi", "BMW", "Chevrolet", "Ford", "GMC", "Honda", "Hyundai", "Jeep", "Kia", "Mazda", "Mercedes-Benz",
             "Nissan", "Ram", "Subaru", "Tesla", "Toyota", "Volkswagen", "Volvo"]
    models = ["Ascent", "BRZ", "Crosstrek", "Forester", "Impreza", "Legacy", "Outback", "Solterra", "WRX"]
    trims = ["Base", "Premium", "Limited", "Touring", "Onyx Edition", "Wilderness"]
    uses = [("commute", "Commuting to work or school"), ("pleasure", "Pleasure / personal errands"), ("business", "Business"),
            ("rideshare", "Rideshare or delivery")]
    steps = [("About you", "/auto/about-you"), ("Vehicle", None), ("Drivers", None), ("Coverage", None)]
    legal = [("Privacy", "https://www.shieldline.com/privacy"), ("Terms of use", "https://www.shieldline.com/terms"),
             ("Licenses", "https://www.shieldline.com/licenses"), ("Accessibility", "https://www.shieldline.com/accessibility"),
             ("Do not sell or share my personal information", "https://www.shieldline.com/privacy/choices")]
    shield = ('<svg width="30" height="34" viewBox="0 0 30 34" aria-hidden="true"><path d="M15 1 2 6v9c0 9 6 15 13 18 7-3 13-9 '
              '13-18V6z" fill="#1d4ed8"/><path d="m9 17 4 4 8-9" stroke="#fff" stroke-width="2.5" fill="none"/></svg>')
    disclaimer = ("Shieldline Insurance Company and its affiliates. Coverage is subject to the terms, conditions and exclusions of "
                  "the policy. Discounts and features are not available in all states. Your price may change after we verify "
                  "your driving and claims history.")

    # ---------------------------------------------------------------- v1: Bootstrap 4 + <sl-progress-tracker> (shadow DOM)
    v1_css = """
  body { font-family: "Open Sans", Arial, sans-serif; background: #f8fafc; color: #0f172a; }
  .quote-header { background: #fff; border-bottom: 1px solid #e2e8f0; padding: 12px 0; }
  .quote-progress { display: block; background: #fff; border-bottom: 1px solid #e2e8f0; }
  .quote-form { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 32px; }
  .divider-text { text-align: center; color: #64748b; margin: 16px 0; }
  .ownership-option { display: inline-block; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 16px; margin-right: 8px; }
  .quote-actions { display: flex; justify-content: space-between; border-top: 1px solid #e2e8f0; margin-top: 24px; padding-top: 24px; }
  .quote-footer { font-size: 12px; color: #64748b; margin-top: 48px; padding: 24px 0; }
"""
    tracker_css = (":host{display:block}nav{max-width:960px;margin:0 auto;padding:12px 16px}.steps{display:flex;gap:8px;"
                   "list-style:none;margin:0;padding:0}.step{flex:1;display:flex;align-items:center;gap:8px;color:#64748b;"
                   "font:14px system-ui}.step__num{display:grid;place-items:center;width:24px;height:24px;border-radius:50%;"
                   "border:2px solid currentColor}.is-current{color:#1d4ed8;font-weight:600}.is-complete{color:#15803d}"
                   ".steps__summary{margin:4px 0 0;font:12px system-ui;color:#64748b}")
    v1_steps = "\n".join(
        (f'          <li class="step is-complete"><a class="step__link" href="{href}"><span class="step__num">{i}</span> <span class="step__label">{name}</span></a></li>'
         if href else
         f'          <li class="step{" is-current" if i == 2 else ""}"{" aria-current=" + chr(34) + "step" + chr(34) if i == 2 else ""}{T("t1") if i == 2 else ""}><span class="step__num">{i}</span> <span class="step__label">{name}</span></li>')
        for i, (name, href) in enumerate(steps, 1))
    v1_body = f"""
<header class="quote-header">
  <div class="container d-flex align-items-center justify-content-between">
    <a class="quote-header__logo" href="https://www.shieldline.com">{shield}<span class="quote-header__brand">Shieldline</span><span class="sr-only">Shieldline home</span></a>
    <span class="quote-header__product">Auto insurance quote</span>
    <div class="quote-header__help">Questions? <a href="tel:18005550147">1-800-555-0147</a></div>
    <a class="quote-header__save" href="/auto/save?quote=Q-88213574">Save &amp; finish later</a>
  </div>
</header>
<sl-progress-tracker class="quote-progress" current="2" total="4">
  <template shadowrootmode="open">
    <style>{tracker_css}</style>
    <nav aria-label="Quote progress">
      <ol class="steps">
{v1_steps}
      </ol>
      <p class="steps__summary">Step 2 of 4</p>
    </nav>
  </template>
</sl-progress-tracker>
<main class="container quote-main py-4">
  <div class="row">
    <div class="col-md-8">
      <form id="vehicle-form" class="quote-form" action="/auto/vehicle" method="post" novalidate>
        <input type="hidden" name="quote_id" value="Q-88213574">
        <input type="hidden" name="_csrf" value="9b2e6f1c-0d4a-47b3-8e5f-2c1a7d9e4b60">
        <h1 class="quote-form__title h3">Tell us about your vehicle</h1>
        <p class="quote-form__lead">Adding your VIN gets you the most accurate price. Don't have it handy? Enter the year, make and model instead.</p>
        <div class="vin-lookup card mb-3">
          <div class="card-body">
            <label for="vin" class="form-label">Vehicle Identification Number (VIN) <span class="text-muted">(optional)</span></label>
            <div class="input-group">
              <input type="text" id="vin" name="vehicle[vin]" class="form-control text-uppercase" maxlength="17" placeholder="17 characters, e.g. 4S4BTGND5R3123456" autocomplete="off" spellcheck="false"{T("t3")}>
              <div class="input-group-append"><button type="button" class="btn btn-outline-primary" id="vin-lookup-btn">Look up</button></div>
            </div>
            <small class="form-text"><a class="vin-help" href="/help/find-your-vin">Where do I find my VIN?</a></small>
          </div>
        </div>
        <div class="divider-text">or</div>
        <div class="form-row">
          <div class="form-group col-sm-4">
            <label for="vehicle-year">Year</label>
            <select id="vehicle-year" name="vehicle[year]" class="form-control custom-select">{opts(years, "2025")}</select>
          </div>
          <div class="form-group col-sm-4">
            <label for="vehicle-make">Make</label>
            <select id="vehicle-make" name="vehicle[make]" class="form-control custom-select"{T("t2")}>{opts(makes, "Subaru")}</select>
          </div>
          <div class="form-group col-sm-4">
            <label for="vehicle-model">Model</label>
            <select id="vehicle-model" name="vehicle[model]" class="form-control custom-select">{opts(models, "Outback")}</select>
          </div>
          <div class="form-group col-sm-6">
            <label for="vehicle-trim">Trim</label>
            <select id="vehicle-trim" name="vehicle[trim]" class="form-control custom-select">{opts(trims, "Premium")}</select>
          </div>
        </div>
        <fieldset class="form-group quote-fieldset">
          <legend class="col-form-label">Do you own, finance or lease this vehicle?</legend>
          <div class="ownership-options">
            <label class="ownership-option"><input type="radio" name="vehicle[ownership]" value="owned"> Owned</label>
            <label class="ownership-option"><input type="radio" name="vehicle[ownership]" value="financed" checked{T("t4")}> Financed</label>
            <label class="ownership-option"><input type="radio" name="vehicle[ownership]" value="leased"> Leased</label>
          </div>
        </fieldset>
        <div class="form-row">
          <div class="form-group col-sm-6">
            <label for="primary-use">Primary use</label>
            <select id="primary-use" name="vehicle[primary_use]" class="form-control custom-select">{opts(uses, "commute")}</select>
          </div>
          <div class="form-group col-sm-6">
            <label for="annual-miles">Annual mileage</label>
            <input type="number" id="annual-miles" name="vehicle[annual_miles]" class="form-control" value="12000" min="0" step="500">
            <small class="form-text text-muted">The U.S. average is about 13,500 miles a year.</small>
          </div>
          <div class="form-group col-sm-6">
            <label for="garage-zip">ZIP code where it's parked overnight</label>
            <input type="text" id="garage-zip" name="vehicle[garaging_zip]" class="form-control" value="43215" inputmode="numeric" maxlength="5">
          </div>
        </div>
        <div class="form-check mb-3">
          <input class="form-check-input" type="checkbox" id="anti-theft" name="vehicle[anti_theft]" value="1" checked>
          <label class="form-check-label" for="anti-theft">This vehicle has an anti-theft device or tracking system</label>
        </div>
        <a class="add-vehicle-link" href="/auto/vehicle/new">+ Add another vehicle</a>
        <div class="quote-actions">
          <a class="btn btn-link btn-back" href="/auto/about-you"{T("t6")}>Back</a>
          <button type="submit" class="btn btn-primary btn-next"{T("t5")}>Next</button>
        </div>
      </form>
    </div>
    <aside class="col-md-4">
      <div class="quote-summary card mb-3">
        <div class="card-header">Your quote so far</div>
        <ul class="list-group list-group-flush">
          <li class="list-group-item d-flex justify-content-between"><span>Driver</span><strong>Jordan Alvarez</strong></li>
          <li class="list-group-item d-flex justify-content-between"><span>ZIP code</span><strong>43215</strong></li>
          <li class="list-group-item d-flex justify-content-between"><span>Quote ID</span><strong>Q-88213574</strong></li>
        </ul>
      </div>
      <div class="help-card card mb-3">
        <div class="card-body">
          <h2 class="h6">Need a hand?</h2>
          <p class="small">Licensed agents are available Mon&ndash;Fri 8 am&ndash;9 pm ET and Sat 9 am&ndash;5 pm ET.</p>
          <a href="tel:18005550147" class="btn btn-outline-secondary btn-sm">Call 1-800-555-0147</a>
          <a href="/chat" class="btn btn-link btn-sm">Chat with an agent</a>
        </div>
      </div>
      <div class="discounts-card card">
        <div class="card-body">
          <h2 class="h6">Discounts you may qualify for</h2>
          <ul class="small mb-0"><li>Multi-policy (bundle home and auto)</li><li>Safe driver</li><li>Anti-theft device</li><li>Paperless billing</li></ul>
        </div>
      </div>
    </aside>
  </div>
</main>
<footer class="quote-footer">
  <div class="container">
    <p class="small">{disclaimer}</p>
    <ul class="list-inline">
{links(legal, ' class="list-inline-item"')}
    </ul>
    <p class="small">&copy; 2026 Shieldline Insurance Group</p>
  </div>
</footer>
"""
    v1 = document(
        title="Vehicle details | Auto quote | Shieldline Insurance",
        head=f"""<meta name="description" content="Get an auto insurance quote from Shieldline in minutes.">
<style>{v1_css}</style>""",
        body=v1_body,
    )

    # ---------------------------------------------------------------- v2: Angular 17 + Angular Material (MDC)
    TNS = "3736059725"
    sel_n = iter(range(2, 40))

    def mat_select(label: str, value_text: str, mark: str = "") -> str:
        n = next(sel_n)
        t = f"ng-tns-c{TNS}-{n}"
        s = f"ng-tns-c2179845426-{n + 20}"
        return f'''<mat-form-field appearance="outline" class="mat-mdc-form-field sl-field mat-mdc-form-field-type-mat-select mat-form-field-appearance-outline mat-primary {t} ng-star-inserted">
          <div class="mat-mdc-text-field-wrapper mdc-text-field mdc-text-field--outlined {t}">
            <div class="mat-mdc-form-field-flex {t}">
              <div class="mdc-notched-outline mdc-notched-outline--upgraded mdc-notched-outline--notched {t} ng-star-inserted"><div class="mdc-notched-outline__leading"></div><div class="mdc-notched-outline__notch"><label class="mdc-floating-label mat-mdc-floating-label mdc-floating-label--float-above {t} ng-star-inserted" id="mat-mdc-form-field-label-{n * 2}" for="mat-select-{n}"><mat-label class="{t}">{label}</mat-label><span aria-hidden="true" class="mat-mdc-form-field-required-marker mdc-floating-label--required {t} ng-star-inserted"></span></label></div><div class="mdc-notched-outline__trailing"></div></div>
              <div class="mat-mdc-form-field-infix {t}">
                <mat-select role="combobox" aria-haspopup="listbox" id="mat-select-{n}" tabindex="0" aria-expanded="false" aria-labelledby="mat-mdc-form-field-label-{n * 2} mat-select-value-{n}" aria-required="true" aria-disabled="false" aria-invalid="false" class="mat-mdc-select {s} {t} ng-untouched ng-pristine ng-valid ng-star-inserted"{mark}>
                  <div cdk-overlay-origin class="mat-mdc-select-trigger {s}"><div class="mat-mdc-select-value {s}" id="mat-select-value-{n}"><span class="mat-mdc-select-value-text {s} ng-star-inserted"><span class="mat-mdc-select-min-line {s} ng-star-inserted">{value_text}</span></span></div><div class="mat-mdc-select-arrow-wrapper {s}"><div class="mat-mdc-select-arrow {s}"><svg viewBox="0 0 24 24" width="24px" height="24px" focusable="false" aria-hidden="true"><path d="M7 10l5 5 5-5z"></path></svg></div></div></div>
                </mat-select>
              </div>
            </div>
          </div>
          <div class="mat-mdc-form-field-subscript-wrapper mat-mdc-form-field-bottom-align {t}"><div class="mat-mdc-form-field-hint-wrapper {t} ng-star-inserted"><div class="mat-mdc-form-field-hint-spacer {t}"></div></div></div>
        </mat-form-field>'''

    def mat_input(label: str, name: str, value: str, extra: str = "", hint: str = "") -> str:
        n = next(sel_n)
        t = f"ng-tns-c{TNS}-{n}"
        hint_html = (f'<mat-hint class="mat-mdc-form-field-hint mat-mdc-form-field-bottom-align {t}" id="mat-mdc-hint-{n}">{hint}</mat-hint>'
                     if hint else "")
        return f'''<mat-form-field appearance="outline" class="mat-mdc-form-field sl-field mat-mdc-form-field-type-mat-input mat-form-field-appearance-outline mat-primary {t} ng-star-inserted">
          <div class="mat-mdc-text-field-wrapper mdc-text-field mdc-text-field--outlined {t}">
            <div class="mat-mdc-form-field-flex {t}">
              <div class="mdc-notched-outline mdc-notched-outline--upgraded mdc-notched-outline--notched {t} ng-star-inserted"><div class="mdc-notched-outline__leading"></div><div class="mdc-notched-outline__notch"><label class="mdc-floating-label mat-mdc-floating-label mdc-floating-label--float-above {t} ng-star-inserted" id="mat-mdc-form-field-label-{n * 2}" for="mat-input-{n}"><mat-label class="{t}">{label}</mat-label></label></div><div class="mdc-notched-outline__trailing"></div></div>
              <div class="mat-mdc-form-field-infix {t}"><input matinput id="mat-input-{n}" name="{name}" value="{value}" class="mat-mdc-input-element mat-mdc-form-field-input-control mdc-text-field__input {t} ng-untouched ng-pristine ng-valid cdk-text-field-autofill-monitored" aria-invalid="false" aria-required="false"{extra}{f' aria-describedby="mat-mdc-hint-{n}"' if hint else ""}></div>
            </div>
          </div>
          <div class="mat-mdc-form-field-subscript-wrapper mat-mdc-form-field-bottom-align {t}"><div class="mat-mdc-form-field-hint-wrapper {t} ng-star-inserted">{hint_html}<div class="mat-mdc-form-field-hint-spacer {t}"></div></div></div>
        </mat-form-field>'''

    def mat_radio(n: int, value: str, label: str, checked: bool = False, mark: str = "") -> str:
        return f'''<mat-radio-button class="mat-mdc-radio-button sl-option mat-accent{" mat-mdc-radio-checked" if checked else ""}" id="mat-radio-{n}">
            <div class="mdc-form-field mat-internal-form-field">
              <div class="mdc-radio">
                <div class="mat-mdc-radio-touch-target"></div>
                <input type="radio" class="mdc-radio__native-control" id="mat-radio-{n}-input" name="ownership" value="{value}" tabindex="{0 if checked else -1}"{" checked" if checked else ""}{mark}>
                <div class="mdc-radio__background"><div class="mdc-radio__outer-circle"></div><div class="mdc-radio__inner-circle"></div></div>
                <div mat-ripple class="mat-ripple mat-radio-ripple mat-mdc-focus-indicator"><div class="mat-ripple-element mat-radio-persistent-ripple"></div></div>
              </div>
              <label class="mdc-label" for="mat-radio-{n}-input">{label}</label>
            </div>
          </mat-radio-button>'''

    def mat_button(kind: str, text: str, extra_cls: str, attrs: str) -> str:
        variants = {"stroked": "mdc-button--outlined mat-mdc-outlined-button mat-unthemed",
                    "flat": "mdc-button--unelevated mat-mdc-unelevated-button mat-primary"}
        return (f'<button mat-{kind}-button class="mdc-button {variants[kind]} mat-mdc-button-base {extra_cls}"{attrs}>'
                f'<span class="mat-mdc-button-persistent-ripple mdc-button__ripple"></span><span class="mdc-button__label">{text}</span>'
                f'<span class="mat-mdc-focus-indicator"></span><span class="mat-mdc-button-touch-target"></span></button>')

    def step_li(i: int, name: str, state: str, mark: str = "") -> str:
        icon_cls = {"done": "mat-step-icon-state-done", "active": "mat-step-icon-state-number mat-step-icon-selected",
                    "todo": "mat-step-icon-state-number"}[state]
        content = "&#10003;" if state == "done" else str(i)
        cur = ' aria-current="step"' if state == "active" else ""
        return (f'<li class="mat-step-header sl-step sl-step--{state}"{cur}{mark}><span class="mat-step-icon {icon_cls}">'
                f'<span class="mat-step-icon-content">{content}</span></span>\n<span class="mat-step-label{" mat-step-label-active" if state != "todo" else ""}">{name}</span></li>')

    v2_steps = [("About you", "done"), ("Your vehicle", "active"), ("Drivers", "todo"), ("Coverage", "todo")]
    stepper = "\n".join(step_li(i, n, s, T("t1") if s == "active" else "") for i, (n, s) in enumerate(v2_steps, 1))
    compact = "\n".join(step_li(i, n, s) for i, (n, s) in enumerate(v2_steps, 1))
    vin_css = (":host{display:block;margin-bottom:24px}.vin{border:1px solid #c7d2fe;border-radius:12px;background:#eef2ff;"
               "padding:16px}.vin__label{display:block;font:600 14px Roboto,sans-serif;margin-bottom:8px}.vin__row{display:flex;"
               "gap:8px}.vin__input{flex:1;font:16px 'Roboto Mono',monospace;text-transform:uppercase;padding:12px;border:1px "
               "solid #94a3b8;border-radius:4px}.vin__btn{border:0;border-radius:20px;background:#1d4ed8;color:#fff;padding:0 18px;"
               "font:500 14px Roboto,sans-serif}.vin__hint{margin:8px 0 0;font:13px Roboto,sans-serif;color:#475569}")
    header = ng(f"""<header class="sl-header">
    <a class="sl-header__brand" href="https://www.shieldline.com" aria-label="Shieldline home">{shield}<span class="sl-header__name">Shieldline</span></a>
    <span class="sl-header__product">Auto quote &middot; Q-88213574</span>
    <span class="sl-spacer"></span>
    <a class="sl-header__phone" href="tel:18005550147">{icon("phone", size=16)} 1-800-555-0147</a>
    {mat_button("stroked", "Save and exit", "sl-header__save", ' type="button"')}
  </header>""", "1180297423")
    progress = ng(f"""<nav class="sl-stepper" aria-label="Quote progress">
      <ol class="sl-stepper__list">
{stepper}
      </ol>
    </nav>
    <div class="sl-progress-compact sl-hide-gt-sm" aria-hidden="true">
      <p class="sl-progress-compact__label">Step 2 of 4</p>
      <ol class="sl-progress-compact__list">
{compact}
      </ol>
    </div>""", "2876493017")
    form_top = ng("""<h1 class="sl-title mat-headline-small">Your vehicle</h1>
        <p class="sl-lead mat-body-large">Have your VIN handy? We'll use it to look up safety features that can lower your price.</p>""", "2876493017")
    form_rest = ng(f"""<p class="sl-or"><span>or tell us about it</span></p>
        <div class="sl-grid">
          {mat_select("Make", "Subaru", T("t2"))}
          {mat_select("Model", "Outback")}
          {mat_select("Year", "2025")}
          {mat_select("Trim", "Premium")}
        </div>
        <div class="sl-question">
          <p class="sl-question__label" id="ownership-label">Is this car financed, leased or owned outright?</p>
          <mat-radio-group role="radiogroup" aria-labelledby="ownership-label" class="mat-mdc-radio-group sl-ownership ng-untouched ng-pristine ng-valid">
          {mat_radio(3, "financed", "Financed (car loan)", True, T("t4"))}
          {mat_radio(4, "leased", "Leased")}
          {mat_radio(5, "owned", "Owned outright")}
          </mat-radio-group>
        </div>
        <div class="sl-grid">
          {mat_select("How is it mostly used?", "Commuting to work or school")}
          {mat_input("Miles driven per year", "annualMileage", "12000", ' type="number" min="0" step="500"', "U.S. average: about 13,500")}
          {mat_input("Overnight parking ZIP", "garagingZip", "43215", ' inputmode="numeric" maxlength="5"')}
        </div>
        <mat-checkbox class="mat-mdc-checkbox sl-check mat-accent mat-mdc-checkbox-checked" id="mat-mdc-checkbox-1">
          <div class="mdc-form-field mat-internal-form-field"><div class="mdc-checkbox"><input type="checkbox" class="mdc-checkbox__native-control" id="mat-mdc-checkbox-1-input" name="antiTheft" checked><div class="mdc-checkbox__background"></div></div><label class="mdc-label" for="mat-mdc-checkbox-1-input">Anti-theft device or tracking system installed</label></div>
        </mat-checkbox>
        <mat-slide-toggle class="mat-mdc-slide-toggle sl-check mat-accent" id="mat-mdc-slide-toggle-1">
          <div class="mdc-form-field mat-internal-form-field"><button role="switch" type="button" class="mdc-switch mdc-switch--unselected" id="mat-mdc-slide-toggle-1-button" aria-checked="false"><span class="mdc-switch__track"></span><span class="mdc-switch__handle-track"><span class="mdc-switch__handle"></span></span></button><label class="mdc-label" for="mat-mdc-slide-toggle-1-button">I drive for a rideshare or delivery service</label></div>
        </mat-slide-toggle>
        <a class="sl-add-vehicle" href="/auto/vehicles/new">{icon("plus", size=16)} Add another vehicle</a>
        <div class="sl-actions">
          {mat_button("stroked", "Back", "sl-back", ' type="button"' + T("t6"))}
          {mat_button("flat", "Continue", "sl-continue", ' type="submit"' + T("t5"))}
        </div>""", "2876493017")
    aside = ng(f"""<aside class="sl-aside">
      <mat-card class="mat-mdc-card mdc-card mat-mdc-card-outlined mdc-card--outlined sl-summary">
        <mat-card-header class="mat-mdc-card-header"><div class="mat-mdc-card-header-text"><mat-card-title class="mat-mdc-card-title">Quote summary</mat-card-title></div></mat-card-header>
        <mat-card-content class="mat-mdc-card-content">
          <dl class="sl-summary__list">
            <div class="sl-summary__row"><dt>Quote ID</dt><dd>Q-88213574</dd></div>
            <div class="sl-summary__row"><dt>Driver</dt><dd>Jordan Alvarez</dd></div>
            <div class="sl-summary__row"><dt>Garaging ZIP</dt><dd>43215</dd></div>
          </dl>
        </mat-card-content>
      </mat-card>
      <mat-card class="mat-mdc-card mdc-card mat-mdc-card-outlined mdc-card--outlined sl-discounts">
        <mat-card-content class="mat-mdc-card-content">
          <h2 class="mat-title-medium">You could save with</h2>
          <mat-chip-set class="mat-mdc-chip-set mdc-evolution-chip-set" role="presentation"><div role="presentation" class="mdc-evolution-chip-set__chips">
            <mat-chip class="mat-mdc-chip mat-mdc-standard-chip">Safe driver</mat-chip>
            <mat-chip class="mat-mdc-chip mat-mdc-standard-chip">Bundle home + auto</mat-chip>
            <mat-chip class="mat-mdc-chip mat-mdc-standard-chip">Anti-theft</mat-chip>
            <mat-chip class="mat-mdc-chip mat-mdc-standard-chip">Paperless</mat-chip>
          </div></mat-chip-set>
        </mat-card-content>
      </mat-card>
      <mat-card class="mat-mdc-card mdc-card mat-mdc-card-outlined mdc-card--outlined sl-help">
        <mat-card-content class="mat-mdc-card-content">
          <h2 class="mat-title-medium">Talk to a licensed agent</h2>
          <p class="mat-body-medium">Mon&ndash;Fri 8 am&ndash;9 pm ET, Sat 9 am&ndash;5 pm ET</p>
          <a class="sl-help__link" href="tel:18005550147">Call 1-800-555-0147</a>
          <a class="sl-help__link" href="/chat">Start a chat</a>
        </mat-card-content>
      </mat-card>
    </aside>""", "2876493017")
    mobile_bar = ng(f"""<div class="sl-mobile-actions sl-hide-gt-sm" role="region" aria-label="Quote navigation">
    {mat_button("stroked", "Back", "sl-back", ' type="button"')}
    {mat_button("flat", "Continue", "sl-continue", ' type="button"')}
  </div>""", "2876493017")
    footer = ng(f"""<footer class="sl-footer">
    <p class="sl-footer__legal">{disclaimer}</p>
    <ul class="sl-footer__links">
{links(legal[::-1], ' class="sl-footer__item"', ' class="sl-footer__link"')}
    </ul>
    <p class="sl-footer__copy">&copy; 2026 Shieldline Insurance Group</p>
  </footer>""", "1180297423")
    v2_body = f"""
<sl-root ng-version="17.3.12">
  <sl-header _nghost-ng-c1180297423="">
  {header}
  </sl-header>
  <router-outlet></router-outlet>
  <sl-vehicle-step _nghost-ng-c2876493017="" class="ng-star-inserted">
    {progress}
    <div _ngcontent-ng-c2876493017="" class="sl-layout">
      <form _ngcontent-ng-c2876493017="" novalidate class="sl-form ng-untouched ng-pristine ng-valid">
        {form_top}
        <sl-vin-lookup _ngcontent-ng-c2876493017="" class="sl-vin">
          <template shadowrootmode="open">
            <style>{vin_css}</style>
            <div class="vin" part="container">
              <label class="vin__label" for="vin">VIN</label>
              <div class="vin__row"><input id="vin" class="vin__input" name="vin" maxlength="17" autocomplete="off" spellcheck="false" placeholder="e.g. 4S4BTGND5R3123456"{T("t3")}><button type="button" class="vin__btn">Decode VIN</button></div>
              <p class="vin__hint">Find it on your registration, your insurance card or the driver-side dashboard.</p>
            </div>
          </template>
        </sl-vin-lookup>
        {form_rest}
      </form>
      {aside}
    </div>
    {mobile_bar}
  </sl-vehicle-step>
  {footer}
</sl-root>
"""
    v2 = document(
        title="Your vehicle – Shieldline Auto Quote",
        head="""<base href="/auto/">
<meta name="description" content="Shieldline auto insurance quote: vehicle details.">
<style ng-app-id="ng">.sl-hide-gt-sm{display:none}@media (max-width:959px){.sl-hide-gt-sm{display:block}}</style>""",
        body=v2_body,
        body_attrs=' class="mat-typography mat-app-background"',
    )

    m = meta(
        "form-09",
        "Auto insurance quote wizard, step 2 of 4: vehicle details — Shieldline",
        ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change", "copy-change",
         "attribute-churn", "structure-move", "insertion", "tag-change"],
        "v1 is a Bootstrap 4 wizard page whose step indicator lives inside an <sl-progress-tracker> declarative shadow "
        "root. v2 is an Angular 17 + Angular Material (MDC) rewrite: the step indicator moves out of the shadow root "
        "into a light-DOM mat-step-header list (step renamed 'Your vehicle'), while the VIN lookup moves into an "
        "<sl-vin-lookup> shadow root. Native selects become <mat-select role=combobox> (Make now first), ownership "
        "radios become mat-radio-buttons (reordered, relabelled 'Financed (car loan)'), 'Next' becomes 'Continue' and "
        "the 'Back' link becomes a mat-stroked-button. _ngcontent/ng-tns-* attributes and classes everywhere. Decoys: a "
        "compact mobile stepper repeating the step list, a sticky mobile action bar with a second 'Back' / 'Continue' "
        "pair, and Model/Year/Trim mat-selects next to Make.",
        [
            target("t1", "Current step 'Vehicle' (step 2 of 4) in the progress indicator",
                   "sl-progress-tracker li.is-current", "//ol[@class='steps']/li[2]",
                   ["shadow-dom", "structure-move", "class-obfuscation", "copy-change", "decoy"]),
            target("t2", "Vehicle make dropdown",
                   "#vehicle-make", "//select[@name='vehicle[make]']",
                   ["tag-change", "class-obfuscation", "id-change", "attribute-churn", "sibling-reorder", "wrapper-divs",
                    "decoy"]),
            target("t3", "VIN input",
                   "input#vin", "//input[@maxlength='17']",
                   ["shadow-dom", "class-obfuscation", "attribute-churn", "copy-change", "structure-move"]),
            target("t4", "'Financed' ownership radio button",
                   "input[name='vehicle[ownership]'][value='financed']", "//label[normalize-space()='Financed']/input",
                   ["class-obfuscation", "wrapper-divs", "attribute-churn", "copy-change", "sibling-reorder", "id-change"]),
            target("t5", "'Next' button that continues to step 3",
                   "button.btn-next", "//button[normalize-space()='Next']",
                   ["class-obfuscation", "copy-change", "wrapper-divs", "decoy"]),
            target("t6", "'Back' link to step 1",
                   "a.btn-back", "//a[normalize-space()='Back']",
                   ["tag-change", "class-obfuscation", "decoy"]),
        ],
    )
    return v1, v2, m


# ======================================================================================
# main
# ======================================================================================
class _AttrCheck(HTMLParser):
    """Flags start tags that repeat an attribute (browsers silently keep the first one)."""

    def __init__(self) -> None:
        super().__init__()
        self.problems: list[str] = []

    def handle_starttag(self, tag, attrs):
        names = [a for a, _ in attrs]
        dupes = sorted({a for a in names if names.count(a) > 1})
        if dupes:
            self.problems.append(f"<{tag}> repeats {dupes} at line {self.getpos()[0]}")


def emit(name: str, v1: str, v2: str, m: dict) -> None:
    out = HERE / name
    out.mkdir(exist_ok=True)
    ids = sorted(t["id"] for t in m["targets"])
    for fname, markup in (("v1.html", v1), ("v2.html", v2)):
        found = sorted(re.findall(r'data-dh-target="(t\d+)"', markup))
        if found != ids:
            raise SystemExit(f"{name}/{fname}: markers {found} != targets {ids}")
        if "~" in " ".join(_CLASS_RE.findall(markup)):
            raise SystemExit(f"{name}/{fname}: unexpanded class token")
        checker = _AttrCheck()
        checker.feed(markup)
        if checker.problems:
            raise SystemExit(f"{name}/{fname}: " + "; ".join(checker.problems))
        (out / fname).write_text(markup, encoding="utf-8")
    (out / "targets.json").write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    names = argv or sorted(SUITES)
    for name in names:
        v1, v2, m = SUITES[name]()
        emit(name, v1, v2, m)
        print(f"wrote {name}: v1 {len(v1.encode()):,} B, v2 {len(v2.encode()):,} B")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
