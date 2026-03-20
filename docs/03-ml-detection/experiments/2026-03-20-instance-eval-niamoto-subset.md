# Évaluation multi-instance ML (2026-03-20)

## Objet

Évaluation complète du ML sur plusieurs datasets réels :
- **Tier 1** : 3 instances de production (niamoto-nc, niamoto-gb, GUYADIV)
- **Tier 1b** : exports GBIF Darwin Core (NC, Gabon, institutionnel)
- **Tier 2** : 7+ fichiers silver représentatifs

## Méthode

- Ground truth manuelle centralisée : `data/eval/annotations/`
- Script : `scripts/ml/eval/run_eval_suite.py`
- Évaluateur : `scripts/ml/eval/evaluate_instance.py`
- Modèles : header (0.7614), values (0.3783), fusion (0.6899) + cross-rank reciprocity
- Détection auto du séparateur CSV (virgule, tab, point-virgule)
- Lecture limitée à 500 lignes par fichier

## Structure d'évaluation

```
data/eval/
  annotations/
    niamoto-nc.yml          # 57 cols (29 occ + 28 plots)
    niamoto-gb.yml          # 27 cols (19 occ + 8 plots)
    guyadiv.yml             # 61 cols (29 trees + 32 plots)
    gbif_darwin_core.yml    # ~50 cols DwC réutilisables
    silver.yml              # ~136 cols sur 9 fichiers
  results/                  # JSON horodatés
```

## Résultats par dataset

### Tier 1 — Instances de production

| Instance | Colonnes | Role% | Concept% |
|----------|----------|-------|----------|
| niamoto-nc | 57 | 61.4% | 45.6% |
| niamoto-gb | 27 | 88.9% | 66.7% |
| guyadiv | 61 | 85.2% | 63.9% |

### Tier 1b — GBIF Darwin Core

| Source | Colonnes annotées | Role% | Concept% |
|--------|-------------------|-------|----------|
| GBIF NC régional | 51 | 84.3% | 76.5% |
| GBIF Gabon régional | 45 | 86.7% | 77.8% |
| GBIF Gabon institutionnel | 41 | 82.9% | 75.6% |

### Tier 2 — Silver représentatif

| Dataset | Colonnes | Role% | Concept% |
|---------|----------|-------|----------|
| silver (agrégé) | 136 | 86.0% | 66.2% |

Fichiers inclus : Berenty (Madagascar), BCI allométrie, Catalonia IEFC,
IFN France, Finland/Sweden, Afrique occ+plots, FIA Florida.

## Résultats détaillés — niamoto-nc

### occurrences.csv (29 colonnes)

| Mode | Role | Concept |
|------|------|---------|
| Alias seul | 11/29 (38%) | 11/29 (38%) |
| ML | 16/29 (55%) | 14/29 (48%) |

| Colonne | Attendu | Détecté | Conf | R | C |
|---------|---------|---------|------|---|---|
| id | identifier.record | identifier.record | 1.00 | ✓ | ✓ |
| id_taxonref | identifier.taxon | identifier.taxon | 1.00 | ✓ | ✓ |
| plot_name | identifier.plot | location.locality | 1.00 | ✗ | ✗ |
| taxaname | taxonomy.name | taxonomy.species | 0.74 | ✓ | ✗ |
| taxonref | taxonomy.name | taxonomy.species | 0.39 | ✓ | ✗ |
| family | taxonomy.family | taxonomy.family | 1.00 | ✓ | ✓ |
| genus | taxonomy.genus | taxonomy.genus | 1.00 | ✓ | ✓ |
| species | taxonomy.species | taxonomy.species | 1.00 | ✓ | ✓ |
| infra | taxonomy.name | measurement.diameter | 0.32 | ✗ | ✗ |
| id_rank | category.status | taxonomy.rank | 0.51 | ✗ | ✗ |
| dbh | measurement.diameter | measurement.diameter | 1.00 | ✓ | ✓ |
| height | measurement.height | measurement.height | 1.00 | ✓ | ✓ |
| strata | category.vegetation | statistic.count | 0.43 | ✗ | ✗ |
| flower | category.ecology | measurement.diameter | 0.72 | ✗ | ✗ |
| fruit | category.ecology | measurement.diameter | 0.72 | ✗ | ✗ |
| month_obs | event.date | event.date | 0.93 | ✓ | ✓ |
| bark_thickness | measurement.trait | other | - | ✗ | ✗ |
| leaf_area | measurement.leaf_area | measurement.leaf_area | 1.00 | ✓ | ✓ |
| leaf_ldmc | measurement.trait | other | - | ✗ | ✗ |
| leaf_sla | measurement.trait | other | - | ✗ | ✗ |
| leaf_thickness | measurement.trait | other | - | ✗ | ✗ |
| wood_density | measurement.wood_density | measurement.wood_density | 1.00 | ✓ | ✓ |
| elevation | location.elevation | location.elevation | 1.00 | ✓ | ✓ |
| rainfall | environment.precipitation | environment.precipitation | 1.00 | ✓ | ✓ |
| holdridge | category.ecology | other | - | ✗ | ✗ |
| province | location.admin_area | location.admin_area | 0.39 | ✓ | ✓ |
| in_forest | category.ecology | location.locality | 0.40 | ✗ | ✗ |
| in_um | category.status | measurement.diameter | 0.77 | ✗ | ✗ |
| geo_pt | location.coordinate | location.coordinate | 0.93 | ✓ | ✓ |

