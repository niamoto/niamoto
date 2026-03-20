# Cartographie des possibilités IA pour Niamoto

*Mars 2026 — Document d'exploration*

## Contexte

Niamoto est une plateforme de données écologiques qui ingère des CSV
(inventaires forestiers, données GBIF, relevés de terrain), détecte les types
de colonnes, transforme les données, et génère des pages de visualisation.

Le pipeline ML actuel (TF-IDF + HistGBT + Fusion, NiamotoOfflineScore 78.84)
fonctionne. Ce document explore ce que les développements récents en IA
pourraient apporter **au-delà de la simple détection de colonnes** — de
l'import à la génération de pages.

**Principe conservé** : automatiser l'analyse de données écologiques et leur
mise en valeur à travers des pages, en agrégeant les données par groupes.

**Contrainte relâchée** : on explore librement, sans se limiter aux
contraintes actuelles (offline strict, scikit-learn only, < 100 MB).

---

## Vue d'ensemble

```
CSV brut
  │
  ▼
┌─────────────────────────────────────────────────────┐
│  1. COMPRENDRE LES COLONNES                         │
│     Que contient ce fichier ?                        │
│     → Détection de types, rôles, concepts            │
├─────────────────────────────────────────────────────┤
│  2. COMPRENDRE LE DATASET                            │
│     De quel type d'étude s'agit-il ?                 │
│     → Pattern detection, relations inter-colonnes    │
├─────────────────────────────────────────────────────┤
│  3. VÉRIFIER LA QUALITÉ                              │
│     Les données sont-elles fiables ?                 │
│     → Anomalies, outliers, cohérence                 │
├─────────────────────────────────────────────────────┤
│  4. TRANSFORMER ET AGRÉGER                           │
│     Quelles statistiques calculer ?                  │
│     → Agrégations par groupe, métriques écologiques  │
├─────────────────────────────────────────────────────┤
│  5. VISUALISER                                       │
│     Quel graphique pour ces données ?                │
│     → Suggestion de charts, mise en page             │
├─────────────────────────────────────────────────────┤
│  6. RACONTER                                         │
│     Que disent ces données ?                         │
│     → Résumés narratifs, descriptions auto-générées  │
├─────────────────────────────────────────────────────┤
│  7. INTERROGER                                       │
│     "Montre-moi le DBH moyen par famille"            │
│     → Langage naturel → SQL/DuckDB                   │
└─────────────────────────────────────────────────────┘
```

---

## 1. Comprendre les colonnes (ce qu'on fait déjà)

### Ce qu'on a

Pipeline 5 couches : alias → header (TF-IDF) → values (HistGBT) → fusion →
projection sémantique. NiamotoOfflineScore 78.84. Fonctionne offline, ~3 MB,
< 500ms par colonne.

### Ce qui existe de mieux

#### Embeddings multilingues (sentence-transformers)

**Quoi** : au lieu de découper les noms de colonnes en morceaux de lettres
(n-grammes), on les transforme en vecteurs denses dans un espace où les mots
similaires sont proches. `"hauteur"` et `"height"` seraient proches même sans
partager de lettres.

**Modèles** :
- `paraphrase-multilingual-MiniLM-L12-v2` — 118 MB, 50+ langues
- `gte-multilingual-base` (Alibaba) — 305 MB, 70+ langues
- `EmbeddingGemma-300M` (Google, via FastEmbed/ONNX) — 200 MB, 100+ langues,
  pas besoin de PyTorch

**Pour Niamoto** : comblerait le trou principal — le matching multilingue
au-delà des racines latines. `"hauteur"` (FR) et `"height"` (EN) ne
partagent aucun n-gramme mais seraient proches en espace vectoriel.

**Verdict** : candidat Phase 4. Utilisable en complément du TF-IDF, pas en
remplacement. ~200 MB, ONNX Runtime (léger), inference < 15ms.

#### Small Language Models (SLM) en zero-shot

**Quoi** : des petits modèles de langage capables de classifier sans
entraînement spécifique. On leur dit "cette colonne s'appelle dbh et contient
[10, 15, 23, 45], qu'est-ce que c'est ?" et ils répondent.

