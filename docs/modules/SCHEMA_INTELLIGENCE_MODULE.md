# Schema Intelligence Module - Functional Documentation

**Module Path**: `src/reportsmith/schema_intelligence/`  
**Version**: 1.0  
**Last Updated**: November 7, 2025

---

## Overview

The `schema_intelligence` module provides semantic understanding of database schemas through embeddings, knowledge graphs, and intelligent schema mapping.

### Purpose
- Manage vector embeddings for semantic search
- Build and maintain knowledge graph of table relationships
- Load and cache dimension values
- Enable intelligent schema discovery

### Key Components
- **EmbeddingManager**: Vector embeddings and semantic search
- **SchemaKnowledgeGraph**: In-memory graph of table relationships
- **KnowledgeGraphBuilder**: Constructs graph from YAML config
- **DimensionLoader**: Loads dimension values from databases

---

## Architecture

```
┌────────────────────────────────────┐
│    KnowledgeGraphBuilder           │
│  • Loads schema YAML                │
│  • Builds graph structure           │
│  • Populates embeddings             │
└──────────┬─────────────────────────┘
           │
           ├─────────────────┐
           ▼                 ▼
┌───────────────────┐  ┌──────────────────┐
│ SchemaKnowledge   │  │ EmbeddingManager │
│ Graph             │  │                  │
│ • NetworkX graph  │  │ • ChromaDB       │
│ • Find join paths │  │ • OpenAI API     │
│ • BFS/DFS         │  │ • Cache layers   │
└───────────────────┘  └──────────────────┘
           │
           ▼
┌───────────────────┐
│ DimensionLoader   │
│ • Load values     │
│ • Cache results   │
└───────────────────┘
```

---

## Core Classes

### 1. EmbeddingManager

**File**: `embedding_manager.py`

#### Description
Manages vector embeddings for semantic search using ChromaDB and OpenAI embeddings.

#### Features
- **Multi-collection support**: Schema, dimensions, context
- **Caching**: Request-level and persistent (Redis) caching
- **Batch processing**: Efficient batch embedding
- **High precision**: ~1.0 similarity scores for exact matches

#### Collections

| Collection | Content | Size | Usage |
|------------|---------|------|-------|
| Schema | Tables, columns, relationships | ~3000 docs | Entity mapping |
| Dimensions | Dimension values (fund types, etc.) | ~500 docs | Filter values |
| Context | Business rules, metrics, samples | ~50 docs | Contextual help |

#### Key Methods

##### embed_text()
```python
def embed_text(self, text: str) -> Vector
```
Generates vector embedding for text with caching.

##### search()
```python
def search(
    self,
    query: str,
    collection_name: str = "schema",
    top_k: int = 5,
    min_score: float = 0.0
) -> List[SearchResult]
```

**Parameters:**
- `query`: Text to search for
- `collection_name`: Which collection to search
- `top_k`: Number of results to return
- `min_score`: Minimum similarity threshold

**Returns**: List of SearchResult with content, metadata, distance

**Example:**
```python
embeddings = EmbeddingManager(...)
results = embeddings.search(
    query="total assets",
    collection_name="schema",
    top_k=5,
    min_score=0.7
)

for result in results:
    print(f"{result.content}: {result.metadata} (score: {1 - result.distance})")
# Output: funds.total_aum: {...} (score: 0.89)
```

##### add_to_collection()
```python
def add_to_collection(
    self,
    collection_name: str,
    documents: List[str],
    metadatas: List[Dict],
    ids: List[str]
)
```

Adds documents to a collection with metadata.

---

### 2. SchemaKnowledgeGraph

**File**: `knowledge_graph.py`

#### Description
In-memory graph representing database schema relationships using NetworkX.

#### Graph Structure
- **Nodes**: Tables
- **Edges**: Relationships (FK-PK, logical)
- **Node Attributes**: Table metadata (columns, filters, description)
- **Edge Attributes**: Join information (from_column, to_column, join_type)

#### Key Methods

