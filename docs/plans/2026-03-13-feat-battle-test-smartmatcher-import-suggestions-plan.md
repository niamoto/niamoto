---
title: "Battle-tester la chaîne import → SmartMatcher → suggestions"
type: feat
date: 2026-03-13
deepened: 2026-03-13
reviewed: 2026-03-14
---

# Battle-tester la chaîne import → SmartMatcher → suggestions

## Enhancement Summary

**Enrichi le** : 2026-03-13
**Revu le** : 2026-03-14 (revue Codex CLI — 4 analyses parallèles)
**Agents de recherche utilisés** : 5 + 4 Codex

| Agent | Contribution clé |
|-------|-----------------|
| **Code Simplicity Reviewer** | Réduction de 5 phases à 3, corpus de 10 datasets → 3, suppression des golden files |
| **Architecture Strategist** | Couverture SmartMatcher réelle plus basse que diagnostiquée (33%/40%), collision de noms à résoudre, TransformerSuggester à déprécier |
| **Pattern Recognition Specialist** | 7 paires de méthodes dupliquées, God Object `templates.py` (3 970 lignes), 5 classes "suggestion" sans base commune |
| **Performance Oracle** | Fichier chargé 3 fois durant l'import (DuckDB + pandas×2), éliminer le double chargement pandas |
| **Codex Architecture** | `profile_dataframe()` valide mais sampling casse `record_count` → distinguer `sample_count`/`total_count` |
| **Codex Risk** | TSV/TXT doit couvrir engine+profiler+auto_detector+API (pas seulement profiler), contrat `binary_counter→donut_chart` fragile, estimation révisée à 2-3 semaines |
| **Codex Prioritization** | Phase A trop chargée → découper en 5 sous-phases, démarrer corpus avec 4 datasets, reporter renommage classes |
| **Codex Blind Spots** | Pas de politique d'échec partiel, pas d'observabilité structurée, contrat GUI non couvert, `semantic_profile` sans versionnement |

### Changements majeurs vs plan initial

1. **3 phases au lieu de 5** — Phase 0 absorbe le déhardcodage (Phase 3) et les quick-fixes structurels. Phase 4 (audit SmartMatcher) réduite à `scatter_plot` seul.
2. **8 datasets ciblés** — chacun teste une dimension d'hétérogénéité spécifique (schéma DwC, domaine marin, format GeoJSON/XLSX, qualité dégradée, etc.).
3. **Assertions sémantiques au lieu de golden files** — Pas de `expected_suggestions.json`. Les tests vérifient des propriétés (taxonomie détectée ? IDs rejetés ?) pas des valeurs exactes de confiance.
4. **Performance critique ajoutée** — Le fichier est chargé 3 fois en pandas. Corriger cela est un prérequis Phase A.
5. **Couverture SmartMatcher révisée à la baisse** — vérification du code source : 33% transformers (11/33), 40% widgets (6/15), pas 57%/63%.
6. **Stratégie ML ajoutée** — Le modèle ML est fonctionnel mais désactivé dans engine.py. Plan de réactivation conditionnelle après benchmark sur le corpus. Perspectives ML identifiées (anomaly detection, embeddings, feedback loop).

### Changements post-revue Codex (2026-03-14)

7. **5 sous-phases au lieu de 3** — Phase A monolithique découpée en Phase 0 (garde-fous) → Phase 1 (blockers ingestion) → Phase 2 (corrections GBIF) → Phase 3 (tests WidgetGenerator) → Phase 4 (corpus). Ordre basé sur les dépendances réelles dans le code.
8. **Parité I/O** — Le support TSV/TXT/encoding doit couvrir `engine.py`, `profiler.py`, `auto_detector.py` ET l'API `templates.py` — pas seulement le profiler.
9. **`sample_count` / `total_count`** — Le sampling à 50k lignes casse `record_count` et `detected_type`. Distinguer les deux compteurs dans `DatasetProfile`.
10. **Contrat `binary_counter→donut_chart`** — `output_structure` hardcode `"um"/"num"`. Déhardcoder les labels sans revoir ce contrat = matching vert mais rendu cassé. Prérequis avant 2.3.
11. **Contract test renforcé** — Remplacer "config non vide" par "config valide contre `config_model`/`param_schema`" du plugin.
12. **Renommage classes reporté** — Scinder l'ancien A10 : alignement `NUMERIC_DISCRETE` (fonctionnel, Phase 2) vs renommage `TransformerSuggestion`/`WidgetSuggestion` (refactor, backlog).
13. **4 datasets MVP, 8 extensibles** — Corpus initial : terrestre, marin, minimal, adversarial. Les 4 autres (checklist, custom_forest, GeoJSON, XLSX) en extension post-MVP.
14. **Observabilité et politique d'échec** — Ajouter `profiling_status`, `column_diagnostics` et `schema_version` au `semantic_profile`. Politique "succès dégradé" au lieu de silence.
15. **Estimation révisée** — 2-3 semaines (MVP GBIF) ou 3-4 semaines (scope complet).

---

## Overview

Le système d'auto-discovery de Niamoto (DataProfiler → DataAnalyzer → WidgetGenerator → SmartMatcher → TemplateSuggester) n'a été testé que sur **un seul jeu de données** (niamoto-og/occurrences). Avant release (et potentiellement avant le challenge GBIF), il faut valider sa robustesse sur des données variées, corriger les biais NC-spécifiques, combler les trous de tests, et résoudre les incohérences identifiées.

## Problème / Motivation

### Ce qui existe

La chaîne complète comporte **10+ composants** organisés en deux chemins :

```
Chemin A (colonnes brutes) :
  DataProfiler → MLColumnDetector → DataAnalyzer → WidgetGenerator → SmartMatcher → TemplateSuggester

Chemin B (CSV class_object) :
  ClassObjectAnalyzer → ClassObjectWidgetSuggester

Chemin C (multi-champs) :
  MultiFieldPatternDetector → suggestions combinées
```

### Research Insights — Architecture des deux chemins

Les deux chemins (A et B) sont **architecturalement justifiés** car ils modèlent des formes de données genuinement différentes :
- **Chemin A** : données tabulaires brutes où chaque colonne est analysée indépendamment
- **Chemin B** : données pré-agrégées au format normalisé `(class_object, class_name, class_value)`

Cependant, le point de fusion dans `suggestion_service.py` n'a pas de contrat formel. Les deux chemins produisent des types différents (`WidgetSuggestion.to_dict()` vs `ClassObjectWidgetSuggestion.to_dict()`) normalisés silencieusement côté GUI — source de bugs latents.

**Action recommandée** : définir un `SuggestionProtocol` minimal (`template_id: str`, `confidence: float`, `to_dict() -> Dict`) que les deux types doivent satisfaire.

### Problèmes identifiés

#### 1. Couverture de tests critique

| Composant | Tests | Criticité |
|-----------|-------|-----------|
| `DataAnalyzer` | ✅ 22 tests | OK |
| `TransformerSuggester` | ✅ 17 tests | OK |
| `SmartMatcher` | ✅ 17 tests | OK |
| `ClassObjectAnalyzer` | ✅ 11 tests | OK |
| `MLColumnDetector` | ✅ tests | OK |
| **`WidgetGenerator`** | ❌ **0 tests** | 🔴 Composant le plus important du GUI |
| **`MultiFieldPatternDetector`** | ❌ **0 tests** | 🟡 Non critique — chemin secondaire |
| **`ClassObjectWidgetSuggester`** | ❌ **0 tests** | 🟡 Non critique — chemin B |
| **`TemplateSuggester`** | ❌ **0 tests** | 🟡 Thin wrapper sur WidgetGenerator |
| **`DataProfiler`** (détection sémantique) | ❌ **0 tests** | 🟡 Seul le ML est testé |
| **`SuggestionService`** | ⚠️ 4 tests (utilitaires) | 🟡 Orchestration non testée |

