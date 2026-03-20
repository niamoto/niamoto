---
title: Rewrite ML detection dashboard
type: refactor
date: 2026-03-20
---

# Rewrite ML detection dashboard

## Overview

Complete rewrite of `docs/03-ml-detection/ml-detection-dashboard.html` — a self-contained single-file HTML dashboard (Plotly + vanilla JS) serving as the internal technical reference for the ML detection system. The current dashboard is frozen at pre-retraining state and needs updating with all recent work: new gold set, retrained models, instance evaluation, error patterns, surrogate loop, and cross-rank reciprocity features.

## Motivation

The dashboard data is stale: gold set 2,231 vs actual 2,492, fusion F1 0.9720 (data leak) vs 0.6899 (leak-free), no ProductScore, no instance evaluation, missing 6 GBIF targeted sources. The roadmap section describes phases that no longer match reality. Everything is in French while the rest of `docs/03-ml-detection/` is now in English.

## Proposed Solution

Rewrite the HTML file with 10 sections, all data updated, all text in English. Keep the same technical stack (single HTML file, Plotly CDN, vanilla JS, CSS custom properties). Reuse the excellent methodology justification blocks. Add new sections for instance evaluation, error patterns, and training evolution.

## Implementation Steps

### Step 1: Update DATASETS array and hero stats

Update the JavaScript `DATASETS` array:
- Add 6 GBIF targeted sources (gbif_targeted_new_caledonia, gbif_targeted_guyane, gbif_targeted_gabon, gbif_targeted_cameroon, gbif_targeted_institutional_gabon, gbif_targeted_institutional_cameroon)
- Add forestscan_paracou_census
- Update column counts if any changed
- Fix continent count to 5 (French convention)

Update hero stat cards:
- ProductScore: 80.04 (new primary KPI, prominent)
- NiamotoOfflineScore: 78.6
- Gold set: 2,492 columns
- Sources: 94+
- Languages: 8
- Concepts: 61
- GPU: 0

Second row model scores:
- Header F1: 0.7614
- Values F1: 0.3783
- Fusion F1: 0.6899 (leak-free CV)
- Instance Role%: 82.3% (new)

### Step 2: Update pipeline architecture section (02)

- Update values features count (43 → 37-38)
- Add cross-rank reciprocity features to fusion detail panel (header_top1_value_rank, value_top1_header_rank, top2_cross_match, both_weak)
- Fix fusion score display
- Translate all French text to English

### Step 3: Update gold set & sources section (03)

- Update DATASETS JS array (from Step 1)
- Translate chart titles and labels to English
- Update filter button counts
- World map, continent chart, language pie chart all auto-update from data

### Step 4: Update concept taxonomy section (04)

- Verify CONCEPTS array counts against current gold set (may need minor updates)
- Translate to English

### Step 5: New "Evaluation Results" section (05)

Replace the old "Résultats & évaluation" section with two sub-sections:

**5a — ProductScore Breakdown**
New horizontal bar chart with the 6 weighted components:

| Bucket | Score | Weight |
|--------|-------|--------|
| tropical_field | 64.88 | 30% |
| gbif_core_standard | 95.87 | 20% |
| research_traits | 70.98 | 15% |
| en_field | 78.53 | 15% |
| anonymous | 100.0 | 10% |
| gbif_extended | 89.75 | 10% |

**5b — Holdouts & Diagnostics**
- Update holdout language chart (remove zh, keep fr/es/de with current scores: fr 66.2, es 89.5, de 92.7)
- Update holdout family chart with current scores
- Add structural diagnostics bar chart: en_standard 95.7, en_field 75.9, coded_headers 72.6, gbif_core_standard 96.3, gbif_extended 87.0
- Add forest_inventory sub-split: ifn_fr 17.9, fia_en 50.3, nordic_inventory 65.2

### Step 6: New "Instance Evaluation" section (06)

Entirely new section with data from `experiments/2026-03-20-instance-eval-niamoto-subset.md`.

**6a — Summary table** (Plotly horizontal bar or HTML table):

| Tier | Instance | Columns | Role% | Concept% |
|------|----------|---------|-------|----------|
| Tier 1 | niamoto-nc | 57 | 61.4% | 45.6% |
| Tier 1 | niamoto-gb | 27 | 88.9% | 66.7% |
| Tier 1 | guyadiv | 61 | 85.2% | 63.9% |
| Tier 1b | GBIF NC | 51 | 84.3% | 76.5% |
| Tier 1b | GBIF Gabon | 45 | 86.7% | 77.8% |
| Tier 1b | GBIF inst. | 41 | 82.9% | 75.6% |
| Tier 2 | Silver | 136 | 86.0% | 66.2% |

