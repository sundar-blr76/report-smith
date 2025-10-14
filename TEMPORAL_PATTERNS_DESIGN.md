# Temporal Patterns - Implicit Rules & Version Management

## Your Critical Insights

### 1. **Implicit Temporal Semantics**
- NULL end_date → Open-ended validity (current/active)
- NULL effective_date → Valid from beginning of time
- Missing dates have MEANING!

### 2. **Version Management Patterns**
- Latest version = valid/current version
- Parent table's version dictates child version
- Version cascading through relationships

These patterns are **critical business logic** that must be captured!

---

## Problem 1: Implicit Temporal Semantics

### The Hidden Rules

```sql
-- funds table
CREATE TABLE funds (
    id INTEGER,
    name VARCHAR,
    effective_date DATE,
    end_date DATE,  -- NULL means "still valid"!
    ...
);

-- Sample data
INSERT INTO funds VALUES
(1, 'Fund A', '2020-01-01', NULL),        -- ← NULL = Currently valid!
(2, 'Fund A', '2019-01-01', '2019-12-31'), -- Old version
(3, 'Fund B', '2021-01-01', '2023-06-30'), -- Closed in June 2023
(4, 'Fund B', '2023-07-01', NULL);        -- ← New version, currently valid
```

**Implicit Rules (NOT in schema, but critical):**
1. `NULL end_date` = "This record is current/active"
2. `NULL effective_date` = "Valid from system start"
3. To get current records: `WHERE end_date IS NULL`
4. To get historical point-in-time: `WHERE effective_date <= @date AND (end_date IS NULL OR end_date > @date)`

**Problem:** LLM has no way to know these rules unless we tell it!

---

## Solution 1: Explicit Temporal Metadata in Schema

### Enhanced YAML Configuration

```yaml
tables:
  funds:
    name: funds
    description: Investment fund master data
    
    # TEMPORAL CONFIGURATION
    temporal_config:
      type: "SCD_TYPE_2"  # Slowly Changing Dimension Type 2
      
      effective_date_column: "effective_date"
      end_date_column: "end_date"
      
      # CRITICAL: Define NULL semantics!
      null_semantics:
        end_date:
          when_null: "record_is_current"
          meaning: "Open-ended validity - record is active/current"
          filter_for_current: "end_date IS NULL"
          
        effective_date:
          when_null: "valid_from_start"
          meaning: "Valid from beginning of time"
          default_value: "1900-01-01"  # Or system start date
      
      # Common temporal queries
      temporal_filters:
        current_records:
          condition: "end_date IS NULL"
          description: "Get only current/active versions"
          default: true  # Apply by default unless user asks for historical
          
        point_in_time:
          condition: "effective_date <= @date AND (end_date IS NULL OR end_date > @date)"
          description: "Get records valid at specific date"
          parameters: ["date"]
          
        date_range:
          condition: "effective_date < @end_date AND (end_date IS NULL OR end_date >= @start_date)"
          description: "Get records valid during date range"
          parameters: ["start_date", "end_date"]
      
      # Business rules
      business_rules:
        - "NULL end_date means record is current"
        - "Most queries should filter to current records only"
        - "Use point_in_time filter for historical queries"
        - "Never join historical to current without date alignment"
    
    columns:
      effective_date:
        type: date
        description: "Date when this record became effective"
        nullable: true
        temporal_role: "effective_date"
        null_meaning: "valid_from_start"
        
      end_date:
        type: date
        description: "Date when this record was superseded (NULL = current)"
        nullable: true
        temporal_role: "end_date"
        null_meaning: "record_is_current"  # KEY INFO!
```

### LLM Learns Temporal Semantics

