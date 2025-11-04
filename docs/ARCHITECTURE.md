# ReportSmith Architecture

**Version**: 1.0  
**Last Updated**: November 4, 2025

---

## System Overview

ReportSmith is a multi-agent natural language to SQL system that translates user questions into executable database queries using a sophisticated pipeline of LLM-powered agents, semantic search, and knowledge graphs.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          User Interface                              │
│  ┌─────────────────┐              ┌──────────────────┐             │
│  │  Streamlit UI   │              │   FastAPI REST   │             │
│  │  (Port 8501)    │              │   (Port 8000)    │             │
│  └─────────────────┘              └──────────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
                                   ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    LangGraph Orchestration Layer                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Multi-Agent Workflow (agents/orchestrator.py)               │  │
│  │                                                               │  │
│  │  1. Intent Analysis    → Extract entities & intent           │  │
│  │  2. Semantic Enrichment → Vector search for entities         │  │
│  │  3. Semantic Filtering → LLM-based result filtering          │  │
│  │  4. Schema Mapping     → Map entities to tables/columns      │  │
│  │  5. Query Planning     → Generate join paths                 │  │
│  │  6. SQL Generation     → Build executable SQL                │  │
│  │  7. SQL Execution      → Execute & format results            │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                   ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      Core Processing Modules                         │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐              │
│  │Query Process │  │Schema Intel │  │Query Exec    │              │
│  │- Intent      │  │- Embeddings │  │- SQL Exec    │              │
│  │- LLM Analysis│  │- Knowledge  │  │- Formatting  │              │
│  │- SQL Gen     │  │  Graph      │  │- Results     │              │
│  └──────────────┘  └─────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
                                   ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         External Services                            │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐              │
│  │OpenAI API    │  │Gemini API   │  │PostgreSQL    │              │
│  │- Embeddings  │  │- LLM        │  │- Metadata    │              │
│  │- Vector      │  │- Analysis   │  │- Target DBs  │              │
│  └──────────────┘  └─────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### 1. Query Processing Layer (`query_processing/`)

**Responsibility**: Analyze natural language queries and generate SQL

#### Components

**Intent Analyzer** (`intent_analyzer.py`, `llm_intent_analyzer.py`, `hybrid_intent_analyzer.py`)
- Extracts intent type (aggregate, list, comparison, ranking)
- Identifies entities (tables, columns, metrics, dimensions)
- Applies filters and conditions
- Uses hybrid approach: local mappings + semantic search + LLM

**SQL Generator** (`sql_generator.py`)
- Converts query plan to executable SQL
- Handles SELECT, FROM, JOIN, WHERE, GROUP BY, ORDER BY, LIMIT
- Auto-applies default filters (e.g., is_active=true)
- Prevents SQL injection
- Supports multi-value IN clauses

#### Data Flow

```
Natural Language → Intent Analysis → Entities → SQL Generation → Executable SQL
    "Show AUM"    → aggregate/metric → [aum, funds] → SELECT SUM(...) → Valid SQL
```

---

### 2. Schema Intelligence Layer (`schema_intelligence/`)

**Responsibility**: Understand database schemas and relationships

#### Components

**Embedding Manager** (`embedding_manager.py`)
- Manages vector embeddings for semantic search
- Supports OpenAI and local embedding models
- Embeds schema metadata, dimension values, business context
- Provides similarity search with configurable thresholds

**Knowledge Graph** (`knowledge_graph.py`)
- In-memory graph of table relationships
- Finds shortest paths between tables for joins
- Discovers multi-table query plans
- Manages bidirectional relationships

**Graph Builder** (`graph_builder.py`)
- Constructs knowledge graph from YAML schema
- Loads table/column metadata
- Identifies relationships (FK-PK, logical)
- Builds dimension value mappings

**Dimension Loader** (`dimension_loader.py`)
- Loads dimension values from databases
- Caches for performance
- Supports dynamic dimension discovery

#### Data Flow

```
Schema YAML → Graph Builder → Knowledge Graph → Join Paths
                             ↓
                      Embedding Manager → Vector Search → Entity Matches
```

---

### 3. Query Execution Layer (`query_execution/`)

**Responsibility**: Execute SQL and format results

#### Components

**SQL Executor** (`sql_executor.py`)
- Executes SQL against target databases
- Handles connection pooling
- Formats results (JSON, table, chart)
- Error handling and validation

#### Data Flow

```
SQL Query → Database Connection → Execution → Results → Formatting → JSON/Table
```

---

### 4. Agent Orchestration Layer (`agents/`)

**Responsibility**: Coordinate multi-agent workflow

#### Components

**Orchestrator** (`orchestrator.py`)
- Manages LangGraph workflow
- Coordinates agent execution
- Tracks state across pipeline
- Handles errors and retries

