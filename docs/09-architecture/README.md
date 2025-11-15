# Architecture

System architecture and design decisions for Niamoto.

## 📚 Documents in this Section

- **[System Overview](system-overview.md)** - High-level architecture (coming soon)
- **[Plugin System](plugin-system.md)** - Plugin architecture analysis
- **[Pipeline Unified](pipeline-unified.md)** - Unified pipeline interface
- **[Corrections Roadmap](corrections-roadmap.md)** - System improvements plan

## 🏗️ Core Architecture

### Three-Layer Design

```
┌─────────────────────────────┐
│      Presentation Layer      │
│        (GUI / CLI)          │
├─────────────────────────────┤
│       Service Layer         │
│  (Components & Plugins)     │
├─────────────────────────────┤
│        Data Layer           │
│   (DuckDB + Registry)      │
└─────────────────────────────┘
```

### Key Principles

1. **Plugin-Based** - Everything is a plugin
2. **Configuration-Driven** - YAML controls behavior
3. **Database-Centric** - DuckDB as the main analytical source
4. **Type-Safe** - Pydantic models everywhere
5. **Modular** - Clear separation of concerns

## 🔌 Plugin Architecture

- Global registry pattern
- Four plugin types (Loader, Transformer, Exporter, Widget)
- Decorator-based registration
- Configuration validation

## 🔄 Data Pipeline

```
Import → Database → Transform → Database → Export
```

- Each phase reads/writes to database
- Transformations are chainable
- Widgets are data consumers

## 🎯 Design Decisions

- **DuckDB for Analytics** — Fast ingestion (`read_csv_auto`), recursive CTEs, spatial extension
- **Static Site Generation** — No runtime dependencies
- **Plugin Registry** — Extensibility without modifying the core
- **YAML Configuration** — Human-readable and version-controllable
- **Entity Registry** — Transform/Export/GUI services now resolve tables via a persistent registry
- **Hash-Based ID Generation** — Hierarchical IDs use MD5 hashes (e.g., `2071543557`) rather than sequences to ensure stability during reimports. Configurable via `id_strategy` in `import.yml`.

## 📄 Architectural Decision Records (ADR)

- [ADR 0001 — DuckDB Adoption](adr/0001-adopt-duckdb.md)
- [ADR 0002 — Retirement of Specialized Importers](adr/0002-retire-legacy-importers.md)

## 🔗 Related Documentation

- [Plugin Development](../04-plugin-development/README.md) - Building plugins
- [Data Pipeline](../02-data-pipeline/README.md) - Pipeline implementation
- [Roadmaps](../10-roadmaps/README.md) - Future architecture plans

---
*For implementation details, see code and API documentation*
