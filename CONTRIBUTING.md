# Contributing to ReportSmith

Thank you for your interest in contributing to ReportSmith!

## Quick Start

### Prerequisites
- Python 3.12+
- PostgreSQL 12+
- Git

### Setup
```bash
# Clone and setup
git clone https://github.com/YOUR_USERNAME/report-smith.git
cd report-smith
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .

# Configure
cp .env.example .env
# Edit .env with your API keys and database credentials

# Initialize database
cd db_setup && python3 setup_database.py

# Run tests
pytest tests/
```

## Development Workflow

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Follow PEP 8 style guidelines
   - Add tests for new functionality
   - Update relevant documentation

3. **Test Thoroughly**
   ```bash
   pytest tests/                           # Run all tests
   python tests/validation/validate_test_queries.py  # Validate test queries
   pytest tests/test_specific.py -v       # Run specific test
   ```

4. **Clean Up Generated Files**
   ```bash
   make clean                              # Clean all generated files
   make clean-coverage                     # Clean coverage reports only
   make clean-logs                         # Clean logs only
   # Or use the script directly:
   ./scripts/cleanup.sh all
   ```

5. **Commit with Clear Messages**
   ```bash
   git commit -m "feat: add currency auto-inclusion for fee queries"
   git commit -m "fix: prevent incorrect fuzzy column mapping"
   git commit -m "docs: update API documentation"
   ```

6. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a Pull Request on GitHub.

## Code Organization

```
src/reportsmith/
├── agents/           # Orchestration and workflow nodes
├── api/             # FastAPI endpoints
├── query_processing/ # Intent analysis, SQL generation
├── query_execution/  # SQL execution and validation
├── schema_intelligence/ # Knowledge graph, embeddings
├── ui/              # Streamlit interface
└── utils/           # Shared utilities
```

## Key Areas to Contribute

### 1. Query Processing
- Improve intent detection accuracy
- Enhance domain value matching
- Add support for new query types

### 2. SQL Generation
- Optimize JOIN strategies
- Improve WHERE clause construction
- Add support for more SQL patterns

### 3. Schema Intelligence
- Enhance relationship detection
- Improve semantic search accuracy
- Add support for new database dialects

### 4. Testing
- Add test cases for edge cases
- Improve test coverage
- Add performance benchmarks

## Coding Standards

### Python Style
- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use meaningful variable names

### Documentation
- Add docstrings to all public functions/classes
- Update README if adding major features
- Include examples in docstrings

### Logging
```python
from reportsmith.logger import get_logger
logger = get_logger(__name__)

logger.info(f"[component] Important info message")
logger.debug(f"[component] Detailed debug info")
logger.warning(f"[component] Warning message")
logger.error(f"[component] Error details", exc_info=True)
```

### Testing
- Write unit tests for new functions
- Add integration tests for workflows
- Use descriptive test names
- Aim for >80% code coverage

## Pull Request Guidelines

### Before Submitting
- [ ] All tests pass
- [ ] Code follows style guidelines
- [ ] Documentation is updated
- [ ] Commit messages are clear
- [ ] No merge conflicts

### PR Description Should Include
- **What**: Brief description of changes
- **Why**: Reason for the change
- **How**: Implementation approach
- **Testing**: How you tested the changes

### Review Process
1. Automated tests run on PR
2. Code review by maintainer
3. Address review feedback
4. Merge after approval

## Testing Guidelines

### Running Tests
```bash
# All tests
pytest tests/

# Specific test file
pytest tests/test_sql_generator.py -v

# With coverage
pytest --cov=src/reportsmith tests/

# Specific test function
pytest tests/test_sql_generator.py::test_currency_inclusion -v
```

### Writing Tests
```python
def test_feature_name():
    """Test that feature works correctly."""
    # Arrange
    input_data = {...}
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result.success
    assert result.value == expected_value
```

## Getting Help

- **Documentation**: See README.md and SETUP.md
- **Issues**: Search existing issues or create new one
- **Questions**: Ask in GitHub Discussions

## Cleanup and Maintenance

### Cleaning Generated Files

The project generates various temporary files during development and testing. Use the provided cleanup tools to keep your workspace clean:

#### Using Make (recommended)
```bash
make clean              # Clean all generated files
make clean-coverage     # Clean coverage reports and .coverage files
make clean-logs         # Clean log files (keeps directory structure)
make clean-cache        # Clean Python __pycache__ and .pyc files
make clean-temp         # Clean temporary files
```

#### Using the Cleanup Script Directly
```bash
./scripts/cleanup.sh              # Clean all
./scripts/cleanup.sh coverage     # Clean coverage only
./scripts/cleanup.sh logs         # Clean logs only
./scripts/cleanup.sh cache        # Clean Python cache only
./scripts/cleanup.sh temp         # Clean temp files only
```

### What Gets Cleaned

- **Coverage reports**: `htmlcov/`, `.coverage`, `.coverage.*`
- **Pytest cache**: `.pytest_cache/`
- **Logs**: `logs/*.log`, `logs/*.json`, `logs/semantic_debug/*.json`
- **Python cache**: `__pycache__/`, `*.pyc`, `*.pyo`
- **Temporary files**: `/tmp/reportsmith_*`, `*.tmp`

### Best Practices

- Run `make clean` before committing to ensure no generated files are included
- Clean logs periodically to save disk space
- Clean coverage reports before running new test coverage analysis
- All generated files are already in `.gitignore`

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
