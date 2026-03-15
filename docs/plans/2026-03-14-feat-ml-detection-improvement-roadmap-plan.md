---
title: "Roadmap ML : détection générique de colonnes et suggestion intelligente"
type: feat
date: 2026-03-14
reviewed: 2026-03-14
---

# Roadmap ML : détection générique de colonnes et suggestion intelligente

## Overview

Rendre Niamoto capable de détecter et classifier **n'importe quel dataset écologique mondial** automatiquement, puis de suggérer les meilleures paires transformer→widget — avec un minimum d'intervention humaine.

Le système actuel (RandomForest, 21 features, ~400 exemples NC-biaisés) est un prototype. Ce plan le remplace par une architecture multi-modèles robuste, multilingue, et auto-améliorante.

**Contraintes architecturales** :
- **Offline-first** : tout doit fonctionner sans réseau. LLM = enrichissement optionnel.
- **Taille modèle < 100 MB** : distribution desktop via Tauri
- **Inférence < 500ms par colonne** : UI réactive
- **Généricité** : "Would this work for a coral reef study in Indonesia?" (CLAUDE.md)
- **Pas de dépendances lourdes** : pas de PyTorch, pas de spaCy, pas de GNN. scikit-learn + rapidfuzz + Unidecode.

**Prérequis** : le [plan battle-test SmartMatcher](2026-03-13-feat-battle-test-smartmatcher-import-suggestions-plan.md) (Phases 0-4 terminées ✅).

---

## Problème / Motivation

### État actuel (post-battle-test)

Le [battle-test SmartMatcher](2026-03-13-feat-battle-test-smartmatcher-import-suggestions-plan.md) a corrigé les blockers I/O, les biais NC et les lacunes de tests. Ce qui **reste à faire** pour le ML :

| Aspect | État post-battle-test | Ce qui manque |
|--------|----------------------|---------------|
| **ML en production** | `DataProfiler(ml_detector=None)` charge le modèle par défaut implicitement | API confuse. Besoin d'un `ml_mode=auto/off/force` explicite. |
| **Données** | ~400 exemples synthétiques NC | Biaisé. Besoin de 5000+ colonnes globales (gold + silver + synthetic). |
| **Types** | 13 types forestiers | Besoin de ~25 types (depth, elevation, pH, bodyMass, habitat...). |
| **Features** | 21 stats sur valeurs uniquement | Besoin de ~80-120 features incluant nom de colonne (30-40% du signal). |
| **Évaluation** | Pas de harness d'évaluation | Besoin de GroupKFold, holdouts géo/linguistique, métriques calibration. |
| **Multilingue** | Patterns DwC (EN) + quelques FR ajoutés | Pas de ES, PT, DE, ID. Pas de handling des colonnes sans nom (X1, col_3). |
| **Matching** | SmartMatcher clé-intersection + 7 paires dans `_generate_widget_params()` | Besoin d'affordance matching. scatter_plot activé, reste line_plot/stacked_area/sunburst. |
| **Sérialisation** | Pickle | Besoin de Joblib + SHA-256. |
| **Observabilité** | ✅ `schema_version`, `profiling_status`, `column_diagnostics` ajoutés | OK — rien à faire. |
| **I/O** | ✅ TSV/TXT, encoding fallback, sampling 50k, profile_dataframe | OK — rien à faire. |
| **Labels** | ✅ Anglais partout, labels NC supprimés, bug "um" corrigé | OK — rien à faire. |
| **Tests** | ✅ 2499 tests (89 ajoutés par battle-test), 8 fixtures, intégration | OK — base solide pour le ML. |

### Ce que la recherche montre

| Système | Année | Approche | F1 | Applicable ? |
|---------|-------|----------|-----|-------------|
| Sherlock | 2019 | 1588 features + NN | 0.89 | Oui (features pertinentes, NN pas nécessaire) |
| Sato | 2020 | Sherlock + contexte table (CRF) | 0.93 | Partiellement (CRF trop lourd, mais le contexte table est utile) |
| DoDuo | 2022 | BERT fine-tuné | 0.95 | Non (trop lourd pour desktop) |
| GAIT | 2024 | Graph Neural Networks | 0.94 | Non (dépendances lourdes) |

