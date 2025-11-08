# Query Processing Module - Functional Documentation

**Module Path**: `src/reportsmith/query_processing/`  
**Version**: 1.0  
**Last Updated**: November 7, 2025

---

## Overview

The `query_processing` module handles natural language understanding and SQL generation. It analyzes user questions to extract intent and entities, then generates executable SQL queries.

### Purpose
- Extract intent and entities from natural language
- Perform hybrid analysis (local mappings + semantic search + LLM)
- Generate optimized SQL queries
- Validate SQL syntax and structure

### Key Components
- **HybridIntentAnalyzer**: Combines multiple analysis techniques
- **LLMIntentAnalyzer**: LLM-based intent extraction
- **SQLGenerator**: Converts query plans to SQL
- **SQLValidator**: Validates generated SQL

---

## Architecture

```
┌──────────────────────────────────┐
│   HybridIntentAnalyzer           │
│  • Local mapping lookup          │
│  • Semantic search               │
│  • LLM analysis                  │
└────────────┬─────────────────────┘
             │
     ┌───────┴────────┐
     ▼                ▼
┌──────────┐    ┌──────────────┐
│  LLM     │    │  Embedding   │
│  Intent  │    │  Manager     │
│ Analyzer │    │              │
└──────────┘    └──────────────┘

┌──────────────────────────────────┐
│      SQLGenerator                 │
│  • Build SELECT clause            │
│  • Build JOIN clause              │
│  • Build WHERE clause             │
│  • Apply auto-filters             │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│      SQLValidator                 │
│  • Validate syntax                │
│  • Check security                 │
└──────────────────────────────────┘
```

---

## Core Classes

### 1. HybridIntentAnalyzer

**File**: `hybrid_intent_analyzer.py`

#### Description
Combines three analysis approaches for maximum accuracy:
1. **Local Mappings**: Fast exact/fuzzy matching from YAML config
2. **Semantic Search**: Vector similarity for unmapped terms
3. **LLM Analysis**: Complex pattern understanding

#### Key Method: analyze()

```python
def analyze(self, question: str) -> IntentResult
```

**Process:**
1. Extract entities from local mappings (exact match)
2. Perform semantic search for unmapped terms
3. Use LLM for complex patterns and validation
4. Merge results from all sources
5. Return unified IntentResult

**Example:**
```python
analyzer = HybridIntentAnalyzer(
    entity_mappings=mappings,
    llm_analyzer=llm,
    embedding_manager=embeddings
)

result = analyzer.analyze("Show AUM for equity funds")
# Returns: IntentResult(
#   intent_type="aggregate",
#   entities=[
#       Entity(text="aum", type="metric", table="funds", column="total_aum"),
#       Entity(text="equity", type="dimension_value", value="Equity Growth")
#   ],
#   aggregations=["sum"]
# )
```

---

### 2. LLMIntentAnalyzer

**File**: `llm_intent_analyzer.py`

#### Description
Uses LLM (Gemini) to extract intent and entities from complex questions.

#### Capabilities
- Identify intent type (aggregate, list, comparison, trend, top_n)
- Extract entities (metrics, dimensions, filters)
- Understand temporal expressions ("last month", "Q1 2024")
- Resolve ambiguous references

#### Key Method: analyze()

```python
def analyze(self, question: str) -> Dict[str, Any]
```

**Prompt Structure:**
```
Given the question: "{question}"

Extract:
1. Intent type (aggregate/list/comparison/trend/top_n)
2. Metrics to calculate
3. Dimensions to group by
4. Filters to apply
5. Time range (if any)
6. Ordering preferences
```

---

### 3. SQLGenerator

**File**: `sql_generator.py`

#### Description
Converts query plans into executable SQL statements with proper syntax, joins, and filters.

#### Key Features
- SELECT clause generation (columns, aggregations)
- FROM/JOIN clause generation (with knowledge graph)
- WHERE clause generation (filters + auto-filters)
- GROUP BY/ORDER BY/LIMIT clauses
- SQL injection prevention
- Multi-value IN clause support

#### Key Method: generate()

```python
def generate(self, plan: QueryPlan) -> SQLQuery
```

**Algorithm:**
1. Build SELECT clause
   - Add columns with aliases
   - Add aggregations (SUM, AVG, COUNT, etc.)
2. Build FROM clause (base table)
3. Build JOIN clauses
   - Use join paths from knowledge graph
   - Determine join types (INNER, LEFT, RIGHT)
4. Build WHERE clause
   - User filters
   - Auto-filters from schema
   - Temporal filters
5. Build GROUP BY (if aggregations)
6. Build ORDER BY (if sorting)
7. Add LIMIT (if specified)
8. Validate SQL
9. Return SQLQuery object

