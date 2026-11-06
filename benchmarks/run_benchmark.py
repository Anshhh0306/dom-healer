#!/usr/bin/env python
"""ML vs. heuristic ranker evaluation on the adversarial DOM-mutation benchmark.

For every target in every suite, a method gets the v1 page (where the authored
selector worked) and the parsed v2 page, and must return a ranked list of v2
elements.  Top-k selector recovery accuracy = the true v2 element is ranked in
the first k.  Methods:

* brittle baselines: the authored CSS selector, the authored XPath, the
  DevTools-style absolute XPath, exact same-tag+text matching, and an
  attribute fallback chain (id -> test-id -> name -> aria-label -> ... -> text);
* dom-healer with the hand-weighted heuristic ranker;
* dom-healer with LogisticRegression / RandomForest rankers, evaluated with
  GroupKFold cross-validation **grouped by suite** (a page is never in both the
  training and test folds) and with leave-one-category-out.

Latency is measured per target as the median of ``--repeats`` runs, with a
fresh page index and cleared memo caches every run (cold), on the parsed page
(HTML parsing is reported separately).

Usage::

    python benchmarks/run_benchmark.py                       # full run, writes results + plots
    python benchmarks/run_benchmark.py --export-model        # also re-train & save the bundled LR model
"""

from __future__ import annotations

import argparse
import gc
import json
import math
import platform
import statistics
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from fixture_lib import FIXTURES_DIR, Suite, Target, load_all  # noqa: E402

import dom_healer  # noqa: E402
from dom_healer import dom as dh_dom  # noqa: E402
from dom_healer import text as dh_text  # noqa: E402
from dom_healer.dom import Element, SelectorError, parse_html, select  # noqa: E402
from dom_healer.features import FEATURE_NAMES  # noqa: E402
from dom_healer.fingerprint import TEST_ATTRS, ElementFingerprint  # noqa: E402
from dom_healer.healer import Healer, get_index  # noqa: E402
from dom_healer.ml import (  # noqa: E402
    Dataset,
    TrainingExample,
    build_dataset,
    rank_positions,
    train_logistic,
    train_random_forest,
)
from dom_healer.rankers import HeuristicRanker, Ranker  # noqa: E402
from dom_healer.synthesis import suggest_selectors  # noqa: E402
from dom_healer.text import normalize_text  # noqa: E402

#: Suites 01-03 of each category were inspected while developing the engine;
#: suites 04-10 were never looked at during development (reported separately).
DEV_SUITE_NUMBERS = frozenset({"01", "02", "03"})

BASELINES = ("css", "xpath", "abs_xpath", "text_match", "attr_fallback")
LEARNED = ("logreg", "random_forest")
ENGINE = ("heuristic",) + LEARNED
METHOD_LABELS = {
    "css": "Authored CSS",
    "xpath": "Authored XPath",
    "abs_xpath": "Absolute XPath",
    "text_match": "Same tag + text",
    "attr_fallback": "Attribute fallback chain",
    "heuristic": "dom-healer · heuristic",
    "logreg": "dom-healer · LogisticRegression",
    "random_forest": "dom-healer · RandomForest",
}


@dataclass
class Query:
    qid: int
    suite: Suite
    target: Target
    fingerprint: ElementFingerprint

    @property
    def group(self) -> str:
        return self.suite.suite_id

    @property
    def split(self) -> str:
        return "dev" if self.suite.suite_id.rsplit("-", 1)[-1] in DEV_SUITE_NUMBERS else "heldout"


# ---------------------------------------------------------------------------------------
# Baselines (each returns an ordered list of candidate elements in the new page)
# ---------------------------------------------------------------------------------------


def _safe_select(doc, selector: str) -> list[Element]:
    try:
        return select(doc, selector)
    except SelectorError:
        return []


def baseline_css(q: Query) -> list[Element]:
    return _safe_select(q.suite.new_doc, q.target.css)


def baseline_xpath(q: Query) -> list[Element]:
    return _safe_select(q.suite.new_doc, q.target.xpath)


def baseline_abs_xpath(q: Query) -> list[Element]:
    return _safe_select(q.suite.new_doc, q.suite.old_doc.absolute_xpath(q.target.old_el))


