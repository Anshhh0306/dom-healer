#!/usr/bin/env python3
"""Generator for the *dashboard* benchmark fixtures (dashboard-01 … dashboard-10).

    python benchmarks/fixtures/dashboard/_build.py           # (re)write every suite
    python benchmarks/fixtures/dashboard/_build.py 03 07     # only some suites

Every suite below is authored by hand as two page templates -- ``v1`` (the app
as it was when the test selectors were written) and ``v2`` (the same screen
after a front-end redesign) -- plus its target list.  Loops are only used for
genuinely repeated UI (rows, tiles, cards, nav items), so the copy, data and
component structure of each suite stay specific to that product.

Ground truth: each target carries ``data-dh-target="tN"`` in both pages (see
``benchmarks/fixtures/README.md``).  Obfuscated class names (CSS modules,
styled-components, emotion) are derived from stable hashes, so the output is
deterministic.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITES: dict = {}


def suite(fn):
    SUITES[fn.__name__.replace("_", "-")] = fn
    return fn


def T(tid: str) -> str:
    """Ground-truth marker attribute (the harness strips it before any method runs)."""
    return f' data-dh-target="{tid}"'


def t_if(cond: bool, tid: str) -> str:
    return T(tid) if cond else ""


# --------------------------------------------------------------------------------------
# deterministic "build tool" class names
# --------------------------------------------------------------------------------------
_B62 = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
_B36 = "0123456789abcdefghijklmnopqrstuvwxyz"
_LET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _hash(seed: str, n: int, alphabet: str) -> str:
    digest = hashlib.sha256(seed.encode()).digest()
    return "".join(alphabet[b % len(alphabet)] for b in digest[:n])


def cm(module: str, local: str) -> str:
    """CSS-modules class name, e.g. ``KpiCard_value__x7Gq2``."""
    return f"{module}_{local}__{_hash(module + '.' + local, 5, _B62)}"


def sc(name: str) -> str:
    """styled-components class pair, e.g. ``sc-gKclnd kQwYzP``."""
    return f"sc-{_hash('sc:' + name, 6, _LET)} {_hash('sx:' + name, 6, _LET)}"


def emo(name: str) -> str:
    """emotion class name, e.g. ``css-1x9f2ab``."""
    return "css-" + _hash("emo:" + name, 7, _B36)


# --------------------------------------------------------------------------------------
# icons (24x24 stroke icons)
# --------------------------------------------------------------------------------------
ICONS = {
    "home": "M3 10.5 12 3l9 7.5V21h-6v-6H9v6H3z",
    "zap": "M13 2 3 14h9l-1 8 10-12h-9z",
    "filter": "M3 4h18l-7 8v6l-4 2v-8z",
    "repeat": "M17 2l4 4-4 4M3 11V9a3 3 0 0 1 3-3h15M7 22l-4-4 4-4M21 13v2a3 3 0 0 1-3 3H3",
    "share": "M18 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM6 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM18 22a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM8.6 13.5l6.8 4M15.4 6.5l-6.8 4",
    "users": "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8",
    "grid": "M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z",
    "activity": "M22 12h-4l-3 9L9 3l-3 9H2",
    "database": "M12 2c4.4 0 8 1.3 8 3v14c0 1.7-3.6 3-8 3s-8-1.3-8-3V5c0-1.7 3.6-3 8-3zM4 5c0 1.7 3.6 3 8 3s8-1.3 8-3M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3",
    "plug": "M9 2v6M15 2v6M6 8h12v4a6 6 0 0 1-12 0zM12 18v4",
    "search": "M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.3-4.3",
    "bell": "M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0",
    "bell-off": "M13.7 21a2 2 0 0 1-3.4 0M18.6 13A17.9 17.9 0 0 1 18 8M6.3 6.3A5.9 5.9 0 0 0 6 8c0 7-3 9-3 9h14M18 8a6 6 0 0 0-9.3-5M1 1l22 22",
    "chevron-down": "M6 9l6 6 6-6",
    "chevron-right": "M9 18l6-6-6-6",
    "chevron-left": "M15 18l-6-6 6-6",
    "calendar": "M3 5h18v16H3zM16 3v4M8 3v4M3 11h18",
    "download": "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3",
    "upload": "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12",
    "plus": "M12 5v14M5 12h14",
    "more-h": "M5 12h.01M12 12h.01M19 12h.01",
    "more-v": "M12 5h.01M12 12h.01M12 19h.01",
    "settings": "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z",
    "info": "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 16v-4M12 8h.01",
    "x": "M18 6 6 18M6 6l12 12",
    "check": "M20 6 9 17l-5-5",
    "pencil": "M17 3a2.8 2.8 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5z",
    "trash": "M3 6h18M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6M10 11v6M14 11v6M9 6V4h6v2",
    "mail": "M4 4h16v16H4zM22 6l-10 7L2 6",
    "phone": "M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z",
    "alert": "M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0zM12 9v4M12 17h.01",
    "power": "M18.4 6.6a9 9 0 1 1-12.8 0M12 2v10",
    "refresh": "M23 4v6h-6M1 20v-6h6M3.5 9a9 9 0 0 1 14.8-3.4L23 10M1 14l4.6 4.4A9 9 0 0 0 20.5 15",
    "map-pin": "M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0 1 18 0zM12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6z",
    "battery": "M2 7h16v10H2zM22 11v2",
    "wifi": "M5 12.6a10 10 0 0 1 14 0M1.4 9a15 15 0 0 1 21.2 0M8.5 16.1a5 5 0 0 1 7 0M12 20h.01",
    "cpu": "M4 4h16v16H4zM9 9h6v6H9zM9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3",
    "clock": "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 6v6l4 2",
    "star": "M12 2l3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1z",
    "inbox": "M22 12h-6l-2 3h-4l-2-3H2M5.5 5.1 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.5-6.9A2 2 0 0 0 16.8 4H7.2a2 2 0 0 0-1.7 1.1z",
    "folder": "M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z",
    "chart": "M18 20V10M12 20V4M6 20v-6",
    "list": "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01",
    "columns": "M3 3h7v18H3zM14 3h7v18h-7z",
    "dollar": "M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6",
    "card": "M1 4h22v16H1zM1 10h22",
    "send": "M22 2 11 13M22 2l-7 20-4-9-9-4z",
    "pause": "M6 4h4v16H6zM14 4h4v16h-4z",
    "play": "M5 3l14 9-14 9z",
    "lock": "M5 11h14v11H5zM7 11V7a5 5 0 0 1 10 0v4",
    "shield": "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",
    "book": "M4 19.5A2.5 2.5 0 0 1 6.5 17H20M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z",
    "message": "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z",
    "tag": "M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L2 12V2h10l8.6 8.6a2 2 0 0 1 0 2.8zM7 7h.01",
    "logout": "M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9",
    "menu": "M3 12h18M3 6h18M3 18h18",
    "help": "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3M12 17h.01",
    "arrow-up": "M12 19V5M5 12l7-7 7 7",
    "arrow-down": "M12 5v14M19 12l-7 7-7-7",
    "external": "M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14 21 3",
    "server": "M2 2h20v8H2zM2 14h20v8H2zM6 6h.01M6 18h.01",
    "flag": "M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1zM4 22v-7",
    "user-plus": "M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M8.5 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM20 8v6M23 11h-6",
    "megaphone": "M3 11v2a1 1 0 0 0 1 1h3l5 4V6L7 10H4a1 1 0 0 0-1 1zM16 8a5 5 0 0 1 0 8",
    "graduation": "M22 10 12 5 2 10l10 5 10-5zM6 12v5c3 2 9 2 12 0v-5",
    "droplet": "M12 2.7l5.7 5.6a8 8 0 1 1-11.3 0z",
    "terminal": "M4 17l6-6-6-6M12 19h8",
    "git": "M6 3v12M18 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM18 9a9 9 0 0 1-9 9",
    "layers": "M12 2 2 7l10 5 10-5zM2 17l10 5 10-5M2 12l10 5 10-5",
    "eye": "M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z",
    "copy": "M9 9h13v13H9zM5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1",
    "trend-up": "M23 6l-9.5 9.5-5-5L1 18M17 6h6v6",
    "briefcase": "M2 7h20v14H2zM16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16",
    "building": "M3 21h18M5 21V7l8-4v18M19 21V11l-6-4M9 9h.01M9 13h.01M9 17h.01",
    "bookmark": "M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z",
    "thermometer": "M14 14.8V3.5a2.5 2.5 0 0 0-5 0v11.3a4.5 4.5 0 1 0 5 0z",
}


def icon(name: str, cls: str = "", *, style: str = "stroke") -> str:
    """Inline SVG icon.  ``style`` varies the markup the way different icon kits do."""
    c = f' class="{cls}"' if cls else ""
    d = ICONS[name]
    if style == "hero":  # Heroicons as pasted from Tailwind UI
        return (f'<svg{c} fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" '
                f'aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="{d}"/></svg>')
    if style == "mui":  # Material-style filled icon component
        return f'<svg{c} focusable="false" aria-hidden="true" viewBox="0 0 24 24"><path d="{d}"/></svg>'
    return (f'<svg{c} viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="{d}"/></svg>')


def page(title: str, body: str, *, css: str = "", head: str = "", lang: str = "en", body_attrs: str = "") -> str:
    style = f"<style>\n{css.strip()}\n</style>\n" if css else ""
    return (
        "<!doctype html>\n"
        f'<html lang="{lang}">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{title}</title>\n{head}{style}</head>\n<body{body_attrs}>\n{body.strip()}\n</body>\n</html>\n"
    )


def line_chart(series, *, w=640, h=200, xlabels=(), svg_cls="", line_cls=(), grid_cls="", text_cls="",
               label="", use_path=False) -> str:
    """Small static line chart.  ``series`` holds lists of values in 0..1."""
    lo, hi = 12, h - 26
    parts = []
    for i in range(4):
        y = lo + (hi - lo) * i / 3
        g = f' class="{grid_cls}"' if grid_cls else ""
        parts.append(f'<line{g} x1="40" x2="{w - 8}" y1="{y:.0f}" y2="{y:.0f}"/>')
    for si, values in enumerate(series):
        n = len(values)
        pts = [(40 + (w - 48) * i / (n - 1), hi - (hi - lo) * v) for i, v in enumerate(values)]
        lc = f' class="{line_cls[si]}"' if si < len(line_cls) and line_cls[si] else ""
        if use_path:
            d = "M" + " L".join(f"{x:.0f} {y:.0f}" for x, y in pts)
            parts.append(f'<path{lc} d="{d}" fill="none"/>')
        else:
            p = " ".join(f"{x:.0f},{y:.0f}" for x, y in pts)
            parts.append(f'<polyline{lc} points="{p}" fill="none"/>')
    for i, xl in enumerate(xlabels):
        x = 40 + (w - 48) * i / max(1, len(xlabels) - 1)
        tc = f' class="{text_cls}"' if text_cls else ""
        parts.append(f'<text{tc} x="{x:.0f}" y="{h - 6}">{xl}</text>')
    sc_ = f' class="{svg_cls}"' if svg_cls else ""
    aria = f' role="img" aria-label="{label}"' if label else ' aria-hidden="true"'
    return f'<svg{sc_} viewBox="0 0 {w} {h}" preserveAspectRatio="none"{aria}>' + "".join(parts) + "</svg>"


def sparkline(values, cls="", w=120, h=32) -> str:
    n = len(values)
    pts = " ".join(f"{w * i / (n - 1):.0f},{h - 2 - (h - 4) * v:.0f}" for i, v in enumerate(values))
    c = f' class="{cls}"' if cls else ""
    return f'<svg{c} viewBox="0 0 {w} {h}" aria-hidden="true"><polyline points="{pts}" fill="none"/></svg>'


def wave(n, seed, base=0.5, amp=0.3, trend=0.0):
    """Deterministic pseudo-random series in 0..1 (for charts/sparklines)."""
    out = []
    h = hashlib.sha256(seed.encode()).digest()
    for i in range(n):
        noise = (h[i % len(h)] / 255 - 0.5) * amp
        weekly = 0.08 * (1 if i % 7 in (1, 2, 3) else -1)
        out.append(min(0.97, max(0.03, base + noise + weekly + trend * i / max(1, n - 1))))
    return out


def meta(suite_id, title, mutations, notes, targets):
    return {
        "suite": suite_id,
        "category": "dashboard",
        "title": title,
        "mutations": mutations,
        "notes": notes,
        "targets": targets,
    }


def tgt(tid, description, css, xpath, mutations):
    return {"id": tid, "description": description, "css": css, "xpath": xpath, "mutations": mutations}


# ======================================================================================
# dashboard-01 — SaaS product-analytics overview ("Lumetric")
# ======================================================================================
@suite
def dashboard_01():
    nav_main = [
        ("overview", "Overview", "home"),
        ("events", "Events", "zap"),
        ("funnels", "Funnels", "filter"),
        ("retention", "Retention", "repeat"),
        ("paths", "User paths", "share"),
        ("cohorts", "Cohorts", "users"),
        ("dashboards", "Dashboards", "grid"),
    ]
    nav_data = [("live", "Live events", "activity"), ("data-management", "Data management", "database"),
                ("integrations", "Integrations", "plug")]
    # key, label, value, delta, direction, previous
    kpis = [
        ("active-users", "Active users", "48,210", "+6.4%", "up", "45,309"),
        ("new-signups", "New signups", "3,982", "+12.1%", "up", "3,552"),
        ("session-duration", "Avg. session duration", "6m 42s", "−0.8%", "down", "6m 45s"),
        ("trial-conversion", "Trial → paid conversion", "4.86%", "+0.31 pts", "up", "4.55%"),
    ]
    sources = [("Organic search", "38.2"), ("Direct", "24.9"), ("Referral", "14.1"), ("Paid social", "11.7"),
               ("Email", "6.3"), ("Other", "4.8")]
    # path, title, visitors, views, avg time, bounce, change
    pages = [
        ("/", "Home · Fernhill", "21,604", "38,912", "1m 12s", "41.0%", "+4.2%"),
        ("/pricing", "Pricing · Fernhill", "9,877", "14,230", "2m 03s", "28.4%", "+18.9%"),
        ("/docs/getting-started", "Getting started · Fernhill Docs", "7,415", "16,688", "4m 51s", "19.7%", "+2.3%"),
        ("/blog/offline-sync-in-v4", "Offline sync in v4 · Fernhill Blog", "5,902", "6,311", "3m 37s", "62.3%", "+141%"),
        ("/signup", "Create your account · Fernhill", "4,388", "5,140", "0m 58s", "12.9%", "+9.6%"),
        ("/changelog", "Changelog · Fernhill", "3,067", "4,019", "1m 46s", "48.8%", "−3.1%"),
        ("/integrations/webhooks", "Webhooks · Fernhill Docs", "2,211", "2,960", "2m 22s", "35.1%", "+0.7%"),
        ("/about", "About us · Fernhill", "1,540", "1,702", "0m 49s", "57.6%", "−8.4%"),
    ]
    events = [("app_opened", "1.21M", "+5.0%"), ("screen_viewed", "984K", "+3.8%"), ("sync_completed", "412K", "+9.2%"),
              ("note_created", "233K", "+6.1%"), ("share_link_copied", "41.3K", "+22.4%"), ("upgrade_clicked", "9.8K", "+11.0%")]
    cur = wave(30, "lum-cur", 0.55, 0.25, 0.15)
    prev = wave(30, "lum-prev", 0.45, 0.25, 0.05)
    xl = ["Oct 6", "Oct 13", "Oct 20", "Oct 27", "Nov 3"]
    pricing = "/pricing"

    # ------------------------------------------------------------------ v1
    v1_css = """
