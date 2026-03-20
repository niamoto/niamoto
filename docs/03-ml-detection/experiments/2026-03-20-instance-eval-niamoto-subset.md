# Évaluation par instance — niamoto-subset (2026-03-20)

## Objet

Première évaluation complète du ML sur une instance réelle finalisée.
Mesure la qualité de détection sur **toutes les colonnes** (57), pas seulement
les colonnes structurelles de l'import.yml.

## Méthode

- Ground truth manuelle : `test-instance/niamoto-subset/config/column_annotations.yml`
- 29 colonnes `occurrences.csv` + 28 colonnes `plots.csv` = 57 colonnes
- Script : `scripts/ml/evaluate_instance.py --compare`
- Modèles utilisés : header (0.7614), values (0.3783), fusion (0.6899)
  avec features cross-rank reciprocity

## Résultats globaux

| Mode | Role correct | Concept correct |
|------|-------------|-----------------|
| **Alias seul** | 15/57 (26%) | 14/57 (25%) |
| **ML** | 35/57 (61%) | 26/57 (46%) |
| **Delta** | **+35 pts** | **+21 pts** |

## Résultats par fichier

### occurrences.csv (29 colonnes)

| Mode | Role | Concept |
|------|------|---------|
| Alias seul | 11/29 (38%) | 11/29 (38%) |
| ML | 16/29 (55%) | 14/29 (48%) |

### plots.csv (28 colonnes)

| Mode | Role | Concept |
|------|------|---------|
| Alias seul | 4/28 (14%) | 3/28 (11%) |
| ML | 19/28 (68%) | 12/28 (43%) |

## Détail ML — occurrences.csv

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

## Détail ML — plots.csv

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

## Patterns d'erreurs identifiés

### 1. Sur-prédiction `measurement.diameter`

Le modèle prédit `measurement.diameter` pour de nombreuses colonnes qui ne sont
pas des diamètres. C'est le biais le plus fréquent.

Colonnes affectées :
- `flower`, `fruit` → booléens (category.ecology)
- `in_um` → booléen (category.status)
- `infra` → texte taxonomique (taxonomy.name)
- `shannon`, `pielou`, `simpson` → indices de diversité (measurement.trait)
- `h_mean` → hauteur moyenne (measurement.height)
- `gymnospermae`, `monocotyledonae`, `dicotyledonae` → comptages (statistic.count)
- `canopy` → strate (measurement.canopy)

Hypothèse : le modèle `values` voit des distributions numériques et les associe
trop facilement à `measurement.diameter` qui est surreprésenté dans le gold set.

### 2. Concept `measurement.trait` non reconnu

Aucune colonne `measurement.trait` n'est correctement détectée :
- `bark_thickness`, `leaf_ldmc`, `leaf_sla`, `leaf_thickness` → `other`
- `species_level`, `shannon`, `pielou`, `simpson` → `other` ou `measurement.diameter`

Hypothèse : les noms composés (`leaf_ldmc`, `leaf_sla`) ne sont pas dans les
patterns connus du header, et les valeurs ne distinguent pas un trait d'une
autre mesure continue.

### 3. Concept `category.*` mal détecté

Les colonnes catégorielles sont rarement reconnues :
- `holdridge`, `strata`, `in_forest` → `other` ou faux positif
- `flower`, `fruit` → `measurement.diameter` (booléens traités comme numériques)

Hypothèse : les catégories à vocabulaire métier ne sont pas couvertes par le
gold set. Les booléens sont ambigus pour le modèle values.

### 4. Confusion `statistic.count` ↔ `measurement.diameter`

Sur les colonnes de comptage de plots :
- `total_stems`, `living_stems`, `pteridophytes`, `emergent` → correct
- `gymnospermae`, `monocotyledonae`, `dicotyledonae` → `measurement.diameter`

Hypothèse : les noms taxonomiques latins ne sont pas reconnus comme des
comptages. Le modèle header les associe plutôt à de la taxonomie ou de la mesure.

### 5. `measurement.canopy` non reconnu

- `canopy` → `measurement.diameter`
- `undercanopy`, `understorey` → `statistic.count`

Hypothèse : `measurement.canopy` est un concept rare dans le gold set. Les
noms `undercanopy`/`understorey` ne matchent pas les patterns connus.

## Pistes d'amélioration

### Court terme (alias + gold set)

1. Ajouter des alias pour les noms de traits courants (`leaf_sla`, `leaf_ldmc`,
   `bark_thickness`)
2. Enrichir le gold set avec des colonnes catégorielles métier (`holdridge`,
   `strata`, `in_forest`, `in_um`)
3. Ajouter des exemples de colonnes booléennes écologiques (`flower`, `fruit`)
4. Ajouter des comptages taxonomiques (`gymnospermae`, `monocotyledonae`, etc.)

### Moyen terme (modèle)

1. Réduire le biais `measurement.diameter` dans le modèle values — probablement
   via une meilleure représentation des distributions de comptages vs mesures
   continues
2. Améliorer la détection de booléens (0/1, true/false) comme catégoriels
3. Ajouter `measurement.trait` comme concept mieux représenté dans les données
   d'entraînement

### Long terme (pipeline)

1. Tester avec les données de `niamoto-gb` une fois la config validée
2. Intégrer les annotations d'instance comme nouvelles données d'entraînement
3. Automatiser le re-benchmark après chaque amélioration

## Commandes de reproduction

```bash
# Évaluation complète avec comparaison alias vs ML
uv run python -m scripts.ml.evaluate_instance \
    --instance test-instance/niamoto-subset --compare

# ML seul
uv run python -m scripts.ml.evaluate_instance \
    --instance test-instance/niamoto-subset

# Alias seul
uv run python -m scripts.ml.evaluate_instance \
    --instance test-instance/niamoto-subset --no-ml
```
