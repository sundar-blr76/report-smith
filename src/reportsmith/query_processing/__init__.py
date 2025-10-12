"""Query Processing Module for ReportSmith."""

from .intent_analyzer import (
    QueryIntentAnalyzer,
    QueryIntent,
    IntentType,
    TimeScope,
    AggregationType,
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
    # Pattern-based (fallback)
    'QueryIntentAnalyzer',
    'QueryIntent',
    'IntentType',
    'TimeScope',
    'AggregationType',
    'ExtractedEntity',
    
    # LLM-based
    'LLMIntentAnalyzer',
    'LLMQueryIntent',
    
    # Hybrid (recommended - combines all approaches)
    'HybridIntentAnalyzer',
    'HybridQueryIntent',
    'LocalEntityMapping',
    'EntityMappingConfig',
]
