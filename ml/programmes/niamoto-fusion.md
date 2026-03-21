# Programme Autoresearch : Detection Stack

## Objectif

Optimiser la stack complète de détection :

- alias exacts
- branche `header`
- branche `values`
- fusion
- calibration implicite par confiance
- comportement dataset-level orienté produit

La métrique finale à maximiser est le **ProductScore**. C'est la vérité de
décision orientée produit pour accepter ou rejeter une variante de la stack
complète.

Le **NiamotoOfflineScore** reste une métrique globale utile, mais il ne doit
plus piloter seul les décisions d'itération. Le simple `macro-f1` n'est plus
suffisant comme arbitre final.

## Périmètre autorisé

Tu peux modifier uniquement :

- `scripts/ml/train_fusion.py`
- `scripts/ml/evaluate.py`
- `scripts/ml/evaluation.py`
- `src/niamoto/core/imports/ml/classifier.py`
- `src/niamoto/core/imports/ml/alias_registry.py`

Tu peux aussi retoucher ponctuellement :

- `src/niamoto/core/imports/ml/header_features.py`

Tu ne dois pas modifier :

- le gold set
- les tests sauf si une hypothèse d'évaluation change explicitement
- `ml-detection-dashboard.html`
- le reste du produit hors pipeline ML

## Commandes d'évaluation

Préparer le cache surrogate une fois :

```bash
uv run python -m ml.scripts.research.build_fusion_surrogate_cache --gold-set ml/data/gold_set.json --splits 3
```

Boucle rapide fusion-only :

```bash
uv run python -m ml.scripts.eval.evaluate --model fusion --metric surrogate-fast --splits 3
```

Validation surrogate plus stricte :

```bash
uv run python -m ml.scripts.eval.evaluate --model fusion --metric surrogate-mid --splits 3
```

Validation stack courte :

```bash
uv run python -m ml.scripts.eval.evaluate --model all --metric product-score-fast-fast --splits 2
```

Diagnostic complémentaire si nécessaire :

```bash
uv run python -m ml.scripts.eval.evaluate --model fusion --metric macro-f1 --splits 5
```

Validation globale secondaire :

```bash
uv run python -m ml.scripts.eval.evaluate --model all --metric product-score --splits 3
```

Validation globale finale :

```bash
uv run python -m ml.scripts.eval.evaluate --model all --metric niamoto-score --splits 3
```

La sortie stdout est un score unique. Les sous-métriques et holdouts sont affichés
sur stderr.

## Ce que mesure le ProductScore

Le score de décision combine les buckets les plus proches de la cible produit :

- `tropical_field` : `30%`
- `research_traits` : `15%`
- `gbif_core_standard` : `20%`
- `gbif_extended` : `10%`
- `en_field` : `15%`
- `anonymous` : `10%`

La surrogate loop fusion-only utilise un cache de probabilités `header/value`
par fold. L'agent ne réentraîne plus que le modèle de fusion à chaque itération.

`surrogate-fast` optimise en priorité :

- `tropical_field`
- `research_traits`
- `en_field`
- `gbif_core_standard`
- `anonymous`

`surrogate-mid` rajoute une vue plus large avec :

- `gbif_extended`
- le même cache par fold
- un coût encore très inférieur à la stack complète

La variante `product-score-mid` garde les mêmes poids, mais réduit le protocole
à :

- OOF primaire
- `tropical_field`
- `research_traits`
- `en_field`
- `gbif_core_standard`
- `gbif_extended`
- `anonymous`

Elle exclut les holdouts langue complets, `forest_inventory` et le diagnostic
synthetic pour rester praticable dans une boucle autoresearch.

`product-score-fast` reste un alias de compatibilité pour cette même variante.

La variante `product-score-fast-fast` devient maintenant la première validation
stack :

- pas d'OOF primaire complet
- `tropical_field` : `35%`
- `research_traits` : `20%`
- `en_field` : `20%`
- `gbif_core_standard` : `15%`
- `anonymous` : `10%`