```python
def get_temporal_info(table: str) -> Dict:
    """
    Get complete temporal configuration including NULL semantics.
    """
    
    schema = config_mgr.get_table_schema(table)
    temporal_config = schema.get('temporal_config', {})
    
    if not temporal_config:
        return {'is_temporal': False}
    
    return {
        'is_temporal': True,
        'type': temporal_config.get('type'),  # SCD_TYPE_2, etc.
        'effective_date_column': temporal_config.get('effective_date_column'),
        'end_date_column': temporal_config.get('end_date_column'),
        
        # NULL semantics - CRITICAL!
        'null_semantics': temporal_config.get('null_semantics', {}),
        
        # Pre-defined filters
        'temporal_filters': temporal_config.get('temporal_filters', {}),
        
        # Business rules
        'business_rules': temporal_config.get('business_rules', []),
        
        # Helper for LLM
        'current_record_filter': temporal_config.get('temporal_filters', {}).get(
            'current_records', {}
        ).get('condition')
    }
```

### LLM Uses Temporal Metadata

```python
# LLM Prompt includes temporal info
prompt = f"""
Table: funds

Temporal Configuration:
- Type: SCD_TYPE_2 (Slowly Changing Dimension)
- Effective Date: effective_date
- End Date: end_date

NULL Semantics (IMPORTANT):
- end_date IS NULL means: "Record is current/active"
- effective_date IS NULL means: "Valid from beginning of time"

Current Records Filter: "end_date IS NULL"
Point-in-Time Filter: "effective_date <= @date AND (end_date IS NULL OR end_date > @date)"

Business Rules:
1. NULL end_date means record is current
2. Most queries should filter to current records only
3. Use point_in_time filter for historical queries

User Query: "Show active funds"

Should you apply the current_records filter?
YES - user said "active" which implies current records.
"""
```

---

## Problem 2: Version Management Patterns

### Pattern 2A: Latest Version is Valid

```sql
-- fee_schedules table (versioned)
CREATE TABLE fee_schedules (
    id INTEGER,
    schedule_code VARCHAR,
    version INTEGER,  -- Version number
    effective_date DATE,
    management_fee DECIMAL,
    is_latest BOOLEAN,  -- ← Explicit flag
    ...
);

-- Sample data
INSERT INTO fee_schedules VALUES
(1, 'SCHED001', 1, '2020-01-01', 1.5, false),
(2, 'SCHED001', 2, '2021-01-01', 1.3, false),
(3, 'SCHED001', 3, '2022-01-01', 1.2, true),  -- ← Latest!
(4, 'SCHED002', 1, '2020-01-01', 2.0, true);
```

**Implicit Rule:** `is_latest = true` OR `version = MAX(version) GROUP BY schedule_code`

### Pattern 2B: Parent's Active Version Cascades

```sql
-- Parent table
CREATE TABLE funds (
    id INTEGER,
    fund_code VARCHAR,
    version INTEGER,
    end_date DATE,  -- NULL = active
    ...
);

-- Child table (must match parent version!)
CREATE TABLE fund_holdings (
    id INTEGER,
    fund_id INTEGER,
    fund_version INTEGER,  -- ← Must match parent's ACTIVE version!
    security_id INTEGER,
    quantity DECIMAL,
    ...
);

-- Query challenge:
-- "Show holdings for Fund X"
-- Must join to parent's ACTIVE version, not all versions!
```

---

## Solution 2: Version Management Metadata

### Enhanced YAML with Version Config

