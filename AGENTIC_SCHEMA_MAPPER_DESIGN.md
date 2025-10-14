# Agentic Schema Mapper Design - Iterative Context Enhancement

## Your Brilliant Insight

> "With additional context, LLM could also auto-apply filters, i.e. records are milestoned, there is a status column, LLM could iteratively obtain additional context, and improve query completeness"

**This is the KEY to making this truly intelligent!** 🎯

---

## The Iterative Agentic Approach

### Traditional Static Mapping (Limited)
```
Query → Semantic Search → Pick Columns → Done
```
**Problem**: Misses important context like:
- Milestoning (effective_date, end_date)
- Status flags (is_active, status = 'Active')
- Soft deletes (deleted_at IS NULL)
- Data quality filters (is_validated = true)

### Agentic Iterative Mapping (Intelligent)
```
Query → Initial Search → LLM Reviews → 
  "I see milestone columns!" → 
    Get Milestoning Rules → 
      "I see status column!" → 
        Get Status Values →
          Apply Smart Filters → 
            Validate Completeness → Done
```

---

## Real-World Example: The Power of Iteration

### Query: "Show AUM for equity funds"

#### **Iteration 1: Initial Semantic Search**
```python
Entity: "equity funds"
Semantic Results:
  - funds.fund_type (0.88)
  - funds.total_aum (0.85)

# Basic mapping, but incomplete!
```

#### **Iteration 2: LLM Reviews Schema Context**
```python
LLM sees full funds table schema:
  - id
  - name
  - fund_type
  - total_aum
  - status ← "Hmm, there's a status column!"
  - inception_date
  - close_date ← "And a close_date! This might indicate active/closed funds"

LLM reasoning:
  "I see status and close_date columns. Let me check what these mean..."

Action: REQUEST MORE CONTEXT
  - What are valid status values?
  - What does close_date indicate?
  - Are there business rules for 'active' funds?
```

#### **Iteration 3: Get Status Context**
```python
Agent calls: get_dimension_values('funds', 'status')

Response:
  - Active (80% of records)
  - Closed (15% of records)
  - Suspended (5% of records)

Agent also gets: get_business_rules('funds')

Response:
  "Active funds: status = 'Active' AND close_date IS NULL"
  "Historical queries should include all statuses"
  "Default queries should filter to active funds only"

LLM reasoning:
  "User said 'Show AUM for equity funds' (present tense).
   They want current/active funds, not closed ones.
   I should auto-apply: WHERE status = 'Active' AND close_date IS NULL"
```

#### **Iteration 4: Check for Milestoning**
```python
LLM sees in schema:
  - effective_date ← "This looks like milestoning!"
  - end_date

Action: REQUEST MILESTONING RULES
  get_milestoning_info('funds')

Response:
  "funds table is milestoned:
   - effective_date: When record became effective
   - end_date: When record was superseded (NULL = current)
   - Current records: end_date IS NULL
   - Point-in-time query: effective_date <= @date AND 
                          (end_date IS NULL OR end_date > @date)"

LLM reasoning:
  "Funds are milestoned! User wants current data, so I need:
   WHERE end_date IS NULL"
```

#### **Iteration 5: Check for Related Filters**
```python
LLM checks: "Are there other filters I should consider?"

Reviews entity "equity funds":
  - Already have: fund_type filter
  - Check: Are there regional/currency considerations?
  
Action: GET SCHEMA METADATA
  get_column_metadata('funds', 'fund_type')

Response:
  "fund_type values: Equity Growth, Bond, Money Market, Balanced, etc.
   Common query patterns:
   - 'equity' matches: Equity Growth, Equity Income, Equity Value
   - Users often want multiple equity types, not just one"

LLM reasoning:
  "User said 'equity funds' (plural). They probably want ALL equity types.
   I should use: WHERE fund_type LIKE 'Equity%'"
```

#### **Iteration 6: Validate Completeness**
```python
LLM final validation:
  "Let me verify this query is complete..."

Checklist:
  ✓ User wants: AUM for equity funds
  ✓ Selected: funds.total_aum, funds.name
  ✓ Filter: fund_type LIKE 'Equity%'
  ✓ Active only: status = 'Active' AND close_date IS NULL
  ✓ Current data: end_date IS NULL (milestoning)
  ✓ Joins needed: None (single table)
  
Completeness: 95%
Missing: Should I include inception_date for context? → Yes, useful!
```

#### **Final Result**
```sql
SELECT 
  f.name,
  f.fund_type,
  f.total_aum,
  f.inception_date
FROM funds f
WHERE f.fund_type LIKE 'Equity%'
  AND f.status = 'Active'
  AND f.close_date IS NULL
  AND f.end_date IS NULL  -- milestoning: current records only
ORDER BY f.total_aum DESC
```

