# Niamoto Agent Instructions

## Project Map
- Ecological data platform: Import -> Transform -> Export, available as Python CLI, FastAPI GUI, React/Vite UI, and Tauri desktop app.
- Core Python code: `src/niamoto`; tests: `tests`; scripts: `scripts`; docs: `docs`.
- GUI backend: `src/niamoto/gui/api`; GUI frontend: `src/niamoto/gui/ui`; desktop shell: `src-tauri`.
- ML detection and training support: `ml`; active local fixtures: `test-instance/niamoto-nc` and `test-instance/niamoto-subset`.

## Commands
| Task | Command |
|------|---------|
| Install | `uv sync --group dev` |
| CLI help | `uv run niamoto --help` |
| Pytest all | `uv run --group dev pytest` |
| Pytest targeted | `uv run --group dev pytest path/to/test.py -k name` |
| Ruff check | `uv run --group dev ruff check src tests` |
| Ruff format | `uv run --group dev ruff format src tests` |
| MyPy | `uv run --group dev mypy src/niamoto` |
| Tox py312 | `uv run tox -e py312` |

## GUI Commands
| Task | Command |
|------|---------|
| Web dev stack | `./scripts/dev/dev_web.sh test-instance/niamoto-nc` |
| API only | `uv run python scripts/dev/dev_api.py --instance test-instance/niamoto-nc` |
| Desktop dev | `./scripts/dev/dev_desktop.sh test-instance/niamoto-nc` |
| UI install | `cd src/niamoto/gui/ui && pnpm install` |
| UI dev | `cd src/niamoto/gui/ui && pnpm dev` |
| UI build | `cd src/niamoto/gui/ui && pnpm build` |
| UI test | `cd src/niamoto/gui/ui && pnpm test` |
| UI lint | `cd src/niamoto/gui/ui && pnpm lint` |
| Bundle stats | `cd src/niamoto/gui/ui && pnpm build:stats` |
| Full GUI build | `bash scripts/build/build_gui.sh` |
| Standalone Tailwind | `uv run python scripts/build/build_tailwind_standalone.py` |

## Ask First
- Ask before changing semantics across `import.yml`, `transform.yml`, and `export.yml`.
- Ask before choosing between a new plugin and modifying an existing plugin.
- Ask before hardening one dataset-specific workaround into generic behavior.
- Check code and config first when the answer is discoverable locally.

## Genericity Rules
- Niamoto must work for many ecology projects, not only New Caledonia.
- Do not hardcode table names, field names, entity names, taxonomic values, or local project paths.
- Use configured schemas, `EntityRegistry`, service APIs, and plugin config models instead.
- Allowed hardcoded names: external standards such as Darwin Core, internal metadata tables such as `niamoto_metadata_*`, and framework conventions.
- Plugins must define `config_model` validation and access data through services rather than ad hoc database calls.
- When another process may lock DuckDB, prefer `Database(path, read_only=True)`.

## Frontend Rules
- New product workflows go in `src/niamoto/gui/ui/src/features/<domain>`.
- Shared code goes in `src/niamoto/gui/ui/src/shared` only when it is genuinely cross-feature.
- Do not add new feature hooks to root `src/hooks` or new feature API clients to root `src/lib/api`.
- Import lazy route modules by leaf path, not feature barrels.
- Desktop native capabilities must flow through `src/shared/desktop/bridge.ts`, not direct Tauri imports.
- Keep `src/niamoto/gui/ui/public/fonts` unless the desktop offline-font strategy changes.

## Validation
- For backend/API changes, run the most targeted pytest module first, then broaden if needed.
- For GUI behavior changes, run `pnpm test` or a targeted Vitest file plus `pnpm build`.
- For routing, editor, Monaco, Tiptap, or large dependency changes, compare `pnpm build:stats`.
- For import/profiler/ML changes, validate with a relevant `test-instance/*` fixture before trusting synthetic tests.

## Session-Derived Gotchas
- GUI/API DuckDB reads must use shared wrappers such as `open_database(..., read_only=True)`; avoid raw `duckdb.connect(...)` in GUI routes and dispose engines after request-scoped work.
- Do not run several commands against the same DuckDB instance in parallel unless the code path is explicitly designed for it.
- In Tauri, protected API mutations must go through the shared API client or desktop bridge so `x-niamoto-desktop-token` is added; avoid raw `fetch` for POST/PUT/PATCH/DELETE.
- Resolve project-relative paths from the active instance/config directory, not `os.getcwd()`; Tauri may run from `src-tauri`.
- Widget proposals are transform-first: reason from raw data plus planned/existing transform outputs, then choose a readable widget for the output shape.
- High-cardinality categoricals should prefer rankings/bar views over donut-style distributions; foundational widgets such as navigation/info/map should stay visible before secondary charts.
- Config writes that touch `transform.yml` and `export.yml` need locks, staging, or rollback; avoid partial success across the two files.
- Plugin discovery/reload must not pollute or lose the global registry: snapshot discovery state and keep the old plugin on reload failure.
- Desktop release fixes belong in packaging/CI when the packaged sidecar fails; keep the sidecar startup smoke test as a release gate.

## References
| Need | File |
|------|------|
| Contributing | `CONTRIBUTING.md` |
| Public docs style | `docs/STYLE_GUIDE.md` |
| Script commands | `scripts/README.md` |
| GUI overview | `docs/07-architecture/gui-overview.md` |
| GUI runtime | `docs/07-architecture/gui-runtime.md` |
| GUI backend/frontend | `src/niamoto/gui/README.md` |
| Frontend architecture | `src/niamoto/gui/ui/README.md` |
| Plugin development | `docs/04-plugin-development/` |
| ML detection | `docs/05-ml-detection/training-guide.md` |
| Release process | `.github/RELEASE.md` |

## Repo Notes
- Keep docs and GUI README files in English.
- Version bump files are `pyproject.toml`, `src/niamoto/__version__.py`, `docs/conf.py`, `src-tauri/tauri.conf.json`, and `src-tauri/Cargo.toml`.
- Do not edit generated/build outputs unless regenerating intentionally: `dist/`, `htmlcov/`, `coverage.xml`, docs `_build`, frontend `coverage/`.
- Commit messages use Conventional Commit prefixes in English.
