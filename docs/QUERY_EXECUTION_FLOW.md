# Query Execution Flow - Report Data Extraction

## Overview
This document describes the step-by-step process for extracting report data using semantic search with an in-memory vector database (ChromaDB).

---

## Architecture Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER QUERY                                │
│  "Show me top 5 funds by AUM with their managers"               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   1. QUERY UNDERSTANDING                         │
│  • Parse natural language query                                 │
│  • Identify entities (funds, managers, AUM)                     │
│  • Identify operations (top 5, sort by AUM)                     │
│  • Identify output requirements (fund + manager info)           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              2. SCHEMA RETRIEVAL (Vector Search)                 │
│  ┌───────────────────────────────────────────────────┐          │
│  │  ChromaDB (In-Memory Vector Store)                │          │
│  │  • Table embeddings (funds, managers, etc)        │          │
│  │  • Column embeddings (aum, fund_name, etc)        │          │
│  │  • Relationship embeddings (FK references)        │          │
│  │  • Business term embeddings (synonyms)            │          │
│  └───────────────────────────────────────────────────┘          │
│                                                                  │
│  Query: "funds AUM managers"                                    │
│  ↓                                                               │
│  Results:                                                        │
│  1. funds.total_aum (score: 0.95)                              │
│  2. funds.fund_name (score: 0.88)                              │
│  3. fund_manager_assignments (score: 0.87)                     │
│  4. fund_managers.first_name, last_name (score: 0.85)          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              3. QUERY PLAN GENERATION                            │
│  • Identify master entity: funds                                │
│  • Identify aggregation: ORDER BY total_aum DESC LIMIT 5        │
│  • Identify join path: funds → fund_manager_assignments         │
│                         → fund_managers                          │
│  • Select columns:                                              │
│    - funds: id, fund_name, total_aum                           │
│    - fund_managers: first_name, last_name                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              4. SQL GENERATION                                   │
│                                                                  │
│  SELECT                                                          │
│    f.fund_name,                                                 │
│    f.total_aum,                                                 │
│    fm.first_name || ' ' || fm.last_name AS manager_name        │
│  FROM funds f                                                   │
│  LEFT JOIN fund_manager_assignments fma                         │
│    ON f.id = fma.fund_id AND fma.is_primary_manager = true    │
│  LEFT JOIN fund_managers fm                                     │
│    ON fma.fund_manager_id = fm.id                              │
│  WHERE f.is_active = true                                       │
│  ORDER BY f.total_aum DESC                                      │
│  LIMIT 5;                                                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              5. EXECUTION TRACKING                               │
│  • Create execution_session record                              │
│  • Create execution_step record                                 │
│  • Log query_execution record                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              6. DATABASE EXECUTION                               │
│  • Connect to financial_testdb (from config)                    │
│  • Execute SQL query                                            │
│  • Capture metrics (rows examined, duration)                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              7. RESULT FORMATTING                                │
│  • Transform to requested format (table, JSON, CSV)             │
│  • Apply template if specified                                  │
│  • Add metadata (execution time, row count)                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              8. RESPONSE DELIVERY                                │
│  ┌────────────────────────────────────────────────┐             │
│  │ Fund Name          │ Total AUM   │ Manager     │             │
│  ├────────────────────┼─────────────┼─────────────┤             │
│  │ Tech Pioneer Fund  │ 500.0M      │ John Smith  │             │
│  │ Growth Equity Fund │ 350.0M      │ Jane Doe    │             │
│  │ ...                │ ...         │ ...         │             │
│  └────────────────────────────────────────────────┘             │
│                                                                  │
│  Execution time: 45ms | Rows: 5                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Multi-Step Query Example

### Complex Query
**User:** "Compare AUM growth for equity funds vs fixed income funds over the last year"

### Execution Steps

