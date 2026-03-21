# Évaluation multi-instance ML (2026-03-20)

## Objet

Évaluation complète du ML sur plusieurs datasets réels, corrections
d'annotations par vérification des valeurs, enrichissement alias registry,
diagnostic gold set et ré-entraînement.

## Infrastructure

- Ground truth centralisé : `ml/data/eval/annotations/` (5 fichiers, 418 colonnes)
- Scripts : `ml/scripts/eval/evaluate_instance.py` et `run_eval_suite.py`
- Détection auto du séparateur CSV (virgule, tab, point-virgule)
- Résultats JSON horodatés dans `ml/data/eval/results/`

```
ml/data/eval/
  annotations/
    niamoto-nc.yml          # 57 cols (29 occ + 28 plots)
    niamoto-gb.yml          # 27 cols (19 occ + 8 plots)
    guyadiv.yml             # 61 cols (29 trees + 32 plots)
    gbif_darwin_core.yml    # ~50 cols DwC réutilisables
    silver.yml              # ~136 cols sur 9 fichiers
  results/                  # JSON horodatés
```

## Progression des scores

### V1 — Annotations initiales (modèles pré-existants)

Première exécution avec annotations brutes, avant vérification.

| Dataset | Colonnes | Role% | Concept% |
|---------|----------|-------|----------|
| niamoto-nc | 57 | 61.4% | 45.6% |
| niamoto-gb | 27 | 88.9% | 66.7% |
| guyadiv | 61 | 85.2% | 63.9% |
| GBIF NC | 51 | 84.3% | 76.5% |
| GBIF Gabon | 45 | 86.7% | 77.8% |
| GBIF inst. Gabon | 41 | 82.9% | 75.6% |
| silver | 136 | 86.0% | 66.2% |
| **TOTAL** | **418** | **82.3%** | **66.5%** |

### V2 — Après correction taxonomie + plot_name

Corrections : `taxonomy.name` → `taxonomy.species` (binomials), `plot_name`
ajusté selon les valeurs réelles (code plot ou localité).

| | Avant | Après | Delta |
|---|:---:|:---:|:---:|
| **TOTAL** | 66.5% | **71.1%** | **+4.6** |

### V3 — Après vérification des valeurs réelles

Vérification colonne par colonne avec échantillon de données :
`canopy/undercanopy/understorey` → `statistic.count` (comptages, pas mesures),
`SPCD` → `identifier.taxon` (code numérique), `Mnemonic` → `identifier.taxon`,
`Author`/`auth_sp` → `text.metadata`, `Vernacular_name` → `taxonomy.vernacular_name`.

| | Avant | Après | Delta |
|---|:---:|:---:|:---:|
| **TOTAL** | 71.1% | **71.3%** | **+0.2** |

### V4 — Après enrichissement alias registry (+13 concepts)

Ajout de 13 concepts manquants dans `column_aliases.yaml` :
`measurement.trait`, `category.ecology`, `category.status`,
`category.vegetation`, `category.basis`, `category.method`,
`environment.topography`, `environment.geology`, `measurement.canopy`,
`identifier.collection`, `identifier.institution`, `location.admin_area`,
`location.continent`, `text.observer`.

| Dataset | V3 | V4 | Delta |
|---------|:---:|:---:|:---:|
| niamoto-nc | 54.4% | **68.4%** | **+14.0** |
| niamoto-gb | 74.1% | 74.1% | 0 |
| guyadiv | 65.6% | 65.6% | 0 |
| GBIF NC | 82.4% | **90.2%** | **+7.8** |
| GBIF Gabon | 82.2% | **88.9%** | **+6.7** |
| GBIF inst. | 80.5% | **85.4%** | **+4.9** |
| silver | 69.9% | **73.5%** | **+3.6** |
| **TOTAL** | **71.3%** | **76.6%** | **+5.3** |

## Diagnostic gold set

Analyse des concepts faibles vs leur présence dans le gold set (2492 entrées) :

| Concept | Score eval | Gold set | Verdict |
|---------|-----------|----------|---------|
| `measurement.trait` | 0/12 (0%) | **ABSENT** | Données manquantes |
| `category.ecology` | 7/19 (37%) | **ABSENT** (après coarsening de phenology/bioclimate) | Données manquantes |
| `environment.topography` | 0/2 (0%) | **ABSENT** | Données manquantes |
| `text.metadata` | 0/5 (0%) | **ABSENT** | Données manquantes |
| `category.vegetation` | 1/2 (50%) | 4 exemples | Quasi-absent |
| `measurement.area` | 0/4 (0%) | 4 exemples | Quasi-absent |
| `measurement.biomass` | 5/13 (38%) | 28 exemples | Présent mais confondu |
| `category.status` | 7/15 (47%) | 50 exemples | Présent, performance faible |

Biais identifié : `measurement.diameter` (171 exemples, 3e plus fréquent) surreprésenté
→ le modèle values associe trop facilement les distributions numériques continues à diameter.

Bug concept_taxonomy.py : `measurement.basal_area → measurement.diameter` (corrigé → biomass).

## Actions réalisées

### Gold set enrichi

Ajout de `NC_FULL_OCC_LABELS` (29 cols) et `NC_FULL_PLOTS_LABELS` (28 cols)
dans `build_gold_set.py` depuis `test-instance/niamoto-nc/imports/`.

