"""Pytest configuration and shared fixtures for ReportSmith tests."""

from pathlib import Path

import pytest


@pytest.fixture
def project_root():
    """
    Provide the project root directory.
    
    This fixture returns the absolute path to the project root,
    which is the parent of the tests/ directory.
    """
    return Path(__file__).parent.parent


@pytest.fixture
def sample_query():
    """Provide a sample query for testing."""
    return "Show AUM for all equity funds"


@pytest.fixture
def sample_config_path(project_root):
    """Provide path to sample configuration."""
    return project_root / "config" / "applications" / "fund_accounting"


@pytest.fixture
def mock_llm_response():
    """Provide mock LLM response for testing."""
    return {
        "intent_type": "aggregate",
        "entities": [
            {"text": "aum", "entity_type": "metric"},
            {"text": "equity", "entity_type": "dimension_value"}
        ],
        "filters": []
    }


@pytest.fixture
def sample_schema():
    """Provide sample schema structure for testing."""
    return {
        "tables": {
            "funds": {
                "description": "Fund master data",
                "columns": {
                    "fund_id": {"type": "integer", "description": "Unique identifier"},
                    "fund_name": {"type": "varchar", "description": "Fund name"},
                    "total_aum": {"type": "decimal", "description": "Assets under management"},
                    "fund_type": {"type": "varchar", "description": "Type of fund"}
                }
            }
        }
    }
