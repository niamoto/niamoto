# Development

Guide for contributing to Niamoto development.

## 📚 Documents in this Section

- **[Setup](setup.md)** - Development environment setup
- **[Testing](testing.md)** - Testing guidelines (coming soon)
- **[Contributing](contributing.md)** - Contribution guide (coming soon)

## 🛠️ Development Setup

### Prerequisites
- Python 3.11+
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
uv pip install -e ".[dev]"

# Install GUI dependencies
cd src/niamoto/gui/ui
pnpm install

# Run tests
uv run pytest

# Start development
niamoto gui --reload
```

## 🧪 Testing

### Run Tests
```bash
# All tests
uv run pytest

# Specific test
uv run pytest tests/core/test_import.py -v

# With coverage
uv run pytest --cov=niamoto
```

### Code Quality
```bash
# Type checking
mypy src/niamoto

# Linting
ruff check src/ --fix

# Formatting
ruff format src/
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
python scripts/generate_requirements.py

# Build Tailwind CSS
python scripts/build_tailwind_standalone.py

# Smart commit with pre-commit
./scripts/smart_commit.sh "message"

# Build documentation
cd docs && sphinx-apidoc -o . ../src/niamoto && make html
```

## 🔗 Related Documentation

- [Architecture](../09-architecture/README.md) - System design
- [Plugin Development](../04-plugin-development/README.md) - Creating plugins
- [API Reference](../05-api-reference/README.md) - API documentation

---
*Questions? Open an issue on GitHub!*