### plots.csv (28 colonnes)

| Mode | Role | Concept |
|------|------|---------|
| Alias seul | 4/28 (14%) | 3/28 (11%) |
| ML | 19/28 (68%) | 12/28 (43%) |

| Colonne | Attendu | Détecté | Conf | R | C |
|---------|---------|---------|------|---|---|
| id_plot | identifier.record | identifier.plot | 0.35 | ✓ | ✗ |
| plot | identifier.plot | identifier.plot | 0.33 | ✓ | ✓ |
| elevation | location.elevation | location.elevation | 1.00 | ✓ | ✓ |
| rainfall | environment.precipitation | environment.precipitation | 1.00 | ✓ | ✓ |
| holdridge | category.ecology | statistic.count | 0.45 | ✗ | ✗ |
| in_um | category.status | measurement.diameter | 0.80 | ✗ | ✗ |
| species_level | measurement.trait | other | - | ✗ | ✗ |
| total_stems | statistic.count | statistic.count | 0.95 | ✓ | ✓ |
| living_stems | statistic.count | statistic.count | 0.95 | ✓ | ✓ |
| nb_families | statistic.count | statistic.count | 0.46 | ✓ | ✓ |
| nb_species | statistic.count | measurement.height | 0.59 | ✗ | ✗ |
| shannon | measurement.trait | measurement.diameter | 0.74 | ✓ | ✗ |
| pielou | measurement.trait | measurement.diameter | 0.85 | ✓ | ✗ |
| simpson | measurement.trait | measurement.diameter | 0.34 | ✓ | ✗ |
| basal_area | measurement.biomass | measurement.basal_area | 1.00 | ✓ | ✗ |
| h_mean | measurement.height | measurement.diameter | 0.69 | ✓ | ✗ |
| dbh_median | measurement.diameter | measurement.diameter | 0.36 | ✓ | ✓ |
| biomass | measurement.biomass | measurement.biomass | 1.00 | ✓ | ✓ |
| wood_density_mean | measurement.wood_density | measurement.wood_density | 0.94 | ✓ | ✓ |
| pteridophytes | statistic.count | statistic.count | 0.82 | ✓ | ✓ |
| gymnospermae | statistic.count | measurement.diameter | 0.46 | ✗ | ✗ |
| monocotyledonae | statistic.count | measurement.diameter | 0.48 | ✗ | ✗ |
| dicotyledonae | statistic.count | measurement.diameter | 0.71 | ✗ | ✗ |
| emergent | statistic.count | statistic.count | 0.89 | ✓ | ✓ |
| canopy | measurement.canopy | measurement.diameter | 0.68 | ✓ | ✗ |
| undercanopy | measurement.canopy | statistic.count | 0.91 | ✗ | ✗ |
| understorey | measurement.canopy | statistic.count | 0.94 | ✗ | ✗ |
| geo_pt | location.coordinate | location.coordinate | 0.93 | ✓ | ✓ |

