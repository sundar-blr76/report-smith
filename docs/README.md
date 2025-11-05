# ReportSmith Documentation

This directory contains all technical documentation for ReportSmith.

## Quick Navigation

### Getting Started
- **[../README.md](../README.md)** - Project overview and quick start
- **[../SETUP.md](../SETUP.md)** - Detailed setup instructions

### Architecture & Design
- **[CURRENT_STATE.md](CURRENT_STATE.md)** - Current system status, features, and roadmap
- **[../REFACTORING_PROPOSAL.md](../REFACTORING_PROPOSAL.md)** - Modular refactoring plan

### Technical Documentation
- **[DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)** - Database schema and tables
- **[EMBEDDING_STRATEGY.md](EMBEDDING_STRATEGY.md)** - Minimal embedding approach
- **[SEMANTIC_SEARCH_REFACTORING.md](SEMANTIC_SEARCH_REFACTORING.md)** - Semantic search design
- **[ENTITY_REFINEMENT.md](ENTITY_REFINEMENT.md)** - Entity extraction process
- **[SQL_COLUMN_ENRICHMENT.md](SQL_COLUMN_ENRICHMENT.md)** - SQL column enrichment

### Diagrams & Flows
- **[QUERY_FLOW_DIAGRAM.txt](QUERY_FLOW_DIAGRAM.txt)** - Query processing workflow

### Historical Documentation
- **[archive/IMPLEMENTATION_HISTORY.md](archive/IMPLEMENTATION_HISTORY.md)** - Historical implementation notes

## Documentation Structure

```
docs/
├── README.md                          # This file - documentation index
├── CURRENT_STATE.md                   # ⭐ Start here for current status
├── DATABASE_SCHEMA.md                 # Database design
├── EMBEDDING_STRATEGY.md              # Embeddings approach
├── SEMANTIC_SEARCH_REFACTORING.md     # Semantic search design
├── ENTITY_REFINEMENT.md               # Entity extraction
├── SQL_COLUMN_ENRICHMENT.md           # SQL enrichment
├── QUERY_FLOW_DIAGRAM.txt             # Query flow visualization
└── archive/                           # Historical documentation
    └── IMPLEMENTATION_HISTORY.md      # Implementation evolution
```

## Database

ReportSmith uses PostgreSQL with 5 tables:

1. **Execution Tracking (3 tables)**
   - `execution_sessions` - Overall query execution
   - `execution_steps` - Multi-step breakdown
   - `query_executions` - SQL query metrics

2. **Saved Queries (1 table)**
   - `saved_queries` - User-saved queries

3. **Vector Store (1 table)**
   - `schema_embeddings` - Semantic search embeddings

## Application Configurations

Application schemas stored in YAML files:

```
config/applications/
├── fund_accounting/
│   ├── app.yaml             # Application metadata
│   ├── schema.yaml          # Schema definition
│   └── instances/           # Database instances
```

Each configuration contains:
- Database connections
- Table schemas
- Business context
- Relationships

**See:** [../config/applications/README.md](../config/applications/README.md)

## For Different Audiences

### 👨‍💻 Developers
Start with:
1. [CURRENT_STATE.md](CURRENT_STATE.md) - Current architecture
2. [../REFACTORING_PROPOSAL.md](../REFACTORING_PROPOSAL.md) - Refactoring plans
3. [EMBEDDING_STRATEGY.md](EMBEDDING_STRATEGY.md) - Semantic search

### 🚀 DevOps
Start with:
1. [../SETUP.md](../SETUP.md) - Setup and deployment
2. [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) - Database requirements
3. [CURRENT_STATE.md](CURRENT_STATE.md) - System status

### 🏗️ Architects
Start with:
1. [CURRENT_STATE.md](CURRENT_STATE.md) - Architecture overview
2. [QUERY_FLOW_DIAGRAM.txt](QUERY_FLOW_DIAGRAM.txt) - System flow
3. [../REFACTORING_PROPOSAL.md](../REFACTORING_PROPOSAL.md) - Future plans

---

**Last Updated**: November 4, 2025  
**Version**: Current as of refactoring proposal implementation
