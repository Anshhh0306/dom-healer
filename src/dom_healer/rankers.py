"""Candidate rankers: a hand-weighted heuristic and learned (linear / scikit-learn) models.

A ranker maps a feature matrix (rows = candidates, columns =
:data:`~dom_healer.features.FEATURE_NAMES`) to one score per candidate; higher
is better.  Scores are in ``[0, 1]`` and are used as the heal *confidence*.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from importlib import resources
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import numpy as np

from dom_healer.features import FEATURE_NAMES

DEFAULT_MODEL_RESOURCE = "linear_ranker.json"

#: Hand-set weights for :class:`HeuristicRanker`.  They encode priors about which
#: signals survive redesigns (accessible name, label/heading/row context, test
#: attributes) and were fixed before the benchmark fixtures existed.
HEURISTIC_WEIGHTS: dict[str, float] = {
    "tag_eq": 1.0,
    "family_eq": 1.0,
    "role_eq": 1.0,
    "id_eq": 2.0,
    "id_token_sim": 0.5,
    "name_eq": 2.0,
    "type_eq": 1.0,
    "testid_eq": 3.0,
    "data_jaccard": 1.5,
    "data_key_jaccard": 0.5,
    "aria_label_sim": 2.0,
    "attr_jaccard": 1.0,
    "placeholder_sim": 1.5,
    "href_sim": 1.5,
    "name_sim": 3.0,
    "text_sim": 1.5,
    "full_text_sim": 1.0,
    "label_sim": 2.5,
    "heading_sim": 2.0,
    "context_sim": 2.0,
    "next_context_sim": 1.0,
    "row_sim": 3.0,
    "column_sim": 2.0,
    "form_sim": 1.0,
    "landmark_eq": 0.5,
    "class_jaccard": 0.5,
    "class_token_jaccard": 1.0,
    "ancestor_jaccard": 1.0,
    "parent_sim": 0.5,
    "prev_sibling_sim": 0.75,
    "next_sibling_sim": 0.75,
    "sibling_pos_sim": 0.5,
    "sibling_count_sim": 0.25,
    "tag_path_sim": 0.75,
    "semantic_path_sim": 1.0,
    "depth_sim": 0.25,
    "position_sim": 0.5,
    "children_sim": 0.5,
    "shadow_eq": 0.25,
    "retrieval": 1.0,
}
HIDDEN_PENALTY = 0.25


@runtime_checkable
class Ranker(Protocol):
    name: str

    def score(self, X: np.ndarray) -> np.ndarray:  # pragma: no cover - protocol
        ...


class HeuristicRanker:
    """Weighted average of the *applicable* features minus a hidden-element penalty."""

    name = "heuristic"

    def __init__(self, weights: Mapping[str, float] | None = None, hidden_penalty: float = HIDDEN_PENALTY) -> None:
        weights = dict(HEURISTIC_WEIGHTS if weights is None else weights)
        unknown = set(weights) - set(FEATURE_NAMES)
        if unknown:
            raise ValueError(f"unknown feature(s) in weights: {sorted(unknown)}")
        self.weights = weights
        self.hidden_penalty = float(hidden_penalty)
        self._w = np.array([weights.get(n, 0.0) for n in FEATURE_NAMES], dtype=float)
        self._w[FEATURE_NAMES.index("hidden_mismatch")] = 0.0
        self._hidden = FEATURE_NAMES.index("hidden_mismatch")

    def score(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        if X.ndim != 2 or X.shape[1] != len(FEATURE_NAMES):
            raise ValueError(f"expected a (n, {len(FEATURE_NAMES)}) feature matrix, got {X.shape}")
        applicable = ~np.isnan(X)
        weighted = np.where(applicable, X, 0.0) * self._w
        denom = (applicable * self._w).sum(axis=1)
        denom[denom == 0] = 1.0
        scores = weighted.sum(axis=1) / denom - self.hidden_penalty * np.nan_to_num(X[:, self._hidden])
        return np.clip(scores, 0.0, 1.0)


class LinearRanker:
    """Logistic-regression ranker evaluated with NumPy only (no scikit-learn at runtime)."""

    def __init__(
        self,
        feature_names: Sequence[str],
        mean: Sequence[float],
        scale: Sequence[float],
        coef: Sequence[float],
        intercept: float,
        fill_value: float = -1.0,
        name: str = "linear",
        meta: Mapping[str, Any] | None = None,
    ) -> None:
        if not (len(feature_names) == len(mean) == len(scale) == len(coef)):
            raise ValueError("feature_names, mean, scale and coef must have the same length")
        self.name = name
        self.feature_names = tuple(feature_names)
        self.mean = np.asarray(mean, dtype=float)
        self.scale = np.asarray(scale, dtype=float)
        self.scale[self.scale == 0] = 1.0
        self.coef = np.asarray(coef, dtype=float)
        self.intercept = float(intercept)
        self.fill_value = float(fill_value)
        self.meta = dict(meta or {})
        index = {n: i for i, n in enumerate(FEATURE_NAMES)}
        self._columns = [index.get(n, -1) for n in self.feature_names]

    def _align(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        out = np.full((X.shape[0], len(self._columns)), self.fill_value)
        for j, col in enumerate(self._columns):
            if col >= 0:
                out[:, j] = X[:, col]
        return np.where(np.isnan(out), self.fill_value, out)

    def decision_function(self, X: np.ndarray) -> np.ndarray:
        Z = (self._align(X) - self.mean) / self.scale
        return Z @ self.coef + self.intercept

    def score(self, X: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-self.decision_function(X)))

    # -- persistence ------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "linear",
            "name": self.name,
            "feature_names": list(self.feature_names),
            "mean": self.mean.tolist(),
            "scale": self.scale.tolist(),
            "coef": self.coef.tolist(),
            "intercept": self.intercept,
            "fill_value": self.fill_value,
            "meta": self.meta,
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=1) + "\n", encoding="utf-8")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> LinearRanker:
        if data.get("type", "linear") != "linear":
            raise ValueError(f"not a linear ranker: type={data.get('type')!r}")
        return cls(
            feature_names=data["feature_names"],
            mean=data["mean"],
            scale=data["scale"],
            coef=data["coef"],
            intercept=data["intercept"],
            fill_value=data.get("fill_value", -1.0),
            name=data.get("name", "linear"),
            meta=data.get("meta"),
        )

    @classmethod
    def load(cls, path: str | Path) -> LinearRanker:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


class SklearnRanker:
    """Wrap any fitted scikit-learn classifier exposing ``predict_proba``."""

    def __init__(self, estimator: Any, name: str = "sklearn", fill_value: float = -1.0) -> None:
        if not hasattr(estimator, "predict_proba"):
            raise TypeError("estimator must implement predict_proba")
        self.estimator = estimator
        self.name = name
        self.fill_value = float(fill_value)

    def score(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        X = np.where(np.isnan(X), self.fill_value, X)
        proba = self.estimator.predict_proba(X)
        return proba[:, list(self.estimator.classes_).index(1)] if proba.shape[1] > 1 else proba[:, 0]


def load_default_model() -> LinearRanker | None:
    """The bundled logistic-regression ranker, or ``None`` if the package ships without one."""
    try:
        payload = resources.files("dom_healer").joinpath("data", DEFAULT_MODEL_RESOURCE).read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return None
    return LinearRanker.from_dict(json.loads(payload))


def get_ranker(spec: str | Ranker | None = None) -> Ranker:
    """Resolve a ranker from a name (``"heuristic"``, ``"linear"``, ``"auto"``), a JSON path, or an instance."""
    if spec is None or spec == "auto":
        model = load_default_model()
        return model if model is not None else HeuristicRanker()
    if isinstance(spec, str):
        if spec == "heuristic":
            return HeuristicRanker()
        if spec == "linear":
            model = load_default_model()
            if model is None:
                raise ValueError("no bundled linear model found; train one with dom_healer.ml")
            return model
        path = Path(spec)
        if path.suffix == ".json" and path.is_file():
            return LinearRanker.load(path)
        raise ValueError(f"unknown ranker {spec!r} (use 'auto', 'heuristic', 'linear' or a .json model path)")
    if isinstance(spec, Ranker):
        return spec
    raise TypeError(f"cannot use {type(spec).__name__} as a ranker")
