#!/usr/bin/env python3
"""
Script to automatically create GitHub issues for cleanup and refactoring tasks.

Usage:
    python create_github_issues.py [--dry-run] [--token YOUR_GITHUB_TOKEN]

If no token provided, will attempt to use gh CLI authentication.
"""

import argparse
import os
import sys
from typing import List, Dict

try:
    from github import Github, GithubException
except ImportError:
    print("Error: PyGithub not installed. Install with: pip install PyGithub")
    sys.exit(1)


REPO_OWNER = "sundar-blr76"
REPO_NAME = "report-smith"
DEFAULT_ASSIGNEE = "agent"

ISSUES = [
    {
        "title": "Move test/validation scripts from root to tests/validation/",
        "body": """**Priority**: High
**Estimated Time**: 30 minutes
**Phase**: 1 - Quick Wins

## Description
Currently, we have 8 test and validation scripts cluttering the root directory. These should be organized into a proper test structure.

## Current State
- 8 scripts in root: `test_cache_payload_display.py`, `test_cache_performance.py`, `test_json_viewer.py`, `test_sql_gen_error_fix.py`, `validate_currency_handling.py`, `validate_fixes.py`, `validate_temporal_predicates.py`, `validate_test_queries.py`

## Tasks
- [ ] Create `tests/validation/` directory
- [ ] Move all `test_*.py` scripts from root to `tests/validation/`
- [ ] Move all `validate_*.py` scripts from root to `tests/validation/`
- [ ] Update `run_all_validations.py` to reference new paths
- [ ] Test that all validation scripts still work
- [ ] Update documentation references

## Success Criteria
- Root directory has max 1 test runner script (`run_all_validations.py`)
- All validation scripts work from new location
- Documentation updated

**Reference**: See `CLEANUP_ANALYSIS.md` and `GITHUB_ISSUES_TEMPLATE.md` for details.
""",
        "labels": ["cleanup", "quick-win", "phase-1"],
        "assignee": DEFAULT_ASSIGNEE,
        "milestone": None
    },
    {
        "title": "Review and consolidate duplicate test query YAML files",
        "body": """**Priority**: High
**Estimated Time**: 1 hour
**Phase**: 1 - Quick Wins

## Description
We have 3 similar test query files (42K total) with unclear purposes and potential duplication.

## Current State
- `test_queries.yaml` (15K)
- `test_queries_comprehensive.yaml` (13K)
- `test_queries_comprehensive_new.yaml` (14K)

## Tasks
- [ ] Review content of all 3 YAML files
- [ ] Identify overlaps and differences
- [ ] Determine canonical version or merge into single file
- [ ] Archive or delete redundant versions
- [ ] Add header comment indicating canonical status and purpose
- [ ] Update scripts/docs that reference old files

## Success Criteria
- Single authoritative test queries file
- Clear documentation of test query structure
- No broken references

**Reference**: See `CLEANUP_ANALYSIS.md` and `GITHUB_ISSUES_TEMPLATE.md` for details.
""",
        "labels": ["cleanup", "quick-win", "phase-1"],
        "assignee": DEFAULT_ASSIGNEE,
        "milestone": None
    },
    {
        "title": "Identify and remove duplicate connection manager implementation",
        "body": """**Priority**: High
**Estimated Time**: 1-2 hours
**Phase**: 1 - Quick Wins

## Description
Two similar connection manager implementations exist, creating confusion about which is active.

## Current State
- `database/connection_manager.py` (246 lines)
- `database/simple_connection_manager.py` (230 lines)

## Tasks
- [ ] Identify which connection manager is actively used
- [ ] Check all imports across codebase
- [ ] Document differences and decision rationale
- [ ] Remove or deprecate unused version
- [ ] Add migration guide if needed (in code comments)
- [ ] Run full test suite to verify

## Success Criteria
- Single connection manager implementation
- All imports updated correctly
- All tests passing
- Documentation updated

**Reference**: See `CLEANUP_ANALYSIS.md` and `GITHUB_ISSUES_TEMPLATE.md` for details.
""",
        "labels": ["refactoring", "technical-debt", "phase-1"],
        "assignee": DEFAULT_ASSIGNEE,
        "milestone": None
    },
    {
        "title": "Document and automate cleanup of generated files",
        "body": """**Priority**: Medium
**Estimated Time**: 1 hour
**Phase**: 1 - Quick Wins

## Description
Generated files (coverage reports, cache, logs) accumulate but lack documented cleanup process.

## Current State
- `htmlcov/` (3.4M), `.coverage` (52K), `.pytest_cache/` (32K), `logs/scratch.json` (276K)

## Tasks
- [ ] Create `scripts/cleanup.sh` with cleanup commands
- [ ] Add Makefile targets: `make clean`, `make clean-logs`, `make clean-coverage`
- [ ] Document cleanup process in CONTRIBUTING.md
- [ ] Verify all generated files are in `.gitignore`
- [ ] Add optional cleanup to CI/CD if applicable

## Example Script
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

## Success Criteria
- Cleanup script created and tested
- Documentation updated
- Easy cleanup for developers

**Reference**: See `CLEANUP_ANALYSIS.md` and `GITHUB_ISSUES_TEMPLATE.md` for details.
""",
        "labels": ["documentation", "tooling", "phase-1"],
        "assignee": DEFAULT_ASSIGNEE,
        "milestone": None
    },
    {
        "title": "Refactor sql_generator.py into modular components",
        "body": """**Priority**: High
**Estimated Time**: 6-8 hours
**Phase**: 2 - Major Refactoring

## Description
`sql_generator.py` is 2,383 lines - too large for easy maintenance and testing.

## Current State
- Single monolithic file with multiple responsibilities
- Difficult to navigate and test individual components

## Proposed Structure
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

## Tasks
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

## Success Criteria
- No single file >800 lines
- All tests passing
- No breaking changes to external API
- Improved testability

**Reference**: See `CLEANUP_ANALYSIS.md` and `GITHUB_ISSUES_TEMPLATE.md` for details.
""",
        "labels": ["refactoring", "technical-debt", "breaking-down-large-files", "phase-2"],
        "assignee": DEFAULT_ASSIGNEE,
        "milestone": None
    },
    {
        "title": "Split cache_manager.py into specialized cache components",
        "body": """**Priority**: Medium
**Estimated Time**: 4-5 hours
**Phase**: 3 - Secondary Refactoring

## Description
`cache_manager.py` (562 lines) handles multiple cache types and strategies in single file.

## Proposed Structure
```
utils/caching/
  ├── __init__.py
  ├── base_cache.py            # Abstract base class
  ├── sql_cache.py             # SQL query caching
  ├── embedding_cache.py       # Vector embedding caching
  ├── llm_cache.py             # LLM response caching
  └── cache_strategies.py      # TTL, LRU, etc.
```

## Tasks
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

## Success Criteria
- Clear separation of concerns
- Each cache type independently testable
- All tests passing

**Reference**: See `CLEANUP_ANALYSIS.md` and `GITHUB_ISSUES_TEMPLATE.md` for details.
""",
        "labels": ["refactoring", "technical-debt", "phase-3"],
        "assignee": DEFAULT_ASSIGNEE,
        "milestone": None
    },
    {
        "title": "Create base class and reduce duplication in intent analyzers",
        "body": """**Priority**: Medium
**Estimated Time**: 3-4 hours
**Phase**: 3 - Secondary Refactoring

## Description
Three intent analyzers with overlapping functionality and no clear hierarchy.

## Current State
- `intent_analyzer.py` (387 lines)
- `llm_intent_analyzer.py` (1,096 lines)
- `hybrid_intent_analyzer.py` (777 lines)

## Tasks
- [ ] Analyze common patterns and utilities
- [ ] Create abstract base class `BaseIntentAnalyzer`
- [ ] Extract shared logic (entity extraction, filtering, etc.)
- [ ] Refactor each analyzer to extend base class
- [ ] Consider strategy pattern for different analysis approaches
- [ ] Update tests
- [ ] Document analyzer selection criteria

## Success Criteria
- Clear inheritance hierarchy
- Reduced code duplication (target: 20% reduction)
- Easier to add new analyzer types
- All tests passing

**Reference**: See `CLEANUP_ANALYSIS.md` and `GITHUB_ISSUES_TEMPLATE.md` for details.
""",
        "labels": ["refactoring", "technical-debt", "phase-3"],
        "assignee": DEFAULT_ASSIGNEE,
        "milestone": None
    },
    {
        "title": "Merge and consolidate documentation files in root",
        "body": """**Priority**: Medium
**Estimated Time**: 1-2 hours
**Phase**: 3 - Secondary Refactoring

## Description
8 markdown files in root directory - some with overlapping content.

## Current State
- CHANGELOG.md
- COMMIT_SUMMARY.md (tracking commits)
- IMPLEMENTATION_HISTORY.md (implementation details)
- OUTSTANDING_ISSUES.md (issue tracking)
- CONTRIBUTING.md
- README.md
- SETUP.md
- TESTING_GUIDE.md

## Tasks
- [ ] Review overlap between COMMIT_SUMMARY.md and CHANGELOG.md
- [ ] Merge commit tracking into CHANGELOG.md
- [ ] Review OUTSTANDING_ISSUES.md - consider GitHub Issues instead
- [ ] Archive IMPLEMENTATION_HISTORY.md to `docs/archive/`
- [ ] Keep only: README, SETUP, CHANGELOG, CONTRIBUTING, TESTING_GUIDE, CLEANUP_ANALYSIS
- [ ] Update cross-references

## Success Criteria
- ≤6 markdown files in root
- No content loss
- Clear purpose for each remaining doc

**Reference**: See `CLEANUP_ANALYSIS.md` and `GITHUB_ISSUES_TEMPLATE.md` for details.
""",
        "labels": ["documentation", "cleanup", "phase-3"],
        "assignee": DEFAULT_ASSIGNEE,
        "milestone": None
    },
    {
        "title": "Implement log rotation and cleanup automation",
        "body": """**Priority**: Low
**Estimated Time**: 2 hours
**Phase**: 4 - Polish

## Description
Logs accumulate without rotation or automated cleanup.

## Current State
- `logs/scratch.json` (277KB)
- Various .log files
- `logs/semantic_debug/` subdirectory

## Tasks
- [ ] Add Python logging rotation configuration
- [ ] Create `scripts/cleanup_logs.sh`
- [ ] Configure max log size and retention
- [ ] Add cron job example for automated cleanup
- [ ] Document in TESTING_GUIDE.md
- [ ] Update .gitignore if needed

## Success Criteria
- Automatic log rotation
- Old logs archived or deleted
- Documentation updated

**Reference**: See `CLEANUP_ANALYSIS.md` and `GITHUB_ISSUES_TEMPLATE.md` for details.
""",
        "labels": ["tooling", "maintenance", "phase-4"],
        "assignee": DEFAULT_ASSIGNEE,
        "milestone": None
    },
    {
        "title": "Perform code quality audit and cleanup",
        "body": """**Priority**: Low
**Estimated Time**: 2-3 hours
**Phase**: 4 - Polish

## Description
Run automated tools to identify unused imports, missing type hints, and other code quality issues.

## Tasks
- [ ] Install and run pylint for unused imports: `pylint --disable=all --enable=W0611,W0612 src/`
- [ ] Clean up identified unused imports
- [ ] Install mypy: `pip install mypy`
- [ ] Run mypy type checking: `mypy src/ --strict` (may need config adjustments)
- [ ] Add type hints where critical and missing
- [ ] Consider adding pre-commit hooks
- [ ] Document code quality standards in CONTRIBUTING.md

## Success Criteria
- Zero unused imports
- Critical functions have type hints
- Code quality tools documented

**Reference**: See `CLEANUP_ANALYSIS.md` and `GITHUB_ISSUES_TEMPLATE.md` for details.
""",
        "labels": ["code-quality", "tooling", "phase-4"],
        "assignee": DEFAULT_ASSIGNEE,
        "milestone": None
    }
]


