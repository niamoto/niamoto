---
title: "Rapport d'opportunité : Niamoto au GBIF Ebbe Nielsen Challenge 2026"
type: feat
date: 2026-03-11
---

# Rapport d'opportunité : Niamoto au GBIF Ebbe Nielsen Challenge 2026

## Résumé exécutif

Le **GBIF Ebbe Nielsen Challenge 2026** est un concours annuel doté de **20 000 €** récompensant des outils innovants exploitant les données de biodiversité du réseau GBIF. La date limite de soumission est le **26 juin 2026**.

Niamoto dispose déjà d'atouts solides pour ce challenge : un système d'enrichissement API générique connecté au GBIF, un export Darwin Core Archive complet, et une architecture plugin hautement extensible. Cependant, pour maximiser les chances de succès, il faudrait développer des fonctionnalités spécifiquement orientées vers les besoins du réseau GBIF.

**Verdict : Opportunité réaliste et atteignable**, à condition de cibler une proposition qui aligne les forces de Niamoto avec les critères de jugement du challenge.

**Orientation retenue** : Un pipeline "local-first" avec intelligence embarquée — pas de dépendance cloud pour l'IA, contrairement aux gagnants 2024-2025. L'angle différenciant est la combinaison de curation intelligente locale + génération automatique de portails web depuis les données GBIF.

---

## 1. Le Challenge en détail

### Objectif
Le challenge recherche des **outils innovants, nouveaux ou améliorés**, qui exploitent les données de biodiversité du réseau GBIF pour faire avancer la science ouverte en soutien à la recherche et aux politiques publiques.

### Soumissions acceptées
- Prototypes fonctionnels récemment développés
- Outils existants dont les capacités ont été améliorées ou étendues
- Nouvelles applications, méthodes de visualisation, workflows ou analyses
- Extensions d'outils et fonctionnalités existants

### Critères d'évaluation (pondération égale)

| Critère | Description | Implication pour Niamoto |
|---------|-------------|--------------------------|
| **Applicabilité** | Pertinence et portée suffisantes pour que les communautés GBIF puissent l'utiliser ou le construire | Niamoto doit démontrer son utilité pour différents types d'utilisateurs GBIF |
| **Bénéfice pour le réseau GBIF** | Valeur ajoutée (nouvelles données, communauté, outils, sensibilisation, politique) | Montrer comment Niamoto enrichit l'écosystème GBIF |
| **Innovation/Nouveauté** | Contribution unique ; une partie significative développée pour le challenge | Développer des fonctionnalités nouvelles, pas juste présenter l'existant |
| **Qualité d'implémentation** | Fiabilité, qualité technique, bonne documentation | Point fort de Niamoto (architecture plugin, Pydantic, tests) |
| **Ouverture et reproductibilité** | Code et contenu librement disponibles et transparents | Niamoto est open-source (OK) |

### Éligibilité
- Ouvert aux individus, équipes, entreprises et agences gouvernementales
- Soumission sur toute plateforme (GitHub, Jupyter, Dryad, FigShare, OSF...)
- Les soumissions basées largement sur du travail déjà publié ne sont **pas éligibles** → il faut du développement nouveau

### Date limite
**Vendredi 26 juin 2026, 23:59 CEST (UTC+2)** — soit environ **3,5 mois** à partir d'aujourd'hui.

---

## 2. Analyse des gagnants précédents (2019-2025)

### Tableau récapitulatif

| Année | 1er Prix | Description | Pattern |
|-------|----------|-------------|---------|
| **2025** | **BDQEmail** (Norvège) + **galaxias** (Australie) | Service email pour vérifier la qualité des données contre le standard BDQ ; Package R/Python pour convertir des données en Darwin Core Archive | Accessibilité + Standards |
| **2024** | **ChatIPT** (Norvège) | Chatbot qui nettoie les tableurs et guide la publication vers GBIF | IA + Publication |
| **2023** | **GBIF Alert** (Belgique) | Système de notification pour les nouveaux enregistrements d'occurrences sur GBIF | Monitoring + Alertes |
| **2022** | **GridDER** + **bdc** | Détection d'imprécisions dans les données de relevés grillés ; Boîte à outils de nettoyage de données intégrée (R) | Qualité des données |
| **2021** | **Bio-Dem** | Web-app explorant les relations entre disponibilité des données biodiversité et dimensions de la démocratie | Analyse croisée + Visualisation |
| **2020** | **ShinyBIOMOD** | Interface Shiny étendant biomod2 pour la modélisation d'espèces | Accessibilité + Modélisation |
| **2019** | **WhereNext** (Colombie) | Système de recommandation pour identifier les priorités d'échantillonnage | Aide à la décision |

### Patterns des gagnants — Ce que le jury valorise

1. **Réduction des barrières d'entrée** (2025 BDQEmail, 2024 ChatIPT, 2020 ShinyBIOMOD) — Rendre l'utilisation de GBIF accessible aux non-techniciens
2. **Qualité des données** (2025 BDQEmail/galaxias, 2022 GridDER/bdc) — Améliorer la fiabilité des données publiées ou consommées
3. **Publication facilitée** (2025 galaxias, 2024 ChatIPT) — Aider les chercheurs à publier leurs données vers GBIF
4. **Visualisation innovante** (2021 Bio-Dem, 2023 GBIF Alert) — Présenter les données de manière nouvelle et utile
5. **Outils open-source réutilisables** — Tous les gagnants sont open-source avec documentation
6. **Usage de l'IA/LLM** (2024-2025) — Tendance récente forte, les 2 derniers premiers prix utilisent des LLM

### Observations stratégiques

- **Rukaya Johaadien a gagné 2 années consécutives** (ChatIPT 2024, BDQEmail 2025) — le jury apprécie les itérations sur un même thème
- **Les packages R/Python sont fréquents** parmi les gagnants — le jury valorise les outils intégrables dans les workflows existants des chercheurs
- **Les outils de publication vers GBIF** sont un thème récurrent et gagnant (2024, 2025)
- **La France a gagné un 2e prix en 2025** (BAM — Biodiversity Around Me, parcs nationaux des Écrins et Cévennes) — preuve que des projets français sont compétitifs

