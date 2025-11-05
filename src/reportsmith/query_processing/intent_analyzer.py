"""
Query Intent Analyzer for ReportSmith

Analyzes natural language queries to extract:
- Intent type (retrieval, aggregation, filtering, comparison)
- Entities (funds, clients, dates, metrics)
- Time scope (daily, monthly, yearly)
- Aggregations (sum, count, average)
- Filters and conditions
"""

from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import re
from datetime import datetime

from ..logger import get_logger
from ..schema_intelligence.embedding_manager import EmbeddingManager

logger = get_logger(__name__)


class IntentType(Enum):
    """Types of query intents."""
    RETRIEVAL = "retrieval"  # Get raw data
    AGGREGATION = "aggregation"  # Sum, count, average
    FILTERING = "filtering"  # Filter by conditions
    COMPARISON = "comparison"  # Compare across dimensions
    RANKING = "ranking"  # Top N, bottom N
    TREND = "trend"  # Time-based analysis


class TimeScope(Enum):
    """Time-based scopes for queries."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    YTD = "year_to_date"
    MTD = "month_to_date"
    CUSTOM = "custom"
    NONE = "none"


class AggregationType(Enum):
    """Types of aggregations."""
    SUM = "sum"
    COUNT = "count"
    AVERAGE = "avg"
    MIN = "min"
    MAX = "max"
    DISTINCT_COUNT = "count_distinct"


@dataclass
class ExtractedEntity:
    """An entity extracted from the query."""
    text: str  # Original text from query
    entity_type: str  # Type: table, column, domain_value, metric
    semantic_matches: List[Dict[str, Any]] = field(default_factory=list)  # Matches from embedding search
    confidence: float = 0.0  # Confidence score 0-1


@dataclass
class QueryIntent:
    """Parsed intent from a natural language query."""
    original_query: str
    intent_type: IntentType
    entities: List[ExtractedEntity] = field(default_factory=list)
    time_scope: TimeScope = TimeScope.NONE
    aggregations: List[AggregationType] = field(default_factory=list)
    filters: List[str] = field(default_factory=list)
    limit: Optional[int] = None
    order_by: Optional[str] = None
    order_direction: str = "ASC"
    
    def __str__(self) -> str:
        """String representation of query intent."""
        parts = [
            f"Query: {self.original_query}",
            f"Intent: {self.intent_type.value}",
            f"Time Scope: {self.time_scope.value}",
        ]
        
        if self.entities:
            parts.append(f"Entities ({len(self.entities)}):")
            for entity in self.entities:
                parts.append(f"  - {entity.text} ({entity.entity_type}, confidence: {entity.confidence:.2f})")
        
        if self.aggregations:
            agg_str = ", ".join([agg.value for agg in self.aggregations])
            parts.append(f"Aggregations: {agg_str}")
        
        if self.filters:
            parts.append(f"Filters: {', '.join(self.filters)}")
        
        if self.limit:
            parts.append(f"Limit: {self.limit}")
            
        return "\n".join(parts)


class QueryIntentAnalyzer:
    """
    Analyzes natural language queries to extract intent and entities.
    
    Uses pattern matching combined with semantic search via embeddings
    to understand what the user wants.
    """
    
    # Intent patterns
    INTENT_PATTERNS = {
        IntentType.RETRIEVAL: [
            r'\b(show|display|list|get|find|retrieve)\b',
            r'\b(what|which)\b.*\?',
        ],
        IntentType.AGGREGATION: [
            r'\b(total|sum|average|mean|count)\b',
            r'\b(how much|how many)\b',
        ],
        IntentType.COMPARISON: [
            r'\b(compare|versus|vs|difference between)\b',
            r'\b(higher|lower|more|less than)\b',
        ],
        IntentType.RANKING: [
            r'\b(top|bottom|best|worst)\s+\d+',
            r'\b(highest|lowest|largest|smallest)\b',
        ],
        IntentType.TREND: [
            r'\b(trend|over time|historical|growth)\b',
            r'\b(month over month|year over year)\b',
        ],
    }
    
    # Time scope patterns
    TIME_PATTERNS = {
        TimeScope.DAILY: [r'\b(daily|per day|each day)\b'],
        TimeScope.WEEKLY: [r'\b(weekly|per week|each week)\b'],
        TimeScope.MONTHLY: [r'\b(monthly|per month|each month)\b'],
        TimeScope.QUARTERLY: [r'\b(quarterly|per quarter|each quarter)\b'],
        TimeScope.YEARLY: [r'\b(yearly|annual|per year|each year)\b'],
        TimeScope.YTD: [r'\b(year to date|ytd)\b'],
        TimeScope.MTD: [r'\b(month to date|mtd)\b'],
    }
    
    # Aggregation patterns
    AGGREGATION_PATTERNS = {
        AggregationType.SUM: [r'\b(sum|total|aggregate)\b'],
        AggregationType.COUNT: [r'\b(count|number of|how many)\b'],
        AggregationType.AVERAGE: [r'\b(average|mean|avg)\b'],
        AggregationType.MIN: [r'\b(minimum|min|lowest|smallest)\b'],
        AggregationType.MAX: [r'\b(maximum|max|highest|largest)\b'],
        AggregationType.DISTINCT_COUNT: [r'\b(unique|distinct)\b'],
    }
    
    # Common financial entities to look for
    COMMON_ENTITIES = {
        'fund_types': ['equity', 'bond', 'balanced', 'money market', 'index', 'growth', 'value'],
        'metrics': ['fee', 'aum', 'nav', 'return', 'performance', 'balance', 'position', 'transaction'],
        'time_periods': ['daily', 'weekly', 'monthly', 'quarterly', 'yearly', 'ytd', 'mtd'],
        'clients': ['client', 'customer', 'investor', 'account holder'],
        'companies': ['management company', 'fund manager', 'company'],
    }
    
    def __init__(self, embedding_manager: EmbeddingManager):
        """
        Initialize query intent analyzer.
        
        Args:
            embedding_manager: Embedding manager for semantic search
        """
        self.embedding_manager = embedding_manager
        logger.info("Initialized QueryIntentAnalyzer")
    
    def analyze(self, query: str) -> QueryIntent:
        """
        Analyze a natural language query to extract intent.
        
        Args:
            query: Natural language query
            
        Returns:
            QueryIntent with extracted information
        """
        logger.info(f"Analyzing query: {query}")
        
        # Normalize query
        normalized_query = query.lower().strip()
        
        # Extract intent type
        intent_type = self._classify_intent(normalized_query)
        
        # Extract entities using semantic search
        entities = self._extract_entities(normalized_query)
        
        # Extract time scope
        time_scope = self._extract_time_scope(normalized_query)
        
        # Extract aggregations
        aggregations = self._extract_aggregations(normalized_query)
        
        # Extract filters
        filters = self._extract_filters(normalized_query)
        
        # Extract limit and ordering
        limit, order_by, order_direction = self._extract_ordering(normalized_query)
        
        intent = QueryIntent(
            original_query=query,
            intent_type=intent_type,
            entities=entities,
            time_scope=time_scope,
            aggregations=aggregations,
            filters=filters,
            limit=limit,
            order_by=order_by,
            order_direction=order_direction
        )
        
        logger.info(f"Extracted intent: {intent_type.value}, {len(entities)} entities, {time_scope.value} time scope")
        return intent
    
    def _classify_intent(self, query: str) -> IntentType:
        """Classify the primary intent of the query."""
        intent_scores = {}
        
        for intent_type, patterns in self.INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    score += 1
            intent_scores[intent_type] = score
        
        # Return intent with highest score, default to RETRIEVAL
        if intent_scores:
            max_score = max(intent_scores.values())
            if max_score > 0:
                return max(intent_scores, key=intent_scores.get)
        
        return IntentType.RETRIEVAL
    
    def _extract_entities(self, query: str) -> List[ExtractedEntity]:
        """
        Extract entities from query using semantic search.
        
        Uses embedding manager to find relevant:
        - Tables
        - Columns
        - Dimension values
        """
        entities = []
        
        # Search schema metadata
        schema_results = self.embedding_manager.search_schema(query, top_k=5)
        for result in schema_results:
            if result.score > 0.3:  # Threshold for relevance
                entity_type = result.metadata.get('type', 'unknown')
                entities.append(ExtractedEntity(
                    text=result.content,
                    entity_type=entity_type,
                    semantic_matches=[{
                        'content': result.content,
                        'metadata': result.metadata,
                        'score': result.score
                    }],
                    confidence=result.score
                ))
        
        # Search domain values
        dimension_results = self.embedding_manager.search_domains(query, top_k=5)
        for result in dimension_results:
            if result.score > 0.3:
                entities.append(ExtractedEntity(
                    text=result.content,
                    entity_type='domain_value',
                    semantic_matches=[{
                        'content': result.content,
                        'metadata': result.metadata,
                        'score': result.score
                    }],
                    confidence=result.score
                ))
        
        # Search business context
        context_results = self.embedding_manager.search_business_context(query, top_k=3)
        for result in context_results:
            if result.score > 0.4:  # Higher threshold for context
                entities.append(ExtractedEntity(
                    text=result.content,
                    entity_type='business_context',
                    semantic_matches=[{
                        'content': result.content,
                        'metadata': result.metadata,
                        'score': result.score
                    }],
                    confidence=result.score
                ))
        
        # Sort by confidence
        entities.sort(key=lambda x: x.confidence, reverse=True)
        
        return entities
    
    def _extract_time_scope(self, query: str) -> TimeScope:
        """Extract time scope from query."""
        for time_scope, patterns in self.TIME_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    return time_scope
        return TimeScope.NONE
    
    def _extract_aggregations(self, query: str) -> List[AggregationType]:
        """Extract aggregation types from query."""
        aggregations = []
        
        for agg_type, patterns in self.AGGREGATION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    if agg_type not in aggregations:
                        aggregations.append(agg_type)
                    break
        
        return aggregations
    
    def _extract_filters(self, query: str) -> List[str]:
        """Extract filter conditions from query."""
        filters = []
        
        # Look for common filter patterns
        # "for X", "where X", "with X"
        filter_patterns = [
            r'\bfor\s+([^,]+?)(?:\s+and|\s+or|\s*,|\s*$)',
            r'\bwhere\s+([^,]+?)(?:\s+and|\s+or|\s*,|\s*$)',
            r'\bwith\s+([^,]+?)(?:\s+and|\s+or|\s*,|\s*$)',
        ]
        
        for pattern in filter_patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                filter_text = match.group(1).strip()
                if filter_text and filter_text not in filters:
                    filters.append(filter_text)
        
        return filters
    
    def _extract_ordering(self, query: str) -> tuple[Optional[int], Optional[str], str]:
        """Extract limit, order by, and direction from query."""
        limit = None
        order_by = None
        order_direction = "ASC"
        
        # Extract limit (top N, first N, limit N)
        limit_patterns = [
            r'\b(?:top|first)\s+(\d+)\b',
            r'\blimit\s+(\d+)\b',
        ]
        
        for pattern in limit_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                limit = int(match.group(1))
                break
        
        # Extract ordering direction
        if re.search(r'\b(descending|desc|highest|largest|most)\b', query, re.IGNORECASE):
            order_direction = "DESC"
        elif re.search(r'\b(ascending|asc|lowest|smallest|least)\b', query, re.IGNORECASE):
            order_direction = "ASC"
        
        # Order by is typically inferred from the query context
        # This will be refined in the schema mapping phase
        
        return limit, order_by, order_direction


# Example usage patterns for testing
EXAMPLE_QUERIES = [
    "Show monthly fees for all TruePotential equity funds",
    "What is the total AUM for bond funds?",
    "List top 10 clients by account balance",
    "Compare performance of equity vs bond funds",
    "Show daily transactions for account 12345",
    "What are the average fees by fund type?",
    "Find all high risk funds with AUM over 100M",
]