_TEXT_FREE_ATTRS = ("aria-label", "name", "placeholder", "title", "alt", "value")


def baseline_text_match(q: Query) -> list[Element]:
    old = q.target.old_el
    root = q.suite.new_doc.root
    text = normalize_text(old.text_content())
    if text:
        return [el for el in root.iter(old.tag) if normalize_text(el.text_content()) == text]
    for attr in _TEXT_FREE_ATTRS:
        value = old.get(attr)
        if value:
            return [el for el in root.iter(old.tag) if el.get(attr) == value]
    return []


def baseline_attr_fallback(q: Query) -> list[Element]:
    """id -> test ids -> name -> aria-label -> placeholder -> title/alt/href -> same tag+text."""
    old = q.target.old_el
    root = q.suite.new_doc.root
    chain: list[tuple[str, bool]] = [("id", False), *[(a, False) for a in TEST_ATTRS]]
    chain += [("name", True), ("aria-label", True), ("placeholder", True), ("title", True), ("alt", True), ("href", True)]
    for attr, same_tag in chain:
        value = old.get(attr)
        if not value:
            continue
        found = [el for el in root.iter(old.tag if same_tag else None) if isinstance(el.tag, str) and el.get(attr) == value]
        if found:
            return found
    return baseline_text_match(q)


BASELINE_FUNCS: dict[str, Callable[[Query], list[Element]]] = {
    "css": baseline_css,
    "xpath": baseline_xpath,
    "abs_xpath": baseline_abs_xpath,
    "text_match": baseline_text_match,
    "attr_fallback": baseline_attr_fallback,
}


def rank_of(target: Element, ranked: list[Element]) -> int | None:
    for i, el in enumerate(ranked):
        if el is target:
            return i + 1
    return None


# ---------------------------------------------------------------------------------------
# Timing helpers
# ---------------------------------------------------------------------------------------

_MEMOS = (
    dh_text.words, dh_text.canonical_words, dh_text.trigrams, dh_text.text_similarity, dh_text.lcs_ratio,
    dh_text.is_obfuscated_class, dh_text.identifier_tokens, dh_text.class_tokens, dh_text.looks_generated,
    dh_dom.compile_selector,
)


def clear_caches() -> None:
    for fn in _MEMOS:
        fn.cache_clear()


def time_engine(q: Query, ranker: Ranker, repeats: int) -> dict[str, float]:
    """Median cold latency: fresh index + cleared memo caches, on the parsed page."""
    totals, index_ms, retrieval, features, ranking, synthesis = [], [], [], [], [], []
    doc = q.suite.new_doc
    for _ in range(repeats):
        clear_caches()
        doc._index = None
        gc.disable()
        t0 = time.perf_counter()
        healer = Healer(doc, ranker=ranker)
        result = healer.locate(q.fingerprint, selector=q.target.css)
        elapsed = (time.perf_counter() - t0) * 1000.0
        gc.enable()
        totals.append(elapsed)
        index_ms.append(healer.index_ms)
        t = result.timings_ms
        retrieval.append(t.get("retrieval", 0.0))
        features.append(t.get("features", 0.0))
        ranking.append(t.get("ranking", 0.0))
        synthesis.append(t.get("synthesis", 0.0))
    med = statistics.median
    return {
        "total": med(totals),
        "index": med(index_ms),
        "retrieval": med(retrieval),
        "features": med(features),
        "ranking": med(ranking),
        "synthesis": med(synthesis),
    }


def time_warm(healer: Healer, q: Query, repeats: int) -> float:
    """Median latency of locate() with the page index and memo caches already warm."""
    healer.locate(q.fingerprint, selector=q.target.css)
    times = []
    for _ in range(repeats):
        gc.disable()
        t0 = time.perf_counter()
        healer.locate(q.fingerprint, selector=q.target.css)
        times.append((time.perf_counter() - t0) * 1000.0)
        gc.enable()
    return statistics.median(times)


def time_baseline(q: Query, fn: Callable[[Query], list[Element]], repeats: int) -> float:
    fn(q)  # warm the selector compile cache (the selector was in use before the redesign)
    times = []
    for _ in range(repeats):
        gc.disable()
        t0 = time.perf_counter()
        fn(q)
        times.append((time.perf_counter() - t0) * 1000.0)
        gc.enable()
    return statistics.median(times)


