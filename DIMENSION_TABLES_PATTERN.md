# Dimension Tables Pattern - Status and Beyond

## Your Key Insight

> "Status could possibly be a dimension table, let us cover that in"

**Absolutely right!** Status (and similar lookup columns) should often be proper dimension tables, not just VARCHAR columns with magic strings.

---

## The Problem with Simple VARCHAR Status

### Current Pattern (Problematic)
```sql
-- funds table
CREATE TABLE funds (
    id INTEGER PRIMARY KEY,
    name VARCHAR,
    status VARCHAR,  -- 'Active', 'Closed', 'Suspended' - magic strings!
    ...
);
```

**Problems:**
- ❌ No referential integrity
- ❌ Typos possible ('active' vs 'Active' vs 'ACTIVE')
- ❌ No description/metadata about what each status means
- ❌ Can't track status change history easily
- ❌ No display order, grouping, or categorization
- ❌ Hard to internationalize

---

## The Right Pattern: Status Dimension Table

### Proper Dimension Design

```sql
-- Status dimension table
CREATE TABLE fund_status_dim (
    status_id INTEGER PRIMARY KEY,
    status_code VARCHAR(20) UNIQUE NOT NULL,  -- 'ACTIVE', 'CLOSED', etc.
    status_name VARCHAR(50),                  -- 'Active', 'Closed'
    description TEXT,                         -- Rich description
    is_active BOOLEAN,                        -- For filtering active statuses
    display_order INTEGER,                    -- For UI sorting
    category VARCHAR(20),                     -- 'OPERATIONAL', 'TERMINAL', etc.
    icon VARCHAR(50),                         -- UI icon reference
    color_code VARCHAR(20),                   -- UI color coding
    created_date DATE,
    created_by VARCHAR(50),
    effective_date DATE,                      -- When this status became valid
    end_date DATE                             -- NULL for current statuses
);

-- Sample data
INSERT INTO fund_status_dim VALUES
(1, 'ACTIVE', 'Active', 'Fund is currently accepting investments and operating normally', 
 true, 1, 'OPERATIONAL', 'check-circle', 'green', '2020-01-01', 'system', '2020-01-01', NULL),
 
(2, 'SUSPENDED', 'Suspended', 'Fund temporarily not accepting new investments', 
 true, 2, 'OPERATIONAL', 'pause-circle', 'yellow', '2020-01-01', 'system', '2020-01-01', NULL),
 
(3, 'CLOSED', 'Closed', 'Fund permanently closed, no longer operating', 
 false, 3, 'TERMINAL', 'x-circle', 'red', '2020-01-01', 'system', '2020-01-01', NULL),
 
(4, 'LIQUIDATING', 'Liquidating', 'Fund in process of liquidation', 
 false, 4, 'TERMINAL', 'arrow-down', 'orange', '2020-01-01', 'system', '2020-01-01', NULL);

-- funds table (refactored)
CREATE TABLE funds (
    id INTEGER PRIMARY KEY,
    name VARCHAR,
    status_id INTEGER REFERENCES fund_status_dim(status_id),  -- FK!
    ...
);
```

---

## Benefits of Dimension Tables

### 1. **Referential Integrity**
```sql
-- Can't insert invalid status
INSERT INTO funds (name, status_id) VALUES ('Test Fund', 999);
-- ERROR: violates foreign key constraint
```

### 2. **Rich Metadata**
```sql
-- LLM can understand what each status means
SELECT status_code, description, category, is_active
FROM fund_status_dim;

-- LLM learns:
-- "ACTIVE means fund is operational and accepting investments"
-- "CLOSED is terminal state, not reversible"
```

### 3. **Easy Business Rules**
```sql
-- Get all operational funds (not just "Active")
SELECT f.*
FROM funds f
JOIN fund_status_dim s ON f.status_id = s.status_id
WHERE s.category = 'OPERATIONAL';  -- Includes Active AND Suspended

-- Or just active statuses
WHERE s.is_active = true;
```

### 4. **Status History with Milestoning**
```sql
-- Track status changes over time
CREATE TABLE fund_status_history (
    fund_id INTEGER,
    status_id INTEGER,
    effective_date DATE,
    end_date DATE,
    reason TEXT,
    changed_by VARCHAR(50)
);

-- Query: "What was the status of Fund X on 2023-06-15?"
SELECT s.status_name
FROM fund_status_history h
JOIN fund_status_dim s ON h.status_id = s.status_id
WHERE h.fund_id = X
  AND h.effective_date <= '2023-06-15'
  AND (h.end_date IS NULL OR h.end_date > '2023-06-15');
```

---

