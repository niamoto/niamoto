# État de la Refactorisation Import Générique - 20 Janvier 2025

**Date de l'audit**: 20 janvier 2025
**Auditeur**: Claude Code
**Version Niamoto**: Alpha (branche feat/pipeline-editor-unified)

---

## 🏗️ INSTANCE DE TEST & RÉFÉRENCES

### Instance de Test Officielle
**Chemin**: `/Users/julienbarbe/Dev/Niamoto/Niamoto/test-instance/niamoto-nc`

Cette instance sert de **référence unique** pour tous les tests et validations :
- Configuration actuelle (import v2, transform, export)
- Base de données DuckDB opérationnelle
- Source de vérité pour les exemples de migration
- Environnement de validation end-to-end

**Structure**:
```
test-instance/niamoto-nc/
├── config/
│   ├── import.yml      # ✅ Format v2 (entities/references/datasets)
│   ├── transform.yml   # ⚠️ Références hardcodées (à migrer)
│   └── export.yml      # ⚠️ Références hardcodées (à valider)
├── db/
│   └── niamoto.duckdb  # Base DuckDB avec données réelles
├── imports/            # Fichiers CSV sources
│   ├── occurrences.csv # ~203k occurrences
│   └── ...
├── exports/            # Outputs générés
└── templates/          # Templates HTML
```

### Configurations de Référence

#### Import Config (✅ Format v2 Opérationnel)
**Fichier**: `test-instance/niamoto-nc/config/import.yml`
- Format: Version 2 (entities/references/datasets)
- Statut: ✅ Fonctionnel avec nouveau système
- Entities définies:
  - **Dataset**: `occurrences` (CSV, 203k+ rows)
  - **Reference**: `taxons` (DERIVED depuis occurrences, adjacency_list)
  - **Reference**: `plots` (FILE, CSV avec géométries)
  - **Reference**: `shapes` (FILE, multi-sources spatiales)

#### Transform Config (⚠️ À Migrer)
**Fichier**: `test-instance/niamoto-nc/config/transform.yml`
- Format: Legacy avec noms tables hardcodés
- Problèmes identifiés:
  - Ligne 11: `group_by: taxons` (hardcodé)
  - Ligne 14: `data: occurrences` (hardcodé)
  - Ligne 15: `grouping: taxons` (hardcodé)
  - Ligne 17: `plugin: nested_set` (non migré!)
- **Action requise**: Migration Phase 3

#### Export Config (⚠️ À Valider)
**Fichier**: `test-instance/niamoto-nc/config/export.yml`
- Statut: Non audité en détail
- Taille: 1602 lignes
- **Action requise**: Audit Phase 3

