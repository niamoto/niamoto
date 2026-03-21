# Programme Autoresearch : Values Model

## Objectif

Optimiser la branche `values` en boucle rapide. Cette branche est surtout critique
pour les colonnes anonymes, les concepts détectables par pattern et les cas où le
header est pauvre ou ambigu.

La métrique locale à maximiser est le **macro-F1** du modèle values. La validation
finale reste la qualité de la stack complète via `niamoto-score`.

## Périmètre autorisé

Tu peux modifier uniquement :

- `scripts/ml/train_value_model.py`

Tu ne dois pas modifier :

- `scripts/ml/evaluate.py`
- `scripts/ml/evaluation.py`
- `scripts/ml/train_fusion.py`
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

### 4. Distribution et robustesse

- nombre de modes
- coefficient de Gini
- rapport `Q3 / Q1`
- normalité simple si cela reste robuste
- ablations par groupe de features

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
