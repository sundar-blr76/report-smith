# ReportSmith Architecture Documentation

This directory contains the C4 model architecture diagrams and documentation for the ReportSmith system.

## Contents

### Main Documentation
- **[C4_ARCHITECTURE.md](C4_ARCHITECTURE.md)** - Complete C4 architecture documentation with detailed explanations
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Quick reference guide for the architecture
- **[VIEWING_GUIDE.md](VIEWING_GUIDE.md)** - How to view and work with PlantUML diagrams
- **[DIAGRAM_SELECTION_GUIDE.md](DIAGRAM_SELECTION_GUIDE.md)** - Choose the right diagram for your needs

### C4 Model Diagrams
- **[c4-context.puml](c4-context.puml)** - Level 1: System Context diagram
- **[c4-container.puml](c4-container.puml)** - Level 2: Container diagram
- **[c4-component.puml](c4-component.puml)** - Level 3: Component diagram

### Supplementary Diagrams
- **[workflow-diagram.puml](workflow-diagram.puml)** - Detailed 8-stage query processing workflow
- **[data-flow-diagram.puml](data-flow-diagram.puml)** - Sequence diagram showing component interactions and data flow

## Quick Start

### Viewing the Diagrams

#### Option 1: Online PlantUML Editor
1. Copy the contents of any `.puml` file
2. Paste into [PlantUML Online Editor](http://www.plantuml.com/plantuml/uml/)
3. View the rendered diagram

#### Option 2: VS Code
1. Install the "PlantUML" extension by jebbs
2. Open any `.puml` file
3. Press `Alt+D` to preview

#### Option 3: Command Line
```bash
# Install PlantUML (requires Java)
sudo apt-get install plantuml

# Generate PNG images
plantuml c4-context.puml
plantuml c4-container.puml
plantuml c4-component.puml
```

## C4 Model Overview

The C4 model provides hierarchical views of the architecture:

### Level 1: Context Diagram
Shows ReportSmith in the context of users and external systems (OpenAI, Gemini, databases).

### Level 2: Container Diagram
Shows the major technology containers:
- Streamlit UI (Port 8501)
- FastAPI Server (Port 8000)
- LangGraph Orchestrator
- Query Processing
- Schema Intelligence
- Query Execution
- ChromaDB (vector database)

### Level 3: Component Diagram
Shows the internal components and their interactions:
- Multi-agent orchestration nodes
- Intent analyzers (hybrid, LLM, semantic)
- SQL generation components (SELECT, JOIN, WHERE builders)
- Schema intelligence (embeddings, knowledge graph)
- Configuration and utilities

## Key Features

✅ **Multi-Agent Architecture**: LangGraph-based workflow with 8 processing stages
✅ **Hybrid Intelligence**: Combines local mappings, semantic search, and LLM reasoning
✅ **Vector Search**: ChromaDB for semantic understanding
✅ **Knowledge Graph**: NetworkX-based schema relationship modeling
✅ **Observability**: Request tracking, LLM usage monitoring, structured logging

## Architecture Principles

1. **Configuration-Driven**: YAML-based schemas, no code changes needed
2. **Multi-Database Support**: PostgreSQL, Oracle, SQL Server
3. **Extensible**: Easy to add new agents, builders, or databases
4. **Performance**: Caching, connection pooling, adaptive LLM selection
5. **Security**: SQL injection prevention, parameterized queries

## Related Documentation

- [Main README](../../README.md)
- [ARCHITECTURE.md](../ARCHITECTURE.md) - Detailed architecture documentation
- [HLD.md](../HLD.md) - High-level design
- [LLD.md](../LLD.md) - Low-level design
- [DATABASE_SCHEMA.md](../DATABASE_SCHEMA.md) - Database schema details

## Contributing

When updating the architecture:
1. Update the relevant `.puml` files
2. Update the C4_ARCHITECTURE.md documentation
3. Keep diagrams consistent with the code
4. Test that diagrams render correctly

---

**Last Updated**: 2025-12-15
