from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("sklearn")

from dom_healer.dom import parse_html  # noqa: E402
from dom_healer.features import FEATURE_NAMES  # noqa: E402
from dom_healer.healer import Healer, capture_fingerprint  # noqa: E402
from dom_healer.ml import (  # noqa: E402
    TrainingExample,
    build_dataset,
    query_matrix,
    rank_positions,
    train_logistic,
    train_random_forest,
)
from dom_healer.rankers import LinearRanker, SklearnRanker  # noqa: E402

PAIRS = [
    ("#nl-email", "input[name=email]"),
    ("#weekly", "input[name=weekly]"),
    ("#cart-link", "nav a[href^='/cart']"),
    ("form#newsletter button[type=submit]", "form button[type=submit]"),
    ("button[data-testid='add-SK-200']", "product-card button"),
    ("//tr[td[1]='#1002']//a[@class='view']", "a[href='/o/1002']"),
]


@pytest.fixture
def examples(old_html, new_html):
    old_doc, new_doc = parse_html(old_html), parse_html(new_html)
    out = []
    for i, (old_sel, new_sel) in enumerate(PAIRS):
        fp = capture_fingerprint(old_doc, old_sel)
        out.append(TrainingExample(fp, new_doc, new_doc.select_one(new_sel), group=f"g{i % 2}", selector=old_sel))
    return out


def test_build_dataset(examples):
    ds = build_dataset(examples, max_candidates=8)
    assert ds.X.shape[1] == len(FEATURE_NAMES)
    assert ds.X.shape[0] == len(ds.y) == len(ds.groups) == len(ds.query)
    assert ds.n_queries == len(PAIRS)
    assert ds.pool_recall == 1.0
    assert int(ds.y.sum()) == len(PAIRS)
    empty = build_dataset([])
    assert empty.X.shape == (0, len(FEATURE_NAMES)) and empty.pool_recall == 0.0


def test_query_matrix_ignores_invalid_selector(examples):
    ex = examples[0]
    ex.selector = "div["
    X, elements = query_matrix(ex, max_candidates=5)
    assert X.shape == (len(elements), len(FEATURE_NAMES))


def test_train_models_and_rank(examples, new_html):
    ds = build_dataset(examples, max_candidates=8)
    lr = train_logistic(ds.X, ds.y, meta={"k": 1})
    assert isinstance(lr, LinearRanker) and lr.meta == {"k": 1}
    rf = train_random_forest(ds.X, ds.y, n_estimators=10, random_state=1)
    assert isinstance(rf, SklearnRanker) and rf.estimator.n_jobs == 1
    for model in (lr, rf):
        for qid in range(ds.n_queries):
            mask = ds.query == qid
            scores = model.score(ds.X[mask])
            assert scores.shape == (int(mask.sum()),)
            assert rank_positions(scores, ds.y[mask]) is not None
    # learned models plug straight into the Healer
    healer = Healer(new_html, ranker=lr)
    assert healer.locate(examples[0].fingerprint).element is not None


def test_rank_positions():
    assert rank_positions([0.1, 0.9, 0.5], [0, 0, 1]) == 2
    assert rank_positions([0.5, 0.5], [0, 1]) == 2  # ties broken by pool order
    assert rank_positions([0.5, 0.5], [0, 0]) is None
    assert rank_positions(np.array([0.2]), np.array([1])) == 1
