# Automatic column detection

## What it does

You import a forest inventory CSV file into Niamoto. Instead of manually configuring each column ("this is a diameter, this is a species, this is coordinates"), Niamoto **automatically detects** the content and proposes a complete dashboard: diameter histogram, distribution map, breakdown by family.

You only need to adjust if necessary.

## Why it is necessary

Every team names its columns differently:

| What it is | French Guiana | France IFN | FIA (US) | Spain | Anonymous |
|------------|---------------|------------|----------|-------|-----------|
| Diameter | `diam` | `C13` | `DIA` | `dap` | `X1` |
| Height | `haut` | `HTOT` | `HT` | `altura` | `col_2` |
| Species | `espece` | `ESPAR` | `SPCD` | `especie` | `X5` |
| Latitude | `lat` | `YL` | `LAT` | `latitud` | `col_3` |

Without automatic detection, every user must manually configure their columns before being able to visualise anything. This is a barrier to adoption.

## How it works

The system detects the **role** of each column — that is, what can be done with it:

| Detected role | What Niamoto proposes |
|--------------|----------------------|
| Numeric measurement | Histogram, statistical summary, scatter plot |
| Taxonomy | Breakdown by family/genus, sunburst |
| Geographic coordinates | Interactive map |
| Temporal data | Timeline, year filter |
| Category | Bar chart, donut chart |
| Identifier | Join key between tables |

Two complementary signals are combined to achieve this:

1. **The column name** — `diametre` and `diametro` share the same letter sequences. A character n-gram model naturally groups them together, even across related languages.

2. **The values** — a diameter follows a log-normal distribution between 5 and 300, coordinates lie between -90 and 90, a species name follows the "Genus species" format. When the column name is anonymous (`X1`), the values take over.

Both are fused into a final prediction. The user can then refine each transformer/widget pair in the GUI.

## Training data

The model is trained on **2,231 labelled columns** from:

- **88 real datasets**: IFN France, FIA US, GBIF (Spain, Norway, Benin, Tanzania, China...), GUYADIV French Guiana, inventories from Africa/New Caledonia/Madagascar/Malaysia/Panama, Zenodo (BCI, FERP California, Heishiding China...)
- **6 continents**, **8 languages** (EN, FR, ES, PT, DE, ID + anonymous headers)
- **61 concepts** organised into roles: taxonomy, location, measurements, environment, statistics, temporal, categories, identifiers

All detection runs locally with scikit-learn (~3 MB of dependencies). No network required, no LLM.

## Contributing

To improve detection for a poorly recognised column type:

1. **Add aliases** in `src/niamoto/core/imports/ml/column_aliases.yaml` — no ML needed, just a YAML file. Example: add `"circonference"` as an alias for `measurement.diameter` in French.

2. **Add training data** in `ml/scripts/data/build_gold_set.py` — label the columns from a new dataset and reference it in the source list.

3. **Retrain**: `uv run python -m ml.scripts.train.train_header_model && uv run python -m ml.scripts.train.train_value_model`

## Current scores

| Model | Macro-F1 | What this means |
|-------|----------|-----------------|
| Header (column name) | 0.77 | 77% of columns correctly classified by their name |
| Values (statistical values) | 0.35 | 35% — values alone are ambiguous (a diameter and a height look similar numerically) |
| Fusion (header + values) | ProductScore 80.04 / NiamotoOfflineScore 78.6 | Combined signal from both branches |

The header score is the most important because in the majority of cases columns have informative names. The values model kicks in when the name is anonymous or ambiguous.

## Known limitations

- Very rare columns (< 5 examples in the gold set) are grouped under generic categories
- Confidence calibration is not yet in place — the model cannot yet say "I am 85% confident"
- The values model remains weak at distinguishing two measurement types from each other (diameter vs height) — but this is not blocking since the "measurement" role is sufficient to suggest a histogram

## Technical architecture

```
Imported CSV
     │
     ├── Column name ──→ TF-IDF char n-grams ──→ LogisticRegression
     │                                                   │
     ├── Values ──→ 37 statistical features ──→ HistGradientBoosting
     │                                                   │
     └── Fusion ──→ LogReg calibrated on probabilities from both branches
                          │
                   Detected role + confidence
                          │
                   Suggested transformer/widget pairs
```

## Academic References

| Project | Year | Approach | Features | Performance | Ecological Relevance | Status |
|---------|------|----------|----------|-------------|---------------------|--------|
| **Sherlock** | 2019 | Deep NN | 1,588 | F1: 0.89 | Low (generic types) | Abandoned |
| **Sato** | 2020 | Hybrid DL + Topic | 1,588+ | F1: 0.92 | Low | Inactive |
| **Pythagoras** | 2024 | GNN | Graph-based | F1: 0.94 | Medium (numeric) | Active |
| **GAIT** | 2024 | GNN variants | Multi-graph | F1: 0.93 | Medium | Active |
| **GitTables** | 2023 | Dataset | N/A | Benchmark | High (diverse) | Active |

Niamoto's approach differs from these academic systems: it uses a lightweight hybrid pipeline (TF-IDF + HistGradientBoosting + Fusion) optimized for ecological data, running fully offline with scikit-learn (~3 MB).

## Key files

| File | Purpose |
|------|---------|
| `src/niamoto/core/imports/ml/alias_registry.py` | Name → concept matching via multilingual aliases |
| `src/niamoto/core/imports/ml/column_aliases.yaml` | 25 concepts × 8 languages |
| `ml/scripts/eval/evaluation.py` | Evaluation harness (GroupKFold, holdouts) |
| `ml/scripts/data/concept_taxonomy.py` | Fusion of 111 fine concepts → 61 concepts |
| `src/niamoto/core/imports/profiler.py` | DataProfiler with `ml_mode=auto/off/force` |
| `ml/scripts/data/build_gold_set.py` | Gold set construction (88 sources) |
| `ml/scripts/train/train_header_model.py` | Header branch training |
| `ml/scripts/train/train_value_model.py` | Values branch training |
| `ml/scripts/eval/evaluate.py` | CLI metric for evaluation |
| `ml/data/gold_set.json` | 2,231 labelled columns |
