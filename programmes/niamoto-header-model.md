# Programme Autoresearch : Header Model

## Objectif

Maximiser le **macro-F1** du modèle header (TF-IDF char n-grams + LogisticRegression)
qui classifie les noms de colonnes en concepts sémantiques.

**Baseline actuel : 0.3658**

## Fichier à modifier

`scripts/ml/train_header_model.py` — uniquement la fonction `build_pipeline()` et
la fonction `prepare_data()` (preprocessing des noms).

**Ne pas modifier** : `evaluate_kfold()`, `load_gold_set()`, le format de sortie.

## Commande d'évaluation

```bash
uv run python scripts/ml/evaluate.py --model header --metric macro-f1
```

Sortie = un nombre décimal sur stdout (ex: `0.4523`). C'est la métrique à maximiser.

## Axes d'exploration

### 1. Hyperparamètres TF-IDF (priorité haute)

- `ngram_range` : essayer (2,4), (2,5), (3,6), (2,6), (4,6)
- `analyzer` : essayer "char" vs "char_wb" (le _wb ajoute des espaces virtuels aux bords)
- `max_features` : essayer 2000, 3000, 5000, 8000, 10000, None
- `sublinear_tf` : True vs False
- `min_df` : 1, 2, 3
- `max_df` : 0.9, 0.95, 1.0

### 2. Classifier (priorité haute)

- `C` (régularisation) : essayer 0.01, 0.1, 0.5, 1.0, 5.0, 10.0, 50.0
- `solver` : "lbfgs", "saga"
- `penalty` : "l2" (défaut), essayer "l1" avec solver="saga"
- `class_weight` : None, "balanced"

### 3. Preprocessing des noms (priorité moyenne)

Dans `prepare_data()` ou `_normalize()` :
- Ajouter un prefix du type de données si disponible (ex: "num_dbh", "str_species")
- Essayer de splitter les noms composés : "stem_diameter" → "stem diameter"
  pour que le TF-IDF capture mieux les mots
- Essayer de doubler le nom (répétition) pour renforcer le signal court
- Tester l'ajout de suffixes dérivés des alias connus

### 4. Feature engineering sur le nom (priorité moyenne)

- Ajouter des features binaires (contient "id", contient un chiffre, longueur du nom)
  et les combiner avec le TF-IDF via `FeatureUnion`
- Ajouter le score d'alias registry comme feature supplémentaire

### 5. Classifier alternatif (priorité basse)

- Remplacer LogReg par `SGDClassifier(loss='modified_huber')` pour des probas calibrées
- Essayer `LinearSVC` + `CalibratedClassifierCV`
- Essayer `RidgeClassifier` (plus rapide, pas de probas natives)

## Contraintes

- Le pipeline doit rester un `sklearn.pipeline.Pipeline` sérialisable avec joblib
- Temps d'entraînement < 10 secondes (on a ~400 samples, ça doit rester rapide)
- Pas de dépendances nouvelles (utiliser scikit-learn, rapidfuzz, unidecode uniquement)
- Le modèle final doit exposer `predict_proba()` (nécessaire pour la fusion)

## Stratégie de recherche

1. Commencer par le grid sur `C` et `ngram_range` (fort impact, rapide)
2. Tester `class_weight="balanced"` (les classes sont très déséquilibrées)
3. Explorer le preprocessing (split des noms composés)
4. Itérer sur les combinaisons gagnantes
5. Terminer par les alternatives de classifier

## Format du commit

Si une itération améliore le score :
```
autoresearch(header): macro-F1 0.XXXX → 0.YYYY (+Z.Z pts)
```