**Modèles** :
- `Qwen3-0.6B` — 1.2 GB, tourne sur CPU via Ollama
- `Phi-3-mini` (Microsoft) — 2.3 GB, bon en raisonnement
- `Gemma-2-2B` (Google) — 2 GB, bien pour les tâches structurées
- `SmolLM-1.7B` (HuggingFace) — 1.7 GB, ultra-compact

**Pour Niamoto** : détection zero-shot des cas difficiles (colonnes anonymes,
codes métier). Pas pour toutes les colonnes (trop lent), mais comme "second
avis" quand le classifieur est incertain.

**Verdict** : candidat Phase 4. Optionnel (dégradation gracieuse si Ollama
n'est pas installé). Qwen3-0.6B est le meilleur rapport taille/qualité.

#### Modèles tabulaires spécialisés (Sherlock, Sato, DoDuo)

**Quoi** : des réseaux neuronaux profonds entraînés spécifiquement sur la
détection de types de colonnes, avec 100k-700k colonnes labélisées.

**Pourquoi pas pour nous** : ils nécessitent 10-100× plus de données que
notre gold set (2 231 colonnes). Avec plus de données, notre pipeline
progresserait aussi — **plus de données bat un meilleur algorithme** à notre
échelle.

#### ColBERT / ModernColBERT / Reason-ModernColBERT

**Quoi** : des modèles de **recherche documentaire** (trouver des passages
pertinents dans un corpus). ColBERT utilise une "interaction tardive" —
chaque token du query interagit avec chaque token du document pour un matching
fin.

**Pourquoi pas pour nous** :
- C'est un **retrieval model**, pas un classifieur
- Reason-ModernColBERT est **anglais uniquement** (entraîné sur 2T tokens EN)
- 149M paramètres pour matcher des noms de colonnes de 1-3 mots = canon pour
  tuer une mouche
- Licence **non commerciale** (cc-by-nc-4.0)

**En résumé** : impressionnant techniquement, mais conçu pour un problème
différent du nôtre.

---

## 2. Comprendre le dataset (relations inter-colonnes)

### Ce qu'on a

`DatasetPatternDetector` : 6 patterns (occurrence, forest, spatial, checklist,
trait, temporal). Règles manuelles.

### Ce qui pourrait exister

#### Suggestions cross-colonnes par SLM

**Quoi** : un petit modèle de langage qui, voyant l'ensemble des colonnes
détectées, fait des inférences de haut niveau :
- "Les colonnes `flower_month` et `fruit_month` forment un calendrier
  phénologique"
- "Les colonnes `lat` + `lon` + `date` + `species` = données d'occurrences
  type GBIF"
- "Ce dataset ressemble à un inventaire forestier tropical (diamètre, hauteur,
  espèce, parcelle)"

**Pour Niamoto** : enrichirait le `DatasetPatternDetector` actuel avec des
inférences que les règles manuelles ne capturent pas.

**Comment** : Qwen3-0.6B via Ollama. On lui passe un résumé structuré du
dataset (liste des colonnes détectées + stats) et on lui demande un JSON de
suggestions.

**Verdict** : intéressant mais pas critique. Les 6 patterns actuels couvrent
80% des cas.

---

## 3. Vérifier la qualité

### Ce qu'on a

12 règles d'anomalie (domain-specific validators). Manuelles mais
explicables.

### Ce qui existe

#### Profilage automatique

- **ydata-profiling** (ex-pandas-profiling) : génère des rapports HTML
  complets (distributions, corrélations, valeurs manquantes, alertes). Open
  source, mature.
- **Great Expectations** : validation de données par assertions déclaratives.
  "La colonne dbh doit être entre 1 et 500 cm."
- **Deepchecks** : détection de drift, intégrité des données, validation
  train/test.

**Pour Niamoto** : ydata-profiling pourrait générer un rapport de qualité
à l'import, avant même la transformation. Mais c'est du profilage descriptif,
pas de l'IA.

#### Détection d'anomalies par ML

**Quoi** : au lieu de règles fixes ("dbh < 500 cm"), un modèle apprend les
distributions attendues et signale les valeurs aberrantes.

