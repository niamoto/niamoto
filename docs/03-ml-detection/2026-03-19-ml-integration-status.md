# Full Status Report — ML Detection × Niamoto Application

## Context

The `feat/ml-detection-improvement` branch built a complete ML pipeline
(alias → header → values → fusion → semantic_profile → affordances). This document
reviews what works, what is integrated into the app, and what still needs to be
connected.

---

## 1. ML Model Status

### Trained and Delivered Models

| Model | File | Size | Technique |
|-------|------|------|-----------|
| Header | `models/header_model.joblib` | 2.6 MB | TF-IDF char n-grams + LogReg |
| Values | `models/value_model.joblib` | 38 MB | HistGradientBoosting (38 features) |
| Fusion | `models/fusion_model.joblib` | 50 KB | LogReg on aligned probas + meta-features |

All 3 models are **bundled in the package** via `pyproject.toml` and loaded
lazily at runtime by `ColumnClassifier`.

### Gold Set

- **2492 columns** (1896 gold + 596 synthetic)
- **61 concepts**, **10 roles**, **7 languages**
- Sources: Guyane (Paracou), targeted GBIF (NC/GF/GA/CM), institutional GBIF
  (GA/CM), forest inventories, synthetic data

### Current Scores

| Metric | Score |
|--------|-------|
| **NiamotoOfflineScore** | 78.6 |
| **ProductScore** | 79.2 |
| GBIF core standard | 96.3 |
| Anonymous | 100.0 |
| English standard | 95.7 |
| tropical_field | 64.0 |
| en_field | 75.9 |
| forest_inventory | 41.8 |

**Model verdict**: strong on GBIF standard and anonymous columns, average on
tropical field data and business-coded headers.

---

## 2. Integration in the Application — What WORKS

### Import Pipeline (end-to-end functional)

```
Upload CSV → POST /api/smart-config/auto-configure
  → ColumnDetector (rules + heuristics)
  → Hierarchy / FK relation detection
  → import.yml generation
  → Review/edit by user
  → POST /api/imports/execute/all
  → DataProfiler → ColumnClassifier (ML 3 branches)
  → Semantic profiles stored in EntityRegistry
  → Transformer suggestions available
```

### Functional GUI Components

- **ImportWizard**: 6-phase wizard (upload → config → review → import → done)
- **FileUploadZone**: drag-and-drop CSV/GPKG/TIF/ZIP
- **AutoConfigDisplay**: shows detected datasets/references/links
- **YamlPreview**: YAML review before import
- **ImportProgress**: async tracking with polling

### Active API Endpoints

| Endpoint | Role | ML? |
|----------|------|-----|
| `POST /api/smart-config/auto-configure` | Full auto-config | Heuristics |
| `POST /api/smart-config/analyze-file` | Column analysis | Heuristics |
| `POST /api/smart-config/detect-hierarchy` | Taxo hierarchy | Heuristics |
| `POST /api/imports/execute/all` | Full import | **ML (profiler)** |
| `GET /api/transformer-suggestions/{entity}` | Widget suggestions | Via semantic profiles |

### Semantic Profiles & Affordances

- `semantic_profile.py`: role + concept + affordances per column
- `affordance_matcher.py`: transformer→widget matching
- Profiles stored in `EntityRegistry` after import
- Transformer suggestions retrievable via API

---

## 3. The GAP — What Is NOT Connected

### ML Does NOT Run During Auto-Config

This is the central issue:

- **During upload/auto-config**: `ColumnDetector` uses **heuristic rules**
  (regex patterns, FK by name), NOT the ML classifier
- **During import**: `DataProfiler` uses the **full ML classifier**
  (alias → header → values → fusion)
- The user sees heuristic results, not ML results

Consequence: auto-config quality depends on heuristics, not on the trained
ML models.

### ML Confidence Scores Are Invisible

- The classifier produces a confidence score (0-1) per column
- This score is **never shown to the user** in the GUI
- The user does not know whether detection is reliable or uncertain

### Semantic Profiles Invisible During Import

- Profiles are generated and stored but **not displayed**
- No endpoint to retrieve intermediate profiles
- The user does not see detected affordances

### Widget Suggestions Not Connected to the GUI

- `class_object_suggester.py` exists but is **not wired to the UI**
- The `transformer-suggestions` endpoint works but is **not called**
  automatically after import

---

## 4. Two Parallel Detection Systems

| Component | When | Technique | File |
|-----------|------|-----------|------|
| `ColumnDetector` | Auto-config (before import) | Rules/heuristics | `column_detector.py` |
| `ColumnClassifier` | Import (profiling) | ML 3 branches | `classifier.py` |

This is the source of confusion: the ML work on this branch improves
`ColumnClassifier`, but the user first sees `ColumnDetector`.

---

## 5. Options to Close the Gap

### Option A — Wire ML into Auto-Config

- Replace or complement `ColumnDetector` with `ColumnClassifier` in
  `smart_config.py`
- The user would see ML results as soon as they upload
- Risk: ML is slower than heuristics (model loading)

### Option B — Show ML Results After Import

- Add an endpoint `/api/semantic-profiles/{entity}`
- Display semantic profiles + confidence in the post-import UI
- Less disruptive, allows visual validation of ML quality

### Option C — Merge the Two Detectors

- `ColumnDetector` becomes a wrapper that first calls `AliasRegistry`,
  then `ColumnClassifier`, then fallback rules
- A single detection path for the entire app
- More coherent but a larger undertaking

### Option D — Freeze and Merge the Branch As-Is

- ML runs during import, which is already useful
- Auto-config heuristics work for simple cases
- Connect ML to the GUI in a future iteration

---

## 6. Retained Recommendation

### Phase 1 — Merge the Branch As-Is

ML runs during import, models are delivered, tests pass.
Merge now to stop accumulating integration debt.

Prerequisites before merge:
- [ ] Verify tests pass on main
- [ ] Clean up obsolete files (`current-state.md` from December 2024)
- [ ] Ensure .joblib models are in the correct state
- [ ] Clean rebase or squash merge

### Phase 2 — Wire ML into ColumnDetector

Make `ColumnClassifier` the single semantic detection engine:

- `ColumnDetector` keeps: FK analysis, hierarchy detection, dataset vs
  reference inference
- `ColumnDetector` delegates to `ColumnClassifier`: semantic column
  classification (type, concept, confidence)
- `smart_config.py` exposes ML scores in the auto-configure response
- GUI displays per-column confidence in `AutoConfigDisplay`

Files to modify:
- `src/niamoto/core/utils/column_detector.py` — call ColumnClassifier
- `src/niamoto/gui/api/routers/smart_config.py` — return ML scores
- `gui/ui/src/components/sources/AutoConfigDisplay.tsx` — display confidence

### Phase 3 — Expose Semantic Profiles in the UI

- Endpoint `GET /api/semantic-profiles/{entity_name}`
- Display affordances and suggestions post-import
- Wire `class_object_suggester` to the GUI

---

## 7. Summary

The ML pipeline is **built, trained, and integrated into import profiling**,
but the user does not yet see it during auto-config — they see the
`ColumnDetector` heuristics, not the ML models.

The clean solution: merge first, then unify the detectors so that all the
autoresearch work directly benefits the UX.
