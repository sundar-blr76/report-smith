# Archive Directory

This directory contains archived versions of files that have been consolidated or superseded.

## Test Query Files

### Archived Test Query YAML Files

The following test query files have been archived as part of Issue #2 (Consolidate Test YAML Files):

- **test_queries.yaml** (original version, 30 queries)
  - First comprehensive test suite
  - Generated: 2025-11-06
  - Superseded by test_queries_comprehensive_new.yaml

- **test_queries_comprehensive.yaml** (39 queries)
  - Intermediate comprehensive version
  - Created to expand test coverage
  - Superseded by test_queries_comprehensive_new.yaml

### Current Canonical Version

The current canonical test queries file is:
- **`/test_queries.yaml`** (formerly test_queries_comprehensive_new.yaml)
- Contains 28 carefully curated test queries
- Includes validation rules and success criteria
- Use this file for all test query validation

## Consolidation Rationale

These files were consolidated because:
1. Having 3 similar files created confusion about which to use
2. test_queries_comprehensive_new.yaml was the most recent and best structured
3. It included additional metadata (validation_rules, success_criteria)
4. Documentation (TESTING_GUIDE.md) already referenced it as the primary version

## Connection Manager

### Archived Connection Manager

- **connection_manager.py** (246 lines)
  - Original connection manager implementation
  - Superseded by simple_connection_manager.py
  - Archived as part of Issue #3 (Remove Duplicate Connection Manager)

### Current Connection Manager

The current connection manager is:
- **`src/reportsmith/database/simple_connection_manager.py`**
- Simpler, more maintainable implementation
- Used throughout the codebase

### Removal Rationale

The original connection_manager.py was archived because:
1. Only simple_connection_manager.py is actively used in the codebase
2. All imports reference simple_connection_manager
3. Having two similar implementations created confusion
4. simple_connection_manager.py is cleaner and more maintainable

## Date Archived

November 16, 2025
