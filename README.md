# ReportSmith

## Overview
ReportSmith is an intelligent natural language to SQL application for financial data reporting. It uses a multi-agent AI system powered by LangGraph to understand database schemas and dynamically generate SQL queries from natural language questions.

## What It Does
- **Natural Language to SQL**: Ask questions in plain English, get executable SQL queries
- **Multi-Database Support**: Query across PostgreSQL, Oracle, SQL Server databases
- **Schema Intelligence**: Hybrid intent analysis using local mappings, semantic search, and LLM
- **Knowledge Graph**: Understands table relationships and generates optimal join paths
- **Auto-Filtering**: Automatically applies default filters (e.g., active records only)
- **SQL Execution**: Execute queries and return formatted results
- **Complete Audit**: Track all executions with full transparency

## Key Features
- **Multi-Agent Architecture**: LangGraph orchestration for intent analysis, semantic enrichment, schema mapping, and SQL generation
- **Hybrid Intent Analysis**: Combines local mappings, vector embeddings, and LLM for accurate entity recognition
- **OpenAI Embeddings**: High-precision semantic search with ~1.0 scores for exact matches
- **YAML-based Configuration**: Simple, declarative application and schema configs
- **FastAPI + Streamlit**: Modern API server with interactive UI
- **Comprehensive Logging**: Request ID tracking, LLM metrics, and detailed debugging output

## Architecture

### Tech Stack
- **LangGraph**: Multi-agent workflow orchestration
- **OpenAI/Gemini**: LLM for intent analysis and filtering
- **ChromaDB**: Vector store for semantic search
- **FastAPI**: REST API server
- **Streamlit**: Interactive web UI
- **PostgreSQL**: Metadata and audit storage

### Project Structure

```
ReportSmith/
├── src/reportsmith/           # Application code
│   ├── agents/                # LangGraph nodes and orchestration
│   ├── query_processing/      # Intent analysis and SQL generation
│   ├── schema_intelligence/   # Embeddings, knowledge graph, schema mapping
│   ├── query_execution/       # SQL execution engine
│   ├── api/                   # FastAPI server
│   └── ui/                    # Streamlit interface
├── config/
│   ├── applications/          # YAML configs (one per app)
│   └── entity_mappings.yaml   # Entity to schema mappings
├── scripts/                   # Operational scripts
├── docs/                      # Documentation
│   ├── CURRENT_STATE.md       # Current status and roadmap
│   ├── ARCHITECTURE.md        # System architecture
│   └── archive/               # Historical implementation notes
└── tests/                     # Unit and integration tests
    ├── unit/                  # Unit tests
    └── integration/           # Integration tests
```

## Quick Start

### Prerequisites
- Python 3.12+
- PostgreSQL 12+
- OpenAI API key (recommended) or local embeddings
- Gemini API key (for LLM analysis)

### Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**
   Create `.env` file with:
   ```bash
   OPENAI_API_KEY=sk-...
   GEMINI_API_KEY=...
   DATABASE_URL=postgresql://user:pass@localhost/dbname
   ```

3. **Initialize Database**
   ```bash
   cd db_setup
   python3 setup_database.py
   ```

4. **Start Application**
   ```bash
   ./start.sh
   ```
   
   This starts:
   - FastAPI server at `http://127.0.0.1:8000`
   - Streamlit UI at `http://127.0.0.1:8501`

### Usage

**Via UI**: Open `http://127.0.0.1:8501` and select a sample query or type your own

**Via API**:
```bash
curl -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Show AUM for all equity funds"}'
```

### Documentation

#### Architecture & Design
- **[docs/architecture/C4_ARCHITECTURE.md](docs/architecture/C4_ARCHITECTURE.md)** - 📐 **C4 model architecture diagrams** - System context, containers, and components
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Detailed architecture documentation
- **[docs/HLD.md](docs/HLD.md)** - High-level design document
- **[docs/LLD.md](docs/LLD.md)** - Low-level design document

#### Setup & Operations
- **[SETUP.md](SETUP.md)** - Detailed setup guide
- **[docs/CURRENT_STATE.md](docs/CURRENT_STATE.md)** - Current system status
- **[docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md)** - Database schema details

#### Performance & Optimization
- **[docs/LATENCY_IMPROVEMENTS.md](docs/LATENCY_IMPROVEMENTS.md)** - Performance optimization analysis
- **[docs/LATENCY_QUICK_WINS.md](docs/LATENCY_QUICK_WINS.md)** - Quick implementation guide

#### Development
- **[REFACTORING_PROPOSAL.md](REFACTORING_PROPOSAL.md)** - Architecture refactoring plan

## Example Use Case

**Query**: "Show AUM for all equity funds"

**ReportSmith Workflow**:
1. **Intent Analysis**: Identifies "AUM" as metric, "equity" as filter
2. **Semantic Enrichment**: Searches embeddings for unmapped entities
3. **Schema Mapping**: Maps "AUM" to `funds.total_aum`, "equity" to `funds.fund_type='Equity Growth'`
4. **Query Planning**: Generates execution plan using knowledge graph
5. **SQL Generation**: Creates optimized SQL with auto-filters
6. **Execution**: Runs query and returns formatted results

**Generated SQL**:
```sql
SELECT SUM(funds.total_aum) AS aum,
       funds.fund_type AS fund_type
  FROM funds
 WHERE funds.fund_type = 'Equity Growth'
   AND funds.is_active = true  -- Auto-filter
 GROUP BY funds.fund_type
```

## Current Status

✅ **Production Ready**:
- Multi-agent orchestration with LangGraph
- Hybrid intent analysis (95% accuracy)
- Semantic search with OpenAI embeddings
- SQL generation with auto-filtering
- SQL execution engine
- FastAPI server + Streamlit UI
- Comprehensive logging and debugging

🚧 **In Progress**:
- Streaming UI with real-time progress
- Advanced query optimization
- Multi-database federation

📋 **Planned**:
- Query result caching
- Natural language result explanations
- Multi-turn conversations

## Performance Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Query Latency | ~3.6s | <2s |
| Intent Accuracy | ~95% | >95% |
| Entity Precision | ~90% | >90% |
| SQL Success Rate | 100% | 100% |

### Performance Optimization

See detailed latency improvement analysis and recommendations:
- **[LATENCY_IMPROVEMENTS.md](docs/LATENCY_IMPROVEMENTS.md)** - Comprehensive analysis with strategic roadmap
- **[LATENCY_QUICK_WINS.md](docs/LATENCY_QUICK_WINS.md)** - Actionable 1-2 week implementation guide

**Quick wins identified**:
- Query result caching: 100% improvement on cache hits
- Adaptive LLM model selection: 30-40% average improvement
- Fast path for simple queries: 80% improvement for 20-30% of queries
- Combined estimated impact: **68% latency reduction** (3.6s → 1.15s)

## Contributing

See [REFACTORING_PROPOSAL.md](REFACTORING_PROPOSAL.md) for current refactoring plans and how to contribute.

## License

TBD