**Modèles** :
- Isolation Forest (scikit-learn, déjà disponible)
- Autoencoders (PyTorch, plus lourd)
- Modèles conditionnels : "pour un Araucaria, un dbh de 150 cm est normal ;
  pour un Metrosideros, c'est suspect"

**Pour Niamoto** : utile si on a assez de données par espèce/site. Les règles
manuelles actuelles sont plus explicables et suffisantes pour la v1.

**Verdict** : post-v1. Les 12 règles actuelles sont le bon choix maintenant.
Isolation Forest pourrait être ajouté comme option sans nouvelle dépendance.

---

## 4. Transformer et agréger (suggestions intelligentes)

### Ce qu'on a

Affordance matching : `ColumnSemanticProfile` → suggestions de
transformers/widgets. Règles manuelles dans `affordance_matcher.py`.

### Ce qui pourrait exister

#### Templates de transformations paramétrés

**Quoi** : au lieu de hardcoder les affordances, un catalogue de
"recettes de transformation" associées à des combinaisons de rôles/concepts :

```yaml
- pattern: [measurement.diameter, taxonomy.species, identifier.plot]
  transforms:
    - name: dbh_by_species
      type: group_stats
      group_by: taxonomy.species
      measure: measurement.diameter
      stats: [mean, std, n, median]
    - name: dbh_distribution
      type: histogram
      column: measurement.diameter
      bins: 20
```

**Pour Niamoto** : rendrait les transformations configurables via YAML au lieu
de code Python. Extensible par la communauté.

**Verdict** : faisable immédiatement, sans IA. C'est de l'ingénierie, pas du
ML.

---

## 5. Visualiser (suggestion et génération de charts)

### Ce qu'on a

Widgets manuellement configurés dans `export.yml`. Le système propose des
affordances (scatter, bar, etc.) mais ne génère pas de code.

### Ce qui existe

#### LIDA (Microsoft Research, 2023)

**Quoi** : prend un dataset + un objectif en langage naturel, et génère du
code de visualisation (matplotlib/seaborn). Utilise un LLM pour chaque
génération.

**Limites** : nécessite un LLM à chaque appel (pas offline), génère
matplotlib (pas Plotly/notre stack), qualité variable.

**URL** : https://github.com/microsoft/lida

#### Data Formulator (Microsoft Research, 2024)

**Quoi** : successeur spirituel de LIDA. Interface conversationnelle pour
créer des visualisations. L'utilisateur décrit ce qu'il veut, le système
génère le code.

**Limites** : application standalone, pas une bibliothèque. Difficile à
intégrer.

**URL** : https://github.com/microsoft/data-formulator

#### Approche pragmatique : templates de widgets

**Quoi** : au lieu de générer du code à la volée, un catalogue de templates
de visualisation associés à des types de données :

| Combinaison détectée | Widget suggéré | Pourquoi |
|---|---|---|
| 1 mesure continue | Histogramme | Distribution |
| 1 mesure + 1 catégorie | Boxplot par groupe | Comparaison |
| 2 mesures continues | Scatter plot | Corrélation |
| 1 mesure + coordonnées | Carte choroplèthe | Spatial |
| 1 catégorie | Barplot / treemap | Fréquences |
| 1 mesure + temps | Line chart | Tendance |
| 1 taxon hiérarchique | Sunburst | Taxonomie |

**Pour Niamoto** : c'est déjà partiellement ce que fait l'affordance matcher.
Le rendre plus explicite et configurable serait un gain immédiat.

#### Génération de specs Plotly par SLM

**Quoi** : un petit modèle génère directement une spec Plotly JSON à partir
d'une description du widget et des données.

**Comment** : Qwen3-4B via Ollama. On lui passe le schema (colonnes, types,
stats) + le template choisi, et il génère la configuration Plotly complète.

**Pour Niamoto** : remplacerait le code Python qui construit les widgets.
L'utilisateur pourrait dire "fais-moi un scatter de dbh vs height coloré par
famille" et obtenir le widget.

**Verdict** : ambitieux mais faisable post-v1. Nécessite Qwen3-4B (~8 GB
RAM) ou un appel API (Claude/GPT).

---