Elle ne conserve que :

- `holdout_family[tropical_field]`
- `holdout_family[research_traits]`
- `holdout_subset[en_field]`
- `holdout_subset[gbif_core_standard]`
- `holdout_anonymous`

Elle exclut `gbif_extended`, les langues complètes, `forest_inventory`,
`synthetic` et l'OOF primaire global pour retomber sur une boucle réellement
plus courte.

Le `NiamotoOfflineScore` continue de mesurer globalement :

- `role_macro_f1`
- `critical_concept_macro_f1`
- `anonymous_role_macro_f1`
- `pair_consistency`
- `confidence_quality`
- `dataset_outcome`

Les diagnostics stderr affichent aussi les holdouts :

- langues : `fr`, `es`, `de`
- familles : `dwc_gbif`, `forest_inventory`, `tropical_field`, `research_traits`
- subsets : `en_standard`, `en_field`, `coded_headers`, `gbif_core_standard`,
  `gbif_extended`
- colonnes anonymes
- synthétique en diagnostic séparé

## Règles d'acceptation

Accepte une variante seulement si :

- le `surrogate-fast` monte
- le `surrogate-mid` confirme
- le `product-score-fast-fast` reste cohérent sur le candidat retenu
- le `product-score` tient ensuite
- le `niamoto-score` global ne décroche pas fortement
- `tropical_field` et `research_traits` ne baissent pas sensiblement
- `gbif_core_standard` reste stable ou monte
- `en_field` ne baisse pas de façon visible
- `anonymous` ne s'effondre pas
- aucun garde-fou critique ne décroche brutalement

Rejette par défaut une variante qui :

- gagne localement sur un seul sous-score mais baisse sur la métrique globale
- augmente les erreurs confiantes
- améliore le synthétique tout en dégradant le réel
- contourne le classifieur avec des règles trop agressives

Traite comme garde-fous secondaires, sans en faire la boussole principale :

- `forest_inventory`
- `forest_inventory/ifn_fr`
- `forest_inventory/fia_en`
- `coded_headers`

## Axes d'exploration prioritaires

### 1. Features de fusion

Dans `extract_fusion_features()` :

- entropie header / values
- max proba header / values
- marge top1 vs top2
- accord des deux branches
- produit ou interaction des confiances
- signaux spécifiques aux colonnes anonymes

### 2. Comportement par contexte

- donner plus de poids à `values` pour les colonnes anonymes
- réduire l'impact de `header` quand il est incertain
- mieux exploiter les cas où une branche est absente ou peu fiable

### 3. Alias et règles haute précision

- éviter toute collision donnant une confiance arbitraire à `1.0`
- ne bypasser le modèle que sur des cas réellement sans ambiguïté
- préférer désactiver un alias ambigu plutôt que forcer une prédiction

### 4. Confiance et abstention

- pénaliser les faux positifs à haute confiance
- tester les seuils qui aident le produit sans masquer les erreurs
- privilégier la bonne prédiction du rôle à la sur-précision du concept

### 5. Cohérence dataset-level

- paires lat/lon
- famille / genre / espèce
- date / année
- plot / record identifiers

Les changements qui améliorent la cohérence au niveau dataset sont prioritaires.

## Contraintes

- pas de fuite de données dans l'évaluation
- cohérence stricte train/runtime sur les features
- pas de nouvelle dépendance
- inférence rapide
- règles déterministes conservatrices

## Stratégie de recherche

1. améliorer la fusion et la confiance
2. corriger les faux positifs dangereux
3. améliorer la cohérence dataset-level
4. valider sur `surrogate-fast`, puis `surrogate-mid`
5. confirmer sur `product-score-mid`, puis `product-score`, puis `niamoto-score`

## Format du commit

```text
autoresearch(stack): product-score 0.XXXX -> 0.YYYY (+Z.Z pts)
```
