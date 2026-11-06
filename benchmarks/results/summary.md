# Benchmark results (2026-11-06)

40 suites · 240 targets · learned rankers: 5-fold GroupKFold by suite · latency = median of 5 cold runs per target · Python 3.13.18 · Intel(R) Xeon(R) Processor @ 2.10GHz

## Selector recovery accuracy

| Method | Top-1 | 95% CI | Top-3 | 95% CI | p50 latency (ms) | p95 latency (ms) |
|---|---:|---:|---:|---:|---:|---:|
| Authored CSS | 1.7% | 1–4 | 1.7% | 1–4 | 0.107 | 0.303 |
| Authored XPath | 9.6% | 6–14 | 12.5% | 9–17 | 0.028 | 0.052 |
| Absolute XPath | 0.0% | 0–2 | 0.0% | 0–2 | 0.004 | 0.006 |
| Same tag + text | 14.6% | 11–20 | 24.2% | 19–30 | 0.037 | 0.215 |
| Attribute fallback chain | 19.2% | 15–25 | 29.6% | 24–36 | 0.140 | 0.451 |
| dom-healer · heuristic | 86.2% | 81–90 | 92.5% | 88–95 | 4.748 | 8.430 |
| dom-healer · LogisticRegression | 83.8% | 79–88 | 92.5% | 88–95 | 4.841 | 8.566 |
| dom-healer · RandomForest | 79.6% | 74–84 | 92.9% | 89–96 | 14.799 | 18.880 |

## Top-1 by category

| Method | dashboard | ecommerce | form | table |
|---|---:|---:|---:|---:|
| Authored CSS | 1.7% | 0.0% | 3.3% | 1.7% |
| Authored XPath | 8.3% | 8.3% | 15.0% | 6.7% |
| Absolute XPath | 0.0% | 0.0% | 0.0% | 0.0% |
| Same tag + text | 23.3% | 0.0% | 11.7% | 23.3% |
| Attribute fallback chain | 28.3% | 5.0% | 18.3% | 25.0% |
| dom-healer · heuristic | 88.3% | 83.3% | 91.7% | 81.7% |
| dom-healer · LogisticRegression | 88.3% | 80.0% | 86.7% | 80.0% |
| dom-healer · RandomForest | 86.7% | 76.7% | 85.0% | 70.0% |

## Top-1: development suites vs. never-inspected suites

| Method | dev (01–03, n=72) | held-out (04–10, n=168) |
|---|---:|---:|
| Authored CSS | 0.0% | 2.4% |
| Authored XPath | 11.1% | 8.9% |
| Absolute XPath | 0.0% | 0.0% |
| Same tag + text | 23.6% | 10.7% |
| Attribute fallback chain | 26.4% | 16.1% |
| dom-healer · heuristic | 84.7% | 86.9% |
| dom-healer · LogisticRegression | 80.6% | 85.1% |
| dom-healer · RandomForest | 76.4% | 81.0% |

## Top-1 by mutation type (targets carrying the tag)

| Mutation | n | Authored CSS | Attribute fallback chain | dom-healer · heuristic | dom-healer · LogisticRegression | dom-healer · RandomForest |
|---|---:|---:|---:|---:|---:|---:|
| attribute-churn | 136 | 2.2% | 17.6% | 90.4% | 86.8% | 82.4% |
| class-obfuscation | 223 | 1.8% | 20.6% | 86.1% | 83.0% | 78.9% |
| copy-change | 134 | 3.0% | 11.2% | 84.3% | 81.3% | 75.4% |
| decoy | 149 | 0.0% | 17.4% | 86.6% | 81.9% | 78.5% |
| id-change | 100 | 0.0% | 18.0% | 89.0% | 86.0% | 81.0% |
| insertion | 53 | 1.9% | 24.5% | 92.5% | 86.8% | 84.9% |
| shadow-dom | 71 | 2.8% | 11.3% | 84.5% | 81.7% | 74.6% |
| sibling-reorder | 149 | 0.7% | 16.8% | 83.9% | 81.2% | 76.5% |
| structure-move | 73 | 2.7% | 20.5% | 86.3% | 87.7% | 87.7% |
| tag-change | 62 | 0.0% | 3.2% | 75.8% | 75.8% | 71.0% |
| testid-change | 17 | 0.0% | 5.9% | 70.6% | 70.6% | 64.7% |
| wrapper-divs | 103 | 1.9% | 26.2% | 83.5% | 78.6% | 76.7% |