## 6. Raconter (résumés narratifs)

### Ce qu'on a

Rien. Les pages générées montrent des graphiques sans texte explicatif.

### Ce qui pourrait exister

#### Descriptions auto-générées de widgets

**Quoi** : chaque widget est accompagné d'un paragraphe descriptif :
> "La distribution des diamètres à hauteur de poitrine (DBH) montre une courbe
> en J inversé typique des forêts tropicales matures, avec 65% des individus
> sous 20 cm et quelques émergents atteignant 120 cm. La famille des
> Sapotaceae domine les grandes classes de diamètre."

**Comment** :
- **Option locale** : Qwen3-4B via Ollama (~8 GB). On passe les stats
  agrégées + le contexte écologique, il génère un paragraphe.
- **Option API** : Claude Haiku. Plus cher mais meilleure qualité. ~$0.001
  par widget.
- **Option template** : des phrases à trous remplies par les statistiques.
  "La distribution de {mesure} montre une médiane de {median} avec un
  coefficient de variation de {cv}%." Zero IA, 100% fiable.

**Pour Niamoto** : transformerait les pages de "tableaux de bord silencieux"
en "rapports narratifs". Gros gain de valeur pour les botanistes.

**Verdict** : l'option template est implémentable immédiatement. L'option
SLM/API serait un upgrade post-v1 spectaculaire.

---

## 7. Interroger (langage naturel → SQL)

### Ce qu'on a

Rien. L'utilisateur doit écrire des configurations YAML ou modifier du code
Python.

### Ce qui existe

#### Text-to-SQL

**Quoi** : l'utilisateur écrit une question en français, le système la
traduit en requête SQL exécutée sur DuckDB.

> "Quel est le diamètre moyen par famille pour les arbres de plus de 10 cm ?"
> → `SELECT family, AVG(dbh) FROM occurrences WHERE dbh > 10 GROUP BY family`

**Modèles** :
- **SQLCoder-7B** (Defog) — 7 GB, spécialisé SQL, bon sur CPU mais lent
- **DuckDB-NSQL-7B** (MotherDuck/NumbersStation) — 4 GB, fine-tuné pour
  DuckDB spécifiquement
- **Qwen3-4B** — 4 GB, généraliste mais correct en SQL
- **Claude/GPT via API** — meilleure qualité, ~$0.01/requête

**Approche pragmatique** : avant le text-to-SQL par LLM, **10 templates SQL
paramétrés** couvrent 90% des questions qu'un botaniste poserait :

```python
TEMPLATES = {
    "distribution": "SELECT {col}, COUNT(*) FROM {table} GROUP BY {col}",
    "stats_by_group": "SELECT {group}, AVG({measure}), STDDEV({measure}) FROM {table} GROUP BY {group}",
    "top_n": "SELECT {group}, COUNT(*) as n FROM {table} GROUP BY {group} ORDER BY n DESC LIMIT {n}",
    # ...
}
```

L'utilisateur choisit un template + les colonnes détectées → requête
instantanée, zéro dépendance.

**Verdict** :
- **Court terme** : templates SQL paramétrés (0 dépendance)
- **Moyen terme** : Qwen3-4B via Ollama si l'utilisateur a 8 GB RAM
- **Long terme** : interface conversationnelle avec un LLM

---

## Matrice de décision

| Possibilité | Impact | Effort | Dépendances | Offline | Phase |
|---|---|---|---|---|---|
| **Templates SQL paramétrés** | Moyen | 2j | Aucune | Oui | v1 |
| **Templates de widgets YAML** | Moyen | 2j | Aucune | Oui | v1 |
| **Descriptions templates (phrases à trous)** | Moyen | 1j | Aucune | Oui | v1 |
| **Embeddings multilingues (ONNX)** | Moyen | 3j | onnxruntime (~20 MB) | Oui | v1.1 |
| **Qwen3-0.6B cross-colonnes** | Moyen | 3j | Ollama (optionnel) | Oui* | v1.1 |
| **ydata-profiling à l'import** | Faible | 1j | ydata-profiling | Oui | v1.1 |
| **Qwen3-4B text-to-SQL** | Élevé | 5j | Ollama (8 GB RAM) | Oui* | v2 |
| **Descriptions par SLM** | Élevé | 5j | Ollama (8 GB RAM) | Oui* | v2 |
| **Génération Plotly par SLM** | Élevé | 7j | Ollama (8 GB RAM) | Oui* | v2+ |
| **Claude API pour narration** | Élevé | 2j | API key + réseau | Non | v2 |
| **Interface conversationnelle** | Très élevé | 10j+ | LLM (local ou API) | Partiel | v3 |