**Nodes** (`nodes.py`)
- Individual agent implementations
- Each node is a step in the pipeline
- Maintains QueryState throughout
- Comprehensive logging

#### Workflow States

```python
class QueryState:
    question: str              # User's question
    intent: Dict              # Extracted intent
    entities: List[Dict]      # Identified entities
    tables: List[str]         # Required tables
    plan: Dict                # Execution plan
    sql: Dict                 # Generated SQL
    execution: Dict           # Execution results
    errors: List[str]         # Any errors
    timings_ms: Dict          # Performance metrics
```

---

### 5. API Layer (`api/`)

**Responsibility**: REST API server

#### Endpoints

- `POST /query` - Process natural language query
- `GET /health` - Health check
- `GET /ready` - Readiness check

#### Features

- Request ID tracking
- CORS support
- Error handling
- JSON responses

---

### 6. UI Layer (`ui/`)

**Responsibility**: Interactive web interface

#### Features

- Sample query dropdown
- Real-time query processing
- JSON result display
- API status monitoring
- Request history

---

## Data Flow: End-to-End Query Processing

### Example: "Show AUM for all equity funds"

```
1. User Input
   ↓
   Question: "Show AUM for all equity funds"

2. Intent Analysis (hybrid_intent_analyzer.py)
   ↓
   Intent: {
     type: "aggregate",
     aggregations: ["sum"],
     entities: [
       {text: "aum", type: "metric"},
       {text: "equity", type: "dimension_value"}
     ]
   }

3. Semantic Enrichment (embedding_manager.py)
   ↓
   Searches: ["aum", "equity", "funds"]
   Matches: [
     {text: "funds.total_aum", score: 0.89},
     {text: "funds.fund_type", score: 0.76},
     {text: "Equity Growth", score: 0.85}
   ]

4. Semantic Filtering (LLM)
   ↓
   Filtered Entities: [
     {text: "aum", table: "funds", column: "total_aum"},
     {text: "equity", table: "funds", column: "fund_type", value: "Equity Growth"}
   ]

5. Schema Mapping (nodes.py)
   ↓
   Mapped Schema: {
     tables: ["funds"],
     columns: ["funds.total_aum", "funds.fund_type"],
     filters: [{column: "funds.fund_type", value: "Equity Growth"}]
   }

6. Query Planning (knowledge_graph.py)
   ↓
   Plan: {
     base_table: "funds",
     joins: [],
     filters: ["funds.fund_type = 'Equity Growth'"],
     aggregations: ["SUM(funds.total_aum)"]
   }

7. SQL Generation (sql_generator.py)
   ↓
   SQL: 
   SELECT SUM(funds.total_aum) AS aum,
          funds.fund_type AS fund_type
     FROM funds
    WHERE funds.fund_type = 'Equity Growth'
      AND funds.is_active = true  -- Auto-filter
    GROUP BY funds.fund_type

8. SQL Execution (sql_executor.py)
   ↓
   Results: [
     {aum: 15000000, fund_type: "Equity Growth"}
   ]

9. Response Formatting
   ↓
   JSON: {
     status: "ok",
     data: {
       question: "Show AUM for all equity funds",
       sql: "SELECT SUM(...)",
       results: [{aum: 15000000, ...}],
       row_count: 1,
       timings_ms: {intent: 250, enrichment: 150, ...}
     }
   }
```

---

## Configuration System

### YAML-Based Configuration

**Application Config** (`config/applications/{app}/app.yaml`)
```yaml
application:
  name: "Fund Accounting"
  vendor: "TruePotential"
  database_vendor: "postgresql"
```

**Schema Config** (`config/applications/{app}/schema.yaml`)
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
```

**Entity Mappings** (`config/entity_mappings.yaml`)
```yaml
aum:
  canonical_name: "AUM"
  table: "funds"
  column: "total_aum"
  entity_type: "metric"
```

### Configuration Loading

```
Startup → Config Loader → YAML Parsing → Validation → In-Memory Cache
                                                           ↓
                                              Knowledge Graph + Embeddings