### Architecture IA des gagnants récents — Un point faible exploitable

| Projet | Architecture IA | Dépendance | Fonctionne hors-ligne |
|--------|----------------|------------|----------------------|
| **ChatIPT** (2024) | Django → **OpenAI GPT-4o API** (cloud) | ☁️ API payante | ❌ Non |
| **BDQEmail** (2025) | Service email → **LLM cloud** pour interpréter les résultats BDQ | ☁️ API payante | ❌ Non |

**Constat clé** : Les deux gagnants IA sont **100% dépendants d'APIs cloud commerciales**. Aucun ne fonctionne sans internet, et tous deux exposent les données utilisateur à des services tiers.

**Problème de reproductibilité scientifique** : ChatIPT et BDQEmail s'appuient sur des LLM pour des **décisions de curation de données** (nettoyage, interprétation, recommandations). Or les LLM sont intrinsèquement **non-déterministes** — même input peut produire un output différent entre deux exécutions. C'est un problème fondamental pour la science ouverte :
- Un chercheur ne peut pas reproduire exactement le même résultat de nettoyage
- Le modèle cloud peut changer à tout moment (mise à jour silencieuse de GPT-4o)
- Les résultats dépendent d'un service tiers hors de contrôle de l'utilisateur

**C'est un angle d'attaque stratégique majeur pour Niamoto**, directement aligné avec le critère "Openness and repeatability".

---

## 3. Capacités actuelles de Niamoto vis-à-vis du GBIF

### Ce qui existe déjà

| Capacité | Détail | Fichier clé |
|----------|--------|-------------|
| **Enrichissement API générique** | Connexion à GBIF Species API, Tropicos, IPNI, WFO, iNaturalist, Endemia — via YAML uniquement | `src/niamoto/core/plugins/loaders/api_taxonomy_enricher.py` |
| **Export Darwin Core Archive** | DwC-A complet (occurrence.csv, meta.xml, eml.xml) compatible GBIF/IPT | `src/niamoto/core/plugins/exporters/dwc_archive_exporter.py` |
| **Transformation DwC** | Mapping complet des champs Darwin Core Occurrence v1.1 | `src/niamoto/core/plugins/transformers/formats/niamoto_to_dwc_occurrence.py` |
| **Système de plugins extensible** | 35+ transformers, auto-discovery, configuration YAML | `src/niamoto/core/plugins/` |
| **Pipeline Import → Transform → Export** | Architecture complète de traitement de données écologiques | Architecture core |
| **GUI Desktop** | Application Tauri + React pour la gestion des données | `src/niamoto/gui/` |
| **Publication statique** | Génération de sites HTML avec visualisations Plotly | `src/niamoto/publish/` |

### Ce qui manque pour le challenge

| Lacune | Impact sur la candidature |
|--------|--------------------------|
| Pas d'intégration directe GBIF API (recherche d'occurrences, téléchargement de datasets) | Limite la démonstration d'utilisation des données GBIF |
| Pas de validation BDQ (Biodiversity Data Quality) | Manque un aspect qualité des données très valorisé |
| Pas de publication automatique vers GBIF/IPT | Le pipeline s'arrête à la génération du DwC-A |
| Pas d'utilisation d'IA/LLM | Tendance forte des derniers gagnants |
| Interface limitée aux experts techniques | Le jury valorise l'accessibilité |

---

## 4. Proposition retenue : "Niamoto — Local-First Intelligence" ⭐

### Concept

Un pipeline complet de curation et publication de données de biodiversité qui fonctionne **entièrement en local** — pas de cloud, pas d'API payante, pas de fuite de données sensibles. L'intelligence est embarquée.

```
CSV/Excel/DwC-A brut
       ↓
[Détection de schéma]              ← scikit-learn classifieur (local, pas de GPU)
       ↓
[Suggestion mapping DwC]           ← fuzzy matching + heuristiques (local)
       ↓
[Validation qualité BDQ]           ← règles TDWG + anomaly detection (local)
       ↓
[Enrichissement GBIF API]          ← API quand disponible, cache local sinon
       ↓
[Transformations automatiques]     ← suggestions basées sur profil données (local)
       ↓
[Génération portail web]           ← Publication HTML statique (local)
       ↓
[Rapport narratif optionnel]       ← Small LLM via Ollama (local, optionnel)
```

### Pitch

*"Turn any biodiversity dataset into a validated, enriched, interactive web portal with species distribution models — entirely offline, with deterministic embedded intelligence. No cloud API, no data leaks, no cost. Same input, same output, every time."*

### Ce qui différencie des gagnants précédents

| | ChatIPT (2024) | BDQEmail (2025) | **Niamoto** |
|---|---|---|---|
| **Fonctionne hors-ligne** | ❌ | ❌ | ✅ |
| **Coût API IA** | Payant (OpenAI) | Payant (LLM cloud) | **Gratuit** |
| **Données restent locales** | ❌ (envoyées à OpenAI) | ❌ (envoyées par email) | ✅ |
| **Publication web incluse** | ❌ | ❌ | ✅ |
| **Extensible (plugins)** | ❌ | ❌ | ✅ |
| **Pipeline complet** | Nettoyage seul | Validation seule | **Import → Curation → Enrichissement → Publication** |

### Principe architectural : séparation déterministe / non-déterministe

C'est le cœur de la différenciation de Niamoto par rapport aux outils IA existants dans l'écosystème GBIF :