*\* Offline si Ollama installé localement. Dégradation gracieuse sinon.*

---

## Ce qui ne vaut PAS le coup (et pourquoi)

| Technologie | Pourquoi non |
|---|---|
| **ColBERT / Reason-ModernColBERT** | Modèle de retrieval, pas de classification. Anglais uniquement. 149M params pour 25 concepts. |
| **TAPAS / TaPEx / TableFormer** | 440-890 MB + GPU. Entraînés sur Wikipedia, pas l'écologie. |
| **Sherlock / Sato / DoDuo complets** | Nécessitent 100k+ colonnes. On en a 2 231. |
| **LIDA intégration directe** | LLM obligatoire à chaque génération. Matplotlib, pas Plotly. |
| **RACOON** | Knowledge Graph externe + LLM en ligne. Trop de dépendances. |
| **BioCLIP** | Modèle vision (images de plantes), pas tabular (CSV). |
| **spaCy / NER** | Overkill pour des noms de colonnes de 1-3 mots. Les n-grammes suffisent. |

---

## La vraie priorité

**Plus de données bat un meilleur algorithme.**

Avec 5 000+ colonnes gold, le pipeline actuel (TF-IDF + HistGBT + Fusion)
progresserait mécaniquement. Avec les mêmes 2 231 colonnes et un modèle plus
sophistiqué, le gain serait marginal.

L'enrichissement du gold set reste la stratégie la plus rentable pour
améliorer la détection. Les technologies explorées ici apportent de la valeur
**au-delà** de la détection — narration, visualisation, interrogation — pas
en remplacement.

---

## Vision cible

```
                    Botaniste
                       │
                 "Importe ce CSV"
                       │
                       ▼
              ┌─────────────────┐
              │  COMPRENDRE     │  ML actuel (amélioré)
              │  colonnes +     │  + embeddings multilingues
              │  dataset        │  + SLM cross-colonnes (optionnel)
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  VÉRIFIER       │  Règles + Isolation Forest
              │  qualité        │  + profiling auto
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  TRANSFORMER    │  Templates YAML
              │  agréger        │  + SQL paramétrés
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  VISUALISER     │  Templates widgets
              │  + RACONTER     │  + descriptions templates
              │                 │  + SLM narration (optionnel)
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  INTERROGER     │  Templates SQL → SLM text-to-SQL
              │  (futur)        │  → interface conversationnelle
              └─────────────────┘
```

Le fil conducteur : **chaque étape a une version sans IA (templates, règles)
et une version enrichie par IA (SLM, embeddings, API)**. L'utilisateur
obtient toujours un résultat, même sans GPU ni connexion internet. L'IA
améliore la qualité quand elle est disponible.

---

## Références

### Modèles mentionnés

- ModernBERT : https://huggingface.co/answerdotai/ModernBERT-base
- Reason-ModernColBERT : https://huggingface.co/lightonai/Reason-ModernColBERT
- paraphrase-multilingual-MiniLM : https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
- EmbeddingGemma : via FastEmbed (ONNX)
- Qwen3 : https://huggingface.co/Qwen
- Phi-3-mini : https://huggingface.co/microsoft/Phi-3-mini-4k-instruct
- SQLCoder : https://huggingface.co/defog/sqlcoder-7b-2
- DuckDB-NSQL : https://huggingface.co/motherduck/DuckDB-NSQL-7B-v0.1

### Outils

- LIDA : https://github.com/microsoft/lida
- Data Formulator : https://github.com/microsoft/data-formulator
- ydata-profiling : https://github.com/ydataai/ydata-profiling
- Ollama : https://ollama.com
- FastEmbed : https://github.com/qdrant/fastembed
