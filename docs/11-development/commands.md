# Development Commands Reference

Complete reference for all development commands. For quick reference, see [CLAUDE.md](../CLAUDE.md).

## Testing & Quality

```bash
uv run --group dev pytest                              # Run all tests
uv run --group dev pytest tests/path/test_file.py -v   # Run specific test
uv run --group dev mypy src/niamoto                    # Type checking
uv run --group dev ruff check src/ --fix               # Lint with auto-fix
uv run --group dev ruff format src/                    # Format code
```

## Database Commands

Database location: `test-instance/niamoto-nc/db/niamoto.duckdb`

```bash
uv run python scripts/data/query_db.py "SELECT * FROM taxon LIMIT 5"   # Execute SQL
uv run python scripts/data/query_db.py --list-tables                   # List tables
uv run python scripts/data/query_db.py --describe taxon                # Describe table
uv run python scripts/data/query_db.py --interactive                   # SQL REPL
```

## GUI Development

### Development Mode (Recommended)

```bash
./scripts/dev/dev_web.sh test-instance/niamoto-nc
```

- FastAPI backend: http://127.0.0.1:8080 (API docs: /api/docs)
- Vite frontend: http://127.0.0.1:5173 (use this URL)
- Full hot reload for React and Python
- Ctrl+C to stop both servers

### Manual Dual Server Setup

```bash
# Terminal 1: Backend
uv run python scripts/dev/dev_api.py --instance test-instance/niamoto-nc

# Terminal 2: Frontend
cd src/niamoto/gui/ui && pnpm run dev
```

### Production Mode

```bash
cd src/niamoto/gui/ui && pnpm install      # Install dependencies
cd src/niamoto/gui/ui && pnpm run build    # Build for production
uv run niamoto gui --port 8080 --no-browser  # Launch (serves from dist/)
```

### Instance Context

The GUI determines which instance to use in this order:
1. CLI argument: `--instance /path/to/instance`
2. Environment variable: `NIAMOTO_HOME=/path/to/instance`
3. Current directory (with warning)

## Build & Publish

```bash
uv run python scripts/build/generate_requirements.py   # Generate requirements.txt
uv run python scripts/build/build_tailwind_standalone.py  # Build Tailwind CSS
# PyPI publish is automated via GitHub Actions (publish-pypi.yml)
cd docs && uv run --group dev --extra docs sphinx-apidoc -o . ../src/niamoto && uv run --group dev --extra docs make html  # Build docs
```

## Git Workflow

```bash
./scripts/dev/smart_commit.sh "commit message"  # Commit with pre-commit hooks
```
