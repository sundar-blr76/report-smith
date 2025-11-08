# ReportSmith - Low-Level Design (LLD)

**Document Version**: 1.0  
**Last Updated**: November 7, 2025  
**Status**: Draft

---

## 1. Introduction

### 1.1 Purpose
This document provides detailed low-level design specifications for ReportSmith's core components, including class diagrams, sequence diagrams, data structures, and algorithms.

### 1.2 Scope
- Detailed component designs
- Class and interface specifications
- Sequence diagrams for key workflows
- Data structures and algorithms
- Database schema details
- API specifications

### 1.3 References
- [High-Level Design (HLD)](HLD.md)
- [Architecture Overview](ARCHITECTURE.md)

---

## 2. Component Design

### 2.1 Multi-Agent Orchestrator

#### 2.1.1 Class Diagram

```
┌──────────────────────────────────────┐
│     MultiAgentOrchestrator           │
├──────────────────────────────────────┤
│ - nodes: AgentNodes                  │
│ - graph: StateGraph                  │
├──────────────────────────────────────┤
│ + __init__(intent_analyzer,          │
│            graph_builder,             │
│            knowledge_graph)           │
│ + process_query(question: str)       │
│   → QueryResult                       │
│ - _build_graph() → StateGraph        │
└──────────────────────────────────────┘
              │
              │ uses
              ▼
┌──────────────────────────────────────┐
│          AgentNodes                   │
├──────────────────────────────────────┤
│ - intent_analyzer: HybridIntentAnalyzer│
│ - graph_builder: KnowledgeGraphBuilder│
│ - knowledge_graph: SchemaKnowledgeGraph│
├──────────────────────────────────────┤
│ + analyze_intent(state: QueryState)  │
│   → QueryState                        │
│ + semantic_enrich(state: QueryState) │
│   → QueryState                        │
│ + semantic_filter(state: QueryState) │
│   → QueryState                        │
│ + refine_entities(state: QueryState) │
│   → QueryState                        │
│ + map_schema(state: QueryState)      │
│   → QueryState                        │
│ + plan_query(state: QueryState)      │
│   → QueryState                        │
│ + generate_sql(state: QueryState)    │
│   → QueryState                        │
│ + finalize(state: QueryState)        │
│   → QueryState                        │
└──────────────────────────────────────┘
```

#### 2.1.2 QueryState Data Structure

```python
@dataclass
class QueryState:
    """State object passed between agents"""
    question: str                    # Original user question
    request_id: str                  # Unique request identifier
    intent: Dict[str, Any]           # Extracted intent
    entities: List[Dict[str, Any]]   # Identified entities
    semantic_results: List[Dict]     # Semantic search results
    filtered_entities: List[Dict]    # LLM-filtered entities
    refined_entities: List[Dict]     # Refined entity mappings
    tables: List[str]                # Required tables
    plan: Dict[str, Any]             # Query execution plan
    sql: Dict[str, Any]              # Generated SQL
    execution: Dict[str, Any]        # Execution results
    errors: List[str]                # Error messages
    timings_ms: Dict[str, float]     # Performance metrics
```

#### 2.1.3 Workflow Sequence

```
User Request
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. analyze_intent                                            │
│    Input: QueryState(question="Show AUM for equity funds")  │
│    Output: QueryState(intent={type: "aggregate", ...})      │
│    Duration: ~250ms                                          │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. semantic_enrich                                           │
│    Input: QueryState with entities from intent               │
│    Output: QueryState(semantic_results=[...])                │
│    Duration: ~150ms                                          │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. semantic_filter (LLM)                                     │
│    Input: QueryState with semantic_results                   │
│    Output: QueryState(filtered_entities=[...])               │
│    Duration: ~2500ms                                         │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. refine_entities                                           │
│    Input: QueryState with filtered_entities                  │
│    Output: QueryState(refined_entities=[...])                │
│    Duration: ~20ms                                           │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. map_schema                                                │
│    Input: QueryState with refined_entities                   │
│    Output: QueryState(tables=[...])                          │
│    Duration: ~50ms                                           │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. plan_query                                                │
│    Input: QueryState with tables                             │
│    Output: QueryState(plan={...})                            │
│    Duration: ~100ms                                          │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. generate_sql                                              │
│    Input: QueryState with plan                               │
│    Output: QueryState(sql={query: "SELECT ...", ...})        │
│    Duration: <1ms                                            │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. finalize                                                  │
│    Input: QueryState with sql                                │
│    Output: Final QueryState with execution results           │
│    Duration: ~500ms (if executing)                           │
└─────────────────────────────────────────────────────────────┘
```

