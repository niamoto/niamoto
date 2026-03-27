# ML Model Regeneration Design

Date: 2026-03-27

## Goal

Regenerate the runtime ML column-classification models with the current dependency stack, specifically `scikit-learn 1.8.x`, so Niamoto no longer relies on models serialized with an older sklearn version.

This work is meant to close the remaining ML compatibility gap after the dependency upgrade to Python `3.12+` and the newer scientific stack.

## Context

Niamoto loads three runtime models from [ml/models](/Users/julienbarbe/Dev/clients/niamoto/ml/models):

- `header_model.joblib`
- `value_model.joblib`
- `fusion_model.joblib`

They are loaded lazily by [classifier.py](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/core/imports/ml/classifier.py).

After upgrading to `scikit-learn 1.8.0`, tests still pass, but the runtime emits `InconsistentVersionWarning` because these models were serialized with `1.7.2`.

The repository already contains the training and evaluation pipeline:

- training scripts in [ml/scripts/train](/Users/julienbarbe/Dev/clients/niamoto/ml/scripts/train)
- evaluation scripts in [ml/scripts/eval](/Users/julienbarbe/Dev/clients/niamoto/ml/scripts/eval)
- training data in [ml/data](/Users/julienbarbe/Dev/clients/niamoto/ml/data)

## Decision

Use the existing ML pipeline to retrain all three runtime models with the current environment, then validate them before replacing the committed artifacts.

We explicitly do **not** pin `scikit-learn` back to `1.7.x`. Model regeneration is the preferred path.

## Scope

In scope:

- retraining the three runtime models
- evaluating the regenerated models with the existing evaluation tooling
- comparing current runtime behavior against the regenerated models on representative inputs
- updating committed `.joblib` artifacts if validation is acceptable
- adding minimal documentation or tests if needed to make future regeneration safer

Out of scope:

- redesigning the ML architecture
- migrating away from `joblib`
- changing semantic concepts or taxonomy labels
- introducing ONNX or a custom inference runtime

## Approaches Considered

### 1. Minimal regeneration with existing pipeline

Retrain the three models using the current scripts, evaluate them, compare a small set of representative predictions, and replace the committed artifacts.

Pros:

- lowest implementation cost
- aligns with the current architecture
- directly removes sklearn serialization mismatch warnings

Cons:

- depends on current training/evaluation scripts being trustworthy
- limited comparison could miss subtle behavior drift

### 2. Regeneration plus broader regression audit

Do the same retraining, but add a larger before/after prediction snapshot suite over curated fixtures before accepting the new models.

Pros:

- stronger confidence in behavior stability
- leaves better future guard rails

Cons:

- more time and more code churn
- not necessary for the first compatibility pass unless drift appears

### 3. Freeze sklearn version

Keep running old serialized models under the old sklearn version.

Pros:

- avoids immediate retraining work

Cons:

- blocks dependency upgrades
- leaves a known compatibility risk in place
- contradicts the current upgrade strategy

## Chosen Approach

Approach 1, with a lightweight comparison step borrowed from approach 2.

That means:

1. retrain all three models with the current environment
2. run the existing evaluation pipeline
3. compare a small representative set of predictions before and after
4. accept model changes if metrics are acceptable and no obvious product regression appears

## Execution Plan

### Step 1: Baseline capture

Capture baseline behavior before overwriting any artifacts:

- record current model file hashes and sizes
- run existing evaluation scripts against the committed models
- collect a small representative inference sample from real or fixture columns

### Step 2: Retraining

Run the existing training scripts in order:

- header model
- value model
- fusion model

The regenerated artifacts should be written back to [ml/models](/Users/julienbarbe/Dev/clients/niamoto/ml/models).

### Step 3: Validation

Validate the regenerated models on three dimensions:

- loading in [classifier.py](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/core/imports/ml/classifier.py) without version-mismatch warnings
- evaluation metrics from the existing ML evaluation scripts
- representative inference comparisons on common column types such as taxonomy, coordinates, dates, identifiers, and quantitative measurements

### Step 4: Acceptance

Accept the regenerated models if:

- model loading is clean
- evaluation metrics are not materially worse
- representative predictions do not show an obvious semantic regression

If drift is noticeable but metrics improve overall, the regenerated models are still acceptable as long as the changes are documented.

### Step 5: Repository update

If accepted:

- commit regenerated `.joblib` files
- commit any minimal supporting test or documentation update

If rejected:

- revert regenerated model artifacts
- document the failure reason
- open a follow-up path for deeper ML audit

## Risks

### Behavior drift

Retraining can change predictions even with the same code and data. This is acceptable if the overall model quality holds and the changes are not obviously harmful to import suggestions.

### Hidden training-script assumptions

The training scripts may assume older package behavior. If they fail, that becomes the first bug to fix before model regeneration can continue.

### Limited reference set

A small before/after sample may miss some regressions. If the first pass shows suspicious changes, the work should expand into a broader regression audit.

## Testing Strategy

Minimum checks for this work:

- targeted ML tests around import/profiler/classifier
- direct smoke load of the three regenerated models
- existing ML evaluation scripts
- one representative end-to-end import suggestion check

## Success Criteria

The work is successful when:

- Niamoto runs on the upgraded dependency stack without sklearn version-mismatch warnings for the committed runtime models
- the regenerated models load successfully
- evaluation remains acceptable
- the updated model artifacts are committed and reproducible through the existing training pipeline