# ---------------------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------------------


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def summarize(ranks: list[int | None]) -> dict:
    n = len(ranks)
    top1 = sum(1 for r in ranks if r == 1)
    top3 = sum(1 for r in ranks if r is not None and r <= 3)
    return {
        "n": n,
        "top1": top1 / n if n else 0.0,
        "top3": top3 / n if n else 0.0,
        "top1_ci": wilson(top1, n),
        "top3_ci": wilson(top3, n),
        "top1_count": top1,
        "top3_count": top3,
    }


def mcnemar(a: list[bool], b: list[bool]) -> dict:
    """Exact two-sided McNemar test on paired top-1 outcomes."""
    from scipy.stats import binomtest

    only_a = sum(1 for x, y in zip(a, b) if x and not y)
    only_b = sum(1 for x, y in zip(a, b) if y and not x)
    n = only_a + only_b
    p = 1.0 if n == 0 else binomtest(min(only_a, only_b), n, 0.5).pvalue
    return {"only_first_correct": only_a, "only_second_correct": only_b, "p_value": min(1.0, p)}


def latency_stats(values: list[float]) -> dict:
    arr = np.asarray(values, dtype=float)
    return {
        "mean": float(arr.mean()),
        "p5": float(np.percentile(arr, 5)),
        "p50": float(np.percentile(arr, 50)),
        "p95": float(np.percentile(arr, 95)),
        "max": float(arr.max()),
        "under_5ms": float(np.mean(arr < 5.0)),
    }


# ---------------------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------------------


def _cpu_model() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine()


def build_queries(suites: list[Suite]) -> list[Query]:
    queries = []
    for suite in suites:
        index = get_index(suite.old_doc)
        for target in suite.targets:
            fp = index.fingerprint(target.old_el, target.css)
            queries.append(Query(len(queries), suite, target, fp))
    return queries