## Common Dimension Tables Beyond Status

### Standard Dimensions in Financial Systems

```sql
-- 1. Fund Status
fund_status_dim (status_id, status_code, status_name, description, is_active, ...)

-- 2. Transaction Type
transaction_type_dim (type_id, type_code, type_name, description, direction, ...)

-- 3. Account Type
account_type_dim (type_id, type_code, type_name, description, tax_treatment, ...)

-- 4. Risk Rating
risk_rating_dim (rating_id, rating_code, rating_name, description, score, ...)

-- 5. Currency
currency_dim (currency_id, currency_code, currency_name, symbol, decimal_places, ...)

-- 6. Country/Region
country_dim (country_id, country_code, country_name, region, tax_rules, ...)

-- 7. Fee Type
fee_type_dim (fee_type_id, fee_code, fee_name, description, calculation_method, ...)

-- 8. Performance Rating
performance_rating_dim (rating_id, rating_code, rating_name, min_value, max_value, ...)
```

---

## How Agentic Mapper Handles Dimension Tables

### Step 1: Discover Dimension References

```python
# LLM sees funds table schema
funds:
  columns:
    status_id:
      type: integer
      foreign_key: fund_status_dim.status_id  # AH! This is a dimension!
      description: "Fund operational status"

# LLM recognizes:
# "status_id is FK to fund_status_dim - this is a dimension table lookup"
```

### Step 2: Enrich with Dimension Context

```python
# User query: "Show active funds"
# Entity: "active"

# LLM iterative process:
Iteration 1: Semantic search for "active"
  - Finds: funds.status_id (0.65) - moderate match
  
Iteration 2: Check if this is a dimension
  - Discovers: status_id → fund_status_dim FK
  - Action: GET_DIMENSION_TABLE_VALUES
  
Iteration 3: Load dimension table data
  Response:
    fund_status_dim has:
      - status_code: 'ACTIVE' (is_active=true)
      - status_code: 'SUSPENDED' (is_active=true)  
      - status_code: 'CLOSED' (is_active=false)
      - status_code: 'LIQUIDATING' (is_active=false)
  
Iteration 4: LLM matches "active" to dimension
  Reasoning:
    "User said 'active funds'. I found fund_status_dim with:
     1. status_code='ACTIVE' - exact match!
     2. is_active=true flag - could mean operational funds
     
     Given context, user probably wants funds with ACTIVE status.
     But I should JOIN to dimension table for clarity."
  
Decision:
  SELECT f.*, s.status_name
  FROM funds f
  JOIN fund_status_dim s ON f.status_id = s.status_id
  WHERE s.status_code = 'ACTIVE'
```

### Step 3: Use Dimension Metadata for Smart Filtering

```python
# User query: "Show operating funds"
# Entity: "operating"

# LLM process:
Semantic search: "operating" doesn't directly match any column

Check dimension tables:
  - Found fund_status_dim with category column
  - Values: 'OPERATIONAL', 'TERMINAL'

LLM reasoning:
  "'operating' is similar to 'operational'. 
   fund_status_dim has category='OPERATIONAL' which includes:
   - ACTIVE
   - SUSPENDED
   
   User wants funds that are still operating, so:
   WHERE s.category = 'OPERATIONAL'"

Result:
  SELECT f.*, s.status_name
  FROM funds f
  JOIN fund_status_dim s ON f.status_id = s.status_id
  WHERE s.category = 'OPERATIONAL'
  -- Returns both ACTIVE and SUSPENDED funds
```

---

## YAML Configuration for Dimension Tables

### Enhanced Schema Definition

```yaml
# config/applications/fund_accounting.yaml

tables:
  funds:
    name: funds
    description: Investment fund master data
    
    columns:
      id:
        type: integer
        primary_key: true
        
      name:
        type: varchar
        description: Fund name
        
      status_id:
        type: integer
        description: Fund operational status
        foreign_key: 
          table: fund_status_dim
          column: status_id
          relationship: many-to-one
        dimension_table: fund_status_dim  # Mark as dimension!
        
      fund_type:
        type: varchar
        is_dimension: true
        dictionary_table: fund_type_dictionary
        
  # Dimension table definition
  fund_status_dim:
    name: fund_status_dim
    description: Fund status dimension table
    is_dimension_table: true  # Mark as dimension table!
    
    columns:
      status_id:
        type: integer
        primary_key: true
        
      status_code:
        type: varchar
        unique: true
        description: Unique status code (ACTIVE, CLOSED, etc.)
        
      status_name:
        type: varchar
        description: Display name for status
        
      description:
        type: text
        description: Detailed description of what this status means
        
      is_active:
        type: boolean
        description: Whether this is an active/operational status
        
      category:
        type: varchar
        description: Status category (OPERATIONAL, TERMINAL, etc.)
        values: ["OPERATIONAL", "TERMINAL"]
        
    # Business rules for this dimension
    business_rules:
      default_filter: "is_active = true"
      common_patterns:
        active_funds: "status_code = 'ACTIVE'"
        operational_funds: "category = 'OPERATIONAL'"
        closed_funds: "status_code IN ('CLOSED', 'LIQUIDATING')"
```

