# Programme Autoresearch : Values Model

## Objectif

Maximiser le **macro-F1** du modèle values (features statistiques + classifier)
qui classifie les colonnes en concepts sémantiques à partir de leurs valeurs.

**Baseline actuel : 0.2877**

## Fichier à modifier

`scripts/ml/train_value_model.py` — les fonctions `extract_value_features()`,
`build_model()`, et éventuellement `FEATURE_NAMES`.

**Ne pas modifier** : `load_and_prepare()`, `evaluate_kfold()`, le format de sortie.

## Commande d'évaluation

```bash
uv run python scripts/ml/evaluate.py --model values --metric macro-f1
```

Sortie = un nombre décimal sur stdout. C'est la métrique à maximiser.

## Axes d'exploration

### 1. Choix du classifier (priorité haute)

Comparer :
- `HistGradientBoostingClassifier` (actuel) — bon pour > 1000 samples
- `RandomForestClassifier` — potentiellement meilleur avec ~400 samples
- `ExtraTreesClassifier` — plus de variance, potentiellement meilleur en petit dataset
- `GradientBoostingClassifier` — version classique, parfois meilleure en petit dataset

Pour chaque, grid sur les hyperparamètres :
- `n_estimators` / `max_iter` : 50, 100, 200, 500
- `max_depth` : 4, 6, 8, 12, None
- `min_samples_leaf` : 1, 3, 5, 10
- `learning_rate` (HGBT/GBT) : 0.01, 0.05, 0.1, 0.2

### 2. class_weight (priorité haute)

- Essayer `class_weight="balanced"` pour gérer le déséquilibre des classes
- Pour HGBT : `class_weight` n'est pas supporté nativement, utiliser
  `sample_weight` via `compute_sample_weight("balanced", y)`

### 3. Feature engineering (priorité moyenne)

Ajouter des features dans `extract_value_features()` :

**Features de distribution** :
- Modes (nombre de pics dans l'histogramme)
- Coefficient de Gini
- Rapport Q3/Q1 (dispersion relative)
- Test de normalité (Shapiro p-value, si < 50 samples)

**Features de pattern** :
- Proportion de valeurs dans [0, 1] (indicateur de ratio/proportion)
- Proportion de valeurs entières positives petites (< 100, indicateur de count)
- Proportion dans [-90, 90] (indicateur latitude)
- Proportion dans [-180, 180] (indicateur longitude)
- Nombre de décimales moyen (2 dec = mesure, 6 dec = coordonnée)

**Features textuelles améliorées** :
- Proportion de valeurs commençant par une majuscule
- Proportion de valeurs avec exactement 2 mots (binomial)
- Proportion de chaînes de longueur fixe (indicateur de code/ID)
- Entropie par caractère (distingue texte libre vs catégoriel)

### 4. Feature selection (priorité moyenne)

- Tester la suppression de groupes de features (ablation par groupe)
  pour identifier les features qui nuisent
- `SelectKBest(mutual_info_classif, k=...)` avec k = 15, 20, 25
- Feature importance du RF/HGBT pour identifier les features inutiles

### 5. Normalisation (priorité basse)

- Tester `StandardScaler` sur les features numériques
- Tester `QuantileTransformer` pour gérer les distributions skewed
- Le HGBT ne devrait pas en avoir besoin (tree-based), mais RF pourrait bénéficier

## Contraintes

- Features extraites en < 50ms par colonne (on a ~50 valeurs par sample)
- Le modèle doit exposer `predict_proba()` (nécessaire pour la fusion)
- Pas de dépendances nouvelles (scikit-learn + scipy uniquement)
- FEATURE_NAMES doit rester synchronisé avec la taille du vecteur de features

## Stratégie de recherche

1. D'abord comparer RF vs HGBT vs ExtraTrees avec params par défaut
2. Grid sur le meilleur classifier (max_depth, n_estimators, class_weight)
3. Ajouter les features de pattern (coordonnées, décimales, etc.)
4. Feature selection / ablation
5. Combiner les meilleurs réglages

## Format du commit

```
autoresearch(values): macro-F1 0.XXXX → 0.YYYY (+Z.Z pts)
```
