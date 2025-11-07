# ReportSmith - Module Documentation Index

**Last Updated**: November 7, 2025

---

## Overview

This directory contains functional documentation for each major module in ReportSmith. Each module document describes the purpose, architecture, key components, and usage of that module.

---

## Module Documentation

### Core Modules

1. **[Agents Module](AGENTS_MODULE.md)**
   - Multi-agent orchestration with LangGraph
   - Workflow coordination and state management
   - Performance: ~3.6s total query processing
   - Key: `MultiAgentOrchestrator`, `AgentNodes`, `QueryState`

2. **[Query Processing Module](QUERY_PROCESSING_MODULE.md)**
   - Natural language understanding and SQL generation
   - Hybrid intent analysis (local + semantic + LLM)
   - Performance: ~2.7s for intent + SQL generation
   - Key: `HybridIntentAnalyzer`, `SQLGenerator`, `SQLValidator`

3. **[Schema Intelligence Module](SCHEMA_INTELLIGENCE_MODULE.md)**
   - Vector embeddings and semantic search
   - Knowledge graph for table relationships
   - Performance: ~150ms for semantic search
   - Key: `EmbeddingManager`, `SchemaKnowledgeGraph`, `KnowledgeGraphBuilder`

### Interface Modules

4. **[API Module](API_MODULE.md)**
   - FastAPI REST server
   - Endpoints: /query, /health, /ready
   - Request/response handling
   - Key: FastAPI application

5. **[UI Module](UI_MODULE.md)**
   - Streamlit web interface
   - Interactive query input
   - Result visualization
   - Key: Streamlit app

### Execution Module

6. **[Query Execution Module](QUERY_EXECUTION_MODULE.md)**
   - SQL query execution
   - Multi-database support
   - Connection pooling
   - Key: `SQLExecutor`, `ConnectionManager`

---

## Module Relationships

```
┌─────────────┐
│  UI Module  │
└──────┬──────┘
       │
       ▼
┌──────────────┐
│  API Module  │
└──────┬───────┘
       │
       ▼
┌───────────────────┐
│  Agents Module    │ ◄─── Orchestration Layer
└────────┬──────────┘
         │
    ┌────┴────┬─────────────┐
    ▼         ▼             ▼
┌─────────┐ ┌──────────┐ ┌───────────┐
│ Query   │ │ Schema   │ │ Query     │
│Process  │ │Intellig. │ │Execution  │
└─────────┘ └──────────┘ └───────────┘
```

---

## Quick Reference

### Module Purposes

| Module | Primary Function | Key Capability |
|--------|------------------|----------------|
| Agents | Orchestration | Multi-stage workflow coordination |
| Query Processing | NL to SQL | Intent analysis and SQL generation |
| Schema Intelligence | Semantic Search | Embeddings and knowledge graph |
| Query Execution | Database Access | SQL execution and result formatting |
| API | REST Interface | HTTP endpoints |
| UI | User Interface | Web-based query interface |

---

## Performance Overview

### Typical Query Flow Timing

```
User Question → API → Agents → Query Processing → Schema Intelligence → SQL Generation → Execution
                                    ~2.7s              ~150ms              <1ms           ~500ms
                                                                                          
Total: ~3.6 seconds
```

### Bottlenecks
1. **LLM API calls** (69% of time) - In Query Processing
2. **SQL Execution** (14% of time) - In Query Execution
3. **Semantic Search** (4% of time) - In Schema Intelligence

---

## How to Use This Documentation

### For Developers
1. Start with [Agents Module](AGENTS_MODULE.md) to understand the overall workflow
2. Read [Query Processing Module](QUERY_PROCESSING_MODULE.md) for NL understanding
3. Review [Schema Intelligence Module](SCHEMA_INTELLIGENCE_MODULE.md) for semantic capabilities
4. Check specific modules for implementation details

### For Architects
1. Review module relationships diagram above
2. Read HLD and LLD in parent `docs/` directory
3. Study module interfaces and dependencies
4. Review performance characteristics

### For Operations
1. Read [API Module](API_MODULE.md) for endpoint details
2. Check [Query Execution Module](QUERY_EXECUTION_MODULE.md) for database config
3. Review error handling sections in each module

---

## Additional Documentation

### Architecture Documents (Parent Directory)
- **[HLD.md](../HLD.md)**: High-level design and system architecture
- **[LLD.md](../LLD.md)**: Low-level design with detailed specifications
- **[ARCHITECTURE_DIAGRAMS.md](../ARCHITECTURE_DIAGRAMS.md)**: Visual architecture diagrams
- **[ARCHITECTURE.md](../ARCHITECTURE.md)**: Original architecture documentation
- **[CURRENT_STATE.md](../CURRENT_STATE.md)**: Current system status and roadmap

### Root Documentation
- **[README.md](../../README.md)**: Project overview and quick start
- **[SETUP.md](../../SETUP.md)**: Detailed setup instructions
- **[CONTRIBUTING.md](../../CONTRIBUTING.md)**: Contribution guidelines

---

## Module Dependency Graph

```
API Module
  └─> Agents Module
       ├─> Query Processing Module
       │    └─> Schema Intelligence Module
       ├─> Schema Intelligence Module
       │    └─> Embedding Manager (OpenAI)
       └─> Query Execution Module
            └─> Connection Manager

UI Module
  └─> API Module (HTTP)
```

---

## Contact and Support

For questions or issues with specific modules:
1. Check module documentation first
2. Review code comments in source files
3. Consult LLD for detailed specifications
4. See CONTRIBUTING.md for how to report issues

---

**Document Control**  
**Version**: 1.0  
**Last Updated**: November 7, 2025  
**Maintainer**: Development Team
