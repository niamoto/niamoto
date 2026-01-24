# Auto-Détection de Transformers - MVP

**Version:** 1.1
**Date:** 2025-01-24
**Statut:** Plan validé et étendu (transform.yml + export.yml)
**Effort estimé:** 10-14 jours

---

## Table des matières

1. [Contexte et objectifs](#contexte-et-objectifs)
2. [Vue d'ensemble du système d'import actuel](#vue-densemble-du-système-dimport-actuel)
3. [Analyse des transformers existants](#analyse-des-transformers-existants)
4. [Architecture détaillée du MVP](#architecture-détaillée-du-mvp)
5. [Plan d'implémentation](#plan-dimplémentation)
6. [Pièges potentiels et solutions](#pièges-potentiels-et-solutions)
7. [Exemple de workflow complet](#exemple-de-workflow-complet)

---

## Contexte et objectifs

### Situation actuelle

Nous avons implémenté un système de **pattern matching bidirectionnel** entre transformers et widgets :
- Transformers déclarent `output_structure`
- Widgets déclarent `compatible_structures`
- `SmartMatcher` trouve automatiquement les correspondances

**Problème :** L'utilisateur doit encore **manuellement** choisir quels transformers appliquer à ses données.

### Objectif MVP

Créer un système d'**auto-détection** qui :
1. Analyse les colonnes des données importées
2. Détecte automatiquement leur type sémantique (numérique continu, catégoriel, géographique...)
3. Suggère les transformers pertinents avec **configurations pré-remplies**
4. Permet à l'utilisateur de valider/modifier en un clic

### Vision UX

```
┌──────────────────────────────────────────────────┐
│ 📁 Fichier: occurrences.csv importé (1250 rows) │
├──────────────────────────────────────────────────┤
│                                                   │
│ ✨ Suggestions automatiques détectées:           │
│                                                   │
│ Pour "elevation":                                 │
│  ✓ Distribution par intervalles (85% confiance)  │
│     └─ 5 bins: 0-250m, 250-500m, 500-750m...    │
│     [Appliquer] [Personnaliser]                  │
│                                                   │
│  ✓ Statistiques (80% confiance)                  │
│     └─ Min, Max, Moyenne, Médiane, Écart-type   │
│     [Appliquer] [Personnaliser]                  │
│                                                   │
│ Pour "species":                                   │
│  ✓ Top 10 espèces (75% confiance)               │
│     [Appliquer]                                  │
│                                                   │
│ [Appliquer tout] [Personnaliser...]             │
└──────────────────────────────────────────────────┘
```

---

## Vue d'ensemble du système d'import actuel

### Architecture existante

**Excellente nouvelle :** Le système de profiling sémantique existe déjà !

**Composants clés identifiés :**

```
src/niamoto/core/imports/
├── engine.py         - GenericImporter (CSV, GeoJSON, Shapefile)
├── profiler.py       - DataProfiler avec détection sémantique ✅
├── ml_detector.py    - MLColumnDetector avec Random Forest ✅
├── auto_detector.py  - AutoDetector pour génération de configs
└── registry.py       - EntityRegistry (metadata persistence)
```

### DataProfiler (déjà implémenté)

Le profiler fait **déjà une analyse sémantique sophistiquée** :

**Types sémantiques détectés** (profiler.py:237-328) :
- `taxonomy.*` : family, genus, species, taxon_id
- `location.*` : latitude, longitude, plot, coordinates
- `geometry` : WKT detection
- `measurement.*` : DBH, height, elevation, rainfall
- `statistic.*` : count, nb_, total_
- `reference.*` : taxon, plot
- `identifier`

**Structure ColumnProfile** :
```python
@dataclass
class ColumnProfile:
    name: str
    dtype: str  # pandas dtype (int64, float64, object...)
    semantic_type: Optional[str]  # taxonomy.genus, location.latitude...
    unique_ratio: float  # 0.0 to 1.0
    null_ratio: float
    sample_values: List[Any]
    confidence: float  # 0.0 to 1.0 (ML confidence)
```

### MLColumnDetector (déjà implémenté)

**ML-based detection avec Random Forest** (21 features statistiques) :

**Capacités** :
- Détection basée sur les **valeurs** (pas seulement les noms de colonnes)
- Types détectés : diameter, height, leaf_area, wood_density, species_name, family_name, genus_name, location, latitude, longitude, date, count, identifier
- Seuil de confiance >= 0.6 pour accepter la prédiction ML

**Features extraites** (ml_detector.py:126-227) :
- Statistiques : mean, std, min, max, quantiles
- Distribution : skew, kurtosis, histogram
- Patterns : proportion positive/negative, proportion integers
- Range indicators : is_longitude, is_latitude, is_density

### Workflow d'import actuel

```
1. GenericImporter.import_from_csv()
   ↓
2. Métadonnées basiques : schema.fields[{name, type}]
   ↓
3. EntityRegistry.register_entity(name, kind, table_name, config)
   ↓
4. Stockage DuckDB : niamoto_metadata_entities table
```

**Point crucial à corriger :** Les métadonnées sémantiques du profiler **NE SONT PAS** persistées dans le registry actuellement !

---

## Analyse des transformers existants

### Transformers avec output_structure

| Transformer | Type de données | Output Structure |
|-------------|----------------|------------------|
| **binned_distribution** | Numérique continu | `{bins, counts, labels, percentages}` |
| **categorical_distribution** | Catégoriel | `{categories, counts, labels, percentages}` |
| **statistical_summary** | Numérique continu | `{min, mean, max, median, std, units, max_value}` |
| **top_ranking** | Catégoriel/ID | `{tops, counts}` |
| **geospatial_extractor** | Géométrie | `{type, features}` (GeoJSON) |
| **time_series_analysis** | Temporel | `{month_data, labels}` |
| **field_aggregator** | Multiple | `{*: dict}` (dynamique) |
| **binary_counter** | Booléen | `{um, num, um_percent, num_percent}` |

### Mapping sémantique → transformers

#### binned_distribution

**Attend :** Colonne numérique continue (elevation, height, dbh)

**Config requise :**
```python
{
    "source": "occurrences",
    "field": "elevation",      # REQUIS
    "bins": [0, 250, 500, ...] # REQUIS - au moins 2 valeurs
    "labels": ["0-250m", ...]  # Optionnel
}
```

**Mapping sémantique :**
- `measurement.*` → confiance haute
- Colonnes numériques avec unique_ratio élevé → confiance moyenne

#### categorical_distribution

**Attend :** Colonne catégorielle ou ID

**Config requise :**
```python
{
    "source": "occurrences",
    "field": "species",
    "categories": [],  # Auto-détect si vide
    "labels": []       # Optionnel
}
```

**Mapping sémantique :**
- `taxonomy.*` → confiance haute
- `reference.*` → confiance haute
- unique_ratio < 0.5 → confiance moyenne

#### statistical_summary

**Attend :** Colonne numérique continue

**Config requise :**
```python
{
    "source": "occurrences",
    "field": "dbh",
    "stats": ["min", "mean", "max", "median", "std"],
    "units": "cm",
    "max_value": 500  # Pour gauge
}
```

**Mapping sémantique :**
- `measurement.*` → confiance haute
- dtype numérique → confiance moyenne

#### top_ranking

**Attend :** Colonne avec valeurs répétées (ID, catégories)

**Config requise :**
```python
{
    "source": "occurrences",
    "field": "species_id",
    "count": 10,
    "mode": "direct"  # ou "hierarchical"
}
```

**Mapping sémantique :**
- `reference.*` → confiance haute
- unique_ratio faible (< 0.3) → confiance moyenne

#### geospatial_extractor

**Attend :** Colonne géométrie (WKT, WKB, Point) ou paire lat/lon

**Config requise :**
```python
{
    "source": "occurrences",
    "field": "geo_pt",  # ou détection lat+lon
    "format": "geojson",
    "properties": []
}
```

**Mapping sémantique :**
- `geometry` → confiance haute
- `location.coordinates` → confiance haute
- `location.latitude` + `location.longitude` → confiance moyenne (paire)

### Validation existante

**Tous les transformers ont :**
- ✅ Validation Pydantic des paramètres
- ✅ Résolution EntityRegistry
- ✅ Gestion colonnes manquantes
- ✅ Type hints stricts

**Aucun n'a :**
- ❌ Validation du type sémantique des données

---

## Architecture détaillée du MVP

### Vision d'ensemble

```
                    IMPORT FLOW ENRICHI
┌─────────────────────────────────────────────────────────┐
│ 1. USER UPLOADS FILE (CSV, GeoJSON, etc.)              │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ 2. EXISTING: DataProfiler.profile()                    │
│    - Génère ColumnProfile avec semantic_type           │
│    - Calcule unique_ratio, null_ratio, confidence      │
│    - Détection ML si disponible                        │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ 3. NEW: DataAnalyzer.enrich_profile()                  │
│    - Ajoute data_category (continuous, categorical...) │
│    - Détecte field_purpose (identifier, measurement...) │
│    - Suggère bins pour numériques                      │
│    - Suggère labels pour catégoriels                   │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ 4. NEW: TransformerSuggester.suggest_transformers()    │
│    - Match semantic metadata → transformers            │
│    - Génère config pré-remplie                         │
│    - Retourne suggestions triées par pertinence        │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ 5. MODIFIED: EntityRegistry.register_entity()          │
│    - Ajouter semantic_profile au config                │
│    - Persister pour réutilisation                      │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ 6. GUI: Afficher suggestions                           │
│    - Liste transformers suggérés par colonne           │
│    - Config pré-remplie modifiable                     │
│    - Boutons "Appliquer" / "Personnaliser"             │
└─────────────────────────────────────────────────────────┘
```

### Module 1 : DataAnalyzer (nouveau)

**Fichier :** `src/niamoto/core/imports/data_analyzer.py` (~300 lignes)

**Responsabilité :** Enrichir ColumnProfile avec métadonnées orientées transformers

**Nouvelles enums :**

```python
class DataCategory(str, Enum):
    """Catégorie de données pour matching transformers."""
    NUMERIC_CONTINUOUS = "numeric_continuous"      # elevation, height, dbh
    NUMERIC_DISCRETE = "numeric_discrete"          # count, age (integer)
    CATEGORICAL = "categorical"                     # species, family, status
    CATEGORICAL_HIGH_CARD = "categorical_high_card" # IDs (beaucoup de valeurs)
    BOOLEAN = "boolean"                            # true/false
    TEMPORAL = "temporal"                          # dates
    GEOGRAPHIC = "geographic"                      # lat/lon, geometry
    TEXT = "text"                                  # descriptions
    IDENTIFIER = "identifier"                      # primary keys

class FieldPurpose(str, Enum):
    """Usage typique du champ."""
    PRIMARY_KEY = "primary_key"
    FOREIGN_KEY = "foreign_key"
    MEASUREMENT = "measurement"
    CLASSIFICATION = "classification"
    LOCATION = "location"
    DESCRIPTION = "description"
    METADATA = "metadata"
```

**Nouvelle structure :**

```python
@dataclass
class EnrichedColumnProfile:
    """Extension de ColumnProfile avec métadonnées pour transformers."""

    # Hérité de ColumnProfile
    name: str
    dtype: str
    semantic_type: Optional[str]
    unique_ratio: float
    null_ratio: float
    sample_values: List[Any]
    confidence: float

    # Enrichissements nouveaux
    data_category: DataCategory
    field_purpose: FieldPurpose
    suggested_bins: Optional[List[float]] = None
    suggested_labels: Optional[List[str]] = None
    cardinality: int = 0
    value_range: Optional[tuple] = None  # (min, max)
```

**Classe principale :**

```python
class DataAnalyzer:
    def enrich_profile(
        self,
        col_profile: ColumnProfile,
        series: pd.Series
    ) -> EnrichedColumnProfile:
        """Enrichir un ColumnProfile avec métadonnées."""

        # Détecter catégorie de données
        data_category = self._detect_data_category(col_profile, series)

        # Détecter purpose
        field_purpose = self._detect_field_purpose(col_profile, series)

        # Suggérer bins si numérique continu
        suggested_bins = None
        if data_category == DataCategory.NUMERIC_CONTINUOUS:
            suggested_bins = self._suggest_bins(series)

        # Suggérer labels si catégoriel
        suggested_labels = None
        if data_category == DataCategory.CATEGORICAL:
            suggested_labels = self._suggest_labels(series)

        return EnrichedColumnProfile(...)
```

**Logique de détection :**

```python
def _detect_data_category(self, col_profile, series) -> DataCategory:
    # Geographic
    if col_profile.semantic_type in ['geometry', 'location.*']:
        return DataCategory.GEOGRAPHIC

    # Temporal
    if 'datetime' in col_profile.dtype:
        return DataCategory.TEMPORAL

    # Numeric
    if pd.api.types.is_numeric_dtype(series):
        # Boolean disguised as 0/1
        if series.dropna().isin([0, 1]).all():
            return DataCategory.BOOLEAN

        # Integer = discrete or ID
        if (series % 1 == 0).all():
            if col_profile.unique_ratio > 0.8:
                return DataCategory.CATEGORICAL_HIGH_CARD  # IDs
            return DataCategory.NUMERIC_DISCRETE

        return DataCategory.NUMERIC_CONTINUOUS

    # Categorical
    if col_profile.unique_ratio < 0.5:
        return DataCategory.CATEGORICAL
    elif col_profile.unique_ratio > 0.95:
        return DataCategory.IDENTIFIER

    return DataCategory.CATEGORICAL_HIGH_CARD
```

**Suggestion de bins intelligente :**

```python
def _suggest_bins(self, series: pd.Series) -> List[float]:
    """Suggérer bins basés sur quantiles."""
    clean = series.dropna()
    if clean.empty:
        return []

    # Utiliser quantiles pour meilleure distribution
    quantiles = [0, 0.25, 0.5, 0.75, 1.0]
    bins = [float(clean.quantile(q)) for q in quantiles]

    # Supprimer doublons et trier
    bins = sorted(list(set(bins)))

    return bins if len(bins) >= 2 else [float(clean.min()), float(clean.max())]
```

### Module 2 : TransformerSuggester (nouveau)

**Fichier :** `src/niamoto/core/imports/transformer_suggester.py` (~250 lignes)

**Responsabilité :** Matcher colonnes enrichies → transformers + générer configs

**Structure de suggestion :**

```python
@dataclass
class TransformerSuggestion:
    transformer_name: str
    confidence: float  # 0.0 to 1.0
    reason: str
    pre_filled_config: Dict[str, Any]
    column_name: str
```

**Mapping catégorie → transformers :**

```python
class TransformerSuggester:
    CATEGORY_TO_TRANSFORMERS = {
        DataCategory.NUMERIC_CONTINUOUS: [
            "binned_distribution",
            "statistical_summary",
        ],
        DataCategory.NUMERIC_DISCRETE: [
            "categorical_distribution",
            "top_ranking",
        ],
        DataCategory.CATEGORICAL: [
            "categorical_distribution",
            "top_ranking",
        ],
        DataCategory.CATEGORICAL_HIGH_CARD: [
            "top_ranking",
        ],
        DataCategory.BOOLEAN: [
            "binary_counter",
        ],
        DataCategory.GEOGRAPHIC: [
            "geospatial_extractor",
        ],
        DataCategory.TEMPORAL: [
            "time_series_analysis",
        ],
        DataCategory.IDENTIFIER: [],  # Pas de transformer
    }
```

**Génération de config pré-remplie :**

```python
def _generate_config(
    self,
    transformer_name: str,
    profile: EnrichedColumnProfile,
    source_entity: str
) -> Optional[Dict[str, Any]]:
    """Générer config pré-remplie."""

    if transformer_name == "binned_distribution":
        return {
            "plugin": "binned_distribution",
            "params": {
                "source": source_entity,
                "field": profile.name,
                "bins": profile.suggested_bins,
                "labels": None,
                "include_percentages": False
            }
        }

    elif transformer_name == "statistical_summary":
        # Inférer units du semantic_type
        units = ""
        if "elevation" in profile.semantic_type or "height" in profile.semantic_type:
            units = "m"
        elif "diameter" in profile.semantic_type:
            units = "cm"

        return {
            "plugin": "statistical_summary",
            "params": {
                "source": source_entity,
                "field": profile.name,
                "stats": ["min", "mean", "max", "median", "std"],
                "units": units,
                "max_value": int(profile.value_range[1]) if profile.value_range else 100
            }
        }

    # ... autres transformers
```

**Calcul de confiance :**

```python
def _calculate_confidence(self, transformer_name, profile) -> float:
    base_confidence = profile.confidence  # From ML

    # Pénalité pour valeurs nulles
    quality_factor = 1.0 - (profile.null_ratio * 0.3)

    # Boost pour category match
    category_match_boost = 0.0
    if transformer_name in self.CATEGORY_TO_TRANSFORMERS.get(profile.data_category, []):
        category_match_boost = 0.2

    # Boost spécifiques
    if transformer_name == "binned_distribution":
        if profile.suggested_bins and len(profile.suggested_bins) >= 3:
            category_match_boost += 0.1

    confidence = min(1.0, base_confidence * quality_factor + category_match_boost)
    return round(confidence, 2)
```

### Module 3 : Intégration Import Pipeline

**Fichier à modifier :** `src/niamoto/core/imports/engine.py`

**Ajouter dans GenericImporter.__init__ :**

```python
from niamoto.core.imports.data_analyzer import DataAnalyzer
from niamoto.core.imports.transformer_suggester import TransformerSuggester

class GenericImporter:
    def __init__(self, db: Database, registry: EntityRegistry):
        self.db = db
        self.registry = registry
        self.data_analyzer = DataAnalyzer()
        self.transformer_suggester = TransformerSuggester(registry)
```

**Nouvelle méthode :**

```python
def _analyze_for_transformers(
    self,
    df: pd.DataFrame,
    csv_path: Path,
    entity_name: str
) -> Dict[str, Any]:
    """Analyser données et suggérer transformers."""

    from niamoto.core.imports.profiler import DataProfiler

    # 1. Profile avec DataProfiler existant
    profiler = DataProfiler(ml_detector=None)
    dataset_profile = profiler.profile(csv_path)

    # 2. Enrichir chaque colonne
    enriched_profiles = []
    for col_profile in dataset_profile.columns:
        if col_profile.name in df.columns:
            enriched = self.data_analyzer.enrich_profile(
                col_profile,
                df[col_profile.name]
            )
            enriched_profiles.append(enriched)

    # 3. Suggérer transformers
    suggestions = self.transformer_suggester.suggest_for_dataset(
        enriched_profiles,
        entity_name
    )

    # 4. Construire semantic_profile
    return {
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "columns": [
            {
                "name": ep.name,
                "data_category": ep.data_category.value,
                "field_purpose": ep.field_purpose.value,
                "cardinality": ep.cardinality,
                "suggested_bins": ep.suggested_bins,
            }
            for ep in enriched_profiles
        ],
        "transformer_suggestions": {
            col_name: [
                {
                    "transformer": s.transformer_name,
                    "confidence": s.confidence,
                    "reason": s.reason,
                    "config": s.pre_filled_config
                }
                for s in suggestions_list
            ]
            for col_name, suggestions_list in suggestions.items()
        }
    }
```

**Intégration dans import_from_csv :**

```python
def import_from_csv(...):
    # ... existing import logic ...

    # NOUVEAU: Analyse sémantique
    semantic_profile = self._analyze_for_transformers(
        df=df,
        csv_path=csv_path,
        entity_name=entity_name
    )

    # Ajouter au metadata
    metadata = self._build_metadata(...)
    metadata["semantic_profile"] = semantic_profile  # NOUVEAU

    self.registry.register_entity(
        name=entity_name,
        kind=kind,
        table_name=table_name,
        config=metadata,
    )
```

### Module 4 : API pour GUI

**Nouveau fichier :** `src/niamoto/gui/api/routes/transformer_suggestions.py`

```python
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from pydantic import BaseModel

router = APIRouter(prefix="/api/transformer-suggestions", tags=["transformers"])

class TransformerSuggestionResponse(BaseModel):
    entity_name: str
    columns: List[Dict[str, Any]]
    suggestions: Dict[str, List[Dict[str, Any]]]

@router.get("/{entity_name}", response_model=TransformerSuggestionResponse)
async def get_transformer_suggestions(entity_name: str):
    """Récupérer suggestions pour une entité."""

    # Get database and registry (from context)
    db = Database(...)
    registry = EntityRegistry(db)

    # Get entity metadata
    metadata = registry.get(entity_name)
    if not metadata or not metadata.config:
        raise HTTPException(status_code=404, detail="Entity not found")

    # Get semantic_profile
    semantic_profile = metadata.config.get("semantic_profile")
    if not semantic_profile:
        raise HTTPException(
            status_code=404,
            detail="No semantic analysis available"
        )

    return TransformerSuggestionResponse(
        entity_name=entity_name,
        columns=semantic_profile["columns"],
        suggestions=semantic_profile["transformer_suggestions"]
    )
```

**Intégrer dans main.py :**

```python
from niamoto.gui.api.routes import transformer_suggestions

app.include_router(transformer_suggestions.router)
```

### Module 5 : Interface GUI (React)

**Nouveau fichier :** `src/niamoto/gui/ui/src/components/transformers/TransformerSuggestions.tsx`

```typescript
interface Suggestion {
  transformer: string;
  confidence: number;
  reason: string;
  config: any;
}

interface Props {
  entityName: string;
}

export const TransformerSuggestions: React.FC<Props> = ({ entityName }) => {
  const [suggestions, setSuggestions] = useState<Record<string, Suggestion[]>>({});

  useEffect(() => {
    fetch(`/api/transformer-suggestions/${entityName}`)
      .then(res => res.json())
      .then(data => setSuggestions(data.suggestions));
  }, [entityName]);

  const handleApply = (columnName: string, suggestion: Suggestion) => {
    // Ajouter au transform.yml
    console.log(`Applying ${suggestion.transformer} to ${columnName}`);
  };

  return (
    <div className="transformer-suggestions">
      <h2>✨ Transformations Suggérées</h2>

      {Object.entries(suggestions).map(([column, columnSuggestions]) => (
        <div key={column} className="column-suggestions">
          <h3>Colonne: {column}</h3>

          {columnSuggestions.map((suggestion, i) => (
            <SuggestionCard
              key={i}
              suggestion={suggestion}
              onApply={() => handleApply(column, suggestion)}
            />
          ))}
        </div>
      ))}

      <button onClick={handleApplyAll}>Appliquer tout</button>
    </div>
  );
};
```

---

## Plan d'implémentation

### Phase 1 : Core Infrastructure (3-4 jours)

#### Étape 1.1 : DataAnalyzer
- **Fichier :** `src/niamoto/core/imports/data_analyzer.py`
- **Classes :** `DataCategory`, `FieldPurpose`, `EnrichedColumnProfile`, `DataAnalyzer`
- **Tests :** `tests/core/imports/test_data_analyzer.py`
- **Effort :** 1.5 jours

**Tâches :**
1. Créer enums DataCategory et FieldPurpose
2. Créer dataclass EnrichedColumnProfile
3. Implémenter DataAnalyzer.enrich_profile()
4. Implémenter _detect_data_category()
5. Implémenter _detect_field_purpose()
6. Implémenter _suggest_bins() avec quantiles
7. Implémenter _suggest_labels()
8. Tests unitaires (15-20 tests)

#### Étape 1.2 : TransformerSuggester
- **Fichier :** `src/niamoto/core/imports/transformer_suggester.py`
- **Classe :** `TransformerSuggester`
- **Tests :** `tests/core/imports/test_transformer_suggester.py`
- **Effort :** 2 jours

**Tâches :**
1. Créer dataclass TransformerSuggestion
2. Définir CATEGORY_TO_TRANSFORMERS mapping
3. Implémenter suggest_transformers()
4. Implémenter _generate_config() pour chaque transformer
5. Implémenter _calculate_confidence()
6. Implémenter _generate_reason()
7. Tests unitaires (20-25 tests)

**Livrable Phase 1 :**
- ✅ DataAnalyzer enrichit ColumnProfile
- ✅ TransformerSuggester génère suggestions avec configs
- ✅ Tests passants

### Phase 2 : Intégration Pipeline (1-2 jours)

#### Étape 2.1 : Modifier GenericImporter
- **Fichier :** `src/niamoto/core/imports/engine.py`
- **Effort :** 1 jour

**Tâches :**
1. Ajouter data_analyzer et transformer_suggester dans __init__
2. Créer _analyze_for_transformers()
3. Intégrer dans import_from_csv()
4. Modifier _build_metadata() pour inclure semantic_profile
5. Tests d'intégration

#### Étape 2.2 : Vérifier Persistence
- **Effort :** 0.5 jour

**Tâches :**
1. Vérifier stockage JSON dans EntityRegistry
2. Tester récupération metadata avec semantic_profile
3. Valider structure données

**Livrable Phase 2 :**
- ✅ Import CSV génère suggestions automatiquement
- ✅ Metadata persistée dans database
- ✅ Tests d'intégration passants

### Phase 3 : API GUI (1 jour)

#### Étape 3.1 : Créer endpoints
- **Fichier :** `src/niamoto/gui/api/routes/transformer_suggestions.py`
- **Effort :** 0.5 jour

**Tâches :**
1. Créer router FastAPI
2. Endpoint GET /api/transformer-suggestions/{entity_name}
3. Modèle Pydantic TransformerSuggestionResponse
4. Gestion erreurs (404, 500)

#### Étape 3.2 : Intégrer API
- **Fichier :** `src/niamoto/gui/api/main.py`
- **Effort :** 0.5 jour

**Tâches :**
1. Ajouter router dans main.py
2. Tester endpoint avec curl/Postman
3. Vérifier documentation OpenAPI

**Livrable Phase 3 :**
- ✅ Endpoint REST fonctionnel
- ✅ Documentation OpenAPI générée

### Phase 4 : Interface GUI - Transform.yml (2-3 jours)

#### Étape 4.1 : Composants React
- **Fichiers :**
  - `TransformerSuggestions.tsx`
  - `SuggestionCard.tsx`
- **Effort :** 1.5 jours

**Tâches :**
1. Créer TransformerSuggestions component
2. Créer SuggestionCard component
3. Fetch suggestions depuis EntityRegistry via API
4. Affichage liste par colonne
5. Boutons Appliquer/Personnaliser
6. Gestion état draft (localStorage)

#### Étape 4.2 : Intégration Workspace Transform
- **Fichier :** `src/niamoto/gui/ui/src/pages/Transform.tsx`
- **Effort :** 1 jour

**Tâches :**
1. Lire suggestions depuis EntityRegistry (semantic_profile)
2. Afficher suggestions dans workspace Transform
3. Workflow : Import → Analyse → Suggestions → Configuration
4. Bouton "Appliquer" qui sérialise vers transform.yml
5. Utiliser useConfig pour backup/écriture
6. Preview config avant application
7. Mode draft avec localStorage (modifications non appliquées)

**Livrable Phase 4 :**
- ✅ Interface complète pour transform.yml
- ✅ Workflow fluide avec draft mode
- ✅ Intégration EntityRegistry

### Phase 4 bis : Génération Export.yml - Widgets & Pages (2-3 jours)

#### Contexte
Une fois que l'utilisateur a accepté les transformers suggérés, le système doit également :
1. Détecter les widgets compatibles avec chaque transformer (via SmartMatcher)
2. Générer des "group blueprints" (taxon/plot/shape) avec widgets initiaux
3. Créer les blocs d'export.yml correspondants

#### Étape 4bis.1 : Widget Mapping & Group Blueprints
- **Fichier :** `src/niamoto/core/imports/widget_mapper.py` (nouveau)
- **Effort :** 1.5 jours

**Nouvelle classe :**

```python
from typing import Dict, List, Any
from niamoto.core.plugins.matching import SmartMatcher

class WidgetMapper:
    """Mappe transformers acceptés → widgets compatibles."""

    def __init__(self):
        self.matcher = SmartMatcher()

    def generate_group_blueprints(
        self,
        accepted_transformers: Dict[str, Dict],
        source_entity: str
    ) -> Dict[str, Any]:
        """
        Génère blueprints par groupe (taxon/plot/shape).

        Args:
            accepted_transformers: {transformer_key: {plugin, params}}
            source_entity: Nom de l'entité source (ex: "occurrences")

        Returns:
            {
                "groups": {
                    "taxon": {
                        "widgets": [...],
                        "data_sources": {...}
                    },
                    "plot": {...},
                    "shape": {...}
                }
            }
        """
        groups = {
            "taxon": {"widgets": [], "data_sources": {}},
            "plot": {"widgets": [], "data_sources": {}},
            "shape": {"widgets": [], "data_sources": {}},
        }

        # Pour chaque transformer accepté
        for trans_key, trans_config in accepted_transformers.items():
            plugin_name = trans_config["plugin"]

            # Récupérer classe transformer depuis registry
            from niamoto.core.plugins.registry import PluginRegistry
            from niamoto.core.plugins.base import PluginType

            transformer_class = PluginRegistry.get_plugin(
                plugin_name,
                PluginType.TRANSFORMER
            )

            if not transformer_class:
                continue

            # Trouver widgets compatibles via SmartMatcher
            widget_suggestions = self.matcher.find_compatible_widgets(
                transformer_class
            )

            # Prendre le meilleur widget (score le plus élevé)
            if widget_suggestions:
                best_widget = widget_suggestions[0]

                # Déterminer le groupe cible
                group = self._infer_group(trans_config, source_entity)

                # Créer widget config
                widget_config = {
                    "widget": best_widget.widget_name,
                    "params": {
                        "data_source": trans_key,
                        "title": f"{trans_config['params']['field']} - {plugin_name}",
                    }
                }

                groups[group]["widgets"].append(widget_config)
                groups[group]["data_sources"][trans_key] = {
                    "transformer": plugin_name,
                    "params": trans_config["params"]
                }

        return {"groups": groups}

    def _infer_group(self, trans_config: Dict, source_entity: str) -> str:
        """Inférer le groupe cible (taxon/plot/shape)."""
        # Heuristique simple basée sur semantic_type ou field name
        field = trans_config.get("params", {}).get("field", "")

        if "taxon" in field.lower() or "species" in field.lower():
            return "taxon"
        elif "plot" in field.lower():
            return "plot"
        elif "geo" in field.lower() or "location" in field.lower():
            return "shape"

        # Défaut: taxon
        return "taxon"
```

**Tâches :**
1. Créer WidgetMapper avec intégration SmartMatcher
2. Implémenter generate_group_blueprints()
3. Implémenter _infer_group() avec heuristiques
4. Générer configs widget avec data_source mappings
5. Tests unitaires (10-15 tests)

#### Étape 4bis.2 : Export Config Generator
- **Fichier :** `src/niamoto/core/imports/export_config_generator.py` (nouveau)
- **Effort :** 1 jour

**Nouvelle classe :**

```python
from typing import Dict, Any, List

class ExportConfigGenerator:
    """Génère blocs export.yml depuis group blueprints."""

    def generate_export_blocks(
        self,
        group_blueprints: Dict[str, Any],
        existing_export_config: Dict = None
    ) -> Dict[str, Any]:
        """
        Génère ou met à jour export.yml avec nouveaux widgets.

        Returns:
            {
                "groups": {
                    "taxon": {
                        "widget_data": [
                            {
                                "group_key": "elevation_dist",
                                "widget": "bar_plot",
                                "params": {...}
                            },
                            ...
                        ]
                    },
                    ...
                }
            }
        """
        export_config = existing_export_config or {"groups": {}}

        for group_name, blueprint in group_blueprints["groups"].items():
            if group_name not in export_config["groups"]:
                export_config["groups"][group_name] = {"widget_data": []}

            # Ajouter widgets depuis blueprint
            for widget_cfg in blueprint["widgets"]:
                widget_entry = {
                    "group_key": widget_cfg["params"]["data_source"],
                    "widget": widget_cfg["widget"],
                    "params": widget_cfg["params"]
                }

                export_config["groups"][group_name]["widget_data"].append(
                    widget_entry
                )

        return export_config
```

**Tâches :**
1. Créer ExportConfigGenerator
2. Implémenter generate_export_blocks()
3. Gestion merge avec export.yml existant
4. Tests unitaires

#### Étape 4bis.3 : Intégration GUI - Export Generation
- **Fichier :** `src/niamoto/gui/ui/src/pages/Transform.tsx` (modifier)
- **Effort :** 0.5 jour

**Tâches :**
1. Étendre bouton "Appliquer" pour générer BOTH transform.yml ET export.yml
2. Appeler API pour widget mapping
3. Générer group blueprints
4. Sérialiser vers export.yml via useConfig
5. Preview dual (transform + export)

**Nouveau endpoint API :**

```python
# src/niamoto/gui/api/routes/transformer_suggestions.py

@router.post("/apply-suggestions", response_model=ApplySuggestionsResponse)
async def apply_suggestions(request: ApplySuggestionsRequest):
    """
    Applique suggestions et génère BOTH transform.yml + export.yml.

    Request:
        {
            "accepted_transformers": {
                "elevation_dist": {
                    "plugin": "binned_distribution",
                    "params": {...}
                },
                ...
            },
            "source_entity": "occurrences"
        }

    Response:
        {
            "transform_config": {...},  # Pour transform.yml
            "export_config": {...},     # Pour export.yml
            "widgets_mapped": 5
        }
    """
    from niamoto.core.imports.widget_mapper import WidgetMapper
    from niamoto.core.imports.export_config_generator import ExportConfigGenerator

    # 1. Générer group blueprints
    mapper = WidgetMapper()
    blueprints = mapper.generate_group_blueprints(
        request.accepted_transformers,
        request.source_entity
    )

    # 2. Générer export config
    generator = ExportConfigGenerator()
    export_config = generator.generate_export_blocks(blueprints)

    # 3. Retourner both configs
    return {
        "transform_config": request.accepted_transformers,
        "export_config": export_config,
        "widgets_mapped": sum(
            len(g["widgets"])
            for g in blueprints["groups"].values()
        )
    }
```

**Livrable Phase 4 bis :**
- ✅ Widget mapping automatique via SmartMatcher
- ✅ Group blueprints générés (taxon/plot/shape)
- ✅ Export.yml généré avec data_source mappings
- ✅ Bouton "Appliquer" génère BOTH configs
- ✅ Tests unitaires passants

### Phase 5 : Tests & Documentation (1 jour)

#### Étape 5.1 : Tests End-to-End
- **Effort :** 0.5 jour

**Tâches :**
1. Test complet : Upload CSV → Suggestions → Apply
2. Test edge cases (colonnes vides, types mixtes...)
3. Test performance (gros fichiers)

#### Étape 5.2 : Documentation
- **Effort :** 0.5 jour

**Tâches :**
1. README avec exemples
2. Documentation utilisateur
3. Documentation API
4. Guide développeur pour ajouter nouveaux transformers

**Livrable Phase 5 :**
- ✅ MVP fonctionnel et testé
- ✅ Documentation complète

### Calendrier récapitulatif

| Phase | Durée | Tâches principales |
|-------|-------|-------------------|
| **Phase 1** | 3-4j | DataAnalyzer + TransformerSuggester |
| **Phase 2** | 1-2j | Intégration pipeline d'import |
| **Phase 3** | 1j | API FastAPI |
| **Phase 4** | 2-3j | Interface React Transform.yml |
| **Phase 4 bis** | 2-3j | Widget Mapping + Export.yml Generation |
| **Phase 5** | 1j | Tests E2E + Documentation |
| **TOTAL** | **10-14j** | MVP complet avec export.yml |

---

## Pièges potentiels et solutions

### 1. Performance sur gros datasets

**Problème :** Analyse sémantique lente sur fichiers de plusieurs Go.

**Solutions :**
- ✅ **Sampling** (déjà dans profiler avec `nrows`)
- ✅ **Lazy analysis** : à la demande, pas lors de l'import
- ✅ **Caching** : persister résultats

**Recommandation MVP :** Sampling 10,000 lignes

### 2. Faux positifs dans détection

**Problème :** ML detector peut se tromper.

**Solutions :**
- ✅ **Seuil confiance** : N'afficher que > 0.6
- ✅ **Multiple suggestions** : Top 3 max par colonne
- ✅ **User feedback** : Permettre rejet/correction

**Recommandation MVP :** Seuil 0.6 + top 3

### 3. Config pré-remplie invalide

**Problème :** Bins ou paramètres invalides.

**Solutions :**
- ✅ **Validation Pydantic** avant génération
- ✅ **Fallback configs** : configs minimales par défaut
- ✅ **Mode Draft** : marquer "à vérifier"

**Recommandation MVP :** Validation systématique

### 4. Dépendances entre colonnes

**Problème :** Certains transformers nécessitent plusieurs colonnes (lat+lon).

**Solutions :**
- ✅ **Détection de patterns** : détecter paires lat/lon
- ✅ **Suggestions composées** : "Combiner lat + lon"
- ✅ **Smart grouping** : grouper suggestions liées

**Recommandation MVP :** Cas simples seulement (1 col = 1 transformer)
**Pour v2 :** Détection paires

### 5. Scalabilité du matching

**Problème :** 100 colonnes × 20 transformers = 2000 comparaisons.

**Solutions :**
- ✅ **Early filtering** : filtrer par data_category
- ✅ **Indexing** : CATEGORY_TO_TRANSFORMERS
- ✅ **Lazy loading** : calculer seulement pour colonnes visibles

**Recommandation MVP :** CATEGORY_TO_TRANSFORMERS (déjà optimisé)

### 6. Synchronisation GUI ↔ Backend

**Problème :** Modifications GUI perdues au reload.

**Solutions :**
- ✅ **Versioning** : draft vs applied
- ✅ **Auto-save** : localStorage
- ✅ **Diff visualization** : montrer changements

**Recommandation MVP :** Mode Draft en localStorage

---

## Exemple de workflow complet

### Scénario : Import occurrences botaniques

#### 1. Upload fichier

**Fichier :** `occurrences_nc.csv`

```csv
id_occurrence,id_taxonref,elevation,dbh,date_observation,plot_id
1,12345,450.5,25.3,2024-01-15,PLOT_001
2,12346,520.0,18.7,2024-01-16,PLOT_002
...
```

#### 2. DataProfiler analyse

```python
ColumnProfile(
    name="elevation",
    dtype="float64",
    semantic_type="measurement.elevation",
    unique_ratio=0.85,
    null_ratio=0.02,
    confidence=0.90
)
```

#### 3. DataAnalyzer enrichit

```python
EnrichedColumnProfile(
    name="elevation",
    data_category=DataCategory.NUMERIC_CONTINUOUS,
    field_purpose=FieldPurpose.MEASUREMENT,
    suggested_bins=[0, 250, 500, 750, 1000],
    value_range=(5.0, 1650.0),
    cardinality=1250
)
```

#### 4. TransformerSuggester génère

```python
[
    TransformerSuggestion(
        transformer_name="binned_distribution",
        confidence=0.85,
        reason="Type: numeric_continuous | Sémantique: measurement.elevation | 5 bins",
        pre_filled_config={
            "plugin": "binned_distribution",
            "params": {
                "source": "occurrences",
                "field": "elevation",
                "bins": [0, 250, 500, 750, 1000],
                "labels": None,
                "include_percentages": False
            }
        }
    ),
    TransformerSuggestion(
        transformer_name="statistical_summary",
        confidence=0.80,
        reason="Type: numeric_continuous | Statistiques descriptives",
        pre_filled_config={
            "plugin": "statistical_summary",
            "params": {
                "source": "occurrences",
                "field": "elevation",
                "stats": ["min", "mean", "max", "median", "std"],
                "units": "m",
                "max_value": 1650
            }
        }
    )
]
```

#### 5. GUI affiche

```
┌──────────────────────────────────────────────────┐
│ ✨ Suggestions pour "occurrences"                │
├──────────────────────────────────────────────────┤
│                                                   │
│ Colonne: elevation                                │
│  ✓ Distribution par intervalles (85% confiance)  │
│    └─ 5 bins: 0-250m, 250-500m, 500-750m...     │
│    [Appliquer] [Personnaliser]                   │
│                                                   │
│  ✓ Statistiques (80% confiance)                  │
│    └─ Min, Max, Moyenne, Médiane, Écart-type    │
│    [Appliquer] [Personnaliser]                   │
│                                                   │
│ Colonne: dbh                                      │
│  ✓ Distribution (82% confiance)                  │
│    └─ 5 bins: 0-20cm, 20-40cm...                │
│    [Appliquer]                                   │
│                                                   │
│ Colonne: id_taxonref                              │
│  ✓ Top 10 espèces (75% confiance)               │
│    └─ Top N des 245 valeurs                      │
│    [Appliquer]                                   │
│                                                   │
│ [Appliquer tout] [Personnaliser...]             │
└──────────────────────────────────────────────────┘
```

#### 6. Utilisateur clique "Appliquer tout"

Système effectue :
1. Génère transform.yml avec transformers acceptés
2. Utilise SmartMatcher pour trouver widgets compatibles
3. Génère group blueprints (taxon/plot/shape)
4. Génère export.yml avec widgets et data_sources

#### 7. transform.yml généré

```yaml
transformers:
  elevation_distribution:
    plugin: binned_distribution
    params:
      source: occurrences
      field: elevation
      bins: [0, 250, 500, 750, 1000]
      labels: null
      include_percentages: false

  elevation_stats:
    plugin: statistical_summary
    params:
      source: occurrences
      field: elevation
      stats: [min, mean, max, median, std]
      units: m
      max_value: 1650

  dbh_distribution:
    plugin: binned_distribution
    params:
      source: occurrences
      field: dbh
      bins: [0, 20, 40, 60, 80]
      labels: null
      include_percentages: false

  top_species:
    plugin: top_ranking
    params:
      source: occurrences
      field: id_taxonref
      count: 10
      mode: direct
      aggregate_function: count
```

#### 8. export.yml généré (automatique via SmartMatcher)

```yaml
groups:
  taxon:
    widget_data:
      - group_key: elevation_distribution
        widget: bar_plot  # SmartMatcher: score=1.0 (exact_match)
        params:
          data_source: elevation_distribution
          title: "Distribution altitudinale"
          x_label: "Altitude (m)"
          y_label: "Nombre d'occurrences"

      - group_key: elevation_stats
        widget: radial_gauge  # SmartMatcher: score=1.0 (exact_match)
        params:
          data_source: elevation_stats
          value_field: "mean"
          max_value: 1650
          title: "Altitude moyenne"
          unit: "m"

      - group_key: dbh_distribution
        widget: bar_plot  # SmartMatcher: score=1.0 (exact_match)
        params:
          data_source: dbh_distribution
          title: "Distribution des diamètres"
          x_label: "DBH (cm)"
          y_label: "Nombre d'individus"

      - group_key: top_species
        widget: bar_plot  # SmartMatcher: score=1.0 (exact_match)
        params:
          data_source: top_species
          title: "Top 10 des espèces"
          x_label: "Espèce"
          y_label: "Nombre d'occurrences"
```

**Note :** Le widget mapping est entièrement automatique grâce au système de pattern matching bidirectionnel :
- `binned_distribution.output_structure` → `bar_plot.compatible_structures` = exact_match
- `statistical_summary.output_structure` → `radial_gauge.compatible_structures` = exact_match

---

## Conclusion et recommandations

### Points forts de l'approche

1. ✅ **Réutilisation maximale** : DataProfiler et MLColumnDetector existent
2. ✅ **Architecture propre** : Séparation analyzer → suggester → persistence
3. ✅ **Configs pré-remplies** : UX fluide, clic "Appliquer"
4. ✅ **Extensible** : Facile d'ajouter nouveaux transformers

### Priorités pour le MVP

**PRIORITÉ 1 (Essentiel) :**
- DataAnalyzer avec data_category detection
- TransformerSuggester avec top 3-4 transformers
- Persister semantic_profile
- API endpoint

**PRIORITÉ 2 (Important) :**
- GUI affichage suggestions
- Bouton "Appliquer" → génère transform.yml
- Tests unitaires

**PRIORITÉ 3 (Nice-to-have) :**
- Mode "Personnaliser" avec formulaire
- Feedback utilisateur (thumbs up/down)
- Détection paires (lat+lon)

### Prochaines étapes

1. ✅ Valider architecture
2. 🔄 Commencer par DataAnalyzer (isolé, tests faciles)
3. 🔄 Intégrer dans pipeline d'import
4. 🔄 Tester avec vraies données NC
5. 🔄 Itérer sur seuils de confiance

### Effort total

**MVP complet avec export.yml : 10-14 jours**

### Intégration points clés

1. **EntityRegistry :** Semantic_profile persisté et lu via registry
2. **useConfig :** Utilisé pour backup/écriture des deux configs (transform + export)
3. **SmartMatcher :** Génère automatiquement le mapping transformer→widget
4. **Draft mode :** localStorage pour modifications non appliquées
5. **Group blueprints :** Génère automatiquement taxon/plot/shape avec widgets initiaux

---

**Document créé le :** 2025-01-23
**Dernière mise à jour :** 2025-01-24
**Version :** 1.1
**Auteur :** Claude Code + Agent Plan
**Statut :** ✅ Plan validé et étendu (transform.yml + export.yml), prêt pour implémentation

## Changelog

### v1.1 (2025-01-24)
- ✅ Ajout Phase 4 bis : Export.yml generation
- ✅ WidgetMapper avec SmartMatcher integration
- ✅ ExportConfigGenerator pour group blueprints
- ✅ API endpoint pour dual config generation
- ✅ Exemple complet avec export.yml généré
- ✅ Mise à jour effort estimé : 10-14 jours
- ✅ Points d'intégration documentés (EntityRegistry, useConfig, draft mode)

### v1.0 (2025-01-23)
- ✅ Architecture initiale DataAnalyzer + TransformerSuggester
- ✅ Plan 5 phases pour transform.yml generation
- ✅ Effort estimé : 8-11 jours
