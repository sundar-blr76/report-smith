# ReportSmith C4 Architecture Documentation

This document provides C4 model architecture diagrams for the ReportSmith system. The C4 model provides a hierarchical set of software architecture diagrams at different levels of abstraction.

## What is the C4 Model?

The C4 model is a way to create maps of your code at various levels of detail, similar to how Google Maps lets you zoom in and out. It consists of:

1. **Context** - The big picture showing how the system fits into the world
2. **Container** - The high-level technology choices and how they communicate
3. **Component** - The major structural building blocks and their interactions
4. **Code** - Class diagrams and implementation details (optional)

## Viewing the Diagrams

The diagrams are written in PlantUML format (`.puml` files). You can view them using:

### Online Viewers
- [PlantUML Online Editor](http://www.plantuml.com/plantuml/uml/)
- [PlantText](https://www.planttext.com/)

### IDE Plugins
- **VS Code**: Install "PlantUML" extension by jebbs
- **IntelliJ IDEA**: Built-in PlantUML support
- **Eclipse**: Install PlantUML plugin

### Command Line
```bash
# Install PlantUML (requires Java)
sudo apt-get install plantuml

# Generate PNG from PUML
plantuml docs/architecture/c4-context.puml
plantuml docs/architecture/c4-container.puml
plantuml docs/architecture/c4-component.puml
```

### GitHub Integration
GitHub can render PlantUML diagrams directly in markdown using the PlantUML proxy:

```markdown
![C4 Context](http://www.plantuml.com/plantuml/proxy?src=https://raw.githubusercontent.com/YOUR_USERNAME/report-smith/main/docs/architecture/c4-context.puml)
```

## Available Diagrams

This documentation includes the following PlantUML diagrams:

### C4 Model Diagrams
1. **[c4-context.puml](c4-context.puml)** - Level 1: System Context
2. **[c4-container.puml](c4-container.puml)** - Level 2: Container Architecture
3. **[c4-component.puml](c4-component.puml)** - Level 3: Component Details

### Supplementary Diagrams
4. **[workflow-diagram.puml](workflow-diagram.puml)** - 8-Stage Query Processing Workflow
5. **[data-flow-diagram.puml](data-flow-diagram.puml)** - Sequence diagram showing data flow and interactions

## Architecture Overview

### Level 1: System Context Diagram

**File**: [`c4-context.puml`](c4-context.puml)

**Purpose**: Shows ReportSmith in the context of its users and external systems.

**Key Elements**:
- **Users**: Business users (analysts, fund managers) and developers/admins
- **ReportSmith System**: The intelligent NL-to-SQL system
- **External Systems**: 
  - OpenAI API (embeddings and LLM)
  - Google Gemini API (LLM for intent analysis)
  - PostgreSQL, Oracle, SQL Server (target databases)

**Key Relationships**:
- Users ask questions via UI/API
- System queries external LLM providers for intelligence
- System executes SQL against multiple database types

### Level 2: Container Diagram

**File**: [`c4-container.puml`](c4-container.puml)

**Purpose**: Shows the high-level technology choices and how containers communicate.

**Key Containers**:

1. **Streamlit UI** (Port 8501)
   - Interactive web interface for end users
   - Python/Streamlit framework

2. **FastAPI Server** (Port 8000)
   - REST API server for programmatic access
   - Python/FastAPI framework

3. **LangGraph Orchestrator**
   - Multi-agent workflow engine
   - Coordinates the 8-step query processing pipeline

4. **Query Processing**
   - Intent analysis (hybrid approach)
   - SQL generation and validation
   - Domain value enrichment

5. **Schema Intelligence**
   - Embedding management for semantic search
   - Knowledge graph for schema relationships
   - Dimension loaders for domain values

6. **Query Execution Engine**
   - SQL execution via SQLAlchemy
   - Result formatting and presentation

7. **ChromaDB**
   - Vector database for semantic search
   - Stores embeddings of schema metadata

8. **Configuration Files**
   - YAML-based application configs
   - Schema definitions and entity mappings

**Key Flows**:
- UI/API → FastAPI → Orchestrator → Processing Modules → Execution
- Processing modules interact with ChromaDB for semantic search
- Execution engine connects to target databases

### Level 3: Component Diagram

**File**: [`c4-component.puml`](c4-component.puml)

**Purpose**: Shows the major structural building blocks within containers.

**Key Component Groups**:

#### 1. LangGraph Orchestrator
- **MultiAgentOrchestrator**: Main workflow coordinator
- **Agent Nodes**: 8 processing nodes in the pipeline
  1. Intent Analysis
  2. Semantic Enrichment
  3. Semantic Filtering
  4. Entity Refinement
  5. Schema Mapping
  6. Query Planning
  7. SQL Generation
  8. Finalization

#### 2. Query Processing Components
- **HybridIntentAnalyzer**: Combines local mappings + semantic search + LLM
- **LLMIntentAnalyzer**: Deep intent understanding using Gemini/OpenAI
- **DomainValueEnricher**: Adds domain-specific values
- **SQLGenerator**: Orchestrates SQL construction
- **SQLValidator**: Validates syntax and semantics

**SQL Generation Sub-components**:
- **SelectBuilder**: Constructs SELECT clauses with aggregations
- **JoinBuilder**: Builds optimal JOIN paths from knowledge graph
- **FilterBuilder**: Creates WHERE clauses with auto-filters
- **ModifiersBuilder**: Adds GROUP BY, ORDER BY, LIMIT

#### 3. Schema Intelligence Components
- **EmbeddingManager**: Manages OpenAI/local embeddings
- **SchemaKnowledgeGraph**: NetworkX-based graph representation
- **KnowledgeGraphBuilder**: Constructs graphs from YAML configs
- **DimensionLoader**: Loads reference data from databases

#### 4. Query Execution Components
- **SQLExecutor**: Executes SQL using SQLAlchemy
- **ResultFormatter**: Formats results for display

#### 5. Configuration System
- **ConfigurationManager**: Loads YAML configurations
- **ConnectionManager**: Database connection pooling

#### 6. Utilities
- **Logger**: Structured logging with request ID tracking
- **LLMTracker**: Tracks LLM usage, tokens, and costs
- **CacheManager**: Query result caching (LRU/Redis/Disk)

## Query Processing Flow

**See Also**: [`workflow-diagram.puml`](workflow-diagram.puml) for detailed visual workflow

The system processes queries through an 8-stage LangGraph workflow:

```
1. Intent Analysis
   ↓ (extracts entities, metrics, dimensions, filters)
2. Semantic Enrichment
   ↓ (searches embeddings for unmapped entities)
3. Semantic Filtering
   ↓ (LLM validates and filters results)
4. Entity Refinement
   ↓ (refines entity mappings)
5. Schema Mapping
   ↓ (maps entities to tables/columns)
6. Query Planning
   ↓ (generates join paths using knowledge graph)
7. SQL Generation
   ↓ (builds executable SQL with auto-filters)
8. Execution & Finalization
   ↓ (runs SQL, formats results)
Results
```

### Example Query Flow

**See Also**: [`data-flow-diagram.puml`](data-flow-diagram.puml) for detailed sequence diagram

**User Question**: "Show AUM for all equity funds"

**Processing Steps**:
1. **Intent Analysis** (Hybrid): Identifies intent=aggregate, metric="AUM", dimension="equity"
2. **Semantic Enrichment** (ChromaDB): Searches vectors, finds "AUM" → `funds.total_aum` (0.98 similarity)
3. **Semantic Filtering** (Gemini LLM): Validates "equity" → `funds.fund_type='Equity Growth'`
4. **Entity Refinement**: Confirms mappings against schema
5. **Schema Mapping**: Maps to table `funds`, columns `total_aum`, `fund_type`
6. **Query Planning** (NetworkX): Determines single table query, no joins
7. **SQL Generation**: Builds `SELECT SUM(total_aum)... WHERE fund_type='Equity Growth' AND is_active=true GROUP BY fund_type`
8. **Execution**: Runs SQL, formats results, tracks LLM usage

**LLM Usage**: 3 calls, 1,247 tokens, $0.003, 1,850ms latency

## Technology Stack

### Core Technologies
- **Python 3.12+**: Primary development language
- **LangGraph**: Multi-agent orchestration framework
- **FastAPI**: Modern REST API framework
- **Streamlit**: Interactive web UI framework

### AI/ML Technologies
- **OpenAI API**: Embeddings and LLM capabilities
- **Google Gemini API**: LLM for intent analysis
- **ChromaDB**: Vector database for semantic search
- **sentence-transformers**: Local embedding models

### Database Technologies
- **PostgreSQL**: Metadata storage and target database
- **SQLAlchemy**: Database abstraction and connection pooling
- **Oracle**: Optional target database
- **SQL Server**: Optional target database

### Development Tools
- **pytest**: Testing framework
- **structlog**: Structured logging
- **pydantic**: Data validation
- **NetworkX**: Graph algorithms for knowledge graph

## Design Principles

### 1. Multi-Agent Architecture
- Uses LangGraph for orchestration
- Each stage is a specialized agent
- Clear separation of concerns
- Extensible and maintainable

### 2. Hybrid Intelligence
- Combines multiple approaches for accuracy:
  - Local entity mappings (fast, deterministic)
  - Semantic search with embeddings (flexible)
  - LLM reasoning (intelligent, context-aware)

### 3. Configuration-Driven
- YAML-based schema definitions
- No code changes for new schemas
- Version-controlled configurations

### 4. Observability First
- Request ID tracking throughout
- LLM usage and cost tracking
- Comprehensive structured logging
- Detailed debugging information

### 5. Performance Optimization
- Query result caching (LRU/Redis/Disk)
- Connection pooling
- Adaptive LLM model selection
- Fast path for simple queries

## Key Architectural Patterns

### 1. Pipeline Pattern
The LangGraph orchestrator implements a pipeline pattern with 8 sequential stages, each transforming the state.

### 2. Strategy Pattern
Multiple intent analyzers (local, semantic, LLM) with a hybrid strategy that combines them.

### 3. Builder Pattern
SQL generation uses multiple builders (SELECT, JOIN, WHERE, modifiers) to construct complex SQL.

### 4. Repository Pattern
Connection manager and configuration manager abstract data access.

### 5. Observer Pattern
Logger and LLM tracker observe operations across components.

## Security Considerations

### SQL Injection Prevention
- Parameterized queries
- Input validation
- SQL syntax validation

### API Key Management
- Environment variables for API keys
- No hardcoded credentials
- Secure credential storage

### Database Access
- Connection pooling with limits
- Query timeout enforcement
- Read-only access recommended for target databases

## Scalability Considerations

### Horizontal Scaling
- Stateless API design
- External vector database (ChromaDB)
- Shared configuration files

### Performance Optimization
- Query result caching
- Embedding caching in ChromaDB
- Connection pooling
- Async API endpoints

### Resource Management
- LLM call tracking and optimization
- Adaptive model selection (faster models for simple queries)
- Cache-first approach for repeated queries

## Extensibility Points

### Adding New Databases
1. Add database config to YAML
2. Update connection manager
3. No code changes required

### Adding New Agents/Nodes
1. Add node function to `AgentNodes` class
2. Update graph in `MultiAgentOrchestrator._build_graph()`
3. Define state transformations

### Custom SQL Generation
1. Create new builder component
2. Integrate into `SQLGenerator`
3. Update configuration as needed

### Custom Embeddings
1. Implement embedding provider
2. Update `EmbeddingManager`
3. Configure in settings

## Related Documentation

- [README.md](../../README.md) - Main project documentation
- [ARCHITECTURE.md](../ARCHITECTURE.md) - Detailed architecture documentation
- [SETUP.md](../../SETUP.md) - Setup and installation guide
- [DATABASE_SCHEMA.md](../DATABASE_SCHEMA.md) - Database schema details
- [LATENCY_IMPROVEMENTS.md](../LATENCY_IMPROVEMENTS.md) - Performance optimization
- [HLD.md](../HLD.md) - High-level design document
- [LLD.md](../LLD.md) - Low-level design document

## Maintenance Notes

### Keeping Diagrams Updated
When making architectural changes:

1. Update relevant `.puml` files
2. Regenerate diagrams if needed
3. Update this documentation
4. Keep diagrams in sync with code

### Best Practices
- Use consistent naming across diagrams
- Keep diagrams at appropriate level of detail
- Update diagrams before major code changes
- Review diagrams during code reviews
- Version control all diagram sources

## Questions or Feedback?

For questions or suggestions about the architecture, please open an issue on GitHub or contact the development team.

---

**Last Updated**: 2025-12-15  
**Maintained By**: ReportSmith Development Team
