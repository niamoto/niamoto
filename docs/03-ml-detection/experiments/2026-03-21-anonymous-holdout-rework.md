# Anonymous Holdout Rework (2026-03-21)

> Status: Experiment
> Audience: Team, AI agents
> Purpose: Replace the old synthetic anonymous holdout with a real, diverse,
> anonymized benchmark

## Context

The previous anonymous holdout was synthetic, overly easy, and permanently
inflated the benchmark. This rework replaced it with a holdout built from real
gold-set columns anonymized with generic names.

## Problem

The old anonymous holdout was not testing anything useful:

- 86 fully synthetic entries
- 76% concentrated on only 2 concepts
- only 10 concepts covered out of ~45 coarse concepts at the time
- the values branch could score highly by predicting generic continuous-float behavior
- 10% of `ProductScore` was therefore being inflated by a weak benchmark

## Implemented solution

### New `_build_anonymous_holdout()`

In `ml/scripts/data/build_gold_set.py`:

- stratified sampling of real columns by `concept_coarse`
- minimum of 2 entries per concept
- fixed seed `42`
- generic randomized names from a large anonymous name pool
- dedicated quality tag: `gold_anonymous`

### Removal of the old mechanism

- removed `HEADER_VARIANTS["anonymous"]`
- removed the legacy synthetic anonymous generation branches

### Values-only anonymous metric

In `ml/scripts/eval/evaluate.py`:

- `_evaluate_holdout_score()` now supports `return_models=True`
- the anonymous block exposes an informative values-only metric
- the `anonymous` bucket in `ProductScore` still uses the full fusion pipeline

## Results

### New holdout distribution

| Metric | Before | After |
|--------|:------:|:-----:|
| Anonymous entries | 86 | **122** |
| Concepts covered | 10 | **61** |
| Quality | `synthetic` | `gold_anonymous` |
| Distribution | 76% on 2 concepts | **2 per concept (uniform floor)** |
| Unique names | 31 | **122** |

### Score changes

| Metric | Before | After | Delta |
|--------|:------:|:-----:|:-----:|
| **ProductScore** | 81.82 | **81.32** | **-0.50** |
| **GlobalScore** | 80.79 | **81.72** | **+0.93** |
| Anonymous holdout | 100.0 | **91.02** | **-8.98** |
| Anonymous values-only | n/a | **94.3%** (115/122) | — |

Detailed `ProductScore` buckets:

| Bucket | Before | After | Delta |
|--------|:------:|:-----:|:-----:|
| tropical_field (30%) | 69.01 | 68.71 | -0.30 |
| research_traits (15%) | 75.49 | 77.08 | +1.59 |
| gbif_core_standard (20%) | 96.02 | 97.36 | +1.34 |
| gbif_extended (10%) | 88.18 | 88.22 | +0.04 |
| en_field (15%) | 78.46 | 78.30 | -0.16 |
| anonymous (10%) | 100.0 | **91.02** | **-8.98** |

## Interpretation

- The anonymous holdout became informative instead of artificially perfect.
- The values branch alone was still strong on anonymized real columns.
- The small `ProductScore` drop came entirely from replacing an inflated 100%
  bucket with a more realistic score.
- The other buckets remained stable within normal run-to-run variance.

### Bug fixed during the session

`gold_anonymous` entries were initially treated as `real_records` because they
were not `synthetic`. That polluted other holdouts and the primary protocol.
The fix explicitly excluded `is_anonymous` entries from `real_records` and
`synthetic_records` inside the protocol evaluation.

## Modified files

| File | Change |
|------|--------|
| `ml/scripts/data/build_gold_set.py` | new anonymous holdout builder, old synthetic mechanism removed |
| `ml/scripts/eval/evaluate.py` | values-only anonymous metric, protocol exclusion fix |
| `ml/data/gold_set.json` | regenerated |

## Reproduction commands

```bash
uv run python -m ml.scripts.data.build_gold_set

uv run python -m ml.scripts.eval.evaluate --model all --metric product-score
```
