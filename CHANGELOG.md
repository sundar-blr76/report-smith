# Changelog

All notable changes to ReportSmith are documented in this file.

## [Unreleased] - 2025-11-06

### Added - Predicate Resolution Enhancement

#### Early Temporal Predicate Resolution
- **Feature**: Temporal predicates (Q1 2025, Q2 2024, etc.) are now resolved during intent analysis instead of SQL generation
- **Implementation**: 
  - LLM intent analyzer now receives temporal schema context (date/time columns)
  - System prompt guides LLM to format temporal filters using SQL EXTRACT expressions
  - Example: "Q1 2025" → `EXTRACT(QUARTER FROM table.column) = 1 AND EXTRACT(YEAR FROM table.column) = 2025`
- **Files Modified**:
  - `src/reportsmith/query_processing/llm_intent_analyzer.py`
  - `src/reportsmith/query_processing/sql_generator.py`

#### Comprehensive Logging for Predicate Resolution
- **Feature**: Added detailed logging to visualize how unmapped predicates are resolved
- **Logging Tag**: `[predicate-resolution]` for easy filtering
- **Stages Logged**:
  1. Temporal schema context building
  2. Filter extraction by LLM
  3. SQL generation and WHERE clause construction
  4. Unmapped entity detection and verification
- **Files Modified**:
  - `src/reportsmith/query_processing/llm_intent_analyzer.py`
  - `src/reportsmith/query_processing/sql_generator.py`
  - `src/reportsmith/agents/nodes.py`

### Changed - Terminology Update

#### Renamed dimension_value to domain_value
- **Reason**: Better semantic clarity - "domain values" are specific values within a field
- **Scope**: Renamed consistently across entire codebase (36 occurrences)
- **Breaking Change**: External integrations referencing "dimension_value" entity type will need updates
- **Files Modified** (8 Python files + 1 config):
  - `src/reportsmith/app.py`
  - `src/reportsmith/query_processing/hybrid_intent_analyzer.py`
  - `src/reportsmith/query_processing/sql_generator.py`
  - `src/reportsmith/query_processing/intent_analyzer.py`
  - `src/reportsmith/query_processing/llm_intent_analyzer.py`
  - `src/reportsmith/agents/nodes.py`
  - `src/reportsmith/schema_intelligence/embedding_manager.py`
  - `src/reportsmith/schema_intelligence/dimension_loader.py`
  - `config/entity_mappings.yaml`
- **API Changes**:
  - `search_dimensions()` → `search_domains()`
  - `load_dimension_values()` → `load_domain_values()`
  - Collection name: `"dimension_values"` → `"domain_values"`

### Fixed

#### SQL Expression Filter Handling
- **Issue**: Complex SQL expressions (EXTRACT, CAST, DATE_TRUNC) were being parsed and failing
- **Solution**: Added detection for SQL function expressions that pass through unchanged
- **Impact**: Temporal filters now work correctly without validation errors

#### Metadata Access Bug
- **Issue**: Used `column_type` instead of `data_type` when accessing schema metadata
- **Solution**: Updated to use correct field name `data_type`
- **Impact**: Temporal column detection now works correctly

## Benefits

### Performance
- **Fewer LLM Calls**: Predicates resolved in one pass instead of multiple refinement iterations
- **Faster Execution**: No validation/refinement loops for temporal predicates

### Accuracy  
- **Better Resolution**: Schema context helps LLM make correct column mappings
- **Cleaner SQL**: Proper SQL expressions generated from the start

### Developer Experience
- **Visibility**: Clear logging of predicate resolution flow
- **Debugging**: Easy to identify where resolution fails
- **Troubleshooting**: Quick identification of unmapped entity handling

## Usage Examples

### Checking Predicate Resolution Logs
```bash
# View all predicate resolution logs
grep "\[predicate-resolution\]" logs/app.log

# Check specific stages
grep "\[predicate-resolution\].*temporal.*context" logs/app.log  # Schema context
grep "\[predicate-resolution\].*LLM extracted" logs/app.log      # Filter extraction
grep "\[predicate-resolution\].*sql-gen" logs/app.log            # SQL generation
grep "\[predicate-resolution\].*UNMAPPED" logs/app.log           # Unmapped entities
```

### Example Query Processing
Query: "List the top 5 clients by total fees paid on bond funds in Q1 2025"

**Before**: 
- Filter: `"quarter = 'Q1 2025'"` 
- SQL: `WHERE quarter = 'Q1 2025'` ❌ (fails - no such column)

**After**:
- Filter: `"EXTRACT(QUARTER FROM fees.fee_period_start) = 1 AND EXTRACT(YEAR FROM fees.fee_period_start) = 2025"`
- SQL: `WHERE EXTRACT(QUARTER FROM fee_transactions.fee_period_start) = 1 AND EXTRACT(YEAR FROM fee_transactions.fee_period_start) = 2025` ✅

## Migration Guide

### For dimension_value → domain_value Rename

If you have external code that:
- References entity type `"dimension_value"` → Update to `"domain_value"`
- Calls `search_dimensions()` → Update to `search_domains()`
- Accesses `"dimension_values"` collection → Update to `"domain_values"`

## Technical Details

### Predicate Resolution Architecture

1. **Intent Analysis Phase**:
   - `_build_temporal_schema_context()` searches for temporal columns
   - Schema context added to LLM system prompt
   - LLM resolves temporal predicates to SQL expressions

2. **SQL Generation Phase**:
   - Complex SQL expressions detected (EXTRACT, CAST, etc.)
   - Expressions passed through unchanged to WHERE clause
   - Standard filters normalized and processed

3. **Validation Phase**:
   - Temporal conditions verified in final SQL
   - Table references extracted and validated

---

**Note**: This changelog follows [Keep a Changelog](https://keepachangelog.com/) format.
