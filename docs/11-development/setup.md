# Development Setup

This guide will help you set up your local development environment for contributing to Niamoto.

## Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) - A fast Python package installer
- Git

## Setting Up Your Development Environment

### 1. Clone the Repository

```bash
git clone https://github.com/niamoto/niamoto.git
cd niamoto
```

### 2. Create a Virtual Environment

Using `uv` (recommended):

```bash
uv venv
```

### 3. Activate the Virtual Environment

```bash
# On macOS/Linux
source .venv/bin/activate

# On Windows
.venv\Scripts\activate
```

### 4. Install Niamoto in Development Mode

```bash
uv sync --group dev
```

`uv sync` installs the project in editable mode together with the selected dependency groups. If you build documentation frequently, you can also sync the documentation extra once:

```bash
uv sync --group dev --extra docs
```

## Managing Multiple Niamoto Installations

When working on the project locally, you may have multiple Niamoto installations on your system:

- **Editable installation**: Installed in your project's virtual environment (e.g., `.venv/lib/python3.12/site-packages`)
- **Global installation**: May exist if previously installed with `pip install niamoto` or `pipx install niamoto`

### Check Which Version You're Using

```bash
# Check which niamoto executable is being used
which niamoto

# Check installed version with uv
uv pip show niamoto
```

### Handling Conflicts

If you have a global installation (e.g., via pipx in `~/.local/bin/niamoto`) that conflicts with your development version:

- **Option 1**: Use `uv run niamoto` from your project directory to ensure the editable version is used
- **Option 2**: Activate your virtual environment with `source .venv/bin/activate` before running `niamoto`
- **Option 3**: Uninstall the global version with `pipx uninstall niamoto` to avoid confusion
- **Option 4**: Reinstall globally from your local code with `pipx install --editable .`

## Development Tools

### Code Quality Tools

The development installation includes several tools for maintaining code quality:

- **mypy**: For static type checking
- **pytest**: For running tests
- **ruff**: For linting and formatting
- **sphinx**: For building documentation via the `docs` extra

### Running Code Quality Checks

```bash
# Type checking
uv run --group dev mypy src/niamoto

# Linting and formatting
uv run --group dev ruff check src/ --fix
uv run --group dev ruff format src/

# Running tests
uv run --group dev pytest
uv run --group dev pytest --cov=src --cov-report html  # With coverage report
```

### Building Documentation

```bash
cd docs
uv run --group dev --extra docs sphinx-apidoc -o . ../src/niamoto
uv run --group dev --extra docs make html
```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes

- Write your code
- Add type hints to all functions
- Write docstrings for all public functions
- Add tests for new features

### 3. Run Tests and Checks

```bash
# Format your code
uv run --group dev ruff format src/

# Check for linting issues
uv run --group dev ruff check src/ --fix

# Run type checking
uv run --group dev mypy src/niamoto

# Run tests
uv run --group dev pytest
```

### 4. Commit Your Changes

Use the smart commit script for automatic pre-commit checks:

```bash
./scripts/dev/smart_commit.sh "feat: add new feature"
```

Or commit manually:

```bash
git add .
git commit -m "feat: add new feature"
```

### 5. Push and Create a Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Useful Commands

### Generate Requirements Files

```bash
uv run python scripts/build/generate_requirements.py
```

### Build Tailwind CSS

```bash
uv run python scripts/build/build_tailwind_standalone.py
```

### Publish to PyPI

PyPI publication is automated via GitHub Actions. Creating a GitHub Release triggers the `publish-pypi.yml` workflow (OIDC Trusted Publishers, no token needed).

## Common Issues

### Import Errors

If you encounter import errors, ensure:
1. Your virtual environment is activated
2. You've synced the project dependencies with `uv sync --group dev`
3. You're running from the project root directory

### Type Checking Errors

If mypy reports errors:
1. Ensure all functions have type hints
2. Check that you're using compatible types
3. Use `# type: ignore` sparingly for third-party libraries without stubs

## Next Steps

- Read the [Contributing Guidelines](contributing.md)
- Explore the [Architecture Documentation](../09-architecture/README.md)
- Check out the [Plugin Development Guide](../04-plugin-development/README.md)
