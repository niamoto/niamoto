# ML Detection Dashboard — Complete Rewrite

## What We're Building

A complete rewrite of `docs/03-ml-detection/ml-detection-dashboard.html` — a self-contained single-file HTML dashboard with Plotly charts, interactive tables, and detailed methodology justifications.

**Audience**: Internal reference for developers working on the ML detection branch. Comprehensive and technical — shows strengths, weaknesses, and actionable diagnostics.

**Language**: English (consistent with the rest of `docs/03-ml-detection/`).

## Why This Rewrite

The current dashboard is frozen at a pre-retraining state (March 17, 2026). Since then:

- Gold set grew from 2,231 to 2,492 columns (Paracou + 6 GBIF targeted sources)
- Models were retrained with cross-rank reciprocity features
- ProductScore metric was introduced (80.04)
- Fusion F1 was corrected from 0.9720 (data leak) to 0.6899 (leak-free CV)
- Training optimized from 5h to 15min (batch extraction)
- Full instance evaluation was run (418 columns, 82.3% role accuracy)
- Surrogate autoresearch loop was implemented and measured
- Error patterns were systematically catalogued across datasets

The dashboard needs to reflect all of this.

## Structure (9 sections)

### 01 — Summary (Hero)

Top-level KPIs in stat cards:

| KPI | Value | Note |
|-----|-------|------|
| ProductScore | 80.04 | Primary metric |
| NiamotoOfflineScore | 78.6 | Global composite |
| Gold set | 2,492 | 1,896 gold + 596 synthetic |
| Sources | 94+ | 88 original + 6 GBIF targeted |
| Continents | 5 | Per French convention |
| Languages | 8 | EN, FR, ES, PT, DE, ID, ZH + anonymous |
| Concepts | 61 | 10 roles |
| GPU required | 0 | Fully offline |

Second row — model scores:

| Model | Score |
|-------|-------|
| Header F1 | 0.7614 |
| Values F1 | 0.3783 |
| Fusion F1 | 0.6899 (leak-free) |
| Instance Role% | 82.3% |

### 02 — Pipeline Architecture

Keep the interactive pipeline diagram (alias → header → values → fusion → semantic projection). Update:

- Values features count: 43 → 37-38
- Add cross-rank reciprocity features to fusion detail panel
- Fix fusion F1 to leak-free value
- Update hyperparameters if changed

### 03 — Gold Set & Data Sources

Keep the world map, continent/language charts, filterable source table. Update:

- Add 6 new GBIF targeted sources (NC, GF, GA, CM + institutional GA, CM)
- Add Paracou/ForestScan
- Update DATASETS array with correct column counts
- Update continent/language distributions

### 04 — Concept Taxonomy

Keep sunburst chart and concept table. Update counts if they changed with the larger gold set.

### 05 — Evaluation Results

**New section replacing the old "Résultats & évaluation"**. Two sub-sections:

**5a — ProductScore Breakdown**
Horizontal bar chart showing the 6 ProductScore components with weights:
- tropical_field (30%): 64.88
- gbif_core_standard (20%): 95.87
- research_traits (15%): 70.98
- en_field (15%): 78.53
- anonymous (10%): 100.0
- gbif_extended (10%): 89.75

**5b — Holdouts & Diagnostics**
- Holdout by language (fr, es, de — remove zh as non-strategic)
- Holdout by family (dwc_gbif, forest_inventory, tropical_field, research_traits)
- Structural diagnostics: en_standard, en_field, coded_headers, gbif_core_standard, gbif_extended
- Forest inventory sub-split: ifn_fr (17.9), fia_en (50.3), nordic_inventory (65.2)

### 06 — Instance Evaluation

**Entirely new section** with data from `experiments/2026-03-20-instance-eval-niamoto-subset.md`.

**6a — Summary by tier**

| Tier | Instance | Columns | Role% | Concept% |
|------|----------|---------|-------|----------|
| Tier 1 | niamoto-nc | 57 | 61.4% | 45.6% |
| Tier 1 | niamoto-gb | 27 | 88.9% | 66.7% |
| Tier 1 | guyadiv | 61 | 85.2% | 63.9% |
| Tier 1b | GBIF NC | 51 | 84.3% | 76.5% |
| Tier 1b | GBIF Gabon | 45 | 86.7% | 77.8% |
| Tier 1b | GBIF inst. | 41 | 82.9% | 75.6% |
| Tier 2 | Silver | 136 | 86.0% | 66.2% |

**6b — Alias vs ML comparison** (collapsible detail for niamoto-nc)

Show the column-by-column table with alias-only vs ML performance.

### 07 — Error Patterns

**New section** consolidating cross-dataset error analysis:

1. **Over-prediction of `measurement.diameter`** — booleans, diversity indices, taxonomic counts, canopy, height all misclassified
2. **`measurement.trait` unrecognized** — leaf_sla, leaf_ldmc, bark_thickness all fail
3. **`category.*` poorly detected** — holdridge, strata, in_forest not covered
4. **`taxonomy.name` → `taxonomy.species` confusion** (16 occurrences, 7 datasets)
5. **GBIF Darwin Core systematic errors** — 9 DwC columns consistently wrong

Each pattern with examples and hypothesized cause.

### 08 — Training Evolution

**Replaces old autoresearch progress section.** Three sub-sections:

**8a — Autoresearch iterations**
Keep the header/values progress line charts. Add annotations for key events:
- "Round 2 (2,492 cols)" on the header chart
- "Cross-rank reciprocity" gain marker

**8b — Cross-rank reciprocity gain**
The 4 new fusion features and their impact:
- surrogate-fast: 55.63 → 56.55 (+0.92)
- surrogate-mid: 59.27 → 60.17 (+0.89)
- ProductScore: 79.25 → 80.04 (+0.79)

**8c — Surrogate loop**
Brief overview of the fusion-only surrogate loop:
- Cache build: ~8min (one-shot)
- surrogate-fast: ~1.7s per evaluation
- Validation chain: fast → mid → product-score → niamoto-score

### 09 — Methodology

Keep the justified methodology blocks (char n-grams, TF-IDF+LR, HistGBT, GroupKFold, macro-F1). These are excellent and still valid. Translate to English.

### 10 — References

Keep the bibliography. Translate section headers to English.

## Key Decisions

- **Self-contained single HTML file** — no external dependencies except Plotly CDN
- **English throughout** — consistent with docs/03-ml-detection/
- **ProductScore as primary KPI** — NiamotoOfflineScore becomes secondary
- **Instance evaluation as new first-class section** — this is what matters for product validation
- **Error patterns extracted from logs** — actionable diagnostics, not just scores
- **Remove old Roadmap section** — phases are outdated, replaced by training evolution timeline
- **Remove Alternatives comparison** — or update it if worth keeping (some data was wrong)
- **Fusion F1 corrected** — 0.9720 was with data leakage, 0.6899 is the real leak-free score

## Data Sources

All data for the dashboard comes from:
- `experiments/2026-03-17-ml-detection-iteration-log.md` — score evolution, holdouts, autoresearch iterations
- `experiments/2026-03-20-instance-eval-niamoto-subset.md` — instance evaluation results
- `scripts/ml/build_gold_set.py` — source list and column counts
- `overview.md` / `branch-architecture.md` — architecture description

## Open Questions

1. Should the Alternatives comparison table be kept (updated) or removed entirely?
2. Should we embed the full niamoto-nc column-by-column table (57 rows) or just show a summary?
3. Should the dashboard auto-generate from data files, or keep hardcoded data in the JS?
