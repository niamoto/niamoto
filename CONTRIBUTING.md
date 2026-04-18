# Contributing to Niamoto

This document covers the development setup, code style, and PR process.

## 🚀 Getting Started

### Development setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/niamoto.git
   cd niamoto
   ```

2. **Set up development environment**
   ```bash
   # Using uv (recommended)
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv sync --group dev

   # Install pre-commit hooks
   uv run --group dev pre-commit install
   ```

3. **Set up GUI development (if working on the interface)**
   ```bash
   cd src/niamoto/gui/ui
   npm install
   ```

## 📝 Development Workflow

### 1. Create a feature branch
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Make your changes
- Follow existing patterns and conventions.
- Add tests for new functionality.
- Document non-obvious behaviour inline.

### 3. Test your changes
```bash
# Run tests
uv run --group dev pytest

# Run specific test
uv run --group dev pytest tests/path/to/test.py -v

# Check type hints
uv run --group dev mypy src/niamoto

# Lint and format
uv run --group dev ruff check src/ --fix
uv run --group dev ruff format src/
```

### 4. Commit your changes
```bash
# Use the smart commit script (recommended)
./scripts/dev/smart_commit.sh "feat: add new feature"

# Or commit manually
git add .
git commit -m "feat: add new feature"
```

## 🎨 Code Style

### Python code
- **Formatting**: Black (via ruff format)
- **Linting**: Ruff
- **Type hints**: Required for all public functions
- **Docstrings**: NumPy style for all public functions and classes

Example:
```python
from typing import Optional, List

def process_data(
    data: List[dict],
    threshold: float = 0.5,
    verbose: Optional[bool] = None
) -> dict:
    """
    Process ecological data with given threshold.

    Parameters
    ----------
    data : List[dict]
        Input data to process
    threshold : float, default=0.5
        Processing threshold value
    verbose : Optional[bool], default=None
        Enable verbose output

    Returns
    -------
    dict
        Processed results
    """
    # Implementation here
    pass
```

### TypeScript/React code (GUI)
- Follow existing patterns in `src/niamoto/gui/ui/`
- Use TypeScript strict mode
- Follow React best practices

## 🧪 Testing

### Writing tests
- Place tests in `tests/` mirroring the source structure
- Use descriptive test names
- Test both success and failure cases
- Use fixtures for common test data

Example:
```python
import pytest
from niamoto.core import SomeClass

def test_some_class_initialization():
    """Test that SomeClass initializes correctly."""
    obj = SomeClass(param="value")
    assert obj.param == "value"

def test_some_class_fails_with_invalid_input():
    """Test that SomeClass raises error with invalid input."""
    with pytest.raises(ValueError):
        SomeClass(param=None)
```

### Running tests
```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=niamoto

# Specific test file
uv run pytest tests/core/test_import.py -v
```

## 📚 Documentation

### Updating documentation

The public docs live under `docs/` and follow a lifecycle layout:

- `01-getting-started/` — install and first project
- `02-user-guide/` — desktop workflows: import, transform, preview, export
- `03-cli-automation/` — CLI, automation, CI/CD recipes
- `04-plugin-development/` — transformers, widgets, loaders, exporters
- `05-ml-detection/` — auto-detection research and training
- `06-reference/` — API, CLI commands, config schemas
- `09-architecture/` — ADRs, system design
- `10-roadmaps/` — dated plans and target architectures
- `99-troubleshooting/` — common issues and desktop smoke tests

Legacy content lives under `docs/_archive/` and is not part of the live
site. `docs/plans/`, `docs/brainstorms/` and `docs/ideation/` are internal
journals; they stay in the repo but are excluded from the rendered docs.

### Documentation style

- Write in English.
- Follow `docs/STYLE_GUIDE.md` for voice, banned vocabulary (AI-slop), and
  preferred product verbs.
- Prefer short sentences and action verbs over adjectives.
- Include runnable code examples when they clarify behaviour.
- Add links to related pages with relative paths, not absolute ones.

## 🔄 Pull Request Process

### Before submitting
1. ✅ All tests pass
2. ✅ Code is formatted and linted
3. ✅ Documentation is updated
4. ✅ Commit messages follow conventions

### PR guidelines
- **Title**: one sentence, imperative mood.
- **Description**: what changed, why, and how to test.
- **Screenshots**: include for UI changes.
- **Tests**: add tests for new features.
- **Breaking changes**: mark them explicitly.

### Commit message convention
We follow conventional commits:
```
type(scope): description

[optional body]

[optional footer(s)]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `chore`: Maintenance tasks

Example:
```
feat(ml-detection): add automatic column type detection

- Implement RandomForest classifier for type detection
- Add confidence scoring
- Include synthetic data generation

Closes #123
```

## 🐛 Reporting Issues

### Bug reports
Include:
- Clear description
- Steps to reproduce
- Expected behavior
- Actual behavior
- System information
- Error messages/logs

### Feature requests
Include:
- Use case description
- Proposed solution
- Alternative solutions considered
- Additional context

## 💡 Areas for Contribution

### High priority
- 🧪 Test coverage improvements
- 📚 Documentation translations
- 🐛 Bug fixes
- 🎨 UI/UX improvements

### Feature areas
- 🤖 ML detection improvements
- 🔌 New plugins
- 📊 New visualizations
- 🌍 Internationalization

## 🤝 Community

- **Discussions**: [GitHub Discussions](https://github.com/niamoto/niamoto/discussions)
- **Issues**: [GitHub Issues](https://github.com/niamoto/niamoto/issues)
- **Documentation**: [docs/](docs/)

## 📜 License

By contributing, you agree that your contributions will be licensed under the GPL-3.0 License.

---

*See the [project README](README.md) and
[docs/STYLE_GUIDE.md](docs/STYLE_GUIDE.md) for writing guidelines.*