```
┌─────────────────────────────────────────────────────────────────┐
│  COUCHE DÉTERMINISTE (core)                                     │
│  → Même entrée = même sortie, toujours, partout                 │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │ Détection schéma │  │ Mapping DwC      │  │ Validation    │ │
│  │ regex + stats    │  │ fuzzy + semantic  │  │ BDQ (règles)  │ │
│  │ scikit-learn     │  │ rapidfuzz + embed │  │ déterministe  │ │
│  └──────────────────┘  └──────────────────┘  └───────────────┘ │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │ Anomalies        │  │ Résolution taxo  │  │ Transfo +     │ │
│  │ IsolationForest  │  │ GBIF Backbone    │  │ Publication   │ │
│  │ scikit-learn     │  │ cache DuckDB     │  │ HTML statique │ │
│  └──────────────────┘  └──────────────────┘  └───────────────┘ │
│                                                                 │
│  ✅ Reproductible   ✅ Explicable   ✅ Auditable               │
├─────────────────────────────────────────────────────────────────┤
│  COUCHE NON-DÉTERMINISTE (optionnelle, narrative seule)         │
│  → Ne prend AUCUNE décision sur les données                     │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ LLM local (LFM2 / Qwen3)                                │   │
│  │ • Génère des rapports narratifs lisibles                 │   │
│  │ • Explique en langage naturel les résultats déterministes│   │
│  │ • Priorise visuellement les problèmes détectés           │   │
│  │ • Ne modifie JAMAIS les données                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ⚠️ Non-déterministe mais sans impact sur les résultats         │
└─────────────────────────────────────────────────────────────────┘
```

**Règle fondamentale** : le LLM est un **rédacteur**, jamais un **décideur**. Toute opération qui modifie, valide, mappe ou transforme les données passe par la couche déterministe. Le LLM ne fait que mettre en forme les résultats en langage naturel.

**Conséquence pour la reproductibilité** :
- Deux exécutions identiques produisent **exactement** le même mapping DwC, les mêmes résultats BDQ, les mêmes anomalies détectées
- Seule la formulation du rapport narratif peut varier (et il est optionnel)
- Le rapport de qualité structuré (JSON) est toujours identique
- **Aucune dépendance à un service tiers** — le résultat ne change pas si OpenAI met à jour GPT-4o

**Comparaison directe avec les gagnants 2024-2025** :

| Aspect | ChatIPT / BDQEmail | **Niamoto** |
|--------|-------------------|------------------------|
| Décisions de nettoyage | LLM (non-déterministe) | Règles + ML (déterministe) |
| Mapping DwC | LLM (non-déterministe) | Fuzzy + embeddings (déterministe) |
| Validation qualité | LLM interprète les tests | Tests BDQ locaux (déterministe) |
| Rapport narratif | LLM (seule sortie) | LLM optionnel (narration seule) |
| Reproductibilité | ❌ Dépend du modèle cloud du jour | ✅ Identique à chaque exécution |
| Auditabilité | ❌ Boîte noire cloud | ✅ Chaque décision traçable |

### Alignement critères du challenge

| Critère | Score | Justification |
|---------|-------|---------------|
| **Applicabilité** | ✅✅ | Tout chercheur, gestionnaire d'aire protégée, université, ONG |
| **Bénéfice GBIF** | ✅✅ | Valorise les données GBIF en portails web + améliore la qualité des publications |
| **Innovation** | ✅✅ | IA locale = première dans l'écosystème GBIF ; pipeline DOI→portail = unique |
| **Qualité** | ✅✅ | Architecture plugin mature, DuckDB, Pydantic, tests |
| **Ouverture et reproductibilité** | ✅✅✅ | Open-source, aucune dépendance cloud, ET résultats déterministes — même entrée = même sortie, toujours |

### Arguments stratégiques pour le jury

1. **Reproductibilité scientifique** — Contrairement aux outils IA cloud (ChatIPT, BDQEmail), toute opération sur les données est **déterministe** : même entrée = même résultat, toujours. Le LLM est un rédacteur optionnel, jamais un décideur. Chaque décision est traçable et auditable.
2. **Souveraineté des données** — Les coordonnées d'espèces menacées sont sensibles ; pas d'envoi vers le cloud (RGPD, espèces protégées)
3. **Coût zéro et pérennité** — Pas d'API key, pas de service tiers qui peut fermer ou changer son modèle. L'outil fonctionnera encore dans 10 ans.
4. **Usage terrain** — Fonctionne dans les stations de recherche isolées, sur le terrain sans internet
5. **Accessibilité universelle** — S'adapte au hardware : du Raspberry Pi (LFM2-1.2B, < 1 Go) au workstation (Qwen3 8B)
6. **Institutions publiques** — Répond aux exigences de souveraineté numérique des organismes gouvernementaux

---

## 5. Architecture technique de l'intelligence locale

L'IA embarquée se décline en **4 niveaux de complexité croissante**, chacun indépendant :

### Niveau 1 : ML classique (scikit-learn, aucun GPU)

| Tâche | Technique | Dépendances | Taille modèle |
|-------|-----------|-------------|---------------|
| **Détection de type de colonnes** (lat/lon, taxon, date, mesure) | Classifieur entraîné sur patterns (regex + stats + distribution) | scikit-learn | ~50 Ko |
| **Détection d'anomalies** dans les coordonnées/mesures | Isolation Forest, LOF (Local Outlier Factor) | scikit-learn | Calcul à la volée |
| **Clustering d'occurrences** pour identifier les doublons | DBSCAN sur coordonnées + dates | scikit-learn | Calcul à la volée |
| **Profilage automatique des données** | Statistiques descriptives, complétude, cardinalité | pandas / ydata-profiling | Aucun modèle |

**Impact** : Fonctionne sur n'importe quel laptop, instantané sur des datasets <1M lignes. Suffit pour le "wow" technique.

### Niveau 2 : Fuzzy matching + heuristiques spécialisées biodiversité

| Tâche | Technique | Dépendances |
|-------|-----------|-------------|
| **Suggestion mapping DwC** | Fuzzy matching noms de colonnes → champs Darwin Core (rapidfuzz + règles) | rapidfuzz |
| **Résolution de noms taxonomiques** | Levenshtein + phonétique (Soundex/Metaphone) + GBIF Backbone cache local | rapidfuzz + DuckDB |
| **Suggestion de transformations** | Règles basées sur profil données (catégoriel → donut, temporel → série, spatial → carte) | Heuristiques Python |
| **Suggestion de widgets** | Mapping type de données → visualisation appropriée | Heuristiques Python |