```
Step 1: Entity Identification
├─ Master entities: funds, performance_reports
├─ Filter criteria: fund_type IN ('Equity', 'Fixed Income')
├─ Time range: last 12 months
└─ Aggregation: SUM(AUM) by fund_type, month

Step 2: Vector Search Results
Query: "AUM growth equity fixed income year"
├─ funds.fund_type (0.92)
├─ funds.total_aum (0.91)
├─ performance_reports.total_aum (0.90)
├─ performance_reports.report_date (0.85)
└─ performance_reports.period_type (0.82)

Step 3: Multi-Query Plan
Query 1: Get equity fund AUM trend
  SELECT report_date, SUM(total_aum)
  FROM performance_reports pr
  JOIN funds f ON pr.fund_id = f.id
  WHERE f.fund_type = 'Equity'
    AND report_date >= NOW() - INTERVAL '1 year'
  GROUP BY report_date
  ORDER BY report_date

Query 2: Get fixed income fund AUM trend
  [Similar query with fund_type = 'Fixed Income']

Query 3: Calculate growth rates
  [Post-processing in application layer]

Step 4: Execution
├─ Execute Query 1 → Result Set A (12 rows)
├─ Execute Query 2 → Result Set B (12 rows)
└─ Merge and calculate growth → Final Result

Step 5: Result
┌──────────┬─────────────┬──────────────┬────────────┐
│ Month    │ Equity AUM  │ FI AUM       │ Growth %   │
├──────────┼─────────────┼──────────────┼────────────┤
│ 2024-01  │ 1200.0M     │ 800.0M       │ -          │
│ 2024-02  │ 1250.0M     │ 820.0M       │ E: +4.2%   │
│ ...      │ ...         │ ...          │ FI: +2.5%  │
└──────────┴─────────────┴──────────────┴────────────┘
```

---

## Vector Store Structure

### Embedding Strategy

```yaml
# Table-level embeddings
funds_table:
  content: "funds table stores master fund information including fund code, name, type, AUM, NAV, risk rating, benchmark"
  metadata:
    type: table
    application: fund_accounting
    database: financial_testdb
    row_count: 100

# Column-level embeddings
funds_total_aum:
  content: "total_aum is total assets under management for the fund, numeric value in base currency"
  metadata:
    type: column
    table: funds
    data_type: numeric
    business_terms: [AUM, assets, fund size]

# Relationship embeddings
funds_managers_relationship:
  content: "funds are managed by fund managers through fund_manager_assignments table with is_primary_manager flag"
  metadata:
    type: relationship
    from_table: funds
    to_table: fund_managers
    via_table: fund_manager_assignments
```

### Similarity Search Process

```python
# Pseudo-code for semantic search
def find_relevant_schema(user_query: str):
    # 1. Embed user query
    query_embedding = embed_text(user_query)
    
    # 2. Search ChromaDB
    results = chroma_collection.query(
        query_embeddings=[query_embedding],
        n_results=10,
        where={"application": "fund_accounting"}
    )
    
    # 3. Group by relevance
    tables = filter_by_type(results, "table")
    columns = filter_by_type(results, "column")
    relationships = filter_by_type(results, "relationship")
    
    # 4. Build schema context
    return {
        "primary_tables": tables[:3],
        "relevant_columns": columns,
        "join_paths": relationships
    }
```

---

## Query Optimization Patterns

### Pattern 1: Single Entity Query
```
User Query → Identify Table → Select Columns → Execute
Simple, 1 database query
```

### Pattern 2: Related Entities
```
User Query → Identify Tables → Find Join Path → Execute
Moderate, 1 joined query
```

### Pattern 3: Aggregation with Grouping
```
User Query → Identify Metrics → Identify Dimensions → Execute with GROUP BY
Moderate, 1 aggregated query
```

### Pattern 4: Cross-Time Analysis
```
User Query → Identify Time Series → Execute Multiple Queries → Merge Results
Complex, 2-3 queries + post-processing
```

### Pattern 5: Cross-Database Comparison
```
User Query → Identify Applications → Execute Parallel Queries → Merge Results
Complex, N parallel queries (N = number of databases)
```

---

## Error Handling

```
┌─────────────────────────────────────┐
│ Query Understanding Failed          │
│ → Ask clarifying questions          │
│ → Suggest similar queries           │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ No Matching Schema Found            │
│ → Show available tables             │
│ → Suggest alternative queries       │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Ambiguous Query                     │
│ → Present multiple interpretations  │
│ → Ask user to select                │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ SQL Execution Failed                │
│ → Log error                         │
│ → Attempt query simplification      │
│ → Return partial results if any     │
└─────────────────────────────────────┘
```

---

## Performance Characteristics

### In-Memory Vector Store (ChromaDB)
- **Load Time:** ~1-2 seconds for 200 tables
- **Search Time:** <50ms for semantic search
- **Memory Usage:** ~100-500MB depending on schema size
- **Best For:** Development, single-user, limited schema size

### Trade-offs
✅ **Advantages:**
- Fast semantic search
- No external dependencies
- Simple setup and maintenance
- Good for prototyping

⚠️ **Limitations:**
- Data lost on restart (need reload)
- Limited scalability (1000s of tables would be slow)
- Single-process (not multi-user without coordination)

---

## Next Steps

1. **Implement schema loader** to populate ChromaDB from config files
2. **Build query understanding** using LLM with schema context
3. **Create SQL generator** from query plan
4. **Add execution engine** with tracking
5. **Implement result formatter** with templates
6. **Add caching layer** for frequently used queries