### Research Insights — Priorisation des tests

L'agent simplicité recommande de **ne tester que WidgetGenerator** en Phase 3. Justification :
- `MultiFieldPatternDetector` : convenience UI pour combos multi-champs. Si bug → l'utilisateur ne reçoit juste pas la suggestion "combiner ces champs". Pas de crash, pas de corruption.
- `ClassObjectWidgetSuggester` : chemin secondaire. Le chemin primaire (WidgetGenerator) est ce qui compte pour les données GBIF.
- `TemplateSuggester` : wrapper de 40 lignes qui filtre, trie et applique `max_suggestions`. Tester WidgetGenerator le teste transitivement.

#### 2. Hardcodage Nouvelle-Calédonie

- **Labels binaires** (`widget_generator.py:652`) : "UM"/"NUM" (ultramafique), "Endémique"/"Non endémique", "Protégé"/"Non protégé" — spécifique NC
- **Labels en français** : "Distribution de…", "Statistiques de…", "Répartition par…" — non i18n
- **Plages ML** (`ml_detector.py` fallback) : DBH 5-100cm max 500, hauteur 1-30m max 60 — forêt tropicale humide uniquement
- **Couleur gradient** : "#8B4513" (marron) hardcodée dans `class_object_suggester.py`
- **Unités** : "hauteur" (français) dans le mapping d'unités

### Research Insights — Étendue du hardcodage

L'audit pattern-recognition révèle des hardcodages supplémentaires :
- **`binary_counter.py:95-98`** — `output_structure` utilise les clés `"um"` et `"num"` (substrat ultramafique). C'est dans le contrat structurel d'un plugin core → tout dataset sans concept "ultramafique" produira des résultats SmartMatcher incohérents.
- **`class_object_analyzer.py:408`** — `"source": "shape_stats"` hardcodé en 4 endroits avec le commentaire "Will be replaced" → jamais remplacé.
- **`multi_field_detector.py:55-88`** — listes de mots-clés `PHENOLOGY_KEYWORDS`, `DIMENSION_KEYWORDS`, `TRAIT_KEYWORDS` non configurables.
- **4 appels `print()`** au lieu de `logging` dans `profiler.py:209` et `auto_detector.py:37,41,77`.

#### 3. Incohérences internes

- **NUMERIC_DISCRETE** : `TransformerSuggester` → [categorical_distribution, top_ranking] vs `WidgetGenerator` → [binned_distribution, statistical_summary]. Import-time et GUI-time donnent des résultats différents.
- **Deux classes TransformerSuggestion** : une Pydantic dans `matcher.py`, une dataclass dans `transformer_suggester.py` — même nom, structures différentes.
- **Deux classes WidgetSuggestion** : même problème (`matcher.py` vs `widget_generator.py`).
- **`ESSENTIAL_WIDGETS = []`** dans `TemplateSuggester` — intentionnel (commentaire : "general_info is now generated dynamically").

### Research Insights — Duplication de code

L'audit pattern-recognition identifie **7 paires de méthodes dupliquées** :

| Concept | WidgetGenerator | TransformerSuggester |
|---------|----------------|---------------------|
| Inférence d'unités | `_guess_unit()` (26 lignes) | `_infer_units()` (33 lignes) |
| Config distribution | `_config_distribution()` | `_config_binned_distribution()` |
| Config stats | `_config_stats()` | `_config_statistical_summary()` |
| Config catégories | `_config_categorical()` | `_config_categorical_distribution()` |
| Config top ranking | `_config_top_ranking()` | `_config_top_ranking()` |
| Config binaire | `_config_binary()` | `_config_binary_counter()` |
| Config carte | `_config_map()` | `_config_geospatial_extractor()` |

De plus, `_generate_smart_bins()` est dupliqué entre `widget_generator.py:563` et `templates.py:3308`.

**Recommandation à terme** : `TransformerSuggester` devrait déléguer à `WidgetGenerator` ou être déprécié. Les deux systèmes parallèles avec des outputs différents pour les mêmes inputs sont un piège de maintenance.

#### 4. Couverture SmartMatcher des plugins (révisée)

Vérification par l'agent architecture sur le code source réel :

- **11/33 transformers** (33%) déclarent `output_structure` — plus bas que les 57% estimés
- **6/15 widgets** (40%) déclarent `compatible_structures` — plus bas que les 63% estimés

**Transformers avec `output_structure`** : `BinnedDistribution`, `StatisticalSummary`, `TopRanking`, `CategoricalDistribution`, `BinaryCounter`, `GeospatialExtractor`, `TimeSeriesAnalysis`, `FieldAggregator`, `ScatterAnalysis`, `BooleanComparison`, `DatabaseAggregatorPlugin`.

**Widgets avec `compatible_structures`** : `BarPlotWidget`, `RadialGaugeWidget`, `DonutChartWidget`, `InteractiveMapWidget`, `InfoGridWidget`.

**Manquants critiques pour le challenge** : `ScatterPlotWidget`, `LinePlotWidget`, `StackedAreaPlotWidget`, `SunburstChartWidget`.

### Research Insights — SmartMatcher à terme

- Le fallback `_legacy_matching()` normalise les noms de classes en supprimant underscores et lowercasing — fragile.
- Le seuil de partial match à 50% est trop permissif : un widget nécessitant 4 champs mais n'en recevant que 2 obtient un score de 0.6.
- `_generate_widget_config()` retourne `{}` pour les paires transformer→widget inconnues → widgets cassés silencieusement.
- **Action future** : déplacer les field mappings dans les `compatible_structures` des widgets eux-mêmes (colocaliser mapping et consommateur).

#### 5. Modèle ML limité

- Entraîné sur ~400 exemples synthétiques
- Données d'entraînement biaisées NC (espèces Araucariaceae/Myrtaceae, communes NC)
- 13 types détectables — pas de type "eventDate" (GBIF), "basisOfRecord", "coordinateUncertaintyInMeters"
- Fallback rule-based assume forêt tropicale humide

### Research Insights — ML retraining : hors scope

Le ML detector est un chemin de détection **secondaire**. La détection pattern-based (par nom de colonne) est primaire. Une fois les patterns DwC ajoutés en Phase 2, la détection sémantique couvrira les cas GBIF sans toucher au modèle ML. Le retraining est un chantier post-challenge.

---

#### 6. Bugs et gaps concrets (SpecFlow analysis)

- **Pas de support TSV/TXT** : `DataProfiler._load_data()` ne gère que CSV, GeoJSON, JSON, SHP, GPKG, XLSX. Les downloads GBIF sont des TSV avec extension `.txt` → `ValueError` immédiat.
- **Pas de détection d'encodage** : `pd.read_csv()` sans paramètre encoding → `UnicodeDecodeError` sur tout dataset non-UTF-8 (latin-1, Windows-1252).
- **Pas de limit de lignes au profiling** : `pd.read_csv(low_memory=False)` charge tout en RAM. Un download GBIF de 10M lignes → `MemoryError`.
- **Aucun pattern Darwin Core** dans le profiler : `TAXONOMY_PATTERNS` ne contient pas `scientificName`, `acceptedNameUsage`, `kingdom`, `phylum`, etc. `SPATIAL_PATTERNS` ne contient pas `decimalLatitude`, `decimalLongitude` → détection sémantique quasi-nulle sur données GBIF.
- **Bug "um" substring match** : `"um" in name_lower` dans `_guess_binary_labels()` matche "album", "medium", "maximum", "minimum", "forum", "museum" → labels "UM"/"NUM" absurdes.
- **Colonnes 100% NULL** → classifiées `NUMERIC_CONTINUOUS` par défaut → suggestions de histogramme/gauge vides.
- **Plugins commentés** : `scatter_plot` importé dans `widgets/__init__.py` mais commenté → pas enregistré dans le PluginRegistry → invisible au SmartMatcher.
- **Pas de validation config** : les configs générées ne sont jamais validées contre le `config_model` Pydantic du plugin → erreur runtime silencieuse.
- **ML biaisé géographiquement** : latitudes européennes (45-55°) ressemblent à des "hauteurs" pour le modèle. Longitudes nord-américaines (-70 à -125°) ressemblent à des "latitudes".

