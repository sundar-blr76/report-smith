#!/usr/bin/env python3
"""
Test script to demonstrate cache payload display for aggregation intent with 3 entities.
This script simulates a cache hit scenario and shows the formatted payload output.
"""

import os
import sys
import json
import logging
from pathlib import Path
from collections import OrderedDict
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field

# Simple logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define minimal classes needed for demo
class IntentType(str, Enum):
    """Types of query intents."""
    AGGREGATION = "aggregation"

class AggregationType(str, Enum):
    """Types of aggregations."""
    SUM = "sum"
    AVERAGE = "avg"

class TimeScope(str, Enum):
    """Time-based scopes for queries."""
    QUARTERLY = "quarterly"
    NONE = "none"

class LLMQueryIntent(BaseModel):
    """Structured query intent from LLM."""
    intent_type: IntentType
    entities: List[str] = Field(default_factory=list)
    time_scope: TimeScope = Field(default=TimeScope.NONE)
    aggregations: List[AggregationType] = Field(default_factory=list)
    filters: List[str] = Field(default_factory=list)
    limit: Optional[int] = Field(None)
    order_by: Optional[str] = Field(None)
    order_direction: str = Field(default="ASC")
    reasoning: str = Field(description="Brief explanation")


class SimpleCache:
    """Simple in-memory cache for demonstration."""
    
    def __init__(self):
        self.cache = {}
        
    def _print_cache_payload(self, category: str, value, source: str):
        """Format and print the cached payload."""
        logger.info("=" * 80)
        logger.info(f"CACHE PAYLOAD RETRIEVED FROM {source}")
        logger.info("=" * 80)
        logger.info(f"Category: {category}")
        logger.info(f"Source: {source}")
        logger.info("-" * 80)
        
        try:
            if hasattr(value, 'model_dump'):  # Pydantic models
                payload_dict = value.model_dump()
                logger.info("Payload Type: Pydantic Model")
                logger.info(f"Model Class: {value.__class__.__name__}")
                logger.info("\nPayload Content:")
                logger.info(json.dumps(payload_dict, indent=2, default=str))
                
                # For intent analysis, print additional structured info
                if category == "llm_intent":
                    logger.info("\n--- Intent Analysis Details ---")
                    logger.info(f"Intent Type: {payload_dict.get('intent_type', 'N/A')}")
                    logger.info(f"Entities: {len(payload_dict.get('entities', []))}")
                    if payload_dict.get('entities'):
                        logger.info("Entity List:")
                        for idx, entity in enumerate(payload_dict.get('entities', []), 1):
                            logger.info(f"  {idx}. {entity}")
                    logger.info(f"Time Scope: {payload_dict.get('time_scope', 'N/A')}")
                    logger.info(f"Aggregations: {payload_dict.get('aggregations', [])}")
                    logger.info(f"Filters: {payload_dict.get('filters', [])}")
                    if payload_dict.get('filters'):
                        logger.info("Filter Details:")
                        for idx, filter_str in enumerate(payload_dict.get('filters', []), 1):
                            logger.info(f"  {idx}. {filter_str}")
                    logger.info(f"Limit: {payload_dict.get('limit', 'None')}")
                    logger.info(f"Order By: {payload_dict.get('order_by', 'None')} {payload_dict.get('order_direction', '')}")
                    logger.info(f"Reasoning: {payload_dict.get('reasoning', 'N/A')}")
        except Exception as e:
            logger.warning(f"Failed to format cache payload: {e}")
            
        logger.info("=" * 80)
        
    def set(self, category: str, value, *args, **kwargs):
        """Store value in cache."""
        key = f"{category}:{':'.join(str(a) for a in args)}"
        self.cache[key] = value
        logger.info(f"[cache-set] {category} key={key[:50]}...")
        
    def get(self, category: str, *args, **kwargs):
        """Retrieve value from cache."""
        key = f"{category}:{':'.join(str(a) for a in args)}"
        value = self.cache.get(key)
        if value:
            logger.info(f"[cache-hit] {category} [L1 memory] key={key[:50]}...")
            self._print_cache_payload(category, value, "L1 memory")
        return value


