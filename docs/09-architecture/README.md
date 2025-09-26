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
│        Data Layer          │
│    (SQLite + SQLAlchemy)   │
└─────────────────────────────┘
```

### Key Principles

1. **Plugin-Based** - Everything is a plugin
2. **Configuration-Driven** - YAML controls behavior
3. **Database-Centric** - SQLite as single source of truth
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

- **SQLite over PostgreSQL** - Simplicity and portability
- **Static Site Generation** - No runtime dependencies
- **Plugin Registry** - Extensibility without modification
- **YAML Configuration** - Human-readable, versionable

## 🔗 Related Documentation

- [Plugin Development](../04-plugin-development/) - Building plugins
- [Data Pipeline](../02-data-pipeline/) - Pipeline implementation
- [Roadmaps](../10-roadmaps/) - Future architecture plans

---
*For implementation details, see code and API documentation*
