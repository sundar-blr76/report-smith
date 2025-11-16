# GitHub Issues for Cleanup and Refactoring

**Repository**: sundar-blr76/report-smith  
**Assignee**: @agent  
**Labels**: refactoring, cleanup, technical-debt

---

## Issue 1: Organize Test and Validation Scripts

**Title**: Move test/validation scripts from root to tests/validation/

**Priority**: High  
**Estimated Time**: 30 minutes  
**Labels**: cleanup, quick-win

**Description**:
Currently, we have 8 test and validation scripts cluttering the root directory. These should be organized into a proper test structure.

**Current State**:
- 8 scripts in root: `test_cache_payload_display.py`, `test_cache_performance.py`, `test_json_viewer.py`, `test_sql_gen_error_fix.py`, `validate_currency_handling.py`, `validate_fixes.py`, `validate_temporal_predicates.py`, `validate_test_queries.py`

**Tasks**:
- [ ] Create `tests/validation/` directory
- [ ] Move all `test_*.py` scripts from root to `tests/validation/`
- [ ] Move all `validate_*.py` scripts from root to `tests/validation/`
- [ ] Update `run_all_validations.py` to reference new paths
- [ ] Test that all validation scripts still work
- [ ] Update documentation references

**Success Criteria**:
- Root directory has max 1 test runner script (`run_all_validations.py`)
- All validation scripts work from new location
- Documentation updated

---

## Issue 2: Consolidate Test YAML Files

**Title**: Review and consolidate duplicate test query YAML files

**Priority**: High  
**Estimated Time**: 1 hour  
**Labels**: cleanup, quick-win

**Description**:
We have 3 similar test query files (42K total) with unclear purposes and potential duplication.

**Current State**:
- `test_queries.yaml` (15K)
- `test_queries_comprehensive.yaml` (13K)
- `test_queries_comprehensive_new.yaml` (14K)

**Tasks**:
- [ ] Review content of all 3 YAML files
- [ ] Identify overlaps and differences
- [ ] Determine canonical version or merge into single file
- [ ] Archive or delete redundant versions
- [ ] Add header comment indicating canonical status and purpose
- [ ] Update scripts/docs that reference old files

**Success Criteria**:
- Single authoritative test queries file
- Clear documentation of test query structure
- No broken references

---

## Issue 3: Remove Duplicate Connection Manager

**Title**: Identify and remove duplicate connection manager implementation

**Priority**: High  
**Estimated Time**: 1-2 hours  
**Labels**: refactoring, technical-debt

**Description**:
Two similar connection manager implementations exist, creating confusion about which is active.

**Current State**:
- `database/connection_manager.py` (246 lines)
- `database/simple_connection_manager.py` (230 lines)

**Tasks**:
- [ ] Identify which connection manager is actively used
- [ ] Check all imports across codebase
- [ ] Document differences and decision rationale
- [ ] Remove or deprecate unused version
- [ ] Add migration guide if needed (in code comments)
- [ ] Run full test suite to verify

**Success Criteria**:
- Single connection manager implementation
- All imports updated correctly
- All tests passing
- Documentation updated

---

## Issue 4: Add Cleanup Documentation and Scripts

**Title**: Document and automate cleanup of generated files

**Priority**: Medium  
**Estimated Time**: 1 hour  
**Labels**: documentation, tooling

**Description**:
Generated files (coverage reports, cache, logs) accumulate but lack documented cleanup process.

**Current State**:
- `htmlcov/` (3.4M), `.coverage` (52K), `.pytest_cache/` (32K), `logs/scratch.json` (276K)

**Tasks**:
- [ ] Create `scripts/cleanup.sh` with cleanup commands
- [ ] Add Makefile targets: `make clean`, `make clean-logs`, `make clean-coverage`
- [ ] Document cleanup process in CONTRIBUTING.md
- [ ] Verify all generated files are in `.gitignore`
- [ ] Add optional cleanup to CI/CD if applicable

**Example Script**:
```bash
#!/bin/bash
# Clean coverage reports
rm -rf htmlcov/ .coverage .coverage.*

# Clean pytest cache
rm -rf .pytest_cache/

# Clean logs (keep structure)
rm -f logs/*.log logs/*.json
rm -rf logs/semantic_debug/*.json

# Clean Python cache
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
```