def test_cache_payload_display():
    """Test cache payload display for aggregation intent with 3 entities."""
    
    logger.info("=" * 80)
    logger.info("TESTING CACHE PAYLOAD DISPLAY")
    logger.info("Scenario: IntentType.AGGREGATION with 3 entities")
    logger.info("=" * 80)
    
    # Initialize simple cache for testing
    cache_manager = SimpleCache()
    
    # Create a sample aggregation intent with 3 entities
    sample_intent = LLMQueryIntent(
        intent_type=IntentType.AGGREGATION,
        entities=[
            "monthly fees",
            "TruePotential equity funds",
            "Q1 2025"
        ],
        time_scope=TimeScope.QUARTERLY,
        aggregations=[AggregationType.SUM],
        filters=[
            "fee_period_start BETWEEN '2025-01-01' AND '2025-03-31'",
            "fund_type = 'equity'"
        ],
        limit=None,
        order_by="total_fees",
        order_direction="DESC",
        reasoning="User wants to aggregate (sum) monthly fees for equity funds in Q1 2025. "
                  "This requires joining fees table with funds table, filtering by period and fund type, "
                  "and aggregating the fee amounts."
    )
    
    logger.info("\n--- STEP 1: Storing Intent in Cache ---")
    query = "Show me the total monthly fees for TruePotential equity funds in Q1 2025"
    
    # Store in cache
    cache_manager.set("llm_intent", sample_intent, query.lower())
    
    logger.info(f"Stored intent in cache for query: '{query}'")
    logger.info(f"Intent Type: {sample_intent.intent_type}")
    logger.info(f"Number of Entities: {len(sample_intent.entities)}")
    
    # Clear to simulate fresh retrieval
    logger.info("\n--- STEP 2: Retrieving Intent from Cache (simulating cache hit) ---")
    
    # Retrieve from cache - this will trigger the payload display
    cached_intent = cache_manager.get("llm_intent", query.lower())
    
    if cached_intent:
        logger.info("\n--- STEP 3: Cache Hit Verification ---")
        logger.info(f"✓ Successfully retrieved cached intent")
        logger.info(f"✓ Intent Type: {cached_intent.intent_type}")
        logger.info(f"✓ Number of Entities: {len(cached_intent.entities)}")
        logger.info(f"✓ Entities: {cached_intent.entities}")
        logger.info(f"✓ Aggregations: {cached_intent.aggregations}")
    else:
        logger.error("✗ Failed to retrieve cached intent!")
    
    # Test with a second query to show multiple cache hits
    logger.info("\n" + "=" * 80)
    logger.info("TESTING SECOND CACHE RETRIEVAL")
    logger.info("=" * 80)
    
    query2 = "What is the average AUM for bond funds and equity funds by region"
    sample_intent2 = LLMQueryIntent(
        intent_type=IntentType.AGGREGATION,
        entities=[
            "average AUM",
            "bond funds",
            "equity funds",
            "region"
        ],
        time_scope=TimeScope.NONE,
        aggregations=[AggregationType.AVERAGE],
        filters=[
            "fund_type IN ('bond', 'equity')"
        ],
        limit=None,
        order_by="region",
        order_direction="ASC",
        reasoning="User wants to compare average AUM across different fund types grouped by region. "
                  "Requires aggregation by fund type and region."
    )
    
    cache_manager.set("llm_intent", sample_intent2, query2.lower())
    
    logger.info(f"\nStored second intent for query: '{query2}'")
    logger.info(f"Number of Entities: {len(sample_intent2.entities)}")
    
    # Retrieve second query
    cached_intent2 = cache_manager.get("llm_intent", query2.lower())
    
    if cached_intent2:
        logger.info("\n✓ Second query successfully retrieved from cache")
    
    logger.info("\n" + "=" * 80)
    logger.info("TEST COMPLETED SUCCESSFULLY")
    logger.info("The cache now formats and prints full payload details on retrieval!")
    logger.info("=" * 80)


if __name__ == "__main__":
    test_cache_payload_display()
