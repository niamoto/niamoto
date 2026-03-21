# Anonymous holdout rework (2026-03-21)

## Objet

Remplacement du holdout anonymous (86 entrées synthétiques, score permanent 100%)
par un holdout diversifié basé sur de vraies colonnes du gold set, anonymisées
avec des noms génériques aléatoires.

## Problème

Le holdout anonymous ne testait rien d'utile :
- 86 entrées 100% synthétiques (distributions numpy)
- 76% concentrées sur 2 concepts (`measurement.height` + `measurement.diameter`)
- 10 concepts couverts sur ~45 coarse concepts
- Le values branch n'avait qu'à prédire "float continu" pour scorer 100%
- Poids de 10% dans ProductScore → gonflait le score sans information

## Solution implémentée

### Nouvelle fonction `_build_anonymous_holdout()`

Dans `scripts/ml/build_gold_set.py` :
- Échantillonnage stratifié des colonnes réelles par `concept_coarse`
- Plancher de 2 entrées par concept, seed fixe 42
- Noms aléatoires tirés d'un pool de ~300 noms génériques (`col_N`, `X_N`, `V_N`, `var_x`, `field_N`)
- Quality tag `"gold_anonymous"` (distinct de `"gold"` et `"synthetic"`)

### Suppression de l'ancien mécanisme

- Supprimé `HEADER_VARIANTS["anonymous"]` (10 concepts × 2-5 variantes)
- Nettoyé les 6 blocs `if lang == "anonymous"` dans `generate_synthetic_columns()`

### Métrique values-only dans `evaluate.py`

- `_evaluate_holdout_score()` accepte `return_models=True`
- Le bloc anonymous affiche maintenant une métrique values-only informative (accuracy du values branch seul)
- Le bucket `anonymous` dans ProductScore reste sur le pipeline fusion complet, poids 10%

## Résultats

### Distribution du nouveau holdout

| Métrique | Avant | Après |
|----------|:-----:|:-----:|
| Entrées anonymes | 86 | **122** |
| Concepts couverts | 10 | **61** |
| Quality | `synthetic` | `gold_anonymous` |
| Distribution | 76% sur 2 concepts | **2 par concept (uniforme)** |
| Noms uniques | 31 | **122** |

### Scores

| Métrique | Avant | Après | Delta |
|----------|:-----:|:-----:|:-----:|
| **ProductScore** | 81.82 | **81.32** | **-0.50** |
| **GlobalScore** | 80.79 | **81.72** | **+0.93** |
| Anonymous holdout | 100.0 | **91.02** | **-8.98** |
| Anonymous values-only | n/a | **94.3%** (115/122) | — |

Détail ProductScore par bucket :

| Bucket | Avant | Après | Delta |
|--------|:-----:|:-----:|:-----:|
| tropical_field (30%) | 69.01 | 68.71 | -0.30 |
| research_traits (15%) | 75.49 | 77.08 | +1.59 |
| gbif_core_standard (20%) | 96.02 | 97.36 | +1.34 |
| gbif_extended (10%) | 88.18 | 88.22 | +0.04 |
| en_field (15%) | 78.46 | 78.30 | -0.16 |
| anonymous (10%) | 100.0 | **91.02** | **-8.98** |

### Analyse

**Anonymous holdout** : Le score a baissé de 100.0 à 91.02 — le holdout est maintenant
informatif. Le values-only est à 94.3% (115/122), ce qui montre que le values branch
seul est performant sur les données anonymes diversifiées.

**Autres buckets stables** : Les 5 buckets non-anonymous sont à ±1.5 pts de leurs
valeurs de référence (variation normale d'un run à l'autre). La baisse du ProductScore
(-0.50) est entièrement due au bucket anonymous qui est passé de 100% gonflé à un score
réaliste de 91%.

**Bug corrigé en cours de session** : Les entrées `gold_anonymous` étaient classifiées
comme `real_records` par `_is_real_record()` (car `quality != "synthetic"`). Elles
participaient aux holdout families et au primary GroupKFold → baisse artificielle de tous
les buckets. Fix : exclusion explicite des `is_anonymous` de `real_records` et
`synthetic_records` dans `evaluate_niamoto_protocol()`.

## Fichiers modifiés

| Fichier | Action |
|---------|--------|
| `scripts/ml/build_gold_set.py` | `_build_anonymous_holdout()`, suppression HEADER_VARIANTS["anonymous"] |
| `scripts/ml/evaluate.py` | Métrique values-only, `return_models` param, exclusion `is_anonymous` de `real_records` |
| `data/gold_set.json` | Régénéré (2561 entrées) |

## Commandes de reproduction

```bash
# Rebuild gold set
uv run python -m scripts.ml.build_gold_set

# Vérifier distribution
uv run python3 -c "
import json
from collections import Counter
with open('data/gold_set.json') as f:
    gold = json.load(f)
anon = [e for e in gold if e.get('is_anonymous')]
print(f'Anonymous: {len(anon)} across {len(Counter(e[\"concept_coarse\"] for e in anon))} concepts')
for c, n in Counter(e['concept_coarse'] for e in anon).most_common():
    print(f'  {c}: {n}')
"

# Évaluation complète
uv run python -m scripts.ml.evaluate --model all --metric product-score
```
