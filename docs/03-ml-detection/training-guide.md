# ML Detection — Training & Evaluation Guide

Workflow complet pour entraîner, évaluer et améliorer le système de détection
sémantique de colonnes. Chaque étape est indépendante et reproductible.

## Vue d'ensemble du pipeline

```
data/silver/          →  build_gold_set.py  →  data/gold_set.json
                                                     │
                                              ┌──────┴──────┐
                                              ▼              ▼
                                     train_header_model   train_value_model
                                              │              │
                                              └──────┬───────┘
                                                     ▼
                                              train_fusion
                                                     │
                                                     ▼
                                          models/*.joblib
                                                     │
                              column_aliases.yaml ───►│
                                                     ▼
                                          run_eval_suite.py
                                                     │
                                                     ▼
                                     data/eval/results/*.json
```

## 1. Données sources

### Silver (données brutes)

Les données brutes sont dans `data/silver/`. Chaque fichier CSV est un dataset
écologique réel (inventaire forestier, GBIF, traits, etc.).

```
data/silver/
  guyane/GUYADIV_*.csv          # Guyane Française
  afrique/                      # Gabon, Cameroun, Congo
  nc_niamoto/                   # Nouvelle-Calédonie (format Gabon)
  gbif_targeted/                # Exports GBIF régionaux
  ifn_france/                   # Inventaire forestier français
  finland_sweden/               # Données nordiques
  fia_fl_tree.csv               # USDA Forest Inventory (Florida)
  Forest_Data_Berenty_Reserve.csv  # Madagascar
  zenodo_bci_allometry.csv      # BCI Panama
  iefc_catalonia.csv            # Catalogne
```

### Instances Niamoto

Les instances de production contiennent des CSV avec des colonnes spécifiques :

```
test-instance/niamoto-nc/imports/   # Nouvelle-Calédonie (57 cols)
test-instance/niamoto-gb/imports/   # Gabon (27 cols)
```

### Annotations d'évaluation

Ground truth vérifié pour l'évaluation, centralisé dans `data/eval/annotations/`.
**Ne pas confondre** avec les labels du gold set — les annotations eval servent
de benchmark indépendant.

## 2. Gold set

Le gold set est le jeu d'entraînement. Chaque entrée est une colonne labélisée
avec son concept sémantique et un échantillon de valeurs.

### Construction

```bash
uv run python -m scripts.ml.build_gold_set
```

Produit `data/gold_set.json` (~2500 entrées, 60+ concepts).

### Ajouter une source

Dans `scripts/ml/build_gold_set.py` :

1. Créer un dict de labels :
```python
MY_LABELS = {
    "column_name": ("concept.subconcept", "role"),
    "dbh": ("measurement.diameter", "measurement"),
    "species": ("taxonomy.species", "taxonomy"),
}
```

2. Ajouter dans la liste `SOURCES` :
```python
{
    "name": "my_dataset",
    "path": ROOT / "data/silver/my_file.csv",
    "labels": MY_LABELS,
    "language": "en",
    "sample_rows": 1000,  # None = tout le fichier
},
```

3. Rebuilder : `uv run python -m scripts.ml.build_gold_set`

### Taxonomie de concepts

Les concepts fins sont coarsened pour l'entraînement via `scripts/ml/concept_taxonomy.py`.
Exemple : `category.phenology` → `category.ecology`, `measurement.basal_area` → `measurement.biomass`.

Vérifier le mapping avant d'ajouter un concept fin — un mauvais merge peut
introduire un biais (cf. l'ancien `basal_area → diameter`).

## 3. Entraînement

Les 3 modèles s'entraînent séquentiellement. Chacun utilise `data/gold_set.json`.

### Header model (noms de colonnes)

```bash
uv run python scripts/ml/train_header_model.py
```

- TF-IDF char n-grams + LogisticRegression
- Capture les patterns cross-langue (diametre/diametro/diameter)
- Produit `models/header_model.joblib` (~2.6 MB)
- Métrique : macro-F1 sur les noms de colonnes

### Value model (valeurs des colonnes)

```bash
uv run python scripts/ml/train_value_model.py
```

- Features statistiques (distribution, patterns, ranges) + HistGradientBoosting
- Fonctionne sans nom de colonne (essentiel pour headers anonymes)
- Produit `models/value_model.joblib` (~40 MB)
- Métrique : macro-F1 sur les statistiques de valeurs

### Fusion model (combinaison)

```bash
uv run python -m scripts.ml.train_fusion
```

- Combine les probabilités header + values + features cross-rank
- LogisticRegression calibrée (isotonic regression)
- Produit `models/fusion_model.joblib` (~80 KB)
- Métrique : macro-F1 leak-free (GroupKFold par dataset)

### Entraînement complet

```bash
uv run python -m scripts.ml.build_gold_set && \
uv run python scripts/ml/train_header_model.py && \
uv run python scripts/ml/train_value_model.py && \
uv run python -m scripts.ml.train_fusion
```

## 4. Alias registry

Le registre d'alias est le **fast-path** : matching exact avant le ML.
Zéro ré-entraînement nécessaire, impact immédiat.

### Fichier

`src/niamoto/core/imports/ml/column_aliases.yaml`

### Format

```yaml
concept.subconcept:
  en: [alias1, alias2, alias3]
  fr: [alias_fr1, alias_fr2]
  dwc: [darwin_core_name]
```

### Quand ajouter un alias

- Le nom de colonne est **univoque** (toujours le même concept)
- Pas d'ambiguïté cross-concept (sinon le registry l'exclut automatiquement)
- Le ML rate systématiquement cette colonne