**Impact** : Algorithmes déterministes, rapides, explicables. La résolution taxonomique nécessite un cache local du GBIF Backbone (~2 Go).

### Niveau 3 : Small Language Models locaux (optionnel, multi-backend)

Deux familles de modèles évaluées — Qwen3 (via Ollama) et **Liquid AI LFM2** (via llama.cpp) :

#### Option A : Liquid AI LFM2 ⭐ RECOMMANDÉ pour le challenge

Architecture hybride (convolutions + attention) spécifiquement optimisée pour l'inférence CPU/edge. **2x plus rapide que Qwen3 sur CPU.**

| Modèle | Params total | Params actifs | RAM | Qualité | Usage |
|--------|-------------|---------------|-----|---------|-------|
| **LFM2-1.2B** | 1.2B | 1.2B | **< 1 Go** | Correcte | Rapports simples, classification |
| **LFM2-8B-A1B** (MoE) ⭐ | 8.3B | **1.5B** | **3-4 Go** | Bonne (niveau 3-4B dense) | Rapports narratifs, extraction structurée |
| LFM2-2.6B | 2.6B | 2.6B | ~2 Go | Correcte+ | Compromis taille/qualité |
| LFM2.5-1.2B-Thinking | 1.2B | 1.2B | < 1 Go | Correcte | Raisonnement en < 1 Go |

**Avantages clés** :
- **Tool calling natif** avec tokens spéciaux (`<|tool_call_start|>` / `<|tool_call_end|>`) → structured output fiable
- **2x plus rapide que Qwen3 sur CPU** → démo plus impressionnante
- **Multilingue** : EN, FR, DE, ES, AR, ZH, JA, KO
- **GGUF disponible** → compatible llama.cpp
- **Licence LFM Open v1.0** : gratuit pour usage commercial < 10M$ CA
- LFM2-1.2B en < 1 Go → démontrable sur hardware très modeste (Raspberry Pi !)

**Limites** : pas de support Ollama natif (llama.cpp/vLLM), benchmarks MMLU inférieurs à Qwen3 (~65 vs ~72), "not recommended for knowledge-intensive tasks" (OK pour notre usage de curation structurée).

#### Option B : Qwen3 via Ollama (alternative)

| Modèle | RAM (Q4_K_M) | Qualité | Usage |
|--------|-------------|---------|-------|
| Qwen3 8B | 6-8 Go | Très bonne | Rapports détaillés, raisonnement |
| Llama 3.2 3B | 3-4 Go | Correcte | Tâches simples |
| Phi-4 14B | 10-12 Go | Excellente | Si hardware permet |

**Avantages** : écosystème Ollama mature, structured output via JSON schema, large communauté.

#### Architecture recommandée : multi-backend adaptatif

```python
class LocalLLMProvider:
    """Abstraction LLM local — s'adapte aux ressources disponibles."""

    def __init__(self, backend="auto"):
        if backend == "auto":
            if available_ram < 2_000:   # < 2 Go dispo
                self.backend = LlamaCpp("LFM2-1.2B")      # < 1 Go
            elif available_ram < 6_000: # < 6 Go dispo
                self.backend = LlamaCpp("LFM2-8B-A1B")    # ~3 Go, sweet spot
            else:
                self.backend = Ollama("qwen3:8b")          # ~5 Go, meilleure qualité
```

**Impact pour le challenge** : démontrer que l'outil **s'adapte automatiquement au hardware** — du Raspberry Pi au workstation — renforce l'argument d'accessibilité universelle.

**Impact** : Bonus impressionnant pour la démo. **Entièrement optionnel** — l'outil fonctionne sans LLM (les niveaux 1-2 suffisent).

### Niveau 4 : Modèles spécialisés biodiversité (optionnel)

| Modèle | Usage | Note |
|--------|-------|------|
| **Google SpeciesNet** (mars 2025, open-source) | Identification d'espèces sur photos de pièges photographiques | 1 295 espèces reconnues |
| **Mbaza AI** | Monitoring biodiversité hors-ligne | Alternative à SpeciesNet |

**Impact** : Pertinent si les données importées incluent des images. Angle supplémentaire pour la démo.

### Niveau 5 : Species Distribution Modeling — SDM (bonus stratégique)

**Contexte** : ShinyBIOMOD a gagné le **1er prix 2020** en rendant le SDM accessible via une interface Shiny/R autour de biomod2. Le SDM depuis des données GBIF est un cas d'usage classique et très visuel.

**L'angle Niamoto** : Ne pas concurrencer ShinyBIOMOD (outil R dédié au SDM) mais **démontrer que l'architecture plugin de Niamoto est si extensible que le SDM s'intègre comme un simple transformer** dans le pipeline existant.

```
Occurrences GBIF     Rasters environnementaux (WorldClim, SRTM)
      ↓                        ↓
[Import DuckDB]        [Import raster_stats existant]
      ↓                        ↓
      └────────┬───────────────┘
               ↓
    [SDM Transformer Plugin]
    Maxent / RandomForest via elapid ou scikit-learn
               ↓
    Carte de probabilité de présence
               ↓
    [Publication dans le portail web]
    Leaflet heatmap + statistiques
```

**Bibliothèque recommandée** : **elapid** (`pip install elapid`)
- Implémentation Python pure de Maxent (pas besoin de Java/R)
- API sklearn-compatible : `model.fit(x, y)` / `model.predict(x)`
- Gestion native des rasters via rasterio + geopandas
- Poids spatiaux, cross-validation géographique, niche enveloppes
- Léger, bien documenté, publié dans JOSS

**Fonctionnalités minimales du plugin** :
1. **Pseudo-absences automatiques** — Génération de points de background dans la zone d'étude
2. **Extraction de covariables** — Croisement occurrences × rasters (élévation, climat) via les transformers existants (raster_stats)
3. **Modèle Maxent** — Entraînement via elapid.MaxentModel() avec defaults sensibles
4. **Carte de prédiction** — Raster de probabilité de présence, exportable en GeoTIFF ou image
5. **Widget de visualisation** — Carte Leaflet avec overlay de la prédiction dans le portail web