---

## Agentic Mapper: Dimension Table Tools

### New Tool: GET_DIMENSION_TABLE_INFO

```python
def get_dimension_table_info(table_name: str, dimension_table: str) -> Dict:
    """
    Get complete information about a dimension table referenced by FK.
    
    This helps LLM understand:
    - What values are available
    - What each value means
    - What metadata columns exist (is_active, category, etc.)
    - What business rules apply
    """
    
    # Get dimension table schema
    dim_schema = config_mgr.get_table_schema(dimension_table)
    
    # Get actual dimension data
    dim_data = db.query(f"""
        SELECT *
        FROM {dimension_table}
        WHERE end_date IS NULL  -- Current values only
        ORDER BY display_order
    """)
    
    # Analyze dimension structure
    has_is_active = 'is_active' in dim_schema.columns
    has_category = 'category' in dim_schema.columns
    has_description = 'description' in dim_schema.columns
    
    return {
        'dimension_table': dimension_table,
        'schema': dim_schema,
        'values': dim_data,
        'count': len(dim_data),
        'has_is_active': has_is_active,
        'has_category': has_category,
        'has_description': has_description,
        'business_rules': config_mgr.get_business_rules(dimension_table)
    }
```

### Enhanced LLM Iteration with Dimensions

```python
class IterativeSchemaMapper:
    
    def _handle_dimension_lookup(self, column_info, entity_text, query_context):
        """
        Special handling when column is FK to dimension table.
        """
        
        dim_table = column_info.get('dimension_table')
        
        if not dim_table:
            return None  # Not a dimension lookup
        
        # Get full dimension table info
        dim_info = self.get_dimension_table_info(
            table_name=column_info['table'],
            dimension_table=dim_table
        )
        
        # LLM reviews dimension values to find match
        llm_prompt = f"""
User Query: {query_context}
Entity: "{entity_text}"

This entity maps to a DIMENSION TABLE: {dim_table}

DIMENSION TABLE SCHEMA:
{json.dumps(dim_info['schema'], indent=2)}

AVAILABLE DIMENSION VALUES:
{json.dumps(dim_info['values'], indent=2)}

Your task: Find the best match for "{entity_text}" in this dimension table.

Consider:
1. Exact matches in codes or names
2. Description text matches
3. Category/grouping matches
4. is_active flag if present

Return:
{{
  "matched_values": ["ACTIVE", "SUSPENDED"],  // Could be multiple!
  "filter_type": "IN",  // =, IN, LIKE, etc.
  "join_needed": true,
  "reasoning": "User said 'active' which matches status_code='ACTIVE' and is_active=true",
  "additional_columns": ["status_name", "category"]  // From dimension table
}}
"""
        
        return self.llm_client.generate(llm_prompt)
```

---

## Example: Complete Flow with Dimension Table

### Query: "Show AUM for active equity funds"

```python
# Iteration 1: Initial search
Entity: "active"
Semantic search: funds.status_id (0.65)

# Iteration 2: Discover dimension
LLM: "status_id is FK to fund_status_dim. Let me get that dimension data."
Action: GET_DIMENSION_TABLE_INFO('funds', 'fund_status_dim')

# Iteration 3: Match to dimension values
Dimension values received:
  - ACTIVE (is_active=true, category=OPERATIONAL)
  - SUSPENDED (is_active=true, category=OPERATIONAL)
  - CLOSED (is_active=false, category=TERMINAL)

LLM: "User said 'active funds'. Best match is status_code='ACTIVE'"

# Iteration 4: Plan JOIN
LLM: "I need to JOIN to fund_status_dim to filter by status"

# Final mapping:
SELECT 
  f.name,
  f.total_aum,
  s.status_name,        -- From dimension table!
  s.category            -- Additional context!
FROM funds f
JOIN fund_status_dim s ON f.status_id = s.status_id  -- JOIN to dimension!
WHERE f.fund_type LIKE 'Equity%'
  AND s.status_code = 'ACTIVE'        -- Filter via dimension!
  AND f.end_date IS NULL
```

---

## Pattern Detection: When to Use Dimension Tables

