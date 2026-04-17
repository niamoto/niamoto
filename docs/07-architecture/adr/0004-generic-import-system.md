# ADR 0004 — Generic Import System: Configuration-Driven Architecture

*Status: Adopted (2025-10-13)*

## Context

Prior to this refactoring, Niamoto's import system was based on four specialized importers:

- `TaxonomyImporter` — Hardcoded to import to `taxon_ref` table with nested set calculations
- `PlotImporter` — Hardcoded to import to `plot_ref` table
- `ShapeImporter` — Hardcoded to import to `shape_ref` table
- `OccurrenceImporter` — Hardcoded to import to `occurrences` table

### Problems with the Legacy System

1. **Inflexibility**: Could only import pre-defined entity types to fixed tables
2. **Code Duplication**: Each importer repeated CSV validation, table creation, and geometry handling logic
3. **Configuration Coupling**: Transform/Export plugins directly accessed `taxon_ref`, `plot_ref`, `shape_ref` — couldn't work with other entity types
4. **Nested Set Overhead**: Taxonomy hierarchies required expensive lft/rght recalculation on every import
5. **Limited Extensibility**: Adding new entity types (habitats, sites, custom references) required new specialized importers

The system couldn't support common use cases like:
- Importing a third-party taxonomy as a reference
- Creating hierarchies from derived data (e.g., extracting taxonomy from occurrence records)
- Defining custom reference entities for project-specific needs

## Decision

We implemented a **Generic Import System** driven by declarative YAML configuration (`import.yml`), eliminating all specialized importers in favor of a unified engine.

### Core Architecture

1. **Entity Registry** (`core/imports/registry.py`)
   - Central metadata service describing all entities in the system
   - Stores entity type, physical table name, schema, links, and aliases
   - Replaces hardcoded assumptions about `taxon_ref`, `plot_ref`, `shape_ref`
   - Provides introspection API for Transform/Export/GUI services

2. **Configuration Models** (`core/imports/config_models.py`)
   - Pydantic models define entity types: `Dataset`, `Reference` (hierarchical/spatial)
   - Validates connector types, schema fields, hierarchy strategies, enrichment configs
   - Supports derived references extracted from datasets

3. **Generic Import Engine** (`core/imports/engine.py`)
   - Orchestrates import execution plan: Datasets → Derived References → Direct References
   - Uses DuckDB connectors (`read_csv_auto`, spatial extension) for efficient ingestion
   - Validates data against schema, builds hierarchies, applies enrichments

4. **Hierarchy Builder** (`core/imports/hierarchy_builder.py`)
   - Supports multiple strategies: adjacency list, nested set (legacy compatibility)
   - For derived references: extracts hierarchy from source data columns
   - Uses DuckDB recursive CTEs for adjacency list construction
   - Hash-based ID generation ensures stable IDs across reimports

### Three Entity Types

**Datasets** — Source data tables (e.g., occurrences, observations)
```yaml
entities:
  datasets:
    occurrences:
      connector:
        type: file
        format: csv
        path: imports/occurrences.csv
```

**Derived References** — Hierarchies extracted from datasets
```yaml
entities:
  references:
    taxonomy:
      kind: hierarchical
      connector:
        type: derived
        source: occurrences
        extraction:
          levels:
            - name: family
              column: family
            - name: genus
              column: genus
```

**Direct References** — Hierarchies loaded from files
```yaml
entities:
  references:
    plots:
      kind: hierarchical
      connector:
        type: file
        format: csv
        path: imports/plots.csv
```

### Plugin Genericization (Phase 8)

All 19 plugins were refactored to:
- Accept `EntityRegistry` instead of `Config`/`Database` objects
- Resolve table names dynamically via registry instead of hardcoding
- Support arbitrary entity types (not just `taxon_ref`, `plot_ref`, `shape_ref`)

**Example transformation**:
```python
# Before (coupled to taxon_ref)
def load(self, config: Config):
    query = "SELECT * FROM taxon_ref WHERE..."

# After (generic via registry)
def load(self, registry: EntityRegistry, entity_name: str):
    table = registry.get_table_name(entity_name)
    query = f"SELECT * FROM {table} WHERE..."
```