### Vérification

```bash
uv run python -c "
from niamoto.core.imports.ml.alias_registry import AliasRegistry
reg = AliasRegistry()
print(reg.match('my_column_name'))
"
```

### Tests

```bash
uv run pytest tests/core/imports/test_alias_registry.py -v
```

## 5. Évaluation

### Annotations

Ground truth centralisé dans `data/eval/annotations/` :

| Fichier | Colonnes | Données |
|---------|----------|---------|
| `niamoto-nc.yml` | 57 | test-instance/niamoto-nc/imports/ |
| `niamoto-gb.yml` | 27 | test-instance/niamoto-gb/imports/ |
| `guyadiv.yml` | 61 | data/silver/guyane/ |
| `gbif_darwin_core.yml` | ~50 | data/silver/gbif_targeted/ |
| `silver.yml` | ~136 | data/silver/ (9 fichiers) |

Format YAML : `colonne: role.concept` (ex: `dbh: measurement.diameter`).
Les annotations GBIF utilisent la clé `_gbif_core` appliquée à tout export GBIF.

### Suite complète

```bash
uv run python -m scripts.ml.eval.run_eval_suite
```

Évalue les 7 datasets (Tier 1 production, Tier 1b GBIF, Tier 2 silver),
produit un rapport agrégé avec confusion patterns et faiblesses par concept.
Résultats JSON horodatés dans `data/eval/results/`.

### Dataset unique

```bash
# Instance avec annotations centralisées
uv run python -m scripts.ml.eval.evaluate_instance \
    --annotations data/eval/annotations/niamoto-nc.yml \
    --data-dir test-instance/niamoto-nc/imports --compare

# GBIF avec CSV spécifique
uv run python -m scripts.ml.eval.evaluate_instance \
    --annotations data/eval/annotations/gbif_darwin_core.yml \
    --csv data/silver/gbif_targeted/new_caledonia/occurrences.csv

# Silver
uv run python -m scripts.ml.eval.evaluate_instance \
    --annotations data/eval/annotations/silver.yml \
    --data-dir data/silver
```

### Tier uniquement

```bash
uv run python -m scripts.ml.eval.run_eval_suite --tier 1     # Production
uv run python -m scripts.ml.eval.run_eval_suite --tier gbif   # GBIF
uv run python -m scripts.ml.eval.run_eval_suite --tier 2      # Silver
```

## 6. Cycle d'amélioration

### Diagnostic

Après une évaluation, identifier :

1. **Concepts faibles** (< 50% accuracy) — vérifier s'ils existent dans le gold set
2. **Colonnes systématiquement fausses** — candidats pour alias
3. **Top confusions** — concept A détecté comme B, pourquoi ?

### Décider de l'action

| Diagnostic | Action | Impact |
|------------|--------|--------|
| Concept absent du gold set | Ajouter labels dans build_gold_set.py | Ré-entraînement requis |
| Nom de colonne univoque raté | Ajouter alias dans column_aliases.yaml | Immédiat, pas de ré-entraînement |
| Concept présent mais confondu | Vérifier concept_taxonomy.py (merge incorrect ?) | Rebuild gold set + ré-entraînement |
| Annotation eval incorrecte | Corriger dans data/eval/annotations/ | Re-run eval seulement |
| Biais de surreprésentation | Rééquilibrer le gold set | Ré-entraînement |

### Vérification des annotations

Avant de conclure que le modèle a tort, vérifier les valeurs réelles :

```bash
uv run python3 -c "
import pandas as pd
df = pd.read_csv('path/to/file.csv', nrows=10)
print(df['column_name'].head())
"
```

Une annotation basée sur le nom de colonne peut être fausse si les valeurs
racontent une autre histoire (cf. `canopy` = comptage, pas mesure de canopée).

### Ne pas contaminer le benchmark

Les annotations eval (`data/eval/annotations/`) sont le **benchmark indépendant**.
Si on les injecte telles quelles dans le gold set, les scores montent mais
la généralisation n'est pas prouvée. Séparer :

- **Gold set** : données d'entraînement (build_gold_set.py)
- **Eval annotations** : benchmark indépendant (data/eval/annotations/)

Si les mêmes colonnes apparaissent dans les deux, c'est acceptable tant que
les labels sont cohérents — mais les scores eval doivent être interprétés
avec cette réserve.

## Référence rapide

```bash
# Pipeline complet (build → train → eval)
uv run python -m scripts.ml.build_gold_set
uv run python scripts/ml/train_header_model.py
uv run python scripts/ml/train_value_model.py
uv run python -m scripts.ml.train_fusion
uv run python -m scripts.ml.eval.run_eval_suite

# Alias seulement (pas de ré-entraînement)
# → éditer src/niamoto/core/imports/ml/column_aliases.yaml
uv run pytest tests/core/imports/test_alias_registry.py -v
uv run python -m scripts.ml.eval.run_eval_suite

# Évaluation seulement
uv run python -m scripts.ml.eval.run_eval_suite
```