## Patterns d'erreurs cross-dataset

### 1. Sur-prédiction `measurement.diameter`

Le biais le plus fréquent. Le modèle prédit `measurement.diameter` pour de
nombreuses colonnes qui ne sont pas des diamètres.

Colonnes affectées (multi-dataset) :
- Booléens : `flower`, `fruit`, `in_um` → category.ecology/status
- Indices diversité : `shannon`, `pielou`, `simpson` → measurement.trait
- Comptages taxonomiques : `gymnospermae`, `monocotyledonae`, `dicotyledonae`
- Strate : `canopy` → measurement.canopy
- Hauteur : `h_mean` → measurement.height

Hypothèse : `measurement.diameter` surreprésenté dans le gold set, le modèle
values associe trop facilement les distributions numériques continues à ce concept.

### 2. Concept `measurement.trait` non reconnu

Aucune colonne `measurement.trait` correctement détectée sur niamoto-nc.
Problème confirmé cross-dataset (silver, GUYADIV).

### 3. Concept `category.*` mal détecté

Les colonnes catégorielles métier ne sont pas couvertes :
- `holdridge`, `strata`, `in_forest` → `other` ou faux positif
- Booléens traités comme numériques

### 4. GBIF : bonne performance sur le noyau Darwin Core (75-78%)

Résultats très cohérents sur 3 exports GBIF (NC 76.5%, Gabon 77.8%,
institutionnel 75.6%). Les colonnes standard DwC (family, genus, species,
decimalLatitude, country, eventDate, etc.) sont bien reconnues.

9 colonnes DwC systématiquement fausses sur les 3 exports :
- `scientificName`, `acceptedScientificName` → taxonomy.species au lieu de .name
- `catalogNumber` → identifier.record au lieu de .collection
- `acceptedTaxonKey`, `speciesKey` → non détectés
- `genericName`, `infraspecificEpithet`, `taxonomicStatus`, `scientificNameAuthorship`

### 5. Confusion `taxonomy.name` → `taxonomy.species` (16x, 7 datasets)

Erreur la plus fréquente cross-dataset. Le modèle a tendance à spécialiser
vers `taxonomy.species` les colonnes qui contiennent des noms scientifiques
complets (genre + espèce). Concerne aussi bien les GBIF que les instances
de production.

## Pistes d'amélioration

### Court terme (alias + gold set)

1. Alias pour traits courants (`leaf_sla`, `leaf_ldmc`, `bark_thickness`)
2. Enrichir gold set avec catégoriels métier (`holdridge`, `strata`, `in_forest`)
3. Exemples booléens écologiques (`flower`, `fruit`)
4. Comptages taxonomiques (`gymnospermae`, `monocotyledonae`)

### Moyen terme (modèle)

1. Réduire biais `measurement.diameter` dans le modèle values
2. Meilleure détection booléens (0/1) comme catégoriels
3. Concept `measurement.trait` mieux représenté

### Long terme (pipeline)

1. Intégrer annotations d'instance comme données d'entraînement
2. Automatiser re-benchmark après chaque amélioration
3. Cibler 70%+ concept sur Tier 1, 85%+ sur GBIF DwC core

## Résultats agrégés

```
418 colonnes évaluées — 82.3% role, 66.5% concept
Temps total : 1307s (~22 min)
Résultats JSON : data/eval/results/20260320_111351.json
```

## Commandes de reproduction

```bash
# Suite complète
uv run python -m scripts.ml.eval.run_eval_suite

# Instance unique
uv run python -m scripts.ml.eval.evaluate_instance \
    --annotations data/eval/annotations/niamoto-nc.yml \
    --data-dir test-instance/niamoto-nc/imports --compare

# GBIF spécifique
uv run python -m scripts.ml.eval.evaluate_instance \
    --annotations data/eval/annotations/gbif_darwin_core.yml \
    --csv data/silver/gbif_targeted/new_caledonia/occurrences.csv

# Silver
uv run python -m scripts.ml.eval.evaluate_instance \
    --annotations data/eval/annotations/silver.yml \
    --data-dir data/silver
```
