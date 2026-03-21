---
title: "feat: Rework anonymous holdout with diversified real columns"
type: feat
date: 2026-03-21
brainstorm: docs/brainstorms/2026-03-21-anonymous-holdout-rework-brainstorm.md
---

# feat: Rework anonymous holdout with diversified real columns

## Overview

Remplacer les 86 entrées anonymes synthétiques du gold set (76% measurement.height/diameter, score permanent 100%) par ~100 entrées diversifiées issues de vraies colonnes du gold set, anonymisées avec des noms génériques aléatoires.

## Problem Statement

Le holdout anonymous ne teste rien d'utile :
- 86 entrées 100% synthétiques (distributions numpy)
- 76% concentrées sur 2 concepts (height + diameter)
- 10 concepts couverts sur ~45
- Score permanent de 100% — le values branch n'a qu'à prédire "float continu"
- Poids de 10% dans ProductScore → gonfle le score sans information

## Proposed Solution

1. Nouvelle fonction `_build_anonymous_holdout()` dans `build_gold_set.py`
2. Suppression du mécanisme `HEADER_VARIANTS["anonymous"]`
3. Ajout d'une métrique values-only informative dans `evaluate.py`

## Acceptance Criteria

- [x] Les anciennes entrées anonymes synthétiques sont supprimées du gold set
- [x] ~100 nouvelles entrées anonymes issues de vraies colonnes, stratifiées par concept_coarse
- [x] Chaque concept_coarse a au minimum 2 représentants anonymes
- [x] Les noms de colonnes sont aléatoires (pool de ~300 noms), sans corrélation concept
- [x] Le gold set est reproductible (seed fixe 42)
- [x] `quality` des nouvelles entrées = `"gold_anonymous"`
- [x] Le bucket `anonymous` dans ProductScore utilise le pipeline fusion (poids 10% inchangé)
- [x] Une métrique `anonymous_values_only` informative est affichée (pas dans ProductScore)
- [x] Le score anonymous baisse significativement par rapport à 100% (attendu) → 91.02
- [x] `uvx ruff check` et `uvx ruff format` passent sans erreur

## Implementation Plan

### Phase 1 : `_build_anonymous_holdout()` dans `build_gold_set.py`

#### 1.1 Supprimer le mécanisme anonymous existant

**Fichier** : `scripts/ml/build_gold_set.py`

- Supprimer la clé `"anonymous"` du dict `HEADER_VARIANTS` (lignes 1795-1806)
- Supprimer les 6 blocs `if lang == "anonymous"` dans `generate_synthetic_columns()` :
  - Bloc biomes (ligne ~1906-1907)
  - Bloc taxonomy (ligne ~1935)
  - Bloc count (ligne ~1956)
  - Bloc coords (ligne ~1981)
  - Bloc dates (ligne ~2002)
  - Bloc ids (ligne ~2023)
- Nettoyer la logique `lang if lang != "anonymous" else "en"` associée

#### 1.2 Créer la fonction `_build_anonymous_holdout()`

**Emplacement** : après le step coarsen dans `build_gold_set()` (après ligne ~2130), car `concept_coarse` doit être disponible pour l'échantillonnage stratifié.

```python
# scripts/ml/build_gold_set.py

# Pool de noms anonymes (~300 noms uniques)
_ANONYMOUS_NAME_POOL = (
    [f"col_{i}" for i in range(1, 100)]
    + [f"X{i}" for i in range(1, 100)]
    + [f"V{i}" for i in range(1, 100)]
    + [f"var_{chr(c)}" for c in range(ord("a"), ord("z") + 1)]
    + [f"field_{i}" for i in range(1, 26)]
)


def _build_anonymous_holdout(
    records: list[dict],
    target_total: int = 100,
    min_per_concept: int = 2,
    seed: int = 42,
) -> list[dict]:
    """Crée un holdout anonyme diversifié à partir de vraies colonnes.

    Échantillonne des colonnes réelles stratifiées par concept_coarse,
    les duplique avec des noms génériques aléatoires.
    """
```

**Algorithme** :
1. Filtrer `records` où `is_anonymous == False`
2. Grouper par `concept_coarse`
3. Calculer N par groupe : `max(min_per_concept, round(target_total * len(group) / total_non_anon))`
4. Ajuster pour que la somme ≈ `target_total`
5. Pour chaque groupe, `rng.choice(group, size=n, replace=False)`
6. Pour chaque entrée sélectionnée, `copy.deepcopy()` + :
   - `column_name` → `rng.choice(_ANONYMOUS_NAME_POOL)` (sans remise au sein du holdout)
   - `is_anonymous` → `True`
   - `quality` → `"gold_anonymous"`
   - `language` → `"en"`
   - Conserver : `values_sample`, `values_stats`, `concept`, `role`, `concept_coarse`, `role_coarse`, `source_dataset`

#### 1.3 Intégrer dans `build_gold_set()`