---

### 2.2 Intent Analysis

#### 2.2.1 Class Diagram

```
┌────────────────────────────────────┐
│   HybridIntentAnalyzer             │
├────────────────────────────────────┤
│ - entity_mappings: Dict            │
│ - llm_analyzer: LLMIntentAnalyzer  │
│ - embedding_manager: EmbeddingMgr  │
├────────────────────────────────────┤
│ + analyze(question: str)           │
│   → IntentResult                   │
│ - _extract_from_mappings()         │
│ - _semantic_search()               │
│ - _llm_analysis()                  │
└────────────────────────────────────┘
            │
            ├── uses
            │
    ┌───────┴────────┐
    ▼                ▼
┌─────────────┐  ┌──────────────────┐
│ LLMIntent   │  │ EmbeddingManager │
│ Analyzer    │  │                  │
├─────────────┤  ├──────────────────┤
│+ analyze()  │  │+ search()        │
│+ extract()  │  │+ embed_text()    │
└─────────────┘  └──────────────────┘
```

#### 2.2.2 Intent Analysis Algorithm

```
Algorithm: HybridIntentAnalysis
Input: question (str)
Output: IntentResult

1. Initialize results = {}

2. Phase 1: Local Mapping Lookup
   FOR each entity_mapping in entity_mappings:
       IF mapping.canonical_name in question (case-insensitive):
           results.add(mapping)
   
3. Phase 2: Semantic Search (for unmapped terms)
   unmapped_terms = extract_terms(question) - results.keys()
   FOR each term in unmapped_terms:
       semantic_matches = embedding_manager.search(term, top_k=5)
       FOR each match in semantic_matches:
           IF match.score > 0.7:
               results.add(match)

4. Phase 3: LLM Analysis (for complex patterns)
   llm_result = llm_analyzer.analyze(question)
   results.merge(llm_result.entities)
   results.intent_type = llm_result.intent_type

5. Return IntentResult(
       intent_type=results.intent_type,
       entities=results.entities,
       filters=results.filters,
       aggregations=results.aggregations
   )
```

#### 2.2.3 Intent Result Data Structure

```python
@dataclass
class IntentResult:
    """Result from intent analysis"""
    intent_type: str                 # "aggregate", "list", "comparison", etc.
    entities: List[Entity]           # Identified entities
    filters: List[Filter]            # Applied filters
    aggregations: List[str]          # Required aggregations (sum, avg, etc.)
    time_range: Optional[TimeRange]  # Temporal filters
    group_by: List[str]              # Grouping dimensions
    order_by: List[OrderBy]          # Sorting
    limit: Optional[int]             # Result limit

@dataclass
class Entity:
    text: str                        # Original text
    type: str                        # "metric", "dimension", "table", etc.
    table: Optional[str]             # Mapped table
    column: Optional[str]            # Mapped column
    value: Optional[str]             # Filter value
    confidence: float                # Matching confidence (0-1)
```

---

### 2.3 Schema Intelligence

#### 2.3.1 Knowledge Graph Class Diagram

```
┌──────────────────────────────────────┐
│    SchemaKnowledgeGraph               │
├──────────────────────────────────────┤
│ - graph: nx.DiGraph                  │
│ - tables: Dict[str, TableNode]       │
│ - columns: Dict[str, ColumnNode]     │
├──────────────────────────────────────┤
│ + add_table(table_info: Dict)        │
│ + add_relationship(from, to, type)   │
│ + find_join_path(table1, table2)     │
│   → List[JoinStep]                   │
│ + get_table_info(table_name)         │
│   → TableNode                         │
│ + get_column_info(table, column)     │
│   → ColumnNode                        │
└──────────────────────────────────────┘
```

#### 2.3.2 Join Path Discovery Algorithm

