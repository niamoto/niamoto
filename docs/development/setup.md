# Development Setup

This guide will help you set up your local development environment for contributing to Niamoto.

## Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) - A fast Python package installer
- Git

## Setting Up Your Development Environment

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/niamoto.git
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
uv pip install -e ".[dev]"
```

The `-e` flag installs the package in editable mode, meaning source code changes are immediately reflected without needing to reinstall the package.

## Managing Multiple Niamoto Installations

When using `uv pip install -e .`, you may have multiple Niamoto installations on your system:

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
- **sphinx**: For building documentation

### Running Code Quality Checks

```bash
# Type checking
mypy src/niamoto

# Linting and formatting
ruff check src/ --fix
ruff format src/

# Running tests
pytest
pytest --cov=src --cov-report html  # With coverage report
```

### Building Documentation

```bash
cd docs
sphinx-apidoc -o . ../src/niamoto
make html
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
ruff format src/

# Check for linting issues
ruff check src/ --fix

# Run type checking
mypy src/niamoto

# Run tests
pytest
```

### 4. Commit Your Changes

Use the smart commit script for automatic pre-commit checks:

```bash
./scripts/smart_commit.sh "feat: add new feature"
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
python scripts/generate_requirements.py
```

### Build Tailwind CSS

```bash
python scripts/build_tailwind_standalone.py
```

### Publish to PyPI

```bash
./scripts/publish.sh
```

## Common Issues

### Import Errors

If you encounter import errors, ensure:
1. Your virtual environment is activated
2. You've installed in editable mode (`-e` flag)
3. You're running from the project root directory

### Type Checking Errors

If mypy reports errors:
1. Ensure all functions have type hints
2. Check that you're using compatible types
3. Use `# type: ignore` sparingly for third-party libraries without stubs

## Next Steps

- Read the [Contributing Guidelines](../CONTRIBUTING.md)
- Explore the [Architecture Documentation](../architecture/README.md)
- Check out the [Plugin Development Guide](../plugins/README.md)