**Ce que ça change pour la démo** :

> *"À partir d'un DOI GBIF contenant des occurrences d'une espèce, Niamoto génère automatiquement un portail web avec : rapport de qualité des données, carte des observations, ET modèle de distribution prédictive — tout en local, sans cloud."*

La carte SDM est un élément visuel extrêmement percutant dans une vidéo de démo. C'est le genre de résultat que le jury comprend en un coup d'œil.

**Effort** : 3-5 jours (le plus dur est le croisement occurrences × rasters, mais `raster_stats` existe déjà)

**Risque / Mitigation** :
- ⚠️ Nécessite des rasters environnementaux (WorldClim = ~1 Go) → prévoir un dataset de démo pré-packagé
- ⚠️ Scope creep → traiter comme Phase 5 bonus, après que le pipeline core fonctionne
- ✅ Si le temps manque, le portail web est déjà impressionnant sans SDM

### Architecture logicielle proposée

```python
# Nouveau plugin : intelligence locale
@register("local_intelligence", PluginType.TRANSFORMER)
class LocalIntelligence(TransformerPlugin):
    """Intelligence embarquée pour la curation de données biodiversité."""

    config_model = LocalIntelligenceConfig  # Pydantic

    def detect_schema(self, df) -> SchemaProfile:
        """Niveau 1 : Détection automatique des types de colonnes."""
        ...

    def suggest_dwc_mapping(self, profile: SchemaProfile) -> DwCMapping:
        """Niveau 2 : Suggestion de mapping Darwin Core."""
        ...

    def validate_bdq(self, df, mapping: DwCMapping) -> QualityReport:
        """Niveau 2 : Validation BDQ locale."""
        ...

    def detect_anomalies(self, df) -> list[Anomaly]:
        """Niveau 1 : Détection d'anomalies statistiques."""
        ...

    def generate_report(self, report: QualityReport) -> str:
        """Niveau 3 (optionnel) : Rapport narratif via LLM local."""
        ...
```

---

## 6. Recommandation stratégique révisée

### Principe directeur : Un outil, une histoire, un moment démo

> *"Colle un DOI GBIF, récupère un portail web interactif complet en 60 secondes — avec rapport de qualité, curation intelligente et modèle de distribution d'espèce, tout en local, avec des résultats reproductibles."*

### Priorisation des développements

| Phase | Semaine | Fonctionnalité | Niveau IA | Criticité |
|-------|---------|----------------|-----------|-----------|
| 1 | S1-S2 | Import GBIF occurrences (CSV/DwC-A → DuckDB) | — | 🔴 Essentielle |
| 2 | S2-S4 | Détection de schéma + suggestion mapping DwC | Niv 1-2 | 🔴 Essentielle |
| 3 | S3-S5 | Validation BDQ locale + détection d'anomalies | Niv 1-2 | 🔴 Essentielle |
| 4 | S4-S6 | Pipeline automatique données → portail web (transformations + publication) | — | 🔴 Essentielle |
| 5 | S5-S7 | Enrichissement en chaîne (GBIF API → multi-sources) avec cache local | Niv 2 | 🟡 Importante |
| 6 | S7-S8 | **SDM plugin** — Maxent via elapid, carte de prédiction dans le portail | Niv 5 | 🟢 Bonus (fort impact démo) |
| 7 | S7-S9 | Rapport narratif via LLM local (LFM2 / Ollama) | Niv 3 | 🟢 Bonus |
| 8 | S8-S10 | Interface GUI pour le workflow complet | — | 🟡 Importante |
| 9 | S10-S12 | Documentation anglaise, vidéo démo, soumission | — | 🔴 Essentielle |

**Logique de priorisation** : Les phases 1-4 forment le **MVP** (pipeline DOI → portail). Les phases 5-7 sont des bonus à fort impact qui se parallélisent. La phase 6 (SDM) est positionnée après le core car elle dépend de l'import GBIF mais apporte un élément visuel très percutant pour la démo.

### Budget temps révisé

- **Aujourd'hui** : 11 mars 2026
- **Deadline** : 26 juin 2026
- **Temps disponible** : ~15 semaines
- **Checkpoint dur** : 30 avril — si le pipeline DOI/CSV → portail ne marche pas end-to-end, réévaluer
- **Budget max** : 15-20 jours de travail effectif
- **Verdict** : Faisable si on reste focalisé sur les phases 1-4 (le cœur) et qu'on traite 5-7 comme des bonus

### Nom de soumission

Soumettre sous le nom **"Niamoto"** — capitaliser sur le projet existant et son identité. Le nom évoque déjà la biodiversité (Niamoto = nom vernaculaire du pin colonnaire de Nouvelle-Calédonie, *Araucaria columnaris*).

---

## 7. Annexe technique — Résultats de la recherche approfondie

### 7.1 Import de données GBIF — Stack technique validé

**API de téléchargement GBIF** :
- Endpoint : `POST https://api.gbif.org/v1/occurrence/download/request`
- Auth : HTTP Basic (compte GBIF gratuit)
- Formats : `SIMPLE_CSV` (recommandé, ~50 champs, plus léger) ou `DWCA` (complet avec verbatim + multimedia)
- Asynchrone : on soumet une requête, on polle le statut, on télécharge le ZIP quand prêt
- Aussi : **SQL Download API** (expérimentale) — permet des `SELECT` avec `GROUP BY` côté serveur

**Bibliothèques Python** :

| Lib | Version | Rôle |
|-----|---------|------|
| `pygbif` | 0.6.6 | Bibliothèque officielle GBIF — requêtes, téléchargements, species match |
| `python-dwca-reader` | 0.16.4 | Parser DwC-A (utile pour métadonnées, pas pour import massif) |

**Import DuckDB** — lecture directe du TSV sans parsing Python :

