# Embedding Strategy for ReportSmith

## Problem Statement

When users ask natural language questions, we need to:
1. Match user terms to actual database columns/tables (e.g., "fund type" → `funds.fund_type`)
2. Match user-provided values to actual domain values (e.g., "equity funds" → `fund_type = 'Equity'`)
3. Handle semantic similarity (e.g., "stocks" should match "Equity")

## What We Embed

### 1. Schema Metadata (DDL-based)
**Purpose**: Table and column discovery

**Content per embedding**:
- Table name + column name + description
- Data type, constraints, examples
- Relationship information

**Example**:
```
Table: funds
Column: fund_type
Type: varchar
Description: Fund type/strategy
Examples: Equity, Fixed Income, Balanced, Money Market
Relationships: Referenced by holdings.fund_id
Common in queries: Filter by fund type, Group by fund type
```

### 2. Dimension Data (Value-based)
**Purpose**: Match user terms to actual database values

**Content per embedding**:
- Table.column identifier
- Actual value from database
- Contextual information

**Example**:
```
Source: funds.fund_type
Value: Equity
Context: Stock-based investments, equity funds
Related: stocks, equities, shares
Count: 15 funds
```

```
Source: funds.fund_type
Value: Fixed Income
Context: Bond funds, debt instruments
Related: bonds, fixed-income, debt securities
Count: 12 funds
```

### 3. Business Context
**Purpose**: Understand business intent and metrics

**Content per embedding**:
- Metric name and formula
- Business rule
- Sample query patterns

**Example**:
```
Metric: Total AUM
Formula: SUM(total_aum) FROM funds WHERE is_active = true
Context: Assets under management, total assets, managed funds
Used in: Fund summary reports, management dashboards
```

## Embedding Lifecycle

### Initial Load (On App Startup or Config Change)
1. **Schema Embeddings**: Parse schema.yaml → Create embeddings for all tables/columns
2. **Dimension Embeddings**: Query dimension tables → Embed distinct values
3. **Business Context**: Parse app.yaml → Embed metrics, rules, sample queries

### Refresh Strategy (Lazy Load)
- **Schema**: Refresh when config changes
- **Dimension Values**: 
  - Lazy load on first query
  - Cache with TTL (e.g., 24 hours for fund_type)
  - Acceptable staleness for semi-static dimensions
- **Business Context**: Refresh when config changes

### What Gets Embedded

#### High-Value Dimensions (Always)
- Fund types, client types, account types
- Transaction types, fee types
- Status fields (Active/Inactive, Open/Closed)
- Risk ratings, regulatory statuses

#### Low-Value Dimensions (On-Demand)
- Specific fund codes (too many, too dynamic)
- Client names (privacy, too many)
- Transaction IDs (too many, not useful for semantic search)

## Storage: In-Memory Vector DB

**Selected**: ChromaDB (in-memory mode)

**Rationale**:
- Limited scope (~200 tables max, ~50 dimensions per app)
- Fast semantic search
- No persistence overhead
- Can reconstruct from configs + dimension queries on startup
- Direct SQL queries still available for exact matches

**Size Estimation**:
- 200 tables × 15 columns avg = 3,000 schema embeddings
- 50 dimension fields × 10 values avg = 500 dimension embeddings
- 50 business context items
- **Total**: ~3,500 embeddings × 1536 dims (OpenAI) × 4 bytes ≈ **21 MB**

## Query Processing Flow

```
User Query: "Show me all equity funds managed by TruePotential"

Step 1: Embedding Search
├─ Schema Match: "equity funds" → funds.fund_type
├─ Dimension Match: "equity" → fund_type = 'Equity'
└─ Schema Match: "TruePotential" → management_companies.short_name

Step 2: Relationship Discovery
├─ funds.management_company_id → management_companies.id
└─ Need JOIN between funds and management_companies

Step 3: Query Construction
SELECT f.fund_code, f.fund_name, f.total_aum
FROM funds f
JOIN management_companies mc ON f.management_company_id = mc.id
WHERE f.fund_type = 'Equity'
AND mc.short_name = 'TruePotential'
AND f.is_active = true
```

