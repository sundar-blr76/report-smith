# Query Orchestrator Workflow Visualization

## Complete End-to-End Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                           USER INPUT                                        │
│                                                                             │
│        "Show me top 5 equity funds by AUM with their managers"             │
│                                                                             │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        QUERY ORCHESTRATOR                                   │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  ITERATION 1: Initial Analysis                                     │    │
│  │                                                                    │    │
│  │  ┌──────────────────────────────────────────────────────────┐     │    │
│  │  │  ENTITY IDENTIFICATION TOOL                              │     │    │
│  │  ├──────────────────────────────────────────────────────────┤     │    │
│  │  │  • Search schema_metadata collection                     │     │    │
│  │  │    Query: "equity funds AUM managers"                    │     │    │
│  │  │                                                           │     │    │
│  │  │  Results:                                                │     │    │
│  │  │    1. funds (table) - score: 0.95                        │     │    │
│  │  │    2. funds.fund_type (column) - score: 0.92             │     │    │
│  │  │    3. funds.total_aum (column) - score: 0.94             │     │    │
│  │  │    4. fund_managers (table) - score: 0.88                │     │    │
│  │  │                                                           │     │    │
│  │  │  • Search dimension_values collection                    │     │    │
│  │  │    Query: "equity"                                       │     │    │
│  │  │                                                           │     │    │
│  │  │  Results:                                                │     │    │
│  │  │    1. funds.fund_type=Equity - score: 0.90              │     │    │
│  │  └──────────────────────────────────────────────────────────┘     │    │
│  │                        ↓                                          │    │
│  │  ┌──────────────────────────────────────────────────────────┐     │    │
│  │  │  CONTEXT EXTRACTION TOOL                                 │     │    │
│  │  ├──────────────────────────────────────────────────────────┤     │    │
│  │  │  • Search business_context collection                    │     │    │
│  │  │  • Identify keywords: "top 5" → LIMIT                    │     │    │
│  │  │  • Identify sorting: "by AUM" → ORDER BY DESC           │     │    │
│  │  │                                                           │     │    │
│  │  │  Context:                                                │     │    │
│  │  │    • Metric: None (no aggregation needed)                │     │    │
│  │  │    • Temporal: None                                      │     │    │
│  │  │    • Aggregation: None                                   │     │    │
│  │  │    • Ordering: total_aum DESC                            │     │    │
│  │  │    • Limit: 5                                            │     │    │
│  │  └──────────────────────────────────────────────────────────┘     │    │
│  │                        ↓                                          │    │
│  │  ┌──────────────────────────────────────────────────────────┐     │    │
│  │  │  FILTER IDENTIFICATION TOOL                              │     │    │
│  │  ├──────────────────────────────────────────────────────────┤     │    │
│  │  │  • Match dimension values to filters                     │     │    │
│  │  │                                                           │     │    │
│  │  │  Filters:                                                │     │    │
│  │  │    1. funds.fund_type = 'Equity' (confidence: HIGH)      │     │    │
│  │  │    2. funds.is_active = true (implicit)                  │     │    │
│  │  └──────────────────────────────────────────────────────────┘     │    │
│  │                        ↓                                          │    │
│  │  ┌──────────────────────────────────────────────────────────┐     │    │
│  │  │  RELATIONSHIP DISCOVERY TOOL                             │     │    │
│  │  ├──────────────────────────────────────────────────────────┤     │    │
│  │  │  • Load relationships from app.yaml                      │     │    │
│  │  │  • Filter to relevant tables: funds, fund_managers       │     │    │
│  │  │                                                           │     │    │
│  │  │  Relationships:                                          │     │    │
│  │  │    1. funds → fund_manager_assignments                   │     │    │
│  │  │       (funds.id = fma.fund_id)                           │     │    │
│  │  │    2. fund_manager_assignments → fund_managers           │     │    │
│  │  │       (fma.fund_manager_id = fm.id)                      │     │    │
│  │  └──────────────────────────────────────────────────────────┘     │    │
│  │                        ↓                                          │    │
│  │  ┌──────────────────────────────────────────────────────────┐     │    │
│  │  │  GRAPH NAVIGATION TOOL                                   │     │    │
│  │  ├──────────────────────────────────────────────────────────┤     │    │
│  │  │  • Build graph: funds ← fma → fund_managers              │     │    │
│  │  │  • Find paths: BFS from funds to fund_managers           │     │    │
│  │  │                                                           │     │    │
│  │  │  Path found (2 hops):                                    │     │    │
│  │  │    funds → fma → fund_managers                           │     │    │
│  │  │                                                           │     │    │
│  │  │  JOIN clauses:                                           │     │    │
│  │  │    1. JOIN fund_manager_assignments fma                  │     │    │
│  │  │       ON funds.id = fma.fund_id                          │     │    │
│  │  │    2. JOIN fund_managers fm                              │     │    │
│  │  │       ON fma.fund_manager_id = fm.id                     │     │    │
│  │  └──────────────────────────────────────────────────────────┘     │    │
│  │                        ↓                                          │    │
│  │  ┌──────────────────────────────────────────────────────────┐     │    │
│  │  │  CONFIDENCE CALCULATION                                  │     │    │
│  │  ├──────────────────────────────────────────────────────────┤     │    │
│  │  │  • Entity relevance: 0.92 (avg)           → 40% weight   │     │    │
│  │  │  • Entity completeness: 1.00 (5/5)        → 20% weight   │     │    │
│  │  │  • Relationship clarity: 1.00              → 20% weight   │     │    │
│  │  │  • Filter quality: 1.00                    → 10% weight   │     │    │
│  │  │  • Path quality: 1.00                      → 10% weight   │     │    │
│  │  │                                                           │     │    │
│  │  │  Overall Score: 0.87 → HIGH CONFIDENCE                   │     │    │
│  │  └──────────────────────────────────────────────────────────┘     │    │
│  │                                                                    │    │
│  │  Decision: HIGH confidence achieved → Stop iteration             │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       QUERY PLAN GENERATION                                 │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  Primary Table Identification                                      │    │
│  │  → funds (highest relevance entity)                                │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                        ↓                                                    │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  Column Selection                                                  │    │
│  │  → funds.id, funds.fund_name, funds.total_aum                      │    │
│  │  → fm.first_name, fm.last_name                                     │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                        ↓                                                    │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  JOIN Clause Generation                                            │    │
│  │  → JOIN fund_manager_assignments fma                               │    │
│  │     ON funds.id = fma.fund_id                                      │    │
│  │  → JOIN fund_managers fm                                           │    │
│  │     ON fma.fund_manager_id = fm.id                                 │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                        ↓                                                    │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  WHERE Clause Generation                                           │    │
│  │  → funds.fund_type = 'Equity'                                      │    │
│  │  → funds.is_active = true                                          │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                        ↓                                                    │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  ORDER BY Clause Generation                                        │    │
│  │  → funds.total_aum DESC                                            │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                        ↓                                                    │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  LIMIT Clause Generation                                           │    │
│  │  → LIMIT 5                                                         │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        VALIDATION & REFINEMENT                              │
│                                                                             │
│  Cross-check against user query:                                           │
│    ✓ Primary table identified (funds)                                      │
│    ✓ Columns selected (5 columns)                                          │
│    ✓ Joins complete (2 joins)                                              │
│    ✓ Filters applied (2 filters)                                           │
│    ✓ Ordering specified (DESC by AUM)                                      │
│    ✓ Limit applied (5)                                                     │
│                                                                             │
│  Result: VALID ✓                                                           │
│  Confidence: HIGH                                                           │
│                                                                             │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FINAL SQL QUERY                                    │
│                                                                             │
│  SELECT                                                                     │
│      funds.id,                                                              │
│      funds.fund_name,                                                       │
│      funds.total_aum,                                                       │
│      fm.first_name,                                                         │
│      fm.last_name                                                           │
│  FROM funds                                                                 │
│  JOIN fund_manager_assignments fma                                          │
│      ON funds.id = fma.fund_id                                              │
│  JOIN fund_managers fm                                                      │
│      ON fma.fund_manager_id = fm.id                                         │
│  WHERE                                                                      │
│      funds.fund_type = 'Equity'                                             │
│      AND funds.is_active = true                                             │
│  ORDER BY                                                                   │
│      funds.total_aum DESC                                                   │
│  LIMIT 5                                                                    │
│                                                                             │
│  Confidence: HIGH (0.87)                                                    │
│  Ready for execution ✓                                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Iterative Refinement Flow (When Needed)

