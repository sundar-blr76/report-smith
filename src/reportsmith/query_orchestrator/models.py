"""
Data models for query orchestration.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class ConfidenceLevel(str, Enum):
    """Confidence level for analysis results."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EntityType(str, Enum):
    """Type of entity identified."""
    TABLE = "table"
    COLUMN = "column"
    DIMENSION_VALUE = "dimension_value"
    METRIC = "metric"


class FilterType(str, Enum):
    """Type of filter identified."""
    EQUALITY = "equality"
    RANGE = "range"
    IN_LIST = "in_list"
    TEMPORAL = "temporal"
    PATTERN = "pattern"


class AggregationType(str, Enum):
    """Type of aggregation."""
    SUM = "sum"
    AVG = "avg"
    COUNT = "count"
    MIN = "min"
    MAX = "max"
    GROUP_BY = "group_by"


@dataclass
class ConfidenceScore:
    """Confidence score with reasoning."""
    level: ConfidenceLevel
    score: float  # 0.0 to 1.0
    reasoning: str


@dataclass
class EntityInfo:
    """Information about an identified entity."""
    name: str
    entity_type: EntityType
    table_name: Optional[str] = None
    column_name: Optional[str] = None
    description: Optional[str] = None
    relevance_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RelationshipInfo:
    """Information about a table relationship."""
    name: str
    parent_table: str
    parent_column: str
    child_table: str
    child_column: str
    relationship_type: str
    confidence: ConfidenceScore = field(default_factory=lambda: ConfidenceScore(
        level=ConfidenceLevel.HIGH,
        score=1.0,
        reasoning="Defined in schema"
    ))


@dataclass
class FilterInfo:
    """Information about a filter condition."""
    filter_type: FilterType
    column: str
    table: str
    value: Any
    operator: str
    confidence: ConfidenceScore
    original_text: Optional[str] = None


@dataclass
class ContextInfo:
    """Business context information."""
    metric_name: Optional[str] = None
    formula: Optional[str] = None
    business_rules: List[str] = field(default_factory=list)
    temporal_context: Optional[str] = None
    aggregations: List[AggregationType] = field(default_factory=list)
    grouping_columns: List[str] = field(default_factory=list)


@dataclass
class NavigationPath:
    """Path through the entity graph."""
    tables: List[str]
    relationships: List[RelationshipInfo]
    joins: List[str] = field(default_factory=list)
    confidence: ConfidenceScore = field(default_factory=lambda: ConfidenceScore(
        level=ConfidenceLevel.HIGH,
        score=1.0,
        reasoning="Direct path found"
    ))


@dataclass
class QueryAnalysisResult:
    """Complete result of query analysis."""
    user_query: str
    entities: List[EntityInfo]
    relationships: List[RelationshipInfo]
    filters: List[FilterInfo]
    context: ContextInfo
    navigation_paths: List[NavigationPath]
    confidence: ConfidenceScore
    refinement_suggestions: List[str] = field(default_factory=list)
    iteration_count: int = 0


@dataclass
class QueryPlan:
    """Execution plan for the query."""
    analysis: QueryAnalysisResult
    primary_table: str
    required_tables: List[str]
    selected_columns: List[str]
    join_clauses: List[str]
    where_clauses: List[str]
    group_by_clauses: List[str]
    order_by_clauses: List[str]
    limit_clause: Optional[str] = None
    sql_query: Optional[str] = None
    confidence: ConfidenceScore = field(default_factory=lambda: ConfidenceScore(
        level=ConfidenceLevel.MEDIUM,
        score=0.7,
        reasoning="Initial plan generated"
    ))
    estimated_rows: Optional[int] = None
    execution_metadata: Dict[str, Any] = field(default_factory=dict)
