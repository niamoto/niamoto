# Contributing to Niamoto

Niamoto is a Python-first project with a desktop GUI and a CLI. Keep changes
small, test the part you touched, and update the docs when behavior changes.

## Set up your environment

Clone the repository and install the Python toolchain from the project root:

```bash
git clone https://github.com/niamoto/niamoto.git
cd niamoto
uv venv
source .venv/bin/activate
uv sync --group dev
uv run --group dev pre-commit install
```

If you work on the GUI, install the frontend dependencies too:

```bash
cd src/niamoto/gui/ui
pnpm install
cd ../../../..
```

## Know the repository

- `src/niamoto/` holds the core Python code.
- `src/niamoto/cli/` holds the CLI entry points and commands.
- `src/niamoto/gui/` holds the FastAPI backend and the React frontend.
- `tests/` holds the test suite.
- `docs/` holds the public docs, internal plans, and reference material.
- `scripts/` holds build, release, and development helpers.

Use `examples/` and `tests/data/` when you need fixtures or sample datasets.

## Work on one change at a time

Create a short branch name that states the change:

```bash
git checkout -b fix/import-preview-empty-state
```

When you change product behavior, keep the pipeline boundaries clear:

- `import.yml` loads data.
- `transform.yml` computes aggregates and statistics.
- `export.yml` renders or publishes outputs.

Do not hardcode dataset names, field names, or entity names for one ecology
project unless the code targets a public standard such as Darwin Core.

## Run the right checks

Run the smallest useful check first, then widen the scope if needed.

### Python and backend changes

```bash
uv run --group dev pytest tests/path/to/test.py -v
uv run --group dev pytest -m "not integration"
uv run --group dev mypy src/niamoto
uv run --group dev ruff check src/ tests/
uv run --group dev ruff format src/ tests/
```

### GUI changes

Start the web stack:

```bash
./scripts/dev/dev_web.sh test-instance/niamoto-nc
```

Or run the backend and frontend separately:

```bash
uv run python scripts/dev/dev_api.py --instance test-instance/niamoto-nc
cd src/niamoto/gui/ui
pnpm dev
```

Before you open a PR for GUI work, run:

```bash
cd src/niamoto/gui/ui
pnpm build
```

If your change depends on the standalone Tailwind bundle, rebuild it:

```bash
uv run python scripts/build/build_tailwind_standalone.py
```

## Follow the house style

### Python

- Use type hints on public code.
- Keep functions and modules small and explicit.
- Let Ruff handle formatting and import order.
- Write NumPy-style docstrings when public APIs need explanation.

### Frontend

- Put new product workflows under `src/features/<domain>`.
- Put shared code under `src/shared/` only when multiple features use it.
- Keep root-level hooks and API helpers small.
- Follow the structure described in `src/niamoto/gui/README.md` and
  `src/niamoto/gui/ui/README.md`.

### Documentation

Write docs in English. Follow [docs/STYLE_GUIDE.md](docs/STYLE_GUIDE.md) for
voice, banned vocabulary, and preferred product terms.

The public docs tree is:

- `docs/01-getting-started/`
- `docs/02-user-guide/`
- `docs/03-cli-automation/`
- `docs/04-plugin-development/`
- `docs/05-ml-detection/`
- `docs/06-reference/`
- `docs/07-architecture/`
- `docs/08-roadmaps/`
- `docs/09-troubleshooting/`

These directories stay in the repository but do not ship as public docs:

- `docs/plans/`
- `docs/brainstorms/`
- `docs/ideation/`
- `docs/_archive/`

## Commit and pull request rules

Use conventional commits:

```text
feat: add collection summary widget
fix: preserve import mapping after reload
docs: refresh contributing guide
```

You can commit by hand or use the helper script:

```bash
./scripts/dev/smart_commit.sh "feat: add collection summary widget"
```

Before you open a pull request:

1. Run the checks for the area you changed.
2. Update the docs when behavior, workflow, or architecture changed.
3. Add or update tests when the change affects behavior.
4. Review the diff for stray files such as `.DS_Store`, `dist/`, or caches.

In the pull request description, explain:

- What changed.
- Why you changed it.
- How a reviewer can test it.
- Which screenshots matter for GUI work.

Call out breaking changes, schema changes, or migration steps.

## Reporting issues and proposing changes

Use [GitHub Issues](https://github.com/niamoto/niamoto/issues) for bugs and
[GitHub Discussions](https://github.com/niamoto/niamoto/discussions) for
questions or broader ideas.

When you report a bug, include:

- The command or screen you used.
- The dataset or instance context, if it matters.
- The expected result.
- The actual result.
- The traceback, logs, or screenshots.

## License

By contributing, you agree to license your work under GPL-3.0-or-later.
