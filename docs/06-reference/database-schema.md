# Database Schema Reference

DuckDB is the default project database at `db/niamoto.duckdb`. SQLite still
works for `.db` and `.sqlite` paths, but new desktop projects default to
DuckDB.

The schema has two layers:

- stable metadata tables maintained by Niamoto
- project-specific tables created from `import.yml` and `transform.yml`

## Stable metadata tables

### `niamoto_metadata_entities`

This registry indexes the entities created by the import pipeline.

Columns:

- `name`: logical entity name used by the config
- `kind`: `reference` or `dataset`
- `table_name`: actual backing table name in the database
- `config`: JSON payload with the persisted entity config
- `created_at`
- `updated_at`

The source of truth is `src/niamoto/core/imports/registry.py`.

### `niamoto_metadata_transform_sources`

This registry stores metadata about transform-only file sources discovered from
configuration.

Columns:

- `name`
- `path`
- `grouping`
- `config`: JSON payload containing persisted schema metadata
- `created_at`
- `updated_at`

The source of truth is `src/niamoto/core/imports/source_registry.py`.

## Imported project tables

Imported tables come from `import.yml`, so their exact shape depends on the
project.

Niamoto usually ends up with two broad families:

- reference tables, often named with `_ref` suffixes such as `taxon_ref`,
  `plot_ref`, or `shape_ref`
- dataset tables created from imported source files

The entity registry links each configured entity to its physical table name,
which is how the GUI and CLI discover available references and datasets.

## Transform result tables

For each `group_by` declared in `transform.yml`, the transformer service creates
or recreates a table named after that group.

Current pattern:

- primary key column: `${group_by}_id BIGINT PRIMARY KEY`
- one `JSON` column per configured widget or transform output

This is implemented in `src/niamoto/core/services/transformer.py`.

Transform tables follow the active configuration: the set of JSON columns
depends on the widget keys present in `transform.yml`.

## Configuration files that shape the schema

- `config/import.yml`: source tables, identifiers, and reference imports
- `config/transform.yml`: derived groups and computed outputs
- `config/export.yml`: exported structures and publication targets
- `config/deploy.yml`: deployment defaults only; it does not shape the schema

## How to inspect a project database

- `niamoto stats`: high-level inspection from the CLI
- the desktop data explorer: table-oriented inspection from the GUI
- [api/modules.rst](api/modules.rst): source-level API reference

## Related docs

- [configuration-guide.md](configuration-guide.md): file-by-file YAML boundaries
- [Import workflow](../02-user-guide/import.md)
- [Transform workflow](../02-user-guide/transform.md)
