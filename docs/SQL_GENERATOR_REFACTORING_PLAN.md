# SQL Generator Refactoring Plan

## Overview

The `sql_generator.py` file is currently 2383 lines with 23 methods. This document outlines the plan to split it into a modular structure for better maintainability and testability.

## Current State Analysis

### File Statistics
- **Total Lines**: 2383
- **Number of Methods**: 23
- **Largest Methods**:
  - `_build_where_conditions` (451 lines) - WHERE clause construction
  - `_enrich_with_context_columns` (421 lines) - Context column enrichment
  - `_refine_column_transformations` (333 lines) - Column transformation refinement
  - `generate` (156 lines) - Main orchestration method
  - `_build_select_columns` (141 lines) - SELECT clause construction

### Current Dependencies
- **External Imports**:
  - `SchemaKnowledgeGraph` - Schema information
  - `SQLValidator` - SQL validation
  - `CacheManager` - Caching
  - `Logger` - Logging
  
- **Internal Usage**:
  - `src/reportsmith/agents/nodes.py` imports `SQLGenerator`
  - Tests import from `reportsmith.query_processing.sql_generator`

## Proposed Module Structure

```
src/reportsmith/query_processing/sql_generation/
├── __init__.py                 # Exports for backward compatibility
├── models.py                   # Data classes (SQLColumn, SQLJoin, SQLQuery)
├── base_generator.py           # Base class with core orchestration
├── select_builder.py           # SELECT clause construction
├── join_builder.py             # JOIN logic
├── filter_builder.py           # WHERE clause construction
├── aggregate_builder.py        # GROUP BY, HAVING
├── ranking_builder.py          # ORDER BY, LIMIT
├── column_enricher.py          # Context columns, transformations
└── utils.py                    # Helper functions (normalization, etc.)
```

## Module Responsibilities

### models.py (Data Classes)
**Lines**: ~100
**Content**:
- `AggregationType` enum
- `IntentType` enum
- `SQLColumn` dataclass with `to_sql()` method
- `SQLJoin` dataclass with `to_sql()` method
- `SQLQuery` dataclass with `to_sql()` method

### base_generator.py (Core Orchestration)
**Lines**: ~200
**Content**:
- `SQLGenerator` class initialization (`__init__`)
- Main `generate()` orchestration method
- Utility methods: `_detect_llm_provider`, `_detect_llm_model`, `_get_column_data_type`
- Explanation building: `_build_explanation`

### select_builder.py
**Lines**: ~150
**Content**:
- `SelectBuilder` class
- `_build_select_columns` method (141 lines)
- Column ordering logic: `_apply_column_ordering` (44 lines)

### join_builder.py
**Lines**: ~100
**Content**:
- `JoinBuilder` class
- `_build_from_and_joins` method (68 lines)
- Join optimization and validation

### filter_builder.py (Largest Module)
**Lines**: ~600
**Content**:
- `FilterBuilder` class
- `_build_where_conditions` method (451 lines)
- `_build_auto_filter_conditions` method (80 lines)
- `_merge_equality_filters` method (46 lines)
- `_normalize_filter_value` method (51 lines)
- `_normalize_column_reference` method (115 lines)

### aggregate_builder.py
**Lines**: ~80
**Content**:
- `AggregateBuilder` class
- `_build_group_by` method (27 lines)
- Aggregation validation and optimization

### ranking_builder.py
**Lines**: ~200
**Content**:
- `RankingBuilder` class
- `_build_order_by` method (33 lines)
- `_determine_limit` method (33 lines)
- `_fallback_add_ranking_identifiers` method (107 lines)

### column_enricher.py
**Lines**: ~800
**Content**:
- `ColumnEnricher` class
- `_enrich_with_context_columns` method (421 lines)
- `_refine_column_transformations` method (333 lines)

### utils.py
**Lines**: ~50
**Content**:
- Shared utility functions
- String normalization helpers
- Common validation logic

## Implementation Steps

### Phase 1: Preparation
1. ✅ Create directory structure: `src/reportsmith/query_processing/sql_generation/`
2. Run full test suite to establish baseline
3. Document all current imports and usages
4. Create feature branch for refactoring

### Phase 2: Extract Data Models
1. Create `models.py` with data classes
2. Update imports in `sql_generator.py`
3. Run tests to verify no breakage

