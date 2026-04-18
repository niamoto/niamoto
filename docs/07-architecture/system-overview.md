# System Overview

Niamoto moves data through three pipeline stages:

1. import raw sources into project tables
2. transform those tables into grouped outputs
3. export or publish the result

The same core services power the CLI, the desktop app, and the GUI API.

## Product surfaces

- CLI commands in `src/niamoto/cli/commands/`
- desktop and web backend in `src/niamoto/gui/api/`
- React frontend in `src/niamoto/gui/ui/src/`

The CLI runs pipeline stages directly. The desktop app and the browser UI call
the same backend services through FastAPI routes.

## Core layers

### Configuration

Niamoto keeps each pipeline stage in its own file:

- `config.yml`: runtime settings and shared paths
- `import.yml`: sources, identifiers, and import rules
- `transform.yml`: grouped statistics and derived outputs
- `export.yml`: website, API, and file exports
- `deploy.yml`: deployment targets and platform settings

### Services and plugins

The service layer coordinates the pipeline. Plugins supply the domain-specific
work:

- loaders read or enrich data
- transformers compute grouped outputs
- widgets render HTML fragments for exports and previews
- exporters write sites or machine-readable files
- deployers publish build artifacts to remote platforms

The main code lives under `src/niamoto/core/services/` and
`src/niamoto/core/plugins/`.

### Persistence

DuckDB is the default project database. Niamoto stores stable metadata in
registry tables and creates project-shaped tables from `import.yml` and
`transform.yml`.

See [../06-reference/database-schema.md](../06-reference/database-schema.md) for
the persisted structure.

## Runtime flow

In the common case, the flow looks like this:

```text
sources -> import services -> DuckDB tables -> transform services -> grouped outputs -> export or deploy
```

The GUI adds API routes, preview rendering, and job orchestration on top of the
same pipeline.

## Where to go next

- [plugin-system.md](plugin-system.md): plugin registry, loading, and override rules
- [gui-overview.md](gui-overview.md): frontend and backend split in the GUI
- [gui-runtime.md](gui-runtime.md): development, packaged, and desktop runtime modes
- [gui-preview-system.md](gui-preview-system.md): preview rendering path
- [../06-reference/configuration-guide.md](../06-reference/configuration-guide.md): YAML boundaries
- [../06-reference/core-api.md](../06-reference/core-api.md): source-level entry points
