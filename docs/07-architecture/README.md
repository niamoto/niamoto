# Architecture

This section groups the current architecture notes and the ADRs that explain
key structural decisions.

## Start here

- [system-overview.md](system-overview.md): current platform layers and runtime flow
- [plugin-system.md](plugin-system.md): plugin types, registry, and loading cascade
- [gui-overview.md](gui-overview.md): GUI backend and frontend split
- [gui-preview-system.md](gui-preview-system.md): widget preview rendering
- [adr/0001-adopt-duckdb.md](adr/0001-adopt-duckdb.md): first ADR in the active series

## Current architecture

- [system-overview.md](system-overview.md)
- [plugin-system.md](plugin-system.md)
- [gui-overview.md](gui-overview.md)
- [gui-runtime.md](gui-runtime.md)
- [gui-preview-system.md](gui-preview-system.md)

## ADRs

- [adr/0001-adopt-duckdb.md](adr/0001-adopt-duckdb.md)
- [adr/0002-retire-legacy-importers.md](adr/0002-retire-legacy-importers.md)
- [adr/0003-derived-references-with-duckdb.md](adr/0003-derived-references-with-duckdb.md)
- [adr/0004-generic-import-system.md](adr/0004-generic-import-system.md)

## Core principles

1. **Plugin-first.** Loaders, transformers, exporters, and widgets are
   all plugins. Deployers extend the same system for publication targets.
2. **Configuration-driven.** YAML controls the pipeline.
3. **DuckDB-centric.** Analytics, recursive CTEs, spatial extension.
4. **Type-safe.** Pydantic models on every plugin boundary.
5. **Deterministic IDs.** Hash-based IDs make re-imports stable
   (configurable via `id_strategy` in `import.yml`).

## Three-layer model

```text
┌────────────────────────────────┐
│  Presentation                  │
│  Desktop (Tauri) · CLI · API   │
├────────────────────────────────┤
│  Services & plugins            │
│  Loaders · transformers · widgets · exporters · deployers │
├────────────────────────────────┤
│  Data                          │
│  DuckDB · EntityRegistry       │
└────────────────────────────────┘
```

## Related

- [../04-plugin-development/README.md](../04-plugin-development/README.md): plugin authoring guides
- [../08-roadmaps/README.md](../08-roadmaps/README.md): roadmaps, target architecture, and longer design proposals

```{toctree}
:hidden:

system-overview
plugin-system
gui-overview
gui-runtime
gui-preview-system
adr/0001-adopt-duckdb
adr/0002-retire-legacy-importers
adr/0003-derived-references-with-duckdb
adr/0004-generic-import-system
```
