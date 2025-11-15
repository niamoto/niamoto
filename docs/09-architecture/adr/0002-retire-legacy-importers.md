# ADR 0002 — Retirement of Specialized Importers in Favor of Generic Import Registry

*Status: Adopted (2025-10-08)*

## Context

- Current importers (`TaxonomyImporter`, `PlotImporter`, `ShapeImporter`, `OccurrenceImporter`) directly manipulate SQLite, recalculate nested sets, and enforce three tables (`taxon_ref`, `plot_ref`, `shape_ref`).
- Transform/Export have been generalized (plugins + config) but remain coupled to these tables.
- The "Generic Import System" roadmap defines a declarative configuration (`entities.references/datasets`) and an Entity Registry to centralize schemas and metadata.
- We are still in alpha ⇒ no backward compatibility requirement.

## Decision

We are progressively retiring specialized importers in favor of a generic engine driven by the new configuration:

- Creation of a persistent **Entity Registry** describing each entity (type, physical table, links, aliases).
- A new import engine will orchestrate connectors, validations, hierarchies, and enrichments relying on DuckDB.
- Transform/Export/GUI will consume the Registry instead of querying fixed tables.
- The `core/components/imports/*` modules will be removed once functional equivalence is achieved.

## Consequences

### Positive

- Ability to describe/import any entity (third-party taxonomy, sites, habitats, etc.).
- Reduction of duplicated code (CSV/Geo validation, table creation, nested sets).
- Complete pipeline alignment (import → transform → export) on declarative configuration.
- Cleanup of plugin dependencies: they will no longer need to load `Config` or `Database` directly.

### Negative / Points of Attention

- Migration of existing plugins (`hierarchical_nav_widget`, `geospatial_extractor`, `top_ranking`, HTML exporters) to handle adjacency list or compatibility views.
- Update tests (unit, integration, CLI) that assume `taxon_ref` existence.
- Significant documentation work (new `import.yml`, examples, GUI guides).
- Risk of regression during switchover; plan fixtures and end-to-end tests.

### Actions

1. Finalize Pydantic models (`config_models`) ✅ (first draft in place).
2. Design Entity Registry + metadata storage (`niamoto_metadata.*` tables).
3. Implement generic import engine (DuckDB connectors, validations, execution plan).
4. Adapt Transform/Export to use Registry (remove `Config()` coupling in plugins).
5. Retire legacy importers and remove rigid SQLAlchemy models.
6. Update documentation (`docs/10-roadmaps/generic-import-ultrathink.md`, GUI README) and provide migration guide.

## Follow-up 2025-10-08
- ✅ Operational DuckDB registry: `registry.py`/`legacy_registry.py` expose entities to Transform/Export services and GUI.
- ✅ `direct_reference` loader and geospatial extractor migrated to registry; associated tests updated.
- 🔄 CLI `stats` command and loaders still depending on `sqlite_master` to be migrated before historical importer removal.
- 📌 Next step: remove `core/components/imports/*` and SQLAlchemy models once CLI is migrated and CLI tests are reinforced.