**Insight clé** : les features de nom de colonne (char n-grams, keywords) portent 30-40% du signal ([Sherlock paper](https://sherlock.media.mit.edu/)). Les features statistiques de valeurs portent 20-25%. Le contexte inter-colonnes apporte ~4 points de F1 (Sato vs Sherlock). L'algorithme (RF vs NN vs BERT) compte moins que les features et les données.

---

## Architecture cible

### 1. Détection de colonnes : 3 branches + fusion

```
            Colonne à classifier
                   |
         [nom + échantillon valeurs + contexte table]
                   |
    ┌──────────────┼──────────────┐
    │              │              │
  HEADER         VALUES        CONTEXT
  (nom)          (stats)       (table)
    │              │              │
  TF-IDF        Features       Features
  char 3-5      denses         inter-cols
  + alias       ~120-180       ~10-15
  + keywords
    │              │              │
  Score          Score          Score
  header         values         context
    │              │              │
    └──────────────┼──────────────┘
                   │
           ┌───────────────┐
           │ Fusion Model  │  LogisticRegression calibrée
           │ + Règles HP   │  + règles haute-précision (lat/lon, WKT, dates)
           └───────────────┘
                   │
         ColumnSemanticProfile
         (role + concept + affordances)
```

#### 1.1 Branche HEADER (nom de colonne)

**Algorithme** : `TfidfVectorizer(analyzer="char_wb", ngram_range=(3,5))` + `LogisticRegression`

Les char n-grams capturent les variations orthographiques entre langues proches (`diametre` / `diametro` / `diameter`). Pour les langues non-latines ou les synonymes (`hauteur` ≠ `height`), un **alias registry YAML** fait le mapping.

```yaml
# config/column_aliases.yaml
measurement.diameter:
  en: [dbh, diameter, trunk_diameter, stem_diameter, girth]
  fr: [diametre, diam, dbh, circonference]
  es: [diametro, dap, diametro_pecho]
  pt: [diametro, dap]
  id: [diameter, dbh]

measurement.height:
  en: [height, tree_height, total_height, canopy_height]
  fr: [hauteur, haut, h_tot, hauteur_arbre]
  es: [altura, alto, altura_total]

measurement.depth:
  en: [depth, water_depth, minimum_depth, maximum_depth]
  fr: [profondeur, prof]
  es: [profundidad]
  de: [tiefe, wassertiefe]

location.latitude:
  en: [latitude, lat, decimal_latitude, decimallatitude]
  fr: [latitude, lat]
  dwc: [decimallatitude, verbatimlatitude]

taxonomy.species:
  en: [species, scientific_name, taxon, species_name]
  fr: [espece, nom_scientifique]
  es: [especie, nombre_cientifico]
  dwc: [scientificname, acceptednameusage]
# ... ~25 concepts × 5-8 langues = 300-500 entrées
```

**Pour les colonnes sans nom** (`X1`, `col_3`, `var_a`) : le score header tombe quasi à zéro. La prédiction repose sur values + context. Si la confiance est moyenne → type générique (`role=measurement`) au lieu de forcer un concept précis.

**Dépendances** : `rapidfuzz` (fuzzy match offline), `Unidecode` (normalisation Unicode). Pas de sentence-transformers.

**Pourquoi pas sentence-transformers** : [rapidfuzz score "running shoes" vs "athletic footwear" à 0.267](https://x.com/KhuyenTran16/status/1958909676755509298) — le fuzzy ne capture pas la sémantique. Mais pour les noms de colonnes écologiques, l'alias registry YAML couvre 95% des cas car le vocabulaire est fermé (~25 concepts). Les embeddings sont un "nice to have" post-MVP pour les 5% restants.

#### 1.2 Branche VALUES (statistiques de valeurs)

**Algorithme** : `HistGradientBoostingClassifier` ou `RandomForest` (benchmarker les deux — [scikit-learn doc](https://scikit-learn.org/stable/auto_examples/ensemble/plot_forest_hist_grad_boosting_comparison.html) montre que HGBT est meilleur > 10k exemples mais le binning peut être approximatif sur petits datasets)

**Features (~120-180)** :

```python
def extract_value_features(series: pd.Series) -> dict:
    """Features statistiques extraites des valeurs de la colonne."""
    clean = series.dropna()
    str_vals = clean.astype(str)
    features = {}

    # ── Stats descriptives (existantes, conservées) ──
    if pd.api.types.is_numeric_dtype(clean):
        features.update({
            'num_mean': clean.mean(), 'num_std': clean.std(),
            'num_min': clean.min(), 'num_max': clean.max(),
            'num_skew': clean.skew(), 'num_kurtosis': clean.kurtosis(),
            'num_q25': clean.quantile(0.25), 'num_q50': clean.median(),
            'num_q75': clean.quantile(0.75),
            'num_range': clean.max() - clean.min(),
            'num_cv': clean.std() / clean.mean() if clean.mean() != 0 else 0,
            'num_negative_ratio': (clean < 0).mean(),
            'num_integer_ratio': (clean == clean.astype(int)).mean(),
            'num_zero_ratio': (clean == 0).mean(),
        })

    # ── Uniqueness et distribution ──
    features['unique_ratio'] = clean.nunique() / max(len(clean), 1)
    features['null_ratio'] = series.isnull().mean()
    features['entropy'] = scipy.stats.entropy(
        clean.value_counts(normalize=True)
    ) if len(clean) > 0 else 0

    # ── Caractères (NOUVEAU — fort signal pour text vs numeric) ──
    features['mean_length'] = str_vals.str.len().mean()
    features['std_length'] = str_vals.str.len().std()
    features['digit_ratio'] = str_vals.str.count(r'\d').sum() / max(str_vals.str.len().sum(), 1)
    features['alpha_ratio'] = str_vals.str.count(r'[a-zA-Z]').sum() / max(str_vals.str.len().sum(), 1)
    features['space_ratio'] = str_vals.str.count(r'\s').sum() / max(str_vals.str.len().sum(), 1)
    features['mean_word_count'] = str_vals.str.split().str.len().mean()

    # ── Regex patterns (NOUVEAU — détection directe de formats) ──
    features['pct_date_iso'] = str_vals.str.match(r'^\d{4}-\d{2}-\d{2}').mean()
    features['pct_coordinate'] = str_vals.str.match(r'^-?\d{1,3}\.\d{4,}$').mean()
    features['pct_boolean'] = str_vals.str.lower().isin(
        ['true', 'false', 'yes', 'no', '0', '1', 'oui', 'non']
    ).mean()
    features['pct_uuid'] = str_vals.str.match(
        r'^[0-9a-f]{8}-[0-9a-f]{4}'
    ).mean()

    # ── Patterns biologiques (NOUVEAU) ──
    features['binomial_score'] = str_vals.str.match(
        r'^[A-Z][a-z]+ [a-z]+'  # Genus species
    ).mean()
    features['family_suffix'] = str_vals.str.match(
        r'.*(?:aceae|idae|ales|ineae)$'
    ).mean()

    return features
```

#### 1.3 Branche CONTEXT (contexte inter-colonnes)

**Pas de CRF/GNN** — des règles de propagation simples :

```python
def extract_context_features(
    col_profile: ColumnProfile,
    all_profiles: List[ColumnProfile],
) -> dict:
    """Features de contexte : relations entre colonnes de la même table."""
    features = {}

    # Présence de paires connues
    all_names = {p.name.lower() for p in all_profiles}
    features['has_lat_lon_pair'] = (
        any('lat' in n for n in all_names) and
        any('lon' in n for n in all_names)
    )
    features['has_taxonomy_hierarchy'] = sum(
        1 for n in all_names
        if any(t in n for t in ['family', 'genus', 'species', 'kingdom', 'phylum'])
    ) >= 2
    features['has_temporal'] = any(
        t in n for n in all_names for t in ['date', 'year', 'month', 'time']
    )
    features['n_numeric_cols'] = sum(
        1 for p in all_profiles if p.dtype.startswith(('int', 'float'))
    )
    features['n_text_cols'] = sum(
        1 for p in all_profiles if p.dtype == 'object'
    )
    features['n_total_cols'] = len(all_profiles)

    return features
```

#### 1.4 Fusion + Règles haute-précision

```python
class ColumnClassifier:
    """3-branch column classifier with calibrated fusion."""

    def __init__(self):
        self.header_model = None      # TF-IDF + LogReg
        self.value_model = None       # HGBT ou RF
        self.fusion_model = None      # LogReg calibrée
        self.alias_registry = load_yaml('config/column_aliases.yaml')

    def classify(self, col_name, series, all_profiles):
        # Règles haute-précision d'abord (confiance >= 0.95)
        rule_result = self._apply_rules(col_name, series)
        if rule_result and rule_result.confidence >= 0.95:
            return rule_result

        # 3 branches en parallèle
        header_scores = self.header_model.predict_proba(
            self._header_features(col_name)
        )
        value_scores = self.value_model.predict_proba(
            self._value_features(series)
        )
        context_features = self._context_features(col_name, all_profiles)

        # Fusion calibrée
        fusion_input = np.concatenate([
            header_scores, value_scores, context_features
        ])
        concept_proba = self.fusion_model.predict_proba([fusion_input])[0]

        # Résultat avec abstention si confiance trop basse
        max_proba = concept_proba.max()
        concept = self.fusion_model.classes_[concept_proba.argmax()]

        if max_proba < 0.50:
            # Confiance trop basse → type générique
            role = self._infer_role(series)
            return ColumnSemanticProfile(
                role=role, concept=None, affordances=self._role_affordances(role),
                confidence=max_proba, evidence={'abstention': True}
            )

        return ColumnSemanticProfile(
            role=CONCEPT_TO_ROLE[concept],
            concept=concept,
            affordances=CONCEPT_AFFORDANCES[concept],
            confidence=max_proba,
            evidence={
                'header_score': float(header_scores.max()),
                'value_score': float(value_scores.max()),
            }
        )
```

---

### 2. Ontologie : 3 axes au lieu de types plats

Le système actuel mappe des types plats (`diameter`) vers des types namespacés (`measurement.diameter`). On enrichit avec 3 axes :

```python
@dataclass
class ColumnSemanticProfile:
    """Profil sémantique riche d'une colonne."""
    role: str                   # identifier, measurement, category, time, geometry, text
    concept: Optional[str]      # organism.dbh, location.latitude, taxonomy.species, None si incertain
    affordances: Set[str]       # numeric_continuous, histogrammable, mappable, join_key, unit_bearing...
    unit: Optional[str]         # cm, m, deg, ha, PSU
    confidence: float           # 0.0-1.0 (calibré)
    evidence: Dict[str, float]  # header_score, value_score, context_score, rule_match
```

**Pourquoi `affordances`** : le matching transformer→widget ne devrait pas dépendre du concept exact (`organism.dbh`) mais de ce que la colonne **peut faire** (`numeric_continuous + histogrammable + unit_bearing`). Un `organism.dbh` et un `measurement.depth` ont des affordances similaires (`numeric_continuous`, `histogrammable`) mais des concepts différents.

```python
# Mapping concept → affordances (dérivé automatiquement)
CONCEPT_AFFORDANCES = {
    'organism.dbh': {'numeric_continuous', 'histogrammable', 'unit_bearing', 'scatterable'},
    'organism.height': {'numeric_continuous', 'histogrammable', 'unit_bearing', 'scatterable'},
    'location.latitude': {'numeric_continuous', 'coordinate', 'mappable'},
    'location.longitude': {'numeric_continuous', 'coordinate', 'mappable'},
    'taxonomy.species': {'categorical', 'rankable', 'hierarchy_level'},
    'taxonomy.family': {'categorical', 'rankable', 'hierarchy_level'},
    'event.date': {'temporal', 'sortable', 'filterable'},
    'identifier': {'join_key', 'unique'},
}

# Mapping role → affordances par défaut (fallback quand concept inconnu)
ROLE_AFFORDANCES = {
    'measurement': {'numeric_continuous', 'histogrammable'},
    'category': {'categorical', 'rankable'},
    'time': {'temporal', 'sortable'},
    'geometry': {'mappable'},
    'identifier': {'join_key'},
    'text': {'searchable'},
}
```

---

### 3. Suggestion transformer→widget : affordance matching + recipe ranker

#### 3.1 Tier S1 : Affordance matching (~60% des suggestions)

Remplace l'intersection de clés par un matching basé sur les affordances :

```python
class AffordanceMatcher:
    """Match columns to transformers/widgets via affordances."""

    def find_candidates(self, profile: ColumnSemanticProfile) -> List[SuggestionCandidate]:
        candidates = []

        for transformer in PluginRegistry.get_plugins_by_type(TRANSFORMER):
            # Le transformer déclare required_affordances
            required = getattr(transformer, 'required_affordances', set())
            if not required:
                continue

            # Score = intersection des affordances
            match = profile.affordances & required
            if len(match) / len(required) >= 0.5:
                score = len(match) / len(required)

                # Trouver les widgets compatibles
                produced = getattr(transformer, 'produced_affordances', set())
                for widget in PluginRegistry.get_plugins_by_type(WIDGET):
                    consumed = getattr(widget, 'consumed_affordances', set())
                    if consumed and produced & consumed:
                        widget_score = len(produced & consumed) / len(consumed)
                        candidates.append(SuggestionCandidate(
                            transformer=transformer.name,
                            widget=widget.name,
                            score=score * widget_score,
                            reason=f"Matched affordances: {match}",
                        ))

        return sorted(candidates, key=lambda c: -c.score)
```

**Migration** : les plugins existants déclarent `output_structure`/`compatible_structures` (clés). On ajoute `required_affordances`/`produced_affordances`/`consumed_affordances` progressivement. L'ancien SmartMatcher reste en fallback.

#### 3.2 Tier S2 : Recipe ranker appris (~25% d'impact — reranking)

Le ranker ne **génère** pas de suggestions — il **réordonne** celles du Tier S1 selon les préférences utilisateur apprises.

```python
class SuggestionRanker:
    """Rerank suggestions based on learned user preferences."""

    def rerank(self, candidates, column_profile, dataset_context):
        if not self.model:
            return candidates  # pas de données → ordre S1

        for c in candidates:
            features = [
                column_profile.confidence,
                column_profile.null_ratio,
                len(column_profile.affordances),
                c.score,  # score S1
                self._pair_prior(c.transformer, c.widget),
                dataset_context.get('n_columns', 0),
            ]
            utility = self.model.predict_proba([features])[0][1]
            c.score = 0.6 * c.score + 0.4 * utility

        return sorted(candidates, key=lambda c: -c.score)
```

**Données du ranker** : chaque choix utilisateur dans le GUI = 1 positif + N négatifs. Stocké dans une table locale, pas dans le `semantic_profile` (séparation données vs télémétrie, comme recommandé par Codex).

**Volume nécessaire** : ~100 interactions pour un ranker utile. Réaliste après quelques semaines d'usage, même pour un outil de niche.

#### 3.3 Tier M1 : Dataset Pattern Detector (~10% des suggestions)

Classifie le dataset entier pour débloquer des suggestions multi-colonnes :

```python
DATASET_PATTERNS = {
    'occurrence_inventory': {
        'requires': ['has_coordinates', 'has_taxonomy'],
        'suggests': [
            ('geospatial_extractor', 'interactive_map', 'Distribution map'),
            ('categorical_distribution', 'bar_plot', 'Taxonomy breakdown'),
        ]
    },
    'forest_inventory': {
        'requires': ['has_measurements', 'has_taxonomy'],
        'suggests': [
            ('scatter_analysis', 'scatter_plot', 'Allometric relationship'),
            ('binned_distribution', 'bar_plot', 'DBH distribution'),
        ]
    },
    'marine_survey': {
        'requires': ['has_depth', 'has_coordinates'],
        'suggests': [
            ('binned_distribution', 'bar_plot', 'Depth distribution'),
        ]
    },
    'taxonomic_checklist': {
        'requires': ['has_taxonomy', 'not:has_coordinates'],
        'suggests': [
            ('categorical_distribution', 'donut_chart', 'Family distribution'),
        ]
    },
}
```

Implémentation : règles simples sur les affordances agrégées de toutes les colonnes. Pas de ML pour ça — le vocabulaire de patterns est fermé.

#### 3.4 Tier M2 : LLM local pour suggestions cross-colonnes (~5%, optionnel)

Le LLM intervient **uniquement** pour les suggestions sémantiques que les règles ne peuvent pas capturer :
- "Les colonnes `flower_month` et `fruit_month` forment un calendrier phénologique"
- "Les colonnes `dbh1` et `dbh2` montrent la croissance entre 2 inventaires"

```python
def suggest_cross_column(profiles, available_plugins):
    """LLM-based cross-column suggestions (optional, via Ollama)."""
    prompt = f"""Ecological dataset with columns:
{format_profiles(profiles)}

Available transformers: {list(available_plugins['transformers'])}
Available widgets: {list(available_plugins['widgets'])}

Suggest up to 3 multi-column visualizations that reveal
scientific relationships BETWEEN columns.
JSON: [{{"columns": [...], "transformer": "...", "widget": "...", "reason": "..."}}]"""

    return call_ollama_or_skip(prompt)
```

**Modèle recommandé** : `Qwen3-0.6B` (100+ langues, Apache 2.0, 1.2 GB quantifié) ou `Gemma-3-1B` (2 GB quantifié). Via Ollama (téléchargement optionnel). Cloud API (Claude Haiku) en fallback.

**Proportion réaliste** : ~5% des suggestions totales. Le LLM est un bonus, pas le moteur principal.

---

### 4. Anomalies : règles métier explicables

Pas d'Isolation Forest — des validateurs déterministes, plus simples, plus explicables, et plus fiables pour les données écologiques :

```python
ANOMALY_RULES = {
    'location.latitude': lambda s: (s < -90) | (s > 90) | (s.abs() < 0.001),
    'location.longitude': lambda s: (s < -180) | (s > 180) | (s.abs() < 0.001),
    'organism.dbh': lambda s: (s < 0) | (s > 500),  # cm
    'organism.height': lambda s: (s < 0) | (s > 150),  # m
    'measurement.depth': lambda s: s > 0,  # profondeur doit être négative
    'event.date': lambda s: pd.to_datetime(s, errors='coerce') > pd.Timestamp.now(),
}

def detect_anomalies(series, concept):
    """Per-column anomaly detection using domain rules."""
    rule = ANOMALY_RULES.get(concept)
    if rule:
        return rule(series)

    # Fallback numérique : IQR × 3
    if pd.api.types.is_numeric_dtype(series):
        q1, q3 = series.quantile([0.25, 0.75])
        iqr = q3 - q1
        return (series < q1 - 3 * iqr) | (series > q3 + 3 * iqr)

    return pd.Series(False, index=series.index)
```

---

### 5. Données d'entraînement : gold / silver / synthetic

#### Sources disponibles

| Source | Colonnes estimées | Qualité | Méthode |
|--------|-------------------|---------|---------|
| **GUYADIV (Guyane)** | ~60 (data dictionary labélisé) | Gold | Extraction automatique du data dictionary |
| **Afrique (Gabon/Cameroun)** | ~50 | Gold (annotation manuelle) | Même schéma que NC |
| **NC (niamoto-og + niamoto-gb)** | ~50 | Gold | Schémas connus |
| **Nos 8 fixtures de test** | ~100 | Gold | Labélisées pendant le battle-test |
| **GBIF DwC downloads** (10-20 datasets) | ~1000 | Silver (auto-labélisé par nom DwC standard) | Téléchargement + mapping nom → type |
| **IFN France** (data.gouv.fr) | ~50 | Silver | Inventaire forestier métropole |
| **ForestPlots.net** | ~100 | Silver | Inventaire pantropical |
| **OBIS marine** | ~200 | Silver | Écologie marine |
| **Synthétique global** | ~3000 | Support | Script amélioré multi-biome × multi-langue |

**Objectif V1** : ~500 gold + ~1500 silver + ~3000 synthetic = **~5000 colonnes**
**Objectif V2** : ~2000 gold + ~5000 silver = **~7000 colonnes** (pas de synthétique comme source principale)

#### Splits anti-fuite

```python
# JAMAIS split par colonne — split par FAMILLE DE DATASET
from sklearn.model_selection import GroupKFold

groups = df['source_dataset']  # ex: "guyadiv", "gbif_marine_001", "ifn_france"
cv = GroupKFold(n_splits=5)

# Holdouts obligatoires :
# - Géographique : entraîner sans Guyane, tester Guyane
# - Linguistique : entraîner sans FR, tester headers FR
# - Headers anonymisés : tester avec X1, col_3, var_a
```

#### Script de génération synthétique

```python
BIOMES = {
    "tropical_rainforest": {"dbh": (5, 150), "height": (2, 50), "elev": (0, 1500)},
    "temperate_forest": {"dbh": (5, 200), "height": (2, 40), "elev": (0, 2500)},
    "boreal_forest": {"dbh": (5, 80), "height": (2, 25), "elev": (0, 1000)},
    "mangrove": {"dbh": (2, 50), "height": (1, 20), "elev": (-2, 10)},
    "marine": {"depth": (-11000, 0), "salinity": (0, 40), "pH": (7.5, 8.5)},
    "grassland": {"height": (0.01, 2), "cover_pct": (0, 100)},
    "alpine": {"dbh": (3, 40), "height": (1, 15), "elev": (1500, 4500)},
}

# Générer pour chaque type × biome × langue (avec bruit et valeurs manquantes)
```

---

### 6. Auto-amélioration sans data scientist

6 mécanismes produit :

1. **Alias registry YAML** éditable par un dev ou un écologue (pas besoin de ML)
2. **Journal local des prédictions et corrections** dans une table DuckDB séparée (pas dans `semantic_profile`)
3. **Active learning dans le GUI** : montrer en priorité les colonnes à forte incertitude
4. **Script de réentraînement one-command** : `niamoto ml retrain` avec rapport HTML
5. **Versionnement strict des modèles** avec rollback automatique si régression
6. **Boucle autoresearch** : optimisation autonome des modèles (voir section 8)

**Règle produit** : si confiance < 0.50, Niamoto propose un `role` générique au lieu d'halluciner un `concept` précis.

---

### 7. Intégration ML dans le profiler : mode explicite

Corriger l'API confuse `ml_detector=None` (qui charge le modèle par défaut) :

```python
class DataProfiler:
    def __init__(self, ml_mode: str = "auto"):
        """
        Args:
            ml_mode: "auto" (charge le modèle si disponible),
                     "off" (patterns seulement),
                     "force" (erreur si modèle indisponible)
        """
        self.ml_mode = ml_mode
        if ml_mode == "auto":
            self.classifier = ColumnClassifier.load_or_none()
        elif ml_mode == "force":
            self.classifier = ColumnClassifier.load()
        else:
            self.classifier = None
```

**Ordre de détection** : Règles haute-précision → Fusion (header + values + context) → Fallback patterns existants. Le ML enrichit les patterns, ne les remplace pas.

---

### 8. Autoresearch : optimisation autonome des modèles

**Réf** : [Rapport d'opportunité autoresearch](../../../../docs/plans/2026-03-15-research-autoresearch-opportunity-report-plan.md)

Inspiré du pattern [autoresearch](https://github.com/karpathy/autoresearch) (Karpathy, mars 2026) : un agent IA modifie du code, mesure une métrique, garde les améliorations, rejette les régressions, et boucle indéfiniment. Le pipeline ML de Niamoto est structurellement compatible grâce au harness d'évaluation (Phase 1) et au budget d'entraînement court (~60s sur scikit-learn).

#### Principe

```
┌──────────────────────────────────────────────────┐
│  programme.md  →  agent modifie train_*.py       │
│       ↓                                          │
│  uv run python -m niamoto.ml.evaluate            │
│       ↓                                          │
│  macro-F1 ≥ baseline ?  ─── oui → git commit     │
│                          └── non → git reset     │
│       ↓                                          │
│  boucle (50-100 itérations)                      │
└──────────────────────────────────────────────────┘
```

#### 3 sous-boucles séquentielles

| Boucle | Cible | Axes d'exploration | Itérations | Durée |
|--------|-------|--------------------|------------|-------|
| **Header** | `train_header_model.py` | ngram_range, analyzer, max_features, régularisation LogReg, preprocessing | ~50 | ~25 min |
| **Values** | `train_value_model.py` | RF vs HGBT vs ExtraTrees, hyperparamètres, feature selection par groupe | ~50 | ~40 min |
| **Fusion** | `train_fusion.py` | Calibration isotonic/Platt, poids des branches, seuils d'abstention, règles HP | ~30 | ~15 min |

**Boucle bonus** : feature engineering autonome (après Phase 2) — l'agent propose de nouvelles features inspirées de Sherlock, ~100 itérations, ~2.5h.

#### Prérequis

- Phase 1 terminée : harness d'évaluation fonctionnel (GroupKFold, holdouts, métriques)
- Gold set ≥ 500 colonnes labélisées
- Scripts d'entraînement séparés par branche (header, values, fusion)
- Script de métrique CLI : `uv run python -m niamoto.ml.evaluate --model <branch> --metric macro-f1` → stdout = nombre

#### Insertion dans le phasage

S'insère **entre la Phase 1 (fondations) et la Phase 2 (modèles)** du phasage existant. Concrètement :
1. Phase 1 : construire le harness, préparer le gold set, structurer les scripts d'entraînement
2. **Phase 1.5 (autoresearch)** : lancer les boucles autonomes pour optimiser les 3 modèles
3. Phase 2 : valider les résultats, intégrer dans le système, silver dataset

L'agent autoresearch ne **remplace** pas le travail de conception (choix d'architecture, features initiales) — il **accélère le tuning** une fois l'architecture posée.

#### Impact attendu

- **+3 à 8 pts de macro-F1** sur les modèles individuels (estimation basée sur les gains typiques rapportés par la communauté autoresearch : ~26% d'amélioration sur TinyStories, ~41% de keep rate)
- **Élimination du tuning manuel** : au lieu de tester manuellement 10 combinaisons, l'agent en explore 130+ en 4h
- **Historique complet** : chaque expérience est un commit git, reproductible et auditable

---

## Évaluation

### Métriques

| Niveau | Métrique | Cible |
|--------|---------|-------|
| **Colonnes** | macro-F1 sur concept | >= 0.85 |
| **Colonnes** | macro-F1 sur role | >= 0.90 |
| **Colonnes** | top-3 accuracy | >= 0.95 |
| **Colonnes** | ECE (calibration) | <= 0.10 |
| **Colonnes** | Coverage@0.70 (% colonnes typées avec confiance >= 0.70) | >= 75% |
| **Suggestions** | top-1 accept rate | >= 60% |
| **Suggestions** | MRR (Mean Reciprocal Rank) | >= 0.70 |

### Protocole de test

- Split par famille de dataset (GroupKFold)
- Holdout géographique (entraîner sans Guyane)
- Holdout linguistique (entraîner sans FR)
- Test "headers anonymisés" (X1, col_3)
- Ablations : header only, values only, header+values, +context
- Benchmark RF vs HistGradientBoosting vs ExtraTrees

---

## Phasage

```
Phase 1 : Fondations (2-3 semaines)
  1.1 Alias registry YAML (~25 concepts × 5-8 langues)
  1.2 Corriger l'API profiler (ml_mode=auto/off/force)
  1.3 Harness d'évaluation (splits, métriques, ablations)
  1.4 Gold set initial (~500 colonnes depuis GUYADIV + Afrique + NC + fixtures)
  1.5 Scripts d'entraînement séparés par branche (header, values, fusion)
  1.6 Script de métrique CLI (niamoto ml evaluate → stdout = nombre)
   ↓
Phase 1.5 : Autoresearch — optimisation autonome (~4h d'exécution)
  1.5a Écrire les programmes.md (header, values, fusion)
  1.5b Boucle header model (~50 itérations, 25 min)
  1.5c Boucle values model (~50 itérations, 40 min)
  1.5d Boucle fusion calibrée (~30 itérations, 15 min)
  1.5e Valider les résultats, sélectionner les meilleurs commits
   ↓
Phase 2 : Modèles — validation et extension (1-2 semaines)
  2.1 Feature extractor enrichi (header + values + context) — baseline + résultats autoloop
  2.2 Valider header model (meilleur autoloop vs baseline)
  2.3 Valider value model (RF vs HGBT — résultat autoloop)
  2.4 Fusion calibrée (résultat autoloop validé)
  2.5 Silver dataset GBIF + synthétique global
  2.6 [Optionnel] Boucle autoresearch feature engineering (~100 itérations, 2.5h)
   ↓
Phase 3 : Intégration (2-3 semaines)
  3.1 Ontologie 3 axes (role/concept/affordances)
  3.2 Affordance matching pour transformer→widget
  3.3 Dataset Pattern Detector (M1)
  3.4 Anomaly rules
  3.5 Sérialisation Joblib + SHA-256
   ↓
Phase 4 : Amélioration continue (ongoing)
  4.1 Feedback loop (choix utilisateur → ranker)
  4.2 Active learning dans le GUI
  4.3 CLI niamoto ml retrain
  4.4 [Optionnel] Boucle autoresearch sur le ranker (après ~100 interactions utilisateur)
  4.5 LLM local (Qwen3-0.6B via Ollama) pour cross-column — optionnel
  4.6 EmbeddingGemma-300M pour matching multilingue avancé — optionnel
```

---

## Acceptance Criteria

### Phase 1 — Fondations
- [x] Alias registry YAML avec ~25 concepts × 5-8 langues
- [x] API profiler : `ml_mode="auto"` / `"off"` / `"force"`
- [x] Harness d'évaluation avec GroupKFold, holdout géo/linguistique, ablations
- [ ] Gold set >= 500 colonnes labélisées manuellement
- [ ] Benchmark F1 baseline documenté

### Phase 1.5 — Autoresearch
- [ ] `programmes/niamoto-header-model.md` écrit et validé
- [ ] `programmes/niamoto-values-model.md` écrit et validé
- [ ] `programmes/niamoto-fusion.md` écrit et validé
- [ ] Script métrique CLI fonctionnel (`niamoto ml evaluate --model <branch> --metric macro-f1`)
- [ ] Boucle header : ≥ 50 itérations exécutées, meilleur commit identifié
- [ ] Boucle values : ≥ 50 itérations exécutées, meilleur commit identifié
- [ ] Boucle fusion : ≥ 30 itérations exécutées, meilleur commit identifié
- [ ] Gain ≥ 1 pt macro-F1 par rapport au baseline manuel (au moins 1 des 3 boucles)
- [ ] `results.tsv` complet avec historique de toutes les expériences

### Phase 2 — Modèles (validation + extension)
- [ ] Header model validé (meilleur autoloop vs baseline)
- [ ] Value model validé (RF vs HGBT — résultat autoloop)
- [ ] Fusion calibrée validée (isotonic regression)
- [ ] macro-F1 concept >= 0.85 sur gold set
- [ ] Coverage@0.70 >= 75%
- [ ] Silver dataset >= 1500 colonnes (GBIF + IFN + OBIS)

### Phase 3 — Intégration
- [ ] `ColumnSemanticProfile` (role + concept + affordances) remplace les types plats
- [ ] Affordance matching pour transformer→widget
- [ ] Dataset Pattern Detector (occurrence, forest, marine, checklist)
- [ ] Anomaly rules métier intégrées au profiling
- [ ] Sérialisation Joblib + SHA-256
- [ ] Aucune régression sur les 2499 tests existants

### Phase 4 — Amélioration continue
- [ ] Feedback loop : choix utilisateur stockés dans table séparée
- [ ] Active learning : colonnes incertaines surlignées dans le GUI
- [ ] CLI `niamoto ml retrain` avec rapport HTML
- [ ] LLM local (optionnel) pour suggestions cross-colonnes
- [ ] Versionnement modèle avec rollback automatique

---

## Dépendances

### Obligatoires (Phase 1-3)

| Package | Taille | Usage |
|---------|--------|-------|
| `rapidfuzz` | ~2 MB | Fuzzy matching offline pour alias registry |
| `Unidecode` | ~1 MB | Normalisation Unicode des headers |
| `joblib` | (transitif via scikit-learn) | Sérialisation sécurisée |

### Optionnelles (Phase 4)

| Package | Taille | Usage |
|---------|--------|-------|
| `sentence-transformers` + `torch` | ~200-800 MB | EmbeddingGemma pour multilingue avancé |
| Ollama (externe) | ~1-2 GB modèle | LLM local cross-column |
| `anthropic` SDK | ~1 MB | Cloud API fallback |

**Pas de LightGBM, XGBoost, spaCy, PyTorch en obligatoire.** Tout le système tourne sur scikit-learn + 3 MB de dépendances légères.

---

## Risques

| Risque | Impact | Mitigation |
|--------|--------|------------|
| Fuite train/test sur schémas DwC répétés | F1 gonflé artificiellement | Split par dataset-source (GroupKFold) + holdouts |
| Gold set trop petit (< 500) | Modèle instable | Silver + synthétique en augmentation, pas en remplacement |
| Alias registry incomplet | Colonnes multilingues non détectées | Communauté contribue via YAML (PR GitHub) |
| Ontologie trop abstraite | Développeurs confus | Mapping automatique concept → affordances, pas de saisie manuelle |
| Feedback loop trop lent (niche tool) | Ranker jamais entraîné | Beta priors par défaut, ranker = bonus pas prérequis |
| Calibration mal faite | Seuils de confiance inutiles | Tester ECE/Brier, isotonic regression, validation croisée |
| API `ml_mode` break backward compat | Anciens appels `DataProfiler(ml_detector=None)` cassent | Garder le paramètre legacy avec deprecation warning |

---

## Références

### Fichiers clés
- `src/niamoto/core/imports/ml_detector.py` — MLColumnDetector actuel (21 features, RF)
- `src/niamoto/core/imports/profiler.py` — DataProfiler (ML + patterns)
- `src/niamoto/core/plugins/matching/matcher.py` — SmartMatcher (output_structure/compatible_structures)
- `src/niamoto/core/imports/widget_generator.py` — WidgetGenerator (suggestions)
- `scripts/ml/train_column_detector.py` — Script d'entraînement actuel
- `models/column_detector.pkl` — Modèle entraîné (635 Ko)

### Données disponibles
- `niamoto-data/Datas/Guyane/dataverse_files/` — GUYADIV (90k arbres + data dictionary labélisé)
- `niamoto-data/Datas/Afrique/imports/` — 193k occurrences Gabon/Cameroun
- `test-instance/niamoto-gb/imports/` — 80k occurrences NC
- `tests/fixtures/datasets/` — 8 fixtures synthétiques (battle-test)

### Autoresearch
- [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — Boucle de recherche autonome, mars 2026
- [davebcn87/pi-autoresearch](https://github.com/davebcn87/pi-autoresearch) — Généralisation du pattern (Shopify/pi)
- [Rapport d'opportunité autoresearch Arsis](../../../../docs/plans/2026-03-15-research-autoresearch-opportunity-report-plan.md)

### Littérature
- [Sherlock: Deep Learning for Semantic Type Detection](https://sherlock.media.mit.edu/) — KDD 2019, 1588 features, F1=0.89
- [Sato: Context-Aware Semantic Type Detection](https://megagonlabs.medium.com/semantic-type-detection-why-it-matters-current-approaches-and-how-to-improve-it-62027bf8632f) — VLDB 2020, F1=0.93
- [Char n-grams for tabular data vectorization](https://arxiv.org/pdf/2312.09634) — 2023
- [scikit-learn: RF vs HistGradientBoosting](https://scikit-learn.org/stable/auto_examples/ensemble/plot_forest_hist_grad_boosting_comparison.html)
- [LLM-assisted labeling for semantic type detection](https://arxiv.org/html/2408.16173v1) — 2024
- [Data visualization recommendation: 2026 survey](https://journals.sagepub.com/doi/10.1177/14738716251409351)

### Benchmarks modèles légers (mars 2026)
- [Best Open-Source Embedding Models Benchmarked](https://supermemory.ai/blog/best-open-source-embedding-models-benchmarked-and-ranked/)
- [Guide to Open-Source Embedding Models — BentoML](https://www.bentoml.com/blog/a-guide-to-open-source-embedding-models)
- [EmbeddingGemma — Google](https://developers.googleblog.com/introducing-embeddinggemma/) — 308M params, 100+ langues, < 200 MB RAM
- [12 Small LMs Benchmarked for Fine-Tuning](https://www.distillabs.ai/blog/we-benchmarked-12-small-language-models-across-8-tasks-to-find-the-best-base-model-for-fine-tuning)
- [Top Small Language Models 2026 — DataCamp](https://www.datacamp.com/blog/top-small-language-models)
- [rapidfuzz vs sentence-transformers comparison](https://x.com/KhuyenTran16/status/1958909676755509298)
- [MTEB Leaderboard March 2026](https://awesomeagents.ai/leaderboards/embedding-model-leaderboard-mteb-march-2026/)
