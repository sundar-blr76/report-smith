# Contributing to ReportSmith

Thank you for your interest in contributing to ReportSmith! This document provides guidelines and best practices for contributing to the project.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Setup](#development-setup)
3. [Code Organization](#code-organization)
4. [Coding Standards](#coding-standards)
5. [Testing](#testing)
6. [Pull Request Process](#pull-request-process)
7. [Documentation](#documentation)

---

## Getting Started

### Prerequisites

Before you begin, ensure you have:
- Python 3.12 or higher
- PostgreSQL 12 or higher
- Git
- A code editor (VS Code recommended)

### First-Time Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/report-smith.git
   cd report-smith
   ```

2. **Create Virtual Environment**
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -e .  # Install in editable mode
   ```

4. **Set Up Environment Variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and database credentials
   ```

5. **Initialize Database**
   ```bash
   cd db_setup
   python3 setup_database.py
   ```

6. **Run Tests**
   ```bash
   pytest tests/
   ```

---

## Development Setup

### Running Locally

**Start the application:**
```bash
./start.sh
```

This starts:
- FastAPI server at `http://127.0.0.1:8000`
- Streamlit UI at `http://127.0.0.1:8501`

**Stop the application:**
```bash
kill $(cat logs/api.pid)
kill $(cat logs/ui.pid)
```

### Development Workflow

1. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Write code following our [coding standards](#coding-standards)
   - Add tests for new functionality
   - Update documentation as needed

3. **Run Tests Frequently**
   ```bash
   pytest tests/
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: Add your feature description"
   ```

5. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   # Then create a Pull Request on GitHub
   ```

---

## Code Organization

### Project Structure

```
src/reportsmith/
├── agents/              # LangGraph orchestration
├── query_processing/    # Intent analysis, SQL generation
├── schema_intelligence/ # Embeddings, knowledge graph
├── query_execution/     # SQL execution
├── api/                 # FastAPI server
└── ui/                  # Streamlit interface
```

### Module Guidelines

1. **Single Responsibility**: Each module should have one clear purpose
2. **No Circular Dependencies**: Avoid circular imports
3. **Size Limit**: Keep files under 500 lines (except generated code)
4. **Package Structure**: Use packages for related functionality

### Adding New Features

**For a new agent node:**
1. Add function to `agents/nodes.py`
2. Update workflow in `agents/orchestrator.py`
3. Update `QueryState` if needed
4. Add tests in `tests/unit/`

**For a new intent type:**
1. Update enum in `query_processing/intent_analyzer.py`
2. Add handling logic
3. Update SQL generator
4. Add integration test

---

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with some modifications:

- **Line Length**: 88 characters (Black default)
- **Quotes**: Double quotes for strings
- **Imports**: Sorted with isort
- **Type Hints**: Required for all functions

### Code Formatting

**Use Black for formatting:**
```bash
black src/ tests/
```

**Use isort for import sorting:**
```bash
isort src/ tests/
```

**Run all formatters:**
```bash
black src/ tests/ && isort src/ tests/
```

### Linting

**Run flake8:**
```bash
flake8 src/ tests/
```

**Run mypy for type checking:**
```bash
mypy src/
```

### Example Code Style

```python
"""Module docstring describing purpose."""

from typing import Dict, List, Optional

from reportsmith.schema_intelligence import KnowledgeGraph
from reportsmith.query_processing.intent_analyzer import Intent


def process_query(
    question: str,
    graph: KnowledgeGraph,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Process a natural language query.
    
    Args:
        question: User's natural language question
        graph: Knowledge graph instance
        timeout: Maximum processing time in seconds
        
    Returns:
        Dictionary containing query results and metadata
        
    Raises:
        ValueError: If question is empty
        TimeoutError: If processing exceeds timeout
    """
    if not question:
        raise ValueError("Question cannot be empty")
    
    # Implementation
    return {"status": "ok"}
```

### Naming Conventions

- **Modules**: `lowercase_with_underscores.py`
- **Classes**: `PascalCase`
- **Functions**: `lowercase_with_underscores()`
- **Constants**: `UPPERCASE_WITH_UNDERSCORES`
- **Private**: Prefix with single underscore `_private_function()`

---

## Testing

### Test Organization

```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── fixtures/       # Test fixtures
└── conftest.py     # Shared fixtures
```

### Writing Tests

**Unit Test Example:**
```python
import pytest
from reportsmith.query_processing.intent_analyzer import IntentAnalyzer


def test_intent_analyzer_basic():
    """Test basic intent analysis."""
    analyzer = IntentAnalyzer()
    result = analyzer.analyze("Show total AUM")
    
    assert result["intent_type"] == "aggregate"
    assert "aum" in [e["text"] for e in result["entities"]]
```

**Integration Test Example:**
```python
import pytest
from reportsmith.agents.orchestrator import Orchestrator


@pytest.mark.integration
def test_end_to_end_query():
    """Test complete query processing pipeline."""
    orchestrator = Orchestrator()
    result = orchestrator.process("Show AUM for equity funds")
    
    assert result["status"] == "ok"
    assert "sql" in result["data"]
    assert result["data"]["sql"]["sql"] is not None
```

### Running Tests

**Run all tests:**
```bash
pytest tests/
```

**Run specific test file:**
```bash
pytest tests/unit/test_intent_analyzer.py
```

**Run with coverage:**
```bash
pytest --cov=src/reportsmith --cov-report=html tests/
```

**View coverage report:**
```bash
open htmlcov/index.html
```

### Test Coverage Requirements

- **Unit tests**: >80% coverage for core modules
- **Integration tests**: All major workflows
- **New features**: Must include tests
- **Bug fixes**: Add regression test

---

## Pull Request Process

### Before Submitting

1. **Run all tests:** `pytest tests/`
2. **Check formatting:** `black --check src/ tests/`
3. **Check linting:** `flake8 src/ tests/`
4. **Check types:** `mypy src/`
5. **Update docs:** If needed

### PR Title Format

Use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat: Add new feature`
- `fix: Fix bug in SQL generator`
- `docs: Update README`
- `refactor: Restructure intent analyzer`
- `test: Add tests for embedding manager`
- `chore: Update dependencies`

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] All tests passing

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings
```

### Review Process

1. **Automated Checks**: CI/CD runs tests, linting, type checking
2. **Code Review**: At least one maintainer reviews
3. **Approval**: PR must be approved before merge
4. **Merge**: Squash and merge to main branch

---

## Documentation

### What to Document

1. **New Features**: Update README.md and relevant docs
2. **API Changes**: Update API documentation
3. **Configuration**: Update SETUP.md if config changes
4. **Architecture**: Update ARCHITECTURE.md for major changes

### Documentation Standards

- **Clear and Concise**: Avoid jargon where possible
- **Examples**: Include code examples
- **Up-to-date**: Keep docs synchronized with code
- **Cross-references**: Link related documentation

### Docstring Format

Use Google-style docstrings:

```python
def function_name(param1: str, param2: int) -> Dict[str, Any]:
    """
    Short description of function.
    
    Longer description if needed, explaining what the function does,
    any important details, edge cases, etc.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When param1 is invalid
        
    Example:
        >>> result = function_name("test", 42)
        >>> print(result)
        {'status': 'ok'}
    """
    pass
```

---

## Common Tasks

### Adding a New LLM Provider

1. Create provider class in `query_processing/`
2. Implement common interface
3. Add configuration options
4. Add tests
5. Update documentation

### Adding a New Database Type

1. Create connection manager
2. Add SQL dialect support
3. Update schema loader
4. Add tests with sample database
5. Update SETUP.md

### Improving Performance

1. **Profile first**: Use cProfile to identify bottlenecks
2. **Measure impact**: Before and after benchmarks
3. **Add tests**: Performance regression tests
4. **Document**: Explain optimization in commit message

### Debugging Tips

**View logs:**
```bash
tail -f logs/app.log
```

**Enable debug logging:**
```python
import logging
logging.getLogger("reportsmith").setLevel(logging.DEBUG)
```

**Use semantic debug output:**
```bash
cat logs/semantic_debug/semantic_output.json | jq .
```

**Interactive debugging:**
```python
import pdb; pdb.set_trace()  # Add breakpoint
```

---

## Getting Help

- **Documentation**: Start with [docs/](docs/)
- **Issues**: Check existing [GitHub Issues](https://github.com/sundar-blr76/report-smith/issues)
- **Discussions**: Use GitHub Discussions for questions
- **Architecture**: See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Code of Conduct

### Our Standards

- **Be Respectful**: Treat everyone with respect
- **Be Constructive**: Provide helpful feedback
- **Be Collaborative**: Work together towards common goals
- **Be Professional**: Maintain professional conduct

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or insulting comments
- Publishing private information
- Other unprofessional conduct

---

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

## Thank You!

Your contributions make ReportSmith better for everyone. We appreciate your time and effort!

---

**Questions?** Open an issue or discussion on GitHub.

**Last Updated**: November 4, 2025