Aggregate: 418 columns, 82.3% role, 66.5% concept.

**6b — Alias vs ML comparison** (collapsible `<details>`) for niamoto-nc occurrences (29 cols):
- Alias only: 11/29 role, 11/29 concept
- ML: 16/29 role, 14/29 concept
- Column-by-column table with checkmarks

### Step 7: New "Error Patterns" section (07)

Consolidate cross-dataset error analysis into a diagnostic section:

1. **Over-prediction `measurement.diameter`** — flower, fruit, in_um, shannon, pielou, simpson, gymnospermae, h_mean, canopy
2. **`measurement.trait` unrecognized** — leaf_sla, leaf_ldmc, bark_thickness (0 correct on niamoto-nc)
3. **`category.*` poorly detected** — holdridge, strata, in_forest → other or false positive
4. **`taxonomy.name` → `taxonomy.species`** — 16 occurrences across 7 datasets
5. **GBIF DwC systematic errors** — scientificName, catalogNumber, acceptedTaxonKey, etc. (9 columns)

Each with examples table and hypothesized cause.

### Step 8: New "Training Evolution" section (08)

Replace old autoresearch progress:

**8a — Autoresearch iterations** — Keep line charts for header and values progression. Update header data to include "Round 2 (2,492 cols)" data point. Update values data.

**8b — Cross-rank reciprocity gain** — Box with the 4 new features and impact:
- surrogate-fast: 55.63 → 56.55 (+0.92)
- surrogate-mid: 59.27 → 60.17 (+0.89)
- ProductScore: 79.25 → 80.04 (+0.79)

**8c — Surrogate loop overview** — Brief description + key metrics:
- Cache build: ~8min one-shot
- surrogate-fast: ~1.7s per eval
- Validation chain diagram: fast → mid → product-score → niamoto-score

**8d — Batch optimization** — Training time: 5h → 15min (20x), identical results.

### Step 9: Update methodology section (09)

Keep the 5 justification blocks (char n-grams, TF-IDF+LR, HistGBT, GroupKFold, macro-F1). Translate all French text to English. These are high-quality and still valid.

### Step 10: Update references section (10)

Translate section headers to English. Keep the bibliography as-is.

### Step 11: Remove Roadmap and Alternatives sections

- **Roadmap**: Phases no longer correspond to reality. Remove entirely.
- **Alternatives**: Keep but update — fix Niamoto score to 80.04 (ProductScore), update gold set size to 2,492, mark Sentence Transformers as "Not planned" instead of "Phase 4".

### Step 12: Update navigation, footer, translate remaining UI

- Update `<nav>` links to match new section structure
- Update footer date to 2026-03-20
- Translate all remaining French text (nav labels, chart labels, hover text, button labels)

## Acceptance Criteria

- [ ] All hero stats updated to current values (ProductScore 80.04, gold set 2,492, etc.)
- [ ] DATASETS array includes 6 GBIF targeted + Paracou sources
- [ ] Fusion F1 corrected from 0.9720 to 0.6899
- [ ] New Instance Evaluation section with tier summary and niamoto-nc detail
- [ ] New Error Patterns section with 5 cross-dataset patterns
- [ ] New Training Evolution section with cross-rank gain and surrogate loop
- [ ] ProductScore breakdown chart with weighted components
- [ ] All text translated to English
- [ ] Methodology justification blocks preserved and translated
- [ ] Roadmap section removed
- [ ] Navigation updated to match new structure
- [ ] Dashboard opens correctly in browser with all Plotly charts rendering
- [ ] Single self-contained HTML file (only external dep: Plotly CDN)

## Dependencies & Risks

**Data source**: All numbers come from experiment logs already in the repo. No external data needed.

**Risk**: The HTML file is ~1,300 lines. The rewrite will be similar or larger. Testing requires opening in a browser — verify charts render correctly.

**Risk**: Plotly CDN dependency. The dashboard uses `plotly-2.35.2.min.js` from CDN. Keep this version (don't upgrade unnecessarily).

## References

- Brainstorm: `docs/brainstorms/2026-03-20-ml-dashboard-rewrite-brainstorm.md`
- Current dashboard: `docs/03-ml-detection/ml-detection-dashboard.html`
- Instance evaluation data: `docs/03-ml-detection/experiments/2026-03-20-instance-eval-niamoto-subset.md`
- Iteration log: `docs/03-ml-detection/experiments/2026-03-17-ml-detection-iteration-log.md`
- Architecture: `docs/03-ml-detection/branch-architecture.md`
- Overview: `docs/03-ml-detection/overview.md`