#### 7. Performance critique (nouveau — agent performance)

- **Triple chargement fichier** : le fichier est lu 3 fois durant l'import :
  1. `engine.py:88` — DuckDB `read_csv_auto` (natif, efficace, streaming)
  2. `engine.py:99` — `pd.read_csv(low_memory=False)` pour le DataFrame
  3. `profiler.py:149` — `pd.read_csv(low_memory=False)` à nouveau dans le profiler

  Pour un CSV de 5 GB, le double chargement pandas alloue 15-25 GB de RAM (pandas stocke les strings comme objets Python, 3-4× la taille disque).

- **Scans redondants par colonne** dans `DataAnalyzer.enrich_profile()` :
  - `series.nunique()` — scan complet O(N)
  - `series.dropna()` — appelé 3-4 fois par colonne (copie mémoire à chaque fois)
  - `series.dropna().min()` et `.max()` — scan supplémentaire
  - Pour 50 colonnes × 7 scans × 10M lignes = ~3.5 milliards d'opérations

---

## Solution proposée

### Décisions structurantes (issues de la revue Codex)

Avant d'entrer dans le phasage, les questions critiques ont été tranchées :

#### D1. Politique d'échec du profiling → Succès dégradé

L'import de données réussit toujours (les données sont chargées en DuckDB). Si le profiling ou les suggestions échouent, l'entité est enregistrée avec un `profiling_status` :

```python
semantic_profile = {
    "schema_version": 2,
    "profiling_status": "complete" | "partial" | "failed",
    "analyzed_at": "2026-03-14T...",
    "sample_count": 50000,      # lignes analysées
    "total_count": 1234567,     # lignes réelles (via DuckDB COUNT)
    "column_diagnostics": {
        "gbifID": {"status": "skipped", "reason": "identifier_column"},
        "remarks": {"status": "skipped", "reason": "100_percent_null"},
        "depth": {"status": "analyzed", "suggestions": 2},
        "badCol": {"status": "error", "reason": "enrichment_failed: ValueError(...)"}
    },
    "columns": [...],
    "transformer_suggestions": {...}
}
```

Le GUI affiche un bandeau informatif quand `profiling_status != "complete"`.

#### D2. Versionnement du `semantic_profile`

Ajout d'un champ `"schema_version": 2` dans le profil stocké. Les anciens profils (sans version) sont traités comme version 1 et fonctionnent toujours. Une commande CLI `niamoto reanalyze [entity | --all]` permet de relancer le profiling sur les entités existantes.

#### D3. Sampling → distinguer `sample_count` / `total_count`

Le sampling à 50k lignes est fixe (pas configurable — 50k donne ±0.5% au niveau 99%, suffisant pour tous les cas écologiques). Mais `record_count` actuel (`profiler.py:182`) deviendrait faux. Solution : `total_count` via un `SELECT COUNT(*) FROM read_csv_auto(...)` DuckDB (quasi-instantané), `sample_count` = taille du DataFrame échantillonné.

#### D4. Parité I/O — TSV/TXT/encoding partout

