# ReportSmith - Copilot Instructions

## Project Overview

ReportSmith is an intelligent natural language to SQL application for financial data reporting. It uses a multi-agent AI system powered by LangGraph to understand database schemas and dynamically generate SQL queries from natural language questions.

**Key Capabilities:**
- Natural Language to SQL conversion for financial reporting
- Multi-database support (PostgreSQL, Oracle, SQL Server)
- Hybrid intent analysis using local mappings, semantic search, and LLM
- Knowledge graph for understanding table relationships
- Automatic filter application and query optimization
- Real-time SQL execution with formatted results
- Complete audit trail of all operations

## Tech Stack

### Languages & Frameworks
- **Python 3.12+**: Primary language (required version)
- **FastAPI**: REST API server
- **Streamlit**: Interactive web UI
- **LangGraph**: Multi-agent workflow orchestration

### AI & Machine Learning
- **OpenAI**: GPT models for intent analysis and embeddings
- **Google Gemini**: Alternative LLM provider
- **LangChain**: LLM integration framework
- **ChromaDB**: Vector store for semantic search
- **Sentence Transformers**: Local embeddings support

### Database
- **SQLAlchemy 2.0+**: ORM and database abstraction
- **PostgreSQL**: Primary metadata and audit storage
- **Alembic**: Database migrations
- **Multiple DB Support**: psycopg2, pymysql, cx_Oracle, pyodbc

### Development Tools
- **pytest**: Testing framework (80%+ coverage required)
- **black**: Code formatting (88 char line length)
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking

## Repository Structure

```
src/reportsmith/
├── agents/                # LangGraph orchestration and workflow nodes
├── query_processing/      # Intent analysis and SQL generation
├── schema_intelligence/   # Embeddings, knowledge graph, schema mapping
├── query_execution/       # SQL execution engine
├── database/              # Database connections and utilities
├── api/                   # FastAPI REST API endpoints
├── ui/                    # Streamlit user interface
├── config_system/         # Configuration management
└── utils/                 # Shared utilities

config/
├── applications/          # YAML configuration files (one per app)
└── entity_mappings.yaml   # Entity to schema mappings

tests/
├── unit/                  # Unit tests for individual components
├── integration/           # End-to-end integration tests
├── fixtures/              # Test data and fixtures
└── conftest.py           # Shared pytest fixtures

docs/
├── ARCHITECTURE.md        # System architecture documentation
├── CURRENT_STATE.md       # Current status and roadmap
├── DATABASE_SCHEMA.md     # Database schema details
└── archive/              # Historical implementation notes
```

## Coding Standards

### Python Style Guide

Follow **PEP 8** with these specific requirements:

1. **Line Length**: 88 characters (Black default)
2. **Quotes**: Double quotes for strings
3. **Imports**: Sorted with isort, grouped by stdlib/third-party/local
4. **Type Hints**: **REQUIRED** for all function signatures
5. **Docstrings**: Google-style format for all public functions/classes

### Naming Conventions

- **Modules**: `lowercase_with_underscores.py`
- **Classes**: `PascalCase`
- **Functions**: `lowercase_with_underscores()`
- **Constants**: `UPPERCASE_WITH_UNDERSCORES`
- **Private members**: Prefix with single underscore `_private_function()`

### Code Formatting Workflow

**Before committing, run:**
```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Check linting
flake8 src/ tests/

# Type check
mypy src/
```

### Example Code Style

```python
"""Module docstring describing purpose."""

from typing import Dict, List, Optional, Any

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
        
    Example:
        >>> result = process_query("Show total AUM", graph)
        >>> print(result["status"])
        'ok'
    """
    if not question:
        raise ValueError("Question cannot be empty")
    
    # Implementation here
    return {"status": "ok"}
```

## Architecture Principles

### Multi-Agent Design

ReportSmith uses a **LangGraph-based multi-agent architecture**. When working with agents:

1. **Stateful Workflows**: All agents operate on a shared `QueryState` object
2. **Node Functions**: Agent nodes are pure functions that take state and return updates
3. **Error Handling**: Each node should handle errors gracefully and update state
4. **Logging**: Use request ID tracking for all agent operations

### Adding New Agent Nodes

1. Create function in `agents/nodes.py`
2. Update workflow in `agents/orchestrator.py`
3. Update `QueryState` TypedDict if adding new state fields
4. Add unit tests in `tests/unit/`
5. Add integration test for the complete workflow

### Database Abstraction

- Use SQLAlchemy for all database operations
- Support multiple database backends (PostgreSQL, Oracle, SQL Server)
- Always use parameterized queries (never string concatenation)
- Handle connection pooling and timeouts appropriately

## Testing Requirements

### Test Coverage

- **Minimum coverage**: 80% for all new code
- **Core modules**: Should exceed 90% coverage
- **Integration tests**: Required for all major workflows
- **New features**: Must include both unit and integration tests
- **Bug fixes**: Must include regression test

### Test Organization

```python
# Unit test example
import pytest
from reportsmith.query_processing.intent_analyzer import IntentAnalyzer


def test_intent_analyzer_basic():
    """Test basic intent analysis."""
    analyzer = IntentAnalyzer()
    result = analyzer.analyze("Show total AUM")
    
    assert result["intent_type"] == "aggregate"
    assert "aum" in [e["text"] for e in result["entities"]]


# Integration test example
@pytest.mark.integration
def test_end_to_end_query():
    """Test complete query processing pipeline."""
    orchestrator = Orchestrator()
    result = orchestrator.process("Show AUM for equity funds")
    
    assert result["status"] == "ok"
    assert "sql" in result["data"]
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src/reportsmith --cov-report=html tests/

# Run specific test type
pytest tests/unit/
pytest tests/integration/

# Run specific test file
pytest tests/unit/test_intent_analyzer.py
```

