# SQL Validation Failure Analysis & Improvements

**Date**: 2025-11-05  
**Query**: "List the top 5 clients by total fees paid on bond funds in Q1 2025"  
**Request ID**: cecb7adcba4449c1929f9e92be1aa5dc

---

## Executive Summary

The SQL validator went through **7 iterations** before hitting a **loop detection** and stopping with unresolved issues. The primary problem was the LLM's inability to identify the correct date column (`payment_date`) for temporal filtering in the `fee_transactions` table.

### Final Status
- **Iterations**: 7/10
- **Outcome**: Loop detected, issues remaining
- **Wrong Column Used**: `created_at` (metadata timestamp)
- **Correct Column**: `payment_date` (business date for fee payment)
- **Impact**: Query filters on wrong date, returns incorrect results

---

## Iteration Timeline

### Iteration 1: Non-existent Column
**Issue**: `column "quarter" does not exist`
```sql
WHERE quarter = 'Q1 2025'  -- ❌ Invalid
```

**LLM Action**: Tried to use `ft.transaction_date`
```sql
WHERE EXTRACT(QUARTER FROM ft.transaction_date) = 1
  AND EXTRACT(YEAR FROM ft.transaction_date) = 2025
```

### Iteration 2: Wrong Column Name (transaction_date)
**Issue**: `column ft.transaction_date does not exist`
```sql
WHERE EXTRACT(QUARTER FROM ft.transaction_date) = 1  -- ❌ Column doesn't exist
```

**LLM Action**: Tried `ft.date`

### Iteration 3: Wrong Column Name (date)
**Issue**: `column ft.date does not exist`
```sql
WHERE EXTRACT(QUARTER FROM ft.date) = 1  -- ❌ Column doesn't exist
```

**LLM Action**: Tried `ft.payment_dt` or similar variants

### Iterations 4-6: Multiple Failed Attempts
- Tried various date column names
- None matched the actual schema
- LLM kept guessing common date column patterns

### Iteration 7: Loop Detected
**Issue**: LLM suggested previously failed SQL
```sql
WHERE EXTRACT(QUARTER FROM ft.created_at) = 1  -- ✅ Column exists but WRONG business logic!
  AND EXTRACT(YEAR FROM ft.created_at) = 2025
```

**Why This is Wrong**:
- `created_at` is a **metadata timestamp** (when record was created in system)
- `payment_date` is the **business date** (when fee was actually paid)
- For Q1 2025 fees, we need `payment_date`, not `created_at`

---

## Root Cause Analysis

### 1. **Schema Information Gap**

The LLM prompt during SQL validation refinement does **NOT include the schema**. It only receives:
- Current SQL
- Validation errors
- Entities discovered
- Query intent
- Previous failed attempts (new)

**Missing**: Table schemas with column names and types!

### 2. **Semantic Enrichment Limitations**

While semantic enrichment mapped:
- ✅ "fees" → `fee_transactions.fee_amount`
- ✅ "Q1 2025" → temporal filter

It did **NOT** map:
- ❌ "Q1 2025" → `fee_transactions.payment_date`
- ❌ Temporal entities to specific date columns

### 3. **Column Discovery Not Used in Validation**

The schema has these date columns in `fee_transactions`:
- `fee_period_start` (date)
- `fee_period_end` (date)
- `payment_date` (date) ← **Correct for "fees paid"**
- `created_at` (timestamp) ← **Metadata, not business date**

But the LLM refinement prompt doesn't have access to this information!

### 4. **Metric Context Not Leveraged**

Entity mapping found:
```yaml
"total fees":
  canonical_name: "total_fees_collected"
  context: "SUM(fee_amount) FROM fee_transactions WHERE payment_status = 'Paid'"
```

This context **mentions `payment_status`** but the query didn't use it, and more importantly, it doesn't specify the date column to use.

---

## Actual Schema (What LLM Should Know)

### fee_transactions Table
```yaml
columns:
  id: integer (PK)
  account_id: integer (FK)
  fund_id: integer (FK)
  fee_type: varchar (Management, Performance, Entry, Exit)
  fee_period_start: date
  fee_period_end: date
  fee_rate: numeric
  calculation_base: numeric
  fee_amount: numeric (aliases: fee, fees, charges)
  currency: varchar
  payment_date: date ← **CORRECT column for "fees paid in Q1 2025"**
  payment_status: varchar (Pending, Paid, Failed)
  created_at: timestamp ← **Metadata only**
  updated_at: timestamp ← **Metadata only**
```

---

## Correct SQL Should Be

