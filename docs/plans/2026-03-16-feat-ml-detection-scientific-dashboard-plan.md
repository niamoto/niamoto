---
title: ML Detection Scientific Dashboard
type: feat
date: 2026-03-16
---

# Dashboard scientifique — ML Column Detection

Page HTML autonome interactive pour présenter et justifier le système de détection automatique de colonnes de Niamoto devant un comité scientifique.

## Overview

Un fichier HTML unique (~2 MB avec Plotly.js inline) ouvrable dans n'importe quel navigateur, contenant :
- Carte mondiale interactive des 93 sources de données
- Visualisations interactives (Plotly) des concepts, scores, progression
- Justification académique de chaque choix méthodologique avec citations
- Comparatif avec les alternatives crédibles
- Roadmap du projet

**Public** : comité scientifique / reviewers — rigueur académique attendue.

## Architecture du fichier

```
ml-detection-dashboard.html (fichier unique, ~2 MB)
├── <head>
│   ├── Plotly.js 3.0.1 (CDN avec fallback inline)
│   ├── CSS inline (design sobre, académique)
│   └── Google Fonts: Inter + JetBrains Mono
├── <body>
│   ├── Section 1: Hero / Résumé
│   ├── Section 2: Architecture du pipeline
│   ├── Section 3: Catalogue des datasets (carte + tableau)
│   ├── Section 4: Taxonomie des concepts
│   ├── Section 5: Justification méthodologique
│   ├── Section 6: Résultats & progression autoresearch
│   ├── Section 7: Alternatives crédibles
│   ├── Section 8: Roadmap
│   └── Section 9: Références bibliographiques
└── <script>
    ├── Données JSON inline (extraites du gold set)
    ├── Plotly charts (carte, sunburst, barres, lignes)
    └── Interactions (filtres, tooltips, navigation)
```

## Sections détaillées

### Section 1 — Hero / Résumé

Bannière sobre avec les métriques clés :

| Métrique | Valeur |
|---|---|
| Colonnes labélisées | 2 231 |
| Sources de données | 93 (88 réelles + synthétiques) |
| Continents | 6 |
| Langues | 7 + Darwin Core |
| Concepts détectés | 62 fins → 45 grossiers |
| Header model F1 | 0.77 |
| Values model F1 | 0.35 |
| Technologie | scikit-learn (offline, sans GPU) |

### Section 2 — Architecture du pipeline

Diagramme SVG/CSS du pipeline 3 branches :

```
Colonne CSV
    ↓
┌─────────┬──────────┬──────────┐
│ HEADER  │  VALUES  │ CONTEXT  │
│ TF-IDF  │ 37 feat. │ (futur)  │
│ char2-5 │ HistGBT  │          │
│ + L1 LR │          │          │
└────┬────┴────┬─────┴────┬─────┘
     └─────────┼──────────┘
               ↓
        FUSION (LogReg)
               ↓
     ColumnSemanticProfile
```

Chaque branche est cliquable → affiche les hyperparamètres et la justification.

**Données à intégrer** :

Header model :
- `TfidfVectorizer(analyzer="char_wb", ngram_range=(2,5), max_features=5000, sublinear_tf=True)`
- `LogisticRegression(C=130.0, penalty="l1", solver="saga", class_weight="balanced")`

Values model :
- 37 features (14 num stats, 3 uniqueness, 6 char, 4 regex, 2 bio, 6 domain, 2 meta)
- `HistGradientBoostingClassifier(max_iter=500, max_depth=10, learning_rate=0.05)`

Fusion model :
- Input : 2×61 probabilities + 3 meta = 125 dimensions
- `LogisticRegression(C=1.0, solver="lbfgs", class_weight="balanced")`

### Section 3 — Catalogue des datasets

#### 3a. Carte mondiale (Plotly scattergeo)

Points sur la carte avec :
- **Couleur** par type : GBIF (bleu), inventaire national (vert), Zenodo (orange), synthétique (gris)
- **Taille** proportionnelle au nombre de colonnes
- **Tooltip** : nom, pays, # colonnes, langue, biome

