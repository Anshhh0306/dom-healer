#!/usr/bin/env python
"""Deterministic generator for the ``table`` benchmark fixtures (table-01 ... table-10).

Every suite is a realistic data-table page (``v1.html``), a heavy but plausible
redesign of the same page (``v2.html``) and ``targets.json`` holding the authored
(brittle) v1 selectors.  Ground-truth markers are only emitted through the
per-page :class:`Marks` helper, which asserts that every target is marked exactly
once per page.  Row/column positions used by positional selectors are computed
from the datasets, so editing a dataset keeps the selectors honest.

    python benchmarks/fixtures/table/_build.py                # rebuild every suite
    python benchmarks/fixtures/table/_build.py table-03 ...   # rebuild some suites

Validate afterwards with::

    .venv/bin/python benchmarks/validate_fixtures.py --category table

Only the standard library is used; output is byte-for-byte reproducible.
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from collections import Counter
from datetime import date
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
GT = "data-dh-target"  # ground-truth marker attribute (stripped by the harness)
CUR = ' aria-current="page"'
SUITES: dict = {}


# ----------------------------------------------------------------------------------------
# generic helpers
# ----------------------------------------------------------------------------------------
def suite(fn):
    SUITES[fn.__name__.replace("_", "-")] = fn
    return fn


def esc(value) -> str:
    return escape(str(value), quote=True)


class Marks:
    """Emit ``data-dh-target`` for a target key; verify each target is marked once."""

    def __init__(self, keys: dict, label: str):
        self.keys, self.label, self.used = keys, label, Counter()

    def __call__(self, key: str) -> str:
        tid = self.keys.get(key)
        if tid is None:
            return ""
        self.used[key] += 1
        return f' {GT}="{tid}"'

    def verify(self) -> None:
        for key, tid in self.keys.items():
            if self.used[key] != 1:
                raise SystemExit(f"{self.label}: target {tid} ({key!r}) marked {self.used[key]} times")


def NOMARK(_key: str) -> str:
    return ""


def page(title, body, *, css="", lang="en", html_attrs="", body_attrs="", head_extra="") -> str:
    ha = f" {html_attrs}" if html_attrs else ""
    ba = f" {body_attrs}" if body_attrs else ""
    return (
        f'<!doctype html>\n<html lang="{lang}"{ha}>\n<head>\n<meta charset="utf-8">\n'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{esc(title)}</title>\n{head_extra}<style>\n{css.strip()}\n</style>\n</head>\n"
        f"<body{ba}>\n{body.strip()}\n</body>\n</html>\n"
    )


def emit(sid, *, title, mutations, notes, targets, v1, v2) -> None:
    keys = {t["key"]: t["id"] for t in targets}
    pages = {}
    for name, render in (("v1.html", v1), ("v2.html", v2)):
        marks = Marks(keys, f"{sid}/{name}")
        pages[name] = render(marks)
        marks.verify()
    meta = {
        "suite": sid,
        "category": "table",
        "title": title,
        "mutations": mutations,
        "notes": notes,
        "targets": [{k: t[k] for k in ("id", "description", "css", "xpath", "mutations")} for t in targets],
    }
    out = HERE / sid
    out.mkdir(exist_ok=True)
    for name, markup in pages.items():
        (out / name).write_text(markup, encoding="utf-8")
    (out / "targets.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {sid}: v1 {len(pages['v1.html']) // 1024} KB, v2 {len(pages['v2.html']) // 1024} KB")


# --- deterministic "build tool" class names -----------------------------------------------
_LOWER = "abcdefghijklmnopqrstuvwxyz"
_LETTERS = _LOWER + _LOWER.upper()
_B36 = "0123456789" + _LOWER
_B62 = _LETTERS + "0123456789"


def _hash(seed: str, n: int, alphabet: str) -> str:
    num = int.from_bytes(hashlib.sha1(seed.encode()).digest(), "big")
    out = []
    for _ in range(n):
        num, r = divmod(num, len(alphabet))
        out.append(alphabet[r])
    return "".join(out)


def cm(component: str, local: str) -> str:
    """CSS Modules (Next.js): ``Component_local__a1B2c``."""
    return f"{component}_{local}__{_hash(component + '.' + local, 5, _B62)}"


def sc(name: str) -> str:
    """styled-components: static component id + generated class."""
    return f"sc-{_hash('sc:' + name, 6, _LETTERS)} {_hash('gen:' + name, 6, _LETTERS)}"


def emo(name: str, label: str = "") -> str:
    """emotion: ``css-1x9f2ab`` (optionally with a dev-mode label suffix)."""
    return f"css-{_hash('emo:' + name, 7, _B36)}" + (f"-{label}" if label else "")


def ve(name: str) -> str:
    """vanilla-extract production class: ``_1q7ce4g3``."""
    return "_" + _hash("ve:" + name, 7, _B36) + str(len(name) % 10)


def ax(*names: str) -> str:
    """Atomic CSS (StyleX-like): one ``x…`` class per declaration."""
    return " ".join("x" + _hash("ax:" + n, 7, _B36) for n in names)


# --- formatting ----------------------------------------------------------------------------
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MINUS = "−"


def d_gb(iso: str) -> str:
    y, m, d = map(int, iso.split("-"))
    return f"{d} {MON[m - 1]} {y}"


def d_us(iso: str) -> str:
    y, m, d = map(int, iso.split("-"))
    return f"{MON[m - 1]} {d}, {y}"


def money(x: float, cur: str = "$") -> str:
    return f"{cur}{x:,.2f}"


def signed(x: float, fmt: str = "{:,.2f}", suffix: str = "") -> str:
    return ("+" if x >= 0 else MINUS) + fmt.format(abs(x)) + suffix


def slug(s: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-").replace("--", "-")


# --- icons (heroicons-like 20x20 paths) ----------------------------------------------------
_ICONS = {
    "dots": "M3 10a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0Zm5.5 0a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0Zm7-1.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3Z",
    "dots-v": "M10 3a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3Zm0 5.5a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3Zm1.5 7a1.5 1.5 0 1 0-3 0 1.5 1.5 0 0 0 3 0Z",
    "bell": "M4 8a6 6 0 1 1 12 0c0 1.887.454 3.665 1.257 5.234a.75.75 0 0 1-.515 1.076 32.91 32.91 0 0 1-3.256.508 3.5 3.5 0 0 1-6.972 0 32.903 32.903 0 0 1-3.256-.508.75.75 0 0 1-.515-1.076A11.448 11.448 0 0 0 4 8Z",
    "download": "M10.75 2.75a.75.75 0 0 0-1.5 0v8.614L6.295 8.235a.75.75 0 1 0-1.09 1.03l4.25 4.5a.75.75 0 0 0 1.09 0l4.25-4.5a.75.75 0 0 0-1.09-1.03l-2.955 3.129V2.75ZM3.5 12.75a.75.75 0 0 0-1.5 0v2.5A2.75 2.75 0 0 0 4.75 18h10.5A2.75 2.75 0 0 0 18 15.25v-2.5a.75.75 0 0 0-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5Z",
    "printer": "M5 2.75C5 1.784 5.784 1 6.75 1h6.5c.966 0 1.75.784 1.75 1.75v3.552c.377.046.752.097 1.126.153A2.212 2.212 0 0 1 18 8.653v4.097A2.25 2.25 0 0 1 15.75 15h-.241l.305 1.984A1.75 1.75 0 0 1 14.084 19H5.915a1.75 1.75 0 0 1-1.73-2.016L4.492 15H4.25A2.25 2.25 0 0 1 2 12.75V8.653c0-1.082.775-2.034 1.874-2.198.374-.056.75-.107 1.127-.153L5 2.75Z",
    "chev-down": "M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z",
    "chev-right": "M8.22 5.22a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.75.75 0 0 1-1.06-1.06L11.94 10 8.22 6.28a.75.75 0 0 1 0-1.06Z",
    "chev-left": "M11.78 5.22a.75.75 0 0 1 0 1.06L8.06 10l3.72 3.72a.75.75 0 1 1-1.06 1.06l-4.25-4.25a.75.75 0 0 1 0-1.06l4.25-4.25a.75.75 0 0 1 1.06 0Z",
    "check": "M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z",
    "x": "M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z",
    "search": "M9 3.5a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11ZM2 9a7 7 0 1 1 12.452 4.391l3.328 3.329a.75.75 0 1 1-1.06 1.06l-3.329-3.328A7 7 0 0 1 2 9Z",
    "eye": "M10 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5ZM.664 10.59a1.651 1.651 0 0 1 0-1.186A10.004 10.004 0 0 1 10 3c4.257 0 7.893 2.66 9.336 6.41.147.381.146.804 0 1.186A10.004 10.004 0 0 1 10 17c-4.257 0-7.893-2.66-9.336-6.41Z",
    "trash": "M8.75 1A2.75 2.75 0 0 0 6 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 1 0 .23 1.482l.149-.022.841 10.518A2.75 2.75 0 0 0 7.596 19h4.807a2.75 2.75 0 0 0 2.742-2.53l.841-10.52.149.023a.75.75 0 0 0 .23-1.482A41.03 41.03 0 0 0 14 4.193V3.75A2.75 2.75 0 0 0 11.25 1h-2.5Z",
    "sort": "M2.24 6.8a.75.75 0 0 0 1.06-.04l1.95-2.1v8.59a.75.75 0 0 0 1.5 0V4.66l1.95 2.1a.75.75 0 1 0 1.1-1.02l-3.25-3.5a.75.75 0 0 0-1.1 0L2.2 5.74a.75.75 0 0 0 .04 1.06Zm8 6.4a.75.75 0 0 0-.04 1.06l3.25 3.5a.75.75 0 0 0 1.1 0l3.25-3.5a.75.75 0 1 0-1.1-1.02l-1.95 2.1V6.75a.75.75 0 0 0-1.5 0v8.59l-1.95-2.1a.75.75 0 0 0-1.06-.04Z",
    "restart": "M15.312 11.424a5.5 5.5 0 0 1-9.201 2.466l-.312-.311h2.433a.75.75 0 0 0 0-1.5H3.989a.75.75 0 0 0-.75.75v4.242a.75.75 0 0 0 1.5 0v-2.43l.31.31a7 7 0 0 0 11.712-3.138.75.75 0 0 0-1.449-.39Zm1.23-3.723a.75.75 0 0 0 .219-.53V2.929a.75.75 0 0 0-1.5 0V5.36l-.31-.31A7 7 0 0 0 3.239 8.188a.75.75 0 1 0 1.448.389A5.5 5.5 0 0 1 13.89 6.11l.311.31h-2.432a.75.75 0 0 0 0 1.5h4.243a.75.75 0 0 0 .53-.219Z",
    "terminal": "M3.25 3A2.25 2.25 0 0 0 1 5.25v9.5A2.25 2.25 0 0 0 3.25 17h13.5A2.25 2.25 0 0 0 19 14.75v-9.5A2.25 2.25 0 0 0 16.75 3H3.25Zm.943 8.752a.75.75 0 0 1 .055-1.06L6.128 9l-1.88-1.693a.75.75 0 1 1 1.004-1.114l2.5 2.25a.75.75 0 0 1 0 1.114l-2.5 2.25a.75.75 0 0 1-1.06-.055ZM9.75 10.25a.75.75 0 0 0 0 1.5h2.5a.75.75 0 0 0 0-1.5h-2.5Z",
    "plus": "M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z",
    "minus": "M4 10a.75.75 0 0 1 .75-.75h10.5a.75.75 0 0 1 0 1.5H4.75A.75.75 0 0 1 4 10Z",
    "funnel": "M2.628 1.601C5.028 1.206 7.49 1 10 1s4.973.206 7.372.601a.75.75 0 0 1 .628.74v2.288a2.25 2.25 0 0 1-.659 1.59l-4.682 4.683a2.25 2.25 0 0 0-.659 1.59v3.037c0 .684-.31 1.33-.844 1.757l-1.937 1.55A.75.75 0 0 1 8 18.25v-5.757a2.25 2.25 0 0 0-.659-1.591L2.659 6.22A2.25 2.25 0 0 1 2 4.629V2.34a.75.75 0 0 1 .628-.74Z",
    "star": "M10.868 2.884c-.321-.772-1.415-.772-1.736 0l-1.83 4.401-4.753.381c-.833.067-1.171 1.107-.536 1.651l3.62 3.102-1.106 4.637c-.194.813.691 1.456 1.405 1.02L10 15.591l4.069 2.485c.713.436 1.598-.207 1.404-1.02l-1.106-4.637 3.62-3.102c.635-.544.297-1.584-.536-1.65l-4.752-.382-1.831-4.401Z",
    "info": "M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-7-4a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM9 9a.75.75 0 0 0 0 1.5h.253a.25.25 0 0 1 .244.304l-.459 2.066A1.75 1.75 0 0 0 10.747 15H11a.75.75 0 0 0 0-1.5h-.253a.25.25 0 0 1-.244-.304l.459-2.066A1.75 1.75 0 0 0 9.253 9H9Z",
    "plane": "M3.105 2.288a.75.75 0 0 0-.826.95l1.414 4.926A1.5 1.5 0 0 0 5.135 9.25h6.115a.75.75 0 0 1 0 1.5H5.135a1.5 1.5 0 0 0-1.442 1.086l-1.414 4.926a.75.75 0 0 0 .826.95 28.897 28.897 0 0 0 15.293-7.155.75.75 0 0 0 0-1.114A28.897 28.897 0 0 0 3.105 2.288Z",
    "doc": "M3 3.5A1.5 1.5 0 0 1 4.5 2h6.879a1.5 1.5 0 0 1 1.06.44l4.122 4.12A1.5 1.5 0 0 1 17 7.622V16.5a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 3 16.5v-13Z",
    "save": "M10 2a.75.75 0 0 1 .75.75v5.59l1.95-2.1a.75.75 0 1 1 1.1 1.02l-3.25 3.5a.75.75 0 0 1-1.1 0L6.2 7.26a.75.75 0 1 1 1.1-1.02l1.95 2.1V2.75A.75.75 0 0 1 10 2Z M5.273 4.5a1.25 1.25 0 0 0-1.205.918l-1.523 5.52c-.006.02-.01.041-.015.062H6a1 1 0 0 1 .894.553l.448.894a1 1 0 0 0 .894.553h3.438a1 1 0 0 0 .86-.49l.606-1.02A1 1 0 0 1 14 11h3.47a1.318 1.318 0 0 0-.015-.062l-1.523-5.52a1.25 1.25 0 0 0-1.205-.918h-.977a.75.75 0 0 1 0-1.5h.977a2.75 2.75 0 0 1 2.651 2.019l1.523 5.52c.066.239.099.485.099.732V15a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2v-3.73c0-.246.033-.492.099-.73l1.523-5.521A2.75 2.75 0 0 1 5.273 3h.977a.75.75 0 0 1 0 1.5h-.977Z",
    "undo": "M7.793 2.232a.75.75 0 0 1-.025 1.06L3.622 7.25h10.003a5.375 5.375 0 0 1 0 10.75H10.75a.75.75 0 0 1 0-1.5h2.875a3.875 3.875 0 0 0 0-7.75H3.622l4.146 3.957a.75.75 0 0 1-1.036 1.085l-5.5-5.25a.75.75 0 0 1 0-1.085l5.5-5.25a.75.75 0 0 1 1.06.025Z",
}


def icon(name: str, cls: str = "", size: int = 16, extra: str = "") -> str:
    c = f' class="{cls}"' if cls else ""
    return (
        f'<svg{c} width="{size}" height="{size}" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"{extra}>'
        f'<path fill-rule="evenodd" d="{_ICONS[name]}" clip-rule="evenodd"/></svg>'
    )


# ========================================================================================
# table-01 — Employee directory (Kestrel HR)  ·  v2: Tailwind UI rewrite
# ========================================================================================
EMP01 = [
    # id, first, last, job title, department, location, start date, status, manager
    ("E1204", "Amara", "Castellanos", "Product Designer", "Design", "Lisbon", "2021-09-06", "Active", "Mateo Alvarez"),
    ("E1077", "Jonah", "Chen", "Staff Software Engineer", "Engineering", "Oslo", "2018-02-19", "Active", "Rafael Duarte"),
    ("E1311", "Fatima", "Chowdhury", "Payroll Specialist", "Finance", "London", "2022-04-25", "Active", "Clara Nyström"),
    ("E1129", "Marcus", "Coleman", "Site Reliability Engineer", "Engineering", "Remote (US)", "2019-11-04", "Active", "Henrik Dahl"),
    ("E1342", "Beatriz", "Costa", "Talent Acquisition Partner", "People", "Lisbon", "2023-01-16", "On leave", "Ana Lindqvist"),
    ("E1018", "Henrik", "Dahl", "Head of Infrastructure", "Engineering", "Oslo", "2016-08-29", "Active", "Sofie Brandt"),
    ("E1256", "Camille", "Delacroix", "Marketing Manager", "Marketing", "Paris", "2021-03-01", "Active", "Lena Fischer"),
    ("E1388", "Ousmane", "Diallo", "Financial Analyst", "Finance", "Paris", "2023-06-12", "Active", "Clara Nyström"),
    ("E1193", "Nikolai", "Dimitrov", "Backend Engineer", "Engineering", "Berlin", "2020-10-05", "Active", "Rafael Duarte"),
    ("E1301", "Siobhan", "Doherty", "Customer Success Lead", "Customer Success", "Dublin", "2022-02-07", "Active", "Megan Doyle"),
    ("E1099", "Rafael", "Duarte", "Engineering Manager", "Engineering", "Lisbon", "2018-07-23", "Active", "Sofie Brandt"),
    ("E1415", "Ingrid", "Eklund", "QA Engineer", "Engineering", "Oslo", "2024-01-08", "Onboarding", "Rafael Duarte"),
    ("E1236", "Giulia", "Esposito", "UX Researcher", "Design", "Remote (EU)", "2020-12-14", "Active", "Mateo Alvarez"),
    ("E1163", "Owen", "Evans", "Sales Director", "Sales", "London", "2019-05-20", "Active", "Thomas Halvorsen"),
    ("E1402", "Yasmin", "Farouk", "Account Executive", "Sales", "Dubai", "2023-10-02", "Active", "Owen Evans"),
    ("E1287", "Tiago", "Ferreira", "Frontend Engineer", "Engineering", "Lisbon", "2021-07-19", "Active", "Rafael Duarte"),
    ("E1058", "Lena", "Fischer", "Head of Marketing", "Marketing", "Berlin", "2017-04-03", "Active", "Thomas Halvorsen"),
    ("E1349", "Declan", "Fitzgerald", "IT Support Specialist", "IT", "Dublin", "2022-09-26", "On leave", "Patrick Moran"),
    ("E1221", "Élodie", "Fontaine", "Legal Counsel", "Legal", "Paris", "2020-06-08", "Active", "Isabel Moreau"),
    ("E1176", "Hiroshi", "Fujimoto", "Mobile Engineer", "Engineering", "Remote (APAC)", "2019-09-16", "Active", "Rafael Duarte"),
]
DEPTS01 = [("Engineering", 68), ("Sales", 29), ("Customer Success", 25), ("Marketing", 15), ("Finance", 14),
           ("Design", 12), ("People", 10), ("IT", 9), ("Legal", 5)]
LOCS01 = ["Berlin", "Dubai", "Dublin", "Lisbon", "London", "Oslo", "Paris", "Remote (APAC)", "Remote (EU)", "Remote (US)"]


def _email01(first, last):
    tr = str.maketrans("éÉèçöüøå", "eeecouoa")
    return f"{first.lower().translate(tr)}.{last.lower().translate(tr)}@halvorsenpike.com"


CSS01_V1 = """
:root{--brand:#0b6e4f;--ink:#1d2433;--muted:#667085;--line:#e4e7ec;--bg:#f7f8fa}
*{box-sizing:border-box}
body{margin:0;font:14px/1.45 "Inter",system-ui,sans-serif;color:var(--ink);background:var(--bg)}
.app-header{display:flex;align-items:center;gap:32px;height:60px;padding:0 24px;background:#fff;border-bottom:1px solid var(--line)}
.app-nav{display:flex;gap:4px}
.app-nav__link{padding:8px 12px;border-radius:6px;color:var(--muted);text-decoration:none}
.app-nav__link--active{color:var(--brand);background:#e7f4ef;font-weight:600}
.app-header__user{margin-left:auto;display:flex;align-items:center;gap:12px}
.layout{display:grid;grid-template-columns:240px 1fr;gap:24px;max-width:1360px;margin:24px auto;padding:0 24px}
.filters{background:#fff;border:1px solid var(--line);border-radius:8px;padding:16px;align-self:start}
.filters__group{border:0;padding:0;margin:0 0 16px}
.check,.radio{display:flex;align-items:center;gap:8px;padding:3px 0}
.count{margin-left:auto;color:var(--muted);font-size:12px}
.page-title{font-size:22px;margin:4px 0}
.toolbar{display:flex;justify-content:space-between;align-items:center;margin:16px 0}
.search-field__input{width:340px;padding:8px 12px;border:1px solid var(--line);border-radius:6px}
.btn{display:inline-flex;align-items:center;gap:6px;padding:8px 14px;border-radius:6px;border:1px solid transparent;font-weight:500;cursor:pointer;text-decoration:none}
.btn--primary{background:var(--brand);color:#fff}
.btn--secondary{background:#fff;border-color:var(--line);color:var(--ink)}
.btn--small{padding:4px 10px;font-size:13px}
.btn--link{background:none;color:var(--brand);padding:0}
.data-table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line)}
.data-table__th{text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);padding:10px 12px;border-bottom:1px solid var(--line)}
.data-table__td{padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:middle}
.sort-btn{all:unset;cursor:pointer}
.cell-name{display:flex;align-items:center;gap:10px}
.avatar{border-radius:50%}
.employee-email{display:block;color:var(--muted);font-size:12px}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px}
.badge--active{background:#e7f4ef;color:#0b6e4f}.badge--on-leave{background:#fff4e5;color:#b54708}.badge--onboarding{background:#eef4ff;color:#3538cd}
.icon-btn{background:none;border:0;padding:4px;color:var(--muted);cursor:pointer}
.table-footer{display:flex;justify-content:space-between;align-items:center;margin-top:12px}
.pagination{display:flex;gap:4px}
.pagination__link{padding:6px 10px;border:1px solid var(--line);border-radius:6px;color:var(--ink);text-decoration:none}
.pagination__link--current{background:var(--brand);color:#fff;border-color:var(--brand)}
.visually-hidden{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.app-footer{display:flex;justify-content:space-between;padding:24px;color:var(--muted);font-size:12px}
"""

CSS_TAILWIND = """
/*! tailwindcss v4.1.11 | MIT License | https://tailwindcss.com */
@layer theme{:root,:host{--font-sans:"Inter var",ui-sans-serif,system-ui,sans-serif;--color-indigo-600:oklch(51.1% .262 276.966);--color-gray-50:oklch(98.5% .002 247.839);--color-gray-200:oklch(92.8% .006 264.531);--color-gray-500:oklch(55.1% .027 264.364);--color-gray-900:oklch(21% .034 264.665);--radius-md:.375rem}}
@layer base{*,:after,:before{box-sizing:border-box;border:0 solid}html{font-family:var(--font-sans)}}
@layer utilities{.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border-width:0}.hidden{display:none}.flex{display:flex}.inline-flex{display:inline-flex}.grid{display:grid}.min-w-full{min-width:100%}.whitespace-nowrap{white-space:nowrap}.text-sm{font-size:.875rem;line-height:1.25rem}.text-xs{font-size:.75rem}.font-medium{font-weight:500}.font-semibold{font-weight:600}.text-gray-500{color:var(--color-gray-500)}.text-gray-900{color:var(--color-gray-900)}.text-indigo-600{color:var(--color-indigo-600)}.bg-white{background-color:#fff}.bg-gray-50{background-color:var(--color-gray-50)}.rounded-md{border-radius:var(--radius-md)}.px-3{padding-inline:.75rem}.py-4{padding-block:1rem}@media (width>=40rem){.sm\\:flex{display:flex}.sm\\:hidden{display:none}}@media (width>=64rem){.lg\\:block{display:block}}}
"""


@suite
def table_01():
    pos = {e[0]: i for i, e in enumerate(EMP01, 1)}
    targets = [
        dict(id="t1", key="sort:start",
             description="Sort toggle in the 'Start date' column header of the people table (the redesign labels the column 'Started')",
             css="#employee-table th[data-sort-key='startDate'] > button.sort-btn",
             xpath="//table[@id='employee-table']/thead/tr/th[5]/button",
             mutations=["class-obfuscation", "copy-change", "attribute-churn", "sibling-reorder", "insertion", "decoy"]),
        dict(id="t2", key="search",
             description="Search box above the people table that filters it by name, email or job title",
             css="#employee-search",
             xpath="//input[@placeholder='Search by name, email or title']",
             mutations=["id-change", "copy-change", "class-obfuscation", "wrapper-divs", "structure-move", "decoy"]),
        dict(id="t3", key="edit:E1129",
             description="'Edit' row action of employee Marcus Coleman",
             css=f"#employee-table tbody tr:nth-child({pos['E1129']}) button[data-testid='edit-employee']",
             xpath="//tr[.//a[normalize-space()='Marcus Coleman']]//button[normalize-space()='Edit']",
             mutations=["tag-change", "testid-change", "sibling-reorder", "class-obfuscation"]),
        dict(id="t4", key="dept:E1256",
             description="Department cell of Camille Delacroix's row (value 'Marketing')",
             css=f"#employee-table > tbody > tr:nth-child({pos['E1256']}) > td:nth-child(3)",
             xpath=f"//table[@id='employee-table']/tbody/tr[{pos['E1256']}]/td[3]",
             mutations=["sibling-reorder", "insertion", "id-change", "class-obfuscation", "decoy"]),
        dict(id="t5", key="page:3",
             description="Pagination link to page 3 below the people table",
             css="nav.pagination > a:nth-of-type(4)",
             xpath="//nav[@aria-label='Pagination']/a[normalize-space()='3']",
             mutations=["class-obfuscation", "attribute-churn", "wrapper-divs"]),
        dict(id="t6", key="menu:E1176",
             description="Icon-only overflow ('More actions' / options) menu button in Hiroshi Fujimoto's row",
             css="tr[data-employee-id='E1176'] .row-menu-trigger",
             xpath=f"(//button[@aria-label='More actions'])[{pos['E1176']}]",
             mutations=["attribute-churn", "copy-change", "id-change", "sibling-reorder", "class-obfuscation", "decoy"]),
    ]

    def v1(M):
        rows = []
        for eid, first, last, title, dept, loc, start, status, _mgr in EMP01:
            name = f"{first} {last}"
            rows.append(f"""
          <tr class="data-table__row" data-employee-id="{eid}">
            <td class="data-table__td cell-name"><img class="avatar" src="/media/avatars/{eid}.jpg" alt="" width="32" height="32"><div class="cell-name__text"><a class="employee-link" href="/people/{eid}">{esc(name)}</a><span class="employee-email">{_email01(first, last)}</span></div></td>
            <td class="data-table__td">{esc(title)}</td>
            <td class="data-table__td"{M('dept:' + eid)}>{esc(dept)}</td>
            <td class="data-table__td">{esc(loc)}</td>
            <td class="data-table__td"><time datetime="{start}">{d_gb(start)}</time></td>
            <td class="data-table__td"><span class="badge badge--{slug(status)}">{status}</span></td>
            <td class="data-table__td data-table__td--actions"><button type="button" class="btn btn--small btn--secondary" data-testid="edit-employee"{M('edit:' + eid)}>Edit</button> <button type="button" class="icon-btn row-menu-trigger" aria-label="More actions" aria-haspopup="menu" data-testid="row-menu"{M('menu:' + eid)}>{icon('dots')}</button></td>
          </tr>""")
        depts = "\n".join(
            f'          <label class="check"><input type="checkbox" name="department" value="{slug(d)}"> {esc(d)} <span class="count">{n}</span></label>'
            for d, n in DEPTS01)
        locs = "".join(f"<option>{esc(loc)}</option>" for loc in LOCS01)
        body = f"""
<header class="app-header">
  <a class="logo" href="/"><img src="/static/kestrel-logo.svg" alt="Kestrel HR" width="112" height="28"></a>
  <nav class="app-nav" aria-label="Main">
    <a class="app-nav__link" href="/dashboard">Dashboard</a>
    <a class="app-nav__link app-nav__link--active" href="/people" aria-current="page">People</a>
    <a class="app-nav__link" href="/time-off">Time off</a>
    <a class="app-nav__link" href="/payroll">Payroll</a>
    <a class="app-nav__link" href="/reports">Reports</a>
    <a class="app-nav__link" href="/settings">Settings</a>
  </nav>
  <div class="app-header__user">
    <button type="button" class="icon-btn" aria-label="Notifications">{icon('bell', size=18)}</button>
    <span class="user-chip"><img class="avatar" src="/media/avatars/E1003.jpg" alt="" width="28" height="28"> Ana Lindqvist</span>
  </div>
</header>
<div class="layout">
  <aside class="filters" aria-label="Filters">
    <h2 class="filters__title">Filters</h2>
    <fieldset class="filters__group">
      <legend>Department</legend>
{depts}
    </fieldset>
    <fieldset class="filters__group">
      <legend>Location</legend>
      <select name="location" class="select"><option selected>All locations</option>{locs}</select>
    </fieldset>
    <fieldset class="filters__group">
      <legend>Status</legend>
      <label class="radio"><input type="radio" name="status" value="any" checked> Any</label>
      <label class="radio"><input type="radio" name="status" value="active"> Active</label>
      <label class="radio"><input type="radio" name="status" value="on-leave"> On leave</label>
      <label class="radio"><input type="radio" name="status" value="onboarding"> Onboarding</label>
    </fieldset>
    <button type="button" class="btn btn--link">Clear all filters</button>
  </aside>
  <main class="content" id="main">
    <div class="page-head">
      <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a> / <span>People</span></nav>
      <h1 class="page-title">People directory</h1>
      <p class="page-subtitle">187 people across 9 departments and 10 locations</p>
    </div>
    <div class="toolbar">
      <div class="search-field">
        <label for="employee-search" class="visually-hidden">Search employees</label>
        <input type="search" id="employee-search" name="q" class="search-field__input" placeholder="Search by name, email or title" autocomplete="off"{M('search')}>
      </div>
      <div class="toolbar__actions">
        <button type="button" class="btn btn--secondary" data-testid="export-csv">Export CSV</button>
        <a href="/people/new" class="btn btn--primary" data-testid="add-employee">Add employee</a>
      </div>
    </div>
    <table class="data-table" id="employee-table">
      <thead>
        <tr>
          <th scope="col" class="data-table__th is-sortable is-sorted" data-sort-key="lastName" aria-sort="ascending"><button type="button" class="sort-btn">Name <span class="sort-icon" aria-hidden="true">&#9650;</span></button></th>
          <th scope="col" class="data-table__th">Job title</th>
          <th scope="col" class="data-table__th is-sortable" data-sort-key="department"><button type="button" class="sort-btn">Department <span class="sort-icon" aria-hidden="true">&#8597;</span></button></th>
          <th scope="col" class="data-table__th">Location</th>
          <th scope="col" class="data-table__th is-sortable" data-sort-key="startDate"><button type="button" class="sort-btn"{M('sort:start')}>Start date <span class="sort-icon" aria-hidden="true">&#8597;</span></button></th>
          <th scope="col" class="data-table__th">Status</th>
          <th scope="col" class="data-table__th data-table__th--actions"><span class="visually-hidden">Actions</span></th>
        </tr>
      </thead>
      <tbody>{''.join(rows)}
      </tbody>
    </table>
    <div class="table-footer">
      <p class="table-footer__summary">Showing <strong>21</strong>&ndash;<strong>40</strong> of <strong>187</strong> people</p>
      <nav class="pagination" aria-label="Pagination">
        <a class="pagination__link pagination__link--prev" href="?page=1" rel="prev">&lsaquo; Previous</a>
        <a class="pagination__link" href="?page=1">1</a>
        <a class="pagination__link pagination__link--current" href="?page=2" aria-current="page">2</a>
        <a class="pagination__link" href="?page=3"{M('page:3')}>3</a>
        <a class="pagination__link" href="?page=4">4</a>
        <span class="pagination__gap">&hellip;</span>
        <a class="pagination__link" href="?page=10">10</a>
        <a class="pagination__link pagination__link--next" href="?page=3" rel="next">Next &rsaquo;</a>
      </nav>
    </div>
  </main>
</div>
<footer class="app-footer">
  <p>&copy; 2025 Halvorsen &amp; Pike Engineering AS &middot; Kestrel HR 4.12.3</p>
  <nav class="app-footer__links" aria-label="Footer"><a href="/help">Help centre</a> &middot; <a href="/privacy">Privacy</a> &middot; <a href="/status">System status</a></nav>
</footer>
"""
        return page("People directory · Kestrel HR", body, css=CSS01_V1)

    def v2(M):
        order = sorted(EMP01, key=lambda e: e[6], reverse=True)  # redesign defaults to "recently joined"
        th = 'class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900"'

        def sortbtn(label, key, mark, clone, active=False):
            ti = ' tabindex="-1"' if clone else ""
            span = ("ml-2 flex-none rounded-sm bg-gray-100 text-gray-900 group-hover:bg-gray-200" if active
                    else "invisible ml-2 flex-none rounded-sm text-gray-400 group-hover:visible group-focus:visible")
            return f'<button type="button" class="group inline-flex items-center"{ti}{mark(key)}>{label}<span class="{span}">{icon("chev-down", cls="size-5")}</span></button>'

        def thead(mark, clone=False):
            return f"""<thead class="bg-gray-50">
                <tr>
                  <th scope="col" class="py-3.5 pr-3 pl-4 text-left text-sm font-semibold text-gray-900 sm:pl-6">{sortbtn('Name', 'sort:name', mark, clone)}</th>
                  <th scope="col" {th}>{sortbtn('Department', 'sort:dept', mark, clone)}</th>
                  <th scope="col" {th}>Job title</th>
                  <th scope="col" {th}>Location</th>
                  <th scope="col" {th}>Manager</th>
                  <th scope="col" {th}>Status</th>
                  <th scope="col" {th} aria-sort="descending">{sortbtn('Started', 'sort:start', mark, clone, active=True)}</th>
                  <th scope="col" class="relative py-3.5 pr-4 pl-3 sm:pr-6"><span class="sr-only">Edit</span></th>
                </tr>
              </thead>"""

        badge = {"Active": "bg-green-50 text-green-700 ring-green-600/20",
                 "On leave": "bg-yellow-50 text-yellow-800 ring-yellow-600/20",
                 "Onboarding": "bg-blue-50 text-blue-700 ring-blue-700/10"}
        td = 'class="px-3 py-4 text-sm whitespace-nowrap text-gray-500"'
        rows = []
        for n, (eid, first, last, title, dept, loc, start, status, mgr) in enumerate(order):
            name = f"{first} {last}"
            rows.append(f"""
                <tr class="even:bg-gray-50">
                  <td class="py-4 pr-3 pl-4 text-sm whitespace-nowrap sm:pl-6"><div class="flex items-center"><div class="size-10 shrink-0"><img class="size-10 rounded-full" src="https://cdn.kestrel-hr.com/avatars/{eid.lower()}.webp" alt=""></div><div class="ml-4"><div class="font-medium text-gray-900"><a href="/people/{eid}" class="hover:underline">{esc(name)}</a></div><div class="mt-1 text-gray-500">{_email01(first, last)}</div></div></div></td>
                  <td {td}{M('dept:' + eid)}>{esc(dept)}</td>
                  <td class="px-3 py-4 text-sm whitespace-nowrap"><div class="text-gray-900">{esc(title)}</div><div class="mt-1 text-xs text-gray-400">{eid}</div></td>
                  <td {td}>{esc(loc)}</td>
                  <td {td}>{esc(mgr)}</td>
                  <td {td}><span class="inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset {badge[status]}">{status}</span></td>
                  <td {td}><time datetime="{start}">{d_us(start)}</time></td>
                  <td class="relative py-4 pr-4 pl-3 text-right text-sm font-medium whitespace-nowrap sm:pr-6"><div class="flex items-center justify-end gap-x-4"><a href="/people/{eid}/edit" class="text-indigo-600 hover:text-indigo-900"{M('edit:' + eid)}>Edit<span class="sr-only">, {esc(name)}</span></a><div class="relative flex-none"><button type="button" class="-m-2.5 block p-2.5 text-gray-500 hover:text-gray-900" id="options-menu-{n}-button" aria-expanded="false" aria-haspopup="true"{M('menu:' + eid)}><span class="sr-only">Open options</span>{icon('dots-v', cls='size-5')}</button></div></div></td>
                </tr>""")
        pg = "relative inline-flex items-center px-4 py-2 text-sm font-semibold text-gray-900 ring-1 ring-gray-300 ring-inset hover:bg-gray-50 focus:z-20 focus:outline-offset-0"
        href = "/people?page={}&amp;sort=-startDate"
        dept_checks = "".join(
            f'<div class="flex items-center gap-3"><input id=":r{20 + i}:" type="checkbox" class="size-4 rounded-sm border-gray-300"><label for=":r{20 + i}:" class="text-sm text-gray-600">{esc(d)}</label></div>'
            for i, (d, _n) in enumerate(DEPTS01))
        search_cls = "col-start-1 row-start-1 block w-full rounded-md bg-white py-1.5 pr-3 pl-10 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-600 sm:pl-9 sm:text-sm/6"
        filter_btn = "inline-flex items-center gap-x-1.5 rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-xs ring-1 ring-gray-300 ring-inset hover:bg-gray-50"
        appbar_css = (":host{display:block;position:sticky;top:0;z-index:40}.bar{display:flex;align-items:center;gap:24px;height:64px;"
                      "padding:0 24px;background:#111827;color:#fff}.links{display:flex;gap:4px}.links a{color:#d1d5db;text-decoration:none;"
                      "font-size:14px;padding:8px 12px;border-radius:6px}.links a[aria-current=page]{background:#1f2937;color:#fff}"
                      ".search{margin-left:auto}.search input{width:280px;border-radius:6px;border:0;padding:6px 10px;background:#374151;color:#fff}"
                      ".icon{background:none;border:0;color:#9ca3af}.me{display:flex;align-items:center;gap:8px;background:none;border:0;color:#fff}")
        body = f"""
<kestrel-app-bar>
  <template shadowrootmode="open">
    <style>{appbar_css}</style>
    <header class="bar" part="bar">
      <a class="brand" href="/home"><img src="https://cdn.kestrel-hr.com/brand/kestrel-mark-white.svg" alt="Kestrel" width="32" height="32"></a>
      <nav class="links" aria-label="Main">
        <a href="/people" aria-current="page">People</a>
        <a href="/time-off">Time off</a>
        <a href="/payroll">Payroll</a>
        <a href="/reports">Reports</a>
        <a href="/home">Home</a>
      </nav>
      <div class="search" role="search"><input type="search" placeholder="Search Kestrel" aria-label="Search everything"></div>
      <button class="icon" type="button"><span hidden>View notifications</span>{icon('bell', size=20)}</button>
      <button class="me" type="button" aria-haspopup="menu"><img src="https://cdn.kestrel-hr.com/avatars/e1003.webp" alt="" width="32" height="32"><span>Ana Lindqvist</span></button>
    </header>
  </template>
</kestrel-app-bar>
<div class="flex items-center gap-x-6 bg-indigo-600 px-6 py-2.5 sm:px-3.5 sm:before:flex-1">
  <p class="text-sm/6 text-white"><strong class="font-semibold">New in Kestrel</strong><svg viewBox="0 0 2 2" class="mx-2 inline size-0.5 fill-current" aria-hidden="true"><circle cx="1" cy="1" r="1"/></svg>Reporting lines are now shown in the people directory.&nbsp;<a href="/changelog/reporting-lines" class="font-semibold whitespace-nowrap">Read the changelog <span aria-hidden="true">&rarr;</span></a></p>
  <div class="flex flex-1 justify-end"><button type="button" class="-m-3 p-3 focus-visible:-outline-offset-4"><span class="sr-only">Dismiss</span>{icon('x', cls='size-5 text-white')}</button></div>
</div>
<div class="fixed inset-0 z-40 hidden" role="dialog" aria-modal="true" aria-label="Filters">
  <div class="fixed inset-0 bg-black/25" aria-hidden="true"></div>
  <div class="relative ml-auto flex size-full max-w-xs flex-col overflow-y-auto bg-white py-4 pb-12 shadow-xl">
    <div class="flex items-center justify-between px-4"><h2 class="text-lg font-medium text-gray-900">Filters</h2><button type="button" class="-mr-2 flex size-10 items-center justify-center rounded-md bg-white p-2 text-gray-400"><span class="sr-only">Close menu</span>{icon('x', cls='size-6')}</button></div>
    <div class="mt-4 grid grid-cols-1 px-4"><input type="search" name="query" aria-label="Search people" placeholder="Search name, email, job title&hellip;" class="{search_cls}"></div>
    <div class="mt-6 space-y-3 px-4">{dept_checks}</div>
  </div>
</div>
<main class="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
  <div class="sm:flex sm:items-center">
    <div class="sm:flex-auto">
      <h1 class="text-base font-semibold text-gray-900">People</h1>
      <p class="mt-2 text-sm text-gray-700">Everyone at Halvorsen &amp; Pike &mdash; 187 people, 9 departments, 10 locations.</p>
    </div>
    <div class="mt-4 flex gap-x-3 sm:mt-0 sm:ml-16 sm:flex-none">
      <button type="button" class="{filter_btn}">{icon('download', cls='-ml-0.5 size-5 text-gray-400')}Export</button>
      <button type="button" class="block rounded-md bg-indigo-600 px-3 py-2 text-center text-sm font-semibold text-white shadow-xs hover:bg-indigo-500">Add person</button>
    </div>
  </div>
  <div class="mt-6 flex flex-wrap items-center gap-3 border-b border-gray-200 pb-4">
    <div class="grid w-full max-w-md grid-cols-1">
      <input type="search" name="query" id=":r5:" aria-label="Search people" placeholder="Search name, email, job title&hellip;" class="{search_cls}"{M('search')}>
      {icon('search', cls='pointer-events-none col-start-1 row-start-1 ml-3 size-5 self-center text-gray-400 sm:size-4')}
    </div>
    <div class="flex items-center gap-2">
      <button type="button" class="{filter_btn}">Department{icon('chev-down', cls='-mr-1 size-5 text-gray-400')}</button>
      <button type="button" class="{filter_btn}">Location{icon('chev-down', cls='-mr-1 size-5 text-gray-400')}</button>
      <button type="button" class="{filter_btn}">Status{icon('chev-down', cls='-mr-1 size-5 text-gray-400')}</button>
    </div>
    <button type="button" class="ml-auto text-sm font-medium text-gray-500 hover:text-gray-700 lg:hidden">{icon('funnel', cls='size-5')}<span class="sr-only">Filters</span></button>
  </div>
  <div class="mt-8 flow-root">
    <div class="sticky top-16 z-10 hidden border-b border-gray-300 bg-gray-50/95 backdrop-blur-sm lg:block" aria-hidden="true">
      <table class="min-w-full table-fixed">
              {thead(NOMARK, clone=True)}
      </table>
    </div>
    <div class="-mx-4 -my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
      <div class="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
        <div class="overflow-hidden shadow-sm ring-1 ring-black/5 sm:rounded-lg">
          <table class="min-w-full divide-y divide-gray-300">
              {thead(M)}
              <tbody class="divide-y divide-gray-200 bg-white">{''.join(rows)}
              </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
  <div class="flex items-center justify-between border-t border-gray-200 bg-white px-4 py-3 sm:px-6">
    <div class="flex flex-1 justify-between sm:hidden">
      <a href="{href.format(1)}" class="relative inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">Previous</a>
      <a href="{href.format(3)}" class="relative ml-3 inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">Next</a>
    </div>
    <div class="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
      <div><p class="text-sm text-gray-700">Showing <span class="font-medium">21</span> to <span class="font-medium">40</span> of <span class="font-medium">187</span> results</p></div>
      <div>
        <nav class="isolate inline-flex -space-x-px rounded-md shadow-xs" aria-label="Pagination">
          <a href="{href.format(1)}" class="relative inline-flex items-center rounded-l-md px-2 py-2 text-gray-400 ring-1 ring-gray-300 ring-inset hover:bg-gray-50 focus:z-20 focus:outline-offset-0"><span class="sr-only">Previous</span>{icon('chev-left', cls='size-5')}</a>
          <a href="{href.format(1)}" class="{pg}">1</a>
          <a href="{href.format(2)}" aria-current="page" class="relative z-10 inline-flex items-center bg-indigo-600 px-4 py-2 text-sm font-semibold text-white focus:z-20 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600">2</a>
          <a href="{href.format(3)}" class="{pg}"{M('page:3')}>3</a>
          <a href="{href.format(4)}" class="{pg} hidden md:inline-flex">4</a>
          <span class="relative inline-flex items-center px-4 py-2 text-sm font-semibold text-gray-700 ring-1 ring-gray-300 ring-inset focus:outline-offset-0">...</span>
          <a href="{href.format(8)}" class="{pg} hidden md:inline-flex">8</a>
          <a href="{href.format(9)}" class="{pg}">9</a>
          <a href="{href.format(10)}" class="{pg}">10</a>
          <a href="{href.format(3)}" class="relative inline-flex items-center rounded-r-md px-2 py-2 text-gray-400 ring-1 ring-gray-300 ring-inset hover:bg-gray-50 focus:z-20 focus:outline-offset-0"><span class="sr-only">Next</span>{icon('chev-right', cls='size-5')}</a>
        </nav>
      </div>
    </div>
  </div>
</main>
<footer class="mx-auto max-w-7xl border-t border-gray-200 px-6 py-8 text-xs text-gray-500 lg:px-8">
  <p>&copy; 2025 Halvorsen &amp; Pike Engineering AS. Kestrel HR 5.0.0-beta.3</p>
</footer>
"""
        return page("People · Kestrel", body, css=CSS_TAILWIND, html_attrs='class="h-full bg-gray-100"', body_attrs='class="h-full"')

    emit("table-01",
         title="People directory — HR employee table",
         mutations=["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change",
                    "testid-change", "copy-change", "tag-change", "attribute-churn", "structure-move", "insertion"],
         notes=("v2 is a Tailwind UI rewrite: BEM classes replaced by utilities, the left filter sidebar becomes a filter bar, "
                "the app header moves into a <kestrel-app-bar> declarative shadow root (with a global search decoy), rows are "
                "re-sorted by start date (newest first), columns are reordered and a Manager column is inserted, an aria-hidden "
                "sticky clone of the header row precedes the real table, a hidden mobile filter drawer duplicates the search box, "
                "the Edit button becomes a link with sr-only row name, row menus lose aria-label/testids, ids regenerate."),
         targets=targets, v1=v1, v2=v2)


# ========================================================================================
# table-02 — Invoices (Ledgerly billing)  ·  v2: CSS Modules + per-row <invoice-actions> shadow roots
# ========================================================================================
INV02 = [
    # number, customer, issued, due, amount, status, amount paid
    ("INV-1048", "Juniper Hill Winery", "2025-10-30", "2025-11-29", 3180.00, "Draft", 0),
    ("INV-1047", "Vantage Point Media", "2025-10-28", "2025-11-27", 7920.00, "Sent", 0),
    ("INV-1046", "Riverstone Credit Union", "2025-10-24", "2025-11-23", 12600.00, "Sent", 0),
    ("INV-1045", "Summit Peak Outfitters", "2025-10-20", "2025-10-27", 2340.75, "Overdue", 0),
    ("INV-1044", "Orchard Lane Florists", "2025-10-17", "2025-11-16", 865.40, "Paid", 865.40),
    ("INV-1043", "Kettle & Crumb Bakery", "2025-10-15", "2025-11-14", 1495.00, "Partially paid", 750.00),
    ("INV-1042", "Bluebird Preschool", "2025-10-13", "2025-11-12", 2100.00, "Paid", 2100.00),
    ("INV-1041", "Atlas Physiotherapy", "2025-10-09", "2025-11-08", 3760.00, "Sent", 0),
    ("INV-1040", "Greenway Landscaping", "2025-10-06", "2025-11-05", 5430.00, "Draft", 0),
    ("INV-1039", "Copperleaf Realty", "2025-10-01", "2025-10-31", 9870.00, "Overdue", 0),
    ("INV-1038", "Saffron Table Restaurants", "2025-09-29", "2025-10-29", 6215.00, "Paid", 6215.00),
    ("INV-1037", "Lumen Analytics", "2025-09-25", "2025-10-25", 18900.00, "Paid", 18900.00),
    ("INV-1036", "Tidewater Kayak Co.", "2025-09-22", "2025-10-07", 1120.00, "Overdue", 0),
    ("INV-1035", "Morrow & Blake LLP", "2025-09-18", "2025-10-18", 4800.00, "Void", 0),
    ("INV-1034", "Pinecrest Veterinary", "2025-09-12", "2025-10-12", 2975.50, "Paid", 2975.50),
    ("INV-1033", "Halcyon Architecture", "2025-09-08", "2025-10-08", 12480.00, "Paid", 12480.00),
    ("INV-1032", "Northwind Coffee Roasters", "2025-09-04", "2025-10-04", 1360.00, "Paid", 1360.00),
    ("INV-1031", "Brightline Dental Group", "2025-09-02", "2025-10-02", 4250.00, "Paid", 4250.00),
]
TODAY02 = "2025-11-03"


def _balance02(inv):
    _n, _c, _i, _d, amount, status, paid = inv
    return 0.0 if status in ("Paid", "Void") else amount - paid


CSS02_V1 = """
body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;font-size:.95rem;background:#f5f6f8;color:#212529}
.app-wrapper{min-height:100vh}
.sidebar{width:232px;flex:0 0 232px;padding:20px 12px;color:#adb5bd}
.sidebar-brand{display:block;font-size:1.3rem;font-weight:700;color:#fff;text-decoration:none;padding:0 12px 20px}
.sidebar .nav-link{color:#ced4da;border-radius:.375rem;padding:.5rem .75rem;display:block;text-decoration:none}
.sidebar .nav-link.active{background:#0d6efd;color:#fff}
.sidebar-footer{margin-top:32px;padding:12px;font-size:.8rem;border-top:1px solid #343a40}
.main-col{flex:1;min-width:0}
.topbar{display:flex;align-items:center;gap:12px;padding:10px 24px;background:#fff;border-bottom:1px solid #dee2e6}
.d-flex{display:flex}.justify-content-between{justify-content:space-between}.align-items-center{align-items:center}
.btn{display:inline-block;font-weight:500;padding:.375rem .75rem;border-radius:.375rem;border:1px solid transparent;text-decoration:none;cursor:pointer}
.btn-sm{padding:.2rem .5rem;font-size:.82rem}
.btn-primary{background:#0d6efd;color:#fff}.btn-link{color:#0d6efd;background:none}
.btn-outline-secondary{border-color:#6c757d;color:#6c757d;background:#fff}.btn-outline-danger{border-color:#dc3545;color:#dc3545;background:#fff}
.btn:disabled{opacity:.45;pointer-events:none}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:16px 0}
.kpi-card{background:#fff;border:1px solid #dee2e6;border-radius:.5rem;padding:14px 16px}
.kpi-label{font-size:.78rem;color:#6c757d;text-transform:uppercase}.kpi-value{font-size:1.4rem;font-weight:600}
.nav-tabs{display:flex;list-style:none;padding:0;margin:0;border-bottom:1px solid #dee2e6}
.nav-tabs .nav-link{display:block;padding:.5rem 1rem;border:1px solid transparent;border-radius:.375rem .375rem 0 0;color:#495057;text-decoration:none}
.nav-tabs .nav-link.active{background:#fff;border-color:#dee2e6 #dee2e6 #fff}
.card{background:#fff;border:1px solid #dee2e6;border-top:0}
.table-toolbar{display:flex;gap:8px;padding:12px}
.form-control,.form-select{padding:.375rem .75rem;border:1px solid #ced4da;border-radius:.375rem}
.table{width:100%;border-collapse:collapse}.table th,.table td{padding:.6rem .75rem;border-bottom:1px solid #dee2e6;vertical-align:middle}
.table-hover tbody tr:hover{background:#f8f9fa}.table-light th{background:#f8f9fa;font-size:.8rem;color:#6c757d}
.text-end{text-align:right}.text-nowrap{white-space:nowrap}.text-muted{color:#6c757d}
.badge{display:inline-block;padding:.35em .65em;font-size:.75em;font-weight:700;border-radius:.375rem}
.text-bg-success{background:#198754;color:#fff}.text-bg-danger{background:#dc3545;color:#fff}.text-bg-warning{background:#ffc107;color:#000}
.text-bg-primary{background:#0d6efd;color:#fff}.text-bg-secondary{background:#6c757d;color:#fff}.text-bg-light{background:#f8f9fa;color:#000}
.table-summary{display:flex;justify-content:space-between;padding:12px 16px;font-size:.85rem;color:#6c757d}
.visually-hidden{position:absolute!important;width:1px!important;height:1px!important;overflow:hidden!important;clip:rect(0,0,0,0)!important}
.site-footer{padding:20px 24px;font-size:.8rem;color:#6c757d}
"""

CSS02_V2 = """
.TopNav_root__x8Ad2{display:flex;align-items:center;gap:28px;height:56px;padding:0 32px;background:#101828;color:#fff}
.Page_main__Gq3vK{max-width:1280px;margin:0 auto;padding:28px 32px}
.Card_card__k39Za{background:#fff;border:1px solid #eaecf0;border-radius:12px;box-shadow:0 1px 2px rgba(16,24,40,.05)}
.InvoiceTable_table__1bX9c{width:100%;border-collapse:separate;border-spacing:0}
.InvoiceTable_num__3kPq1{text-align:right;font-variant-numeric:tabular-nums}
.StatusPill_pill__Qm3Xa{display:inline-flex;align-items:center;gap:6px;padding:2px 8px;border-radius:16px;font-size:12px;font-weight:500}
.Segmented_root__3fQ9x{display:inline-flex;padding:4px;border-radius:10px;background:#f2f4f7}
"""

PILL02 = {"Paid": "success", "Overdue": "danger", "Partially paid": "warning", "Sent": "info", "Draft": "neutral", "Void": "muted"}
BADGE02 = {"Paid": "text-bg-success", "Overdue": "text-bg-danger", "Partially paid": "text-bg-warning",
           "Sent": "text-bg-primary", "Draft": "text-bg-secondary", "Void": "text-bg-light"}


@suite
def table_02():
    pos = {inv[0]: i for i, inv in enumerate(INV02, 1)}
    counts = Counter(inv[5] for inv in INV02)
    unpaid = [inv for inv in INV02 if inv[5] in ("Sent", "Partially paid", "Overdue")]
    overdue = [inv for inv in INV02 if inv[5] == "Overdue"]
    out_total = sum(_balance02(i) for i in unpaid)
    od_total = sum(_balance02(i) for i in overdue)
    paid_total = sum(i[6] for i in INV02 if i[5] == "Paid")
    targets = [
        dict(id="t1", key="check:INV-1043",
             description="Bulk-select checkbox of invoice INV-1043 (Kettle & Crumb Bakery)",
             css=f"#invoices-table tbody tr:nth-child({pos['INV-1043']}) .row-check",
             xpath="//tr[td[2]='INV-1043']//input[@type='checkbox']",
             mutations=["class-obfuscation", "wrapper-divs", "sibling-reorder", "insertion", "id-change"]),
        dict(id="t2", key="download:INV-1038",
             description="Download-PDF row action of invoice INV-1038 (v2 label 'Export PDF')",
             css="#invoices-table tr[data-invoice='INV-1038'] button[data-testid='download-pdf']",
             xpath="//a[normalize-space()='INV-1038']/ancestor::tr//button[normalize-space()='Download']",
             mutations=["shadow-dom", "copy-change", "testid-change", "class-obfuscation", "sibling-reorder", "decoy"]),
        dict(id="t3", key="status:INV-1045",
             description="Status badge of invoice INV-1045 (value 'Overdue')",
             css=f"#invoices-table tbody tr:nth-child({pos['INV-1045']}) td:nth-child(7) > span.badge",
             xpath="//tr[@data-invoice='INV-1045']//span[contains(@class,'badge')]",
             mutations=["class-obfuscation", "sibling-reorder", "attribute-churn", "decoy"]),
        dict(id="t4", key="amount:INV-1033",
             description="Amount cell of invoice INV-1033 (Halcyon Architecture, $12,480.00)",
             css=f"#invoices-table > tbody > tr:nth-child({pos['INV-1033']}) > td:nth-child(6)",
             xpath="//tr[td[2]='INV-1033']/td[6]",
             mutations=["sibling-reorder", "insertion", "class-obfuscation", "id-change"]),
        dict(id="t5", key="void:INV-1047",
             description="'Void' action of invoice INV-1047 (moved into the row's overflow menu as 'Void invoice' in v2)",
             css=f"#invoices-table tbody tr:nth-child({pos['INV-1047']}) .btn-void",
             xpath="//tr[@data-invoice='INV-1047']//button[@data-testid='void-invoice']",
             mutations=["shadow-dom", "structure-move", "copy-change", "testid-change", "sibling-reorder", "decoy"]),
        dict(id="t6", key="tab:outstanding",
             description="'Outstanding' status filter tab above the invoice list (v2: 'Unpaid' segment)",
             css="ul.nav-tabs a[href='?status=outstanding']",
             xpath="//ul[contains(@class,'nav-tabs')]//a[starts-with(normalize-space(),'Outstanding')]",
             mutations=["tag-change", "copy-change", "sibling-reorder", "class-obfuscation", "wrapper-divs"]),
    ]

    def v1(M):
        rows = []
        for inv in INV02:
            num, cust, issued, due, amount, status, _paid = inv
            can_void = status in ("Draft", "Sent", "Overdue", "Partially paid")
            dis = "" if can_void else ' disabled title="Paid or voided invoices can&#39;t be voided"'
            rows.append(f"""
                <tr data-invoice="{num}">
                  <td class="col-check"><input class="form-check-input row-check" type="checkbox" name="selected[]" value="inv_{num[4:]}" aria-label="Select {num}"{M('check:' + num)}></td>
                  <td><a href="/invoices/{num}" class="invoice-link">{num}</a></td>
                  <td>{esc(cust)}</td>
                  <td>{d_gb(issued)}</td>
                  <td>{d_gb(due)}</td>
                  <td class="text-end"{M('amount:' + num)}>{money(amount)}</td>
                  <td><span class="badge {BADGE02[status]}"{M('status:' + num)}>{status}</span></td>
                  <td class="text-end text-nowrap"><a href="/invoices/{num}" class="btn btn-sm btn-link">View</a> <button type="button" class="btn btn-sm btn-outline-secondary btn-download" data-testid="download-pdf"{M('download:' + num)}><i class="bi bi-download" aria-hidden="true"></i> Download</button> <button type="button" class="btn btn-sm btn-outline-danger btn-void" data-testid="void-invoice"{dis}{M('void:' + num)}>Void</button></td>
                </tr>""")
        tabs = [("all", "All", len(INV02)), ("draft", "Draft", counts["Draft"]), ("outstanding", "Outstanding", len(unpaid)),
                ("paid", "Paid", counts["Paid"]), ("void", "Void", counts["Void"])]
        tab_html = "\n".join(
            f'          <li class="nav-item"><a class="nav-link{" active" if k == "all" else ""}" href="?status={k}"'
            f'{CUR if k == "all" else ""}{M("tab:" + k)}>{label} <span class="badge rounded-pill text-bg-light">{n}</span></a></li>'
            for k, label, n in tabs)
        nav = ["Dashboard", "Invoices", "Quotes", "Customers", "Products &amp; services", "Payments", "Reports", "Settings"]
        nav_html = "\n".join(
            f'        <li class="nav-item"><a class="nav-link{" active" if n == "Invoices" else ""}" href="/{slug(n.replace("&amp;", "and"))}">{n}</a></li>'
            for n in nav)
        body = f"""
<div class="d-flex app-wrapper">
  <nav class="sidebar bg-dark" aria-label="Primary">
    <a class="sidebar-brand" href="/">Ledgerly</a>
    <ul class="nav flex-column">
{nav_html}
    </ul>
    <div class="sidebar-footer">Fernhill Studio Ltd<br><small>Growth plan &middot; USD</small></div>
  </nav>
  <div class="main-col">
    <header class="topbar navbar">
      <form class="topbar-search" role="search"><input class="form-control" type="search" placeholder="Search invoices, customers, payments" aria-label="Search"></form>
      <a class="btn btn-link" href="/help">Help</a>
      <span class="topbar-user">Rosa Whitfield</span>
    </header>
    <main class="container-fluid py-4">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h1 class="h3 mb-0">Invoices</h1>
        <div class="btn-group"><button type="button" class="btn btn-outline-secondary">Import</button> <a href="/invoices/new" class="btn btn-primary">+ New invoice</a></div>
      </div>
      <div class="kpis">
        <div class="kpi-card"><div class="kpi-label">Outstanding</div><div class="kpi-value">{money(out_total)}</div><div class="text-muted">{len(unpaid)} invoices</div></div>
        <div class="kpi-card"><div class="kpi-label">Overdue</div><div class="kpi-value">{money(od_total)}</div><div class="text-muted">{len(overdue)} invoices</div></div>
        <div class="kpi-card"><div class="kpi-label">Paid (last 90 days)</div><div class="kpi-value">{money(paid_total)}</div><div class="text-muted">{counts['Paid']} invoices</div></div>
        <div class="kpi-card"><div class="kpi-label">Avg. days to pay</div><div class="kpi-value">18</div><div class="text-muted">&minus;3 vs. previous period</div></div>
      </div>
      <ul class="nav nav-tabs" role="tablist">
{tab_html}
      </ul>
      <div class="card">
        <div class="table-toolbar">
          <select class="form-select" aria-label="Date range"><option>Last 90 days</option><option>This year</option><option>All time</option></select>
          <input class="form-control" type="search" placeholder="Filter by customer" aria-label="Filter by customer">
          <button type="button" class="btn btn-outline-secondary" disabled>Bulk actions</button>
        </div>
        <table class="table table-hover align-middle mb-0" id="invoices-table">
          <thead class="table-light">
            <tr>
              <th scope="col" class="col-check"><input class="form-check-input" type="checkbox" id="select-all" aria-label="Select all invoices"></th>
              <th scope="col">Invoice</th>
              <th scope="col">Customer</th>
              <th scope="col">Issued</th>
              <th scope="col">Due</th>
              <th scope="col" class="text-end">Amount</th>
              <th scope="col">Status</th>
              <th scope="col" class="text-end">Actions</th>
            </tr>
          </thead>
          <tbody>{''.join(rows)}
          </tbody>
        </table>
        <div class="table-summary"><span>{len(INV02)} invoices</span><span>Outstanding balance: <strong>{money(out_total)}</strong></span></div>
      </div>
    </main>
    <footer class="site-footer">&copy; 2025 Ledgerly Inc. &middot; <a href="/legal/terms">Terms</a> &middot; <a href="/legal/privacy">Privacy</a> &middot; <a href="https://status.ledgerly.example">Status</a></footer>
  </div>
</div>
"""
        return page("Invoices · Ledgerly", body, css=CSS02_V1)

    def v2(M):
        order = sorted(INV02, key=lambda i: i[3])  # redesign sorts by due date, soonest first
        T = lambda local: cm("InvoiceTable", local)  # noqa: E731
        pill = lambda status, mark="": (  # noqa: E731
            f'<span class="{cm("StatusPill", "pill")} {cm("StatusPill", PILL02[status])}"{mark}>'
            f'<svg class="{cm("StatusPill", "dot")}" width="6" height="6" viewBox="0 0 6 6" aria-hidden="true"><circle cx="3" cy="3" r="3"/></svg>{status}</span>')
        ia_css = (":host{display:inline-flex;align-items:center;gap:4px;position:relative}"
                  ".ia-icon,.ia-btn{display:inline-flex;align-items:center;gap:6px;height:32px;border-radius:8px;border:1px solid #d0d5dd;background:#fff;color:#344054;font:500 13px/1 Inter,sans-serif}"
                  ".ia-icon{width:32px;justify-content:center}.ia-btn{padding:0 10px}"
                  ".ia-menu{position:absolute;right:0;top:36px;min-width:180px;padding:4px;border-radius:8px;background:#fff;box-shadow:0 12px 16px -4px rgba(16,24,40,.08)}"
                  ".ia-item{display:block;width:100%;text-align:left;padding:8px 10px;border:0;background:none;border-radius:6px}"
                  ".ia-item--danger{color:#b42318}.ia-item[aria-disabled=true]{opacity:.4}")
        rows = []
        for inv in order:
            num, cust, issued, due, amount, status, _paid = inv
            hid = _hash(num, 8, _B36)
            initials = "".join(w[0] for w in cust.replace("&", "").split()[:2]).upper()
            void_dis = "" if status in ("Draft", "Sent", "Overdue", "Partially paid") else ' aria-disabled="true"'
            rows.append(f"""
                    <tr class="{T('row')}">
                      <td class="{T('check')}"><label class="{cm('Checkbox', 'root')}"><input type="checkbox" class="{cm('Checkbox', 'input')}" aria-label="Select invoice {num}"{M('check:' + num)}><span class="{cm('Checkbox', 'box')}" aria-hidden="true"></span></label></td>
                      <td class="{T('status')}">{pill(status, M('status:' + num))}</td>
                      <td><a class="{T('number')}" href="/app/invoices/{hid}">{num}</a></td>
                      <td><div class="{T('customer')}"><span class="{cm('Avatar', 'initials')}" aria-hidden="true">{initials}</span><span>{esc(cust)}</span></div></td>
                      <td class="{T('date')}">{d_us(issued)}</td>
                      <td class="{T('date')}">{d_us(due)}</td>
                      <td class="{T('num')}"{M('amount:' + num)}>{money(amount)}</td>
                      <td class="{T('num')}">{money(_balance02(inv))}</td>
                      <td class="{T('actions')}"><invoice-actions data-invoice-id="{hid}"><template shadowrootmode="open"><style>{ia_css}</style><a class="ia-icon" href="/app/invoices/{hid}" title="View" aria-label="View invoice">{icon('eye')}</a><button class="ia-btn" type="button" part="export"{M('download:' + num)}>{icon('download')}Export PDF</button><button class="ia-icon" type="button" aria-label="More actions" aria-haspopup="menu" aria-expanded="false">{icon('dots')}</button><div class="ia-menu" role="menu" hidden><button class="ia-item" role="menuitem" type="button">Duplicate</button><button class="ia-item" role="menuitem" type="button">Send reminder</button><button class="ia-item ia-item--danger" role="menuitem" type="button"{void_dis}{M('void:' + num)}>Void invoice</button></div></template></invoice-actions></td>
                    </tr>""")
        att = []
        for inv in sorted(overdue, key=lambda i: i[3]):
            num, cust, _issued, due, _amount, status, _paid = inv
            days = (date.fromisoformat(TODAY02) - date.fromisoformat(due)).days
            att.append(f"""
                <tr><td><a href="/app/invoices/{_hash(num, 8, _B36)}">{num}</a></td><td>{esc(cust)}</td><td>{pill(status)}</td><td>{days} days</td><td class="{cm('Attention', 'num')}">{money(_balance02(inv))}</td><td><button type="button" class="{cm('Button', 'secondary')} {cm('Button', 'sm')}">Send reminder</button></td></tr>""")
        seg = [("all", "All", len(INV02)), ("outstanding", "Unpaid", len(unpaid)), ("draft", "Draft", counts["Draft"]),
               ("paid", "Paid", counts["Paid"]), ("void", "Void", counts["Void"])]
        seg_html = "".join(
            f'<button type="button" role="tab" aria-selected="{"true" if k == "all" else "false"}" class="{cm("Segmented", "item")}'
            f'{" " + cm("Segmented", "active") if k == "all" else ""}"{M("tab:" + k)}>{label} <span class="{cm("Segmented", "count")}">{n}</span></button>'
            for k, label, n in seg)
        seg_opts = "".join(f"<option>{label} ({n})</option>" for _k, label, n in seg)
        nav = [("Invoices", True), ("Quotes", False), ("Customers", False), ("Payments", False), ("Products", False), ("Reports", False), ("Overview", False)]
        nav_html = "".join(
            f'<a class="{cm("TopNav", "link")}{" " + cm("TopNav", "current") if cur else ""}" href="/app/{n.lower()}"{CUR if cur else ""}>{n}</a>'
            for n, cur in nav)
        kpi = lambda label, value, sub: (  # noqa: E731
            f'<div class="{cm("Stat", "root")}"><dt class="{cm("Stat", "label")}">{label}</dt><dd class="{cm("Stat", "value")}">{value}</dd><dd class="{cm("Stat", "sub")}">{sub}</dd></div>')
        body = f"""
<header class="{cm('TopNav', 'root')}">
  <a class="{cm('TopNav', 'brand')}" href="/app"><svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true"><rect width="24" height="24" rx="6" fill="#7f56d9"/></svg><span>Ledgerly</span></a>
  <nav class="{cm('TopNav', 'links')}" aria-label="Main">{nav_html}</nav>
  <div class="{cm('TopNav', 'right')}"><button type="button" class="{cm('Button', 'primary')}">{icon('plus')}New invoice</button><button type="button" class="{cm('TopNav', 'avatar')}" aria-label="Account menu">RW</button></div>
</header>
<main class="{cm('Page', 'main')}">
  <div class="{cm('PageHeader', 'root')}">
    <div><h1 class="{cm('PageHeader', 'title')}">Invoices</h1><p class="{cm('PageHeader', 'subtitle')}">Fernhill Studio Ltd &middot; all amounts in USD</p></div>
    <div class="{cm('PageHeader', 'actions')}"><button type="button" class="{cm('Button', 'secondary')}">Import CSV</button><button type="button" class="{cm('Button', 'secondary')}">{icon('download')}Export</button></div>
  </div>
  <dl class="{cm('StatGrid', 'root')}">
    {kpi('Unpaid', money(out_total), f'{len(unpaid)} invoices')}
    {kpi('Overdue', money(od_total), f'{len(overdue)} invoices')}
    {kpi('Collected (90 days)', money(paid_total), f'{counts["Paid"]} invoices')}
    {kpi('Average time to pay', '18 days', 'down 3 days')}
  </dl>
  <section class="{cm('Card', 'card')} {cm('Attention', 'root')}" aria-labelledby="attention-title">
    <div class="{cm('Card', 'header')}"><h2 id="attention-title" class="{cm('Card', 'title')}">Needs attention</h2><span class="{cm('Card', 'meta')}">{len(overdue)} overdue invoices</span></div>
    <table class="{cm('Attention', 'table')}">
      <thead><tr><th scope="col">Invoice</th><th scope="col">Customer</th><th scope="col">Status</th><th scope="col">Overdue by</th><th scope="col">Balance</th><th scope="col"><span class="{cm('Util', 'srOnly')}">Action</span></th></tr></thead>
      <tbody>{''.join(att)}
      </tbody>
    </table>
  </section>
  <div class="{cm('Filters', 'root')}">
    <div role="tablist" aria-label="Filter by status" class="{cm('Segmented', 'root')}">{seg_html}</div>
    <select class="{cm('Filters', 'mobileSelect')}" aria-label="Filter by status">{seg_opts}</select>
    <div class="{cm('Filters', 'search')}">{icon('search')}<input type="search" placeholder="Search by invoice # or customer" aria-label="Search invoices"></div>
    <button type="button" class="{cm('Button', 'secondary')}">{icon('funnel')}More filters</button>
  </div>
  <div class="{cm('BulkBar', 'root')}" role="toolbar" aria-label="Bulk actions" hidden><span>0 selected</span><button type="button" class="{cm('Button', 'secondary')}">Mark as paid</button><button type="button" class="{cm('Button', 'secondary')}">Send reminders</button><button type="button" class="{cm('Button', 'secondary')}">Export PDFs</button></div>
  <section class="{cm('Card', 'card')}">
    <div class="{T('scroll')}">
      <div class="{T('inner')}">
        <table class="{T('table')}">
          <thead class="{T('head')}">
            <tr>
              <th scope="col" class="{T('check')}"><label class="{cm('Checkbox', 'root')}"><input type="checkbox" class="{cm('Checkbox', 'input')}" aria-label="Select all"><span class="{cm('Checkbox', 'box')}" aria-hidden="true"></span></label></th>
              <th scope="col">Status</th>
              <th scope="col">Invoice</th>
              <th scope="col">Customer</th>
              <th scope="col">Issued</th>
              <th scope="col" aria-sort="ascending"><button type="button" class="{T('sort')}">Due date{icon('chev-down')}</button></th>
              <th scope="col" class="{T('num')}">Amount</th>
              <th scope="col" class="{T('num')}">Balance due</th>
              <th scope="col"><span class="{cm('Util', 'srOnly')}">Actions</span></th>
            </tr>
          </thead>
          <tbody>{''.join(rows)}
          </tbody>
        </table>
      </div>
    </div>
    <div class="{T('footer')}"><span>Showing 1&ndash;{len(INV02)} of {len(INV02)}</span><span>Total unpaid <strong>{money(out_total)}</strong></span></div>
  </section>
</main>
<footer class="{cm('Footer', 'root')}">&copy; 2025 Ledgerly Inc. &middot; <a href="/legal/terms">Terms</a> &middot; <a href="/legal/privacy">Privacy</a></footer>
"""
        return page("Invoices – Ledgerly", body, css=CSS02_V2)

    emit("table-02",
         title="Invoices list with status badges, row actions and bulk selection",
         mutations=["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change",
                    "testid-change", "copy-change", "tag-change", "attribute-churn", "structure-move", "insertion"],
         notes=("v2 migrates from Bootstrap to CSS Modules, swaps the sidebar for a top nav, re-sorts invoices by due date, moves "
                "the Status column to the front and inserts 'Balance due', renders each row's actions in an <invoice-actions> "
                "declarative shadow root ('Download' becomes 'Export PDF'; 'Void' moves into a hidden overflow menu as 'Void "
                "invoice'), adds a 'Needs attention' summary table repeating the overdue invoices with identical status pills, "
                "turns the status tabs into a segmented control ('Outstanding' -> 'Unpaid') plus a mobile <select>, and drops "
                "data-invoice/data-testid/ids."),
         targets=targets, v1=v1, v2=v2)


# ========================================================================================
# table-03 — Watchlist (Bluefin Invest)  ·  v2: styled-components, whole watchlist in a shadow root
# ========================================================================================
WL03 = [
    # symbol, name, last, change, change %, volume, day low, day high, market cap
    ("AAPL", "Apple Inc.", 229.87, 1.42, 0.62, "48.21M", 227.10, 230.44, "3.41T"),
    ("MSFT", "Microsoft Corp.", 512.30, -3.18, -0.62, "19.87M", 509.75, 517.02, "3.81T"),
    ("NVDA", "NVIDIA Corp.", 186.52, 4.91, 2.70, "212.4M", 181.20, 187.95, "4.54T"),
    ("AMZN", "Amazon.com Inc.", 221.04, 0.87, 0.40, "36.02M", 218.66, 222.31, "2.36T"),
    ("GOOGL", "Alphabet Inc. Class A", 246.15, -1.02, -0.41, "28.77M", 244.80, 249.12, "2.98T"),
    ("TSLA", "Tesla Inc.", 428.66, -9.37, -2.14, "96.15M", 424.10, 441.90, "1.38T"),
    ("META", "Meta Platforms Inc.", 736.20, 6.14, 0.84, "11.48M", 727.35, 738.80, "1.85T"),
    ("ASML", "ASML Holding N.V. ADR", 1012.40, 18.25, 1.84, "1.32M", 992.05, 1015.70, "398.2B"),
    ("BTC-USD", "Bitcoin", 104212.00, 1844.10, 1.80, "38.6B", 101950.00, 104880.00, "2.07T"),
    ("ETH-USD", "Ethereum", 3412.58, -61.22, -1.76, "19.2B", 3388.10, 3502.44, "411.9B"),
    ("SOL-USD", "Solana", 184.33, 7.95, 4.51, "5.41B", 175.02, 186.90, "100.3B"),
    ("JPM", "JPMorgan Chase & Co.", 302.11, 0.65, 0.22, "7.94M", 299.84, 303.30, "830.6B"),
    ("KO", "Coca-Cola Co.", 69.48, -0.21, -0.30, "12.66M", 69.11, 69.97, "299.0B"),
    ("NVO", "Novo Nordisk A/S ADR", 54.73, -1.88, -3.32, "22.31M", 54.20, 56.88, "244.1B"),
]

CSS03_V1 = """
:root{color-scheme:dark;--bg:#0b0f17;--panel:#121826;--line:#1f2937;--txt:#e5e7eb;--mut:#8b95a7;--up:#16c784;--down:#ea3943;--acc:#3b82f6}
body{margin:0;background:var(--bg);color:var(--txt);font:13px/1.4 "IBM Plex Sans",system-ui,sans-serif}
.topbar{display:flex;align-items:center;gap:28px;padding:0 20px;height:52px;border-bottom:1px solid var(--line)}
.brand{font-weight:700;font-size:17px;color:#fff;text-decoration:none}.brand-tag{color:var(--acc);margin-left:4px}
.topnav a{color:var(--mut);text-decoration:none;margin-right:18px}.topnav a.active{color:#fff}
.account-summary{margin-left:auto;text-align:right}.account-summary .label{display:block;color:var(--mut);font-size:11px}
.market-strip{display:flex;gap:24px;padding:8px 20px;border-bottom:1px solid var(--line);font-size:12px}
.wl-page{display:grid;grid-template-columns:1fr 300px;gap:20px;padding:20px}
.wl-panel,.side-card{background:var(--panel);border:1px solid var(--line);border-radius:8px}
.wl-header{display:flex;align-items:center;gap:16px;padding:14px 16px;border-bottom:1px solid var(--line)}
.wl-title{font-size:16px;margin:0}.wl-tab{background:none;border:0;color:var(--mut);padding:6px 10px}.wl-tab.is-active{color:#fff;border-bottom:2px solid var(--acc)}
.wl-add{margin-left:auto;display:flex;gap:6px}.wl-add__input{background:#0b0f17;border:1px solid var(--line);color:var(--txt);padding:6px 10px;border-radius:6px;width:200px}
.wl-table{width:100%;border-collapse:collapse}.wl-table th{color:var(--mut);font-weight:500;text-align:left;padding:8px 12px;border-bottom:1px solid var(--line)}
.wl-table td{padding:9px 12px;border-bottom:1px solid var(--line)}.num{text-align:right;font-variant-numeric:tabular-nums}
.is-up{color:var(--up)}.is-down{color:var(--down)}.ticker{display:block}.company{color:var(--mut);font-size:11px}
.range-track{display:inline-block;position:relative;width:60px;height:3px;margin:0 6px;background:#374151;vertical-align:middle}.range-pos{position:absolute;top:-2px;width:3px;height:7px;background:#fff}
.wl-btn{border:0;border-radius:4px;padding:4px 10px;font-weight:600;color:#fff;cursor:pointer}.wl-btn--buy{background:#15803d}.wl-btn--sell{background:#b91c1c;margin-left:4px}
.wl-icon-btn{background:none;border:0;color:var(--mut);padding:4px;cursor:pointer}
.side-card h2{font-size:13px;margin:0;padding:12px 14px;border-bottom:1px solid var(--line)}
.mover-list,.news-list{list-style:none;margin:0;padding:6px 14px}.mover-list li,.news-list li{padding:6px 0;border-bottom:1px solid var(--line)}
.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.site-footer{padding:16px 20px;color:var(--mut);font-size:11px;border-top:1px solid var(--line)}
"""


def _px(x):
    return f"${x:,.2f}"


def _spark(sym, up):
    rnd = random.Random(sym)
    y, pts = 12.0, []
    for i in range(12):
        y = max(2.0, min(22.0, y + rnd.uniform(-3.5, 3.5) - (0.6 if up else -0.6)))
        pts.append(f"{i * 7:.0f},{y:.1f}")
    return " ".join(pts)


@suite
def table_03():
    pos = {w[0]: i for i, w in enumerate(WL03, 1)}
    targets = [
        dict(id="t1", key="alert:NVDA",
             description="Icon-only price-alert (bell) button in the NVDA watchlist row",
             css="#watchlist tr[data-symbol='NVDA'] .wl-alert-btn",
             xpath="//tr[td[1]/strong='NVDA']//button[@title='Set price alert']",
             mutations=["shadow-dom", "class-obfuscation", "attribute-churn", "copy-change", "sibling-reorder", "structure-move"]),
        dict(id="t2", key="price:ETH-USD",
             description="Last-price cell of the ETH-USD watchlist row ($3,412.58)",
             css=f"#watchlist tbody tr:nth-child({pos['ETH-USD']}) td.col-price",
             xpath="//table[@id='watchlist']//tr[@data-symbol='ETH-USD']/td[2]",
             mutations=["shadow-dom", "sibling-reorder", "insertion", "class-obfuscation", "attribute-churn", "decoy"]),
        dict(id="t3", key="pct:TSLA",
             description="Change-% cell of the TSLA watchlist row (−2.14%)",
             css=f"#watchlist > tbody > tr:nth-child({pos['TSLA']}) > td:nth-child(4)",
             xpath="//strong[.='TSLA']/ancestor::tr/td[contains(@class,'col-chg-pct')]",
             mutations=["shadow-dom", "sibling-reorder", "class-obfuscation", "wrapper-divs", "decoy"]),
        dict(id="t4", key="add-symbol",
             description="'Add symbol' text input of the watchlist",
             css="#add-symbol",
             xpath="//form[contains(@class,'wl-add')]/input[@name='symbol']",
             mutations=["shadow-dom", "id-change", "copy-change", "wrapper-divs", "class-obfuscation", "structure-move"]),
        dict(id="t5", key="buy:MSFT",
             description="'Buy' quick-trade button in the MSFT watchlist row",
             css=f"#watchlist tbody tr:nth-child({pos['MSFT']}) .wl-btn--buy",
             xpath="//tr[@data-symbol='MSFT']//button[normalize-space()='Buy']",
             mutations=["shadow-dom", "sibling-reorder", "class-obfuscation", "attribute-churn", "wrapper-divs", "decoy"]),
        dict(id="t6", key="sort:pct",
             description="Sort control in the 'Chg %' column header (v2: 'Change %' button)",
             css="#watchlist th.col-chg-pct a.sort-link",
             xpath="//th/a[normalize-space()='Chg %']",
             mutations=["shadow-dom", "tag-change", "copy-change", "sibling-reorder", "class-obfuscation"]),
    ]

    def v1(M):
        rows = []
        for sym, name, last, chg, pct, vol, lo, hi, _cap in WL03:
            d = "is-up" if chg >= 0 else "is-down"
            left = round((last - lo) / (hi - lo) * 100)
            rows.append(f"""
          <tr data-symbol="{sym}" class="wl-row">
            <td class="col-symbol"><strong class="ticker">{sym}</strong><span class="company">{esc(name)}</span></td>
            <td class="col-price num"{M('price:' + sym)}>{_px(last)}</td>
            <td class="col-chg num {d}">{signed(chg)}</td>
            <td class="col-chg-pct num {d}"{M('pct:' + sym)}>{signed(pct, suffix='%')}</td>
            <td class="col-vol num">{vol}</td>
            <td class="col-range"><span class="range-lo">{lo:,.2f}</span><span class="range-track"><span class="range-pos" style="left:{left}%"></span></span><span class="range-hi">{hi:,.2f}</span></td>
            <td class="col-actions"><button type="button" class="wl-btn wl-btn--buy"{M('buy:' + sym)}>Buy</button><button type="button" class="wl-btn wl-btn--sell">Sell</button><button type="button" class="wl-icon-btn wl-alert-btn" title="Set price alert" aria-label="Set price alert for {sym}"{M('alert:' + sym)}>{icon('bell')}</button><button type="button" class="wl-icon-btn wl-remove-btn" title="Remove from watchlist" aria-label="Remove {sym} from watchlist">{icon('x')}</button></td>
          </tr>""")
        movers = sorted(WL03, key=lambda w: -abs(w[4]))[:5]
        mover_html = "".join(
            f'<li><a href="/quote/{w[0]}">{w[0]}</a> <span class="{"is-up" if w[4] >= 0 else "is-down"}">{signed(w[4], suffix="%")}</span></li>'
            for w in movers)
        body = f"""
<header class="topbar">
  <a class="brand" href="/">Bluefin<span class="brand-tag">Invest</span></a>
  <nav class="topnav" aria-label="Main"><a href="/markets">Markets</a><a class="active" href="/watchlists" aria-current="page">Watchlists</a><a href="/portfolio">Portfolio</a><a href="/orders">Orders</a><a href="/news">News</a></nav>
  <div class="account-summary"><span class="label">Buying power</span><span class="value">$24,318.62</span></div>
</header>
<div class="market-strip" aria-label="Market overview">
  <span>S&amp;P 500 <b>6,842.15</b> <span class="is-up">+0.42%</span></span>
  <span>Nasdaq <b>23,104.88</b> <span class="is-up">+0.71%</span></span>
  <span>Dow <b>47,281.04</b> <span class="is-down">{MINUS}0.12%</span></span>
  <span>EUR/USD <b>1.0842</b> <span class="is-down">{MINUS}0.05%</span></span>
  <span>Gold <b>$4,011.30</b> <span class="is-up">+0.33%</span></span>
</div>
<main class="wl-page">
  <section class="wl-panel" aria-labelledby="wl-title">
    <div class="wl-header">
      <h1 id="wl-title" class="wl-title">My watchlist</h1>
      <div class="wl-tabs" role="tablist">
        <button type="button" role="tab" aria-selected="true" class="wl-tab is-active">My watchlist</button>
        <button type="button" role="tab" aria-selected="false" class="wl-tab">Tech</button>
        <button type="button" role="tab" aria-selected="false" class="wl-tab">Crypto</button>
        <button type="button" role="tab" aria-selected="false" class="wl-tab">Dividends</button>
      </div>
      <form class="wl-add" action="/watchlists/8812/symbols" method="post"><input id="add-symbol" class="wl-add__input" name="symbol" placeholder="Add symbol, e.g. AAPL" autocomplete="off"{M('add-symbol')}><button type="submit" class="wl-add__btn wl-btn">Add</button></form>
    </div>
    <table class="wl-table" id="watchlist">
      <thead>
        <tr>
          <th class="col-symbol">Symbol</th>
          <th class="col-price num">Last</th>
          <th class="col-chg num">Change</th>
          <th class="col-chg-pct num sortable"><a href="?sort=chg_pct" class="sort-link"{M('sort:pct')}>Chg %</a></th>
          <th class="col-vol num">Volume</th>
          <th class="col-range">Day range</th>
          <th class="col-actions"><span class="sr-only">Actions</span></th>
        </tr>
      </thead>
      <tbody>{''.join(rows)}
      </tbody>
    </table>
    <p class="wl-foot">Quotes delayed 15 minutes for NYSE/Nasdaq. Crypto prices are real-time. Last refresh 15:42:07 ET.</p>
  </section>
  <aside class="wl-side">
    <section class="side-card"><h2>Biggest movers in this list</h2><ul class="mover-list">{mover_html}</ul></section>
    <section class="side-card"><h2>News for your watchlist</h2>
      <ul class="news-list">
        <li><a href="/news/8812-1">Chipmakers extend rally as data-centre orders beat estimates</a><span class="company">Reuters &middot; 38 min ago</span></li>
        <li><a href="/news/8812-2">Tesla slips after delivery guidance trimmed for Q4</a><span class="company">Bloomberg &middot; 1 h ago</span></li>
        <li><a href="/news/8812-3">Ether falls as ETF outflows continue for a third session</a><span class="company">CoinDesk &middot; 2 h ago</span></li>
        <li><a href="/news/8812-4">Novo Nordisk shares drop on pricing pressure in the US</a><span class="company">FT &middot; 3 h ago</span></li>
      </ul>
    </section>
  </aside>
</main>
<footer class="site-footer">Bluefin Invest LLC, member FINRA/SIPC. Investing involves risk, including loss of principal. &copy; 2025</footer>
"""
        return page("My watchlist — Bluefin Invest", body, css=CSS03_V1, html_attrs='data-theme="dark"')

    def v2(M):
        order = sorted(WL03, key=lambda w: -w[4])  # default sort is now "Change %" descending
        rows = []
        for sym, name, last, chg, pct, vol, _lo, _hi, cap in order:
            up = chg >= 0
            tone = sc("Delta.up") if up else sc("Delta.down")
            rows.append(f"""
            <tr class="{sc('Row')}" data-ticker="{sym}">
              <td class="{sc('Cell.symbol')}"><div class="{sc('SymbolCell')}"><span class="{sc('Logo')}" aria-hidden="true">{sym[0]}</span><div class="{sc('SymbolText')}"><a class="{sc('SymbolLink')}" href="/quote/{sym}">{sym}</a><span class="{sc('CompanyName')}">{esc(name)}</span></div></div></td>
              <td class="{sc('Cell.chart')}"><svg class="{sc('Spark')}" width="80" height="24" viewBox="0 0 80 24" aria-hidden="true"><polyline fill="none" stroke="currentColor" stroke-width="1.5" points="{_spark(sym, up)}"/></svg></td>
              <td class="{sc('Cell.num')}"{M('pct:' + sym)}><span class="{tone}">{signed(pct, suffix='%')}</span></td>
              <td class="{sc('Cell.num')}"{M('price:' + sym)}>{_px(last)}</td>
              <td class="{sc('Cell.num')}"><span class="{tone}">{signed(chg)}</span></td>
              <td class="{sc('Cell.num')}">{cap}</td>
              <td class="{sc('Cell.num')}">{vol}</td>
              <td class="{sc('Cell.actions')}"><div class="{sc('RowActions')}"><button type="button" class="{sc('TradeButton.buy')}"{M('buy:' + sym)}>Buy</button><button type="button" class="{sc('TradeButton.sell')}">Sell</button><button type="button" class="{sc('IconButton')}" aria-label="Create price alert" aria-pressed="false"{M('alert:' + sym)}>{icon('bell')}</button><button type="button" class="{sc('IconButton')}" aria-label="More options" aria-haspopup="menu">{icon('dots')}</button></div></td>
            </tr>""")
        tick = "".join(
            f'<a class="{sc("TickerChip")}" href="/quote/{w[0]}">{w[0]} <span class="{sc("Delta.up") if w[4] >= 0 else sc("Delta.down")}">{signed(w[4], suffix="%")}</span></a>'
            for w in sorted(WL03, key=lambda w: -abs(w[4]))[:6])
        recent = [("ETH-USD", 3412.58, -1.76), ("TSLA", 428.66, -2.14), ("PLTR", 187.42, 3.06), ("SHOP", 162.05, -0.88), ("NVO", 54.73, -3.32)]
        recent_rows = "".join(
            f'<tr><td><a href="/quote/{s}">{s}</a></td><td>{_px(p)}</td><td>{signed(c, suffix="%")}</td></tr>' for s, p, c in recent)
        wl_css = (":host{display:block;color-scheme:dark}*{box-sizing:border-box}"
                  "table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}th,td{padding:10px 12px;border-bottom:1px solid #1e2533}"
                  "th{font-weight:500;color:#7c8799;text-align:right}th:first-child{text-align:left}"
                  "input{background:#0e131d;border:1px solid #273042;border-radius:8px;color:#e6e9ef;padding:8px 10px 8px 32px;width:280px}")
        body = f"""
<header class="{sc('AppHeader')}">
  <a class="{sc('Brand')}" href="/"><svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true"><path d="M2 18 C8 4 18 4 24 18" stroke="#4f8cff" stroke-width="3" fill="none"/></svg><span>Bluefin</span></a>
  <nav class="{sc('MainNav')}" aria-label="Main"><a class="{sc('NavLink')}" href="/portfolio">Portfolio</a><a class="{sc('NavLink.active')}" href="/watchlists" aria-current="page">Watchlists</a><a class="{sc('NavLink')}" href="/markets">Markets</a><a class="{sc('NavLink')}" href="/news">News</a><a class="{sc('NavLink')}" href="/orders">Orders</a></nav>
  <div class="{sc('HeaderRight')}"><div class="{sc('BuyingPower')}"><span>Buying power</span><strong>$24,318.62</strong></div><button type="button" class="{sc('DepositButton')}">Deposit</button></div>
</header>
<div class="{sc('TickerStrip')}" aria-label="Top movers in your lists">{tick}</div>
<div class="{sc('Layout')}">
  <main class="{sc('MainColumn')}">
    <div class="{sc('Banner')}" role="status">{icon('info')}<p>Extended-hours trading is now available for all US stocks from 4:00 a.m. to 8:00 p.m. ET. <a href="/help/extended-hours">Learn more</a></p></div>
    <bf-watchlist list-id="wl_8812" density="comfortable">
      <template shadowrootmode="open">
        <style>{wl_css}</style>
        <section class="{sc('Panel')}" aria-label="My watchlist">
          <div class="{sc('PanelHeader')}">
            <div class="{sc('TitleGroup')}"><h2 class="{sc('PanelTitle')}">My watchlist</h2><span class="{sc('Count')}">{len(WL03)} symbols</span></div>
            <div class="{sc('ListTabs')}" role="tablist" aria-label="Lists">
              <button type="button" role="tab" aria-selected="true" class="{sc('ListTab.active')}">My watchlist</button>
              <button type="button" role="tab" aria-selected="false" class="{sc('ListTab')}">Crypto</button>
              <button type="button" role="tab" aria-selected="false" class="{sc('ListTab')}">Tech</button>
              <button type="button" role="tab" aria-selected="false" class="{sc('ListTab')}">Dividends</button>
              <button type="button" class="{sc('NewList')}">{icon('plus')}New list</button>
            </div>
          </div>
          <div class="{sc('Toolbar')}">
            <div class="{sc('Combobox')}" role="combobox" aria-expanded="false" aria-haspopup="listbox" aria-owns="bf-sym-results">
              {icon('search', cls=sc('ComboboxIcon'))}
              <input class="{sc('ComboboxInput')}" id="bf-sym-input-3" type="text" name="symbol" placeholder="Search symbol or company" aria-label="Add symbol to watchlist" aria-autocomplete="list" autocomplete="off"{M('add-symbol')}>
              <kbd class="{sc('Kbd')}">/</kbd>
            </div>
            <ul id="bf-sym-results" role="listbox" class="{sc('Results')}" hidden></ul>
            <button type="button" class="{sc('GhostButton')}">Customize columns</button>
          </div>
          <div class="{sc('TableScroll')}">
            <table class="{sc('Table')}">
              <thead>
                <tr>
                  <th scope="col">Symbol</th>
                  <th scope="col"><span class="{sc('SrOnly')}">7-day chart</span></th>
                  <th scope="col" aria-sort="descending"><button type="button" class="{sc('SortButton.active')}"{M('sort:pct')}>Change %{icon('chev-down')}</button></th>
                  <th scope="col"><button type="button" class="{sc('SortButton')}">Last price</button></th>
                  <th scope="col">Change</th>
                  <th scope="col"><button type="button" class="{sc('SortButton')}">Mkt cap</button></th>
                  <th scope="col">Volume</th>
                  <th scope="col"><span class="{sc('SrOnly')}">Actions</span></th>
                </tr>
              </thead>
              <tbody>{''.join(rows)}
              </tbody>
            </table>
          </div>
          <p class="{sc('Disclaimer')}">Stock quotes delayed 15 min. Crypto in real time. Updated 3:42 PM ET.</p>
        </section>
      </template>
    </bf-watchlist>
  </main>
  <aside class="{sc('RightRail')}">
    <section class="{sc('RailCard')}" aria-labelledby="recent-h"><h3 id="recent-h" class="{sc('RailTitle')}">Recently viewed</h3>
      <table class="{sc('MiniTable')}"><thead><tr><th scope="col">Symbol</th><th scope="col">Price</th><th scope="col">Today</th></tr></thead><tbody>{recent_rows}</tbody></table>
    </section>
    <section class="{sc('RailCard')}" aria-labelledby="news-h"><h3 id="news-h" class="{sc('RailTitle')}">Watchlist news</h3>
      <ul class="{sc('NewsList')}">
        <li><a href="/news/8812-2">Tesla slips after delivery guidance trimmed for Q4</a><time>1h</time></li>
        <li><a href="/news/8812-1">Chipmakers extend rally as data-centre orders beat estimates</a><time>38m</time></li>
        <li><a href="/news/8812-3">Ether falls as ETF outflows continue for a third session</a><time>2h</time></li>
      </ul>
    </section>
  </aside>
</div>
<footer class="{sc('Footer')}"><p>Bluefin Invest LLC, member FINRA/SIPC. Crypto services provided by Bluefin Digital Assets LLC. &copy; 2025</p></footer>
"""
        return page("Watchlists · Bluefin", body, css="body{margin:0;background:#080b12;color:#e6e9ef;font-family:Inter,system-ui,sans-serif}", html_attrs='data-theme="dark"')

    emit("table-03",
         title="Stock & crypto watchlist with price columns and alert bells",
         mutations=["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change",
                    "copy-change", "tag-change", "attribute-churn", "structure-move", "insertion"],
         notes=("v2 is a styled-components rewrite that renders the whole watchlist inside a <bf-watchlist> declarative shadow "
                "root; rows are re-sorted by Change % (desc), columns reordered (Change % before Last price) with a sparkline "
                "and Market-cap column inserted, the day-range column dropped, the bell loses its title and gets a generic "
                "'Create price alert' label, the add-symbol form becomes a combobox, the Chg % header link becomes a 'Change %' "
                "sort button, and a light-DOM 'Recently viewed' table repeats ETH-USD and TSLA values next to a ticker strip."),
         targets=targets, v1=v1, v2=v2)


# ========================================================================================
# table-04 — Order fulfilment queue (Packwise WMS)  ·  v2: emotion, grouped tbodies, shadow DOM moved
# ========================================================================================
ORD04 = [
    # order, placed, customer, item count, first item, destination, carrier, channel, group
    ("SO-58229", "2025-10-31T08:14", "Harriet Mallory", 3, "Trailhead 28L Daypack — Moss", "Harrogate, GB", "dpd", "Web store", "ready"),
    ("SO-58231", "2025-10-31T09:02", "Callum Reid", 1, "Ridgeline Down Jacket — M, Navy", "Inverness, GB", "rm48", "Web store", "awaiting"),
    ("SO-58232", "2025-10-31T10:47", "Sanne de Vries", 2, "Fjell 2P Tent — Sand", "Rotterdam, NL", "dhl", "Marketplace", "ready"),
    ("SO-58233", "2025-10-31T11:30", "Priya Nair", 1, "Merino Base Layer — W, S", "Leicester, GB", "evri", "Web store", "ready"),
    ("SO-58235", "2025-10-31T14:22", "Tomás Ruiz", 4, "Summit Trekking Poles (pair)", "Bilbao, ES", "dhl", "Web store", "awaiting"),
    ("SO-58237", "2025-10-31T16:05", "Eleanor Whitcombe", 2, "Coastal Rain Shell — W, L", "Truro, GB", "rm24", "Web store", "ready"),
    ("SO-58238", "2025-11-01T07:41", "Jakub Nowak", 1, "Alpine 45L Pack — Slate", "Kraków, PL", "dhl", "Marketplace", "ready"),
    ("SO-58240", "2025-11-01T09:18", "Fiona Gallagher", 2, "Thermal Flask 750 ml — Forest", "Galway, IE", "dpd", "Web store", "awaiting"),
    ("SO-58241", "2025-11-01T12:56", "Oliver Brennan", 5, "Camp Cook Set — Titanium", "Sheffield, GB", "dpd", "Web store", "ready"),
    ("SO-58242", "2025-11-01T15:33", "Amelia Hartley", 1, "Trail Running Shoes — UK 6", "Bath, GB", "rm48", "Click & collect", "ready"),
    ("SO-58243", "2025-11-02T08:09", "Lukas Becker", 3, "Insulated Gloves — L", "Munich, DE", "ups", "Marketplace", "awaiting"),
    ("SO-58244", "2025-11-02T10:15", "Daan Bakker", 1, "Packable Hammock — Olive", "Rotterdam, NL", "dhl", "Web store", "ready"),
    ("SO-58245", "2025-11-02T13:48", "Grace Thornton", 2, "Wool Beanie — Charcoal", "Cardiff, GB", "evri", "Web store", "ready"),
    ("SO-58246", "2025-11-02T17:20", "Rhys Morgan", 1, "Headtorch 400 lm", "Swansea, GB", "rm24", "Web store", "awaiting"),
]
CARRIERS04 = {  # code: (v1 label, v2 label, ship-by)
    "rm48": ("Royal Mail Tracked 48", "Royal Mail · Tracked 48", "Today 17:00"),
    "rm24": ("Royal Mail Tracked 24", "Royal Mail · Tracked 24", "Today 17:00"),
    "dpd": ("DPD Next Day", "DPD · Next day", "Today 15:30"),
    "evri": ("Evri Standard", "Evri · Standard", "Tomorrow 12:00"),
    "dhl": ("DHL Express Worldwide", "DHL · Express Worldwide", "Today 16:15"),
    "ups": ("UPS Standard (EU)", "UPS · Standard EU", "Today 16:45"),
}
SHIPBY04 = {"Today 15:30": 0, "Today 16:15": 1, "Today 16:45": 2, "Today 17:00": 3, "Tomorrow 12:00": 4}

CSS04_V1 = """
body{margin:0;font:14px/1.5 "Source Sans 3",Arial,sans-serif;color:#22262e;background:#eef0f3}
.pw-header{display:flex;align-items:center;gap:20px;padding:0 20px;height:54px;background:#1b3a4b;color:#fff}
.pw-logo{color:#fff;font-weight:700;font-size:18px;text-decoration:none}.pw-site{opacity:.8}
.pw-nav a{color:#cfe0ea;text-decoration:none;margin-right:14px}.pw-nav a.current{color:#fff;border-bottom:2px solid #f2a541}
.pw-user{margin-left:auto;font-size:13px;opacity:.85}
.pw-main{padding:20px 24px}.pw-sub{color:#5b6472;margin-top:0}
.status-chips{display:flex;gap:8px;list-style:none;padding:0}.chip{display:inline-block;padding:4px 12px;border-radius:16px;background:#fff;border:1px solid #c8ccd2;color:#22262e;text-decoration:none}
.chip--active{background:#1b3a4b;color:#fff;border-color:#1b3a4b}
.queue-toolbar{display:flex;align-items:center;gap:12px;margin:12px 0}.queue-bulk{margin-left:auto;display:flex;gap:8px}
.queue-search{padding:6px 10px;border:1px solid #c8ccd2;border-radius:4px;width:260px}
.btn{padding:6px 12px;border-radius:4px;border:1px solid transparent;cursor:pointer;font:inherit}
.btn-primary{background:#f2a541;border-color:#e0922b;color:#1b1b1b;font-weight:600}.btn-secondary{background:#fff;border-color:#c8ccd2}
.queue-table{width:100%;border-collapse:collapse;background:#fff}.queue-table th{text-align:left;font-size:12px;color:#5b6472;padding:8px 10px;border-bottom:2px solid #d5d9df}
.queue-table td{padding:8px 10px;border-bottom:1px solid #e3e6ea;vertical-align:top}
.order-link{font-weight:600}.order-channel,.item-first{display:block;color:#5b6472;font-size:12px}
.col-actions{white-space:nowrap}.col-actions .btn{margin-left:4px}
.icon-printer{display:inline-block;width:12px;height:12px;background:currentColor;mask:url(/static/icons/printer.svg) center/contain no-repeat}
.queue-foot{color:#5b6472;font-size:13px}.pw-footer{padding:16px 24px;color:#5b6472;font-size:12px}
"""

PICKER04_CSS = ":host{display:inline-block}select{font:inherit;padding:4px 8px;border:1px solid #c8ccd2;border-radius:4px;background:#fff;min-width:190px}"


@suite
def table_04():
    pos = {o[0]: i for i, o in enumerate(ORD04, 1)}
    targets = [
        dict(id="t1", key="carrier:SO-58237",
             description="Carrier <select> of order SO-58237 (Eleanor Whitcombe, Truro)",
             css="tr[data-order='SO-58237'] pw-carrier-picker select[name='carrier']",
             xpath=f"//table[@id='fulfilment-queue']/tbody/tr[{pos['SO-58237']}]//select",
             mutations=["shadow-dom", "structure-move", "sibling-reorder", "insertion", "attribute-churn", "copy-change", "wrapper-divs"]),
        dict(id="t2", key="ship:SO-58241",
             description="'Ship' button of order SO-58241 (Oliver Brennan) — v2 label 'Mark as shipped'",
             css="#fulfilment-queue tr[data-order='SO-58241'] [data-qa='ship-order']",
             xpath="//tr[td/a='#SO-58241']//button[normalize-space()='Ship']",
             mutations=["copy-change", "testid-change", "class-obfuscation", "sibling-reorder", "decoy"]),
        dict(id="t3", key="label:SO-58229",
             description="'Print label' button of order SO-58229 (Harriet Mallory) — icon-only in v2",
             css="#fulfilment-queue tbody tr:first-child button[data-qa='print-label']",
             xpath="(//button[contains(@class,'btn-label')])[1]",
             mutations=["copy-change", "testid-change", "class-obfuscation", "attribute-churn", "decoy"]),
        dict(id="t4", key="dest:SO-58244",
             description="Destination cell of order SO-58244 (value 'Rotterdam, NL')",
             css=f"#fulfilment-queue tbody tr:nth-child({pos['SO-58244']}) td.col-dest",
             xpath="//tr[@data-order='SO-58244']/td[6]",
             mutations=["sibling-reorder", "insertion", "class-obfuscation", "attribute-churn", "decoy"]),
        dict(id="t5", key="bulk-print",
             description="Bulk 'Print labels for selected' toolbar button (v2: 'Print labels' in the bulk-action bar)",
             css="#bulk-print",
             xpath="//button[normalize-space()='Print labels for selected']",
             mutations=["id-change", "copy-change", "structure-move", "class-obfuscation", "decoy"]),
        dict(id="t6", key="order:SO-58233",
             description="Order-number link '#SO-58233' (Priya Nair) in the queue table",
             css="a.order-link[href='/orders/SO-58233']",
             xpath="//table[@id='fulfilment-queue']//a[.='#SO-58233']",
             mutations=["class-obfuscation", "attribute-churn", "sibling-reorder"]),
    ]

    def placed(iso):
        d, t = iso.split("T")
        return f"{int(d[8:])} {MON[int(d[5:7]) - 1]}, {t}"

    def v1(M):
        rows = []
        for num, ts, cust, n, first, dest, carrier, channel, _grp in ORD04:
            opts = "".join(f'<option value="{c}"{" selected" if c == carrier else ""}>{lbl[0]}</option>' for c, lbl in CARRIERS04.items())
            rows.append(f"""
      <tr data-order="{num}">
        <td class="col-select"><input type="checkbox" name="orders" value="{num}" aria-label="Select order {num}"></td>
        <td class="col-order"><a class="order-link" href="/orders/{num}"{M('order:' + num)}>#{num}</a><span class="order-channel">{esc(channel)}</span></td>
        <td class="col-placed">{placed(ts)}</td>
        <td class="col-customer">{esc(cust)}</td>
        <td class="col-items"><span class="item-count">{n} item{'s' if n > 1 else ''}</span><span class="item-first">{esc(first)}</span></td>
        <td class="col-dest"{M('dest:' + num)}>{esc(dest)}</td>
        <td class="col-carrier"><pw-carrier-picker order="{num}"><template shadowrootmode="open"><style>{PICKER04_CSS}</style><select part="select" name="carrier" aria-label="Carrier"{M('carrier:' + num)}>{opts}</select></template></pw-carrier-picker></td>
        <td class="col-actions"><button type="button" class="btn btn-secondary btn-label" data-qa="print-label"{M('label:' + num)}><span class="icon icon-printer" aria-hidden="true"></span> Print label</button><button type="button" class="btn btn-primary btn-ship" data-qa="ship-order"{M('ship:' + num)}>Ship</button></td>
      </tr>""")
        body = f"""
<header class="pw-header">
  <a class="pw-logo" href="/">Packwise</a>
  <span class="pw-site">Leeds DC &middot; Northcote Outdoor Co.</span>
  <nav class="pw-nav" aria-label="Main"><a href="/home">Home</a><a href="/orders">Orders</a><a class="current" href="/fulfilment" aria-current="page">Fulfilment</a><a href="/inventory">Inventory</a><a href="/returns">Returns</a><a href="/analytics">Analytics</a></nav>
  <div class="pw-user">Early shift (06:00&ndash;14:00) &middot; Dan Okafor</div>
</header>
<main class="pw-main">
  <div class="pw-titlebar">
    <h1>Fulfilment queue</h1>
    <p class="pw-sub">Orders waiting to be picked, packed and shipped from Leeds DC.</p>
  </div>
  <ul class="status-chips">
    <li><a class="chip chip--active" href="?status=unfulfilled" aria-current="page">Unfulfilled (14)</a></li>
    <li><a class="chip" href="?status=on-hold">On hold (3)</a></li>
    <li><a class="chip" href="?status=shipped-today">Shipped today (41)</a></li>
    <li><a class="chip" href="?status=returns">Returns to process (6)</a></li>
  </ul>
  <div class="queue-toolbar">
    <label class="queue-sort">Sort by <select name="sort"><option selected>Order date (oldest first)</option><option>Order date (newest first)</option><option>Destination</option><option>Carrier</option></select></label>
    <input class="queue-search" type="search" name="q" placeholder="Order #, customer or SKU" aria-label="Search orders">
    <div class="queue-bulk"><button type="button" class="btn btn-secondary" id="bulk-print"{M('bulk-print')}>Print labels for selected</button><button type="button" class="btn btn-primary" id="bulk-ship">Mark selected as shipped</button></div>
  </div>
  <table class="queue-table" id="fulfilment-queue">
    <thead>
      <tr>
        <th class="col-select"><input type="checkbox" id="select-all-orders" aria-label="Select all orders"></th>
        <th>Order</th><th>Placed</th><th>Customer</th><th>Items</th><th>Destination</th><th>Carrier</th><th class="col-actions">Actions</th>
      </tr>
    </thead>
    <tbody>{''.join(rows)}
    </tbody>
  </table>
  <p class="queue-foot">{len(ORD04)} orders &middot; cut-off for same-day DPD collection is 15:30 &middot; Royal Mail collection 17:00</p>
</main>
<footer class="pw-footer">Packwise WMS 2.8.4 &middot; Support +44 113 496 0123 &middot; <a href="/help">Help</a></footer>
"""
        return page("Fulfilment queue · Packwise", body, css=CSS04_V1, lang="en-GB")

    def v2(M):
        ready = [o for o in ORD04 if o[8] == "ready"]
        waiting = [o for o in ORD04 if o[8] == "awaiting"]
        key = lambda o: (SHIPBY04[CARRIERS04[o[6]][2]], o[0])  # noqa: E731
        btn = emo("Button")
        btn_primary = emo("Button.primary")
        rows_by_group = {}
        cards = []
        sel_n = 0
        for grp, orders in (("ready", sorted(ready, key=key)), ("awaiting", sorted(waiting, key=key))):
            out = []
            for num, _ts, cust, n, first, dest, carrier, channel, _g in orders:
                sel_n += 1
                opts = "".join(f'<option value="{c}"{" selected" if c == carrier else ""}>{lbl[1]}</option>' for c, lbl in CARRIERS04.items())
                shipby = CARRIERS04[carrier][2]
                dis = ' disabled aria-describedby="awaiting-note"' if grp == "awaiting" else ""
                out.append(f"""
          <tr class="{emo('Row')}">
            <td class="{emo('Cell.check')}"><input type="checkbox" class="{emo('Checkbox')}" aria-label="Select {num}"></td>
            <td class="{emo('Cell')}"><a class="{emo('OrderLink')}" href="/fulfil/orders/{num[3:]}"{M('order:' + num)}>#{num}</a><span class="{emo('Muted')}">{esc(channel)}</span></td>
            <td class="{emo('Cell')}"><span class="{emo('ShipBy.urgent') if shipby == 'Today 15:30' else emo('ShipBy')}">{shipby}</span></td>
            <td class="{emo('Cell')}">{esc(cust)}</td>
            <td class="{emo('Cell')}"{M('dest:' + num)}><span class="{emo('Flag')}" aria-hidden="true"></span>{esc(dest)}</td>
            <td class="{emo('Cell')}">{n} &times; <span class="{emo('Muted')}">{esc(first)}</span></td>
            <td class="{emo('Cell')}"><div class="{emo('SelectWrap')}"><select class="{emo('Select')}" id="carrier-:r{sel_n:x}:" name="shipments[{sel_n - 1}].carrierCode" aria-label="Carrier for {num}"{M('carrier:' + num)}>{opts}</select>{icon('chev-down', cls=emo('SelectChevron'))}</div></td>
            <td class="{emo('Cell.actions')}"><div class="{emo('Actions')}"><button type="button" class="{emo('IconButton')}" aria-label="Print shipping label" title="Print shipping label"{M('label:' + num)}>{icon('printer')}</button><button type="button" class="{btn_primary}"{dis}{M('ship:' + num)}>Mark as shipped</button></div></td>
          </tr>""")
                cards.append(f"""
    <article class="{emo('MobileCard')}"><h3 class="{emo('MobileCard.title')}">#{num}</h3><dl class="{emo('MobileCard.meta')}"><dt>Customer</dt><dd>{esc(cust)}</dd><dt>Ship to</dt><dd>{esc(dest)}</dd><dt>Carrier</dt><dd>{CARRIERS04[carrier][1]}</dd></dl><div class="{emo('MobileCard.actions')}"><button type="button" class="{btn}">Print label</button><button type="button" class="{btn_primary}">Mark as shipped</button></div></article>""")
            rows_by_group[grp] = "".join(out)
        hdr_css = (":host{display:block}.hdr{display:flex;align-items:center;gap:24px;height:56px;padding:0 24px;background:#0f2430;color:#fff}"
                   ".logo{font-weight:800;color:#fff;text-decoration:none}nav a{color:#9fb6c3;text-decoration:none;margin-right:16px}"
                   "nav a[aria-current]{color:#fff}.site{margin-left:auto;background:#1d3b4c;color:#fff;border:0;border-radius:6px;padding:6px 10px}")
        group_row = lambda label, n: (  # noqa: E731
            f'<tr class="{emo("GroupRow")}"><th colspan="8" scope="rowgroup" class="{emo("GroupHeader")}"><span>{label}</span>'
            f'<span class="{emo("Badge")}">{n}</span></th></tr>')
        bulk = (f'<span class="{emo("BulkCount")}">0 selected</span><button type="button" class="{btn}"{{mark}}>{icon("printer")}Print labels</button>'
                f'<button type="button" class="{btn_primary}">Mark as shipped</button>')
        body = f"""
<pw-app-header>
  <template shadowrootmode="open">
    <style>{hdr_css}</style>
    <header class="hdr">
      <a class="logo" href="/">Packwise</a>
      <nav aria-label="Main"><a href="/fulfil" aria-current="page">Fulfil</a><a href="/orders">Orders</a><a href="/inventory">Inventory</a><a href="/returns">Returns</a><a href="/analytics">Analytics</a><a href="/home">Home</a></nav>
      <button class="site" type="button" aria-haspopup="listbox">Leeds DC</button>
      <span class="user">Dan Okafor</span>
    </header>
  </template>
</pw-app-header>
<main class="{emo('Page')}">
  <div class="{emo('PageHeader')}">
    <div><h1 class="{emo('Title')}">Fulfil orders</h1><span class="{emo('Muted')}">Leeds DC &middot; Northcote Outdoor Co.</span></div>
    <div class="{emo('Tabs')}" role="tablist" aria-label="Order status">
      <button type="button" role="tab" aria-selected="true" class="{emo('Tab.active')}">Unfulfilled <span class="{emo('Badge')}">14</span></button>
      <button type="button" role="tab" aria-selected="false" class="{emo('Tab')}">On hold <span class="{emo('Badge')}">3</span></button>
      <button type="button" role="tab" aria-selected="false" class="{emo('Tab')}">Shipped today <span class="{emo('Badge')}">41</span></button>
    </div>
  </div>
  <div class="{emo('Notice')}" role="status">{icon('info')}<p>DPD collection today at <strong>15:30</strong> &middot; 9 parcels booked. Royal Mail collects at 17:00.</p></div>
  <div class="{emo('Toolbar')}">
    <div class="{emo('SearchField')}">{icon('search')}<input type="search" class="{emo('SearchInput')}" placeholder="Search orders, customers, SKUs" aria-label="Search"></div>
    <select class="{emo('Select')}" aria-label="Sort orders"><option selected>Ship-by time</option><option>Order date</option><option>Destination</option></select>
  </div>
  <div class="{emo('BulkBar')}" role="toolbar" aria-label="Bulk actions">{bulk.replace('{mark}', M('bulk-print'))}</div>
  <div class="{emo('TableCard')}">
    <div class="{emo('TableScroll')}">
      <table class="{emo('Table')}" id="fulfilment-queue">
        <thead>
          <tr>
            <th class="{emo('Head.check')}"><input type="checkbox" class="{emo('Checkbox')}" aria-label="Select all"></th>
            <th class="{emo('Head')}">Order</th><th class="{emo('Head')}">Ship by</th><th class="{emo('Head')}">Customer</th><th class="{emo('Head')}">Destination</th><th class="{emo('Head')}">Items</th><th class="{emo('Head')}">Carrier</th><th class="{emo('Head')}"><span class="{emo('SrOnly')}">Actions</span></th>
          </tr>
        </thead>
        <tbody class="{emo('Group')}">
          {group_row('Ready to ship', len(ready))}{rows_by_group['ready']}
        </tbody>
        <tbody class="{emo('Group')}">
          {group_row('Awaiting stock', len(waiting))}{rows_by_group['awaiting']}
        </tbody>
      </table>
    </div>
    <p id="awaiting-note" class="{emo('Muted')}">Orders awaiting stock can be shipped once all lines are allocated.</p>
  </div>
  <div class="{emo('MobileList')}" style="display:none" aria-hidden="true">{''.join(cards)}
  </div>
  <div class="{emo('MobileBulkBar')}" hidden>{bulk.replace('{mark}', '')}</div>
</main>
<footer class="{emo('Footer')}">Packwise 3.0 &middot; <a href="/help">Help centre</a> &middot; <a href="/status">Status</a></footer>
"""
        return page("Fulfil orders – Packwise", body, css="body{margin:0;font-family:Inter,Arial,sans-serif;background:#f6f7f9}", lang="en-GB")

    emit("table-04",
         title="Order fulfilment queue with carrier selects and ship/print-label actions",
         mutations=["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change",
                    "testid-change", "copy-change", "attribute-churn", "structure-move", "insertion"],
         notes=("v1 renders each row's carrier picker as a <pw-carrier-picker> web component with a declarative shadow root; "
                "v2 (emotion CSS-in-JS) flattens it to a light-DOM <select> with regenerated id/name and reworded options, "
                "moves the app header into a <pw-app-header> shadow root, splits the queue into 'Ready to ship' / 'Awaiting "
                "stock' tbodies sorted by a new 'Ship by' column, reorders Destination/Items, turns 'Print label' into an "
                "icon-only button, renames 'Ship' to 'Mark as shipped', moves the bulk buttons into a bulk-action bar, and adds "
                "a hidden mobile card list plus a hidden mobile bulk bar that duplicate every action. The table id survives, so "
                "positional selectors now hit the wrong order."),
         targets=targets, v1=v1, v2=v2)


# ========================================================================================
# table-05 — Server inventory (Fleetdeck)  ·  v2: <table> -> ARIA div grid inside a shadow root
# ========================================================================================
SRV05 = [
    # id, hostname, status, environment, region, private ip, os, size, uptime, public ip
    ("srv-0101", "api-gw-01.fra1", "Running", "production", "fra1", "10.24.1.11", "Ubuntu 24.04 LTS", "8 vCPU · 32 GB", "41d 6h", "203.0.113.21"),
    ("srv-0102", "api-gw-02.fra1", "Running", "production", "fra1", "10.24.1.12", "Ubuntu 24.04 LTS", "8 vCPU · 32 GB", "41d 6h", "203.0.113.22"),
    ("srv-0188", "prod-api-07.fra1", "Running", "production", "fra1", "10.24.2.37", "Ubuntu 22.04 LTS", "16 vCPU · 64 GB", "12d 3h", ""),
    ("srv-0412", "cache-redis-03.fra1", "Degraded", "production", "fra1", "10.24.3.19", "Debian 12", "4 vCPU · 32 GB", "3d 22h", ""),
    ("srv-0193", "db-pg-primary-02.ams3", "Running", "production", "ams3", "10.31.0.21", "Rocky Linux 9.4", "32 vCPU · 256 GB", "97d 14h", ""),
    ("srv-0194", "db-pg-replica-04.ams3", "Running", "production", "ams3", "10.31.0.24", "Rocky Linux 9.4", "32 vCPU · 256 GB", "97d 14h", ""),
    ("srv-0520", "etl-worker-02.ams3", "Stopped", "staging", "ams3", "10.31.4.8", "Ubuntu 22.04 LTS", "8 vCPU · 32 GB", "", ""),
    ("srv-0230", "k8s-cp-01.lon1", "Running", "production", "lon1", "10.40.0.10", "Flatcar 4081.2", "4 vCPU · 16 GB", "63d 1h", ""),
    ("srv-0377", "k8s-worker-14.sfo2", "Running", "production", "sfo2", "10.52.6.114", "Flatcar 4081.2", "16 vCPU · 64 GB", "8d 19h", ""),
    ("srv-0261", "web-edge-11.lon1", "Running", "production", "lon1", "10.40.3.21", "Debian 12", "2 vCPU · 4 GB", "22d 7h", "198.51.100.11"),
    ("srv-0262", "web-edge-12.lon1", "Degraded", "production", "lon1", "10.40.3.22", "Debian 12", "2 vCPU · 4 GB", "0d 4h", "198.51.100.12"),
    ("srv-0145", "search-os-01.fra1", "Running", "production", "fra1", "10.24.5.41", "Ubuntu 24.04 LTS", "16 vCPU · 128 GB", "30d 2h", ""),
    ("srv-0610", "ci-runner-05.sfo2", "Running", "tooling", "sfo2", "10.52.9.15", "Ubuntu 24.04 LTS", "8 vCPU · 16 GB", "1d 11h", ""),
    ("srv-0007", "vpn-gw-01.lon1", "Running", "tooling", "lon1", "10.40.9.2", "OpenBSD 7.6", "2 vCPU · 2 GB", "211d 9h", "198.51.100.2"),
    ("srv-0533", "staging-api-02.ams3", "Running", "staging", "ams3", "10.31.2.12", "Ubuntu 24.04 LTS", "4 vCPU · 16 GB", "5d 0h", ""),
    ("srv-0301", "mq-rabbit-02.fra1", "Maintenance", "production", "fra1", "10.24.6.12", "Debian 12", "8 vCPU · 32 GB", "", ""),
    ("srv-0640", "metrics-prom-01.sfo2", "Running", "tooling", "sfo2", "10.52.8.30", "Ubuntu 22.04 LTS", "8 vCPU · 64 GB", "44d 18h", ""),
    ("srv-0641", "log-loki-02.sfo2", "Running", "tooling", "sfo2", "10.52.8.42", "Ubuntu 22.04 LTS", "8 vCPU · 64 GB", "44d 18h", ""),
    ("srv-0090", "backup-01.ams3", "Running", "tooling", "ams3", "10.31.9.5", "Debian 12", "4 vCPU · 16 GB", "120d 3h", ""),
    ("srv-0702", "ml-gpu-03.sfo2", "Running", "research", "sfo2", "10.52.12.63", "Ubuntu 22.04 LTS", "32 vCPU · 256 GB · A100", "2d 8h", ""),
    ("srv-0815", "dev-sandbox-09.lon1", "Stopped", "development", "lon1", "10.40.12.9", "Fedora 40", "2 vCPU · 8 GB", "", ""),
    ("srv-0003", "bastion-01.fra1", "Running", "tooling", "fra1", "10.24.0.5", "Debian 12", "1 vCPU · 2 GB", "180d 0h", "203.0.113.5"),
]
REGIONS05 = {"ams3": "Amsterdam", "fra1": "Frankfurt", "lon1": "London", "sfo2": "San Francisco"}
DOT05 = {"Running": "ok", "Degraded": "warn", "Stopped": "off", "Maintenance": "maint"}

CSS05_V1 = """
body{margin:0;font:13px/1.45 "Roboto",Arial,sans-serif;color:#202124;background:#f1f3f4}
.console{display:grid;grid-template-columns:220px 1fr;min-height:100vh}
.console-nav{background:#263238;color:#cfd8dc;padding:16px 0}.console-brand{display:block;color:#fff;font-weight:700;font-size:17px;padding:0 18px 12px;text-decoration:none}
.project-switch{margin:0 12px 12px;width:calc(100% - 24px)}
.console-nav a.nav-item{display:block;padding:8px 18px;color:#cfd8dc;text-decoration:none}.console-nav a.nav-item.is-active{background:#37474f;color:#fff;border-left:3px solid #4fc3f7}
.console-top{display:flex;align-items:center;gap:16px;height:48px;padding:0 20px;background:#fff;border-bottom:1px solid #dadce0}
.global-search{margin-left:auto;width:320px;padding:6px 10px;border:1px solid #dadce0;border-radius:4px}
.servers{padding:20px}.servers-head{display:flex;align-items:center;justify-content:space-between}
.count-pill{font-size:12px;background:#e8eaed;border-radius:10px;padding:2px 8px;vertical-align:middle}
.env-filter{display:flex;gap:4px;margin:12px 0}.env-filter a{padding:4px 10px;border-radius:4px;color:#3c4043;text-decoration:none}.env-filter a.is-active{background:#e8f0fe;color:#1967d2}
.btn{padding:6px 12px;border:1px solid #dadce0;background:#fff;border-radius:4px;cursor:pointer}.btn-primary{background:#1a73e8;border-color:#1a73e8;color:#fff}
.inv-table{width:100%;border-collapse:collapse;background:#fff;box-shadow:0 1px 2px rgba(60,64,67,.3)}
.inv-table th{text-align:left;font-weight:500;color:#5f6368;padding:8px 10px;border-bottom:1px solid #dadce0;white-space:nowrap}
.inv-table td{padding:7px 10px;border-bottom:1px solid #f1f3f4;white-space:nowrap}.mono{font-family:"Roboto Mono",monospace}
.status-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}.status-dot--ok{background:#1e8e3e}.status-dot--warn{background:#f9ab00}.status-dot--off{background:#9aa0a6}.status-dot--maint{background:#4285f4}
.env-tag{font-size:11px;padding:1px 6px;border-radius:3px;background:#e8eaed}.env-tag--production{background:#fce8e6;color:#c5221f}
.act{border:1px solid transparent;background:none;padding:3px 8px;border-radius:4px;cursor:pointer;color:#1a73e8}.act:hover{background:#f1f3f4}.act:disabled{color:#9aa0a6}
.pager{display:flex;justify-content:flex-end;gap:12px;padding:10px;color:#5f6368}
.console-footer{padding:12px 20px;color:#5f6368;font-size:12px}
"""


@suite
def table_05():
    pos = {s[1]: i for i, s in enumerate(SRV05, 1)}
    sid = {s[1]: s[0] for s in SRV05}
    targets = [
        dict(id="t1", key="reboot:db-pg-primary-02.ams3",
             description="'Reboot' action of server db-pg-primary-02.ams3 (v2: 'Restart')",
             css=f".inv-table tbody tr:nth-child({pos['db-pg-primary-02.ams3']}) button.act-reboot",
             xpath="//tr[td[2]='db-pg-primary-02.ams3']//button[normalize-space()='Reboot']",
             mutations=["tag-change", "shadow-dom", "copy-change", "class-obfuscation", "sibling-reorder", "decoy"]),
        dict(id="t2", key="status:cache-redis-03.fra1",
             description="Status cell of server cache-redis-03.fra1 (value 'Degraded')",
             css=f"tr#{sid['cache-redis-03.fra1']} td.col-status",
             xpath=f"//tr[@id='{sid['cache-redis-03.fra1']}']/td[3]",
             mutations=["tag-change", "shadow-dom", "sibling-reorder", "id-change", "class-obfuscation", "decoy"]),
        dict(id="t3", key="ip:web-edge-11.lon1",
             description="IP-address cell of server web-edge-11.lon1 (10.40.3.21; v2 column 'Private IP')",
             css=f".inv-table > tbody > tr:nth-child({pos['web-edge-11.lon1']}) > td:nth-child(6)",
             xpath="//a[.='web-edge-11.lon1']/../../td[6]",
             mutations=["tag-change", "shadow-dom", "sibling-reorder", "insertion", "copy-change", "class-obfuscation"]),
        dict(id="t4", key="check:prod-api-07.fra1",
             description="Row-selection checkbox of server prod-api-07.fra1",
             css=f"input[type='checkbox'][value='{sid['prod-api-07.fra1']}']",
             xpath=f"//tbody/tr[{pos['prod-api-07.fra1']}]/td[1]/input",
             mutations=["tag-change", "shadow-dom", "sibling-reorder", "attribute-churn", "wrapper-divs"]),
        dict(id="t5", key="head:uptime",
             description="'Uptime' column header of the server grid",
             css=".inv-table thead th:nth-child(9)",
             xpath="//th[normalize-space()='Uptime']",
             mutations=["tag-change", "shadow-dom", "sibling-reorder", "insertion", "class-obfuscation", "decoy"]),
        dict(id="t6", key="console:k8s-worker-14.sfo2",
             description="Icon-only 'Open web console' button of server k8s-worker-14.sfo2",
             css="tr[data-host='k8s-worker-14.sfo2'] .act-console",
             xpath=f"(//table[contains(@class,'inv-table')]//button[@title='Open web console'])[{pos['k8s-worker-14.sfo2']}]",
             mutations=["tag-change", "shadow-dom", "attribute-churn", "copy-change", "sibling-reorder", "class-obfuscation"]),
    ]

    def v1(M):
        rows = []
        for srv, host, status, env, region, ip, os_, size, uptime, _pub in SRV05:
            stopped = status == "Stopped"
            rows.append(f"""
            <tr id="{srv}" data-host="{host}" class="inv-row">
              <td class="td-check"><input type="checkbox" name="server" value="{srv}" aria-label="Select {host}"{M('check:' + host)}></td>
              <td class="col-host"><a href="/servers/{srv}" class="host-link">{host}</a></td>
              <td class="col-status"{M('status:' + host)}><span class="status-dot status-dot--{DOT05[status]}" aria-hidden="true"></span>{status}</td>
              <td class="col-env"><span class="env-tag env-tag--{env}">{env}</span></td>
              <td class="col-region">{region}</td>
              <td class="col-ip mono"{M('ip:' + host)}>{ip}</td>
              <td class="col-os">{esc(os_)}</td>
              <td class="col-size">{esc(size)}</td>
              <td class="col-uptime">{uptime or '&mdash;'}</td>
              <td class="col-actions"><button type="button" class="act act-console" title="Open web console"{' disabled' if stopped else ''}{M('console:' + host)}>{icon('terminal')}</button><button type="button" class="act act-reboot"{' disabled' if stopped else ''}{M('reboot:' + host)}>Reboot</button><button type="button" class="act act-more" aria-label="More actions">{icon('dots-v')}</button></td>
            </tr>""")
        nav = ["Overview", "Servers", "Clusters", "Load balancers", "Networks", "Volumes", "Alerts", "Audit log"]
        nav_html = "".join(f'<a class="nav-item{" is-active" if n == "Servers" else ""}" href="/corvid-prod/{slug(n)}">{n}</a>' for n in nav)
        body = f"""
<div class="console">
  <aside class="console-nav">
    <a class="console-brand" href="/">Fleetdeck</a>
    <select class="project-switch" aria-label="Project"><option selected>corvid-prod</option><option>corvid-staging</option><option>corvid-research</option></select>
    <nav aria-label="Resources">{nav_html}</nav>
  </aside>
  <div class="console-main">
    <header class="console-top">
      <div class="breadcrumb"><a href="/corvid-prod">corvid-prod</a> / Servers</div>
      <input type="search" class="global-search" placeholder="Search resources (Ctrl+K)" aria-label="Search resources">
      <a class="account" href="/account">Mira Sato</a>
    </header>
    <section class="servers">
      <div class="servers-head">
        <h1>Servers <span class="count-pill">142</span></h1>
        <div class="servers-actions"><button type="button" class="btn" id="btn-refresh">Refresh</button> <button type="button" class="btn btn-primary" id="btn-add-server">Add server</button></div>
      </div>
      <div class="env-filter" role="tablist"><a class="is-active" href="?env=all">All (142)</a><a href="?env=production">Production (88)</a><a href="?env=staging">Staging (21)</a><a href="?env=tooling">Tooling (24)</a><a href="?env=development">Development (9)</a></div>
      <table class="inv-table">
        <thead>
          <tr>
            <th class="th-check"><input type="checkbox" aria-label="Select all servers"></th>
            <th>Hostname</th>
            <th>Status</th>
            <th>Environment</th>
            <th>Region</th>
            <th>IP address</th>
            <th>OS</th>
            <th>Size</th>
            <th{M('head:uptime')}>Uptime</th>
            <th class="th-actions">Actions</th>
          </tr>
        </thead>
        <tbody>{''.join(rows)}
        </tbody>
      </table>
      <div class="pager"><span>1&ndash;{len(SRV05)} of 142</span><button type="button" class="btn" disabled>Previous</button><button type="button" class="btn">Next</button></div>
    </section>
    <footer class="console-footer">Fleetdeck 2024.11 &middot; Region data refreshed every 60 s &middot; <a href="/docs">Docs</a></footer>
  </div>
</div>
"""
        return page("Servers – corvid-prod – Fleetdeck", body, css=CSS05_V1)

    def v2(M):
        cols = ["Name", "Region", "Status", "Private IP", "Public IP", "Env", "Image", "Size", "Uptime", ""]
        hdr = []
        for i, c in enumerate(cols, 2):
            if not c:
                hdr.append(f'<div role="columnheader" aria-colindex="{i}" class="{ve("hcell")} {ve("hcell-actions")}"><span class="{ve("sr")}">Actions</span></div>')
                continue
            sort = ' aria-sort="ascending"' if c == "Name" else ' aria-sort="none"'
            mark = M("head:uptime") if c == "Uptime" else ""
            hdr.append(f'<div role="columnheader" aria-colindex="{i}"{sort} tabindex="-1" class="{ve("hcell")}"{mark}><span class="{ve("hlabel")}">{c}</span><button type="button" class="{ve("hmenu")}" aria-label="Column menu" tabindex="-1">{icon("dots-v")}</button></div>')
        body_rows, ri = [], 2
        for region in sorted(REGIONS05):
            group = sorted((s for s in SRV05 if s[4] == region), key=lambda s: s[1])
            body_rows.append(f'<div role="row" aria-rowindex="{ri}" class="{ve("group-row")}"><div role="gridcell" aria-colspan="11" class="{ve("group-cell")}">{icon("chev-down")}<strong>{region}</strong> &middot; {REGIONS05[region]} <span class="{ve("muted")}">{len(group)} servers</span></div></div>')
            ri += 1
            for srv, host, status, env, reg, ip, os_, size, uptime, pub in group:
                stopped = status == "Stopped"
                cell = lambda k, inner, extra="": f'<div role="gridcell" aria-colindex="{k}" class="{ve("cell")}"{extra}>{inner}</div>'  # noqa: E731
                body_rows.append(f"""
          <div role="row" aria-rowindex="{ri}" aria-selected="false" data-rowid="{_hash(srv, 10, _B36)}" class="{ve('row')}">
            {cell(1, f'<input type="checkbox" class="{ve("cbx")}" aria-label="Select row"{M("check:" + host)}>')}
            {cell(2, f'<a class="{ve("name")}" href="/p/corvid-prod/servers/{_hash(srv, 10, _B36)}">{host}</a>')}
            {cell(3, reg)}
            {cell(4, f'<span class="{ve("dot-" + DOT05[status])}" aria-hidden="true"></span>{status}', M('status:' + host))}
            {cell(5, f'<code class="{ve("mono")}">{ip}</code>', M('ip:' + host))}
            {cell(6, f'<code class="{ve("mono")}">{pub}</code>' if pub else '&mdash;')}
            {cell(7, f'<span class="{ve("env-" + env)}">{env[:4] if env == "production" else env}</span>')}
            {cell(8, esc(os_))}
            {cell(9, esc(size))}
            {cell(10, uptime or '&mdash;')}
            {cell(11, f'<div class="{ve("actions")}"><button type="button" class="{ve("icon-btn")}" aria-label="Console"{" disabled" if stopped else ""}{M("console:" + host)}>{icon("terminal")}</button><button type="button" class="{ve("btn")}"{" disabled" if stopped else ""}{M("reboot:" + host)}>{icon("restart")}Restart</button><button type="button" class="{ve("icon-btn")}" aria-label="More" aria-haspopup="menu">{icon("dots")}</button></div>')}
          </div>""")
                ri += 1
        colmenu = "".join(f'<div role="menuitemcheckbox" aria-checked="true" class="{ve("menu-item")}">{c}</div>' for c in cols if c)
        attention = "".join(
            f'<li class="{ve("att-item")}"><a href="/p/corvid-prod/servers/{_hash(s[0], 10, _B36)}">{s[1]}</a><span class="{ve("att-status")}">{s[2]}</span><button type="button" class="{ve("btn-sm")}">Restart</button></li>'
            for s in SRV05 if s[2] == "Degraded")
        grid_css = (":host{display:block;font:13px/1.4 Inter,sans-serif;--line:#e5e7eb}[role=grid]{display:grid;border:1px solid var(--line);border-radius:8px;overflow:auto}"
                    "[role=row]{display:grid;grid-template-columns:40px 220px 70px 120px 120px 120px 90px 150px 170px 90px 150px;border-bottom:1px solid var(--line)}"
                    "[role=gridcell],[role=columnheader]{padding:8px 10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}")
        body = f"""
<header class="{ve('topbar')}">
  <a class="{ve('logo')}" href="/">Fleetdeck</a>
  <button type="button" class="{ve('project')}" aria-haspopup="listbox">corvid-prod{icon('chev-down')}</button>
  <nav class="{ve('tabs')}" aria-label="Resources"><a href="/p/corvid-prod/servers" aria-current="page">Servers</a><a href="/p/corvid-prod/clusters">Clusters</a><a href="/p/corvid-prod/networks">Networks</a><a href="/p/corvid-prod/volumes">Volumes</a><a href="/p/corvid-prod/load-balancers">Load balancers</a><a href="/p/corvid-prod/alerts">Alerts</a><a href="/p/corvid-prod">Overview</a></nav>
  <button type="button" class="{ve('cmdk')}">{icon('search')}<span>Search</span><kbd>Ctrl K</kbd></button>
  <button type="button" class="{ve('avatar')}" aria-label="Account">MS</button>
</header>
<main class="{ve('main')}">
  <div class="{ve('head')}">
    <h1 class="{ve('title')}">Servers</h1><span class="{ve('count')}">142 total &middot; 88 production</span>
    <div class="{ve('head-actions')}"><button type="button" class="{ve('btn')}">{icon('restart')}Refresh</button><button type="button" class="{ve('btn-primary')}">{icon('plus')}Create server</button></div>
  </div>
  <aside class="{ve('attention')}" aria-label="Needs attention"><h2 class="{ve('att-title')}">{icon('info')}Needs attention</h2><ul class="{ve('att-list')}">{attention}</ul></aside>
  <div class="{ve('filters')}"><button type="button" class="{ve('chip-active')}">All environments</button><button type="button" class="{ve('chip')}">production</button><button type="button" class="{ve('chip')}">staging</button><button type="button" class="{ve('chip')}">tooling</button><button type="button" class="{ve('chip')}">Group by: Region{icon('chev-down')}</button></div>
  <fd-server-grid project="corvid-prod" page-size="25">
    <template shadowrootmode="open">
      <style>{grid_css}</style>
      <div class="{ve('toolbar')}"><span class="{ve('muted')}">{len(SRV05)} of 142 rows</span><button type="button" class="{ve('btn')}" aria-haspopup="menu">Columns</button><div role="menu" class="{ve('menu')}" hidden>{colmenu}</div><button type="button" class="{ve('btn')}">Density</button><button type="button" class="{ve('btn')}">{icon('download')}Export CSV</button></div>
      <div role="grid" aria-label="Servers" aria-rowcount="143" aria-colcount="11" aria-multiselectable="true" class="{ve('grid')}">
        <div role="rowgroup" class="{ve('header')}">
          <div role="row" aria-rowindex="1" class="{ve('header-row')}">
            <div role="columnheader" aria-colindex="1" class="{ve('hcell')}"><input type="checkbox" class="{ve('cbx')}" aria-label="Select all rows"></div>
            {''.join(hdr)}
          </div>
        </div>
        <div role="rowgroup" class="{ve('body')}">{''.join(body_rows)}
        </div>
      </div>
      <div class="{ve('pager')}"><span>Rows per page: 25</span><span>1&ndash;{len(SRV05)} of 142</span><button type="button" class="{ve('icon-btn')}" aria-label="Previous page" disabled>{icon('chev-left')}</button><button type="button" class="{ve('icon-btn')}" aria-label="Next page">{icon('chev-right')}</button></div>
    </template>
  </fd-server-grid>
</main>
<footer class="{ve('footer')}">Fleetdeck 2025.10 &middot; <a href="/docs">Docs</a> &middot; <a href="/status">Status</a></footer>
"""
        return page("Servers · corvid-prod · Fleetdeck", body, css="body{margin:0;background:#fafafa;color:#111827;font-family:Inter,sans-serif}")

    emit("table-05",
         title="Server inventory data grid (table migrated to an ARIA div grid)",
         mutations=["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change",
                    "copy-change", "tag-change", "attribute-churn", "structure-move", "insertion"],
         notes=("v2 replaces the <table> with a vanilla-extract styled ARIA grid (role=grid/row/gridcell/columnheader divs) "
                "rendered inside an <fd-server-grid> declarative shadow root; rows are grouped by region (group rows inserted) "
                "and sorted by name, columns are reordered and renamed (Hostname->Name, IP address->Private IP, OS->Image) with a "
                "Public IP column inserted, Reboot becomes Restart, the console button loses its title, row ids/values are "
                "replaced by opaque data-rowid hashes, and a hidden column-visibility menu plus a light-DOM 'Needs attention' "
                "list repeat column names, statuses and Restart actions."),
         targets=targets, v1=v1, v2=v2)


# ========================================================================================
# table-06 — League standings (Touchline sport)  ·  v2: atomic CSS, columns moved, zone separators
# ========================================================================================
TEAMS06 = [
    ("Kingsport United", 1.62), ("Riverside Rovers", 1.50), ("Ashford Athletic", 1.42), ("Northgate City", 1.37),
    ("Bayview Celtic", 1.30), ("Eastbrook Wanderers", 1.24), ("Harrowfield FC", 1.18), ("Westcliff Albion", 1.12),
    ("Stonebridge Rangers", 1.10), ("Millbrook Town", 1.05), ("Oakham Forest", 1.01), ("Fairhaven Orient", 0.98),
    ("Thornbury Villa", 0.95), ("Castleford Park", 0.92), ("Redmoor County", 0.90), ("Elmstead Borough", 0.86),
    ("Lakeside Athletic", 0.83), ("Port Ellis Dynamo", 0.80), ("Granton Swifts", 0.76), ("Whitby Hollow", 0.72),
]
SCORERS06 = [("Tomasz Wilk", "Kingsport United", 11), ("Jamal Okonjo", "Bayview Celtic", 9), ("Lucas Ferreira", "Riverside Rovers", 8),
             ("Callum Bright", "Ashford Athletic", 8), ("Eoin Gallagher", "Stonebridge Rangers", 7), ("Mats Lindgren", "Northgate City", 6),
             ("Ryo Takeda", "Bayview Celtic", 6), ("Kofi Mensah", "Harrowfield FC", 5)]


def _poisson(rnd, lam):
    import math
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rnd.random()
        if p <= limit:
            return k
        k += 1


def _season06():
    rnd = random.Random(1783)  # seed chosen so the table tracks club strength plausibly
    names = [t for t, _ in TEAMS06]
    strength = dict(TEAMS06)
    arr = list(range(len(names)))
    rnd.shuffle(arr)
    results = {n: [] for n in names}
    fixtures = []
    for rnd_no in range(13):
        pairs = []
        for i in range(len(arr) // 2):
            a, b = arr[i], arr[-1 - i]
            home, away = (a, b) if (rnd_no + i) % 2 == 0 else (b, a)
            pairs.append((names[home], names[away]))
        if rnd_no == 12:
            fixtures = pairs
        else:
            for hn, an in pairs:
                gh = _poisson(rnd, 1.30 * strength[hn] / strength[an] ** 0.9)
                ga = _poisson(rnd, 1.00 * strength[an] / strength[hn] ** 0.9)
                results[hn].append((an, gh, ga, "H"))
                results[an].append((hn, ga, gh, "A"))
        arr = [arr[0], arr[-1]] + arr[1:-1]
    nxt = {}
    for hn, an in fixtures:
        nxt[hn] = (an, "H")
        nxt[an] = (hn, "A")
    table = []
    for n in names:
        res = results[n]
        w = sum(f > a for _, f, a, _ in res)
        d = sum(f == a for _, f, a, _ in res)
        gf, ga = sum(r[1] for r in res), sum(r[2] for r in res)
        table.append(dict(name=n, p=len(res), w=w, d=d, l=len(res) - w - d, gf=gf, ga=ga, gd=gf - ga, pts=3 * w + d,
                          form=res[-5:], next=nxt[n]))
    table.sort(key=lambda t: (-t["pts"], -t["gd"], -t["gf"], t["name"]))
    for i, t in enumerate(table, 1):
        t["pos"] = i
    return table


def _zone06(pos):
    return "cl" if pos <= 4 else "cc" if pos == 5 else "rel" if pos >= 18 else ""


CSS06_V1 = """
body{margin:0;font:15px/1.5 Georgia,"Times New Roman",serif;color:#141414;background:#fff}
.site-header{border-bottom:4px solid #c8102e}.masthead{display:flex;align-items:center;gap:24px;padding:10px 24px;background:#141414}
.logo{color:#fff;font:700 24px/1 Arial,sans-serif;text-decoration:none;letter-spacing:-.5px}.sport-nav a,.section-nav a{font-family:Arial,sans-serif;text-decoration:none}
.sport-nav a{color:#bbb;margin-right:14px;font-size:13px}.sport-nav a.is-current{color:#fff}.signin{margin-left:auto;color:#fff;font:13px Arial,sans-serif}
.section-nav{padding:8px 24px;background:#f4f4f4}.section-nav a{color:#141414;margin-right:18px;font-size:14px}.section-nav a.is-current{color:#c8102e;font-weight:700}
.page{display:grid;grid-template-columns:1fr 300px;gap:32px;max-width:1200px;margin:0 auto;padding:20px 24px}
.league-tabs{display:flex;gap:2px;border-bottom:1px solid #ddd;font-family:Arial,sans-serif}.league-tab{padding:8px 14px;color:#444;text-decoration:none;font-size:14px}.league-tab.is-active{border-bottom:3px solid #c8102e;color:#141414;font-weight:700}
.table-controls{display:flex;justify-content:space-between;align-items:center;margin:12px 0;font-family:Arial,sans-serif}
.view-btn{border:1px solid #ccc;background:#fff;padding:4px 12px;font-size:13px}.view-btn.is-active{background:#141414;color:#fff;border-color:#141414}
.standings{width:100%;border-collapse:collapse;font:14px Arial,sans-serif}.standings th{font-size:12px;color:#666;font-weight:400;padding:6px;border-bottom:2px solid #141414;text-align:center}
.standings td{padding:7px 6px;border-bottom:1px solid #e6e6e6;text-align:center}.standings td.team,.standings th.team{text-align:left}
.standings .pts{font-weight:700}.crest{vertical-align:middle;margin-right:8px}
.zone-cl td.pos{box-shadow:inset 4px 0 #1d70b8}.zone-cc td.pos{box-shadow:inset 4px 0 #00a499}.zone-rel td.pos{box-shadow:inset 4px 0 #c8102e}
.result{display:inline-block;width:20px;height:20px;line-height:20px;border-radius:50%;color:#fff;font-size:11px;margin:0 1px}.result--w{background:#00843d}.result--d{background:#888}.result--l{background:#c8102e}
.legend{list-style:none;padding:0;font:13px Arial,sans-serif;color:#555}.swatch{display:inline-block;width:10px;height:10px;margin-right:6px}
.side h2{font:700 16px Arial,sans-serif;border-bottom:2px solid #141414;padding-bottom:4px}.scorers{width:100%;font:14px Arial,sans-serif;border-collapse:collapse}.scorers td{padding:5px 4px;border-bottom:1px solid #eee}
.visually-hidden{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.site-footer{background:#141414;color:#bbb;padding:24px;font:13px Arial,sans-serif}.site-footer a{color:#ddd;margin-right:12px}
"""


@suite
def table_06():
    table = _season06()
    by = {t["name"]: t for t in table}
    fav = "Stonebridge Rangers"
    targets = [
        dict(id="t1", key="pts:Stonebridge Rangers",
             description=f"Points cell of Stonebridge Rangers in the league table (value '{by[fav]['pts']}')",
             css=f"#league-table tbody tr:nth-child({by[fav]['pos']}) td.pts",
             xpath=f"//table[@id='league-table']/tbody/tr[{by[fav]['pos']}]/td[10]",
             mutations=["sibling-reorder", "insertion", "class-obfuscation", "decoy"]),
        dict(id="t2", key="link:Bayview Celtic",
             description="Team link 'Bayview Celtic' inside the league table",
             css="#league-table a[href='/teams/bayview-celtic']",
             xpath="//table[@id='league-table']//a[normalize-space()='Bayview Celtic']",
             mutations=["attribute-churn", "class-obfuscation", "wrapper-divs", "decoy"]),
        dict(id="t3", key="form:Ashford Athletic",
             description="Form-guide cell (last five results) of Ashford Athletic",
             css=f"#league-table > tbody > tr:nth-child({by['Ashford Athletic']['pos']}) > td.form",
             xpath="//a[.='Ashford Athletic']/ancestor::tr/td[last()]",
             mutations=["sibling-reorder", "insertion", "class-obfuscation", "attribute-churn"]),
        dict(id="t4", key="head:gd",
             description="'GD' (goal difference) column header of the league table (v2 shows '+/−')",
             css="#league-table thead th.gd",
             xpath="//thead/tr/th[abbr[@title='Goal difference']]",
             mutations=["copy-change", "sibling-reorder", "class-obfuscation", "decoy"]),
        dict(id="t5", key="tab:championship",
             description="'Championship' league tab above the table",
             css=".league-tabs a[href='/football/tables/championship']",
             xpath="//nav[contains(@class,'league-tabs')]/a[2]",
             mutations=["sibling-reorder", "attribute-churn", "class-obfuscation", "decoy"]),
        dict(id="t6", key="view:away",
             description="'Away' view toggle of the league table",
             css=".view-toggle button[data-view='away']",
             xpath="//div[@aria-label='Table view']/button[3]",
             mutations=["sibling-reorder", "insertion", "attribute-churn", "class-obfuscation", "wrapper-divs"]),
    ]
    leagues = [("premier-division", "Premier Division"), ("championship", "Championship"), ("league-one", "League One"),
               ("womens-premier", "Women's Premier"), ("coastal-cup", "Coastal Cup")]

    def form_title(r):
        opp, f, a, venue = r
        res = "W" if f > a else "D" if f == a else "L"
        return res, f"{res} {f}&ndash;{a} v {esc(opp)} ({venue})"

    def v1(M):
        rows = []
        for t in table:
            n = t["name"]
            z = _zone06(t["pos"])
            form = "".join(f'<span class="result result--{r.lower()}" title="{tt}">{r}</span>' for r, tt in map(form_title, t["form"]))
            rows.append(f"""
        <tr{f' class="zone-{z}"' if z else ''}>
          <td class="pos">{t['pos']}</td>
          <td class="team"><img class="crest" src="/img/crests/{slug(n)}.png" alt="" width="20" height="20"><a href="/teams/{slug(n)}"{M('link:' + n)}>{esc(n)}</a></td>
          <td>{t['p']}</td><td>{t['w']}</td><td>{t['d']}</td><td>{t['l']}</td><td>{t['gf']}</td><td>{t['ga']}</td>
          <td class="gd">{signed(t['gd'], '{:d}') if t['gd'] else '0'}</td>
          <td class="pts"{M('pts:' + n)}>{t['pts']}</td>
          <td class="form"{M('form:' + n)}>{form}</td>
        </tr>""")
        tabs = "".join(
            f'<a href="/football/tables/{k}" class="league-tab{" is-active" if i == 0 else ""}"{CUR if i == 0 else ""}{M("tab:" + k)}>{esc(v)}</a>'
            for i, (k, v) in enumerate(leagues))
        scorers = "".join(f"<tr><td>{i}</td><td>{esc(p)}</td><td>{esc(c)}</td><td>{g}</td></tr>" for i, (p, c, g) in enumerate(SCORERS06, 1))
        body = f"""
<header class="site-header">
  <div class="masthead">
    <a class="logo" href="/">Touchline</a>
    <nav class="sport-nav" aria-label="Sports"><a class="is-current" href="/football">Football</a><a href="/rugby">Rugby</a><a href="/cricket">Cricket</a><a href="/tennis">Tennis</a><a href="/golf">Golf</a><a href="/cycling">Cycling</a></nav>
    <a class="signin" href="/signin">Sign in</a>
  </div>
  <nav class="section-nav" aria-label="Football"><a href="/football">News</a><a href="/football/scores-fixtures">Scores &amp; Fixtures</a><a class="is-current" href="/football/tables">Tables</a><a href="/football/transfers">Transfers</a><a href="/football/video">Video</a><a href="/fantasy">Fantasy</a></nav>
</header>
<div class="page">
  <main>
    <h1>Coastal Premier Division table</h1>
    <p class="standfirst">2025/26 season &middot; updated after Saturday's matches (matchday 12)</p>
    <nav class="league-tabs" aria-label="Competitions">{tabs}</nav>
    <div class="table-controls">
      <label>Season <select name="season"><option selected>2025/26</option><option>2024/25</option><option>2023/24</option></select></label>
      <div class="view-toggle" role="group" aria-label="Table view"><button type="button" class="view-btn is-active" data-view="all" aria-pressed="true">All</button><button type="button" class="view-btn" data-view="home" aria-pressed="false">Home</button><button type="button" class="view-btn" data-view="away" aria-pressed="false"{M('view:away')}>Away</button></div>
    </div>
    <table class="standings" id="league-table">
      <caption class="visually-hidden">Coastal Premier Division table, 2025/26</caption>
      <thead>
        <tr>
          <th scope="col" class="pos"><abbr title="Position">Pos</abbr></th>
          <th scope="col" class="team">Team</th>
          <th scope="col"><abbr title="Played">P</abbr></th>
          <th scope="col"><abbr title="Won">W</abbr></th>
          <th scope="col"><abbr title="Drawn">D</abbr></th>
          <th scope="col"><abbr title="Lost">L</abbr></th>
          <th scope="col"><abbr title="Goals for">F</abbr></th>
          <th scope="col"><abbr title="Goals against">A</abbr></th>
          <th scope="col" class="gd"{M('head:gd')}><abbr title="Goal difference">GD</abbr></th>
          <th scope="col" class="pts"><abbr title="Points">Pts</abbr></th>
          <th scope="col" class="form">Form</th>
        </tr>
      </thead>
      <tbody>{''.join(rows)}
      </tbody>
    </table>
    <ul class="legend">
      <li><span class="swatch" style="background:#1d70b8"></span>Atlantic Champions Cup group stage</li>
      <li><span class="swatch" style="background:#00a499"></span>Atlantic Conference play-off</li>
      <li><span class="swatch" style="background:#c8102e"></span>Relegation</li>
    </ul>
  </main>
  <aside class="side">
    <h2>Top scorers</h2>
    <table class="scorers"><tbody>{scorers}</tbody></table>
    <h2>Most read</h2>
    <ol class="most-read"><li><a href="/football/news/1">Kingsport stretch lead with late winner at Millbrook</a></li><li><a href="/football/news/2">Whitby Hollow part company with head coach</a></li><li><a href="/football/news/3">Bayview Celtic striker Okonjo called up for national team</a></li></ol>
  </aside>
</div>
<footer class="site-footer">
  <nav aria-label="Competitions"><a href="/football/tables/premier-division">Premier Division</a><a href="/football/tables/championship">Championship</a><a href="/football/tables/league-one">League One</a><a href="/football/tables/womens-premier">Women's Premier</a></nav>
  <p>&copy; 2025 Touchline Media Ltd. Data provided by Statline.</p>
</footer>
"""
        return page("Coastal Premier Division table 2025/26 – Touchline", body, css=CSS06_V1, lang="en-GB")

    def v2(M):
        cls_cell = ax("padding:8px 6px", "text-align:center", "border-bottom:1px solid #eceef1")
        cls_num = ax("padding:8px 6px", "text-align:center", "border-bottom:1px solid #eceef1", "font-variant-numeric:tabular-nums")
        cls_pts = ax("padding:8px 6px", "text-align:center", "font-weight:800", "background:#f6f7f9")
        cls_th = ax("font-size:12px", "font-weight:600", "color:#6b7280", "padding:10px 6px", "text-align:center")
        rows, zone_prev = [], None
        for t in table:
            n = t["name"]
            z = _zone06(t["pos"])
            if zone_prev is not None and z != zone_prev and (zone_prev or z):
                rows.append(f'\n          <tr aria-hidden="true" class="{ax("height:4px", "background:#fff")}"><td colspan="12" class="{ax("padding:0", "border-top:2px dashed #d1d5db")}"></td></tr>')
            zone_prev = z
            form = "".join(
                f'<abbr class="{ax("display:inline-grid", "width:18px", "border-radius:4px", "font-weight:700", "color:#fff", "bg:" + r)}" title="{tt}">{r}</abbr>'
                for r, tt in map(form_title, t["form"]))
            opp, venue = t["next"]
            rows.append(f"""
          <tr class="{ax("height:44px", "zone:" + (z or 'none'))}">
            <td class="{cls_cell}"><span class="{ax("font-weight:700")}">{t['pos']}</span></td>
            <td class="{ax("padding:8px 6px", "text-align:left", "border-bottom:1px solid #eceef1")}"><a class="{ax("display:flex", "align-items:center", "gap:8px", "color:inherit")}" href="/football/clubs/{slug(n)}/overview"{M('link:' + n)}><img class="{ax("width:22px", "height:22px")}" src="https://img.touchline.example/crests/v2/{slug(n)}.svg" alt=""><span class="{ax("font-weight:600")}">{esc(n)}</span></a></td>
            <td class="{cls_num}">{t['p']}</td>
            <td class="{cls_pts}"{M('pts:' + n)}>{t['pts']}</td>
            <td class="{cls_num}">{t['w']}</td><td class="{cls_num}">{t['d']}</td><td class="{cls_num}">{t['l']}</td><td class="{cls_num}">{t['gf']}</td><td class="{cls_num}">{t['ga']}</td>
            <td class="{cls_num}">{signed(t['gd'], '{:d}') if t['gd'] else '0'}</td>
            <td class="{ax("padding:8px 6px", "white-space:nowrap", "border-bottom:1px solid #eceef1")}"{M('form:' + n)}>{form}</td>
            <td class="{cls_cell}"><a href="/football/clubs/{slug(opp)}/overview" title="Next: {esc(opp)} ({venue})"><img class="{ax("width:20px", "height:20px")}" src="https://img.touchline.example/crests/v2/{slug(opp)}.svg" alt="{esc(opp)}"></a></td>
          </tr>""")
        order = [0, 3, 1, 2, 4]  # Women's Premier promoted to second tab
        tabs = "".join(
            f'<a role="tab" aria-selected="{"true" if i == 0 else "false"}" href="/football/{leagues[i][0]}/table" class="{ax("padding:10px 14px", "border-radius:999px", "active" if i == 0 else "idle")}"{M("tab:" + leagues[i][0])}>{esc(leagues[i][1])}</a>'
            for i in order)
        me = by[fav]
        myclub_css = (":host{display:block;margin-bottom:16px}.card{border:1px solid #e5e7eb;border-radius:12px;padding:12px 16px}"
                      "table{width:100%;border-collapse:collapse;font:14px Inter,sans-serif}th{font-size:12px;color:#6b7280;font-weight:600}td,th{padding:6px;text-align:center}")
        scorers = "".join(
            f'<tr><td>{i}</td><td>{esc(p)}</td><td><a href="/football/clubs/{slug(c)}/overview">{esc(c)}</a></td><td>{g}</td></tr>'
            for i, (p, c, g) in enumerate(SCORERS06, 1))
        clubs = "".join(f'<li><a href="/football/clubs/{slug(n)}/overview">{esc(n)}</a></li>' for n in sorted(by))
        body = f"""
<header class="{ax("display:flex", "align-items:center", "gap:24px", "padding:0 24px", "height:60px", "background:#0b1f3a")}">
  <a class="{ax("color:#fff", "font-weight:900", "font-size:22px")}" href="/">Touchline</a>
  <nav class="{ax("display:flex", "gap:4px")}" aria-label="Football"><a href="/football/scores">Scores</a><a href="/football/tables" aria-current="page">Tables</a><a href="/football">News</a><a href="/football/transfers">Transfers</a><a href="/football/video">Video</a><a href="/fantasy">Fantasy</a></nav>
  <a class="{ax("margin-left:auto", "color:#fff")}" href="/account/login">Log in</a>
</header>
<div class="{ax("background:#c8102e", "color:#fff", "padding:8px 24px", "font-weight:600")}" role="status"><span class="{ax("text-transform:uppercase", "font-size:11px")}">Live</span> Riverside Rovers 1&ndash;0 Northgate City &middot; 63&prime; <a href="/football/live/rrv-ngc">Follow live</a></div>
<div class="{ax("display:grid", "grid-template-columns:1fr 320px", "gap:32px", "max-width:1240px", "margin:0 auto", "padding:24px")}">
  <main>
    <h1 class="{ax("font-size:28px", "font-weight:800")}">Coastal Premier Division</h1>
    <p class="{ax("color:#6b7280")}">Table &middot; 2025/26 &middot; after matchday 12</p>
    <tl-my-club club="{slug(fav)}">
      <template shadowrootmode="open">
        <style>{myclub_css}</style>
        <section class="card" aria-label="Your club">
          <h2>Your club</h2>
          <table>
            <thead><tr><th scope="col"><abbr title="Position">Pos</abbr></th><th scope="col">Club</th><th scope="col"><abbr title="Played">P</abbr></th><th scope="col"><abbr title="Goal difference">GD</abbr></th><th scope="col"><abbr title="Points">Pts</abbr></th></tr></thead>
            <tbody><tr><td>{me['pos']}</td><td><a href="/football/clubs/{slug(fav)}/overview">{esc(fav)}</a></td><td>{me['p']}</td><td>{signed(me['gd'], '{:d}') if me['gd'] else '0'}</td><td>{me['pts']}</td></tr></tbody>
          </table>
          <a href="/account/favourites">Change club</a>
        </section>
      </template>
    </tl-my-club>
    <div class="{ax("display:flex", "justify-content:space-between", "align-items:center", "gap:16px", "flex-wrap:wrap")}">
      <div role="tablist" aria-label="Competitions" class="{ax("display:flex", "gap:6px", "overflow-x:auto")}">{tabs}</div>
      <div class="{ax("display:flex", "gap:8px")}">
        <select class="{ax("border:1px solid #d1d5db", "border-radius:8px")}" aria-label="Season"><option selected>2025/26</option><option>2024/25</option><option>2023/24</option></select>
        <div role="radiogroup" aria-label="Table view" class="{ax("display:inline-flex", "border-radius:999px", "background:#f3f4f6")}">
          <button type="button" role="radio" aria-checked="true" class="{ax("seg", "active")}">Overall</button><button type="button" role="radio" aria-checked="false" class="{ax("seg")}">Form</button><button type="button" role="radio" aria-checked="false" class="{ax("seg")}">Home</button><button type="button" role="radio" aria-checked="false" class="{ax("seg")}"{M('view:away')}>Away</button>
        </div>
      </div>
    </div>
    <div class="{ax("overflow-x:auto", "margin-top:12px")}">
      <table id="league-table" class="{ax("width:100%", "border-collapse:collapse", "font-size:14px")}">
        <caption class="{ax("sr-only")}">Coastal Premier Division table 2025/26</caption>
        <thead>
          <tr>
            <th scope="col" class="{cls_th}"><abbr title="Position">#</abbr></th>
            <th scope="col" class="{cls_th} {ax("text-align:left")}">Club</th>
            <th scope="col" class="{cls_th}"><abbr title="Played">P</abbr></th>
            <th scope="col" class="{cls_th}"><abbr title="Points">Pts</abbr></th>
            <th scope="col" class="{cls_th}"><abbr title="Won">W</abbr></th>
            <th scope="col" class="{cls_th}"><abbr title="Drawn">D</abbr></th>
            <th scope="col" class="{cls_th}"><abbr title="Lost">L</abbr></th>
            <th scope="col" class="{cls_th}"><abbr title="Goals for">GF</abbr></th>
            <th scope="col" class="{cls_th}"><abbr title="Goals against">GA</abbr></th>
            <th scope="col" class="{cls_th}"{M('head:gd')}><abbr title="Goal difference">+/&minus;</abbr></th>
            <th scope="col" class="{cls_th}">Form</th>
            <th scope="col" class="{cls_th}">Next</th>
          </tr>
        </thead>
        <tbody>{''.join(rows)}
        </tbody>
      </table>
    </div>
    <ul class="{ax("display:flex", "gap:16px", "font-size:13px", "color:#4b5563")}"><li>Atlantic Champions Cup</li><li>Conference play-off</li><li>Relegation</li></ul>
  </main>
  <aside>
    <section aria-labelledby="ts-h"><h2 id="ts-h" class="{ax("font-size:16px", "font-weight:800")}">Top scorers</h2>
      <table class="{ax("width:100%", "font-size:14px")}"><thead><tr><th scope="col">#</th><th scope="col">Player</th><th scope="col">Club</th><th scope="col">Goals</th></tr></thead><tbody>{scorers}</tbody></table>
    </section>
  </aside>
</div>
<footer class="{ax("background:#0b1f3a", "color:#cbd5e1", "padding:32px 24px")}">
  <h2 class="{ax("font-size:14px")}">Clubs</h2>
  <ul class="{ax("display:grid", "grid-template-columns:repeat(4,1fr)", "gap:6px")}">{clubs}</ul>
  <nav aria-label="Competitions"><a href="/football/premier-division/table">Premier Division</a> <a href="/football/championship/table">Championship</a> <a href="/football/league-one/table">League One</a> <a href="/football/womens-premier/table">Women's Premier</a></nav>
  <p>&copy; 2025 Touchline Media Ltd.</p>
</footer>
"""
        return page("Coastal Premier Division table | Touchline", body, css="body{margin:0;font-family:Inter,system-ui,sans-serif;color:#111827}", lang="en-GB")

    emit("table-06",
         title="Football league standings with zones and form guide",
         mutations=["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "copy-change",
                    "attribute-churn", "insertion"],
         notes=("v2 swaps semantic classes for atomic (StyleX-like) classes, moves Pts next to P, renames GD to '+/−' and "
                "appends a 'Next' fixture column (so the form guide is no longer the last cell), inserts aria-hidden zone "
                "separator rows, reorders the competition tabs and the view toggle (Overall/Form/Home/Away), changes club URLs, "
                "and adds a 'Your club' summary table in a <tl-my-club> shadow root plus club links in the top-scorers table "
                "and footer. The table keeps id='league-table', so positional selectors resolve to wrong cells."),
         targets=targets, v1=v1, v2=v2)


# ========================================================================================
# table-07 — Product inventory with inline edits (Stockroom)  ·  v2: Tailwind + input web components
# ========================================================================================
PROD07 = [
    # product id, name, variant, sku, price, on hand, status, committed, dirty field
    (8811, "Ethiopia Yirgacheffe", "250 g · Whole bean", "EO-ETH-YIR-250", 16.50, 142, "Active", 8, ""),
    (8812, "Ethiopia Yirgacheffe", "1 kg · Whole bean", "EO-ETH-YIR-1K", 54.00, 38, "Active", 2, ""),
    (8813, "Colombia Huila Supremo", "250 g · Whole bean", "EO-COL-HUI-250", 14.00, 96, "Active", 5, ""),
    (8814, "Colombia Huila Supremo", "1 kg · Whole bean", "EO-COL-HUI-1K", 46.00, 21, "Active", 1, "price"),
    (8817, "Kenya Nyeri AA", "250 g · Whole bean", "EO-KEN-NYE-250", 18.50, 12, "Active", 3, ""),
    (8820, "Guatemala Antigua", "250 g · Whole bean", "EO-GUA-ANT-250", 15.00, 74, "Active", 4, ""),
    (8823, "Ember Espresso Blend", "250 g · Whole bean", "EO-ESP-BLD-250", 13.50, 210, "Active", 14, ""),
    (8824, "Ember Espresso Blend", "1 kg · Whole bean", "EO-ESP-BLD-1K", 44.00, 58, "Active", 6, "stock"),
    (8826, "Decaf Swiss Water Peru", "250 g · Whole bean", "EO-DEC-PER-250", 15.50, 9, "Active", 1, ""),
    (8829, "Cold Brew Coarse Grind", "500 g · Coarse", "EO-CBR-CRS-500", 19.00, 0, "Active", 0, ""),
    (8840, "Hand Grinder", "Steel burr", "EO-GRD-HND-01", 89.00, 17, "Active", 2, ""),
    (8841, "Pour-over Kettle 1 L", "Matte black", "EO-KTL-GSN-1L", 72.00, 6, "Active", 1, ""),
    (8843, "Chemex 6-cup", "Glass handle", "EO-CMX-6CP", 49.00, 3, "Active", 1, ""),
    (8845, "Enamel Mug 350 ml", "Ember red", "EO-MUG-ENM-RD", 18.00, 64, "Active", 3, ""),
    (8850, "Seasonal Holiday Blend", "250 g · Whole bean", "EO-HOL-BLD-250", 16.00, 120, "Draft", 0, ""),
    (8852, "Gift Box: Tasting Trio", "3 × 100 g", "EO-GFT-TRIO", 34.00, 25, "Draft", 0, ""),
]


def _stock_flag07(stock):
    return "Out of stock" if stock == 0 else "Low stock" if stock <= 12 else ""


CSS07_V1 = """
body{margin:0;font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#202223;background:#f1f2f4}
.topbar{display:flex;align-items:center;gap:20px;height:56px;padding:0 16px;background:#1a1a1a;color:#e3e3e3}
.topbar__logo{color:#fff;font-weight:700;text-decoration:none}.topbar__search{flex:0 1 480px;margin:0 auto;padding:6px 10px;border-radius:8px;border:1px solid #616161;background:#303030;color:#fff}
.shell{display:grid;grid-template-columns:240px 1fr}.sidenav{padding:12px 8px;background:#ebebeb;min-height:calc(100vh - 56px)}
.sidenav a{display:block;padding:6px 10px;border-radius:8px;color:#303030;text-decoration:none}.sidenav a.is-active{background:#fff;font-weight:650}.sidenav .sub{padding-left:28px;font-size:13px}
.content{padding:20px 28px}.content__head{display:flex;justify-content:space-between;align-items:center}
.button{display:inline-flex;align-items:center;padding:6px 12px;border-radius:8px;border:1px solid #c9cccf;background:#fff;color:#202223;font:inherit;cursor:pointer;text-decoration:none}
.button--primary{background:#303030;border-color:#303030;color:#fff}.button--plain{border-color:transparent;background:none;color:#005bd3}.button--small{padding:3px 8px;font-size:13px}.button:disabled{opacity:.45}
.inv-tabs{display:flex;gap:4px;margin:14px 0 0}.inv-tab{padding:6px 12px;border-radius:8px;color:#303030;text-decoration:none}.inv-tab.is-selected{background:#e3e3e3;font-weight:600}
.inv-filters{display:flex;gap:8px;padding:10px;background:#fff;border-radius:12px 12px 0 0;border-bottom:1px solid #e3e3e3}
.inv-table{width:100%;border-collapse:collapse;background:#fff}.inv-table th{text-align:left;font-weight:550;font-size:12px;color:#616161;padding:8px 10px;background:#f7f7f7}
.inv-table td{padding:8px 10px;border-top:1px solid #ebebeb;vertical-align:middle}.inv-thumb{border-radius:6px;border:1px solid #e3e3e3}
.inv-product-link{font-weight:600;color:#202223}.inv-variant{display:block;color:#616161;font-size:12px}
.inline-input{width:84px;padding:5px 8px;border:1px solid #8a8a8a;border-radius:8px;font:inherit}.inv-prefix{margin-right:4px;color:#616161}
.inv-row.is-dirty{background:#fff8db}.stock-badge{display:inline-block;margin-left:8px;padding:2px 8px;border-radius:8px;font-size:12px}
.stock-badge--low{background:#ffef9d;color:#4f4700}.stock-badge--out{background:#fedad9;color:#8e1f0b}
.status{padding:2px 8px;border-radius:8px;font-size:12px}.status--active{background:#cdfee1;color:#0c5132}.status--draft{background:#e3e3e3;color:#303030}
.unsaved-bar{display:flex;align-items:center;gap:12px;margin-top:12px;padding:10px 14px;border-radius:12px;background:#303030;color:#fff}
.visually-hidden{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.app-footer{padding:20px 28px;color:#616161;font-size:12px}
"""

MONEY07_CSS = (":host{display:inline-block}.field{display:flex;align-items:center;gap:4px;width:118px;height:34px;padding:0 8px;"
               "border:1px solid #d1d5db;border-radius:6px;background:#fff}.field:focus-within{outline:2px solid #4f46e5}"
               ".prefix,.suffix{color:#6b7280;font-size:12px}input{border:0;outline:0;width:100%;font:inherit;text-align:right}")
STEP07_CSS = (":host{display:inline-block}.wrap{display:inline-flex;align-items:center;height:34px;border:1px solid #d1d5db;border-radius:6px}"
              ".step{width:28px;height:100%;border:0;background:#f9fafb;color:#374151}input{width:56px;border:0;text-align:center;font:inherit}")


@suite
def table_07():
    pos = {p[3]: i for i, p in enumerate(PROD07, 1)}
    targets = [
        dict(id="t1", key="price:EO-ETH-YIR-250",
             description="Inline price input of SKU EO-ETH-YIR-250 (Ethiopia Yirgacheffe, 250 g)",
             css="#price-EO-ETH-YIR-250",
             xpath="//tr[td[3]='EO-ETH-YIR-250']//input[@name='price']",
             mutations=["shadow-dom", "id-change", "attribute-churn", "wrapper-divs", "sibling-reorder", "class-obfuscation"]),
        dict(id="t2", key="stock:EO-GRD-HND-01",
             description="Inline stock-quantity input of SKU EO-GRD-HND-01 (Hand Grinder) — v2 column 'On hand'",
             css=f"#inventory tbody tr:nth-child({pos['EO-GRD-HND-01']}) input.inline-input--stock",
             xpath="//input[@name='stock'][ancestor::tr/@data-sku='EO-GRD-HND-01']",
             mutations=["shadow-dom", "copy-change", "attribute-churn", "wrapper-divs", "sibling-reorder", "insertion", "class-obfuscation"]),
        dict(id="t3", key="save:EO-COL-HUI-1K",
             description="Per-row 'Save' button of the edited row EO-COL-HUI-1K (Colombia Huila Supremo, 1 kg)",
             css="tr[data-sku='EO-COL-HUI-1K'] button[data-testid='save-row']",
             xpath=f"//table[@id='inventory']/tbody/tr[{pos['EO-COL-HUI-1K']}]/td[last()]/button[1]",
             mutations=["testid-change", "sibling-reorder", "class-obfuscation", "attribute-churn", "decoy"]),
        dict(id="t4", key="badge:EO-CMX-6CP",
             description="'Low stock' badge in the Chemex 6-cup row (EO-CMX-6CP)",
             css=f"#inventory tbody tr:nth-child({pos['EO-CMX-6CP']}) .stock-badge",
             xpath="//tr[@data-sku='EO-CMX-6CP']//span[normalize-space()='Low stock']",
             mutations=["structure-move", "sibling-reorder", "class-obfuscation", "attribute-churn", "decoy"]),
        dict(id="t5", key="link:EO-KEN-NYE-250",
             description="Product-name link 'Kenya Nyeri AA' in the inventory table",
             css="a.inv-product-link[href='/admin/products/8817']",
             xpath="//a[normalize-space()='Kenya Nyeri AA']",
             mutations=["attribute-churn", "class-obfuscation", "sibling-reorder", "decoy"]),
        dict(id="t6", key="reset:EO-ESP-BLD-1K",
             description="Per-row 'Reset' (discard edits) button of the edited row EO-ESP-BLD-1K (Ember Espresso Blend, 1 kg)",
             css=f"#inventory tbody tr:nth-child({pos['EO-ESP-BLD-1K']}) [data-testid='reset-row']",
             xpath="//tr[td[3]='EO-ESP-BLD-1K']//button[normalize-space()='Reset']",
             mutations=["copy-change", "testid-change", "attribute-churn", "class-obfuscation", "sibling-reorder"]),
    ]

    def v1(M):
        rows = []
        for pid, name, variant, sku, price, stock, status, _com, dirty in PROD07:
            flag = _stock_flag07(stock)
            badge = (f'<span class="stock-badge stock-badge--{"out" if stock == 0 else "low"}"{M("badge:" + sku)}>{flag}</span>' if flag else "")
            dis = "" if dirty else " disabled"
            label = f"{name} {variant.split(' · ')[0]}"
            rows.append(f"""
          <tr data-sku="{sku}" class="inv-row{' is-dirty' if dirty else ''}">
            <td class="inv-col-img"><img src="/media/products/{pid}-thumb.jpg" alt="" width="40" height="40" class="inv-thumb"></td>
            <td class="inv-col-product"><a href="/admin/products/{pid}" class="inv-product-link"{M('link:' + sku)}>{esc(name)}</a><span class="inv-variant">{esc(variant)}</span></td>
            <td class="inv-col-sku">{sku}</td>
            <td class="inv-col-price"><span class="inv-prefix">$</span><input type="number" step="0.01" min="0" name="price" id="price-{sku}" class="inline-input inline-input--price" value="{price:.2f}" aria-label="Price for {esc(label)}"{M('price:' + sku)}></td>
            <td class="inv-col-stock"><input type="number" step="1" min="0" name="stock" id="stock-{sku}" class="inline-input inline-input--stock" value="{stock}" aria-label="Stock for {esc(label)}"{M('stock:' + sku)}>{badge}</td>
            <td class="inv-col-status"><span class="status status--{status.lower()}">{status}</span></td>
            <td class="inv-col-actions"><button type="button" class="button button--small button--primary" data-testid="save-row"{dis}{M('save:' + sku)}>Save</button> <button type="button" class="button button--small button--plain" data-testid="reset-row"{dis}{M('reset:' + sku)}>Reset</button></td>
          </tr>""")
        low = sum(1 for p in PROD07 if _stock_flag07(p[5]) == "Low stock")
        out = sum(1 for p in PROD07 if p[5] == 0)
        drafts = sum(1 for p in PROD07 if p[6] == "Draft")
        body = f"""
<header class="topbar">
  <a class="topbar__logo" href="/admin">Stockroom</a>
  <span class="topbar__store">Ember &amp; Oak Coffee Roasters</span>
  <input class="topbar__search" type="search" placeholder="Search products, orders and customers" aria-label="Search admin">
  <span class="topbar__user">Nadia Prescott</span>
</header>
<div class="shell">
  <nav class="sidenav" aria-label="Admin">
    <a href="/admin">Home</a>
    <a href="/admin/orders">Orders <span class="count">12</span></a>
    <a href="/admin/products">Products</a>
    <a class="sub" href="/admin/products">All products</a>
    <a class="sub is-active" href="/admin/products/inventory" aria-current="page">Inventory</a>
    <a class="sub" href="/admin/collections">Collections</a>
    <a class="sub" href="/admin/gift-cards">Gift cards</a>
    <a href="/admin/customers">Customers</a>
    <a href="/admin/analytics">Analytics</a>
    <a href="/admin/discounts">Discounts</a>
    <a href="/admin/settings">Settings</a>
  </nav>
  <main class="content">
    <div class="content__head">
      <h1>Inventory</h1>
      <div class="content__actions"><button type="button" class="button">Export</button> <button type="button" class="button">Import</button> <a class="button button--primary" href="/admin/products/new">Add product</a></div>
    </div>
    <div class="unsaved-bar" role="status"><span>2 unsaved changes</span><button type="button" class="button button--plain">Discard all</button><button type="button" class="button button--primary">Save all</button></div>
    <div class="inv-tabs" role="tablist"><a class="inv-tab is-selected" href="?view=all" aria-current="page">All</a><a class="inv-tab" href="?view=low">Low stock ({low})</a><a class="inv-tab" href="?view=out">Out of stock ({out})</a><a class="inv-tab" href="?view=draft">Drafts ({drafts})</a></div>
    <div class="inv-filters">
      <input type="search" class="inv-filter-input" placeholder="Filter products" aria-label="Filter products">
      <select aria-label="Product type"><option>All product types</option><option>Coffee</option><option>Equipment</option><option>Merchandise</option></select>
      <select aria-label="Location"><option selected>Bristol roastery</option><option>Leeds warehouse</option></select>
    </div>
    <table class="inv-table" id="inventory">
      <thead>
        <tr>
          <th class="inv-col-img"><span class="visually-hidden">Image</span></th>
          <th>Product</th>
          <th>SKU</th>
          <th>Price</th>
          <th>Stock</th>
          <th>Status</th>
          <th class="inv-col-actions"><span class="visually-hidden">Actions</span></th>
        </tr>
      </thead>
      <tbody>{''.join(rows)}
      </tbody>
    </table>
  </main>
</div>
<footer class="app-footer">Stockroom &middot; Learn more about <a href="/help/inventory">managing inventory</a></footer>
"""
        return page("Inventory · Ember & Oak · Stockroom", body, css=CSS07_V1)

    def v2(M):
        order = sorted(PROD07, key=lambda p: (p[5] - p[7], p[3]))  # sorted by Available, lowest first
        td = "px-3 py-3 text-sm whitespace-nowrap text-gray-700"
        rows = []
        for pid, name, variant, sku, price, stock, status, com, dirty in order:
            flag = _stock_flag07(stock)
            avail = stock - com
            badge = ""
            if flag:
                tone = "bg-red-50 text-red-700 ring-red-600/10" if stock == 0 else "bg-amber-50 text-amber-800 ring-amber-600/20"
                badge = f'<span class="ml-2 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset {tone}"{M("badge:" + sku)}>{flag}</span>'
            dis = "" if dirty else " disabled"
            vid = 41800 + pid % 100 * 7
            rows.append(f"""
              <tr class="{'bg-amber-50/60' if dirty else 'hover:bg-gray-50'}">
                <td class="relative w-12 px-4"><input type="checkbox" class="size-4 rounded border-gray-300 text-indigo-600" aria-label="Select {esc(name)} – {esc(variant.split(' · ')[0])}"></td>
                <td class="py-3 pr-3 text-sm"><div class="flex items-center gap-3"><img class="size-10 rounded-md object-cover ring-1 ring-gray-200" src="https://cdn.stockroom.example/s/ember-oak/{pid}/thumb_80.webp" alt=""><div class="min-w-0"><a href="/store/ember-oak/products/{pid}/variants/{vid}" class="font-medium text-gray-900 hover:underline"{M('link:' + sku)}>{esc(name)}</a><p class="truncate text-xs text-gray-500">{esc(variant)} &middot; <span class="font-mono">{sku}</span></p></div></div></td>
                <td class="{td} tabular-nums"><span class="font-semibold text-gray-900">{avail}</span>{badge}</td>
                <td class="{td}"><sr-stepper value="{stock}" min="0" label="On hand"><template shadowrootmode="open"><style>{STEP07_CSS}</style><div class="wrap"><button class="step" type="button" aria-label="Decrease" tabindex="-1">{icon('minus', size=14)}</button><input type="text" inputmode="numeric" part="input" value="{stock}" aria-label="On hand quantity"{M('stock:' + sku)}><button class="step" type="button" aria-label="Increase" tabindex="-1">{icon('plus', size=14)}</button></div></template></sr-stepper></td>
                <td class="{td} tabular-nums text-gray-500">{com}</td>
                <td class="{td}"><sr-money-field currency="USD" value="{price:.2f}"><template shadowrootmode="open"><style>{MONEY07_CSS}</style><label class="field"><span class="prefix">$</span><input type="text" inputmode="decimal" part="input" value="{price:.2f}" aria-label="Price" autocomplete="off"{M('price:' + sku)}><span class="suffix">USD</span></label></template></sr-money-field></td>
                <td class="{td}"><span class="inline-flex items-center rounded-md px-2 py-1 text-xs font-medium {'bg-green-50 text-green-700' if status == 'Active' else 'bg-gray-100 text-gray-600'}">{status}</span></td>
                <td class="py-3 pr-4 pl-3 text-right text-sm whitespace-nowrap"><button type="button" class="rounded-md bg-indigo-600 px-2.5 py-1.5 text-sm font-semibold text-white shadow-xs hover:bg-indigo-500 disabled:opacity-40"{dis}{M('save:' + sku)}>Save</button><button type="button" class="ml-1 rounded-md p-1.5 text-gray-400 hover:text-gray-600 disabled:opacity-40" aria-label="Discard changes" title="Discard changes"{dis}{M('reset:' + sku)}>{icon('undo')}</button></td>
              </tr>""")
        lows = [p for p in PROD07 if _stock_flag07(p[5]) == "Low stock"]
        alert_items = "".join(
            f'<li class="flex items-center justify-between py-2"><a href="/store/ember-oak/products/{p[0]}" class="text-sm font-medium text-amber-900 hover:underline">{esc(p[1])}</a><span class="text-sm text-amber-800">{p[5]} left</span></li>'
            for p in lows)
        side_nav = "".join(
            f'<a href="/store/ember-oak/{slug(n)}" class="group flex gap-x-3 rounded-md p-2 text-sm font-semibold {"bg-gray-100 text-indigo-600" if n == "Inventory" else "text-gray-700 hover:bg-gray-50"}"{CUR if n == "Inventory" else ""}>{n}</a>'
            for n in ["Home", "Orders", "Products", "Inventory", "Collections", "Customers", "Discounts", "Analytics", "Settings"])
        body = f"""
<div class="min-h-full">
  <header class="sticky top-0 z-40 flex h-14 items-center gap-x-4 border-b border-gray-200 bg-white px-4 shadow-xs sm:gap-x-6 sm:px-6">
    <a href="/store/ember-oak" class="flex items-center gap-2 font-bold text-gray-900"><svg class="size-7 text-indigo-600" viewBox="0 0 28 28" aria-hidden="true"><rect width="28" height="28" rx="7" fill="currentColor"/></svg>Stockroom</a>
    <button type="button" class="inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm text-gray-700 hover:bg-gray-50">Ember &amp; Oak Coffee Roasters{icon('chev-down', cls='size-4')}</button>
    <form class="grid flex-1 grid-cols-1" action="/store/ember-oak/search" method="GET"><input type="search" name="q" aria-label="Search" class="col-start-1 row-start-1 block size-full bg-white pl-8 text-base text-gray-900 outline-hidden placeholder:text-gray-400 sm:text-sm/6" placeholder="Search">{icon('search', cls='pointer-events-none col-start-1 row-start-1 size-5 self-center text-gray-400')}</form>
    <button type="button" class="-m-2.5 p-2.5 text-gray-400 hover:text-gray-500"><span class="sr-only">View notifications</span>{icon('bell', cls='size-6')}</button>
    <span class="text-sm font-semibold text-gray-900">Nadia Prescott</span>
  </header>
  <div class="flex">
    <nav class="hidden w-60 shrink-0 border-r border-gray-200 bg-white p-4 lg:block" aria-label="Store">{side_nav}</nav>
    <main class="flex-1 px-4 py-8 sm:px-6 lg:px-8">
      <div class="sticky top-14 z-30 -mx-4 mb-6 flex items-center justify-between bg-gray-900 px-4 py-3 text-white sm:-mx-6 lg:-mx-8" role="region" aria-label="Unsaved changes">
        <p class="text-sm font-medium">2 unsaved changes</p>
        <div class="flex gap-2"><button type="button" class="rounded-md px-3 py-1.5 text-sm font-semibold text-white ring-1 ring-white/30">Discard</button><button type="button" class="rounded-md bg-white px-3 py-1.5 text-sm font-semibold text-gray-900">Save</button></div>
      </div>
      <div class="md:flex md:items-center md:justify-between">
        <div class="min-w-0 flex-1"><h1 class="text-2xl/7 font-bold text-gray-900 sm:truncate sm:text-3xl sm:tracking-tight">Inventory</h1><p class="mt-1 text-sm text-gray-500">Location: <button type="button" class="font-medium text-indigo-600">Bristol roastery</button></p></div>
        <div class="mt-4 flex gap-x-3 md:mt-0 md:ml-4"><button type="button" class="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-xs ring-1 ring-gray-300 ring-inset hover:bg-gray-50">Import</button><button type="button" class="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-xs ring-1 ring-gray-300 ring-inset hover:bg-gray-50">Export</button><button type="button" class="inline-flex items-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-xs hover:bg-indigo-700">Add product</button></div>
      </div>
      <section class="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-4" aria-labelledby="low-stock-h">
        <div class="flex items-center gap-2">{icon('info', cls='size-5 text-amber-500')}<h2 id="low-stock-h" class="text-sm font-semibold text-amber-900">{len(lows)} products are running low</h2></div>
        <ul class="mt-2 divide-y divide-amber-200/70">{alert_items}</ul>
      </section>
      <div class="mt-6 border-b border-gray-200"><nav class="-mb-px flex gap-x-8" aria-label="Tabs"><a href="?status=all" class="border-b-2 border-indigo-500 px-1 py-3 text-sm font-medium text-indigo-600" aria-current="page">All</a><a href="?status=low" class="border-b-2 border-transparent px-1 py-3 text-sm font-medium text-gray-500">Low stock</a><a href="?status=out" class="border-b-2 border-transparent px-1 py-3 text-sm font-medium text-gray-500">Out of stock</a><a href="?status=draft" class="border-b-2 border-transparent px-1 py-3 text-sm font-medium text-gray-500">Draft</a></nav></div>
      <div class="mt-4 flow-root">
        <div class="-mx-4 -my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
          <div class="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
            <div class="overflow-hidden rounded-lg shadow-sm ring-1 ring-black/5">
              <table class="min-w-full divide-y divide-gray-200" id="inventory">
                <thead class="bg-gray-50">
                  <tr>
                    <th scope="col" class="relative w-12 px-4"><input type="checkbox" class="size-4 rounded border-gray-300" aria-label="Select all"></th>
                    <th scope="col" class="py-3 pr-3 text-left text-sm font-semibold text-gray-900">Product</th>
                    <th scope="col" class="px-3 py-3 text-left text-sm font-semibold text-gray-900" aria-sort="ascending">Available</th>
                    <th scope="col" class="px-3 py-3 text-left text-sm font-semibold text-gray-900">On hand</th>
                    <th scope="col" class="px-3 py-3 text-left text-sm font-semibold text-gray-900">Committed</th>
                    <th scope="col" class="px-3 py-3 text-left text-sm font-semibold text-gray-900">Price</th>
                    <th scope="col" class="px-3 py-3 text-left text-sm font-semibold text-gray-900">Status</th>
                    <th scope="col" class="relative py-3 pr-4 pl-3"><span class="sr-only">Actions</span></th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-200 bg-white">{''.join(rows)}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
  <div class="relative z-50 hidden" role="dialog" aria-modal="true" aria-label="Bulk edit">
    <div class="fixed inset-y-0 right-0 flex w-96 flex-col bg-white p-6 shadow-xl">
      <h2 class="text-base font-semibold text-gray-900">Bulk edit 0 variants</h2>
      <label class="mt-4 block text-sm font-medium text-gray-900">Price<sr-money-field currency="USD"><template shadowrootmode="open"><style>{MONEY07_CSS}</style><label class="field"><span class="prefix">$</span><input type="text" inputmode="decimal" part="input" aria-label="Price" autocomplete="off"><span class="suffix">USD</span></label></template></sr-money-field></label>
      <label class="mt-4 block text-sm font-medium text-gray-900">On hand<input type="text" inputmode="numeric" class="mt-2 block w-full rounded-md border-gray-300" aria-label="On hand quantity"></label>
      <div class="mt-6 flex justify-end gap-2"><button type="button" class="rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 ring-1 ring-gray-300">Cancel</button><button type="button" class="rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white">Save</button></div>
    </div>
  </div>
</div>
<footer class="border-t border-gray-200 px-8 py-6 text-xs text-gray-500">Stockroom &copy; 2025 &middot; <a href="/help/inventory" class="underline">Inventory help</a></footer>
"""
        return page("Inventory – Stockroom", body, css=CSS_TAILWIND, html_attrs='class="h-full bg-gray-50"', body_attrs='class="h-full"')

    emit("table-07",
         title="Product inventory table with inline price/stock editing and per-row save",
         mutations=["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change",
                    "testid-change", "copy-change", "attribute-churn", "structure-move", "insertion"],
         notes=("v2 is a Tailwind rewrite: price inputs move into <sr-money-field> and stock inputs into <sr-stepper> web "
                "components with declarative shadow roots (ids/names dropped), 'Stock' becomes 'On hand' with new 'Available' "
                "and 'Committed' columns, the SKU folds into the product cell, rows are re-sorted by Available, the Low-stock "
                "badge moves to the Available column, 'Reset' becomes an icon-only 'Discard changes' button, data-testids and "
                "data-sku disappear, and decoys are added: a sticky unsaved-changes bar (Save/Discard), a low-stock alert card "
                "linking the same product names first, and a hidden bulk-edit drawer with another Price field and Save button. "
                "The table id survives, so the positional Save XPath hits another product's Save."),
         targets=targets, v1=v1, v2=v2)


# ========================================================================================
# table-08 — Bank transaction ledger (Lindmoor Bank)  ·  v2: Vue scoped styles, day-grouped tbodies
# ========================================================================================
TXN08 = [
    # id, date, time, description, reference, category, paid out, paid in
    ("tx_7735", "2025-10-31", "07:02", "Halden Consulting Ltd", "SALARY OCT 2025", "Income", None, 2846.12),
    ("tx_7733", "2025-10-30", "18:42", "Tesco Stores 3214", "Contactless · card ending 4821", "Groceries", 48.37, None),
    ("tx_7731", "2025-10-30", "08:12", "TfL Travel Charge", "Contactless · card ending 4821", "Transport", 8.90, None),
    ("tx_7728", "2025-10-29", "21:15", "Amazon Marketplace", "AMZN Mktp UK*2K4L91", "Shopping", 42.99, None),
    ("tx_7726", "2025-10-28", "13:05", "Pret A Manger", "Contactless · card ending 4821", "Eating out", 6.45, None),
    ("tx_7725", "2025-10-28", "06:00", "Octopus Energy", "Direct debit · A-4F2C19", "Bills", 96.00, None),
    ("tx_7719", "2025-10-26", "09:30", "Transfer to Lindmoor Saver", "To account ••7710", "Transfers", 200.00, None),
    ("tx_7712", "2025-10-25", "17:58", "Sainsbury's", "Card payment · card ending 4821", "Groceries", 63.12, None),
    ("tx_7709", "2025-10-24", "11:20", "ASOS refund", "Refund · order 8812-0042", "Shopping", None, 34.00),
    ("tx_7704", "2025-10-23", "19:47", "Shell Petrol Station", "Card payment · card ending 4821", "Transport", 71.20, None),
    ("tx_7701", "2025-10-22", "06:00", "Thames Water", "Direct debit · 9001234567", "Bills", 38.50, None),
    ("tx_7690", "2025-10-20", "06:00", "Lambeth Council Tax", "Direct debit · 10023491", "Bills", 152.00, None),
    ("tx_7688", "2025-10-19", "06:00", "PureGym", "Direct debit · PG-883210", "Health & fitness", 24.99, None),
    ("tx_7684", "2025-10-18", "16:21", "Tesco Stores 3214", "Contactless · card ending 4821", "Groceries", 52.80, None),
    ("tx_7675", "2025-10-16", "09:00", "J Okonkwo — Rent", "Standing order · NOV RENT", "Housing", 1150.00, None),
]
CATS08 = ["Income", "Groceries", "Transport", "Shopping", "Bills", "Eating out", "Entertainment", "Transfers",
          "Health & fitness", "Housing", "General"]
EXPANDED08 = "tx_7712"
WEEKDAY08 = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _balances08():
    bal, out = 3214.77, {}
    for tid, *_rest, paid_out, paid_in in TXN08:  # newest first
        out[tid] = bal
        bal = bal + (paid_out or 0) - (paid_in or 0)
    return out


def _gbp(x):
    return f"£{x:,.2f}"


CSS08_V1 = """
body{margin:0;font:15px/1.5 Arial,Helvetica,sans-serif;color:#1d1d1b;background:#f3f1ee}
.bank-header{display:flex;align-items:center;gap:28px;padding:0 32px;height:64px;background:#00543c;color:#fff}
.bank-logo{color:#fff;font:700 21px Georgia,serif;text-decoration:none}.bank-nav a{color:#d6efe5;text-decoration:none;margin-right:18px}.bank-nav a.is-active{color:#fff;text-decoration:underline}
.bank-session{margin-left:auto;font-size:13px}.bank-session a{color:#fff}
.bank-main{max-width:1100px;margin:0 auto;padding:24px 32px}
.account-summary{background:#fff;border-radius:6px;padding:20px 24px;border-left:6px solid #00543c}.account-meta{color:#5f5f5f;margin:0}
.balances{display:flex;gap:48px;margin:12px 0 0}.balances dt{font-size:13px;color:#5f5f5f}.balances dd{margin:0;font-size:24px;font-weight:700}.balances .note{font-size:12px;font-weight:400;color:#5f5f5f}
.account-tabs{display:flex;gap:4px;margin:20px 0 0;border-bottom:2px solid #00543c}.account-tabs a{padding:8px 16px;color:#00543c;text-decoration:none}.account-tabs a.is-active{background:#00543c;color:#fff}
.ledger-filters{display:flex;flex-wrap:wrap;align-items:center;gap:12px;padding:14px 0}.ledger-filters input,.ledger-filters select{padding:6px 8px;border:1px solid #8c8c8c;border-radius:3px}
.btn{padding:6px 14px;border:1px solid #00543c;background:#00543c;color:#fff;border-radius:3px;cursor:pointer}.btn-link{background:none;border-color:transparent;color:#00543c;text-decoration:underline;padding:2px 4px}
.download-csv{color:#00543c;font-weight:700}
.ledger{width:100%;border-collapse:collapse;background:#fff}.ledger caption{text-align:left;padding:8px 0;color:#5f5f5f}
.ledger th{text-align:left;font-size:13px;padding:10px;border-bottom:2px solid #1d1d1b}.ledger td{padding:10px;border-bottom:1px solid #e3e0dc;vertical-align:top}
.num{text-align:right;font-variant-numeric:tabular-nums}.txn-ref{display:block;font-size:12px;color:#5f5f5f}.amount-in{color:#00703c}
.txn-category{padding:3px 6px;border:1px solid #b1b4b6;border-radius:3px;background:#fff}
.txn-toggle{border:0;background:none;color:#00543c;cursor:pointer}.txn-detail td{background:#f8f7f5}.txn-detail__facts{display:grid;grid-template-columns:160px 1fr;margin:0}
.visually-hidden{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.bank-footer{max-width:1100px;margin:0 auto;padding:16px 32px;font-size:12px;color:#5f5f5f}
"""


@suite
def table_08():
    bal = _balances08()
    targets = [
        dict(id="t1", key="toggle:tx_7733",
             description="Icon-only expand/collapse toggle of the 30 Oct 'Tesco Stores 3214' transaction (£48.37)",
             css="tr[data-txn-id='tx_7733'] button.txn-toggle",
             xpath="//tr[td[2][contains(.,'Tesco Stores 3214')]][1]//button[@aria-label='Show details']",
             mutations=["structure-move", "copy-change", "attribute-churn", "sibling-reorder", "class-obfuscation", "decoy"]),
        dict(id="t2", key="category:tx_7731",
             description="Category <select> of the 30 Oct 'TfL Travel Charge' transaction",
             css="#ledger tr[data-txn-id='tx_7731'] select.txn-category",
             xpath="//tr[contains(.,'TfL Travel Charge')]//select[@name='category']",
             mutations=["sibling-reorder", "insertion", "class-obfuscation", "id-change", "attribute-churn", "decoy"]),
        dict(id="t3", key="out:tx_7728",
             description="'Paid out' amount cell of the 29 Oct Amazon Marketplace transaction (£42.99)",
             css="#ledger tbody tr[data-txn-id='tx_7728'] td.amount-out",
             xpath="//tr[td[2]//span[.='AMZN Mktp UK*2K4L91']]/td[4]",
             mutations=["sibling-reorder", "copy-change", "class-obfuscation", "attribute-churn", "structure-move"]),
        dict(id="t4", key="dispute:tx_7712",
             description="'Dispute this transaction' button in the expanded detail row of the 25 Oct Sainsbury's payment (v2: 'Report a problem')",
             css="#txn-detail-tx_7712 .btn-dispute",
             xpath="//tr[@id='txn-detail-tx_7712']//button[normalize-space()='Dispute this transaction']",
             mutations=["copy-change", "id-change", "class-obfuscation", "wrapper-divs", "decoy"]),
        dict(id="t5", key="export",
             description="Download-as-CSV link of the transaction list (v2: 'Export CSV' in the ledger toolbar)",
             css="a.download-csv",
             xpath="//a[normalize-space()='Download (CSV)']",
             mutations=["shadow-dom", "copy-change", "class-obfuscation", "attribute-churn", "structure-move", "decoy"]),
        dict(id="t6", key="search",
             description="'Search transactions' text input above the ledger",
             css="#txn-search",
             xpath="//input[@placeholder='Search transactions']",
             mutations=["shadow-dom", "id-change", "copy-change", "wrapper-divs", "structure-move"]),
    ]

    def cat_options(selected, grouped=False):
        if not grouped:
            return "".join(f'<option{" selected" if c == selected else ""}>{esc(c)}</option>' for c in CATS08)
        groups = [("Spending", [c for c in CATS08 if c not in ("Income", "Transfers")]), ("Money in &amp; transfers", ["Income", "Transfers"])]
        return "".join(
            f'<optgroup label="{g}">' + "".join(f'<option value="{slug(c)}"{" selected" if c == selected else ""}>{esc(c)}</option>' for c in cs) + "</optgroup>"
            for g, cs in groups)

    def v1(M):
        rows = []
        for tid, d, t, desc, ref, cat, out, inn in TXN08:
            open_ = tid == EXPANDED08
            rows.append(f"""
        <tr class="txn" data-txn-id="{tid}">
          <td class="txn-date"><time datetime="{d}">{int(d[8:])} {MON[int(d[5:7]) - 1]}</time></td>
          <td class="txn-desc"><strong>{esc(desc)}</strong><span class="txn-ref">{esc(ref)}</span></td>
          <td class="txn-cat"><select class="txn-category" name="category" aria-label="Category for {esc(desc)}"{M('category:' + tid)}>{cat_options(cat)}</select></td>
          <td class="num amount-out"{M('out:' + tid)}>{_gbp(out) if out else ''}</td>
          <td class="num amount-in">{_gbp(inn) if inn else ''}</td>
          <td class="num balance">{_gbp(bal[tid])}</td>
          <td class="txn-expand"><button type="button" class="txn-toggle" aria-expanded="{'true' if open_ else 'false'}" aria-controls="txn-detail-{tid}" aria-label="{'Hide details' if open_ else 'Show details'}"{M('toggle:' + tid)}>{icon('chev-down' if open_ else 'chev-right')}</button></td>
        </tr>
        <tr class="txn-detail" id="txn-detail-{tid}"{'' if open_ else ' hidden'}>
          <td colspan="7"><div class="txn-detail__body"><dl class="txn-detail__facts"><dt>Date and time</dt><dd>{d_gb(d)}, {t}</dd><dt>Payment type</dt><dd>{esc(ref.split(' · ')[0])}</dd><dt>Transaction ID</dt><dd>{tid.upper()}</dd></dl><div class="txn-detail__actions"><button type="button" class="btn btn-link btn-note">Add a note</button><button type="button" class="btn btn-link btn-dispute"{M('dispute:' + tid)}>Dispute this transaction</button></div></div></td>
        </tr>""")
        body = f"""
<header class="bank-header">
  <a class="bank-logo" href="/">Lindmoor Bank</a>
  <nav class="bank-nav" aria-label="Main"><a class="is-active" href="/accounts">Accounts</a><a href="/payments">Payments &amp; transfers</a><a href="/cards">Cards</a><a href="/savings">Savings</a><a href="/help">Help</a></nav>
  <div class="bank-session">Last log in 2 Nov 2025, 19:04 &middot; <a href="/logout">Log out</a></div>
</header>
<main class="bank-main">
  <section class="account-summary">
    <h1>Everyday Current Account</h1>
    <p class="account-meta">Sort code 20-44-91 &middot; Account number ****4821</p>
    <dl class="balances"><div><dt>Balance</dt><dd>{_gbp(3214.77)}</dd></div><div><dt>Available to spend</dt><dd>{_gbp(3714.77)}</dd><dd class="note">includes {_gbp(500)} arranged overdraft</dd></div></dl>
  </section>
  <nav class="account-tabs" aria-label="Account"><a class="is-active" href="/accounts/4821/transactions" aria-current="page">Transactions</a><a href="/accounts/4821/statements">Statements</a><a href="/accounts/4821/standing-orders">Standing orders</a><a href="/accounts/4821/direct-debits">Direct debits</a><a href="/accounts/4821/details">Account details</a></nav>
  <form class="ledger-filters" role="search" action="/accounts/4821/transactions">
    <label for="txn-search">Search</label>
    <input id="txn-search" type="search" name="q" placeholder="Search transactions"{M('search')}>
    <label>Period <select name="period"><option selected>Last 30 days</option><option>This month</option><option>Last 3 months</option><option>Custom range&hellip;</option></select></label>
    <label>Category <select name="cat"><option selected>All categories</option>{cat_options('')}</select></label>
    <button type="submit" class="btn">Apply</button>
    <a class="download-csv" href="/accounts/4821/transactions.csv?period=30d"{M('export')}>Download (CSV)</a>
    <button type="button" class="btn btn-link">Print</button>
  </form>
  <table class="ledger" id="ledger">
    <caption>Transactions from 16 Oct to 31 Oct 2025</caption>
    <thead>
      <tr><th scope="col">Date</th><th scope="col">Description</th><th scope="col">Category</th><th scope="col" class="num">Paid out</th><th scope="col" class="num">Paid in</th><th scope="col" class="num">Balance</th><th scope="col"><span class="visually-hidden">Details</span></th></tr>
    </thead>
    <tbody>{''.join(rows)}
    </tbody>
  </table>
  <p class="ledger-note">Pending card payments are not shown until they are processed.</p>
</main>
<footer class="bank-footer">Lindmoor Bank plc is authorised by the Prudential Regulation Authority. Registered in England No. 0442118. &copy; 2025</footer>
"""
        return page("Transactions – Everyday Current Account – Lindmoor Bank", body, css=CSS08_V1, lang="en-GB")

    def v2(M):
        v = 'data-v-7c1e2a4b'
        days = {}
        for tx in TXN08:
            days.setdefault(tx[1], []).append(tx)
        bodies = []
        for d in sorted(days, reverse=True):
            txs = sorted(days[d], key=lambda x: x[2])  # within a day: chronological
            net = sum((x[7] or 0) - (x[6] or 0) for x in txs)
            wd = WEEKDAY08[date.fromisoformat(d).weekday()]
            rows = [f'<tr class="statement-day" {v}><th colspan="6" scope="rowgroup" {v}><time datetime="{d}">{wd} {int(d[8:])} {MON[int(d[5:7]) - 1].replace("Oct", "October")}</time><span class="statement-day__net" {v}>{"+" if net >= 0 else MINUS}{_gbp(abs(net))}</span></th></tr>']
            for tid, _d, t, desc, ref, cat, out, inn in txs:
                open_ = tid == EXPANDED08
                pid = "p-" + _hash(tid, 6, _B36)
                rows.append(f"""
        <tr class="statement-row{' statement-row--open' if open_ else ''}" {v}>
          <td class="statement-row__toggle" {v}><button type="button" class="disclosure" aria-expanded="{'true' if open_ else 'false'}" aria-controls="{pid}" {v}{M('toggle:' + tid)}>{icon('chev-down' if open_ else 'chev-right')}<span class="u-sr" {v}>Toggle details</span></button></td>
          <td class="statement-row__payee" {v}><p class="payee__name" {v}>{esc(desc)}</p><span class="payee__ref" {v}>{esc(ref)}</span></td>
          <td {v}><select id="cat-{pid}" class="category-picker" name="category" aria-label="Category" {v}{M('category:' + tid)}>{cat_options(cat, grouped=True)}</select></td>
          <td class="money money--in" {v}>{'+' + _gbp(inn) if inn else ''}</td>
          <td class="money money--out" {v}{M('out:' + tid)}>{_gbp(out) if out else ''}</td>
          <td class="money" {v}>{_gbp(bal[tid])}</td>
        </tr>
        <tr class="statement-panel" id="{pid}" {v}{'' if open_ else ' hidden'}>
          <td colspan="6" {v}><div class="panel" {v}><dl class="panel__facts" {v}><dt>When</dt><dd>{d_gb(d)} at {t}</dd><dt>How</dt><dd>{esc(ref.split(' · ')[0])}</dd><dt>Reference</dt><dd>{tid.upper()}</dd></dl><div class="panel__actions" {v}><button type="button" class="ghost-btn" {v}>Add note</button><button type="button" class="ghost-btn" {v}>Split payment</button><button type="button" class="ghost-btn ghost-btn--warn" {v}{M('dispute:' + tid)}>Report a problem</button></div></div></td>
        </tr>""")
            bodies.append(f'\n      <tbody class="statement-group" {v}>' + "".join(rows) + "\n      </tbody>")
        tb_css = (":host{display:block;margin:16px 0}.bar{display:flex;flex-wrap:wrap;align-items:center;gap:10px;padding:12px;border:1px solid #d9e2dc;border-radius:12px;background:#fff}"
                  ".search{display:flex;align-items:center;gap:6px;flex:1 1 320px;padding:0 10px;border:1px solid #9aa6a0;border-radius:8px}"
                  ".search input{border:0;outline:0;width:100%;padding:8px 0;font:inherit}.export{margin-left:auto;font-weight:700;color:#0b5d44}"
                  ".more{position:absolute}")
        exp = "/api/v2/accounts/4821/transactions/export?period=30d&amp;format="
        body = f"""
<header class="masthead" {v}>
  <a class="masthead__brand" href="/" {v}><svg width="30" height="30" viewBox="0 0 30 30" aria-hidden="true"><circle cx="15" cy="15" r="15" fill="#0b5d44"/></svg>Lindmoor</a>
  <nav class="masthead__nav" aria-label="Main" {v}><a href="/home" {v}>Home</a><a href="/payments" {v}>Payments</a><a href="/cards" {v}>Cards</a><a href="/savings" {v}>Savings</a><a href="/help" {v}>Help</a></nav>
  <button type="button" class="masthead__profile" aria-haspopup="menu" {v}>Maya Thompson{icon('chev-down')}</button>
</header>
<main class="page" {v}>
  <section class="hero-card" {v}>
    <div {v}><p class="hero-card__eyebrow" {v}>Everyday Current Account &middot; 20-44-91 &middot; ****4821</p><p class="hero-card__balance" {v}>{_gbp(3214.77)}</p><p class="hero-card__sub" {v}>{_gbp(3714.77)} available including {_gbp(500)} overdraft</p></div>
    <div class="hero-card__actions" {v}><a href="/payments/new" class="pill-btn" {v}>Pay someone</a><a href="/transfers/new" class="pill-btn" {v}>Move money</a></div>
  </section>
  <nav class="tabs" role="tablist" aria-label="Account" {v}><a role="tab" aria-selected="true" href="/a/4821" {v}>Transactions</a><a role="tab" aria-selected="false" href="/a/4821/statements" {v}>Statements</a><a role="tab" aria-selected="false" href="/a/4821/regular-payments" {v}>Regular payments</a><a role="tab" aria-selected="false" href="/a/4821/details" {v}>Details</a></nav>
  <section class="pending" aria-labelledby="pending-h" {v}>
    <h2 id="pending-h" class="pending__title" {v}>Pending</h2>
    <table class="pending__table" {v}>
      <tbody {v}>
        <tr {v}><td {v}>Uber *Trip</td><td {v}>Transport</td><td class="money" {v}>{_gbp(14.20)}</td></tr>
        <tr {v}><td {v}>TfL Travel Charge</td><td {v}>Transport</td><td class="money" {v}>{_gbp(2.80)}</td></tr>
        <tr {v}><td {v}>Costa Coffee</td><td {v}>Eating out</td><td class="money" {v}>{_gbp(3.85)}</td></tr>
      </tbody>
    </table>
  </section>
  <lb-ledger-toolbar account="4821">
    <template shadowrootmode="open">
      <style>{tb_css}</style>
      <div class="bar" role="search">
        <label class="search">{icon('search')}<input type="search" id="q-{_hash('search', 4, _B36)}" placeholder="Search payee, reference or amount" aria-label="Search transactions"{M('search')}></label>
        <select aria-label="Period"><option selected>Last 30 days</option><option>This month</option><option>Last 3 months</option></select>
        <button class="filters" type="button">{icon('funnel')}Filters</button>
        <a class="export" href="{exp}csv" download{M('export')}>Export CSV</a>
        <button class="more-btn" type="button" aria-haspopup="menu" aria-label="More export options">{icon('dots')}</button>
        <div class="more" role="menu" hidden><a role="menuitem" href="{exp}csv" download>Export CSV</a><a role="menuitem" href="{exp}pdf" download>Export PDF</a><a role="menuitem" href="{exp}ofx" download>Export OFX (Quicken)</a></div>
      </div>
    </template>
  </lb-ledger-toolbar>
  <table class="statement" {v}>
    <caption class="u-sr" {v}>Transactions, last 30 days</caption>
    <thead {v}>
      <tr {v}><th scope="col" {v}><span class="u-sr" {v}>Details</span></th><th scope="col" {v}>Payee</th><th scope="col" {v}>Category</th><th scope="col" class="money" {v}>Money in</th><th scope="col" class="money" {v}>Money out</th><th scope="col" class="money" {v}>Balance</th></tr>
    </thead>{''.join(bodies)}
  </table>
</main>
<footer class="legal" {v}>Lindmoor Bank plc. Authorised by the Prudential Regulation Authority and regulated by the Financial Conduct Authority. &copy; 2025</footer>
"""
        css = (".masthead[data-v-7c1e2a4b]{display:flex;align-items:center;gap:24px;height:68px;padding:0 32px;background:#fff;border-bottom:1px solid #e3e8e5}"
               ".statement[data-v-7c1e2a4b]{width:100%;border-collapse:separate;border-spacing:0}.money[data-v-7c1e2a4b]{text-align:right;font-variant-numeric:tabular-nums}"
               ".u-sr[data-v-7c1e2a4b]{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}")
        return page("Everyday Current Account | Lindmoor", body, css=css, lang="en-GB")

    emit("table-08",
         title="Bank transaction ledger with expandable detail rows and category selects",
         mutations=["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "id-change",
                    "copy-change", "attribute-churn", "structure-move", "insertion"],
         notes=("v2 is a Vue rewrite (scoped data-v attributes, renamed classes): transactions are grouped into one tbody per "
                "day with a day-heading row (the Date column disappears) and ordered chronologically inside each day, the "
                "expand toggle moves to the first column with an sr-only 'Toggle details' label, Paid in/Paid out become "
                "Money in/Money out in swapped order, detail rows get hashed ids and 'Report a problem' replaces 'Dispute this "
                "transaction', the category selects get optgroups, a 'Pending' table repeats a TfL payment, and search + "
                "export move into an <lb-ledger-toolbar> shadow root with a hidden export menu duplicating 'Export CSV'."),
         targets=targets, v1=v1, v2=v2)


# ========================================================================================
# table-09 — Airport departures board (Halden Airport)  ·  v2: table -> <ol> list inside a shadow root
# ========================================================================================
FL09 = [
    # scheduled, flight, airline, destination, IATA, terminal, gate, status
    ("14:30", "SK 1415", "SAS", "Copenhagen", "CPH", "T2", "B3", "Departed 14:38"),
    ("14:35", "FR 8812", "Ryanair", "Barcelona", "BCN", "T1", "A12", "Gate closed"),
    ("14:40", "LH 2471", "Lufthansa", "Munich", "MUC", "T2", "B9", "Gate closed"),
    ("14:45", "U2 6103", "easyJet", "Amsterdam", "AMS", "T1", "A4", "Boarding"),
    ("14:55", "EI 3417", "Aer Lingus", "Lisbon", "LIS", "T1", "A7", "Boarding"),
    ("15:00", "KL 1182", "KLM", "Amsterdam", "AMS", "T2", "B14", "Boarding"),
    ("15:10", "BA 0847", "British Airways", "London Heathrow", "LHR", "T2", "B6", "Delayed 16:05"),
    ("15:15", "AF 1069", "Air France", "Paris CDG", "CDG", "T2", "B11", "Go to gate"),
    ("15:25", "W6 4410", "Wizz Air", "Budapest", "BUD", "T1", "A2", "Go to gate"),
    ("15:30", "AY 1352", "Finnair", "Helsinki", "HEL", "T2", "B8", "On time"),
    ("15:40", "IB 3726", "Iberia", "Madrid", "MAD", "T1", "A9", "On time"),
    ("15:45", "TP 1347", "TAP Air Portugal", "Porto", "OPO", "T1", "A5", "Cancelled"),
    ("15:55", "LX 0459", "SWISS", "Zurich", "ZRH", "T2", "B2", "On time"),
    ("16:05", "FI 0417", "Icelandair", "Reykjavík", "KEF", "T2", "B12", "On time"),
    ("16:10", "EK 0016", "Emirates", "Dubai", "DXB", "T2", "C21", "On time"),
    ("16:20", "FR 2933", "Ryanair", "Kraków", "KRK", "T1", "A14", "On time"),
    ("16:30", "SN 2584", "Brussels Airlines", "Brussels", "BRU", "T2", "B5", "Delayed 17:15"),
    ("16:40", "DY 1307", "Norwegian", "Oslo", "OSL", "T1", "A3", "On time"),
    ("16:50", "OS 0458", "Austrian", "Vienna", "VIE", "T2", "B10", "On time"),
    ("17:05", "UA 0921", "United", "Newark", "EWR", "T2", "C24", "On time"),
    ("17:15", "U2 6219", "easyJet", "Edinburgh", "EDI", "T1", "A6", "On time"),
    ("17:25", "AZ 0207", "ITA Airways", "Rome Fiumicino", "FCO", "T2", "B7", "On time"),
]
FOLLOWED09 = ("BA 0847", "KL 1182")


def _st09(status):
    return {"Departed": "departed", "Gate": "closed", "Boarding": "boarding", "Delayed": "delayed", "Go": "gate",
            "On": "ontime", "Cancelled": "cancelled"}[status.split()[0]]


def _est09(f):
    parts = f[7].split()
    return parts[-1] if parts[0] in ("Departed", "Delayed") else f[0]


CSS09_V1 = """
body{margin:0;font:16px/1.5 "Frutiger","Segoe UI",Arial,sans-serif;color:#0d1b2a;background:#fff}
.site-header{background:#0d1b2a}.site-header__inner{display:flex;align-items:center;gap:32px;max-width:1180px;margin:0 auto;padding:12px 24px}
.primary-nav a{color:#e0e6ed;text-decoration:none;margin-right:22px}.primary-nav a.active{color:#ffd23f;font-weight:700}.lang{margin-left:auto;color:#e0e6ed}
.flights-page{max-width:1180px;margin:0 auto;padding:24px}
.board-tabs{display:flex;gap:4px;margin-bottom:16px}.board-tab{padding:10px 22px;background:#e9edf1;color:#0d1b2a;text-decoration:none;font-weight:700}.board-tab.active{background:#ffd23f}
.flight-search{display:flex;align-items:center;gap:10px}.flight-search input{flex:1;max-width:380px;padding:8px 12px;border:2px solid #0d1b2a}
.btn-search{padding:8px 18px;background:#0d1b2a;color:#fff;border:0}.board-meta{color:#5c6b7a;font-size:14px}
.fids{width:100%;border-collapse:collapse;background:#0d1b2a;color:#fff;font-family:"DIN Alternate","Roboto Mono",monospace}
.fids th{text-align:left;font-size:13px;color:#ffd23f;padding:10px 12px;border-bottom:2px solid #ffd23f}.fids td{padding:10px 12px;border-bottom:1px solid #22344a}
.airline-logo{vertical-align:middle;margin-right:6px;background:#fff;border-radius:3px}
.is-boarding .fids-status{color:#3ddc97}.is-delayed .fids-status{color:#ffb347}.is-cancelled .fids-status{color:#ff5a5f}.is-departed{opacity:.55}
.btn-track{padding:4px 12px;background:transparent;color:#ffd23f;border:1px solid #ffd23f;cursor:pointer}
.board-more{text-align:center;margin:16px 0}.load-more{padding:10px 24px;border:2px solid #0d1b2a;background:#fff;font-weight:700}
.info-panels{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:24px}.info-panel{background:#f4f6f8;padding:16px 20px}
.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.site-footer{background:#0d1b2a;color:#c5d0db;padding:24px}.site-footer a{color:#fff;margin-right:16px}
"""


@suite
def table_09():
    pos = {f[1]: i for i, f in enumerate(FL09, 1)}
    targets = [
        dict(id="t1", key="track:EI 3417",
             description="'Track' button of flight EI 3417 to Lisbon (v2: 'Follow')",
             css="#departures tr[data-flight='EI3417'] .btn-track",
             xpath="//td[contains(.,'EI 3417')]/following-sibling::td/button[.='Track']",
             mutations=["shadow-dom", "copy-change", "tag-change", "class-obfuscation", "sibling-reorder", "decoy"]),
        dict(id="t2", key="gate:KL 1182",
             description="Gate cell of flight KL 1182 to Amsterdam (gate B14)",
             css=f"#departures tbody tr:nth-child({pos['KL 1182']}) td.fids-gate",
             xpath="//tr[@data-flight='KL1182']/td[5]",
             mutations=["shadow-dom", "tag-change", "sibling-reorder", "class-obfuscation", "copy-change", "decoy"]),
        dict(id="t3", key="status:BA 0847",
             description="Status cell of flight BA 0847 to London Heathrow ('Delayed 16:05')",
             css=f"#departures > tbody > tr:nth-child({pos['BA 0847']}) > td:nth-child(6)",
             xpath="//tr[td[2][contains(normalize-space(),'BA 0847')]]/td[@class='fids-status']",
             mutations=["shadow-dom", "tag-change", "sibling-reorder", "class-obfuscation", "wrapper-divs", "decoy"]),
        dict(id="t4", key="tab:arrivals",
             description="'Arrivals' board tab next to 'Departures'",
             css=".board-tabs a[href='/flights/arrivals']",
             xpath="//div[@class='board-tabs']/a[2]",
             mutations=["sibling-reorder", "insertion", "attribute-churn", "class-obfuscation", "decoy"]),
        dict(id="t5", key="search",
             description="Flight search input above the departures board",
             css="#flight-q",
             xpath="//input[@placeholder='Flight number, airline or destination']",
             mutations=["shadow-dom", "copy-change", "class-obfuscation", "wrapper-divs", "structure-move"]),
        dict(id="t6", key="later",
             description="'Show later flights' button below the departures board (v2: 'Load more departures')",
             css="button.load-more",
             xpath="//button[normalize-space()='Show later flights']",
             mutations=["shadow-dom", "copy-change", "class-obfuscation", "decoy"]),
    ]

    def v1(M):
        rows = []
        for sched, fno, airline, dest, _iata, term, gate, status in FL09:
            code = fno.replace(" ", "")
            rows.append(f"""
      <tr class="fids-row is-{_st09(status)}" data-flight="{code}">
        <td class="fids-time">{sched}</td>
        <td class="fids-flight"><img class="airline-logo" src="/img/airlines/{fno[:2]}.svg" alt="{esc(airline)}" width="20" height="20"> {fno}</td>
        <td class="fids-dest">{esc(dest)}</td>
        <td class="fids-terminal">{term}</td>
        <td class="fids-gate"{M('gate:' + fno)}>{gate}</td>
        <td class="fids-status"{M('status:' + fno)}>{status}</td>
        <td class="fids-track"><button type="button" class="btn-track" data-flight="{code}"{M('track:' + fno)}>Track</button></td>
      </tr>""")
        body = f"""
<header class="site-header">
  <div class="site-header__inner">
    <a class="logo" href="/"><img src="/static/halden-airport-logo.svg" alt="Halden Airport" width="150" height="36"></a>
    <nav class="primary-nav" aria-label="Main"><a class="active" href="/flights">Flights</a><a href="/parking">Parking</a><a href="/shops-dining">Shops &amp; dining</a><a href="/getting-here">Getting here</a><a href="/help">Help</a></nav>
    <a class="lang" href="/no" lang="nb">Norsk</a>
  </div>
</header>
<main class="flights-page">
  <h1>Departures</h1>
  <div class="board-tabs"><a href="/flights/departures" class="board-tab active" aria-current="page">Departures</a><a href="/flights/arrivals" class="board-tab"{M('tab:arrivals')}>Arrivals</a></div>
  <form class="flight-search" role="search" action="/flights/departures">
    <label for="flight-q">Find a flight</label>
    <input id="flight-q" name="q" type="search" placeholder="Flight number, airline or destination"{M('search')}>
    <select name="terminal" aria-label="Terminal"><option>All terminals</option><option>Terminal 1</option><option>Terminal 2</option></select>
    <button type="submit" class="btn-search">Search</button>
  </form>
  <p class="board-meta">Last updated <time datetime="2025-11-03T14:52">14:52</time> &middot; All times are local</p>
  <table class="fids" id="departures">
    <thead>
      <tr><th scope="col">Time</th><th scope="col">Flight</th><th scope="col">Destination</th><th scope="col">Terminal</th><th scope="col">Gate</th><th scope="col">Status</th><th scope="col"><span class="sr-only">Track</span></th></tr>
    </thead>
    <tbody>{''.join(rows)}
    </tbody>
  </table>
  <div class="board-more"><button type="button" class="load-more"{M('later')}>Show later flights</button></div>
  <section class="info-panels">
    <div class="info-panel"><h2>Security wait times</h2><p>Terminal 1: about 8 minutes<br>Terminal 2: about 14 minutes</p></div>
    <div class="info-panel"><h2>Travelling soon?</h2><p>Check in online and arrive at the airport at least two hours before departure. Liquids up to 100 ml in a clear bag.</p></div>
  </section>
</main>
<footer class="site-footer">
  <nav aria-label="Footer"><a href="/flights/departures">Departures</a><a href="/flights/arrivals">Arrivals</a><a href="/parking">Parking</a><a href="/accessibility">Accessibility</a><a href="/contact">Contact us</a></nav>
  <p>&copy; 2025 Halden Lufthavn AS</p>
</footer>
"""
        return page("Departures | Halden Airport", body, css=CSS09_V1)

    def v2(M):
        order = sorted(FL09, key=lambda f: (_est09(f), f[0]))
        E = lambda name: emo("fids:" + name, name)  # noqa: E731
        pill = lambda status, mark="": f'<div class="{E("StatusCell")}"{mark}><span class="{E("Pill")} {E("Pill-" + _st09(status))}">{status}</span></div>'  # noqa: E731
        gatecell = lambda gate, mark="": f'<div class="{E("GateCell")}"{mark}><span class="{E("Label")}">Gate</span> {gate}</div>'  # noqa: E731
        items = []
        for sched, fno, airline, dest, iata, term, gate, status in order:
            followed = fno in FOLLOWED09
            items.append(f"""
        <li class="{E('FlightRow')}" data-status="{_st09(status)}">
          <div class="{E('Time')}"><time datetime="2025-11-03T{sched}">{sched}</time></div>
          <div class="{E('Flight')}"><img src="https://cdn.haldenairport.example/airlines/{fno[:2].lower()}.png" alt="" width="24" height="24"><div><span class="{E('FlightNo')}">{fno}</span><span class="{E('Airline')}">{esc(airline)}</span></div></div>
          <div class="{E('Destination')}"><span class="{E('City')}">{esc(dest)}</span><span class="{E('Iata')}">{iata}</span></div>
          {pill(status, M('status:' + fno))}
          {gatecell(gate, M('gate:' + fno))}
          <div class="{E('Terminal')}">{term}</div>
          <div class="{E('Actions')}"><button type="button" class="{E('FollowButton')}" aria-pressed="{'true' if followed else 'false'}" aria-label="{'Unfollow' if followed else 'Follow'} {fno}"{M('track:' + fno)}>{icon('bell')}{'Following' if followed else 'Follow'}</button></div>
        </li>""")
        saved = []
        for f in FL09:
            if f[1] in FOLLOWED09:
                saved.append(f'<article class="{E("SavedCard")}"><div class="{E("SavedFlight")}"><strong>{f[1]}</strong> to {esc(f[3])} &middot; {f[0]}</div>{pill(f[7])}{gatecell(f[6])}<a href="/en/flights/{f[1].replace(" ", "").lower()}" class="{E("SavedLink")}">Details</a></article>')
        board_css = (":host{display:block;font:15px/1.4 Inter,sans-serif;color:#0f172a}ol{list-style:none;margin:0;padding:0}"
                     "li{display:grid;grid-template-columns:70px 1.4fr 1.6fr 1.3fr 90px 60px 130px;align-items:center;gap:12px;padding:12px 16px;border-bottom:1px solid #e2e8f0}")
        body = f"""
<header class="{E('SiteHeader')}">
  <a class="{E('Logo')}" href="/en"><img src="https://cdn.haldenairport.example/brand/logo-2025.svg" alt="Halden Airport" width="132" height="32"></a>
  <nav class="{E('MainNav')}" aria-label="Main"><a href="/en/flights" aria-current="page">Flights</a><a href="/en/getting-here">Getting here</a><a href="/en/parking">Parking</a><a href="/en/shopping-and-dining">Shops &amp; dining</a><a href="/en/help">Help</a></nav>
  <button type="button" class="{E('LangSwitch')}" aria-haspopup="listbox">EN{icon('chev-down')}</button>
</header>
<div class="{E('Alert')}" role="alert">{icon('info')}<p>Strong winds this afternoon: some departures may be delayed. Please check with your airline before travelling.</p></div>
<main class="{E('Page')}">
  <div class="{E('PageHead')}">
    <h1 class="{E('Title')}">Flights</h1>
    <nav class="{E('BoardTabs')}" aria-label="Flight boards"><a href="/en/flights/departures" aria-current="page" class="{E('BoardTab')}">{icon('plane')}Departures</a><a href="/en/flights/connections" class="{E('BoardTab')}">Connections</a><a href="/en/flights/arrivals" class="{E('BoardTab')}"{M('tab:arrivals')}>Arrivals</a></nav>
  </div>
  <section class="{E('Saved')}" aria-labelledby="saved-h">
    <h2 id="saved-h" class="{E('SectionTitle')}">Flights you follow</h2>
    <div class="{E('SavedGrid')}">{''.join(saved)}</div>
  </section>
  <hx-flight-board direction="departures" airport="HLD">
    <template shadowrootmode="open">
      <style>{board_css}</style>
      <div class="{E('BoardToolbar')}">
        <label class="{E('Search')}">{icon('search')}<input id="flight-q" type="search" placeholder="Search by flight, airline or city" aria-label="Search departures" autocomplete="off"{M('search')}></label>
        <div role="radiogroup" aria-label="Terminal" class="{E('Segmented')}"><button type="button" role="radio" aria-checked="true">All</button><button type="button" role="radio" aria-checked="false">T1</button><button type="button" role="radio" aria-checked="false">T2</button></div>
        <span class="{E('Updated')}">Updated 14:52</span>
      </div>
      <button type="button" class="{E('LoadEarlier')}">Show earlier flights</button>
      <div class="{E('BoardHead')}" aria-hidden="true"><span>Time</span><span>Flight</span><span>Destination</span><span>Status</span><span>Gate</span><span>Terminal</span><span></span></div>
      <ol class="{E('FlightList')}" role="list" aria-label="Departures">{''.join(items)}
      </ol>
      <button type="button" class="{E('LoadMore')}"{M('later')}>Load more departures</button>
    </template>
  </hx-flight-board>
  <section class="{E('InfoGrid')}"><div class="{E('InfoCard')}"><h2>Security queues</h2><p>T1 &middot; 8 min &nbsp; T2 &middot; 14 min</p></div><div class="{E('InfoCard')}"><h2>Before you fly</h2><p>Arrive two hours before departure. Liquids up to 100 ml in a clear bag.</p></div></section>
</main>
<footer class="{E('Footer')}">
  <nav aria-label="Quick links"><a href="/en/flights/arrivals">Arrivals</a><a href="/en/flights/departures">Departures</a><a href="/en/parking">Parking</a><a href="/en/accessibility">Accessibility</a><a href="/en/contact">Contact</a></nav>
  <p>&copy; 2025 Halden Lufthavn AS</p>
</footer>
"""
        return page("Flights – Departures – Halden Airport", body, css="body{margin:0;font-family:Inter,Arial,sans-serif;background:#f8fafc}")

    emit("table-09",
         title="Airport departures board with gate/status cells and track buttons",
         mutations=["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "copy-change",
                    "tag-change", "attribute-churn", "structure-move", "insertion"],
         notes=("v2 replaces the <table> board with an <ol role=list> of CSS-grid rows (emotion classes with dev labels) "
                "rendered inside an <hx-flight-board> declarative shadow root, re-sorts flights by estimated departure time "
                "(delayed and departed flights move), reorders columns (Status before Gate, gate shown as 'Gate B14'), renames "
                "'Track' to 'Follow' and 'Show later flights' to 'Load more departures' (plus a new 'Show earlier flights' "
                "button), inserts a 'Connections' tab between Departures and Arrivals, and adds a 'Flights you follow' panel "
                "that repeats the status and gate cells of BA 0847 and KL 1182. The search input keeps id='flight-q'."),
         targets=targets, v1=v1, v2=v2)


# ========================================================================================
# table-10 — SaaS pricing comparison (Tasklane)  ·  v2: Chakra UI, new plan column, regrouped features
# ========================================================================================
Y10, N10 = True, False
PLANS10 = [
    # key, name, price, unit, blurb, CTA (v1), CTA (v2)
    ("free", "Free", "$0", "free forever", "For individuals getting organised", "Get started", "Get started"),
    ("starter", "Starter", "$8", "per user / month", "For small teams shipping together", "Start free trial", "Start free trial"),
    ("pro", "Pro", "$16", "per user / month", "For growing teams that need control", "Start free trial", "Start free trial"),
    ("business", "Business", "$24", "per user / month", "For multi-team organisations", None, "Start free trial"),
    ("enterprise", "Enterprise", "Custom", "annual agreement", "For large organisations", "Contact sales", "Talk to sales"),
]
F10 = {
    # key: (v1 label, v2 label, (free, starter, pro, business, enterprise))
    "projects": ("Projects", "Projects", ("3", "Unlimited", "Unlimited", "Unlimited", "Unlimited")),
    "tasks": ("Tasks &amp; subtasks", "Tasks &amp; subtasks", (Y10, Y10, Y10, Y10, Y10)),
    "storage": ("Storage", "File storage", ("2 GB", "50 GB", "250 GB", "1 TB", "Unlimited")),
    "views": ("Board, list &amp; calendar views", "Board, list &amp; calendar views", (Y10, Y10, Y10, Y10, Y10)),
    "timeline": ("Timeline (Gantt) view", "Timeline (Gantt) view", (N10, Y10, Y10, Y10, Y10)),
    "automations": ("Automations per month", "Automations per month", (N10, "250", "5,000", "25,000", "Unlimited")),
    "guests": ("Guest access", "Guest users", (N10, Y10, Y10, Y10, Y10)),
    "comments": ("Comments &amp; @mentions", "Comments &amp; @mentions", (Y10, Y10, Y10, Y10, Y10)),
    "dashboards": ("Shared dashboards", "Shared dashboards", (N10, N10, Y10, Y10, Y10)),
    "time": ("Time tracking", "Time tracking", (N10, Y10, Y10, Y10, Y10)),
    "proofing": ("Proofing &amp; approvals", "Proofing &amp; approvals", (N10, N10, Y10, Y10, Y10)),
    "2fa": ("Two-factor authentication", "Two-factor authentication", (Y10, Y10, Y10, Y10, Y10)),
    "sso": ("SSO (SAML / OIDC)", "SSO (SAML / OIDC)", (N10, N10, N10, Y10, Y10)),
    "audit": ("Audit log", "Audit log", (N10, N10, N10, Y10, Y10)),
    "roles": ("Custom roles &amp; permissions", "Custom roles &amp; permissions", (N10, N10, Y10, Y10, Y10)),
    "residency": ("Data residency (EU or US)", "Data residency (EU or US)", (N10, N10, N10, N10, Y10)),
    "help": ("Help centre &amp; community", "Help centre &amp; community", (Y10, Y10, Y10, Y10, Y10)),
    "email": ("Email support", "Email support", (N10, Y10, Y10, Y10, Y10)),
    "priority": ("Priority support (4-hour response)", "Priority support (4-hour response)", (N10, N10, Y10, Y10, Y10)),
    "csm": ("Dedicated customer success manager", "Dedicated success manager", (N10, N10, N10, N10, Y10)),
    "sla": ("Uptime SLA", "Uptime SLA", (N10, N10, "99.9%", "99.9%", "99.99%")),
    "integrations": (None, "Integrations", ("5", "50+", "Unlimited", "Unlimited", "Unlimited")),
    "soc2": (None, "SOC 2 Type II report", (N10, N10, N10, Y10, Y10)),
    "onboarding": (None, "Guided onboarding", (N10, N10, N10, Y10, Y10)),
}
SECTIONS10_V1 = [("Core features", ["projects", "tasks", "storage", "views", "timeline", "automations"]),
                 ("Collaboration", ["guests", "comments", "dashboards", "time", "proofing"]),
                 ("Security &amp; admin", ["2fa", "sso", "audit", "roles", "residency"]),
                 ("Support", ["help", "email", "priority", "csm", "sla"])]
SECTIONS10_V2 = [("Essentials", ["projects", "storage", "tasks", "views", "timeline"]),
                 ("Collaboration", ["comments", "guests", "dashboards", "proofing"]),
                 ("Automation &amp; integrations", ["automations", "integrations", "time"]),
                 ("Security &amp; compliance", ["2fa", "roles", "sso", "audit", "soc2", "residency"]),
                 ("Support", ["help", "email", "priority", "onboarding", "csm", "sla"])]
FAQ10 = [("Can I change plans later?", "Yes. Upgrades take effect immediately and are prorated; downgrades apply at the next billing date."),
         ("What counts as a user?", "Anyone with edit access to your workspace. Guests who can only view or comment are free on paid plans."),
         ("Do you offer discounts for non-profits?", "Registered non-profits and schools get 50% off Starter and Pro. Contact us with proof of status."),
         ("How does the free trial work?", "Paid plans include a 14-day trial with every feature unlocked. No credit card required."),
         ("Which payment methods do you accept?", "All major cards, plus invoicing and bank transfer on annual Business and Enterprise plans."),
         ("Where is my data stored?", "In the EU (Frankfurt) or the US (Oregon). Enterprise customers can pin data to a region.")]

CSS10_V1 = """
body{margin:0;font:16px/1.6 "Inter",system-ui,sans-serif;color:#1f2430;background:#fff}
.container{max-width:1160px;margin:0 auto;padding:0 24px}.site-header{border-bottom:1px solid #eceef3}
.nav-wrap{display:flex;align-items:center;gap:36px;height:68px}.brand{font-weight:800;font-size:20px;color:#5b3df5;text-decoration:none}
.main-nav a{color:#4b5160;text-decoration:none;margin-right:22px}.main-nav a.active{color:#1f2430;font-weight:600}.nav-cta{margin-left:auto;display:flex;gap:12px;align-items:center}
.btn{display:inline-block;padding:10px 18px;border-radius:8px;font-weight:600;text-decoration:none;text-align:center}.btn-sm{padding:6px 12px}
.btn-primary{background:#5b3df5;color:#fff}.btn-outline{border:1px solid #c9cdd8;color:#1f2430}
.pricing-hero{text-align:center;padding:64px 0 32px}.pricing-hero h1{font-size:44px;margin:0}.lead{color:#5d6475;font-size:19px}
.billing-toggle{display:inline-flex;padding:4px;border-radius:999px;background:#f1f2f6}.toggle-btn{border:0;background:none;padding:8px 18px;border-radius:999px;font:inherit;cursor:pointer}
.toggle-btn.is-active{background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.12)}.save-badge{margin-left:6px;font-size:12px;color:#0f9d58;font-weight:700}
.compare-table{width:100%;border-collapse:collapse;margin:32px 0}.compare-table th,.compare-table td{padding:14px 16px;border-bottom:1px solid #eceef3;text-align:center}
.feature-col,.feature-name{text-align:left!important;font-weight:500}.plan-col{vertical-align:bottom}.plan-col.is-featured{background:#f6f3ff}
.plan-flag{display:inline-block;font-size:12px;color:#5b3df5;font-weight:700}.plan-name{font-size:18px;font-weight:700}.price-amount{font-size:32px;font-weight:800}.price-unit{display:block;font-size:13px;color:#5d6475}
.section-row th{background:#f8f9fb;text-align:left!important;font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:#5d6475}
.icon-check{color:#5b3df5}.dash{color:#b8bdc9}.visually-hidden{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.faq{max-width:760px;margin:48px auto}.faq details{border-bottom:1px solid #eceef3;padding:14px 0}.faq summary{font-weight:600;cursor:pointer}
.cta-banner{text-align:center;padding:48px 0;background:#f6f3ff}.site-footer{padding:32px 0;color:#5d6475;font-size:14px}
"""


def _ck(component, variant=""):
    """Chakra UI: semantic component class + emotion hash."""
    return f"chakra-{component} {emo('ck:' + component + ':' + variant)}"


@suite
def table_10():
    v1_rows = []
    for sec, keys in SECTIONS10_V1:
        v1_rows.append(("section", sec))
        v1_rows += [("feature", k) for k in keys]
    row_of = {k: i for i, (kind, k) in enumerate(v1_rows, 1) if kind == "feature"}
    targets = [
        dict(id="t1", key="cta:pro",
             description="'Start free trial' call-to-action in the Pro column header of the comparison table",
             css="th[data-plan='pro'] a.plan-cta",
             xpath="//table[contains(@class,'compare-table')]/thead/tr/th[4]/a",
             mutations=["class-obfuscation", "attribute-churn", "wrapper-divs", "insertion", "decoy"]),
        dict(id="t2", key="price:starter",
             description="Monthly price label of the Starter plan ('$8') in the comparison table header",
             css=".compare-table thead th:nth-child(3) .price-amount",
             xpath="//th[@data-plan='starter']//span[@class='price-amount']",
             mutations=["class-obfuscation", "attribute-churn", "wrapper-divs", "decoy"]),
        dict(id="t3", key="cell:audit:enterprise",
             description="Enterprise-plan cell of the 'Audit log' feature row (included)",
             css=f".compare-table tbody tr:nth-child({row_of['audit']}) td:nth-child(5)",
             xpath="//tr[th[normalize-space()='Audit log']]/td[4]",
             mutations=["sibling-reorder", "insertion", "structure-move", "class-obfuscation", "decoy"]),
        dict(id="t4", key="feature:guests",
             description="Row header of the 'Guest access' feature row (v2: 'Guest users')",
             css=f".compare-table tbody tr:nth-child({row_of['guests']}) > th",
             xpath="//th[@scope='row' and normalize-space()='Guest access']",
             mutations=["copy-change", "sibling-reorder", "class-obfuscation"]),
        dict(id="t5", key="billing:annual",
             description="'Annual' billing-period option of the Monthly/Annual toggle (v2: 'Yearly' radio)",
             css=".billing-toggle button[data-period='annual']",
             xpath="//div[@aria-label='Billing period']/button[2]",
             mutations=["tag-change", "copy-change", "attribute-churn", "class-obfuscation", "wrapper-divs"]),
        dict(id="t6", key="cta:enterprise",
             description="'Contact sales' call-to-action in the Enterprise column header (v2: 'Talk to sales')",
             css="th[data-plan='enterprise'] .plan-cta",
             xpath="(//a[normalize-space()='Contact sales'])[1]",
             mutations=["copy-change", "sibling-reorder", "insertion", "class-obfuscation", "decoy"]),
    ]

    def cell_v1(v):
        if v is True:
            return f'<td>{icon("check", cls="icon-check")}<span class="visually-hidden">Included</span></td>'
        if v is False:
            return '<td><span class="dash" aria-hidden="true">&mdash;</span><span class="visually-hidden">Not included</span></td>'
        return f"<td>{v}</td>"

    def v1(M):
        heads = []
        for key, name, price, unit, _blurb, cta, _cta2 in PLANS10:
            if cta is None:
                continue
            flag = '<span class="plan-flag">Most popular</span>' if key == "pro" else ""
            href = "/contact-sales" if key == "enterprise" else f"/signup?plan={key}"
            btn = "btn-primary" if key == "pro" else "btn-outline"
            heads.append(f'<th scope="col" class="plan-col{" is-featured" if key == "pro" else ""}" data-plan="{key}">{flag}<div class="plan-name">{name}</div>'
                         f'<div class="plan-price"><span class="price-amount"{M("price:" + key)}>{price}</span><span class="price-unit">{unit}</span></div>'
                         f'<a href="{href}" class="btn {btn} plan-cta"{M("cta:" + key)}>{cta}</a></th>')
        body_rows = []
        for kind, k in v1_rows:
            if kind == "section":
                body_rows.append(f'\n        <tr class="section-row"><th scope="rowgroup" colspan="5">{k}</th></tr>')
                continue
            label, _l2, vals = F10[k]
            free, starter, pro, _business, ent = vals
            body_rows.append(f'\n        <tr><th scope="row" class="feature-name"{M("feature:" + k)}>{label}</th>'
                             + "".join(cell_v1(v) for v in (free, starter, pro)) + cell_v1(ent).replace("<td>", f'<td{M("cell:" + k + ":enterprise")}>', 1) + "</tr>")
        faq = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in FAQ10)
        body = f"""
<header class="site-header">
  <div class="container nav-wrap">
    <a href="/" class="brand">Tasklane</a>
    <nav class="main-nav" aria-label="Main"><a href="/product">Product</a><a href="/solutions">Solutions</a><a href="/pricing" class="active" aria-current="page">Pricing</a><a href="/customers">Customers</a><a href="/docs">Docs</a></nav>
    <div class="nav-cta"><a href="/login" class="nav-login">Log in</a><a href="/signup" class="btn btn-sm btn-primary">Start free</a></div>
  </div>
</header>
<main>
  <section class="pricing-hero container">
    <h1>Pricing that scales with your team</h1>
    <p class="lead">Start free. Upgrade when you need advanced workflows, security and support.</p>
    <div class="billing-toggle" role="radiogroup" aria-label="Billing period"><button type="button" role="radio" aria-checked="true" class="toggle-btn is-active" data-period="monthly">Monthly</button><button type="button" role="radio" aria-checked="false" class="toggle-btn" data-period="annual"{M('billing:annual')}>Annual <span class="save-badge">Save 20%</span></button></div>
  </section>
  <section class="compare-section container" aria-label="Compare plans">
    <table class="compare-table">
      <thead>
        <tr><th scope="col" class="feature-col"><span class="visually-hidden">Features</span></th>{''.join(heads)}</tr>
      </thead>
      <tbody>{''.join(body_rows)}
      </tbody>
    </table>
    <p class="compare-note">Prices in USD, billed monthly. Taxes may apply. Annual billing saves 20%.</p>
  </section>
  <section class="faq container" aria-labelledby="faq-h"><h2 id="faq-h">Frequently asked questions</h2>{faq}</section>
  <section class="cta-banner"><h2>Still deciding?</h2><p>See Tasklane with your own projects in a 30-minute demo.</p><a class="btn btn-primary" href="/demo">Book a demo</a> <a class="btn btn-outline" href="/contact-sales">Contact sales</a></section>
</main>
<footer class="site-footer container"><p>&copy; 2025 Tasklane Inc. &middot; <a href="/legal/terms">Terms</a> &middot; <a href="/legal/privacy">Privacy</a> &middot; <a href="/security">Security</a></p></footer>
"""
        return page("Pricing – Tasklane", body, css=CSS10_V1)

    def v2(M):
        def cell(v, mark=""):
            if v is True:
                return f'<td class="{_ck("table__cell", "c")}"{mark}>{icon("check", cls=_ck("icon", "check"))}<span class="{_ck("visually-hidden")}">Included</span></td>'
            if v is False:
                return f'<td class="{_ck("table__cell", "c")}"{mark}><span aria-hidden="true">&mdash;</span><span class="{_ck("visually-hidden")}">Not included</span></td>'
            return f'<td class="{_ck("table__cell", "c")}"{mark}>{v}</td>'

        def plan_block(key, name, price, unit, cta, mark, clone=False):
            ti = ' tabindex="-1"' if clone else ""
            href = "/contact/sales" if key == "enterprise" else f"/signup?plan={key}&amp;billing=monthly"
            badge = f'<span class="{_ck("badge", "popular")}">Most popular</span>' if key == "pro" else ""
            return (f'<div class="{_ck("stack", "plan")}"><p class="{_ck("text", "plan")}">{name}</p>{badge}'
                    f'<p class="{_ck("text", "price")}"><span class="{emo("price-amount")}"{mark("price:" + key)}>{price}</span> <span class="{emo("price-unit")}">{unit}</span></p>'
                    f'<a class="{_ck("button", "solid" if key == "pro" else "outline")}" href="{href}"{ti}{mark("cta:" + key)}>{cta}</a></div>')

        heads = "".join(f'<th scope="col" class="{_ck("table__column-header", "plan")}">{plan_block(k, n, p, u, c2, M)}</th>' for k, n, p, u, _b, _c1, c2 in PLANS10)
        clone = "".join(plan_block(k, n, p, u, c2, NOMARK, clone=True) for k, n, p, u, _b, _c1, c2 in PLANS10)
        cards = "".join(
            f'<div class="{_ck("card", "plan")}"><div class="{_ck("card__header")}"><h3 class="{_ck("heading", "h3")}">{n}</h3><p class="{_ck("text", "muted")}">{b}</p></div>'
            f'<div class="{_ck("card__body")}"><p class="{_ck("text", "price")}"><span class="{emo("price-amount")}">{p}</span> <span class="{emo("price-unit")}">{u}</span></p></div>'
            f'<div class="{_ck("card__footer")}"><a class="{_ck("button", "solid" if k == "pro" else "outline")}" href="{"/contact/sales" if k == "enterprise" else "/signup?plan=" + k}">{c2}</a></div></div>'
            for k, n, p, u, b, _c1, c2 in PLANS10)
        rows = []
        for sec, keys in SECTIONS10_V2:
            rows.append(f'\n          <tr class="{_ck("table__row", "section")}"><th scope="colgroup" colspan="6" class="{_ck("table__column-header", "section")}">{sec}</th></tr>')
            for k in keys:
                _l1, label, vals = F10[k]
                tds = "".join(cell(v, M(f"cell:{k}:enterprise") if i == 4 else "") for i, v in enumerate(vals))
                rows.append(f'\n          <tr class="{_ck("table__row")}"><th scope="row" class="{_ck("table__row-header")}"{M("feature:" + k)}>{label}<button type="button" class="{_ck("icon-button", "ghost")}" aria-label="More about {label}">{icon("info", size=14)}</button></th>{tds}</tr>')
        faq_css = (":host{display:block;max-width:760px;margin:64px auto}details{border-bottom:1px solid #e2e8f0;padding:16px 0}"
                   "summary{font-weight:600;cursor:pointer;list-style:none}p{color:#4a5568}")
        faq = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in FAQ10)
        body = f"""
<header class="{_ck('container', 'header')}">
  <div class="{_ck('stack', 'header')}">
    <a href="/" class="{_ck('link', 'brand')}"><svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true"><path d="M4 8h20v4H4zM4 16h14v4H4z" fill="#6d28d9"/></svg>Tasklane</a>
    <nav aria-label="Main" class="{_ck('stack', 'nav')}"><a href="/product" class="{_ck('link')}">Product</a><a href="/customers" class="{_ck('link')}">Customers</a><a href="/pricing" class="{_ck('link', 'active')}" aria-current="page">Pricing</a><a href="/solutions" class="{_ck('link')}">Solutions</a><a href="/docs" class="{_ck('link')}">Docs</a></nav>
    <div class="{_ck('stack', 'cta')}"><a href="/contact-sales" class="{_ck('link')}">Contact sales</a><a href="/login" class="{_ck('link')}">Log in</a><a href="/signup" class="{_ck('button', 'solid-sm')}">Start free</a></div>
  </div>
</header>
<main>
  <section class="{_ck('container', 'hero')}">
    <span class="{_ck('badge', 'new')}">New: Business plan</span>
    <h1 class="{_ck('heading', 'h1')}">Plans for every stage of your team</h1>
    <p class="{_ck('text', 'lead')}">Try any paid plan free for 14 days. No credit card required.</p>
    <div role="radiogroup" aria-label="Billing period" class="{_ck('radio-group', 'billing')}">
      <label class="{_ck('radio', 'seg')}"><input type="radio" name="billing" value="monthly" class="{_ck('radio__input')}" checked><span class="{_ck('radio__control')}" aria-hidden="true"></span><span class="{_ck('radio__label')}">Monthly</span></label>
      <label class="{_ck('radio', 'seg')}"><input type="radio" name="billing" value="yearly" class="{_ck('radio__input')}"{M('billing:annual')}><span class="{_ck('radio__control')}" aria-hidden="true"></span><span class="{_ck('radio__label')}">Yearly <span class="{_ck('badge', 'save')}">&minus;20%</span></span></label>
    </div>
  </section>
  <section class="{_ck('container', 'cards')}" aria-label="Plans"><div class="{_ck('simple-grid', 'plans')}">{cards}</div></section>
  <section class="{_ck('container', 'compare')}" aria-labelledby="compare-h">
    <h2 id="compare-h" class="{_ck('heading', 'h2')}">Compare all features</h2>
    <div class="{emo('sticky-plans')}" aria-hidden="true">{clone}</div>
    <div class="{_ck('table__container')}">
      <table class="{_ck('table', 'compare')}">
        <thead class="{_ck('table__thead')}">
          <tr class="{_ck('table__row')}"><th scope="col" class="{_ck('table__column-header', 'feature')}"><span class="{_ck('visually-hidden')}">Feature</span></th>{heads}</tr>
        </thead>
        <tbody class="{_ck('table__tbody')}">{''.join(rows)}
        </tbody>
      </table>
    </div>
  </section>
  <tl-faq>
    <template shadowrootmode="open">
      <style>{faq_css}</style>
      <h2>Questions &amp; answers</h2>
      {faq}
    </template>
  </tl-faq>
  <section class="{_ck('container', 'banner')}"><h2 class="{_ck('heading', 'h2')}">Need a hand choosing?</h2><a class="{_ck('button', 'solid')}" href="/demo">Book a demo</a> <a class="{_ck('button', 'outline')}" href="/contact/sales">Talk to sales</a></section>
</main>
<footer class="{_ck('container', 'footer')}"><p class="{_ck('text', 'small')}">&copy; 2025 Tasklane Inc. &middot; <a href="/legal/terms">Terms</a> &middot; <a href="/legal/privacy">Privacy</a> &middot; <a href="/trust">Trust centre</a></p></footer>
"""
        return page("Pricing | Tasklane", body, css="body{margin:0;font-family:Inter,system-ui,sans-serif;color:#1a202c}")

    emit("table-10",
         title="SaaS pricing comparison table (plans as columns, feature rows, CTA per plan)",
         mutations=["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "copy-change",
                    "tag-change", "attribute-churn", "structure-move", "insertion"],
         notes=("v2 is a Chakra UI rebuild: a new 'Business' plan column is inserted between Pro and Enterprise, feature rows "
                "are regrouped into new sections and reordered (Guest access -> 'Guest users'), plan-card tiles above the table "
                "and an aria-hidden sticky clone of the plan header repeat every price and CTA, the Monthly/Annual toggle "
                "becomes a native radio group ('Yearly'), 'Contact sales' becomes 'Talk to sales' while the site header gains a "
                "'Contact sales' link, data-plan attributes disappear, and the FAQ moves into a <tl-faq> shadow root."),
         targets=targets, v1=v1, v2=v2)


# ---- SUITES-END (new suites are inserted above this line) --------------------------------


def main(argv: list[str]) -> int:
    wanted = argv or list(SUITES)
    unknown = [w for w in wanted if w not in SUITES]
    if unknown:
        print(f"unknown suite(s): {unknown}; available: {sorted(SUITES)}")
        return 2
    for name in wanted:
        SUITES[name]()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
