# Repository Guidelines

## Project Structure & Module Organization
Core packages live in `src/niamoto`, grouped by domain (CLI, data pipelines, web export). Tests mirror this layout under `tests/` with `integration` markers for slower scenarios. Reusable scripts sit in `scripts/`, static assets in `assets/`, and developer docs in `docs/`. Use `examples/` for sample datasets when validating UI and pipeline changes.

## Build, Test, and Development Commands
Set up once per checkout:
```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```
Daily workflow:
```bash
uv run niamoto --help        # sanity-check CLI wiring
pytest                       # unit suite
pytest -m "not integration"  # fast loop
uv run tox -e py312          # multi-version check (optional)
```
Use `python scripts/build_tailwind_standalone.py` before committing GUI style updates.

## Coding Style & Naming Conventions
Follow Ruff formatting: 4-space indentation, 88-character lines, double quotes preferred, and imports sorted automatically (`ruff format` + `ruff check src/ --fix`). Keep functions type-hinted; MyPy runs in strict mode via `mypy src/niamoto`. Name modules and packages with lowercase underscores, classes in CapWords, and CLI commands/action handlers with imperative verbs (e.g., `transform_dataset`).

## Testing Guidelines
Pytest is the canonical harness; place new files beside the code they exercise (`tests/<module>/test_<feature>.py`). Mark long-running scenarios with `@pytest.mark.integration` and exclude them locally with the flag above. Aim to maintain coverage near the existing HTML report (`htmlcov/index.html`); add regression fixtures in `tests/data/` and document datasets in `examples/README.md` when applicable.

## Commit & Pull Request Guidelines
Commits follow Conventional Commit verbs (`feat:`, `fix:`, `chore:`). Run `./scripts/smart_commit.sh "feat: summary"` for automatic checks, or stage manually after `ruff`, `mypy`, and `pytest` pass. Pull requests should describe the motivation, list behavioral changes, link tracking issues, and include screenshots or CLI output for UI/UX or pipeline updates. Confirm docs or config snapshots in `docs/` and `assets/` stay in sync before requesting review.