### LLM Can Auto-Detect Dimension Patterns

```python
def detect_dimension_candidates(table_schema):
    """
    Analyze schema to suggest which columns should be dimension tables.
    """
    
    candidates = []
    
    for column_name, column_def in table_schema.columns.items():
        
        # Pattern 1: Column name ends with _id or _code
        if column_name.endswith('_id') or column_name.endswith('_code'):
            # Check if FK to dimension table
            if column_def.get('foreign_key'):
                fk_table = column_def['foreign_key']['table']
                if fk_table.endswith('_dim') or fk_table.endswith('_dictionary'):
                    candidates.append({
                        'column': column_name,
                        'type': 'existing_dimension',
                        'dimension_table': fk_table
                    })
        
        # Pattern 2: VARCHAR with limited distinct values
        elif column_def.get('type') == 'varchar':
            # Check if this should be a dimension
            if any(keyword in column_name.lower() for keyword in 
                   ['status', 'type', 'category', 'rating', 'class']):
                
                # Query distinct values
                distinct_count = db.query(
                    f"SELECT COUNT(DISTINCT {column_name}) FROM {table_schema.name}"
                )
                
                if distinct_count < 50:  # Limited value set
                    candidates.append({
                        'column': column_name,
                        'type': 'dimension_candidate',
                        'reason': f'Limited values ({distinct_count}), common dimension pattern',
                        'suggestion': f'Consider creating {column_name}_dim table'
                    })
    
    return candidates
```

---

## Migration Path: VARCHAR → Dimension Table

### For Existing Systems

```python
# Tool to help migrate VARCHAR columns to dimension tables

def generate_dimension_table_migration(table_name, column_name):
    """
    Generate migration script to convert VARCHAR to dimension table.
    """
    
    # Get current distinct values
    current_values = db.query(f"""
        SELECT DISTINCT {column_name}, COUNT(*) as usage_count
        FROM {table_name}
        WHERE {column_name} IS NOT NULL
        GROUP BY {column_name}
        ORDER BY usage_count DESC
    """)
    
    # Generate dimension table
    dim_table_name = f"{column_name}_dim"
    
    migration_sql = f"""
-- Step 1: Create dimension table
CREATE TABLE {dim_table_name} (
    {column_name}_id SERIAL PRIMARY KEY,
    {column_name}_code VARCHAR(50) UNIQUE NOT NULL,
    {column_name}_name VARCHAR(100),
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    display_order INTEGER,
    created_date DATE DEFAULT CURRENT_DATE,
    effective_date DATE DEFAULT CURRENT_DATE,
    end_date DATE
);

-- Step 2: Populate dimension table
INSERT INTO {dim_table_name} ({column_name}_code, {column_name}_name, display_order)
VALUES
{chr(10).join(f"  ('{val}', '{val.title()}', {idx+1})" for idx, val in enumerate(current_values))}
;

-- Step 3: Add new FK column to main table
ALTER TABLE {table_name} ADD COLUMN {column_name}_id INTEGER;

-- Step 4: Populate FK values
UPDATE {table_name} t
SET {column_name}_id = d.{column_name}_id
FROM {dim_table_name} d
WHERE t.{column_name} = d.{column_name}_code;

-- Step 5: Add FK constraint
ALTER TABLE {table_name}
ADD CONSTRAINT fk_{table_name}_{column_name}
FOREIGN KEY ({column_name}_id) REFERENCES {dim_table_name}({column_name}_id);

-- Step 6: Drop old VARCHAR column (optional, after validation)
-- ALTER TABLE {table_name} DROP COLUMN {column_name};
"""
    
    return migration_sql
```

---

## Summary: Dimension Tables in Agentic Mapper

### Key Points

1. **Status, type, category columns → Dimension tables**
   - Better data integrity
   - Richer metadata
   - Easier business rule application

2. **LLM discovers dimension relationships**
   - Detects FK to dimension tables
   - Loads dimension values
   - Matches entities to dimension codes

3. **Auto-applies smart JOINs**
   - Includes dimension table in query
   - Filters via dimension attributes
   - Adds dimension metadata columns

4. **Configuration-driven**
   - Mark dimension tables in YAML
   - Define business rules on dimensions
   - Specify common patterns

### Your Insight is Key!

By treating status (and similar attributes) as proper dimension tables, the agentic mapper can:
- ✅ Understand semantic relationships better
- ✅ Apply richer filtering logic
- ✅ Include meaningful metadata automatically
- ✅ Handle complex categorizations
- ✅ Support temporal changes in dimensions

**Should we update the financial_testdb schema to use dimension tables for status, type, etc.?** This would make our implementation more realistic and powerful!
