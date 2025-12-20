#!/usr/bin/env python3
"""
Analyze all sample queries for incoherence.

Executes all UI sample queries and checks for issues like:
- Missing expected columns
- Wrong temporal aggregations (EXTRACT vs DATE_TRUNC)
- Missing filters
- Incorrect intent detection
"""

import requests
import json
import time
from typing import List, Dict, Any

API_BASE = "http://127.0.0.1:8000"

# All sample queries from UI
SAMPLE_QUERIES = [
    "For equity products, show total fees by month for the last 12 months, only for funds managed by top-rated managers (performance_rating >= 4)",
    "List the top 5 clients by total fees paid on bond funds in Q1 2025",
    "Compare average AUM and total fees between equity and bond funds over 2024; return results by quarter",
    "Show daily transactions and fees for account 12345 between 2025-01-01 and 2025-01-31 (join through subscriptions if needed)",
    "Find funds with AUM over 100M but total fees under 1M in 2024; include fund manager names",
    "Show AUM for all equity funds",
    "List fees for TruePotential clients",
    "What's the total balance for institutional investors?",
    "I need the managed assets for stock portfolios",
    "Show me charges for TP customers",
    "Compare AUM between conservative and aggressive funds",
    "What are the average fees by fund type for all our retail investors?",
]