```
Algorithm: FindJoinPath
Input: source_table (str), target_table (str)
Output: List[JoinStep]

1. IF source_table == target_table:
       RETURN []

2. Use BFS (Breadth-First Search) to find shortest path:
   queue = [(source_table, [])]
   visited = {source_table}
   
   WHILE queue is not empty:
       current_table, path = queue.pop(0)
       
       FOR each neighbor in graph.neighbors(current_table):
           IF neighbor == target_table:
               relationship = graph.edge(current_table, neighbor)
               RETURN path + [JoinStep(
                   from_table=current_table,
                   to_table=neighbor,
                   from_column=relationship.from_column,
                   to_column=relationship.to_column,
                   join_type=relationship.join_type
               )]
           
           IF neighbor not in visited:
               visited.add(neighbor)
               new_path = path + [create_join_step(current_table, neighbor)]
               queue.append((neighbor, new_path))
   
   RETURN None  # No path found
```

#### 2.3.3 Embedding Manager Design

```
┌──────────────────────────────────────┐
│      EmbeddingManager                 │
├──────────────────────────────────────┤
│ - chroma_client: ChromaDB            │
│ - embedding_function: OpenAIEmbedding│
│ - collections: Dict[str, Collection] │
│ - request_cache: Dict[str, Vector]   │
│ - redis_cache: Optional[Redis]       │
├──────────────────────────────────────┤
│ + embed_text(text: str) → Vector     │
│ + search(query: str, collection: str,│
│          top_k: int) → List[Match]   │
│ + add_to_collection(collection,      │
│                      documents,      │
│                      metadata)       │
│ - _get_from_cache(text: str)         │
│   → Optional[Vector]                  │
│ - _put_in_cache(text: str, vector)   │
└──────────────────────────────────────┘
```

#### 2.3.4 Semantic Search Algorithm

```
Algorithm: SemanticSearch
Input: query_text (str), collection_name (str), top_k (int)
Output: List[SearchResult]

1. Check request cache:
   IF query_text in request_cache:
       query_embedding = request_cache[query_text]
   ELSE:
       Check Redis cache (if available):
       IF query_text in redis_cache:
           query_embedding = redis_cache.get(query_text)
       ELSE:
           query_embedding = openai.embed([query_text])[0]
           redis_cache.set(query_text, query_embedding, ttl=86400)
       request_cache[query_text] = query_embedding

2. Get collection:
   collection = collections[collection_name]

3. Perform vector search:
   results = collection.query(
       query_embeddings=[query_embedding],
       n_results=top_k
   )

4. Transform results:
   search_results = []
   FOR i in range(len(results['documents'][0])):
       search_results.append(SearchResult(
           content=results['documents'][0][i],
           metadata=results['metadatas'][0][i],
           distance=results['distances'][0][i]
       ))

5. RETURN search_results
```

---

### 2.4 SQL Generation

#### 2.4.1 SQL Generator Class Diagram

```
┌──────────────────────────────────────┐
│         SQLGenerator                  │
├──────────────────────────────────────┤
│ - knowledge_graph: SchemaKnowledgeGraph│
│ - validator: SQLValidator            │
├──────────────────────────────────────┤
│ + generate(plan: QueryPlan)          │
│   → SQLQuery                          │
│ - _build_select_clause()             │
│ - _build_from_clause()               │
│ - _build_join_clause()               │
│ - _build_where_clause()              │
│ - _build_group_by_clause()           │
│ - _build_order_by_clause()           │
│ - _apply_auto_filters()              │
│ - _validate_and_escape()             │
└──────────────────────────────────────┘
```

#### 2.4.2 SQL Generation Algorithm