```yaml
tables:
  fee_schedules:
    name: fee_schedules
    description: Fee schedule versions
    
    # VERSION CONFIGURATION
    version_config:
      type: "explicit_version"  # or "implicit_temporal", "sequence"
      
      version_column: "version"
      version_key: ["schedule_code", "version"]  # Composite key
      
      # How to identify latest/current version
      latest_version_strategy:
        type: "flag"  # or "max_version", "end_date_null"
        flag_column: "is_latest"
        flag_value: true
        
        # Alternative: max version
        # type: "max_version"
        # max_condition: "version = (SELECT MAX(version) FROM fee_schedules f2 WHERE f2.schedule_code = fee_schedules.schedule_code)"
      
      # Filter for current version
      current_version_filter: "is_latest = true"
      
      business_rules:
        - "is_latest = true indicates current/active version"
        - "Most queries should filter to latest version only"
        - "Historical queries need explicit version or date"
        - "Never aggregate across versions without grouping"
    
    columns:
      version:
        type: integer
        description: "Version number (higher = newer)"
        version_role: "version_number"
        
      is_latest:
        type: boolean
        description: "TRUE if this is the latest/current version"
        version_role: "latest_flag"
        default: false

  fund_holdings:
    name: fund_holdings
    description: Security holdings by fund (versioned with parent)"
    
    # PARENT VERSION DEPENDENCY
    version_config:
      type: "parent_dependent"
      
      parent_table: "funds"
      parent_version_column: "fund_version"  # Column holding parent's version
      parent_join:
        - "fund_holdings.fund_id = funds.id"
        - "fund_holdings.fund_version = funds.version"
      
      # Critical rule!
      version_cascade_rule:
        description: "Holdings must join to parent fund's ACTIVE version"
        parent_filter: "funds.end_date IS NULL"  # Parent's active version
        join_on_version: true
        
      business_rules:
        - "fund_version must match parent fund's version"
        - "When querying holdings, join to parent's ACTIVE version"
        - "Holdings are tied to specific fund version"
        - "Cross-version aggregation requires explicit version alignment"
```

---

## Solution 3: LLM Tools for Temporal/Version Handling

### Tool: Get Temporal & Version Info

```python
class TemporalVersionHandler:
    """
    Handles temporal and version management patterns.
    """
    
    def get_temporal_version_info(self, table: str) -> Dict:
        """
        Get complete temporal and version configuration for table.
        """
        
        schema = self.config_mgr.get_table_schema(table)
        
        info = {
            'table': table,
            'temporal': self._get_temporal_config(schema),
            'version': self._get_version_config(schema),
            'combined_filter': None
        }
        
        # Build combined filter if both temporal and versioned
        if info['temporal']['is_temporal'] and info['version']['is_versioned']:
            info['combined_filter'] = self._build_combined_filter(
                info['temporal'], 
                info['version']
            )
        
        return info
    
    def _get_temporal_config(self, schema: Dict) -> Dict:
        """Extract temporal configuration."""
        
        temporal = schema.get('temporal_config', {})
        
        if not temporal:
            return {'is_temporal': False}
        
        return {
            'is_temporal': True,
            'type': temporal.get('type'),
            'effective_date_column': temporal.get('effective_date_column'),
            'end_date_column': temporal.get('end_date_column'),
            
            # NULL semantics
            'null_semantics': temporal.get('null_semantics', {}),
            
            # Current record filter
            'current_filter': temporal.get('temporal_filters', {}).get(
                'current_records', {}
            ).get('condition', 'end_date IS NULL'),
            
            'business_rules': temporal.get('business_rules', [])
        }
    
    def _get_version_config(self, schema: Dict) -> Dict:
        """Extract version configuration."""
        
        version = schema.get('version_config', {})
        
        if not version:
            return {'is_versioned': False}
        
        return {
            'is_versioned': True,
            'type': version.get('type'),
            'version_column': version.get('version_column'),
            
            # How to get latest version
            'latest_strategy': version.get('latest_version_strategy', {}),
            'current_filter': version.get('current_version_filter'),
            
            # Parent dependency (if exists)
            'parent_dependent': version.get('type') == 'parent_dependent',
            'parent_table': version.get('parent_table'),
            'parent_version_column': version.get('parent_version_column'),
            'parent_join': version.get('parent_join', []),
            'cascade_rule': version.get('version_cascade_rule', {}),
            
            'business_rules': version.get('business_rules', [])
        }
    
    def _build_combined_filter(self, temporal: Dict, version: Dict) -> str:
        """
        Build filter when table has BOTH temporal and version patterns.
        
        Example: 
        - end_date IS NULL (temporal - current)
        - AND is_latest = true (version - latest)
        """
        
        filters = []
        
        if temporal.get('current_filter'):
            filters.append(temporal['current_filter'])
        
        if version.get('current_filter'):
            filters.append(version['current_filter'])
        
        return ' AND '.join(filters) if filters else None
```