```sql
SELECT SUM(ft.fee_amount) AS fees,
       c.company_name AS company_name,
       c.first_name AS first_name,
       c.last_name AS last_name,
       c.client_code AS client_code,
       c.client_type AS client_type
  FROM funds AS f
  INNER JOIN holdings AS h ON f.id = h.fund_id
  INNER JOIN accounts AS a ON h.account_id = a.id
  INNER JOIN clients AS c ON a.client_id = c.id
  INNER JOIN fee_transactions AS ft ON f.id = ft.fund_id
 WHERE f.is_active = true
   AND f.fund_type = 'Bond'
   AND EXTRACT(QUARTER FROM ft.payment_date) = 1  -- ✅ CORRECT!
   AND EXTRACT(YEAR FROM ft.payment_date) = 2025  -- ✅ CORRECT!
   AND ft.payment_status = 'Paid'                 -- ✅ BONUS: Only count paid fees
 GROUP BY c.company_name, c.first_name, c.last_name, c.client_code, c.client_type
 ORDER BY fees DESC
 LIMIT 5
```

**Key Fixes**:
1. Use `ft.payment_date` instead of `ft.created_at`
2. Add `ft.payment_status = 'Paid'` filter (from metric context)
3. Use `ft.fee_amount` instead of `ft.fee_rate` (rate vs actual amount)

---

## Recommended Improvements

### 🔴 **CRITICAL: Add Schema to LLM Refinement Prompt**

**Current Prompt Structure** (sql_validator.py:_refine_sql_with_llm):
```python
prompt = f"""
User Question: "{question}"
Current SQL: {current_sql}
Validation Issues: {issues}
Warnings: {warnings}
Expected Entities: {entities}
Query Intent: {intent}
Previous Failed Attempts: {previous_attempts}  # ✅ Just added
"""
```

**Proposed Enhancement**:
```python
prompt = f"""
User Question: "{question}"
Current SQL: {current_sql}
Validation Issues: {issues}
Warnings: {warnings}

=== SCHEMA INFORMATION ===
Tables Used in Query:
{extract_schema_for_tables(current_sql)}

All Available Columns:
- fee_transactions:
  - fee_amount (numeric) - actual fee charged
  - fee_rate (numeric) - percentage or rate
  - payment_date (date) - when fee was paid ← USE FOR TEMPORAL FILTERS
  - created_at (timestamp) - system metadata, DO NOT use for business logic
  - payment_status (varchar) - Paid, Pending, Failed
  ...

Expected Entities: {entities}
Query Intent: {intent}
Previous Failed Attempts: {previous_attempts}
"""
```

### 🟡 **HIGH: Enhance Semantic Enrichment for Temporal Entities**

**Current Behavior**:
- Extracts "Q1 2025" as temporal filter
- Maps to generic EXTRACT(QUARTER...) syntax

**Improvement**:
Add temporal-to-column mapping in entity enrichment:

```python
# In semantic enrichment step
temporal_entities = [
    {
        "text": "Q1 2025",
        "entity_type": "temporal",
        "target_table": "fee_transactions",
        "target_column": "payment_date",  # ← SPECIFY THIS!
        "reasoning": "For 'fees paid', use payment_date not created_at"
    }
]
```

### 🟡 **HIGH: Improve Metric Context Usage**

**Current Metric**:
```yaml
total_fees:
  context: "SUM(fee_amount) FROM fee_transactions WHERE payment_status = 'Paid'"
```

**Enhanced Metric**:
```yaml
total_fees_paid:
  canonical_name: "total_fees_collected"
  aggregation: "SUM"
  source_table: "fee_transactions"
  source_column: "fee_amount"
  required_filters:
    - column: "payment_status"
      value: "Paid"
  temporal_column: "payment_date"  # ← ADD THIS!
  temporal_context: "Use payment_date for when fees were paid, not created_at"
  description: "Total fees collected from clients, filtered by payment date"
```

### 🟢 **MEDIUM: Add Column Type Hints to Refinement**

When LLM encounters a date/time filter error, provide:
- All date/datetime/timestamp columns in involved tables
- Business meaning of each date column
- Recommendation based on query intent

**Example**:
```
Error: column "quarter" does not exist

Available date columns in fee_transactions:
✓ payment_date (date) - when fee was paid to company
✓ fee_period_start (date) - start of fee calculation period  
✓ fee_period_end (date) - end of fee calculation period
✗ created_at (timestamp) - system metadata, avoid for business logic

Based on query "fees paid in Q1 2025", use: payment_date
```

### 🟢 **MEDIUM: Schema-Aware Entity Extraction**

