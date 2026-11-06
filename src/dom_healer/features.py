"""Pairwise structural-diff features between a stored fingerprint and a candidate element.

Every feature is a similarity in ``[0, 1]`` (``hidden_mismatch`` is a 0/1
penalty).  A feature is ``NaN`` when it is *not applicable* because the
original element had no such signal (e.g. ``id_eq`` when the original had no
id) — NaN-ness therefore only depends on the stored fingerprint and is
constant across the candidates of one query.  :func:`feature_matrix` also adds
query-relative columns (``x - max(x)`` over the candidate pool) so pointwise
models can reason about "best in this page" rather than absolute values.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from dom_healer.fingerprint import TEST_ATTRS, ElementFingerprint
from dom_healer.text import class_tokens, identifier_tokens, jaccard, lcs_ratio, text_similarity

NAN = math.nan

RAW_FEATURES: tuple[str, ...] = (
    "tag_eq",
    "family_eq",
    "role_eq",
    "id_eq",
    "id_token_sim",
    "name_eq",
    "type_eq",
    "testid_eq",
    "data_jaccard",
    "data_key_jaccard",
    "aria_label_sim",
    "attr_jaccard",
    "placeholder_sim",
    "href_sim",
    "name_sim",
    "text_sim",
    "full_text_sim",
    "label_sim",
    "heading_sim",
    "context_sim",
    "next_context_sim",
    "row_sim",
    "column_sim",
    "form_sim",
    "landmark_eq",
    "class_jaccard",
    "class_token_jaccard",
    "ancestor_jaccard",
    "parent_sim",
    "prev_sibling_sim",
    "next_sibling_sim",
    "sibling_pos_sim",
    "sibling_count_sim",
    "tag_path_sim",
    "semantic_path_sim",
    "depth_sim",
    "position_sim",
    "children_sim",
    "hidden_mismatch",
    "shadow_eq",
    "retrieval",
)

#: Raw features that also get a query-relative ``rel_<name>`` column.
RELATIVE_OF: tuple[str, ...] = (
    "name_sim",
    "text_sim",
    "full_text_sim",
    "label_sim",
    "heading_sim",
    "context_sim",
    "row_sim",
    "column_sim",
    "testid_eq",
    "data_jaccard",
    "aria_label_sim",
    "class_token_jaccard",
    "ancestor_jaccard",
    "tag_path_sim",
    "retrieval",
)

FEATURE_NAMES: tuple[str, ...] = RAW_FEATURES + tuple(f"rel_{n}" for n in RELATIVE_OF)
_RAW_INDEX = {name: i for i, name in enumerate(RAW_FEATURES)}
_REL_COLUMNS = [_RAW_INDEX[n] for n in RELATIVE_OF]

_OTHER_ATTRS_EXCLUDED = frozenset({"name", "type", "role", "placeholder", "href", "aria-label"})


class _Derived:
    """Pre-computed sets/tuples for one fingerprint (cached on the instance)."""

    __slots__ = (
        "classes", "class_toks", "data_kv", "data_keys", "other_kv", "test_values", "aria_label", "placeholder",
        "href", "name", "type", "id_toks", "anc", "children", "tag_path", "sem_path", "prev", "next", "rel_pos",
    )

    def __init__(self, fp: ElementFingerprint) -> None:
        attrs = fp.attrs
        self.classes = frozenset(fp.classes)
        self.class_toks = class_tokens(tuple(fp.classes))
        data = {k: v.lower() for k, v in attrs.items() if k.startswith("data-") and k not in TEST_ATTRS}
        self.data_kv = frozenset(f"{k}={v}" for k, v in data.items())
        self.data_keys = frozenset(data)
        self.other_kv = frozenset(
            f"{k}={v.lower()}"
            for k, v in attrs.items()
            if not k.startswith(("data-", "aria-")) and k not in _OTHER_ATTRS_EXCLUDED
        )
        self.test_values = frozenset(attrs[k].lower() for k in TEST_ATTRS if attrs.get(k))
        self.aria_label = (attrs.get("aria-label") or "").lower()
        self.placeholder = (attrs.get("placeholder") or "").lower()
        self.href = (attrs.get("href") or "").lower()
        self.name = (attrs.get("name") or "").lower()
        self.type = attrs.get("type") or ""
        self.id_toks = frozenset(identifier_tokens(fp.id)) if fp.id else frozenset()
        self.anc = frozenset(fp.ancestor_tokens)
        self.children = frozenset(fp.children)
        self.tag_path = tuple(fp.tag_path)
        self.sem_path = tuple(fp.semantic_path)
        self.prev = tuple(fp.prev_sibling.split("|", 1)) if fp.prev_sibling else ()
        self.next = tuple(fp.next_sibling.split("|", 1)) if fp.next_sibling else ()
        self.rel_pos = fp.sibling_index / max(1, fp.sibling_count - 1) if fp.sibling_count > 1 else 0.5


def derived(fp: ElementFingerprint) -> _Derived:
    d = fp.__dict__.get("_derived")
    if d is None:
        d = _Derived(fp)
        fp.__dict__["_derived"] = d
    return d


def _sig_sim(a: tuple[str, ...], b: tuple[str, ...]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    tag = 1.0 if a[0] == b[0] else 0.0
    ta, tb = (a[1] if len(a) > 1 else ""), (b[1] if len(b) > 1 else "")
    text = 1.0 if (not ta and not tb) else text_similarity(ta, tb)
    return 0.25 * tag + 0.75 * text


def _opt_sim(a: str, b: str) -> float:
    return NAN if not a else text_similarity(a, b)


def _opt_jac(a: frozenset, b: frozenset) -> float:
    return NAN if not a else jaccard(a, b)


def pair_features(a: ElementFingerprint, b: ElementFingerprint, retrieval: float = 0.0) -> list[float]:
    """Raw feature vector (ordered as :data:`RAW_FEATURES`) comparing original ``a`` with candidate ``b``."""
    da, db = derived(a), derived(b)
    if da.test_values:
        testid = 1.0 if (da.test_values & db.test_values) else 0.0
    else:
        testid = NAN
    return [
        1.0 if a.tag == b.tag else 0.0,
        1.0 if a.family == b.family else 0.0,
        NAN if not a.role else (1.0 if a.role == b.role else 0.0),
        NAN if not a.id else (1.0 if a.id == b.id else 0.0),
        _opt_jac(da.id_toks, db.id_toks),
        NAN if not da.name else (1.0 if da.name == db.name else 0.0),
        NAN if not da.type else (1.0 if da.type == db.type else 0.0),
        testid,
        _opt_jac(da.data_kv, db.data_kv),
        _opt_jac(da.data_keys, db.data_keys),
        _opt_sim(da.aria_label, db.aria_label),
        _opt_jac(da.other_kv, db.other_kv),
        _opt_sim(da.placeholder, db.placeholder),
        _opt_sim(da.href, db.href),
        _opt_sim(a.accessible_name, b.accessible_name),
        _opt_sim(a.text, b.text),
        _opt_sim(a.full_text, b.full_text),
        _opt_sim(a.label, b.label),
        _opt_sim(a.heading, b.heading),
        _opt_sim(a.context, b.context),
        _opt_sim(a.next_context, b.next_context),
        _opt_sim(a.row, b.row),
        _opt_sim(a.column_header, b.column_header),
        _opt_sim(a.form, b.form),
        1.0 if a.landmark == b.landmark else 0.0,
        _opt_jac(da.classes, db.classes),
        _opt_jac(da.class_toks, db.class_toks),
        _opt_jac(da.anc, db.anc),
        text_similarity(a.parent, b.parent) if (a.parent or b.parent) else 1.0,
        _sig_sim(da.prev, db.prev),
        _sig_sim(da.next, db.next),
        1.0 - abs(da.rel_pos - db.rel_pos),
        min(a.sibling_count, b.sibling_count) / max(1, a.sibling_count, b.sibling_count),
        lcs_ratio(da.tag_path, db.tag_path),
        lcs_ratio(da.sem_path, db.sem_path) if (da.sem_path or db.sem_path) else 1.0,
        1.0 / (1.0 + abs(a.depth - b.depth)),
        1.0 - min(1.0, abs(a.position - b.position)),
        jaccard(da.children, db.children),
        1.0 if a.hidden != b.hidden else 0.0,
        1.0 if (a.shadow_depth > 0) == (b.shadow_depth > 0) else 0.0,
        float(retrieval),
    ]


def feature_matrix(
    original: ElementFingerprint,
    candidates: Sequence[ElementFingerprint],
    retrieval: Sequence[float] | None = None,
) -> np.ndarray:
    """``(n_candidates, len(FEATURE_NAMES))`` matrix with raw + query-relative features."""
    n = len(candidates)
    if retrieval is None:
        retrieval = [0.0] * n
    raw = np.array(
        [pair_features(original, c, r) for c, r in zip(candidates, retrieval)], dtype=float
    ).reshape(n, len(RAW_FEATURES))
    rel = raw[:, _REL_COLUMNS]
    if n:
        with np.errstate(invalid="ignore"):
            col_max = np.max(rel, axis=0)  # NaN columns stay NaN (constant per query)
        rel = rel - col_max
    return np.hstack([raw, rel])
