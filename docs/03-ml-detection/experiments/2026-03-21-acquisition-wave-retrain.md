# Acquisition Wave Retrain and Evaluation (2026-03-21)

> Status: Experiment
> Audience: Team, AI agents
> Purpose: Measure the impact of the `SINP 1A + ETS + sPlotOpen` acquisition
> wave after a full rebuild and retrain

## Context

This run measures the effect of the acquisition wave on the ML detection stack
after:

1. rebuilding the gold set
2. retraining the `header`, `values`, and `fusion` branches
3. rerunning both the internal benchmark and the real-dataset suite

## Data integrated before retrain

### Added to the gold set

- `TAXREF v18` (`ml/data/silver/taxref/TAXREFv18.txt`)
- `ETS Occurrence_ext.csv`
- `ETS Taxon_ext.csv`
- `ETS Measurement_or_Fact_ext.csv`
- `sPlotOpen_header(3).txt`
- `sPlotOpen_DT(2).txt`
- `sPlotOpen_CWM_CWV(2).txt`
- `sPlotOpen_metadata(2).txt`

### Added at runtime only

- `sinp:` alias block in `column_aliases.yaml`
- `ets:` alias block in `column_aliases.yaml`
- `splot:` alias block in `column_aliases.yaml`

### Explicitly left out

- `OpenObs / SINP`: source unavailable
- `species_trait_data.csv`: too specialized / semantically fragile
- `PREDICTS`: kept outside the critical path

## Resulting gold set

| Metric | Value |
|--------|:-----:|
| Labelled columns | **2540** |
| Coarse concepts | **61** |
| Added sources | `taxref_v18`, `ets_*`, `splot_*` |

Visible contribution by source:

| Source | Columns |
|--------|:-------:|
| `taxref_v18` | 17 |
| `ets_occurrence_ext` | 9 |
| `ets_taxon_ext` | 17 |
| `ets_measurement_ext` | 4 |
| `splot_header` | 33 |
| `splot_dt` | 6 |
| `splot_cwm` | 40 |
| `splot_metadata` | 15 |

## Commands run

```bash
uv run python -m ml.scripts.data.build_gold_set
uv run python -m ml.scripts.train.train_header_model
uv run python -m ml.scripts.train.train_value_model
uv run python -m ml.scripts.train.train_fusion
uv run python -m ml.scripts.eval.run_eval_suite
```

## Training results

| Model | Cross-val macro-F1 | Note |
|-------|:------------------:|------|
| Header | **0.753** | strongest branch |
| Values | **0.378** | useful signal, still weak on generalization |
| Fusion | **0.639** | stronger than `values`, still below `header` alone |

### Warnings

`header` and `fusion` triggered `ConvergenceWarning` messages during retraining.
The models still trained and were saved successfully, but `max_iter` and/or the
solver deserved a later adjustment.

## Evaluation results

Output file:

- `ml/data/eval/results/20260321_194036.json`

### Internal benchmarks after retrain

| Benchmark | Value |
|-----------|:-----:|
| **ProductScore** | **80.8392** |
| **GlobalScore / NiamotoOfflineScore** | **82.764** |

Detailed `ProductScore`:

| Bucket | Score |
|--------|:-----:|
| `gbif_core_standard` | 98.511 |
| `gbif_extended` | 91.018 |
| `en_field` | 82.672 |
| `tropical_field` | 75.093 |
| `research_traits` | 71.621 |
| `anonymous` | 63.634 |

Interpretation:

- the historical holdout metrics remain broadly solid
- they are consistent with the annotated dataset suite
- `anonymous` is now the clearest penalizing bucket
- coded headers and inventory-style exports remain the main generalization ceiling

### Full eval suite (9 datasets, 478 columns)

| Dataset | Cols | Role % | Concept % |
|---------|:----:|:------:|:---------:|
| `niamoto-nc` | 57 | 96.5 | **91.2** |
| `niamoto-gb` | 27 | 100.0 | **100.0** |
| `guyadiv` | 61 | 83.6 | **83.6** |
| `gbif-nc` | 51 | 94.1 | **90.2** |
| `gbif-gabon` | 45 | 91.1 | **88.9** |
| `gbif-inst-gabon` | 41 | 90.2 | **87.8** |
| `silver` | 136 | 89.0 | **77.2** |
| `acceptance-niamoto-gb` | 27 | 100.0 | **100.0** |
| `acceptance-fia-or` | 33 | 75.8 | **63.6** |
| **TOTAL** | **478** | **90.4** | **84.7** |

### Product-oriented aggregate view (7 datasets, 418 columns)

| Aggregate | Role % | Concept % |
|-----------|:------:|:---------:|
| Tier 1 + Tier 1b + Silver | **90.9** | **85.4** |

## Interpretation

### What worked well

- `niamoto-gb` stayed at **100%**
- `niamoto-nc` rose to **91.2%**
- `guyadiv` rose to **83.6%**
- the three GBIF datasets closest to the product all landed between **87.8%** and **90.2%**

The acquisition wave clearly improved the core product datasets and nearby
standardized cases.

### What remains weak

The frozen out-of-train benchmark remains dominated by `acceptance-fia-or`:

| Dataset | Concept % |
|---------|:---------:|
| `acceptance-niamoto-gb` | 100.0 |
| `acceptance-fia-or` | **63.6** |

Main remaining errors:

- `measurement.biomass -> measurement.volume`
- `identifier.taxon -> taxonomy.species`
- `category.habitat -> (not found)`
- FIA-coded headers such as `SPCD`, `CR`, `VOLCFNET`, `VOLBFNET`
- GBIF taxonomic keys such as `acceptedTaxonKey`, `speciesKey`,
  `genericName`, `infraspecificEpithet`, `scientificNameAuthorship`

## Conclusion

This acquisition wave was worth it.

- Yes, it improved the Niamoto core datasets
- Yes, it stabilized real GBIF-like cases
- No, it did not solve coded inventory generalization yet

The next logical step was not another acquisition wave, but a targeted
correction pass on:

1. the remaining GBIF taxonomic key columns
2. the FIA-coded columns
3. `measurement.biomass`, `identifier.taxon`, `category.habitat`,
   `text.metadata`