### LLM Iteration with Temporal/Version Awareness

```python
def _llm_handle_temporal_versioned_table(
    self,
    table: str,
    query_context: str
) -> Dict:
    """
    LLM handles table with temporal/version patterns.
    """
    
    # Get temporal & version info
    info = self.temporal_handler.get_temporal_version_info(table)
    
    prompt = f"""
User Query: "{query_context}"
Table: {table}

TEMPORAL CONFIGURATION:
{json.dumps(info['temporal'], indent=2)}

VERSION CONFIGURATION:
{json.dumps(info['version'], indent=2)}

CRITICAL NULL SEMANTICS:
{json.dumps(info['temporal'].get('null_semantics', {}), indent=2)}

Your Task: Determine what filters to apply.

Questions to consider:
1. Does user want CURRENT data or HISTORICAL data?
   - "active", "current", "latest" → current
   - "as of date", "on date" → point-in-time
   - No time context → assume current (default)

2. For versioned tables:
   - Does user want latest version?
   - Do they need historical versions?
   - Is this child of a versioned parent?

3. NULL end_date semantics:
   - NULL means: {info['temporal'].get('null_semantics', {}).get('end_date', {}).get('meaning')}
   - Should we filter: {info['temporal'].get('current_filter')}

Return:
{{
  "filters_needed": [
    "end_date IS NULL",  // Temporal
    "is_latest = true"   // Version
  ],
  "reasoning": "User wants current/active data, so need both temporal and version filters",
  "query_type": "current",  // current, historical, point_in_time
  "parent_version_handling": null  // or details if parent-dependent
}}
"""
    
    return self.llm_client.generate(prompt)
```

---

## Solution 4: Parent-Child Version Cascading

### Handling Version Dependencies

```python
def handle_parent_version_cascade(
    self,
    child_table: str,
    parent_table: str,
    query_context: str
) -> Dict:
    """
    Handle case where child table's version depends on parent's active version.
    """
    
    child_version_config = self.config_mgr.get_version_config(child_table)
    parent_version_config = self.config_mgr.get_version_config(parent_table)
    parent_temporal_config = self.config_mgr.get_temporal_config(parent_table)
    
    # Check if child is parent-dependent
    if child_version_config.get('type') != 'parent_dependent':
        return None
    
    cascade_rule = child_version_config.get('version_cascade_rule', {})
    
    llm_prompt = f"""
User Query: "{query_context}"

PARENT-CHILD VERSION RELATIONSHIP:
Parent: {parent_table}
Child: {child_table}

Parent Version Config:
{json.dumps(parent_version_config, indent=2)}

Parent Temporal Config (if any):
{json.dumps(parent_temporal_config, indent=2)}

Child Version Config:
{json.dumps(child_version_config, indent=2)}

CASCADE RULE:
{json.dumps(cascade_rule, indent=2)}

CRITICAL: Child records must join to parent's ACTIVE version!

Example:
- funds table has multiple versions (version 1, 2, 3)
- fund_holdings.fund_version links to specific fund version
- Query for "current holdings" must join to fund's ACTIVE version
- JOIN funds ON holdings.fund_id = funds.id 
              AND holdings.fund_version = funds.version
              AND funds.end_date IS NULL  ← Parent's ACTIVE version!

Your Task: Generate correct JOIN with version alignment.

Return:
{{
  "join_clause": "fund_holdings.fund_id = funds.id AND fund_holdings.fund_version = funds.version",
  "parent_filter": "funds.end_date IS NULL",
  "reasoning": "Must join to parent's active version to get current holdings",
  "warning": "Never join without version filter - will get wrong data!"
}}
"""
    
    return self.llm_client.generate(llm_prompt)
```

---

## Example Scenarios

### Scenario 1: Simple Temporal Query

```yaml
Query: "Show active funds"

LLM Discovers:
- funds table has temporal_config
- end_date NULL semantics: "record_is_current"
- Business rule: "Most queries should filter to current records"

LLM Decides:
- User said "active" → wants current records
- Apply filter: end_date IS NULL

SQL:
SELECT * FROM funds
WHERE end_date IS NULL
  AND is_active = true
```

