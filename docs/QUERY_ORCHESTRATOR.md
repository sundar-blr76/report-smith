# Query Orchestrator - LangChain-Based Query Analysis

## Overview

The Query Orchestrator is a LangChain-based system that performs comprehensive analysis of natural language queries for report extraction. It uses a set of MCP (Model Context Protocol) tools to:

1. **Identify entities** - tables, columns, and dimension values
2. **Discover relationships** - how tables connect via foreign keys
3. **Extract context** - business metrics, aggregations, and temporal information
4. **Identify filters** - WHERE clause conditions
5. **Navigate graphs** - find optimal paths through entity relationships
6. **Validate results** - cross-check against user query
7. **Generate SQL** - produce executable query plans

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     QUERY ORCHESTRATOR                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  1. ENTITY IDENTIFICATION TOOL                           │  │
│  │  • Semantic search on schema metadata                    │  │
│  │  • Dimension value matching                              │  │
│  │  • Relevance scoring                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          ↓                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  2. RELATIONSHIP DISCOVERY TOOL                          │  │
│  │  • Load relationships from app.yaml                      │  │
│  │  • Filter to relevant tables                             │  │
│  │  • Return join information                               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          ↓                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  3. CONTEXT EXTRACTION TOOL                              │  │
│  │  • Search business context embeddings                    │  │
│  │  • Identify aggregations (SUM, AVG, COUNT)               │  │
│  │  • Extract temporal context                              │  │
│  │  • Identify grouping requirements                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          ↓                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  4. FILTER IDENTIFICATION TOOL                           │  │
│  │  • Match dimension values to filters                     │  │
│  │  • Identify temporal filters                             │  │
│  │  • Extract range/equality conditions                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          ↓                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  5. GRAPH NAVIGATION TOOL                                │  │
│  │  • Build relationship graph                              │  │
│  │  • Find shortest paths between tables                    │  │
│  │  • Generate JOIN clauses                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          ↓                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  6. VALIDATION & REFINEMENT                              │  │
│  │  • Cross-check against user query                        │  │
│  │  • Confidence scoring                                    │  │
│  │  • Iterative refinement (up to 3 iterations)             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          ↓                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  7. SQL QUERY GENERATION                                 │  │
│  │  • SELECT clause generation                              │  │
│  │  • JOIN clause generation                                │  │
│  │  • WHERE clause generation                               │  │
│  │  • GROUP BY, ORDER BY, LIMIT                             │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. QueryOrchestrator

Main orchestrator class that coordinates all MCP tools.

**Methods:**
- `analyze_query(user_query)` - Analyze natural language query
- `generate_query_plan(analysis)` - Generate SQL query plan
- `validate_and_refine(plan)` - Validate and refine plan

**Features:**
- Iterative refinement (max 3 iterations)
- Confidence-based stopping
- Automatic refinement suggestions

### 2. MCP Tools

#### EntityIdentificationTool
Identifies entities from natural language using semantic search.

**Input:** Natural language query  
**Output:** List of EntityInfo with relevance scores

**Process:**
1. Search schema metadata embeddings
2. Search dimension value embeddings
3. Rank by relevance score
4. Return top K entities

#### RelationshipDiscoveryTool
Discovers relationships between identified tables.

**Input:** List of table names  
**Output:** List of RelationshipInfo

**Process:**
1. Load relationships from app.yaml
2. Filter to tables in the query
3. Return parent-child relationships with join info

#### ContextExtractionTool
Extracts business context and identifies metrics.

**Input:** Query string and identified entities  
**Output:** ContextInfo with metrics, aggregations, temporal context

**Process:**
1. Search business context embeddings
2. Identify aggregation keywords (sum, avg, count)
3. Extract temporal phrases (last, previous, current)
4. Identify grouping requirements

#### FilterIdentificationTool
Identifies filter conditions from natural language.

**Input:** Query string and identified entities  
**Output:** List of FilterInfo

**Process:**
1. Match dimension values to filters
2. Identify temporal filters (date ranges)
3. Extract range conditions (top, bottom)
4. Return confidence-scored filters

#### GraphNavigationTool
Navigates the entity relationship graph to find join paths.

**Input:** Start tables, target tables, relationships  
**Output:** List of NavigationPath

**Process:**
1. Build adjacency graph from relationships
2. Use BFS to find all paths
3. Limit to max_hops (default: 3)
4. Score paths by length (shorter is better)
5. Generate JOIN clauses

### 3. Data Models

#### EntityInfo
Represents an identified entity (table, column, or dimension value).

```python
@dataclass
class EntityInfo:
    name: str
    entity_type: EntityType  # TABLE, COLUMN, DIMENSION_VALUE, METRIC
    table_name: Optional[str]
    column_name: Optional[str]
    description: Optional[str]
    relevance_score: float
    metadata: Dict[str, Any]
```

#### RelationshipInfo
Represents a relationship between tables.

```python
@dataclass
class RelationshipInfo:
    name: str
    parent_table: str
    parent_column: str
    child_table: str
    child_column: str
    relationship_type: str  # one_to_many, many_to_one, many_to_many
    confidence: ConfidenceScore
```

#### FilterInfo
Represents a filter condition.

```python
@dataclass
class FilterInfo:
    filter_type: FilterType  # EQUALITY, RANGE, IN_LIST, TEMPORAL, PATTERN
    column: str
    table: str
    value: Any
    operator: str
    confidence: ConfidenceScore
    original_text: Optional[str]
```

#### ContextInfo
Represents business context.

