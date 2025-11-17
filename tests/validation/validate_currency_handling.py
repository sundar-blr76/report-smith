#!/usr/bin/env python3
"""
Currency Handling Validation Script

Tests that currency columns are automatically included when querying monetary amounts.
"""

import requests
import json
import sys

API_URL = "http://localhost:8000/query"

test_cases = [
    {
        "id": "TC001",
        "query": "List fees for TruePotential clients",
        "expected_columns": ["fee_amount", "currency"],
        "description": "Basic fee query should include currency"
    },
    {
        "id": "TC002",
        "query": "Total fees by client type",
        "expected_columns": ["fee_amount", "currency", "client_type"],
        "description": "Aggregated fees should include currency in GROUP BY"
    },
    {
        "id": "TC003",
        "query": "List the top 5 clients by total fees paid on bond funds in Q1 2025",
        "expected_columns": ["fee_amount", "currency"],
        "description": "Complex fee query with temporal + filter should include currency"
    },
    {
        "id": "TC004",
        "query": "Show transaction amounts for equity funds",
        "expected_columns": ["gross_amount", "currency"],
        "description": "Transaction amounts should include currency"
    },
    {
        "id": "TC005",
        "query": "Average fund NAV by fund type",
        "expected_columns": ["nav_per_share", "base_currency"],
        "description": "NAV queries should include base_currency from funds table"
    }
]

def validate_currency_in_sql(sql: str, expected_columns: list) -> tuple[bool, str]:
    """Check if SQL includes expected currency columns."""
    sql_upper = sql.upper()
    
    # Check for currency column in SELECT
    has_currency = any(col.upper() in sql_upper for col in expected_columns if 'currency' in col.lower())
    
    if not has_currency:
        return False, f"Currency column not found in SQL. Expected one of: {[c for c in expected_columns if 'currency' in c.lower()]}"
    
    # If there's a GROUP BY, currency should be in it
    if "GROUP BY" in sql_upper:
        group_by_start = sql_upper.find("GROUP BY")
        group_by_section = sql_upper[group_by_start:group_by_start+200]
        
        currency_in_group_by = any(col.upper() in group_by_section for col in expected_columns if 'currency' in col.lower())
        if not currency_in_group_by:
            return False, "Currency column found in SELECT but not in GROUP BY (will cause SQL error)"
    
    return True, "✓ Currency handling correct"

def run_test(test_case: dict) -> dict:
    """Run a single test case."""
    print(f"\n{'='*80}")
    print(f"Test {test_case['id']}: {test_case['description']}")
    print(f"Query: {test_case['query']}")
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
        
        print(f"\nGenerated SQL:\n{sql}\n")
        
        # Validate currency handling
        is_valid, message = validate_currency_in_sql(sql, test_case['expected_columns'])
        
        if is_valid:
            print(f"✓ PASS: {message}")
            return {
                "id": test_case['id'],
                "status": "PASS",
                "message": message,
                "sql": sql
            }
        else:
            print(f"✗ FAIL: {message}")
            return {
                "id": test_case['id'],
                "status": "FAIL",
                "error": message,
                "sql": sql
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
    print("Currency Handling Validation")
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
    with open('currency_validation_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results written to currency_validation_results.json")
    
    # Exit code based on results
    sys.exit(0 if (failed == 0 and errors == 0) else 1)

if __name__ == "__main__":
    main()