## Development Workflow

### Setting Up Development Environment

```bash
# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .  # Editable install

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Initialize database
cd db_setup
python3 setup_database.py
```

### Running the Application

```bash
# Start both API and UI
./start.sh

# Or start individually:
# FastAPI server (http://127.0.0.1:8000)
uvicorn src.reportsmith.api.main:app --reload

# Streamlit UI (http://127.0.0.1:8501)
streamlit run src/reportsmith/ui/app.py
```

### Making Changes

1. **Create feature branch**: `git checkout -b feature/your-feature-name`
2. **Make changes**: Follow coding standards
3. **Add tests**: Unit and integration tests as needed
4. **Run tests**: `pytest tests/`
5. **Format code**: `black src/ tests/ && isort src/ tests/`
6. **Lint**: `flake8 src/ tests/`
7. **Type check**: `mypy src/`
8. **Commit**: Use conventional commits format (see below)
9. **Push and create PR**

### Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat: Add new feature` - New feature
- `fix: Fix bug in SQL generator` - Bug fix
- `docs: Update README` - Documentation only
- `refactor: Restructure intent analyzer` - Code refactoring
- `test: Add tests for embedding manager` - Test changes
- `chore: Update dependencies` - Maintenance tasks
- `perf: Improve query caching` - Performance improvements

## Common Tasks & Patterns

### Adding a New LLM Provider

1. Create provider class in `query_processing/`
2. Implement common interface (e.g., `analyze()`, `generate()`)
3. Add configuration options in YAML
4. Add unit tests for the provider
5. Update documentation

### Working with Configuration

- Application configs are in `config/applications/` (YAML format)
- Entity mappings in `config/entity_mappings.yaml`
- Environment variables in `.env` file
- Use Pydantic models for configuration validation

### Debugging Tips

```bash
# View application logs
tail -f logs/app.log

# View semantic search debug output
cat logs/semantic_debug/semantic_output.json | jq .

# Enable debug logging in code
import logging
logging.getLogger("reportsmith").setLevel(logging.DEBUG)
```

## Important Guidelines

### When Generating SQL

1. **Always use parameterized queries** - Never concatenate user input
2. **Apply default filters** - Check for `is_active` or similar flags
3. **Validate table relationships** - Use the knowledge graph
4. **Handle NULL values** - Consider edge cases
5. **Test with actual database** - Verify SQL syntax for target database

### When Working with LLMs

1. **Handle rate limits** - Implement exponential backoff
2. **Log all LLM calls** - Include token counts and latency
3. **Use appropriate models** - Consider cost vs. performance
4. **Validate LLM output** - Never trust raw output without validation
5. **Provide context** - Include relevant schema information in prompts

### Performance Considerations

- **Minimize LLM calls** - Cache results when possible
- **Optimize embeddings** - Use batch operations
- **Connection pooling** - Reuse database connections
- **Query optimization** - Review generated SQL for efficiency
- **Async operations** - Use async/await for I/O operations

### Security Best Practices

1. **Never log sensitive data** - API keys, passwords, PII
2. **Validate all inputs** - Especially in SQL generation
3. **Use environment variables** - For all secrets and configuration
4. **Secure database connections** - Use SSL/TLS where possible
5. **Audit trail** - Log all query executions with user context

## Key Documentation

Before making changes, review these documents:

- **[CONTRIBUTING.md](../CONTRIBUTING.md)** - Detailed contribution guidelines
- **[README.md](../README.md)** - Project overview and quick start
- **[docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)** - System architecture
- **[docs/CURRENT_STATE.md](../docs/CURRENT_STATE.md)** - Current status and roadmap
- **[docs/DATABASE_SCHEMA.md](../docs/DATABASE_SCHEMA.md)** - Database schema details
- **[SETUP.md](../SETUP.md)** - Detailed setup instructions

## Module-Specific Guidelines

### `agents/` - LangGraph Orchestration
- Each node function should be pure (no side effects except logging)
- Update `QueryState` consistently across all nodes
- Handle errors gracefully and update state with error information
- Use type hints for all state fields

### `query_processing/` - Intent Analysis & SQL Generation
- Intent analyzer should return structured data (not free text)
- SQL generator must support multiple database dialects
- Always validate generated SQL before execution
- Include confidence scores for intent classification

### `schema_intelligence/` - Embeddings & Knowledge Graph
- Embeddings should be cached (use Redis if available)
- Knowledge graph must be loaded on startup
- Support both OpenAI and local embeddings
- Handle missing or incomplete schema gracefully

### `query_execution/` - SQL Execution Engine
- Use connection pooling
- Handle timeouts appropriately
- Format results consistently (Pandas DataFrames)
- Log all query executions with timing information

### `api/` - FastAPI Endpoints
- Use async handlers where possible
- Validate request bodies with Pydantic models
- Include proper error handling and status codes
- Document endpoints with OpenAPI docstrings

### `ui/` - Streamlit Interface
- Keep UI code separate from business logic
- Use session state for user context
- Provide clear feedback for long-running operations
- Handle errors gracefully with user-friendly messages

## Questions or Issues?

- Check existing [GitHub Issues](https://github.com/sundar-blr76/report-smith/issues)
- Review documentation in `docs/` directory
- See `CONTRIBUTING.md` for detailed guidelines
- Use GitHub Discussions for questions

---

**Last Updated**: November 2025
**Maintained By**: ReportSmith Team