Sources à géolocaliser (coordonnées approximatives) :

| Source | Pays/Région | Lat | Lon | Colonnes | Type |
|---|---|---|---|---|---|
| gbif_mexico_flora | Mexique | 23.6 | -102.5 | 40 | GBIF |
| gbif_colombia_wetland | Colombie | 4.6 | -74.1 | 39 | GBIF |
| gbif_norway_nfi | Norvège | 60.5 | 10.7 | 38 | GBIF |
| gbif_wales_woodland | Pays de Galles | 52.1 | -3.8 | 35 | GBIF |
| gbif_madagascar_grasses | Madagascar | -18.9 | 47.5 | 35 | GBIF |
| gbif_philippines_samar | Philippines | 11.5 | 125.0 | 34 | GBIF |
| gbif_spain_ifn3 | Espagne | 40.4 | -3.7 | 30+ | GBIF |
| gbif_benin | Bénin | 9.3 | 2.3 | 30+ | GBIF |
| gbif_uganda_savanna | Ouganda | 1.4 | 32.3 | 30+ | GBIF |
| gbif_kenya_mangrove | Kenya | -4.0 | 39.7 | 30+ | GBIF |
| gbif_ethiopia | Éthiopie | 9.0 | 38.7 | 30+ | GBIF |
| gbif_tanzania | Tanzanie | -6.4 | 34.9 | 30+ | GBIF |
| gbif_india_sundarbans | Inde | 21.9 | 89.2 | 30+ | GBIF |
| gbif_china_* | Chine | 35.9 | 104.2 | 30+ | GBIF |
| gbif_japan | Japon | 36.2 | 138.3 | 30+ | GBIF |
| gbif_thailand | Thaïlande | 15.9 | 100.5 | 30+ | GBIF |
| gbif_australia | Australie | -25.3 | 133.8 | 30+ | GBIF |
| gbif_nz_pdd | N.-Zélande | -40.9 | 174.9 | 30+ | GBIF |
| gbif_france | France | 46.2 | 2.2 | 30+ | GBIF |
| gbif_sweden | Suède | 60.1 | 18.6 | 30+ | GBIF |
| gbif_poland | Pologne | 51.9 | 19.1 | 30+ | GBIF |
| gbif_austria | Autriche | 47.5 | 14.6 | 30+ | GBIF |
| gbif_bulgaria | Bulgarie | 42.7 | 25.5 | 30+ | GBIF |
| gbif_canada | Canada | 56.1 | -106.3 | 30+ | GBIF |
| gbif_brazil | Brésil | -14.2 | -51.9 | 30+ | GBIF |
| fia_fl_* | Floride, USA | 27.7 | -81.5 | 40+ | IFN |
| fia_or_* | Oregon, USA | 43.8 | -120.6 | 40+ | IFN |
| ifn_* (8 modules) | France | 46.2 | 2.2 | 100+ | IFN |
| iefc_catalonia | Catalogne | 41.6 | 1.5 | 20+ | IFN |
| zenodo_bci_* | Panama (BCI) | 9.2 | -79.8 | 30+ | Zenodo |
| zenodo_california | Californie | 36.8 | -119.4 | 30+ | Zenodo |
| zenodo_china_* | Chine | 35.9 | 104.2 | 30+ | Zenodo |
| pasoh_* | Malaisie (Pasoh) | 2.98 | 102.3 | 20+ | Inventaire |
| berenty_* | Madagascar | -25.0 | 46.3 | 20+ | Inventaire |
| nc_occ, nc_plots | N.-Calédonie | -22.3 | 166.5 | 20+ | Inventaire |
| guyadiv_* | Guyane française | 3.9 | -53.1 | 20+ | Inventaire |
| afrique_* | Afrique multi-pays | 0.0 | 20.0 | 20+ | Inventaire |

#### 3b. Tableau filtrable

Colonnes : Source | Type | Pays | Continent | Langue | Biome | # Colonnes | Qualité (gold/silver/synthetic)