##### add_table()
```python
def add_table(
    self,
    table_name: str,
    table_info: Dict[str, Any]
)
```

Adds a table node to the graph with metadata.

##### add_relationship()
```python
def add_relationship(
    self,
    from_table: str,
    to_table: str,
    from_column: str,
    to_column: str,
    relationship_type: str = "one_to_many",
    join_type: str = "inner"
)
```

Adds directed edge representing table relationship.

##### find_join_path()
```python
def find_join_path(
    self,
    source_table: str,
    target_table: str
) -> List[JoinStep]
```

**Algorithm**: Breadth-First Search (BFS)

**Process:**
1. If source == target, return empty list
2. Use BFS to find shortest path
3. Convert path to list of JoinStep objects
4. Return join sequence

**Example:**
```python
kg = SchemaKnowledgeGraph()
kg.add_table("funds", {...})
kg.add_table("management_companies", {...})
kg.add_relationship(
    from_table="funds",
    to_table="management_companies",
    from_column="management_company_id",
    to_column="id"
)

path = kg.find_join_path("funds", "management_companies")
# Returns: [JoinStep(
#   from_table="funds",
#   to_table="management_companies",
#   from_column="management_company_id",
#   to_column="id",
#   join_type="INNER"
# )]
```

##### get_table_info()
```python
def get_table_info(self, table_name: str) -> TableNode
```

Returns complete metadata for a table including:
- Description
- Columns and types
- Primary/foreign keys
- Default filters
- Relationships

---

### 3. KnowledgeGraphBuilder

**File**: `graph_builder.py`

#### Description
Constructs knowledge graph and populates embeddings from YAML configuration files.

#### Responsibilities
- Load schema YAML files
- Parse table and column definitions
- Extract relationships
- Build knowledge graph
- Populate embedding collections
- Load dimension values

#### Key Methods

##### build()
```python
def build(
    self,
    schema_config: Dict,
    entity_mappings: Dict
) -> Tuple[SchemaKnowledgeGraph, EmbeddingManager]
```

**Process:**
1. Create knowledge graph instance
2. Load tables from schema config
3. Add tables to graph
4. Extract and add relationships
5. Create embedding collections
6. Embed schema metadata
7. Embed dimension values
8. Embed business context
9. Return populated graph and embeddings

**Example:**
```python
builder = KnowledgeGraphBuilder()
kg, embeddings = builder.build(schema_config, entity_mappings)

# Knowledge graph ready for use
tables = kg.get_all_tables()
print(f"Loaded {len(tables)} tables")

# Embeddings ready for search
results = embeddings.search("AUM")
```

---

### 4. DimensionLoader

**File**: `dimension_loader.py`

#### Description
Loads dimension values from databases for semantic search and filtering.

#### Features
- Lazy loading (on-demand)
- Caching with TTL (24 hours default)
- Batch loading for performance
- Support for multiple databases

#### Key Methods

##### load_domain_values()
```python
def load_domain_values(
    self,
    table: str,
    column: str,
    database: str
) -> List[str]
```

**Process:**
1. Check cache for values
2. If not cached, query database
3. Execute: `SELECT DISTINCT {column} FROM {table}`
4. Store in cache with TTL
5. Return values

**Example:**
```python
loader = DimensionLoader(connection_manager)
fund_types = loader.load_domain_values(
    table="funds",
    column="fund_type",
    database="financial_db"
)
# Returns: ["Equity Growth", "Fixed Income", "Balanced", ...]
```

---

## Data Structures

### SearchResult

```python
@dataclass
class SearchResult:
    content: str              # Matched text
    metadata: Dict[str, Any]  # Associated metadata
    distance: float           # Vector distance (lower = better)
    
    @property
    def score(self) -> float:
        """Convert distance to similarity score (0-1)"""
        return 1.0 - self.distance
```

### JoinStep

```python
@dataclass
class JoinStep:
    from_table: str
    to_table: str
    from_column: str
    to_column: str
    join_type: str  # "INNER", "LEFT", "RIGHT"
```

