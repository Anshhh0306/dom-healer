from __future__ import annotations

import math

import numpy as np

from dom_healer.features import FEATURE_NAMES, RAW_FEATURES, RELATIVE_OF, feature_matrix, pair_features
from dom_healer.fingerprint import ElementFingerprint
from dom_healer.healer import capture_fingerprint


def test_identical_fingerprints_score_max(old_doc):
    fp = capture_fingerprint(old_doc, "#nl-email")
    vec = dict(zip(RAW_FEATURES, pair_features(fp, fp, 1.0)))
    for name, value in vec.items():
        if math.isnan(value):
            continue
        if name == "hidden_mismatch":
            assert value == 0.0
        else:
            assert value == 1.0, name


def test_not_applicable_features_are_nan():
    bare = ElementFingerprint(tag="div")
    other = ElementFingerprint(tag="span", id="x", attrs={"data-testid": "t"}, classes=["a"])
    vec = dict(zip(RAW_FEATURES, pair_features(bare, other)))
    for name in ("role_eq", "id_eq", "id_token_sim", "name_eq", "type_eq", "testid_eq", "data_jaccard",
                 "aria_label_sim", "attr_jaccard", "placeholder_sim", "href_sim", "name_sim", "text_sim",
                 "label_sim", "heading_sim", "row_sim", "column_sim", "form_sim", "class_jaccard",
                 "class_token_jaccard", "ancestor_jaccard"):
        assert math.isnan(vec[name]), name
    assert vec["tag_eq"] == 0.0
    assert vec["prev_sibling_sim"] == 1.0  # both have no previous sibling
    assert vec["semantic_path_sim"] == 1.0
    assert vec["parent_sim"] == 1.0


def test_signals_and_penalties():
    a = ElementFingerprint(tag="button", role="button", family="clickable", attrs={"data-testid": "buy", "type": "submit"},
                           prev_sibling="span|$120", hidden=False, shadow_depth=0)
    b = ElementFingerprint(tag="a", role="button", family="clickable", attrs={"data-qa": "BUY", "type": "submit"},
                           prev_sibling="span|", hidden=True, shadow_depth=2)
    vec = dict(zip(RAW_FEATURES, pair_features(a, b, 0.5)))
    assert vec["tag_eq"] == 0.0 and vec["family_eq"] == 1.0 and vec["role_eq"] == 1.0
    assert vec["testid_eq"] == 1.0  # same value under a different test attribute
    assert vec["type_eq"] == 1.0
    assert vec["hidden_mismatch"] == 1.0 and vec["shadow_eq"] == 0.0
    assert vec["prev_sibling_sim"] == 0.25
    assert vec["retrieval"] == 0.5


def test_feature_matrix_relative_columns(old_doc, new_doc):
    from dom_healer.healer import get_index

    fp = capture_fingerprint(old_doc, "#nl-email")
    index = get_index(new_doc)
    cands = index.candidates(fp, k=6)
    X = feature_matrix(fp, [index.fingerprint(el) for el, _ in cands], [s for _, s in cands])
    assert X.shape == (len(cands), len(FEATURE_NAMES))
    rel = X[:, len(RAW_FEATURES):]
    for j, name in enumerate(RELATIVE_OF):
        col = rel[:, j]
        if not np.isnan(col).all():
            assert np.nanmax(col) == 0.0, name
    empty = feature_matrix(fp, [])
    assert empty.shape == (0, len(FEATURE_NAMES))
    default_retrieval = feature_matrix(fp, [fp])
    assert default_retrieval[0, RAW_FEATURES.index("retrieval")] == 0.0