```
┌─────────────────────────────────────────────────────────────────┐
│  ITERATION 1                                                    │
│  ├─ Initial analysis                                            │
│  ├─ Confidence: MEDIUM (0.65)                                   │
│  └─ Issues: Ambiguous filters, unclear relationships            │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  REFINEMENT SUGGESTIONS                                         │
│  ├─ "Consider adding more context to identify relevant tables"  │
│  ├─ "No clear path between tables - verify relationships"       │
│  └─ Apply refinements: Broaden entity search                    │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  ITERATION 2                                                    │
│  ├─ Re-run entity identification with broader search            │
│  ├─ Confidence: MEDIUM (0.72)                                   │
│  └─ Issues: Some filters still ambiguous                        │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  REFINEMENT SUGGESTIONS                                         │
│  ├─ "Clarify temporal filter"                                   │
│  └─ Apply refinements: Extract temporal context better          │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  ITERATION 3                                                    │
│  ├─ Re-run with improved temporal extraction                    │
│  ├─ Confidence: HIGH (0.82)                                     │
│  └─ Stop: HIGH confidence achieved ✓                           │
└─────────────────────────────────────────────────────────────────┘
```

## Confidence Scoring Details

```
┌─────────────────────────────────────────────────────────────────┐
│  CONFIDENCE CALCULATION                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Component                    Score    Weight   Contribution    │
│  ────────────────────────────────────────────────────────────   │
│  Entity Relevance (avg)       0.92     40%      0.368          │
│  Entity Completeness           1.00     20%      0.200          │
│  Relationship Clarity          1.00     20%      0.200          │
│  Filter Quality                1.00     10%      0.100          │
│  Path Quality                  1.00     10%      0.100          │
│  ────────────────────────────────────────────────────────────   │
│  TOTAL SCORE                                    0.968          │
│                                                                 │
│  Confidence Level: HIGH                                         │
│  Reasoning: "Strong entity matches and clear relationships"     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## MCP Tool Details

```
┌─────────────────────────────────────────────────────────────────┐
│  EntityIdentificationTool                                       │
├─────────────────────────────────────────────────────────────────┤
│  Input:  "Show me top 5 equity funds by AUM"                    │
│  Output: List[EntityInfo] with relevance scores                 │
│                                                                 │
│  Process:                                                       │
│    1. Embed query using sentence-transformer                    │
│    2. Search schema_metadata collection (ChromaDB)              │
│    3. Search dimension_values collection                        │
│    4. Rank by cosine similarity                                 │
│    5. Return top K entities                                     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  RelationshipDiscoveryTool                                      │
├─────────────────────────────────────────────────────────────────┤
│  Input:  ["funds", "fund_managers"]                             │
│  Output: List[RelationshipInfo]                                 │
│                                                                 │
│  Process:                                                       │
│    1. Load relationships from app.yaml                          │
│    2. Filter to tables in input list                            │
│    3. Include parent-child relationships                        │
│    4. Return with join information                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  ContextExtractionTool                                          │
├─────────────────────────────────────────────────────────────────┤
│  Input:  Query + Entities                                       │
│  Output: ContextInfo                                            │
│                                                                 │
│  Process:                                                       │
│    1. Search business_context embeddings                        │
│    2. Identify aggregation keywords (sum, avg, count)           │
│    3. Extract temporal phrases (last, previous, current)        │
│    4. Identify grouping requirements (by, per)                  │
│    5. Identify ordering (top, bottom)                           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  FilterIdentificationTool                                       │
├─────────────────────────────────────────────────────────────────┤
│  Input:  Query + Entities                                       │
│  Output: List[FilterInfo]                                       │
│                                                                 │
│  Process:                                                       │
│    1. Match dimension values from entities                      │
│    2. Identify temporal filters (date columns + temporal words) │
│    3. Extract range conditions (>, <, between)                  │
│    4. Assign confidence scores                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  GraphNavigationTool                                            │
├─────────────────────────────────────────────────────────────────┤
│  Input:  Start tables, Target tables, Relationships             │
│  Output: List[NavigationPath]                                   │
│                                                                 │
│  Process:                                                       │
│    1. Build adjacency graph from relationships                  │
│    2. Use BFS to find all paths                                 │
│    3. Limit to max_hops (default: 3)                            │
│    4. Score by path length (shorter = better)                   │
│    5. Generate JOIN clauses                                     │
└─────────────────────────────────────────────────────────────────┘
```

## Integration with Existing Systems

```
┌─────────────────────────────────────────────────────────────────┐
│                    ReportSmith Architecture                      │
│                                                                 │
│  ┌───────────────┐    ┌──────────────────┐                     │
│  │ Config System │───▶│ YAML Configs     │                     │
│  │ • Loader      │    │ • app.yaml       │                     │
│  │ • Models      │    │ • schema.yaml    │                     │
│  └───────┬───────┘    └──────────────────┘                     │
│          │                      │                               │
│          └──────────┬───────────┘                               │
│                     ▼                                           │
│  ┌──────────────────────────────────────┐                      │
│  │   Schema Intelligence                │                      │
│  │   • EmbeddingManager (ChromaDB)      │                      │
│  │   • DimensionLoader                  │                      │
│  └──────────┬───────────────────────────┘                      │
│             │                                                   │
│             ▼                                                   │
│  ┌──────────────────────────────────────┐                      │
│  │   QUERY ORCHESTRATOR ◀── NEW         │                      │
│  │   • 5 MCP Tools                      │                      │
│  │   • Iterative Refinement             │                      │
│  │   • SQL Generation                   │                      │
│  └──────────┬───────────────────────────┘                      │
│             │                                                   │
│             ▼                                                   │
│  ┌──────────────────────────────────────┐                      │
│  │   Database Layer                     │                      │
│  │   • ConnectionManager                │                      │
│  │   • Query Execution                  │                      │
│  └──────────────────────────────────────┘                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```
