# Contributing to Serpex Haystack Integration

Thank you for your interest in contributing to the Serpex Haystack integration! We welcome contributions from the community.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/serpex-haystack.git`
3. Create a new branch: `git checkout -b feature/your-feature-name`

## Development Setup

```bash
# Install in development mode with all dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/haystack_integrations --cov-report=html

# Run specific test file
pytest tests/test_serpex.py
```

## Code Style

We use:
- `black` for code formatting
- `ruff` for linting
- `mypy` for type checking

```bash
# Format code
black .

# Run linting
ruff check .

# Run type checking
mypy src/
```

## Pull Request Process

1. Ensure all tests pass
2. Update documentation if needed
3. Add tests for new features
4. Update CHANGELOG.md
5. Submit a pull request with a clear description

## Code of Conduct

Please be respectful and constructive in all interactions.

## Questions?

Open an issue or reach out via Discord: https://discord.gg/serpex