:root{--brand:#5b4bdb;--ink:#1d2433;--muted:#6b7385;--line:#e6e8ef;--up:#12805c;--down:#c2412d}
*{box-sizing:border-box}
body{margin:0;font:14px/1.45 Inter,system-ui,sans-serif;color:var(--ink);background:#f6f7fb}
.app-header{display:flex;align-items:center;gap:16px;height:56px;padding:0 20px;background:#fff;border-bottom:1px solid var(--line)}
.global-search{flex:1;max-width:420px;display:flex;align-items:center;gap:8px;border:1px solid var(--line);border-radius:8px;padding:0 10px}
.global-search input{border:0;flex:1;height:34px;outline:none}
.app-body{display:flex;min-height:calc(100vh - 56px)}
.sidebar{width:232px;flex:none;border-right:1px solid var(--line);background:#fff;padding:12px}
.nav-list{list-style:none;margin:0;padding:0}
.nav-item{display:flex;align-items:center;gap:10px;padding:7px 12px;border-radius:6px;color:var(--ink);text-decoration:none}
.nav-item.active{background:#efedff;color:var(--brand);font-weight:600}
.nav-section{margin:18px 12px 6px;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.content{flex:1;padding:24px 32px}
.page-header{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;margin-bottom:20px}
.page-actions{display:flex;align-items:center;gap:12px}
.date-range{display:inline-flex;border:1px solid var(--line);border-radius:8px;overflow:hidden;background:#fff}
.preset-btn{border:0;background:none;padding:7px 12px;cursor:pointer}
.preset-btn.is-selected{background:var(--brand);color:#fff}
.btn{display:inline-flex;align-items:center;gap:6px;border-radius:8px;padding:7px 12px;border:1px solid var(--line);background:#fff}
.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:16px}
.kpi-card,.panel{background:#fff;border:1px solid var(--line);border-radius:10px;padding:16px}
.kpi-value{font-size:28px;font-weight:600}
.kpi-delta.up{color:var(--up)}.kpi-delta.down{color:var(--down)}
.panel-grid{display:grid;grid-template-columns:2fr 1fr;gap:16px;margin-bottom:16px}
.panel-header{display:flex;justify-content:space-between;align-items:center}
.tab{border:0;background:none;padding:6px 10px;border-radius:6px}
.tab.is-active{background:#efedff;color:var(--brand)}
.chart svg{width:100%;height:200px}.chart line{stroke:#eef0f4}.chart .series-current{stroke:var(--brand);stroke-width:2}
.chart .series-previous{stroke:#b9bfcc;stroke-dasharray:4 3}
.bar-track{display:block;height:6px;background:#eef0f4;border-radius:3px}.bar-fill{display:block;height:6px;background:var(--brand);border-radius:3px}
.top-pages{width:100%;border-collapse:collapse}.top-pages td,.top-pages th{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left}
.app-footer{display:flex;gap:16px;padding:16px 32px;color:var(--muted);font-size:12px;border-top:1px solid var(--line)}
"""

    def v1_nav(items, current="overview"):
        out = []
        for key, label, ic in items:
            active = key == current
            cls = "nav-item active" if active else "nav-item"
            aria = ' aria-current="page"' if active else ""
            out.append(f'          <li><a class="{cls}" href="/p/fernhill/{key}"{aria}>{icon(ic, "nav-icon")}'
                       f'<span class="nav-label">{label}</span></a></li>')
        return "\n".join(out)

    v1_kpis = "\n".join(
        f'''        <div class="kpi-card" id="kpi-{k}" data-testid="kpi-{k}">
          <div class="kpi-label">{label}</div>
          <div class="kpi-main"><span class="kpi-value"{t_if(k == "active-users", "t2")}>{val}</span><span class="kpi-delta {d}">{delta}</span></div>
          <div class="kpi-foot">vs. {prv} in previous 30 days</div>
        </div>''' for k, label, val, delta, d, prv in kpis)

    v1_sources = "\n".join(
        f'          <li class="bar-row"><span class="bar-name">{n}</span><span class="bar-track"><span class="bar-fill" '
        f'style="width:{p}%"></span></span><span class="bar-value">{p}%</span></li>' for n, p in sources)

    v1_pages = "\n".join(
        f'''            <tr>
              <td class="page"><a href="/p/fernhill/pages?path={path.replace("/", "%2F")}"{t_if(path == pricing, "t5")}>{path}</a></td>
              <td class="num">{vis}</td><td class="num">{views}</td><td class="num">{avg}</td><td class="num">{bounce}</td>
            </tr>''' for path, _t, vis, views, avg, bounce, _c in pages)

    v1_events = "\n".join(
        f'          <li class="event-row"><code class="event-name">{name}</code><span class="event-count">{cnt}</span>'
        f'<span class="kpi-delta up">{chg}</span></li>' for name, cnt, chg in events)

    v1_body = f'''
<div class="app-shell">
  <header class="app-header">
    <a class="brand" href="/p/fernhill/overview" aria-label="Lumetric home">{icon("activity", "brand-mark")}<span class="brand-name">Lumetric</span></a>
    <div class="project-switcher">
      <button class="project-switcher-btn" type="button" aria-haspopup="listbox"><span class="project-dot"></span>Fernhill — Production{icon("chevron-down")}</button>
    </div>
    <form class="global-search" role="search" action="/search">
      {icon("search")}<input type="search" name="q" placeholder="Search events, reports, cohorts…" aria-label="Search Lumetric"><kbd>⌘K</kbd>
    </form>
    <nav class="header-links" aria-label="Resources">
      <a href="https://docs.lumetric.example/">Docs</a>
      <a href="/changelog">What's new</a>
    </nav>
    <button class="icon-btn" type="button" aria-label="Notifications">{icon("bell")}<span class="badge">3</span></button>
    <button class="avatar-btn" type="button" aria-label="Account menu"><span class="avatar">NK</span></button>
  </header>
  <div class="app-body">
    <aside class="sidebar">
      <nav class="sidebar-nav" aria-label="Main">
        <ul class="nav-list">
{v1_nav(nav_main)}
        </ul>
        <h4 class="nav-section">Data</h4>
        <ul class="nav-list">
{v1_nav(nav_data)}
        </ul>
      </nav>
      <div class="sidebar-footer">
        <div class="usage">
          <div class="usage-label">Growth plan · events this month</div>
          <div class="usage-bar"><div class="usage-fill" style="width:82%"></div></div>
          <div class="usage-meta">8.2M of 10M</div>
        </div>
        <a class="upgrade-link" href="/settings/billing">Upgrade plan</a>
      </div>
    </aside>
    <main class="content" id="main">
      <div class="page-header">
        <div class="page-heading">
          <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/p/fernhill">Fernhill</a><span class="sep">/</span><span>Overview</span></nav>
          <h1 class="page-title">Overview</h1>
          <p class="page-subtitle">All platforms · Data updated 4 minutes ago</p>
        </div>
        <div class="page-actions">
          <div class="date-range" role="group" aria-label="Date range">
            <button type="button" class="preset-btn" data-range="today">Today</button>
            <button type="button" class="preset-btn" data-range="7d">7D</button>
            <button type="button" class="preset-btn is-selected" data-range="30d" aria-pressed="true"{T("t1")}>30D</button>
            <button type="button" class="preset-btn" data-range="90d">90D</button>
            <button type="button" class="preset-btn preset-custom" data-range="custom">{icon("calendar")}Oct 6 – Nov 4, 2026</button>
          </div>
          <label class="compare-toggle"><input type="checkbox" id="compare-prev" name="compare"{T("t6")}> Compare to previous period</label>
          <button type="button" class="btn btn-secondary" id="share-btn">{icon("share")}Share</button>
          <button type="button" class="btn btn-secondary" id="export-btn"{T("t4")}>{icon("download")}Export</button>
        </div>
      </div>

      <section class="kpi-grid" aria-label="Key metrics">
{v1_kpis}
      </section>

      <div class="panel-grid">
        <section class="panel chart-panel" id="panel-active-users">
          <header class="panel-header">
            <h2 class="panel-title">Active users over time</h2>
            <div class="tabs" role="tablist" aria-label="Granularity">
              <button type="button" role="tab" class="tab is-active" aria-selected="true">Daily</button>
              <button type="button" role="tab" class="tab" aria-selected="false"{T("t3")}>Weekly</button>
              <button type="button" role="tab" class="tab" aria-selected="false">Monthly</button>
            </div>
          </header>
          <div class="chart">{line_chart([cur, prev], xlabels=xl, line_cls=("series-current", "series-previous"), label="Daily active users, Oct 6 to Nov 4")}</div>
          <ul class="chart-legend">
            <li><span class="swatch swatch-current"></span>This period <span class="legend-value">48,210</span></li>
            <li><span class="swatch swatch-previous"></span>Previous period <span class="legend-value">45,309</span></li>
          </ul>
        </section>
        <section class="panel" id="panel-sources">
          <header class="panel-header"><h2 class="panel-title">Traffic sources</h2><a class="panel-link" href="/p/fernhill/acquisition">View all</a></header>
          <ul class="bar-list">
{v1_sources}
          </ul>
        </section>
      </div>

      <div class="panel-grid">
        <section class="panel" id="panel-top-pages">
          <header class="panel-header"><h2 class="panel-title">Top pages</h2><span class="panel-meta">By unique visitors</span></header>
          <table class="top-pages">
            <thead><tr><th>Page</th><th>Visitors</th><th>Views</th><th>Avg. time</th><th>Bounce</th></tr></thead>
            <tbody>
{v1_pages}
            </tbody>
          </table>
        </section>
        <section class="panel" id="panel-events">
          <header class="panel-header"><h2 class="panel-title">Top events</h2><a class="panel-link" href="/p/fernhill/events">All events</a></header>
          <ol class="event-list">
{v1_events}
          </ol>
        </section>
      </div>
    </main>
  </div>
  <footer class="app-footer">
    <span>© 2026 Lumetric Labs, Inc.</span>
    <a href="https://status.lumetric.example">Status</a>
    <a href="/legal/privacy">Privacy</a>
    <a href="/legal/terms">Terms</a>
    <span class="build">v4.18.2</span>
  </footer>
</div>
'''
    v1 = page("Overview · Fernhill — Lumetric", v1_body, css=v1_css)

    # ------------------------------------------------------------------ v2
    def c(m, l):
        return cm(m, l)

    nav2 = [
        ("overview", "Overview", "home"), ("dashboards", "Dashboards", "grid"), ("events", "Events", "zap"),
        ("funnels", "Funnels", "filter"), ("retention", "Retention", "repeat"), ("journeys", "Journeys", "share"),
        ("cohorts", "Cohorts", "users"), ("replay", "Session replay", "eye"),
    ]

    def v2_nav(items):
        out = []
        for key, label, ic in items:
            active = key == "overview"
            cls = c("SideNav", "item") + (" " + c("SideNav", "itemActive") if active else "")
            aria = ' aria-current="page"' if active else ""
            badge = f'<span class="{c("Badge", "root")} {c("Badge", "beta")}">Beta</span>' if key == "replay" else ""
            out.append(f'        <a class="{cls}" href="/p/fernhill/{key}"{aria}>{icon(ic, c("SideNav", "icon"))}'
                       f'<span class="{c("SideNav", "label")}">{label}</span>{badge}</a>')
        return "\n".join(out)

    kpis2 = [kpis[1], kpis[3], kpis[0], kpis[2], ("stickiness", "Stickiness (DAU/MAU)", "31.7%", "+1.2 pts", "up", "30.5%")]

    def v2_kpi(k, label, val, delta, d, prv):
        arrow = "arrow-up" if d == "up" else "arrow-down"
        return f'''          <article class="{c("KpiCard", "root")}" data-metric="{k.replace("-", "_")}">
            <header class="{c("KpiCard", "header")}"><h3 class="{c("KpiCard", "label")}">{label}</h3><button type="button" class="{c("KpiCard", "info")}" aria-label="About {label}">{icon("info")}</button></header>
            <div class="{c("KpiCard", "body")}"><div class="{c("KpiCard", "valueRow")}"><span class="{c("KpiCard", "value")}"{t_if(k == "active-users", "t2")}>{val}</span></div><span class="{c("Delta", "root")} {c("Delta", d)}">{icon(arrow)}{delta.lstrip("+−")}</span></div>
            <p class="{c("KpiCard", "compare")}">Previous 30 days: {prv}</p>
            {sparkline(wave(14, "kpi" + k, 0.5, 0.4), c("KpiCard", "spark"))}
          </article>'''

    pages2 = sorted(pages, key=lambda r: -int(r[3].replace(",", "")))

    def v2_page_row(path, title, vis, views, avg, bounce, chg):
        cls = c("DataTable", "neg") if chg.startswith("−") else c("DataTable", "pos")
        return f'''              <tr class="{c("DataTable", "row")}">
                <td class="{c("DataTable", "cell")}"><div class="{c("PageCell", "root")}"><a class="{c("PageCell", "path")}" href="/p/fernhill/pages/{path.replace("/", "%2F")}"{t_if(path == pricing, "t5")}>{path}</a><span class="{c("PageCell", "title")}">{title}</span></div></td>
                <td class="{c("DataTable", "cell")} {c("DataTable", "num")}">{views}</td>
                <td class="{c("DataTable", "cell")} {c("DataTable", "num")}">{vis}</td>
                <td class="{c("DataTable", "cell")} {c("DataTable", "num")}">{avg}</td>
                <td class="{c("DataTable", "cell")} {c("DataTable", "num")}">{bounce}</td>
                <td class="{c("DataTable", "cell")} {c("DataTable", "num")} {cls}">{chg}</td>
              </tr>'''

    def tabs2(prefix, selected="Day", target=None):
        out = []
        for lab in ("Hour", "Day", "Week", "Month"):
            sel = lab == selected
            cls = c("Segmented", "item") + (" " + c("Segmented", "active") if sel else "")
            mark = T(target) if target and lab == "Week" else ""
            out.append(f'<button type="button" role="tab" id="{prefix}-tab-{lab.lower()}" aria-selected="{str(sel).lower()}" '
                       f'class="{cls}"{mark}>{lab}</button>')
        return "".join(out)

    v2_css = f"""
.{c("Layout", "root")}{{min-height:100vh;background:#fafafb;color:#16181d;font:14px/1.5 "Inter var",system-ui,sans-serif}}
.{c("TopBar", "root")}{{position:sticky;top:0;z-index:20;display:flex;align-items:center;gap:20px;height:52px;padding:0 16px;background:#fff;box-shadow:0 1px 0 #ececf1}}
.{c("Layout", "body")}{{display:grid;grid-template-columns:248px 1fr}}
.{c("SideNav", "item")}{{display:flex;align-items:center;gap:10px;padding:6px 10px;border-radius:6px;color:#3b3f4a;text-decoration:none}}
.{c("SideNav", "itemActive")}{{background:#f0eeff;color:#4a3bc9}}
.{c("MetricGrid", "root")}{{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:12px}}
.{c("KpiCard", "root")}{{border-radius:12px;background:#fff;box-shadow:0 0 0 1px #ececf1;padding:14px 16px}}
.{c("KpiCard", "value")}{{font-size:26px;font-weight:650;letter-spacing:-.01em}}
.{c("Segmented", "root")}{{display:inline-flex;padding:2px;border-radius:8px;background:#f1f1f4}}
.{c("Segmented", "active")}{{background:#fff;box-shadow:0 1px 2px rgba(0,0,0,.08)}}
.{c("DataTable", "table")}{{width:100%;border-collapse:separate;border-spacing:0}}
"""
    drp_css = """
:host{display:inline-flex;align-items:center;gap:8px;font:inherit}
.picker{display:flex;align-items:center;gap:8px}
.presets{display:inline-flex;padding:2px;border-radius:8px;background:#f1f1f4}
.preset{border:0;background:none;padding:5px 10px;border-radius:6px;font:inherit;color:#3b3f4a}
.preset[aria-checked="true"]{background:#fff;color:#16181d;box-shadow:0 1px 2px rgba(0,0,0,.08)}
.range-trigger{display:inline-flex;gap:6px;align-items:center;border:1px solid #e3e3ea;border-radius:8px;background:#fff;padding:5px 10px}
.compare{display:inline-flex;align-items:center;gap:6px;color:#585d6b}
.compare input{position:absolute;opacity:0}
.track{width:28px;height:16px;border-radius:8px;background:#d7d7df;display:inline-block;position:relative}
"""
    presets2 = [("today", "Today"), ("yesterday", "Yesterday"), ("last_7_days", "Last 7 days"),
                ("last_30_days", "Last 30 days"), ("last_90_days", "Last 90 days"), ("last_12_months", "Last 12 months")]
    presets2_html = "\n".join(
        f'                    <button type="button" class="preset" role="radio" aria-checked="{str(v == "last_30_days").lower()}" '
        f'data-value="{v}"{t_if(v == "last_30_days", "t1")}>{lab}</button>' for v, lab in presets2)

    v2_body = f'''
<div id="__next">
<div class="{c("Layout", "root")}">
  <div class="{c("Banner", "root")}" role="region" aria-label="Announcement">
    <p class="{c("Banner", "text")}"><strong>New:</strong> Session replay is now in beta on Growth plans. <a href="/p/fernhill/replay">Try it on your top pages</a></p>
    <button type="button" class="{c("Banner", "close")}" aria-label="Dismiss announcement">{icon("x")}</button>
  </div>
  <header class="{c("TopBar", "root")}">
    <a class="{c("TopBar", "brand")}" href="/p/fernhill/overview">{icon("activity", c("TopBar", "logo"))}<span>Lumetric</span></a>
    <button type="button" class="{c("ProjectSwitcher", "trigger")}" aria-haspopup="menu"><span class="{c("ProjectSwitcher", "name")}">Fernhill</span><span class="{c("ProjectSwitcher", "env")}">Production</span>{icon("chevron-down")}</button>
    <div class="{c("CommandBar", "root")}"><button type="button" class="{c("CommandBar", "trigger")}">{icon("search")}<span>Search or jump to…</span><kbd>⌘K</kbd></button></div>
    <div class="{c("TopBar", "right")}">
      <a class="{c("TopBar", "link")}" href="/changelog">What's new</a>
      <a class="{c("TopBar", "link")}" href="https://docs.lumetric.example/">Docs</a>
      <button type="button" class="{c("IconButton", "root")}" aria-label="Notifications, 3 unread">{icon("bell")}<span class="{c("IconButton", "dot")}"></span></button>
      <button type="button" class="{c("Avatar", "root")}" aria-label="Open account menu">NK</button>
    </div>
  </header>
  <div class="{c("Layout", "body")}">
    <nav class="{c("SideNav", "root")}" aria-label="Primary">
      <div class="{c("SideNav", "group")}">
{v2_nav(nav2)}
      </div>
      <div class="{c("SideNav", "group")}">
        <p class="{c("SideNav", "heading")}">Data</p>
{v2_nav([("live", "Live events", "activity"), ("data", "Data management", "database"), ("integrations", "Integrations", "plug")])}
      </div>
      <div class="{c("SideNav", "footer")}">
        <div class="{c("Usage", "root")}"><span class="{c("Usage", "label")}">8.2M / 10M events</span><progress class="{c("Usage", "bar")}" max="100" value="82">82%</progress></div>
        <a class="{c("Usage", "upgrade")}" href="/settings/billing">Upgrade</a>
      </div>
    </nav>
    <main class="{c("Page", "root")}" id="main-content">
      <div class="{c("PageHeader", "root")}">
        <div class="{c("PageHeader", "titles")}">
          <h1 class="{c("PageHeader", "title")}">Overview</h1>
          <p class="{c("PageHeader", "subtitle")}">All platforms · Updated 4 min ago</p>
        </div>
        <div class="{c("PageHeader", "toolbar")}">
          <div class="{c("Toolbar", "group")}">
            <date-range-picker value="last_30_days" compare-enabled>
              <template shadowrootmode="open">
                <style>{drp_css}</style>
                <div class="picker" part="base">
                  <div class="presets" role="radiogroup" aria-label="Date range">
{presets2_html}
                  </div>
                  <button type="button" class="range-trigger" aria-haspopup="dialog">{icon("calendar")}<span>Oct 6, 2026 – Nov 4, 2026</span></button>
                  <label class="compare"><input type="checkbox" role="switch" name="comparePrevious" id="compare-:r3:"{T("t6")}><span class="track"><span class="thumb"></span></span><span class="text">Compare with previous period</span></label>
                </div>
              </template>
            </date-range-picker>
          </div>
          <div class="{c("Toolbar", "group")}">
            <span class="{c("Tooltip", "anchor")}"><button type="button" class="{c("Button", "root")} {c("Button", "ghost")}">{icon("share")}Share</button></span>
            <div class="{c("Menu", "root")}">
              <button type="button" class="{c("Button", "root")} {c("Button", "secondary")}" aria-haspopup="menu" aria-expanded="false"{T("t4")}>{icon("download")}Export{icon("chevron-down")}</button>
              <div class="{c("Menu", "panel")}" role="menu" hidden>
                <button type="button" role="menuitem" class="{c("Menu", "item")}">Download CSV</button>
                <button type="button" role="menuitem" class="{c("Menu", "item")}">Download PNG</button>
                <button type="button" role="menuitem" class="{c("Menu", "item")}">Schedule email report…</button>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="{c("MobileFilters", "sheet")}" hidden>
        <p class="{c("MobileFilters", "title")}">Date range</p>
        <div class="{c("MobileFilters", "options")}">
          <button type="button" class="{c("MobileFilters", "option")}">Last 7 days</button>
          <button type="button" class="{c("MobileFilters", "option")}">Last 30 days</button>
          <button type="button" class="{c("MobileFilters", "option")}">Last 90 days</button>
        </div>
      </div>

      <section class="{c("MetricGrid", "root")}" aria-label="Key metrics">
{chr(10).join(v2_kpi(*k) for k in kpis2)}
      </section>

      <div class="{c("Grid", "twoUp")}">
        <section class="{c("Card", "root")}" aria-labelledby="sources-title">
          <header class="{c("Card", "header")}"><h2 class="{c("Card", "title")}" id="sources-title">Traffic sources</h2><a class="{c("Card", "link")}" href="/p/fernhill/acquisition">View report</a></header>
          <ul class="{c("BarList", "root")}">
{chr(10).join(f'            <li class="{c("BarList", "row")}"><span class="{c("BarList", "label")}">{n}</span><meter class="{c("BarList", "meter")}" min="0" max="100" value="{p}">{p}%</meter><span class="{c("BarList", "value")}">{p}%</span></li>' for n, p in sources)}
          </ul>
        </section>
        <section class="{c("Card", "root")} {c("ChartCard", "root")}" aria-labelledby="chart-:r9:-title">
          <header class="{c("ChartCard", "header")}">
            <h2 class="{c("Card", "title")}" id="chart-:r9:-title">Active users</h2>
            <div class="{c("Segmented", "root")}" role="tablist" aria-label="Interval">{tabs2("users", target="t3")}</div>
          </header>
          <div class="{c("ChartCard", "plot")}">{line_chart([cur, prev], xlabels=xl, use_path=True, label="Active users per day")}</div>
          <ul class="{c("Legend", "root")}">
            <li class="{c("Legend", "item")}"><span class="{c("Legend", "swatch")}"></span><span class="{c("Legend", "label")}">This period</span><span class="{c("Legend", "value")}">48,210</span></li>
            <li class="{c("Legend", "item")}"><span class="{c("Legend", "swatch")} {c("Legend", "muted")}"></span><span class="{c("Legend", "label")}">Previous period</span><span class="{c("Legend", "value")}">45,309</span></li>
          </ul>
        </section>
        <section class="{c("Card", "root")} {c("ChartCard", "root")}" aria-labelledby="chart-:ra:-title">
          <header class="{c("ChartCard", "header")}">
            <h2 class="{c("Card", "title")}" id="chart-:ra:-title">Sessions</h2>
            <div class="{c("Segmented", "root")}" role="tablist" aria-label="Interval">{tabs2("sessions")}</div>
          </header>
          <div class="{c("ChartCard", "plot")}">{line_chart([wave(30, "lum-sess", 0.5, 0.3, 0.1)], xlabels=xl, use_path=True, label="Sessions per day")}</div>
        </section>
      </div>

      <div class="{c("Grid", "twoUp")}">
        <section class="{c("Card", "root")}" aria-labelledby="top-pages-title">
          <header class="{c("Card", "header")}">
            <h2 class="{c("Card", "title")}" id="top-pages-title">Top pages</h2>
            <div class="{c("Card", "actions")}">
              <select class="{c("Select", "root")}" aria-label="Sort top pages by"><option>Unique visitors</option><option selected>Pageviews</option><option>Avg. time on page</option></select>
              <button type="button" class="{c("Button", "root")} {c("Button", "ghost")}">{icon("download")}Export</button>
            </div>
          </header>
          <table class="{c("DataTable", "table")}">
            <thead><tr><th>Page</th><th>Views</th><th>Visitors</th><th>Avg. time</th><th>Bounce rate</th><th>Change</th></tr></thead>
            <tbody>
{chr(10).join(v2_page_row(*r) for r in pages2)}
            </tbody>
          </table>
        </section>
        <section class="{c("Card", "root")}" aria-labelledby="events-title">
          <header class="{c("Card", "header")}"><h2 class="{c("Card", "title")}" id="events-title">Top events</h2></header>
          <table class="{c("DataTable", "table")}">
            <tbody>
{chr(10).join(f'              <tr class="{c("DataTable", "row")}"><td class="{c("DataTable", "cell")}"><code>{n}</code></td><td class="{c("DataTable", "cell")} {c("DataTable", "num")}">{cnt}</td><td class="{c("DataTable", "cell")} {c("DataTable", "pos")}">{chg}</td></tr>' for n, cnt, chg in events)}
            </tbody>
          </table>
        </section>
      </div>
    </main>
  </div>
  <footer class="{c("Footer", "root")}">
    <span>© 2026 Lumetric Labs, Inc.</span>
    <nav class="{c("Footer", "links")}" aria-label="Legal"><a href="https://status.lumetric.example">Status</a><a href="/legal/privacy">Privacy</a><a href="/legal/terms">Terms</a></nav>
    <span class="{c("Footer", "build")}">v5.0.1</span>
  </footer>
</div>
<help-launcher position="bottom-right">
  <template shadowrootmode="open">
    <style>:host{{position:fixed;right:20px;bottom:20px}} button{{width:44px;height:44px;border-radius:50%;border:0;background:#4a3bc9;color:#fff}}</style>
    <button type="button" class="launcher" aria-label="Open help and support">{icon("help")}</button>
  </template>
</help-launcher>
</div>
'''
    v2 = page("Overview · Fernhill — Lumetric", v2_body, css=v2_css)

    targets = [
        tgt("t1", "'30D' preset of the date-range picker in the page header (the currently selected range)",
            '.date-range .preset-btn[data-range="30d"]',
            "//div[@class='date-range']/button[normalize-space()='30D']",
            ["shadow-dom", "class-obfuscation", "copy-change", "attribute-churn", "insertion", "decoy"]),
        tgt("t2", "Value of the 'Active users' KPI card (48,210)",
            "#kpi-active-users .kpi-value",
            "//div[@data-testid='kpi-active-users']//span[@class='kpi-value']",
            ["class-obfuscation", "sibling-reorder", "id-change", "testid-change", "wrapper-divs", "insertion", "decoy"]),
        tgt("t3", "'Weekly' interval tab of the 'Active users over time' chart panel",
            "#panel-active-users .tabs > button:nth-child(2)",
            "//section[@id='panel-active-users']//button[@role='tab'][normalize-space()='Weekly']",
            ["class-obfuscation", "copy-change", "id-change", "insertion", "sibling-reorder", "decoy"]),
        tgt("t4", "'Export' button in the page-header toolbar (next to Share)",
            "#export-btn",
            "//button[normalize-space()='Export']",
            ["id-change", "class-obfuscation", "wrapper-divs", "attribute-churn", "decoy"]),
        tgt("t5", "'/pricing' page link in the Top pages table",
            "table.top-pages tbody tr:nth-child(2) td.page a",
            "//table[@class='top-pages']//a[text()='/pricing']",
            ["class-obfuscation", "sibling-reorder", "wrapper-divs", "attribute-churn", "insertion"]),
        tgt("t6", "'Compare to previous period' checkbox next to the date-range picker",
            "input#compare-prev",
            "//label[contains(normalize-space(.),'Compare to previous period')]/input[@type='checkbox']",
            ["shadow-dom", "id-change", "copy-change", "wrapper-divs", "attribute-churn", "structure-move"]),
    ]
    m = meta(
        "dashboard-01", "Product-analytics overview — Lumetric (SaaS analytics)",
        ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change", "testid-change",
         "copy-change", "attribute-churn", "insertion", "structure-move"],
        "v2 is a Next.js rewrite with CSS-modules class hashes. The date-range presets and the compare toggle move into a "
        "<date-range-picker> web component (declarative shadow root) with relabelled presets ('30D' -> 'Last 30 days') "
        "and a new 'Yesterday'/'Last 12 months' option; a hidden mobile filter sheet repeats the presets. KPI cards are "
        "reordered and a 'Stickiness' card is added; ids/test ids are gone. The chart panels swap places, intervals become "
        "Hour/Day/Week/Month and a new 'Sessions' chart repeats the same tabs. Top pages is re-sorted by pageviews, gains a "
        "'Change' column and its own 'Export' button. A help launcher web component and an announcement banner are added.",
        targets,
    )
    return v1, v2, m


# ======================================================================================
# dashboard-02 — admin user management ("Keyline Admin" for Halcyon Freight Co.)
# ======================================================================================
@suite
def dashboard_02():
    dom = "halcyon-freight.example"
    # id, name, role, team, last active, status, avatar colour
    users = [
        ("u_1001", "Rhea Castellanos", "Owner", "Operations leadership", "Active now", "Active", "indigo"),
        ("u_1002", "Marcus Bell", "Admin", "IT & security", "12 min ago", "Active", "sky"),
        ("u_1003", "Priya Raman", "Admin", "Finance", "1 hour ago", "Active", "teal"),
        ("u_1004", "Diego Fuentes", "Manager", "Dispatch", "3 hours ago", "Active", "amber"),
        ("u_1005", "Hana Kobayashi", "Member", "Customer success", "Yesterday", "Active", "rose"),
        ("u_1006", "Oluwaseun Adeyemi", "Member", "Fleet maintenance", "Yesterday", "Active", "lime"),
        ("u_1007", "Greta Lindholm", "Manager", "Customer success", "Nov 2, 2026", "Active", "violet"),
        ("u_1008", "Samir Haddad", "Member", "Dispatch", "Oct 28, 2026", "Suspended", "orange"),
        ("u_1009", "Claire Dubois", "Guest", "External auditors", "—", "Invited", "cyan"),
        ("u_1010", "Tomás Ibarra", "Member", "Engineering", "—", "Invited", "emerald"),
    ]
    teams = ["Dispatch", "Fleet maintenance", "Finance", "Customer success", "Engineering", "IT & security",
             "Operations leadership", "External auditors"]
    target_user = "Priya Raman"

    def initials(name):
        return "".join(p[0] for p in name.split()[:2])

    def email(name):
        return name.lower().replace("á", "a").replace(" ", ".") + "@" + dom

    def amp(s):
        return s.replace("&", "&amp;")

    # ------------------------------------------------------------------ v1 (Bootstrap 4-era admin)
    v1_css = """
body{font-family:"Source Sans Pro",-apple-system,"Segoe UI",Roboto,sans-serif;font-size:.9375rem;background:#f4f6f9;color:#212529;margin:0}
.wrapper{display:flex;min-height:100vh}
.main-sidebar{width:250px;background:#343a40;color:#c2c7d0;flex:none}
.sidebar-brand{display:flex;align-items:center;gap:.5rem;padding:.9rem 1rem;color:#fff;text-decoration:none;border-bottom:1px solid #4b545c}
.org-card{margin:1rem;padding:.75rem;border-radius:.25rem;background:#3f474e}
.nav-heading{margin:1rem 1rem .25rem;font-size:.75rem;text-transform:uppercase;color:#8a939b}
.sidebar-nav .nav-link{display:block;padding:.45rem 1rem;color:#c2c7d0;text-decoration:none}
.sidebar-nav .nav-link.active{background:#007bff;color:#fff;border-radius:.25rem}
.main-panel{flex:1;display:flex;flex-direction:column}
.navbar{display:flex;align-items:center;gap:1rem;padding:.5rem 1rem;background:#fff;border-bottom:1px solid #dee2e6}
.content{padding:1.5rem}
.page-heading{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:1rem}
.btn{display:inline-block;padding:.375rem .75rem;border-radius:.25rem;border:1px solid transparent}
.btn-primary{background:#007bff;color:#fff}.btn-outline-secondary{border-color:#6c757d;color:#6c757d}
.stat-card{background:#fff;border-radius:.25rem;padding:.75rem 1rem;box-shadow:0 0 1px rgba(0,0,0,.125),0 1px 3px rgba(0,0,0,.2)}
.card{background:#fff;border-radius:.25rem;box-shadow:0 0 1px rgba(0,0,0,.125),0 1px 3px rgba(0,0,0,.2)}
.table{width:100%;border-collapse:collapse}.table td,.table th{padding:.6rem .75rem;border-top:1px solid #dee2e6}
.avatar{display:inline-flex;width:32px;height:32px;border-radius:50%;align-items:center;justify-content:center;color:#fff;font-size:.8rem}
.badge-role{padding:.2em .5em;border-radius:.25rem;background:#e9ecef}
.modal{display:none}
"""
    v1_rows = []
    for uid, name, role, team, last, status, colour in users:
        is_t = name == target_user
        v1_rows.append(f'''              <tr data-user-id="{uid}">
                <td><input class="form-check-input" type="checkbox" aria-label="Select {name}"></td>
                <td>
                  <div class="user-cell"><span class="avatar avatar-sm bg-{colour}">{initials(name)}</span>
                    <div><div class="user-name">{name}</div><div class="user-email text-muted">{email(name)}</div></div>
                  </div>
                </td>
                <td><span class="badge badge-role role-{role.lower()}">{role}</span></td>
                <td>{amp(team)}</td>
                <td class="text-muted">{last}</td>
                <td><span class="status-dot status-{status.lower()}"></span>{status}</td>
                <td class="text-right"><button type="button" class="btn btn-icon btn-sm" aria-label="More actions for {name}"{t_if(is_t, "t3")}><i class="ico ico-more-vertical"></i></button></td>
              </tr>''')

    def v1_navlist(items):
        out = []
        for href, label, ico, extra in items:
            active = href == "/admin/users"
            cls = "nav-link active" if active else "nav-link"
            aria = ' aria-current="page"' if active else ""
            out.append(f'          <li class="nav-item"><a class="{cls}" href="{href}"{aria}{extra}><i class="ico ico-{ico}"></i>{label}</a></li>')
        return "\n".join(out)

    v1_body = f'''
<div class="wrapper">
  <aside class="main-sidebar">
    <a class="sidebar-brand" href="/admin"><span class="brand-logo">K</span><span class="brand-text">Keyline <small>Admin</small></span></a>
    <div class="org-card">
      <div class="org-name">Halcyon Freight Co.</div>
      <div class="org-plan">Business plan · 128 of 150 seats</div>
    </div>
    <nav class="sidebar-nav" aria-label="Admin">
      <p class="nav-heading">Organization</p>
      <ul class="nav flex-column">
{v1_navlist([("/admin/overview", "Overview", "home", ""), ("/admin/users", "Users", "users", ""), ("/admin/teams", "Teams", "layers", ""), ("/admin/groups", "Groups", "grid", ""), ("/admin/roles", "Roles &amp; permissions", "shield", ""), ("/admin/apps", "Apps &amp; integrations", "plug", "")])}
      </ul>
      <p class="nav-heading">Security</p>
      <ul class="nav flex-column">
{v1_navlist([("/admin/sso", "Single sign-on", "lock", ""), ("/admin/password-policy", "Password policy", "key", ""), ("/admin/audit-log", "Audit log", "list", T("t4")), ("/admin/api-tokens", "API tokens", "terminal", "")])}
      </ul>
      <p class="nav-heading">Billing</p>
      <ul class="nav flex-column">
{v1_navlist([("/admin/subscription", "Subscription", "card", ""), ("/admin/invoices", "Invoices", "file", "")])}
      </ul>
    </nav>
    <div class="sidebar-footer"><a href="https://help.keyline.example">Help center</a> · <a href="https://status.keyline.example">System status</a></div>
  </aside>
  <div class="main-panel">
    <nav class="navbar navbar-light bg-white">
      <ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="/admin">Admin</a></li>
        <li class="breadcrumb-item active" aria-current="page">Users</li>
      </ol>
      <form class="navbar-search ml-auto" role="search"><input class="form-control form-control-sm" type="search" placeholder="Search admin…" aria-label="Search admin"></form>
      <ul class="navbar-nav">
        <li class="nav-item"><a class="nav-link" href="https://help.keyline.example"><i class="ico ico-help-circle"></i><span class="sr-only">Help</span></a></li>
        <li class="nav-item"><a class="nav-link" href="/admin/notifications"><i class="ico ico-bell"></i><span class="badge badge-danger">2</span><span class="sr-only">Notifications</span></a></li>
        <li class="nav-item dropdown"><a class="nav-link dropdown-toggle" href="#" data-toggle="dropdown" aria-expanded="false"><span class="avatar avatar-xs bg-indigo">RC</span> Rhea Castellanos</a></li>
      </ul>
    </nav>
    <div class="content container-fluid">
      <div class="page-heading">
        <div>
          <h1 class="h3">Users</h1>
          <p class="text-muted">Manage who can access Halcyon Freight Co. workspaces and what they can do.</p>
        </div>
        <div class="page-actions">
          <button type="button" class="btn btn-outline-secondary"><i class="ico ico-download"></i> Export CSV</button>
          <button type="button" class="btn btn-primary" data-action="invite" data-toggle="modal" data-target="#invite-modal"{T("t1")}><i class="ico ico-plus"></i> Invite user</button>
        </div>
      </div>
      <div class="row stats-row">
        <div class="col"><div class="stat-card"><div class="stat-label">Members</div><div class="stat-value">128</div></div></div>
        <div class="col"><div class="stat-card"><div class="stat-label">Pending invites</div><div class="stat-value">6</div></div></div>
        <div class="col"><div class="stat-card"><div class="stat-label">Admins</div><div class="stat-value">9</div></div></div>
        <div class="col"><div class="stat-card"><div class="stat-label">Seats available</div><div class="stat-value">22</div></div></div>
      </div>
      <div class="card users-card">
        <div class="card-header">
          <ul class="nav nav-tabs card-header-tabs status-tabs" role="tablist">
            <li class="nav-item" role="presentation"><button class="nav-link active" type="button" role="tab" aria-selected="true">All <span class="badge badge-light">134</span></button></li>
            <li class="nav-item" role="presentation"><button class="nav-link" type="button" role="tab" aria-selected="false">Active <span class="badge badge-light">119</span></button></li>
            <li class="nav-item" role="presentation"><button class="nav-link" type="button" role="tab" aria-selected="false"{T("t5")}>Invited <span class="badge badge-light">6</span></button></li>
            <li class="nav-item" role="presentation"><button class="nav-link" type="button" role="tab" aria-selected="false">Suspended <span class="badge badge-light">9</span></button></li>
          </ul>
        </div>
        <div class="card-body">
          <div class="table-toolbar">
            <input type="search" id="user-search" class="form-control" placeholder="Search by name or email" aria-label="Search users">
            <select id="role-filter" class="custom-select" aria-label="Filter by role"><option selected>All roles</option><option>Owner</option><option>Admin</option><option>Manager</option><option>Member</option><option>Guest</option></select>
            <select id="team-filter" class="custom-select" aria-label="Filter by team"><option selected>All teams</option>{"".join(f"<option>{amp(t)}</option>" for t in teams)}</select>
          </div>
          <table class="table table-hover users-table" id="users-table">
            <thead>
              <tr><th><input class="form-check-input" type="checkbox" aria-label="Select all users"></th><th>Name</th><th>Role</th><th>Team</th><th>Last active</th><th>Status</th><th><span class="sr-only">Actions</span></th></tr>
            </thead>
            <tbody>
{chr(10).join(v1_rows)}
            </tbody>
          </table>
        </div>
        <div class="card-footer">
          <span class="text-muted">Showing 1–10 of 134 users</span>
          <nav aria-label="Users pagination">
            <ul class="pagination pagination-sm">
              <li class="page-item disabled"><a class="page-link" href="#" tabindex="-1">Previous</a></li>
              <li class="page-item active"><a class="page-link" href="?page=1">1</a></li>
              <li class="page-item"><a class="page-link" href="?page=2">2</a></li>
              <li class="page-item"><a class="page-link" href="?page=3">3</a></li>
              <li class="page-item"><a class="page-link" href="?page=14">14</a></li>
              <li class="page-item"><a class="page-link" href="?page=2">Next</a></li>
            </ul>
          </nav>
        </div>
      </div>
    </div>
    <footer class="footer">© 2026 Keyline Software, Inc. · <a href="/legal/privacy">Privacy</a> · <a href="/legal/terms">Terms</a> · Admin console v3.12</footer>
  </div>
</div>
<div class="modal fade" id="invite-modal" tabindex="-1" aria-labelledby="invite-modal-title" aria-hidden="true">
  <div class="modal-dialog modal-dialog-centered">
    <div class="modal-content">
      <form id="invite-form" action="/admin/users/invite" method="post">
        <div class="modal-header">
          <h5 class="modal-title" id="invite-modal-title">Invite users</h5>
          <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">×</span></button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label for="invite-emails">Email addresses</label>
            <textarea id="invite-emails" name="emails" class="form-control" rows="3" placeholder="name@{dom}, …"></textarea>
            <small class="form-text text-muted">Separate multiple addresses with commas.</small>
          </div>
          <div class="form-row">
            <div class="form-group col-md-6">
              <label for="invite-role">Role</label>
              <select id="invite-role" name="role" class="custom-select"{T("t2")}><option value="member" selected>Member</option><option value="manager">Manager</option><option value="admin">Admin</option><option value="guest">Guest</option></select>
            </div>
            <div class="form-group col-md-6">
              <label for="invite-team">Team</label>
              <select id="invite-team" name="team" class="custom-select"><option value="">No team</option>{"".join(f"<option>{amp(t)}</option>" for t in teams[:6])}</select>
            </div>
          </div>
          <div class="form-check">
            <input class="form-check-input" type="checkbox" id="invite-require-sso" name="require_sso" checked>
            <label class="form-check-label" for="invite-require-sso">Require single sign-on</label>
          </div>
          <div class="form-group">
            <label for="invite-message">Personal message <span class="text-muted">(optional)</span></label>
            <textarea id="invite-message" name="message" class="form-control" rows="2"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-light" data-dismiss="modal">Cancel</button>
          <button type="submit" class="btn btn-primary"{T("t6")}>Send invite</button>
        </div>
      </form>
    </div>
  </div>
</div>
'''
    v1 = page("Users · Keyline Admin", v1_body, css=v1_css)

    # ------------------------------------------------------------------ v2 (Tailwind UI app shell)
    role_badge = {
        "Owner": "bg-purple-50 text-purple-700 ring-purple-700/10",
        "Admin": "bg-green-50 text-green-700 ring-green-600/20",
        "Manager": "bg-blue-50 text-blue-700 ring-blue-700/10",
        "Member": "bg-gray-50 text-gray-600 ring-gray-500/10",
        "Guest": "bg-yellow-50 text-yellow-800 ring-yellow-600/20",
    }
    nav_groups = [
        ("Workspace", [("/admin/overview", "Overview", "home"), ("/admin/members", "Members", "users"),
                       ("/admin/teams", "Teams", "layers"), ("/admin/groups", "Groups", "grid"),
                       ("/admin/apps", "Apps", "plug")]),
        ("Security &amp; compliance", [("/admin/security/audit-log", "Audit log", "list"),
                                       ("/admin/security/sso", "Single sign-on", "lock"),
                                       ("/admin/security/roles", "Roles &amp; permissions", "shield"),
                                       ("/admin/security/passwords", "Password policy", "lock"),
                                       ("/admin/security/tokens", "API tokens", "terminal")]),
        ("Billing", [("/admin/billing/plan", "Plan &amp; seats", "card"), ("/admin/billing/invoices", "Invoices", "dollar")]),
    ]

    def tw_nav(mobile):
        groups = []
        for heading, items in nav_groups:
            lis = []
            for href, label, ic in items:
                cur = href == "/admin/members"
                cls = ("group flex gap-x-3 rounded-md p-2 text-sm/6 font-semibold "
                       + ("bg-gray-800 text-white" if cur else "text-gray-400 hover:bg-gray-800 hover:text-white"))
                aria = ' aria-current="page"' if cur else ""
                mark = T("t4") if (not mobile and label == "Audit log") else ""
                lis.append(f'                <li><a href="{href}" class="{cls}"{aria}{mark}>{icon(ic, "size-6 shrink-0", style="hero")}{label}</a></li>')
            groups.append(f'''            <li>
              <div class="text-xs/6 font-semibold text-gray-400">{heading}</div>
              <ul role="list" class="-mx-2 mt-2 space-y-1">
{chr(10).join(lis)}
              </ul>
            </li>''')
        return f'''        <nav class="flex flex-1 flex-col" aria-label="Admin">
          <ul role="list" class="flex flex-1 flex-col gap-y-7">
{chr(10).join(groups)}
            <li class="mt-auto"><a href="/admin/settings" class="group -mx-2 flex gap-x-3 rounded-md p-2 text-sm/6 font-semibold text-gray-400 hover:bg-gray-800 hover:text-white">{icon("settings", "size-6 shrink-0", style="hero")}Settings</a></li>
          </ul>
        </nav>'''

    def card(uid, name, role, team, last, status, colour):
        is_t = name == target_user
        if status == "Invited":
            sub = f'{amp(team)} · Invitation sent Nov 3'
        elif status == "Suspended":
            sub = f'{amp(team)} · Suspended Oct 30'
        else:
            sub = f'{amp(team)} · {"Online now" if last == "Active now" else "Active " + last.lower() if "ago" in last or last == "Yesterday" else "Last seen " + last}'
        return f'''          <li class="col-span-1 divide-y divide-gray-200 rounded-lg bg-white shadow">
            <div class="flex w-full items-center justify-between space-x-6 p-6">
              <div class="flex-1 truncate">
                <div class="flex items-center space-x-3">
                  <h3 class="truncate text-sm font-medium text-gray-900">{name}</h3>
                  <span class="inline-flex shrink-0 items-center rounded-full px-1.5 py-0.5 text-xs font-medium ring-1 ring-inset {role_badge[role]}">{role}</span>
                </div>
                <p class="mt-1 truncate text-sm text-gray-500">{email(name)}</p>
                <p class="mt-1 text-xs text-gray-400">{sub}</p>
              </div>
              <span class="inline-flex size-10 shrink-0 items-center justify-center rounded-full bg-{colour}-500"><span class="text-sm font-medium text-white">{initials(name)}</span></span>
            </div>
            <div class="-mt-px flex divide-x divide-gray-200">
              <div class="flex w-0 flex-1"><a href="mailto:{email(name)}" class="relative -mr-px inline-flex w-0 flex-1 items-center justify-center gap-x-3 rounded-bl-lg border border-transparent py-4 text-sm font-semibold text-gray-900">{icon("mail", "size-5 text-gray-400", style="hero")}Email</a></div>
              <div class="-ml-px flex w-0 flex-1"><a href="/admin/members/{uid}" class="relative inline-flex w-0 flex-1 items-center justify-center gap-x-3 border border-transparent py-4 text-sm font-semibold text-gray-900">{icon("settings", "size-5 text-gray-400", style="hero")}Manage</a></div>
              <div class="relative flex flex-none items-center px-4">
                <button type="button" class="-m-2.5 block p-2.5 text-gray-500 hover:text-gray-900" aria-haspopup="menu" aria-expanded="false"{t_if(is_t, "t3")}><span class="sr-only">Open options</span>{icon("more-v", "size-5", style="hero")}</button>
              </div>
            </div>
          </li>'''

    cards = sorted(users, key=lambda u: u[1])
    role_opts = '<option value="member" selected>Member</option><option value="manager">Manager</option><option value="admin">Admin</option><option value="guest">Guest</option>'
    sel_cls = ("col-start-1 row-start-1 w-full appearance-none rounded-md bg-white py-1.5 pl-3 pr-8 text-base text-gray-900 "
               "outline outline-1 -outline-offset-1 outline-gray-300 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-600 sm:text-sm/6")
    chev = icon("chevron-down", "pointer-events-none col-start-1 row-start-1 mr-2 size-5 self-center justify-self-end text-gray-500 sm:size-4", style="hero")
    logo = '<span class="inline-flex size-8 items-center justify-center rounded-md bg-indigo-500 font-bold text-white">K</span><span class="ml-3 text-sm font-semibold text-white">Keyline Admin</span>'

    v2_body = f'''
<div class="min-h-full">
  <div class="relative z-50 lg:hidden" role="dialog" aria-modal="true" hidden>
    <div class="fixed inset-0 bg-gray-900/80" aria-hidden="true"></div>
    <div class="fixed inset-0 flex">
      <div class="relative mr-16 flex w-full max-w-xs flex-1">
        <div class="absolute left-full top-0 flex w-16 justify-center pt-5">
          <button type="button" class="-m-2.5 p-2.5"><span class="sr-only">Close sidebar</span>{icon("x", "size-6 text-white", style="hero")}</button>
        </div>
        <div class="flex grow flex-col gap-y-5 overflow-y-auto bg-gray-900 px-6 pb-4 ring-1 ring-white/10">
          <div class="flex h-16 shrink-0 items-center">{logo}</div>
{tw_nav(mobile=True)}
        </div>
      </div>
    </div>
  </div>

  <div class="hidden lg:fixed lg:inset-y-0 lg:z-50 lg:flex lg:w-72 lg:flex-col">
    <div class="flex grow flex-col gap-y-5 overflow-y-auto bg-gray-900 px-6 pb-4">
      <div class="flex h-16 shrink-0 items-center">{logo}</div>
      <div class="rounded-md bg-gray-800 px-3 py-2"><p class="text-sm font-medium text-white">Halcyon Freight Co.</p><p class="text-xs text-gray-400">Business · 128 / 150 seats</p></div>
{tw_nav(mobile=False)}
    </div>
  </div>

  <div class="lg:pl-72">
    <div class="sticky top-0 z-40 flex h-16 shrink-0 items-center gap-x-4 border-b border-gray-200 bg-white px-4 shadow-sm sm:gap-x-6 sm:px-6 lg:px-8">
      <button type="button" class="-m-2.5 p-2.5 text-gray-700 lg:hidden"><span class="sr-only">Open sidebar</span>{icon("menu", "size-6", style="hero")}</button>
      <div class="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
        <form class="grid flex-1 grid-cols-1" action="/admin/search" method="GET">
          <input id="search-field" type="search" name="search" aria-label="Search" class="col-start-1 row-start-1 block size-full bg-white pl-8 text-base text-gray-900 outline-none placeholder:text-gray-400 sm:text-sm/6" placeholder="Search members, teams, settings…">
          {icon("search", "pointer-events-none col-start-1 row-start-1 size-5 self-center text-gray-400", style="hero")}
        </form>
        <div class="flex items-center gap-x-4 lg:gap-x-6">
          <notification-bell count="2">
            <template shadowrootmode="open">
              <style>:host{{display:inline-flex}} button{{position:relative;border:0;background:none;color:#9ca3af;padding:10px}} .dot{{position:absolute;top:8px;right:8px;width:8px;height:8px;border-radius:50%;background:#ef4444}}</style>
              <button type="button" part="button" aria-label="View notifications (2 new)">{icon("bell", "", style="hero")}<span class="dot"></span></button>
            </template>
          </notification-bell>
          <div class="hidden lg:block lg:h-6 lg:w-px lg:bg-gray-200" aria-hidden="true"></div>
          <div class="relative">
            <button type="button" class="-m-1.5 flex items-center p-1.5" id="user-menu-button" aria-expanded="false" aria-haspopup="true">
              <span class="sr-only">Open user menu</span>
              <span class="inline-flex size-8 items-center justify-center rounded-full bg-indigo-500 text-sm font-medium text-white">RC</span>
              <span class="hidden lg:flex lg:items-center"><span class="ml-4 text-sm/6 font-semibold text-gray-900" aria-hidden="true">Rhea Castellanos</span>{icon("chevron-down", "ml-2 size-5 text-gray-400", style="hero")}</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <main class="py-10">
      <div class="px-4 sm:px-6 lg:px-8">
        <div class="invisible fixed inset-x-0 top-16 z-30 border-b border-gray-200 bg-white/95 lg:pl-72" aria-hidden="true" data-sticky-actions>
          <div class="flex items-center justify-between px-8 py-2">
            <p class="text-sm font-semibold text-gray-900">Members</p>
            <button type="button" tabindex="-1" class="rounded-md bg-indigo-600 px-2.5 py-1.5 text-sm font-semibold text-white shadow-sm">Invite member</button>
          </div>
        </div>
        <div class="sm:flex sm:items-center">
          <div class="sm:flex-auto">
            <h1 class="text-base font-semibold text-gray-900">Members</h1>
            <p class="mt-2 text-sm text-gray-700">Everyone with access to Halcyon Freight Co., their role, team and when they were last active.</p>
          </div>
          <div class="mt-4 flex gap-x-3 sm:ml-16 sm:mt-0 sm:flex-none">
            <button type="button" class="inline-flex items-center gap-x-1.5 rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50">{icon("download", "-ml-0.5 size-5 text-gray-400", style="hero")}Export</button>
            <div class="inline-flex rounded-md shadow-sm">
              <button type="button" class="relative inline-flex items-center gap-x-1.5 rounded-l-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-500 focus:z-10"{T("t1")}>{icon("user-plus", "-ml-0.5 size-5", style="hero")}Invite member</button>
              <div class="relative -ml-px block">
                <button type="button" class="relative inline-flex items-center rounded-r-md bg-indigo-600 px-2 py-2 text-white hover:bg-indigo-500 focus:z-10" aria-expanded="false" aria-haspopup="true"><span class="sr-only">More invite options</span>{icon("chevron-down", "size-5", style="hero")}</button>
                <div class="absolute right-0 z-10 mt-2 w-56 origin-top-right rounded-md bg-white shadow-lg ring-1 ring-black/5 focus:outline-none" role="menu" aria-orientation="vertical" hidden>
                  <div class="py-1" role="none">
                    <button type="button" role="menuitem" class="block w-full px-4 py-2 text-left text-sm text-gray-700">Invite users via CSV</button>
                    <button type="button" role="menuitem" class="block w-full px-4 py-2 text-left text-sm text-gray-700">Copy invite link</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <dl class="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-4">
          <div class="overflow-hidden rounded-lg bg-white px-4 py-5 shadow sm:p-6"><dt class="truncate text-sm font-medium text-gray-500">Members</dt><dd class="mt-1 text-3xl font-semibold tracking-tight text-gray-900">128</dd></div>
          <div class="overflow-hidden rounded-lg bg-white px-4 py-5 shadow sm:p-6"><dt class="truncate text-sm font-medium text-gray-500">Pending invitations</dt><dd class="mt-1 text-3xl font-semibold tracking-tight text-gray-900">6</dd></div>
          <div class="overflow-hidden rounded-lg bg-white px-4 py-5 shadow sm:p-6"><dt class="truncate text-sm font-medium text-gray-500">Admins &amp; owners</dt><dd class="mt-1 text-3xl font-semibold tracking-tight text-gray-900">10</dd></div>
          <div class="overflow-hidden rounded-lg bg-white px-4 py-5 shadow sm:p-6"><dt class="truncate text-sm font-medium text-gray-500">Seats left</dt><dd class="mt-1 text-3xl font-semibold tracking-tight text-gray-900">22</dd></div>
        </dl>

        <div class="mt-8">
          <div class="sm:hidden">
            <select aria-label="Select a tab" class="{sel_cls}"><option selected>All</option><option>Active</option><option>Suspended</option><option>Invited</option></select>
          </div>
          <div class="hidden sm:block">
            <div class="border-b border-gray-200">
              <nav class="-mb-px flex space-x-8" aria-label="Tabs">
                <a href="?status=all" class="flex whitespace-nowrap border-b-2 border-indigo-500 px-1 py-4 text-sm font-medium text-indigo-600" aria-current="page">All <span class="ml-3 rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-medium text-indigo-600">134</span></a>
                <a href="?status=active" class="flex whitespace-nowrap border-b-2 border-transparent px-1 py-4 text-sm font-medium text-gray-500 hover:border-gray-200 hover:text-gray-700">Active <span class="ml-3 rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-900">119</span></a>
                <a href="?status=suspended" class="flex whitespace-nowrap border-b-2 border-transparent px-1 py-4 text-sm font-medium text-gray-500 hover:border-gray-200 hover:text-gray-700">Suspended <span class="ml-3 rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-900">9</span></a>
                <a href="?status=invited" class="flex whitespace-nowrap border-b-2 border-transparent px-1 py-4 text-sm font-medium text-gray-500 hover:border-gray-200 hover:text-gray-700"{T("t5")}>Invited <span class="ml-3 rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-900">6</span></a>
              </nav>
            </div>
          </div>
        </div>

        <div class="mt-4 flex flex-wrap items-center gap-3">
          <div class="grid w-full grid-cols-1 sm:max-w-xs">
            <input type="search" name="q" aria-label="Filter members" placeholder="Filter by name or email" class="col-start-1 row-start-1 block w-full rounded-md bg-white py-1.5 pl-9 pr-3 text-sm text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300">
            {icon("search", "pointer-events-none col-start-1 row-start-1 ml-3 size-4 self-center text-gray-400", style="hero")}
          </div>
          <div class="grid grid-cols-1"><select name="role" aria-label="Role" class="{sel_cls}"><option selected>Any role</option><option>Owner</option><option>Admin</option><option>Manager</option><option>Member</option><option>Guest</option></select>{chev}</div>
          <div class="grid grid-cols-1"><select name="team" aria-label="Team" class="{sel_cls}"><option selected>Any team</option>{"".join(f"<option>{amp(t)}</option>" for t in sorted(teams))}</select>{chev}</div>
        </div>

        <ul role="list" class="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
{chr(10).join(card(*u) for u in cards)}
        </ul>

        <nav class="mt-8 flex items-center justify-between border-t border-gray-200 px-4 sm:px-0" aria-label="Pagination">
          <div class="-mt-px flex w-0 flex-1"><a href="#" class="inline-flex items-center border-t-2 border-transparent pr-1 pt-4 text-sm font-medium text-gray-500">{icon("chevron-left", "mr-3 size-5 text-gray-400", style="hero")}Previous</a></div>
          <div class="hidden md:-mt-px md:flex">
            <a href="?page=1" class="inline-flex items-center border-t-2 border-indigo-500 px-4 pt-4 text-sm font-medium text-indigo-600" aria-current="page">1</a>
            <a href="?page=2" class="inline-flex items-center border-t-2 border-transparent px-4 pt-4 text-sm font-medium text-gray-500">2</a>
            <a href="?page=3" class="inline-flex items-center border-t-2 border-transparent px-4 pt-4 text-sm font-medium text-gray-500">3</a>
            <span class="inline-flex items-center border-t-2 border-transparent px-4 pt-4 text-sm font-medium text-gray-500">…</span>
            <a href="?page=14" class="inline-flex items-center border-t-2 border-transparent px-4 pt-4 text-sm font-medium text-gray-500">14</a>
          </div>
          <div class="-mt-px flex w-0 flex-1 justify-end"><a href="?page=2" class="inline-flex items-center border-t-2 border-transparent pl-1 pt-4 text-sm font-medium text-gray-500">Next{icon("chevron-right", "ml-3 size-5 text-gray-400", style="hero")}</a></div>
        </nav>
      </div>
    </main>
    <footer class="border-t border-gray-200 px-8 py-6 text-xs text-gray-500 lg:pl-8">© 2026 Keyline Software, Inc. · <a href="/legal/privacy" class="hover:text-gray-700">Privacy</a> · <a href="/legal/terms" class="hover:text-gray-700">Terms</a></footer>
  </div>
</div>

<div class="relative z-50" role="dialog" aria-modal="true" aria-labelledby="headlessui-dialog-title-:r5:" id="headlessui-dialog-:r4:" hidden>
  <div class="fixed inset-0 bg-gray-500/75 transition-opacity" aria-hidden="true"></div>
  <div class="fixed inset-0 z-10 w-screen overflow-y-auto">
    <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
      <div class="relative transform overflow-hidden rounded-lg bg-white px-4 pb-4 pt-5 text-left shadow-xl sm:my-8 sm:w-full sm:max-w-lg sm:p-6">
        <div class="flex items-start justify-between">
          <h3 class="text-base font-semibold text-gray-900" id="headlessui-dialog-title-:r5:">Invite members</h3>
          <button type="button" class="rounded-md bg-white text-gray-400 hover:text-gray-500"><span class="sr-only">Close</span>{icon("x", "size-6", style="hero")}</button>
        </div>
        <div class="mt-4 border-b border-gray-200">
          <div class="-mb-px flex space-x-6" role="tablist" aria-orientation="horizontal">
            <button type="button" role="tab" id="headlessui-tabs-tab-:r6:" aria-selected="true" class="border-b-2 border-indigo-500 py-2 text-sm font-medium text-indigo-600">By email</button>
            <button type="button" role="tab" id="headlessui-tabs-tab-:r7:" aria-selected="false" class="border-b-2 border-transparent py-2 text-sm font-medium text-gray-500">Bulk upload (CSV)</button>
          </div>
        </div>
        <form id="headlessui-tabs-panel-:r8:" role="tabpanel" class="mt-5 space-y-5">
          <div>
            <label for="emails-:r9:" class="block text-sm/6 font-medium text-gray-900">Email addresses</label>
            <div class="mt-2"><textarea id="emails-:r9:" name="emails" rows="3" placeholder="name@{dom}" class="block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300 sm:text-sm/6"></textarea></div>
            <p class="mt-2 text-sm text-gray-500">Separate addresses with commas or new lines.</p>
          </div>
          <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label for="team-:ra:" class="block text-sm/6 font-medium text-gray-900">Team</label>
              <div class="mt-2 grid grid-cols-1"><select id="team-:ra:" name="teamId" class="{sel_cls}"><option value="">No team</option>{"".join(f"<option>{amp(t)}</option>" for t in teams[:6])}</select>{chev}</div>
            </div>
            <div>
              <label for="role-:rb:" class="block text-sm/6 font-medium text-gray-900">Role</label>
              <div class="mt-2 grid grid-cols-1"><select id="role-:rb:" name="roleId" class="{sel_cls}"{T("t2")}>{role_opts}</select>{chev}</div>
            </div>
          </div>
          <div class="flex items-center justify-between">
            <span class="flex grow flex-col"><span class="text-sm/6 font-medium text-gray-900">Require single sign-on</span><span class="text-sm text-gray-500">Invitees must sign in with Halcyon SSO.</span></span>
            <button type="button" role="switch" aria-checked="true" aria-label="Require single sign-on" class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent bg-indigo-600"><span aria-hidden="true" class="pointer-events-none inline-block size-5 translate-x-5 rounded-full bg-white shadow ring-0"></span></button>
          </div>
          <div class="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3">
            <button type="submit" class="inline-flex w-full justify-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 sm:col-start-2"{T("t6")}>Send invite</button>
            <button type="button" class="mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 sm:col-start-1 sm:mt-0">Cancel</button>
          </div>
        </form>
        <form id="headlessui-tabs-panel-:rc:" role="tabpanel" class="mt-5 space-y-5" hidden>
          <div>
            <label for="csv-:rd:" class="block text-sm/6 font-medium text-gray-900">CSV file</label>
            <input id="csv-:rd:" name="file" type="file" accept=".csv" class="mt-2 block w-full text-sm text-gray-900">
            <p class="mt-2 text-sm text-gray-500">One address per row; optional columns: team, role.</p>
          </div>
          <div>
            <label for="csv-role-:re:" class="block text-sm/6 font-medium text-gray-900">Default role</label>
            <div class="mt-2 grid grid-cols-1"><select id="csv-role-:re:" name="roleId" class="{sel_cls}">{role_opts}</select>{chev}</div>
          </div>
          <div class="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3">
            <button type="submit" class="inline-flex w-full justify-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 sm:col-start-2">Send invite</button>
            <button type="button" class="mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 sm:col-start-1 sm:mt-0">Cancel</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</div>
'''
    v2 = page("Members · Keyline Admin", v2_body, body_attrs=' class="h-full bg-gray-50"',
              head='<link rel="icon" href="/favicon.svg">\n')

    targets = [
        tgt("t1", "Primary 'Invite user' button in the Users page header",
            '.page-actions button[data-action="invite"]',
            "//button[contains(normalize-space(),'Invite user')]",
            ["class-obfuscation", "copy-change", "attribute-churn", "wrapper-divs", "decoy"]),
        tgt("t2", "Role select inside the invite-user dialog (single-invite form)",
            "#invite-role",
            "//form[@id='invite-form']//select[@name='role']",
            ["id-change", "attribute-churn", "class-obfuscation", "wrapper-divs", "sibling-reorder", "decoy"]),
        tgt("t3", "Icon-only row-actions (kebab) button of user Priya Raman",
            "#users-table tbody tr:nth-child(3) .btn-icon",
            "//button[@aria-label='More actions for Priya Raman']",
            ["tag-change", "structure-move", "sibling-reorder", "attribute-churn", "class-obfuscation", "decoy"]),
        tgt("t4", "'Audit log' link in the admin sidebar navigation",
            '.sidebar-nav a.nav-link[href="/admin/audit-log"]',
            "//nav[@aria-label='Admin']//a[normalize-space()='Audit log']",
            ["class-obfuscation", "sibling-reorder", "attribute-churn", "structure-move", "decoy"]),
        tgt("t5", "'Invited' status tab above the user list",
            ".status-tabs li:nth-child(3) > button",
            "//ul[contains(@class,'status-tabs')]//button[starts-with(normalize-space(),'Invited')]",
            ["tag-change", "sibling-reorder", "class-obfuscation", "attribute-churn"]),
        tgt("t6", "'Send invite' submit button of the invite-user dialog",
            "#invite-modal .modal-footer .btn-primary",
            "//div[@id='invite-modal']//button[@type='submit']",
            ["id-change", "class-obfuscation", "wrapper-divs", "sibling-reorder", "decoy"]),
    ]
    m = meta(
        "dashboard-02", "Admin console — user management (Keyline Admin)",
        ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change", "copy-change",
         "tag-change", "attribute-churn", "structure-move", "insertion"],
        "v1 is a Bootstrap 4 admin template (icon-font nav, users <table>, Bootstrap modal). v2 is a Tailwind UI app shell: "
        "the sidebar is regrouped ('Audit log' moves to the top of a new 'Security & compliance' group) and duplicated in a "
        "hidden mobile off-canvas drawer; 'Users' becomes 'Members'; the user table becomes a card grid sorted by name with "
        "sr-only 'Open options' kebab buttons; status tabs become links in a new order; 'Invite user' becomes a split button "
        "'Invite member' (its menu contains 'Invite users via CSV') with a hidden sticky-header copy; the modal becomes a "
        "Headless UI dialog with React ids, Team/Role swapped and a hidden CSV tab that repeats the role select and "
        "'Send invite'. The notification bell is a web component with a declarative shadow root.",
        targets,
    )
    return v1, v2, m


# ======================================================================================
# dashboard-03 — DevOps / infrastructure monitoring ("Pulsegrid" for Quillpay production)
# ======================================================================================
@suite
def dashboard_03():
    # name, status, p95, error rate, throughput, 30d uptime, kind
    services = [
        ("api-gateway", "Healthy", "112 ms", "0.04%", "8,420 rps", "99.99%", "Edge"),
        ("checkout-api", "Degraded", "842 ms", "3.8%", "1,240 rps", "99.71%", "Service"),
        ("payments-worker", "Degraded", "1.9 s", "1.2%", "310 jobs/s", "99.82%", "Worker"),
        ("auth-service", "Healthy", "64 ms", "0.01%", "2,980 rps", "100%", "Service"),
        ("search-indexer", "Healthy", "220 ms", "0.00%", "95 docs/s", "99.97%", "Worker"),
        ("notifications", "Healthy", "180 ms", "0.20%", "640 msg/s", "99.95%", "Service"),
        ("postgres-primary", "Healthy", "4 ms", "0.00%", "12.8k qps", "99.99%", "Database"),
        ("postgres-replica-2", "Healthy", "6 ms", "0.00%", "7.1k qps", "99.98%", "Database"),
        ("redis-cache", "Healthy", "0.8 ms", "0.00%", "41k ops/s", "100%", "Cache"),
        ("kafka-broker-3", "Down", "—", "—", "0 msg/s", "98.40%", "Broker"),
        ("cdn-edge", "Healthy", "38 ms", "0.02%", "22k rps", "99.99%", "Edge"),
        ("ml-scoring", "Healthy", "95 ms", "0.10%", "450 rps", "99.93%", "Service"),
    ]
    # id, severity, title, service, age, expr
    alerts = [
        ("7811", "Critical", "5xx rate above 2% on checkout-api", "checkout-api", "34m", "http_5xx_ratio &gt; 0.02"),
        ("7812", "Warning", "Disk usage above 90% on postgres-replica-2", "postgres-replica-2", "52m", "disk_used_pct &gt; 90"),
        ("7809", "Critical", "kafka-broker-3 is unreachable", "kafka-broker-3", "1h 12m", "up == 0"),
        ("7806", "Warning", "p95 latency above 1.5 s on payments-worker", "payments-worker", "1h 40m", "latency_p95_s &gt; 1.5"),
        ("7803", "Warning", "Consumer lag above 50k on orders-events", "kafka-broker-3", "2h 03m", "consumer_lag &gt; 50000"),
        ("7799", "Info", "TLS certificate for api.quillpay.example expires in 14 days", "cdn-edge", "5h", "cert_expiry_days &lt; 15"),
        ("7795", "Warning", "Memory above 85% on ml-scoring-7d9f", "ml-scoring", "6h", "mem_used_pct &gt; 85"),
        ("7790", "Info", "Deploy freeze starts Friday 18:00 UTC", "—", "9h", "calendar"),
    ]
    deploys = [
        ("checkout-api", "v2026.11.05-3", "lucia.ferraro", "13:41 UTC", "Rolled out"),
        ("auth-service", "v4.22.0", "kenji.watanabe", "11:02 UTC", "Rolled out"),
        ("ml-scoring", "v0.18.4", "amara.diallo", "09:57 UTC", "Canary 25%"),
        ("notifications", "v3.9.1", "jon.eriksen", "Yesterday", "Rolled out"),
        ("search-indexer", "v1.40.2", "lucia.ferraro", "Yesterday", "Rolled back"),
    ]
    nav = [("/overview", "Overview"), ("/services", "Services"), ("/alerts", "Alerts"), ("/incidents", "Incidents"),
           ("/logs", "Logs"), ("/traces", "Traces"), ("/oncall", "On-call")]

    # ------------------------------------------------------------------ v1
    v1_css = """
body{margin:0;background:#0f1218;color:#d7dce5;font:13px/1.5 "IBM Plex Sans",system-ui,sans-serif}
a{color:#7cb7ff}
.topnav{display:flex;align-items:center;gap:20px;height:48px;padding:0 16px;background:#161b24;border-bottom:1px solid #252c38}
.topnav-links a{color:#aeb6c4;text-decoration:none;padding:14px 8px}.topnav-links a.current{color:#fff;box-shadow:inset 0 -2px #4c8dff}
.env-select{background:#1f2632;color:#fff;border:1px solid #303949;border-radius:4px}
.incident-banner{display:flex;align-items:center;gap:12px;padding:10px 16px;background:#3b1d12;color:#ffd7c2;border-bottom:1px solid #7a3417}
.btn{display:inline-block;padding:5px 10px;border-radius:4px;text-decoration:none}.btn-join{background:#ff7a45;color:#1a0b04;font-weight:600}
.overview{padding:16px}
.layout{display:grid;grid-template-columns:1fr 380px;gap:16px}
.tile-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
.service-tile{background:#161b24;border:1px solid #252c38;border-radius:6px;padding:10px}
.status-healthy .status-dot{background:#2ecc71}.status-degraded .status-dot{background:#f5a623}.status-down .status-dot{background:#ff4d4f}
.status-dot{display:inline-block;width:8px;height:8px;border-radius:50%}
.tile-metrics{display:flex;gap:12px;margin:8px 0}.tile-metrics dd{margin:0;color:#fff}
.alerts-panel{background:#161b24;border:1px solid #252c38;border-radius:6px}
.alert-item{display:flex;gap:10px;padding:10px;border-top:1px solid #252c38}
.sev-badge{font-size:11px;padding:1px 6px;border-radius:3px}.sev-critical .sev-badge{background:#ff4d4f;color:#fff}
.btn-ack{background:#263041;color:#fff;border:1px solid #344156;border-radius:4px;padding:3px 8px}
.btn-icon{background:none;border:0;color:#aeb6c4}
.deploys table{width:100%;border-collapse:collapse}.deploys td,.deploys th{padding:6px 8px;border-bottom:1px solid #252c38;text-align:left}
"""

    def v1_tile(name, status, p95, err, rps, up, kind):
        is_t = name == "checkout-api"
        return f'''        <div class="service-tile status-{status.lower()}" data-service="{name}">
          <div class="tile-head"><span class="status-dot"></span><h3 class="service-name">{name}</h3><span class="status-label"{t_if(is_t, "t2")}>{status}</span></div>
          <p class="tile-kind">{kind}</p>
          <dl class="tile-metrics">
            <div><dt>p95</dt><dd>{p95}</dd></div>
            <div><dt>Errors</dt><dd>{err}</dd></div>
            <div><dt>Traffic</dt><dd>{rps}</dd></div>
          </dl>
          {sparkline(wave(20, "pg" + name, 0.5, 0.5), "sparkline")}
          <div class="tile-foot"><span class="uptime">30d uptime {up}</span><a class="tile-link" href="/services/{name}">Details</a></div>
        </div>'''

    def v1_alert(aid, sev, title, svc, age, expr):
        return f'''          <li class="alert-item sev-{sev.lower()}" id="alert-{aid}" data-alert-id="{aid}">
            <span class="sev-badge">{sev}</span>
            <div class="alert-body">
              <p class="alert-title">{title}</p>
              <p class="alert-meta"><span class="alert-service">{svc}</span> · fired {age} ago · <code>{expr}</code></p>
            </div>
            <div class="alert-actions">
              <button type="button" class="btn-ack"{t_if(aid == "7812", "t1")}>Acknowledge</button>
              <button type="button" class="btn-icon btn-silence" aria-label="Silence alert" title="Silence for 1 hour"{t_if(aid == "7811", "t6")}>{icon("bell-off")}</button>
            </div>
          </li>'''

    v1_nav = "\n".join(
        f'      <a href="{h}" class="topnav-link{" current" if h == "/overview" else ""}"{T("t5") if h == "/incidents" else ""}>'
        f'{lab}{" <span class=" + chr(34) + "pill" + chr(34) + ">8</span>" if lab == "Alerts" else ""}</a>' for h, lab in nav)

    v1_body = f'''
<header class="topnav">
  <a class="logo" href="/overview">{icon("activity", "logo-mark")}<span>Pulsegrid</span></a>
  <select id="env-select" class="env-select" aria-label="Environment"{T("t4")}>
    <option value="production" selected>production</option>
    <option value="staging">staging</option>
    <option value="dev">dev</option>
  </select>
  <nav class="topnav-links">
{v1_nav}
  </nav>
  <div class="topnav-right">
    <input type="search" class="topnav-search" placeholder="Search services, hosts, traces…" aria-label="Search">
    <span class="last-updated">Updated 14:32:08 UTC</span>
    <button type="button" class="avatar" aria-label="Account">MO</button>
  </div>
</header>
<div class="incident-banner sev-2" role="alert">
  {icon("alert", "banner-icon")}
  <div class="incident-text"><strong>INC-2291 · SEV-2</strong> Elevated 5xx errors on checkout-api (us-east-1) — <span class="incident-state">Investigating</span> · started 13:58 UTC · IC: Marisol Ortega</div>
  <a class="banner-link" href="/incidents/INC-2291">View incident</a>
  <a class="btn btn-join" href="https://meet.quillpay.example/inc-2291" target="_blank" rel="noopener"{T("t3")}>Join war room</a>
</div>
<main class="overview">
  <div class="overview-header">
    <h1>Production overview</h1>
    <div class="region-tabs" role="tablist">
      <a class="region-tab active" href="?region=us-east-1" role="tab" aria-selected="true">us-east-1</a>
      <a class="region-tab" href="?region=eu-west-1" role="tab" aria-selected="false">eu-west-1</a>
      <a class="region-tab" href="?region=ap-southeast-2" role="tab" aria-selected="false">ap-southeast-2</a>
    </div>
    <label class="refresh">Auto-refresh <select class="refresh-select"><option>Off</option><option selected>30s</option><option>1m</option><option>5m</option></select></label>
  </div>
  <section class="health-summary">
    <span class="summary-item">12 services</span>
    <span class="summary-item ok">9 healthy</span>
    <span class="summary-item warn">2 degraded</span>
    <span class="summary-item crit">1 down</span>
    <span class="summary-item">SLO budget remaining: 61%</span>
  </section>
  <div class="layout">
    <section class="services">
      <h2>Service health</h2>
      <div class="tile-grid">
{chr(10).join(v1_tile(*s) for s in services)}
      </div>
    </section>
    <aside class="alerts-panel">
      <div class="panel-head"><h2>Alerts</h2><span class="panel-count">8 open</span><a href="/alerts">View all</a></div>
      <ul class="alert-feed">
{chr(10).join(v1_alert(*a) for a in alerts)}
      </ul>
    </aside>
  </div>
  <div class="layout">
    <section class="deploys">
      <h2>Recent deploys</h2>
      <table>
        <thead><tr><th>Service</th><th>Version</th><th>Author</th><th>Time</th><th>Status</th></tr></thead>
        <tbody>
{chr(10).join(f'          <tr><td>{s}</td><td><code>{v}</code></td><td>{a}</td><td>{t}</td><td>{st}</td></tr>' for s, v, a, t, st in deploys)}
        </tbody>
      </table>
    </section>
    <section class="oncall">
      <h2>On-call now</h2>
      <ul class="oncall-list">
        <li><span class="oncall-role">Primary</span> Marisol Ortega <span class="oncall-team">SRE</span></li>
        <li><span class="oncall-role">Secondary</span> Kenji Watanabe <span class="oncall-team">Platform</span></li>
        <li><span class="oncall-role">Escalation</span> Payments engineering</li>
      </ul>
      <button type="button" class="btn btn-page">Page on-call</button>
      <a href="/oncall/schedule">View schedule</a>
    </section>
  </div>
</main>
<footer class="footer">Pulsegrid · Quillpay / production · Region us-east-1 · Retention 30 days · <a href="https://docs.pulsegrid.example">Docs</a> · <a href="https://status.pulsegrid.example">Status</a></footer>
'''
    v1 = page("Production overview — Pulsegrid", v1_body, css=v1_css)

    # ------------------------------------------------------------------ v2 (styled-components + web components)
    order = {"Down": 0, "Degraded": 1, "Healthy": 2}
    services2 = sorted(services, key=lambda s: (order[s[1]], s[0]))
    tile_css = (":host{display:block} .tile{background:var(--pg-surface,#171c26);border-radius:8px;padding:12px;"
                "box-shadow:inset 0 0 0 1px #262e3d} .head{display:flex;align-items:center;gap:8px} .dot{width:8px;height:8px;"
                "border-radius:50%} .badge{margin-left:auto;font-size:11px;padding:1px 8px;border-radius:999px} "
                ".metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;margin:10px 0} dd{margin:0;color:#fff}")

    def v2_tile(name, status, p95, err, rps, up, kind):
        is_t = name == "checkout-api"
        st = status.lower()
        return f'''        <service-tile name="{name}" status="{st}">
          <template shadowrootmode="open">
            <style>{tile_css}</style>
            <article class="tile" part="tile">
              <header class="head"><span class="dot dot--{st}"></span><h3 class="name">{name}</h3><span class="badge badge--{st}"{t_if(is_t, "t2")}>{status}</span></header>
              <dl class="metrics">
                <div><dt>p95</dt><dd>{p95}</dd></div>
                <div><dt>Error rate</dt><dd>{err}</dd></div>
                <div><dt>Throughput</dt><dd>{rps}</dd></div>
              </dl>
              {sparkline(wave(20, "pg" + name, 0.5, 0.5), "spark")}
              <footer class="foot"><span>{kind} · 30d {up}</span><a href="/services/{name}">Open</a></footer>
            </article>
          </template>
        </service-tile>'''

    alerts2 = [
        ("01JC8Z4M2Q", "Critical", "Error budget burn rate 14× on checkout-api", "checkout-api", "12m", "slo_burn_rate_1h &gt; 14"),
        ("01JC8V0X7T", "Critical", "5xx rate above 2% on checkout-api", "checkout-api", "34m", "http_5xx_ratio &gt; 0.02"),
        ("01JC8R2B9K", "Critical", "kafka-broker-3 is unreachable", "kafka-broker-3", "1h 12m", "up == 0"),
        ("01JC8YB1D4", "Warning", "Replica lag above 30 s on postgres-replica-2", "postgres-replica-2", "20m", "pg_replication_lag_s &gt; 30"),
        ("01JC8TQ6HN", "Warning", "Disk usage above 90% on postgres-replica-2", "postgres-replica-2", "52m", "disk_used_pct &gt; 90"),
        ("01JC8NF3WA", "Warning", "p95 latency above 1.5 s on payments-worker", "payments-worker", "1h 40m", "latency_p95_s &gt; 1.5"),
        ("01JC8K7PZE", "Warning", "Consumer lag above 50k on orders-events", "kafka-broker-3", "2h 03m", "consumer_lag &gt; 50000"),
        ("01JC85C2RM", "Warning", "Memory above 85% on ml-scoring-7d9f", "ml-scoring", "6h", "mem_used_pct &gt; 85"),
        ("01JC7ZJ0QS", "Info", "TLS certificate for api.quillpay.example expires in 14 days", "cdn-edge", "5h", "cert_expiry_days &lt; 15"),
        ("01JC7S8D1V", "Info", "Deploy freeze starts Friday 18:00 UTC", "—", "9h", "calendar"),
    ]
    sev_short = {"Critical": "CRIT", "Warning": "WARN", "Info": "INFO"}

    def v2_alert(aid, sev, title, svc, age, expr):
        ack_t = t_if(title.startswith("Disk usage above 90%"), "t1")
        sil_t = t_if(title.startswith("5xx rate above 2%"), "t6")
        svc_html = f'<a href="/services/{svc}" class="{sc("MetaLink")}">{svc}</a>' if svc != "—" else "<span>Calendar</span>"
        return f'''            <li class="{sc("AlertRow")}" data-severity="{sev.lower()}" data-alert="{aid}">
              <div class="{sc("SevStripe")}" aria-hidden="true"></div>
              <div class="{sc("AlertMain")}">
                <div class="{sc("AlertHead")}"><span class="{sc("SevPill")}">{sev_short[sev]}</span><h4 class="{sc("AlertTitle")}">{title}</h4></div>
                <div class="{sc("AlertMeta")}">{svc_html}<span>{age}</span><code>{expr}</code></div>
              </div>
              <div class="{sc("AlertActions")}" role="group" aria-label="Alert actions">
                <button type="button" class="{sc("AckButton")}" title="Acknowledge"{ack_t}>Ack</button>
                <span class="{sc("TooltipTrigger")}"><button type="button" class="{sc("IconButton")}" aria-label="Silence for 1h"{sil_t}>{icon("bell-off")}</button></span>
                <button type="button" class="{sc("IconButton")}" aria-label="More alert actions">{icon("more-h")}</button>
              </div>
            </li>'''

    nav2 = [("/overview", "Overview", "home"), ("/incidents", "Incidents", "flag"), ("/alerts", "Alerts", "bell"),
            ("/services", "Services", "server"), ("/logs", "Logs", "terminal"), ("/traces", "Traces", "git"),
            ("/oncall", "On-call", "phone")]

    def v2_nav(mobile=False):
        out = []
        for h, lab, ic in nav2:
            cur = ' aria-current="page"' if h == "/overview" else ""
            mark = T("t5") if (h == "/incidents" and not mobile) else ""
            badge = f'<span class="{sc("NavCount")}">10</span>' if lab == "Alerts" else ""
            out.append(f'        <a href="{h}" class="{sc("NavItem")}"{cur}{mark}>{icon(ic)}<span class="{sc("NavLabel")}">{lab}</span>{badge}</a>')
        return "\n".join(out)

    v2_css = """
:root{--pg-bg:#0c0f15;--pg-surface:#151a23;--pg-border:#242c3a;--pg-text:#dfe4ee;--pg-accent:#5b9dff}
body{margin:0;background:var(--pg-bg);color:var(--pg-text);font:13px/1.5 Inter,system-ui,sans-serif}
"""
    v2_body = f'''
<div id="root">
<div class="{sc("AppFrame")}">
  <aside class="{sc("Sidebar")}">
    <div class="{sc("SidebarHeader")}">
      <a class="{sc("Brand")}" href="/overview">{icon("activity")}<span>Pulsegrid</span></a>
      <div class="{sc("EnvSwitch")}">
        <span class="{sc("EnvDot")}" aria-hidden="true"></span>
        <select class="{sc("EnvSelect")}" name="env" aria-label="Environment"{T("t4")}>
          <option value="production" selected>Production</option>
          <option value="staging">Staging</option>
          <option value="dev">Development</option>
        </select>
      </div>
    </div>
    <nav class="{sc("NavList")}" aria-label="Primary">
{v2_nav()}
    </nav>
    <div class="{sc("SidebarFooter")}"><a href="https://docs.pulsegrid.example">Docs</a><a href="https://status.pulsegrid.example">Status</a></div>
  </aside>
  <div class="{sc("MainColumn")}">
    <header class="{sc("TopBar")}">
      <div class="{sc("Crumbs")}"><span>Quillpay</span>{icon("chevron-right")}<span>Production</span>{icon("chevron-right")}<strong>Overview</strong></div>
      <div class="{sc("SearchBox")}">{icon("search")}<input type="search" placeholder="Search services, hosts, trace IDs" aria-label="Search"></div>
      <span class="{sc("Updated")}">Live · 14:32:08 UTC</span>
      <button type="button" class="{sc("Avatar")}" aria-label="Account menu">MO</button>
    </header>
    <main class="{sc("Content")}">
      <div class="{sc("PageHead")}">
        <h1 class="{sc("PageTitle")}">Production overview</h1>
        <div class="{sc("Segmented")}" role="tablist" aria-label="Region">
          <button type="button" role="tab" aria-selected="true" class="{sc("SegItem")}">us-east-1</button>
          <button type="button" role="tab" aria-selected="false" class="{sc("SegItem")}">eu-west-1</button>
          <button type="button" role="tab" aria-selected="false" class="{sc("SegItem")}">ap-southeast-2</button>
        </div>
        <button type="button" class="{sc("GhostButton")}" aria-pressed="true">{icon("refresh")}Auto-refresh 30s</button>
      </div>
      <section class="{sc("IncidentCallout")}" role="status" aria-live="polite">
        <div class="{sc("CalloutIcon")}">{icon("alert")}</div>
        <div class="{sc("CalloutBody")}">
          <p class="{sc("CalloutTitle")}"><a href="/incidents/INC-2291">INC-2291</a> Elevated 5xx errors on checkout-api</p>
          <p class="{sc("CalloutMeta")}">SEV-2 · Investigating · open 34 min · Incident commander: Marisol Ortega</p>
        </div>
        <div class="{sc("CalloutActions")}">
          <button type="button" class="{sc("GhostButton")}">Post update</button>
          <button type="button" class="{sc("PrimaryButton")}" data-href="https://meet.quillpay.example/inc-2291"{T("t3")}>Join war room</button>
        </div>
      </section>
      <div class="{sc("SummaryBar")}">
        <span class="{sc("SummaryChip")}" data-tone="crit">1 down</span>
        <span class="{sc("SummaryChip")}" data-tone="warn">2 degraded</span>
        <span class="{sc("SummaryChip")}" data-tone="ok">9 healthy</span>
        <span class="{sc("SummaryChip")}">Error budget left 61%</span>
      </div>
      <div class="{sc("TwoColumn")}">
        <section class="{sc("Panel")}" aria-labelledby="svc-heading">
          <div class="{sc("PanelHead")}"><h2 id="svc-heading" class="{sc("PanelTitle")}">Services</h2><span class="{sc("PanelHint")}">sorted by status</span></div>
          <div class="{sc("TileGrid")}">
{chr(10).join(v2_tile(*s) for s in services2)}
          </div>
        </section>
        <section class="{sc("Panel")}" aria-labelledby="alerts-heading">
          <div class="{sc("PanelHead")}"><h2 id="alerts-heading" class="{sc("PanelTitle")}">Firing alerts</h2><span class="{sc("Count")}">10</span><a href="/alerts" class="{sc("PanelLink")}">All alerts</a></div>
          <ul class="{sc("AlertList")}">
{chr(10).join(v2_alert(*a) for a in alerts2)}
          </ul>
        </section>
      </div>
      <div class="{sc("TwoColumn")}">
        <section class="{sc("Panel")}" aria-labelledby="deploy-heading">
          <div class="{sc("PanelHead")}"><h2 id="deploy-heading" class="{sc("PanelTitle")}">Deploys today</h2></div>
          <ol class="{sc("Timeline")}">
{chr(10).join(f'            <li class="{sc("TimelineItem")}"><span class="{sc("TimelineTime")}">{t}</span><strong>{s}</strong> <code>{v}</code> <span>{st}</span> <span class="{sc("Muted")}">by {a}</span></li>' for s, v, a, t, st in deploys)}
          </ol>
        </section>
        <oncall-card schedule="sre-primary">
          <template shadowrootmode="open">
            <style>:host{{display:block;background:#151a23;border-radius:8px;padding:12px}} h2{{font-size:14px;margin:0 0 8px}} button{{margin-top:8px}}</style>
            <h2>On-call</h2>
            <ul class="people">
              <li><span class="role">Primary</span> Marisol Ortega</li>
              <li><span class="role">Secondary</span> Kenji Watanabe</li>
              <li><span class="role">Escalation</span> Payments engineering</li>
            </ul>
            <button type="button" class="page-btn">Page on-call</button>
          </template>
        </oncall-card>
      </div>
    </main>
  </div>
  <aside class="{sc("IncidentDrawer")}" aria-label="Incident INC-2291" hidden>
    <h2>INC-2291 · Elevated 5xx errors on checkout-api</h2>
    <p>Timeline, responders and linked alerts.</p>
    <div class="{sc("DrawerActions")}"><button type="button" class="{sc("PrimaryButton")}">Join war room</button><button type="button" class="{sc("GhostButton")}">Resolve</button></div>
  </aside>
  <nav class="{sc("MobileTabBar")}" aria-label="Mobile" hidden>
{v2_nav(mobile=True)}
  </nav>
</div>
</div>
'''
    v2 = page("Overview · Production — Pulsegrid", v2_body, css=v2_css)

    targets = [
        tgt("t1", "'Acknowledge' button of the alert 'Disk usage above 90% on postgres-replica-2'",
            "#alert-7812 .btn-ack",
            "//li[@data-alert-id='7812']//button[text()='Acknowledge']",
            ["id-change", "copy-change", "sibling-reorder", "insertion", "class-obfuscation", "decoy"]),
        tgt("t2", "Status label ('Degraded') of the checkout-api service tile",
            '.service-tile[data-service="checkout-api"] .status-label',
            "//div[h3='checkout-api']/span[@class='status-label']",
            ["shadow-dom", "sibling-reorder", "class-obfuscation", "attribute-churn", "decoy"]),
        tgt("t3", "'Join war room' action of the active-incident banner (INC-2291)",
            ".incident-banner a.btn-join",
            "//a[normalize-space()='Join war room']",
            ["tag-change", "structure-move", "class-obfuscation", "attribute-churn", "decoy"]),
        tgt("t4", "Environment switcher select (production/staging/dev)",
            "select#env-select",
            "//select[@aria-label='Environment']",
            ["id-change", "structure-move", "copy-change", "class-obfuscation", "wrapper-divs"]),
        tgt("t5", "'Incidents' item of the primary navigation",
            '.topnav-links a[href="/incidents"]',
            "//nav[@class='topnav-links']/a[4]",
            ["structure-move", "sibling-reorder", "class-obfuscation", "wrapper-divs", "decoy"]),
        tgt("t6", "Icon-only 'Silence' button of the alert '5xx rate above 2% on checkout-api'",
            "#alert-7811 .btn-silence",
            "//li[@id='alert-7811']//button[@aria-label='Silence alert']",
            ["id-change", "attribute-churn", "wrapper-divs", "sibling-reorder", "insertion", "class-obfuscation"]),
    ]
    m = meta(
        "dashboard-03", "Infrastructure monitoring overview — Pulsegrid (DevOps)",
        ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change", "copy-change",
         "tag-change", "attribute-churn", "structure-move", "insertion"],
        "v2 re-implements the console with styled-components. The horizontal top nav becomes a left sidebar (Incidents "
        "moves up; a hidden mobile tab bar repeats the links) and the environment select moves into the sidebar header. "
        "Each service tile becomes a <service-tile> web component with its own declarative shadow root, sorted by status "
        "(down, degraded, healthy). The incident banner turns into a callout inside the page with a <button> instead of a "
        "link; a hidden incident drawer repeats 'Join war room'. Alerts are re-sorted by severity, get ULID ids, two new "
        "alerts are inserted, 'Acknowledge' becomes 'Ack' and the silence button is wrapped in a tooltip trigger with a new "
        "aria-label. On-call moves into an <oncall-card> shadow root.",
        targets,
    )
    return v1, v2, m


# ======================================================================================
# dashboard-04 — CRM sales-pipeline kanban ("Kestrel CRM" for Brightline Solar)
# ======================================================================================
@suite
def dashboard_04():
    owners = {"TN": "Tomasz Nowak", "AB": "Aisha Bello", "RM": "Rafael Mendes", "HL": "Hannah Lindqvist",
              "OG": "Owen Gallagher"}
    # id, title, company, value, close, owner, tag
    stages = [
        ("lead", "Lead", 8, "$412,600", [
            ("1031", "Harbor Point Apartments — carport solar", "Harbor Point Property Group", "$48,000", "Dec 12", "AB", "Multifamily"),
            ("1035", "Greyfield Logistics — warehouse roof", "Greyfield Logistics", "$126,500", "Jan 30", "RM", "Industrial"),
            ("1038", "St. Brigid's School — PV + storage", "St. Brigid's Parish School", "$64,200", "Feb 14", "HL", "Education"),
            ("1040", "Copper Kettle Brewing — rooftop", "Copper Kettle Brewing Co.", "$22,800", "Dec 20", "OG", "SMB"),
        ]),
        ("qualified", "Qualified", 7, "$802,300", [
            ("1022", "Lakeview Medical Plaza — 310 kW", "Lakeview Medical Partners", "$388,000", "Jan 15", "TN", "Healthcare"),
            ("1027", "Northfield Self Storage — 4 sites", "Northfield Storage LLC", "$142,000", "Dec 31", "AB", "Commercial"),
            ("1029", "Pinecrest Golf Club — clubhouse array", "Pinecrest Golf Club", "$57,300", "Jan 9", "RM", "Hospitality"),
            ("1033", "Riverbend Credit Union — branch rollout", "Riverbend Credit Union", "$96,000", "Feb 27", "HL", "Finance"),
        ]),
        ("proposal", "Proposal", 6, "$598,150", [
            ("1018", "Altamont Unified — district bus depot", "Altamont Unified School District", "$212,000", "Dec 18", "OG", "Public sector"),
            ("1024", "Meridian Hotels — rooftop array", "Meridian Hospitality Group", "$174,500", "Dec 5", "TN", "Hospitality"),
            ("1026", "Fairhaven Senior Living — canopy", "Fairhaven Senior Living", "$83,750", "Dec 22", "AB", "Healthcare"),
            ("1030", "Delgado Farms — irrigation pumps", "Delgado Family Farms", "$39,900", "Jan 6", "RM", "Agriculture"),
        ]),
        ("negotiation", "Negotiation", 5, "$918,400", [
            ("1012", "Ironwood Data Center — phase 1", "Ironwood Colocation", "$460,000", "Nov 28", "TN", "Industrial"),
            ("1047", "Cobalt Ridge Winery — battery backup", "Cobalt Ridge Vineyards", "$71,400", "Nov 21", "HL", "Agriculture"),
            ("1015", "Westgate Mall — parking canopies", "Westgate Retail REIT", "$298,000", "Dec 15", "OG", "Retail"),
            ("1020", "Bayside Marine Supply — roof + EV", "Bayside Marine Supply", "$44,600", "Nov 30", "AB", "SMB"),
        ]),
        ("won", "Closed won", 5, "$672,100", [
            ("1003", "Summit Cold Storage — 520 kW", "Summit Cold Storage", "$512,000", "Won Oct 29", "RM", "Industrial"),
            ("1008", "Oak Hollow Library — rooftop", "City of Oak Hollow", "$36,200", "Won Oct 22", "HL", "Public sector"),
            ("1009", "Granite Peak Fitness — 2 gyms", "Granite Peak Fitness", "$28,900", "Won Oct 17", "OG", "SMB"),
        ]),
    ]
    summary = [("Total pipeline", "$2,731,450"), ("Weighted value", "$1,229,710"), ("Open deals", "26"),
               ("Avg. deal age", "23 days"), ("Win rate (90 days)", "27%")]

    # ------------------------------------------------------------------ v1
    v1_css = """
*{box-sizing:border-box}
body{margin:0;font:13px/1.4 "Nunito Sans",Helvetica,Arial,sans-serif;color:#2b2f36;background:#eef1f5}
.crm-app{display:flex;min-height:100vh}
.icon-rail{width:56px;background:#1e2a3a;display:flex;flex-direction:column;align-items:center;padding:10px 0;gap:6px}
.rail-item{display:flex;width:40px;height:40px;align-items:center;justify-content:center;border-radius:8px;color:#9fb0c6}
.rail-item.is-active{background:#2f4a6d;color:#fff}.rail-bottom{margin-top:auto}
.workspace{flex:1;display:flex;flex-direction:column;min-width:0}
.board-header{display:flex;justify-content:space-between;align-items:center;padding:14px 20px;background:#fff;border-bottom:1px solid #dde3ea}
.board-tools{display:flex;gap:10px;align-items:center}
.btn-primary{background:#ff6a3d;color:#fff;border:0;border-radius:6px;padding:7px 14px;font-weight:700}
.board{display:flex;gap:12px;padding:16px 20px;overflow-x:auto}
.kanban-column{width:272px;flex:none;background:#e3e8ef;border-radius:8px;padding:8px}
.column-header{display:flex;align-items:center;gap:6px;padding:4px 6px 10px}
.column-count{background:#cfd7e2;border-radius:10px;padding:0 7px;font-weight:700}
.column-total{margin-left:auto;color:#5d6876}
.deal-card{background:#fff;border-radius:6px;padding:10px;margin-bottom:8px;box-shadow:0 1px 2px rgba(16,24,40,.12)}
.deal-title{font-weight:700;color:#1d3b63;text-decoration:none}
.deal-meta{display:flex;justify-content:space-between;margin:6px 0}
.owner-avatar{display:inline-flex;width:22px;height:22px;border-radius:50%;background:#7b8ba1;color:#fff;font-size:10px;align-items:center;justify-content:center}
.quick-actions{display:flex;gap:2px}.qa-btn{border:0;background:none;color:#7b8ba1;padding:3px}
"""
    kpi_css = (":host{display:block;padding:10px 20px;background:#fff;border-bottom:1px solid #dde3ea}"
               ".pipeline-summary{display:flex;gap:28px;margin:0}.summary-item dt{color:#6b7684;font-size:12px}"
               ".summary-item dd{margin:0;font-size:18px;font-weight:700}")

    def v1_card(did, title, company, value, close, owner, tag):
        return f'''            <article class="deal-card" id="deal-{did}" data-deal-id="{did}">
              <a class="deal-title" href="/deals/{did}"{t_if(did == "1024", "t1")}>{title}</a>
              <p class="deal-company">{company}</p>
              <div class="deal-meta"><span class="deal-value">{value}</span><span class="deal-close">{icon("calendar")} {close}</span></div>
              <div class="deal-tags"><span class="tag">{tag}</span></div>
              <div class="deal-footer">
                <span class="owner-avatar" title="{owners[owner]}">{owner}</span>
                <div class="quick-actions">
                  <button type="button" class="qa-btn" aria-label="Log call" title="Log call"{t_if(did == "1047", "t2")}>{icon("phone")}</button>
                  <button type="button" class="qa-btn" aria-label="Send email" title="Send email">{icon("mail")}</button>
                  <button type="button" class="qa-btn" aria-label="More actions" title="More">{icon("more-h")}</button>
                </div>
              </div>
            </article>'''

    def v1_column(key, name, count, total, deals):
        more = count - len(deals)
        return f'''        <section class="kanban-column" data-stage="{key}">
          <header class="column-header">
            <h2>{name}</h2>
            <span class="column-count"{t_if(key == "negotiation", "t3")}>{count}</span>
            <span class="column-total">{total}</span>
            <button type="button" class="column-add" aria-label="Add deal to {name}">{icon("plus")}</button>
          </header>
          <div class="column-cards">
{chr(10).join(v1_card(*d) for d in deals)}
          </div>
          {f'<button type="button" class="show-more">Show {more} more</button>' if more else ""}
        </section>'''

    rail = [("/home", "Home", "home"), ("/pipeline", "Pipeline", "columns"), ("/contacts", "Contacts", "users"),
            ("/companies", "Companies", "building"), ("/activities", "Activities", "calendar"), ("/reports", "Reports", "chart")]
    v1_rail = "\n".join(
        f'    <a class="rail-item{" is-active" if h == "/pipeline" else ""}" href="{h}" aria-label="{lab}" title="{lab}"'
        f'{" aria-current=" + chr(34) + "page" + chr(34) if h == "/pipeline" else ""}{t_if(lab == "Reports", "t5")}>{icon(ic)}</a>'
        for h, lab, ic in rail)

    v1_body = f'''
<div class="crm-app">
  <nav class="icon-rail" aria-label="Primary">
    <a class="rail-logo" href="/home" aria-label="Kestrel CRM home">K</a>
{v1_rail}
    <a class="rail-item rail-bottom" href="/settings" aria-label="Settings" title="Settings">{icon("settings")}</a>
  </nav>
  <div class="workspace">
    <header class="board-header">
      <div class="board-title">
        <h1>Deals</h1>
        <button type="button" class="pipeline-picker" aria-haspopup="listbox">New business pipeline {icon("chevron-down")}</button>
      </div>
      <div class="board-tools">
        <div class="search-box">{icon("search")}<input type="search" placeholder="Search deals, companies, contacts" aria-label="Search deals"></div>
        <label class="filter"><span class="filter-label">Owner</span>
          <select id="owner-filter" name="owner"{T("t6")}>
            <option value="all" selected>Everyone</option>
            <option value="me">Me (Tomasz Nowak)</option>
            <option value="aisha">Aisha Bello</option>
            <option value="rafael">Rafael Mendes</option>
            <option value="hannah">Hannah Lindqvist</option>
            <option value="owen">Owen Gallagher</option>
          </select>
        </label>
        <label class="filter"><span class="filter-label">Close date</span>
          <select id="close-filter" name="close"><option>Any time</option><option>This month</option><option selected>This quarter</option><option>Next quarter</option></select>
        </label>
        <div class="view-toggle" role="group" aria-label="View">
          <button type="button" aria-label="Board view" aria-pressed="true">{icon("columns")}</button>
          <button type="button" aria-label="List view" aria-pressed="false">{icon("list")}</button>
          <button type="button" aria-label="Forecast view" aria-pressed="false">{icon("chart")}</button>
        </div>
        <button type="button" class="btn btn-primary" id="add-deal">{icon("plus")} Add deal</button>
      </div>
    </header>
    <kpi-strip pipeline="new-business">
      <template shadowrootmode="open">
        <style>{kpi_css}</style>
        <dl class="pipeline-summary">
{chr(10).join(f'          <div class="summary-item"><dt>{k}</dt><dd{t_if(k == "Weighted value", "t4")}>{v}</dd></div>' for k, v in summary)}
        </dl>
      </template>
    </kpi-strip>
    <div class="board">
{chr(10).join(v1_column(*s) for s in stages)}
    </div>
    <footer class="crm-footer">Kestrel CRM · Brightline Solar workspace · Pipeline values in USD · <a href="/help/pipeline">How stages are weighted</a></footer>
  </div>
</div>
'''
    v1 = page("Deals · New business — Kestrel CRM", v1_body, css=v1_css)

    # ------------------------------------------------------------------ v2 (emotion + drag-and-drop wrappers)
    def mdate(s):
        months = {"Nov": 11, "Dec": 12, "Jan": 13, "Feb": 14, "Oct": 10}
        parts = s.replace("Won ", "").split()
        return months[parts[0]] * 100 + int(parts[1])

    by_key = {s[0]: s for s in stages}
    qualified = by_key["qualified"][4]
    stages2 = [
        ("lead", "Lead", "#94a3b8", 8, "$412,600", by_key["lead"][4]),
        ("qualified", "Qualified", "#60a5fa", 4, "$530,000", [qualified[0], qualified[1]]),
        ("demo", "Demo scheduled", "#a78bfa", 3, "$272,300", [qualified[2], qualified[3]]),
        ("proposal", "Proposal", "#f59e0b", 6, "$598,150", by_key["proposal"][4]),
        ("negotiation", "Negotiation", "#f97316", 5, "$918,400", by_key["negotiation"][4]),
        ("won", "Closed won", "#22c55e", 5, "$672,100", by_key["won"][4]),
    ]

    def avatar(code, size=20):
        return (f'<k-avatar name="{owners[code]}" size="{size}"><template shadowrootmode="open">'
                f'<span class="avatar" part="avatar" title="{owners[code]}">{code}</span></template></k-avatar>')

    draggable = [0]

    def v2_card(did, title, company, value, close, owner, tag):
        draggable[0] += 1
        return f'''            <div data-rbd-draggable-context-id="1" data-rbd-draggable-id="deal_{did}" tabindex="0" role="button" aria-describedby="rbd-hidden-text-1-hidden-text-{draggable[0]}" class="{emo("draggable")}">
              <article class="{emo("card")}">
                <div class="{emo("cardTop")}">
                  <h3 class="{emo("cardTitle")}"><a href="/deals/{did}" class="{emo("cardLink")}"{t_if(did == "1024", "t1")}>{title}</a></h3>
                  <span class="{emo("amount")}">{value}</span>
                </div>
                <p class="{emo("company")}">{icon("building")} {company}</p>
                <div class="{emo("cardBottom")}">
                  <span class="{emo("chip")}">{tag}</span>
                  <span class="{emo("due")}">{icon("calendar")} {close}</span>
                  {avatar(owner)}
                </div>
                <div class="{emo("hoverBar")}" role="toolbar" aria-label="Quick actions">
                  <button type="button" class="{emo("qa")}" aria-label="Log a call"{t_if(did == "1047", "t2")}>{icon("phone")}</button>
                  <button type="button" class="{emo("qa")}" aria-label="Email contact">{icon("mail")}</button>
                  <button type="button" class="{emo("qa")}" aria-label="Schedule meeting">{icon("calendar")}</button>
                </div>
              </article>
            </div>'''

    def v2_column(key, name, colour, count, total, deals):
        deals = sorted(deals, key=lambda d: mdate(d[4]))
        more = count - len(deals)
        more_html = f'<a href="?stage={key}" class="{emo("showMore")}">Show {more} more</a>' if more else ""
        return f'''        <section class="{emo("column")}" aria-labelledby="col-{key}">
          <header class="{emo("colHeader")}">
            <span class="{emo("stageDot")}" style="background:{colour}"></span>
            <h3 id="col-{key}" class="{emo("colTitle")}">{name}</h3>
            <span class="{emo("colCount")}"{t_if(key == "negotiation", "t3")}>{count}</span>
            <span class="{emo("colSum")}">{total}</span>
          </header>
          <div data-rbd-droppable-id="stage_{key}" data-rbd-droppable-context-id="1" class="{emo("dropzone")}">
{chr(10).join(v2_card(*d) for d in deals)}
          </div>
          <button type="button" class="{emo("colAdd")}">{icon("plus")} Add deal</button>
          {more_html}
        </section>'''

    rail2 = [("/home", "Home", "home"), ("/deals", "Deals", "columns"), ("/reports", "Reports", "chart"),
             ("/inbox", "Inbox", "inbox"), ("/contacts", "Contacts", "users"), ("/companies", "Companies", "building"),
             ("/activities", "Activities", "calendar"), ("/settings", "Settings", "settings")]
    v2_rail = "\n".join(
        f'    <a class="{emo("railItem")}" href="{h}"{" aria-current=" + chr(34) + "page" + chr(34) if h == "/deals" else ""}'
        f'{t_if(lab == "Reports", "t5")}>{icon(ic)}<span class="{emo("railLabel")}">{lab}</span></a>' for h, lab, ic in rail2)
    stats2 = [("Weighted forecast", "$1,229,710", "by stage probability"), ("Open pipeline", "$2,731,450", "26 open deals"),
              ("Win rate · 90d", "27%", "+3 pts vs. prior"), ("Avg. deal age", "23 days", "median 17 days")]

    v2_body = f'''
<div id="root">
<div class="{emo("shell")}">
  <nav class="{emo("rail")}" aria-label="Primary">
    <a class="{emo("railLogo")}" href="/home"><span class="{emo("visuallyHidden")}">Kestrel CRM</span>K</a>
{v2_rail}
  </nav>
  <div class="{emo("page")}">
    <div class="{emo("topbar")}">
      <div class="{emo("titleGroup")}">
        <h1 class="{emo("h1")}">Pipeline</h1>
        <button type="button" class="{emo("pipelineSwitch")}" aria-haspopup="menu">New business {icon("chevron-down")}</button>
      </div>
      <div class="{emo("recent")}">
        <button type="button" class="{emo("ghost")}" aria-haspopup="menu" aria-expanded="false">{icon("clock")} Recently viewed</button>
        <div class="{emo("menu")}" role="menu" hidden>
          <a role="menuitem" href="/deals/1024" class="{emo("menuItem")}">Meridian Hotels — rooftop array</a>
          <a role="menuitem" href="/deals/1012" class="{emo("menuItem")}">Ironwood Data Center — phase 1</a>
          <a role="menuitem" href="/deals/1022" class="{emo("menuItem")}">Lakeview Medical Plaza — 310 kW</a>
        </div>
      </div>
      <button type="button" class="{emo("primary")}">{icon("plus")} New deal</button>
    </div>
    <section class="{emo("stats")}" aria-label="Pipeline summary">
{chr(10).join(f'      <div class="{emo("stat")}"><p class="{emo("statLabel")}">{k}</p><p class="{emo("statValue")}"{t_if(k == "Weighted forecast", "t4")}>{v}</p><p class="{emo("statHint")}">{h}</p></div>' for k, v, h in stats2)}
    </section>
    <div class="{emo("filters")}">
      <div class="{emo("search")}">{icon("search")}<input type="search" placeholder="Search pipeline" aria-label="Search pipeline"></div>
      <div class="{emo("filterGroup")}">
        <button type="button" class="{emo("filterButton")}" aria-haspopup="listbox" aria-expanded="false" aria-label="Filter by owner"{T("t6")}><span class="{emo("avatarStack")}">{avatar("TN", 18)}{avatar("AB", 18)}{avatar("RM", 18)}</span><span>Owner: Everyone</span>{icon("chevron-down")}</button>
        <ul class="{emo("listbox")}" role="listbox" aria-label="Owner" hidden>
          <li role="option" aria-selected="true">Everyone</li>
          {"".join(f'<li role="option" aria-selected="false">{n}</li>' for n in owners.values())}
        </ul>
      </div>
      <button type="button" class="{emo("filterButton")}" aria-haspopup="listbox">Close: This quarter {icon("chevron-down")}</button>
      <button type="button" class="{emo("filterButton")}" aria-haspopup="listbox">Sort: Close date {icon("chevron-down")}</button>
      <div class="{emo("viewSwitch")}" role="radiogroup" aria-label="Layout">
        <button type="button" role="radio" aria-checked="true" class="{emo("viewOption")}">{icon("columns")} Board</button>
        <button type="button" role="radio" aria-checked="false" class="{emo("viewOption")}">{icon("list")} Table</button>
      </div>
    </div>
    <div class="{emo("board")}" data-rbd-droppable-context-id="1">
{chr(10).join(v2_column(*s) for s in stages2)}
    </div>
    <div id="rbd-hidden-text-1-hidden-text-1" style="display:none">Press space bar to start a drag.</div>
  </div>
  <aside class="{emo("forecastDrawer")}" aria-label="Forecast" hidden>
    <h2>Q4 forecast</h2>
    <div class="{emo("stat")}"><p class="{emo("statLabel")}">Weighted pipeline</p><p class="{emo("statValue")}">$1,229,710</p></div>
    <div class="{emo("stat")}"><p class="{emo("statLabel")}">Commit</p><p class="{emo("statValue")}">$684,000</p></div>
  </aside>
  <nav class="{emo("tabbar")}" aria-label="Mobile" hidden>
    <a href="/home">Home</a><a href="/deals" aria-current="page">Deals</a><a href="/reports">Reports</a><a href="/inbox">Inbox</a>
  </nav>
</div>
</div>
'''
    v2_css = """
body{margin:0;font:13px/1.45 "Inter",system-ui,sans-serif;color:#1f2937;background:#f8fafc}
"""
    v2 = page("Pipeline · Kestrel CRM", v2_body, css=v2_css)

    targets = [
        tgt("t1", "Title link of the deal 'Meridian Hotels — rooftop array' in the Proposal column",
            '.kanban-column[data-stage="proposal"] .deal-card:nth-child(2) .deal-title',
            "//section[@data-stage='proposal']//a[normalize-space()='Meridian Hotels — rooftop array']",
            ["class-obfuscation", "wrapper-divs", "sibling-reorder", "insertion", "attribute-churn", "decoy"]),
        tgt("t2", "Icon-only 'Log call' quick action on the deal card 'Cobalt Ridge Winery — battery backup'",
            '#deal-1047 button[aria-label="Log call"]',
            "//article[.//a[normalize-space()='Cobalt Ridge Winery — battery backup']]//button[@title='Log call']",
            ["id-change", "attribute-churn", "wrapper-divs", "sibling-reorder", "class-obfuscation"]),
        tgt("t3", "Deal-count badge of the Negotiation column (5)",
            '[data-stage="negotiation"] .column-count',
            "//h2[text()='Negotiation']/following-sibling::span[@class='column-count']",
            ["class-obfuscation", "tag-change", "insertion", "attribute-churn", "decoy"]),
        tgt("t4", "'Weighted value' figure of the pipeline summary ($1,229,710)",
            ".pipeline-summary .summary-item:nth-child(2) dd",
            "//dt[text()='Weighted value']/following-sibling::dd",
            ["shadow-dom", "tag-change", "copy-change", "sibling-reorder", "class-obfuscation", "decoy"]),
        tgt("t5", "Icon-only 'Reports' link of the left navigation rail",
            'nav.icon-rail a[aria-label="Reports"]',
            "//nav[@aria-label='Primary']/a[7]",
            ["sibling-reorder", "insertion", "attribute-churn", "class-obfuscation", "decoy"]),
        tgt("t6", "Owner filter of the board toolbar",
            "select#owner-filter",
            "//select[@name='owner']",
            ["tag-change", "id-change", "attribute-churn", "class-obfuscation", "wrapper-divs"]),
    ]
    m = meta(
        "dashboard-04", "Sales pipeline kanban board — Kestrel CRM",
        ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change", "copy-change",
         "tag-change", "attribute-churn", "structure-move", "insertion"],
        "v1's pipeline summary lives in a <kpi-strip> web component (declarative shadow root); v2 moves it out into "
        "emotion-styled React markup with <p> values, a reordered layout and the label 'Weighted forecast' (a hidden "
        "forecast drawer repeats the figure). Deal cards are wrapped in react-beautiful-dnd draggables, sorted by close "
        "date, and a new 'Demo scheduled' stage is inserted; card ids are gone and the quick actions become an aria-labelled "
        "hover toolbar ('Log a call'). Owner avatars become <k-avatar> shadow-DOM components. The icon rail gains labels, a "
        "new 'Inbox' item and a new order (a hidden mobile tab bar repeats 'Reports'). The owner <select> becomes a "
        "listbox button. A 'Recently viewed' menu repeats deal titles.",
        targets,
    )
    return v1, v2, m


# ======================================================================================
# dashboard-05 — personal finance / online banking overview ("Copperleaf Bank")
# ======================================================================================
@suite
def dashboard_05():
    # id, name, mask, balance label, balance, kind
    accounts = [
        ("chk-4821", "Everyday Checking", "••4821", "Available balance", "$3,214.56", "Checking"),
        ("sav-7730", "High-Yield Savings", "••7730", "Available balance", "$18,940.12", "Savings"),
        ("sav-7731", "Vacation Fund", "••7731", "Available balance", "$2,450.00", "Savings"),
        ("cc-0193", "Copperleaf Rewards Card", "••0193", "Current balance", "$1,284.40", "Credit card"),
        ("ln-5512", "Auto Loan", "••5512", "Principal remaining", "$11,962.77", "Loan"),
    ]
    # date, weekday, merchant, category, account, amount
    txns = [
        ("Nov 4", "Wednesday", "Juniper Street Grocers", "Groceries", "••0193", "−$86.42"),
        ("Nov 4", "Wednesday", "Northgate Transit", "Transportation", "••4821", "−$2.75"),
        ("Nov 3", "Tuesday", "Sunline Utilities", "Bills &amp; utilities", "••4821", "−$142.18"),
        ("Nov 3", "Tuesday", "Payroll — Ardent Systems", "Income", "••4821", "+$2,840.00"),
        ("Nov 2", "Monday", "Pinecone Coffee Roasters", "Dining out", "••0193", "−$6.80"),
        ("Nov 2", "Monday", "Transfer to Vacation Fund", "Transfer", "••4821", "−$200.00"),
        ("Nov 1", "Sunday", "Riverside Apartments", "Rent", "••4821", "−$1,650.00"),
        ("Oct 31", "Saturday", "Mossgate Pharmacy", "Health", "••0193", "−$23.19"),
        ("Oct 30", "Friday", "Streamline Fiber", "Bills &amp; utilities", "••4821", "−$64.99"),
        ("Oct 30", "Friday", "Interest payment", "Income", "••7730", "+$61.47"),
    ]
    # key, name, spent, limit
    budgets = [("groceries", "Groceries", 86, 600), ("dining", "Dining out", 48, 250), ("transport", "Transportation", 3, 120),
               ("entertainment", "Entertainment", 0, 100), ("shopping", "Shopping", 112, 200),
               ("bills", "Bills &amp; utilities", 207, 320)]
    bills = [("Rewards Card payment", "Nov 18", "$1,284.40"), ("Auto Loan", "Nov 20", "$386.12"),
             ("Streamline Fiber", "Nov 30", "$64.99"), ("Sunline Utilities", "Dec 3", "est. $140.00")]

    # ------------------------------------------------------------------ v1
    v1_css = """
body{margin:0;font:15px/1.5 Georgia,"Times New Roman",serif;color:#1f2a2e;background:#f3f1ec}
.cb-topbar{display:flex;justify-content:space-between;padding:4px 32px;background:#13343b;color:#cfe3df;font:12px Arial,sans-serif}
.cb-topbar a{color:#cfe3df;margin-right:14px}
.cb-header{display:flex;align-items:center;gap:32px;padding:14px 32px;background:#fff;border-bottom:3px solid #b87333;font-family:Arial,sans-serif}
.cb-logo{font-size:22px;font-weight:700;color:#13343b;text-decoration:none}
.cb-mainnav ul{display:flex;gap:22px;list-style:none;margin:0;padding:0}
.cb-mainnav a{color:#13343b;text-decoration:none;font-weight:600}.cb-mainnav a.active{border-bottom:2px solid #b87333}
.cb-main{max-width:1180px;margin:0 auto;padding:24px 32px;font-family:Arial,sans-serif}
.cb-grid{display:grid;grid-template-columns:2fr 1fr;gap:20px}
.cb-card{background:#fff;border:1px solid #ddd6c8;border-radius:4px;padding:18px;margin-bottom:20px}
.account-row{display:flex;justify-content:space-between;padding:12px 0;border-bottom:1px solid #eee7da}
.balance{font-size:20px;font-weight:700}
.cb-btn{padding:9px 16px;border:1px solid #13343b;border-radius:3px;background:#fff;color:#13343b;font-weight:600}
.cb-btn-primary{background:#13343b;color:#fff}
.txn-table{width:100%;border-collapse:collapse}.txn-table td,.txn-table th{padding:8px;border-bottom:1px solid #eee7da;text-align:left}
.txn-table .amount{text-align:right;font-variant-numeric:tabular-nums}.amount.credit{color:#1e7b4f}
.budget-bar{height:8px;background:#ece6da;border-radius:4px}.budget-fill{height:8px;background:#b87333;border-radius:4px}
.cb-footer{padding:24px 32px;background:#13343b;color:#cfe3df;font:12px/1.6 Arial,sans-serif}
"""

    def v1_account(aid, name, mask, label, bal, kind):
        return f'''          <li class="account-row" data-account="{aid}">
            <div class="acct-name"><a href="/accounts/{aid}">{name}</a><span class="acct-mask">{mask}</span><span class="acct-kind">{kind}</span></div>
            <div class="acct-balance"><span class="balance-label">{label}</span><span class="balance"{t_if(aid == "sav-7730", "t2")}>{bal}</span></div>
          </li>'''

    def v1_txn(date, _wd, merchant, cat, acct, amt):
        credit = " credit" if amt.startswith("+") else ""
        return (f'            <tr><td class="txn-date">{date}</td><td class="txn-desc">{merchant}</td><td class="txn-cat">{cat}</td>'
                f'<td class="txn-acct">{acct}</td><td class="amount{credit}"{t_if(merchant == "Sunline Utilities", "t3")}>{amt}</td></tr>')

    def v1_budget(key, name, spent, limit):
        pct = round(100 * spent / limit)
        return f'''          <li class="budget" data-category="{key}">
            <div class="budget-head"><span class="budget-name">{name}</span><button type="button" class="icon-button budget-edit" aria-label="Edit {name} budget"{t_if(key == "dining", "t4")}>{icon("pencil")}</button></div>
            <div class="budget-bar" role="progressbar" aria-valuenow="{pct}" aria-valuemin="0" aria-valuemax="100"><div class="budget-fill" style="width:{pct}%"></div></div>
            <p class="budget-amounts">${spent} spent of ${limit}</p>
          </li>'''

    nav1 = [("/overview", "Overview"), ("/accounts", "Accounts"), ("/transfers", "Payments &amp; transfers"),
            ("/cards", "Cards"), ("/budgets", "Budgets"), ("/statements", "Statements &amp; documents")]
    v1_nav = "\n".join(
        f'        <li><a href="{h}"{" class=" + chr(34) + "active" + chr(34) + " aria-current=" + chr(34) + "page" + chr(34) if h == "/overview" else ""}'
        f'{t_if(h == "/statements", "t5")}>{lab}</a></li>' for h, lab in nav1)

    v1_body = f'''
<div class="cb-topbar">
  <div><a href="/personal">Personal</a><a href="/business">Business</a><a href="/wealth">Wealth management</a></div>
  <div><a href="/locations">Locations</a><a href="/help">Help &amp; support</a><a href="/es" lang="es">Español</a></div>
</div>
<header class="cb-header">
  <a class="cb-logo" href="/overview">Copperleaf Bank</a>
  <nav class="cb-mainnav" aria-label="Main">
    <ul>
{v1_nav}
    </ul>
  </nav>
  <div class="cb-user">
    <button type="button" class="icon-button" aria-label="Secure messages (2 unread)">{icon("mail")}</button>
    <span class="cb-username">Daniela Ortiz</span>
    <a href="/logout" class="cb-logout">Log out</a>
  </div>
</header>
<main class="cb-main">
  <div class="cb-welcome">
    <h1>Good evening, Daniela</h1>
    <p class="cb-lastlogin">Last sign-in: Nov 4, 2026 at 8:12 PM from Portland, OR</p>
  </div>
  <div class="cb-grid">
    <div class="cb-col-main">
      <section class="cb-card accounts-card" aria-labelledby="accounts-heading">
        <div class="card-head"><h2 id="accounts-heading">Accounts</h2><a href="/accounts/open" class="cb-link">Open an account</a></div>
        <ul class="account-list">
{chr(10).join(v1_account(*a) for a in accounts)}
        </ul>
        <div class="accounts-total"><span>Total cash</span> <strong>$24,604.68</strong></div>
      </section>
      <section class="cb-card quick-actions" aria-label="Quick actions">
        <button type="button" id="btn-transfer" class="cb-btn cb-btn-primary" data-testid="quick-transfer"{T("t1")}>Transfer money</button>
        <button type="button" class="cb-btn">Pay a bill</button>
        <button type="button" class="cb-btn">Deposit a check</button>
        <button type="button" class="cb-btn">Send to a friend</button>
      </section>
      <section class="cb-card transactions" aria-labelledby="txn-heading">
        <div class="card-head">
          <h2 id="txn-heading">Recent transactions</h2>
          <div class="txn-filter">
            <label for="txn-account-filter">Account</label>
            <select id="txn-account-filter" name="account"{T("t6")}>
              <option value="all" selected>All accounts</option>
              <option value="chk-4821">Everyday Checking ••4821</option>
              <option value="sav-7730">High-Yield Savings ••7730</option>
              <option value="cc-0193">Copperleaf Rewards Card ••0193</option>
            </select>
          </div>
          <a href="/transactions" class="cb-link">See all</a>
        </div>
        <table class="txn-table">
          <thead><tr><th>Date</th><th>Description</th><th>Category</th><th>Account</th><th class="amount">Amount</th></tr></thead>
          <tbody>
{chr(10).join(v1_txn(*t) for t in txns)}
          </tbody>
        </table>
      </section>
    </div>
    <aside class="cb-col-side">
      <section class="cb-card budgets" aria-labelledby="budgets-heading">
        <div class="card-head"><h2 id="budgets-heading">November budgets</h2><a href="/budgets" class="cb-link">Manage</a></div>
        <ul class="budget-list">
{chr(10).join(v1_budget(*b) for b in budgets)}
        </ul>
      </section>
      <section class="cb-card upcoming" aria-labelledby="bills-heading">
        <h2 id="bills-heading">Upcoming bills</h2>
        <ul class="bill-list">
{chr(10).join(f'          <li class="bill"><span class="bill-name">{n}</span><span class="bill-due">Due {d}</span><span class="bill-amt">{a}</span></li>' for n, d, a in bills)}
        </ul>
        <a href="/transfers/bills" class="cb-link">Manage payees</a>
      </section>
      <section class="cb-card promo">
        <h2>Earn 4.10% APY</h2>
        <p>Grow your savings with a Copperleaf Certificate of Deposit. 12-month term, $500 minimum.</p>
        <a href="/cds" class="cb-btn">Learn more</a>
      </section>
    </aside>
  </div>
</main>
<footer class="cb-footer">
  <nav aria-label="Footer"><a href="/privacy">Privacy &amp; security</a> · <a href="/accessibility">Accessibility</a> · <a href="/fees">Fee schedule</a> · <a href="/contact">Contact us</a></nav>
  <p>Copperleaf Bank, N.A. Deposits insured up to applicable limits. Equal Housing Lender. © 2026 Copperleaf Financial Corp.</p>
</footer>
'''
    v1 = page("Account overview | Copperleaf Bank", v1_body, css=v1_css)

    # ------------------------------------------------------------------ v2 (CSS modules + <account-carousel>)
    def c(mod, local):
        return cm(mod, local)

    accounts2 = [accounts[0], accounts[3], accounts[1], accounts[2], accounts[4]]
    carousel_css = (":host{display:block} .track{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(220px,1fr);gap:12px;"
                    "list-style:none;margin:0;padding:0;overflow-x:auto} .acct{border-radius:14px;padding:16px;background:#fff;"
                    "box-shadow:0 1px 3px rgba(19,52,59,.12)} .amount{font:600 22px/1.2 'Söhne',Arial,sans-serif;margin:2px 0 0}"
                    " .label{margin:12px 0 0;color:#5f6f72;font-size:13px}")

    def slide(aid, name, mask, label, bal, kind):
        return f'''            <li class="slide" data-kind="{kind.lower().replace(" ", "-")}">
              <article class="acct">
                <header class="acct-head"><span class="kind">{kind}</span><span class="mask">{mask}</span></header>
                <h3 class="name"><a href="/accounts/{aid}">{name}</a></h3>
                <p class="label">{label}</p>
                <p class="amount"{t_if(aid == "sav-7730", "t2")}>{bal}</p>
              </article>
            </li>'''

    groups = []
    seen = []
    for t in txns:
        if t[0] not in seen:
            seen.append(t[0])
    for d in seen:
        rows = [t for t in txns if t[0] == d]
        rows = sorted(rows, key=lambda r: not r[5].startswith("+"))  # deposits first within a day
        wd = rows[0][1]
        lis = []
        for date, _wd, merchant, cat, acct, amt in rows:
            kind = "credit" if amt.startswith("+") else "debit"
            lis.append(f'''            <li class="{c("TxnRow", "root")}">
              <span class="{c("TxnRow", "avatar")}" aria-hidden="true">{merchant[0]}</span>
              <div class="{c("TxnRow", "main")}"><p class="{c("TxnRow", "merchant")}">{merchant}</p><p class="{c("TxnRow", "meta")}">{cat} · {acct}</p></div>
              <span class="{c("Amount", "root")} {c("Amount", kind)}"{t_if(merchant == "Sunline Utilities", "t3")}>{amt}</span>
            </li>''')
        groups.append(f'''          <div class="{c("TxnList", "group")}">
            <h3 class="{c("TxnList", "date")}">{wd}, {d}</h3>
            <ul class="{c("TxnList", "rows")}">
{chr(10).join(lis)}
            </ul>
          </div>''')

    budgets2 = sorted(budgets, key=lambda b: -b[2] / b[3])

    def budget2(key, name, spent, limit):
        pct = round(100 * spent / limit)
        return f'''          <li class="{c("BudgetRow", "root")}">
            <div class="{c("BudgetRow", "top")}">
              <span class="{c("BudgetRow", "name")}" id="budget-{key}-name">{name}</span>
              <span class="{c("BudgetRow", "figures")}">${spent} / ${limit}</span>
              <button type="button" class="{c("IconButton", "root")} {c("BudgetRow", "edit")}" aria-label="Edit budget" aria-describedby="budget-{key}-name"{t_if(key == "dining", "t4")}>{icon("pencil")}</button>
            </div>
            <progress class="{c("BudgetRow", "meter")}" max="100" value="{pct}">{pct}%</progress>
          </li>'''

    v2_css = f"""
body{{margin:0;font:15px/1.5 "Söhne",Arial,sans-serif;color:#14282c;background:#f6f5f2}}
.{c("Header", "root")}{{position:sticky;top:0;display:flex;align-items:center;gap:28px;padding:12px 40px;background:#fff;box-shadow:0 1px 0 #e7e2d8}}
.{c("Layout", "grid")}{{display:grid;grid-template-columns:minmax(0,2fr) minmax(280px,1fr);gap:24px;max-width:1240px;margin:0 auto;padding:24px 40px}}
.{c("Card", "root")}{{background:#fff;border-radius:16px;padding:20px;box-shadow:0 1px 3px rgba(19,52,59,.08)}}
.{c("Amount", "credit")}{{color:#1d7a4d}}
"""
    v2_body = f'''
<div id="app">
  <header class="{c("Header", "root")}">
    <a class="{c("Header", "logo")}" href="/overview" aria-label="Copperleaf home"><span class="{c("Header", "mark")}"></span>Copperleaf</a>
    <nav class="{c("MainNav", "root")}" aria-label="Main">
      <a class="{c("MainNav", "link")} {c("MainNav", "active")}" href="/overview" aria-current="page">Overview</a>
      <a class="{c("MainNav", "link")}" href="/accounts">Accounts</a>
      <a class="{c("MainNav", "link")}" href="/cards">Cards</a>
      <a class="{c("MainNav", "link")}" href="/pay">Pay &amp; transfer</a>
      <a class="{c("MainNav", "link")}" href="/budgets">Budgets &amp; goals</a>
      <div class="{c("MainNav", "more")}">
        <button type="button" class="{c("MainNav", "link")}" aria-haspopup="menu" aria-expanded="false">More {icon("chevron-down")}</button>
        <div class="{c("Menu", "panel")}" role="menu" hidden>
          <a role="menuitem" class="{c("Menu", "item")}" href="/documents"{T("t5")}>Statements &amp; documents</a>
          <a role="menuitem" class="{c("Menu", "item")}" href="/rewards">Rewards</a>
          <a role="menuitem" class="{c("Menu", "item")}" href="/settings">Settings</a>
        </div>
      </div>
    </nav>
    <div class="{c("Header", "actions")}">
      <button type="button" class="{c("Button", "root")} {c("Button", "primary")} {c("Header", "cta")}">Move money</button>
      <button type="button" class="{c("IconButton", "root")}" aria-label="Messages, 2 unread">{icon("mail")}</button>
      <button type="button" class="{c("Avatar", "root")}" aria-label="Profile and settings">DO</button>
    </div>
  </header>
  <div class="{c("Layout", "grid")}">
    <main class="{c("Layout", "main")}">
      <div class="{c("Greeting", "root")}">
        <h1 class="{c("Greeting", "title")}">Hi Daniela</h1>
        <p class="{c("Greeting", "sub")}">Here’s where your money stands today.</p>
      </div>
      <section class="{c("Accounts", "root")}" aria-labelledby="accounts-title">
        <div class="{c("Section", "head")}"><h2 id="accounts-title" class="{c("Section", "title")}">Your accounts</h2><span class="{c("Section", "aside")}">Cash $24,604.68</span><a class="{c("Section", "link")}" href="/accounts/open">Open account</a></div>
        <account-carousel aria-label="Your accounts">
          <template shadowrootmode="open">
            <style>{carousel_css}</style>
            <div class="viewport" part="viewport">
              <ul class="track" role="list">
{chr(10).join(slide(*a) for a in accounts2)}
              </ul>
            </div>
            <div class="controls"><button type="button" class="prev" aria-label="Previous accounts">{icon("chevron-left")}</button><button type="button" class="next" aria-label="Next accounts">{icon("chevron-right")}</button></div>
          </template>
        </account-carousel>
      </section>
      <div class="{c("QuickActions", "root")}" role="toolbar" aria-label="Quick actions">
        <a class="{c("QuickActions", "tile")}" href="/pay/bills">{icon("calendar")}<span>Pay a bill</span></a>
        <button type="button" class="{c("QuickActions", "tile")} {c("QuickActions", "primary")}" data-testid="qa-move-money"{T("t1")}>Move money</button>
        <a class="{c("QuickActions", "tile")}" href="/deposit">{icon("upload")}<span>Deposit a check</span></a>
        <a class="{c("QuickActions", "tile")}" href="/send">{icon("send")}<span>Send to a friend</span></a>
      </div>
      <aside class="{c("Insight", "root")}" role="note">
        <p><strong>Nice work:</strong> you spent 12% less on dining out in October than in September.</p>
      </aside>
      <section class="{c("Card", "root")}" aria-labelledby="activity-title">
        <div class="{c("Card", "header")}">
          <h2 id="activity-title" class="{c("Section", "title")}">Activity</h2>
          <div class="{c("Select", "root")}">
            <select class="{c("Select", "native")}" name="accountId" aria-label="Show activity for"{T("t6")}>
              <option value="" selected>All accounts</option>
              <option value="chk-4821">Checking ••4821</option>
              <option value="cc-0193">Rewards Card ••0193</option>
              <option value="sav-7730">Savings ••7730</option>
              <option value="sav-7731">Vacation Fund ••7731</option>
            </select>
            {icon("chevron-down", c("Select", "chevron"))}
          </div>
          <a class="{c("Section", "link")}" href="/activity">View all activity</a>
        </div>
        <div class="{c("TxnList", "root")}">
          <div class="{c("TxnList", "group")}">
            <h3 class="{c("TxnList", "date")}">Pending</h3>
            <ul class="{c("TxnList", "rows")}">
            <li class="{c("TxnRow", "root")} {c("TxnRow", "pending")}">
              <span class="{c("TxnRow", "avatar")}" aria-hidden="true">J</span>
              <div class="{c("TxnRow", "main")}"><p class="{c("TxnRow", "merchant")}">Juniper Street Grocers</p><p class="{c("TxnRow", "meta")}">Groceries · ••0193 · Pending</p></div>
              <span class="{c("Amount", "root")} {c("Amount", "debit")}">−$31.07</span>
            </li>
            </ul>
          </div>
{chr(10).join(groups)}
        </div>
      </section>
    </main>
    <aside class="{c("Layout", "side")}">
      <section class="{c("Card", "root")}" aria-labelledby="budget-title">
        <div class="{c("Card", "header")}"><h2 id="budget-title" class="{c("Section", "title")}">Budgets · November</h2><a class="{c("Section", "link")}" href="/budgets">See all</a></div>
        <ul class="{c("BudgetList", "root")}">
{chr(10).join(budget2(*b) for b in budgets2)}
        </ul>
      </section>
      <section class="{c("Card", "root")}" aria-labelledby="goals-title">
        <div class="{c("Card", "header")}"><h2 id="goals-title" class="{c("Section", "title")}">Savings goals</h2></div>
        <div class="{c("Goal", "root")}">
          <p class="{c("Goal", "name")}">Emergency fund · High-Yield Savings</p>
          <p class="{c("Goal", "saved")}">$18,940.12</p>
          <p class="{c("Goal", "target")}">of $20,000 goal</p>
          <progress class="{c("Goal", "meter")}" max="100" value="95">95%</progress>
        </div>
        <div class="{c("Goal", "root")}">
          <p class="{c("Goal", "name")}">Lisbon trip · Vacation Fund</p>
          <p class="{c("Goal", "saved")}">$2,450.00</p>
          <p class="{c("Goal", "target")}">of $4,000 goal</p>
          <progress class="{c("Goal", "meter")}" max="100" value="61">61%</progress>
        </div>
      </section>
      <section class="{c("Card", "root")}" aria-labelledby="bills-title">
        <div class="{c("Card", "header")}"><h2 id="bills-title" class="{c("Section", "title")}">Coming up</h2></div>
        <ul class="{c("Bills", "list")}">
{chr(10).join(f'          <li class="{c("Bills", "item")}"><span>{n}</span><time>{d}</time><strong>{a}</strong></li>' for n, d, a in bills)}
        </ul>
      </section>
    </aside>
  </div>
  <footer class="{c("Footer", "root")}">
    <nav class="{c("Footer", "nav")}" aria-label="Footer">
      <a href="/documents">Statements &amp; documents</a><a href="/privacy">Privacy &amp; security</a><a href="/accessibility">Accessibility</a><a href="/fees">Fees</a><a href="/contact">Contact us</a>
    </nav>
    <p class="{c("Footer", "legal")}">Copperleaf Bank, N.A. Deposits insured up to applicable limits. Equal Housing Lender. © 2026 Copperleaf Financial Corp.</p>
  </footer>
</div>
'''
    v2 = page("Overview · Copperleaf", v2_body, css=v2_css)

    targets = [
        tgt("t1", "Primary 'Transfer money' quick-action button",
            '[data-testid="quick-transfer"]',
            "//section[contains(@class,'quick-actions')]/button[1]",
            ["testid-change", "id-change", "copy-change", "class-obfuscation", "sibling-reorder", "tag-change", "decoy"]),
        tgt("t2", "Balance of the 'High-Yield Savings ••7730' account ($18,940.12)",
            'li[data-account="sav-7730"] .balance',
            "//a[text()='High-Yield Savings']/ancestor::li//span[@class='balance']",
            ["shadow-dom", "tag-change", "sibling-reorder", "attribute-churn", "class-obfuscation", "decoy"]),
        tgt("t3", "Amount of the 'Sunline Utilities' transaction (−$142.18)",
            "table.txn-table tbody tr:nth-child(3) td.amount",
            "//td[text()='Sunline Utilities']/following-sibling::td[contains(@class,'amount')]",
            ["tag-change", "structure-move", "sibling-reorder", "insertion", "class-obfuscation", "wrapper-divs"]),
        tgt("t4", "Icon-only edit button of the 'Dining out' budget",
            'button[aria-label="Edit Dining out budget"]',
            "//li[@data-category='dining']//button[contains(@class,'budget-edit')]",
            ["attribute-churn", "sibling-reorder", "class-obfuscation"]),
        tgt("t5", "'Statements & documents' item of the main navigation",
            '.cb-mainnav a[href="/statements"]',
            "//nav[@aria-label='Main']//a[contains(text(),'Statements')]",
            ["structure-move", "wrapper-divs", "attribute-churn", "class-obfuscation", "decoy"]),
        tgt("t6", "Account filter select of the recent transactions list",
            "#txn-account-filter",
            "//label[text()='Account']/following-sibling::select",
            ["id-change", "attribute-churn", "copy-change", "wrapper-divs", "class-obfuscation"]),
    ]
    m = meta(
        "dashboard-05", "Online banking account overview — Copperleaf Bank",
        ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change", "copy-change",
         "tag-change", "attribute-churn", "structure-move", "insertion"],
        "v1 is a traditional bank layout (utility bar, underlined nav, account list, transactions <table>). v2 is a CSS-modules "
        "SPA: accounts render inside an <account-carousel> web component (declarative shadow root) in a new order with "
        "<p> balances, and a new 'Savings goals' card repeats the savings balance. 'Transfer money' becomes 'Move money' "
        "(second tile; a header CTA repeats it). The transactions table becomes an activity feed grouped by day with a "
        "pending item inserted. Budgets are sorted by % used and every edit button shares the aria-label 'Edit budget'. "
        "'Statements & documents' moves into a 'More' menu (the footer repeats it). The account filter loses its id and "
        "visible label.",
        targets,
    )
    return v1, v2, m


# ======================================================================================
# dashboard-06 — project-management workspace ("Tasklane", Orchard Studio)
# ======================================================================================
@suite
def dashboard_06():
    people = {"LF": ("Lena Fischer", "rose"), "MO": ("Marcus Obi", "emerald"), "SV": ("Sofia Varga", "violet"),
              "JP": ("Jonah Pierce", "amber"), "ID": ("Ines Duarte", "sky")}
    # id, title, assignee, due (day of Nov), priority, comments
    sections = [
        ("design", "Design", [
            ("311", "Finalize homepage hero copy", "LF", 6, "High", 4),
            ("312", "Export icon set for new nav", "SV", 9, "Medium", 1),
            ("313", "Review pricing page mockups", "MO", 10, "Medium", 6),
            ("314", "Update brand color tokens", "SV", 13, "Low", 0),
        ]),
        ("development", "Development", [
            ("315", "Implement responsive header", "JP", 7, "High", 3),
            ("316", "Migrate blog to new CMS", "ID", 17, "Medium", 2),
            ("317", "Set up staging CDN", "JP", 5, "High", 5),
            ("320", "Add structured data to product pages", "ID", 19, "Low", 0),
        ]),
        ("qa", "QA &amp; launch", [
            ("318", "Accessibility audit", "MO", 12, "High", 2),
            ("319", "QA regression pass", "LF", 12, "Medium", 0),
            ("321", "Launch announcement email", "SV", 20, "Medium", 1),
            ("322", "Redirect map for legacy URLs", "JP", 16, "High", 7),
        ]),
    ]
    projects = [("website-relaunch", "Website relaunch", "#e8743b"), ("q4-brand-campaign", "Q4 brand campaign", "#4f7cff"),
                ("mobile-app-v3", "Mobile app v3", "#18a0c9"), ("customer-research-q4", "Customer research — Q4", "#9b59b6"),
                ("brand-refresh-2027", "Brand refresh 2027", "#e84393"), ("hiring-senior-designer", "Hiring: Senior designer", "#27ae60")]
    weekday = {5: "Thu", 6: "Fri", 7: "Sat", 9: "Mon", 10: "Tue", 12: "Thu", 13: "Fri", 16: "Mon", 17: "Tue", 19: "Thu", 20: "Fri"}
    activity = [("Marcus Obi", "commented on", "Review pricing page mockups", "12 min ago"),
                ("Jonah Pierce", "completed", "Purge legacy CSS bundles", "1 h ago"),
                ("Sofia Varga", "attached a file to", "Export icon set for new nav", "3 h ago"),
                ("Lena Fischer", "changed the due date of", "Finalize homepage hero copy", "Yesterday"),
                ("Ines Duarte", "was assigned", "Migrate blog to new CMS", "Yesterday")]

    # ------------------------------------------------------------------ v1
    v1_css = """
body{margin:0;font:14px/1.45 "Helvetica Neue",Helvetica,Arial,sans-serif;color:#1e1f21;background:#fff}
.tl-app{display:flex;min-height:100vh}
.tl-sidebar{width:240px;background:#2e2e30;color:#f5f4f3;padding:12px 8px;flex:none}
.tl-nav-link,.project-link{display:flex;align-items:center;gap:8px;padding:5px 10px;border-radius:6px;color:#f5f4f3;text-decoration:none}
.project-link.active{background:#4a4a4d}
.project-list{list-style:none;margin:0;padding:0}
.dot{width:8px;height:8px;border-radius:2px;display:inline-block}
.tl-main{flex:1;min-width:0}
.tl-topbar{display:flex;align-items:center;gap:12px;height:48px;padding:0 20px;border-bottom:1px solid #e8e8e8}
.project-header{padding:14px 24px 0;border-bottom:1px solid #e8e8e8}
.project-tabs{display:flex;gap:18px}.project-tabs .tab{padding:10px 0;color:#6d6e6f;text-decoration:none}
.project-tabs .tab.active{color:#1e1f21;box-shadow:inset 0 -2px #1e1f21}
.list-toolbar{display:flex;justify-content:space-between;padding:10px 24px}
.task-list{width:100%;border-collapse:collapse}
.task-list td,.task-list th{padding:6px 10px;border-bottom:1px solid #edeae9;text-align:left}
.section-row th{font-size:15px;padding-top:18px}
.avatar{display:inline-flex;width:24px;height:24px;border-radius:50%;background:#aaa;color:#fff;font-size:11px;align-items:center;justify-content:center}
.tag-high{background:#ffd5d5}.tag-medium{background:#ffeec2}.tag-low{background:#d8f1e6}
.add-task{border:0;background:none;color:#6d6e6f;padding:4px 0}
.tl-activity{width:280px;border-left:1px solid #e8e8e8;padding:16px}
"""

    def v1_task(tid, title, who, day, prio, comments):
        name, _col = people[who]
        return f'''          <tr class="task-row" data-task-id="{tid}">
            <td class="cell-check"><input type="checkbox" id="task-{tid}-done" aria-label="Mark complete"{t_if(tid == "311", "t1")}></td>
            <td class="cell-title">{title}</td>
            <td class="cell-assignee"><span class="avatar" title="{name}">{who}</span><span class="assignee-name">{name}</span></td>
            <td class="cell-due"><time datetime="2026-11-{day:02d}"{t_if(tid == "318", "t5")}>Nov {day}</time></td>
            <td class="cell-priority"><span class="tag tag-{prio.lower()}">{prio}</span></td>
            <td class="cell-comments">{icon("message")} {comments}</td>
          </tr>'''

    def v1_section(key, name, tasks):
        return f'''        <tbody class="task-section" data-section="{key}">
          <tr class="section-row"><th colspan="6" scope="rowgroup"><button type="button" class="section-toggle" aria-expanded="true" aria-label="Collapse {name}">{icon("chevron-down")}</button>{name} <span class="section-count">{len(tasks)}</span></th></tr>
{chr(10).join(v1_task(*t) for t in tasks)}
          <tr class="add-row"><td colspan="6"><button type="button" class="add-task"{t_if(key == "development", "t6")}>Add task…</button></td></tr>
        </tbody>'''

    v1_projects = "\n".join(
        f'          <li><a href="/projects/{k}" class="project-link{" active" if k == "website-relaunch" else ""}"'
        f'{t_if(k == "mobile-app-v3", "t2")}><span class="dot" style="background:{col}"></span>{n}</a></li>' for k, n, col in projects)
    tabs1 = [("overview", "Overview"), ("list", "List"), ("board", "Board"), ("timeline", "Timeline"), ("calendar", "Calendar"),
             ("files", "Files")]
    v1_tabs = "\n".join(
        f'          <a href="/projects/website-relaunch/{k}" class="tab{" active" if k == "list" else ""}"'
        f'{" aria-current=" + chr(34) + "page" + chr(34) if k == "list" else ""}{t_if(k == "board", "t4")}>{lab}</a>' for k, lab in tabs1)

    v1_body = f'''
<div class="tl-app">
  <aside class="tl-sidebar">
    <div class="ws-switcher"><button type="button" class="ws-button" aria-haspopup="menu"><span class="ws-logo">OS</span>Orchard Studio {icon("chevron-down")}</button></div>
    <nav class="tl-nav" aria-label="Workspace">
      <a href="/home" class="tl-nav-link">{icon("home")}Home</a>
      <a href="/my-tasks" class="tl-nav-link">{icon("check")}My tasks</a>
      <a href="/inbox" class="tl-nav-link">{icon("inbox")}Inbox <span class="tl-badge">5</span></a>
      <a href="/calendar" class="tl-nav-link">{icon("calendar")}Calendar</a>
      <a href="/reporting" class="tl-nav-link">{icon("chart")}Reporting</a>
    </nav>
    <div class="tl-section">
      <div class="tl-section-head"><span>Projects</span><button type="button" class="tl-icon-btn" aria-label="New project">{icon("plus")}</button></div>
      <ul class="project-list">
{v1_projects}
      </ul>
    </div>
    <div class="tl-section">
      <div class="tl-section-head"><span>Teams</span></div>
      <ul class="team-list">
        <li><a href="/teams/design" class="tl-nav-link">Design</a></li>
        <li><a href="/teams/engineering" class="tl-nav-link">Engineering</a></li>
        <li><a href="/teams/marketing" class="tl-nav-link">Marketing</a></li>
      </ul>
    </div>
    <div class="tl-sidebar-footer"><button type="button" class="invite-btn">{icon("user-plus")}Invite teammates</button><p class="trial">Business trial · 12 days left</p></div>
  </aside>
  <div class="tl-main">
    <header class="tl-topbar">
      <input type="search" class="tl-search" placeholder="Search tasks, projects and people" aria-label="Search">
      <button type="button" class="btn btn-create">{icon("plus")}Create</button>
      <button type="button" class="tl-icon-btn" aria-label="Help">{icon("help")}</button>
      <span class="avatar avatar-me" title="Lena Fischer">LF</span>
    </header>
    <div class="project-header">
      <div class="project-title-row">
        <span class="project-icon" style="background:#e8743b"></span>
        <h1>Website relaunch</h1>
        <button type="button" class="tl-icon-btn" aria-label="Add to favorites">{icon("star")}</button>
        <span class="status-pill on-track">On track</span>
        <div class="project-members">
          <span class="avatar" title="Lena Fischer">LF</span><span class="avatar" title="Marcus Obi">MO</span><span class="avatar" title="Sofia Varga">SV</span><span class="avatar" title="Jonah Pierce">JP</span><span class="avatar" title="Ines Duarte">ID</span>
          <button type="button" class="btn btn-share">Share</button>
        </div>
      </div>
      <nav class="project-tabs">
{v1_tabs}
      </nav>
    </div>
    <div class="tl-content">
      <div class="tl-list">
        <div class="list-toolbar">
          <button type="button" class="btn btn-primary btn-new-task">{icon("plus")} Add task</button>
          <div class="filters">
            <label class="filter">Assignee
              <select id="filter-assignee" name="assignee"{T("t3")}>
                <option value="any" selected>Anyone</option><option value="me">Me</option>
                {"".join(f'<option value="{k.lower()}">{v[0]}</option>' for k, v in people.items())}
                <option value="none">Unassigned</option>
              </select>
            </label>
            <label class="filter">Due
              <select id="filter-due" name="due"><option selected>Any time</option><option>Overdue</option><option>This week</option><option>Next week</option></select>
            </label>
            <label class="filter chk"><input type="checkbox" id="show-completed" name="show_completed"> Show completed</label>
            <label class="filter">Sort
              <select id="sort-by" name="sort"><option selected>Due date</option><option>Priority</option><option>Assignee</option><option>Created</option></select>
            </label>
          </div>
        </div>
        <table class="task-list">
          <thead><tr><th></th><th>Task name</th><th>Assignee</th><th>Due date</th><th>Priority</th><th></th></tr></thead>
{chr(10).join(v1_section(*s) for s in sections)}
        </table>
      </div>
      <aside class="tl-activity" aria-labelledby="activity-heading">
        <h2 id="activity-heading">Project activity</h2>
        <ul class="activity-list">
{chr(10).join(f'          <li class="activity-item"><strong>{w}</strong> {verb} <a href="#">{what}</a><span class="when">{when}</span></li>' for w, verb, what, when in activity)}
        </ul>
      </aside>
    </div>
  </div>
</div>
'''
    v1 = page("Website relaunch – List – Tasklane", v1_body, css=v1_css)

    # ------------------------------------------------------------------ v2 (Tailwind, treegrid)
    prio_cls = {"High": "bg-red-50 text-red-700 ring-red-600/10", "Medium": "bg-yellow-50 text-yellow-800 ring-yellow-600/20",
                "Low": "bg-green-50 text-green-700 ring-green-600/20"}

    def v2_due(day):
        if day == 5:
            return "Today"
        if day == 6:
            return "Tomorrow"
        return f"{weekday[day]}, Nov {day}"

    def v2_task(tid, title, who, day, prio, comments):
        name, col = people[who]
        overdue = " text-red-600" if day == 5 else " text-gray-600"
        return f'''          <div role="row" aria-level="2" class="group flex items-center gap-3 border-b border-gray-100 py-2 hover:bg-gray-50">
            <div role="gridcell" class="flex w-6 justify-center"><button type="button" role="checkbox" aria-checked="false" aria-label="Mark complete" class="size-4 rounded-full border border-gray-300 hover:border-emerald-500"{t_if(tid == "311", "t1")}></button></div>
            <div role="gridcell" class="min-w-0 flex-1"><a href="/t/{tid}" class="truncate text-sm text-gray-900 hover:underline">{title}</a></div>
            <div role="gridcell" class="flex w-40 items-center gap-2"><span class="inline-flex size-6 items-center justify-center rounded-full bg-{col}-500 text-[11px] font-medium text-white">{who}</span><span class="truncate text-sm text-gray-700">{name}</span></div>
            <div role="gridcell" class="w-28 text-sm{overdue}"><time datetime="2026-11-{day:02d}"{t_if(tid == "318", "t5")}>{v2_due(day)}</time></div>
            <div role="gridcell" class="w-24"><span class="inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset {prio_cls[prio]}">{prio}</span></div>
            <div role="gridcell" class="flex w-12 items-center gap-1 text-xs text-gray-500">{icon("message", "size-4", style="hero")}{comments}</div>
          </div>'''

    def v2_section(key, name, tasks):
        tasks = sorted(tasks, key=lambda t: t[3])
        return f'''        <div role="rowgroup" aria-labelledby="sec-{key}" class="mt-6">
          <div role="row" class="flex items-center gap-2 py-2">
            <button type="button" aria-expanded="true" class="rounded p-0.5 text-gray-400 hover:bg-gray-100"><span class="sr-only">Toggle section</span>{icon("chevron-down", "size-4", style="hero")}</button>
            <h3 id="sec-{key}" class="text-sm font-semibold text-gray-900">{name}</h3>
            <span class="rounded-full bg-gray-100 px-2 text-xs text-gray-600">{len(tasks)}</span>
          </div>
{chr(10).join(v2_task(*t) for t in tasks)}
          <div role="row" class="py-1.5 pl-9">
            <button type="button" class="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900"{t_if(key == "development", "t6")}>{icon("plus", "size-4", style="hero")}Add task</button>
          </div>
        </div>'''

    def proj_links(mobile):
        out = []
        for k, n, col in sorted(projects, key=lambda p: p[1]):
            cur = k == "website-relaunch"
            cls = "group flex items-center gap-x-2 rounded-md px-2 py-1.5 text-sm " + ("bg-gray-200 font-medium text-gray-900" if cur else "text-gray-700 hover:bg-gray-200")
            mark = T("t2") if (k == "mobile-app-v3" and not mobile) else ""
            out.append(f'            <li><a href="/p/{k}" class="{cls}"{" aria-current=" + chr(34) + "page" + chr(34) if cur else ""}{mark}>'
                       f'<span class="size-2 shrink-0 rounded-sm" style="background:{col}"></span><span class="truncate">{n}</span></a></li>')
        return "\n".join(out)

    tabs2 = ["Overview", "List", "Dashboard", "Board", "Timeline", "Calendar", "Files", "Messages"]
    sections2 = [sections[1], sections[0], sections[2]]
    nav_top = [("/home", "Home", "home"), ("/my-tasks", "My tasks", "check"), ("/inbox", "Inbox", "inbox"),
               ("/reporting", "Reporting", "chart"), ("/goals", "Goals", "flag")]
    nav_top_html = "\n".join(
        f'          <li><a href="{h}" class="flex items-center gap-x-2 rounded-md px-2 py-1.5 text-sm text-gray-700 hover:bg-gray-200">'
        f'{icon(ic, "size-4 text-gray-400", style="hero")}{lab}{"<span class=" + chr(34) + "ml-auto rounded-full bg-indigo-100 px-1.5 text-xs text-indigo-700" + chr(34) + ">5</span>" if lab == "Inbox" else ""}</a></li>'
        for h, lab, ic in nav_top)

    v2_body = f'''
<div class="flex h-screen bg-white">
  <div class="relative z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation" hidden>
    <div class="fixed inset-0 bg-gray-900/60"></div>
    <div class="fixed inset-y-0 left-0 w-72 overflow-y-auto bg-gray-50 px-3 py-4">
      <p class="px-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Projects</p>
      <ul role="list" class="mt-1 space-y-0.5">
{proj_links(True)}
      </ul>
    </div>
  </div>
  <aside class="hidden w-64 shrink-0 flex-col border-r border-gray-200 bg-gray-50 lg:flex">
    <div class="flex h-14 items-center gap-2 px-4">
      <button type="button" class="flex w-full items-center gap-2 rounded-md px-2 py-1 text-sm font-semibold text-gray-900 hover:bg-gray-200" aria-haspopup="menu"><span class="inline-flex size-6 items-center justify-center rounded bg-orange-500 text-xs text-white">OS</span>Orchard Studio{icon("chevron-down", "ml-auto size-4 text-gray-400", style="hero")}</button>
    </div>
    <nav class="flex-1 space-y-6 overflow-y-auto px-3 py-2" aria-label="Sidebar">
      <ul role="list" class="space-y-0.5">
{nav_top_html}
      </ul>
      <div>
        <h3 class="px-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Favorites</h3>
        <ul role="list" class="mt-1 space-y-0.5">
          <li><a href="/p/website-relaunch" class="flex items-center gap-x-2 rounded-md px-2 py-1.5 text-sm text-gray-700 hover:bg-gray-200">{icon("star", "size-4 text-amber-400", style="hero")}<span class="truncate">Website relaunch</span></a></li>
          <li><a href="/p/q4-brand-campaign" class="flex items-center gap-x-2 rounded-md px-2 py-1.5 text-sm text-gray-700 hover:bg-gray-200">{icon("star", "size-4 text-amber-400", style="hero")}<span class="truncate">Q4 brand campaign</span></a></li>
        </ul>
      </div>
      <div>
        <div class="flex items-center justify-between px-2">
          <h3 class="text-xs font-semibold uppercase tracking-wide text-gray-500">Projects</h3>
          <button type="button" class="rounded p-0.5 text-gray-400 hover:bg-gray-200"><span class="sr-only">Create project</span>{icon("plus", "size-4", style="hero")}</button>
        </div>
        <ul role="list" class="mt-1 space-y-0.5">
{proj_links(False)}
        </ul>
      </div>
      <div>
        <h3 class="px-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Teams</h3>
        <ul role="list" class="mt-1 space-y-0.5">
          <li><a href="/teams/design" class="block rounded-md px-2 py-1.5 text-sm text-gray-700 hover:bg-gray-200">Design</a></li>
          <li><a href="/teams/engineering" class="block rounded-md px-2 py-1.5 text-sm text-gray-700 hover:bg-gray-200">Engineering</a></li>
          <li><a href="/teams/marketing" class="block rounded-md px-2 py-1.5 text-sm text-gray-700 hover:bg-gray-200">Marketing</a></li>
        </ul>
      </div>
    </nav>
    <div class="border-t border-gray-200 px-4 py-3"><button type="button" class="flex items-center gap-2 text-sm text-gray-700">{icon("user-plus", "size-4", style="hero")}Invite people</button></div>
  </aside>
  <div class="flex min-w-0 flex-1 flex-col">
    <header class="flex h-14 shrink-0 items-center gap-3 border-b border-gray-200 px-6">
      <nav aria-label="Breadcrumb" class="flex items-center gap-1 text-sm text-gray-500"><a href="/projects" class="hover:text-gray-700">Projects</a>{icon("chevron-right", "size-4", style="hero")}<span class="font-semibold text-gray-900">Website relaunch</span></nav>
      <button type="button" class="rounded p-1 text-gray-400 hover:bg-gray-100"><span class="sr-only">Favorite</span>{icon("star", "size-4", style="hero")}</button>
      <span class="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700"><span class="size-1.5 rounded-full bg-emerald-500"></span>On track</span>
      <div class="ml-auto flex items-center gap-3">
        <avatar-stack max="4">
          <template shadowrootmode="open">
            <style>:host{{display:inline-flex}} .a{{width:24px;height:24px;margin-left:-6px;border-radius:50%;border:2px solid #fff;font:500 11px/20px sans-serif;text-align:center;color:#fff}} .more{{background:#e5e7eb;color:#374151}}</style>
            <span class="a" style="background:#f43f5e" title="Lena Fischer">LF</span><span class="a" style="background:#10b981" title="Marcus Obi">MO</span><span class="a" style="background:#8b5cf6" title="Sofia Varga">SV</span><span class="a" style="background:#f59e0b" title="Jonah Pierce">JP</span><span class="a more" title="Ines Duarte">+1</span>
          </template>
        </avatar-stack>
        <button type="button" class="rounded-md bg-white px-2.5 py-1.5 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300">Share</button>
        <button type="button" class="rounded-full bg-gray-100 p-1.5 text-gray-500"><span class="sr-only">Search</span>{icon("search", "size-4", style="hero")}</button>
      </div>
    </header>
    <div class="border-b border-gray-200 px-6">
      <div role="tablist" aria-label="Project views" class="-mb-px flex gap-6">
{chr(10).join(f'        <button type="button" role="tab" aria-selected="{str(t == "List").lower()}" class="border-b-2 py-2.5 text-sm font-medium {"border-gray-900 text-gray-900" if t == "List" else "border-transparent text-gray-500 hover:text-gray-700"}"{t_if(t == "Board", "t4")}>{t}</button>' for t in tabs2)}
      </div>
    </div>
    <div class="flex min-h-0 flex-1">
      <div class="min-w-0 flex-1 overflow-auto">
        <div class="flex flex-wrap items-center gap-2 px-6 py-3">
          <button type="button" class="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-2.5 py-1.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500">{icon("plus", "size-4", style="hero")}Add task</button>
          <div class="ml-auto flex flex-wrap items-center gap-2">
            <input type="search" placeholder="Filter tasks" aria-label="Filter tasks" class="w-44 rounded-md border-0 py-1.5 text-sm ring-1 ring-inset ring-gray-300">
            <div class="grid grid-cols-1">
              <label for="filter-assignee" class="sr-only">Assignee</label>
              <select id="filter-assignee" name="assigneeId" class="col-start-1 row-start-1 appearance-none rounded-md py-1.5 pl-3 pr-8 text-sm ring-1 ring-inset ring-gray-300"{T("t3")}>
                <option value="" selected>All assignees</option><option value="me">Assigned to me</option>
                {"".join(f'<option value="{k.lower()}">{v[0]}</option>' for k, v in sorted(people.items(), key=lambda kv: kv[1][0]))}
                <option value="none">Unassigned</option>
              </select>
              {icon("chevron-down", "pointer-events-none col-start-1 row-start-1 mr-2 size-4 self-center justify-self-end text-gray-400", style="hero")}
            </div>
            <select name="due" aria-label="Due date" class="rounded-md py-1.5 pl-3 pr-8 text-sm ring-1 ring-inset ring-gray-300"><option selected>Any due date</option><option>Overdue</option><option>This week</option><option>Next week</option></select>
            <span class="flex items-center gap-2 text-sm text-gray-700"><button type="button" role="switch" aria-checked="false" class="relative inline-flex h-5 w-9 rounded-full bg-gray-200"><span class="sr-only">Show completed tasks</span><span aria-hidden="true" class="inline-block size-4 translate-x-0.5 translate-y-0.5 rounded-full bg-white shadow"></span></button>Completed</span>
            <select name="sort" aria-label="Sort tasks" class="rounded-md py-1.5 pl-3 pr-8 text-sm ring-1 ring-inset ring-gray-300"><option selected>Sort: Due date</option><option>Sort: Priority</option><option>Sort: Assignee</option></select>
          </div>
        </div>
        <div role="treegrid" aria-label="Tasks" class="px-6 pb-10">
          <div role="rowgroup" class="sticky top-0 z-10 bg-white">
            <div role="row" class="flex items-center gap-3 border-b border-gray-200 py-2 text-xs font-medium uppercase tracking-wide text-gray-500">
              <span role="columnheader" class="w-6"></span><span role="columnheader" class="flex-1">Task</span><span role="columnheader" class="w-40">Assignee</span><span role="columnheader" class="w-28">Due</span><span role="columnheader" class="w-24">Priority</span><span role="columnheader" class="w-12"></span>
            </div>
          </div>
{chr(10).join(v2_section(*s) for s in sections2)}
        </div>
      </div>
      <activity-feed project="website-relaunch" class="hidden w-80 shrink-0 border-l border-gray-200 xl:block">
        <template shadowrootmode="open">
          <style>:host{{display:block;padding:16px;font:13px/1.5 system-ui}} h2{{font-size:13px;margin:0 0 8px}} li{{margin-bottom:10px}} time{{display:block;color:#6b7280}}</style>
          <h2>Activity</h2>
          <ol class="feed">
{chr(10).join(f'            <li><b>{w}</b> {verb} <a href="#">{what}</a><time>{when}</time></li>' for w, verb, what, when in activity)}
          </ol>
        </template>
      </activity-feed>
    </div>
  </div>
</div>
'''
    v2 = page("Website relaunch · List · Tasklane", v2_body, body_attrs=' class="h-full"')

    targets = [
        tgt("t1", "Completion checkbox of the task 'Finalize homepage hero copy'",
            "#task-311-done",
            "//tr[td[normalize-space()='Finalize homepage hero copy']]//input[@type='checkbox']",
            ["tag-change", "id-change", "sibling-reorder", "structure-move", "class-obfuscation", "wrapper-divs"]),
        tgt("t2", "'Mobile app v3' project link in the sidebar Projects list",
            ".project-list li:nth-child(3) a",
            "//ul[@class='project-list']//a[normalize-space()='Mobile app v3']",
            ["sibling-reorder", "class-obfuscation", "wrapper-divs", "attribute-churn", "insertion", "decoy"]),
        tgt("t3", "Assignee filter select in the list toolbar",
            "#filter-assignee",
            "//label[starts-with(normalize-space(),'Assignee')]/select",
            ["attribute-churn", "copy-change", "wrapper-divs", "class-obfuscation"]),
        tgt("t4", "'Board' view tab of the project header",
            "nav.project-tabs a.tab:nth-child(3)",
            "//nav[@class='project-tabs']/a[text()='Board']",
            ["tag-change", "insertion", "class-obfuscation", "attribute-churn"]),
        tgt("t5", "Due date of the task 'Accessibility audit' (Nov 12)",
            'tr[data-task-id="318"] td.cell-due time',
            "//td[text()='Accessibility audit']/following-sibling::td[@class='cell-due']/time",
            ["copy-change", "structure-move", "sibling-reorder", "class-obfuscation", "decoy"]),
        tgt("t6", "'Add task' button at the end of the Development section",
            'tbody[data-section="development"] .add-task',
            "(//button[@class='add-task'])[2]",
            ["sibling-reorder", "copy-change", "class-obfuscation", "structure-move", "decoy"]),
    ]
    m = meta(
        "dashboard-06", "Project workspace task list — Tasklane",
        ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change", "copy-change",
         "tag-change", "attribute-churn", "structure-move", "insertion"],
        "v1 is a dark-sidebar workspace with a <table> task list (one <tbody> per section, native checkboxes). v2 is a Tailwind "
        "rewrite: the list becomes an ARIA treegrid of div rows, sections are reordered (Development first) and tasks sorted "
        "by due date, completion checkboxes become button[role=checkbox], due dates read 'Thu, Nov 12'. The sidebar gains "
        "a Favorites section and an alphabetical Projects list (a hidden mobile drawer repeats it). Project tabs become "
        "role=tab buttons with new 'Dashboard'/'Messages' tabs. The assignee filter keeps its id but loses the wrapping "
        "label. Member avatars and the activity panel become web components with declarative shadow roots.",
        targets,
    )
    return v1, v2, m


# ======================================================================================
# dashboard-07 — email-marketing campaign dashboard ("Postwick" for Saltmarsh Outfitters)
# ======================================================================================
@suite
def dashboard_07():
    # id, name, status, segment, detail, metrics(opens, clicks, revenue) | None, progress | None
    campaigns = {
        "cmp_8841": ("Black Friday Early Access", "Sending", "VIP customers · 22,480 recipients", "13,938 of 22,480 sent", ("38.2%", "5.1%", "$41,260"), 62),
        "cmp_8835": ("November Newsletter", "Scheduled", "All subscribers · 84,312 recipients", "Sends Nov 7, 9:00 AM PST", None, None),
        "cmp_8790": ("Winter Gear Lookbook", "Sent", "All subscribers · 83,950 recipients", "Sent Oct 29, 8:00 AM PST", ("41.8%", "4.4%", "$22,915"), None),
        "cmp_8762": ("Re-engagement: 90-day inactive", "Paused", "Inactive 90+ days · 9,412 recipients", "Paused Nov 2 · 3,294 of 9,412 sent", ("12.6%", "0.9%", "$1,180"), 35),
        "cmp_8850": ("Holiday Gift Guide", "Draft", "Segment not set", "Last edited 2 hours ago by Sam Okoro", None, None),
        "cmp_8853": ("Cyber Monday Preview", "Scheduled", "Engaged 30 days · 41,077 recipients", "Sends Nov 30, 7:00 AM PST", None, None),
        "cmp_8846": ("Loyalty Points Reminder", "Sending", "Members with 500+ points · 6,120 recipients", "1,102 of 6,120 sent", ("29.4%", "3.2%", "$2,870"), 18),
    }
    v1_order = ["cmp_8841", "cmp_8835", "cmp_8790", "cmp_8762", "cmp_8850", "cmp_8853", "cmp_8846"]
    v2_order = ["cmp_8846", "cmp_8841", "cmp_8762", "cmp_8835", "cmp_8853", "cmp_8850", "cmp_8790"]
    stats = [("Subscribers", "84,312", "+1,208 this month"), ("Avg. open rate", "41.8%", "+2.1 pts"),
             ("Avg. click rate", "3.9%", "+0.4 pts"), ("Unsubscribe rate", "0.18%", "−0.03 pts"),
             ("Revenue attributed", "$128,440", "last 30 days")]
    variants = [("A", "Your early access to Black Friday starts now", "2,248", "38.9%", "4.6%"),
                ("B", "Members only: 30% off before everyone else", "2,249", "44.2%", "5.8%")]

    # ------------------------------------------------------------------ v1 (BEM)
    v1_css = """
body{margin:0;font:14px/1.5 "Work Sans",Arial,sans-serif;color:#22223b;background:#f7f5fb}
.pw-header{display:flex;align-items:center;gap:28px;padding:0 28px;height:60px;background:#22223b;color:#fff}
.pw-nav__link{color:#c9c6e0;text-decoration:none;padding:20px 4px}.pw-nav__link--active{color:#fff;box-shadow:inset 0 -3px #ff8fab}
.pw-btn{display:inline-block;padding:7px 14px;border-radius:999px;border:1px solid #4a4e69;background:#fff;color:#22223b;text-decoration:none}
.pw-btn--primary{background:#ff5d8f;border-color:#ff5d8f;color:#fff}
.pw-main{max-width:1200px;margin:0 auto;padding:24px}
.pw-stats{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}
.pw-stat{background:#fff;border-radius:12px;padding:14px;display:flex;flex-direction:column}
.pw-stat__value{font-size:24px}
.pw-campaign-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.pw-campaign-card{background:#fff;border-radius:12px;padding:16px;border:1px solid #e6e1f2}
.pw-badge{font-size:11px;text-transform:uppercase;letter-spacing:.05em;padding:2px 8px;border-radius:999px;background:#eee}
.pw-badge--sending{background:#d8f3dc}.pw-badge--paused{background:#ffe5d9}
.pw-progress{height:6px;background:#eee;border-radius:3px}.pw-progress__bar{height:6px;background:#ff5d8f;border-radius:3px}
.pw-campaign-card__stats{display:flex;gap:16px}.pw-campaign-card__stats dd{margin:0;font-weight:600}
.pw-ab-table{width:100%;border-collapse:collapse}.pw-ab-table td,.pw-ab-table th{padding:8px;border-bottom:1px solid #e6e1f2;text-align:left}
"""

    def v1_actions(cid, status):
        if status == "Sending":
            pause_t = t_if(cid == "cmp_8841", "t1")
            return (f'<button type="button" class="pw-btn pw-btn--secondary pw-btn-pause" data-qa="pause-campaign"{pause_t}>Pause</button>'
                    f'<a href="/campaigns/{cid}/report" class="pw-link">View report</a>')
        if status == "Scheduled":
            return f'<a href="/campaigns/{cid}/edit" class="pw-btn pw-btn--secondary">Edit</a><button type="button" class="pw-btn pw-btn--ghost">Unschedule</button>'
        if status == "Sent":
            return f'<a href="/campaigns/{cid}/report" class="pw-btn pw-btn--secondary">View report</a><button type="button" class="pw-btn pw-btn--ghost">Duplicate</button>'
        if status == "Paused":
            return (f'<button type="button" class="pw-btn pw-btn--primary"{t_if(cid == "cmp_8762", "t2")}>Resume</button>'
                    f'<a href="/campaigns/{cid}/edit" class="pw-btn pw-btn--secondary">Edit</a>')
        return f'<a href="/campaigns/{cid}/edit" class="pw-btn pw-btn--primary">Continue editing</a><button type="button" class="pw-btn pw-btn--ghost" aria-label="Delete draft">{icon("trash")}</button>'

    def v1_card(cid):
        name, status, seg, detail, metrics, prog = campaigns[cid]
        prog_html = (f'<div class="pw-progress"><div class="pw-progress__bar" style="width:{prog}%"></div></div>' if prog else "")
        stats_html = ""
        if metrics:
            stats_html = (f'<dl class="pw-campaign-card__stats"><div><dt>Opens</dt><dd>{metrics[0]}</dd></div>'
                          f'<div><dt>Clicks</dt><dd>{metrics[1]}</dd></div><div><dt>Revenue</dt><dd>{metrics[2]}</dd></div></dl>')
        return f'''        <article class="pw-campaign-card" data-campaign-id="{cid}">
          <header class="pw-campaign-card__head"><span class="pw-badge pw-badge--{status.lower()}">{status}</span><h3 class="pw-campaign-card__title">{name}</h3></header>
          <p class="pw-campaign-card__meta">{seg}</p>
          {prog_html}
          <p class="pw-campaign-card__detail">{detail}</p>
          {stats_html}
          <footer class="pw-campaign-card__actions">{v1_actions(cid, status)}</footer>
        </article>'''

    nav = [("/dashboard", "Dashboard"), ("/campaigns", "Campaigns"), ("/automations", "Automations"), ("/audience", "Audience"),
           ("/templates", "Templates"), ("/reports", "Reports")]
    v1_nav = "\n".join(
        f'    <a href="{h}" class="pw-nav__link{" pw-nav__link--active" if h == "/dashboard" else ""}"{t_if(h == "/automations", "t5")}>{lab}</a>'
        for h, lab in nav)

    v1_body = f'''
<header class="pw-header">
  <a class="pw-logo" href="/dashboard">{icon("send", "pw-logo__mark")}Postwick</a>
  <nav class="pw-nav">
{v1_nav}
  </nav>
  <div class="pw-header__actions">
    <a href="/campaigns/new" class="pw-btn pw-btn--primary">Create campaign</a>
    <button type="button" class="pw-avatar" aria-label="Account: Saltmarsh Outfitters">SO</button>
  </div>
</header>
<main class="pw-main">
  <div class="pw-page-head">
    <div><h1>Campaign dashboard</h1><p class="pw-muted">Saltmarsh Outfitters · 84,312 subscribers</p></div>
    <label class="pw-period">Period <select id="period" name="period"><option>Last 7 days</option><option selected>Last 30 days</option><option>Last 90 days</option></select></label>
  </div>
  <section class="pw-stats" aria-label="Account summary">
{chr(10).join(f'    <div class="pw-stat"><span class="pw-stat__label">{k}</span><strong class="pw-stat__value"{t_if(k == "Avg. open rate", "t6")}>{v}</strong><span class="pw-stat__delta">{d}</span></div>' for k, v, d in stats)}
  </section>
  <section class="pw-campaigns">
    <div class="pw-section-head">
      <h2>Active &amp; recent campaigns</h2>
      <div class="pw-filter-tabs" role="tablist">
        <button type="button" role="tab" aria-selected="true" class="pw-filter-tab pw-filter-tab--active">All</button>
        <button type="button" role="tab" aria-selected="false" class="pw-filter-tab">Sending</button>
        <button type="button" role="tab" aria-selected="false" class="pw-filter-tab">Scheduled</button>
        <button type="button" role="tab" aria-selected="false" class="pw-filter-tab">Sent</button>
        <button type="button" role="tab" aria-selected="false" class="pw-filter-tab">Drafts</button>
      </div>
    </div>
    <div class="pw-campaign-grid">
{chr(10).join(v1_card(c) for c in v1_order)}
    </div>
  </section>
  <section class="pw-ab-test" id="ab-test-cmp_8841">
    <div class="pw-section-head"><h2>A/B test: Black Friday Early Access</h2><span class="pw-badge">Testing · 4h 12m left</span></div>
    <table class="pw-ab-table">
      <thead><tr><th>Variant</th><th>Subject line</th><th>Recipients</th><th>Open rate</th><th>Click rate</th></tr></thead>
      <tbody>
{chr(10).join(f'        <tr{" class=" + chr(34) + "is-leading" + chr(34) if v == "B" else ""}><td>{v}</td><td>{s}</td><td>{r}</td><td class="open-rate"{t_if(v == "B", "t3")}>{o}</td><td class="click-rate">{c_}</td></tr>' for v, s, r, o, c_ in variants)}
      </tbody>
    </table>
    <form class="pw-ab-settings">
      <label for="ab-winner-metric">Pick winner by</label>
      <select id="ab-winner-metric" name="winner_metric"{T("t4")}><option value="open_rate" selected>Open rate</option><option value="click_rate">Click rate</option><option value="revenue">Revenue</option></select>
      <label for="ab-duration">Test duration</label>
      <select id="ab-duration" name="duration"><option>4 hours</option><option selected>8 hours</option><option>24 hours</option></select>
      <button type="button" class="pw-btn pw-btn--secondary">Send winner now</button>
    </form>
  </section>
  <section class="pw-deliverability">
    <h2>Deliverability</h2>
    <ul class="pw-health">
      <li><span>Sender reputation</span><strong>98 / 100</strong></li>
      <li><span>Bounce rate</span><strong>0.6%</strong></li>
      <li><span>Spam complaints</span><strong>0.02%</strong></li>
      <li><span>DMARC alignment</span><strong>Pass</strong></li>
    </ul>
  </section>
</main>
<footer class="pw-footer">Postwick · <a href="/help">Help center</a> · <a href="/legal/anti-spam">Anti-spam policy</a> · © 2026 Postwick Labs</footer>
'''
    v1 = page("Dashboard – Postwick", v1_body, css=v1_css)

    # ------------------------------------------------------------------ v2 (Angular Material + Lit element)
    ngc = ' _ngcontent-ng-c2911541853=""'
    btn_kind = {
        "stroked": ("mat-stroked-button", "mdc-button mdc-button--outlined mat-mdc-outlined-button mat-unthemed mat-mdc-button-base"),
        "flat": ("mat-flat-button", "mdc-button mdc-button--unelevated mat-mdc-unelevated-button mat-primary mat-mdc-button-base"),
        "text": ("mat-button", "mdc-button mat-mdc-button mat-unthemed mat-mdc-button-base"),
    }

    def mat_btn(label, kind="stroked", attrs="", tag="button"):
        directive, cls = btn_kind[kind]
        typ = ' type="button"' if tag == "button" else ""
        return (f'<{tag}{ngc} {directive}=""{typ} class="{cls}"{attrs}><span class="mat-mdc-button-persistent-ripple mdc-button__ripple"></span>'
                f'<span class="mdc-button__label">{label}</span><span class="mat-mdc-focus-indicator"></span>'
                f'<span class="mat-mdc-button-touch-target"></span></{tag}>')

    def mat_icon_btn(ligature, label):
        return (f'<button{ngc} mat-icon-button="" type="button" class="mdc-icon-button mat-mdc-icon-button mat-unthemed mat-mdc-button-base" '
                f'aria-label="{label}"><span class="mat-mdc-button-persistent-ripple mdc-icon-button__ripple"></span>'
                f'<mat-icon role="img" class="mat-icon notranslate material-icons mat-ligature-font mat-icon-no-color" aria-hidden="true" '
                f'data-mat-icon-type="font">{ligature}</mat-icon><span class="mat-mdc-focus-indicator"></span>'
                f'<span class="mat-mdc-button-touch-target"></span></button>')

    def v2_actions(cid, status):
        if status == "Sending":
            return (mat_btn("Pause sending", "stroked", t_if(cid == "cmp_8841", "t1"))
                    + mat_btn("View report", "text", f' href="/campaigns/{cid}/report"', tag="a"))
        if status == "Scheduled":
            return mat_btn("Edit", "stroked", f' href="/campaigns/{cid}/edit"', tag="a") + mat_btn("Unschedule", "text")
        if status == "Sent":
            return mat_btn("View report", "stroked", f' href="/campaigns/{cid}/report"', tag="a") + mat_btn("Duplicate", "text")
        if status == "Paused":
            return mat_btn("Resume sending", "flat", t_if(cid == "cmp_8762", "t2")) + mat_btn("Edit", "text", f' href="/campaigns/{cid}/edit"', tag="a")
        return mat_btn("Continue editing", "flat", f' href="/campaigns/{cid}/edit"', tag="a") + mat_icon_btn("delete", "Delete draft")

    def v2_card(cid):
        name, status, seg, detail, metrics, prog = campaigns[cid]
        chip = (f'<mat-chip{ngc} class="mat-mdc-chip mat-mdc-standard-chip mdc-evolution-chip status-chip status-{status.lower()}">'
                f'<span class="mdc-evolution-chip__cell mdc-evolution-chip__cell--primary"><span class="mdc-evolution-chip__action mat-mdc-chip-action">'
                f'<span class="mdc-evolution-chip__text-label mat-mdc-chip-action-label">{status}</span></span></span></mat-chip>')
        prog_html = ""
        if prog:
            prog_html = (f'<mat-progress-bar{ngc} mode="determinate" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{prog}" '
                         f'class="mat-mdc-progress-bar mdc-linear-progress mat-primary"><div class="mdc-linear-progress__buffer">'
                         f'<div class="mdc-linear-progress__buffer-bar"></div></div><div class="mdc-linear-progress__bar mdc-linear-progress__primary-bar" '
                         f'style="transform: scaleX({prog / 100:.2f})"><span class="mdc-linear-progress__bar-inner"></span></div></mat-progress-bar>')
        metrics_html = ""
        if metrics:
            metrics_html = (f'<div{ngc} class="metrics">'
                            + "".join(f'<div{ngc} class="metric"><div{ngc} class="metric-value">{v}</div><div{ngc} class="metric-label">{k}</div></div>'
                                      for k, v in zip(("Opens", "Clicks", "Revenue"), metrics))
                            + "</div>")
        return f'''          <mat-card{ngc} appearance="outlined" class="mat-mdc-card mdc-card mat-mdc-card-outlined mdc-card--outlined campaign-card" data-status="{status.lower()}">
            <mat-card-header{ngc} class="mat-mdc-card-header">
              <div class="mat-mdc-card-header-text"><mat-card-title{ngc} class="mat-mdc-card-title">{name}</mat-card-title><mat-card-subtitle{ngc} class="mat-mdc-card-subtitle">{seg}</mat-card-subtitle></div>
              {chip}
            </mat-card-header>
            <mat-card-content{ngc} class="mat-mdc-card-content">
              {prog_html}
              <p{ngc} class="detail">{detail}</p>
              {metrics_html}
            </mat-card-content>
            <mat-card-actions{ngc} class="mat-mdc-card-actions mdc-card__actions">{v2_actions(cid, status)}</mat-card-actions>
          </mat-card>'''

    nav2 = [("/dashboard", "Dashboard"), ("/campaigns", "Campaigns"), ("/audience", "Audience"), ("/automations", "Automations"),
            ("/forms", "Sign-up forms"), ("/templates", "Templates"), ("/reports", "Reports")]

    def tab_link(h, lab):
        active = h == "/dashboard"
        return (f'<a{ngc} mat-tab-link="" href="{h}" class="mdc-tab mat-mdc-tab-link mat-mdc-focus-indicator{" mdc-tab--active" if active else ""}"'
                f'{" aria-current=" + chr(34) + "page" + chr(34) if active else ""}{t_if(h == "/automations", "t5")}>'
                f'<span class="mdc-tab__ripple"></span><span class="mdc-tab__content"><span class="mdc-tab__text-label">{lab}</span></span>'
                f'<span class="mdc-tab-indicator{" mdc-tab-indicator--active" if active else ""}"><span class="mdc-tab-indicator__content mdc-tab-indicator__content--underline"></span></span></a>')

    ab_css = (":host{display:block;font:14px/1.5 Roboto,sans-serif} .panel{border:1px solid #e0dced;border-radius:12px;padding:16px;background:#fff}"
              " .variants{display:grid;grid-template-columns:1fr 1fr;gap:12px} .variant{border-radius:10px;padding:12px;background:#f8f6fc}"
              " .variant--leading{outline:2px solid #6750a4} .metrics{display:flex;gap:18px} .metric{display:flex;flex-direction:column}"
              " .metric-value{font-size:20px} .settings{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center;margin-top:14px}")

    def v2_variant(v, subj, rec, opens, clicks):
        lead = v == "B"
        return f'''                <article class="variant{" variant--leading" if lead else ""}" data-variant="{v}">
                  <h3>Variant {v}{" <span class=" + chr(34) + "badge" + chr(34) + ">Leading</span>" if lead else ""}</h3>
                  <p class="subject">“{subj}”</p>
                  <div class="metrics">
                    <div class="metric"><span class="metric-label">Open rate</span><strong class="metric-value"{t_if(lead, "t3")}>{opens}</strong></div>
                    <div class="metric"><span class="metric-label">Click rate</span><strong class="metric-value">{clicks}</strong></div>
                    <div class="metric"><span class="metric-label">Recipients</span><strong class="metric-value">{rec}</strong></div>
                  </div>
                </article>'''

    v2_body = f'''
<app-root _nghost-ng-c2911541853="" ng-version="17.3.8">
  <mat-toolbar{ngc} color="primary" class="mat-toolbar mat-primary mat-toolbar-single-row app-toolbar">
    {mat_icon_btn("menu", "Open navigation")}
    <a{ngc} class="brand" href="/dashboard">Postwick</a>
    <span{ngc} class="toolbar-spacer"></span>
    {mat_btn("Create campaign", "flat", ' href="/campaigns/new"', tag="a")}
    {mat_icon_btn("notifications", "Notifications")}
    <button{ngc} type="button" class="avatar-button" aria-label="Account: Saltmarsh Outfitters">SO</button>
  </mat-toolbar>
  <nav{ngc} mat-tab-nav-bar="" aria-label="Main navigation" class="mat-mdc-tab-nav-bar mat-mdc-tab-header mat-primary">
    <div class="mat-mdc-tab-link-container"><div class="mat-mdc-tab-list"><div class="mat-mdc-tab-links">
      {"".join(tab_link(h, lab) for h, lab in nav2)}
    </div></div></div>
  </nav>
  <div{ngc} class="mat-mdc-menu-panel overflow-menu" role="menu" hidden>
    <a mat-menu-item="" role="menuitem" class="mat-mdc-menu-item mat-mdc-focus-indicator" href="/automations">Automations</a>
    <a mat-menu-item="" role="menuitem" class="mat-mdc-menu-item mat-mdc-focus-indicator" href="/forms">Sign-up forms</a>
    <a mat-menu-item="" role="menuitem" class="mat-mdc-menu-item mat-mdc-focus-indicator" href="/templates">Templates</a>
  </div>
  <main{ngc} class="page">
    <div{ngc} class="page-header">
      <div{ngc}><h1{ngc} class="mat-headline-small">Dashboard</h1><p{ngc} class="mat-body-medium subtle">Saltmarsh Outfitters · 84,312 subscribers</p></div>
      <mat-form-field{ngc} appearance="outline" class="mat-mdc-form-field period-field mat-mdc-form-field-type-mat-select">
        <div class="mat-mdc-text-field-wrapper mdc-text-field mdc-text-field--outlined"><div class="mat-mdc-form-field-infix">
          <mat-select role="combobox" aria-haspopup="listbox" aria-label="Reporting period" class="mat-mdc-select"><div class="mat-mdc-select-trigger"><div class="mat-mdc-select-value"><span class="mat-mdc-select-value-text"><span class="mat-mdc-select-min-line">Last 30 days</span></span></div><div class="mat-mdc-select-arrow-wrapper"><div class="mat-mdc-select-arrow"></div></div></div></mat-select>
        </div></div>
      </mat-form-field>
    </div>
    <div{ngc} class="stats-grid">
{chr(10).join(f'      <mat-card{ngc} appearance="outlined" class="mat-mdc-card mdc-card mat-mdc-card-outlined mdc-card--outlined stat-card"><mat-card-content{ngc} class="mat-mdc-card-content"><div{ngc} class="stat-label">{k.replace("Avg. open rate", "Open rate (avg.)").replace("Avg. click rate", "Click rate (avg.)")}</div><div{ngc} class="stat-value"{t_if(k == "Avg. open rate", "t6")}>{v}</div><div{ngc} class="stat-trend">{d}</div></mat-card-content></mat-card>' for k, v, d in [stats[4], stats[1], stats[2], stats[0], stats[3]])}
    </div>
    <ab-test-panel campaign-id="cmp_8841" class="ab-panel">
      <template shadowrootmode="open">
        <style>{ab_css}</style>
        <section class="panel" part="panel">
          <header class="head"><h2>A/B test · Black Friday Early Access</h2><span class="pill">Testing · 4h 12m left</span></header>
          <div class="variants">
{chr(10).join(v2_variant(*v) for v in variants)}
          </div>
          <form class="settings">
            <label for="winner-metric">Choose winner by</label>
            <select id="winner-metric" name="winnerMetric"{T("t4")}><option value="opens" selected>Open rate</option><option value="clicks">Click rate</option><option value="revenue">Revenue per recipient</option></select>
            <label for="test-duration">Test runs for</label>
            <select id="test-duration" name="durationHours"><option value="4">4 hours</option><option value="8" selected>8 hours</option><option value="24">24 hours</option></select>
            <button type="button" class="send-winner">Send winning variant now</button>
          </form>
        </section>
      </template>
    </ab-test-panel>
    <section{ngc} class="campaigns">
      <div{ngc} class="section-header">
        <h2{ngc} class="mat-title-medium">Campaigns</h2>
        <mat-button-toggle-group{ngc} role="group" aria-label="Filter campaigns" class="mat-button-toggle-group mat-button-toggle-group-appearance-standard">
          <mat-button-toggle class="mat-button-toggle mat-button-toggle-checked"><button type="button" class="mat-button-toggle-button" aria-pressed="true"><span class="mat-button-toggle-label-content">All</span></button></mat-button-toggle>
          <mat-button-toggle class="mat-button-toggle"><button type="button" class="mat-button-toggle-button" aria-pressed="false"><span class="mat-button-toggle-label-content">Needs attention</span></button></mat-button-toggle>
          <mat-button-toggle class="mat-button-toggle"><button type="button" class="mat-button-toggle-button" aria-pressed="false"><span class="mat-button-toggle-label-content">Scheduled</span></button></mat-button-toggle>
          <mat-button-toggle class="mat-button-toggle"><button type="button" class="mat-button-toggle-button" aria-pressed="false"><span class="mat-button-toggle-label-content">Sent</span></button></mat-button-toggle>
        </mat-button-toggle-group>
      </div>
      <div{ngc} class="campaign-grid">
{chr(10).join(v2_card(c) for c in v2_order)}
      </div>
    </section>
    <section{ngc} class="deliverability">
      <h2{ngc} class="mat-title-medium">Deliverability</h2>
      <mat-list{ngc} class="mat-mdc-list mat-mdc-list-base mdc-list">
        <mat-list-item class="mat-mdc-list-item mdc-list-item"><span class="mdc-list-item__content">Sender reputation <b>98 / 100</b></span></mat-list-item>
        <mat-list-item class="mat-mdc-list-item mdc-list-item"><span class="mdc-list-item__content">Bounce rate <b>0.6%</b></span></mat-list-item>
        <mat-list-item class="mat-mdc-list-item mdc-list-item"><span class="mdc-list-item__content">Spam complaints <b>0.02%</b></span></mat-list-item>
        <mat-list-item class="mat-mdc-list-item mdc-list-item"><span class="mdc-list-item__content">DMARC alignment <b>Pass</b></span></mat-list-item>
      </mat-list>
    </section>
  </main>
  <footer{ngc} class="app-footer">© 2026 Postwick Labs · <a href="/help">Help center</a> · <a href="/legal/anti-spam">Anti-spam policy</a></footer>
</app-root>
'''
    v2 = page("Dashboard · Postwick", v2_body, css="body{margin:0;font-family:Roboto,'Helvetica Neue',sans-serif;background:#fef7ff}",
              head='<base href="/">\n')

    targets = [
        tgt("t1", "'Pause' button on the 'Black Friday Early Access' campaign card (currently sending)",
            '[data-campaign-id="cmp_8841"] [data-qa="pause-campaign"]',
            "//article[.//h3[text()='Black Friday Early Access']]//button[text()='Pause']",
            ["testid-change", "copy-change", "sibling-reorder", "class-obfuscation", "attribute-churn", "structure-move", "decoy"]),
        tgt("t2", "'Resume' button on the paused 'Re-engagement: 90-day inactive' campaign card",
            ".pw-campaign-grid > article:nth-child(4) .pw-btn--primary",
            "//h3[contains(text(),'Re-engagement')]/ancestor::article//button[normalize-space()='Resume']",
            ["copy-change", "sibling-reorder", "class-obfuscation", "attribute-churn", "structure-move"]),
        tgt("t3", "Open rate of variant B in the A/B-test results (44.2%)",
            ".pw-ab-table tbody tr:nth-child(2) td.open-rate",
            "//table[contains(@class,'pw-ab-table')]//tr[td[1]='B']/td[4]",
            ["shadow-dom", "tag-change", "structure-move", "class-obfuscation"]),
        tgt("t4", "'Pick winner by' select of the A/B-test settings",
            "#ab-winner-metric",
            "//select[@name='winner_metric']",
            ["shadow-dom", "id-change", "attribute-churn", "copy-change", "structure-move"]),
        tgt("t5", "'Automations' item of the main navigation",
            '.pw-nav a[href="/automations"]',
            "//nav[@class='pw-nav']/a[3]",
            ["wrapper-divs", "sibling-reorder", "insertion", "class-obfuscation", "decoy"]),
        tgt("t6", "Value of the 'Avg. open rate' account statistic (41.8%)",
            ".pw-stats .pw-stat:nth-child(2) .pw-stat__value",
            "//span[text()='Avg. open rate']/following-sibling::strong",
            ["tag-change", "copy-change", "sibling-reorder", "class-obfuscation", "wrapper-divs", "decoy"]),
    ]
    m = meta(
        "dashboard-07", "Email-marketing campaign dashboard — Postwick",
        ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change", "copy-change",
         "tag-change", "attribute-churn", "structure-move", "insertion"],
        "v1 is a BEM-styled server-rendered page. v2 is an Angular Material rewrite (mat-card/mat-toolbar/mat-tab-nav-bar markup, "
        "_ngcontent attributes, ligature mat-icons): nav links get three wrapper divs, a new order and a new 'Sign-up forms' item "
        "(a hidden overflow menu repeats 'Automations'); stat values become divs in a new order with relabelled captions; campaign "
        "cards are regrouped (two sending campaigns first, so 'Pause sending' appears twice) and their buttons are MDC buttons with "
        "label spans ('Pause' -> 'Pause sending', 'Resume' -> 'Resume sending'). The A/B-test table becomes variant cards inside an "
        "<ab-test-panel> Lit element (declarative shadow root) placed above the campaigns, with a renamed winner-metric select.",
        targets,
    )
    return v1, v2, m


# ======================================================================================
# dashboard-08 — IoT device fleet console ("Sparrowgrid Fleet" for Greenhollow Farms)
# ======================================================================================
@suite
def dashboard_08():
    # id, label, type, location, status, battery, signal, firmware, update available, note
    devices = [
        ("GW-NORTH-01", "GW-North-01", "LoRaWAN gateway", "Bay 1", "Online", "Mains", "−61 dBm", "2.3.1", True),
        ("SM-A14", "SM-A14", "Soil moisture sensor", "Bed A, row 4", "Online", "64%", "−88 dBm", "2.3.1", True),
        ("SM-A15", "SM-A15", "Soil moisture sensor", "Bed A, row 5", "Online", "71%", "−90 dBm", "2.4.0", False),
        ("VALVE-07", "VALVE-07", "Irrigation valve", "Zone 3", "Online", "18%", "−79 dBm", "2.3.1", True),
        ("CL-N2", "CL-N2", "Climate sensor", "North aisle", "Offline", "41%", "—", "2.3.0", True),
        ("SM-B02", "SM-B02", "Soil moisture sensor", "Bed B, row 2", "Updating", "55%", "−84 dBm", "2.3.1 → 2.4.0", False),
        ("GW-NORTH-02", "GW-North-02", "LoRaWAN gateway", "Bay 4", "Online", "Mains", "−58 dBm", "2.4.0", False),
        ("VALVE-03", "VALVE-03", "Irrigation valve", "Zone 1", "Online", "77%", "−74 dBm", "2.4.0", False),
        ("CL-N1", "CL-N1", "Climate sensor", "South aisle", "Online", "89%", "−70 dBm", "2.3.1", True),
        ("SM-C11", "SM-C11", "Soil moisture sensor", "Bed C, row 11", "Online", "18%", "−92 dBm", "2.3.1", True),
        ("PUMP-02", "PUMP-02", "Pump controller", "Pump house", "Offline", "Mains", "—", "1.9.4", False),
        ("SM-B07", "SM-B07", "Soil moisture sensor", "Bed B, row 7", "Online", "93%", "−81 dBm", "2.4.0", False),
    ]
    pins = [(52, 40, "on"), (96, 62, "on"), (140, 44, "on"), (188, 70, "on"), (230, 52, "off"), (272, 86, "upd"),
            (318, 60, "on"), (70, 130, "on"), (128, 150, "on"), (186, 140, "on"), (244, 162, "off"), (300, 134, "on"),
            (350, 170, "on"), (90, 186, "on")]

    # ------------------------------------------------------------------ v1 (BEM, server-rendered)
    v1_css = """
body{margin:0;font:13px/1.45 "Roboto Condensed",Roboto,Arial,sans-serif;color:#1c2b2a;background:#eef3f1}
.sg-layout{display:flex;min-height:100vh}
.sg-sidebar{width:220px;background:#173f35;color:#d5e8e1;flex:none;display:flex;flex-direction:column}
.sg-menu{list-style:none;margin:0;padding:8px}.sg-menu__link{display:flex;gap:8px;padding:8px 10px;color:#d5e8e1;text-decoration:none;border-radius:4px}
.sg-menu__item--active .sg-menu__link{background:#24604f;color:#fff}
.sg-content{flex:1;min-width:0}
.sg-topbar{display:flex;align-items:center;gap:16px;padding:10px 20px;background:#fff;border-bottom:1px solid #d6e2dd}
.sg-main{padding:18px 20px}
.sg-summary{display:flex;gap:10px;margin-bottom:16px}
.sg-chip{display:flex;align-items:baseline;gap:6px;background:#fff;border-radius:6px;padding:8px 12px;border-left:4px solid #9bb}
.sg-chip--online{border-color:#2f9e6e}.sg-chip--offline{border-color:#c0392b}.sg-chip__count{font-size:20px;font-weight:700}
.sg-row{display:grid;grid-template-columns:2fr 1fr;gap:16px;margin-bottom:16px}
.sg-panel{background:#fff;border-radius:6px;padding:14px;border:1px solid #d6e2dd}
.sg-device-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
.sg-device{border:1px solid #d6e2dd;border-radius:6px;padding:10px}
.sg-status{font-size:11px;padding:1px 6px;border-radius:3px;background:#e1f3ea}.sg-status--offline{background:#fbe3e0}
.sg-device__stats{list-style:none;padding:0;margin:8px 0;display:grid;gap:2px}.sg-device__stats .k{color:#5f7a73;margin-right:6px}
.sg-btn{border:1px solid #24604f;background:#24604f;color:#fff;border-radius:4px;padding:5px 10px}
.sg-btn--warn{background:#b9770e;border-color:#b9770e}.sg-icon-btn{border:0;background:none;color:#5f7a73}
"""

    def v1_device(did, label, typ, loc, status, batt, sig, fw, upd):
        if upd:
            fw_action = f'<button type="button" class="sg-btn sg-btn--small btn-fw" data-testid="fw-update"{t_if(did == "SM-A14", "t1")}>Update firmware</button>'
        elif "→" in fw:
            fw_action = '<span class="sg-fw-state">Installing…</span>'
        else:
            fw_action = '<span class="sg-fw-state">Up to date</span>'
        return f'''          <div class="sg-device sg-device--{status.lower()}" data-device-id="{did}">
            <div class="sg-device__head"><span class="sg-status sg-status--{status.lower()}">{status}</span><h3 class="sg-device__name">{label}</h3></div>
            <p class="sg-device__type">{typ} · {loc}</p>
            <ul class="sg-device__stats">
              <li><span class="k">Battery</span><span class="v"{t_if(did == "VALVE-07", "t2")}>{batt}</span></li>
              <li><span class="k">Signal</span><span class="v">{sig}</span></li>
              <li><span class="k">Firmware</span><span class="v">{fw}</span></li>
            </ul>
            <div class="sg-device__actions">
              {fw_action}
              <button type="button" class="sg-icon-btn" aria-label="Reboot {label}" title="Reboot"{t_if(did == "GW-NORTH-01", "t4")}>{icon("power")}</button>
              <a class="sg-link" href="/devices/{did}">Details</a>
            </div>
          </div>'''

    def map_svg(cls_on, cls_off, cls_upd, grid_cls=""):
        g = f' class="{grid_cls}"' if grid_cls else ""
        lines = "".join(f'<line{g} x1="{x}" y1="10" x2="{x}" y2="210"/>' for x in range(40, 400, 60))
        lines += "".join(f'<line{g} x1="10" y1="{y}" x2="390" y2="{y}"/>' for y in range(30, 220, 50))
        circles = "".join(
            f'<circle class="{ {"on": cls_on, "off": cls_off, "upd": cls_upd}[s] }" cx="{x}" cy="{y}" r="5"/>' for x, y, s in pins)
        return (f'<svg viewBox="0 0 400 220" aria-hidden="true"><rect x="10" y="10" width="380" height="200" rx="6" fill="none"/>'
                f'{lines}{circles}</svg>')

    menu = [("/fleet", "Fleet overview", "grid"), ("/devices", "Devices", "cpu"), ("/groups", "Groups", "layers"),
            ("/firmware", "Firmware", "download"), ("/alerts", "Alerts", "bell"), ("/rules", "Rules &amp; automations", "zap"),
            ("/api-keys", "API keys", "lock"), ("/settings", "Settings", "settings")]
    v1_menu = "\n".join(
        f'      <li class="sg-menu__item{" sg-menu__item--active" if h == "/fleet" else ""}"><a href="{h}" class="sg-menu__link"'
        f'{" aria-current=" + chr(34) + "page" + chr(34) if h == "/fleet" else ""}>{icon(ic)}{lab}'
        f'{" <span class=" + chr(34) + "sg-count" + chr(34) + ">5</span>" if lab == "Alerts" else ""}</a></li>' for h, lab, ic in menu)
    chips = [("online", "214", "Online"), ("offline", "9", "Offline"), ("updating", "3", "Updating"),
             ("attention", "5", "Needs attention"), ("battery", "7", "Low battery")]

    v1_body = f'''
<div class="sg-layout">
  <nav class="sg-sidebar" aria-label="Console">
    <div class="sg-sidebar__brand">{icon("wifi")} Sparrowgrid <span class="sg-sidebar__product">Fleet</span></div>
    <ul class="sg-menu">
{v1_menu}
    </ul>
    <button type="button" class="sg-sidebar__collapse" aria-label="Collapse sidebar">{icon("chevron-left")}</button>
  </nav>
  <div class="sg-content">
    <header class="sg-topbar">
      <label class="sg-site"><span class="sg-site__label">Site</span>
        <select id="site-select" name="site"{T("t3")}>
          <option value="gh-north" selected>Greenhouse North</option>
          <option value="gh-south">Greenhouse South</option>
          <option value="orchard-c">Orchard Block C</option>
          <option value="packhouse">Packhouse</option>
        </select>
      </label>
      <input type="search" class="sg-search" placeholder="Search by device ID, name or tag" aria-label="Search devices">
      <span class="sg-sync">{icon("refresh")} Last sync 14:21:07</span>
      <button type="button" class="sg-avatar" aria-label="Account: Mateo Ruiz">MR</button>
    </header>
    <main class="sg-main">
      <h1 class="sg-title">Fleet overview <small>Greenhollow Farms</small></h1>
      <section class="sg-summary" aria-label="Fleet status">
{chr(10).join(f'        <div class="sg-chip sg-chip--{k}"><span class="sg-chip__count"{t_if(k == "offline", "t5")}>{n}</span><span class="sg-chip__label">{lab}</span></div>' for k, n, lab in chips)}
      </section>
      <div class="sg-row">
        <section class="sg-panel sg-map-panel">
          <h2 class="sg-panel__title">Device locations — Greenhouse North</h2>
          <div class="sg-map" role="img" aria-label="Map of Greenhouse North with device locations">
            {map_svg("sg-pin sg-pin--online", "sg-pin sg-pin--offline", "sg-pin sg-pin--updating", "sg-map__grid")}
          </div>
          <ul class="sg-map__legend"><li class="sg-legend sg-legend--online">Online</li><li class="sg-legend sg-legend--offline">Offline</li><li class="sg-legend sg-legend--updating">Updating</li></ul>
        </section>
        <section class="sg-panel sg-rollout">
          <h2 class="sg-panel__title">Firmware 2.4.0 rollout</h2>
          <p>Staged rollout to Greenhouse North · 38% complete (81 of 214 devices)</p>
          <progress class="sg-rollout__bar" value="38" max="100">38%</progress>
          <dl class="sg-rollout__facts">
            <div><dt>Started</dt><dd>Nov 3, 09:00</dd></div>
            <div><dt>Failures</dt><dd>2</dd></div>
            <div><dt>Next wave</dt><dd>Nov 5, 21:00</dd></div>
          </dl>
          <div class="sg-rollout__actions"><button type="button" class="sg-btn sg-btn--warn" id="pause-rollout"{T("t6")}>Pause rollout</button><a href="/firmware/2.4.0">Release notes</a></div>
        </section>
      </div>
      <section class="sg-panel sg-devices">
        <div class="sg-devices__head">
          <h2 class="sg-panel__title">Devices</h2>
          <div class="sg-filters">
            <select name="type" aria-label="Device type"><option selected>All types</option><option>Gateways</option><option>Soil sensors</option><option>Valves</option><option>Climate sensors</option><option>Pump controllers</option></select>
            <select name="status" aria-label="Status"><option selected>Any status</option><option>Online</option><option>Offline</option><option>Updating</option></select>
            <label class="sg-check"><input type="checkbox" name="outdated"> Only outdated firmware</label>
          </div>
        </div>
        <div class="sg-device-grid">
{chr(10).join(v1_device(*d) for d in devices)}
        </div>
        <div class="sg-pager">Showing 12 of 226 devices · <a href="/devices">View all devices</a></div>
      </section>
    </main>
    <footer class="sg-footer">Sparrowgrid Fleet 3.8 · Greenhollow Farms · <a href="https://docs.sparrowgrid.example">Docs</a> · <a href="https://status.sparrowgrid.example">Status</a></footer>
  </div>
</div>
'''
    v1 = page("Fleet overview · Sparrowgrid", v1_body, css=v1_css)

    # ------------------------------------------------------------------ v2 (SvelteKit + Lit web components)
    def sv(name):
        return "svelte-" + _hash("svelte:" + name, 6, _B36)

    s_app, s_nav, s_top, s_chips, s_roll, s_dev = (sv(n) for n in ("App", "Nav", "TopBar", "StatusChips", "Rollout", "Devices"))
    rank = {"VALVE-07": 0, "SM-C11": 1, "CL-N2": 2, "PUMP-02": 3, "SM-B02": 4}
    devices2 = sorted(devices, key=lambda d: (rank.get(d[0], 9), d[1]))
    card_css = (":host{display:block} .card{border-radius:10px;padding:12px;background:#fff;box-shadow:0 0 0 1px #dfe8e4}"
                " header{display:flex;justify-content:space-between;align-items:center} .status{font-size:11px;border-radius:999px;padding:1px 8px}"
                " .stats{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;margin:8px 0} .label{display:block;color:#6b827c;font-size:11px}"
                " .low{color:#c0392b;font-weight:600} .actions{display:flex;gap:6px;align-items:center}")

    def v2_card(did, label, typ, loc, status, batt, sig, fw, upd):
        st = status.lower()
        if upd:
            fw_action = f'<button type="button" class="primary" data-testid="fw-update"{t_if(did == "SM-A14", "t1")}>Update to 2.4.0</button>'
        elif "→" in fw:
            fw_action = '<span class="fw-note">Installing 2.4.0…</span>'
        else:
            fw_action = '<span class="fw-note">Up to date</span>'
        low = " low" if batt.endswith("%") and int(batt[:-1]) < 25 else ""
        return f'''              <device-card device-id="{did}" status="{st}">
                <template shadowrootmode="open">
                  <style>{card_css}</style>
                  <article class="card" part="card">
                    <header><h3 class="name">{label}</h3><span class="status {st}">{status}</span></header>
                    <p class="meta">{typ} · {loc}</p>
                    <div class="stats">
                      <div class="stat"><span class="label">Battery</span><span class="value{low}"{t_if(did == "VALVE-07", "t2")}>{batt}</span></div>
                      <div class="stat"><span class="label">Signal</span><span class="value">{sig}</span></div>
                      <div class="stat"><span class="label">Firmware</span><span class="value">{fw}</span></div>
                    </div>
                    <footer class="actions">
                      {fw_action}
                      <button type="button" class="icon" aria-label="Reboot device" title="Reboot"{t_if(did == "GW-NORTH-01", "t4")}>{icon("power")}</button>
                      <a href="/devices/{did}" class="details">Details</a>
                    </footer>
                  </article>
                </template>
              </device-card>'''

    nav2 = [("/fleet", "Overview", "grid"), ("/devices", "Devices", "cpu"), ("/alerts", "Alerts", "bell"),
            ("/firmware", "Firmware", "download"), ("/groups", "Groups", "layers"), ("/rules", "Automations", "zap"),
            ("/api-keys", "API keys", "lock"), ("/settings", "Settings", "settings")]
    v2_nav = "\n".join(
        f'        <a href="{h}" class="item{" active" if h == "/fleet" else ""} {s_nav}"{" aria-current=" + chr(34) + "page" + chr(34) if h == "/fleet" else ""}>'
        f'{icon(ic)}<span class="label {s_nav}">{lab}</span>{"<b class=" + chr(34) + "count " + s_nav + chr(34) + ">5</b>" if lab == "Alerts" else ""}</a>'
        for h, lab, ic in nav2)
    chips2 = [("warn", "5", "Needs attention"), ("off", "9", "Offline"), ("upd", "3", "Updating"), ("low", "7", "Low battery"),
              ("on", "214", "Online")]
    map_css = ":host{display:block;border-radius:10px;overflow:hidden;background:#f4f8f6} svg{width:100%;height:auto} line{stroke:#dce7e2} .on{fill:#2f9e6e} .off{fill:#c0392b} .upd{fill:#e0a526}"
    grid_css = ":host{display:block} .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px}"

    v2_body = f'''
<div class="app {s_app}">
  <aside class="rail {s_app}" aria-label="Console navigation">
    <a class="logo {s_app}" href="/fleet">{icon("wifi")}<span>Sparrowgrid</span></a>
    <nav class="menu {s_nav}">
{v2_nav}
    </nav>
  </aside>
  <div class="main {s_app}">
    <header class="topbar {s_top}">
      <h1 class="title {s_top}">Greenhollow Farms <span class="sub {s_top}">Fleet</span></h1>
      <div class="site-picker {s_top}">
        <label for="site-s1" class="{s_top}">Location</label>
        <select id="site-s1" name="siteId" class="{s_top}"{T("t3")}>
          <option value="gh-north" selected>Greenhouse North</option>
          <option value="gh-south">Greenhouse South</option>
          <option value="orchard-c">Orchard Block C</option>
          <option value="packhouse">Packhouse</option>
        </select>
      </div>
      <div class="search {s_top}">{icon("search")}<input type="search" placeholder="Find a device…" aria-label="Find a device" class="{s_top}"></div>
      <span class="sync {s_top}">Synced 14:21</span>
      <button type="button" class="avatar {s_top}" aria-label="Account menu">MR</button>
    </header>
    <div class="status-filters {s_chips}" role="group" aria-label="Filter devices by status">
{chr(10).join(f'      <button type="button" class="chip {k} {s_chips}" aria-pressed="false"><span class="num {s_chips}"{t_if(k == "off", "t5")}>{n}</span> {lab}</button>' for k, n, lab in chips2)}
    </div>
    <div class="overview-grid {s_app}">
      <section class="card rollout {s_roll}" aria-labelledby="rollout-h">
        <div class="card-head {s_roll}"><h2 id="rollout-h" class="{s_roll}">Firmware rollout · 2.4.0</h2><span class="pill {s_roll}">Wave 2 of 4</span></div>
        <div class="progress {s_roll}" role="progressbar" aria-valuenow="38" aria-valuemin="0" aria-valuemax="100"><div class="fill {s_roll}" style="width:38%"></div></div>
        <p class="{s_roll}">81 of 214 devices updated · 2 failures · next wave Nov 5, 21:00</p>
        <div class="actions {s_roll}"><a href="/firmware/2.4.0" class="{s_roll}">Release notes</a><button type="button" class="btn danger {s_roll}"{T("t6")}>Pause rollout</button></div>
      </section>
      <fleet-map site="gh-north" class="{s_app}">
        <template shadowrootmode="open">
          <style>{map_css}</style>
          <figure class="map" part="map">
            {map_svg("on", "off", "upd")}
            <figcaption>Greenhouse North · 14 devices shown</figcaption>
          </figure>
        </template>
      </fleet-map>
    </div>
    <section class="card devices {s_dev}" aria-labelledby="devices-h">
      <div class="card-head {s_dev}">
        <h2 id="devices-h" class="{s_dev}">Devices</h2>
        <span class="hint {s_dev}">Needs attention first</span>
        <select name="type" aria-label="Device type" class="{s_dev}"><option selected>All types</option><option>Gateways</option><option>Soil sensors</option><option>Valves</option><option>Climate sensors</option><option>Pump controllers</option></select>
        <button type="button" role="switch" aria-checked="false" class="switch {s_dev}">Outdated firmware only</button>
      </div>
      <device-grid page-size="12">
        <template shadowrootmode="open">
          <style>{grid_css}</style>
          <div class="grid" part="grid">
{chr(10).join(v2_card(*d) for d in devices2)}
          </div>
          <nav class="pager" aria-label="Device pages"><span>1–12 of 226</span><a href="/devices?page=2">Next</a></nav>
        </template>
      </device-grid>
    </section>
    <footer class="footer {s_app}">Sparrowgrid Fleet 4.0 · <a href="https://docs.sparrowgrid.example">Docs</a> · <a href="https://status.sparrowgrid.example">Status</a></footer>
  </div>
</div>
<dialog class="confirm {s_roll}" aria-labelledby="confirm-h">
  <h2 id="confirm-h" class="{s_roll}">Pause the 2.4.0 rollout?</h2>
  <p class="{s_roll}">Devices that already updated keep 2.4.0. The remaining waves are put on hold until you resume.</p>
  <form method="dialog" class="{s_roll}"><button value="cancel" class="btn {s_roll}">Keep rolling out</button><button value="confirm" class="btn danger {s_roll}">Pause rollout</button></form>
</dialog>
'''
    v2 = page("Greenhollow Farms · Fleet · Sparrowgrid", v2_body,
              css="body{margin:0;font:14px/1.5 'Inter',system-ui,sans-serif;background:#f3f6f5;color:#14211e}",
              head='<link rel="modulepreload" href="/_app/immutable/entry/start.js">\n')

    targets = [
        tgt("t1", "'Update firmware' button on the device card SM-A14",
            '.sg-device[data-device-id="SM-A14"] .btn-fw',
            "//div[h3[text()='SM-A14']]/following-sibling::div[contains(@class,'actions')]/button[normalize-space()='Update firmware']",
            ["shadow-dom", "copy-change", "sibling-reorder", "class-obfuscation", "attribute-churn", "wrapper-divs", "decoy"]),
        tgt("t2", "Battery level of the irrigation valve VALVE-07 (18%)",
            '[data-device-id="VALVE-07"] .sg-device__stats li:first-child .v',
            "//div[@data-device-id='VALVE-07']//span[@class='k' and text()='Battery']/following-sibling::span",
            ["shadow-dom", "sibling-reorder", "class-obfuscation", "attribute-churn", "wrapper-divs", "decoy"]),
        tgt("t3", "Site switcher select in the top bar",
            "#site-select",
            "//label[span='Site']/select",
            ["id-change", "attribute-churn", "copy-change", "class-obfuscation", "wrapper-divs"]),
        tgt("t4", "Icon-only 'Reboot' button of the gateway GW-North-01",
            'button[aria-label="Reboot GW-North-01"]',
            "//div[@data-device-id='GW-NORTH-01']//button[@title='Reboot']",
            ["shadow-dom", "attribute-churn", "sibling-reorder", "class-obfuscation"]),
        tgt("t5", "Count in the 'Offline' fleet-status summary chip (9)",
            ".sg-chip--offline .sg-chip__count",
            "//span[text()='Offline']/preceding-sibling::span",
            ["tag-change", "sibling-reorder", "class-obfuscation", "structure-move"]),
        tgt("t6", "'Pause rollout' button of the firmware 2.4.0 rollout panel",
            "#pause-rollout",
            "//button[normalize-space()='Pause rollout']",
            ["id-change", "sibling-reorder", "class-obfuscation", "structure-move", "decoy"]),
    ]
    m = meta(
        "dashboard-08", "IoT device fleet console — Sparrowgrid Fleet",
        ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change", "copy-change",
         "tag-change", "attribute-churn", "structure-move", "insertion"],
        "v2 is a SvelteKit rewrite (scoped svelte-* classes). The device list becomes a <device-grid> web component whose "
        "cards are <device-card> web components, i.e. nested declarative shadow roots; cards are re-sorted with devices that "
        "need attention first, 'Update firmware' becomes 'Update to 2.4.0' and every reboot button shares the aria-label "
        "'Reboot device'. Another sensor (SM-C11) also reports 18% battery. The summary chips become filter buttons in a new "
        "order with the label as bare text. The rollout panel moves before the map (now a <fleet-map> shadow root), swaps its "
        "action order and a confirmation <dialog> repeats 'Pause rollout'. The site select is relabelled 'Location'.",
        targets,
    )
    return v1, v2, m


# ======================================================================================
# dashboard-09 — customer-support helpdesk overview ("Quokka Desk" for Pinecrest Software)
# ======================================================================================
@suite
def dashboard_09():
    # id, subject, requester, priority, sla (v1 text), sla state, minutes left, channel, created
    tickets = [
        ("48213", "Refund not received for order #77120", "Grace Okafor", "High", "0h 42m", "warning", 42, "Email", "Today 09:14"),
        ("48190", "SSO login loop for entire team", "Viktor Lindgren", "Urgent", "0h 08m", "danger", 8, "Chat", "Today 08:51"),
        ("48177", "Export to CSV times out for large reports", "Mei Chen", "Normal", "3h 15m", "ok", 195, "Email", "Today 08:02"),
        ("48172", "Can't add a second billing contact", "Daniel Osei", "Low", "6h 40m", "ok", 400, "Web form", "Today 07:40"),
        ("48166", "Webhook deliveries failing with 401", "Laura Becker", "High", "−0h 12m", "breached", -12, "Email", "Today 07:12"),
        ("48159", "Invoice shows wrong VAT number", "Tomasz Wiśniewski", "Normal", "2h 05m", "ok", 125, "Email", "Yesterday 18:33"),
        ("48151", "Mobile app crashes when uploading photos", "Ana Lima", "High", "1h 20m", "warning", 80, "In-app", "Yesterday 17:02"),
        ("48144", "Request: dark mode for the dashboard", "Kofi Mensah", "Low", "1d 2h", "ok", 1560, "Community", "Yesterday 15:47"),
        ("48139", "Password reset email never arrives", "Sophie Martin", "Normal", "4h 50m", "ok", 290, "Phone", "Yesterday 14:20"),
        ("48131", "Charged twice for annual plan", "Ravi Shankar", "Urgent", "0h 31m", "warning", 31, "Phone", "Yesterday 13:05"),
    ]
    views = [("unassigned", "Unassigned", "14"), ("mine", "My open tickets", "9"), ("urgent", "Urgent", "3"),
             ("pending", "Waiting on customer", "22"), ("billing", "Billing", "11"), ("bugs", "Bugs &amp; defects", "7"),
             ("solved", "Recently solved", "")]
    team_views = [("tier2", "Tier 2 escalations", "4"), ("vip", "VIP accounts", "2"), ("refunds", "Refund requests", "6")]
    agents = [("Tobias Kern", "Online", 9), ("Amina Yusuf", "Online", 12), ("Jonas Berg", "Away", 7), ("Lucía Ortega", "Online", 10),
              ("Ewan MacLeod", "Online", 5), ("Hye-jin Park", "Away", 8)]
    stats = [("First response time (today)", "1h 12m"), ("SLA compliance (7 days)", "94.3%"), ("Tickets solved today", "58"),
             ("CSAT (30 days)", "4.6 / 5")]

    # ------------------------------------------------------------------ v1
    v1_css = """
body{margin:0;font:13px/1.5 "Lato",Arial,sans-serif;color:#2f3941;background:#f8f9f9}
.qd-topbar{display:flex;align-items:center;gap:14px;height:52px;padding:0 16px;background:#03363d;color:#fff}
.qd-search input{width:320px;border-radius:4px;border:0;padding:6px 10px}
.qd-btn{display:inline-block;border-radius:4px;padding:5px 12px;border:1px solid #1f73b7;background:#fff;color:#1f73b7;text-decoration:none}
.qd-btn-new{background:#1f73b7;color:#fff}
.qd-body{display:grid;grid-template-columns:230px 1fr 260px;min-height:calc(100vh - 52px)}
.qd-views{background:#fff;border-right:1px solid #d8dcde;padding:12px}
.qd-view-list{list-style:none;margin:0;padding:0}.qd-view{display:flex;justify-content:space-between;padding:6px 8px;border-radius:4px;color:#2f3941;text-decoration:none}
.qd-view.active{background:#e9ebed;font-weight:700}
.qd-main{padding:16px}
.qd-tickets{width:100%;border-collapse:collapse;background:#fff}.qd-tickets td,.qd-tickets th{padding:8px;border-bottom:1px solid #e9ebed;text-align:left}
.qd-sla{font-weight:700;padding:1px 6px;border-radius:3px}.qd-sla-warning{background:#fff0c7}.qd-sla-danger,.qd-sla-breached{background:#fde8e8;color:#cc3340}
.qd-prio{font-size:11px;text-transform:uppercase}
.qd-stats dl{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.qd-stats dd{margin:0;font-size:20px;font-weight:700}
.qd-side{border-left:1px solid #d8dcde;padding:12px;background:#fff}
"""
    presence_css = ":host{display:inline-flex} .presence{display:inline-flex;align-items:center;gap:6px} .dot{width:8px;height:8px;border-radius:50%;background:#5eae91}"

    def v1_ticket(tid, subj, req, prio, sla, state, _m, chan, created):
        return f'''          <tr class="qd-ticket" data-ticket-id="{tid}">
            <td><input type="checkbox" aria-label="Select ticket #{tid}"></td>
            <td class="qd-subject"><a href="/agent/tickets/{tid}">{subj}</a> <span class="qd-ticket-id">#{tid}</span></td>
            <td class="qd-requester">{req}</td>
            <td><span class="qd-prio qd-prio-{prio.lower()}">{prio}</span></td>
            <td><span class="qd-sla qd-sla-{state}"{t_if(tid == "48190", "t2")}>{sla}</span></td>
            <td class="qd-channel">{chan}</td>
            <td class="qd-created">{created}</td>
            <td class="qd-actions"><button type="button" class="qd-btn qd-btn-claim"{t_if(tid == "48213", "t1")}>Claim</button></td>
          </tr>'''

    v1_views = "\n".join(
        f'        <li><a href="/agent/views/{k}" class="qd-view{" active" if k == "unassigned" else ""}"{t_if(k == "pending", "t3")}>{lab}'
        f'{(" <span class=" + chr(34) + "qd-count" + chr(34) + ">" + n + "</span>") if n else ""}</a></li>' for k, lab, n in views)
    v1_team = "\n".join(f'        <li><a href="/agent/views/{k}" class="qd-view">{lab} <span class="qd-count">{n}</span></a></li>' for k, lab, n in team_views)

    v1_body = f'''
<header class="qd-topbar">
  <a class="qd-logo" href="/agent">Quokka Desk</a>
  <form class="qd-search" role="search" action="/agent/search"><input type="search" name="q" placeholder="Search tickets, customers, articles" aria-label="Search"></form>
  <a href="/agent/tickets/new" class="qd-btn qd-btn-new"{T("t5")}>+ New ticket</a>
  <presence-switch agent="tkern">
    <template shadowrootmode="open">
      <style>{presence_css}</style>
      <label class="presence"><span class="dot"></span><span class="sr">Status</span>
        <select id="agent-status" name="status"{T("t4")}><option value="online" selected>Online</option><option value="away">Away</option><option value="offline">Offline</option></select>
      </label>
    </template>
  </presence-switch>
  <button type="button" class="qd-icon" aria-label="Notifications">{icon("bell")}</button>
  <span class="qd-avatar" title="Tobias Kern">TK</span>
</header>
<div class="qd-body">
  <aside class="qd-views">
    <h2 class="qd-views-title">Views</h2>
    <ul class="qd-view-list">
{v1_views}
    </ul>
    <h2 class="qd-views-title">Team views</h2>
    <ul class="qd-view-list">
{v1_team}
    </ul>
    <a href="/agent/views/manage" class="qd-manage">Manage views</a>
  </aside>
  <main class="qd-main">
    <div class="qd-queue-head">
      <h1>Unassigned</h1>
      <span class="qd-muted">14 tickets · sorted by created date</span>
      <div class="qd-bulk"><button type="button" class="qd-btn" disabled>Assign selected</button><button type="button" class="qd-btn" disabled>Merge</button></div>
    </div>
    <section class="qd-stats" aria-label="Team performance">
      <dl>
{chr(10).join(f'        <div class="qd-stat"><dt>{k}</dt><dd{t_if(k.startswith("First response"), "t6")}>{v}</dd></div>' for k, v in stats)}
      </dl>
    </section>
    <table class="qd-tickets">
      <thead><tr><th><input type="checkbox" aria-label="Select all tickets"></th><th>Subject</th><th>Requester</th><th>Priority</th><th>SLA</th><th>Channel</th><th>Created</th><th></th></tr></thead>
      <tbody>
{chr(10).join(v1_ticket(*t) for t in tickets)}
      </tbody>
    </table>
    <div class="qd-pager">1–10 of 14 · <a href="?page=2">Next page</a></div>
  </main>
  <aside class="qd-side">
    <h2>Agents online</h2>
    <ul class="qd-agents">
{chr(10).join(f'      <li class="qd-agent"><span class="qd-agent-name">{n}</span><span class="qd-agent-status qd-{s.lower()}">{s}</span><span class="qd-agent-load">{o} open</span></li>' for n, s, o in agents)}
    </ul>
    <h2>Popular macros</h2>
    <ul class="qd-macros"><li><a href="/agent/macros/12">Refund — request bank details</a></li><li><a href="/agent/macros/7">SSO troubleshooting checklist</a></li><li><a href="/agent/macros/31">Close — no reply 7 days</a></li></ul>
  </aside>
</div>
<footer class="qd-footer">Quokka Desk · Pinecrest Software support · <a href="/agent/shortcuts">Keyboard shortcuts</a></footer>
'''
    v1 = page("Unassigned – Quokka Desk", v1_body, css=v1_css)

    # ------------------------------------------------------------------ v2 (Fluent UI v9 / Griffel atomic classes)
    def flu(component, slot="", n=4):
        base = f"fui-{component}" + (f"__{slot}" if slot else "")
        key = f"{component}:{slot}"
        reset = "r" + _hash("griffel-r:" + key, 7, _B36)
        atoms = " ".join("f" + _hash(f"griffel:{key}:{i}", 7, _B36) for i in range(n))
        return f"{base} {reset} {atoms}"

    def atom(name, n=3):
        return "___" + _hash("griffel-m:" + name, 7, _B36) + "_" + _hash("griffel-m2:" + name, 7, _B36) + " " + \
            " ".join("f" + _hash(f"griffel-a:{name}:{i}", 7, _B36) for i in range(n))

    def btn(label, appearance="secondary", attrs="", icon_name=None):
        ic = f'<span class="{flu("Button", "icon", 2)}">{icon(icon_name)}</span>' if icon_name else ""
        extra = " " + atom("btn-" + appearance, 2)
        return f'<button type="button" class="{flu("Button", "", 6)}{extra}"{attrs}>{ic}{label}</button>'

    order = sorted(tickets, key=lambda t: t[6])

    def sla2(minutes):
        if minutes < 0:
            return f"−{-minutes}m", "breached"
        if minutes < 60:
            return f"{minutes}m", "danger" if minutes < 15 else "warning"
        if minutes < 1440:
            return f"{minutes // 60}h {minutes % 60:02d}m", "ok"
        return f"{minutes // 1440}d {minutes % 1440 // 60}h", "ok"

    timer_css = ":host{display:inline-flex} .timer{font:600 12px/1 'Segoe UI',sans-serif;padding:3px 6px;border-radius:4px} .breached,.danger{background:#fde7e9;color:#b10e1c} .warning{background:#fff4ce;color:#835b00}"

    def v2_row(i, tid, subj, req, prio, _sla, _state, minutes, chan, created):
        txt, st = sla2(minutes)
        return f'''          <div role="row" aria-rowindex="{i + 2}" class="{flu("DataGridRow", "", 5)}">
            <div role="gridcell" class="{flu("DataGridCell", "", 3)}"><span class="{flu("Checkbox", "", 2)}"><input type="checkbox" class="{flu("Checkbox", "input", 2)}" aria-label="Select row"></span></div>
            <div role="gridcell" class="{flu("DataGridCell", "", 3)} {atom("subject-cell")}"><div class="{atom("subject")}"><a href="/agent/tickets/{tid}" class="{flu("Link", "", 3)}">{subj}</a><span class="{flu("Text", "", 2)}">#{tid} · {req}</span></div></div>
            <div role="gridcell" class="{flu("DataGridCell", "", 3)}"><span class="{flu("Badge", "", 4)}">{prio}</span></div>
            <div role="gridcell" class="{flu("DataGridCell", "", 3)}"><sla-timer remaining="{minutes}" state="{st}"><template shadowrootmode="open"><style>{timer_css}</style><span class="timer {st}" part="timer"{t_if(tid == "48190", "t2")}>{txt}</span></template></sla-timer></div>
            <div role="gridcell" class="{flu("DataGridCell", "", 3)}">{chan}</div>
            <div role="gridcell" class="{flu("DataGridCell", "", 3)}">{created}</div>
            <div role="gridcell" class="{flu("DataGridCell", "", 3)}">{btn("Assign to me", "subtle", t_if(tid == "48213", "t1"))}</div>
          </div>'''

    views2 = [("unassigned", "Unassigned", "14"), ("mine", "Mine", "9"), ("urgent", "Urgent", "3"), ("billing", "Billing", "11"),
              ("pending", "Awaiting customer", "22"), ("bugs", "Bugs", "7"), ("solved", "Solved", "")]

    def tab(k, lab, n):
        sel = k == "unassigned"
        badge = f'<span class="{flu("CounterBadge", "", 3)}">{n}</span>' if n else ""
        return (f'<button type="button" role="tab" value="{k}" aria-selected="{str(sel).lower()}" class="{flu("Tab", "", 5)}"{t_if(k == "pending", "t3")}>'
                f'<span class="{flu("Tab", "content", 2)}">{lab}</span>{badge}</button>')

    def menu_item(k, lab, n):
        badge = f'<span class="{flu("CounterBadge", "", 3)}">{n}</span>' if n else ""
        return f'<button type="button" role="menuitem" class="{flu("MenuItem", "", 4)}"><span class="{flu("Tab", "content", 2)}">{lab}</span>{badge}</button>'

    stats2 = [("First reply · today", "1h 12m"), ("SLA met · 7 days", "94.3%"), ("Solved today", "58"), ("CSAT · 30 days", "4.6 / 5")]

    v2_body = f'''
<div id="root">
<div class="fui-FluentProvider fui-FluentProviderr0 {atom("provider", 4)}" dir="ltr">
  <div class="{atom("shell", 5)}">
    <header class="{atom("header", 6)}">
      <a href="/agent" class="{atom("logo", 2)}">{icon("message")}<span>Quokka Desk</span></a>
      <span class="{flu("SearchBox", "", 4)}"><span class="{flu("Input", "contentBefore", 2)}">{icon("search")}</span><input type="search" class="{flu("Input", "input", 3)}" placeholder="Search tickets, people and articles" aria-label="Search"></span>
      <div class="{atom("header-actions", 3)}">
        <button type="button" aria-label="Create" aria-haspopup="menu" aria-expanded="false" class="{flu("MenuButton", "", 4)}">{icon("plus")}</button>
        <div role="menu" class="{flu("MenuPopover", "", 3)}" hidden>
          <a role="menuitem" href="/agent/tickets/new" class="{flu("MenuItem", "", 4)}">New ticket</a>
          <a role="menuitem" href="/agent/macros/new" class="{flu("MenuItem", "", 4)}">New macro</a>
          <a role="menuitem" href="/agent/articles/new" class="{flu("MenuItem", "", 4)}">New help article</a>
        </div>
        <div class="{atom("presence", 3)}">
          <span role="img" aria-label="Available" class="{flu("PresenceBadge", "", 3)}"></span>
          <span class="{flu("Select", "", 3)}"><select id="presence-select" name="status" aria-label="Your status" class="{flu("Select", "select", 4)}"{T("t4")}><option value="online" selected>Available</option><option value="away">Away</option><option value="dnd">Do not disturb</option><option value="offline">Appear offline</option></select><span class="{flu("Select", "icon", 2)}">{icon("chevron-down")}</span></span>
        </div>
        <button type="button" aria-label="Notifications" class="{flu("Button", "", 6)}">{icon("bell")}</button>
        <span role="img" aria-label="Tobias Kern" class="{flu("Avatar", "", 3)}"><span class="{flu("Avatar", "initials", 2)}">TK</span></span>
      </div>
    </header>
    <main class="{atom("main", 4)}">
      <div class="{atom("queue-head", 4)}">
        <div><h1 class="{flu("Text", "", 3)}">Unassigned</h1><span class="{flu("Text", "", 2)}">14 tickets · sorted by SLA</span></div>
        <div class="{atom("queue-actions", 2)}">{btn("Assign selected", "secondary", " disabled")}{btn("New ticket", "primary", T("t5"), "plus")}</div>
      </div>
      <div role="tablist" aria-orientation="horizontal" aria-label="Views" class="{flu("TabList", "", 4)}">
        {"".join(tab(*v) for v in views2)}
        <button type="button" aria-label="More views" aria-haspopup="menu" class="{flu("Button", "", 6)}">{icon("more-h")}</button>
      </div>
      <div role="menu" aria-label="All views" class="{flu("MenuList", "", 3)}" hidden>
        {"".join(menu_item(*v) for v in views2)}
        {"".join(menu_item(*v) for v in [("tier2", "Tier 2 escalations", "4"), ("vip", "VIP accounts", "2"), ("refunds", "Refund requests", "6")])}
      </div>
      <section class="{atom("stats", 3)}" aria-label="Team performance">
{chr(10).join(f'        <div class="{flu("Card", "", 4)}"><span class="{flu("Text", "", 2)} {atom("stat-label", 1)}">{k}</span><span class="{flu("Text", "", 2)} {atom("stat-value", 2)}"{t_if(k.startswith("First reply"), "t6")}>{v}</span></div>' for k, v in stats2)}
      </section>
      <div role="grid" aria-label="Tickets" aria-rowcount="15" class="{flu("DataGrid", "", 4)}">
        <div role="rowgroup" class="{flu("DataGridHeader", "", 3)}">
          <div role="row" class="{flu("DataGridRow", "", 5)}">
            <div role="columnheader" class="{flu("DataGridHeaderCell", "", 3)}"><span class="{flu("Checkbox", "", 2)}"><input type="checkbox" class="{flu("Checkbox", "input", 2)}" aria-label="Select all rows"></span></div>
            <div role="columnheader" class="{flu("DataGridHeaderCell", "", 3)}">Ticket</div>
            <div role="columnheader" class="{flu("DataGridHeaderCell", "", 3)}">Priority</div>
            <div role="columnheader" class="{flu("DataGridHeaderCell", "", 3)}" aria-sort="ascending">SLA</div>
            <div role="columnheader" class="{flu("DataGridHeaderCell", "", 3)}">Channel</div>
            <div role="columnheader" class="{flu("DataGridHeaderCell", "", 3)}">Created</div>
            <div role="columnheader" class="{flu("DataGridHeaderCell", "", 3)}"><span class="{atom("visually-hidden", 1)}">Actions</span></div>
          </div>
        </div>
        <div role="rowgroup" class="{flu("DataGridBody", "", 3)}">
{chr(10).join(v2_row(i, *t) for i, t in enumerate(order))}
        </div>
      </div>
      <nav aria-label="Pagination" class="{atom("pager", 2)}"><span>1–10 of 14</span>{btn("Next page", "subtle")}</nav>
    </main>
    <aside class="{atom("side", 4)}" aria-label="Team">
      <h2 class="{flu("Text", "", 2)}">Team presence</h2>
      <ul class="{atom("agents", 2)}">
{chr(10).join(f'        <li class="{atom("agent", 2)}"><span role="img" aria-label="{s}" class="{flu("PresenceBadge", "", 3)}"></span><span>{n}</span><span class="{flu("Text", "", 2)}">{o} open</span></li>' for n, s, o in agents)}
      </ul>
    </aside>
  </div>
</div>
</div>
'''
    v2 = page("Unassigned · Quokka Desk", v2_body, css="body{margin:0;background:#fafafa}")

    targets = [
        tgt("t1", "'Claim' button of ticket #48213 ('Refund not received for order #77120')",
            'tr[data-ticket-id="48213"] .qd-btn-claim',
            "//tr[.//span[text()='#48213']]//button[text()='Claim']",
            ["copy-change", "tag-change", "sibling-reorder", "class-obfuscation", "wrapper-divs", "decoy"]),
        tgt("t2", "SLA countdown of ticket #48190 ('SSO login loop for entire team')",
            "table.qd-tickets tbody tr:nth-child(2) .qd-sla",
            "//a[contains(text(),'SSO login loop')]/ancestor::tr/td[5]/span",
            ["shadow-dom", "copy-change", "sibling-reorder", "tag-change", "class-obfuscation"]),
        tgt("t3", "'Waiting on customer' view in the ticket-views navigation",
            ".qd-view-list li:nth-child(4) a",
            "//a[starts-with(normalize-space(),'Waiting on customer')]",
            ["tag-change", "structure-move", "copy-change", "sibling-reorder", "class-obfuscation", "decoy"]),
        tgt("t4", "Agent presence/status select (Online / Away / Offline)",
            "presence-switch select#agent-status",
            "//select[@name='status']",
            ["shadow-dom", "structure-move", "id-change", "copy-change", "class-obfuscation", "wrapper-divs"]),
        tgt("t5", "'New ticket' action in the top bar",
            "a.qd-btn-new",
            "//header//a[contains(.,'New ticket')]",
            ["tag-change", "structure-move", "copy-change", "class-obfuscation", "decoy"]),
        tgt("t6", "'First response time (today)' statistic value (1h 12m)",
            ".qd-stats dl > div:first-child dd",
            "//dt[starts-with(text(),'First response time')]/following-sibling::dd",
            ["tag-change", "copy-change", "class-obfuscation", "wrapper-divs"]),
    ]
    m = meta(
        "dashboard-09", "Customer-support helpdesk queue overview — Quokka Desk",
        ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change", "copy-change",
         "tag-change", "attribute-churn", "structure-move", "insertion"],
        "v1 is a classic three-column agent workspace whose presence select lives in a <presence-switch> shadow root. v2 is a "
        "Fluent UI v9 rewrite with atomic Griffel classes: the presence select moves out of shadow DOM into the header "
        "(keeping name='status'); the views sidebar becomes a horizontal TabList of role=tab buttons ('Waiting on customer' -> "
        "'Awaiting customer', reordered) with a hidden overflow menu repeating every view; the ticket <table> becomes a "
        "role=grid DataGrid sorted by SLA, each SLA timer is an <sla-timer> web component (declarative shadow root) with "
        "shorter copy ('0h 08m' -> '8m'), and 'Claim' becomes 'Assign to me' on every row. 'New ticket' turns from a header "
        "link into a queue-header button while a hidden 'Create' menu in the header keeps a 'New ticket' link. Stat values "
        "become Fluent Text spans with new captions.",
        targets,
    )
    return v1, v2, m


# ======================================================================================
# dashboard-10 — LMS instructor dashboard ("Lanternhall" at Westbrook Community College)
# ======================================================================================
@suite
def dashboard_10():
    # code, slug, title, meta, students, waitlist, colour
    courses = [
        ("BIO 101", "bio-101", "Introduction to Biology", "Sections 01–03 · MWF 9:00 AM · Science Hall 204", 142, 3, "#2f6f5e"),
        ("CHEM 210", "chem-210", "Organic Chemistry I", "Section 01 · TTh 11:00 AM · Lab B", 64, 0, "#8a4b2f"),
        ("BIO 330", "bio-330", "Genetics", "Section 01 · MW 1:30 PM · Science Hall 112", 38, 1, "#3d5a98"),
        ("HON 199", "hon-199", "Honors Seminar: Science &amp; Society", "Section 01 · F 2:00 PM · Library 3A", 18, 0, "#7a3d84"),
    ]
    # assignment, course, due, submitted, to grade, assignment id
    queue = [
        ("Lab Report 4: Enzyme Kinetics", "BIO 101", "Oct 30", "131 / 142", 47, "4412"),
        ("Problem Set 6: Stereochemistry", "CHEM 210", "Nov 2", "58 / 64", 18, "5120"),
        ("Midterm reflection essay", "HON 199", "Oct 31", "17 / 18", 9, "6007"),
        ("Quiz 7: Pedigree analysis (short answer)", "BIO 330", "Nov 3", "36 / 38", 11, "5531"),
    ]
    announcements = [("CHEM 210", "Office hours moved to Wednesday this week", "Nov 3"),
                     ("BIO 101", "Lab 5 safety quiz is now open", "Nov 2"),
                     ("HON 199", "Guest speaker on Friday: Dr. Ilse Brandt", "Oct 29")]
    todo = [("Nov 6", "BIO 101 Lab 5 — enzyme assays"), ("Nov 9", "CHEM 210 Exam 2 (in class)"),
            ("Nov 11", "Veterans Day — no classes"), ("Nov 13", "BIO 330 Problem set 8 due"),
            ("Nov 20", "Midterm grades due to registrar")]
    # student, login, course, flag, flag kind, last active
    check_ins = [("Marcus Delgado", "mdelgado", "BIO 101", "3 missing assignments", "missing", "Oct 27"),
                 ("Hannah Vu", "hvu", "CHEM 210", "Grade below 60%", "grade", "Nov 3"),
                 ("Tyler Brooks", "tbrooks", "BIO 330", "Not active for 9 days", "inactive", "Oct 26"),
                 ("Aaliyah Grant", "agrant", "BIO 101", "2 late submissions", "late", "Nov 4"),
                 ("Samuel Ortiz", "sortiz", "HON 199", "Requested an extension", "request", "Nov 4")]

    # ------------------------------------------------------------------ v1
    v1_css = """
body{margin:0;font:14px/1.5 "Open Sans",Arial,sans-serif;color:#2d3b45;background:#f5f5f5}
.lh-global{display:flex;align-items:center;gap:20px;padding:0 24px;height:56px;background:#394b58;color:#fff}
.lh-brand{font-weight:700;color:#fff;text-decoration:none;font-size:18px}
.lh-global-nav a{color:#e3e8eb;text-decoration:none;padding:18px 10px}.lh-global-nav a.current{background:#2d3b45;color:#fff}
.lh-unread{background:#e66135;border-radius:8px;padding:0 6px;font-size:11px}
.lh-dashboard{max-width:1180px;margin:0 auto;padding:24px}
.lh-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}
.lh-stat{background:#fff;border:1px solid #c7cdd1;border-radius:4px;padding:12px}
.lh-course-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}
.lh-course-card{background:#fff;border:1px solid #c7cdd1;border-radius:4px;overflow:hidden}
.lh-course-banner{height:80px}.lh-course-body{padding:12px}
.lh-course-links a{margin-right:10px}
.lh-grading-table{width:100%;border-collapse:collapse;background:#fff}.lh-grading-table td,.lh-grading-table th{padding:8px;border-bottom:1px solid #e3e8eb;text-align:left}
.lh-btn{display:inline-block;padding:6px 12px;border-radius:3px;border:1px solid #c7cdd1;background:#f5f5f5;color:#2d3b45;text-decoration:none}
.lh-btn-primary{background:#0374b5;border-color:#0374b5;color:#fff}
.lh-two-col{display:grid;grid-template-columns:3fr 2fr;gap:20px;margin-top:20px}
.lh-field{display:flex;flex-direction:column;margin-bottom:10px}
"""

    def v1_course(code, slug, title, meta_, n, wait, col):
        cid = code.replace(" ", "-")
        return f'''      <div class="lh-course-card" data-course="{cid}">
        <div class="lh-course-banner" style="background:{col}"></div>
        <div class="lh-course-body">
          <h3 class="lh-course-title"><a href="/courses/{slug}">{code} · {title}</a></h3>
          <p class="lh-course-meta">{meta_}</p>
          <p class="lh-enrollment"><span class="enrollment-count"{t_if(code == "CHEM 210", "t2")}>{n} students</span> · {wait} waitlisted</p>
          <div class="lh-course-links"><a href="/courses/{slug}/gradebook">Gradebook</a><a href="/courses/{slug}/announcements">Announcements</a><a href="/courses/{slug}/discussions">Discussions</a></div>
        </div>
      </div>'''

    def v1_row(name, course, due, sub, tog, aid):
        slug = course.lower().replace(" ", "-")
        return (f'        <tr><td>{name}</td><td>{course}</td><td>{due}</td><td>{sub}</td><td class="num">{tog}</td>'
                f'<td><a class="lh-btn lh-btn-sm" href="/courses/{slug}/assignments/{aid}/grade"{t_if(aid == "4412", "t1")}>Start grading</a></td></tr>')

    gnav = [("/dashboard", "Dashboard"), ("/courses", "Courses"), ("/calendar", "Calendar"), ("/inbox", "Inbox"),
            ("/gradebook", "Gradebook"), ("/help", "Help")]
    v1_gnav = "\n".join(
        f'    <a href="{h}" class="lh-nav-item{" current" if h == "/dashboard" else ""}"{" aria-current=" + chr(34) + "page" + chr(34) if h == "/dashboard" else ""}'
        f'{t_if(h == "/gradebook", "t6")}>{lab}{" <span class=" + chr(34) + "lh-unread" + chr(34) + ">3</span>" if lab == "Inbox" else ""}</a>'
        for h, lab in gnav)
    course_opts = "".join(f'<option value="{s}">{c} · {t}</option>' for c, s, t, *_ in courses)

    v1_body = f'''
<header class="lh-global">
  <a class="lh-brand" href="/dashboard">Lanternhall</a>
  <span class="lh-inst">Westbrook Community College</span>
  <nav class="lh-global-nav" aria-label="Global">
{v1_gnav}
  </nav>
  <div class="lh-account"><span class="lh-avatar">AN</span> Dr. Amara Nwosu · <a href="/logout">Log out</a></div>
</header>
<main class="lh-dashboard">
  <div class="lh-page-head"><h1>Instructor dashboard</h1><p class="lh-term">Fall 2026 · Week 10 of 16</p></div>
  <section class="lh-stats" aria-label="Teaching summary">
    <div class="lh-stat"><span class="lh-stat-label">Total students</span><strong class="lh-stat-value">262</strong></div>
    <div class="lh-stat"><span class="lh-stat-label">New enrollments (7 days)</span><strong class="lh-stat-value">7</strong></div>
    <div class="lh-stat"><span class="lh-stat-label">Drop requests</span><strong class="lh-stat-value">2</strong></div>
    <div class="lh-stat"><span class="lh-stat-label">Submissions to grade</span><strong class="lh-stat-value">85</strong></div>
  </section>
  <section class="lh-courses">
    <h2>Your courses</h2>
    <div class="lh-course-grid">
{chr(10).join(v1_course(*c) for c in courses)}
    </div>
  </section>
  <section class="lh-grading">
    <div class="lh-section-head"><h2>Grading queue</h2><a href="/grading">View all</a></div>
    <table class="lh-grading-table">
      <thead><tr><th>Assignment</th><th>Course</th><th>Due</th><th>Submitted</th><th>To grade</th><th></th></tr></thead>
      <tbody>
{chr(10).join(v1_row(*q) for q in queue)}
      </tbody>
    </table>
  </section>
  <section class="lh-alerts">
    <div class="lh-section-head"><h2>Students to check in with</h2><a href="/insights/students">See all insights</a></div>
    <table class="lh-alerts-table">
      <thead><tr><th>Student</th><th>Course</th><th>Flag</th><th>Last active</th><th></th></tr></thead>
      <tbody>
{chr(10).join(f'        <tr><td>{s}</td><td>{c}</td><td><span class="lh-flag lh-flag-{k}">{f}</span></td><td>{d}</td><td><a href="/inbox/compose?to={u}" class="lh-btn lh-btn-sm">Message</a></td></tr>' for s, u, c, f, k, d in check_ins)}
      </tbody>
    </table>
  </section>
  <div class="lh-two-col">
    <section class="lh-announce">
      <h2>Post an announcement</h2>
      <form id="announcement-form" class="lh-form" action="/announcements" method="post">
        <div class="lh-field"><label for="announcement-course">Course</label><select id="announcement-course" name="course_id"{T("t3")}><option value="">Select a course…</option>{course_opts}</select></div>
        <div class="lh-field"><label for="announcement-title">Title</label><input id="announcement-title" name="title" type="text" maxlength="120"{T("t4")}></div>
        <div class="lh-field"><label for="announcement-body">Message</label><textarea id="announcement-body" name="body" rows="5"></textarea></div>
        <label class="lh-check"><input type="checkbox" name="notify_email" checked> Also send as email to students</label>
        <div class="lh-form-actions"><button type="button" class="lh-btn lh-btn-light">Schedule…</button><button type="submit" class="lh-btn lh-btn-primary"{T("t5")}>Post announcement</button></div>
      </form>
      <h3>Recent announcements</h3>
      <ul class="lh-announcement-list">
{chr(10).join(f'        <li><span class="lh-tag">{c}</span> <a href="#">{t}</a> <span class="lh-date">{d}</span></li>' for c, t, d in announcements)}
      </ul>
    </section>
    <section class="lh-upcoming">
      <h2>Coming up</h2>
      <ul class="lh-todo">
{chr(10).join(f'        <li><span class="lh-date">{d}</span> {t}</li>' for d, t in todo)}
      </ul>
      <a href="/calendar">Open calendar</a>
    </section>
  </div>
</main>
<footer class="lh-footer"><a href="/policies/accessibility">Accessibility</a> · <a href="/policies/privacy">Privacy policy</a> · Lanternhall LMS 2026.4 · Westbrook Community College</footer>
'''
    v1 = page("Dashboard | Lanternhall", v1_body, css=v1_css)

    # ------------------------------------------------------------------ v2 (Chakra UI + Lit web components)
    def ck(component, name=""):
        return f"chakra-{component} " + emo("chakra:" + component + ":" + name)

    card_css = (":host{display:block} .card{background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)}"
                " .banner{height:72px;padding:10px;color:#fff;font-weight:700} .body{padding:12px 14px} .title{margin:0;font-size:15px}"
                " .enrolled{display:flex;gap:10px;color:#4a5568} .links{display:flex;gap:12px;padding:10px 14px;border-top:1px solid #edf2f7}")

    def v2_course(code, slug, title, meta_, n, wait, col):
        return f'''          <lh-course-card course-id="{code.replace(" ", "-")}" accent="{col}">
            <template shadowrootmode="open">
              <style>{card_css}</style>
              <article class="card" part="card">
                <div class="banner" style="background:{col}"><span class="code">{code}</span></div>
                <div class="body">
                  <h3 class="title"><a href="/courses/{slug}">{title}</a></h3>
                  <p class="meta">{meta_.replace("MWF", "Mon/Wed/Fri").replace("TTh", "Tue/Thu").replace("MW", "Mon/Wed").replace("F 2", "Fri 2")}</p>
                  <p class="enrolled"><span class="count"{t_if(code == "CHEM 210", "t2")}>{n} enrolled</span><span class="wait">{wait} on waitlist</span></p>
                </div>
                <nav class="links" aria-label="{code} shortcuts"><a href="/courses/{slug}/gradebook">Gradebook</a><a href="/courses/{slug}/announcements">Announcements</a><a href="/courses/{slug}/modules">Modules</a></nav>
              </article>
            </template>
          </lh-course-card>'''

    queue2 = [("Discussion: CRISPR ethics", "HON 199", "Nov 4", "15 / 18", 12, "6015")] + sorted(
        queue, key=lambda q: {"Oct 30": 1030, "Oct 31": 1031, "Nov 2": 1102, "Nov 3": 1103}[q[2]], reverse=True)

    def v2_queue(name, course, due, sub, tog, aid):
        slug = course.lower().replace(" ", "-")
        return f'''            <li class="{emo("queue-item")}">
              <div class="{emo("queue-text")}"><p class="{ck("text", "queue-title")}">{name}</p><p class="{ck("text", "queue-meta")}">{course} · due {due} · {sub.replace(" / ", " of ")} submitted</p></div>
              <span class="{ck("badge", "queue")}">{tog} to grade</span>
              <a class="{ck("button", "queue")}" href="/grade/{slug}/{aid}"{t_if(aid == "4412", "t1")}>Grade</a>
            </li>'''

    composer_css = (":host{display:block} form{background:#fff;border-radius:12px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.1)}"
                    " .row{display:grid;grid-template-columns:2fr 1fr;gap:12px} .field{display:flex;flex-direction:column;gap:4px;margin-bottom:10px}"
                    " .actions{display:flex;justify-content:flex-end;gap:8px} .primary{background:#3182ce;color:#fff;border:0;border-radius:6px;padding:8px 16px}")
    snav = [("/dashboard", "Dashboard", "home"), ("/courses", "Courses", "book"), ("/gradebook", "Gradebook", "check"),
            ("/calendar", "Calendar", "calendar"), ("/inbox", "Inbox", "inbox"), ("/analytics", "Analytics", "chart"),
            ("/help", "Help", "help")]

    def sidenav(mobile):
        return "\n".join(
            f'        <a class="{ck("link", "sidenav")}" href="{h}"{" aria-current=" + chr(34) + "page" + chr(34) if h == "/dashboard" else ""}'
            f'{t_if(h == "/gradebook" and not mobile, "t6")}>{icon(ic)}<span>{lab}</span>'
            f'{"<span class=" + chr(34) + ck("badge", "inbox") + chr(34) + ">3</span>" if lab == "Inbox" else ""}</a>' for h, lab, ic in snav)

    stats2 = [("Students", "262", "across 4 courses"), ("To grade", "97", "+12 since yesterday"), ("New this week", "7", "enrollments"),
              ("Drop requests", "2", "awaiting approval")]
    discussions = [("Maya Chen", "BIO 330", "Is crossing-over frequency the same for every chromosome pair?"),
                   ("Jordan Ellis", "HON 199", "Response to the CRISPR ethics reading — consent across generations"),
                   ("Priya Natarajan", "CHEM 210", "Clarification on question 4 of Problem Set 6")]

    v2_body = f'''
<div id="__next">
<div class="{emo("layout")}">
  <div class="chakra-portal">
    <div class="{ck("modal__overlay", "drawer")}" hidden></div>
    <div class="{ck("modal__content-container", "drawer")}" hidden>
      <section role="dialog" aria-modal="true" aria-label="Navigation" class="{ck("modal__content", "drawer")}">
        <nav class="{emo("mobile-nav")}" aria-label="Global">
{sidenav(True)}
        </nav>
      </section>
    </div>
  </div>
  <aside class="{emo("sidebar")}">
    <a href="/dashboard" class="{emo("logo")}">{icon("graduation")}<span>Lanternhall</span></a>
    <p class="{ck("text", "inst")}">Westbrook Community College</p>
    <nav class="{emo("sidenav")}" aria-label="Global">
{sidenav(False)}
    </nav>
  </aside>
  <div class="{emo("content")}">
    <header class="{emo("topbar")}">
      <button type="button" class="{ck("button", "menu")}" aria-label="Open navigation">{icon("menu")}</button>
      <h1 class="{ck("heading", "page")}">Good afternoon, Dr. Nwosu</h1>
      <span class="{ck("badge", "term")}">Fall 2026 · Week 10</span>
      <div class="{emo("spacer")}"></div>
      <button type="button" class="{ck("button", "icon")}" aria-label="Notifications">{icon("bell")}</button>
      <span class="{ck("avatar", "me")}" role="img" aria-label="Amara Nwosu"><div class="{ck("avatar__initials", "me")}">AN</div></span>
    </header>
    <div class="{ck("stack", "stats")}">
{chr(10).join(f'      <div class="{ck("stat", "s")}"><dl><dt class="{ck("stat__label", "s")}">{k}</dt><dd class="{ck("stat__number", "s")}">{v}</dd><dd class="{ck("stat__help-text", "s")}">{h}</dd></dl></div>' for k, v, h in stats2)}
    </div>
    <div class="{emo("main-grid")}">
      <div class="{ck("stack", "left")}">
        <section class="{ck("card", "courses")}" aria-labelledby="courses-h">
          <div class="{ck("card__header", "courses")}"><h2 id="courses-h" class="{ck("heading", "section")}">Courses</h2><a class="{ck("link", "all")}" href="/courses">All courses</a></div>
          <div class="{emo("course-grid")}">
{chr(10).join(v2_course(*c) for c in sorted(courses, key=lambda c: c[0]))}
          </div>
        </section>
        <section class="{ck("card", "queue")}" aria-labelledby="queue-h">
          <div class="{ck("card__header", "queue")}"><h2 id="queue-h" class="{ck("heading", "section")}">Needs grading</h2><span class="{ck("badge", "count")}">97</span></div>
          <ul role="list" class="{emo("queue-list")}">
{chr(10).join(v2_queue(*q) for q in queue2)}
          </ul>
        </section>
        <section class="{ck("card", "checkins")}" aria-labelledby="checkins-h">
          <div class="{ck("card__header", "checkins")}"><h2 id="checkins-h" class="{ck("heading", "section")}">Students to check in with</h2><a class="{ck("link", "insights")}" href="/insights/students">Insights</a></div>
          <ul role="list" class="{emo("checkin-list")}">
{chr(10).join(f'            <li class="{emo("checkin-item")}"><span class="{ck("avatar", "student")}" role="img" aria-label="{s}"><div class="{ck("avatar__initials", "student")}">{"".join(p[0] for p in s.split())}</div></span><div class="{emo("checkin-text")}"><p class="{ck("text", "checkin-name")}">{s} <span class="{ck("badge", "course")}">{c}</span></p><p class="{ck("text", "checkin-flag")}">{f} · last active {d}</p></div><a class="{ck("button", "message")}" href="/inbox/compose?to={u}" aria-label="Message {s}">{icon("mail")}</a></li>' for s, u, c, f, k, d in check_ins)}
          </ul>
        </section>
      </div>
      <div class="{ck("stack", "right")}">
        <announcement-composer courses="bio-101,bio-330,chem-210,hon-199">
          <template shadowrootmode="open">
            <style>{composer_css}</style>
            <form class="composer" part="form">
              <h2>New announcement</h2>
              <div class="row">
                <div class="field"><label for="ac-subject">Subject</label><input id="ac-subject" name="subject" type="text" maxlength="120" placeholder="e.g. Lab 5 moved to Thursday"{T("t4")}></div>
                <div class="field"><label for="ac-course">Post to</label><select id="ac-course" name="courseId"{T("t3")}><option value="" selected>Choose course</option>{"".join(f'<option value="{s}">{c}</option>' for c, s, *_ in sorted(courses, key=lambda c: c[0]))}<option value="all">All my courses</option></select></div>
              </div>
              <div class="field"><label for="ac-body">Message</label><textarea id="ac-body" name="message" rows="5"></textarea></div>
              <label class="check"><input type="checkbox" name="email" checked> Email students too</label>
              <div class="actions"><button type="button" class="secondary">Schedule</button><button type="submit" class="primary"{T("t5")}>Post</button></div>
            </form>
          </template>
        </announcement-composer>
        <section class="{ck("card", "discuss")}" aria-labelledby="discuss-h">
          <div class="{ck("card__header", "discuss")}"><h2 id="discuss-h" class="{ck("heading", "section")}">Unanswered discussion posts</h2></div>
          <ul role="list" class="{emo("discuss-list")}">
{chr(10).join(f"""            <li class="{emo('discuss-item')}">
              <p class="{ck('text', 'discuss-meta')}"><b>{who}</b> · {course}</p>
              <p class="{ck('text', 'discuss-body')}">{text}</p>
              <form class="{emo('quick-reply')}" hidden><textarea aria-label="Reply to {who}" rows="2" class="{ck('textarea', 'reply')}"></textarea><button type="submit" class="{ck('button', 'reply')}">Post</button></form>
              <button type="button" class="{ck('button', 'reply-toggle')}">Reply</button>
            </li>""" for who, course, text in discussions)}
          </ul>
        </section>
        <section class="{ck("card", "todo")}" aria-labelledby="todo-h">
          <div class="{ck("card__header", "todo")}"><h2 id="todo-h" class="{ck("heading", "section")}">Coming up</h2></div>
          <ul role="list" class="{emo("todo-list")}">
{chr(10).join(f'            <li class="{emo("todo-item")}"><time class="{ck("text", "todo-date")}">{d}</time><span>{t}</span></li>' for d, t in todo)}
          </ul>
        </section>
      </div>
    </div>
    <footer class="{emo("footer")}"><a class="{ck("link", "footer")}" href="/policies/accessibility">Accessibility</a><a class="{ck("link", "footer")}" href="/policies/privacy">Privacy</a><span>Lanternhall 2026.11</span></footer>
  </div>
</div>
</div>
'''
    v2 = page("Dashboard · Lanternhall", v2_body, body_attrs=' class="chakra-ui-light"',
              css="body{margin:0;font-family:Inter,system-ui,sans-serif;background:#f7fafc;color:#1a202c}")

    targets = [
        tgt("t1", "'Start grading' action of 'Lab Report 4: Enzyme Kinetics' (BIO 101) in the grading queue",
            "table.lh-grading-table tbody tr:first-child a.lh-btn",
            "//td[text()='Lab Report 4: Enzyme Kinetics']/following-sibling::td/a[text()='Start grading']",
            ["copy-change", "structure-move", "sibling-reorder", "insertion", "class-obfuscation", "decoy"]),
        tgt("t2", "Enrollment count on the CHEM 210 course card (64 students)",
            '.lh-course-card[data-course="CHEM-210"] .enrollment-count',
            "//a[contains(text(),'CHEM 210')]/ancestor::div[@class='lh-course-card']//span[@class='enrollment-count']",
            ["shadow-dom", "copy-change", "sibling-reorder", "class-obfuscation", "attribute-churn"]),
        tgt("t3", "Course select of the 'Post an announcement' form",
            "#announcement-course",
            "//form[@id='announcement-form']//select[@name='course_id']",
            ["shadow-dom", "id-change", "attribute-churn", "copy-change", "sibling-reorder"]),
        tgt("t4", "Title input of the 'Post an announcement' form",
            "input#announcement-title",
            "//label[text()='Title']/following-sibling::input[1]",
            ["shadow-dom", "id-change", "attribute-churn", "copy-change", "sibling-reorder", "wrapper-divs"]),
        tgt("t5", "'Post announcement' submit button of the announcement form",
            '#announcement-form button[type="submit"]',
            "//button[normalize-space()='Post announcement']",
            ["shadow-dom", "copy-change", "class-obfuscation", "decoy"]),
        tgt("t6", "'Gradebook' item of the global navigation",
            'nav.lh-global-nav a[href="/gradebook"]',
            "//nav[@aria-label='Global']/a[5]",
            ["structure-move", "sibling-reorder", "insertion", "class-obfuscation", "decoy"]),
    ]
    m = meta(
        "dashboard-10", "LMS instructor dashboard — Lanternhall",
        ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change", "copy-change",
         "tag-change", "attribute-churn", "structure-move", "insertion"],
        "v2 is a Chakra UI rewrite (chakra-* plus emotion css-* classes). The horizontal global nav becomes a sidebar with "
        "icons, a new 'Analytics' item and Gradebook moved up (a hidden Chakra drawer repeats the nav; course cards also "
        "carry 'Gradebook' links). Course cards become <lh-course-card> web components (declarative shadow roots), sorted by "
        "course code, with the code moved into the banner and '64 students' -> '64 enrolled'. The grading table becomes a list "
        "sorted by newest due date with a new item on top and 'Start grading' -> 'Grade'. The announcement form becomes an "
        "<announcement-composer> shadow root: Subject (was Title) and 'Post to' (was Course) swap places, ids/names change and "
        "'Post announcement' becomes 'Post'; hidden quick-reply forms in a new discussions card each have a 'Post' button.",
        targets,
    )
    return v1, v2, m


# ======================================================================================
def main(argv: list[str]) -> int:
    wanted = {f"dashboard-{a.zfill(2)}" if a.isdigit() else a for a in argv}
    for name, fn in SUITES.items():
        if wanted and name not in wanted:
            continue
        v1, v2, m = fn()
        assert m["suite"] == name, (m["suite"], name)
        d = HERE / name
        d.mkdir(exist_ok=True)
        (d / "v1.html").write_text(v1, encoding="utf-8")
        (d / "v2.html").write_text(v2, encoding="utf-8")
        (d / "targets.json").write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {name}: v1 {len(v1.encode()):,} B, v2 {len(v2.encode()):,} B")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