```
Algorithm: GenerateSQL
Input: QueryPlan
Output: SQLQuery

1. Initialize SQL components:
   select_clause = []
   from_clause = ""
   join_clauses = []
   where_clauses = []
   group_by_clause = []
   order_by_clause = []

2. Build SELECT clause:
   FOR each column in plan.select_columns:
       IF column.aggregation:
           select_clause.add(f"{column.aggregation}({column.table}.{column.column}) AS {column.alias}")
       ELSE:
           select_clause.add(f"{column.table}.{column.column} AS {column.alias}")

3. Build FROM clause:
   from_clause = plan.base_table

4. Build JOIN clauses:
   FOR each join in plan.joins:
       join_type = join.type.upper()  # INNER, LEFT, RIGHT
       join_clauses.add(
           f"{join_type} JOIN {join.to_table} "
           f"ON {join.from_table}.{join.from_column} = {join.to_table}.{join.to_column}"
       )

5. Build WHERE clause:
   # User filters
   FOR each filter in plan.filters:
       where_clauses.add(build_filter_clause(filter))
   
   # Auto filters from schema
   auto_filters = get_auto_filters(plan.tables)
   FOR each auto_filter in auto_filters:
       where_clauses.add(auto_filter)

6. Build GROUP BY clause:
   IF plan.has_aggregation:
       FOR each dimension in plan.group_by:
           group_by_clause.add(f"{dimension.table}.{dimension.column}")

7. Build ORDER BY clause:
   FOR each order in plan.order_by:
       direction = "DESC" if order.descending else "ASC"
       order_by_clause.add(f"{order.column} {direction}")

8. Assemble SQL:
   sql = f"SELECT {', '.join(select_clause)}\n"
   sql += f"  FROM {from_clause}\n"
   IF join_clauses:
       sql += "  " + "\n  ".join(join_clauses) + "\n"
   IF where_clauses:
       sql += f" WHERE {' AND '.join(where_clauses)}\n"
   IF group_by_clause:
       sql += f" GROUP BY {', '.join(group_by_clause)}\n"
   IF order_by_clause:
       sql += f" ORDER BY {', '.join(order_by_clause)}\n"
   IF plan.limit:
       sql += f" LIMIT {plan.limit}\n"

9. Validate SQL:
   validator.validate(sql)

10. RETURN SQLQuery(
        query=sql,
        parameters={},
        estimated_rows=estimate_rows(plan)
    )
```

#### 2.4.3 Filter Building Logic

```python
def build_filter_clause(filter: Filter) -> str:
    """Build SQL filter clause from filter object"""
    
    column_ref = f"{filter.table}.{filter.column}"
    
    if filter.operator == "=":
        return f"{column_ref} = '{escape(filter.value)}'"
    
    elif filter.operator == "IN":
        values = [f"'{escape(v)}'" for v in filter.values]
        return f"{column_ref} IN ({', '.join(values)})"
    
    elif filter.operator == "BETWEEN":
        return f"{column_ref} BETWEEN '{escape(filter.start)}' AND '{escape(filter.end)}'"
    
    elif filter.operator == "LIKE":
        return f"{column_ref} LIKE '%{escape(filter.pattern)}%'"
    
    elif filter.operator in [">", "<", ">=", "<="]:
        return f"{column_ref} {filter.operator} {filter.value}"
    
    else:
        raise ValueError(f"Unsupported operator: {filter.operator}")
```

---

### 2.5 Query Execution

#### 2.5.1 SQL Executor Class Diagram

```
┌──────────────────────────────────────┐
│         SQLExecutor                   │
├──────────────────────────────────────┤
│ - connection_manager: ConnectionMgr  │
│ - result_formatter: ResultFormatter  │
├──────────────────────────────────────┤
│ + execute(sql: str, db_name: str)    │
│   → ExecutionResult                   │
│ - _get_connection(db_name)           │
│ - _execute_query(connection, sql)    │
│ - _format_results(rows, format)      │
│ - _log_execution(sql, duration, rows)│
└──────────────────────────────────────┘
```

#### 2.5.2 Execution Sequence Diagram

```
Client              SQLExecutor         ConnectionMgr      Database
  │                      │                    │               │
  │  execute(sql, db)    │                    │               │
  ├─────────────────────>│                    │               │
  │                      │                    │               │
  │                      │ get_connection(db) │               │
  │                      ├───────────────────>│               │
  │                      │                    │               │
  │                      │   <connection>     │               │
  │                      │<───────────────────┤               │
  │                      │                    │               │
  │                      │  execute(sql)      │               │
  │                      ├────────────────────┼──────────────>│
  │                      │                    │               │
  │                      │                    │  query results│
  │                      │<───────────────────┼───────────────┤
  │                      │                    │               │
  │                      │ release_connection │               │
  │                      ├───────────────────>│               │
  │                      │                    │               │
  │                      │ format_results()   │               │
  │                      │                    │               │
  │  ExecutionResult     │                    │               │
  │<─────────────────────┤                    │               │
```

---

## 3. Data Model

### 3.1 Configuration Schema

#### 3.1.1 Application Config (app.yaml)