## Complex Scenario: Multi-Step Navigation

```
User Query: "Total fees collected from clients invested in TruePotential equity funds last quarter"

Step 1: Entity Identification (via embeddings)
- Primary entities: fee_transactions, funds, management_companies
- Dimension values: 'Equity', 'TruePotential'
- Time filter: last quarter

Step 2: Relationship Path Discovery
fee_transactions → fund_id → funds
funds → management_company_id → management_companies
funds → fund_type = 'Equity'

Step 3: Query Generation
SELECT 
  SUM(ft.fee_amount) as total_fees,
  COUNT(DISTINCT ft.account_id) as client_count
FROM fee_transactions ft
JOIN funds f ON ft.fund_id = f.id
JOIN management_companies mc ON f.management_company_id = mc.id
WHERE f.fund_type = 'Equity'
AND mc.short_name = 'TruePotential'
AND ft.fee_period_start >= DATE_TRUNC('quarter', CURRENT_DATE - INTERVAL '3 months')
AND ft.fee_period_end < DATE_TRUNC('quarter', CURRENT_DATE)
AND ft.payment_status IN ('Paid', 'Pending')
```

## Implementation Approach

### 1. EmbeddingManager Class
```python
class EmbeddingManager:
    def __init__(self):
        self.chroma_client = chromadb.Client()  # In-memory
        self.collections = {
            'schema': None,
            'dimensions': None,
            'context': None
        }
    
    def load_schema_embeddings(self, schema_yaml):
        """Load table/column metadata"""
        
    def load_dimension_embeddings(self, app_id, table, column):
        """Lazy load dimension values from actual database"""
        
    def search_schema(self, query, top_k=5):
        """Find relevant tables/columns"""
        
    def search_dimensions(self, query, column_hint=None, top_k=3):
        """Find matching dimension values"""
```

### 2. Dimension Loader
```python
def load_dimension_values(db_instance, table, column, max_values=100):
    """
    Query actual database for dimension values
    
    SELECT DISTINCT {column}, COUNT(*) as count
    FROM {table}
    GROUP BY {column}
    HAVING COUNT(*) > 5  -- Filter rare values
    ORDER BY count DESC
    LIMIT {max_values}
    """
```

### 3. Embedding Content Template
```python
def create_dimension_embedding(table, column, value, count, config):
    """
    Create searchable text for dimension value:
    
    - Column full path: {table}.{column}
    - Value: {value}
    - Description: {from schema config}
    - Synonyms: {if defined in config}
    - Context: {business context if available}
    - Frequency: Appears in {count} records
    """
```

## Benefits

1. **Semantic Matching**: "stocks" → "Equity", "bonds" → "Fixed Income"
2. **Typo Tolerance**: "Equty" still matches "Equity"
3. **Context Awareness**: Understands "fees" in context of fee_transactions
4. **Relationship Discovery**: Knows how to navigate from clients → accounts → holdings → funds
5. **Value Validation**: Can suggest valid values if user provides invalid one

## Limitations & Trade-offs

1. **Staleness**: Dimension values may be up to 24 hours old (acceptable for semi-static data)
2. **No Complex Queries**: Embeddings don't handle complex WHERE conditions directly
3. **Limited to Known Values**: Won't help with free-text fields like client names
4. **Rebuild on Schema Change**: Need to regenerate embeddings when schema changes

## Decision: In-Memory with Lazy Load

**Chosen**: ChromaDB in-memory mode with lazy dimension loading

**Advantages**:
- Fast startup
- No persistence complexity
- Easy to refresh
- Direct SQL still available for exact matches
- Semantic similarity where it matters

**Trade-offs**:
- Rebuilds on app restart (acceptable, fast)
- Limited to semi-static dimensions
- Not suitable for highly dynamic data

---

*This strategy balances semantic search capabilities with practical implementation constraints.*