def evaluate(args: argparse.Namespace) -> dict:
    from sklearn.model_selection import GroupKFold

    t_start = time.perf_counter()
    suites = load_all(args.fixtures)
    if args.only_dev:
        suites = [s for s in suites if s.suite_id.rsplit("-", 1)[-1] in DEV_SUITE_NUMBERS]
    if args.limit_suites:
        suites = suites[: args.limit_suites]
    queries = build_queries(suites)
    n_suites = len(suites)
    print(f"loaded {n_suites} suites, {len(queries)} targets", flush=True)

    ranks: dict[str, list[int | None]] = {m: [None] * len(queries) for m in BASELINES + ENGINE}
    latency: dict[str, list[float]] = {m: [0.0] * len(queries) for m in BASELINES + ENGINE}
    breakdown: dict[str, list[dict]] = {m: [{}] * len(queries) for m in ENGINE}
    warm: dict[str, list[float]] = {m: [0.0] * len(queries) for m in ENGINE}

    # -- baselines -----------------------------------------------------------------------
    for q in queries:
        for name, fn in BASELINE_FUNCS.items():
            ranks[name][q.qid] = rank_of(q.target.new_el, fn(q))
            latency[name][q.qid] = time_baseline(q, fn, args.repeats)
    print("baselines done", flush=True)

    # -- candidate pools / features (shared by all learned rankers) -----------------------
    examples = [
        TrainingExample(q.fingerprint, q.suite.new_doc, q.target.new_el, q.group, q.target.css) for q in queries
    ]
    dataset: Dataset = build_dataset(examples, max_candidates=args.max_candidates)
    pool_sizes = np.bincount(dataset.query, minlength=len(queries))
    print(f"dataset: {dataset.X.shape[0]} candidate rows, pool recall {dataset.pool_recall:.3f}", flush=True)

    # -- heuristic -----------------------------------------------------------------------
    heuristic = HeuristicRanker()
    mismatches = 0
    for q in queries:
        mask = dataset.query == q.qid
        r = rank_positions(heuristic.score(dataset.X[mask]), dataset.y[mask])
        ranks["heuristic"][q.qid] = r
        result = Healer(q.suite.new_doc, ranker=heuristic).locate(q.fingerprint, selector=q.target.css)
        api_rank = rank_of(q.target.new_el, [c.element for c in result.candidates])
        mismatches += api_rank != r
    print(f"heuristic done (dataset/API rank mismatches: {mismatches})", flush=True)

    # -- learned rankers: GroupKFold by suite ---------------------------------------------
    qids = np.arange(len(queries))
    groups = np.array([q.group for q in queries])
    gkf = GroupKFold(n_splits=min(args.folds, n_suites))
    fold_models: dict[int, dict[str, Ranker]] = {}
    fold_of = np.zeros(len(queries), dtype=int)
    for fold, (train_idx, test_idx) in enumerate(gkf.split(qids, groups=groups)):
        train_mask = np.isin(dataset.query, train_idx)
        models: dict[str, Ranker] = {
            "logreg": train_logistic(dataset.X[train_mask], dataset.y[train_mask], C=args.lr_c),
            "random_forest": train_random_forest(dataset.X[train_mask], dataset.y[train_mask],
                                                 n_estimators=args.rf_trees, n_jobs=-1),
        }
        fold_models[fold] = models
        for qid in test_idx:
            fold_of[qid] = fold
            mask = dataset.query == qid
            for name, model in models.items():
                ranks[name][qid] = rank_positions(model.score(dataset.X[mask]), dataset.y[mask])
        print(f"fold {fold}: train suites={len(set(groups[train_idx]))} test suites={len(set(groups[test_idx]))}",
              flush=True)

    # -- leave-one-category-out ---------------------------------------------------------
    loco: dict[str, dict] = {}
    categories = sorted({q.suite.category for q in queries})
    if len(categories) > 1:
        loco_ranks: dict[str, list[int | None]] = {m: [None] * len(queries) for m in LEARNED}
        for cat in categories:
            test_idx = [q.qid for q in queries if q.suite.category == cat]
            train_mask = ~np.isin(dataset.query, test_idx)
            models = {
                "logreg": train_logistic(dataset.X[train_mask], dataset.y[train_mask], C=args.lr_c),
                "random_forest": train_random_forest(dataset.X[train_mask], dataset.y[train_mask],
                                                     n_estimators=args.rf_trees, n_jobs=-1),
            }
            for qid in test_idx:
                mask = dataset.query == qid
                for name, model in models.items():
                    loco_ranks[name][qid] = rank_positions(model.score(dataset.X[mask]), dataset.y[mask])
        for name in LEARNED:
            loco[name] = {
                "overall": summarize(loco_ranks[name]),
                "by_category": {
                    cat: summarize([loco_ranks[name][q.qid] for q in queries if q.suite.category == cat])
                    for cat in categories
                },
            }

    # -- latency (cold, fresh index per run) -------------------------------------------
    for q in queries:
        rankers = {"heuristic": heuristic, **fold_models[int(fold_of[q.qid])]}
        for name, ranker in rankers.items():
            stats = time_engine(q, ranker, args.repeats)
            latency[name][q.qid] = stats["total"]
            breakdown[name][q.qid] = stats
    for suite in suites:
        for name in ENGINE:
            members = [q for q in queries if q.suite is suite]
            if name == "heuristic":
                healer = Healer(suite.new_doc, ranker=heuristic)
                for q in members:
                    warm[name][q.qid] = time_warm(healer, q, args.repeats)
            else:
                for q in members:
                    healer = Healer(suite.new_doc, ranker=fold_models[int(fold_of[q.qid])][name])
                    warm[name][q.qid] = time_warm(healer, q, args.repeats)
    print("latency done", flush=True)

    parse_ms = []
    for suite in suites:
        times = []
        for _ in range(args.repeats):
            t0 = time.perf_counter()
            parse_html(suite.new_html)
            times.append((time.perf_counter() - t0) * 1000.0)
        parse_ms.append(statistics.median(times))

    # -- healed-selector verification (heuristic & LR top-1) ----------------------------
    selector_checks = {"checked": 0, "css_unique": 0, "xpath_unique": 0, "positional_css": 0}
    for q in queries:
        result = Healer(q.suite.new_doc, ranker=heuristic).locate(q.fingerprint, selector=q.target.css)
        if result.element is None:
            continue
        sugg = suggest_selectors(q.suite.new_doc, result.element)
        selector_checks["checked"] += 1
        css_hits = _safe_select(q.suite.new_doc, sugg.css)
        xpath_hits = _safe_select(q.suite.new_doc, sugg.xpath)
        selector_checks["css_unique"] += len(css_hits) == 1 and css_hits[0] is result.element
        selector_checks["xpath_unique"] += len(xpath_hits) == 1 and xpath_hits[0] is result.element
        selector_checks["positional_css"] += sugg.css_strategy in ("position", "anchored:position")

    # -- aggregate ----------------------------------------------------------------------
    def by(predicate: Callable[[Query], bool], method: str) -> dict:
        return summarize([ranks[method][q.qid] for q in queries if predicate(q)])

    mutation_tags = sorted({m for q in queries for m in q.target.mutations})
    results: dict = {
        "meta": {
            "date": date.today().isoformat(),
            "dom_healer_version": dom_healer.__version__,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "processor": _cpu_model(),
            "n_suites": n_suites,
            "n_targets": len(queries),
            "folds": gkf.get_n_splits(),
            "repeats": args.repeats,
            "max_candidates": args.max_candidates,
            "rf_trees": args.rf_trees,
            "lr_c": args.lr_c,
            "dev_suites": sorted({q.group for q in queries if q.split == "dev"}),
            "runtime_s": None,
        },
        "methods": {m: METHOD_LABELS[m] for m in BASELINES + ENGINE},
        "overall": {m: summarize(ranks[m]) for m in BASELINES + ENGINE},
        "by_category": {
            cat: {m: by(lambda q, c=cat: q.suite.category == c, m) for m in BASELINES + ENGINE} for cat in categories
        },
        "by_split": {
            split: {m: by(lambda q, s=split: q.split == s, m) for m in BASELINES + ENGINE} for split in ("dev", "heldout")
        },
        "by_mutation": {
            tag: {m: by(lambda q, t=tag: t in q.target.mutations, m) for m in BASELINES + ENGINE} for tag in mutation_tags
        },
        "in_shadow_v2": {m: by(lambda q: q.suite.new_doc.shadow_depth(q.target.new_el) > 0, m) for m in BASELINES + ENGINE},
        "loco": loco,
        "latency_ms": {m: latency_stats(latency[m]) for m in BASELINES + ENGINE},
        "latency_warm_ms": {m: latency_stats(warm[m]) for m in ENGINE},
        "latency_breakdown_ms": {
            m: {k: float(np.median([b[k] for b in breakdown[m]])) for k in breakdown[m][0]} for m in ENGINE
        },
        "parse_ms": latency_stats(parse_ms),
        "candidate_pool": {
            "recall": dataset.pool_recall,
            "mean_size": float(pool_sizes.mean()),
            "max_size": int(pool_sizes.max()),
        },
        "selector_checks": selector_checks,
        "mcnemar_top1": {
            "heuristic_vs_logreg": mcnemar([r == 1 for r in ranks["heuristic"]], [r == 1 for r in ranks["logreg"]]),
            "heuristic_vs_random_forest": mcnemar(
                [r == 1 for r in ranks["heuristic"]], [r == 1 for r in ranks["random_forest"]]
            ),
            "logreg_vs_random_forest": mcnemar(
                [r == 1 for r in ranks["logreg"]], [r == 1 for r in ranks["random_forest"]]
            ),
        },
        "page_stats": {
            "elements_v2_mean": float(np.mean([len(s.new_doc) for s in suites])),
            "elements_v2_max": int(max(len(s.new_doc) for s in suites)),
            "bytes_v2_mean": float(np.mean([len(s.new_html.encode()) for s in suites])),
        },
        "queries": [
            {
                "suite": q.group,
                "category": q.suite.category,
                "target": q.target.id,
                "description": q.target.description,
                "mutations": q.target.mutations,
                "split": q.split,
                "in_shadow_v2": q.suite.new_doc.shadow_depth(q.target.new_el) > 0,
                "ranks": {m: ranks[m][q.qid] for m in BASELINES + ENGINE},
                "latency_ms": {m: round(latency[m][q.qid], 4) for m in BASELINES + ENGINE},
            }
            for q in queries
        ],
    }

    # -- feature importance (models trained on all suites) -------------------------------
    full_lr = train_logistic(dataset.X, dataset.y, C=args.lr_c, name="logreg",
                             meta={"trained_on_suites": n_suites, "trained_on_targets": len(queries),
                                   "date": date.today().isoformat(),
                                   "cv_top1": results["overall"]["logreg"]["top1"],
                                   "cv_top3": results["overall"]["logreg"]["top3"],
                                   "max_candidates": args.max_candidates})
    full_rf = train_random_forest(dataset.X, dataset.y, n_estimators=args.rf_trees, n_jobs=-1)
    lr_weights = sorted(zip(FEATURE_NAMES, full_lr.coef.tolist()), key=lambda kv: -abs(kv[1]))
    rf_imp = sorted(zip(FEATURE_NAMES, full_rf.estimator.feature_importances_.tolist()), key=lambda kv: -kv[1])
    results["feature_importance"] = {
        "logreg_standardized_coef": lr_weights[:15],
        "random_forest_importance": rf_imp[:15],
    }
    if args.export_model:
        out = ROOT / "src" / "dom_healer" / "data" / "linear_ranker.json"
        full_lr.save(out)
        print(f"exported bundled model -> {out.relative_to(ROOT)}", flush=True)

    results["meta"]["runtime_s"] = round(time.perf_counter() - t_start, 1)
    return results