Filtres interactifs : continent, langue, type de source, biome.

### Section 4 — Taxonomie des concepts

#### 4a. Sunburst Plotly

Hiérarchie à 3 niveaux : Rôle → Concept grossier → Concept fin

```
measurement (22.8%)
├── diameter (171 cols)
├── height (177 cols)
├── biomass (30+ cols)
├── canopy (20+ cols)
├── cover (20+ cols)
├── ...
taxonomy (22.1%)
├── species (191 cols)
├── family (57 cols)
├── genus (41 cols)
├── ...
location (20.2%)
├── elevation (98 cols)
├── latitude (63 cols)
├── longitude (63 cols)
├── country (73 cols)
├── ...
```

#### 4b. Tableau des fusions (CONCEPT_MERGE)

Montrer les 73 fusions (concepts fins → grossiers) avec le nombre d'exemples avant/après.

### Section 5 — Justification méthodologique

Section centrale pour les reviewers. Pour chaque choix, un bloc structuré :

#### 5a. Pourquoi des n-grammes de caractères ?

**Choix** : `TfidfVectorizer(analyzer="char_wb", ngram_range=(2,5))`

**Justification** : Les noms de colonnes écologiques (1-3 mots) partagent des racines latines/grecques entre langues. "diametre" (FR) et "diametro" (ES) génèrent les mêmes trigrammes "dia", "iam", "ame". Les n-grammes de caractères sont le choix canonique pour les chaînes courtes multilingues.

**Citations** :
- Cavnar & Trenkle 1994 — N-gram-based Text Categorization (fondation théorique)
- Bojanowski et al. 2017 — fastText subword embeddings (morphèmes partagés entre langues)
- Apple Research — Language ID from Very Short Strings (supériorité sur strings < 50 chars)

**Visualisation** : Exemple interactif — saisir un nom de colonne, voir les n-grammes générés et les concepts prédits.

#### 5b. Pourquoi TF-IDF + LogisticRegression L1 ?

**Choix** : Baseline linéaire au lieu de Transformers/BERT

**Justification** : Avec 2 231 colonnes labélisées, un BERT (110M paramètres) risque le sur-apprentissage. TF-IDF + L1 LogReg est un "embarrassingly strong baseline" (Wang & Manning 2012) qui produit des coefficients interprétables — on peut inspecter quels n-grammes pilotent chaque prédiction.

**Citations** :
- Wang & Manning, ACL 2012 — "Baselines and Bigrams" (baselines linéaires compétitives)
- Shmueli, Statistical Science 2010 — "To Explain or to Predict?" (interprétabilité comme avantage scientifique)

**Visualisation** : Tableau comparatif TF-IDF+LR vs BERT vs Sentence Transformers sur les critères : taille de données requise, temps d'entraînement, interprétabilité, offline, taille du modèle.

#### 5c. Pourquoi HistGradientBoosting pour les valeurs ?

**Choix** : Arbres boostés sur 37 features statistiques

**Justification** : Le papier de référence (Grinsztajn et al. NeurIPS 2022) montre que les modèles à base d'arbres dominent les réseaux neuronaux sur données tabulaires < 10k lignes, surtout quand des features sont non informatives (ex: `in_lat_range` pour un concept non géographique).

**Citations** :
- Grinsztajn, Oyallon & Varoquaux, NeurIPS 2022 — "Why do tree-based models still outperform deep learning on tabular data?"
- Hulsebos et al., KDD 2019 — Sherlock (notre 37 features est une version allégée de leurs 1 588)

**Visualisation** : Feature importance chart (top 15 features les plus discriminantes du modèle values).

#### 5d. Pourquoi GroupKFold ?

**Choix** : Validation croisée groupée par `source_dataset`

**Justification** : Les colonnes d'un même dataset partagent des conventions de nommage, la qualité des données, les protocoles d'échantillonnage. Un KFold naïf laisserait fuiter cette information partagée. Roberts et al. 2017 est la référence pour les données écologiques structurées.