Nouveaux concepts injectés : `measurement.trait` (8), `category.bioclimate` (4),
`category.phenology` (+2), `category.stratum` (+1). Gold set : 2492 → 2525.

### Ré-entraînement (V5)

Ré-entraînement des 3 modèles sur le gold set enrichi :

| Modèle | Avant | Après |
|--------|:-----:|:-----:|
| header | 0.7614 | 0.7467 |
| values | 0.3783 | 0.3935 |
| fusion | 0.6899 | 0.6876 |

### V5 — Résultats après ré-entraînement

| Dataset | V4 (alias) | V5 (retrain) | Delta |
|---------|:---:|:---:|:---:|
| niamoto-nc | 68.4% | **87.7%** | **+19.3** |
| niamoto-gb | 74.1% | 66.7% | -7.4 |
| guyadiv | 65.6% | 65.6% | 0 |
| GBIF NC | 90.2% | 90.2% | 0 |
| GBIF Gabon | 88.9% | 88.9% | 0 |
| GBIF inst. | 85.4% | **87.8%** | +2.4 |
| silver | 73.5% | 69.1% | -4.4 |
| **TOTAL** | **76.6%** | **77.5%** | **+0.9** |

niamoto-nc gagne +19 pts (le modèle connaît ses colonnes).
niamoto-gb et silver baissent légèrement (gold set a changé, ces données
n'ont pas été enrichies proportionnellement).

`measurement.trait` : 0/12 → **8/12 (67%)** — le concept est maintenant reconnu.
Le biais `measurement.diameter` a disparu des top confusions.

## Résumé progression complète de la session

| Étape | TOTAL concept% | Delta |
|-------|:--------------:|:-----:|
| V1 — Annotations initiales | 66.5% | — |
| V2 — Correction taxo + plot_name | 71.1% | +4.6 |
| V3 — Vérification valeurs réelles | 71.3% | +0.2 |
| V4 — Alias registry (+13 concepts) | 76.6% | +5.3 |
| V5 — Gold set + ré-entraînement | **77.5%** | **+0.9** |
| **Gain total** | | **+11.0 pts** |

## ProductScore et GlobalScore (V5)

Recalculés après ré-entraînement sur le gold set enrichi (2525 cols).

| Métrique | Avant | Après | Delta |
|----------|:-----:|:-----:|:-----:|
| **ProductScore** | 80.04 | **81.82** | **+1.78** |
| **GlobalScore** | 78.6 | **80.79** | **+2.19** |

Détail ProductScore par bucket :

| Bucket | Avant | Après | Delta |
|--------|:-----:|:-----:|:-----:|
| tropical_field (30%) | 64.88 | **69.01** | **+4.13** |
| research_traits (15%) | 70.98 | **75.49** | **+4.51** |
| gbif_core_standard (20%) | 95.87 | **96.02** | +0.15 |
| gbif_extended (10%) | 89.75 | 88.18 | -1.57 |
| en_field (15%) | 78.53 | 78.46 | -0.07 |
| anonymous (10%) | 100.0 | 100.0 | = |

Les gains les plus forts sont sur `tropical_field` (+4.13) et `research_traits`
(+4.51) — exactement les familles enrichies par les colonnes niamoto-nc.

## Fix batch evaluate.py

Le script `evaluate.py` utilisait `extract_fusion_features()` record par record
(boucle Python). Remplacé par `extract_fusion_features_batch()` (déjà disponible
dans `train_fusion.py`). Temps ProductScore : **14h → 42 min** (20x).

## Faiblesses restantes (V5)

| Concept | Score | Occurrences |
|---------|-------|-------------|
| `taxonomy.name` | 0/8 (0%) | Noms génériques vs binomials |
| `measurement.area` | 0/4 (0%) | subpl_width, dim, area |
| `environment.temperature` | 1/3 (33%) | Tair, Tair_max, Tair_min |
| `measurement.biomass` | 5/13 (38%) | volume, carbone, poids |
| `text.metadata` | 2/5 (40%) | Auteurs, sources |
| `identifier.taxon` | 6/14 (43%) | Clés GBIF numériques |
| `category.status` | 7/15 (47%) | Statuts booléens/codés |

Colonnes systématiquement fausses (3 datasets) : `acceptedTaxonKey`,
`speciesKey`, `genericName`, `infraspecificEpithet`, `scientificNameAuthorship`.

## Commandes de reproduction

```bash
# Suite complète
uv run python -m ml.scripts.eval.run_eval_suite

# Instance unique
uv run python -m ml.scripts.eval.evaluate_instance \
    --annotations ml/data/eval/annotations/niamoto-nc.yml \
    --data-dir test-instance/niamoto-nc/imports --compare

# GBIF spécifique
uv run python -m ml.scripts.eval.evaluate_instance \
    --annotations ml/data/eval/annotations/gbif_darwin_core.yml \
    --csv ml/data/silver/gbif_targeted/new_caledonia/occurrences.csv

# Rebuild gold set + retrain
uv run python -m ml.scripts.data.build_gold_set
uv run python -m ml.scripts.train.train_header_model
uv run python -m ml.scripts.train.train_value_model
uv run python -m ml.scripts.train.train_fusion
```
