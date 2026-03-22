# ML Detection — Training & Evaluation Guide

> Status: Active
> Audience: Team, AI agents
> Purpose: Operational reference for data, training, evaluation, and
> improvement cycles

This guide explains how to build the gold set, train the three ML branches,
evaluate the stack, and decide what kind of improvement is needed next.

## Pipeline overview

```text
ml/data/silver/          ->  build_gold_set.py  ->  ml/data/gold_set.json
                                                     |
                                              +------+------+
                                              |             |
                                              v             v
                                     train_header_model   train_value_model
                                              |             |
                                              +------+------+
                                                     |
                                                     v
                                              train_fusion
                                                     |
                                                     v
                                          ml/models/*.joblib
                                                     |
                             column_aliases.yaml --->|
                                                     v
                               evaluate.py / run_eval_suite.py
                                                     |
                                                     v
                                  ml/data/eval/results/*.json
```

## 1. Source data

### Silver data

`ml/data/silver/` contains real ecological tabular sources used to enrich the
gold set:

- forest inventories
- GBIF exports
- trait datasets
- tropical field datasets
- standards-based tabular sources such as TAXREF, ETS, and sPlotOpen

These files are the raw material for training data construction.

### Niamoto instance datasets

The tested instance datasets remain important because they represent the actual
product target:

- `test-instance/niamoto-nc/imports/`
- `test-instance/niamoto-gb/imports/`

### Evaluation annotations

Independent ground truth lives in `ml/data/eval/annotations/`.

This is distinct from the gold set:

- **gold set** = training data
- **eval annotations** = benchmark data

Do not treat them as interchangeable, even when some columns overlap.

## 2. Gold set

The gold set is the training dataset. Each entry represents one labelled
column, with:

- `column_name`
- `concept_coarse`
- `role`
- sampled values
- dataset metadata

### Build the gold set

```bash
uv run python -m ml.scripts.data.build_gold_set
```

Output:

- `ml/data/gold_set.json`

### Add a new source

In `ml/scripts/data/build_gold_set.py`:

1. Define a label dictionary:

```python
MY_LABELS = {
    "dbh": ("measurement.diameter", "measurement"),
    "species": ("taxonomy.species", "taxonomy"),
    "plot_id": ("identifier.plot", "identifier"),
}
```

2. Register the source in `SOURCES`:

```python
{
    "name": "my_dataset",
    "path": ML_ROOT / "data/silver/my_file.csv",
    "labels": MY_LABELS,
    "language": "en",
    "sample_rows": 1000,
}
```

3. Rebuild the gold set.

### Concept taxonomy

Fine-grained concepts are merged into a coarser training taxonomy through
`ml/scripts/data/concept_taxonomy.py`.

Example:

- `category.phenology` -> `category.ecology`
- `measurement.basal_area` -> `measurement.biomass`

Always verify the merge logic before adding new fine concepts, because an
incorrect merge can bias the whole stack.

## 3. Training

All three models train from `ml/data/gold_set.json`.

### Header model

```bash
uv run python -m ml.scripts.train.train_header_model
```

- TF-IDF character n-grams + Logistic Regression
- strongest branch when headers are informative
- outputs `ml/models/header_model.joblib`
- local metric: macro-F1 on column names

### Value model

```bash
uv run python -m ml.scripts.train.train_value_model
```

- statistical and pattern features + HistGradientBoosting
- useful for anonymous or ambiguous headers
- outputs `ml/models/value_model.joblib`
- local metric: macro-F1 on value-derived features

### Fusion model

```bash
uv run python -m ml.scripts.train.train_fusion
```

- combines header/value probabilities and meta-features
- outputs `ml/models/fusion_model.joblib`
- evaluated with leak-aware GroupKFold by dataset

### Full retrain

```bash
uv run python -m ml.scripts.data.build_gold_set
uv run python -m ml.scripts.train.train_header_model
uv run python -m ml.scripts.train.train_value_model
uv run python -m ml.scripts.train.train_fusion
```

## 4. Alias registry

The alias registry is the high-precision fast path checked before ML.

File:

- `src/niamoto/core/imports/ml/column_aliases.yaml`

Format:

```yaml
concept.subconcept:
  en: [alias1, alias2]
  fr: [alias_fr1, alias_fr2]
  dwc: [darwin_core_name]
```

Add an alias when:

