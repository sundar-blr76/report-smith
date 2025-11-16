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

## Test Query Consolidation Rationale

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

## Documentation Files

### Archived Documentation (Issue #6)

The following documentation files have been archived to keep the root directory clean and focused:

**Implementation and History:**
- **IMPLEMENTATION_HISTORY.md** - Detailed implementation notes and historical context
- **COMMIT_SUMMARY.md** - Commit-level change summary (now tracked in CHANGELOG.md)
- **OUTSTANDING_ISSUES.md** - Historical issues list (use GitHub Issues instead)

**Task-Specific Documentation:**
- **GITHUB_ISSUES_TEMPLATE.md** - Template for creating GitHub issues (task completed)
- **HOW_TO_CREATE_ISSUES.md** - Guide for issue creation (task completed)
- **CLEANUP_ANALYSIS.md** - Analysis that led to these cleanup tasks

**Technical Documentation:**
- **EMBEDDING_STRATEGY.md** - Vector embedding strategy details
- **PERFORMANCE.md** - Performance analysis and benchmarks
- **SQL_VALIDATION_FAILURE_ANALYSIS.md** - SQL validation debugging notes

### Current Core Documentation

The root directory now contains only essential documentation:
- **README.md** - Project overview and quick start
- **SETUP.md** - Detailed setup instructions
- **CHANGELOG.md** - Version history and changes
- **CONTRIBUTING.md** - Contribution guidelines (includes cleanup procedures)
- **TESTING_GUIDE.md** - Testing procedures and validation

### Documentation Consolidation Rationale

Documentation was consolidated to:
1. Reduce clutter in root directory (from 11 to 5 .md files)
2. Keep only actively maintained documentation visible
3. Archive historical/task-specific docs for reference
4. Make it easier for new contributors to find relevant docs
5. Follow best practices for OSS project structure

## Date Archived

November 16, 2025