```python
def build_gold_set() -> list[dict]:
    all_records = []

    # 1. Extraction réelle
    for source in SOURCES:
        records = extract_from_source(source)
        all_records.extend(records)

    # 2. Synthétique (sans anonymous)
    synthetic = generate_synthetic_columns()
    all_records.extend(synthetic)

    # 3. Coarsen
    from scripts.ml.concept_taxonomy import coarsen
    for r in all_records:
        r["concept_coarse"] = coarsen(r["concept"])
        r["role_coarse"] = r["concept_coarse"].split(".")[0]

    # 4. Anonymous holdout diversifié (NOUVEAU)
    anon_holdout = _build_anonymous_holdout(all_records)
    all_records.extend(anon_holdout)

    # 5. Supprimer les anciens anonymes (sécurité — ne devrait plus y en avoir)
    all_records = [r for r in all_records if not (
        r.get("is_anonymous") and r.get("quality") == "synthetic"
    )]

    return all_records
```

### Phase 2 : Métrique values-only dans `evaluate.py`

#### 2.1 Ajouter l'évaluation values-only

**Fichier** : `scripts/ml/evaluate.py`

Dans le bloc anonymous (lignes 705-717), après l'évaluation fusion existante, ajouter une évaluation values-only :

```python
# Bloc existant (inchangé)
anonymous_records = [r for r in records if r.get("is_anonymous")]
if anonymous_records:
    train_records = [r for r in records if not r.get("is_anonymous")]
    score, _preds, _confs = _evaluate_holdout_score(
        anonymous_records, train_records, all_concepts,
    )
    product_buckets["anonymous"] = float(score.final_score)

    # NOUVEAU : évaluation values-only (informatif)
    values_only_score = _evaluate_values_only_holdout(
        anonymous_records, train_records, all_concepts,
    )
    # Affiché dans les résultats mais PAS dans product_buckets
```

#### 2.2 Implémenter `_evaluate_values_only_holdout()`

Réutiliser `_train_all_models()` pour entraîner le values model, puis prédire sur les anonymous records en utilisant **uniquement les features values** (sans header features ni fusion).

```python
def _evaluate_values_only_holdout(
    test_records: list[dict],
    train_records: list[dict],
    all_concepts: list[str],
) -> float:
    """Évalue le values branch seul sur le holdout anonymous."""
```

**Inputs/outputs** : mêmes entrées que `_evaluate_holdout_score()`, retourne un float (accuracy ou macro-F1).

**Implémentation** :
1. Entraîner le values model sur `train_records` (réutiliser la logique existante de `_train_all_models()`)
2. Extraire les features values des `test_records` (via `extract_values_features()`)
3. Prédire avec le values model seul
4. Comparer aux ground truth `concept_coarse`
5. Calculer et retourner le score

### Phase 3 : Vérification et rebuild

#### 3.1 Rebuild gold set

```bash
uv run python -m scripts.ml.build_gold_set
```

#### 3.2 Vérifier la distribution

```bash
uv run python3 -c "
import json
from collections import Counter
with open('data/gold_set.json') as f:
    gold = json.load(f)
anon = [e for e in gold if e.get('is_anonymous')]
non_anon = [e for e in gold if not e.get('is_anonymous')]
print(f'Total: {len(gold)}, Non-anonymous: {len(non_anon)}, Anonymous: {len(anon)}')
print(f'Quality values: {Counter(e[\"quality\"] for e in anon)}')
print()
for c, n in Counter(e['concept_coarse'] for e in anon).most_common():
    print(f'  {c}: {n}')
"
```

**Résultat attendu** : ~100 entrées anonymes, couverture de ~45 concepts coarse, quality `"gold_anonymous"`, distribution relativement uniforme.

#### 3.3 Recalculer le ProductScore

```bash
uv run python -m scripts.ml.evaluate --model all --metric product-score
```

**Résultat attendu** : Score anonymous significativement < 100%. ProductScore global en baisse (mécanique, attendu).

#### 3.4 Rebuild surrogate cache (si autoresearch nécessaire)

```bash
uv run python -m scripts.ml.build_fusion_surrogate_cache --gold-set data/gold_set.json --splits 3
```

## Dependencies & Risks

- **Risque faible** : Le score ProductScore global va baisser mécaniquement. C'est le résultat attendu et souhaité — le score devient informatif.
- **Dépendance** : Le surrogate cache doit être reconstruit après modification du gold set si autoresearch doit tourner.
- **Pas de risque de régression** : Le filtrage `is_anonymous` dans evaluate.py reste identique.

## Scores de référence (avant)

| Métrique | Score |
|----------|-------|
| ProductScore | 81.82 |
| GlobalScore | 80.79 |
| Anonymous holdout | 100.0 |
| Instance eval | 77.5% |

## References

- Brainstorm : `docs/brainstorms/2026-03-21-anonymous-holdout-rework-brainstorm.md`
- Plan de session initial : `docs/03-ml-detection/experiments/next-session-anonymous-holdout.md`
- Architecture branches : `docs/03-ml-detection/branch-architecture.md`
- Session précédente : `docs/03-ml-detection/experiments/2026-03-20-multi-instance-eval-and-improvement.md`
