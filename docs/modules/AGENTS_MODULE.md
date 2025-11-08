# Agents Module - Functional Documentation

**Module Path**: `src/reportsmith/agents/`  
**Version**: 1.0  
**Last Updated**: November 7, 2025

---

## Overview

The `agents` module implements the multi-agent orchestration layer for ReportSmith. It uses LangGraph to coordinate a workflow of specialized agents that transform natural language questions into executable SQL queries.

### Purpose
- Orchestrate multi-stage query processing pipeline
- Manage state transitions between processing stages
- Coordinate interactions between specialized components
- Track performance metrics and error handling

### Key Components
- **MultiAgentOrchestrator**: LangGraph-based workflow coordinator
- **AgentNodes**: Individual processing stage implementations
- **QueryState**: Shared state object passed between agents

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────┐
│      MultiAgentOrchestrator              │
│  • Builds LangGraph workflow             │
│  • Manages state transitions             │
│  • Handles errors and retries            │
└──────────────┬──────────────────────────┘
               │
               │ uses
               ▼
┌─────────────────────────────────────────┐
│           AgentNodes                     │
│  ┌───────────────────────────────────┐  │
│  │ 1. analyze_intent                 │  │
│  │ 2. semantic_enrich                │  │
│  │ 3. semantic_filter                │  │
│  │ 4. refine_entities                │  │
│  │ 5. map_schema                     │  │
│  │ 6. plan_query                     │  │
│  │ 7. generate_sql                   │  │
│  │ 8. finalize                       │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

---

## Core Classes

### 1. MultiAgentOrchestrator

**File**: `orchestrator.py`

#### Description
Main orchestrator class that builds and executes the LangGraph workflow for query processing.

#### Responsibilities
- Build LangGraph state machine
- Coordinate agent execution
- Track state transitions
- Handle errors and logging

#### Constructor Parameters
- `intent_analyzer`: Hybrid intent analyzer for entity extraction
- `graph_builder`: Builder for knowledge graph construction
- `knowledge_graph`: In-memory graph of table relationships

#### Key Method: process_query()
Main entry point for processing natural language queries.

**Parameters:**
- `question` (str): Natural language question
- `request_id` (str, optional): Unique request identifier

**Returns**: Dictionary with SQL, results, timings, and errors

**Workflow**: intent → semantic → semantic_filter → refine → schema → plan → sql → finalize

---

### 2. AgentNodes

**File**: `nodes.py`

Collection of node functions implementing individual processing stages.

#### Node Functions Summary

| Node | Purpose | Duration | Input | Output |
|------|---------|----------|-------|--------|
| analyze_intent | Extract entities & intent | ~250ms | question | intent, entities |
| semantic_enrich | Vector similarity search | ~150ms | entities | semantic_results |
| semantic_filter | LLM filtering | ~2500ms | semantic_results | filtered_entities |
| refine_entities | Merge & validate | ~20ms | filtered_entities | refined_entities |
| map_schema | Map to DB schema | ~50ms | refined_entities | tables, columns |
| plan_query | Generate join paths | ~100ms | tables, columns | plan |
| generate_sql | Build SQL query | <1ms | plan | sql |
| finalize | Execute & format | ~500ms | sql | execution results |

---

## Performance Metrics

### Typical Query Processing Time

Total: ~3.6 seconds

**Breakdown:**
- LLM API calls (semantic_filter): 69% of total time (bottleneck)
- SQL Execution (finalize): 14%
- Intent Analysis: 7%
- Semantic Enrichment: 4%
- Query Planning: 3%
- Other stages: 3%

---

## Usage Example

```python
from reportsmith.agents import MultiAgentOrchestrator

orchestrator = MultiAgentOrchestrator(
    intent_analyzer=analyzer,
    graph_builder=builder,
    knowledge_graph=kg
)

result = orchestrator.process_query("Show AUM for equity funds")

if result['status'] == 'success':
    print(f"SQL: {result['sql']['query']}")
    print(f"Time: {result['timings_ms']['total']}ms")
else:
    print(f"Errors: {result['errors']}")
```

---

## Error Handling

The module handles multiple error types:
- Intent analysis errors (no entities, ambiguous intent)
- Semantic search errors (API failure, no matches)
- Schema mapping errors (table/column not found)
- SQL generation errors (invalid plan, validation failure)

All errors are logged with request ID for tracing.

---

**See Also:**
- [Query Processing Module](QUERY_PROCESSING_MODULE.md)
- [Schema Intelligence Module](SCHEMA_INTELLIGENCE_MODULE.md)
- [Low-Level Design](../LLD.md)