**Citations** :
- Roberts et al., Ecography 2017 — Cross-validation for structured ecological data
- Dietterich, Neural Computation 1998 — Tests statistiques pour comparer des classifieurs

**Visualisation** : Schéma de 5 folds montrant la répartition des datasets entre train/test.

#### 5e. Pourquoi macro-F1 ?

**Choix** : Moyenne non pondérée des F1 par concept

**Justification** : Les concepts rares (soil_ph, canopy_cover, phenology) sont souvent les plus précieux scientifiquement. Macro-F1 les traite avec le même poids que les concepts courants (species, latitude).

**Citations** :
- Sokolova & Lapalme, Information Processing & Management 2009
- Opitz & Burst 2021 — Clarification des deux formules macro-F1

**Visualisation** : Barchart comparant accuracy, micro-F1, weighted-F1, macro-F1 sur nos données — montrant comment les métriques biaisées masquent la performance sur les classes rares.

### Section 6 — Résultats & progression autoresearch

#### 6a. Courbe de progression

Graphique Plotly (lignes) montrant l'évolution du macro-F1 au fil des itérations autoresearch :

**Header model** (23 itérations documentées) :
```
0.3658 → 0.4455 → 0.4937 → 0.5283 → 0.5370 → 0.5375 → 0.5383 →
0.5470 → 0.5497 → 0.5529 → 0.5591 → 0.5640 → 0.5641 → ... → 0.7745*
```
*Note : le score 0.7745 vient de l'évaluation live (post-round 2 enrichi), les commits intermédiaires ne sont pas tous tracés.

**Values model** (8 itérations documentées) :
```
0.2877 → 0.3005 → 0.3063 → 0.3068 → 0.3257 → 0.3370 → 0.3403 →
0.3433 → 0.3522 → 0.3527
```

#### 6b. Lien avec Karpathy autoresearch

Encart expliquant le pattern autoresearch (Karpathy, mars 2026) :
1. Agent modifie un hyperparamètre
2. Évaluation GroupKFold macro-F1
3. Si F1 monte → git commit, on garde
4. Si F1 baisse → git revert, on essaie autre chose
5. Répéter 50+ fois

Lien : https://github.com/karpathy/autoresearch

### Section 7 — Alternatives crédibles

Tableau comparatif interactif :

| Approche | Données requises | Offline | F1 attendu | Complexité | Statut Niamoto |
|---|---|---|---|---|---|
| **TF-IDF + LR (actuel)** | 2k+ colonnes | Oui | 0.77 (header) | Faible | ✅ Implémenté |
| **Sherlock (DNN)** | 100k+ colonnes | Oui | 0.89 (VizNet) | Élevée | ❌ Données insuffisantes |
| **Sato (CRF + contexte)** | 100k+ colonnes | Oui | 0.93 (weighted) | Élevée | ❌ Données insuffisantes |
| **DoDuo (BERT fine-tuned)** | 10k+ colonnes | Oui (GPU) | 0.90+ | Élevée | ❌ Données insuffisantes |
| **LLM zero-shot (GPT-4)** | 0 | Non | 0.85+ (EN) | Faible | 🔄 Possible enrichissement gold set |
| **Sentence Transformers** | 1k+ colonnes | Oui (22 MB) | ~0.80? | Moyenne | 🔄 Candidat Phase 4 |
| **Regex / règles pures** | 0 | Oui | 0.20-0.40 | Très faible | ⚠️ Intégré comme features |
| **Active Learning** | Incrémental | Oui | Progressif | Moyenne | 🔄 Candidat Phase 4 |

Pour chaque alternative, un panneau dépliable avec :
- Description de l'approche (2-3 phrases accessibles)
- Papier de référence avec DOI/URL
- Pourquoi retenue ou écartée pour Niamoto
- Conditions sous lesquelles elle deviendrait pertinente

