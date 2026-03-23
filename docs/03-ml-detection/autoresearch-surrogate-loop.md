# Autoresearch Surrogate Loop

> Status: Active
> Audience: Team, AI agents
> Purpose: Current surrogate-loop strategy and acceptance logic for
> autoresearch

## Purpose

This document formalises the following pivot:

- stop running `autoresearch` directly against an end-to-end metric that is
  too costly;
- refocus the autonomous loop on a **fusion-only surrogate loop**;
- reserve full-stack metrics for deferred validation of the best candidates.

## Observed Problem

The `autoresearch` pattern is only worthwhile if it can chain many iterations
autonomously.

On this branch, even recent variants of fast metrics remain too expensive:

- `product-score`: too slow for an autonomous loop;
- `product-score-mid`: still too costly for broad exploration;
- `product-score-fast-fast`: shorter, but still too long to target
  50+ runs per session.

The real problem is therefore not just the metric. It is the **granularity of
the search**:

- we retrain the entire stack for a change that is often local;
- we pay a full cost for a modification that only concerns the fusion;
- the autonomous loop spends its budget on certification instead of exploring.

## Decision

The next `autoresearch` mode must no longer be:

- `full stack -> full metric -> full guardrails`

at every iteration.

It must become:

- `very cheap local surrogate -> many iterations`
- then `deferred validation` on the best candidates only.

## Principle of the Fusion-Only Loop

Fusion is currently the best entry point for a surrogate loop, because:

- its scope is bounded;
- its changes are often local;
- it consumes signals already produced by `header` and `values`;
- it can be retrained much faster if the right caches are put in place.

The idea is to freeze, for a given benchmark:

- the splits;
- the outputs of the `header` branch;
- the outputs of the `values` branch;
- the target labels;
- the base fusion features.

Then the `autoresearch` loop only retrains the fusion model, or a small
variant of its features, without redoing the full stack on every run.

## What the Surrogate Loop Must Optimise

The local metric must not pretend to replace product truth. It must be:

- fast;
- stable;
- sensitive to genuine fusion gains;
- sufficiently correlated with stack validation to serve as a filter.

In this mode, we optimise a **FusionSurrogateScore** computed from
pre-prepared folds.

This score should mainly reward:

- the right `header/values` combination;
- robustness on anonymous columns;
- quality on `en_field`;
- quality on `tropical_field` and `research_traits` if these examples are
  present in the cache;
- reduction of `statistic.count` false positives on coded columns.

## Caches to Produce

Speed depends on this.

For each frozen fold, we want to store:

- `train_records`
- `test_records`
- `header` probabilities aligned on all concepts
- `values` probabilities aligned on all concepts
- base fusion meta-features
- target labels
- bucket metadata:
  - `tropical_field`
  - `research_traits`
  - `en_field`
  - `gbif_core_standard`
  - `anonymous`

Recommended format:

- `data/cache/ml/fusion_surrogate/<cache_version>/fold_*.npz`
- plus a `manifest.json` describing:
  - gold set hash
  - concept list
  - protocol
  - feature version

## Two Surrogate Levels

### 1. Ultra-Fast Surrogate

Goal:

- explore broadly;
- reject quickly;
- accept that it is slightly approximate.

Recommended content:

- a few fixed folds;
- critical buckets only;
- fusion-only retraining;
- no header/values rerun.

### 2. Promotion Surrogate

Goal:

- confirm the best candidates;
- verify that a local fusion gain is not heading in a misleading direction.

Recommended content:

- same cache, but more folds or more buckets;
- still without retraining the entire stack;
- higher cost than ultra-fast, but still well below the full `product-score`.

## Recommended Validation Chain

The new chain should become:

1. `fusion-surrogate-fast`
2. `fusion-surrogate-mid`
3. `product-score-fast-fast`
4. `product-score-mid`
5. `product-score`
6. `niamoto-score`

Interpretation:

- the first two levels serve autonomous exploration;
- levels 3 to 6 serve promotion of genuine winners.

## Recommended Acceptance Rule

A candidate can be:

- `candidate`
  - beats `fusion-surrogate-fast`
- `provisional`
  - beats `fusion-surrogate-mid`
- `promotable`
  - beats `product-score-fast-fast`
- `validated`
  - beats `product-score-mid`
- `certified`
  - beats `product-score`
  - does not break `niamoto-score`

The important point:

- the autonomous loop must not wait for `certified` before continuing to
  run;
- it should primarily produce a queue of promising candidates.

## Recommended Initial Scope

First recommended work:

- `fusion-only` loop

Relevant files:

- `ml/scripts/train/train_fusion.py`
- `src/niamoto/core/imports/ml/classifier.py`
- future surrogate cache script

Not to include in the first loop:

- alias registry
- profiler rules
- gold set
- dashboard
- product docs

## Non-Goals

This pivot does not seek to:

- replace real product validation;
- hide global regressions;
- remove `product-score` or `niamoto-score`.

It seeks to:

- make `autoresearch` finally practical;
- restore cadence to exploration;
- clearly separate exploration from certification.

## Current State

The minimal building blocks are now in place:

1. build the `fusion_surrogate` cache
   via:

```bash
uv run python -m ml.scripts.research.build_fusion_surrogate_cache --gold-set ml/data/gold_set.json --splits 3
```

2. expose a command such as:

```bash
uv run python -m ml.scripts.eval.evaluate --model fusion --metric surrogate-fast
```

3. also expose:

```bash
uv run python -m ml.scripts.eval.evaluate --model fusion --metric surrogate-mid
```

4. run `autoresearch` only on these metrics
5. promote only the best candidates to full stack validation

Local runner added:

```bash
uv run python -m ml.scripts.research.run_fusion_surrogate_autoresearch --iterations 50
```

Behaviour:

- computes `surrogate-fast`, `surrogate-mid` baselines
- defers `product-score-fast-fast` until the first candidate that passes `surrogate-mid`
- launches one `codex` iteration per candidate
- evaluates gates itself
- reverts losers
- automatically commits winners to keep a clean worktree
- writes a JSONL log under `.autoresearch/`

## First Measurements

On the current gold set:

- `fusion_surrogate` cache build (`splits=3`):
  - approximately `490s` (`~8m10s`)
- `surrogate-fast` on warm cache:
  - approximately `1.66s`
- `surrogate-mid` on warm cache:
  - approximately `1.31s`

Reading:

- the initial build remains a notable one-shot cost;
- however, fusion-only runs are now fast enough to support a real
  `autoresearch` loop.

## Reference Decision

As long as this surrogate loop does not exist, full-stack `autoresearch`
remains structurally too slow to deliver its real value.
