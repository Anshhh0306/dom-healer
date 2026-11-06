"""Loading and ground-truth handling for the adversarial DOM-mutation benchmark.

Each suite lives in ``benchmarks/fixtures/<category>/<suite-id>/`` and contains
``v1.html`` (original page), ``v2.html`` (redesigned/mutated page) and
``targets.json``.  The ground-truth element for target ``tN`` is marked in both
pages with ``data-dh-target="tN"``.  Those marker attributes are **removed**
from the parsed trees before anything (engine or baseline) sees them; the
harness keeps references to the marked elements and compares by identity.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from dom_healer.dom import Document, Element, parse_html

GT_ATTR = "data-dh-target"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
CATEGORIES = ("ecommerce", "dashboard", "table", "form")
MUTATION_TAGS = frozenset(
    {
        "class-obfuscation",
        "wrapper-divs",
        "sibling-reorder",
        "shadow-dom",
        "decoy",
        "id-change",
        "testid-change",
        "copy-change",
        "tag-change",
        "attribute-churn",
        "structure-move",
        "insertion",
    }
)
SUITE_RE = re.compile(r"^(ecommerce|dashboard|table|form)-\d{2}$")
TARGET_ID_RE = re.compile(r"^t\d{1,2}$")


class FixtureError(Exception):
    pass


@dataclass
class Target:
    id: str
    description: str
    css: str
    xpath: str
    mutations: list[str]
    old_el: Element
    new_el: Element


@dataclass
class Suite:
    suite_id: str
    category: str
    title: str
    path: Path
    old_doc: Document
    new_doc: Document
    targets: list[Target]
    meta: dict = field(default_factory=dict)
    old_html: str = ""
    new_html: str = ""


def _collect_markers(doc: Document, label: str) -> dict[str, Element]:
    found: dict[str, Element] = {}
    for el in doc.root.iter():
        if not isinstance(el.tag, str):
            continue
        tid = el.get(GT_ATTR)
        if tid is None:
            continue
        if tid in found:
            raise FixtureError(f"{label}: target id {tid!r} is marked on more than one element")
        found[tid] = el
    return found


def _strip_markers(doc: Document) -> None:
    for el in doc.root.iter():
        if isinstance(el.tag, str) and GT_ATTR in el.attrib:
            del el.attrib[GT_ATTR]


def strip_marker_text(markup: str) -> str:
    """Remove ground-truth markers from raw HTML (for string-based APIs such as the CLI)."""
    return re.sub(r"\s+" + re.escape(GT_ATTR) + r"\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", "", markup)


def load_suite(path: Path) -> Suite:
    path = Path(path)
    meta = json.loads((path / "targets.json").read_text(encoding="utf-8"))
    old_html = (path / "v1.html").read_text(encoding="utf-8")
    new_html = (path / "v2.html").read_text(encoding="utf-8")
    old_doc = parse_html(old_html)
    new_doc = parse_html(new_html)
    label = meta.get("suite", path.name)
    old_markers = _collect_markers(old_doc, f"{label}/v1.html")
    new_markers = _collect_markers(new_doc, f"{label}/v2.html")
    _strip_markers(old_doc)
    _strip_markers(new_doc)
    targets = []
    for t in meta.get("targets", []):
        tid = t.get("id")
        if tid not in old_markers:
            raise FixtureError(f"{label}: target {tid!r} not marked in v1.html")
        if tid not in new_markers:
            raise FixtureError(f"{label}: target {tid!r} not marked in v2.html")
        targets.append(
            Target(
                id=tid,
                description=t.get("description", ""),
                css=t.get("css", ""),
                xpath=t.get("xpath", ""),
                mutations=list(t.get("mutations", [])),
                old_el=old_markers[tid],
                new_el=new_markers[tid],
            )
        )
    return Suite(
        suite_id=meta.get("suite", path.name),
        category=meta.get("category", path.parent.name),
        title=meta.get("title", ""),
        path=path,
        old_doc=old_doc,
        new_doc=new_doc,
        targets=targets,
        meta=meta,
        old_html=strip_marker_text(old_html),
        new_html=strip_marker_text(new_html),
    )


def suite_dirs(fixtures_dir: Path = FIXTURES_DIR, categories: tuple[str, ...] = CATEGORIES) -> list[Path]:
    dirs: list[Path] = []
    for category in categories:
        cdir = Path(fixtures_dir) / category
        if not cdir.is_dir():
            continue
        dirs.extend(sorted(p for p in cdir.iterdir() if p.is_dir() and SUITE_RE.match(p.name)))
    return dirs


def load_all(fixtures_dir: Path = FIXTURES_DIR, categories: tuple[str, ...] = CATEGORIES) -> list[Suite]:
    return [load_suite(p) for p in suite_dirs(fixtures_dir, categories)]
