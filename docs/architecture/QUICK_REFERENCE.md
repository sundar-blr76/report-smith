# ReportSmith Architecture Quick Reference

This is a quick reference guide for understanding the ReportSmith architecture. For complete details, see [C4_ARCHITECTURE.md](C4_ARCHITECTURE.md).

## 🏗️ System Overview

**ReportSmith** = Natural Language → SQL translation system for financial data reporting

**Core Technology**: Multi-agent AI system powered by LangGraph, OpenAI, and Gemini

## 📊 Architecture Diagrams

| Diagram | Level | Purpose | File |
|---------|-------|---------|------|
| Context | C4-L1 | System boundaries and users | [c4-context.puml](c4-context.puml) |
| Container | C4-L2 | Technology choices | [c4-container.puml](c4-container.puml) |
| Component | C4-L3 | Internal structure | [c4-component.puml](c4-component.puml) |
| Workflow | Detail | Processing pipeline | [workflow-diagram.puml](workflow-diagram.puml) |
| Data Flow | Detail | Component interactions | [data-flow-diagram.puml](data-flow-diagram.puml) |

## 🔧 Key Containers

```
┌─────────────────────────────────────────────────────────────┐
│ User Interfaces                                              │
│ • Streamlit UI (8501) - Interactive web interface           │
│ • FastAPI Server (8000) - REST API                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Core Engine                                                  │
│ • LangGraph Orchestrator - 8-stage workflow                 │
│ • Query Processing - Intent analysis & SQL generation       │
│ • Schema Intelligence - Embeddings & knowledge graph        │
│ • Query Execution - SQL executor & result formatter         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Data Stores & External Services                             │
│ • ChromaDB - Vector embeddings                              │
│ • PostgreSQL/Oracle/SQL Server - Target databases           │
│ • OpenAI API - Embeddings & LLM                             │
│ • Google Gemini API - LLM intent analysis                   │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 8-Stage Query Pipeline

| Stage | Component | Purpose | Technology |
|-------|-----------|---------|------------|
| 1️⃣ | Intent Analysis | Extract entities & intent | HybridIntentAnalyzer |
| 2️⃣ | Semantic Enrichment | Vector search for entities | ChromaDB + OpenAI |
| 3️⃣ | Semantic Filtering | LLM validates candidates | Gemini/OpenAI LLM |
| 4️⃣ | Entity Refinement | Refine mappings | DomainValueEnricher |
| 5️⃣ | Schema Mapping | Map to tables/columns | SchemaKnowledgeGraph |
| 6️⃣ | Query Planning | Generate join paths | NetworkX algorithms |
| 7️⃣ | SQL Generation | Build executable SQL | SQL Builders (4 types) |
| 8️⃣ | Finalization | Execute & format | SQLExecutor |

## 🧩 Key Components

### Query Processing
- **HybridIntentAnalyzer**: Combines 3 approaches (local + semantic + LLM)
- **SQLGenerator**: Orchestrates 4 SQL builders
  - SelectBuilder (aggregations)
  - JoinBuilder (optimal paths)
  - FilterBuilder (WHERE + auto-filters)
  - ModifiersBuilder (GROUP BY/ORDER BY/LIMIT)

### Schema Intelligence
- **EmbeddingManager**: OpenAI/local embeddings for semantic search
- **SchemaKnowledgeGraph**: NetworkX graph of table relationships
- **DimensionLoader**: Loads reference data from databases

### Infrastructure
- **Logger**: Structured logging with request ID tracking
- **LLMTracker**: Monitors LLM usage, tokens, costs
- **CacheManager**: Query result caching (LRU/Redis/Disk)
- **ConnectionManager**: Database connection pooling

## 🎯 Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Multi-Agent** | LangGraph orchestration with 8 specialized nodes |
| **Hybrid Intelligence** | Local mappings + Semantic search + LLM reasoning |
| **Configuration-Driven** | YAML schemas, no code changes needed |
| **Observability** | Request tracking, LLM monitoring, structured logging |
| **Performance** | Caching, pooling, adaptive LLM selection |
| **Security** | SQL injection prevention, parameterized queries |

## 📈 Technology Stack

### Backend
- Python 3.12+
- LangGraph (multi-agent orchestration)
- FastAPI (REST API)
- SQLAlchemy (database abstraction)

### AI/ML
- OpenAI API (embeddings + LLM)
- Google Gemini API (LLM)
- ChromaDB (vector storage)
- sentence-transformers (local embeddings)

### Frontend
- Streamlit (interactive UI)

### Databases
- PostgreSQL (metadata + target)
- Oracle (optional target)
- SQL Server (optional target)

## 🔍 Example Query Flow

**Input**: "Show AUM for all equity funds"

```
User Question
    ↓ (Streamlit/FastAPI)
LangGraph Orchestrator
    ↓ Stage 1
Intent: aggregate, metric="AUM", dimension="equity"
    ↓ Stage 2
ChromaDB Search: "AUM" → funds.total_aum (0.98 similarity)
    ↓ Stage 3
Gemini LLM: "equity" → fund_type='Equity Growth'
    ↓ Stage 4-6
Schema Mapping & Planning: Single table, no joins
    ↓ Stage 7
SQL Generation: SELECT SUM(total_aum)... WHERE fund_type='Equity Growth' AND is_active=true
    ↓ Stage 8
Execute & Format Results
    ↓
Return to User
```

## 📊 Performance Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Query Latency | ~3.6s | <2s |
| Intent Accuracy | ~95% | >95% |
| SQL Success Rate | 100% | 100% |

## 🚀 Optimization Features

- ✅ Query result caching (LRU/Redis/Disk)
- ✅ Connection pooling
- ✅ LLM usage tracking & cost monitoring
- ✅ Adaptive LLM model selection
- ✅ Fast path for simple queries
- ✅ Embedding caching in ChromaDB

## 📚 Related Documents

- [C4_ARCHITECTURE.md](C4_ARCHITECTURE.md) - Complete architecture documentation
- [../../README.md](../../README.md) - Main project README
- [../ARCHITECTURE.md](../ARCHITECTURE.md) - Detailed architecture guide
- [../HLD.md](../HLD.md) - High-level design
- [../LLD.md](../LLD.md) - Low-level design

## 🛠️ Extending the System

### Add a New Database
1. Add database config to YAML
2. Update connection manager
3. ✅ Done (no code changes)

### Add a New Agent/Stage
1. Add node function to `AgentNodes`
2. Update graph in `MultiAgentOrchestrator`
3. Define state transformations

### Add Custom SQL Logic
1. Create new builder component
2. Integrate into `SQLGenerator`
3. Update configuration

---

**Quick Tip**: Start with the [workflow-diagram.puml](workflow-diagram.puml) to understand the query flow, then review [c4-component.puml](c4-component.puml) for detailed component interactions.