**vs. Without Iteration (Naive):**
```sql
SELECT f.total_aum
FROM funds f
WHERE f.fund_type = 'Equity Growth'
-- Missing: status filter, closed funds included, historical records included!
-- Result: WRONG DATA!
```

---

## Architecture: Iterative Agentic Workflow

### Phase 1: Initial Discovery
```python
class IterativeSchemaMapper:
    def map_with_iteration(self, query_intent):
        """
        Iteratively build complete schema mapping.
        """
        context = {
            'query': query_intent.original_query,
            'entities': query_intent.entities,
            'iteration': 0,
            'max_iterations': 5
        }
        
        mapping = SchemaMapping()
        
        while not mapping.is_complete and context['iteration'] < context['max_iterations']:
            context['iteration'] += 1
            
            # LLM decides what to do next
            next_action = self._llm_decide_next_action(mapping, context)
            
            if next_action.type == 'SEMANTIC_SEARCH':
                results = self._do_semantic_search(next_action)
                mapping.add_semantic_results(results)
                
            elif next_action.type == 'GET_TABLE_SCHEMA':
                schema = self._get_table_schema(next_action.table)
                mapping.add_table_context(schema)
                
            elif next_action.type == 'GET_DIMENSION_VALUES':
                values = self._get_dimension_values(next_action.table, next_action.column)
                mapping.add_dimension_context(values)
                
            elif next_action.type == 'GET_BUSINESS_RULES':
                rules = self._get_business_rules(next_action.table)
                mapping.add_business_rules(rules)
                
            elif next_action.type == 'GET_MILESTONING_INFO':
                milestone_info = self._get_milestoning_info(next_action.table)
                mapping.add_milestoning_rules(milestone_info)
                
            elif next_action.type == 'CHECK_RELATIONSHIPS':
                relationships = self._get_relationships(next_action.tables)
                mapping.add_relationships(relationships)
                
            elif next_action.type == 'VALIDATE_COMPLETENESS':
                validation = self._validate_mapping(mapping)
                mapping.set_validation(validation)
                
            elif next_action.type == 'COMPLETE':
                mapping.mark_complete()
                break
                
            # Log iteration
            logger.info(f"Iteration {context['iteration']}: {next_action.type}")
            logger.debug(f"Action details: {next_action}")
        
        return mapping
```

### Phase 2: LLM as Decision Engine

```python
def _llm_decide_next_action(self, mapping, context):
    """
    LLM decides what information to request next.
    """
    
    prompt = f"""
You are an intelligent database query agent iteratively building a complete query.

ITERATION: {context['iteration']}/{context['max_iterations']}
USER QUERY: {context['query']}

CURRENT MAPPING STATE:
{mapping.to_json()}

WHAT WE KNOW SO FAR:
- Tables identified: {mapping.tables}
- Columns selected: {mapping.columns}
- Filters applied: {mapping.filters}
- Business rules: {mapping.business_rules}
- Milestoning: {mapping.milestoning_info}

AVAILABLE ACTIONS:
1. SEMANTIC_SEARCH - Search for entities in schema
2. GET_TABLE_SCHEMA - Get full schema for a table
3. GET_DIMENSION_VALUES - Get possible values for a dimension column
4. GET_BUSINESS_RULES - Get business rules for a table/domain
5. GET_MILESTONING_INFO - Check if table has temporal/milestone columns
6. CHECK_RELATIONSHIPS - Get join paths between tables
7. VALIDATE_COMPLETENESS - Check if mapping is complete and correct
8. COMPLETE - Mapping is complete, ready to generate SQL

YOUR TASK: Decide the NEXT action to improve query completeness.

Consider:
- Do I need to check for status/active filters?
- Are there milestone/effective date columns?
- Do I understand all dimension values?
- Are my filters correct and complete?
- Do I have all necessary columns for a meaningful result?
- Are there business rules I should apply?

Return JSON:
{{
  "action": "GET_BUSINESS_RULES",
  "reasoning": "I see a status column but don't know valid values or rules",
  "parameters": {{"table": "funds"}},
  "expected_impact": "Will help me auto-apply active-only filter"
}}
"""
    
    response = self.llm_client.generate(prompt)
    return Action.from_json(response)
```

### Phase 3: Context Providers (Tools for LLM)

