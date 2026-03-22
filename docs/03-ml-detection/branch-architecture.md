# ML Detection Branch Architecture

> Status: Active
> Audience: Team, AI agents, curious developers
> Purpose: Architecture reference for the hybrid pipeline and its decision
> criteria

## Purpose

This document describes what the `feat/ml-detection-improvement` branch aims to
achieve, the architecture adopted, and how `autoresearch` should be used in
Niamoto.

The subject is no longer just "detect a column type". The goal is to produce
detection good enough to auto-configure an import, build a `semantic_profile`,
and propose useful affordances and suggestions without relying on an LLM.

## Product Objective

The product objective is not academic perfection on fine-grained concepts. The
system must primarily:

- recognise the correct **role** of a column;
- recognise a few **critical concepts** that change product behaviour;
- perform well on new, multilingual, and partially anonymous datasets;
- avoid high-confidence false positives;
- feed a usable `semantic_profile` for transformer/widget suggestions.

In practice, a confusion between `measurement.height` and `measurement.diameter`
is less serious than a confusion between `identifier.plot` and `statistic.count`.

## Adopted Architecture

The branch has converged on a local, compact, and explainable hybrid pipeline:

1. **Exact aliases**
2. **Header branch**
3. **Values branch**
4. **Fusion**
5. **Product semantic projection**

### 1. Exact Aliases

Aliases provide a high-precision fast path for known column names. They remain
essential, but must stay conservative:

- an ambiguous alias should be disabled;
- an exact alias must not bypass the classifier if doing so creates false
  positives at confidence 1.0.

References:

- [alias_registry.py](src/niamoto/core/imports/ml/alias_registry.py)
- [column_aliases.yaml](src/niamoto/core/imports/ml/column_aliases.yaml)

### 2. Header Branch

The `header` branch classifies the column name from a normalised enriched text.
It is the best-performing branch when the header is informative.

Technology:

- TF-IDF char n-grams
- Logistic Regression

References:

- [train_header_model.py](../../ml/scripts/train/train_header_model.py)
- [header_features.py](src/niamoto/core/imports/ml/header_features.py)

### 3. Values Branch

The `values` branch learns from statistics and patterns extracted from the
values:

- numerical distributions;
- simple regexes;
- booleans, dates, coordinates;
- signals from encoded/categorical columns.

It is less accurate alone than `header`, but it is decisive for:

- anonymous headers;
- ambiguous cases;
- certain concepts that are strongly detectable by pattern.

References:

- [train_value_model.py](../../ml/scripts/train/train_value_model.py)
- [value_features.py](src/niamoto/core/imports/ml/value_features.py)

### 4. Fusion

Fusion combines the two branches in a shared concept space. It must not be a
simple implicit average:

- it receives the aligned probabilities from both branches;
- it uses confidence and disagreement meta-features;
- it can integrate targeted guardrails for frequent errors.

Fusion is the right layer for correcting cases where one branch becomes too
dominant on a particular domain.

References:

- [train_fusion.py](../../ml/scripts/train/train_fusion.py)
- [fusion_features.py](src/niamoto/core/imports/ml/fusion_features.py)

### 5. Product Semantic Projection

The real product output is not just a raw concept. The current branch projects
detection towards:

- a `role`
- a `concept`
- affordances and suggestions

This layer is what aligns detection with the Niamoto product.

References:

- [semantic_profile.py](src/niamoto/core/imports/ml/semantic_profile.py)
- [affordance_matcher.py](src/niamoto/core/imports/ml/affordance_matcher.py)
- [profiler.py](src/niamoto/core/imports/profiler.py)

## Why This Architecture

This architecture is suited to the real constraints of the project:

- limited annotated data relative to the number of concepts;
- high heterogeneity of datasets;
- multilingual;
- need for explainability;
- local execution;
- short training cost;
- product value closer to the correct role and correct suggestion than to the
  perfect fine-grained concept.

A larger end-to-end approach would be more fragile here than a compact hybrid
system with targeted rules.

## What We Are Really Trying to Improve

The branch does not aim to maximise a simple classification score. It aims to
improve:

- the correct auto-configuration rate;
- robustness on new datasets;
- handling of anonymous columns;
- the quality of output suggestions;
- the ability to abstain or remain cautious on hard cases.

## Retained Evaluation Ground Truth

The final metric targeted by the branch is the `NiamotoOfflineScore`, computed
in [evaluation.py](../../ml/scripts/eval/evaluation.py)
and exposed by [evaluate.py](../../ml/scripts/eval/evaluate.py).

The score combines:

- `role_macro_f1`
- `critical_concept_macro_f1`
- `anonymous_role_macro_f1`
- `pair_consistency`
- `confidence_quality`
- `dataset_outcome`

The important holdouts are:

- languages: `fr`, `es`, `de`, `zh`
- families: `dwc_gbif`, `forest_inventory`, `tropical_field`,
  `research_traits`
- anonymous columns

## Role of Autoresearch

`autoresearch` must not decide the architecture. It must locally optimise an
already well-framed system.

Expected role:

- propose bounded variants;
- evaluate quickly;
- keep improvements;
- reject regressions;
- accelerate tuning.

What it must not do:

- change the product ground truth;
- optimise a proxy score at the expense of guardrails;
- introduce unvalidated aggressive rules;
- silently degrade a hard holdout to gain elsewhere.

## Recommended Autoresearch Programmes

Three loop levels are useful:

- [niamoto-header-model.md](../../ml/programmes/niamoto-header-model.md)
- [niamoto-values-model.md](../../ml/programmes/niamoto-values-model.md)
- [niamoto-fusion.md](../../ml/programmes/niamoto-fusion.md)

The `fusion` programme now plays the role of the **full-stack** programme.

## Current Guardrails

Results observed on the branch indicate that certain domains must be treated as
explicit guardrails:

- `forest_inventory`
- `tropical_field`
- `fr`

The largest risk identified at this stage is over-prediction of ill-suited
concepts such as `statistic.count` on business-coded columns.

## Recommended Direction

The right direction is not "more model". The right direction is:

- better train/runtime consistency;
- better evaluation;
- better fusion;
- cautious targeted rules;
- better use of dataset-level context.

The most promising part of the branch remains the alignment:

`detection -> semantic_profile -> affordances -> suggestions`

and not merely the optimisation of an isolated classifier.
