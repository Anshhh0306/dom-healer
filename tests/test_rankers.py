from __future__ import annotations

import json
import math

import numpy as np
import pytest

from dom_healer import rankers
from dom_healer.features import FEATURE_NAMES
from dom_healer.rankers import (
    HeuristicRanker,
    LinearRanker,
    Ranker,
    SklearnRanker,
    get_ranker,
    load_default_model,
)

N = len(FEATURE_NAMES)


def _row(**values: float) -> np.ndarray:
    row = np.full(N, math.nan)
    for name, value in values.items():
        row[FEATURE_NAMES.index(name)] = value
    return row


def test_heuristic_uses_only_applicable_features():
    ranker = HeuristicRanker()
    X = np.vstack([
        _row(tag_eq=1.0, name_sim=1.0, hidden_mismatch=0.0),
        _row(tag_eq=1.0, name_sim=0.2, hidden_mismatch=0.0),
        _row(tag_eq=1.0, name_sim=1.0, hidden_mismatch=1.0),
    ])
    s = ranker.score(X)
    assert s[0] == pytest.approx(1.0)
    assert s[0] > s[1]
    assert s[2] == pytest.approx(1.0 - rankers.HIDDEN_PENALTY)
    assert ranker.score(np.vstack([_row()]))[0] == 0.0  # nothing applicable
    assert isinstance(ranker, Ranker)


def test_heuristic_validation():
    with pytest.raises(ValueError):
        HeuristicRanker({"not_a_feature": 1.0})
    with pytest.raises(ValueError):
        HeuristicRanker().score(np.zeros((2, 3)))
    custom = HeuristicRanker({"tag_eq": 1.0}, hidden_penalty=0.0)
    assert custom.score(np.vstack([_row(tag_eq=0.5, hidden_mismatch=1.0)]))[0] == pytest.approx(0.5)


def _linear(names=FEATURE_NAMES) -> LinearRanker:
    k = len(names)
    return LinearRanker(names, mean=[0.0] * k, scale=[1.0] * (k - 1) + [0.0], coef=[0.1] * k, intercept=-0.5,
                        meta={"note": "test"})


def test_linear_ranker_roundtrip(tmp_path):
    model = _linear()
    X = np.vstack([_row(tag_eq=1.0, name_sim=1.0), _row(tag_eq=0.0)])
    s = model.score(X)
    assert s.shape == (2,) and np.all((s > 0) & (s < 1)) and s[0] > s[1]
    path = tmp_path / "m.json"
    model.save(path)
    loaded = LinearRanker.load(path)
    assert np.allclose(loaded.score(X), s)
    assert loaded.meta == {"note": "test"}
    assert LinearRanker.from_dict(model.to_dict()).name == "linear"
    with pytest.raises(ValueError):
        LinearRanker.from_dict({**model.to_dict(), "type": "forest"})
    with pytest.raises(ValueError):
        LinearRanker(["a"], [0.0, 1.0], [1.0], [1.0], 0.0)


def test_linear_ranker_aligns_columns_by_name():
    model = LinearRanker(["tag_eq", "unknown_feature"], mean=[0, 0], scale=[1, 1], coef=[2.0, 5.0], intercept=0.0,
                         fill_value=0.0)
    X = np.vstack([_row(tag_eq=1.0), _row(tag_eq=0.0)])
    assert np.allclose(model.decision_function(X), [2.0, 0.0])


class _FakeEstimator:
    def __init__(self, classes):
        self.classes_ = np.array(classes)

    def predict_proba(self, X):
        p = np.clip(np.nan_to_num(X[:, 0], nan=0.0), 0, 1)
        if len(self.classes_) == 1:
            return p[:, None]
        cols = [1 - p, p] if list(self.classes_) == [0, 1] else [p, 1 - p]
        return np.column_stack(cols)


def test_sklearn_ranker_wrapper():
    X = np.vstack([_row(tag_eq=0.9), _row(tag_eq=0.1)])
    assert np.allclose(SklearnRanker(_FakeEstimator([0, 1])).score(X), [0.9, 0.1])
    assert np.allclose(SklearnRanker(_FakeEstimator([1, 0])).score(X), [0.9, 0.1])
    assert np.allclose(SklearnRanker(_FakeEstimator([1])).score(X), [0.9, 0.1])
    assert SklearnRanker(_FakeEstimator([0, 1])).score(np.zeros((0, N))).shape == (0,)
    with pytest.raises(TypeError):
        SklearnRanker(object())


def test_default_model_and_get_ranker(tmp_path, monkeypatch):
    bundled = load_default_model()
    assert isinstance(bundled, LinearRanker) and bundled.meta["trained_on_suites"] == 40
    assert isinstance(get_ranker("linear"), LinearRanker)
    assert isinstance(get_ranker("auto"), HeuristicRanker)
    assert isinstance(get_ranker("heuristic"), HeuristicRanker)
    instance = HeuristicRanker()
    assert get_ranker(instance) is instance
    path = tmp_path / "model.json"
    path.write_text(json.dumps(_linear().to_dict()))
    assert isinstance(get_ranker(str(path)), LinearRanker)
    with pytest.raises(ValueError):
        get_ranker("nonsense")
    with pytest.raises(TypeError):
        get_ranker(3.5)  # type: ignore[arg-type]

    monkeypatch.setattr(rankers, "DEFAULT_MODEL_RESOURCE", "does-not-exist.json")
    assert load_default_model() is None
    assert isinstance(get_ranker(None), HeuristicRanker)
    with pytest.raises(ValueError):
        get_ranker("linear")
