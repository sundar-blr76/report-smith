#!/usr/bin/env python3
"""
Test script to verify percentage-based filter handling.
"""
import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from reportsmith.query_processing.llm_intent_analyzer import LLMIntentAnalyzer
from reportsmith.schema_intelligence.embedding_manager import EmbeddingManager
from reportsmith.config_system.config_loader import ConfigLoader
from reportsmith.logger import get_logger

logger = get_logger(__name__)

def test_percentage_filter():
    """Test that percentage-based filters are correctly extracted."""
    
    # Load config
    config_path = "config/applications/fund_accounting/app.yaml"
    config_loader = ConfigLoader()
    app_config = config_loader.load_app_config(config_path)
    
    # Initialize embedding manager
    embedding_manager = EmbeddingManager(
        app_config=app_config,
        embedding_provider="openai"
    )
    
    # Initialize LLM intent analyzer
    analyzer = LLMIntentAnalyzer(
        embedding_manager=embedding_manager,
        llm_provider="openai"
    )
    
    # Test query
    query = "Show clients with holdings where unrealized gains exceed 20%"
    
    logger.info(f"Testing query: {query}")
    logger.info("=" * 80)
    
    # Analyze the query
    intent = analyzer.analyze(query)
    
    # Check the results
    logger.info("\nExtracted Intent:")
    logger.info(f"  Type: {intent.intent_type.value}")
    logger.info(f"  Filters: {intent.filters}")
    logger.info(f"  Entities: {[e.text for e in intent.entities]}")
    
    # Validate filters
    if not intent.filters:
        logger.error("❌ FAIL: No filters extracted!")
        return False
    
    # Check if percentage-based filter is present
    has_percentage_filter = any(
        "unrealized_gain_loss" in f and ("/" in f or ">" in f or "0.2" in f or "20" in f)
        for f in intent.filters
    )
    
    if has_percentage_filter:
        logger.info("✅ PASS: Percentage-based filter detected!")
        logger.info(f"   Filter: {intent.filters}")
        return True
    else:
        logger.error("❌ FAIL: Percentage-based filter not detected correctly!")
        logger.error(f"   Got filters: {intent.filters}")
        return False

if __name__ == "__main__":
    try:
        success = test_percentage_filter()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Test failed with exception: {e}", exc_info=True)
        sys.exit(1)
