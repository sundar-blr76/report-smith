# Regression Testing Framework

## Overview
This framework provides automated regression testing for ReportSmith to prevent the "fix one, break another" cycle.

## Quick Start

### 1. Install Dependencies
```bash
pip install colorama sqlparse pyyaml
```

### 2. Record Golden Snapshots
```bash
# Make sure the API is running
cd tests/regression
python run_regression.py --record
```

This will execute all test cases and save their outputs as "golden" snapshots.

### 3. Run Regression Tests
```bash
python run_regression.py
```

This compares current behavior against golden snapshots and reports any differences.

## Usage

### Record Mode
Record golden snapshots after verifying changes are correct:
```bash
# Record all tests
python run_regression.py --record

# Record specific category
python run_regression.py --record --category temporal_aggregation
```

### Test Mode
Run regression tests to detect changes:
```bash
# Run all tests
python run_regression.py

# Run specific category
python run_regression.py --category comparison

# Verbose output with detailed diffs
python run_regression.py --verbose
```

### Exit Codes
- `0`: All tests passed
- `1`: One or more tests failed

## Test Cases

Test cases are defined in `test_cases/*.yaml`:

```yaml
id: equity_fees_by_month
description: "Monthly fees for equity funds"
category: temporal_aggregation
question: "For equity products, show total fees by month..."
tags:
  - temporal
  - aggregation
expectations:
  intent_type: aggregation
  should_use_date_trunc: true
  required_columns:
    - month
    - fees
```

## Golden Snapshots

Golden snapshots are stored in `golden/*.json` and contain:
- Intent analysis results
- Generated SQL
- Execution results (columns, row count, sample data)
- LLM call metadata
- Timings

## Comparison Logic

The framework uses smart comparison:
- **SQL**: Normalized comparison (whitespace, formatting independent)
- **Entities**: Set-based comparison (order independent)
- **Columns**: Exact match with order checking
- **Row Count**: 10% tolerance by default
- **Dates**: Allows shifting for relative dates ("last 12 months")

## Workflow

### When Making Changes

1. **Before changes**: Run tests to ensure baseline passes
   ```bash
   python run_regression.py
   ```

2. **After changes**: Run tests to see what broke
   ```bash
   python run_regression.py --verbose
   ```

3. **If intentional**: Update golden snapshots
   ```bash
   python run_regression.py --record
   ```

4. **If bug**: Fix code and re-run tests

### Adding New Test Cases

1. Create YAML file in `test_cases/`
2. Run in record mode to create golden snapshot
3. Verify golden snapshot is correct
4. Commit both files

## Categories

- `temporal_aggregation`: Queries with DATE_TRUNC, monthly/quarterly grouping
- `ranking`: TOP N queries
- `comparison`: Compare across dimensions
- `simple_aggregation`: Basic SUM/AVG queries
- `simple_filter`: Basic WHERE clause queries

## Files

```
tests/regression/
├── test_case.py          # Data structures
├── comparator.py         # Comparison logic
├── run_regression.py     # Main test runner
├── test_cases/           # Test case definitions (YAML)
├── golden/               # Golden snapshots (JSON)
└── reports/              # Test reports (future)
```

## Tips

- Run tests before committing changes
- Update golden snapshots only after manual verification
- Use categories to run subset of tests during development
- Check diffs carefully when tests fail
- Add new test cases when bugs are found

## Future Enhancements

- HTML diff reports
- LLM call mocking for faster tests
- Performance regression detection
- CI/CD integration
