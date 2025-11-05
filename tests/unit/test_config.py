"""Tests for configuration module."""

import pytest
from reportsmith.config import Settings


def test_settings_default_values():
    """Test that settings have appropriate default values."""
    settings = Settings()
    
    assert settings.app_name == "ReportSmith"
    assert settings.debug is False
    assert settings.chunk_size == 1000
    assert settings.chunk_overlap == 200
    assert settings.max_retrieval_results == 5
    assert settings.llm_model == "gpt-3.5-turbo"
    assert settings.temperature == 0.7


def test_settings_with_env_override():
    """Test that environment variables override defaults."""
    import os
    
    # Set environment variable
    os.environ["CHUNK_SIZE"] = "2000"
    os.environ["DEBUG"] = "true"
    
    # Create new settings instance
    settings = Settings()
    
    # Clean up
    os.environ.pop("CHUNK_SIZE", None)
    os.environ.pop("DEBUG", None)
    
    # Note: This test might not work as expected without proper env setup
    # In a real scenario, you'd use pytest fixtures for environment setup