```python
@dataclass
class ContextInfo:
    metric_name: Optional[str]
    formula: Optional[str]
    business_rules: List[str]
    temporal_context: Optional[str]
    aggregations: List[AggregationType]
    grouping_columns: List[str]
```

#### QueryAnalysisResult
Complete result of query analysis.

```python
@dataclass
class QueryAnalysisResult:
    user_query: str
    entities: List[EntityInfo]
    relationships: List[RelationshipInfo]
    filters: List[FilterInfo]
    context: ContextInfo
    navigation_paths: List[NavigationPath]
    confidence: ConfidenceScore
    refinement_suggestions: List[str]
    iteration_count: int
```

#### QueryPlan
Execution plan for the query.

```python
@dataclass
class QueryPlan:
    analysis: QueryAnalysisResult
    primary_table: str
    required_tables: List[str]
    selected_columns: List[str]
    join_clauses: List[str]
    where_clauses: List[str]
    group_by_clauses: List[str]
    order_by_clauses: List[str]
    limit_clause: Optional[str]
    sql_query: Optional[str]
    confidence: ConfidenceScore
    estimated_rows: Optional[int]
    execution_metadata: Dict[str, Any]
```

## Usage Example

```python
from reportsmith.schema_intelligence.embedding_manager import EmbeddingManager
from reportsmith.query_orchestrator import QueryOrchestrator
from reportsmith.config_system.config_loader import ConfigLoader

# Load configuration
config_loader = ConfigLoader()
app_config = config_loader.load_app_config("fund_accounting")

# Initialize embedding manager
embedding_manager = EmbeddingManager()
embedding_manager.load_schema_metadata("fund_accounting", app_config)

# Initialize orchestrator
orchestrator = QueryOrchestrator(
    embedding_manager=embedding_manager,
    app_config=app_config,
    max_refinement_iterations=3
)

# Analyze user query
user_query = "Show me top 5 equity funds by AUM with their managers"
analysis = orchestrator.analyze_query(user_query)

print(f"Confidence: {analysis.confidence.level}")
print(f"Entities found: {len(analysis.entities)}")
print(f"Relationships found: {len(analysis.relationships)}")
print(f"Filters found: {len(analysis.filters)}")

# Generate query plan
plan = orchestrator.generate_query_plan(analysis)

print(f"\nPrimary table: {plan.primary_table}")
print(f"Required tables: {plan.required_tables}")
print(f"\nGenerated SQL:\n{plan.sql_query}")

# Validate and refine
refined_plan = orchestrator.validate_and_refine(plan)

if refined_plan.confidence.level == "high":
    # Execute the query
    print("\n✓ High confidence - ready to execute")
else:
    print(f"\n⚠ {refined_plan.confidence.level} confidence")
    print(f"Issues: {refined_plan.analysis.refinement_suggestions}")
```

## Iterative Refinement

The orchestrator performs up to 3 iterations of refinement:

1. **First iteration**: Initial analysis
2. **Check confidence**: If HIGH, stop
3. **Generate suggestions**: Identify issues
4. **Refine analysis**: Adjust entity search, filters, etc.
5. **Repeat**: Until HIGH confidence or max iterations

**Stopping conditions:**
- Confidence level reaches HIGH
- No refinement suggestions
- Max iterations reached

## Confidence Scoring

Confidence is calculated based on:

1. **Entity relevance** (40%): Average relevance score of entities
2. **Entity completeness** (20%): Number of entities found
3. **Relationship clarity** (20%): Clear relationships between tables
4. **Filter quality** (10%): Filters with high confidence
5. **Path quality** (10%): Clear navigation paths

**Levels:**
- **HIGH** (0.8+): Strong matches, clear relationships
- **MEDIUM** (0.6-0.8): Good matches, some ambiguity
- **LOW** (<0.6): Weak matches, unclear relationships

## Integration with Existing Systems

### Embedding Manager
Uses `EmbeddingManager` for semantic search:
- `search_schema()` - Find tables and columns
- `search_dimensions()` - Find dimension values
- `search_business_context()` - Find metrics and rules

### Config System
Loads application configuration:
- Relationships from `app.yaml`
- Schema metadata
- Business context

### Connection Manager
Query execution (future integration):
- `execute_query(plan.sql_query)`
- Result processing
- Error handling

## Best Practices

1. **Load embeddings once** - Cache in memory for performance
2. **Use app_id filtering** - Limit search scope to relevant application
3. **Adjust top_k** - Balance between precision and recall
4. **Monitor confidence** - Log low confidence queries for review
5. **Validate generated SQL** - Always validate before execution
6. **Handle errors gracefully** - Provide fallback for low confidence

## Future Enhancements

1. **LangChain integration** - Use LangChain agents for tool orchestration
2. **LLM-based refinement** - Use LLM to improve low-confidence queries
3. **Query caching** - Cache analysis results for common queries
4. **Learning from feedback** - Improve based on user corrections
5. **Multi-step queries** - Support complex queries requiring multiple SQL statements
6. **Cross-database queries** - Join data from multiple databases
7. **Natural language results** - Generate human-readable summaries

## Testing

Run tests:
```bash
python tests/test_orchestrator_models.py
```

Run demo:
```bash
python examples/orchestrator_demo.py
```

## API Reference

See inline documentation in:
- `src/reportsmith/query_orchestrator/models.py`
- `src/reportsmith/query_orchestrator/mcp_tools.py`
- `src/reportsmith/query_orchestrator/orchestrator.py`
