# Repository Guidelines

## Project Overview

Niamoto is a Python-first project with:

- core code in [src/niamoto](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto)
- tests in [tests](/Users/julienbarbe/Dev/clients/niamoto/tests)
- developer scripts in [scripts](/Users/julienbarbe/Dev/clients/niamoto/scripts)
- documentation in [docs](/Users/julienbarbe/Dev/clients/niamoto/docs)
- the GUI stack in [src/niamoto/gui](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui)

Use [examples](/Users/julienbarbe/Dev/clients/niamoto/examples) and `tests/data/` for sample datasets and regression fixtures.

Product model:

- import raw data
- transform it into reusable group statistics
- export/publish final outputs

Keep solutions understandable to domain users. If a field botanist would not understand the workflow quickly, it is probably too complex.

## Codebase Map

Important areas:

- [src/niamoto/cli](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/cli): CLI commands and entry points
- [src/niamoto/core](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/core): import, transform, export, plugins
- [src/niamoto/gui/api](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/api): FastAPI GUI backend
- [src/niamoto/gui/ui](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui): React/Vite frontend
- [docs/06-gui](/Users/julienbarbe/Dev/clients/niamoto/docs/06-gui): GUI architecture and operations docs

Frontend architecture now follows:

- `src/app`
- `src/features`
- `src/shared`

For frontend-specific structure and conventions, see:

- [src/niamoto/gui/README.md](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/README.md)
- [src/niamoto/gui/ui/README.md](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/README.md)

## Setup and Daily Commands

Python environment:

```bash
uv venv && source .venv/bin/activate
uv sync --group dev
```

Useful project commands:

```bash
uv run niamoto --help
uv run --group dev pytest
uv run --group dev pytest -m "not integration"
uv run tox -e py312
```

GUI development:

```bash
./scripts/dev/dev_web.sh test-instance/niamoto-nc
uv run python scripts/dev/dev_api.py --instance test-instance/niamoto-nc
cd src/niamoto/gui/ui && pnpm dev
cd src/niamoto/gui/ui && pnpm build
```

If you change GUI styling that depends on the standalone Tailwind bundle, run:

```bash
uv run python scripts/build/build_tailwind_standalone.py
```

## Coding Conventions

- Use Ruff formatting and import sorting.
- Keep Python code type-hinted; MyPy is expected to pass on `src/niamoto`.
- Use lowercase underscore module names, CapWords classes, and imperative CLI handler names.
- Prefer small, explicit refactors over broad file churn.
- Keep documentation in English unless a file is explicitly meant to stay otherwise.

## Modeling and Architecture Rules

- Respect the product layers:
  - `import.yml` for data loading
  - `transform.yml` for statistics and aggregation logic
  - `export.yml` for rendering and publication
- Clarify with the user when a change crosses one of these boundaries.
- Favor generic solutions over dataset-specific shortcuts.

Do not hardcode:

- dataset or table names
- field names
- entity names
- domain-specific values tied to one project

Allowed exceptions:

- well-known external standards such as Darwin Core fields
- internal metadata tables such as `niamoto_metadata_*`
- framework conventions

When unsure, ask: would this still work for a different ecology project with different entities, schemas, and taxonomies?

- Access the database through services, not directly inside plugins
- Plugins should expose `config_model` validation
- Prefer existing plugin mechanisms over bespoke one-off code paths

## Testing and Validation

- Pytest is the main test harness.
- Put tests beside the code they exercise under [tests](/Users/julienbarbe/Dev/clients/niamoto/tests).
- Mark slow scenarios with `@pytest.mark.integration`.
- For GUI work, run `pnpm build` at minimum.
- For backend/API changes, run the most targeted pytest module possible, then broaden if needed.
- Prefer checking the relevant code and config first before asking the user clarifying questions.

## Frontend Conventions

- New product workflows should go in `src/features/<domain>`.
- Put only truly cross-feature code in `src/shared`.
- Avoid adding new feature logic to root `src/hooks` or root `src/lib/api` unless it is genuinely shared.
- Keep feature docs aligned with:
  - [src/niamoto/gui/ui/README.md](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/README.md)
  - [docs/06-gui](/Users/julienbarbe/Dev/clients/niamoto/docs/06-gui)

## Documentation Rules

- Update docs when workflows, architecture, or commands materially change.
- Prefer documenting the current implementation over aspirational designs.
- Treat [docs/06-gui](/Users/julienbarbe/Dev/clients/niamoto/docs/06-gui) as the GUI architecture/operations reference.
- Keep [src/niamoto/gui/README.md](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/README.md) and [src/niamoto/gui/ui/README.md](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/README.md) consistent with code moves.

## Git and Commit Rules

- Use Conventional Commit prefixes such as `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`.
- Before committing, run the most relevant checks for the area you changed.
- Do not revert unrelated user changes.
- Keep commits scoped to one coherent concern when possible.

## Repo-Specific Notes

- `dist/` under the frontend is build output and should not be treated as source.
- `.DS_Store` and `.ruff_cache` should never be committed.
- [src/niamoto/gui/ui/public/fonts](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/public/fonts) is intentionally kept because desktop mode uses local fonts.
- [src/niamoto/gui/ui/components.json](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/components.json) is the shadcn/ui config file and should stay in sync with the UI structure if shadcn tooling is used.
- The GUI docs live in [docs/06-gui](/Users/julienbarbe/Dev/clients/niamoto/docs/06-gui) and should describe the current implementation, not old plans.
