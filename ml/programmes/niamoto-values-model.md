# Programme Autoresearch : Values Model

## Objectif

Optimiser la branche `values` en boucle rapide. Cette branche est surtout critique
pour les colonnes anonymes, les concepts détectables par pattern et les cas où le
header est pauvre ou ambigu.

La métrique locale à maximiser est le **macro-F1** du modèle values. La validation
finale reste la qualité de la stack complète via `niamoto-score`.

## Périmètre autorisé

Tu peux modifier uniquement :

- `ml/scripts/train/train_value_model.py`
- `src/niamoto/core/imports/ml/value_features.py`

Tu ne dois pas modifier :

- `ml/scripts/eval/evaluate.py`
- `ml/scripts/eval/evaluation.py`
- `ml/scripts/train/train_fusion.py`
- `src/niamoto/core/imports/ml/classifier.py`
- `src/niamoto/core/imports/ml/alias_registry.py`

## Commandes d'évaluation

Boucle rapide :

```bash
uv run python -m ml.scripts.eval.evaluate --model values --metric macro-f1 --splits 5
```

Validation stack après une amélioration locale :

```bash
uv run python -m ml.scripts.eval.evaluate --model all --metric niamoto-score --splits 3
```

La sortie stdout est un nombre décimal unique. Les diagnostics détaillés sont écrits
sur stderr.

## Règle de décision

- Garde une variante si le score `values` monte de façon nette.
- Donne la priorité aux variantes qui améliorent les cas anonymes.
- Rejette une variante si elle détériore le `niamoto-score` global.
- Rejette une variante si elle augmente les faux positifs confiants.

## Axes d'exploration

### 1. Choix du classifier

Comparer :

- `HistGradientBoostingClassifier`
- `RandomForestClassifier`
- `ExtraTreesClassifier`
- `GradientBoostingClassifier`

Hyperparamètres à tester :

- `n_estimators` / `max_iter` : `50`, `100`, `200`, `500`
- `max_depth` : `4`, `6`, `8`, `12`, `None`
- `min_samples_leaf` : `1`, `3`, `5`, `10`
- `learning_rate` : `0.01`, `0.05`, `0.1`, `0.2`

### 2. Gestion du déséquilibre

- `class_weight="balanced"` si disponible
- `sample_weight` calculé pour les modèles qui n'acceptent pas `class_weight`

### 3. Feature engineering à forte valeur produit

Priorité aux features qui aident les concepts structurels et les colonnes anonymes :

- proportion dans `[-90, 90]` et `[-180, 180]`
- nombre moyen de décimales
- proportion de petites valeurs entières positives
- proportion dans `[0, 1]`
- longueur fixe des chaînes
- entropie caractère
- proportion de binomiaux textuels
- proportion de valeurs commençant par majuscule

### 4. Forme de distribution et spécialisation numérique

Inspiré de Pythagoras (EDBT 2024) qui montre que la spécialisation numérique
aide à distinguer les concepts proches (diameter vs height, biomass vs volume).

À tester dans `extract_value_features` :

- `bimodality_coefficient` : (skew² + 1) / kurtosis — distingue unimodal vs bimodal
- `pct_positive_log_skew` : skewness de log(values) quand toutes positives — proxy
  cheap pour la log-normalité (pas de Shapiro-Wilk, trop coûteux/fragile en inférence)
- `pct_round_values` : proportion de valeurs rondes (multiples de 5 ou 10)
- `pct_sequential` : proportion de paires consécutives dans les valeurs triées uniques
  (sorted unique values, pas dépendant de l'ordre des lignes)
- `range_ratio` : range / std — distingue uniforme vs concentré
- nombre de modes
- coefficient de Gini
- rapport `Q3 / Q1`
- ablations par groupe de features

Rappel : l'extraction est partagée train/runtime (`value_features.py`),
chaque feature ajoutée s'exécute à l'inférence sur les séries brutes.
Privilégier les features O(n) sans dépendance à l'ordre des lignes.

### 5. Sélection et simplification

- suppression de features qui nuisent
- `SelectKBest(mutual_info_classif, k=...)`
- lecture des importances pour supprimer le bruit

## Contraintes

- extraction rapide des features
- `FEATURE_NAMES` doit rester aligné avec le vecteur
- le modèle final doit exposer `predict_proba()`
- pas de nouvelle dépendance
- éviter les features fragiles ou sur-ajustées au synthétique

## Priorité produit

Quand deux variantes sont proches en `macro-f1`, préfère celle qui :

- améliore les colonnes anonymes
- améliore les coordonnées, dates et identifiants
- réduit les erreurs confiantes

## Format du commit

```text
autoresearch(values): macro-F1 0.XXXX -> 0.YYYY (+Z.Z pts)
```
