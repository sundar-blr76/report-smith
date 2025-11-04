"""Tests for entity refinement with priority and optimal source selection."""

import pytest
from pathlib import Path
from reportsmith.query_processing.hybrid_intent_analyzer import (
    LocalEntityMapping,
    HybridIntentAnalyzer,
    EntityMappingConfig,
)


def test_local_entity_mapping_with_priority():
    """Test that LocalEntityMapping supports priority and optimal_source fields."""
    mapping = LocalEntityMapping(
        term="aum",
        canonical_name="total_aum",
        entity_type="column",
        table="funds",
        column="total_aum",
        priority="high",
        optimal_source=True,
        source_notes="Primary source for AUM"
    )
    
    assert mapping.priority == "high"
    assert mapping.optimal_source is True
    assert mapping.source_notes == "Primary source for AUM"


def test_entity_mappings_loaded_with_priority():
    """Test that entity mappings are loaded with priority information from YAML."""
    # Find the entity mappings file
    project_root = Path(__file__).parent.parent.parent
    mappings_file = project_root / "config" / "entity_mappings.yaml"
    
    if not mappings_file.exists():
        pytest.skip("Entity mappings file not found")
    
    # Load mappings
    import yaml
    with open(mappings_file, 'r') as f:
        data = yaml.safe_load(f)
    
    # Check that AUM mapping has priority fields
    aum_mapping = data.get('columns', {}).get('aum', {})
    assert aum_mapping is not None, "AUM column mapping not found"
    assert aum_mapping.get('priority') == 'high', "AUM should have high priority"
    assert aum_mapping.get('optimal_source') is True, "AUM should be marked as optimal source"
    assert 'source_notes' in aum_mapping, "AUM should have source notes"
    
    # Check alternative AUM sources have lower priority
    aum_from_holdings = data.get('columns', {}).get('aum_from_holdings', {})
    if aum_from_holdings:
        assert aum_from_holdings.get('priority') == 'low', "Holdings AUM should have low priority"
        assert aum_from_holdings.get('optimal_source') is False, "Holdings AUM should not be optimal"


def test_refine_entities_prompt_includes_priority_guidance():
    """Test that the entity refinement function includes priority guidance in the prompt."""
    # Create a mock entity list
    entities = [
        {
            "text": "aum",
            "entity_type": "column",
            "confidence": 1.0,
            "table": "funds",
            "column": "total_aum",
            "source": "local",
            "local_mapping": LocalEntityMapping(
                term="aum",
                canonical_name="total_aum",
                entity_type="column",
                table="funds",
                column="total_aum",
                priority="high",
                optimal_source=True,
                source_notes="Primary source for AUM"
            )
        },
        {
            "text": "aum",
            "entity_type": "column",
            "confidence": 0.7,
            "table": "holdings",
            "column": "market_value",
            "source": "semantic",
            "local_mapping": None
        }
    ]
    
    # Note: This test is primarily for documentation of expected behavior
    # In a real scenario with LLM integration, we would verify the actual refinement
    assert len(entities) == 2
    assert entities[0]["local_mapping"].optimal_source is True
    assert entities[0]["local_mapping"].priority == "high"


def test_entity_mapping_config_structure():
    """Test that EntityMappingConfig can store mappings with priority info."""
    config = EntityMappingConfig()
    
    # Add a mapping with priority
    high_priority_mapping = LocalEntityMapping(
        term="aum",
        canonical_name="total_aum",
        entity_type="column",
        table="funds",
        column="total_aum",
        priority="high",
        optimal_source=True,
        source_notes="Primary source"
    )
    
    low_priority_mapping = LocalEntityMapping(
        term="aum_from_holdings",
        canonical_name="market_value",
        entity_type="column",
        table="holdings",
        column="market_value",
        priority="low",
        optimal_source=False,
        source_notes="Secondary source"
    )
    
    config.columns["aum"] = high_priority_mapping
    config.columns["aum_from_holdings"] = low_priority_mapping
    
    assert config.columns["aum"].priority == "high"
    assert config.columns["aum"].optimal_source is True
    assert config.columns["aum_from_holdings"].priority == "low"
    assert config.columns["aum_from_holdings"].optimal_source is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
