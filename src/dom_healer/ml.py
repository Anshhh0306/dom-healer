"""Training utilities for learned candidate rankers.

Requires scikit-learn (``pip install "dom-healer[ml]"``).  Training data are
*(stored fingerprint, new document, true element)* triples; each one becomes a
query whose candidate pool is produced exactly as at inference time
(:meth:`PageIndex.candidates`), labelled 1 for the true element and 0
otherwise.  A pointwise classifier on these pairwise structural-diff features
is then used to rank candidates.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from dom_healer.dom import Document, Element, SelectorError
from dom_healer.features import FEATURE_NAMES, feature_matrix
from dom_healer.fingerprint import ElementFingerprint
from dom_healer.healer import DEFAULT_MAX_CANDIDATES, get_index
from dom_healer.rankers import LinearRanker, SklearnRanker

FILL_VALUE = -1.0


def _require_sklearn() -> None:
    try:
        import sklearn  # noqa: F401
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise ImportError('scikit-learn is required for training: pip install "dom-healer[ml]"') from exc


@dataclass
class TrainingExample:
    """One query: a fingerprint captured on the old page and its true element on the new page."""

    fingerprint: ElementFingerprint
    document: Document
    target: Element
    group: str = ""
    selector: str | None = None


@dataclass
class Dataset:
    X: np.ndarray
    y: np.ndarray
    groups: np.ndarray
    query: np.ndarray
    in_pool: list[bool] = field(default_factory=list)

    @property
    def n_queries(self) -> int:
        return len(self.in_pool)

    @property
    def pool_recall(self) -> float:
        return float(np.mean(self.in_pool)) if self.in_pool else 0.0


def query_matrix(example: TrainingExample, max_candidates: int = DEFAULT_MAX_CANDIDATES) -> tuple[np.ndarray, list[Element]]:
    """Feature matrix and candidate elements for one example (same pool as inference)."""
    index = get_index(example.document)
    extra: list[Element] = []
    if example.selector:
        try:
            extra = example.document.select(example.selector)[:5]
        except SelectorError:
            extra = []
    pool = index.candidates(example.fingerprint, max_candidates, extra)
    elements = [el for el, _ in pool]
    X = feature_matrix(example.fingerprint, [index.fingerprint(el) for el in elements], [s for _, s in pool])
    return X, elements


def build_dataset(examples: Iterable[TrainingExample], max_candidates: int = DEFAULT_MAX_CANDIDATES) -> Dataset:
    """Turn examples into a stacked (X, y, groups, query-id) dataset."""
    xs, ys, groups, queries, in_pool = [], [], [], [], []
    for qid, ex in enumerate(examples):
        X, elements = query_matrix(ex, max_candidates)
        labels = np.array([1 if el is ex.target else 0 for el in elements], dtype=int)
        in_pool.append(bool(labels.any()))
        xs.append(X)
        ys.append(labels)
        groups.extend([ex.group] * len(elements))
        queries.extend([qid] * len(elements))
    if not xs:
        empty = np.zeros((0, len(FEATURE_NAMES)))
        return Dataset(empty, np.zeros(0, dtype=int), np.array([], dtype=object), np.zeros(0, dtype=int), [])
    return Dataset(
        X=np.vstack(xs),
        y=np.concatenate(ys),
        groups=np.array(groups, dtype=object),
        query=np.array(queries, dtype=int),
        in_pool=in_pool,
    )


def _filled(X: np.ndarray) -> np.ndarray:
    return np.where(np.isnan(X), FILL_VALUE, X)


def train_logistic(X: np.ndarray, y: np.ndarray, C: float = 1.0, name: str = "logreg",
                   meta: dict[str, Any] | None = None) -> LinearRanker:
    """Fit standardised logistic regression and export it as a NumPy-only :class:`LinearRanker`."""
    _require_sklearn()
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    Xf = _filled(np.asarray(X, dtype=float))
    scaler = StandardScaler().fit(Xf)
    model = LogisticRegression(C=C, class_weight="balanced", max_iter=5000)
    model.fit(scaler.transform(Xf), np.asarray(y))
    return LinearRanker(
        feature_names=FEATURE_NAMES,
        mean=scaler.mean_,
        scale=scaler.scale_,
        coef=model.coef_[0],
        intercept=float(model.intercept_[0]),
        fill_value=FILL_VALUE,
        name=name,
        meta=meta,
    )


def train_random_forest(
    X: np.ndarray,
    y: np.ndarray,
    n_estimators: int = 300,
    min_samples_leaf: int = 2,
    max_depth: int | None = None,
    random_state: int = 0,
    n_jobs: int | None = None,
    name: str = "random_forest",
) -> SklearnRanker:
    """Fit a class-balanced random forest wrapped as a :class:`SklearnRanker`."""
    _require_sklearn()
    from sklearn.ensemble import RandomForestClassifier

    model = RandomForestClassifier(
        n_estimators=n_estimators,
        min_samples_leaf=min_samples_leaf,
        max_depth=max_depth,
        max_features="sqrt",
        class_weight="balanced_subsample",
        random_state=random_state,
        n_jobs=n_jobs,
    )
    model.fit(_filled(np.asarray(X, dtype=float)), np.asarray(y))
    model.n_jobs = 1  # single-threaded inference: lower latency for small candidate pools
    return SklearnRanker(model, name=name, fill_value=FILL_VALUE)


def rank_positions(scores: Sequence[float], labels: Sequence[int]) -> int | None:
    """1-based rank of the positive candidate under ``scores`` (ties broken by pool order), or None."""
    labels = list(labels)
    if 1 not in labels:
        return None
    order = sorted(range(len(scores)), key=lambda i: (-scores[i], i))
    return order.index(labels.index(1)) + 1
