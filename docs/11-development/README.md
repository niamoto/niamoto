# Development

Guide for contributing to Niamoto development.

## 📚 Documents in this Section

- **[Setup](setup.md)** - Development environment setup
- **[Testing](testing.md)** - Testing guidelines (coming soon)
- **[Contributing](contributing.md)** - Contribution guide (coming soon)

## 🛠️ Development Setup

### Prerequisites
- Python 3.12+
- uv (recommended) or pip
- Node.js 18+ (for GUI)
- Git

### Quick Start
```bash
# Clone repository
git clone https://github.com/niamoto/niamoto.git
cd niamoto

# Install dependencies
uv venv
uv sync --group dev

# Install GUI dependencies
cd src/niamoto/gui/ui
pnpm install

# Run tests
uv run --group dev pytest

# Start development
uv run niamoto gui --reload
```

## 🧪 Testing

### Run Tests
```bash
# All tests
uv run --group dev pytest

# Specific test
uv run --group dev pytest tests/core/test_import.py -v

# With coverage
uv run --group dev pytest --cov=niamoto
```

### Code Quality
```bash
# Type checking
uv run --group dev mypy src/niamoto

# Linting
uv run --group dev ruff check src/ --fix

# Formatting
uv run --group dev ruff format src/
```

## 📝 Development Workflow

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Run quality checks
5. Submit pull request

## 🔧 Key Commands

```bash
# Generate requirements
uv run python scripts/build/generate_requirements.py

# Build Tailwind CSS
uv run python scripts/build/build_tailwind_standalone.py

# Smart commit with pre-commit
./scripts/dev/smart_commit.sh "message"

# Build documentation
cd docs && uv run --group dev --extra docs sphinx-apidoc -o . ../src/niamoto && uv run --group dev --extra docs make html
```

## 🔗 Related Documentation

- [Architecture](../09-architecture/README.md) - System design
- [Plugin Development](../04-plugin-development/README.md) - Creating plugins
- [API Reference](../05-api-reference/README.md) - API documentation

---
*Questions? Open an issue on GitHub!*