```python
class ContextProviders:
    """Tools that LLM can call to get more context."""
    
    def get_business_rules(self, table: str) -> Dict:
        """
        Get business rules from config or metadata.
        """
        # From YAML config
        rules = self.config_mgr.get_business_rules(table)
        
        # Example rules for funds:
        return {
            'active_records': "status = 'Active' AND close_date IS NULL",
            'current_milestone': "end_date IS NULL",
            'default_filters': [
                'status = "Active"',
                'end_date IS NULL'
            ],
            'common_patterns': {
                'equity_funds': "fund_type LIKE 'Equity%'",
                'open_funds': "close_date IS NULL"
            }
        }
    
    def get_milestoning_info(self, table: str) -> Dict:
        """
        Detect if table is milestoned and return rules.
        """
        schema = self.config_mgr.get_table_schema(table)
        
        # Check for common milestoning patterns
        milestone_columns = []
        if 'effective_date' in schema.columns:
            milestone_columns.append('effective_date')
        if 'end_date' in schema.columns:
            milestone_columns.append('end_date')
        if 'valid_from' in schema.columns:
            milestone_columns.append('valid_from')
        if 'valid_to' in schema.columns:
            milestone_columns.append('valid_to')
        
        if milestone_columns:
            return {
                'is_milestoned': True,
                'columns': milestone_columns,
                'current_record_filter': self._infer_current_filter(milestone_columns),
                'pattern': 'SCD Type 2' if 'effective_date' in milestone_columns else 'custom'
            }
        
        return {'is_milestoned': False}
    
    def get_dimension_values(self, table: str, column: str) -> Dict:
        """
        Get actual dimension values from database or dictionary.
        """
        # Check if there's a dictionary table
        dict_info = self.config_mgr.get_dictionary_info(table, column)
        
        if dict_info:
            # Query dictionary table
            values = self.db.query(
                f"SELECT {dict_info['value_column']}, "
                f"{dict_info['description_column']} "
                f"FROM {dict_info['dictionary_table']}"
            )
        else:
            # Query distinct values from main table
            values = self.db.query(
                f"SELECT DISTINCT {column} "
                f"FROM {table} "
                f"WHERE {column} IS NOT NULL "
                f"LIMIT 100"
            )
        
        return {
            'column': column,
            'values': values,
            'has_dictionary': bool(dict_info),
            'sample_values': values[:10]
        }
    
    def get_column_metadata(self, table: str, column: str) -> Dict:
        """
        Get rich metadata about a column.
        """
        schema = self.config_mgr.get_table_schema(table)
        col_def = schema.columns.get(column, {})
        
        # Enrich with statistics if needed
        stats = self.db.query(
            f"SELECT "
            f"COUNT(*) as total_rows, "
            f"COUNT({column}) as non_null_rows, "
            f"COUNT(DISTINCT {column}) as distinct_values "
            f"FROM {table}"
        )
        
        return {
            'name': column,
            'type': col_def.get('type'),
            'description': col_def.get('description'),
            'is_dimension': col_def.get('is_dimension', False),
            'statistics': stats,
            'common_patterns': self._get_query_patterns(table, column)
        }
```

---

## Enhanced LLM Prompts with Iteration Context

### Iteration 1: Discovery
```python
"""
You are discovering what information you need to build a complete query.

Query: "Show AUM for equity funds"

Start by identifying:
1. What tables/columns might be relevant (use SEMANTIC_SEARCH)
2. Once you have tables, get their full schemas (GET_TABLE_SCHEMA)

What do you want to do first?
"""
```

### Iteration 2: Schema Analysis
```python
"""
You've identified table: funds

Full schema shows columns:
- id, name, fund_type, total_aum, status, close_date, 
  effective_date, end_date, ...

I see several columns that might need special handling:
- status: What values are valid?
- close_date: Does NULL mean open/active?
- effective_date/end_date: Is this milestoned data?

What should we investigate next?
"""
```

### Iteration 3: Business Rules
```python
"""
You requested business rules for 'funds' table.

Rules retrieved:
- Active funds: status='Active' AND close_date IS NULL
- Milestoning: end_date IS NULL for current records
- Query defaults: Most queries want active, current records

Given user query "Show AUM for equity funds":
- Should we auto-apply active filter?
- Should we filter to current milestones?

Decide and explain your reasoning.
"""
```

### Iteration 4: Validation
```python
"""
You've built this mapping:

SELECT: funds.name, funds.total_aum, funds.inception_date
FROM: funds
WHERE: 
  - fund_type LIKE 'Equity%'
  - status = 'Active'
  - close_date IS NULL
  - end_date IS NULL

Validate completeness:
✓ Answers user question?
✓ All necessary filters applied?
✓ Any missing context columns?
✓ Joins needed?
✓ Aggregations correct?

Is this complete or do you need more information?
"""
```

---

## Benefits of Iterative Approach

### ✅ **Auto-Applies Best Practices**

