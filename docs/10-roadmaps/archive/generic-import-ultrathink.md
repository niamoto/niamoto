# Generic Import System - Analyse & Plan de Refactorisation

**Date**: 2025-10-07
**Auteur**: Claude Code
**Statut**: Analyse approfondie
**Version**: Alpha - Pas de contrainte de rétrocompatibilité

---

## Table des Matières

0. [Journal d'avancement](#journal-davancement)
1. [Executive Summary](#1-executive-summary)
2. [Analyse de l'Architecture Actuelle](#2-analyse-de-larchitecture-actuelle)
3. [Problèmes Identifiés & Impact](#3-problèmes-identifiés--impact)
4. [Vision Cible](#4-vision-cible)
   - 4.1 [Principes Directeurs](#41-principes-directeurs)
   - 4.2 [Entity Registry Architecture](#42-entity-registry-architecture)
   - 4.3 [Import Planner & Connectors](#43-import-planner--connectors)
   - 4.4 [Lifecycle & Observability](#44-lifecycle--observability)
   - 4.5 [Configuration Cible](#45-configuration-cible)
   - 4.6 [Schéma de Base de Données Cible (DuckDB)](#46-schéma-de-base-de-données-cible-duckdb)
   - 4.7 [Configuration Transform Cible](#47-configuration-transform-cible)
5. [Analyse des Risques & Contraintes](#5-analyse-des-risques--contraintes)
6. [Solution Proposée](#6-solution-proposée)
7. [Roadmap Détaillée](#7-roadmap-détaillée)
8. [Points de Décision Critiques](#8-points-de-décision-critiques)
9. [Métriques de Succès](#9-métriques-de-succès)
10. [Conclusion & Next Steps](#conclusion--next-steps)
11. Annexe : Impact DuckDB

---

## Journal d'avancement

### 2025-10-08 (Matin)
- ✅ GeospatialExtractor, loader `direct_reference`, services Transformer/Exporter
  et endpoints GUI `/table-fields` & `/status` consomment désormais la registry et
  les helpers DuckDB.
- ✅ `legacy_registry` et `direct_reference_legacy` servent d'amorce pour les
  tables historiques tout en garantissant la transition vers DuckDB.
- ✅ Loader `join_table` et les endpoints GUI `/schema`, `/tables/*`, `query` s'appuient désormais sur la registry/DuckDB (plus de requêtes directes sur `sqlite_master`).

### 2025-10-08 (Après-midi) - Migration Complète Generic Import System
- ✅ **Suppression complète du code legacy**:
  - Éliminé `Config.get_imports_config` legacy - retourne uniquement `GenericImportConfig`
  - Supprimé complètement `src/niamoto/core/components/imports/`
  - Supprimé tous les modèles SQLAlchemy legacy (TaxonRef, PlotRef, OccurrenceModel, ShapeRef)

- ✅ **Refactorisation complète de l'ImporterService**:
  - Nouvelles méthodes: `import_reference()`, `import_dataset()`, `import_all()`
  - Tables génériques: `entity_{name}` pour références, `dataset_{name}` pour datasets
  - Support complet de `ReferenceEntityConfig` et `DatasetEntityConfig`

- ✅ **Refactorisation CLI**:
  - Nouvelles commandes: `niamoto import run`, `niamoto import reference <name>`, `niamoto import dataset <name>`, `niamoto import list`
  - Suppression des commandes legacy (`taxonomy`, `occurrences`, `plots`, `shapes`)

- ✅ **Refactorisation API GUI Backend**:
  - Endpoints génériques: `/api/imports/execute/all`, `/api/imports/execute/reference/{entity_name}`, `/api/imports/execute/dataset/{entity_name}`
  - Endpoints de métadonnées: `/api/imports/entities`, `/api/imports/status`, `/api/imports/jobs`
  - Suppression de tous les endpoints hardcodés (taxonomy, occurrences, plots, shapes)

- ✅ **Mise à jour des hooks TypeScript**:
  - `useImportStatus.ts` utilise maintenant `ImportStatusResponse` avec `references[]` et `datasets[]`
  - `import.ts` refactorisé avec `executeImport()`, `executeImportAll()`, `getEntities()`

- ✅ **Ajout de `ReferenceKind` à config_models.py**:
  - Enum pour `hierarchical`, `spatial`, `categorical`, `generic`

- ✅ **Tests complètement réécrits**:
  - `tests/core/services/test_importer.py` - 7 tests passent (100%)
  - Tests couvrent: import reference, import dataset, import_all, reset_table, validation

- 📌 **Note Frontend UI**: Les composants React utilisent encore l'ancienne structure hardcodée.
  Une refonte complète de l'UI sera nécessaire dans une phase ultérieure.

### 2025-10-09 - Références Dérivées et Fix Critique

- ✅ **Système de références dérivées opérationnel**:
  - HierarchyBuilder avec extraction DuckDB CTEs niveau par niveau
  - Support `connector.type: derived` pour extraction automatique depuis datasets
  - IDs stables générés via hash MD5 des paths hiérarchiques

- ✅ **Fix critique `incomplete_rows: skip`**:
  - **Problème**: Filtrage global trop strict (183 taxons au lieu de 1667)
  - **Solution**: Filtrage niveau par niveau dans `_build_extraction_cte()` (lignes 138-142)
  - **Résultat**: 1667 taxons extraits correctement (95 familles, 297 genres, 1213 espèces, 62 infra)

- ✅ **Migration instance test `niamoto-nc`**:
  - DuckDB opérationnel (13 MB)
  - 203 865 occurrences importées
  - Registry persisté avec 3 entités (occurrences, taxonomy, plots)
  - Configuration v2 en production

- ✅ **Tests**:
  - `test_importer.py`: 7/7 tests passent
  - `test_hierarchy_builder.py`: 4/5 tests passent (1 test obsolète à mettre à jour)

### 2025-10-10 - Démarrage Phase 8 : Plugins Génériques

- 🚧 **Phase 8 EN COURS**: Refactorisation des 12 plugins pour éliminer hardcoded table names
- 🚧 **Objectif**: Supprimer `legacy_registry.py` et tous les alias
- 🚧 **Audit plugins**: Documentation des modifications requises (voir `phase8-plugin-audit.md`)

## Actions restantes (Octobre 2025)

- ✅ Supprimer `src/niamoto/core/components/imports` et les modèles SQLAlchemy fixes - **TERMINÉ**
- ✅ Fix `incomplete_rows: skip` pour extraction hiérarchies partielles - **TERMINÉ**
- ✅ Instance test `niamoto-nc` migrée et opérationnelle - **TERMINÉ**
- 🚧 **Phase 8 EN COURS**: Refactoriser 12 plugins pour accepter EntityRegistry et éliminer hardcoded table names
- 🚧 Créer widget GUI `entity-select` pour sélection dynamique d'entités
- 🚧 Supprimer `legacy_registry.py` une fois plugins génériques
- 🚧 Consolider les tests d'intégration : seed registry partiel, `niamoto stats`, endpoints GUI `/schema`/`/query` sous DuckDB
- 🚧 Documenter la configuration générique côté GUI/CLI (guides + exemples) et mettre à jour les snapshots transform/export après retrait legacy

---

## 1. Executive Summary

### Contexte
Niamoto possède actuellement :
- ✅ **Transform** : Système générique basé sur plugins
- ✅ **Export** : Système générique basé sur plugins
- ❌ **Import** : Système rigide avec tables et modèles fixes

**Statut Alpha** : Pas de contrainte de rétrocompatibilité, possibilité de breaking changes.

### Objectif
Rendre l'import aussi générique que transform/export, permettant aux utilisateurs de :
- Définir leurs propres entités de référence (pas seulement taxonomy/plots/shapes)
- Importer n'importe quelle structure de données
- Bootstrapper automatiquement une instance depuis des fichiers bruts

### Enjeux Critiques
1. ~~**Rétrocompatibilité**~~ : ❌ N/A - Version alpha
2. **Cohérence Import-Transform-Export** : Nommage et structure doivent être unifiés
3. **Performance** : Schéma dynamique ne doit pas dégrader les performances
4. **Complexité** : Ne pas rendre le système trop abstrait au point d'être incompréhensible

### Recommandation
**Refactoring direct en 3 phases** - 8 semaines :
1. **Phase 1** (3 semaines) : Core abstractions + Generic import engine
2. **Phase 2** (3 semaines) : Bootstrap & auto-detection
3. **Phase 3** (2 semaines) : GUI integration

---

## 2. Analyse de l'Architecture Actuelle

### 2.1 Import System (Rigide)

#### Structure des Données
```yaml
# import.yml - Structure actuelle
taxonomy:
  path: imports/occurrences.csv
  hierarchy:
    levels: [family, genus, species, infra]
    taxon_id_column: id_taxonref

plots:
  type: csv
  path: imports/plots.csv
  identifier: id_plot
  locality_field: plot
  location_field: geo_pt

occurrences:
  type: csv
  path: imports/occurrences.csv
  identifier: id_taxonref
  location_field: geo_pt
```

#### Modèles de Données (SQLAlchemy)
```python
class TaxonRef(Base):
    __tablename__ = "taxon_ref"
    id = Column(Integer, primary_key=True)
    taxon_id = Column(Integer)
    full_name = Column(String(255))
    rank_name = Column(String(50))
    lft, rght, level = Columns(Integer)  # Nested Set
    parent_id = Column(Integer, ForeignKey("taxon_ref.id"))
    extra_data = Column(JSON)

class PlotRef(Base):
    __tablename__ = "plot_ref"
    # Structure similaire avec nested set

class ShapeRef(Base):
    __tablename__ = "shape_ref"
    # Structure similaire avec nested set
```

#### Importers Spécialisés
- `TaxonomyImporter` : 906 lignes, gère hierarchies taxonomiques
- `PlotImporter` : 1579 lignes, gère geometries et hierarchies spatiales
- `OccurrenceImporter` : 679 lignes, gère liens avec taxonomie
- `ShapeImporter` : Non lu mais similaire

#### Service d'Import
```python
class ImporterService:
    def __init__(self, db_path: str):
        self.taxonomy_importer = TaxonomyImporter(self.db)
        self.occurrence_importer = OccurrenceImporter(self.db)
        self.plot_importer = PlotImporter(self.db)
        self.shape_importer = ShapeImporter(self.db)
```

**Forces :**
- ✅ Robuste et testé
- ✅ Validation spécifique à chaque type
- ✅ Gestion des cas particuliers (nested sets, geometries)
- ✅ Performance optimisée

**Faiblesses :**
- ❌ Tables et noms hardcodés
- ❌ Impossible d'ajouter de nouveaux types d'entités
- ❌ Code dupliqué entre importers (nested set, validation)
- ❌ Couplage fort avec les noms de tables

### 2.2 Transform System (Générique)

#### Configuration Transform
```yaml
# transform.yml - Déjà générique !
- group_by: taxon  # ← Référence la table "taxon_ref"
  sources:
    - name: occurrences
      data: occurrences  # ← Référence la table "occurrences"
      grouping: taxon_ref  # ← Nom de table hardcodé
      relation:
        plugin: nested_set
        key: taxon_ref_id
        fields:
          parent: parent_id  # ← Noms de colonnes hardcodés
          left: lft
          right: rght

  widgets_data:
    general_info:
      plugin: field_aggregator
      params:
        fields:
          - source: taxon_ref  # ← Référence directe à la table
            field: full_name
```

**Constat Crucial :**
Le système transform est "générique" au niveau des **plugins**, mais il dépend fortement des **noms de tables** et **noms de colonnes** fixes définis lors de l'import.

**Problèmes de couplage :**
1. `group_by: taxon` → Doit correspondre à une table `taxon_ref`
2. `grouping: taxon_ref` → Nom de table hardcodé
3. `source: taxon_ref` → Référence directe à la table
4. `fields: {parent_id, lft, rght}` → Structure de nested set imposée

**Conséquence :**
Si on change le système d'import pour être générique, **tous les fichiers transform.yml existants deviennent invalides** à moins de :
- Maintenir les mêmes noms de tables (taxon_ref, plot_ref, etc.)
- OU créer un système de mapping/alias
- OU migrer automatiquement les configurations

### 2.3 Export System (Générique)

Le système d'export est déjà totalement générique car il consomme simplement les données transformées sans se soucier de leur origine.

**Pas d'impact majeur sur export**, mais il faut s'assurer que les données transformées restent dans le même format.

---

## 3. Problèmes Identifiés & Impact

### 3.1 Problème #1 : Couplage Fort avec Noms de Tables

**Symptôme :**
```yaml
# Dans transform.yml
group_by: taxon  # ← "taxon" est mappé à "taxon_ref" quelque part
source: taxon_ref  # ← Référence directe
```

**Impact :**
- Impossible d'importer une entité nommée "species" ou "locality" sans casser le système
- Les utilisateurs ne peuvent pas définir leurs propres noms d'entités
- Forte dépendance entre import.yml et transform.yml

**Gravité :** 🔴 CRITIQUE

### 3.2 Problème #2 : Modèles SQLAlchemy Fixes

**Symptôme :**
```python
# models.py
class TaxonRef(Base):
    __tablename__ = "taxon_ref"
    # Colonnes hardcodées
```

**Impact :**
- Impossible de créer de nouvelles tables sans modifier le code Python
- Pas de flexibilité pour les structures de données custom
- Maintenance difficile (ajout de colonnes = migration Python)

**Gravité :** 🔴 CRITIQUE

### 3.3 Problème #3 : Importers Spécialisés

**Symptôme :**
- `TaxonomyImporter` : 906 lignes
- `PlotImporter` : 1579 lignes
- Code dupliqué (nested sets, validation, progress tracking)

**Impact :**
- Maintenance coûteuse (bug fixes en 3+ endroits)
- Incohérence potentielle entre importers
- Ajout d'un nouveau type = copier/coller 1000+ lignes

**Gravité :** 🟡 MAJEUR

### 3.4 Problème #4 : Configuration Import Non Standard

**Symptôme :**
```yaml
# import.yml - Structure custom pour chaque type
taxonomy:
  hierarchy:
    levels: [...]
plots:
  type: csv
  identifier: id_plot
occurrences:
  identifier: id_taxonref
```

**Impact :**
- Pas de pattern unifié
- Difficile à documenter et expliquer
- GUI complexe (interface différente par type)

**Gravité :** 🟡 MAJEUR

### 3.5 Problème #5 : Relations Hiérarchiques Hardcodées

**Symptôme :**
```python
# Nested Set dans TaxonRef et PlotRef
lft = Column(Integer)
rght = Column(Integer)
level = Column(Integer)
parent_id = Column(Integer, ForeignKey("taxon_ref.id"))
```

**Impact :**
- Impossible d'utiliser d'autres types de hiérarchies (adjacency list simple, closure table)
- Logique nested set dupliquée dans TaxonomyImporter et PlotImporter
- Difficile à généraliser

**Gravité :** 🟠 MOYEN

---

## 4. Vision Cible

### 4.1 Principes Directeurs

1. **User-Defined Entities** : L'utilisateur définit ses propres entités (pas nous)
2. **Convention over Configuration** : Auto-détection intelligente avec possibilité d'override
3. **Unified Configuration** : Même structure YAML pour import/transform/export
4. **Config-first** : Tout découle de la configuration déclarative
5. **Composable Pipeline** : Import en étapes (profile → validate → ingest → relations → enrich → index)
6. **Metadata Everywhere** : Provenance, transformations, couverture FK, statistiques
7. **Fail Loud, Fail Early** : Validation avant mutation DB, transactions quand possible

### 4.2 Entity Registry Architecture

**Composant Central : Entity Registry**

Le Registry est le service central qui gère toutes les métadonnées des entités et sert de point d'accès unique pour import, transform, export et GUI.

#### 4.2.1 Responsabilités

```python
class EntityRegistry:
    """
    Central metadata service for all entities in Niamoto

    Responsibilities:
    - Register and persist entity metadata
    - Provide entity lookup by name/type
    - Manage table naming conventions
    - Track entity lifecycle state
    - Store schema versions and checksums
    """

    def register(self, entity: EntityMetadata) -> None:
        """Register a new entity with metadata"""

    def get(self, name: str) -> Optional[EntityMetadata]:
        """Get entity metadata by name"""

    def list_references(self) -> List[EntityMetadata]:
        """List all reference entities"""

    def list_datasets(self) -> List[EntityMetadata]:
        """List all dataset entities"""

    def get_relationships(self, entity_name: str) -> List[Relationship]:
        """Get all relationships for an entity"""

    def update_state(self, entity_name: str, state: EntityState) -> None:
        """Update entity lifecycle state"""

    def persist(self) -> None:
        """Persist registry to database"""

@dataclass
class EntityMetadata:
    """Metadata for a single entity"""
    name: str
    entity_type: EntityType  # reference | dataset
    kind: Optional[str]  # hierarchical | spatial | categorical
    table_name: str  # Actual DB table name
    connector_config: ConnectorConfig
    schema: EntitySchema
    relationships: List[Relationship]
    state: EntityState
    version: str
    checksum: str
    created_at: datetime
    updated_at: datetime

class EntityType(Enum):
    REFERENCE = "reference"
    DATASET = "dataset"

class EntityState(Enum):
    PLANNED = "planned"
    LOADING = "loading"
    READY = "ready"
    FAILED = "failed"

@dataclass
class EntitySchema:
    """Schema definition for an entity"""
    id_field: str
    fields: List[FieldDefinition]
    indexes: List[IndexDefinition]
    constraints: List[ConstraintDefinition]

@dataclass
class FieldDefinition:
    name: str
    type: str  # integer, float, string, text, date, geometry, json
    semantic: Optional[str]  # taxonomy.family, identifier, coordinates, etc.
    nullable: bool = True
    default: Optional[Any] = None

@dataclass
class Relationship:
    """Relationship between entities"""
    from_entity: str
    from_field: str
    to_entity: str
    to_field: str
    type: RelationType  # foreign_key | many_to_many

class RelationType(Enum):
    FOREIGN_KEY = "foreign_key"
    MANY_TO_MANY = "many_to_many"
```

#### 4.2.2 Persistence

**Metadata Table Schema (DuckDB):**

```sql
CREATE TABLE niamoto_metadata.entities (
    name VARCHAR PRIMARY KEY,
    entity_type VARCHAR NOT NULL,  -- 'reference' | 'dataset'
    kind VARCHAR,  -- 'hierarchical' | 'spatial' | 'categorical'
    table_name VARCHAR NOT NULL UNIQUE,
    connector_type VARCHAR NOT NULL,
    connector_config JSON NOT NULL,
    schema JSON NOT NULL,  -- Fields, indexes, constraints
    relationships JSON,
    state VARCHAR NOT NULL DEFAULT 'planned',
    version VARCHAR NOT NULL,
    checksum VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    metadata JSON  -- Additional metadata
);

CREATE INDEX idx_entities_type ON niamoto_metadata.entities(entity_type);
CREATE INDEX idx_entities_state ON niamoto_metadata.entities(state);
```

#### 4.2.3 Table Naming Convention

Pour éviter les collisions avec tables internes et garantir la clarté :

```python
class TableNamingStrategy:
    """Consistent table naming across Niamoto"""

    @staticmethod
    def for_reference(entity_name: str) -> str:
        """entity_<name> for references"""
        return f"entity_{entity_name}"

    @staticmethod
    def for_dataset(dataset_name: str) -> str:
        """dataset_<name> for datasets"""
        return f"dataset_{dataset_name}"

    @staticmethod
    def is_internal(table_name: str) -> bool:
        """Check if table is internal (niamoto_*)"""
        return table_name.startswith("niamoto_")

# Examples:
# species (reference) → entity_species
# sites (reference) → entity_sites
# observations (dataset) → dataset_observations
# niamoto_metadata.entities (internal) → niamoto_metadata.entities
```

**Avantages :**
- ✅ Évite collisions avec tables système
- ✅ Distinction claire reference vs dataset
- ✅ Prévisible pour transform/export
- ✅ Compatible avec conventions SQL

#### 4.2.4 Integration avec Transform/Export

**Avant (couplage fort) :**
```python
# Transform plugin hardcodé
taxon_data = db.query("SELECT * FROM taxon_ref")
```

**Après (via Registry) :**
```python
# Transform plugin dynamique
registry = EntityRegistry.load()
entity = registry.get("species")  # or whatever user named it
taxon_data = db.query(f"SELECT * FROM {entity.table_name}")

# OR avec alias pour backward compat
taxonomy_entity = registry.get_by_alias("taxonomy")  # Points to user's chosen entity
```

### 4.3 Import Planner & Connectors

#### 4.3.1 Import Planner

Le Planner valide la configuration, résout les dépendances, et crée un plan d'exécution ordonné.

```python
class ImportPlanner:
    """
    Validates configuration and creates executable import plan

    Responsibilities:
    - Validate configuration syntax and semantics
    - Resolve entity dependencies (FK order)
    - Detect circular dependencies
    - Create ordered execution plan
    - Estimate resources needed
    """

    def __init__(self, registry: EntityRegistry):
        self.registry = registry

    def create_plan(self, config: ImportConfig) -> ImportPlan:
        """
        Create executable import plan from configuration

        Steps:
        1. Validate configuration syntax (Pydantic)
        2. Validate semantic constraints (fields exist, types compatible)
        3. Build dependency graph
        4. Topological sort for execution order
        5. Create ImportPlan with ordered actions
        """
        # Validate
        validation = self._validate_config(config)
        if not validation.valid:
            raise ConfigurationError(validation.errors)

        # Resolve dependencies
        dependency_graph = self._build_dependency_graph(config)
        execution_order = self._topological_sort(dependency_graph)

        # Create plan
        actions = []
        for entity_name in execution_order:
            entity_config = config.get_entity(entity_name)
            actions.append(self._create_import_action(entity_config))

        return ImportPlan(
            actions=actions,
            estimated_duration=self._estimate_duration(actions),
            resource_requirements=self._estimate_resources(actions)
        )

    def _validate_config(self, config: ImportConfig) -> ValidationResult:
        """Comprehensive configuration validation"""
        errors = []
        warnings = []

        # Check references before datasets
        for dataset in config.datasets.values():
            for link in dataset.links:
                if link.entity not in config.references:
                    errors.append(f"Dataset {dataset.name} references unknown entity {link.entity}")

        # Check for circular dependencies
        if self._has_circular_dependencies(config):
            errors.append("Circular dependencies detected in entity relationships")

        # Check connector availability
        for entity in config.all_entities():
            if not self._connector_available(entity.connector.type):
                errors.append(f"Connector {entity.connector.type} not available")

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

    def _build_dependency_graph(self, config: ImportConfig) -> DependencyGraph:
        """Build graph of entity dependencies"""
        graph = DependencyGraph()

        # Add all entities as nodes
        for entity in config.all_entities():
            graph.add_node(entity.name)

        # Add edges for relationships
        for dataset in config.datasets.values():
            for link in dataset.links:
                # Dataset depends on reference
                graph.add_edge(dataset.name, link.entity)

        return graph

    def _topological_sort(self, graph: DependencyGraph) -> List[str]:
        """Topological sort to determine import order"""
        # Standard Kahn's algorithm
        # References before datasets that depend on them
        pass

@dataclass
class ImportPlan:
    """Executable import plan"""
    actions: List[ImportAction]
    estimated_duration: timedelta
    resource_requirements: ResourceEstimate
    created_at: datetime

    def execute(self, engine: ImportEngine) -> ImportResult:
        """Execute the plan"""
        pass

@dataclass
class ImportAction:
    """Single import action (one entity)"""
    entity_name: str
    connector: Connector
    target_table: str
    mode: ImportMode  # create | replace | append
    chunk_size: int
    checkpoint_enabled: bool

class ImportMode(Enum):
    CREATE = "create"
    REPLACE = "replace"
    APPEND = "append"
    UPDATE = "update"
```

#### 4.3.2 Connector Architecture

Les Connectors abstraient les sources de données avec une interface unifiée.

```python
from abc import ABC, abstractmethod
from typing import Iterator, Optional

class Connector(ABC):
    """
    Abstract base class for data connectors

    Connectors handle:
    - Connection to data source
    - Schema detection/profiling
    - Data streaming in chunks
    - Error handling and retries
    """

    @abstractmethod
    def connect(self, config: ConnectorConfig) -> Connection:
        """Establish connection to data source"""
        pass

    @abstractmethod
    def profile(self, connection: Connection) -> SourceProfile:
        """Profile data source (schema, stats, samples)"""
        pass

    @abstractmethod
    def stream(self, connection: Connection, chunk_size: int) -> Iterator[DataChunk]:
        """Stream data in chunks"""
        pass

    @abstractmethod
    def validate(self, connection: Connection) -> ValidationResult:
        """Validate data source"""
        pass

    def close(self, connection: Connection) -> None:
        """Close connection (optional)"""
        pass

@dataclass
class ConnectorConfig:
    """Configuration for a connector"""
    type: str
    params: Dict[str, Any]

@dataclass
class Connection:
    """Active connection to data source"""
    connector_type: str
    handle: Any  # Connector-specific handle
    metadata: Dict[str, Any]

@dataclass
class SourceProfile:
    """Profile of a data source"""
    row_count: int
    columns: List[ColumnProfile]
    sample_rows: List[Dict]
    statistics: Dict[str, Any]

@dataclass
class DataChunk:
    """Chunk of data from source"""
    data: Any  # DataFrame, List[Dict], etc.
    chunk_index: int
    total_chunks: int
    row_count: int
```

#### 4.3.3 Concrete Connectors

**DuckDB CSV Connector (Natif) :**

```python
class DuckDBCSVConnector(Connector):
    """Connector for CSV files using DuckDB native functions"""

    def connect(self, config: ConnectorConfig) -> Connection:
        """No actual connection needed, DuckDB reads directly"""
        path = config.params['path']
        if not Path(path).exists():
            raise FileNotFoundError(f"CSV file not found: {path}")

        return Connection(
            connector_type='duckdb_csv',
            handle=path,
            metadata={'format': 'csv'}
        )

    def profile(self, connection: Connection) -> SourceProfile:
        """Use DuckDB schema detection"""
        path = connection.handle

        # DuckDB auto-detects schema
        schema_df = self.db.execute(f"""
            DESCRIBE SELECT * FROM read_csv_auto('{path}')
        """).fetchdf()

        # Get sample rows
        sample_df = self.db.execute(f"""
            SELECT * FROM read_csv_auto('{path}') LIMIT 100
        """).fetchdf()

        # Get count
        count = self.db.execute(f"""
            SELECT COUNT(*) FROM read_csv_auto('{path}')
        """).fetchone()[0]

        columns = [
            ColumnProfile(
                name=row['column_name'],
                type=self._map_duckdb_type(row['column_type']),
                nullable=row['null'] == 'YES',
                unique_ratio=None,  # Could compute if needed
                null_ratio=None
            )
            for _, row in schema_df.iterrows()
        ]

        return SourceProfile(
            row_count=count,
            columns=columns,
            sample_rows=sample_df.head(10).to_dict('records'),
            statistics={'detected_by': 'duckdb_csv_auto'}
        )

    def stream(self, connection: Connection, chunk_size: int) -> Iterator[DataChunk]:
        """Stream CSV in chunks using DuckDB"""
        path = connection.handle

        # Get total count
        total = self.db.execute(f"""
            SELECT COUNT(*) FROM read_csv_auto('{path}')
        """).fetchone()[0]

        total_chunks = (total // chunk_size) + (1 if total % chunk_size else 0)

        # Stream chunks
        for i in range(total_chunks):
            offset = i * chunk_size
            chunk_df = self.db.execute(f"""
                SELECT * FROM read_csv_auto('{path}')
                LIMIT {chunk_size} OFFSET {offset}
            """).fetchdf()

            yield DataChunk(
                data=chunk_df,
                chunk_index=i,
                total_chunks=total_chunks,
                row_count=len(chunk_df)
            )

    def validate(self, connection: Connection) -> ValidationResult:
        """Validate CSV can be read"""
        try:
            path = connection.handle
            self.db.execute(f"SELECT * FROM read_csv_auto('{path}') LIMIT 1")
            return ValidationResult(valid=True, errors=[])
        except Exception as e:
            return ValidationResult(valid=False, errors=[str(e)])
```

**Spatial Connector (DuckDB Spatial Extension) :**

```python
class DuckDBSpatialConnector(Connector):
    """Connector for spatial files using DuckDB spatial extension"""

    def __init__(self, db):
        self.db = db
        # Ensure spatial extension is loaded
        self.db.execute("INSTALL spatial")
        self.db.execute("LOAD spatial")

    def connect(self, config: ConnectorConfig) -> Connection:
        """Connect to spatial file"""
        path = config.params['path']
        format = config.params.get('format', 'geojson')

        if not Path(path).exists():
            raise FileNotFoundError(f"Spatial file not found: {path}")

        return Connection(
            connector_type='duckdb_spatial',
            handle=path,
            metadata={'format': format}
        )

    def profile(self, connection: Connection) -> SourceProfile:
        """Profile spatial data"""
        path = connection.handle

        # Read with ST_Read
        schema_df = self.db.execute(f"""
            DESCRIBE SELECT * FROM ST_Read('{path}')
        """).fetchdf()

        # Sample
        sample_df = self.db.execute(f"""
            SELECT *, ST_AsText(geometry) as geometry_wkt
            FROM ST_Read('{path}')
            LIMIT 10
        """).fetchdf()

        # Count
        count = self.db.execute(f"""
            SELECT COUNT(*) FROM ST_Read('{path}')
        """).fetchone()[0]

        columns = [
            ColumnProfile(
                name=row['column_name'],
                type='geometry' if row['column_name'] == 'geometry' else self._map_duckdb_type(row['column_type']),
                nullable=row['null'] == 'YES'
            )
            for _, row in schema_df.iterrows()
        ]

        return SourceProfile(
            row_count=count,
            columns=columns,
            sample_rows=sample_df.to_dict('records'),
            statistics={'spatial': True}
        )

    def stream(self, connection: Connection, chunk_size: int) -> Iterator[DataChunk]:
        """Stream spatial data"""
        path = connection.handle

        # Similar to CSV but with ST_Read
        total = self.db.execute(f"""
            SELECT COUNT(*) FROM ST_Read('{path}')
        """).fetchone()[0]

        total_chunks = (total // chunk_size) + (1 if total % chunk_size else 0)

        for i in range(total_chunks):
            offset = i * chunk_size
            chunk_df = self.db.execute(f"""
                SELECT * FROM ST_Read('{path}')
                LIMIT {chunk_size} OFFSET {offset}
            """).fetchdf()

            yield DataChunk(
                data=chunk_df,
                chunk_index=i,
                total_chunks=total_chunks,
                row_count=len(chunk_df)
            )
```

**Connector Registry :**

```python
class ConnectorRegistry:
    """Registry of available connectors"""

    _connectors: Dict[str, Type[Connector]] = {}

    @classmethod
    def register(cls, connector_type: str, connector_class: Type[Connector]):
        """Register a connector"""
        cls._connectors[connector_type] = connector_class

    @classmethod
    def get(cls, connector_type: str) -> Type[Connector]:
        """Get connector class by type"""
        if connector_type not in cls._connectors:
            raise ValueError(f"Unknown connector type: {connector_type}")
        return cls._connectors[connector_type]

    @classmethod
    def list_available(cls) -> List[str]:
        """List available connector types"""
        return list(cls._connectors.keys())

# Register connectors
ConnectorRegistry.register('duckdb_csv', DuckDBCSVConnector)
ConnectorRegistry.register('duckdb_spatial', DuckDBSpatialConnector)
```

### 4.4 Lifecycle & Observability

#### 4.4.1 Import Job Lifecycle

**State Machine :**

```
┌─────────┐
│ PLANNED │ ← Config validated, plan created
└────┬────┘
     │
     ▼
┌─────────┐
│ LOADING │ ← Import in progress, checkpoints possible
└────┬────┘
     │
     ├─→ ┌───────┐
     │   │ READY │ ← Import completed successfully
     │   └───────┘
     │
     └─→ ┌────────┐
         │ FAILED │ ← Import failed, can be retried
         └────────┘
```

**Implementation :**

```python
class ImportJob:
    """
    Represents an import job with lifecycle management

    Features:
    - State tracking
    - Checkpointing for resume
    - Progress reporting
    - Error recovery
    """

    def __init__(self, plan: ImportPlan, registry: EntityRegistry):
        self.plan = plan
        self.registry = registry
        self.state = EntityState.PLANNED
        self.checkpoints: List[Checkpoint] = []
        self.errors: List[ImportError] = []
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

    def execute(self, engine: ImportEngine) -> ImportResult:
        """Execute the import job"""
        try:
            self._transition_to(EntityState.LOADING)
            self.started_at = datetime.now()

            for action in self.plan.actions:
                # Execute action
                result = engine.execute_action(action)

                # Create checkpoint
                checkpoint = Checkpoint(
                    entity_name=action.entity_name,
                    completed_at=datetime.now(),
                    rows_imported=result.rows_imported,
                    state=result.state
                )
                self.checkpoints.append(checkpoint)

                # Update registry
                self.registry.update_state(action.entity_name, EntityState.READY)

            self._transition_to(EntityState.READY)
            self.completed_at = datetime.now()

            return ImportResult(
                success=True,
                entities_imported=len(self.plan.actions),
                total_rows=sum(cp.rows_imported for cp in self.checkpoints),
                duration=self.completed_at - self.started_at
            )

        except Exception as e:
            self._transition_to(EntityState.FAILED)
            self.errors.append(ImportError(
                entity=action.entity_name,
                error=str(e),
                timestamp=datetime.now()
            ))
            raise

    def resume(self) -> ImportResult:
        """Resume failed import from last checkpoint"""
        if self.state != EntityState.FAILED:
            raise ValueError("Can only resume failed jobs")

        # Find last successful checkpoint
        last_checkpoint = self.checkpoints[-1] if self.checkpoints else None

        # Create new plan from remaining actions
        remaining_actions = [
            action for action in self.plan.actions
            if not any(cp.entity_name == action.entity_name for cp in self.checkpoints)
        ]

        if not remaining_actions:
            raise ValueError("No remaining actions to resume")

        # Execute remaining actions
        # ...

    def _transition_to(self, new_state: EntityState):
        """Transition to new state"""
        logger.info(f"Import job transitioning: {self.state} → {new_state}")
        self.state = new_state

@dataclass
class Checkpoint:
    """Import checkpoint for recovery"""
    entity_name: str
    completed_at: datetime
    rows_imported: int
    state: EntityState
    metadata: Dict[str, Any] = None

@dataclass
class ImportError:
    """Error during import"""
    entity: str
    error: str
    timestamp: datetime
    traceback: Optional[str] = None
```

#### 4.4.2 Observability

**Structured Logging :**

```python
import structlog

logger = structlog.get_logger()

class ObservableImportEngine:
    """Import engine with comprehensive observability"""

    def execute_action(self, action: ImportAction) -> ActionResult:
        """Execute import action with logging"""

        # Start context
        log = logger.bind(
            entity=action.entity_name,
            connector=action.connector.type,
            mode=action.mode.value,
            job_id=self.job_id
        )

        log.info("import_action_started",
                 target_table=action.target_table,
                 chunk_size=action.chunk_size)

        start_time = time.time()
        rows_processed = 0

        try:
            # Execute import
            for chunk in action.connector.stream(chunk_size=action.chunk_size):
                # Process chunk
                rows_processed += chunk.row_count

                log.debug("chunk_processed",
                         chunk_index=chunk.chunk_index,
                         rows=chunk.row_count,
                         total_rows=rows_processed)

                # Emit metric
                self.metrics.increment('rows_imported', chunk.row_count,
                                      tags={'entity': action.entity_name})

            duration = time.time() - start_time

            log.info("import_action_completed",
                    rows_imported=rows_processed,
                    duration_seconds=duration,
                    rows_per_second=rows_processed / duration if duration > 0 else 0)

            # Emit metrics
            self.metrics.timing('import_duration', duration,
                               tags={'entity': action.entity_name})
            self.metrics.gauge('entity_row_count', rows_processed,
                             tags={'entity': action.entity_name})

            return ActionResult(
                success=True,
                rows_imported=rows_processed,
                duration=duration,
                state=EntityState.READY
            )

        except Exception as e:
            log.error("import_action_failed",
                     error=str(e),
                     rows_processed=rows_processed,
                     exc_info=True)

            # Emit error metric
            self.metrics.increment('import_errors',
                                  tags={'entity': action.entity_name, 'error_type': type(e).__name__})

            raise
```

**Metrics & Progress Tracking :**

```python
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

class ProgressTracker:
    """Rich progress tracker for CLI"""

    def __init__(self):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("[bold green]{task.fields[status]}"),
        )

    def track_import(self, job: ImportJob):
        """Track import job progress"""
        with self.progress:
            # Overall task
            overall_task = self.progress.add_task(
                "Import Job",
                total=len(job.plan.actions),
                status="Starting..."
            )

            for action in job.plan.actions:
                # Entity task
                entity_task = self.progress.add_task(
                    f"Importing {action.entity_name}",
                    total=100,  # Will update as we know chunk count
                    status="Connecting..."
                )

                # Execute and update
                for chunk in action.connector.stream(chunk_size=action.chunk_size):
                    self.progress.update(
                        entity_task,
                        completed=chunk.chunk_index,
                        total=chunk.total_chunks,
                        status=f"{chunk.row_count} rows"
                    )

                self.progress.update(entity_task, status="✓ Complete")
                self.progress.advance(overall_task)
```

### 4.5 Configuration Cible

**Structure references/datasets (alignée avec refactor-roadmap) :**

```yaml
# import.yml - Nouvelle structure générique
entities:
  references:
    species:
      kind: hierarchical
      connector:
        type: duckdb_csv
        path: data/species.csv
      schema:
        id_field: species_id
        fields:
          - name: family
            type: string
            semantic: taxonomy.family
          - name: genus
            type: string
            semantic: taxonomy.genus
          - name: species
            type: string
            semantic: taxonomy.species
      hierarchy:
        strategy: recursive_cte  # DuckDB recursive CTEs
        levels: [family, genus, species]
      enrichment:
        - plugin: gbif_enricher
          config:
            url: https://api.gbif.org
            key_env: GBIF_API_KEY

    sites:
      kind: spatial
      connector:
        type: duckdb_spatial
        path: data/sites.geojson
      schema:
        id_field: site_id
        fields:
          - name: site_name
            type: string
          - name: geometry
            type: geometry
            srid: 4326

    habitats:
      kind: categorical
      connector:
        type: duckdb_csv
        path: data/habitats.csv
      schema:
        id_field: habitat_code
        fields:
          - name: habitat_type
            type: string
          - name: description
            type: text

  datasets:
    observations:
      connector:
        type: duckdb_csv
        path: data/observations.csv
      schema:
        id_field: occurrence_id
        fields:
          - name: species_code
            type: string
            reference: species.species_id
          - name: site_code
            type: string
            reference: sites.site_id
          - name: habitat_code
            type: string
            reference: habitats.habitat_code
          - name: dbh
            type: float
          - name: height
            type: float
          - name: observation_date
            type: date
      links:
        - entity: species
          field: species_code
          target_field: species_id
        - entity: sites
          field: site_code
          target_field: site_id
        - entity: habitats
          field: habitat_code
          target_field: habitat_code
      options:
        mode: replace
        chunk_size: 10000
```

**Avantages de cette structure :**
- ✅ Distinction claire `references` vs `datasets`
- ✅ Connectors explicites (DuckDB CSV, Spatial)
- ✅ Hiérarchies via recursive CTEs (pas de nested sets!)
- ⚠️ Migration à planifier pour les widgets/transformations qui utilisent encore `lft`/`rght` (proposer alias ou vue transitoire avant suppression).
- 📌 Plugins à adapter : `hierarchical_nav_widget`, `geospatial_extractor`, `top_ranking` (et `nested_set` loader / export HTML pour la préparation).
- ✅ Semantic types pour détection intelligente
- ✅ Liens FK clairs et validables
- ✅ Enrichment plugins optionnels

### 4.6 Schéma de Base de Données Cible (DuckDB)

**Convention de nommage :** `entity_<name>` pour references, `dataset_<name>` pour datasets

```sql
-- Tables créées dynamiquement par ImportEngine

-- Reference: species (hierarchical) avec Recursive CTEs (pas de nested sets!)
CREATE TABLE entity_species (
    id INTEGER PRIMARY KEY,
    species_id VARCHAR,  -- ID externe
    scientific_name VARCHAR,
    family VARCHAR,
    genus VARCHAR,
    species VARCHAR,
    parent_id INTEGER REFERENCES entity_species(id),
    extra_data JSON
);

-- Index pour performance hierarchical queries
CREATE INDEX idx_entity_species_parent ON entity_species(parent_id);
CREATE INDEX idx_entity_species_family ON entity_species(family);
CREATE INDEX idx_entity_species_genus ON entity_species(genus);

-- Queries hiérarchiques avec Recursive CTEs (simple!)
WITH RECURSIVE descendants AS (
    SELECT * FROM entity_species WHERE id = 42
    UNION ALL
    SELECT s.* FROM entity_species s
    JOIN descendants d ON s.parent_id = d.id
)
SELECT * FROM descendants;

-- Reference: sites (spatial)
CREATE TABLE entity_sites (
    id INTEGER PRIMARY KEY,
    site_id VARCHAR,
    site_name VARCHAR,
    geometry GEOMETRY,  -- DuckDB spatial extension
    extra_data JSON
);

-- Index spatial avec DuckDB spatial extension
CREATE INDEX idx_entity_sites_geom ON entity_sites USING RTREE(geometry);

-- Reference: habitats (categorical)
CREATE TABLE entity_habitats (
    id INTEGER PRIMARY KEY,
    habitat_code VARCHAR,
    habitat_type VARCHAR,
    description TEXT,
    extra_data JSON
);

-- Dataset: observations (factual data)
CREATE TABLE dataset_observations (
    id INTEGER PRIMARY KEY,
    occurrence_id VARCHAR,
    species_id INTEGER REFERENCES entity_species(id),
    site_id INTEGER REFERENCES entity_sites(id),
    habitat_id INTEGER REFERENCES entity_habitats(id),
    -- Toutes les colonnes du CSV source
    dbh DOUBLE,
    height DOUBLE,
    observation_date DATE,
    extra_data JSON
);

-- Index pour FK lookups
CREATE INDEX idx_dataset_observations_species ON dataset_observations(species_id);
CREATE INDEX idx_dataset_observations_site ON dataset_observations(site_id);
CREATE INDEX idx_dataset_observations_habitat ON dataset_observations(habitat_id);
CREATE INDEX idx_dataset_observations_date ON dataset_observations(observation_date);
```

**Avantages DuckDB :**
- ✅ Pas de `AUTOINCREMENT` complexe, juste `INTEGER PRIMARY KEY`
- ✅ Types natifs : `VARCHAR`, `DOUBLE`, `DATE`, `GEOMETRY`, `JSON`
- ✅ Recursive CTEs au lieu de nested sets (lft/rght)
- ✅ Spatial extension native pour géométries
- ✅ Compression automatique (bases 5-10x plus petites)
- ✅ Performance analytique supérieure (10-100x sur agrégations)

### 4.7 Configuration Transform Cible

**Intégration avec Entity Registry :**

```yaml
# transform.yml - Compatible avec nouveau système via Registry
- group_by: species  # ← Référence l'entité "species"
  sources:
    - name: observations
      data: dataset_observations  # ← Registry résout vers "dataset_observations"
      grouping: entity_species  # ← Registry résout vers "entity_species"
      relation:
        plugin: recursive_hierarchy  # ← Nouveau plugin pour DuckDB recursive CTEs
        key: species_id

  widgets_data:
    general_info:
      plugin: field_aggregator
      params:
        fields:
          - source: entity_species  # ← Via Registry
            field: scientific_name  # ← Champ défini dans import.yml
            target: name
          - source: entity_species
            field: family
            target: family_name
```

**Résolution via Registry :**

```python
# Dans le transformer
registry = EntityRegistry.load()
species_entity = registry.get("species")  # EntityMetadata
# species_entity.table_name = "entity_species"

observations_entity = registry.get("observations")  # EntityMetadata
# observations_entity.table_name = "dataset_observations"

# Query building devient:
query = f"""
    SELECT
        {species_entity.table_name}.scientific_name,
        COUNT(*) as occurrence_count
    FROM {observations_entity.table_name}
    JOIN {species_entity.table_name}
        ON {observations_entity.table_name}.species_id = {species_entity.table_name}.id
    GROUP BY {species_entity.table_name}.id
"""
```

**Point clé :**
- Les noms d'entités dans `import.yml` sont symboliques
- Le Registry les mappe vers les vrais noms de tables
- Transform/Export utilisent le Registry, jamais de hardcoded table names

---

## 5. Analyse des Risques & Contraintes

### 5.1 Risques Techniques

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| **Performance dégradée** | 🟡 MOYENNE | 🟡 MAJEUR | Indexes dynamiques + Benchmarking continu |
| **Bugs sur cas edge** | 🟡 MOYENNE | 🟡 MAJEUR | Tests exhaustifs + Cas de test variés |
| **Complexité accrue** | 🟠 MOYENNE | 🟠 MOYEN | Documentation claire + Abstractions simples |
| **Over-engineering** | 🟠 MOYENNE | 🟠 MOYEN | Itérations courtes + Validation utilisateur |
| **Couplage persistant des plugins (Config/DB)** | 🟡 MOYENNE | 🟠 MAJEUR | Migrer vers le Registry
et l'adaptateur DuckDB durant la refonte (éviter un refactor intermédiaire inutile).

### 5.2 Contraintes Business

1. **Timeline** : Besoin d'une solution viable en 8 semaines
2. **Utilisateurs** : Scientifiques non-techniques qui ont besoin de simplicité
3. **Documentation** : Doit être mise à jour en parallèle avec le développement
4. **Testing** : Nécessite datasets variés pour validation

### 5.3 Contraintes Techniques (avec DuckDB)

1. ~~**SQLite** : Limitations sur ALTER TABLE complexe~~ → **DuckDB** : DDL flexible avec CREATE OR REPLACE
2. ~~**Nested Sets** : Algorithme complexe, difficile à généraliser~~ → **Recursive CTEs** : Simple et performant
3. ~~**Géométries** : Validation et stockage WKT nécessitent traitement spécial~~ → **Spatial Extension** : Support natif
4. **Hiérarchies** : Peuvent être profondes (8+ niveaux), performance critique → Recursive CTEs optimisés
5. **Dynamic Schema** : Création de tables/indexes à la volée nécessite validation rigoureuse → DuckDB schema detection aide

**Migration DuckDB élimine la majorité des contraintes techniques!**

---

## 6. Solution Proposée

**Approche : Refactoring Direct en 3 Phases**

Sans contrainte de rétrocompatibilité, nous pouvons adopter une approche plus directe et efficace :

### Vue d'Ensemble

**Timeline :** 8 semaines (au lieu de 12)
**Stratégie :** Remplacer complètement le système existant par une architecture générique propre

### Architecture Cible (avec DuckDB)

```
┌─────────────────────────────────────────────────────────────────┐
│                     Configuration Layer                         │
│  ImportConfig (Pydantic) → references + datasets                │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Entity Registry                            │
│  - EntityMetadata (name, type, table_name, schema, state)       │
│  - Persistence (niamoto_metadata.entities)                      │
│  - Table naming (entity_*, dataset_*)                           │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Import Planner                             │
│  - Validate config (syntax + semantics)                         │
│  - Build dependency graph                                       │
│  - Topological sort (execution order)                           │
│  - Create ImportPlan (ordered actions)                          │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Import Engine                              │
│  - Execute ImportPlan                                           │
│  - Connectors (DuckDB CSV, Spatial, API)                       │
│  - Stream data in chunks                                        │
│  - Create tables (entity_*, dataset_*)                          │
│  - Enforce relationships                                        │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Observability                              │
│  - ImportJob (state machine: planned → loading → ready/failed) │
│  - Structured logging (structlog)                               │
│  - Metrics (rows_imported, duration, errors)                    │
│  - Progress tracking (Rich)                                     │
│  - Checkpoints (for resume)                                     │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                      DuckDB Store                               │
│  - Tables: entity_*, dataset_*, niamoto_metadata.*              │
│  - Recursive CTEs (hierarchies)                                 │
│  - Spatial extension (geometry)                                 │
│  - Native CSV/Parquet ingestion                                 │
└─────────────────────────────────────────────────────────────────┘
                                ↓
                    ┌───────────┴───────────┐
                    ↓                       ↓
              Transform                  Export
           (via Registry)            (via Registry)
```

**Composants Clés :**

1. **Entity Registry** : Métadonnées centralisées (voir 4.2)
2. **Import Planner** : Validation + résolution dépendances (voir 4.3)
3. **Connectors** : Abstractions sources de données (voir 4.3)
4. **Import Engine** : Exécution plan avec observability (voir 4.4)
5. **DuckDB Store** : Base analytique performante
6. **Bootstrap System** : Profiling + génération config (Phase 2)
7. **GUI Integration** : Import wizard (Phase 3)

### Phases de Développement

#### Phase 1 : Entity Registry + Import Engine (3 semaines)

**Semaine 1 : Entity Registry & Config**
- Implémenter `EntityRegistry` avec persistence (DuckDB metadata table)
- Créer `EntityMetadata`, `EntitySchema`, `FieldDefinition` (Pydantic)
- Table naming strategy (`entity_*`, `dataset_*`)
- Config loader pour nouvelle structure `references`/`datasets`
- Migration DuckDB : CREATE OR REPLACE, spatial extension setup

**Semaine 2 : Import Planner & Connectors**
- Implémenter `ImportPlanner` (validation, dependency resolution, topological sort)
- Créer `Connector` interface + `DuckDBCSVConnector` (utilise `read_csv_auto`)
- Créer `DuckDBSpatialConnector` (utilise `ST_Read`, spatial extension)
- `ConnectorRegistry` pour enregistrement connectors
- Tests validation config et résolution dépendances

**Semaine 3 : Import Engine & Observability**
- Implémenter `ImportEngine` avec exécution plan
- `ImportJob` avec state machine (planned → loading → ready/failed)
- Structured logging (structlog), metrics, progress tracking (Rich)
- Checkpointing pour resume
- Tests end-to-end avec DuckDB

**Livrables Phase 1 :**
- ✅ Entity Registry opérationnel avec DuckDB
- ✅ Import Planner validant config et résolvant dépendances
- ✅ Connectors DuckDB (CSV, Spatial)
- ✅ Import Engine avec observability
- ✅ Tests coverage > 85%
- ✅ Performance DuckDB validée (10-100x plus rapide que SQLite sur agrégations)

#### Phase 2 : Bootstrap & Auto-detection (3 semaines)

**Semaine 4 : Data Profiler**
- Implémenter `DataProfiler` avec détection intelligente
- Détection types (hierarchical, spatial, factual)
- Détection relations (foreign keys)
- Scoring de confiance

**Semaine 5 : Config Generator**
- Implémenter `ConfigGenerator`
- Génération automatique `import.yml`
- Validation cohérence
- Suggestions intelligentes

**Semaine 6 : CLI & Tests**
- CLI: `niamoto bootstrap <data_dir>`
- Tests sur datasets variés
- Accuracy testing (> 85%)
- Documentation bootstrap process

**Livrables Phase 2 :**
- ✅ Bootstrap automatique fonctionnel
- ✅ Accuracy détection > 85%
- ✅ CLI user-friendly
- ✅ Documentation complète

#### Phase 3 : GUI Integration (2 semaines)

**Semaine 7 : Import Wizard**
- Composants React: Upload, Analysis, Review
- Éditeur visuel de configuration
- Preview des données
- Validation en temps réel

**Semaine 8 : Finalisation**
- Tests E2E complets
- Polish UI/UX
- Documentation utilisateur
- Video tutorial

**Livrables Phase 3 :**
- ✅ GUI complète et intuitive
- ✅ User testing réussi
- ✅ Documentation complète
- ✅ Ready for production

### Avantages de Cette Approche

✅ **Simplicité** : Pas de code legacy à maintenir
✅ **Rapidité** : 8 semaines au lieu de 12
✅ **Qualité** : Architecture propre dès le départ
✅ **Flexibilité** : Pas de contraintes historiques
✅ **Testabilité** : Code neuf, facile à tester

### Gestion du Risque

Sans rétrocompatibilité, les risques sont réduits mais nécessitent quand même attention :

**Stratégie de mitigation :**
1. **Tests exhaustifs** : Datasets variés, cas edge
2. **Validation continue** : Benchmarking performance à chaque phase
3. **Documentation parallèle** : Docs écrites pendant développement
4. **User feedback early** : Tests utilisateurs dès Phase 2
5. **Rollback plan** : Possibilité de revenir à l'ancien système si critique

---

## 7. Roadmap Détaillée

La roadmap complète est décrite dans la [Section 6](#6-solution-proposée). Cette section fournit uniquement des notes d'implémentation critiques.

### Phase 1 : Core Abstractions + Generic Engine (Semaines 1-3)

**Composants clés à implémenter :**

1. **BaseEntityImporter** (`src/niamoto/core/imports/base.py`)
   - Méthodes communes : `validate_file()`, `load_data()`, `batch_commit()`, `handle_extra_data()`
   - Gestion d'erreurs standardisée
   - Progress tracking intégré

2. **HierarchyManager** (`src/niamoto/core/imports/hierarchy.py`)
   - Support nested sets (prioritaire)
   - Interface pour futurs types de hiérarchies (adjacency list, closure table)
   - Méthodes : `build_hierarchy()`, `update_nested_set_values()`, `validate_hierarchy()`

3. **GeometryValidator** (`src/niamoto/core/imports/geometry.py`)
   - Validation WKT/WKB/GeoJSON
   - Conversion vers WKT unifié
   - Agrégation de géométries pour hiérarchies

4. **DynamicTableFactory** (`src/niamoto/core/imports/table_factory.py`)
   - Création tables avec SQLAlchemy MetaData
   - Mapping types : `{integer, float, string, text, date, geometry, json}`
   - Génération automatique d'indexes

5. **GenericEntityImporter** (`src/niamoto/core/imports/generic_importer.py`)
   - Utilise tous les composants ci-dessus
   - Gère les 3 types d'entités : hierarchical, spatial, categorical
   - Linking automatique entre entités

**Points d'attention :**
- Benchmarking continu vs. ancien système
- Tests avec datasets réels dès semaine 2
- Documentation parallèle au code

### Phase 2 : Bootstrap & Auto-detection (Semaines 4-6)

**Composants clés à implémenter :**

1. **DataProfiler** (`src/niamoto/core/imports/profiler.py`)
   - Détection patterns taxonomiques (binomial nomenclature)
   - Détection géométries (WKT, coordonnées)
   - Détection identifiants (unique ratio > 0.95)
   - Détection relations (patterns `*_id`, `*_code`)

2. **ConfigGenerator** (`src/niamoto/core/imports/config_generator.py`)
   - Génère `import.yml` depuis profiles
   - Validation cohérence (références utilisées, liens valides)
   - Scoring de confiance global

3. **CLI Bootstrap** (`src/niamoto/cli/commands/bootstrap.py`)
   - Command: `niamoto bootstrap <data_dir>`
   - Flags: `--auto-confirm`, `--output`, `--preview`
   - Workflow: Analyze → Generate → Preview → Import

**Target accuracy :**
- Détection type d'entité : > 90%
- Détection relations : > 80%
- Configuration utilisable sans édition : > 70%

### Phase 3 : GUI Integration (Semaines 7-8)

**Composants clés à implémenter :**

1. **Backend API** (`src/niamoto/gui/api/routers/imports.py`)
   - `POST /api/imports/analyze` : Analyse fichiers uploadés
   - `POST /api/imports/generate` : Génère configuration
   - `POST /api/imports/run` : Execute import
   - `GET /api/imports/status/{id}` : Status import en cours

2. **Frontend Wizard** (`src/niamoto/gui/ui/src/components/import/`)
   - `ImportWizard.tsx` : Container principal
   - `UploadStage.tsx` : Drag & drop files
   - `AnalysisStage.tsx` : Affichage profiles
   - `ReviewStage.tsx` : Édition configuration
   - `ConfigEditor.tsx` : Éditeur visuel YAML
   - `ImportProgressStage.tsx` : Progress real-time

**User testing :**
- Minimum 3 utilisateurs non-techniques
- Scénarios : Import taxonomie, import spatial, import mixte
- Métriques : Time to completion, errors, satisfaction

**Critères de succès :**
- Import complet < 10 minutes (upload → données importées)
- Éditions configuration < 3 en moyenne
- Satisfaction utilisateur > 4/5

---

## 8. Points de Décision Critiques

### 8.1 Naming Strategy

**Question :** Comment nommer les tables génériques?

**Options :**

A. **Suffixe "_ref" systématique** (Recommandé)
```yaml
entities:
  species: {...}  # → Table: species_ref
  sites: {...}    # → Table: sites_ref
```

✅ **Pros :**
- Convention claire et cohérente
- Facilite la distinction reference vs. data tables
- Transform configs predictibles

❌ **Cons :**
- Convention imposée

**B. User-defined table names**
```yaml
entities:
  species:
    table_name: custom_species_table  # Override optionnel
```

✅ **Pros :** Flexibilité totale
❌ **Cons :** Peut créer confusion, noms incohérents

**Recommandation :** **Option A** (suffixe systématique) avec possibilité d'override si absolument nécessaire

---

### 8.2 Hierarchy System

**Question :** Quel système de hiérarchie généraliser?

**Options :**

A. **Nested Set uniquement** (Actuel)
- ✅ Performance excellente pour requêtes de sous-arbres
- ❌ Insertions coûteuses
- ❌ Complexe à maintenir

B. **Adjacency List** (Simple parent_id)
- ✅ Simple, insertions rapides
- ❌ Requêtes de sous-arbres complexes (recursive CTEs)

C. **Hybrid** (Nested Set + Adjacency) (Recommandé)
- ✅ Meilleur des deux mondes
- ✅ Fallback si nested set échoue
- ❌ Légèrement plus de storage

**Recommandation :** **Option C** - Hybrid

```yaml
entities:
  species:
    hierarchy:
      type: nested_set  # ou 'adjacency_list'
      levels: [family, genus, species]
```


---

## 9. Métriques de Succès

### 9.1 Métriques Techniques

| Métrique | Target | Mesure |
|----------|--------|--------|
| **Test Coverage** | > 85% | Lignes de code couvertes |
| **Performance Import** | < 10% dégradation | Temps d'import dataset test |
| **Auto-detection Accuracy** | > 85% | % configs correctes sans édition |
| **API Response Time** | < 2s | Temps analyse fichier |

### 9.2 Métriques Utilisateur

| Métrique | Target | Mesure |
|----------|--------|--------|
| **Time to First Import** | < 10 min | Temps upload → import complet |
| **User Edits Required** | < 3 | Nb modifications config auto-générée |
| **Error Rate** | < 5% | % imports échouant |
| **User Satisfaction** | > 4/5 | Survey post-utilisation |

### 9.3 Métriques Business

| Métrique | Target | Mesure |
|----------|--------|--------|
| **Adoption Rate** | > 90% en 3 mois | % utilisateurs utilisant nouveau système |
| **New Entity Types** | > 5 types créés | Diversité entités custom créées par utilisateurs |
| **Support Tickets** | < 2/semaine | Tickets liés à import |
| **Documentation Quality** | > 4/5 | Feedback utilisateurs sur docs |
| **Bootstrap Success Rate** | > 80% | % bootstraps réussis sans intervention |

---

## Conclusion & Next Steps

### Résumé

Cette analyse ultrathink propose un refactoring direct du système d'import Niamoto en **3 phases sur 8 semaines** :

1. **Phase 1 (3 sem)** : Core abstractions + Generic import engine
2. **Phase 2 (3 sem)** : Bootstrap & auto-detection
3. **Phase 3 (2 sem)** : GUI integration

**Approche clé :** Refactoring direct sans contrainte de rétrocompatibilité, architecture propre dès le départ.

**Avantages du statut alpha :**
- ✅ Pas de code legacy à maintenir
- ✅ Architecture optimale sans compromis
- ✅ Timeline réduite (8 vs 12 semaines)
- ✅ Simplicité accrue

### Actions Immédiates

1. **Validation Équipe** (Semaine 0)
   - Review ce document
   - Décisions sur points critiques (Naming, Hierarchy)
   - Validation timeline 8 semaines
   - Préparation datasets de test

- ✅ Module `src/niamoto/core/imports/config_models.py` introduit (Pydantic) pour modéliser les entités/connexions décrites dans cette roadmap.
- ✅ Tests unitaires `tests/core/imports/test_config_models.py` validant parsing et règles de base (alias id/id_field, hiérarchie, options dataset).
- ✅ ADR 0001 « Adoption de DuckDB » et ADR 0002 « Retrait des importeurs legacy » publiés (`docs/09-architecture/adr/`).
- ✅ Entity Registry initiale (`src/niamoto/core/imports/registry.py`) + tests (`tests/core/imports/test_registry.py`).
- ✅ Première abstraction `Database` hybride (DuckDB/SQLite) avec chargement d’extensions spatiales et API `fetch_all` partagée.
- ✅ `TransformerService` et `ExporterService` instancient la registry et résolvent les tables via alias (fallback si absence).
- ✅ Endpoints GUI (`/table-fields` & `/status`), loader `direct_reference` et transformer `geospatial_extractor` utilisent désormais la registry + helpers DB, sans PRAGMA SQLite.
- 🔜 Prototype adaptateur DuckDB (connexion + introspection) et migration des services vers la registry.

2. **Setup Projet** (Semaine 0)
   - Créer feature branch `feat/generic-import`
   - Setup environnement de développement
   - Préparer suite de tests avec datasets variés
   - CI/CD pour tests automatiques

3. **Kick-off Phase 1** (Semaine 1)
   - Démarrer implémentation BaseEntityImporter
   - Analyser code existant pour extraction logique
   - Documentation technique en parallèle

### Risques Majeurs à Monitorer

1. ⚠️ **Complexité technique** : Nested sets et géométries nécessitent attention
2. ⚠️ **Performance** : Benchmarking continu vs. baseline
3. ⚠️ **User Experience** : GUI doit être intuitive, user testing dès que possible
4. ⚠️ **Over-engineering** : Garder la simplicité, itérations courtes

### Success Factors

- ✅ Tests exhaustifs à chaque étape
- ✅ Benchmarking performance systématique
- ✅ Documentation parallèle au développement
- ✅ User feedback précoce (Phase 2)
- ✅ Architecture simple et claire
- ✅ Code reviews régulières

### Livrables Finaux (Semaine 8)

- ✅ Système d'import générique fonctionnel
- ✅ Support entités custom (hierarchical, spatial, categorical)
- ✅ Bootstrap automatique avec > 85% accuracy
- ✅ GUI complète avec wizard d'import
- ✅ Documentation complète (technique + utilisateur)
- ✅ Suite de tests > 85% coverage
- ✅ Performance validée

---

**Prêt à démarrer?** 🚀
## Annexe : Impact du Passage à DuckDB sur la Refactorisation {#annexe-impact-duckdb}

### Contexte

DuckDB offre des capacités significativement supérieures à SQLite pour l'import et l'analyse de données. Cette annexe analyse l'impact potentiel sur la refactorisation du système d'import.

---

## 1. Avantages Majeurs de DuckDB

### 1.1 Import Natif de Données

**Capacités natives :**
```sql
-- SQLite : Nécessite pandas + transformation
df = pd.read_csv('data.csv')
df.to_sql('table', conn)

-- DuckDB : Direct, avec détection automatique
CREATE TABLE species AS
SELECT * FROM read_csv_auto('data.csv');

-- Avec options
CREATE TABLE species AS
SELECT * FROM read_csv('data.csv',
    auto_detect=true,
    header=true,
    delimiter=',',
    compression='gzip'
);
```

**Formats supportés nativement :**
- CSV/TSV (avec `read_csv_auto()`)
- Parquet (`read_parquet()`)
- JSON (`read_json_auto()`)
- Excel via extension
- **GeoParquet** pour données spatiales

**Avantage :** Élimine le besoin de pandas pour la plupart des imports.

### 1.2 Détection Automatique de Schéma

```sql
-- DuckDB détecte automatiquement les types
DESCRIBE SELECT * FROM read_csv_auto('observations.csv');

-- Output:
-- column_name | column_type | null | key | default | extra
-- id          | INTEGER     | NO   |     |         |
-- species_id  | VARCHAR     | YES  |     |         |
-- dbh         | DOUBLE      | YES  |     |         |
-- date        | DATE        | YES  |     |         |
```

**Impact sur notre refactorisation :**
- ✅ `DataTypeDetector` peut devenir **beaucoup plus simple**
- ✅ Utiliser directement les capacités DuckDB au lieu de réinventer
- ✅ Réduction significative du code custom

### 1.3 Hiérarchies avec Recursive CTEs

**Actuellement (Nested Sets) :**
```sql
-- Complexe : calcul lft/rght, updates coûteux
UPDATE taxon_ref SET lft = ..., rght = ... -- Algorithme complexe
```

**Avec DuckDB (Recursive CTEs) :**
```sql
-- Simple et élégant
WITH RECURSIVE taxon_tree AS (
    -- Anchor: root nodes
    SELECT id, name, parent_id, 1 as level,
           CAST(name AS VARCHAR) as path
    FROM taxon_ref
    WHERE parent_id IS NULL

    UNION ALL

    -- Recursive: children
    SELECT t.id, t.name, t.parent_id, tt.level + 1,
           tt.path || ' > ' || t.name
    FROM taxon_ref t
    JOIN taxon_tree tt ON t.parent_id = tt.id
)
SELECT * FROM taxon_tree;

-- Obtenir tous les descendants d'un taxon
WITH RECURSIVE descendants AS (
    SELECT * FROM taxon_ref WHERE id = 42
    UNION ALL
    SELECT t.* FROM taxon_ref t
    JOIN descendants d ON t.parent_id = d.id
)
SELECT * FROM descendants;
```

**Avantages :**
- ✅ **Beaucoup plus simple** que nested sets
- ✅ Insertions/updates simples (juste parent_id)
- ✅ Pas de recalcul lft/rght
- ✅ Performance excellente pour queries hiérarchiques
- ✅ Code `HierarchyManager` drastiquement simplifié

**Inconvénient nested sets (peut être éliminé) :**
- ❌ Complexité du code
- ❌ Maintenance difficile
- ❌ Updates coûteux

### 1.4 Extension Spatial Native

```sql
-- Installation extension spatial
INSTALL spatial;
LOAD spatial;

-- Import GeoJSON direct
CREATE TABLE sites AS
SELECT * FROM ST_Read('sites.geojson');

-- Opérations spatiales
SELECT
    name,
    ST_AsText(geometry) as wkt,
    ST_Area(geometry) as area,
    ST_Centroid(geometry) as centroid
FROM sites;

-- Spatial joins
SELECT o.*, s.name as site_name
FROM observations o
JOIN sites s
ON ST_Contains(s.geometry, ST_Point(o.longitude, o.latitude));
```

**Avantages :**
- ✅ Support natif WKT, WKB, GeoJSON
- ✅ Opérations spatiales performantes
- ✅ Pas besoin de shapely/geopandas pour validation
- ✅ `GeometryValidator` simplifié

### 1.5 Performance Analytique

**Optimisations OLAP :**
- Compression automatique (réduction 5-10x taille)
- Vectorisation (SIMD)
- Parallélisme automatique
- Cache-aware algorithms

**Impact transform phase :**
```sql
-- Agrégations complexes beaucoup plus rapides
SELECT
    taxon_id,
    COUNT(*) as occurrences,
    AVG(dbh) as avg_dbh,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY height) as median_height,
    ST_ConvexHull(ST_Collect(geometry)) as distribution_hull
FROM observations
GROUP BY taxon_id;
```

Performance : **10-100x plus rapide** que SQLite sur agrégations complexes.

---

## 2. Impact sur l'Architecture de la Refactorisation

### 2.1 Simplifications Majeures

**Composants qui deviennent plus simples :**

| Composant | Actuellement | Avec DuckDB | Réduction Complexité |
|-----------|--------------|-------------|---------------------|
| `DataTypeDetector` | ~300 lignes analyse pandas | ~50 lignes wrapper DuckDB | -83% |
| `HierarchyManager` | ~500 lignes nested sets | ~100 lignes recursive CTEs | -80% |
| `GeometryValidator` | ~200 lignes shapely | ~50 lignes spatial extension | -75% |
| `DynamicTableFactory` | ~400 lignes SQLAlchemy | ~150 lignes SQL direct | -62% |
| **Total** | **~1400 lignes** | **~350 lignes** | **-75%** |

### 2.2 Nouvelle Architecture Simplifiée

```python
# Avec DuckDB, l'import devient trivial
class DuckDBEntityImporter:
    """Simplified importer leveraging DuckDB capabilities"""

    def import_entity(self, entity_name: str, config: Dict) -> int:
        """Import entity using DuckDB native functions"""
        source = config['source']

        # 1. Auto-detect and create table (ONE LINE!)
        self.db.execute(f"""
            CREATE TABLE {entity_name}_ref AS
            SELECT * FROM read_csv_auto('{source}')
        """)

        # 2. Add hierarchy columns if needed (simple)
        if config.get('kind') == 'hierarchical':
            self._add_hierarchy_columns(entity_name)

        # 3. Validate spatial data if needed
        if config.get('kind') == 'spatial':
            self._validate_spatial(entity_name, config['geometry']['field'])

        return self.db.execute(f"SELECT COUNT(*) FROM {entity_name}_ref").fetchone()[0]

    def _add_hierarchy_columns(self, table: str):
        """Just add parent_id - no lft/rght needed!"""
        # DuckDB recursive CTEs handle hierarchy traversal
        pass
```

**Code réduit de ~75%** car on utilise les capacités natives de DuckDB!

### 2.3 Bootstrap Simplifié

```python
class DuckDBDataProfiler:
    """Leverage DuckDB's schema detection"""

    def profile(self, file_path: Path) -> DatasetProfile:
        # DuckDB fait le travail dur
        schema = self.db.execute(f"""
            DESCRIBE SELECT * FROM read_csv_auto('{file_path}')
        """).fetchdf()

        # Juste enrichir avec détection sémantique
        columns = [
            self._enrich_column_profile(row)
            for _, row in schema.iterrows()
        ]

        return DatasetProfile(
            file_path=file_path,
            columns=columns,
            detected_type=self._detect_type(columns)
        )
```

---

## 3. Considérations et Trade-offs

### 3.1 Avantages DuckDB pour Niamoto

✅ **Import simplifié** : 75% moins de code
✅ **Performance** : 10-100x plus rapide sur agrégations
✅ **Hiérarchies simples** : Recursive CTEs au lieu de nested sets
✅ **Spatial natif** : Meilleur support géospatial
✅ **Schéma dynamique** : Détection automatique
✅ **Files-as-tables** : Peut query directement des CSV sans import
✅ **Compression** : Bases de données 5-10x plus petites

### 3.2 Inconvénients / Considérations

⚠️ **Adoption** : DuckDB moins connu que SQLite
⚠️ **API différente** : Nécessite migration du code existant
⚠️ **Extensions** : Spatial extension nécessite installation
⚠️ **Write workload** : SQLite parfois meilleur pour write-heavy (mais Niamoto est read-heavy après import)

### 3.3 Compatibilité avec Architecture Actuelle

**Migration SQLite → DuckDB :**
```python
# DuckDB peut lire directement des bases SQLite!
import duckdb

conn = duckdb.connect('niamoto.duckdb')

# Importer depuis SQLite
conn.execute("INSTALL sqlite")
conn.execute("LOAD sqlite")
conn.execute("ATTACH 'old_niamoto.db' AS sqlite_db (TYPE sqlite)")

# Copier tables
conn.execute("CREATE TABLE taxon_ref AS SELECT * FROM sqlite_db.taxon_ref")
```

---

## 4. Recommandations

### 4.1 Scénario Optimal : Refactorisation + DuckDB

**Timeline ajustée :**

| Phase | Avec SQLite | Avec DuckDB | Économie |
|-------|-------------|-------------|----------|
| Phase 1 | 3 semaines | **2 semaines** | -33% |
| Phase 2 | 3 semaines | **2 semaines** | -33% |
| Phase 3 | 2 semaines | 2 semaines | 0% |
| **Total** | **8 semaines** | **6 semaines** | **-25%** |

**Justification réduction Phase 1 :**
- DataTypeDetector : Utilise `read_csv_auto()` → -2 jours
- HierarchyManager : Recursive CTEs simples → -2 jours
- GeometryValidator : Extension spatial → -1 jour
- DynamicTableFactory : SQL direct → -2 jours

**Justification réduction Phase 2 :**
- DataProfiler : Wrapper DuckDB → -3 jours
- ConfigGenerator : Moins de validation nécessaire → -2 jours

### 4.2 Proposition Concrète

**Option A : Migration immédiate à DuckDB** ✅ **RECOMMANDÉ**

**Avantages :**
- Architecture plus simple dès le départ
- Timeline réduite (6 vs 8 semaines)
- Code plus maintenable (75% moins de lignes)
- Performance supérieure
- Fonctionnalités natives (spatial, recursive CTEs)

**Risques :**
- Nécessite apprentissage DuckDB
- Migration bases existantes (mais facile avec ATTACH)

**Option B : SQLite d'abord, DuckDB plus tard**

**Avantages :**
- Pas de changement de technologie pendant refactorisation
- Familiarité avec SQLite

**Inconvénients :**
- Code plus complexe
- Timeline plus longue
- Refactorisation supplémentaire nécessaire pour DuckDB plus tard

### 4.3 Architecture Cible avec DuckDB

```
src/niamoto/core/imports/
├── base.py                    # BaseEntityImporter (simplifié)
├── duckdb_importer.py        # DuckDB-specific importer (NEW)
├── hierarchy.py              # Recursive CTEs (simple)
├── spatial.py                # Wrapper spatial extension
├── profiler.py               # Utilise DuckDB schema detection
├── config_generator.py       # Simplifié
└── bootstrap.py              # Orchestration

# Hiérarchies
- Pas de nested sets (lft/rght)
+ Adjacency list (parent_id)
+ Recursive CTEs pour queries

# Spatial
- Pas de WKT custom validation
+ Extension spatial native
+ ST_* functions

# Import
- Pas de pandas transformation
+ read_csv_auto() direct
+ CREATE TABLE AS SELECT
```

---

## 5. Décision Requise

### Question Clé

**Devons-nous intégrer le passage à DuckDB dans cette refactorisation?**

**Arguments POUR (⭐ Recommandé) :**
- ✅ Simplifie drastiquement la refactorisation
- ✅ Réduit timeline de 25% (6 vs 8 semaines)
- ✅ Code 75% plus simple
- ✅ Performance supérieure
- ✅ Pas de refactorisation future nécessaire
- ✅ Niamoto est idéal pour DuckDB (read-heavy, analytique)

**Arguments CONTRE :**
- ⚠️ Changement technologique supplémentaire
- ⚠️ Courbe d'apprentissage
- ⚠️ Migration bases existantes (mais simple)

### Recommandation Finale

**JE RECOMMANDE FORTEMENT d'intégrer DuckDB dans cette refactorisation.**

**Justification :**
1. Architecture devient **beaucoup plus simple**
2. Timeline **réduite** au lieu d'allongée
3. Évite une **double refactorisation** (SQLite → DuckDB plus tard)
4. DuckDB est **parfaitement adapté** à Niamoto (OLAP, analytique)
5. Migration facile grâce à `ATTACH` SQLite

**Timeline ajustée : 6 semaines au lieu de 8** 🚀

---

## Conclusion

Le passage à DuckDB transforme cette refactorisation d'un projet complexe en un projet **significativement plus simple**. Les capacités natives de DuckDB (import automatique, recursive CTEs, spatial extension) éliminent la majorité de la complexité du code custom.

**Next step :** Décision sur DuckDB + ajustement planning si accepté.