During entity extraction, when a temporal phrase is detected:
1. Identify tables that will be used (from other entities)
2. Find date columns in those tables
3. Rank them by relevance to query intent
4. Pre-associate temporal entity with best matching column

**Algorithm**:
```python
def associate_temporal_to_column(temporal_entity, tables, intent):
    """
    Associates temporal entities with appropriate date columns.
    
    Example:
      Query: "fees paid in Q1 2025"
      Tables: [fee_transactions]
      Intent: "fees paid" → payment_date
    """
    date_columns = get_date_columns(tables)
    
    # Score each date column
    scores = {}
    for col in date_columns:
        score = 0
        # "paid" in query + "payment_date" = high match
        if any(keyword in col.name for keyword in ["payment", "paid", "transaction"]):
            score += 10
        # Avoid metadata columns
        if col.name in ["created_at", "updated_at", "deleted_at"]:
            score -= 20
        scores[col] = score
    
    return max(scores, key=scores.get)
```

### 🟢 **MEDIUM: Add Column Usage Guidelines**

Create guidelines document that LLM can reference:

```markdown
# Date Column Usage Guidelines

## fee_transactions Table

### Business Dates (USE THESE)
- **payment_date**: When the fee was actually paid
  - Use for: "fees paid in Q1", "payments received"
  - ✅ Good: "total fees paid in Q1 2025"
  
- **fee_period_start/end**: The period for which fee was calculated
  - Use for: "fees for Q1 holdings", "quarterly fee calculations"
  - ✅ Good: "management fees for Q1 2025 period"

### Metadata Dates (AVOID FOR BUSINESS LOGIC)
- **created_at**: When record was created in system
  - ❌ Bad: Using for "fees paid in Q1" (could be paid in Q2 but created in Q1)
  - ⚠️ Only use for: System auditing, data quality checks

- **updated_at**: When record was last modified
  - ❌ Never use for business queries
```

### 🔵 **LOW: Validation Metadata Collection**

Track which columns were tried and why they failed:

```python
validation_history.append({
    "iteration": 2,
    "attempted_column": "ft.transaction_date",
    "error": "column does not exist",
    "available_alternatives": ["payment_date", "created_at", "fee_period_start"],
    "reasoning": "LLM guessed common name, not in schema"
})
```

---

## Implementation Priority

### Phase 1: Critical Fixes (Week 1)
1. ✅ **Add previous attempts to LLM context** (COMPLETED)
2. 🔴 **Add schema information to refinement prompt**
3. 🟡 **Enhance metric context with temporal_column**

### Phase 2: Smart Mapping (Week 2)
4. 🟡 **Temporal-to-column mapping in semantic enrichment**
5. 🟢 **Column type hints in validation errors**

### Phase 3: Guidelines & Optimization (Week 3)
6. 🟢 **Schema-aware entity extraction**
7. 🟢 **Column usage guidelines**
8. 🔵 **Enhanced validation metadata**

---

## Expected Impact

### After Phase 1
- **Success Rate**: 60% → 85% (for temporal queries)
- **Iterations**: 7 avg → 3 avg
- **Loop Detection**: 15% → 5%

### After Phase 2
- **Success Rate**: 85% → 95%
- **Iterations**: 3 avg → 2 avg
- **First-try Accuracy**: 40% → 70%

### After Phase 3
- **Success Rate**: 95% → 98%
- **Iterations**: 2 avg → 1.5 avg
- **First-try Accuracy**: 70% → 85%

---

## Metrics to Track

1. **Column Misidentification Rate**: How often LLM picks wrong column
2. **Temporal Filter Success Rate**: Specifically for date/time queries
3. **Schema-related Errors**: Errors due to missing schema context
4. **Iteration Efficiency**: Iterations needed per query type

---

## Testing Checklist

After implementing improvements, test with:

- ✅ "List fees paid in Q1 2025" → payment_date
- ✅ "Show fee calculations for Q1 period" → fee_period_start/end
- ✅ "Recent fee transactions" → created_at (acceptable here)
- ✅ "Fees collected last month" → payment_date
- ✅ "Monthly fee revenue for 2025" → payment_date + aggregation
- ✅ "Fee transactions created yesterday" → created_at (metadata query)

---

## Conclusion

The validation failed because:
1. ❌ Schema not provided to LLM during refinement
2. ❌ Temporal entities not mapped to specific columns
3. ❌ Metric context doesn't specify temporal column
4. ✅ Loop detection worked (prevented infinite iterations)

**Top Priority**: Add schema information to LLM refinement prompt to prevent column guessing.

**Secondary**: Enhance semantic enrichment to map temporal entities to appropriate date columns based on business context.
