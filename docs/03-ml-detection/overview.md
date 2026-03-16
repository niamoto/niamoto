# Détection automatique des colonnes

## Ce que ça fait

Tu importes un fichier CSV d'inventaire forestier dans Niamoto. Au lieu de configurer manuellement chaque colonne ("ça c'est un diamètre, ça c'est une espèce, ça c'est des coordonnées"), Niamoto **détecte automatiquement** le contenu et propose un dashboard complet : histogramme des diamètres, carte de distribution, répartition par famille.

Tu n'as plus qu'à ajuster si besoin.

## Pourquoi c'est nécessaire

Chaque équipe nomme ses colonnes différemment :

| Ce que c'est | Guyane | France IFN | FIA (US) | Espagne | Anonyme |
|-------------|--------|------------|----------|---------|---------|
| Diamètre | `diam` | `C13` | `DIA` | `dap` | `X1` |
| Hauteur | `haut` | `HTOT` | `HT` | `altura` | `col_2` |
| Espèce | `espece` | `ESPAR` | `SPCD` | `especie` | `X5` |
| Latitude | `lat` | `YL` | `LAT` | `latitud` | `col_3` |

Sans détection automatique, chaque utilisateur doit configurer manuellement ses colonnes avant de pouvoir visualiser quoi que ce soit. C'est un frein à l'adoption.

## Comment ça marche

Le système détecte le **rôle** de chaque colonne — c'est-à-dire ce qu'on peut en faire :

| Rôle détecté | Ce que Niamoto propose |
|-------------|----------------------|
| Mesure numérique | Histogramme, résumé statistique, scatter plot |
| Taxonomie | Répartition par famille/genre, sunburst |
| Coordonnées géographiques | Carte interactive |
| Données temporelles | Timeline, filtre par année |
| Catégorie | Bar chart, donut chart |
| Identifiant | Clé de jointure entre tables |

Pour y arriver, deux signaux complémentaires sont combinés :

1. **Le nom de la colonne** — `diametre` et `diametro` partagent les mêmes séquences de lettres. Un modèle de n-grammes de caractères les rapproche naturellement, même entre langues proches.

2. **Les valeurs** — un diamètre a une distribution log-normale entre 5 et 300, des coordonnées sont entre -90 et 90, un nom d'espèce suit le format "Genre espece". Quand le nom de colonne est anonyme (`X1`), les valeurs prennent le relais.

Les deux sont fusionnés en une prédiction finale. L'utilisateur peut ensuite affiner chaque paire transformer/widget dans le GUI.

## Les données d'entraînement

Le modèle est entraîné sur **2231 colonnes labélisées** provenant de :

- **88 jeux de données réels** : IFN France, FIA US, GBIF (Espagne, Norvège, Bénin, Tanzanie, Chine...), GUYADIV Guyane, inventaires Afrique/NC/Madagascar/Malaisie/Panama, Zenodo (BCI, FERP Californie, Heishiding Chine...)
- **6 continents**, **8 langues** (EN, FR, ES, PT, DE, ID + headers anonymes)
- **61 concepts** organisés en rôles : taxonomie, localisation, mesures, environnement, statistiques, temporel, catégories, identifiants

Toute la détection tourne en local avec scikit-learn (~3 MB de dépendances). Pas besoin de réseau, pas de LLM.

## Contribuer

Pour améliorer la détection d'un type de colonne mal reconnu :

1. **Ajouter des alias** dans `src/niamoto/core/imports/ml/column_aliases.yaml` — pas besoin de ML, juste un fichier YAML. Exemple : ajouter `"circonference"` comme alias de `measurement.diameter` en français.

2. **Ajouter des données d'entraînement** dans `scripts/ml/build_gold_set.py` — labéliser les colonnes d'un nouveau dataset et le référencer dans la liste des sources.

3. **Ré-entraîner** : `uv run python scripts/ml/train_header_model.py && uv run python scripts/ml/train_value_model.py`

## Scores actuels

| Modèle | Macro-F1 | Ce que ça veut dire |
|--------|----------|-------------------|
| Header (nom de colonne) | 0.77 | 77% des colonnes correctement classifiées par leur nom |
| Values (valeurs statistiques) | 0.35 | 35% — les valeurs seules sont ambiguës (un diamètre et une hauteur se ressemblent numériquement) |
| Fusion (header + values) | en évaluation | Combinaison des deux signaux |

Le score du header est le plus important car dans la majorité des cas, les colonnes ont des noms informatifs. Le modèle sur les valeurs intervient quand le nom est anonyme ou ambigu.

## Limites connues

- Les colonnes très rares (< 5 exemples dans le gold set) sont regroupées sous des catégories génériques
- La calibration de confiance n'est pas encore en place — le modèle ne sait pas encore dire "je suis sûr à 85%"
- Le modèle sur les valeurs reste faible pour distinguer deux types de mesures entre eux (diamètre vs hauteur) — mais ce n'est pas bloquant car le rôle "mesure" suffit pour proposer un histogramme

## Architecture technique

```
CSV importé
     │
     ├── Nom de colonne ──→ TF-IDF char n-grams ──→ LogisticRegression
     │                                                      │
     ├── Valeurs ──→ 37 features statistiques ──→ HistGradientBoosting
     │                                                      │
     └── Fusion ──→ LogReg calibrée sur les probas des 2 branches
                           │
                    Rôle détecté + confiance
                           │
                    Suggestion de paires transformer/widget
```

## Fichiers clés

| Fichier | Rôle |
|---------|------|
| `src/niamoto/core/imports/ml/alias_registry.py` | Matching nom → concept via aliases multilingues |
| `src/niamoto/core/imports/ml/column_aliases.yaml` | 25 concepts × 8 langues |
| `src/niamoto/core/imports/ml/evaluation.py` | Harness d'évaluation (GroupKFold, holdouts) |
| `src/niamoto/core/imports/ml/concept_taxonomy.py` | Fusion des 111 concepts fins → 61 concepts |
| `src/niamoto/core/imports/profiler.py` | DataProfiler avec `ml_mode=auto/off/force` |
| `scripts/ml/build_gold_set.py` | Construction du gold set (88 sources) |
| `scripts/ml/train_header_model.py` | Entraînement branche header |
| `scripts/ml/train_value_model.py` | Entraînement branche values |
| `scripts/ml/evaluate.py` | CLI metric pour évaluation |
| `data/gold_set.json` | 2231 colonnes labélisées |