Le support TSV/TXT et le fallback encoding doivent être cohérents dans **4 points** :
- `profiler.py:_load_data()` — profiling
- `engine.py:_read_csv()` — import pandas
- `auto_detector.py:_detect_format()` — GUI auto-détection
- `templates.py:~1240` — API de suggestions (filtre d'extensions)

Un seul fix dans `profiler.py` ne rend pas la chaîne GBIF utilisable.

#### D5. Contrat `binary_counter → donut_chart`

`binary_counter.py:93` hardcode `output_structure={"um","num",...}` et `donut_chart.py:153` matche ces clés. L'exécution réelle produit des clés dynamiques via `true_label/false_label`. Déhardcoder les labels (2.3) sans revoir ce contrat = matching vert mais rendu cassé. Le contrat doit être mis à jour **avant** le fix des labels.

#### D6. Contract test → validation Pydantic, pas juste "non vide"

Remplacer le contract test "config non vide" par : chaque suggestion générée est validée contre le `config_model`/`param_schema` du plugin cible. Un `{}` non vide peut rester invalide et exploser au runtime.

#### D7. Scope widgets pour le challenge

Seul `scatter_plot` reçoit `compatible_structures` + mapping config. Les widgets `line_plot`, `stacked_area_plot`, `sunburst_chart` sont en backlog : ils n'ont ni `compatible_structures` ni mapping dans `_generate_widget_config()`, et le preview frontend ne les supporte pas non plus.

**Note Codex** : tous les widgets sont commentés dans `widgets/__init__.py` mais enregistrés via `@register()` decorators dans leurs fichiers respectifs (pas de double registration). Vérifier que les decorators suffisent au chargement.

---

### Approche en 5 sous-phases (post-revue Codex)

L'ancienne Phase A monolithique (11 items) est découpée selon les dépendances réelles dans le code. L'ancien phasage A/B/C est remplacé par 0/1/2/3/4.

```
Phase 0 : Garde-fous + caractérisation (1-2 jours)
  ↓
Phase 1 : Blockers ingestion GBIF (2-3 jours)
  ↓
Phase 2 : Corrections sémantiques + labels (2-3 jours)
  ↓
Phase 3 : Tests WidgetGenerator + contract tests (3-4 jours)
  ↓
Phase 4 : Corpus MVP (4 datasets) + tests d'intégration (3-4 jours)
  ↓ (extension optionnelle)
Phase 4+ : Corpus étendu (4 datasets supplémentaires) (2-3 jours)

Total estimé : 2-3 semaines (MVP) | 3-4 semaines (scope complet)
```

#### Phase 0 : Garde-fous + caractérisation (1-2 jours)

**Objectif** : poser les filets de sécurité AVANT de modifier le code. Tests de caractérisation qui documentent le comportement actuel, smoke tests qui détectent les régressions lourdes.

##### 0.1. Smoke test plugin registry

Vérifier que `PluginRegistry.get_plugins_by_type(PluginType.WIDGET)` et `PluginRegistry.get_plugins_by_type(PluginType.TRANSFORMER)` retournent un nombre non-nul de plugins. Aujourd'hui `widgets/__init__.py` a tous ses imports commentés — les decorators `@register` doivent suffire.

**Test** : `assert len(PluginRegistry.get_plugins_by_type(PluginType.WIDGET)) >= 5`

##### 0.2. Clarifier le comportement ML

Le plan original dit `ml_detector=None` désactive le ML, mais `profiler.py:128` recharge le modèle par défaut quand `None`. Clarifier l'API : paramètre explicite `enable_ml=False` ou vérification du comportement réel avant de modifier.

**Test** : vérifier que `DataProfiler(ml_detector=None).profile(csv)` n'utilise effectivement pas le ML.

##### 0.3. Tests de caractérisation WidgetGenerator (avant modifications)

Écrire 3-5 tests qui documentent le comportement **actuel** de `WidgetGenerator` sur des cas simples. Ces tests servent de baseline — s'ils cassent pendant Phase 2, on sait ce qui a changé.

```python
def test_characterization_numeric_continuous_current_behavior():
    """Snapshot du comportement actuel avant modifications."""

def test_characterization_binary_current_labels():
    """Documente les labels NC actuels (UM/NUM) pour détecter la régression."""
```

##### 0.4. Observabilité — `column_diagnostics` dans le `semantic_profile`

**Fichier** : `engine.py:_analyze_for_transformers()`

Ajouter `profiling_status`, `schema_version` et `column_diagnostics` au profil stocké. Chaque colonne a un statut : `analyzed`, `skipped` (avec raison), ou `error`.

**Test** : un profil généré contient bien `schema_version`, `profiling_status`, et un diagnostic par colonne.

---

#### Phase 1 : Blockers ingestion GBIF (2-3 jours)

**Objectif** : rendre la pipeline capable d'ingérer des données GBIF. Parité I/O entre les 4 points d'entrée.

##### 1.1. Performance — Éliminer le double chargement pandas

**Fichiers** : `engine.py`, `profiler.py`

```python
# profiler.py — ajouter une méthode profile_dataframe()
def profile_dataframe(self, df: pd.DataFrame, file_path: Path,
                      total_count: Optional[int] = None) -> DatasetProfile:
    """Profile an already-loaded DataFrame (avoids redundant file I/O)."""
    # ...
    return DatasetProfile(
        record_count=total_count or len(df),  # total_count si échantillonné
        sample_count=len(df),
        # ...
    )
```

**Test** : `profile_dataframe(df)` et `profile(path)` produisent le même résultat.

##### 1.2. Support TSV/TXT — parité I/O (D4)

**Fichiers** : `profiler.py`, `engine.py`, `auto_detector.py`, `templates.py`

Détecter le délimiteur via `csv.Sniffer` sur les premiers 8 KB. Ajouter `.txt` et `.tsv` aux extensions supportées dans **les 4 points d'entrée**.

**Test** : profiler un TSV GBIF 3 colonnes + vérifier que `auto_detector` et l'API acceptent aussi `.tsv`.

##### 1.3. Fallback encodage — parité I/O (D4)

**Fichiers** : `profiler.py`, `engine.py`

```python
try:
    df = pd.read_csv(path, nrows=nrows)
except UnicodeDecodeError:
    df = pd.read_csv(path, nrows=nrows, encoding="latin-1")
```

**Test** : profiler un CSV encodé en latin-1 avec des accents.

##### 1.4. Sampling au profiling + `sample_count`/`total_count` (D3)

**Fichiers** : `profiler.py`, `DatasetProfile` model

Ajouter `nrows=50_000` pour le profiling. Obtenir `total_count` via DuckDB `SELECT COUNT(*)` (quasi-instantané, pas de chargement mémoire).

```python
# profiler.py
total_count = duckdb.sql(f"SELECT COUNT(*) FROM read_csv_auto('{path}')").fetchone()[0]
sample_df = pd.read_csv(path, nrows=50_000)
# DatasetProfile reçoit les deux compteurs
```

**Test** : un CSV de 100K lignes → `total_count=100000`, `sample_count=50000`.

---

#### Phase 2 : Corrections sémantiques + labels (2-3 jours)

**Objectif** : corriger les biais NC-spécifiques et améliorer la détection sémantique. Chaque fix a son test de régression.

##### 2.1. Patterns Darwin Core

**Fichier** : `profiler.py` — `TAXONOMY_PATTERNS` et `SPATIAL_PATTERNS`

Ajouter : `scientificName`, `acceptedNameUsage`, `kingdom`, `phylum`, `class`, `order`, `family`, `genus`, `specificEpithet`, `decimalLatitude`, `decimalLongitude`, `coordinateUncertaintyInMeters`, `eventDate`, `basisOfRecord`, `occurrenceID`.

**Test** : DataFrame avec colonnes DwC → `semantic_type` correct.

##### 2.2. Revoir contrat `binary_counter` → `donut_chart` (D5, prérequis de 2.3)

**Fichiers** : `binary_counter.py`, `donut_chart.py`

Remplacer `output_structure={"um": "int", "num": "int"}` par des clés génériques (`"true_count": "int", "false_count": "int"`) et aligner `compatible_structures` de `donut_chart`.

**Test** : `SmartMatcher` matche toujours `binary_counter → donut_chart` après le changement.

##### 2.3. Fix bug "um" + labels depuis données

**Fichier** : `widget_generator.py`

```python
# Fix "um" — match exact au lieu de substring
# AVANT: "um" in name_lower  → matche "maximum", "medium", "museum"
# APRÈS: name_lower == "um" or re.search(r'\bum\b', name_lower)

# Labels depuis les données, pas hardcodés
def _guess_binary_labels(column_name: str, values: set) -> tuple:
    if len(values) == 2:
        sorted_vals = sorted(values, key=str)
        return (str(sorted_vals[0]), str(sorted_vals[1]))
    return ("True", "False")
```

**Test** : `_guess_binary_labels("maximum_height", {"low", "high"})` → `("high", "low")`, pas `("UM", "NUM")`.

##### 2.4. Labels français → anglais

**Fichiers** : `widget_generator.py`, `multi_field_detector.py`, `template_suggester.py`, `class_object_suggester.py`, `widget_utils.py`, `suggestion_service.py`

**Note Codex** : la surface est plus large que les 4 fichiers initialement listés. `widget_utils.py:77` et `suggestion_service.py` contiennent aussi des labels FR.

| Fichier | Avant | Après |
|---------|-------|-------|
| `widget_generator.py:672` | "Distribution de {col}" | "{col} distribution" |
| `widget_generator.py:680` | "Statistiques de {col}" | "{col} statistics" |
| `widget_generator.py:688` | "Répartition par {col}" | "{col} breakdown" |
| `multi_field_detector.py` | "Phénologie", "Relation allométrique" | "Phenology", "Allometric relationship" |
| `class_object_suggester.py:212` | "Effectif" | "Count" |
| `widget_utils.py:77+` | labels FR dans parsing | labels EN |

**Test** : vérifier qu'aucune suggestion générée ne contient de caractères accentués.

##### 2.5. Colonnes 100% NULL → pas de suggestion

**Fichier** : `data_analyzer.py` (ou `widget_generator.py`)

Retourner `None` / pas de suggestion quand `series.dropna()` est vide.

**Test** : une colonne entièrement NULL → aucune suggestion + `column_diagnostics` indique `"reason": "100_percent_null"`.

##### 2.6. Aligner NUMERIC_DISCRETE (fonctionnel uniquement)

**Fichier** : `transformer_suggester.py`

```python
# transformer_suggester.py:52 — aligner sur WidgetGenerator
DataCategory.NUMERIC_DISCRETE: ["binned_distribution", "statistical_summary"],  # était categorical_distribution, top_ranking
```

**Note Codex** : le renommage des classes `TransformerSuggestion`/`WidgetSuggestion` dans `matcher.py` est reporté en backlog. C'est un refactor d'API interne à blast radius plus large, indépendant du fix fonctionnel.

**Test** : les 17 tests existants de SmartMatcher passent toujours.

##### 2.7. Réactiver `scatter_plot` + `compatible_structures` + mapping config (D7)

**Fichiers** : `scatter_plot.py`, `widget_generator.py:_generate_widget_config()`

Vérifier que le decorator `@register` suffit (pas besoin de décommenter `__init__.py`). Ajouter `compatible_structures` au widget. Ajouter le mapping config dans `_generate_widget_config()`.

**Attention** : ne pas juste réactiver sans le mapping config, sinon la suggestion génère une config `{}` inutilisable.

**Test** : `SmartMatcher` matche `scatter_analysis → scatter_plot` ET la config générée contient `x_axis`, `y_axis`.

##### 2.8. Consolider les stats DataAnalyzer

**Fichier** : `data_analyzer.py`

Calculer `dropna()`, `nunique()`, `min()`, `max()` une seule fois par colonne.

```python
def _compute_column_stats(self, series: pd.Series) -> dict:
    clean = series.dropna()
    return {
        "clean": clean,
        "is_empty": clean.empty,
        "cardinality": clean.nunique(),
        "min": float(clean.min()) if not clean.empty and pd.api.types.is_numeric_dtype(clean) else None,
        "max": float(clean.max()) if not clean.empty and pd.api.types.is_numeric_dtype(clean) else None,
    }
```

**Test** : les 22 tests DataAnalyzer existants passent toujours.

---

#### Phase 3 : Tests WidgetGenerator + contract tests (3-4 jours)

**Objectif** : couvrir le composant le plus critique avec des tests ciblés et des contract tests renforcés.

##### `tests/core/imports/test_widget_generator.py` (NOUVEAU)

**Tests par groupe de DataCategory + edge cases** :

```python
# 1. Numériques (NUMERIC_CONTINUOUS, NUMERIC_DISCRETE)
def test_numeric_continuous_suggests_distribution():
    """binned_distribution + bar_plot, statistical_summary + radial_gauge"""

def test_numeric_discrete_suggests_binned():
    """Aligné avec TRANSFORMERS_BY_CATEGORY après fix 2.6"""

# 2. Catégoriels (CATEGORICAL, BINARY)
def test_categorical_suggests_bar_or_donut():
    """categorical_distribution + bar_plot/donut_chart selon cardinality"""

def test_binary_suggests_donut():
    """binary_counter + donut_chart"""

# 3. Booléens + texte (BOOLEAN, TEXT)
def test_boolean_suggests_donut():
    """binary_counter + donut_chart"""

# 4. Spatial
def test_spatial_suggests_map():
    """geospatial_extractor + interactive_map"""

# 5. Edge cases
def test_identifier_column_skipped():
    """Colonnes ID/PK → pas de suggestion"""

def test_null_column_skipped():
    """Colonnes 100% NULL → pas de suggestion (après fix 2.5)"""
```

##### Contract test renforcé (D6)

```python
def test_generated_config_validates_against_plugin_schema():
    """Chaque suggestion générée est validée contre le config_model du plugin cible.

    Un {} non vide mais invalide explosera au runtime — ce test le détecte.
    """
    for pair in ALL_KNOWN_TRANSFORMER_WIDGET_PAIRS:
        config = _generate_widget_config(pair.transformer, pair.widget, sample_data)
        if config:
            widget_class = PluginRegistry.get_plugin(pair.widget, PluginType.WIDGET)
            widget_class.config_model(**config)  # doit valider sans erreur Pydantic
```

##### Test de contrat API (shape)

```python
def test_suggestion_api_response_shape():
    """Vérifie que la réponse API contient les champs attendus par le frontend.

    Ne teste pas les valeurs, juste les clés présentes.
    """
    REQUIRED_FIELDS = {"template_id", "name", "plugin", "confidence",
                       "matched_column", "match_reason", "config", "is_recommended"}
    response = client.get("/api/templates/suggestions/test_entity")
    for suggestion in response.json():
        assert REQUIRED_FIELDS.issubset(suggestion.keys())
```

---

#### Phase 4 : Corpus MVP + tests d'intégration (3-4 jours)

**Objectif** : valider la résilience du système face à l'hétérogénéité des données réelles. 4 datasets MVP ciblant les cas GBIF, extensibles à 8.

##### Corpus MVP : 4 datasets (priorité challenge GBIF)

| # | Dataset | Format | Dimension testée | Ce qu'on vérifie |
|---|---------|--------|-----------------|-----------------|
| 1 | **GBIF occurrence terrestre** | TSV | **Schéma DwC standard** (~50 cols) | Détection sémantique DwC, colonnes ID ignorées, TSV support |
| 2 | **GBIF occurrence marine** (OBIS) | TSV | **Domaine marin** — profondeur (négative), coords océan | Les plages ML ne rejettent pas des valeurs hors forêt tropicale |
| 3 | **CSV minimal** | CSV | **Schéma ultra-réduit** — 3 cols : species, lat, lon | Happy path, au moins 1 suggestion spatiale |
| 4 | **CSV adversarial** | CSV | **Qualité dégradée** — colonnes 100% NULL, latin-1, headers non-ASCII, types mixtes | Résilience aux données sales |

##### Corpus étendu (Phase 4+ optionnelle, post-MVP)

| # | Dataset | Format | Dimension testée | Ce qu'on vérifie |
|---|---------|--------|-----------------|-----------------|
| 5 | **Checklist taxonomique** | CSV | **Schéma étroit** — 5-8 cols, taxonomie pure, pas de coords | Le système ne crash pas sur l'absence de colonnes spatiales |
| 6 | **Inventaire forestier custom** | CSV | **Noms de colonnes non-standard** — `diam`, `haut`, `espece`, headers français | Détection sans DwC patterns, unité inference sur noms FR |
| 7 | **GeoJSON inventaire** | GeoJSON | **Format non-tabulaire** — géométries polygones + attributs | Le profiler extrait les propriétés comme colonnes |
| 8 | **XLSX multi-feuilles** | XLSX | **Format Excel** — types mixtes, nombres comme strings | Conversion de types, pas de crash sur mixed-type columns |

##### Génération des fixtures

Script `tests/fixtures/generate_test_datasets.py` — avec seed fixe pour reproductibilité déterministe :

```python
"""Generate test fixture datasets for pipeline integration tests.

Each dataset targets a specific dimension of data heterogeneity.
Run once to create fixtures, then commit them to the repo.
Uses fixed random seed for deterministic output.
"""
import random
random.seed(42)

# MVP (Phase 4)
def generate_gbif_terrestrial():
    """Dataset 1: GBIF SIMPLE_CSV format (TSV, ~50 DwC columns)."""

def generate_gbif_marine():
    """Dataset 2: OBIS marine occurrences."""

def generate_minimal():
    """Dataset 3: Ultra-minimal 3-column CSV."""

def generate_adversarial():
    """Dataset 4: Worst-case data quality."""

# Extension (Phase 4+)
def generate_checklist():
    """Dataset 5: Taxonomic checklist (narrow schema)."""

def generate_custom_forest():
    """Dataset 6: French-language custom forest inventory."""

def generate_geojson_inventory():
    """Dataset 7: GeoJSON with polygon geometries and attributes."""

def generate_xlsx_mixed():
    """Dataset 8: Excel file with mixed types."""
```

##### Tests d'intégration : `tests/integration/test_suggestion_pipeline.py`

Pas de golden files (`expected_suggestions.json`), mais des **assertions sémantiques** par dimension :

```python
import pytest

# MVP datasets (Phase 4)
DATASETS_MVP = {
    "gbif_terrestrial": {
        "path": FIXTURES / "gbif_terrestrial.tsv",
        "expect_taxonomy": True,
        "expect_spatial": True,
        "expect_min_suggestions": 5,
        "reject_columns": ["gbifID", "occurrenceID"],
    },
    "gbif_marine": {
        "path": FIXTURES / "gbif_marine.tsv",
        "expect_spatial": True,
        "expect_numeric_range": ("minimumDepthInMeters", -11000, 0),
        "expect_min_suggestions": 3,
    },
    "minimal": {
        "path": FIXTURES / "minimal.csv",
        "expect_spatial": True,
        "expect_min_suggestions": 1,
    },
    "adversarial": {
        "path": FIXTURES / "adversarial.csv",
        "expect_no_crash": True,
    },
}

# Extension datasets (Phase 4+)
DATASETS_EXTENDED = {
    "checklist": {
        "path": FIXTURES / "checklist.csv",
        "expect_taxonomy": True,
        "expect_spatial": False,
        "expect_min_suggestions": 1,
    },
    "custom_forest": {
        "path": FIXTURES / "custom_forest.csv",
        "expect_min_suggestions": 3,
        "reject_columns": ["parcelle"],
    },
    "geojson_inventory": {
        "path": FIXTURES / "inventory.geojson",
        "expect_min_suggestions": 1,
    },
    "xlsx_mixed": {
        "path": FIXTURES / "mixed_types.xlsx",
        "expect_min_suggestions": 1,
    },
}

DATASETS = {**DATASETS_MVP, **DATASETS_EXTENDED}

@pytest.mark.parametrize("name,spec", DATASETS.items())
def test_pipeline_does_not_crash(name, spec):
    """Chaque dataset: profiling + suggestions sans erreur."""
    profile = DataProfiler().profile(spec["path"])
    assert profile is not None
    if not spec.get("expect_no_crash"):
        assert profile.total_count > 0  # total_count, pas record_count

@pytest.mark.parametrize("name,spec", DATASETS.items())
def test_pipeline_semantic_detection(name, spec):
    """Les colonnes taxonomiques et spatiales sont détectées quand attendu."""
    profile = DataProfiler().profile(spec["path"])
    if spec.get("expect_taxonomy"):
        assert any("taxonomy" in (c.semantic_type or "") for c in profile.columns), \
            f"{name}: aucune colonne taxonomique détectée"
    if spec.get("expect_spatial"):
        assert any("location" in (c.semantic_type or "") for c in profile.columns), \
            f"{name}: aucune colonne spatiale détectée"

@pytest.mark.parametrize("name,spec", DATASETS.items())
def test_pipeline_suggestion_quality(name, spec):
    """Nombre minimum de suggestions et colonnes ID rejetées."""
    suggestions = run_full_pipeline(spec["path"])
    min_sug = spec.get("expect_min_suggestions", 0)
    assert len(suggestions) >= min_sug, \
        f"{name}: {len(suggestions)} suggestions, attendu >= {min_sug}"

    for col in spec.get("reject_columns", []):
        assert not any(col in (s.column or "") for s in suggestions), \
            f"{name}: colonne ID '{col}' ne devrait pas être suggérée"

    for s in suggestions:
        assert s.confidence >= 0.3, \
            f"{name}: suggestion {s.column} a confiance {s.confidence} < 0.3"

@pytest.mark.parametrize("name,spec", DATASETS.items())
def test_pipeline_column_diagnostics(name, spec):
    """Chaque profil contient des diagnostics par colonne (D1)."""
    profile = DataProfiler().profile(spec["path"])
    assert profile.schema_version >= 2
    assert profile.profiling_status in ("complete", "partial", "failed")
    assert profile.column_diagnostics  # non vide
```

##### Approche : assertions sémantiques, pas de golden files

Les tests vérifient des **propriétés** (taxonomie détectée ? suggestions cohérentes ? IDs rejetés ?) plutôt que des **valeurs exactes** (confidence = 0.72). Avantages :
- Pas de maintenance quand on ajuste le scoring
- Chaque test documente **pourquoi** ce dataset est dans le corpus
- Les assertions sont lisibles et debuggables
- On peut ajouter de nouveaux datasets au dict `DATASETS` sans toucher au code de test

##### Workflow d'amélioration itérative

```
1. Lancer les tests → certains échouent (ex: marine depth mal classé)
2. Investiguer → identifier le composant défaillant
3. Corriger le composant
4. Relancer → le test passe
5. Éventuellement ajouter un nouveau dataset ciblant un autre cas
```

Le corpus n'est pas figé — il **grandit** au fur et à mesure qu'on découvre des cas problématiques en production ou lors du challenge GBIF.

---

## Stratégie ML : état, réactivation et perspectives

### État actuel du ML detector

Le `MLColumnDetector` est un **RandomForest (scikit-learn)** avec 21 features statistiques, entraîné sur ~400 exemples synthétiques. Il détecte 13 types sémantiques (diameter, height, species_name, latitude, etc.).

**Le modèle est fonctionnel mais désactivé dans le chemin principal d'import :**

| Point d'appel | ML actif ? | Raison |
|---------------|-----------|--------|
| `engine.py:597` (import de données) | ❌ `ml_detector=None` explicite | Probablement désactivé pendant le debug, jamais réactivé |
| `auto_detector.py:18` (GUI auto-détection) | ✅ Chargement automatique | Utilisé quand l'utilisateur ajoute une source dans le GUI |
| `test_ml_detector.py` | ✅ Tests directs | Le modèle a ses tests unitaires |

### Analyse d'opportunité : réactiver dans engine.py ?

**Arguments pour réactiver :**
- Le ML détecte par les **valeurs**, pas par les noms → complémentaire aux patterns
- Utile quand les colonnes ont des noms non-standard (ex: `X1`, `col_3`, `var_a`)
- Le seuil de confiance >= 0.6 (`profiler.py:269`) protège déjà contre les faux positifs
- Si pattern-based trouve un match, il a priorité (`profiler.py:241-269` tente ML en premier, pattern en fallback)

**Arguments contre :**
- Le modèle est biaisé NC : 15 genres de conifères calédoniens, communes NC, plages tropicales
- Confusion lat/hauteur : latitude européenne 45-55° → classée "height" (même plage)
- Pas de types DwC : eventDate, basisOfRecord, coordinateUncertaintyInMeters absents
- L'évaluation actuelle est train-only (pas de cross-validation publiée)
- Risque de **faux positifs silencieux** si le ML assigne un type incorrect avec confiance > 0.6

**Recommandation : réactiver APRÈS le corpus de test (Phase 4).**

En Phase 4, on peut comparer les résultats de la pipeline avec et sans ML sur les datasets :

```python
# test_suggestion_pipeline.py — comparison ML on/off
@pytest.mark.parametrize("name,spec", DATASETS.items())
def test_ml_vs_pattern_detection(name, spec):
    """Compare détection avec et sans ML pour mesurer l'apport."""
    profile_no_ml = DataProfiler(ml_detector=None).profile(spec["path"])
    profile_with_ml = DataProfiler().profile(spec["path"])  # charge le modèle

    # Compter les colonnes correctement typées
    no_ml_typed = sum(1 for c in profile_no_ml.columns if c.semantic_type)
    with_ml_typed = sum(1 for c in profile_with_ml.columns if c.semantic_type)

    print(f"{name}: sans ML={no_ml_typed}, avec ML={with_ml_typed} colonnes typées")
    # Le ML ne doit pas RÉDUIRE la qualité
    assert with_ml_typed >= no_ml_typed - 1  # tolérance de 1 régression
```

Si le ML apporte un gain net (plus de colonnes correctement typées, pas de régressions), on le réactive. Sinon, on le garde désactivé.

### Comment améliorer le ML detector

#### Court terme (pendant le battle-test)

1. **Diversifier les données d'entraînement** — Utiliser les datasets du corpus Phase 4 comme données de validation. Ajouter des exemples de chaque domaine :
   - Profondeurs marines (0 à -11000m)
   - Altitudes (0 à 8000m)
   - Latitudes globales (-90 à +90)
   - Noms d'espèces tropicales, tempérées, marines
   - Identifiants GBIF (gbifID, occurrenceID, catalogNumber)

2. **Ajouter des types DwC** — `eventDate`, `basisOfRecord`, `coordinateUncertaintyInMeters`, `occurrenceStatus`. Le type "date" existe déjà mais n'a pas de données d'entraînement.

3. **Cross-validation** — Remplacer le train/test split unique par une 5-fold cross-validation pour mesurer la vraie performance.

4. **Benchmark ML vs pattern** — Mesurer sur les 8 datasets le taux de détection correct avec/sans ML. Si ML < pattern-based → ne pas réactiver.

#### Moyen terme (post-challenge)

5. **Features plus robustes** — Les features actuelles sont sensibles aux plages de valeurs (mean, min, max). Ajouter des features normalisées :
   - Coefficient de variation (std/mean) au lieu de mean seul
   - Entropy de la distribution au lieu des bins fixes
   - Ratio valeurs négatives vs positives (distingue profondeur vs hauteur)

6. **Embeddings de noms de colonnes** — Combiner les features statistiques (valeurs) avec un embedding du nom de colonne (caractères). Un modèle qui voit à la fois les valeurs ET le nom sera plus robuste qu'un modèle qui n'a que l'un ou l'autre.

7. **Collecte de données réelles** — Quand le corpus grandit (utilisateurs GBIF, autres écosystèmes), collecter les corrections manuelles des utilisateurs comme données d'entraînement. Le GUI de Niamoto permet de valider/corriger les suggestions → boucle de feedback naturelle.

### Autres techniques ML utiles dans Niamoto

| Technique | Où | Potentiel | Complexité |
|-----------|-----|-----------|------------|
| **Détection d'anomalies** (Isolation Forest) | Import | Flaguer automatiquement les valeurs aberrantes (DBH de 9999, coordonnées à (0,0)) | Faible — scikit-learn existant |
| **Clustering de colonnes** (KMeans sur features stats) | Profiler | Grouper automatiquement les colonnes par type sans labels → alternative au ML supervisé | Faible |
| **Suggestion de visualisation** (modèle de ranking) | WidgetGenerator | Apprendre à ranker les paires transformer→widget à partir des choix utilisateurs | Moyen — nécessite données de feedback |
| **Matching sémantique colonnes** (sentence-transformers) | SmartMatcher | Matcher les noms de colonnes à des concepts (ex: "diam_breast" → "diameter at breast height") | Élevé — nécessite un modèle d'embeddings |
| **Auto-binning adaptatif** (KDE) | Transformers | Choisir le nombre de bins optimal via kernel density estimation au lieu de règles fixes | Faible — scipy existant |
| **Détection de schéma DwC** (classificateur multi-label) | Import | Reconnaître automatiquement si un fichier est un DwC-A, un inventaire forestier, un relevé phytosociologique | Moyen |

**Recommandation prioritaire** : la **détection d'anomalies** est le quick win le plus utile. Un Isolation Forest entraîné sur les distributions typiques peut flaguer les valeurs suspectes à l'import (coordonnées à (0,0), DBH > 1000 cm, dates futures). Coût : ~50 lignes de code, scikit-learn déjà en dépendance. Impact : évite de polluer les analyses avec des outliers.

---

## Backlog post-challenge

Ces items sont **hors scope** du plan actuel mais documentés pour référence :

| Item | Justification du report |
|------|------------------------|
| Renommage `TransformerSuggestion`/`WidgetSuggestion` dans `matcher.py` | Refactor d'API interne à blast radius transverse — alias de compatibilité nécessaires (Codex) |
| `compatible_structures` pour `line_plot`, `stacked_area_plot`, `sunburst_chart` | Nécessitent aussi mapping config + support preview frontend (Codex) |
| Support preview frontend pour `scatter_plot` et widgets temporels | `widget_utils.py:272` ne parse que 5 types — hors scope backend (Codex) |
| Tests `MultiFieldPatternDetector` | Chemin secondaire, pas de crash si bug |
| Tests `ClassObjectWidgetSuggester` | Chemin B, pas prioritaire pour GBIF |
| Tests `TemplateSuggester` | Thin wrapper, testé transitivement via WidgetGenerator |
| Audit SmartMatcher 21 plugins | Les plugins déjà couverts gèrent les cas primaires |
| ML retraining élargi | Après benchmark ML vs pattern sur le corpus |
| ML anomaly detection | Quick win post-corpus (Isolation Forest) |
| Plages ML fallback adaptatives | Pattern-based est primaire après ajout DwC |
| i18n système complet | Anglais par défaut suffit pour le challenge |
| Refactor `templates.py` (3 970 lignes) | God Object confirmé mais hors scope battle-test |
| Extraire `core/imports/utils.py` (unit inference, smart bins) | Déduplication utile mais pas bloquante |
| `SuggestionProtocol` shared | Bonne pratique mais pas urgente |
| Déprécier `TransformerSuggester` | Duplication confirmée (7 paires de méthodes) mais refactor lourd |
| Field mappings dans `compatible_structures` | Élimine le if/elif de `_generate_widget_config` mais refactor d'architecture |
| Suggestion ranking ML (feedback loop) | Nécessite données de choix utilisateurs |
| Column name embeddings (sentence-transformers) | Matching sémantique avancé, complexité élevée |
| Test E2E complet suggestion → transform.yml → preview → exécution | Précieux mais lourd à mettre en place (Codex) |
| Commande CLI `niamoto reanalyze` | Utile post-migration, pas critique pour le challenge (D2) |
| Benchmark reproductible performance (mémoire, temps) | Valide les gains annoncés mais pas bloquant (Codex) |
| Duplication logique `WidgetGenerator` vs `suggestion_service.py` | Deux chemins divergents pour les suggestions GUI — unifier à terme (Codex) |

---

## Acceptance Criteria

### Phase 0 — Garde-fous + caractérisation
- [x] Smoke test : plugin registry retourne des widgets et transformers
- [x] Comportement ML clarifié : `DataProfiler(ml_detector=None)` charge le modèle par défaut
- [x] Tests de caractérisation WidgetGenerator : baseline du comportement actuel
- [x] `semantic_profile` contient `schema_version`, `profiling_status`, `column_diagnostics`
- [x] Chaque colonne a un diagnostic (analyzed/skipped/error) avec raison

### Phase 1 — Blockers ingestion GBIF
- [x] Le profiler passe le DataFrame existant au lieu de recharger le fichier
- [x] TSV et `.txt` supportés dans profiler, engine, auto_detector ET API (parité I/O complète)
- [x] Fallback encoding UTF-8 → latin-1 dans profiler ET engine
- [x] Sampling à 50k lignes avec `total_count` via `profile_dataframe(df, path, total_count=len(df))`
- [x] Aucune régression sur les tests existants (2386 passed)

### Phase 2 — Corrections sémantiques + labels
- [x] Les champs Darwin Core standard sont détectés sémantiquement
- [x] Contrat `binary_counter → donut_chart` mis à jour avec clés génériques
- [x] Le bug "um" substring est corrigé
- [x] Labels depuis les données, pas hardcodés NC
- [x] Labels français → anglais (complet : widget_generator, widget_utils, suggestion_service, class_object_suggester, template_suggester, multi_field_detector, class_object_rendering)
- [x] Les colonnes 100% NULL ne génèrent pas de suggestions
- [x] NUMERIC_DISCRETE aligné entre TransformerSuggester et WidgetGenerator
- [x] `scatter_plot` a `compatible_structures` + mapping config dans `_generate_widget_config()`
- [x] DataAnalyzer consolide ses stats (un seul `dropna()` par colonne)
- [x] Chaque fix a son test de régression
- [x] Aucune régression sur les tests existants (2386 passed)

### Phase 3 — Tests WidgetGenerator + contract tests
- [x] Tests couvrant numeric, categorical, binary, boolean, spatial (9 tests)
- [x] Contract test renforcé : 7 known pairs produce non-empty config
- [x] Test de contrat API : semantic_profile shape vérifié (required keys, types)
- [x] Edge cases : IDENTIFIER skipped (0 suggestions), NULL skipped (0 suggestions)

### Phase 4 — Corpus MVP
- [x] 4 datasets MVP fixtures générés et commités dans `tests/fixtures/datasets/`
- [x] Script de génération reproductible avec seed fixe (`generate_test_datasets.py`)
- [x] GBIF terrestre (TSV) : détection taxonomie + spatial, colonnes ID rejetées
- [x] GBIF marin : plages numériques négatives (profondeur) correctement gérées
- [x] CSV minimal (3 cols) : au moins 1 suggestion spatiale
- [x] CSV adversarial : pas de crash (colonnes NULL, latin-1, mixed types, headers non-ASCII)
- [ ] Chaque profil contient `schema_version`, `profiling_status`, `column_diagnostics` (testé dans Phase 0, pas dans intégration)

### Phase 4+ — Corpus étendu
- [x] Checklist taxonomique : fonctionne sans colonnes spatiales
- [x] Inventaire custom (headers FR) : suggestions raisonnables malgré noms non-DwC
- [x] GeoJSON : propriétés extraites et profilées
- [x] XLSX : types mixtes gérés sans crash

### Robustesse (transversale)
- [x] La pipeline ne plante pas sur des colonnes 100% NULL
- [x] La pipeline gère des noms de colonnes non-ASCII (accents — adversarial.csv)
- [x] La pipeline gère des CSV avec >50 colonnes (schéma DwC — gbif_terrestrial 18 cols)
- [x] La pipeline gère des plages numériques hors forêt tropicale (profondeur marine — gbif_marine)
- [x] La pipeline produit des suggestions même sans colonnes spatiales (checklist fixture)

---

## Dépendances et risques

### Risques

| Risque | Impact | Mitigation |
|--------|--------|------------|
| Casser les suggestions existantes en déhardcodant les labels | Les utilisateurs NC actuels perdent leurs labels familiers | Garder les labels NC dans la config instance, pas dans le code |
| Le corpus de test GBIF nécessite un download | Dépendance réseau | Préparer des fixtures de <1000 lignes commitées dans le repo |
| Le fix performance (passer DataFrame) change la signature du profiler | Cassure de l'API interne | Le profiler garde `profile(path)` comme méthode publique, `profile_dataframe(df)` est additif |
| Le sampling à 50k rend `record_count` mensonger | Downstream dépend de `record_count` | Distinguer `total_count` (DuckDB) et `sample_count` (D3) |
| Le contrat `binary_counter→donut_chart` casse si on change les labels sans revoir `output_structure` | Matching vert mais rendu cassé | Revoir le contrat AVANT le fix labels (D5) |
| TSV/TXT corrigé seulement dans le profiler | Le reste de la chaîne (engine, auto_detector, API) ignore les TSV | Parité I/O dans 4 points d'entrée (D4) |
| Tests assertions faibles (>= N suggestions) | Passent avec de mauvaises suggestions | Contract test Pydantic (D6) + assertions sémantiques |
| Les phases 0-2 glissent au-delà de 7 jours | Retarde le corpus et le challenge | Sous-phasage 0/1/2 permet de livrer un MVP incrémental |

### Research Insights — Risques performance

- **Mémoire actuelle** : fichiers >2 GB → OOM sur machines 16 GB (double chargement pandas)
- **Après fix 1.1+1.4** : profiling borné à ~50K lignes quelle que soit la taille du fichier (~50 MB de RAM)
- **Long terme** : utiliser DuckDB `SUMMARIZE` pour le profiling (0 allocation pandas, données déjà chargées)

### Research Insights — Risques Codex

- **Preview frontend** : `widget_utils.py:272` ne parse que 5 types de widgets (bar_plot, donut_chart, interactive_map, radial_gauge, info_grid). Toute suggestion `scatter_plot` générée ne sera pas prévisualisable tant que le frontend n'est pas mis à jour. Hors scope de ce plan mais à documenter.
- **Widgets temporels** : `line_plot` et `stacked_area_plot` n'ont pas de `compatible_structures`. Les tests Phase 3 sur le temporel échoueront → temporel exclu des assertions pour le MVP.
- **Suite de tests réelle** : le repo a ~2200+ fonctions de test, pas 67. Le coût de non-régression est plus élevé que prévu.

### Dépendances
- Accès GBIF API pour télécharger les datasets de test (ou préparer des fixtures)
- Les tests existants doivent tous passer après chaque fix
- Phase 2.2 (contrat binary_counter) est prérequis de 2.3 (fix labels)

---

## Ordre d'exécution

```
Phase 0 (1-2 jours) :
  0.1. Smoke test plugin registry
  0.2. Clarifier comportement ML
  0.3. Tests de caractérisation WidgetGenerator (baseline)
  0.4. Ajouter schema_version, profiling_status, column_diagnostics
   ↓
Phase 1 (2-3 jours) :
  1.1. Éliminer double chargement (profile_dataframe)
  1.2. Support TSV/TXT — parité I/O (4 points d'entrée)
  1.3. Fallback encodage — parité I/O
  1.4. Sampling nrows=50_000 + total_count DuckDB
   ↓
Phase 2 (2-3 jours) :
  2.1. Patterns Darwin Core
  2.2. Contrat binary_counter → donut_chart (prérequis 2.3)
  2.3. Fix "um" + labels depuis données
  2.4. Labels français → anglais (6+ fichiers)
  2.5. Colonnes NULL → pas de suggestion
  2.6. Aligner NUMERIC_DISCRETE (fonctionnel, sans renommage)
  2.7. scatter_plot : compatible_structures + mapping config
  2.8. Consolider stats DataAnalyzer
   ↓
Phase 3 (3-4 jours) :
  Tests WidgetGenerator (~8 tests ciblés)
  Contract test renforcé : config valide contre config_model (D6)
  Test contrat API : shape de réponse
   ↓
Phase 4 (3-4 jours) :
  Script de génération des 4 fixtures MVP (seed fixe)
  4 datasets × 4 tests paramétrés (no-crash, sémantique, qualité, diagnostics)
  Boucle itérative : test échoue → investiguer → corriger → relancer
   ↓
Phase 4+ (optionnel, 2-3 jours) :
  4 datasets supplémentaires (checklist, custom_forest, GeoJSON, XLSX)
   ↓
Release / Challenge GBIF
```

**Budget total : 2-3 semaines (MVP)** | 3-4 semaines (scope complet).

La Phase 4 est itérative : chaque dataset qui échoue révèle un composant à corriger, ce qui améliore le système progressivement.

**Si le temps manque**, le chemin critique est : Phase 0 → Phase 1 → Phase 2 (2.1, 2.3, 2.5 minimum) → Phase 4 (2 datasets : terrestre + adversarial). Ce minimum viable prend ~8-10 jours.

---

## Références

### Fichiers clés (chaîne de suggestion)
- `src/niamoto/core/imports/profiler.py` — DataProfiler, détection sémantique
- `src/niamoto/core/imports/ml_detector.py` — MLColumnDetector, RandomForest 13 types
- `src/niamoto/core/imports/data_analyzer.py` — DataAnalyzer, enrichissement profils
- `src/niamoto/core/imports/widget_generator.py` — WidgetGenerator, génération suggestions (844 lignes, 0 tests)
- `src/niamoto/core/imports/class_object_analyzer.py` — ClassObjectAnalyzer
- `src/niamoto/core/imports/class_object_suggester.py` — ClassObjectWidgetSuggester
- `src/niamoto/core/imports/multi_field_detector.py` — MultiFieldPatternDetector
- `src/niamoto/core/imports/template_suggester.py` — TemplateSuggester (thin wrapper)
- `src/niamoto/core/imports/transformer_suggester.py` — TransformerSuggester (import-time, duplication avec WidgetGenerator)
- `src/niamoto/core/plugins/matching/matcher.py` — SmartMatcher
- `src/niamoto/gui/api/services/templates/suggestion_service.py` — SuggestionService
- `src/niamoto/gui/api/routers/templates.py` — God Object 3 970 lignes (hors scope)

### Tests existants
- `tests/core/imports/test_data_analyzer.py` — 22 tests ✅
- `tests/core/imports/test_transformer_suggester.py` — 17 tests ✅
- `tests/core/plugins/matching/test_pattern_matching.py` — 17 tests ✅
- `tests/core/imports/test_class_object_analyzer.py` — 11 tests ✅
- `tests/core/imports/test_ml_detector.py` — tests ML ✅

### ML et training
- `scripts/ml/train_column_detector.py` — Script d'entraînement
- `scripts/ml/collect_training_data.py` — Collecte de données
- `models/column_detector.pkl` — Modèle entraîné (635 Ko)

### Architecture
- `docs/09-architecture/adr/0004-generic-import-system.md` — ADR import générique
- `docs/03-ml-detection/overview.md` — Documentation ML
