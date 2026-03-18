# Programme Autoresearch : Header Model

## Objectif

Optimiser la branche `header` en boucle rapide, sans perdre de vue la qualité de la
stack complète.

La métrique locale à maximiser est le **macro-F1** du modèle header. Cette métrique
sert au tri rapide des variantes. La décision finale reste produit : une amélioration
header ne vaut que si elle ne dégrade pas le score global de détection.

## Périmètre autorisé

Tu peux modifier uniquement :

- `scripts/ml/train_header_model.py`
- `src/niamoto/core/imports/ml/header_features.py`

Tu ne dois pas modifier :

- `scripts/ml/evaluate.py`
- `scripts/ml/evaluation.py`
- `scripts/ml/train_fusion.py`
- `src/niamoto/core/imports/ml/alias_registry.py`
- `src/niamoto/core/imports/profiler.py`

## Commandes d'évaluation

Boucle rapide :

```bash
uv run python -m scripts.ml.evaluate --model header --metric macro-f1 --splits 5
```

Validation stack après une amélioration locale :

```bash
uv run python -m scripts.ml.evaluate --model all --metric niamoto-score --splits 3
```

La sortie stdout est un nombre décimal unique. Les détails de diagnostic partent sur
stderr.

## Règle de décision

- Garde une variante si le score `header` monte de façon nette.
- Rejette-la si le `niamoto-score` global baisse.
- Rejette-la si elle dégrade visiblement les cas anonymes ou augmente les erreurs
  confiantes de la stack.

En pratique :

- recherche locale : `macro-f1 header`
- arbitre final : `niamoto-score` sur la stack complète

## Axes d'exploration

### 1. Hyperparamètres TF-IDF

- `ngram_range` : essayer `(2,4)`, `(2,5)`, `(3,6)`, `(2,6)`, `(4,6)`
- `analyzer` : comparer `"char"` et `"char_wb"`
- `max_features` : essayer `2000`, `3000`, `5000`, `8000`, `10000`, `None`
- `sublinear_tf` : `True` / `False`
- `min_df` : `1`, `2`, `3`
- `max_df` : `0.9`, `0.95`, `1.0`

### 2. Logistic Regression

- `C` : essayer `0.01`, `0.1`, `0.5`, `1.0`, `5.0`, `10.0`, `50.0`
- `solver` : `"lbfgs"`, `"saga"`
- `penalty` : `"l2"` par défaut, tester `"l1"` avec `"saga"`
- `class_weight` : `None`, `"balanced"`

### 3. Preprocessing partagé des headers

Le preprocessing runtime/train/fusion doit rester strictement cohérent.

À tester dans `header_features.py` :

- enrichissement par type de donnée
- normalisation des booléens et dates
- hints de longueur cohérents sur tous les dtypes
- split des noms composés : `stem_diameter -> stem diameter`
- duplication légère du signal pour les noms très courts

### 4. Features légères autour du nom

- présence de chiffres
- présence de tokens indicateurs (`id`, `lat`, `lon`, `date`, `year`)
- longueur normalisée du header
- préfixes/suffixes utiles si cela reste sérialisable et simple

### 5. Alternatives prudentes

- `SGDClassifier(loss="modified_huber")`
- `LinearSVC` + calibration
- `RidgeClassifier`

À n'essayer qu'après avoir épuisé les variantes simples de TF-IDF + LogReg.

## Contraintes

- le pipeline doit rester sérialisable avec joblib
- le modèle doit exposer `predict_proba()`
- pas de nouvelle dépendance
- temps d'entraînement court
- pas de divergence entre preprocessing d'entraînement et d'inférence

## Format du commit

Si une itération est retenue :

```text
autoresearch(header): macro-F1 0.XXXX -> 0.YYYY (+Z.Z pts)
```
