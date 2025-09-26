# Contributing to Niamoto

Thank you for your interest in contributing to Niamoto! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Development Setup

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
   uv pip install -e ".[dev]"

   # Install pre-commit hooks
   pre-commit install
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
- Write clean, documented code
- Follow existing patterns and conventions
- Add tests for new functionality

### 3. Test your changes
```bash
# Run tests
uv run pytest

# Run specific test
uv run pytest tests/path/to/test.py -v

# Check type hints
mypy src/niamoto

# Lint and format
ruff check src/ --fix
ruff format src/
```

### 4. Commit your changes
```bash
# Use the smart commit script (recommended)
./scripts/smart_commit.sh "feat: add new feature"

# Or commit manually
git add .
git commit -m "feat: add new feature"
```

## 🎨 Code Style

### Python Code
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

### TypeScript/React Code (GUI)
- Follow existing patterns in `src/niamoto/gui/ui/`
- Use TypeScript strict mode
- Follow React best practices

## 🧪 Testing

### Writing Tests
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

### Running Tests
```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=niamoto

# Specific test file
uv run pytest tests/core/test_import.py -v
```

## 📚 Documentation

### Updating Documentation
- Update relevant documentation in `docs/`
- Follow the numbered structure (01-getting-started, 02-data-pipeline, etc.)
- Include examples and use cases
- Update README.md if adding major features

### Documentation Style
- Write in English
- Use clear, concise language
- Include code examples
- Add links to related documentation

## 🔄 Pull Request Process

### Before submitting
1. ✅ All tests pass
2. ✅ Code is formatted and linted
3. ✅ Documentation is updated
4. ✅ Commit messages follow conventions

### PR Guidelines
- **Title**: Clear and descriptive
- **Description**: Explain what, why, and how
- **Screenshots**: Include for UI changes
- **Tests**: Add tests for new features
- **Breaking changes**: Clearly marked

### Commit Message Convention
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

### Bug Reports
Include:
- Clear description
- Steps to reproduce
- Expected behavior
- Actual behavior
- System information
- Error messages/logs

### Feature Requests
Include:
- Use case description
- Proposed solution
- Alternative solutions considered
- Additional context

## 💡 Areas for Contribution

### High Priority
- 🧪 Test coverage improvements
- 📚 Documentation translations
- 🐛 Bug fixes
- 🎨 UI/UX improvements

### Feature Areas
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

## 🙏 Thank You!

Your contributions make Niamoto better for everyone. We appreciate your time and effort!

---

*For more information, see the [Development Guide](docs/11-development/)*
