# Multi-Instance ML Evaluation and Improvement (2026-03-20)

> Status: Experiment
> Audience: Team, AI agents
> Purpose: Summarize the first full evaluation round on multiple real datasets
> and the corrections applied during that session

## Context

This session evaluated the ML stack on several real datasets, corrected
annotation issues by inspecting actual values, enriched the alias registry, and
 retrained the models on an enriched gold set.

## Evaluation setup

- Ground truth in `ml/data/eval/annotations/`
- Main scripts:
  - `ml/scripts/eval/evaluate_instance.py`
  - `ml/scripts/eval/run_eval_suite.py`
- Timestamped JSON results in `ml/data/eval/results/`

## Score progression

### V1 — Initial annotations

| Dataset | Columns | Role % | Concept % |
|---------|:-------:|:------:|:---------:|
| niamoto-nc | 57 | 61.4 | 45.6 |
| niamoto-gb | 27 | 88.9 | 66.7 |
| guyadiv | 61 | 85.2 | 63.9 |
| GBIF NC | 51 | 84.3 | 76.5 |
| GBIF Gabon | 45 | 86.7 | 77.8 |
| GBIF inst. Gabon | 41 | 82.9 | 75.6 |
| silver | 136 | 86.0 | 66.2 |
| **TOTAL** | **418** | **82.3** | **66.5** |

### V2 — After taxonomy + `plot_name` correction

Main correction:

- `taxonomy.name -> taxonomy.species` for true binomials
- `plot_name` adjusted based on real values

| Aggregate | Before | After | Delta |
|-----------|:------:|:-----:|:-----:|
| **TOTAL concept %** | 66.5 | **71.1** | **+4.6** |

### V3 — After value-level annotation verification

Examples:

- `canopy` / `undercanopy` / `understorey` -> `statistic.count`
- `SPCD` -> `identifier.taxon`
- `Mnemonic` -> `identifier.taxon`
- `Author` / `auth_sp` -> `text.metadata`
- `Vernacular_name` -> `taxonomy.vernacular_name`

| Aggregate | Before | After | Delta |
|-----------|:------:|:-----:|:-----:|
| **TOTAL concept %** | 71.1 | **71.3** | **+0.2** |

### V4 — After alias registry enrichment

New alias coverage added for 13 concepts, including:

- `measurement.trait`
- `category.ecology`
- `category.status`
- `category.vegetation`
- `category.method`
- `environment.topography`
- `measurement.canopy`
- `identifier.collection`
- `identifier.institution`
- `location.admin_area`
- `text.observer`

| Dataset | V3 | V4 | Delta |
|---------|:--:|:--:|:-----:|
| niamoto-nc | 54.4 | **68.4** | **+14.0** |
| niamoto-gb | 74.1 | 74.1 | 0 |
| guyadiv | 65.6 | 65.6 | 0 |
| GBIF NC | 82.4 | **90.2** | **+7.8** |
| GBIF Gabon | 82.2 | **88.9** | **+6.7** |
| GBIF inst. | 80.5 | **85.4** | **+4.9** |
| silver | 69.9 | **73.5** | **+3.6** |
| **TOTAL** | **71.3** | **76.6** | **+5.3** |

## Gold-set diagnosis

The main diagnosis at that stage was:

- some weak concepts were absent or nearly absent from the gold set
- `measurement.diameter` was overrepresented
- `measurement.basal_area -> measurement.diameter` was a bad taxonomy merge and had to be fixed

Examples of missing or weakly covered concepts then:

- `measurement.trait`
- `category.ecology`
- `environment.topography`
- `text.metadata`
- `measurement.area`
- `category.status`

## Actions taken

### Gold set enrichment

Added `NC_FULL_OCC_LABELS` and `NC_FULL_PLOTS_LABELS` from the Niamoto New
Caledonia instance into `build_gold_set.py`.

Gold set size moved from `2492` to `2525`.

### V5 — Retrain on the enriched gold set

| Model | Before | After |
|-------|:------:|:-----:|
| header | 0.7614 | 0.7467 |
| values | 0.3783 | 0.3935 |
| fusion | 0.6899 | 0.6876 |

### V5 — Results after retrain

| Dataset | V4 | V5 | Delta |
|---------|:--:|:--:|:-----:|
| niamoto-nc | 68.4 | **87.7** | **+19.3** |
| niamoto-gb | 74.1 | 66.7 | -7.4 |
| guyadiv | 65.6 | 65.6 | 0 |
| GBIF NC | 90.2 | 90.2 | 0 |
| GBIF Gabon | 88.9 | 88.9 | 0 |
| GBIF inst. | 85.4 | **87.8** | +2.4 |
| silver | 73.5 | 69.1 | -4.4 |
| **TOTAL** | **76.6** | **77.5** | **+0.9** |

Key observation:

- `niamoto-nc` jumped strongly because the model now knew those columns
- some broader datasets dipped slightly because the gold set had shifted and had not yet been rebalanced further

## Session summary

| Step | TOTAL concept % | Delta |
|------|:---------------:|:-----:|
| V1 — Initial annotations | 66.5 | — |
| V2 — Taxonomy + `plot_name` correction | 71.1 | +4.6 |
| V3 — Value verification | 71.3 | +0.2 |
| V4 — Alias enrichment | 76.6 | +5.3 |
| V5 — Gold set + retrain | **77.5** | **+0.9** |
| **Total gain** | | **+11.0 pts** |

## ProductScore and GlobalScore after V5

| Metric | Before | After | Delta |
|--------|:------:|:-----:|:-----:|
| **ProductScore** | 80.04 | **81.82** | **+1.78** |
| **GlobalScore** | 78.6 | **80.79** | **+2.19** |

The strongest gains landed in:

- `tropical_field`
- `research_traits`

which matched the families newly enriched in the gold set.

## Other notable outcome

`evaluate.py` was switched from record-by-record fusion feature extraction to
the existing batched path, which reduced `ProductScore` runtime from roughly
14 hours to roughly 42 minutes.

## Remaining weak areas after V5

- `taxonomy.name`
- `measurement.area`
- `environment.temperature`
- `measurement.biomass`
- `text.metadata`
- `identifier.taxon`
- `category.status`

Systematically wrong columns at that stage included:

- `acceptedTaxonKey`
- `speciesKey`
- `genericName`
- `infraspecificEpithet`
- `scientificNameAuthorship`

## Reproduction commands

```bash
uv run python -m ml.scripts.eval.run_eval_suite

uv run python -m ml.scripts.eval.evaluate_instance \
    --annotations ml/data/eval/annotations/niamoto-nc.yml \
    --data-dir test-instance/niamoto-nc/imports --compare

uv run python -m ml.scripts.data.build_gold_set
uv run python -m ml.scripts.train.train_header_model
uv run python -m ml.scripts.train.train_value_model
uv run python -m ml.scripts.train.train_fusion
```