```python
con.execute("""
    CREATE TABLE gbif_occurrences AS
    SELECT * FROM read_csv(
        'occurrence.txt',
        delim = '\t', header = true,
        auto_detect = true, null_padding = true,
        ignore_errors = true, sample_size = -1
    )
""")
```

**Pièges identifiés** :
- Mots réservés SQL : `"order"`, `"year"`, `"class"` → guillemets doubles
- `eventDate` : peut être ISO 8601, plage (`2023-05-15/2023-05-16`), ou partiel (`2023-05`) → importer en VARCHAR
- Champs vides vs NULL : utiliser `NULL ''` dans COPY
- Colonne `issue` : flags GBIF séparés par `;` → garder en VARCHAR
- Performance : ~1-5 min pour 10M lignes sur hardware moderne

**Plugin Niamoto prévu** : `gbif_occurrence_loader` (LoaderPlugin) acceptant un download key ou un chemin ZIP local.

---

### 7.2 Intelligence locale — Stack validé et dimensionné

#### Détection de schéma (Niveau 1)

| Outil | Taille | Rôle |
|-------|--------|------|
| `csv-detective` (datagouv) | ~100 Ko | 30+ types détectés, scoring 3 couches (contenu + label + combiné) |
| `ydata-profiling` 4.18 | ~5 Mo | Profilage statistique profond, type system visions |
| Détecteur bio custom | ~200 lignes | Regex biodiversité (noms scientifiques, coordonnées, mesures) |

**Pattern** : regex + statistiques sur un échantillon de 500 valeurs → classifieur par colonne avec score de confiance.

#### Mapping Darwin Core (Niveau 2)

**Couche 1 — Fuzzy matching** (`rapidfuzz`, 2 Mo) :
- Matching des noms de colonnes contre les ~50 termes DwC principaux
- Pré-filtrage par type détecté (latitude détectée → candidats `decimalLatitude` uniquement)
- Score WRatio pour tolérer les variations de nommage

**Couche 2 — Similarité sémantique** (`all-MiniLM-L6-v2`, **22 Mo**) :
- Modèle d'embedding léger (22M paramètres, CPU, millisecondes)
- Gère les cas où les noms sont complètement différents (ex: "espece" → "scientificName", "altitude" → "minimumElevationInMeters")
- Score combiné : fuzzy × 0.6 + sémantique × 0.4

#### Résolution taxonomique locale (Niveau 2)

**GBIF Backbone Taxonomy** téléchargeable :
- Source : `https://hosted-datasets.gbif.org/datasets/backbone/backbone-current-simple.txt.gz`
- Taille : **~500 Mo compressé, ~3 Go dans DuckDB**
- Contenu : ~10 millions de noms (Catalogue of Life + sources)
- Import direct dans DuckDB avec index sur `canonicalName`, `scientificName`

**Algorithme de résolution** :
1. Match exact sur `canonicalName`
2. Si échec → extraction du genre, fuzzy match sur le genre via `rapidfuzz`
3. Filtrage des candidats par genre → fuzzy match sur le nom complet
4. Score de confiance avec seuil configurable

**Alternative** : algorithme **Taxamatch** (gold standard publié dans PLOS One) — Damerau-Levenshtein modifié + encodage phonétique pour noms latins. ~200 lignes Python.

#### Détection d'anomalies (Niveau 1)

- **Coordonnées** : `IsolationForest` (scikit-learn) — pas d'hypothèse de distribution, scale bien sur >10K records
- **Coordonnées clustered** : `LocalOutlierFactor` — sensible aux variations de densité locale
- **Règles déterministes** : coordonnées (0,0), lat/lon inversés, dates futures, mesures négatives

#### LLM local optionnel (Niveau 3) — Multi-backend

Deux familles évaluées :

| Modèle | Architecture | RAM | Vitesse CPU | Structured output | Intérêt |
|--------|-------------|-----|-------------|-------------------|---------|
| **LFM2-8B-A1B** ⭐ | MoE hybride (Liquid AI) | 3-4 Go | 2x Qwen3 | Tool calling natif | Sweet spot : léger + rapide + qualité |
| **LFM2-1.2B** | Dense hybride (Liquid AI) | < 1 Go | 3x Qwen3 | Tool calling natif | Ultra-léger, démo sur hardware modeste |
| Qwen3 8B | Transformer (Ollama) | 6-8 Go | Référence | JSON schema Ollama | Meilleure qualité brute |

**Recommandation** : LFM2-8B-A1B comme modèle par défaut (3 Go, 2x plus rapide, tool calling natif), Qwen3 8B en fallback si hardware permet. Architecture multi-backend adaptative selon les ressources disponibles.

**Point clé** : le LLM n'est qu'une couche de synthèse optionnelle — les statistiques sont pré-calculées par scikit-learn, le LLM les met en forme narrative. L'outil fonctionne parfaitement sans LLM.

#### Budget disque total

| Composant | Taille | Obligatoire |
|-----------|--------|-------------|
| GBIF Backbone (DuckDB) | ~3 Go | Oui (résolution taxonomique) |
| Embedding all-MiniLM-L6-v2 | 22 Mo | Oui (mapping DwC) |
| Frontières pays (Natural Earth) | ~15 Mo | Oui (validation spatiale) |
| **LFM2-8B-A1B** (GGUF Q4) | **~3 Go** | Non (LLM optionnel, recommandé) |
| LFM2-1.2B (GGUF) | < 1 Go | Non (LLM alternatif ultra-léger) |
| Qwen3 8B via Ollama | ~5 Go | Non (LLM alternatif) |
| SpeciesNet (Google) | ~2 Go | Non (optionnel, pièges photo) |
| **Total minimal (sans LLM)** | **~3.1 Go** | |
| **Total avec LFM2-8B-A1B** | **~6.1 Go** | |
| **Total complet** | **~11 Go** | |

---

### 7.3 Validation BDQ — Opportunité majeure identifiée