# ---------------------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------------------


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def _ci(ci: tuple[float, float]) -> str:
    return f"{100 * ci[0]:.0f}–{100 * ci[1]:.0f}"


def markdown_summary(res: dict) -> str:
    meta = res["meta"]
    order = BASELINES + ENGINE
    lines = [
        f"# Benchmark results ({meta['date']})",
        "",
        f"{meta['n_suites']} suites · {meta['n_targets']} targets · learned rankers: {meta['folds']}-fold GroupKFold "
        f"by suite · latency = median of {meta['repeats']} cold runs per target · Python {meta['python']} · "
        f"{meta['processor']}",
        "",
        "## Selector recovery accuracy",
        "",
        "| Method | Top-1 | 95% CI | Top-3 | 95% CI | p50 latency (ms) | p95 latency (ms) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for m in order:
        o, lat = res["overall"][m], res["latency_ms"][m]
        lines.append(
            f"| {res['methods'][m]} | {_pct(o['top1'])} | {_ci(o['top1_ci'])} | {_pct(o['top3'])} | {_ci(o['top3_ci'])} "
            f"| {lat['p50']:.3f} | {lat['p95']:.3f} |"
        )
    lines += ["", "## Top-1 by category", "", "| Method | " + " | ".join(res["by_category"]) + " |",
              "|---|" + "---:|" * len(res["by_category"])]
    for m in order:
        cells = [f"{_pct(res['by_category'][c][m]['top1'])}" for c in res["by_category"]]
        lines.append(f"| {res['methods'][m]} | " + " | ".join(cells) + " |")
    lines += ["", "## Top-1: development suites vs. never-inspected suites", "",
              "| Method | dev (01–03, n={}) | held-out (04–10, n={}) |".format(
                  res["by_split"]["dev"][order[0]]["n"], res["by_split"]["heldout"][order[0]]["n"]),
              "|---|---:|---:|"]
    for m in order:
        lines.append(f"| {res['methods'][m]} | {_pct(res['by_split']['dev'][m]['top1'])} | "
                     f"{_pct(res['by_split']['heldout'][m]['top1'])} |")
    lines += ["", "## Top-1 by mutation type (targets carrying the tag)", "",
              "| Mutation | n | " + " | ".join(res["methods"][m] for m in ("css", "attr_fallback") + ENGINE) + " |",
              "|---|---:|" + "---:|" * (2 + len(ENGINE))]
    for tag, row in res["by_mutation"].items():
        cells = [_pct(row[m]["top1"]) for m in ("css", "attr_fallback") + ENGINE]
        lines.append(f"| {tag} | {row['heuristic']['n']} | " + " | ".join(cells) + " |")
    if res["loco"]:
        lines += ["", "## Leave-one-category-out (train on 3 categories, test on the 4th)", "",
                  "| Model | Top-1 | Top-3 | " + " | ".join(res["loco"]["logreg"]["by_category"]) + " |",
                  "|---|---:|---:|" + "---:|" * len(res["loco"]["logreg"]["by_category"])]
        for m, row in res["loco"].items():
            cells = [_pct(v["top1"]) for v in row["by_category"].values()]
            lines.append(f"| {res['methods'][m]} | {_pct(row['overall']['top1'])} | {_pct(row['overall']['top3'])} | "
                         + " | ".join(cells) + " |")
    lines += ["", "## Latency (ms)", "",
              "| Method | cold p50 | cold p95 | cold max | % < 5 ms | warm p50 (index reused) |", "|---|---:|---:|---:|---:|---:|"]
    for m in order:
        lat = res["latency_ms"][m]
        warm = res["latency_warm_ms"].get(m)
        warm_p50 = "" if warm is None else f"{warm['p50']:.3f}"
        lines.append(f"| {res['methods'][m]} | {lat['p50']:.3f} | {lat['p95']:.3f} | {lat['max']:.3f} | "
                     f"{_pct(lat['under_5ms'])} | {warm_p50} |")
    pb = res["parse_ms"]
    lines += ["", f"HTML parsing of the v2 page (not included above): p50 {pb['p50']:.2f} ms, p95 {pb['p95']:.2f} ms.",
              "", "Median cold breakdown (ms):", "", "| Method | index | retrieval | features | ranking | synthesis |",
              "|---|---:|---:|---:|---:|---:|"]
    for m in ENGINE:
        b = res["latency_breakdown_ms"][m]
        lines.append(f"| {res['methods'][m]} | {b['index']:.3f} | {b['retrieval']:.3f} | {b['features']:.3f} | "
                     f"{b['ranking']:.3f} | {b['synthesis']:.3f} |")
    cp = res["candidate_pool"]
    sc = res["selector_checks"]
    lines += ["", "## Other diagnostics", "",
              f"* Candidate pool recall (true element among the {res['meta']['max_candidates']} fully-scored candidates): "
              f"{_pct(cp['recall'])}; mean pool size {cp['mean_size']:.1f}.",
              f"* Healed selectors verified unique in v2: CSS {sc['css_unique']}/{sc['checked']}, XPath "
              f"{sc['xpath_unique']}/{sc['checked']} (positional CSS fallback used {sc['positional_css']} times).",
              "* McNemar exact test on paired top-1 outcomes:"]
    for name, t in res["mcnemar_top1"].items():
        lines.append(f"  * {name.replace('_', ' ')}: {t['only_first_correct']} vs {t['only_second_correct']} "
                     f"discordant, p = {t['p_value']:.3g}")
    lines += ["", "## Most influential features", "", "| LogisticRegression (std. coef) | RandomForest (importance) |",
              "|---|---|"]
    for (ln, lv), (rn, rv) in zip(res["feature_importance"]["logreg_standardized_coef"][:10],
                                  res["feature_importance"]["random_forest_importance"][:10]):
        lines.append(f"| `{ln}` {lv:+.2f} | `{rn}` {rv:.3f} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fixtures", type=Path, default=FIXTURES_DIR)
    parser.add_argument("--out", type=Path, default=HERE / "results")
    parser.add_argument("--plots", type=Path, default=ROOT / "docs" / "assets")
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--max-candidates", type=int, default=24)
    parser.add_argument("--rf-trees", type=int, default=200)
    parser.add_argument("--lr-c", type=float, default=1.0)
    parser.add_argument("--limit-suites", type=int, default=0, help="debug: only use the first N suites")
    parser.add_argument("--only-dev", action="store_true", help="debug: only use development suites (01-03)")
    parser.add_argument("--export-model", action="store_true", help="save the all-suites LR model into the package")
    parser.add_argument("--no-plots", action="store_true")
    args = parser.parse_args(argv)

    results = evaluate(args)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "results.json").write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
    (args.out / "summary.md").write_text(markdown_summary(results), encoding="utf-8")
    print(markdown_summary(results))
    if not args.no_plots:
        from plots import render_all

        for path in render_all(results, args.plots):
            print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