## Leave-one-category-out (train on 3 categories, test on the 4th)

| Model | Top-1 | Top-3 | dashboard | ecommerce | form | table |
|---|---:|---:|---:|---:|---:|---:|
| dom-healer · LogisticRegression | 81.7% | 92.5% | 86.7% | 80.0% | 88.3% | 71.7% |
| dom-healer · RandomForest | 75.4% | 91.2% | 83.3% | 71.7% | 78.3% | 68.3% |

## Latency (ms)

| Method | cold p50 | cold p95 | cold max | % < 5 ms | warm p50 (index reused) |
|---|---:|---:|---:|---:|---:|
| Authored CSS | 0.107 | 0.303 | 0.382 | 100.0% |  |
| Authored XPath | 0.028 | 0.052 | 0.073 | 100.0% |  |
| Absolute XPath | 0.004 | 0.006 | 0.021 | 100.0% |  |
| Same tag + text | 0.037 | 0.215 | 0.788 | 100.0% |  |
| Attribute fallback chain | 0.140 | 0.451 | 1.023 | 100.0% |  |
| dom-healer · heuristic | 4.748 | 8.430 | 10.056 | 55.0% | 1.252 |
| dom-healer · LogisticRegression | 4.841 | 8.566 | 9.930 | 56.7% | 1.229 |
| dom-healer · RandomForest | 14.799 | 18.880 | 27.630 | 0.8% | 10.943 |

HTML parsing of the v2 page (not included above): p50 0.76 ms, p95 1.32 ms.

Median cold breakdown (ms):

| Method | index | retrieval | features | ranking | synthesis |
|---|---:|---:|---:|---:|---:|
| dom-healer · heuristic | 0.547 | 1.088 | 2.020 | 0.095 | 0.640 |
| dom-healer · LogisticRegression | 0.544 | 1.076 | 1.992 | 0.083 | 0.635 |
| dom-healer · RandomForest | 0.552 | 1.083 | 2.002 | 9.983 | 0.679 |

## Other diagnostics

* Candidate pool recall (true element among the 24 fully-scored candidates): 95.0%; mean pool size 14.5.
* Healed selectors verified unique in v2: CSS 238/238, XPath 238/238 (positional CSS fallback used 89 times).
* McNemar exact test on paired top-1 outcomes:
  * heuristic vs logreg: 13 vs 7 discordant, p = 0.263
  * heuristic vs random forest: 24 vs 8 discordant, p = 0.007
  * logreg vs random forest: 14 vs 4 discordant, p = 0.0309

## Most influential features

| LogisticRegression (std. coef) | RandomForest (importance) |
|---|---|
| `rel_label_sim` +1.57 | `retrieval` 0.179 |
| `rel_container_sim` +1.54 | `rel_retrieval` 0.174 |
| `rel_row_sim` +1.10 | `rel_name_sim` 0.083 |
| `retrieval` +1.01 | `name_sim` 0.075 |
| `rel_retrieval` +1.01 | `rel_container_sim` 0.062 |
| `form_sim` +0.97 | `container_sim` 0.036 |
| `hidden_mismatch` -0.89 | `rel_context_sim` 0.031 |
| `rel_tag_path_sim` -0.89 | `next_context_sim` 0.026 |
| `column_sim` -0.84 | `position_sim` 0.025 |
| `name_sim` +0.78 | `context_sim` 0.024 |