**Découverte clé : Il n'existe AUCUNE bibliothèque Python implémentant les tests BDQ TDWG.**

Les seules implémentations sont en Java (FilteredPush/Kurator). BDQEmail (gagnant 2025) est un service, pas une bibliothèque réutilisable. **Être le premier à proposer une implémentation Python BDQ est un différenciant fort.**

#### Les tests BDQ en bref

- **~100-160 tests** en 4 domaines (NAME, SPACE, TIME, OTHER)
- **4 types** : VALIDATION (pass/fail), AMENDMENT (correction proposée), MEASURE (métrique), ISSUE (flag)
- **Spécifications machine-readable** disponibles : `TG2_tests.csv` et `TG2_tests.ttl` sur GitHub tdwg/bdq

#### Les 12 tests Tier-1 (60% des problèmes réels)

| # | Test | Domaine | Données externes |
|---|------|---------|------------------|
| 1 | `COORDINATES_NOTZERO` | SPACE | Aucune |
| 2 | `DECIMALLATITUDE_INRANGE` | SPACE | Aucune |
| 3 | `DECIMALLONGITUDE_INRANGE` | SPACE | Aucune |
| 4 | `COUNTRYCOUNTRYCODE_CONSISTENT` | SPACE | Frontières pays (15 Mo) |
| 5 | `COORDINATES_COUNTRYCENTROID` | SPACE | Centroïdes pays (1 Ko) |
| 6 | `EVENTDATE_INRANGE` | TIME | Aucune |
| 7 | `DAY_INRANGE` | TIME | Aucune |
| 8 | `MONTH_INRANGE` | TIME | Aucune |
| 9 | `EVENT_CONSISTENT` | TIME | Aucune |
| 10 | `OCCURRENCEID_NOTEMPTY` | OTHER | Aucune |
| 11 | `BASISOFRECORD_NOTSTANDARD` | OTHER | Vocabulaire (enum) |
| 12 | `SCIENTIFICNAME_NOTEMPTY` | NAME | Aucune |

**8 des 12 tests Tier-1 ne nécessitent aucune donnée externe** → implémentables en quelques heures.

#### Roadmap d'implémentation

| Phase | Effort | Tests | Données externes |
|-------|--------|-------|------------------|
| TIME + OTHER | 2-3 jours | ~25 tests | Aucune (pure Python) |
| SPACE | 3-5 jours | ~20 tests | Natural Earth GeoJSON (15 Mo) |
| NAME (basique) | 1-2 jours | ~10 tests | Aucune (complétude seule) |
| NAME (avancé) | 3-5 jours | ~15 tests | GBIF Backbone (3 Go) |
| **Total** | **~10-15 jours** | **~70 tests** | |

---

## 8. Analyse SWOT (révisée, post-recherche)

### Forces (Strengths)
- Architecture plugin mature et extensible (35+ transformers)
- Enrichissement API multi-sources déjà fonctionnel (GBIF, Tropicos, IPNI, WFO, iNaturalist)
- Export Darwin Core Archive complet et testé
- DuckDB performant pour le traitement local de gros volumes
- GUI desktop existant (Tauri + React) avec mode offline
- Système de publication HTML avec 5 thèmes et visualisations Plotly
- **Philosophie local-first déjà ancrée** (DuckDB, offline support, polices locales)

### Faiblesses (Weaknesses)
- Pas encore d'import de données GBIF (seulement enrichissement via API)
- Interface technique pour la configuration YAML
- Projet relativement jeune, pas encore de communauté d'utilisateurs internationale
- Documentation principalement en français → traduction anglaise nécessaire pour le challenge
- Un seul développeur → capacité limitée

### Opportunités (Opportunities)
- **L'IA locale est un océan bleu** dans l'écosystème GBIF — aucun gagnant n'a exploré cette voie
- **Souveraineté des données** = argument politique fort (institutions publiques, RGPD, espèces sensibles)
- Pipeline "données brutes → site web" sans cloud = angle peu exploré
- La France est compétitive (BAM, 2e prix 2025)
- Les modèles légers (scikit-learn, Qwen 2.5-7B via Ollama) sont matures et performants en 2026
- Le jury valorise les outils réutilisables et extensibles

### Menaces (Threats)
- Délai serré (15 semaines, ~15-20 jours effectifs)
- Règle de nouveauté : "a significant portion developed specifically for the challenge"
- Risque de scope creep si on essaie de tout faire (IA + portail + GUI + doc)
- Concurrence invisible — on ne sait pas ce que d'autres équipes préparent
- Si le jury a une "fatigue IA" après 2024-2025, l'angle local pourrait être perçu comme "encore de l'IA"

---

## 9. Éléments de soumission à préparer

### Format de soumission
1. **Repository GitHub** avec README complet
2. **Vidéo de démonstration** (2-3 minutes)
3. **Description écrite** expliquant :
   - L'innovation et l'impact du système
   - Les objectifs du développement
   - Les outils utilisés
   - Comment les données GBIF sont utilisées
4. **Exemples reproductibles** (Jupyter notebooks, jeux de données test)

### Points à mettre en avant
- **Généricité** : fonctionne pour tout type de données de biodiversité, pas spécifique à un territoire
- **Pipeline complet** : de la donnée brute au portail web
- **Architecture ouverte** : système de plugins permettant l'extension par la communauté
- **Multi-API** : pas seulement GBIF mais enrichissement croisé avec d'autres sources
- **Performance** : DuckDB pour le traitement rapide de gros volumes

---

## 10. Conclusion

### Le challenge est-il réaliste pour Niamoto ?

**Oui**, à condition de :

1. **Rester focalisé** — un outil, une histoire, un moment démo. Pas de scope creep.
2. **Miser sur l'IA locale comme différenciant** — c'est l'angle que personne n'a exploré
3. **Prioriser le pipeline DOI/CSV → portail** — c'est le "wow" visuel pour la vidéo démo
4. **Checkpoint dur au 30 avril** — pipeline end-to-end fonctionnel ou réévaluation
5. **Soigner la présentation** — vidéo démo percutante, documentation anglaise, exemples reproductibles