### Base de Données de Test
**Fichier**: `test-instance/niamoto-nc/db/niamoto.duckdb`
- Engine: DuckDB (post-migration depuis SQLite)
- Extension: Spatial activée
- Contenu:
  - **entity_occurrences**: 203,865 rows (occurrences géolocalisées)
  - **entity_taxons**: 1,667 rows (taxonomie extraite)
  - **entity_plots**: ~XX rows (sites d'observation)
  - **entity_shapes**: Multi-layers (provinces, zones écologiques)
  - **niamoto_metadata_entities**: Registry persisté
  - **transform_groups_***: Tables stats transformées

**Commandes Utiles**:
```bash
# Lister tables
uv run python scripts/query_db.py --list-tables

# Query exemple
uv run python scripts/query_db.py "SELECT COUNT(*) FROM entity_occurrences"

# Décrire schema
uv run python scripts/query_db.py --describe entity_taxons

# Mode interactif
uv run python scripts/query_db.py --interactive
```

### Validation des Changements

**Tous les tests et validations doivent**:
1. ✅ Exécuter depuis `test-instance/niamoto-nc/`
2. ✅ Utiliser les configs de cette instance
3. ✅ Valider contre la DB `niamoto.duckdb`
4. ✅ Comparer résultats avant/après changements
5. ✅ Documenter écarts dans ce fichier

**Workflow de Test Standard**:
```bash
# 1. Naviguer vers l'instance
cd test-instance/niamoto-nc

# 2. Réinitialiser DB (si nécessaire)
rm db/niamoto.duckdb
niamoto init

# 3. Exécuter import
niamoto import

# 4. Exécuter transform
niamoto transform

# 5. Exécuter export
niamoto export

# 6. Valider résultats
ls -lh exports/web/
ls -lh exports/data/
```

---

## 📊 RÉSUMÉ EXÉCUTIF

### État Global
**Progression réelle: ~60% (vs 95% annoncé dans la documentation)**

⚠️ **ALERTE CRITIQUE**: Les ADR et roadmaps indiquent "Phase 8 complete - All 19 plugins refactored" (2025-10-13), mais l'audit du code révèle que **seulement 7/49 plugins sont migrés (14%)**.

### Points Clés
- ✅ **Backend Core**: 100% fonctionnel (EntityRegistry, Import Engine, DuckDB)
- ⚠️ **Plugins**: 14% migrés (7/49) - **42 plugins restants**
- ❌ **GUI Frontend**: 0% - Interface legacy hardcodée
- ⚠️ **Configuration**: Format mixte (v1 + v2)
- ✅ **Tests**: 100% passing (1609 tests)
- ❌ **Documentation**: Déconnectée de la réalité du code

### Écart Documentation vs Réalité
| Document | Statut Annoncé | Statut Réel |
|----------|---------------|-------------|
| ADR 0004 | "All 19 plugins refactored" | **7/49 plugins migrés (14%)** |
| Roadmap | "Phase 8 complete (2025-10-13)" | **Phase 8 à 14% seulement** |
| Roadmap | "GUI adapted" | **GUI 0% - Wizard legacy actif** |

---

## ✅ CE QUI EST TERMINÉ

### 1. Core Backend - 100% ✅

#### EntityRegistry
- **Fichier**: `src/niamoto/core/imports/registry.py`
- **Statut**: Opérationnel
- **Features**:
  - Métadonnées persistées en DuckDB (`niamoto_metadata_entities`)
  - API CRUD complète (`register_entity`, `get`, `list_entities`)
  - Support aliases (obsolète: `legacy_registry.py` supprimé)
  - Résolution table names: `get_table_name(entity_name)`
- **Tests**: ✅ Tous passing

#### Generic Import Engine
- **Fichier**: `src/niamoto/core/imports/engine.py`
- **Statut**: Opérationnel
- **Features**:
  - Connecteurs: FILE (CSV/GeoPackage/Shapefile), DERIVED (CTE extraction)
  - Import 3 phases: datasets → derived references → direct references
  - Validation schéma Pydantic (`config_models.py`)
  - Gestion erreurs et rollback
- **Tests**: ✅ Integration tests passing

#### DuckDB Migration
- **ADR**: 0001 - Adopt DuckDB
- **Statut**: Complète
- **Changements**:
  - SQLite remplacé par DuckDB pour analytics
  - Extension spatiale active
  - Recursive CTEs pour hiérarchies (adjacency list)
  - `Database` class adaptée (`common/database.py`)
- **Legacy Code Supprimé**:
  - ❌ `core/components/imports/*` (TaxonomyImporter, PlotImporter, etc.)
  - ❌ `core/models/models.py` (SQLAlchemy models rigides)
  - ❌ `core/repositories/niamoto_repository.py`
  - ❌ `legacy_registry.py`

#### Derived References
- **ADR**: 0003 - Derived References with DuckDB CTEs
- **Fichier**: `src/niamoto/core/imports/hierarchy_builder.py`
- **Statut**: Opérationnel
- **Features**:
  - Extraction hiérarchies depuis datasets (CTE-based)
  - Hash-based IDs stables (MD5 de path hiérarchique)
  - Adjacency list vs nested sets
  - Validation intégrité hiérarchique
- **Exemple**: Taxonomie extraite depuis `occurrences` CSV

#### CLI Commands
- **Statut**: Migré vers nouveau système
- **Commandes**:
  - `niamoto import` → Utilise EntityRegistry + ImportEngine
  - `niamoto transform` → Consomme registry (partiellement)
  - `niamoto export` → Consomme registry (partiellement)
- **Tests CLI**: ✅ `tests/cli/test_imports.py` passing

### 2. API Backend GUI - 90% ✅

#### Endpoints REST
- **Fichier**: `src/niamoto/gui/api/routers/imports.py`
- **Statut**: Opérationnel
- **Endpoints**:
  - `POST /api/imports/execute/all` - Import toutes entities
  - `POST /api/imports/execute/reference/{name}` - Import reference spécifique
  - `POST /api/imports/execute/dataset/{name}` - Import dataset spécifique
  - `GET /api/imports/jobs/{job_id}` - Status import asynchrone
  - `GET /api/imports/status` - État de tous les imports
  - `GET /api/imports/entities` - Liste entities disponibles
  - `POST /api/files/analyze` - Détection colonnes/types fichiers

#### Job Tracking System
- **Statut**: Opérationnel
- **Features**:
  - Exécution asynchrone avec `BackgroundTasks`
  - Polling status avec `job_id`
  - Progress tracking (0-100%)
  - Error/warning collection
- **Limitation**: In-memory storage (production devrait utiliser Redis/DB)

#### File Analysis
- **Endpoint**: `/api/files/analyze`
- **Features**:
  - Détection type fichier (CSV/Excel/JSON/GeoJSON/Shapefile)
  - Inférence types colonnes
  - Suggestions de mapping
  - Preview des données
  - Count unique taxons (pour taxonomie)

### 3. Configuration - 50% ⚠️

#### Instance de Test (Nouveau Format v2) ✅
- **Fichier**: `test-instance/niamoto-nc/config/import.yml`
- **Format**: Version 2 (entities/references/datasets)
- **Contenu**:
  ```yaml
  entities:
    datasets:
      occurrences:
        connector:
          type: file
          format: csv
    references:
      taxons:
        connector:
          type: derived
          source: occurrences
  ```
- **Statut**: ✅ Fonctionnel avec nouveau système

#### Root Config (Ancien Format v1) ❌
- **Fichier**: `config/import.yml`
- **Format**: Version 1 (taxonomy/plots/occurrences)
- **Contenu**:
  ```yaml
  taxonomy:
    type: csv
    path: imports/taxonomy.csv
  plots:
    type: csv
  occurrences:
    type: csv
  ```
- **Problème**: Format legacy, incompatible avec EntityRegistry

### 4. Tests - 100% ✅

#### Résultats
- **Total**: 1609 tests
- **Statut**: ✅ All passing
- **Coverage**:
  - Unit tests: Import engine, registry, hierarchy builder
  - Integration tests: End-to-end workflows (datasets → derived → direct)
  - CLI tests: Commands avec mocks
  - Service tests: Importer, Transformer, Exporter

#### Tests Clés
- `tests/core/imports/test_config_models.py` - Validation Pydantic
- `tests/core/imports/test_entity_registry.py` - CRUD registry
- `tests/core/imports/test_hierarchy_builder.py` - Extraction CTE
- `tests/core/services/test_importer_integration.py` - E2E workflows
- `tests/cli/test_imports.py` - CLI commands

#### Limitation Critique
⚠️ **Tous les tests utilisent entities standard** (`taxon_ref`, `plot_ref`, `occurrences`)
❌ **Aucun test avec entities custom** (ex: "habitats", "sites", etc.)

---

## ❌ CE QUI RESTE À FAIRE

### 1. MIGRATION PLUGINS - 🚨 CRITIQUE (86% NON MIGRÉS)

#### Vue d'Ensemble
| Catégorie | Total | Migrés | Non Migrés | % Migré |
|-----------|-------|--------|------------|---------|
| **Loaders** | 7 | 3 | 4 | 43% |
| **Transformers - Aggregation** | 5 | 1 | 4 | 20% |
| **Transformers - Extraction** | 3 | 3 | 0 | 100% ✅ |
| **Transformers - Class Objects** | 5 | 0 | 5 | 0% |
| **Transformers - Distribution** | 3 | 0 | 3 | 0% |
| **Transformers - Autres** | 4+ | 0 | 4+ | 0% |
| **Exporters** | 4 | 0 | 4 | 0% (n/a) |
| **Widgets** | 16 | 0 | 16 | 0% (n/a) |
| **TOTAL** | 49+ | **7** | **42+** | **14%** |

#### 1.1. Loaders - 43% Migrés (3/7)

**✅ Migrés**:
1. **`direct_reference.py`**
   - Imports: `from niamoto.core.imports.registry import EntityRegistry`
   - Constructor: `def __init__(self, db, registry=None)`
   - Usage: `metadata = self.registry.get(logical_name)` → `metadata.table_name`
   - Ligne 167-170: Résolution dynamique

2. **`join_table.py`**
   - Imports: `from niamoto.core.imports.registry import EntityRegistry`
   - Constructor: `def __init__(self, db, registry=None)`
   - Usage: `self.registry.get()` dans `_resolve_table_name()`
   - Ligne 172-179: Résolution via registry

3. **`stats_loader.py`**
   - Imports: `from niamoto.core.imports.registry import EntityRegistry`
   - Usage: `entity_registry = EntityRegistry(self.db)`
   - Ligne 158-164: `metadata = entity_registry.get(entity_name)`
   - Accès config: `metadata.config.get("schema", {}).get("id_field")`

**❌ Non Migrés**:
4. **`nested_set.py`** - 🔴 PRIORITÉ 1 (bloque transform.yml)
   - Ligne 124-125: `config["data"]` et `config["grouping"]` hardcodés
   - Pas d'import EntityRegistry
   - Utilisé dans: `transform.yml` (ligne 17-18)
   - **Impact**: Transform ne peut pas utiliser entities arbitraires

5. **`spatial.py`**
   - Ligne 69-71: `config["reference"]["name"]` et `config["main"]` hardcodés
   - Pas d'import EntityRegistry
   - Utilisé pour: Références spatiales avec géométries

6. **`adjacency_list.py`**
   - Ligne 122-123: `config["data"]` et `config["grouping"]` hardcodés
   - Pas d'import EntityRegistry
   - Utilisé pour: Hiérarchies adjacency list (alternative à nested_set)

7. **`api_taxonomy_enricher.py`** - ⚪ ACCEPTABLE (pas d'interaction DB)
   - Constructor: `db=None, registry=None` mais inutilisés
   - Pure API-based, ne résout pas de tables
   - **Décision**: Migration optionnelle

#### 1.2. Transformers - Aggregation - 20% Migrés (1/5)

**✅ Migrés**:
1. **`field_aggregator.py`**
   - Ligne 14: `from niamoto.core.imports.registry import EntityRegistry`
   - Ligne 98-100: Constructor initialise registry, stocke Config
   - Utilise EntityRegistry pour résolution

**❌ Non Migrés**:
2. **`top_ranking.py`** - 🔴 PRIORITÉ 1 (très utilisé)
   - Pas d'import EntityRegistry
   - Travaille avec noms logiques dans config
   - Utilisé dans: Stats "Top 10 espèces", etc.

3. **`database_aggregator.py`** - ⚪ ACCEPTABLE
   - Pure SQL query executor
   - Ne fait pas de résolution table names
   - **Décision**: Migration optionnelle

4. **`binary_counter.py`**
   - Pas d'import EntityRegistry
   - Références hardcodées dans config

5. **`statistical_summary.py`**
   - Pas d'import EntityRegistry
   - Références hardcodées dans config

#### 1.3. Transformers - Extraction - 100% Migrés ✅

**✅ Tous Migrés**:
1. **`direct_attribute.py`**
   - Ligne 13: `from niamoto.core.imports.registry import EntityRegistry`
   - Ligne 84-98: `self.registry = EntityRegistry(db)`
   - Usage: `table_name = entity_info.table_name if entity_info else source`

2. **`multi_column_extractor.py`**
   - Ligne 14: `from niamoto.core.imports.registry import EntityRegistry`
   - Résolution similaire à `direct_attribute`

3. **`geospatial_extractor.py`**
   - Ligne 19: `from niamoto.core.imports.registry import EntityRegistry`
   - Usage: `table_name = self._resolve_table_name(source)`
   - Support géométries via DuckDB spatial extension

#### 1.4. Transformers - Class Objects - 0% Migrés (0/5) 🔴

**❌ Tous Non Migrés - PRIORITÉ 1**:

1. **`categories_extractor.py`**
   - Hardcode: `source="shape_stats"`
   - Pas d'EntityRegistry import
   - Utilisé pour: Extraction catégories depuis stats shapes

2. **`series_extractor.py`**
   - Hardcode: `source="shape_stats"`
   - Pas d'EntityRegistry import
   - Utilisé pour: Séries temporelles/catégorielles

3. **`binary_aggregator.py`**
   - Hardcode: `source="raw_shape_stats"`
   - Pas d'EntityRegistry import
   - Utilisé pour: Comptage binaire (endémique/non-endémique)

4. **`series_ratio_aggregator.py`**
   - Hardcode: Tables stats
   - Pas d'EntityRegistry import
   - Utilisé pour: Ratios entre séries

5. **`field_aggregator.py`** (version class_objects)
   - Différent de la version aggregation/
   - Hardcode: Références tables
   - Utilisé pour: Agrégation champs class objects

**Impact**: Impossible d'utiliser ces transformers avec entities custom

#### 1.5. Transformers - Distribution - 0% Migrés (0/3) 🔴

**❌ Tous Non Migrés - PRIORITÉ 1**:

1. **`categorical_distribution.py`**
   - Hardcode: `source="occurrences"` par défaut
   - Pas d'EntityRegistry import
   - Utilisé pour: Distributions catégorielles (ex: par province)

2. **`binned_distribution.py`**
   - Hardcode: `source="occurrences"` par défaut
   - Pas d'EntityRegistry import
   - Utilisé pour: Histogrammes binned (ex: altitude)

3. **`time_series_analysis.py`**
   - Hardcode: `source="occurrences"` par défaut
   - Pas d'EntityRegistry import
   - Utilisé pour: Analyses temporelles (phénologie)

**Impact**: Transform ne peut analyser que "occurrences", pas datasets custom

#### 1.6. Transformers - Autres - 0% Migrés (4+)

**❌ Non Migrés**:

1. **`niamoto_to_dwc_occurrence.py`** (formats/)
   - Hardcode: `_taxon_id_column = "id_taxonref"`
   - Pas d'EntityRegistry import
   - Utilisé pour: Export DarwinCore

2. **`shape_processor.py`** (geospatial/)
   - Hardcode: `source="shapes"`
   - Pas d'EntityRegistry import
   - Utilisé pour: Simplification géométries

3. Autres transformers (formats, geospatial, etc.)
   - Pas encore audités en détail
   - Probablement pattern similaire

#### 1.7. Exporters - 0% Migrés (0/4) ⚪

**❌ Non Migrés (mais probablement OK)**:

1. **`html_page_exporter.py`**
   - Import: `from niamoto.core.plugins.registry import PluginRegistry` (pas EntityRegistry)
   - Génère HTML depuis widgets transformés
   - **Analyse**: Ne fait pas de résolution table names directes
   - **Décision**: Migration probablement non nécessaire

2. **`json_api_exporter.py`**
   - Config-driven, pas de DB queries directes
   - Mappe données déjà transformées
   - **Décision**: Migration probablement non nécessaire

3. **`dwc_archive_exporter.py`**
   - Génère archives DarwinCore depuis données transformées
   - **Décision**: Migration probablement non nécessaire

4. **`index_generator.py`**
   - Génère index HTML depuis exports
   - **Décision**: Migration probablement non nécessaire

**Conclusion Exporters**: Travaillent sur outputs de Transform, pas sur tables brutes → Migration basse priorité

#### 1.8. Widgets - 0% Migrés (0/16) ⚪

**❌ Non Migrés (mais OK)**:

- `hierarchical_nav_widget.py` - Référence `referential_data="taxons"` (string)
- `interactive_map.py` - Pas d'interaction DB
- `bar_plot.py`, `scatter_plot.py`, etc. - Composants visualisation

**Conclusion Widgets**: Composants visualisation purs, ne font pas de résolution tables → Pas de migration nécessaire

### 2. GUI FRONTEND - 🚨 CRITIQUE (0% Migré)

#### État Actuel - Wizard Legacy Hardcodé

**Fichiers**:
- `src/niamoto/gui/ui/src/pages/import/index.tsx` - Page principale
- `src/niamoto/gui/ui/src/pages/import/Overview.tsx` - Étape 1
- `src/niamoto/gui/ui/src/pages/import/OccurrencesStep.tsx` - Étape 2
- `src/niamoto/gui/ui/src/pages/import/AggregationStep.tsx` - Étape 3
- `src/niamoto/gui/ui/src/pages/import/SummaryStep.tsx` - Étape 4

**Structure Actuelle**:
```typescript
// Wizard en 4 étapes hardcodées
steps = [
  { title: "Overview" },
  { title: "Occurrences" },    // ❌ Hardcodé
  { title: "Aggregations" },    // ❌ Hardcodé (taxonomy)
  { title: "Summary" }
]
```

**Problèmes Identifiés**:
1. ❌ **Hardcodé à 4 entités fixes**: taxonomy, plots, occurrences, shapes
2. ❌ **Pas de support entities arbitraires**: Impossible d'ajouter "habitats", "sites", etc.
3. ❌ **Pas d'éditeur YAML**: Utilisateur ne peut pas définir `import.yml` visuellement
4. ❌ **Pas de support "derived"**: Impossible de configurer extraction hiérarchie
5. ❌ **Config mapping hardcodé**: Champs mappés à tables fixes dans code
6. ❌ **Pas de EntitySelector component**: Dropdowns statiques, pas de query registry

**Hooks/API Actuels**:
- `useImportStatus()` - ✅ Fonctionne avec EntityRegistry (ligne 24: `/api/imports/status`)
- `executeImport()` - ✅ Appelle endpoints génériques (ligne 62-66)
- `analyzeFile()` - ✅ Détection colonnes (ligne 39-51)
- `getEntities()` - ✅ Liste entities depuis config (ligne 228-231)

#### Ce Qu'il Faut Construire

**Architecture Cible**:
```
┌─────────────────────────────────────────────┐
│ Entity Configuration Manager                 │
├─────────────────────────────────────────────┤
│                                              │
│  [Datasets]           [References]          │
│  ┌──────────────┐     ┌──────────────┐     │
│  │ occurrences  │     │ taxonomy     │     │
│  │ observations │     │ plots        │     │
│  │ + Add New    │     │ + Add New    │     │
│  └──────────────┘     └──────────────┘     │
│                                              │
│  Selected: occurrences (Dataset)            │
│  ┌─────────────────────────────────────┐   │
│  │ Connector:                           │   │
│  │  ○ File (CSV/GeoJSON/Shapefile)     │   │
│  │  ○ API (REST/GraphQL)               │   │
│  │                                       │   │
│  │ File: [Browse...] occurrences.csv    │   │
│  │                                       │   │
│  │ Schema Mapping:                      │   │
│  │  id_field: [id_taxonref ▼]          │   │
│  │  Fields:                             │   │
│  │   • family → string                  │   │
│  │   • genus → string                   │   │
│  │   • geo_pt → geometry (auto-detect) │   │
│  │                                       │   │
│  │ Links:                               │   │
│  │  • taxonomy.taxon_id ← id_taxonref  │   │
│  │  • plots.locality ← plot_name       │   │
│  │                                       │   │
│  │ [Preview Data] [Save] [Import Now]  │   │
│  └─────────────────────────────────────┘   │
│                                              │
│  Selected: taxonomy (Reference - Derived)   │
│  ┌─────────────────────────────────────┐   │
│  │ Connector: Derived from occurrences  │   │
│  │                                       │   │
│  │ Hierarchy Levels:                    │   │
│  │  1. family ← [family ▼]             │   │
│  │  2. genus ← [genus ▼]               │   │
│  │  3. species ← [species ▼]           │   │
│  │  [+ Add Level]                       │   │
│  │                                       │   │
│  │ ID Strategy:                         │   │
│  │  ○ Hash-based (recommended)          │   │
│  │  ○ Sequential                        │   │
│  │  ○ External column: [id_taxonref▼]  │   │
│  │                                       │   │
│  │ Incomplete Rows:                     │   │
│  │  ○ Skip                              │   │
│  │  ○ Fill with "Unknown"               │   │
│  │  ○ Error                             │   │
│  │                                       │   │
│  │ [Preview Hierarchy] [Save] [Extract]│   │
│  └─────────────────────────────────────┘   │
│                                              │
│  [Preview import.yml] [Import All Entities] │
└─────────────────────────────────────────────┘
```

**Composants à Créer**:

##### 2.1. EntityManagerPage
**Fichier**: `src/niamoto/gui/ui/src/pages/entities/index.tsx`
**Responsabilités**:
- Afficher liste entities (datasets + references)
- Boutons CRUD (Add/Edit/Delete)
- Statut import (imported/pending/failed)
- Tabs Datasets/References
- Search/filter entities

**Structure**:
```typescript
interface EntityListItem {
  name: string
  kind: 'dataset' | 'reference'
  connector_type: 'file' | 'derived' | 'api'
  is_imported: boolean
  row_count?: number
  last_import?: string
}

export function EntityManagerPage() {
  const { entities, loading } = useEntities()
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null)

  return (
    <div>
      <EntityList entities={entities} onSelect={setSelectedEntity} />
      {selectedEntity && (
        <EntityEditor entity={selectedEntity} />
      )}
    </div>
  )
}
```

##### 2.2. EntityFormDialog
**Fichier**: `src/niamoto/gui/ui/src/components/entities/EntityFormDialog.tsx`
**Responsabilités**:
- Formulaire create/edit entity
- Sélection type (dataset vs reference)
- Sélection connector (file/derived/api)
- Validation temps réel

**Props**:
```typescript
interface EntityFormDialogProps {
  open: boolean
  onClose: () => void
  entity?: EntityConfig // Pour edit
  mode: 'create' | 'edit'
}

// Formulaire dynamique selon connector_type:
// - file: File upload + format selector
// - derived: Source selector + extraction config
// - api: URL + auth config
```

##### 2.3. HierarchyBuilderDialog
**Fichier**: `src/niamoto/gui/ui/src/components/entities/HierarchyBuilderDialog.tsx`
**Responsabilités**:
- Configurateur hiérarchies (adjacency_list/nested_set)
- Levels editor: Add/Remove/Reorder levels
- Mapping colonnes → levels
- Preview structure hiérarchique
- Validation cohérence (pas de "species sans genus")

**Structure**:
```typescript
interface HierarchyLevel {
  name: string        // "family"
  column: string      // "family" (colonne source)
  order: number       // 0, 1, 2...
}

export function HierarchyBuilderDialog({
  sourceDataset,
  levels,
  onSave
}: {
  sourceDataset: string
  levels: HierarchyLevel[]
  onSave: (config: HierarchyConfig) => void
}) {
  // Drag-and-drop pour reorder levels
  // Auto-détection colonnes depuis sourceDataset
  // Preview arbre hiérarchique résultant
}
```

##### 2.4. FieldMappingComponent
**Fichier**: `src/niamoto/gui/ui/src/components/entities/FieldMappingComponent.tsx`
**Responsabilités**:
- Détection auto colonnes (via `/api/files/analyze`)
- Mapping colonnes → schema fields
- Inférence types (string/int/float/geometry/date)
- Validation format (ex: géométrie valide)
- Preview données

**Features**:
```typescript
interface FieldMapping {
  source_column: string
  target_field: string
  type: 'string' | 'integer' | 'float' | 'geometry' | 'date'
  required: boolean
  description?: string
}

// Drag-and-drop: Colonne CSV → Schema Field
// Auto-suggestions basées sur noms similarité
// Validation: Géométrie WKT/WKB, dates ISO8601
```

##### 2.5. YamlPreviewComponent
**Fichier**: `src/niamoto/gui/ui/src/components/entities/YamlPreviewComponent.tsx`
**Responsabilités**:
- Générer `import.yml` depuis formulaires
- Syntax highlighting YAML
- Copy to clipboard
- Download as file
- Validation schema

**Exemple**:
```typescript
export function YamlPreviewComponent({ config }: { config: ImportConfig }) {
  const yaml = generateYaml(config)

  return (
    <div>
      <pre className="language-yaml">
        <code>{yaml}</code>
      </pre>
      <Button onClick={() => copy(yaml)}>Copy</Button>
      <Button onClick={() => download(yaml, 'import.yml')}>Download</Button>
    </div>
  )
}
```

##### 2.6. EntitySelectorComponent (Réutilisable)
**Fichier**: `src/niamoto/gui/ui/src/components/entities/EntitySelector.tsx`
**Responsabilités**:
- Dropdown qui charge entities depuis EntityRegistry
- Filtres par type (reference/dataset/all)
- Search/autocomplete
- Affichage metadata (row count, last import)

**Usage**:
```typescript
// Dans transform.yml editor:
<EntitySelector
  type="reference"
  value={selectedEntity}
  onChange={setSelectedEntity}
  label="Group by"
/>

// Dans widget config:
<EntitySelector
  type="dataset"
  value={dataSource}
  onChange={setDataSource}
  label="Data source"
/>
```

**Cette structure sera utilisée partout** dans l'app (transform, export, widgets)

#### Nouveaux Endpoints API

**À Ajouter dans** `src/niamoto/gui/api/routers/entities.py`:

```python
# CRUD Entities
GET    /api/entities                 # Liste entities (query: ?kind=reference)
GET    /api/entities/{name}          # Détails entity
POST   /api/entities                 # Créer entity
PUT    /api/entities/{name}          # Modifier entity
DELETE /api/entities/{name}          # Supprimer entity

# Preview & Validation
GET    /api/entities/{name}/preview  # Preview données (10 rows)
GET    /api/entities/{name}/schema   # Schema complet
POST   /api/entities/validate        # Valider config avant save

# Hierarchy Builder
POST   /api/entities/{name}/hierarchy/preview  # Preview hiérarchie
GET    /api/entities/{name}/hierarchy/stats    # Stats (levels, counts)

# Field Detection
POST   /api/fields/detect            # Détection auto colonnes
POST   /api/fields/suggest-mapping   # Suggestions mapping
```

### 3. CONFIGURATION TRANSFORM/EXPORT - ⚠️ IMPORTANT

#### Problème Transform Config

**Fichier Actuel**: `test-instance/niamoto-nc/config/transform.yml`

**Ligne 11-23 (Problématique)**:
```yaml
- group_by: taxons              # ❌ Nom hardcodé
  sources:
    - name: occurrences
      data: occurrences          # ❌ Table hardcodée
      grouping: taxons           # ❌ Table hardcodée
      relation:
        plugin: nested_set       # ❌ Plugin non migré!
        key: id_taxonref
        ref_key: taxons_id
        fields:
          left: lft
          right: rght
          parent: parent_id
```

**Problèmes**:
1. ❌ `data: occurrences` - Hardcodé, devrait résoudre via EntityRegistry
2. ❌ `grouping: taxons` - Hardcodé, devrait résoudre via EntityRegistry
3. ❌ `plugin: nested_set` - Plugin non migré vers EntityRegistry
4. ❌ Aucun moyen de choisir entity arbitraire

**Format Cible**:
```yaml
- group_by: taxonomy            # Nom logique (résolu via registry)
  sources:
    - name: occurrences
      entity: occurrences       # Résolution EntityRegistry
      grouping: taxonomy        # Résolution EntityRegistry
      relation:
        plugin: nested_set       # Migré pour utiliser EntityRegistry
        key: id_taxonref
        ref_key: taxonomy.taxon_id
```

**Actions Requises**:
1. Migrer `nested_set.py` vers EntityRegistry (PRIORITÉ 1)
2. Adapter `TransformerService.get_group_data()` pour résoudre entities
3. Mettre à jour validation config pour accepter entity names
4. Créer GUI pour éditer `transform.yml` avec EntitySelector

#### Problème Export Config

**Fichier**: `test-instance/niamoto-nc/config/export.yml`

**Probablement similaire**: Références hardcodées à tables

**Actions Requises**:
1. Audit `export.yml` pour références hardcodées
2. Migrer exporters si nécessaire (probablement OK)
3. Adapter `ExporterService` pour résoudre entities
4. GUI pour éditer `export.yml`

### 4. DOCUMENTATION - ⚠️ IMPORTANT

#### Documents à Mettre à Jour

##### ADR 0004 - Generic Import System
**Fichier**: `docs/09-architecture/adr/0004-generic-import-system.md`

**Ligne 99-102 (FAUX)**:
```markdown
### Plugin Genericization (Phase 8)

All 19 plugins were refactored to:
- Accept `EntityRegistry` instead of `Config`/`Database` objects
```

**Réalité**: 7/49 plugins migrés (14%)

**Corrections Nécessaires**:
- Mettre à jour section "Implementation Phases"
- Corriger "All 19 plugins" → "7/49 plugins (14%)"
- Ajouter liste détaillée plugins migrés vs non migrés
- Mettre statut "IN PROGRESS" au lieu de "COMPLETE"

##### Roadmap - generic-import-refactor-roadmap.md
**Fichier**: `docs/10-roadmaps/generic-import-refactor-roadmap.md`

**Ligne 12-19 (FAUX)**:
```markdown
## Progress Snapshot (2025-10-10)
- ✅ **Core refactoring complete**: Generic import system operational
- 🚧 **Phase 8 in progress**: Refactoring 12 plugins
```

**Réalité**: Phase 8 à 14% seulement, 42 plugins restants

**Corrections Nécessaires**:
- Mettre à jour "Progress Snapshot" avec date réelle (2025-01-20)
- Corriger "12 plugins" → "49 plugins, 7 migrés"
- Ajouter status détaillé par catégorie
- Mettre GUI status: 0% au lieu de "functional"

#### Documents à Créer

##### 1. Migration Guide - Instances Existantes
**Fichier**: `docs/guides/migration-v1-to-v2.md`

**Contenu**:
- Différences format v1 vs v2
- Script conversion automatique `import.yml`
- Migration données SQLite → DuckDB
- Checklist migration pas-à-pas
- Troubleshooting commun

##### 2. Entity Configuration Guide
**Fichier**: `docs/guides/entity-configuration.md`

**Contenu**:
- Syntaxe `import.yml` complète
- Exemples datasets (CSV/GeoJSON/Shapefile)
- Exemples references (file/derived)
- Configuration hiérarchies
- Liens entre entities
- Enrichment plugins

##### 3. Plugin Migration Guide
**Fichier**: `docs/guides/plugin-migration.md`

**Contenu**:
- Pattern migration: Config → EntityRegistry
- Exemples before/after
- Résolution table names
- Gestion fallback (compatibility)
- Testing strategies

##### 4. GUI User Guide
**Fichier**: `docs/guides/gui-entity-manager.md`

**Contenu**:
- Utiliser Entity Manager
- Créer dataset
- Créer reference (file vs derived)
- Configurer hiérarchies
- Importer entities
- Troubleshooting GUI

##### 5. API Documentation
**Fichier**: `docs/api/entity-management.md`

**Contenu**:
- Endpoints REST complets
- Request/Response schemas
- Exemples curl/axios
- Error codes
- Rate limiting

---

## 📋 PLAN D'ACTION DÉTAILLÉ

### PHASE 1 - PLUGINS CRITIQUES (Priorité 🔴)
**Durée Estimée**: 3-5 jours
**Objectif**: Migrer plugins qui bloquent utilisation réelle

#### Tâche 1.1 - Loaders (3 plugins)
**Fichiers**:
- `src/niamoto/core/plugins/loaders/nested_set.py` 🔴 CRITIQUE
- `src/niamoto/core/plugins/loaders/spatial.py`
- `src/niamoto/core/plugins/loaders/adjacency_list.py`

**Actions**:
1. Ajouter import: `from niamoto.core.imports.registry import EntityRegistry`
2. Modifier constructor: `def __init__(self, db, registry=None)`
3. Ajouter fallback: `self.registry = registry or EntityRegistry(db)`
4. Créer méthode: `_resolve_table_name(logical_name: str) -> str`
5. Remplacer `config["data"]` → `self._resolve_table_name(config["data"])`
6. Remplacer `config["grouping"]` → `self._resolve_table_name(config["grouping"])`
7. Tests: Vérifier avec entity custom (pas `taxon_ref`)

**Critères de Succès**:
- [ ] Tests unitaires passent
- [ ] `transform.yml` fonctionne avec entities arbitraires
- [ ] Aucune référence hardcodée à `taxon_ref`, `plot_ref`, `shape_ref`

#### Tâche 1.2 - Class Object Transformers (5 plugins)
**Fichiers**:
- `src/niamoto/core/plugins/transformers/class_objects/categories_extractor.py`
- `src/niamoto/core/plugins/transformers/class_objects/series_extractor.py`
- `src/niamoto/core/plugins/transformers/class_objects/binary_aggregator.py`
- `src/niamoto/core/plugins/transformers/class_objects/series_ratio_aggregator.py`
- `src/niamoto/core/plugins/transformers/class_objects/field_aggregator.py`

**Actions**:
1. Pattern identique à 1.1
2. Remplacer hardcoded `"shape_stats"` → Résolution dynamique
3. Remplacer hardcoded `"raw_shape_stats"` → Résolution dynamique
4. Support sources configurables dans params

**Critères de Succès**:
- [ ] Transformers fonctionnent avec datasets custom
- [ ] Pas de référence à `shape_stats` en dur
- [ ] Tests avec entities non-standard

#### Tâche 1.3 - Distribution Transformers (3 plugins)
**Fichiers**:
- `src/niamoto/core/plugins/transformers/aggregation/categorical_distribution.py`
- `src/niamoto/core/plugins/transformers/aggregation/binned_distribution.py`
- `src/niamoto/core/plugins/transformers/aggregation/time_series_analysis.py`

**Actions**:
1. Pattern identique à 1.1
2. Remplacer default `source="occurrences"` → Paramètre configurable
3. Résolution via EntityRegistry
4. Fallback intelligent si source non spécifié

**Critères de Succès**:
- [ ] Distribution fonctionne sur datasets custom
- [ ] Source configurable dans `transform.yml`
- [ ] Tests avec "observations" au lieu de "occurrences"

#### Tâche 1.4 - Aggregation Transformers (3 plugins)
**Fichiers**:
- `src/niamoto/core/plugins/transformers/aggregation/top_ranking.py` 🔴 CRITIQUE
- `src/niamoto/core/plugins/transformers/aggregation/binary_counter.py`
- `src/niamoto/core/plugins/transformers/aggregation/statistical_summary.py`

**Actions**:
1. Pattern identique à 1.1
2. Résolution sources dynamiques
3. Support multi-entity aggregation

**Critères de Succès**:
- [ ] `top_ranking` utilisable avec n'importe quelle entity
- [ ] Aggregations multi-sources possibles
- [ ] Tests coverage augmenté

#### Tâche 1.5 - Autres Transformers (2+ plugins)
**Fichiers**:
- `src/niamoto/core/plugins/transformers/formats/niamoto_to_dwc_occurrence.py`
- `src/niamoto/core/plugins/transformers/geospatial/shape_processor.py`

**Actions**:
1. Pattern identique à 1.1
2. Remplacer hardcoded field names → Config-driven
3. Support colonnes custom

**Critères de Succès**:
- [ ] DWC export fonctionne avec taxonomy custom
- [ ] Shape processor gère entities spatiales arbitraires

**Livrables Phase 1**:
- [ ] 14 plugins migrés (100% transformers critiques)
- [ ] Tests unitaires pour chaque plugin
- [ ] Tests integration avec entities custom
- [ ] `transform.yml` mis à jour avec nouveaux patterns
- [ ] Documentation: Plugin Migration Guide (création)

---

### PHASE 2 - GUI GÉNÉRIQUE (Priorité 🔴)
**Durée Estimée**: 5-7 jours
**Objectif**: Interface utilisateur pour configurer entities arbitraires

#### Tâche 2.1 - API Endpoints (1 jour)
**Fichier**: `src/niamoto/gui/api/routers/entities.py` (nouveau)

**Actions**:
1. Créer router FastAPI
2. Implémenter CRUD endpoints:
   ```python
   GET    /api/entities
   GET    /api/entities/{name}
   POST   /api/entities
   PUT    /api/entities/{name}
   DELETE /api/entities/{name}
   ```
3. Implémenter preview endpoints:
   ```python
   GET    /api/entities/{name}/preview
   GET    /api/entities/{name}/schema
   POST   /api/entities/validate
   ```
4. Implémenter hierarchy endpoints:
   ```python
   POST   /api/entities/{name}/hierarchy/preview
   GET    /api/entities/{name}/hierarchy/stats
   ```
5. Tests API avec pytest + httpx

**Livrables**:
- [ ] Fichier `entities.py` avec tous endpoints
- [ ] Schémas Pydantic (request/response models)
- [ ] Tests API (coverage >80%)
- [ ] Documentation OpenAPI auto-générée

#### Tâche 2.2 - EntityManagerPage (2 jours)
**Fichier**: `src/niamoto/gui/ui/src/pages/entities/index.tsx` (nouveau)

**Actions**:
1. Créer page EntityManager
2. Implémenter EntityList component:
   - Table entities avec colonnes: name, kind, type, status, actions
   - Search/filter par name
   - Tabs: All / Datasets / References
   - Status badges: imported/pending/failed
3. Implémenter actions:
   - Button "Add Dataset"
   - Button "Add Reference"
   - Dropdown actions: Edit / Delete / Import
4. Hooks:
   ```typescript
   useEntities() // Liste entities
   useEntityActions() // CRUD operations
   useEntityStatus() // Import status
   ```

**Livrables**:
- [ ] Page EntityManager fonctionnelle
- [ ] EntityList component
- [ ] Hooks réutilisables
- [ ] Tests React Testing Library

#### Tâche 2.3 - EntityFormDialog (1.5 jours)
**Fichier**: `src/niamoto/gui/ui/src/components/entities/EntityFormDialog.tsx` (nouveau)

**Actions**:
1. Dialog component avec steps:
   - Step 1: Type (dataset/reference)
   - Step 2: Connector (file/derived/api)
   - Step 3: Configuration spécifique
   - Step 4: Review
2. Formulaires conditionnels selon type:
   - **File connector**: File upload + format selector
   - **Derived connector**: Source selector + extraction config
   - **API connector**: URL + auth config
3. Validation temps réel:
   - Check name unique
   - Validate paths
   - Check source exists (pour derived)
4. Preview généré `import.yml` section

**Livrables**:
- [ ] EntityFormDialog component
- [ ] Formulaires conditionnels
- [ ] Validation client-side
- [ ] Tests formulaires

#### Tâche 2.4 - HierarchyBuilderDialog (1.5 jours)
**Fichier**: `src/niamoto/gui/ui/src/components/entities/HierarchyBuilderDialog.tsx` (nouveau)

**Actions**:
1. Dialog pour configurer hiérarchies
2. Levels editor:
   - Liste levels avec drag-and-drop reorder
   - Formulaire add level: name + column mapping
   - Détection auto colonnes depuis source dataset
   - Validation: Pas de levels vides, ordre cohérent
3. Configuration avancée:
   - Strategy: adjacency_list / nested_set
   - ID strategy: hash / sequential / external
   - Incomplete rows: skip / fill_unknown / error
4. Preview hiérarchie:
   - Tree view avec niveaux
   - Stats: Nombre nodes par level
   - Exemples paths hiérarchiques
5. Hook: `useHierarchyPreview(sourceDataset, levels)`

**Livrables**:
- [ ] HierarchyBuilderDialog component
- [ ] Drag-and-drop levels
- [ ] Preview arbre hiérarchique
- [ ] Tests interactions

#### Tâche 2.5 - FieldMappingComponent (1 jour)
**Fichier**: `src/niamoto/gui/ui/src/components/entities/FieldMappingComponent.tsx` (nouveau)

**Actions**:
1. Component mapping colonnes → schema
2. Auto-détection:
   - Upload file → Appel `/api/files/analyze`
   - Affichage colonnes détectées avec types
   - Suggestions mapping basées sur noms
3. Interface mapping:
   - Deux colonnes: Source columns | Schema fields
   - Drag-and-drop colonnes vers fields
   - Dropdown pour select column
4. Validation:
   - Required fields mappés
   - Types compatibles (ex: geometry → geometry)
   - Preview data samples
5. Hook: `useFieldMapping(file, schema)`

**Livrables**:
- [ ] FieldMappingComponent
- [ ] Auto-détection colonnes
- [ ] Drag-and-drop mapping
- [ ] Validation mapping

#### Tâche 2.6 - YamlPreviewComponent (0.5 jour)
**Fichier**: `src/niamoto/gui/ui/src/components/entities/YamlPreviewComponent.tsx` (nouveau)

**Actions**:
1. Component affichage YAML généré
2. Features:
   - Syntax highlighting (ex: `react-syntax-highlighter`)
   - Line numbers
   - Copy to clipboard
   - Download as file
3. Génération YAML depuis config:
   ```typescript
   function generateYaml(entities: EntityConfig[]): string {
     // Convert EntityConfig[] → YAML string
   }
   ```
4. Validation schema avant affichage

**Livrables**:
- [ ] YamlPreviewComponent
- [ ] Syntax highlighting
- [ ] Copy/Download actions
- [ ] Tests générateur YAML

#### Tâche 2.7 - EntitySelector (Réutilisable) (0.5 jour)
**Fichier**: `src/niamoto/gui/ui/src/components/entities/EntitySelector.tsx` (nouveau)

**Actions**:
1. Dropdown component réutilisable
2. Props:
   ```typescript
   interface EntitySelectorProps {
     type?: 'dataset' | 'reference' | 'all'
     value: string
     onChange: (name: string) => void
     label?: string
     placeholder?: string
     required?: boolean
   }
   ```
3. Features:
   - Load entities depuis `/api/entities`
   - Filter par type
   - Search/autocomplete
   - Affichage metadata (icon, row count)
   - Loading state
4. Hook: `useEntities(type)`

**Livrables**:
- [ ] EntitySelector component
- [ ] Hook useEntities
- [ ] Tests component
- [ ] Storybook stories

#### Tâche 2.8 - Integration & Polish (1 jour)
**Actions**:
1. Intégrer tous composants dans EntityManagerPage
2. Router setup: `/entities` route
3. Navigation: Ajouter lien dans sidebar
4. Responsive design: Mobile/tablet support
5. Error handling: Toasts/notifications
6. Loading states: Skeletons
7. Empty states: Illustrations + CTA
8. Internationalization: Strings dans i18n
9. Tests E2E: Playwright scenario complet

**Livrables**:
- [ ] Page complètement fonctionnelle
- [ ] Design responsive
- [ ] Error/loading states
- [ ] Tests E2E passants

**Livrables Phase 2**:
- [ ] Entity Manager UI complet
- [ ] 7 nouveaux composants React
- [ ] API endpoints fonctionnels
- [ ] Tests (unit + integration + E2E)
- [ ] Documentation: GUI User Guide (création)

---

### PHASE 3 - CONFIG TRANSFORM/EXPORT (Priorité 🟡)
**Durée Estimée**: 2-3 jours
**Objectif**: Adapter Transform/Export pour utiliser EntityRegistry

#### Tâche 3.1 - Transform Service Adaptation (1 jour)
**Fichier**: `src/niamoto/core/services/transformer.py`

**Actions**:
1. Modifier `get_group_data()`:
   - Accepter entity names au lieu de table names
   - Résoudre via EntityRegistry: `registry.get_table_name(entity_name)`
   - Fallback: Si table existe directement, utiliser (backward compat)
2. Modifier `validate_configuration()`:
   - Valider entity names existent dans registry
   - Checker links entre entities
3. Adapter tests:
   - Tester avec entities custom
   - Tester fallback backward compat

**Livrables**:
- [ ] TransformerService adapté
- [ ] Tests unitaires mis à jour
- [ ] Backward compatibility validée

#### Tâche 3.2 - Transform Config Migration (0.5 jour)
**Fichier**: `test-instance/niamoto-nc/config/transform.yml`

**Actions**:
1. Mettre à jour syntaxe:
   ```yaml
   # Avant:
   data: occurrences       # Table name
   grouping: taxons        # Table name

   # Après:
   entity: occurrences     # Entity name (résolu via registry)
   grouping: taxonomy      # Entity name (résolu via registry)
   ```
2. Vérifier plugins référencés sont migrés
3. Tester workflow complet: import → transform → export

**Livrables**:
- [ ] `transform.yml` mis à jour
- [ ] Tests end-to-end passants
- [ ] Documentation syntaxe nouvelle

#### Tâche 3.3 - Transform GUI Editor (1 jour)
**Fichier**: `src/niamoto/gui/ui/src/pages/transform/editor.tsx` (nouveau)

**Actions**:
1. Créer page Transform Config Editor
2. Features:
   - Liste transform groups
   - Formulaire edit group:
     - **EntitySelector** pour group_by
     - **EntitySelector** pour sources
     - Plugin selector (nested_set/adjacency_list/stats_loader)
     - Widget config editor
   - Preview `transform.yml` généré
   - Save/Load config
3. Validation:
   - Entities existent
   - Plugins disponibles
   - Relations cohérentes

**Livrables**:
- [ ] Transform Editor UI
- [ ] Utilise EntitySelector component
- [ ] Validation config
- [ ] Tests UI

#### Tâche 3.4 - Export Service Adaptation (0.5 jour)
**Fichier**: `src/niamoto/core/services/exporter.py`

**Actions**:
1. Audit: Vérifier si ExporterService utilise table names hardcodés
2. Si oui: Adapter pour résoudre via EntityRegistry
3. Mettre à jour `export.yml` si nécessaire
4. Tests exporters avec entities custom

**Livrables**:
- [ ] ExporterService adapté (si nécessaire)
- [ ] `export.yml` mis à jour
- [ ] Tests passants

**Livrables Phase 3**:
- [ ] Transform/Export utilisent EntityRegistry
- [ ] Configs migrés vers nouvelle syntaxe
- [ ] GUI editors fonctionnels
- [ ] Tests end-to-end complets

---

### PHASE 4 - DOCUMENTATION (Priorité 🟡)
**Durée Estimée**: 2 jours
**Objectif**: Documentation complète et à jour

#### Tâche 4.1 - Mise à Jour ADR/Roadmaps (0.5 jour)

**Fichiers**:
- `docs/09-architecture/adr/0004-generic-import-system.md`
- `docs/10-roadmaps/generic-import-refactor-roadmap.md`

**Actions**:
1. Corriger ADR 0004:
   - Section "Implementation Phases": Mettre status réel
   - Ligne 99-102: Corriger "All 19 plugins" → Liste détaillée
   - Ajouter tableau progression plugins par catégorie
   - Mettre status "IN PROGRESS" au lieu de "COMPLETE"
2. Corriger Roadmap:
   - Mettre à jour "Progress Snapshot" (date + status réel)
   - Corriger "Phase 8 complete" → "Phase 8: 14% (7/49 plugins)"
   - Ajouter section "Remaining Work" détaillée
   - Mettre GUI status: "0% (in development)"

**Livrables**:
- [ ] ADR 0004 corrigé et à jour
- [ ] Roadmap corrigée et à jour
- [ ] Statut réel documenté

#### Tâche 4.2 - Migration Guide (0.5 jour)
**Fichier**: `docs/guides/migration-v1-to-v2.md` (nouveau)

**Sections**:
1. **Introduction**: Pourquoi migrer, bénéfices
2. **Différences v1 vs v2**: Tableau comparatif formats
3. **Checklist Migration**:
   - [ ] Backup données existantes
   - [ ] Installer DuckDB
   - [ ] Convertir `import.yml`
   - [ ] Migrer données SQLite → DuckDB
   - [ ] Mettre à jour `transform.yml`
   - [ ] Tester imports
4. **Script Conversion**: `scripts/convert_import_v1_to_v2.py`
5. **Troubleshooting**: Erreurs communes + solutions
6. **Rollback**: Comment revenir en arrière si problème

**Livrables**:
- [ ] Migration Guide complet
- [ ] Script conversion automatique
- [ ] Exemples avant/après

#### Tâche 4.3 - Entity Configuration Guide (0.5 jour)
**Fichier**: `docs/guides/entity-configuration.md` (nouveau)

**Sections**:
1. **Syntaxe `import.yml`**: Format complet avec annotations
2. **Types Entities**:
   - Datasets: CSV, GeoJSON, GeoPackage, Shapefile
   - References: File-based, Derived
3. **Connectors**:
   - File connector: Formats supportés, options
   - Derived connector: Extraction hiérarchies
   - API connector: Auth methods, rate limiting
4. **Hiérarchies**:
   - Adjacency list vs nested sets
   - Configuration levels
   - ID strategies
5. **Liens entre Entities**: Syntax `links:`
6. **Enrichment Plugins**: Config API enrichment
7. **Exemples Complets**:
   - Occurrence dataset simple
   - Taxonomy derived depuis occurrences
   - Plots avec géométries
   - Multi-source references

**Livrables**:
- [ ] Entity Configuration Guide complet
- [ ] Exemples annotés
- [ ] Schémas YAML validés

#### Tâche 4.4 - Plugin Migration Guide (0.25 jour)
**Fichier**: `docs/guides/plugin-migration.md` (nouveau)

**Sections**:
1. **Pourquoi Migrer**: Benefits EntityRegistry
2. **Pattern Migration**:
   - Before/After code examples
   - Étapes détaillées
3. **Résolution Table Names**: `_resolve_table_name()`
4. **Gestion Fallback**: Backward compatibility
5. **Testing Strategies**: Tests avec entities custom
6. **Checklist Migration**:
   - [ ] Import EntityRegistry
   - [ ] Modifier constructor
   - [ ] Créer méthode résolution
   - [ ] Remplacer hardcoded names
   - [ ] Écrire tests
   - [ ] Valider backward compat

**Livrables**:
- [ ] Plugin Migration Guide
- [ ] Code examples
- [ ] Checklist réutilisable

#### Tâche 4.5 - GUI User Guide (0.25 jour)
**Fichier**: `docs/guides/gui-entity-manager.md` (nouveau)

**Sections**:
1. **Introduction**: Accès Entity Manager
2. **Créer Dataset**:
   - Walkthrough avec screenshots
   - File upload
   - Field mapping
3. **Créer Reference**:
   - File-based reference
   - Derived reference (extraction)
4. **Configurer Hiérarchies**:
   - Hierarchy builder
   - Preview structure
5. **Importer Entities**:
   - Import individuel
   - Import all
   - Monitoring progress
6. **Troubleshooting GUI**:
   - Erreurs communes
   - Browser compatibility
   - Performance tips

**Livrables**:
- [ ] GUI User Guide avec screenshots
- [ ] Walkthroughs step-by-step
- [ ] FAQ GUI

**Livrables Phase 4**:
- [ ] 5 documents créés/mis à jour
- [ ] ADR/Roadmaps corrigés
- [ ] Guides complets (migration, config, plugin, GUI)
- [ ] Exemples validés

---

### PHASE 5 - TESTS & VALIDATION (Priorité 🟢)
**Durée Estimée**: 2 jours
**Objectif**: Validation complète avec entities custom

#### Tâche 5.1 - Tests Entities Custom (0.5 jour)
**Fichiers**: `tests/core/services/test_importer_custom_entities.py` (nouveau)

**Actions**:
1. Créer suite tests avec entities non-standard:
   - **Datasets**: "observations" (au lieu de "occurrences")
   - **References**: "flora" (au lieu de "taxonomy")
   - **References**: "sites" (au lieu de "plots")
2. Tests scenarios:
   - Import dataset custom
   - Extract hierarchy derived custom
   - Transform sur entities custom
   - Export depuis entities custom
3. Valider:
   - Aucune référence hardcodée ne casse
   - Registry résout correctement
   - Plugins fonctionnent generically

**Livrables**:
- [ ] Suite tests entities custom
- [ ] Coverage >90% sur nouveaux plugins
- [ ] Tests end-to-end passants

#### Tâche 5.2 - Tests GUI (0.5 jour)
**Fichiers**: `tests/gui/e2e/entity-manager.spec.ts` (nouveau)

**Actions**:
1. Tests E2E avec Playwright:
   - Scenario: Créer dataset "observations"
   - Scenario: Créer reference derived "flora"
   - Scenario: Importer entities
   - Scenario: Éditer entity existante
   - Scenario: Supprimer entity
2. Tests composants:
   - EntityFormDialog validation
   - HierarchyBuilderDialog drag-and-drop
   - FieldMappingComponent mapping
   - YamlPreviewComponent copy/download
3. Tests responsive:
   - Desktop (1920x1080)
   - Tablet (768x1024)
   - Mobile (375x667)

**Livrables**:
- [ ] Tests E2E Playwright
- [ ] Tests composants RTL
- [ ] Tests responsive

#### Tâche 5.3 - Tests Migration (0.5 jour)
**Fichiers**: `tests/migration/test_v1_to_v2.py` (nouveau)

**Actions**:
1. Créer instance test format v1:
   - `import.yml` format legacy
   - Données SQLite
2. Script migration:
   - Convert config v1 → v2
   - Migrate data SQLite → DuckDB
3. Valider:
   - Données identiques post-migration
   - Imports fonctionnent
   - Transform/Export fonctionnent
4. Tests rollback:
   - Revenir à v1 si échec

**Livrables**:
- [ ] Tests migration complets
- [ ] Script migration validé
- [ ] Procédure rollback documentée

#### Tâche 5.4 - Performance Benchmarks (0.5 jour)
**Fichiers**: `tests/performance/benchmark_imports.py` (nouveau)

**Actions**:
1. Benchmarks imports:
   - Small dataset (1k rows)
   - Medium dataset (100k rows)
   - Large dataset (1M rows)
2. Comparer:
   - Legacy system (si encore dispo)
   - Nouveau système (EntityRegistry)
3. Mesurer:
   - Temps import
   - Mémoire utilisée
   - Taille DB résultante
4. Profiling:
   - Identifier bottlenecks
   - Optimiser si nécessaire

**Livrables**:
- [ ] Suite benchmarks
- [ ] Rapport performance
- [ ] Optimisations si nécessaire

**Livrables Phase 5**:
- [ ] Tests custom entities (>90% coverage)
- [ ] Tests GUI E2E passants
- [ ] Tests migration validés
- [ ] Benchmarks performance
- [ ] Rapport final validation

---

## 📊 MÉTRIQUES DE SUIVI

### Métriques Plugins
| Catégorie | Total | Migrés | % Migré | Cible |
|-----------|-------|--------|---------|-------|
| **Loaders** | 7 | 3 | 43% | 100% (7/7) |
| **Transformers - Aggregation** | 5 | 1 | 20% | 100% (5/5) |
| **Transformers - Extraction** | 3 | 3 | 100% ✅ | 100% (3/3) |
| **Transformers - Class Objects** | 5 | 0 | 0% | 100% (5/5) |
| **Transformers - Distribution** | 3 | 0 | 0% | 100% (3/3) |
| **Transformers - Autres** | 4+ | 0 | 0% | 100% (4+/4+) |
| **Exporters** | 4 | 0 | 0% (n/a) | 0% (pas nécessaire) |
| **Widgets** | 16 | 0 | 0% (n/a) | 0% (pas nécessaire) |
| **TOTAL CRITIQUE** | **27** | **7** | **26%** | **100%** |

**Objectif Phase 1**: 27/27 plugins critiques migrés (100%)

### Métriques GUI
| Composant | Status | Cible |
|-----------|--------|-------|
| EntityManagerPage | ❌ 0% | ✅ 100% |
| EntityFormDialog | ❌ 0% | ✅ 100% |
| HierarchyBuilderDialog | ❌ 0% | ✅ 100% |
| FieldMappingComponent | ❌ 0% | ✅ 100% |
| YamlPreviewComponent | ❌ 0% | ✅ 100% |
| EntitySelector | ❌ 0% | ✅ 100% |
| Transform Editor | ❌ 0% | ✅ 100% |
| **TOTAL** | **0%** | **100%** |

**Objectif Phase 2**: 7/7 composants fonctionnels (100%)

### Métriques Tests
| Type Test | Current | Cible |
|-----------|---------|-------|
| Unit Tests | 1609 | 1700+ |
| Integration Tests | 11 | 25+ |
| E2E Tests | 0 | 10+ |
| Custom Entity Tests | 0 | 15+ |
| GUI Tests | 0 | 20+ |
| Migration Tests | 0 | 5+ |
| **Coverage** | **~80%** | **>90%** |

**Objectif Phase 5**: Coverage >90%, tous tests passants

### Métriques Documentation
| Document | Status | Cible |
|----------|--------|-------|
| ADR 0004 | ⚠️ Obsolète | ✅ À jour |
| Roadmap | ⚠️ Obsolète | ✅ À jour |
| Migration Guide | ❌ N/A | ✅ Complet |
| Entity Config Guide | ❌ N/A | ✅ Complet |
| Plugin Migration Guide | ❌ N/A | ✅ Complet |
| GUI User Guide | ❌ N/A | ✅ Complet |
| API Documentation | ⚠️ Partiel | ✅ Complet |
| **TOTAL** | **2/7 (29%)** | **7/7 (100%)** |

**Objectif Phase 4**: 7/7 documents complets

---

## 🎯 TIMELINE ESTIMÉE

### Vue d'Ensemble
| Phase | Durée | Dates Estimées | Priorité |
|-------|-------|----------------|----------|
| **Phase 1 - Plugins** | 3-5 jours | 20-25 Jan | 🔴 Critique |
| **Phase 2 - GUI** | 5-7 jours | 26 Jan - 2 Fév | 🔴 Critique |
| **Phase 3 - Transform/Export** | 2-3 jours | 3-6 Fév | 🟡 Important |
| **Phase 4 - Documentation** | 2 jours | 7-8 Fév | 🟡 Important |
| **Phase 5 - Tests/Validation** | 2 jours | 9-10 Fév | 🟢 Validation |
| **TOTAL** | **14-19 jours** | **~3-4 semaines** | |

### Planning Détaillé

**Semaine 1 (20-26 Jan)** - PLUGINS
- Lundi 20: Loaders (nested_set, spatial, adjacency_list)
- Mardi 21: Class Objects (categories, series, binary, ratio)
- Mercredi 22: Distribution (categorical, binned, time_series)
- Jeudi 23: Aggregation (top_ranking, binary_counter, statistical)
- Vendredi 24: Autres transformers (dwc, shape_processor)
- **Livrable Semaine 1**: 14 plugins migrés, tests unitaires

**Semaine 2 (27 Jan - 2 Fév)** - GUI
- Lundi 27: API Endpoints entities
- Mardi 28: EntityManagerPage + EntityList
- Mercredi 29: EntityFormDialog
- Jeudi 30: HierarchyBuilderDialog + FieldMapping
- Vendredi 31: YamlPreview + EntitySelector
- Samedi 1: Integration & Polish
- Dimanche 2: Tests E2E + Bug fixes
- **Livrable Semaine 2**: Entity Manager UI complet

**Semaine 3 (3-9 Fév)** - TRANSFORM/EXPORT & DOCS
- Lundi 3: Transform Service adaptation
- Mardi 4: Transform GUI Editor
- Mercredi 5: Export Service adaptation
- Jeudi 6: Tests transform/export
- Vendredi 7: Documentation (ADR, Roadmap, Migration Guide)
- Samedi 8: Documentation (Config Guide, Plugin Guide, GUI Guide)
- Dimanche 9: Review documentation
- **Livrable Semaine 3**: Transform/Export + Docs complètes

**Semaine 4 (10-11 Fév)** - VALIDATION
- Lundi 10: Tests entities custom + GUI E2E
- Mardi 11: Tests migration + Performance benchmarks
- **Livrable Semaine 4**: Validation complète, release ready

---

## ⚠️ RISQUES & MITIGATION

### Risques Identifiés

#### R1 - Scope Creep 🔴
**Probabilité**: Haute
**Impact**: Élevé
**Description**: Découverte de plugins/features additionnels nécessitant migration

**Mitigation**:
- Freeze scope après Phase 1
- Documenter features "nice-to-have" pour version future
- Maintenir focus sur entities critiques

#### R2 - Tests Insuffisants 🔴
**Probabilité**: Moyenne
**Impact**: Élevé
**Description**: Plugins migrés mais bugs non détectés avec entities custom

**Mitigation**:
- Phase 5 dédiée aux tests
- Tests custom entities obligatoires pour chaque plugin
- E2E tests GUI avant release
- Beta testing avec instance niamoto-nc

#### R3 - GUI Complexity 🟡
**Probabilité**: Moyenne
**Impact**: Moyen
**Description**: Interface Entity Manager trop complexe pour utilisateurs

**Mitigation**:
- UX review avec stakeholders
- Wizard simplifié pour cas communs
- Documentation extensive avec screenshots
- Tooltips/help text dans UI

#### R4 - Backward Compatibility 🟡
**Probabilité**: Faible
**Impact**: Élevé
**Description**: Instances existantes cassées par migration

**Mitigation**:
- Script migration automatique
- Tests migration extensive
- Procédure rollback documentée
- Support format v1 en parallel (transition)

#### R5 - Performance Dégradée 🟢
**Probabilité**: Faible
**Impact**: Moyen
**Description**: EntityRegistry ralentit imports/transforms

**Mitigation**:
- Benchmarks Phase 5
- Cache registry lookups
- Profiling si performance issues
- Optimisations ciblées

#### R6 - Documentation Lag 🟡
**Probabilité**: Moyenne
**Impact**: Moyen
**Description**: Documentation pas synchronisée avec code

**Mitigation**:
- Phase 4 dédiée documentation
- Review docs à chaque phase
- Exemples validés par tests
- Docs inline dans code

### Dépendances Critiques

#### D1 - Phase 1 bloque Phase 3
**Description**: Transform/Export nécessitent plugins migrés (surtout `nested_set`)
**Mitigation**: Prioriser `nested_set.py` en Phase 1 (jour 1)

#### D2 - Phase 2 API bloque Phase 2 UI
**Description**: Composants GUI nécessitent API endpoints
**Mitigation**: Tâche 2.1 (API) en premier, puis parallel UI dev

#### D3 - Phase 1+2 bloquent Phase 5
**Description**: Tests custom entities nécessitent plugins + GUI
**Mitigation**: Tests unitaires plugins en Phase 1, E2E en Phase 5

---

## 📋 CHECKLIST IMMÉDIATE (Cette Semaine)

### Lundi 20 Jan - Setup
- [x] Créer ce document de suivi ✅
- [ ] Créer branch feature: `feat/plugin-migration-phase1`
- [ ] Setup tracking: GitHub Issues/Project
- [ ] Brief équipe sur plan d'action

### Mardi 21 Jan - Phase 1 Start
- [ ] Migrer `nested_set.py` (PRIORITÉ 1)
- [ ] Tests unitaires `nested_set`
- [ ] Valider `transform.yml` fonctionne

### Mercredi 22 Jan - Loaders
- [ ] Migrer `spatial.py`
- [ ] Migrer `adjacency_list.py`
- [ ] Tests unitaires loaders

### Jeudi 23 Jan - Class Objects
- [ ] Migrer 5 class_objects transformers
- [ ] Tests unitaires class_objects

### Vendredi 24 Jan - Distribution + Review
- [ ] Migrer 3 distribution transformers
- [ ] Review code Phase 1
- [ ] Préparer merge request

---

## 🎯 CRITÈRES DE SUCCÈS GLOBAUX

### Must-Have (Release Blocker)
- [ ] 27/27 plugins critiques migrés (loaders + transformers)
- [ ] Entity Manager UI fonctionnel (CRUD entities)
- [ ] EntitySelector component utilisable partout
- [ ] Tests custom entities passants (>90% coverage)
- [ ] Migration v1→v2 validée sur niamoto-nc
- [ ] Documentation mise à jour (ADR, Roadmap, guides)
- [ ] Aucune référence hardcodée `taxon_ref`/`plot_ref`/`shape_ref` dans code critique

### Should-Have (Post-Release OK)
- [ ] Transform Editor GUI complet
- [ ] Export Service adapté
- [ ] HierarchyBuilder UI avec drag-and-drop
- [ ] Tests E2E GUI (Playwright)
- [ ] Performance benchmarks documentés
- [ ] API documentation complète (OpenAPI)

### Nice-to-Have (Future)
- [ ] API connector support (REST/GraphQL)
- [ ] Real-time import progress (WebSocket)
- [ ] Advanced field mapping (transformations inline)
- [ ] Import templates (presets pour cas communs)
- [ ] Multi-user support (locks, concurrent imports)
- [ ] Audit log (qui a importé quoi quand)

---

## 📞 CONTACTS & RESSOURCES

### Équipe
- **Lead Dev**: Julien Barbe
- **AI Assistant**: Claude Code

### Ressources Clés
- **Repo**: `/Users/julienbarbe/Dev/Niamoto/Niamoto`
- **Branch**: `feat/pipeline-editor-unified`
- **Test Instance**: `test-instance/niamoto-nc/`
- **Documentation**: `docs/`

### Outils
- **Tests**: pytest, React Testing Library, Playwright
- **Linting**: ruff, mypy, eslint
- **CI/CD**: GitHub Actions (si configuré)
- **Issue Tracking**: À définir (GitHub Issues?)

---

## 📝 NOTES & DÉCISIONS

### Décisions Architecture

**D1 - Exporters/Widgets pas migrés** (20 Jan 2025)
- **Raison**: Ne font pas de résolution table names directes
- **Impact**: Pas de migration nécessaire, économise ~20 fichiers
- **Validation**: À confirmer en Phase 3

**D2 - EntitySelector component réutilisable** (20 Jan 2025)
- **Raison**: Utilisé dans Transform, Export, Widgets configs
- **Impact**: Composant critique, haute priorité Phase 2
- **Design**: Props flexibles, filtrage par type, metadata display

**D3 - Migration v1→v2 via script automatique** (20 Jan 2025)
- **Raison**: Faciliter adoption, réduire friction utilisateurs
- **Impact**: Script Python à créer en Phase 4
- **Features**: Convert config + migrate data SQLite→DuckDB

### Questions Ouvertes

**Q1 - Support format v1 en parallel ?**
- **Options**:
  - A) Deprecate v1 immédiatement
  - B) Support v1+v2 pendant 6 mois
  - C) Converter automatique v1→v2 au runtime