- the header is genuinely unambiguous
- there is no cross-concept ambiguity
- the ML stack repeatedly misses a stable real-world header

Quick check:

```bash
uv run python -c "
from niamoto.core.imports.ml.alias_registry import AliasRegistry
reg = AliasRegistry()
print(reg.match('my_column_name'))
"
```

Tests:

```bash
uv run pytest tests/core/imports/test_alias_registry.py -v
```

## 5. Evaluation

### Annotated datasets

Current benchmark annotations live in `ml/data/eval/annotations/`.

Typical files:

- `niamoto-nc.yml`
- `niamoto-gb.yml`
- `guyadiv.yml`
- `gbif_darwin_core.yml`
- `silver.yml`

The YAML format is `column_name: role.concept`.

### Full real-dataset suite

```bash
uv run python -m ml.scripts.eval.run_eval_suite
```

This runs the annotated dataset benchmark and writes timestamped JSON files to:

- `ml/data/eval/results/`

### Single dataset evaluation

```bash
uv run python -m ml.scripts.eval.evaluate_instance \
    --annotations ml/data/eval/annotations/niamoto-nc.yml \
    --data-dir test-instance/niamoto-nc/imports --compare
```

Other common variants:

```bash
uv run python -m ml.scripts.eval.evaluate_instance \
    --annotations ml/data/eval/annotations/gbif_darwin_core.yml \
    --csv ml/data/silver/gbif_targeted/new_caledonia/occurrences.csv

uv run python -m ml.scripts.eval.evaluate_instance \
    --annotations ml/data/eval/annotations/silver.yml \
    --data-dir ml/data/silver
```

### Tier-only evaluation

```bash
uv run python -m ml.scripts.eval.run_eval_suite --tier 1
uv run python -m ml.scripts.eval.run_eval_suite --tier gbif
uv run python -m ml.scripts.eval.run_eval_suite --tier acceptance
```

### Gold-set / holdout evaluation

Use `evaluate.py` for the internal benchmark built from the gold set and
holdout protocol:

```bash
uv run python -m ml.scripts.eval.evaluate --model values --metric macro-f1 --splits 5
uv run python -m ml.scripts.eval.evaluate --model fusion --metric macro-f1 --splits 5
uv run python -m ml.scripts.eval.evaluate --model all --metric product-score --splits 3
uv run python -m ml.scripts.eval.evaluate --model all --metric niamoto-score --splits 3
```

## 6. Improvement cycle

After an evaluation pass, identify:

1. **Weak concepts**: low accuracy, possibly absent or underrepresented in the gold set
2. **Systematically wrong headers**: likely alias candidates
3. **Top confusions**: concept A repeatedly predicted as B

### Choose the action

| Diagnosis | Action | Typical impact |
|-----------|--------|----------------|
| Concept missing from gold set | Add labels in `build_gold_set.py` | Requires rebuild + retrain |
| Stable unambiguous header missed | Add alias in `column_aliases.yaml` | Immediate, no retrain |
| Concept present but confused | Inspect `concept_taxonomy.py` or feature space | Rebuild + retrain |
| Evaluation annotation is wrong | Fix `ml/data/eval/annotations/` | Re-run eval only |
| Gold set overrepresentation bias | Rebalance or enrich the data | Retrain |

### Verify annotations against real values

Before assuming the model is wrong, inspect the actual column values:

```bash
uv run python -c "
import pandas as pd
df = pd.read_csv('path/to/file.csv', nrows=10)
print(df['column_name'].head())
"
```

Header-based assumptions can be misleading if the values tell another story.

### Protect benchmark integrity

Keep the separation clear:

- **Gold set**: training material
- **Eval annotations**: independent benchmark

If the same columns appear in both, interpret the scores carefully and keep the
labels aligned.

## Quick reference

```bash
# Full build -> train -> evaluate
uv run python -m ml.scripts.data.build_gold_set
uv run python -m ml.scripts.train.train_header_model
uv run python -m ml.scripts.train.train_value_model
uv run python -m ml.scripts.train.train_fusion
uv run python -m ml.scripts.eval.run_eval_suite

# Alias-only improvement path
uv run pytest tests/core/imports/test_alias_registry.py -v
uv run python -m ml.scripts.eval.run_eval_suite

# Internal benchmark only
uv run python -m ml.scripts.eval.evaluate --model all --metric niamoto-score --splits 3
```
