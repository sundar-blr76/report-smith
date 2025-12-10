"""Query Processing Module for ReportSmith."""

from .base_intent_analyzer import (
    BaseIntentAnalyzer,
    BaseQueryIntent,
    IntentType,
    TimeScope,
    AggregationType,
    EnrichedEntity,
)

from .intent_analyzer import (
    QueryIntentAnalyzer,
    QueryIntent,
    ExtractedEntity,
)

from .llm_intent_analyzer import (
    LLMIntentAnalyzer,
    LLMQueryIntent,
)

from .hybrid_intent_analyzer import (
    HybridIntentAnalyzer,
    HybridQueryIntent,
    LocalEntityMapping,
    EntityMappingConfig,
)

__all__ = [
    # Base types (New)
    'BaseIntentAnalyzer',
    'BaseQueryIntent',
    'IntentType',
    'TimeScope',
    'AggregationType',
    'EnrichedEntity',

    # Pattern-based (Legacy)
    'QueryIntentAnalyzer',
    'QueryIntent',
    'ExtractedEntity',
    
    # LLM-based
    'LLMIntentAnalyzer',
    'LLMQueryIntent',
    
    # Hybrid (Recommended)
    'HybridIntentAnalyzer',
    'HybridQueryIntent',
    'LocalEntityMapping',
    'EntityMappingConfig',
]
