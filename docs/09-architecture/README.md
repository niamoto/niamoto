# Architecture

> Status: Active
> Audience: Maintainers, contributors, reviewers evaluating Niamoto.
> Purpose: System design, decision records, and long-form rationale.

## Start here

- [system-overview.md](system-overview.md) — high-level layering of
  the platform.
- [pipeline-unified.md](pipeline-unified.md) — how import, transform,
  and export connect through DuckDB.
- [plugin-system.md](plugin-system.md) — the plugin registry and its
  types.
- [adr/](adr/) — architecture decision records.

## If you want to…

- **Understand how the desktop and CLI share code** — see
  [gui-overview.md](gui-overview.md),
  [gui-runtime.md](gui-runtime.md).
- **Understand the preview system** — see
  [gui-preview-system.md](gui-preview-system.md).
- **Read the decision history** — see [adr/](adr/):
  - [0001-adopt-duckdb.md](adr/0001-adopt-duckdb.md)
  - [0002-retire-legacy-importers.md](adr/0002-retire-legacy-importers.md)
  - [0003-derived-references-with-duckdb.md](adr/0003-derived-references-with-duckdb.md)
  - [0004-generic-import-system.md](adr/0004-generic-import-system.md)
- **See the target architecture for 2026** — see
  [target-architecture-2026.md](target-architecture-2026.md),
  [target-architecture-2026-execution-plan.md](target-architecture-2026-execution-plan.md).

## Structure

### Active reference
- [system-overview.md](system-overview.md)
- [pipeline-unified.md](pipeline-unified.md)
- [plugin-system.md](plugin-system.md)
- [gui-overview.md](gui-overview.md)
- [gui-runtime.md](gui-runtime.md)
- [gui-preview-system.md](gui-preview-system.md)

### Roadmaps and evolving targets
- [target-architecture-2026.md](target-architecture-2026.md)
- [target-architecture-2026-comex-cto.md](target-architecture-2026-comex-cto.md)
- [target-architecture-2026-execution-plan.md](target-architecture-2026-execution-plan.md)
- [corrections-roadmap.md](corrections-roadmap.md)
- [plugin-improvement.md](plugin-improvement.md)
- [technical-analysis.md](technical-analysis.md)

### Decision records
- [adr/](adr/)

## Core principles

1. **Plugin-first.** Loaders, transformers, exporters, and widgets are
   all plugins. The core stays thin.
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
│  Loaders · transformers · …    │
├────────────────────────────────┤
│  Data                          │
│  DuckDB · EntityRegistry       │
└────────────────────────────────┘
```

## Related

- [../04-plugin-development/README.md](../04-plugin-development/README.md) —
  building plugins that use these interfaces.
- [../10-roadmaps/README.md](../10-roadmaps/README.md) — long-running
  plans that shape architecture.