### ROI au-delà du challenge

Même sans gagner, les fonctionnalités développées :
- Renforcent Niamoto comme plateforme de données écologiques
- Ajoutent la détection de schéma et le mapping DwC intelligent (utile pour tous les utilisateurs)
- Ouvrent Niamoto à un public international via la compatibilité GBIF
- Positionnent Niamoto dans l'écosystème GBIF (visibilité, communauté)
- Les fonctionnalités IA locale bénéficient à toute la plateforme (suggestions de transformations, widgets)

### Prochaine étape recommandée

1. Valider l'orientation "Local-First Intelligence" et le budget temps (15-20 jours)
2. Lancer la Phase 1 (import GBIF occurrences CSV/DwC-A → DuckDB)
3. Prototyper la détection de schéma (Niveau 1 IA) sur des données GBIF réelles

---

## Sources

- [2026 Ebbe Nielsen Challenge — Appel à soumissions](https://www.gbif.org/news/3DyM3tK5wgYipqyaHwG2c2/2026-ebbe-nielsen-challenge-open-for-submissions)
- [Règles officielles 2025 (référence)](https://www.gbif.org/article/3OKkJRBx4w73RidYK0ZkFw/official-rules-2025-gbif-ebbe-nielsen-challenge)
- [Gagnants précédents](https://www.gbif.org/composition/6m87h1AVkXkeCUvAApsoQ4/ebbe-nielsen-challenge-previous-winners)
- [Gagnants 2025 — BDQEmail + galaxias](https://www.gbif.org/news/2LugQxJfG2kCzjiJocXzVZ/winners-from-norway-and-australia-share-first-place-in-the-2025-ebbe-nielsen-challenge)
- [Gagnant 2024 — ChatIPT](https://www.gbif.org/news/6aw2VFiEHYlqb48w86uKSf/chatipt-system-wins-the-2024-ebbe-nielsen-challenge)
- [Gagnants 2023 — GBIF Alert](https://www.gbif.org/news/EQgUzZ4YA75BSeLs1naI9/belgian-built-gbif-alert-system-wins-the-2023-ebbe-nielsen-challenge)
- [Gagnants 2022 — GridDER + bdc](https://www.gbif.org/news/6J94JrRZtDCPhUZMMiTALq/gridder-and-bdc-share-top-honors-in-2022-gbif-ebbe-nielsen-challenge)
- [Gagnant 2021 — Bio-Dem](https://www.gbif.org/news/QWLleXqOFkDOGR4Oxaj94/bio-dem-wins-2021-gbif-ebbe-nielsen-challenge)
- [Gagnant 2020 — ShinyBIOMOD](https://www.gbif.org/news/AcT155L4KYZ5RxsfDnGGt/shinybiomod-wins-2020-gbif-ebbe-nielsen-challenge)
- [Page principale Ebbe Nielsen Challenge](https://www.gbif.org/ebbe)

### Sources techniques (recherche approfondie)

- [GBIF API Downloads Documentation](https://techdocs.gbif.org/en/data-use/api-downloads)
- [GBIF Download Formats](https://techdocs.gbif.org/en/data-use/download-formats)
- [GBIF SQL Downloads (expérimental)](https://techdocs.gbif.org/en/data-use/api-sql-downloads)
- [GBIF Species Match API](https://techdocs.gbif.org/en/openapi/v1/species)
- [pygbif — bibliothèque Python officielle GBIF](https://github.com/gbif/pygbif)
- [python-dwca-reader](https://github.com/BelgianBiodiversityPlatform/python-dwca-reader)
- [Darwin Core Text Guide (spécification)](https://dwc.tdwg.org/text/)
- [DuckDB CSV Import](https://duckdb.org/docs/stable/data/csv/overview)
- [GBIF Backbone Taxonomy (téléchargement)](https://hosted-datasets.gbif.org/datasets/backbone/)
- [TDWG BDQ Interest Group](https://github.com/tdwg/bdq)
- [TG2 Tests CSV (spécifications machine-readable)](https://github.com/tdwg/bdq/blob/master/tg2/core/TG2_tests.csv)
- [FilteredPush — implémentation Java BDQ](https://github.com/FilteredPush/event_date_qc)
- [GBIF Occurrence Issues & Flags](https://techdocs.gbif.org/en/data-use/occurrence-issues-and-flags)
- [csv-detective (datagouv)](https://github.com/datagouv/csv-detective)
- [ydata-profiling](https://github.com/ydataai/ydata-profiling)
- [rapidfuzz](https://rapidfuzz.github.io/RapidFuzz/)
- [sentence-transformers/all-MiniLM-L6-v2 (22 Mo)](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- [Google SpeciesNet / cameratrapai](https://github.com/google/cameratrapai)
- [ChatIPT (GitHub)](https://github.com/gbif-norway/ChatIPT)
- [Taxamatch algorithm (PLOS One)](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0107510)
- [bdc R Package — Biodiversity Data Cleaning](https://brunobrr.github.io/bdc/)
- [Liquid AI — LFM2 Blog Post](https://www.liquid.ai/blog/liquid-foundation-models-v2-our-second-series-of-generative-ai-models)
- [LFM2-1.2B sur HuggingFace](https://huggingface.co/LiquidAI/LFM2-1.2B)
- [LFM2-8B-A1B sur HuggingFace](https://huggingface.co/LiquidAI/LFM2-8B-A1B)
- [LFM2 Technical Report (arXiv)](https://arxiv.org/html/2511.23404v1)
- [elapid — Python SDM / Maxent (sklearn-compatible)](https://github.com/earth-chris/elapid)
- [ShinyBIOMOD — 1er prix 2020](https://www.gbif.org/news/AcT155L4KYZ5RxsfDnGGt/shinybiomod-wins-2020-gbif-ebbe-nielsen-challenge)
- [scikit-learn Species Distribution Modeling example](https://scikit-learn.org/stable/auto_examples/applications/plot_species_distribution_modeling.html)
