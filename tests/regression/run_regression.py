"""
Regression Test Runner

Main entry point for running regression tests.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional
import requests
import time
from colorama import init, Fore, Style

from test_case import TestCase, GoldenSnapshot, ComparisonResult
from comparator import Comparator

# Initialize colorama for cross-platform colored output
init(autoreset=True)


class RegressionRunner:
    """Runs regression tests against the API."""
    
    def __init__(self, api_base: str = "http://127.0.0.1:8000"):
        self.api_base = api_base
        self.comparator = Comparator()
        
        # Use script directory as base for paths
        script_dir = Path(__file__).parent.absolute()
        self.test_cases_dir = script_dir / "test_cases"
        self.golden_dir = script_dir / "golden"
        self.reports_dir = script_dir / "reports"
        
        # Ensure directories exist
        self.golden_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def load_test_cases(self, category: Optional[str] = None) -> List[TestCase]:
        """Load test cases from YAML files."""
        test_cases = []
        
        if not self.test_cases_dir.exists():
            print(f"{Fore.YELLOW}Warning: Test cases directory not found: {self.test_cases_dir}{Style.RESET_ALL}")
            return test_cases
        
        for yaml_file in sorted(self.test_cases_dir.glob("*.yaml")):
            try:
                test_case = TestCase.from_yaml(yaml_file)
                
                # Filter by category if specified
                if category and test_case.category != category:
                    continue
                
                test_cases.append(test_case)
            except Exception as e:
                print(f"{Fore.RED}Error loading {yaml_file}: {e}{Style.RESET_ALL}")
        
        return test_cases
    
    def execute_query(self, question: str, timeout: int = 120) -> dict:
        """Execute query via API."""
        try:
            response = requests.post(
                f"{self.api_base}/query",
                json={"question": question},
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def record_golden(self, test_case: TestCase) -> bool:
        """Record golden snapshot for a test case."""
        print(f"\n{Fore.CYAN}Recording: {test_case.id}{Style.RESET_ALL}")
        print(f"  Question: {test_case.question}")
        
        # Execute query
        response = self.execute_query(test_case.question)
        
        if "error" in response:
            print(f"  {Fore.RED}✗ Failed: {response['error']}{Style.RESET_ALL}")
            return False
        
        # Create golden snapshot
        snapshot = GoldenSnapshot.from_api_response(
            test_id=test_case.id,
            question=test_case.question,
            response=response
        )
        
        # Save to file
        golden_file = self.golden_dir / f"{test_case.id}.json"
        snapshot.to_json(golden_file)
        
        print(f"  {Fore.GREEN}✓ Recorded to {golden_file}{Style.RESET_ALL}")
        return True
    
    def test_against_golden(self, test_case: TestCase) -> ComparisonResult:
        """Test a query against its golden snapshot."""
        result = ComparisonResult(test_id=test_case.id, passed=True)
        
        # Load golden snapshot
        golden_file = self.golden_dir / f"{test_case.id}.json"
        if not golden_file.exists():
            result.add_warning(f"Golden snapshot not found: {golden_file}")
            result.passed = False
            return result
        
        try:
            golden = GoldenSnapshot.from_json(golden_file)
        except Exception as e:
            result.add_warning(f"Failed to load golden snapshot: {e}")
            result.passed = False
            return result
        
        # Execute query
        actual_response = self.execute_query(test_case.question)
        
        if "error" in actual_response:
            result.add_difference("execution", "success", f"error: {actual_response['error']}")
            return result
        
        # Compare responses
        self._compare_responses(golden.response, actual_response, result, test_case)
        
        return result
    
    def _compare_responses(self, golden: dict, actual: dict, result: ComparisonResult, test_case: TestCase):
        """Compare golden vs actual response."""
        golden_data = golden.get("data", {}).get("result", {})
        actual_data = actual.get("data", {}).get("result", {})
        
        # Compare intent type
        golden_intent = golden_data.get("intent", {})
        actual_intent = actual_data.get("intent", {})
        
        if golden_intent.get("type") != actual_intent.get("type"):
            result.add_difference(
                "intent_type",
                golden_intent.get("type"),
                actual_intent.get("type")
            )
        
        # Compare SQL
        golden_sql = golden_data.get("sql", {}).get("sql", "")
        actual_sql = actual_data.get("sql", {}).get("sql", "")
        
        sql_match, sql_diffs = self.comparator.compare_sql(golden_sql, actual_sql)
        if not sql_match:
            result.add_difference("sql", golden_sql, actual_sql, path="sql")
            for diff in sql_diffs:
                result.add_warning(f"SQL: {diff}")
        
        # Compare execution results
        golden_exec = golden_data.get("execution", {})
        actual_exec = actual_data.get("execution", {})
        
        # Compare columns
        golden_cols = golden_exec.get("columns", [])
        actual_cols = actual_exec.get("columns", [])
        
        cols_match, col_diffs = self.comparator.compare_columns(golden_cols, actual_cols)
        if not cols_match:
            result.add_difference("columns", golden_cols, actual_cols)
            for diff in col_diffs:
                result.add_warning(f"Columns: {diff}")
        
        # Compare row count
        golden_count = golden_exec.get("row_count", 0)
        actual_count = actual_exec.get("row_count", 0)
        
        count_match, count_diffs = self.comparator.compare_row_count(golden_count, actual_count)
        if not count_match:
            result.add_difference("row_count", golden_count, actual_count)
            for diff in count_diffs:
                result.add_warning(f"Row count: {diff}")
    
    def run_tests(self, category: Optional[str] = None) -> dict:
        """Run all regression tests."""
        test_cases = self.load_test_cases(category)
        
        if not test_cases:
            print(f"{Fore.YELLOW}No test cases found{Style.RESET_ALL}")
            return {"total": 0, "passed": 0, "failed": 0}
        
        print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Running {len(test_cases)} regression tests{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        
        results = []
        passed = 0
        failed = 0
        
        for test_case in test_cases:
            print(f"\n{Fore.CYAN}Testing: {test_case.id}{Style.RESET_ALL}")
            print(f"  Question: {test_case.question[:80]}...")
            
            result = self.test_against_golden(test_case)
            results.append(result)
            
            if result.passed:
                print(f"  {Fore.GREEN}✓ PASSED{Style.RESET_ALL}")
                passed += 1
            else:
                print(f"  {Fore.RED}✗ FAILED{Style.RESET_ALL}")
                failed += 1
                
                # Show differences
                for diff in result.differences[:3]:  # Show first 3
                    print(f"    - {diff['category']}: {diff.get('expected', 'N/A')} → {diff.get('actual', 'N/A')}")
                
                if len(result.differences) > 3:
                    print(f"    ... and {len(result.differences) - 3} more differences")
        
        # Summary
        print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Summary:{Style.RESET_ALL}")
        print(f"  Total: {len(test_cases)}")
        print(f"  {Fore.GREEN}Passed: {passed}{Style.RESET_ALL}")
        print(f"  {Fore.RED}Failed: {failed}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
        
        return {
            "total": len(test_cases),
            "passed": passed,
            "failed": failed,
            "results": results
        }
    
    def record_all(self, category: Optional[str] = None) -> None:
        """Record golden snapshots for all test cases."""
        test_cases = self.load_test_cases(category)
        
        if not test_cases:
            print(f"{Fore.YELLOW}No test cases found{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Recording {len(test_cases)} golden snapshots{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        
        success = 0
        failed = 0
        
        for test_case in test_cases:
            if self.record_golden(test_case):
                success += 1
            else:
                failed += 1
            
            # Small delay to avoid overwhelming API
            time.sleep(0.5)
        
        print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Recording complete:{Style.RESET_ALL}")
        print(f"  {Fore.GREEN}Success: {success}{Style.RESET_ALL}")
        print(f"  {Fore.RED}Failed: {failed}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="ReportSmith Regression Test Runner")
    parser.add_argument("--record", action="store_true", help="Record golden snapshots")
    parser.add_argument("--category", type=str, help="Filter by category")
    parser.add_argument("--api-base", type=str, default="http://127.0.0.1:8000", help="API base URL")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    runner = RegressionRunner(api_base=args.api_base)
    
    if args.record:
        runner.record_all(category=args.category)
    else:
        summary = runner.run_tests(category=args.category)
        
        # Exit with error code if tests failed
        if summary["failed"] > 0:
            sys.exit(1)


if __name__ == "__main__":
    main()