def execute_query(question: str) -> Dict[str, Any]:
    """Execute query via API."""
    try:
        response = requests.post(
            f"{API_BASE}/query",
            json={"question": question},
            timeout=120
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def analyze_query(idx: int, question: str, response: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze a query response for incoherence."""
    issues = []
    
    if "error" in response:
        return {
            "query_num": idx + 1,
            "question": question,
            "status": "ERROR",
            "error": response["error"],
            "issues": []
        }
    
    result = response.get("data", {}).get("result", {})
    intent = result.get("intent", {})
    sql_data = result.get("sql", {})
    execution = result.get("execution", {})
    
    sql = sql_data.get("sql", "")
    columns = execution.get("columns", [])
    row_count = execution.get("row_count", 0)
    
    # Check for common issues
    
    # 1. Temporal queries using EXTRACT instead of DATE_TRUNC
    if any(word in question.lower() for word in ["by month", "by quarter", "by year", "monthly", "quarterly"]):
        if "EXTRACT" in sql and "DATE_TRUNC" not in sql:
            issues.append({
                "type": "TEMPORAL_AGGREGATION",
                "severity": "HIGH",
                "description": f"Query asks for '{[w for w in ['by month', 'by quarter', 'by year'] if w in question.lower()][0]}' but SQL uses EXTRACT instead of DATE_TRUNC",
                "expected": "DATE_TRUNC('month/quarter/year', column)",
                "actual": "EXTRACT(MONTH/YEAR FROM column)"
            })
    
    # 2. Missing time filters
    if any(word in question.lower() for word in ["2024", "2025", "q1", "q2", "q3", "q4", "last", "between"]):
        has_date_filter = any(word in sql.upper() for word in ["WHERE", "BETWEEN", ">=", "<=", ">", "<"]) and \
                         any(word in sql for word in ["2024", "2025", "INTERVAL", "CURRENT_DATE", "BETWEEN"])
        if not has_date_filter and "between" in question.lower():
            issues.append({
                "type": "MISSING_TIME_FILTER",
                "severity": "HIGH",
                "description": "Query specifies time period but SQL may be missing proper date filter",
                "expected": "WHERE date_column BETWEEN ... or >= ...",
                "actual": "No clear date filter found"
            })
    
    # 3. Comparison queries missing comparison dimension
    if "compare" in question.lower():
        # Extract what's being compared
        if "between" in question.lower():
            # Should have the comparison dimension in GROUP BY
            if "GROUP BY" in sql:
                # Check if we have multiple groups (for comparison)
                group_by_clause = sql.split("GROUP BY")[1].split("ORDER BY")[0] if "ORDER BY" in sql else sql.split("GROUP BY")[1]
                num_groups = len([x for x in group_by_clause.split(",") if x.strip()])
                if num_groups < 2:
                    issues.append({
                        "type": "MISSING_COMPARISON_DIMENSION",
                        "severity": "MEDIUM",
                        "description": "Comparison query should group by comparison dimension",
                        "expected": "GROUP BY comparison_field, time_period",
                        "actual": f"Only {num_groups} GROUP BY field(s)"
                    })
    
    # 4. Top N queries
    if any(word in question.lower() for word in ["top", "bottom", "first", "last"]) and any(char.isdigit() for char in question):
        if "LIMIT" not in sql.upper():
            issues.append({
                "type": "MISSING_LIMIT",
                "severity": "MEDIUM",
                "description": "Query asks for 'top N' but SQL has no LIMIT clause",
                "expected": "LIMIT N",
                "actual": "No LIMIT found"
            })
    
    # 5. Check for empty results
    if row_count == 0 and not any(word in question.lower() for word in ["if", "whether", "check"]):
        issues.append({
            "type": "EMPTY_RESULTS",
            "severity": "LOW",
            "description": "Query returned 0 rows - may indicate wrong filters or missing data",
            "expected": "> 0 rows",
            "actual": "0 rows"
        })
    
    # 6. Column name issues
    if "month" in question.lower() and "month" in [c.lower() for c in columns]:
        # Check if month column is just a number
        sample_rows = execution.get("rows", [])
        if sample_rows and "month" in sample_rows[0]:
            month_val = str(sample_rows[0]["month"])
            if month_val.isdigit() and len(month_val) <= 2:
                issues.append({
                    "type": "WRONG_DATE_FORMAT",
                    "severity": "HIGH",
                    "description": "Month column contains just month number instead of full date",
                    "expected": "YYYY-MM or YYYY-MM-DD format",
                    "actual": f"Month number: {month_val}"
                })
    
    return {
        "query_num": idx + 1,
        "question": question,
        "status": "SUCCESS",
        "intent_type": intent.get("type"),
        "sql": sql,
        "columns": columns,
        "row_count": row_count,
        "issues": issues
    }

def main():
    """Main analysis function."""
    print("=" * 100)
    print("SAMPLE QUERY INCOHERENCE ANALYSIS")
    print("=" * 100)
    print(f"\nAnalyzing {len(SAMPLE_QUERIES)} sample queries...\n")
    
    results = []
    
    for idx, question in enumerate(SAMPLE_QUERIES):
        print(f"\n[{idx + 1}/{len(SAMPLE_QUERIES)}] Executing: {question[:80]}...")
        
        response = execute_query(question)
        analysis = analyze_query(idx, question, response)
        results.append(analysis)
        
        if analysis["status"] == "ERROR":
            print(f"  ❌ ERROR: {analysis['error']}")
        elif analysis["issues"]:
            print(f"  ⚠️  {len(analysis['issues'])} issue(s) found")
            for issue in analysis["issues"]:
                print(f"     - [{issue['severity']}] {issue['type']}: {issue['description']}")
        else:
            print(f"  ✅ No issues detected")
        
        time.sleep(0.5)  # Small delay
    
    # Summary
    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)
    
    total_queries = len(results)
    errors = len([r for r in results if r["status"] == "ERROR"])
    with_issues = len([r for r in results if r["issues"]])
    clean = total_queries - errors - with_issues
    
    print(f"\nTotal Queries: {total_queries}")
    print(f"  ✅ Clean: {clean}")
    print(f"  ⚠️  With Issues: {with_issues}")
    print(f"  ❌ Errors: {errors}")
    
    # Issue breakdown
    all_issues = []
    for r in results:
        all_issues.extend(r.get("issues", []))
    
    if all_issues:
        print(f"\nIssue Breakdown:")
        issue_types = {}
        for issue in all_issues:
            issue_type = issue["type"]
            severity = issue["severity"]
            key = f"{issue_type} ({severity})"
            issue_types[key] = issue_types.get(key, 0) + 1
        
        for issue_type, count in sorted(issue_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {issue_type}: {count}")
    
    # Detailed report
    print("\n" + "=" * 100)
    print("DETAILED ISSUES")
    print("=" * 100)
    
    for result in results:
        if result["issues"]:
            print(f"\n[Query {result['query_num']}] {result['question'][:80]}...")
            print(f"  Intent: {result.get('intent_type', 'N/A')}")
            print(f"  Columns: {', '.join(result.get('columns', []))}")
            print(f"  Row Count: {result.get('row_count', 0)}")
            print(f"\n  Issues:")
            for issue in result["issues"]:
                print(f"    [{issue['severity']}] {issue['type']}")
                print(f"      Description: {issue['description']}")
                print(f"      Expected: {issue['expected']}")
                print(f"      Actual: {issue['actual']}")
    
    # Save to file
    with open("/tmp/query_analysis.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n\nFull results saved to: /tmp/query_analysis.json")
    print("=" * 100)

if __name__ == "__main__":
    main()
