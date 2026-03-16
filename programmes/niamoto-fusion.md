# Programme Autoresearch : Fusion Model

## Objectif

Maximiser le **macro-F1** du modèle de fusion qui combine les sorties
des branches header et values en une prédiction unique calibrée.

**Baseline actuel : 0.2034** (KFold sur fusion seule)
**Combined score : 0.3898** (weighted all)

## Fichier à modifier

`scripts/ml/train_fusion.py` — les fonctions `extract_fusion_features()`
et `build_fusion_model()`.

**Ne pas modifier** : `load_branch_models()`, le format de sortie.

## Commande d'évaluation

```bash
uv run python scripts/ml/evaluate.py --model fusion --metric macro-f1
```

## Prérequis

Les modèles header et values doivent être entraînés avant :
```bash
uv run python scripts/ml/train_header_model.py
uv run python scripts/ml/train_value_model.py
```

## Axes d'exploration

### 1. Features de fusion enrichies (priorité haute)

Dans `extract_fusion_features()`, ajouter :

**Méta-features sur les probas** :
- Entropie des probas header (mesure l'incertitude du header model)
- Entropie des probas values (mesure l'incertitude du values model)
- Max proba header (confiance du header model)
- Max proba values (confiance du values model)
- Accord header/values (1 si même top-1 prediction, 0 sinon)
- Ratio max/2nd proba (marge de confiance)

**Features croisées** :
- Produit des probas header × values pour le top-1 de chaque branche
- Différence de confiance entre les deux branches

### 2. Classifier de fusion (priorité haute)

Essayer :
- `LogisticRegression` avec différents `C` : 0.01, 0.1, 1.0, 10.0
- `class_weight="balanced"`
- `RandomForestClassifier(n_estimators=100)` — pourrait mieux gérer
  les interactions non-linéaires entre les probas
- `HistGradientBoostingClassifier` — si le nombre de features le justifie

### 3. Règles haute-précision (priorité haute)

Ajouter des overrides déterministes AVANT le classifier pour les cas évidents :
- Si header match exact un alias avec score 1.0 ET values confirme → confiance 0.95+
- Si pattern regex (coordonnées, dates ISO, WKT) → bypass le classifier
- Si `is_anonymous=True` ET max_proba_values > 0.8 → utiliser values seul

Implémenter dans une fonction `_apply_high_precision_rules()` qui retourne
soit un résultat final, soit None (continue vers le classifier).

### 4. Calibration (priorité moyenne)

Une fois que le gold set sera plus grand (> 500 avec ≥ 3 par classe) :
- Réactiver `CalibratedClassifierCV(cv=2, method="isotonic")`
- Tester `method="sigmoid"` (Platt scaling, plus robuste en petit dataset)
- Mesurer l'ECE avant/après calibration

### 5. Seuils d'abstention (priorité moyenne)

- Tester différents seuils de confiance pour l'abstention : 0.30, 0.40, 0.50, 0.60
- Quand confiance < seuil → retourner `role` générique au lieu de `concept` précis
- Mesurer Coverage@0.70 en plus du macro-F1

### 6. Pondération des branches (priorité basse)

Au lieu de concaténer header_proba et values_proba :
- Essayer une pondération apprise : `alpha * header + (1-alpha) * values`
- Essayer d'ignorer header quand `is_anonymous=True`
- Essayer de donner plus de poids à values quand l'entropie header est haute

## Contraintes

- Le fusion model doit rester rapide (< 100ms inférence par colonne)
- Doit fonctionner même si un seul branch model est disponible
- Les règles haute-précision ne doivent JAMAIS produire de faux positifs
  (précision >= 0.99 sur le gold set)
- Pas de dépendances nouvelles

## Stratégie de recherche

1. Ajouter les méta-features (entropie, confiance, accord) — impact immédiat
2. Tester `class_weight="balanced"` sur LogReg
3. Implémenter les règles haute-précision pour les cas évidents
4. Grid sur C de la LogReg
5. Tester RF comme classifier de fusion
6. Optimiser les seuils d'abstention

## Format du commit

```
autoresearch(fusion): macro-F1 0.XXXX → 0.YYYY (+Z.Z pts)
```
