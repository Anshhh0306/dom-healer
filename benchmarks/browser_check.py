#!/usr/bin/env python
"""Check healed selectors in a real browser (Chromium via Playwright for Node).

dom-healer works on a static lxml tree.  This script verifies that the
selectors it emits also work where they will actually be used: every target of
every suite is healed with the default ranker, then each ``v2.html`` is opened
in Chromium (JavaScript disabled, so the DOM is the same static page) and the
healed CSS and XPath are evaluated with Playwright's ``css=`` / ``xpath=``
engines.  The ``data-dh-target`` markers still present in the raw files tell
the browser side which element is the true one.

Requires Node.js with the ``playwright`` package and a Chromium build
(``npm i playwright && npx playwright install chromium``).

Usage::

    python benchmarks/browser_check.py            # writes benchmarks/results/browser_check.{json,md}
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from fixture_lib import FIXTURES_DIR, load_all  # noqa: E402

from dom_healer.healer import Healer, get_index  # noqa: E402


def build_plan(fixtures: Path) -> tuple[dict, dict]:
    suites = load_all(fixtures)
    plan: dict = {"suites": []}
    meta: dict = {}
    for suite in suites:
        old_index = get_index(suite.old_doc)
        healer = Healer(suite.new_doc)
        entries = []
        for t in suite.targets:
            result = healer.locate(old_index.fingerprint(t.old_el, t.css), selector=t.css)
            if result.element is None:
                continue
            best = result.best
            entries.append({"target": t.id, "css": best.css, "xpath": best.xpath})
            meta[(suite.suite_id, t.id)] = {
                "correct": result.element is t.new_el,
                "in_shadow": suite.new_doc.shadow_depth(t.new_el) > 0,
                "css_strategy": best.selectors.css_strategy,
                "xpath_strategy": best.selectors.xpath_strategy,
            }
        plan["suites"].append(
            {"suite": suite.suite_id, "v2_path": str((suite.path / "v2.html").resolve()), "targets": entries}
        )
    return plan, meta


def summarize(results: list[dict], meta: dict) -> dict:
    groups: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    failures = []
    for r in results:
        info = meta[(r["suite"], r["target"])]
        truth_ok = r["truth"].get("count") == 1
        groups["all"]["targets"] += 1
        groups["all"]["truth_resolvable"] += truth_ok
        if not info["correct"]:
            groups["all"]["wrong_prediction"] += 1
            continue
        key = "shadow" if info["in_shadow"] else "light"
        for g in ("correct", key):
            groups[g]["n"] += 1
            for kind in ("css", "xpath"):
                probe = r[kind]
                exact = probe.get("count") == 1 and probe["markers"] == [r["target"]]
                groups[g][f"{kind}_exact"] += exact
                groups[g][f"{kind}_error"] += "error" in probe
        if not (r["css"].get("count") == 1 and r["css"]["markers"] == [r["target"]]):
            failures.append({"suite": r["suite"], "target": r["target"], "in_shadow": info["in_shadow"],
                             "css_strategy": info["css_strategy"], "css": r["css"]})
    return {"groups": {k: dict(v) for k, v in groups.items()}, "css_failures": failures}


def markdown(summary: dict) -> str:
    g = summary["groups"]
    lines = [
        "# Healed selectors in a real browser (Chromium + Playwright, JavaScript disabled)",
        "",
        f"{g['all']['targets']} healed targets; ground-truth marker resolvable in the browser for "
        f"{g['all']['truth_resolvable']}; {g['all'].get('wrong_prediction', 0)} wrong predictions excluded below.",
        "",
        "| Correctly healed targets | n | CSS finds exactly the true element | XPath finds exactly the true element |",
        "|---|---:|---:|---:|",
    ]
    for key, label in (("correct", "all"), ("light", "in light DOM"), ("shadow", "inside shadow DOM")):
        row = g.get(key)
        if not row:
            continue
        n = row["n"]
        lines.append(f"| {label} | {n} | {row.get('css_exact', 0)} ({100 * row.get('css_exact', 0) / n:.1f}%) | "
                     f"{row.get('xpath_exact', 0)} ({100 * row.get('xpath_exact', 0) / n:.1f}%) |")
    lines += ["", "Playwright's XPath engine does not pierce shadow roots, so XPath is only expected to work for "
              "light-DOM targets."]
    return "\n".join(lines) + "\n"


def main() -> int:
    plan, meta = build_plan(FIXTURES_DIR)
    with tempfile.TemporaryDirectory() as tmp:
        plan_path, out_path = Path(tmp) / "plan.json", Path(tmp) / "out.json"
        plan_path.write_text(json.dumps(plan))
        subprocess.run(["node", str(HERE / "browser_check.cjs"), str(plan_path), str(out_path)], check=True)
        results = json.loads(out_path.read_text())
    summary = summarize(results, meta)
    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "browser_check.json").write_text(json.dumps(summary, indent=1) + "\n")
    (out_dir / "browser_check.md").write_text(markdown(summary))
    print(markdown(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