### TableNode

```python
{
    "name": "funds",
    "description": "Fund master data",
    "columns": {
        "fund_id": {
            "type": "integer",
            "primary_key": True
        },
        "total_aum": {
            "type": "decimal",
            "description": "Assets under management"
        }
    },
    "relationships": [...],
    "default_filters": [
        {"column": "is_active", "value": True}
    ]
}
```

---

## Performance Characteristics

### Embedding Operations

| Operation | Duration | Notes |
|-----------|----------|-------|
| Single text embedding | ~50ms | OpenAI API call |
| Batch embedding (20 texts) | ~200ms | More efficient |
| Cache hit | <1ms | In-memory lookup |
| Vector search | ~10ms | ChromaDB query |

### Knowledge Graph Operations

| Operation | Complexity | Duration |
|-----------|------------|----------|
| Add table | O(1) | <1ms |
| Add relationship | O(1) | <1ms |
| Find join path | O(V+E) | ~10-50ms |
| Get table info | O(1) | <1ms |

---

## Caching Strategy

### Request-Level Cache
- **Scope**: Single request
- **Storage**: In-memory dictionary
- **Lifetime**: Request duration
- **Purpose**: Avoid duplicate embeddings in same request

### Persistent Cache (Redis)
- **Scope**: Cross-request
- **Storage**: Redis
- **Lifetime**: 24 hours (TTL)
- **Purpose**: Avoid repeated API calls for common terms

```python
# Cache key format
embedding:{hash(text)} → pickled vector
dimension:{table}:{column} → JSON array
```

---

## Configuration

### Schema YAML

```yaml
tables:
  funds:
    description: "Fund master data"
    columns:
      fund_id:
        type: integer
        primary_key: true
      total_aum:
        type: decimal
        description: "Assets under management"
    relationships:
      - to_table: management_companies
        from_column: management_company_id
        to_column: id
        relationship_type: one_to_many
        join_type: inner
    default_filters:
      - column: is_active
        value: true
        operator: "="
```

---

## Usage Examples

### Building Knowledge Graph

```python
from reportsmith.schema_intelligence import KnowledgeGraphBuilder

builder = KnowledgeGraphBuilder()
kg, embeddings = builder.build(schema_config, entity_mappings)

# Use knowledge graph
path = kg.find_join_path("funds", "clients")
print(f"Join path: {[step.from_table for step in path]}")

# Use embeddings
results = embeddings.search("equity funds")
for r in results:
    print(f"{r.content}: {r.score:.2f}")
```

### Semantic Search

```python
# Search schema collection
schema_results = embeddings.search(
    query="total assets",
    collection_name="schema",
    top_k=3,
    min_score=0.7
)

# Search dimension values
dim_results = embeddings.search(
    query="equity",
    collection_name="dimensions",
    top_k=5
)
```

---

## Error Handling

### Common Errors
- `TableNotFoundError`: Referenced table doesn't exist in graph
- `NoJoinPathError`: No path exists between tables
- `EmbeddingAPIError`: OpenAI API failure
- `CollectionNotFoundError`: Embedding collection doesn't exist

### Recovery Strategies
- Retry with exponential backoff for API errors
- Fall back to fuzzy matching if semantic search fails
- Use cached embeddings when API unavailable

---

## Testing

```python
def test_knowledge_graph():
    kg = SchemaKnowledgeGraph()
    kg.add_table("funds", {...})
    kg.add_table("clients", {...})
    kg.add_relationship("funds", "clients", ...)
    
    path = kg.find_join_path("funds", "clients")
    assert len(path) > 0

def test_embeddings():
    em = EmbeddingManager()
    results = em.search("AUM", collection_name="schema")
    assert len(results) > 0
    assert results[0].score > 0.7
```

---

**See Also:**
- [Agents Module](AGENTS_MODULE.md)
- [Query Processing Module](QUERY_PROCESSING_MODULE.md)
- [Low-Level Design](../LLD.md)