### Phase 3: Extract Builders (One at a Time)
For each builder module:
1. Create new module file
2. Extract relevant methods
3. Add proper imports and dependencies
4. Update `sql_generator.py` to use new module
5. Run tests after each extraction
6. Commit incrementally

**Order of extraction**:
1. `utils.py` (small, no dependencies)
2. `join_builder.py` (self-contained)
3. `aggregate_builder.py` (small, simple)
4. `select_builder.py` (medium complexity)
5. `ranking_builder.py` (medium complexity)
6. `filter_builder.py` (large, many dependencies)
7. `column_enricher.py` (large, complex)

### Phase 4: Create Base Generator
1. Extract remaining orchestration logic to `base_generator.py`
2. Compose all builders in base generator
3. Update internal method calls

### Phase 5: Backward Compatibility
1. Create `__init__.py` that exports `SQLGenerator`
2. Update `sql_generator.py` to import from new modules
3. Or make `sql_generator.py` a thin compatibility shim
4. Verify all existing imports still work

### Phase 6: Testing & Validation
1. Run full test suite
2. Run validation scripts
3. Test with example queries
4. Check test coverage (should maintain or improve)
5. Performance testing (ensure no regression)

### Phase 7: Cleanup & Documentation
1. Update docstrings
2. Update README and CONTRIBUTING.md
3. Add migration guide for developers
4. Update any architecture documentation

## Backward Compatibility Strategy

### Option 1: Keep `sql_generator.py` as Shim
```python
# sql_generator.py
"""Backward compatibility shim for SQLGenerator"""
from reportsmith.query_processing.sql_generation import SQLGenerator

__all__ = ['SQLGenerator', 'SQLColumn', 'SQLJoin', 'SQLQuery', 
           'AggregationType', 'IntentType']
```

### Option 2: Re-export from `__init__.py`
```python
# sql_generation/__init__.py
from .base_generator import SQLGenerator
from .models import SQLColumn, SQLJoin, SQLQuery, AggregationType, IntentType

__all__ = ['SQLGenerator', 'SQLColumn', 'SQLJoin', 'SQLQuery',
           'AggregationType', 'IntentType']
```

## Testing Strategy

### Unit Tests
- Test each builder module independently
- Mock dependencies (schema, cache, etc.)
- Test edge cases and error handling

### Integration Tests
- Test complete SQL generation pipeline
- Use real schema and queries
- Verify generated SQL matches expectations

### Regression Tests
- Run existing test suite
- Compare output before/after refactoring
- Ensure no behavioral changes

## Risks & Mitigation

### Risk 1: Breaking Existing Code
**Mitigation**: 
- Maintain backward compatibility through imports
- Extensive testing before merging
- Incremental commits for easy rollback

### Risk 2: Performance Regression
**Mitigation**:
- Benchmark before/after
- Profile key methods
- Optimize if needed

### Risk 3: Complex Dependencies Between Methods
**Mitigation**:
- Careful analysis of method dependencies
- Extract in logical order
- Use dependency injection for shared state

### Risk 4: Time Investment
**Mitigation**:
- Estimate: 6-8 hours as per issue
- Can be done incrementally over multiple sessions
- Each phase can be committed separately

## Success Criteria

- [ ] No single file >800 lines
- [ ] All existing tests passing
- [ ] No breaking changes to external API
- [ ] Code coverage maintained or improved
- [ ] Documentation updated
- [ ] Performance maintained (within 5%)
- [ ] Each module has clear, single responsibility
- [ ] Improved testability (easier to mock and test)

## Timeline Estimate

- **Phase 1 (Preparation)**: 1 hour
- **Phase 2 (Data Models)**: 30 minutes
- **Phase 3 (Builders)**: 3-4 hours
- **Phase 4 (Base Generator)**: 1 hour
- **Phase 5 (Compatibility)**: 30 minutes
- **Phase 6 (Testing)**: 1 hour
- **Phase 7 (Documentation)**: 30 minutes

**Total**: 7-8 hours

## Notes

This refactoring should be done as a separate, focused task with:
- Dedicated time block
- Full test coverage verification
- Careful attention to backward compatibility
- Incremental commits for safety

## Status

**Current**: Planning complete, directory structure created
**Next**: Ready for implementation when time allows
**Owner**: To be assigned
**Priority**: Medium (after quick wins are complete)