**Success Criteria**:
- Cleanup script created and tested
- Documentation updated
- Easy cleanup for developers

---

## Issue 5: Split sql_generator.py into Modules

**Title**: Refactor sql_generator.py into modular components

**Priority**: High  
**Estimated Time**: 6-8 hours  
**Labels**: refactoring, technical-debt, breaking-down-large-files

**Description**:
`sql_generator.py` is 2,383 lines - too large for easy maintenance and testing.

**Current State**:
- Single monolithic file with multiple responsibilities
- Difficult to navigate and test individual components

**Proposed Structure**:
```
query_processing/sql_generation/
  ├── __init__.py
  ├── base_generator.py        # Base class and shared utilities
  ├── select_builder.py         # SELECT clause construction
  ├── join_builder.py           # JOIN logic
  ├── filter_builder.py         # WHERE clause construction
  ├── aggregate_builder.py      # GROUP BY, aggregations
  └── ranking_builder.py        # ORDER BY, LIMIT, ranking queries
```

**Tasks**:
- [ ] Create new directory structure
- [ ] Extract base generator class
- [ ] Split SELECT clause logic to `select_builder.py`
- [ ] Split JOIN logic to `join_builder.py`
- [ ] Split WHERE/filter logic to `filter_builder.py`
- [ ] Split aggregation logic to `aggregate_builder.py`
- [ ] Split ranking logic to `ranking_builder.py`
- [ ] Update imports across codebase
- [ ] Maintain backward compatibility via `__init__.py`
- [ ] Run full test suite
- [ ] Update documentation

**Success Criteria**:
- No single file >800 lines
- All tests passing
- No breaking changes to external API
- Improved testability

---

## Issue 6: Consolidate Documentation Files

**Title**: Merge and consolidate documentation files in root

**Priority**: Medium  
**Estimated Time**: 1-2 hours  
**Labels**: documentation, cleanup

**Description**:
8 markdown files in root directory - some with overlapping content.

**Current State**:
- CHANGELOG.md
- COMMIT_SUMMARY.md (tracking commits)
- IMPLEMENTATION_HISTORY.md (implementation details)
- OUTSTANDING_ISSUES.md (issue tracking)
- CONTRIBUTING.md
- README.md
- SETUP.md
- TESTING_GUIDE.md

**Tasks**:
- [ ] Review overlap between COMMIT_SUMMARY.md and CHANGELOG.md
- [ ] Merge commit tracking into CHANGELOG.md
- [ ] Review OUTSTANDING_ISSUES.md - consider GitHub Issues instead
- [ ] Archive IMPLEMENTATION_HISTORY.md to `docs/archive/`
- [ ] Keep only: README, SETUP, CHANGELOG, CONTRIBUTING, TESTING_GUIDE, CLEANUP_ANALYSIS
- [ ] Update cross-references

**Success Criteria**:
- ≤6 markdown files in root
- No content loss
- Clear purpose for each remaining doc

---

## Issue 7: Refactor Cache Manager into Modules

**Title**: Split cache_manager.py into specialized cache components

**Priority**: Medium  
**Estimated Time**: 4-5 hours  
**Labels**: refactoring, technical-debt

**Description**:
`cache_manager.py` (562 lines) handles multiple cache types and strategies in single file.

**Proposed Structure**:
```
utils/caching/
  ├── __init__.py
  ├── base_cache.py            # Abstract base class
  ├── sql_cache.py             # SQL query caching
  ├── embedding_cache.py       # Vector embedding caching
  ├── llm_cache.py             # LLM response caching
  └── cache_strategies.py      # TTL, LRU, etc.
```

**Tasks**:
- [ ] Create new directory structure
- [ ] Extract base cache interface
- [ ] Split SQL caching to `sql_cache.py`
- [ ] Split embedding caching to `embedding_cache.py`
- [ ] Split LLM caching to `llm_cache.py`
- [ ] Extract cache strategies to separate module
- [ ] Update imports
- [ ] Maintain backward compatibility
- [ ] Test all cache types
- [ ] Update documentation

**Success Criteria**:
- Clear separation of concerns
- Each cache type independently testable
- All tests passing

---

## Issue 8: Refactor Intent Analyzer Hierarchy

