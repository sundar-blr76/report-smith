#!/usr/bin/env python3
"""
Test Query Validator and Executor

This script validates and executes the test queries defined in test_queries.yaml
to verify ReportSmith's capabilities and prepare for regression testing.

Usage:
    python validate_test_queries.py [--query-id Q001] [--category basic_retrieval] [--complexity simple]
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
import yaml
import requests

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QueryValidator:
    """Validates and executes test queries against ReportSmith API"""
    
    def __init__(self, api_url: str = "http://localhost:8000", app_id: str = "fund_accounting"):
        self.api_url = api_url
        self.app_id = app_id
        self.results = []
    
    def load_queries(self, file_path: str) -> Dict:
        """Load queries from YAML file"""
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        return data
    
    def execute_query(self, query: str, timeout: int = 120) -> Dict:
        """Execute a query against the API"""
        try:
            response = requests.post(
                f"{self.api_url}/query",
                json={
                    "question": query,
                    "app_id": self.app_id
                },
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return {"error": str(e)}
    
    def validate_result(self, query_def: Dict, result: Dict) -> Dict:
        """Validate query result against expected outcomes"""
        validations = {
            "query_id": query_def.get("id"),
            "query_text": query_def.get("query"),
            "passed": True,
            "checks": []
        }
        
        if "error" in result:
            validations["passed"] = False
            validations["checks"].append({
                "check": "api_execution",
                "passed": False,
                "message": f"API error: {result['error']}"
            })
            return validations
        
        # Check SQL was generated
        if "sql" not in result or not result.get("sql", {}).get("sql"):
            validations["passed"] = False
            validations["checks"].append({
                "check": "sql_generation",
                "passed": False,
                "message": "No SQL generated"
            })
            return validations
        
        sql = result["sql"]["sql"]
        intent = result.get("intent", {})
        
        # Check expected intent type
        if "expected_intent" in query_def:
            expected_intent = query_def["expected_intent"]
            actual_intent = intent.get("type", "").lower()
            passed = expected_intent.lower() in actual_intent
            validations["checks"].append({
                "check": "intent_type",
                "expected": expected_intent,
                "actual": actual_intent,
                "passed": passed
            })
            if not passed:
                validations["passed"] = False
        
        # Check currency is included for monetary queries
        if query_def.get("expected_columns") and "currency (auto-added)" in str(query_def["expected_columns"]):
            has_currency = "currency" in sql.lower()
            validations["checks"].append({
                "check": "currency_auto_included",
                "passed": has_currency,
                "message": "Currency column should be auto-included for monetary queries"
            })
            if not has_currency:
                validations["passed"] = False
        
        # Check BETWEEN is used for temporal filters
        if query_def.get("expected_filters"):
            for filter_def in query_def["expected_filters"]:
                if "BETWEEN" in str(filter_def):
                    has_between = "BETWEEN" in sql.upper()
                    validations["checks"].append({
                        "check": "temporal_between",
                        "passed": has_between,
                        "message": "Should use BETWEEN for date ranges"
                    })
                    if not has_between:
                        validations["passed"] = False
        
        # Check payment_date vs fee_period_start for fees paid queries
        if "fees paid" in query_def["query"].lower():
            uses_payment_date = "payment_date" in sql.lower()
            uses_fee_period = "fee_period_start" in sql.lower()
            correct_column = uses_payment_date and not uses_fee_period
            validations["checks"].append({
                "check": "correct_temporal_column",
                "passed": correct_column,
                "message": "'fees paid' should use payment_date, not fee_period_start"
            })
            if not correct_column:
                validations["passed"] = False
        
        # Check SQL validity (executed without error)
        if result.get("result", {}).get("success"):
            validations["checks"].append({
                "check": "sql_execution",
                "passed": True,
                "rows_returned": result["result"].get("row_count", 0)
            })
        else:
            validations["passed"] = False
            validations["checks"].append({
                "check": "sql_execution",
                "passed": False,
                "message": result.get("result", {}).get("error", "Execution failed")
            })
        
        return validations
    
    def run_tests(
        self, 
        queries_file: str,
        query_id: Optional[str] = None,
        category: Optional[str] = None,
        complexity: Optional[str] = None
    ) -> Dict:
        """Run validation tests on queries"""
        
        # Load queries
        data = self.load_queries(queries_file)
        test_queries = data.get("test_queries", [])
        
        # Filter queries
        if query_id:
            test_queries = [q for q in test_queries if q.get("id") == query_id]
        if category:
            test_queries = [q for q in test_queries if q.get("category") == category]
        if complexity:
            test_queries = [q for q in test_queries if q.get("complexity") == complexity]
        
        logger.info(f"Running {len(test_queries)} test queries...")
        
        results = {
            "total": len(test_queries),
            "passed": 0,
            "failed": 0,
            "details": []
        }
        
        for i, query_def in enumerate(test_queries, 1):
            query_id = query_def.get("id", f"Q{i:03d}")
            query_text = query_def.get("query")
            
            logger.info(f"\n[{i}/{len(test_queries)}] Testing {query_id}: {query_text}")
            
            # Execute query
            start_time = time.time()
            result = self.execute_query(query_text)
            execution_time = time.time() - start_time
            
            # Validate result
            validation = self.validate_result(query_def, result)
            validation["execution_time_sec"] = round(execution_time, 2)
            validation["sql"] = result.get("sql", {}).get("sql", "")
            
            # Log results
            if validation["passed"]:
                results["passed"] += 1
                logger.info(f"✓ {query_id} PASSED ({execution_time:.2f}s)")
            else:
                results["failed"] += 1
                logger.warning(f"✗ {query_id} FAILED")
                for check in validation["checks"]:
                    if not check.get("passed", True):
                        logger.warning(f"  - {check.get('check')}: {check.get('message', 'Failed')}")
            
            results["details"].append(validation)
        
        return results
    
    def generate_report(self, results: Dict, output_file: Optional[str] = None):
        """Generate a detailed test report"""
        
        report = []
        report.append("=" * 80)
        report.append("REPORTSMITH TEST QUERY VALIDATION REPORT")
        report.append("=" * 80)
        report.append(f"\nTotal Queries: {results['total']}")
        report.append(f"Passed: {results['passed']} ({results['passed']/results['total']*100:.1f}%)")
        report.append(f"Failed: {results['failed']} ({results['failed']/results['total']*100:.1f}%)")
        report.append("\n" + "=" * 80)
        report.append("DETAILED RESULTS")
        report.append("=" * 80)
        
        for detail in results["details"]:
            status = "✓ PASS" if detail["passed"] else "✗ FAIL"
            report.append(f"\n{detail['query_id']}: {status}")
            report.append(f"Query: {detail['query_text']}")
            report.append(f"Execution Time: {detail['execution_time_sec']}s")
            
            if detail["checks"]:
                report.append("Checks:")
                for check in detail["checks"]:
                    check_status = "✓" if check.get("passed", True) else "✗"
                    check_name = check.get("check", "unknown")
                    report.append(f"  {check_status} {check_name}")
                    if not check.get("passed", True) and "message" in check:
                        report.append(f"      {check['message']}")
            
            if detail["sql"]:
                report.append(f"Generated SQL:\n{detail['sql'][:200]}...")
        
        report_text = "\n".join(report)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)
            logger.info(f"\nReport saved to: {output_file}")
        
        print("\n" + report_text)
        
        return report_text


def main():
    parser = argparse.ArgumentParser(description="Validate ReportSmith test queries")
    parser.add_argument(
        "--queries-file",
        default="test_queries.yaml",
        help="Path to test queries YAML file"
    )
    parser.add_argument(
        "--query-id",
        help="Run only specific query by ID (e.g., Q001)"
    )
    parser.add_argument(
        "--category",
        help="Run only queries in category (e.g., basic_retrieval)"
    )
    parser.add_argument(
        "--complexity",
        choices=["simple", "medium", "hard", "very_hard"],
        help="Run only queries of specific complexity"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="ReportSmith API URL"
    )
    parser.add_argument(
        "--output",
        help="Output file for detailed report"
    )
    
    args = parser.parse_args()
    
    # Create validator
    validator = QueryValidator(api_url=args.api_url)
    
    # Run tests
    results = validator.run_tests(
        queries_file=args.queries_file,
        query_id=args.query_id,
        category=args.category,
        complexity=args.complexity
    )
    
    # Generate report
    validator.generate_report(results, output_file=args.output)
    
    # Exit with appropriate code
    sys.exit(0 if results["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