```python
Without Iteration:
  WHERE fund_type = 'Equity Growth'
  # Missing: status filter, could return closed funds!

With Iteration:
  WHERE fund_type LIKE 'Equity%'
    AND status = 'Active'
    AND close_date IS NULL
    AND end_date IS NULL
  # Complete: only active, current records
```

### ✅ **Discovers Data Quality Rules**

```python
LLM discovers:
  - status column exists
  - Requests: What are valid values?
  - Learns: 'Active', 'Closed', 'Suspended'
  - Decides: User wants Active only
  - Applies: WHERE status = 'Active'
```

### ✅ **Handles Temporal Complexity**

```python
LLM discovers:
  - effective_date and end_date columns
  - Requests: Is this milestoned?
  - Learns: Yes, SCD Type 2
  - Applies: WHERE end_date IS NULL (current records)
```

### ✅ **Context-Aware Filtering**

```python
Query: "Show AUM for equity funds"

LLM reasons:
  - "equity funds" is plural
  - Should match ALL equity types
  - Uses: fund_type LIKE 'Equity%'
  
vs. Naive:
  - fund_type = 'Equity Growth' (just one type!)
```

### ✅ **Adds Useful Context Columns**

```python
LLM decides:
  "User wants AUM data. They'll also want:
   - fund name (to identify funds)
   - inception_date (for context)
   - fund_type (to see what type)
   
Even though only 'AUM' was mentioned!"
```

---

## Configuration Enhancements

### Add Business Rules to YAML

```yaml
# config/applications/fund_accounting.yaml

tables:
  funds:
    name: funds
    description: Investment fund master data
    
    # Business rules for automatic application
    business_rules:
      default_filters:
        - condition: "status = 'Active'"
          reason: "Most queries want active funds only"
          auto_apply: true
          exceptions: ["historical", "audit", "all"]
        
        - condition: "close_date IS NULL"
          reason: "Exclude closed funds"
          auto_apply: true
          exceptions: ["historical", "closed"]
        
        - condition: "end_date IS NULL"
          reason: "Current milestone records only"
          auto_apply: true
          exceptions: ["historical", "point_in_time"]
      
      common_patterns:
        equity_funds: "fund_type LIKE 'Equity%'"
        bond_funds: "fund_type LIKE 'Bond%'"
        active_funds: "status = 'Active' AND close_date IS NULL"
        large_funds: "total_aum > 100000000"
    
    # Milestoning configuration
    milestoning:
      enabled: true
      type: "SCD_TYPE_2"
      effective_date_column: "effective_date"
      end_date_column: "end_date"
      current_record_filter: "end_date IS NULL"
    
    columns:
      status:
        type: varchar
        is_dimension: true
        description: "Fund status"
        values: ["Active", "Closed", "Suspended"]
        default_filter: "Active"
      
      close_date:
        type: date
        description: "Date fund was closed (NULL = open)"
        related_filter: "close_date IS NULL for active funds"
```

---

## Implementation Roadmap

### Phase 1: Basic Iteration (Week 1)
- ✅ Semantic search initial mapping
- ✅ Get full table schema
- ✅ LLM reviews and picks columns
- ✅ Basic filter application

### Phase 2: Business Rules (Week 1-2)
- ✅ Add business_rules to YAML config
- ✅ Implement get_business_rules()
- ✅ LLM auto-applies common filters
- ✅ Status/active filtering

### Phase 3: Milestoning (Week 2)
- ✅ Detect milestoned tables
- ✅ Implement get_milestoning_info()
- ✅ Auto-apply current record filters
- ✅ Handle point-in-time queries

### Phase 4: Advanced Context (Week 2-3)
- ✅ Dimension value lookup
- ✅ Pattern matching (LIKE vs =)
- ✅ Related column suggestions
- ✅ Completeness validation

### Phase 5: Learning (Week 3+)
- ⏭️ Log successful query patterns
- ⏭️ Use query history as examples
- ⏭️ Refine based on user feedback
- ⏭️ Build query template library

---

## Summary

Your insight about **iterative context enhancement** is the key to making this truly intelligent!

### The Magic Formula:
```
Smart Query = 
  Semantic Search (what matches?) +
  Full Schema Context (what exists?) +
  Business Rules (what's standard?) +
  Milestoning Rules (what's current?) +
  Dimension Knowledge (what values?) +
  LLM Reasoning (what makes sense?) +
  Iterative Refinement (what's missing?)
```

This approach:
- ✅ Auto-applies best practices (status filters, milestoning)
- ✅ Discovers data quality rules
- ✅ Handles temporal complexity
- ✅ Adds missing context columns
- ✅ Validates completeness
- ✅ Gets smarter over time

**Shall we start implementing this iterative agentic approach?** 🚀