**Title**: Create base class and reduce duplication in intent analyzers

**Priority**: Medium  
**Estimated Time**: 3-4 hours  
**Labels**: refactoring, technical-debt

**Description**:
Three intent analyzers with overlapping functionality and no clear hierarchy.

**Current State**:
- `intent_analyzer.py` (387 lines)
- `llm_intent_analyzer.py` (1,096 lines)
- `hybrid_intent_analyzer.py` (777 lines)

**Tasks**:
- [ ] Analyze common patterns and utilities
- [ ] Create abstract base class `BaseIntentAnalyzer`
- [ ] Extract shared logic (entity extraction, filtering, etc.)
- [ ] Refactor each analyzer to extend base class
- [ ] Consider strategy pattern for different analysis approaches
- [ ] Update tests
- [ ] Document analyzer selection criteria

**Success Criteria**:
- Clear inheritance hierarchy
- Reduced code duplication (target: 20% reduction)
- Easier to add new analyzer types
- All tests passing

---

## Issue 9: Add Log Rotation and Management

**Title**: Implement log rotation and cleanup automation

**Priority**: Low  
**Estimated Time**: 2 hours  
**Labels**: tooling, maintenance

**Description**:
Logs accumulate without rotation or automated cleanup.

**Current State**:
- `logs/scratch.json` (277KB)
- Various .log files
- `logs/semantic_debug/` subdirectory

**Tasks**:
- [ ] Add Python logging rotation configuration
- [ ] Create `scripts/cleanup_logs.sh`
- [ ] Configure max log size and retention
- [ ] Add cron job example for automated cleanup
- [ ] Document in TESTING_GUIDE.md
- [ ] Update .gitignore if needed

**Success Criteria**:
- Automatic log rotation
- Old logs archived or deleted
- Documentation updated

---

## Issue 10: Run Code Quality Checks and Cleanup

**Title**: Perform code quality audit and cleanup

**Priority**: Low  
**Estimated Time**: 2-3 hours  
**Labels**: code-quality, tooling

**Description**:
Run automated tools to identify unused imports, missing type hints, and other code quality issues.

**Tasks**:
- [ ] Install and run pylint for unused imports: `pylint --disable=all --enable=W0611,W0612 src/`
- [ ] Clean up identified unused imports
- [ ] Install mypy: `pip install mypy`
- [ ] Run mypy type checking: `mypy src/ --strict` (may need config adjustments)
- [ ] Add type hints where critical and missing
- [ ] Consider adding pre-commit hooks
- [ ] Document code quality standards in CONTRIBUTING.md

**Success Criteria**:
- Zero unused imports
- Critical functions have type hints
- Code quality tools documented

---

## Priority Order for Implementation

### Phase 1 (Do First):
1. Issue 1: Organize test scripts ✅
2. Issue 2: Consolidate YAML files ✅
3. Issue 3: Remove duplicate connection manager ✅
4. Issue 4: Add cleanup documentation ✅

### Phase 2 (Major Refactoring):
5. Issue 5: Split sql_generator.py 🔨

### Phase 3 (Secondary Refactoring):
6. Issue 7: Refactor cache manager
7. Issue 8: Refactor intent analyzers
8. Issue 6: Consolidate documentation

### Phase 4 (Polish):
9. Issue 9: Add log rotation
10. Issue 10: Code quality checks

---

## How to Create These Issues on GitHub

**Option 1: Web UI**
1. Go to https://github.com/sundar-blr76/report-smith/issues/new
2. Copy/paste each issue above
3. Assign to @agent
4. Add appropriate labels

**Option 2: GitHub CLI**
```bash
# Install GitHub CLI if not present
# sudo apt install gh

# Create issues
gh issue create --title "Move test/validation scripts" --body "See GITHUB_ISSUES_TEMPLATE.md #1" --assignee agent --label "cleanup,quick-win"
gh issue create --title "Consolidate test YAML files" --body "See GITHUB_ISSUES_TEMPLATE.md #2" --assignee agent --label "cleanup,quick-win"
# ... repeat for all issues
```

**Option 3: Python Script**
A script using PyGithub could automate this - let me know if you want me to create it.

---

**Reference**: See `CLEANUP_ANALYSIS.md` for detailed technical analysis.
