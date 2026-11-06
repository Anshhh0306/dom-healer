#!/usr/bin/env python
"""Validate benchmark fixture suites (format, ground truth, selector sanity, mutation coverage).

Usage:
    python benchmarks/validate_fixtures.py                 # all categories
    python benchmarks/validate_fixtures.py --category form # one category
    python benchmarks/validate_fixtures.py --suite benchmarks/fixtures/form/form-03

Exit status is 1 if any ERROR was found (warnings do not fail the run).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fixture_lib import (  # noqa: E402
    CATEGORIES,
    FIXTURES_DIR,
    GT_ATTR,
    MUTATION_TAGS,
    SUITE_RE,
    TARGET_ID_RE,
    FixtureError,
    load_suite,
)

from dom_healer.dom import SelectorError, select  # noqa: E402

REQUIRED_SUITE_MUTATIONS = {"class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy"}
MIN_TARGETS = 5
MIN_ELEMENTS = 120
MAX_BYTES = 200_000
_WS = re.compile(r"\s+")


def _norm(text: str) -> str:
    return _WS.sub(" ", text or "").strip().lower()


def _classes(doc) -> set[str]:
    out: set[str] = set()
    for el in doc.root.iter():
        if isinstance(el.tag, str):
            out.update((el.get("class") or "").split())
    return out


def _count_elements(doc) -> int:
    return sum(1 for el in doc.root.iter() if isinstance(el.tag, str))


def _related(a, b) -> bool:
    """True if a is b, or one is an ancestor of the other."""
    if a is b:
        return True
    for anc in a.iterancestors():
        if anc is b:
            return True
    return any(anc is a for anc in b.iterancestors())


def validate_suite(path: Path) -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    warnings: list[str] = []
    stats: dict = {"suite": path.name}
    label = f"{path.parent.name}/{path.name}"

    if not SUITE_RE.match(path.name):
        errors.append(f"{label}: directory name must look like '<category>-NN'")
    for fname in ("v1.html", "v2.html", "targets.json"):
        if not (path / fname).is_file():
            errors.append(f"{label}: missing {fname}")
    if errors:
        return errors, warnings, stats

    try:
        meta = json.loads((path / "targets.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{label}: targets.json is not valid JSON: {exc}"], warnings, stats

    for key in ("suite", "category", "title", "mutations", "targets"):
        if key not in meta:
            errors.append(f"{label}: targets.json missing key {key!r}")
    if errors:
        return errors, warnings, stats
    if meta["suite"] != path.name:
        errors.append(f"{label}: 'suite' is {meta['suite']!r}, expected {path.name!r}")
    if meta["category"] != path.parent.name:
        errors.append(f"{label}: 'category' is {meta['category']!r}, expected {path.parent.name!r}")
    suite_mut = set(meta.get("mutations") or [])
    if unknown := suite_mut - MUTATION_TAGS:
        errors.append(f"{label}: unknown suite mutation tags {sorted(unknown)}")
    if missing := REQUIRED_SUITE_MUTATIONS - suite_mut:
        errors.append(f"{label}: suite 'mutations' must include {sorted(missing)}")
    targets = meta.get("targets") or []
    if len(targets) < MIN_TARGETS:
        errors.append(f"{label}: needs >= {MIN_TARGETS} targets, found {len(targets)}")
    ids = [t.get("id") for t in targets]
    if len(set(ids)) != len(ids):
        errors.append(f"{label}: duplicate target ids {ids}")
    for t in targets:
        tid = t.get("id")
        if not isinstance(tid, str) or not TARGET_ID_RE.match(tid):
            errors.append(f"{label}: bad target id {tid!r} (use t1, t2, ...)")
        for key in ("description", "css", "xpath", "mutations"):
            if not t.get(key):
                errors.append(f"{label}/{tid}: missing or empty {key!r}")
        if unknown := set(t.get("mutations") or []) - MUTATION_TAGS:
            errors.append(f"{label}/{tid}: unknown mutation tags {sorted(unknown)}")
        for key in ("css", "xpath"):
            if GT_ATTR in (t.get(key) or ""):
                errors.append(f"{label}/{tid}: {key} selector must not reference {GT_ATTR}")

    for fname in ("v1.html", "v2.html"):
        raw = (path / fname).read_text(encoding="utf-8")
        if len(raw.encode("utf-8")) > MAX_BYTES:
            errors.append(f"{label}: {fname} is larger than {MAX_BYTES} bytes")
        raw_markers = len(re.findall(GT_ATTR + r"\s*=", raw))
        if raw_markers != len(targets):
            errors.append(
                f"{label}: {fname} contains {raw_markers} {GT_ATTR} markers but targets.json lists {len(targets)}"
            )
    if errors:
        return errors, warnings, stats

    try:
        suite = load_suite(path)
    except FixtureError as exc:
        return [f"{label}: {exc}"], warnings, stats
    except Exception as exc:  # parse failures etc.
        return [f"{label}: failed to load: {type(exc).__name__}: {exc}"], warnings, stats

    n_old, n_new = _count_elements(suite.old_doc), _count_elements(suite.new_doc)
    stats.update(elements_v1=n_old, elements_v2=n_new, targets=len(suite.targets))
    if n_old < MIN_ELEMENTS or n_new < MIN_ELEMENTS:
        errors.append(f"{label}: pages need >= {MIN_ELEMENTS} elements (v1={n_old}, v2={n_new})")
    if not suite.new_doc.shadow_hosts:
        errors.append(f"{label}: v2.html has no declarative shadow root (<template shadowrootmode=\"open\">)")

    survived = 0
    in_shadow = 0
    text_decoys = 0
    tags = Counter()
    for t in suite.targets:
        tags[t.old_el.tag] += 1
        for kind, sel in (("css", t.css), ("xpath", t.xpath)):
            try:
                matches = select(suite.old_doc, sel)
            except SelectorError as exc:
                errors.append(f"{label}/{t.id}: {kind} selector is invalid: {exc}")
                continue
            if len(matches) != 1 or matches[0] is not t.old_el:
                errors.append(
                    f"{label}/{t.id}: {kind} selector {sel!r} must match exactly the target in v1 "
                    f"(matched {len(matches)} element(s){'' if not matches else ', first is target' if matches[0] is t.old_el else ', first is NOT target'})"
                )
            try:
                new_matches = select(suite.new_doc, sel)
            except SelectorError:
                new_matches = []
            if new_matches and new_matches[0] is t.new_el:
                survived += 1
        if suite.new_doc.shadow_depth(t.new_el) > 0:
            in_shadow += 1
        text = _norm(t.new_el.text_content())
        if text:
            for el in suite.new_doc.root.iter(t.new_el.tag):
                if el is not t.new_el and not _related(el, t.new_el) and _norm(el.text_content()) == text:
                    text_decoys += 1
                    break

    stats.update(
        selectors_surviving=f"{survived}/{2 * len(suite.targets)}",
        targets_in_shadow_v2=in_shadow,
        targets_with_same_text_decoy=text_decoys,
        target_tags=dict(tags),
    )
    if survived > 0.4 * 2 * len(suite.targets):
        warnings.append(
            f"{label}: {survived}/{2 * len(suite.targets)} authored selectors still find the target in v2 "
            "(v2 may not be mutated enough)"
        )
    if text_decoys < 2:
        warnings.append(f"{label}: only {text_decoys} target(s) have a same-tag/same-text decoy in v2 (aim for >= 2)")
    if len(tags) < 3:
        warnings.append(f"{label}: targets use only {len(tags)} distinct tag(s); aim for >= 3")

    c_old, c_new = _classes(suite.old_doc), _classes(suite.new_doc)
    if c_old:
        overlap = len(c_old & c_new) / len(c_old | c_new)
        stats["class_jaccard_v1_v2"] = round(overlap, 3)
        if overlap > 0.35:
            warnings.append(f"{label}: class vocabulary overlap v1/v2 is {overlap:.2f} (aim for <= 0.35)")
    return errors, warnings, stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--category", choices=CATEGORIES, action="append")
    parser.add_argument("--suite", type=Path, action="append", help="validate a single suite directory")
    parser.add_argument("--fixtures", type=Path, default=FIXTURES_DIR)
    parser.add_argument("--quiet", action="store_true", help="only print problems and the summary")
    args = parser.parse_args(argv)

    if args.suite:
        paths = [p.resolve() for p in args.suite]
    else:
        cats = tuple(args.category or CATEGORIES)
        paths = []
        for cat in cats:
            cdir = args.fixtures / cat
            if cdir.is_dir():
                paths.extend(sorted(p for p in cdir.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))))

    all_errors: list[str] = []
    all_warnings: list[str] = []
    shadow_suites: Counter = Counter()
    for path in paths:
        errors, warnings, stats = validate_suite(path)
        all_errors += errors
        all_warnings += warnings
        if stats.get("targets_in_shadow_v2"):
            shadow_suites[path.parent.name] += 1
        if not args.quiet:
            print(json.dumps(stats))
        for msg in errors:
            print("ERROR  ", msg)
        for msg in warnings:
            print("WARNING", msg)

    if not args.suite:
        for cat in args.category or CATEGORIES:
            n_suites = sum(1 for p in paths if p.parent.name == cat)
            if n_suites and shadow_suites[cat] < min(3, n_suites):
                msg = f"category {cat}: only {shadow_suites[cat]} suite(s) have a target inside a shadow root in v2 (need >= 3)"
                if n_suites >= 10:
                    all_errors.append(msg)
                    print("ERROR  ", msg)
                else:
                    all_warnings.append(msg)
                    print("WARNING", msg)

    print(f"\nchecked {len(paths)} suite(s): {len(all_errors)} error(s), {len(all_warnings)} warning(s)")
    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main())
