# Query Orchestrator Module

## Overview

The Query Orchestrator is a LangChain-based system that orchestrates the analysis of natural language queries for SQL generation. It uses a set of MCP (Model Context Protocol) tools to perform entity identification, relationship discovery, context extraction, filter identification, and graph navigation.

## Components

### 1. Models (`models.py`)
Data models representing:
- **EntityInfo** - Identified entities (tables, columns, dimension values)
- **RelationshipInfo** - Table relationships
- **FilterInfo** - Filter conditions
- **ContextInfo** - Business context
- **QueryAnalysisResult** - Complete analysis result
- **QueryPlan** - SQL query execution plan
- **ConfidenceScore** - Confidence scoring

### 2. MCP Tools (`mcp_tools.py`)
Five specialized tools:

1. **EntityIdentificationTool**
   - Searches schema metadata
   - Matches dimension values
   - Returns relevance-scored entities

2. **RelationshipDiscoveryTool**
   - Loads relationships from app.yaml
   - Filters to relevant tables
   - Returns join information

3. **ContextExtractionTool**
   - Identifies metrics and aggregations
   - Extracts temporal context
   - Identifies grouping requirements

4. **FilterIdentificationTool**
   - Matches dimension values to filters
   - Identifies temporal filters
   - Returns confidence-scored filters

5. **GraphNavigationTool**
   - Builds relationship graph
   - Finds shortest paths (BFS)
   - Generates JOIN clauses

### 3. Orchestrator (`orchestrator.py`)
Main coordinator that:
- Runs all MCP tools in sequence
- Performs iterative refinement (up to 3 iterations)
- Validates results against user query
- Generates SQL query plans
- Provides confidence scoring

## Usage

```python
from reportsmith.query_orchestrator import QueryOrchestrator
from reportsmith.schema_intelligence.embedding_manager import EmbeddingManager

# Initialize
embedding_manager = EmbeddingManager()
orchestrator = QueryOrchestrator(embedding_manager, app_config)

# Analyze query
analysis = orchestrator.analyze_query("Show top 5 equity funds by AUM")

# Generate SQL plan
plan = orchestrator.generate_query_plan(analysis)

# Validate and refine
refined_plan = orchestrator.validate_and_refine(plan)

print(refined_plan.sql_query)
```

## Key Features

- **Iterative Refinement** - Up to 3 iterations to improve confidence
- **Confidence Scoring** - HIGH/MEDIUM/LOW based on multiple factors
- **Graph Navigation** - BFS-based path finding between tables
- **Semantic Search** - Uses embeddings for entity matching
- **Modular Design** - Each tool is independent and testable

## Testing

Run tests:
```bash
python tests/test_orchestrator_models.py
```

All tests should pass:
```
✓ Models Import
✓ EntityInfo Creation
✓ RelationshipInfo Creation
✓ FilterInfo Creation
✓ QueryAnalysisResult Creation
✓ QueryPlan Creation
```

## Example

See `examples/orchestrator_demo.py` for a complete demonstration.

## Documentation

Full documentation: `docs/QUERY_ORCHESTRATOR.md`

## Architecture

```
User Query → EntityIdentificationTool → RelationshipDiscoveryTool 
           → ContextExtractionTool → FilterIdentificationTool 
           → GraphNavigationTool → QueryPlan → SQL
```

## Dependencies

- EmbeddingManager (from schema_intelligence)
- Application config (relationships, schema)
- Logger (from reportsmith.logger)

## Future Enhancements

- LangChain agent integration
- LLM-based refinement
- Query caching
- Learning from feedback
- Multi-step query support
- Cross-database queries