```yaml
# Schema Definition
application:
  name: string                    # Application name
  vendor: string                  # Vendor name
  database_vendor: string         # "postgresql", "oracle", "sqlserver"
  
databases:
  - name: string                  # Database identifier
    host: string                  # Database host
    port: integer                 # Database port
    database: string              # Database name
    schema: string                # Default schema

default_filters:                  # Auto-applied filters
  - table: string
    column: string
    value: any
    operator: string              # "=", "IN", etc.
```

#### 3.1.2 Schema Config (schema.yaml)

```yaml
# Schema Definition
tables:
  {table_name}:
    description: string
    business_name: string
    
    columns:
      {column_name}:
        type: string              # SQL data type
        description: string
        business_name: string
        primary_key: boolean
        foreign_key:
          table: string
          column: string
        auto_filter:              # Default filter
          operator: string
          value: any
        
    relationships:
      - to_table: string
        from_column: string
        to_column: string
        relationship_type: string  # "one_to_many", "many_to_one"
        join_type: string          # "inner", "left", "right"
```

### 3.2 Runtime Data Structures

#### 3.2.1 Entity Mappings

```python
{
    "aum": {
        "canonical_name": "AUM",
        "table": "funds",
        "column": "total_aum",
        "entity_type": "metric",
        "synonyms": ["assets under management", "total assets"],
        "aggregation": "sum"
    },
    "equity": {
        "canonical_name": "Equity Funds",
        "table": "funds",
        "column": "fund_type",
        "entity_type": "domain_value",
        "value": "Equity Growth",
        "synonyms": ["equity", "stock funds"]
    }
}
```

#### 3.2.2 Query Plan Structure

```python
{
    "base_table": "funds",
    "select_columns": [
        {
            "table": "funds",
            "column": "total_aum",
            "alias": "aum",
            "aggregation": "SUM"
        },
        {
            "table": "funds",
            "column": "fund_type",
            "alias": "fund_type",
            "aggregation": None
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
    "filters": [
        {
            "table": "funds",
            "column": "fund_type",
            "operator": "=",
            "value": "Equity Growth"
        },
        {
            "table": "funds",
            "column": "is_active",
            "operator": "=",
            "value": True
        }
    ],
    "group_by": ["funds.fund_type"],
    "order_by": [],
    "limit": None
}
```

---

## 4. API Specifications

### 4.1 REST API Endpoints

#### 4.1.1 POST /query

**Request:**
```json
{
    "question": "Show AUM for all equity funds",
    "execute": true,
    "format": "json"
}
```

**Response (Success):**
```json
{
    "status": "success",
    "request_id": "rid_abc123",
    "data": {
        "question": "Show AUM for all equity funds",
        "intent": {
            "type": "aggregate",
            "aggregations": ["sum"]
        },
        "sql": {
            "query": "SELECT SUM(funds.total_aum) AS aum...",
            "database": "financial_db"
        },
        "results": [
            {
                "aum": 15000000,
                "fund_type": "Equity Growth"
            }
        ],
        "row_count": 1,
        "execution_time_ms": 543
    },
    "timings_ms": {
        "intent": 250,
        "semantic": 150,
        "filter": 2500,
        "schema": 50,
        "plan": 100,
        "sql": 1,
        "execution": 543,
        "total": 3594
    }
}
```

**Response (Error):**
```json
{
    "status": "error",
    "request_id": "rid_xyz789",
    "error": {
        "code": "INTENT_ANALYSIS_FAILED",
        "message": "Could not identify entities in question",
        "details": {
            "stage": "semantic_filter",
            "reason": "No semantic matches found"
        }
    }
}
```

#### 4.1.2 GET /health

**Response:**
```json
{
    "status": "healthy",
    "version": "1.0.0",
    "timestamp": "2025-11-07T04:47:45Z"
}
```

#### 4.1.3 GET /ready

**Response:**
```json
{
    "status": "ready",
    "dependencies": {
        "database": "connected",
        "embeddings": "loaded",
        "knowledge_graph": "loaded",
        "llm_provider": "available"
    }
}
```

---

## 5. Database Schema

### 5.1 Metadata Database Tables

#### 5.1.1 execution_sessions

```sql
CREATE TABLE execution_sessions (
    session_id VARCHAR(50) PRIMARY KEY,
    original_query TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(20),  -- 'running', 'completed', 'failed'
    total_duration_ms INTEGER,
    request_id VARCHAR(50),
    user_id VARCHAR(50)
);
```

#### 5.1.2 execution_steps

