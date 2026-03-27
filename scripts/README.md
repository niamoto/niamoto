# Scripts

Development and maintenance scripts for Niamoto.

## Structure

```
scripts/
├── build/      # Build, release, asset generation
├── dev/        # Daily development workflow
├── data/       # Data manipulation and querying
└── _archive/   # Archived scripts (kept for reference)
```

## build/

Build, release, and asset generation scripts.

| Script | Description |
|--------|-------------|
| `build_gui.sh` | Build React GUI with pnpm |
| `generate_changelog.py` | Generate CHANGELOG.md from git tags |
| `generate_requirements.py` | Generate requirements.txt from pyproject.toml |
| `build_tailwind_standalone.py` | Build Tailwind CSS standalone binary |
| `plotly-bundles/` | Vendored Plotly bundle builder |

## dev/

Daily development workflow scripts.

| Script | Description |
|--------|-------------|
| `dev_web.sh` | Launch full dev environment (FastAPI + Vite HMR) |
| `dev_api.py` | Launch FastAPI backend only |
| `dev_desktop.sh` | Launch Tauri desktop app in dev mode |
| `smart_commit.sh` | Automated commit with pre-commit hooks |
| `test_preview_suggestions.py` | Batch test all preview suggestions |
| `test_shapes_previews.py` | Test shapes widget previews |
| `bench_preview.py` | Benchmark preview engine (P50/P95/P99 latency) |
| `bench_pipeline.py` | Benchmark `transform` and `export` on a staged instance |
| `evaluate_pipeline.py` | Diagnostic tool for data profiling + suggestions |

**Common usage:**
```bash
# Launch web dev environment
./scripts/dev/dev_web.sh test-instance/niamoto-nc

# Launch API only
uv run python scripts/dev/dev_api.py test-instance/niamoto-nc

# Benchmark preview routes (requires running server)
uv run python scripts/dev/bench_preview.py --base-url http://localhost:8000

# Benchmark transform/export on niamoto-subset
uv run python scripts/dev/bench_pipeline.py --instance test-instance/niamoto-subset

# Evaluate suggestion pipeline on a CSV
uv run python scripts/dev/evaluate_pipeline.py path/to/data.csv
```

## data/

Data manipulation and querying utilities.

| Script | Description |
|--------|-------------|
| `query_db.py` | SQL queries on DuckDB instances |
| `create_test_subset.py` | Create lightweight test instance from full dataset |
| `fetch_gbif_targeted.py` | Fetch targeted GBIF occurrence batches |

**Common usage:**
```bash
# SQL query
uv run python scripts/data/query_db.py "SELECT * FROM taxon LIMIT 5"

# Interactive mode
uv run python scripts/data/query_db.py --interactive
```
