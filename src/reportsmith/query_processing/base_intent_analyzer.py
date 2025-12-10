"""
Base classes and common structures for Intent Analysis.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import abc

class IntentType(str, Enum):
    """Types of query intents."""
    RETRIEVAL = "retrieval"
    AGGREGATION = "aggregation"
    FILTERING = "filtering"
    COMPARISON = "comparison"
    RANKING = "ranking"
    TREND = "trend"


class TimeScope(str, Enum):
    """Time-based scopes for queries."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    YTD = "year_to_date"
    MTD = "month_to_date"
    LAST_MONTH = "last_month"
    LAST_QUARTER = "last_quarter"
    LAST_YEAR = "last_year"
    CUSTOM = "custom"
    NONE = "none"


class AggregationType(str, Enum):
    """Types of aggregations."""
    SUM = "sum"
    COUNT = "count"
    AVERAGE = "avg"
    MIN = "min"
    MAX = "max"
    DISTINCT_COUNT = "count_distinct"


@dataclass
class EnrichedEntity:
    """
    Entity enriched with metadata, mappings, and semantic search results.
    Unified structure to support both LLM and Local/Hybrid workflows.
    """
    text: str
    entity_type: str
    canonical_name: Optional[str] = None
    table: Optional[str] = None
    column: Optional[str] = None
    value: Optional[str] = None
    source: str = "llm"  # "local", "llm", "semantic"
    confidence: float = 0.0
    semantic_matches: List[Dict[str, Any]] = field(default_factory=list)
    local_mapping: Optional[Any] = None # Stores LocalEntityMapping object if available
    
    def __str__(self):
        source_emoji = {"local": "📌", "llm": "🤖", "semantic": "🔍"}.get(self.source, "❓")
        parts = [f"{source_emoji} {self.text}"]
        if self.canonical_name and self.canonical_name != self.text:
            parts.append(f"→ {self.canonical_name}")
        parts.append(f"({self.entity_type}, conf: {self.confidence:.2f})")
        return " ".join(parts)


@dataclass
class BaseQueryIntent:
    """Base class for query intent results."""
    original_query: str
    intent_type: IntentType
    entities: List[EnrichedEntity]
    time_scope: TimeScope
    aggregations: List[AggregationType]
    filters: List[str]
    limit: Optional[int]
    order_by: Optional[str]
    order_direction: str
    llm_reasoning: Optional[str] = None
    
    def __str__(self) -> str:
        parts = [
            f"Query: {self.original_query}",
            f"Intent: {self.intent_type.value}",
            f"Time Scope: {self.time_scope.value}",
        ]
        
        if self.entities:
            parts.append(f"\nEntities ({len(self.entities)}):")
            for entity in self.entities:
                parts.append(f"  {entity}")
        
        if self.aggregations:
            parts.append(f"\nAggregations: {', '.join([a.value for a in self.aggregations])}")
        
        if self.filters:
            parts.append(f"Filters: {', '.join(self.filters)}")
        
        if self.llm_reasoning:
            parts.append(f"\nReasoning: {self.llm_reasoning}")
        
        return "\n".join(parts)


class BaseIntentAnalyzer(abc.ABC):
    """Abstract base class for intent analyzers."""
    
    @abc.abstractmethod
    def analyze(self, query: str) -> BaseQueryIntent:
        """Analyze a natural language query."""
        pass
