# ADR 0001 — DuckDB Adoption as Primary Analytics Engine

*Status: Adopted (2025-10-08)*

## Context

- The current pipeline relies on SQLite for imports, with extensive Python logic (pandas `to_sql`, index recalculation, manual validations) and significant limitations (limited DDL, degraded performance on large files, lack of analytical features).
- The "Generic Import" refactoring aims for a more flexible engine to create dynamic tables, read massive files, manipulate geometries, and execute recursive CTEs.
- DuckDB natively provides `read_csv_auto`, `read_parquet`, a spatial extension, and `CREATE OR REPLACE TABLE` statements that simplify the pipeline.

## Decision

We are migrating Niamoto's analytical infrastructure to DuckDB:

- New import tables will be created in a DuckDB file (`.duckdb`) defined by the configuration (`config.yml`).
- The `niamoto.common.database` module will be extended/adapted to encapsulate DuckDB (SQL execution, introspection, transactions).
- Scripts and tests will use DuckDB by default; SQLite will remain only for temporary compatibility (targeted tests) but will no longer be the primary engine.
- The CLI and GUI will automatically load the spatial extension when necessary (plots/shapes).

## Consequences

### Positive

- "Direct" import with `read_csv_auto` / `CREATE TABLE AS SELECT`, reducing code and execution time.
- Native support for recursive CTEs ⇒ simple adjacency list hierarchies.
- Handling of modern formats (Parquet, GeoParquet) without additional conversions.
- Simplified statistics/profiling generation via SQL.

### Negative / Points of Attention

- DuckDB learning curve for the team (DDL syntax, limitations). Snippets will be added to documentation.
- Spatial extension must be explicitly loaded (initialization scripts ➜ check presence and document).
- Migration of existing environments: provide an `ATTACH …` script to copy old SQLite tables if necessary.
- Adjust CI (DuckDB installation, extension) and packaging (`pyproject.toml`).

### Actions

1. Adapt `Database` + unit tests for DuckDB.
2. Document configuration (`docs/09-architecture/README.md`, installation guides).
3. Update scripts (bootstrap, tests) to create/initialize the DuckDB file.
4. Prepare a migration guide (`docs/10-roadmaps/generic-import-ultrathink.md` ➜ migration appendix) with `ATTACH` examples.

## Follow-up 2025-10-08
- ✅ DuckDB helpers (SQL execution, introspection) integrated via registry and refactored loaders (`core/common/database.py`, `core/imports/registry.py`).
- ✅ Spatial extension loaded via export/transform services after geospatial extractor migration.
- 🔄 CLI stats and remaining loaders still aligned with `sqlite_master`: migration to DuckDB adapter in progress, `tests/cli/test_stats.py` tests to be finalized.
