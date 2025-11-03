# Auto-Filter Implementation Summary

## Overview
Implemented automatic default filtering for columns marked with `auto_filter_on_default` property in the schema configuration. This allows columns with default values (like `is_active = true`) to be automatically filtered unless the user explicitly mentions otherwise.

## Changes Made

### 1. Schema Configuration (`config/applications/fund_accounting/schema.yaml`)
Added `auto_filter_on_default: true` property to columns that should have default filters:

```yaml
is_active:
  type: boolean
  default: true
  auto_filter_on_default: true  # Automatically filter to default value unless user specifies otherwise
```

Applied to these tables:
- `funds.is_active`
- `fund_managers.is_active`
- `account_fund_subscriptions.is_active`

### 2. Knowledge Graph Builder (`src/reportsmith/schema_intelligence/graph_builder.py`)
Updated `_add_column_nodes()` method to include `default` and `auto_filter_on_default` metadata:

```python
metadata={
    'data_type': column_def.get('type', ''),
    'description': column_def.get('description', ''),
    'nullable': column_def.get('nullable', True),
    'is_dimension': column_def.get('is_dimension', False),
    'default': column_def.get('default'),
    'auto_filter_on_default': column_def.get('auto_filter_on_default', False),
}
```

### 3. SQL Generator (`src/reportsmith/query_processing/sql_generator.py`)
Added two key enhancements:

#### a. Track Explicitly Filtered Columns
Modified `_build_where_conditions()` to track columns that are explicitly filtered by the user in the `explicitly_filtered_columns` set.

#### b. Auto-Filter Method
Added `_build_auto_filter_conditions()` method that:
1. Scans all tables involved in the query
2. Identifies columns with `auto_filter_on_default = true`
3. Skips columns already filtered by the user
4. Generates appropriate filter conditions based on data type:
   - Boolean: `column = true/false`
   - String: `column = 'value'`
   - Numeric: `column = value`

## How It Works

### Example 1: Basic Query (Auto-Filter Applied)
**Query:** "Show AUM for all equity funds"

**Generated SQL:**
```sql
SELECT SUM(funds.total_aum) AS aum,
       funds.fund_type AS fund_type,
       funds.base_currency AS base_currency,
       funds.risk_rating AS risk_rating
  FROM funds
 WHERE funds.fund_type = 'Equity Growth'
   AND funds.is_active = true  -- Auto-filter applied
 GROUP BY funds.fund_type, funds.base_currency, funds.risk_rating
```

**Log Output:**
```
[sql-gen][auto-filter] applied default filter: funds.is_active = true (auto_filter_on_default=true)
```

### Example 2: Negation Query (Auto-Filter Applied)
**Query:** "Show AUM for all non equity funds"

**Generated SQL:**
```sql
SELECT SUM(funds.total_aum) AS aum,
       funds.fund_type AS fund_type,
       funds.base_currency AS base_currency,
       funds.risk_rating AS risk_rating
  FROM funds
 WHERE funds.fund_type != 'Equity Growth'
   AND funds.is_active = true  -- Auto-filter still applied
 GROUP BY funds.fund_type, funds.base_currency, funds.risk_rating
```

### Example 3: Explicit Filter (Auto-Filter Skipped)
If the user explicitly filters on `is_active`, the auto-filter is skipped:

**Query:** "Show AUM for inactive equity funds"
- The LLM should detect "inactive" and add `is_active = false` to filters
- The auto-filter logic will skip adding `is_active = true` because the column is already filtered

## Benefits

1. **Automatic Data Quality**: Ensures queries default to active/valid records without requiring explicit filters
2. **Schema-Driven**: Configuration is declarative in the schema YAML files
3. **Property-Based**: Uses column properties (not hardcoded column names like "is_active")
4. **Smart Override**: Respects user intent when they explicitly filter the column
5. **Type-Safe**: Handles different data types appropriately (boolean, string, numeric)

## Future Enhancements

1. **LLM Intent Detection**: Improve LLM's ability to detect keywords like "inactive", "deactivated", "disabled" and map them to appropriate filters
2. **Multiple Auto-Filters**: Support multiple auto-filter conditions per table
3. **Conditional Auto-Filters**: Support auto-filters based on context or other conditions
4. **Configuration Options**: Add schema-level configuration to enable/disable auto-filtering globally

## Testing

Tested with various queries:
- ✅ Basic aggregation with auto-filter
- ✅ Negation queries (non-equity) with auto-filter
- ✅ Multi-table queries (auto-filter applied to relevant tables only)
- ⚠️ Inactive/deactivated queries (requires LLM improvement for proper detection)

## Related Files

- `config/applications/fund_accounting/schema.yaml` - Schema configuration
- `src/reportsmith/schema_intelligence/graph_builder.py` - Metadata loading
- `src/reportsmith/query_processing/sql_generator.py` - SQL generation with auto-filters