- **Décision**: À prendre en Phase 4

**Q2 - GUI approach: Wizard vs Manager ?**
- **Options**:
  - A) Wizard multi-étapes (comme actuellement)
  - B) Entity Manager (liste + formulaires)
  - C) Hybrid (Manager + Quick wizard)
- **Décision**: Option B (Manager) - Plus flexible
- **Rationale**: Wizard trop rigide, Manager permet édition facile

**Q3 - API connector priorité ?**
- **Options**:
  - A) Phase 2 (avec GUI)
  - B) Phase 6 (post-release)
- **Décision**: Phase 6 - Pas bloquant pour MVP
- **Rationale**: FILE + DERIVED couvrent 90% cas d'usage

---

## 📚 RÉFÉRENCES

### Documents Liés
- [ADR 0001 - Adopt DuckDB](../09-architecture/adr/0001-adopt-duckdb.md)
- [ADR 0002 - Retire Legacy Importers](../09-architecture/adr/0002-retire-legacy-importers.md)
- [ADR 0003 - Derived References](../09-architecture/adr/0003-derived-references-with-duckdb.md)
- [ADR 0004 - Generic Import System](../09-architecture/adr/0004-generic-import-system.md)
- [Roadmap - Generic Import Refactor](./generic-import-refactor-roadmap.md)

### Code Références
- EntityRegistry: `src/niamoto/core/imports/registry.py`
- Import Engine: `src/niamoto/core/imports/engine.py`
- Config Models: `src/niamoto/core/imports/config_models.py`
- Hierarchy Builder: `src/niamoto/core/imports/hierarchy_builder.py`
- API Imports: `src/niamoto/gui/api/routers/imports.py`

### Exemples Configs
- Instance v2: `test-instance/niamoto-nc/config/import.yml`
- Root v1: `config/import.yml` (legacy)
- Transform: `test-instance/niamoto-nc/config/transform.yml`

---

**Document maintenu par**: Julien Barbe
**Dernière mise à jour**: 20 janvier 2025
**Prochaine review**: 24 janvier 2025 (fin Phase 1)