```

---

## Key Design Patterns

### 1. Multi-Agent Architecture
- **Pattern**: Agent-based workflow with LangGraph
- **Benefit**: Each agent has single responsibility
- **Trade-off**: More complexity, better maintainability

### 2. Hybrid Intent Analysis
- **Pattern**: Local mappings + Semantic search + LLM
- **Benefit**: Fast exact matches, fallback for fuzzy/complex
- **Trade-off**: More complex, higher accuracy

### 3. Knowledge Graph
- **Pattern**: In-memory graph with BFS/DFS
- **Benefit**: Fast join path discovery
- **Trade-off**: Memory usage, rebuild on schema change

### 4. Minimal Embeddings
- **Pattern**: Embed names only, store metadata separately
- **Benefit**: Higher precision (scores ~1.0 for exact)
- **Trade-off**: Less context in embeddings

### 5. Auto-Filtering
- **Pattern**: Schema-driven default filters
- **Benefit**: Automatic data quality
- **Trade-off**: Must configure in YAML

---

## Performance Characteristics

### Latency Breakdown (Typical Query)

| Stage | Latency | % of Total |
|-------|---------|------------|
| Intent Analysis | ~250ms | 7% |
| Semantic Enrichment | ~150ms | 4% |
| LLM Filtering | ~2500ms | 69% |
| Schema Mapping | ~50ms | 1% |
| Query Planning | ~100ms | 3% |
| SQL Generation | <1ms | <1% |
| SQL Execution | ~500ms | 14% |
| **Total** | **~3.6s** | **100%** |

### Bottlenecks
1. **LLM API calls** (69% of time) - Main bottleneck
2. **SQL Execution** (14%) - Depends on query complexity
3. **Semantic Enrichment** (4%) - Vector search overhead

### Optimization Opportunities
1. **Cache LLM responses** for common queries
2. **Parallel LLM calls** where independent
3. **Local LLM** for filtering (faster, no API cost)
4. **Query result caching** for frequently run queries

---

## Scalability Considerations

### Current Limitations
- **In-memory knowledge graph**: Requires rebuild on schema changes
- **Synchronous processing**: One query at a time
- **No distributed processing**: Single-threaded LLM calls

### Future Enhancements
- **Async workflow**: Concurrent query processing
- **Distributed graph**: Redis/Neo4j for large schemas
- **Query queue**: Background processing for expensive queries
- **Horizontal scaling**: Multiple API instances with load balancer

---

## Security Considerations

### Implemented
- **SQL injection prevention**: Quote escaping in SQL generator
- **Parameterized queries**: Planned for execution layer
- **Environment variables**: Secrets not in code
- **API authentication**: Planned (currently open)

### TODO
- [ ] API key authentication
- [ ] Rate limiting
- [ ] Query cost limits
- [ ] Audit logging
- [ ] Role-based access control

---

## Monitoring & Observability

### Logging
- **Request ID tracking**: All logs tagged with `[rid:xxxxx]`
- **Stage-based logging**: Each pipeline stage logged separately
- **LLM metrics**: Token usage, latency, model info
- **Performance timing**: Sub-millisecond precision

### Log Locations
- `logs/app.log` - Application logs
- `logs/ui.log` - Streamlit UI logs
- `logs/boot.log` - Startup errors
- `logs/semantic_debug/` - Semantic search debug output

### Metrics (Future)
- Query throughput (queries/second)
- P50/P95/P99 latency
- LLM API costs per query
- Cache hit rates
- Error rates by stage

---

## Technology Stack Summary

### Core Technologies
- **Python 3.12**: Main language
- **LangGraph**: Multi-agent orchestration
- **OpenAI**: Embeddings API
- **Gemini**: LLM analysis
- **FastAPI**: REST API framework
- **Streamlit**: Web UI
- **PostgreSQL**: Metadata storage
- **ChromaDB**: Vector store
- **SQLAlchemy**: Database ORM
- **Pydantic**: Data validation

### Development Tools
- **pytest**: Testing framework
- **black**: Code formatter
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking

---

## Extension Points

### Adding New Agent Nodes
1. Define node function in `agents/nodes.py`
2. Add to workflow in `agents/orchestrator.py`
3. Update `QueryState` if needed
4. Add logging and error handling

### Adding New Intent Types
1. Update intent type enum
2. Add handling in `intent_analyzer.py`
3. Update SQL generator for new pattern
4. Add test cases

### Adding New Database Types
1. Implement connection manager
2. Add SQL dialect support in generator
3. Update schema loader
4. Test with sample database

### Adding New LLM Providers
1. Add provider client in `query_processing/`
2. Update prompt templates
3. Add configuration options
4. Implement fallback logic

---

## References

- **Code Repository**: `src/reportsmith/`
- **Configuration**: `config/`
- **Documentation**: `docs/`
- **Tests**: `tests/`
- **Examples**: `examples/`

For detailed implementation notes, see:
- [CURRENT_STATE.md](CURRENT_STATE.md) - Current status
- [docs/archive/IMPLEMENTATION_HISTORY.md](docs/archive/IMPLEMENTATION_HISTORY.md) - Historical notes
- [../REFACTORING_PROPOSAL.md](../REFACTORING_PROPOSAL.md) - Future plans

---

**Last Updated**: November 4, 2025  
**Version**: 1.0  
**Author**: GitHub Copilot