Refactored plugins include:
- **Loaders**: `direct_reference`, `join_table`, `nested_set`, `adjacency_list`, `stats_loader`
- **Transformers**: `database_aggregator`, `field_aggregator`, `top_ranking`, `direct_attribute`, `geospatial_extractor`, `multi_column_extractor`, `niamoto_to_dwc_occurrence`, `shape_processor`
- **Exporters**: `dwc_archive_exporter`, `html_page_exporter`, `index_generator`, `json_api_exporter`

## Implementation Phases (Completed)

### Phase 0-3: Foundation
- ✅ Pydantic configuration models
- ✅ DuckDB integration (see ADR 0001)
- ✅ Entity Registry implementation
- ✅ Generic import engine with execution plan

### Phase 4-5: Hierarchy Systems
- ✅ Adjacency list builder with hash-based IDs
- ✅ Derived reference extraction from datasets (see ADR 0003)
- ✅ Multi-source spatial references

### Phase 6-7: Service Integration
- ✅ CLI migration to use EntityRegistry
- ✅ Transform/Export services consume registry
- ✅ GUI API endpoints adapted for dynamic entities

### Phase 8: Plugin Genericization
- ✅ All 19 plugins refactored to accept EntityRegistry
- ✅ Dynamic table resolution removes hardcoded assumptions
- ✅ Plugins now work with any entity type

## Consequences

### Positive

1. **Flexibility**: Can define any entity type in `import.yml` without code changes
2. **Maintainability**: Single import engine eliminates code duplication
3. **Performance**: DuckDB direct ingestion and recursive CTEs are faster than SQLite+pandas
4. **Extensibility**: New entity types, connectors, or hierarchy strategies are configuration changes
5. **Decoupling**: Plugins resolve tables via registry — no hardcoded dependencies
6. **Stability**: Hash-based IDs ensure referential integrity across reimports

### Challenges & Migration Requirements

1. **Breaking Change**: Existing projects must migrate from SQLite schema to DuckDB
2. **Configuration Migration**: Old CLI workflows must be converted to `import.yml` format
3. **Plugin Updates**: Any custom plugins need EntityRegistry integration
4. **Documentation**: Extensive examples needed for new configuration syntax
5. **GUI Adaptation**: Interface must support dynamic entity definition (in progress)

### Technical Debt Retired

- ❌ Removed: `core/components/imports/` (TaxonomyImporter, PlotImporter, ShapeImporter, OccurrenceImporter)
- ❌ Removed: `core/models/models.py` (rigid SQLAlchemy models for taxon_ref, plot_ref, shape_ref)
- ❌ Removed: `core/repositories/niamoto_repository.py` (tightly coupled data access)
- ✅ Replaced: Hardcoded table names in 19 plugins with dynamic registry resolution

## Related ADRs

- **ADR 0001** — DuckDB Adoption: Enables efficient generic imports with `read_csv_auto`, recursive CTEs
- **ADR 0002** — Retirement of Specialized Importers: Documents transition strategy from legacy system
- **ADR 0003** — Derived References with DuckDB CTEs: Explains hierarchy extraction architecture

## Validation

The system has been validated through:
- ✅ 89 unit tests covering config models, registry, hierarchy builder, engine
- ✅ Integration tests for full import workflows (datasets → derived → direct)
- ✅ Plugin tests demonstrating generic entity support
- ✅ CLI tests for import/transform/export workflows
- ✅ Real-world usage with New Caledonia biodiversity data (test-instance)

## Next Steps

1. **GUI Adaptation**: Update import wizard to support dynamic entity definition via `import.yml`
2. **Migration Guide**: Document transition path for existing Niamoto projects
3. **Performance Benchmarking**: Compare DuckDB generic engine vs. legacy SQLite importers
4. **Advanced Features**: Implement validation rules, conditional enrichments, incremental imports

## Status

**COMPLETE** — All 8 implementation phases finished as of 2025-10-13. The generic import system is operational and all legacy importers have been removed. GUI adaptation is the remaining work item.
