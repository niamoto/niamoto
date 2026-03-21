# Anonymous Holdout Rework — Brainstorm

**Date** : 2026-03-21
**Statut** : Validé

## Ce qu'on construit

Remplacement du holdout anonymous actuel (86 entrées 100% synthétiques, 76% measurement.height/diameter, score permanent de 100%) par un holdout diversifié basé sur de vraies colonnes du gold set, anonymisées avec des noms génériques aléatoires.

**Objectif** : Rendre le holdout anonymous informatif — tester si le values branch (et le pipeline fusion) détecte correctement les types sémantiques **sans aucune information de nom de colonne**.

## Pourquoi cette approche

### Problème actuel

- 86 entrées anonymes, toutes synthétiques (distributions numpy)
- 76% sont `measurement.height` (35) + `measurement.diameter` (30)
- Seulement 10 concepts sur ~45 coarse concepts couverts
- Le values branch n'a qu'à prédire "float continu positif" pour scorer 100%
- Le poids de 10% dans ProductScore gonfle le score sans tester rien d'utile

### Solution retenue

**Anonymiser des colonnes réelles du gold set** plutôt que générer des synthétiques.

Avantages par rapport au synthétique :
- Vrais patterns de données (pas des distributions numpy simplistes)
- Toujours à jour avec le gold set (régénéré automatiquement)
- Couverture diversifiée de tous les concepts coarse (~45 familles)
- Teste la reconnaissance de patterns, pas la mémorisation

### Approches écartées

- **Anonymisation on-the-fly dans evaluate.py** : Gold set propre mais évaluation non-déterministe et non-inspectable. Rejetée.
- **Fichier holdout séparé** : Séparation claire mais deux artefacts à maintenir en sync. Sur-ingénierie pour un gain marginal. Rejetée.

## Décisions clés

### 1. Deux métriques d'évaluation
- **anonymous_fusion** (dans ProductScore, poids 10%) : Pipeline complet header → values → fusion
- **anonymous_values_only** (informatif seulement) : Values branch seul, pour diagnostiquer si le fusion aide ou dégrade

### 2. Échantillonnage stratifié automatique
- Grouper les colonnes réelles par `concept_coarse`
- Échantillonner proportionnellement avec un plancher de 2 par concept
- Cible : ~100 entrées au total
- Seed fixe (42) pour reproductibilité

### 3. Remplacement complet
- Suppression des 86 entrées synthétiques anonymes existantes
- Suppression du mécanisme `HEADER_VARIANTS["anonymous"]` dans `generate_synthetic_columns()`
- Les nouvelles entrées ont `quality: "gold_anonymous"` (distingue de `"gold"` et `"synthetic"`)

### 4. Noms aléatoires sans corrélation
- Pool de ~300 noms génériques : `col_1`..`col_99`, `X1`..`X99`, `var_a`..`var_z`, `V1`..`V99`, `field_1`..`field_99`
- Chaque entrée anonyme reçoit un nom tiré au hasard
- Aucune corrélation nom → concept (contrairement à l'ancien système où `X1` = diameter, `X2` = height)

### 5. Pas de changement de poids ProductScore
- Le poids de 10% reste inchangé
- Le score va naturellement baisser (attendu et souhaité)
- Le ProductScore devient plus informatif

## Fichiers impactés

| Fichier | Action |
|---------|--------|
| `scripts/ml/build_gold_set.py` | Ajouter `_build_anonymous_holdout()`, supprimer `HEADER_VARIANTS["anonymous"]` et la logique `if lang == "anonymous"` |
| `scripts/ml/evaluate.py` | Ajouter métrique values-only informative (le filtrage `is_anonymous` existant reste identique) |
| `scripts/ml/concept_taxonomy.py` | Aucun changement |
| `data/gold_set.json` | Régénéré automatiquement |

## Fonction `_build_anonymous_holdout(gold_set)`

1. Filtrer les entrées non-anonymes
2. Grouper par `concept_coarse`
3. Échantillonner `min(N, len(group))` par groupe (N calculé pour ~100 total, plancher 2)
4. Pour chaque entrée sélectionnée, créer une copie :
   - `column_name` → nom aléatoire du pool
   - `is_anonymous` → `True`
   - `quality` → `"gold_anonymous"`
   - `language` → `"en"`
   - `source_dataset`, `values_sample`, `values_stats`, `concept`, `role`, `concept_coarse`, `role_coarse` → conservés
5. Supprimer les anciennes entrées anonymes
6. Ajouter les nouvelles

## Cas difficiles à couvrir

Le doc original identifie des cas intéressants que l'échantillonnage stratifié couvrira naturellement :

- `elevation` (int 0-4000) vs `statistic.count` (int 0-1000) vs `year` (int 1980-2024)
- `measurement.diameter` (float 5-100) vs `measurement.trait` (float 0-1)
- `location.latitude` (float -90/90) vs `measurement.height` (float 0-50)

Ces cas seront présents si le gold set contient ces concepts, ce qui est le cas.

## Vérification

```bash
# 1. Rebuild le gold set
uv run python -m scripts.ml.build_gold_set

# 2. Vérifier la distribution anonyme
uv run python3 -c "
import json
from collections import Counter
with open('data/gold_set.json') as f:
    gold = json.load(f)
anon = [e for e in gold if e.get('is_anonymous')]
print(f'Anonymous: {len(anon)}')
for c, n in Counter(e['concept_coarse'] for e in anon).most_common():
    print(f'  {c}: {n}')
"

# 3. Recalculer le ProductScore
uv run python -m scripts.ml.evaluate --model all --metric product-score
```

## Scores de référence (avant)

- ProductScore : 81.82
- GlobalScore : 80.79
- Anonymous holdout : 100.0 (← devrait significativement baisser)
- Instance eval : 77.5% concept (418 cols, 7 datasets)

## Questions ouvertes

Aucune — le design est validé.
