#!/usr/bin/env python3
"""
Temporal Predicate Validation Script

Tests that temporal predicates use the correct date column based on query intent:
- "fees PAID in Q1" should use payment_date
- "fees FOR Q1" should use fee_period_start/fee_period_end
- Temporal predicates should use BETWEEN for date ranges
"""

import requests
import json
import sys
import re

API_URL = "http://localhost:8000/query"

test_cases = [
    {
        "id": "TP001",
        "query": "List the top 5 clients by total fees paid in Q1 2025",
        "expected_date_column": "payment_date",
        "expected_predicate_type": "BETWEEN",
        "expected_dates": ["2025-01-01", "2025-03-31"],
        "description": "PAID keyword should use payment_date with BETWEEN"
    },
    {
        "id": "TP002",
        "query": "Show fees collected in January 2025",
        "expected_date_column": "payment_date",
        "expected_predicate_type": "BETWEEN",
        "expected_dates": ["2025-01-01", "2025-01-31"],
        "description": "COLLECTED keyword should use payment_date"
    },
    {
        "id": "TP003",
        "query": "List fees for the period Q1 2025",
        "expected_date_column": "fee_period",
        "expected_predicate_type": "BETWEEN",
        "expected_dates": ["2025-01-01", "2025-03-31"],
        "description": "PERIOD keyword should use fee_period_start/end"
    },
    {
        "id": "TP004",
        "query": "Total fees paid on bond funds in Q1 2025",
        "expected_date_column": "payment_date",
        "expected_predicate_type": "BETWEEN",
        "expected_dates": ["2025-01-01", "2025-03-31"],
        "description": "PAID with fund filter should use payment_date"
    },
    {
        "id": "TP005",
        "query": "Transactions in Q2 2024",
        "expected_date_column": "transaction_date",
        "expected_predicate_type": "BETWEEN",
        "expected_dates": ["2024-04-01", "2024-06-30"],
        "description": "Transactions should use transaction_date with Q2 dates"
    },
    {
        "id": "TP006",
        "query": "Fees received in September 2024",
        "expected_date_column": "payment_date",
        "expected_predicate_type": "BETWEEN",
        "expected_dates": ["2024-09-01", "2024-09-30"],
        "description": "RECEIVED with month should use payment_date"
    }
]

def validate_temporal_predicate(sql: str, test_case: dict) -> tuple[bool, str]:
    """Validate temporal predicate in SQL."""
    sql_upper = sql.upper()
    
    # Check for expected date column
    expected_col = test_case['expected_date_column'].upper()
    if expected_col not in sql_upper:
        # Handle variations like fee_period_start vs just fee_period
        if "FEE_PERIOD" in expected_col:
            if "FEE_PERIOD_START" not in sql_upper and "FEE_PERIOD_END" not in sql_upper:
                return False, f"Expected date column '{expected_col}_START' or '{expected_col}_END' not found in SQL"
        else:
            return False, f"Expected date column '{expected_col}' not found in SQL"
    
    # Check for BETWEEN predicate
    if test_case['expected_predicate_type'] == "BETWEEN":
        if "BETWEEN" not in sql_upper:
            return False, "Expected BETWEEN predicate but found EXTRACT or other format"
        
        # Check if expected dates are in SQL
        expected_dates = test_case.get('expected_dates', [])
        for date in expected_dates:
            if date not in sql:
                return False, f"Expected date '{date}' not found in SQL BETWEEN clause"
    
    return True, "✓ Temporal predicate correct"

def check_wrong_date_column(sql: str, test_case: dict) -> tuple[bool, str]:
    """Check if wrong date column is being used."""
    sql_upper = sql.upper()
    expected_col = test_case['expected_date_column'].upper()
    
    # Check for common wrong patterns
    wrong_patterns = []
    
    if "PAID" in test_case['query'].upper() or "COLLECTED" in test_case['query'].upper() or "RECEIVED" in test_case['query'].upper():
        # Should use payment_date, not fee_period
        if "FEE_PERIOD_START" in sql_upper and "PAYMENT_DATE" not in sql_upper:
            wrong_patterns.append("Using fee_period_start instead of payment_date for PAID/COLLECTED/RECEIVED")
    
    if "PERIOD" in test_case['query'].upper() and "PAID" not in test_case['query'].upper():
        # Should use fee_period, not payment_date
        if "PAYMENT_DATE" in sql_upper and "FEE_PERIOD" not in sql_upper:
            wrong_patterns.append("Using payment_date instead of fee_period for period-based query")
    
    if wrong_patterns:
        return False, "; ".join(wrong_patterns)
    
    return True, ""

def run_test(test_case: dict) -> dict:
    """Run a single test case."""
    print(f"\n{'='*80}")
    print(f"Test {test_case['id']}: {test_case['description']}")
    print(f"Query: {test_case['query']}")
    print(f"Expected: {test_case['expected_date_column']} with {test_case['expected_predicate_type']}")
    print(f"{'='*80}")
    
    try:
        response = requests.post(
            API_URL,
            json={"question": test_case['query']},
            timeout=60
        )
        
        if response.status_code != 200:
            return {
                "id": test_case['id'],
                "status": "FAIL",
                "error": f"API error: {response.status_code}",
                "sql": None
            }
        
        result = response.json()
        sql = result.get('sql', '')
        intent = result.get('intent', {})
        filters = intent.get('filters', [])
        
        print(f"\nIntent Filters:")
        for f in filters:
            print(f"  - {f}")
        
        print(f"\nGenerated SQL:\n{sql}\n")
        
        # Validate temporal predicate
        is_valid, message = validate_temporal_predicate(sql, test_case)
        
        # Check for wrong date column usage
        no_wrong_col, wrong_msg = check_wrong_date_column(sql, test_case)
        
        if is_valid and no_wrong_col:
            print(f"✓ PASS: {message}")
            return {
                "id": test_case['id'],
                "status": "PASS",
                "message": message,
                "sql": sql,
                "filters": filters
            }
        else:
            error_msg = message if not is_valid else wrong_msg
            print(f"✗ FAIL: {error_msg}")
            return {
                "id": test_case['id'],
                "status": "FAIL",
                "error": error_msg,
                "sql": sql,
                "filters": filters
            }
    
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
        return {
            "id": test_case['id'],
            "status": "ERROR",
            "error": str(e),
            "sql": None
        }

def main():
    print("="*80)
    print("Temporal Predicate Validation")
    print("="*80)
    
    results = []
    for test_case in test_cases:
        result = run_test(test_case)
        results.append(result)
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    
    passed = sum(1 for r in results if r['status'] == 'PASS')
    failed = sum(1 for r in results if r['status'] == 'FAIL')
    errors = sum(1 for r in results if r['status'] == 'ERROR')
    
    print(f"Total: {len(results)}")
    print(f"✓ Passed: {passed}")
    print(f"✗ Failed: {failed}")
    print(f"⚠ Errors: {errors}")
    
    if failed > 0 or errors > 0:
        print("\nFailed/Error Tests:")
        for r in results:
            if r['status'] in ['FAIL', 'ERROR']:
                print(f"  - {r['id']}: {r.get('error', 'Unknown error')}")
    
    # Write detailed results to file
    with open('temporal_validation_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results written to temporal_validation_results.json")
    
    # Exit code based on results
    sys.exit(0 if (failed == 0 and errors == 0) else 1)

if __name__ == "__main__":
    main()