**Citations clés** :
- Sherlock : Hulsebos et al., KDD 2019 (https://arxiv.org/abs/1905.10688)
- Sato : Zhang et al., VLDB 2020 (https://arxiv.org/abs/1911.06311)
- DoDuo : Suhara et al., SIGMOD 2022 (https://arxiv.org/abs/2104.01785)
- LLM Column Typing : Korini & Bizer, VLDB Workshop 2023 (https://arxiv.org/abs/2306.00745)
- RACOON : 2024 (https://arxiv.org/abs/2409.14556)
- Magneto : Freire et al., VLDB 2025 (https://arxiv.org/abs/2412.08194)

### Section 8 — Roadmap

Timeline visuelle (barre horizontale ou Gantt simplifié CSS) :

```
Phase 1 — Fondations          ████████████████████ ✅ TERMINÉ
  Gold set 2231 cols, alias YAML, évaluation GroupKFold

Phase 1.5 — Autoresearch      ███████████░░░░░░░░░ 🔄 EN COURS
  Header 0.77, Values 0.35, Fusion en cours

Phase 2 — Validation           ░░░░░░░░░░░░░░░░░░░ ⏳
  Cible: macro-F1 ≥ 0.85, coverage@0.70 ≥ 75%

Phase 3 — Intégration          ░░░░░░░░░░░░░░░░░░░ ⏳
  ColumnSemanticProfile, affordances, anomalies

Phase 4 — Amélioration         ░░░░░░░░░░░░░░░░░░░ ⏳
  Active learning, feedback loop, LLM local optionnel
```

### Section 9 — Références bibliographiques

Liste complète des 17+ citations au format académique, triées par thème :

**Détection de types de colonnes** :
1. Hulsebos et al. (2019). Sherlock: A Deep Learning Approach to Semantic Data Type Detection. KDD.
2. Zhang et al. (2020). Sato: Contextual Semantic Type Detection in Tables. VLDB.
3. Deng et al. (2021). TURL: Table Understanding through Representation Learning. VLDB.
4. Suhara et al. (2022). Annotating Columns with Pre-trained Language Models. SIGMOD.
5. Korini & Bizer (2023). Column Type Annotation using ChatGPT. VLDB Workshop.
6. RACOON (2024). Retrieval-Augmented Column Type Annotation with LLMs.
7. Freire et al. (2025). Magneto: Combining Small and Large Language Models for Schema Matching. VLDB.

**Modélisation** :
8. Grinsztajn et al. (2022). Why do tree-based models still outperform deep learning on tabular data? NeurIPS.
9. Wang & Manning (2012). Baselines and Bigrams. ACL.
10. Bojanowski et al. (2017). Enriching Word Vectors with Subword Information. TACL.
11. Cavnar & Trenkle (1994). N-gram-based Text Categorization.

**Évaluation** :
12. Roberts et al. (2017). Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. Ecography.
13. Sokolova & Lapalme (2009). A systematic analysis of performance measures. IPM.
14. Opitz & Burst (2021). Macro F1 and Macro F1.
15. Dietterich (1998). Approximate Statistical Tests. Neural Computation.

**Méthodologie** :
16. Shmueli (2010). To Explain or to Predict? Statistical Science.
17. Karpathy (2026). autoresearch. GitHub.

## Choix techniques pour le HTML

### Librairies (inline ou CDN)

| Lib | Usage | Taille | Source |
|---|---|---|---|
| Plotly.js 3.0.1 | Carte, sunburst, barres, lignes | ~3.5 MB (minifié) | CDN avec `integrity` hash |
| Inter (Google Fonts) | Texte principal | CDN | Fallback system-ui |
| JetBrains Mono | Code/données | CDN | Fallback monospace |

**Option offline** : Un flag `OFFLINE_MODE` en haut du script — si activé, utilise des SVG statiques au lieu de Plotly (pour les situations sans internet).

### Design

- Palette sobre : fond blanc, accents bleu (#2563eb) et vert (#059669)
- Style inspiré des supplementary materials de Nature/Science
- Sections avec ancres pour navigation
- `@media print` pour export PDF propre
- Responsive (tablette minimum)

### Données inline

Les données du gold set seront extraites et injectées en JSON dans le HTML :

```javascript
const DATASETS = [
  { name: "gbif_mexico_flora", country: "Mexico", lat: 23.6, lon: -102.5,
    columns: 40, type: "gbif", language: "es", biome: "tropical" },
  // ... 92 autres sources
];

const CONCEPTS = [
  { fine: "taxonomy.species", coarse: "taxonomy.species", role: "taxonomy", count: 191 },
  // ... 61 autres concepts
];

const AUTORESEARCH_HEADER = [
  { iteration: 1, score: 0.3658, date: "2026-03-15" },
  // ... progression
];

const AUTORESEARCH_VALUES = [
  { iteration: 1, score: 0.2877, date: "2026-03-16" },
  // ...
];
```

**Script d'extraction** : Un petit script Python (`scripts/ml/export_dashboard_data.py`) extrait les données du gold set et des commits git pour générer le JSON, évitant de hardcoder.

## Acceptance Criteria

- [ ] Fichier HTML unique ouvrable dans Chrome/Firefox/Safari sans serveur
- [ ] Carte mondiale interactive avec les 93 sources (Plotly scattergeo)
- [ ] Sunburst des 62 concepts organisés par rôle
- [ ] Courbes de progression autoresearch (header + values)
- [ ] 5 blocs de justification méthodologique avec citations académiques
- [ ] Tableau comparatif des 8 alternatives avec références
- [ ] Roadmap visuelle des 4 phases
- [ ] 17+ références bibliographiques au format académique
- [ ] Filtres interactifs sur le tableau des datasets (continent, langue, type)
- [ ] Responsive (lisible sur tablette)
- [ ] `@media print` pour export PDF propre
- [ ] Données extraites du gold set (pas hardcodées à la main)

## Phases d'implémentation

### Phase 1 : Script d'extraction des données (~30 min)

`scripts/ml/export_dashboard_data.py` :
- Lit `ml/data/gold_set.json`
- Extrait les métriques agrégées (sources, concepts, rôles)
- Parse le git log pour la progression autoresearch
- Génère un `dashboard_data.json` ou injecte directement dans le template HTML

### Phase 2 : Structure HTML + CSS (~1h)

- Squelette des 9 sections
- Navigation sticky
- Design académique (Inter, palette sobre)
- Print stylesheet

### Phase 3 : Visualisations Plotly (~1h30)

- Carte mondiale scattergeo
- Sunburst des concepts
- Barcharts (distribution par rôle, par continent, par langue)
- Courbes de progression autoresearch
- Feature importance chart

### Phase 4 : Contenu textuel (~1h)

- Blocs de justification méthodologique
- Descriptions des alternatives
- Références bibliographiques
- Roadmap

### Phase 5 : Polish (~30 min)

- Tooltips informatifs
- Panneaux dépliables pour le détail technique
- Test cross-browser
- Test impression/PDF

## Risques

| Risque | Impact | Mitigation |
|---|---|---|
| Plotly.js trop lourd (3.5 MB) | Fichier lent à charger | Utiliser le partial build `plotly-geo.min.js` (~1.5 MB) |
| Coordonnées sources approximatives | Points mal placés sur la carte | Vérifier avec les métadonnées GBIF réelles |
| Score header 0.77 vs 0.56 dans les commits | Confusion pour les reviewers | Expliquer : 0.56 = round 1 (432 cols), 0.77 = round 2 (2231 cols enrichi) |
| Références inaccessibles (paywalls) | Reviewers ne peuvent pas vérifier | Privilégier les liens arXiv (accès libre) |

## Références internes

- Gold set : `ml/data/gold_set.json`
- Concept taxonomy : `ml/scripts/data/concept_taxonomy.py`
- Column aliases : `src/niamoto/core/imports/ml/column_aliases.yaml`
- Training scripts : `ml/scripts/train/train_{header,value,fusion}.py`
- Evaluation : `ml/scripts/eval/evaluate.py`
- Roadmap ML : `docs/plans/2026-03-14-feat-ml-detection-improvement-roadmap-plan.md`