**Example:**
```python
generator = SQLGenerator(knowledge_graph=kg)

plan = QueryPlan(
    select_columns=[
        {"table": "funds", "column": "total_aum", "aggregation": "SUM"}
    ],
    filters=[
        {"table": "funds", "column": "fund_type", "value": "Equity Growth"}
    ],
    base_table="funds"
)

sql = generator.generate(plan)
# Returns: SELECT SUM(funds.total_aum) AS aum
#          FROM funds
#          WHERE funds.fund_type = 'Equity Growth'
#            AND funds.is_active = true
```

---

### 4. SQLValidator

**File**: `sql_validator.py`

#### Description
Validates generated SQL for syntax, security, and correctness.

#### Validation Checks
- **Syntax**: Basic SQL syntax validation
- **Security**: SQL injection prevention
- **Structure**: Required clauses present
- **Table/Column**: Valid references

#### Key Method: validate()

```python
def validate(self, sql: str) -> ValidationResult
```

**Checks:**
- No dangerous keywords (DROP, DELETE, TRUNCATE)
- Proper quote escaping
- Valid SELECT structure
- No nested queries (unless allowed)
- Column references match schema

---

## Data Structures

### IntentResult

```python
@dataclass
class IntentResult:
    intent_type: str                 # "aggregate", "list", "comparison"
    entities: List[Entity]           # Identified entities
    filters: List[Filter]            # Applied filters
    aggregations: List[str]          # ["sum", "avg", etc.]
    time_range: Optional[TimeRange]  # Temporal filters
    group_by: List[str]              # Grouping dimensions
    order_by: List[OrderBy]          # Sorting
    limit: Optional[int]             # Result limit
```

### Entity

```python
@dataclass
class Entity:
    text: str                        # Original text from question
    type: str                        # "metric", "dimension", "table"
    table: Optional[str]             # Mapped table
    column: Optional[str]            # Mapped column
    value: Optional[str]             # Filter value
    confidence: float                # Matching confidence (0-1)
```

### QueryPlan

```python
{
    "base_table": "funds",
    "select_columns": [
        {
            "table": "funds",
            "column": "total_aum",
            "alias": "aum",
            "aggregation": "SUM"
        }
    ],
    "joins": [
        {
            "from_table": "funds",
            "to_table": "management_companies",
            "from_column": "management_company_id",
            "to_column": "id",
            "join_type": "INNER"
        }
    ],
    "filters": [...],
    "group_by": [...],
    "order_by": [...],
    "limit": None
}
```

---

## Usage Examples

### Basic Intent Analysis

```python
from reportsmith.query_processing import HybridIntentAnalyzer

analyzer = HybridIntentAnalyzer(...)
result = analyzer.analyze("Show total AUM for equity funds")

print(f"Intent: {result.intent_type}")
print(f"Entities: {[e.text for e in result.entities]}")
print(f"Aggregations: {result.aggregations}")
```

### SQL Generation

```python
from reportsmith.query_processing import SQLGenerator

generator = SQLGenerator(knowledge_graph=kg)
sql = generator.generate(query_plan)

print(f"SQL: {sql.query}")
print(f"Parameters: {sql.parameters}")
```

---

## Performance Considerations

### Intent Analysis
- Local mapping lookup: <10ms
- Semantic search: ~150ms
- LLM analysis: ~2500ms
- **Total**: ~2650ms

### SQL Generation
- Query plan to SQL: <1ms
- Validation: <1ms
- **Total**: <2ms

---

## Configuration

### Entity Mappings (YAML)

```yaml
aum:
  canonical_name: "AUM"
  table: "funds"
  column: "total_aum"
  entity_type: "metric"
  synonyms: ["assets under management", "total assets"]
  aggregation: "sum"
```

---

## Error Handling

### Intent Analysis Errors
- `NoEntitiesFoundError`: No entities identified
- `AmbiguousIntentError`: Multiple possible interpretations

### SQL Generation Errors
- `InvalidQueryPlanError`: Query plan structure invalid
- `SQLValidationError`: Generated SQL failed validation
- `TableNotFoundError`: Referenced table doesn't exist

---

## Testing

### Unit Tests

```python
def test_intent_analyzer():
    analyzer = HybridIntentAnalyzer(...)
    result = analyzer.analyze("Show AUM")
    assert result.intent_type == "aggregate"
    assert len(result.entities) > 0

def test_sql_generator():
    generator = SQLGenerator(...)
    sql = generator.generate(plan)
    assert "SELECT" in sql.query
    assert "FROM funds" in sql.query
```

---

**See Also:**
- [Agents Module](AGENTS_MODULE.md)
- [Schema Intelligence Module](SCHEMA_INTELLIGENCE_MODULE.md)
- [Low-Level Design](../LLD.md)