def create_issues(token: str = None, dry_run: bool = False) -> None:
    """Create GitHub issues from the ISSUES list."""
    
    # Authenticate
    if token:
        g = Github(token)
    else:
        # Try to use gh CLI token
        try:
            import subprocess
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                check=True
            )
            token = result.stdout.strip()
            g = Github(token)
            print("✓ Using GitHub CLI authentication")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Error: No token provided and gh CLI not configured.")
            print("Please either:")
            print("  1. Provide token with --token flag")
            print("  2. Configure gh CLI with: gh auth login")
            sys.exit(1)
    
    try:
        repo = g.get_repo(f"{REPO_OWNER}/{REPO_NAME}")
        print(f"✓ Connected to repository: {REPO_OWNER}/{REPO_NAME}")
    except GithubException as e:
        print(f"Error accessing repository: {e}")
        sys.exit(1)
    
    # Create issues
    created_issues = []
    
    for idx, issue_data in enumerate(ISSUES, 1):
        print(f"\n[{idx}/{len(ISSUES)}] Processing: {issue_data['title']}")
        
        if dry_run:
            print(f"  [DRY RUN] Would create issue with labels: {issue_data['labels']}")
            continue
        
        try:
            # Get or create labels
            repo_labels = {label.name: label for label in repo.get_labels()}
            issue_labels = []
            
            for label_name in issue_data['labels']:
                if label_name not in repo_labels:
                    print(f"  Creating label: {label_name}")
                    new_label = repo.create_label(name=label_name, color="0e8a16")
                    repo_labels[label_name] = new_label
                issue_labels.append(repo_labels[label_name])
            
            # Create issue
            issue = repo.create_issue(
                title=issue_data['title'],
                body=issue_data['body'],
                labels=issue_labels,
                assignee=issue_data['assignee']
            )
            
            created_issues.append(issue)
            print(f"  ✓ Created issue #{issue.number}: {issue.html_url}")
            
        except GithubException as e:
            print(f"  ✗ Error creating issue: {e}")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Summary: Created {len(created_issues)} issues")
    if created_issues:
        print(f"\nIssues created:")
        for issue in created_issues:
            print(f"  #{issue.number}: {issue.title}")
            print(f"    {issue.html_url}")


def main():
    parser = argparse.ArgumentParser(
        description="Create GitHub issues for report-smith cleanup and refactoring"
    )
    parser.add_argument(
        "--token",
        help="GitHub personal access token (or use gh CLI auth)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without actually creating issues"
    )
    
    args = parser.parse_args()
    
    print("GitHub Issues Creator for report-smith")
    print("="*60)
    
    create_issues(token=args.token, dry_run=args.dry_run)
    
    print("\n✓ Done!")


if __name__ == "__main__":
    main()
