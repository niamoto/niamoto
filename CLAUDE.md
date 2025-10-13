e# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Niamoto Development Guidelines

## Commands
- **Test**: `pytest` (all tests), `pytest tests/path/to/test_file.py -v` (specific file)
- **Type check**: `mypy src/niamoto`
- **Lint/Format**: `ruff check src/ --fix` and `ruff format src/`
- **Generate requirements**: `python scripts/generate_requirements.py`
- **Build docs**: `cd docs && sphinx-apidoc -o . ../src/niamoto && make html`
- **Publish to PyPI**: See scripts/publish.sh
- **Build Tailwind CSS**: `python scripts/build_tailwind_standalone.py` (uses standalone binary, no npm required)
- **Always use uv for tests or running python scripts**
- **Run tests with uv**: `uv run pytest`
- **Smart commit with pre-commit**: `./scripts/smart_commit.sh "commit message"` (automates commit process with pre-commit)

### Database Commands
- **Query database**: `uv run python scripts/query_db.py "SELECT * FROM taxon LIMIT 5"` (execute SQL queries)
- **List tables**: `uv run python scripts/query_db.py --list-tables`
- **Describe table**: `uv run python scripts/query_db.py --describe taxon`
- **Interactive mode**: `uv run python scripts/query_db.py --interactive` (SQL REPL)
- **Database location**: Test instance database is at `test-instance/niamoto-nc/db/niamoto.duckdb`

### GUI Commands
- **Install GUI dependencies**: `cd src/niamoto/gui/ui && npm install`
- **Run GUI development server**: `cd src/niamoto/gui/ui && npm run dev`
- **Build GUI for production**: `cd src/niamoto/gui/ui && npm run build`
- **Launch Niamoto GUI**: `niamoto gui` (options: `--port 8080`, `--host 127.0.0.1`, `--no-browser`, `--reload`)
- **Access GUI**: Default at `http://127.0.0.1:8080`, API docs at `/api/docs`

## Development Notes
- A niamoto instance exists in the test-instance/niamoto-nc directory, where you can find source configuration files and execute niamoto commands
- **Database**: Niamoto uses **DuckDB** (not SQLite) - database file is `test-instance/niamoto-nc/db/niamoto.duckdb`
- Use `scripts/query_db.py` to inspect and query the database during development

## High-Level Architecture
Niamoto is an ecological data platform built around a data pipeline with three phases:
1. **Import**: Load data from CSV, GIS formats (import.yml)
2. **Transform**: Calculate statistics via plugins (transform.yml)
3. **Export**: Generate static sites with visualizations (export.yml)

### Core Architecture Patterns
- **Plugin System**: All transformations are plugins registered in a global registry
- **Configuration-Driven**: YAML files define the entire pipeline - no code changes needed for new analyses
- **Type Safety**: Pydantic models validate all plugin configurations
- **Database-Centric**: DuckDB (analytics database) with SQLAlchemy ORM; GeoAlchemy2 handles spatial data

### Key Architectural Components
- **CLI (cli/)**: Click-based commands orchestrate the pipeline
- **Components (core/components/)**: Handle imports/exports with specialized classes
- **Plugins (core/plugins/)**: 4 types - Loader, Transformer, Exporter, Widget
- **Services (core/services/)**: Coordinate components and manage data flow
- **Models (core/models/)**: SQLAlchemy models define database schema
- **GUI (gui/)**: Modern web interface for visual configuration
  - **API (gui/api/)**: FastAPI backend serving REST endpoints and static files
  - **UI (gui/ui/)**: React + TypeScript frontend with shadcn/ui components

### GUI Architecture
The GUI provides a visual configuration interface for the Niamoto pipeline:
- **Frontend Stack**: React 19, TypeScript, Vite, Tailwind CSS v4, shadcn/ui
- **Backend**: FastAPI serving both API endpoints and static React build
- **Features**:
  - Multi-step import wizard with real-time validation
  - Drag-and-drop file upload (CSV, Excel, JSON, GeoJSON, Shapefile)
  - Column mapping and data transformation configuration
  - Internationalization support (French/English)
  - Taxonomy hierarchy editor with visual drag-and-drop
- **API Endpoints**:
  - `/api/config`: Configuration management
  - `/api/files`: File operations and directory listing
  - `/api/imports`: Import process management and field detection
- **Location**: `src/niamoto/gui/` (api and ui subdirectories)

### Plugin Development Pattern
```python
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register

@register("my_plugin", PluginType.TRANSFORMER)
class MyPlugin(TransformerPlugin):
    def transform(self, data, config):
        # Transform logic here
        return result
```

## Code Style
- **Imports**: Group in order: stdlib, third-party, local
- **Formatting**: Follows ruff format standards
- **Types**: Always use type hints (disallow_untyped_defs=True in mypy.ini)
- **Naming**: snake_case for variables/functions, PascalCase for classes
- **Error handling**: Use appropriate exception types, favor explicit error handling
- **Documentation**: Use docstrings for all public functions and classes
- **Testing**: Write comprehensive tests for new features and bug fixes

## Testing Patterns
- Use BaseTest class for database tests (handles setup/teardown)
- Mock external dependencies with pytest-mock
- Test plugins with both valid and invalid configurations
- Always test error conditions and edge cases

## Database Patterns
- Models use SQLAlchemy declarative base
- Use context managers for database sessions
- **DuckDB Read-Only Mode**: Use `Database(db_path, read_only=True)` to inspect the database while other processes (like DBeaver) have a write lock
  ```python
  from niamoto.common.database import Database
  db = Database('db/niamoto.duckdb', read_only=True)
  # Can now query even if another process has the file locked
  ```

## Common Pitfalls to Avoid
- Don't access database outside of service layer
- Always validate plugin configurations with Pydantic
- Don't hardcode paths - use config system
- Remember to register new plugins with @register decorator
- When working on the graphical interface, you must build the GUI after each completed task, then run "niamoto gui" in @/Users/julienbarbe/Dev/Niamoto/Niamoto/test-instance/niamoto-gui

## Golden Rule
**If you can explain it to a field ecologist or botanist in 2 minutes, it's the right solution.**