```sql
CREATE TABLE execution_steps (
    step_id SERIAL PRIMARY KEY,
    session_id VARCHAR(50) REFERENCES execution_sessions(session_id),
    step_number INTEGER,
    step_type VARCHAR(50),  -- 'query', 'aggregation', 'export'
    database_name VARCHAR(100),
    query_executed TEXT,
    rows_examined INTEGER,
    rows_returned INTEGER,
    duration_ms INTEGER,
    status VARCHAR(20),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 5.1.3 query_executions

```sql
CREATE TABLE query_executions (
    execution_id SERIAL PRIMARY KEY,
    session_id VARCHAR(50) REFERENCES execution_sessions(session_id),
    sql_query TEXT NOT NULL,
    database_name VARCHAR(100),
    execution_time_ms INTEGER,
    rows_returned INTEGER,
    status VARCHAR(20),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 6. Algorithms and Pseudocode

### 6.1 Hybrid Entity Matching

```
Algorithm: HybridEntityMatching
Input: question (str), entity_mappings (Dict), embedding_manager (EmbeddingManager)
Output: List[MatchedEntity]

1. matched_entities = []

2. // Phase 1: Exact matching from local mappings
   FOR each word in question.lower().split():
       FOR each (key, mapping) in entity_mappings:
           IF word == key OR word in mapping.synonyms:
               matched_entities.add(MatchedEntity(
                   text=word,
                   mapping=mapping,
                   confidence=1.0,
                   source="exact_match"
               ))

3. // Phase 2: Fuzzy matching with Levenshtein distance
   unmatched_words = question_words - matched_words
   FOR each word in unmatched_words:
       FOR each (key, mapping) in entity_mappings:
           distance = levenshtein_distance(word, key)
           IF distance <= 2:  // Allow up to 2 character differences
               matched_entities.add(MatchedEntity(
                   text=word,
                   mapping=mapping,
                   confidence=1.0 - (distance / len(key)),
                   source="fuzzy_match"
               ))

4. // Phase 3: Semantic matching using embeddings
   still_unmatched = unmatched_words - fuzzy_matched_words
   FOR each word in still_unmatched:
       semantic_results = embedding_manager.search(
           query=word,
           collection="schema",
           top_k=3,
           min_score=0.7
       )
       FOR each result in semantic_results:
           matched_entities.add(MatchedEntity(
               text=word,
               mapping=result.metadata,
               confidence=result.score,
               source="semantic_match"
           ))

5. // Deduplicate and sort by confidence
   matched_entities = deduplicate(matched_entities)
   matched_entities.sort(key=lambda x: x.confidence, reverse=True)

6. RETURN matched_entities
```

### 6.2 Auto-Filter Application

```
Algorithm: ApplyAutoFilters
Input: query_plan (QueryPlan), schema_config (SchemaConfig)
Output: Updated QueryPlan

1. FOR each table in query_plan.tables:
       table_config = schema_config.get_table(table)
       
       IF table_config.default_filters exists:
           FOR each default_filter in table_config.default_filters:
               // Check if filter already exists
               filter_exists = FALSE
               FOR each existing_filter in query_plan.filters:
                   IF existing_filter.column == default_filter.column:
                       filter_exists = TRUE
                       BREAK
               
               IF NOT filter_exists:
                   query_plan.filters.add(Filter(
                       table=table,
                       column=default_filter.column,
                       operator=default_filter.operator,
                       value=default_filter.value
                   ))

2. RETURN query_plan
```

---

## 7. Performance Optimization

### 7.1 Caching Strategy

#### Request-Level Cache
```python
class RequestCache:
    """Cache for single request lifecycle"""
    def __init__(self):
        self._cache = {}
    
    def get_embedding(self, text: str) -> Optional[Vector]:
        return self._cache.get(f"emb:{text}")
    
    def set_embedding(self, text: str, vector: Vector):
        self._cache[f"emb:{text}"] = vector
    
    def clear(self):
        self._cache.clear()
```

#### Persistent Cache (Redis)
```python
class PersistentCache:
    """Redis-based cache for embeddings"""
    def __init__(self, redis_client):
        self.redis = redis_client
        self.ttl = 86400  # 24 hours
    
    def get_embedding(self, text: str) -> Optional[Vector]:
        key = f"embedding:{hash(text)}"
        data = self.redis.get(key)
        if data:
            return pickle.loads(data)
        return None
    
    def set_embedding(self, text: str, vector: Vector):
        key = f"embedding:{hash(text)}"
        self.redis.setex(key, self.ttl, pickle.dumps(vector))
```

### 7.2 Batch Processing

```python
def batch_embed_texts(texts: List[str], batch_size: int = 20) -> List[Vector]:
    """Embed multiple texts in batches to reduce API calls"""
    vectors = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_vectors = openai_client.embed(batch)
        vectors.extend(batch_vectors)
    
    return vectors
```

---

## 8. Error Handling

### 8.1 Error Hierarchy

```
Exception
    └── ReportSmithError
        ├── ConfigurationError
        │   ├── InvalidYAMLError
        │   └── MissingConfigError
        ├── IntentAnalysisError
        │   ├── NoEntitiesFoundError
        │   └── AmbiguousIntentError
        ├── SchemaError
        │   ├── TableNotFoundError
        │   ├── ColumnNotFoundError
        │   └── RelationshipNotFoundError
        ├── SQLGenerationError
        │   ├── InvalidQueryPlanError
        │   └── SQLValidationError
        └── ExecutionError
            ├── DatabaseConnectionError
            ├── QueryExecutionError
            └── ResultFormattingError
```

### 8.2 Error Recovery Strategies

```python
def execute_with_retry(func, max_retries=3, backoff=2):
    """Execute function with exponential backoff retry"""
    for attempt in range(max_retries):
        try:
            return func()
        except (ConnectionError, TimeoutError) as e:
            if attempt == max_retries - 1:
                raise
            wait_time = backoff ** attempt
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
            time.sleep(wait_time)
```

---

## 9. Testing Strategy

### 9.1 Unit Test Examples

```python
class TestIntentAnalyzer:
    def test_extract_metric(self):
        analyzer = HybridIntentAnalyzer(...)
        result = analyzer.analyze("Show total AUM")
        assert result.entities[0].type == "metric"
        assert result.entities[0].column == "total_aum"
    
    def test_extract_filter(self):
        analyzer = HybridIntentAnalyzer(...)
        result = analyzer.analyze("Show equity funds")
        assert len(result.filters) > 0
        assert result.filters[0].value == "Equity Growth"

class TestSQLGenerator:
    def test_simple_select(self):
        plan = QueryPlan(...)
        sql = SQLGenerator().generate(plan)
        assert "SELECT" in sql.query
        assert "FROM funds" in sql.query
    
    def test_with_joins(self):
        plan = QueryPlan(joins=[...])
        sql = SQLGenerator().generate(plan)
        assert "JOIN" in sql.query
```

### 9.2 Integration Test Examples

```python
class TestEndToEnd:
    def test_query_flow(self):
        orchestrator = MultiAgentOrchestrator(...)
        result = orchestrator.process_query("Show AUM for equity funds")
        
        assert result.status == "success"
        assert result.sql is not None
        assert "SELECT" in result.sql.query
        assert len(result.results) > 0
```

---

## 10. Deployment Specifications

### 10.1 Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Optional
REDIS_URL=redis://localhost:6379
LOG_LEVEL=INFO
MAX_WORKERS=4
ENABLE_METRICS=true
```

### 10.2 Resource Requirements

| Component | CPU | Memory | Disk | Notes |
|-----------|-----|--------|------|-------|
| API Server | 2 cores | 4GB | 10GB | FastAPI |
| UI Server | 1 core | 2GB | 5GB | Streamlit |
| PostgreSQL | 2 cores | 8GB | 50GB | Metadata + target DBs |
| Redis (optional) | 1 core | 2GB | 5GB | Cache |

---

## 11. Appendix

### 11.1 Code Snippets

See individual module documentation for detailed code examples.

### 11.2 Configuration Examples

See `config/applications/` directory for complete YAML examples.

### 11.3 Glossary

- **Entity**: A business term identified in user's question (metric, dimension, filter)
- **Intent**: The type of question asked (aggregate, list, comparison, etc.)
- **Knowledge Graph**: In-memory graph of table relationships
- **Embedding**: Vector representation of text for semantic search
- **Query Plan**: Intermediate representation before SQL generation
- **Auto-Filter**: Default filter automatically applied from schema config

---

**Document Control**  
**Version**: 1.0  
**Last Updated**: November 7, 2025  
**Author**: Development Team  
**Approver**: [Pending]