### Scenario 2: Versioned Table

```yaml
Query: "Show current fee schedule for Fund X"

LLM Discovers:
- fee_schedules is versioned (version_column: version)
- latest_strategy: flag (is_latest = true)
- Business rule: "Most queries should filter to latest version"

LLM Decides:
- User said "current" → wants latest version
- Apply filter: is_latest = true

SQL:
SELECT * FROM fee_schedules
WHERE schedule_code = 'FUND_X_SCHED'
  AND is_latest = true
```

### Scenario 3: Parent-Child Version Cascade

```yaml
Query: "Show holdings for Fund X"

LLM Discovers:
- fund_holdings is parent_dependent on funds
- funds has temporal_config (end_date IS NULL = current)
- Cascade rule: join to parent's active version

LLM Decides:
- User wants current holdings
- Must join to fund's ACTIVE version
- Use version column in JOIN

SQL:
SELECT 
  h.security_id,
  h.quantity,
  f.name as fund_name,
  f.version as fund_version
FROM fund_holdings h
JOIN funds f 
  ON h.fund_id = f.id 
  AND h.fund_version = f.version  -- Version alignment!
  AND f.end_date IS NULL          -- Parent's ACTIVE version!
WHERE f.fund_code = 'FUND_X'
```

### Scenario 4: Historical Point-in-Time

```yaml
Query: "Show Fund X as of 2022-06-15"

LLM Discovers:
- funds has temporal_config
- point_in_time filter available
- Parameters: date

LLM Decides:
- User wants historical snapshot
- Use point_in_time filter with date

SQL:
SELECT * FROM funds
WHERE fund_code = 'FUND_X'
  AND effective_date <= '2022-06-15'
  AND (end_date IS NULL OR end_date > '2022-06-15')
```

---

## Configuration Best Practices

### Temporal Tables

```yaml
temporal_config:
  # Always specify NULL semantics!
  null_semantics:
    end_date:
      when_null: "record_is_current"
      meaning: "Open-ended validity"
    effective_date:
      when_null: "valid_from_start"
      
  # Provide pre-built filters
  temporal_filters:
    current_records:
      condition: "end_date IS NULL"
      default: true
      
  # Document business rules
  business_rules:
    - "NULL end_date means current"
    - "Default to current unless historical requested"
```

### Versioned Tables

```yaml
version_config:
  # Clear strategy for latest version
  latest_version_strategy:
    type: "flag"  # or "max_version"
    flag_column: "is_latest"
    
  # Provide current filter
  current_version_filter: "is_latest = true"
  
  # Document rules
  business_rules:
    - "is_latest = true is current version"
    - "Never aggregate across versions"
```

### Parent-Dependent Tables

```yaml
version_config:
  type: "parent_dependent"
  parent_table: "funds"
  
  # CRITICAL: Document cascade rule!
  version_cascade_rule:
    description: "Must join to parent's active version"
    parent_filter: "funds.end_date IS NULL"
    join_on_version: true
    
  business_rules:
    - "Version must match parent"
    - "Join to parent's ACTIVE version for current data"
```

---

## Summary: Temporal & Version Patterns

### Your Key Insights:

1. **NULL has meaning!**
   - NULL end_date → current/active record
   - Must be explicitly documented

2. **Version patterns vary**
   - Latest version = current
   - Parent's version cascades to children
   - Must specify strategy

3. **These are implicit business rules**
   - Not obvious from schema alone
   - Critical for correct queries
   - Must be captured in configuration

### Implementation Checklist:

✅ Add `temporal_config` to YAML
✅ Document NULL semantics
✅ Add `version_config` for versioned tables
✅ Specify latest version strategy
✅ Document parent-child version dependencies
✅ Provide pre-built filters
✅ Include business rules
✅ LLM tools to read and apply these configs
✅ Comprehensive logging

**This makes temporal/version handling explicit and teachable to LLM!** 🎯
