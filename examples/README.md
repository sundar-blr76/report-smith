# Schema Intelligence Examples

## Current Examples

### ✅ `embedding_demo.py` - **Main Embedding Demo**

**Demonstrates the ReportSmith embedding system:**
- **Config-Driven Dimensions**: Uses `is_dimension: true` in column definitions
- **Unlimited Loading**: No artificial `max_values=100` or `min_count=1` limits  
- **Linked Dimensions**: Dimensions defined directly in table column definitions
- **Dictionary Support**: Ready for enhanced descriptions with predicates
- **Semantic Search**: Demonstrates search on unlimited dimension values

### ✅ `query_processing_example.py` - **Query Processing Pipeline Demo**

**Demonstrates complex natural language query processing:**

**Example Query**: "Show clients with >$1M in TruePotential funds and their transaction history"

Shows complete pipeline:
- **Query Decomposition**: Breaking natural language into semantic components
- **Schema Mapping**: Using embeddings to find relevant tables/columns
- **Dimension Matching**: Finding specific values mentioned in query
- **Table Identification**: Determining 6 required tables automatically
- **Join Planning**: Planning 5-table join path with relationships
- **SQL Generation**: Producing executable SQL with aggregations
- **Results Display**: Sample output formatting

Run it:
```bash
cd examples
./run_query_example.sh
```

### ✅ `knowledge_graph_demo.py` - **Knowledge Graph Demo** (NEW!)

**Demonstrates in-memory knowledge graph for schema relationships:**

Shows graph-based relationship discovery:
- **Graph Building**: Automatic construction from schema configuration
- **Path Finding**: BFS shortest path between any two tables
- **Multiple Paths**: DFS all possible paths with max depth limit
- **Relationship Analysis**: Outgoing/incoming edges for each table
- **SQL Generation**: Automatic JOIN clause generation from paths
- **Complex Queries**: Join path planning for multi-table queries

**Example Paths Found**:
- clients → transactions (2 hops)
- clients → funds (3 hops via accounts, holdings)
- clients → fund_managers (5 hops!)
- management_companies → transactions (2 hops)

**Statistics**:
- 174 nodes (13 tables + 161 columns)
- 30 relationships (auto-inferred from schema)
- Bidirectional path finding
- Multiple path discovery

Run it:
```bash
cd examples
./run_knowledge_graph_demo.sh
```

---

### Quick Run

**Using the run script (RECOMMENDED - with logging)**
```bash
cd examples
./run_embedding_demo.sh

# Output is shown on screen AND saved to:
# examples/logs/embedding_demo_YYYYMMDD_HHMMSS.log
```

**View the latest log:**
```bash
# Quick view of latest log
cd examples
./view_latest_log.sh

# Or manually
ls -lt examples/logs/*.log | head -1    # Find latest
cat examples/logs/embedding_demo_*.log  # View it
```

**Manual run (without logging)**
```bash
# From project root
source venv/bin/activate
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"
python3 examples/embedding_demo.py
```

**Sample Output:**
```
✓ Identified 4 dimensions from column markers
  - funds.fund_type: 10 values loaded (ALL, no limits)
  - funds.risk_rating: 3 values loaded
  - clients.client_type: 3 values loaded  
  - fund_managers.performance_rating: 46 values loaded

🔍 Query: 'equity investments' → finds 'Equity Growth', 'Equity Value'
✅ Total: 62 dimension values loaded (no truncation)
```

---

## Overview

This directory contains examples demonstrating ReportSmith's embedding and semantic search capabilities.

## What's Implemented

### 1. Embedding System (`embedding_manager.py`)

**Purpose**: Manages vector embeddings for semantic search across:
- Schema metadata (tables, columns from YAML configs)
- Dimension values (actual data from databases)
- Business context (metrics, rules, sample queries)

**Key Features**:
- In-memory vector storage using ChromaDB
- Lazy loading of dimension values
- 24-hour cache TTL for dimension data
- Semantic similarity search

### 2. Dimension Loader (`dimension_loader.py`)

**Purpose**: Identifies and loads dimension columns from databases.

**Auto-identifies dimensions** based on:
- Column naming patterns (`*_type`, `*_status`, `*_category`, etc.)
- Known dimension fields (fund_type, client_type, etc.)
- Data types with limited cardinality

## Running the Demo

### Prerequisites
```bash
# Ensure environment variables are set
export FINANCIAL_TESTDB_HOST=192.168.29.69
export FINANCIAL_TESTDB_PORT=5432
# ... other DB variables (automatically set from ~/.bashrc)

# Activate virtual environment  
source venv/bin/activate
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"
```

### Execute Demo
```bash
# Run the embedding demo
python3 examples/embedding_demo.py
```

**Output demonstrates:**
- Config-driven dimension loading (is_dimension: true)
- Unlimited dimension values (ALL loaded, no truncation)
- Semantic search examples on complete datasets
- Dictionary table configuration guide

## Key System Improvements

### Before (Old System - Removed)
- Hardcoded dimension patterns in code
- Artificial `max_values=100` truncation  
- Separate dimensions section creating duplication
- Pattern matching for dimension identification

### After (Current System)
- Dimensions marked as `is_dimension: true` in column definitions
- ALL dimension values loaded (no artificial limits)
- Single source of truth in column definitions
- Dictionary table support with predicates
- Clean config-driven approach

## Integration with Main Application

The demo uses the same embedding system as the main ReportSmith application:

```bash
# Main application uses identical system
./restart.sh  # Shows same dimension loading

# Both load same 4 dimensions with 62 total values
# Both use config-driven approach with no limits
```

## How It Works

### Schema Embeddings
1. Parse YAML config files
2. Create searchable documents for each table/column
3. Embed using sentence-transformers
4. Store in ChromaDB

### Dimension Embeddings
1. Identify dimension columns from schema
2. Query database for distinct values + counts
3. Create searchable documents for each value
4. Embed and store with metadata
5. Cache for 24 hours (staleness acceptable)

### Semantic Search
1. User query → embedding
2. Vector similarity search in ChromaDB
3. Return top-k matches with scores
4. Use metadata for context (table, column, value, count)

## Benefits

- **Semantic Matching**: "equity" → "Equity Growth", "Equity Value"
- **Typo Tolerance**: "equty" still matches "Equity"
- **Context Awareness**: Understands "fees" in context of fee_transactions
- **Value Discovery**: Finds valid dimension values from actual data
- **Fast**: In-memory search, <100ms for most queries

## Next Steps

1. Integrate with query generation pipeline
2. Add relationship discovery
3. Build multi-step query planning
4. Create UI for query confirmation

## Implementation Details

**Vector Store**: ChromaDB (in-memory)
**Embedding Model**: sentence-transformers/all-MiniLM-L6-v2
**Embedding Size**: 384 dimensions
**Total Embeddings** (for fund_accounting app):
- Schema: 174 embeddings (13 tables, 161 columns)
- Dimensions: 15 values (from 3 dimension columns)
- Business Context: 10 embeddings

**Memory Usage**: ~1-2 MB for current dataset
