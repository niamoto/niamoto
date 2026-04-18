# Architecture

This section describes the current Niamoto architecture.

The main entry point is the runtime and system notes below. ADRs remain in the
folder as background material for a few older decisions, but they are no longer
the primary way to understand the codebase.

## Start here

- [system-overview.md](system-overview.md): current platform layers and runtime flow
- [plugin-system.md](plugin-system.md): plugin types, registry, and loading cascade
- [gui-overview.md](gui-overview.md): GUI backend and frontend split
- [gui-runtime.md](gui-runtime.md): development, packaged, and desktop runtime modes
- [gui-preview-system.md](gui-preview-system.md): widget preview rendering path

## Current architecture

- [system-overview.md](system-overview.md)
- [plugin-system.md](plugin-system.md)
- [gui-overview.md](gui-overview.md)
- [gui-runtime.md](gui-runtime.md)
- [gui-preview-system.md](gui-preview-system.md)

## Historical decision notes

The `adr/` directory is still kept for a small set of decisions that explain
why some parts of the runtime look the way they do, especially the move to
DuckDB and the generic import transition. They are optional background reading,
not the recommended entry point for new readers.

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
- `docs/plans/`: dated implementation plans and research notes

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
