# ReportSmith Test Query Suite

## Overview

This directory contains a comprehensive suite of 30 test queries designed to validate ReportSmith's capabilities across varying complexity levels. These queries test real-world use cases from the fund accounting domain and can be converted to regression tests.

## Files

- **`test_queries.yaml`** - Complete test query definitions with expected outcomes
- **`validate_test_queries.py`** - Validation script to execute and verify queries
- **`TEST_QUERIES_README.md`** - This file

## Test Query Categories

### 1. Basic Retrieval (Q001-Q005)
Simple queries testing basic table access and filtering:
- List active funds
- Filter by domain values (equity, bond, individual)
- Multiple filter conditions
- Basic joins

### 2. Aggregation (Q006-Q010)
Queries testing aggregation functions:
- SUM, COUNT, AVG
- GROUP BY clauses
- Temporal filtering with aggregation
- Currency auto-inclusion for monetary values

### 3. Ranking/Top-N (Q011-Q015)
Queries testing ranking and ordering:
- Top N by metric
- Temporal predicates with ranking
- Multi-table joins with ranking

**Key Test:** Q012 validates recent fixes:
- Temporal column selection (payment_date vs fee_period_start)
- BETWEEN for date ranges
- Currency auto-inclusion

### 4. Temporal Queries (Q016-Q020)
Queries testing date/time handling:
- Quarter predicates (Q1, Q2, etc.)
- Month predicates
- Year-to-date
- Trend analysis
- Correct temporal column selection

### 5. Multi-Table Joins (Q021-Q025)
Queries testing complex join scenarios:
- Multi-hop joins (clients -> accounts -> holdings -> funds)
- Many-to-many relationships
- Aggregation across joins

### 6. Advanced/Complex (Q026-Q030)
Challenging queries testing advanced features:
- Calculated columns
- Window functions
- Subqueries
- CASE WHEN expressions
- HAVING clauses

## Complexity Distribution

- **Simple:** 5 queries (17%)
- **Medium:** 13 queries (43%)
- **Hard:** 10 queries (33%)
- **Very Hard:** 2 queries (7%)

## Feature Coverage

The test suite validates:

✅ **Recent Fixes:**
- Temporal predicate resolution (BETWEEN format)
- Correct column selection (payment_date vs fee_period_start)
- Currency auto-inclusion for monetary queries
- Token comparison in local mapping

✅ **Core Features:**
- Entity recognition (tables, columns, domain values)
- Multi-table joins
- Aggregations (SUM, COUNT, AVG)
- Filtering and WHERE clauses
- GROUP BY and ORDER BY
- Temporal filters (quarters, months, date ranges)

🔄 **Partial Support (marked in queries):**
- Window functions (Q013, Q029)
- Subqueries (Q027)
- Complex CASE WHEN (Q028)
- HAVING clauses (Q030)

## Usage

### Run All Tests

```bash
python validate_test_queries.py
```

### Run Specific Query

```bash
python validate_test_queries.py --query-id Q012
```

### Run by Category

```bash
python validate_test_queries.py --category temporal
```

### Run by Complexity

```bash
python validate_test_queries.py --complexity simple
```

### Generate Report

```bash
python validate_test_queries.py --output test_report.txt
```

## Validation Criteria

Each query is validated against:

1. **API Execution:** Query executes without error
2. **SQL Generation:** Valid SQL is produced
3. **Intent Recognition:** Correct intent type identified
4. **Entity Recognition:** Expected entities found
5. **Currency Auto-Inclusion:** Currency added for monetary queries
6. **Temporal BETWEEN:** Date ranges use BETWEEN
7. **Temporal Column:** Correct column for temporal context
8. **SQL Execution:** SQL runs successfully in database

## Expected Results

Based on current ReportSmith capabilities:

- **Q001-Q015:** Should fully pass (basic retrieval, aggregation, ranking)
- **Q016-Q020:** Should fully pass (temporal queries with recent fixes)
- **Q021-Q025:** Should mostly pass (join capabilities)
- **Q026-Q030:** Partial pass (advanced features still in development)

## Converting to Regression Tests

Once validated, these queries can be converted to pytest tests:

```python
# Example regression test
def test_q012_top_clients_with_temporal_and_currency():
    """Test Q012: Top 5 clients by fees paid in Q1 2025"""
    response = client.post("/query", json={
        "question": "List the top 5 clients by total fees paid on bond funds in Q1 2025",
        "app_id": "fund_accounting"
    })
    
    assert response.status_code == 200
    result = response.json()
    
    # Verify SQL contains currency
    assert "currency" in result["sql"]["sql"].lower()
    
    # Verify BETWEEN is used
    assert "BETWEEN" in result["sql"]["sql"]
    
    # Verify payment_date is used (not fee_period_start)
    assert "payment_date" in result["sql"]["sql"].lower()
```

## Data Requirements

The test suite assumes the fund_accounting database contains:

- **Funds:** ~50+ funds across 10 fund types
- **Clients:** 500+ clients (Individual, Corporate, Institutional)
- **Transactions:** Data from 2021-2025
- **Fee Transactions:** Data with payment_date and currency
- **Holdings:** Current and historical holdings
- **Performance Reports:** Performance metrics

## Maintenance

Update test_queries.yaml when:
- New features are added
- Edge cases are discovered
- Data model changes
- Business requirements evolve

## Notes

### Query Design Principles

1. **Real-world scenarios** - Queries reflect actual business needs
2. **Progressive complexity** - Build from simple to advanced
3. **Feature coverage** - Test all major capabilities
4. **Regression safety** - Validate recent fixes don't break

### Known Limitations

Queries marked with these flags may not fully work:
- `window_function: true` - Window functions partial support
- `subquery: true` - Subqueries in development
- `case_when: true` - Complex CASE expressions
- `having_clause: true` - HAVING filter support

These can guide future development priorities.

## Example Outputs

### Successful Query (Q012)

```
✓ Q012 PASSED (2.34s)
Generated SQL:
SELECT SUM(fee_transactions.fee_amount) AS fees,
       fee_transactions.currency AS currency,
       clients.client_name
FROM clients
INNER JOIN accounts ON clients.id = accounts.client_id
INNER JOIN fee_transactions ON accounts.id = fee_transactions.account_id
INNER JOIN funds ON fee_transactions.fund_id = funds.id
WHERE fee_transactions.payment_date BETWEEN '2025-01-01' AND '2025-03-31'
  AND funds.fund_type = 'Bond'
  AND funds.is_active = true
GROUP BY fee_transactions.currency, clients.client_name
ORDER BY fees DESC
LIMIT 5
```

### Validation Checks

```
Checks:
  ✓ intent_type (ranking)
  ✓ currency_auto_included
  ✓ temporal_between
  ✓ correct_temporal_column
  ✓ sql_execution (5 rows returned)
```

## Contributing

When adding new test queries:

1. Follow the YAML structure in test_queries.yaml
2. Assign sequential ID (Q031, Q032, etc.)
3. Include expected entities, filters, and outcomes
4. Add notes explaining what the query tests
5. Update complexity and category distributions
6. Run validation to ensure query works

## Future Enhancements

- [ ] Add expected row count validation
- [ ] Add column name validation
- [ ] Add performance benchmarks
- [ ] Integration with CI/CD pipeline
- [ ] Automated regression test generation
- [ ] Query execution result caching
- [ ] Diff comparison for SQL changes

---

**Last Updated:** 2025-11-06  
**Total Queries:** 30  
**Coverage:** Basic to Advanced  
**Status:** Ready for validation
