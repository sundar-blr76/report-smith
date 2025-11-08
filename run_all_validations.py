#!/usr/bin/env python3
"""
Master Validation Script

Runs all validation scripts and provides a comprehensive report.
"""

import subprocess
import sys
from datetime import datetime

def run_script(script_name: str, description: str) -> tuple[bool, str]:
    """Run a validation script and return success status."""
    print(f"\n{'='*80}")
    print(f"Running: {description}")
    print(f"{'='*80}")
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=False,
            timeout=300
        )
        
        success = result.returncode == 0
        status = "✓ PASSED" if success else "✗ FAILED"
        return success, status
    
    except subprocess.TimeoutExpired:
        return False, "✗ TIMEOUT"
    except Exception as e:
        return False, f"✗ ERROR: {str(e)}"

def main():
    print("="*80)
    print("ReportSmith Validation Suite")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    validation_scripts = [
        ("validate_currency_handling.py", "Currency Auto-Inclusion Validation"),
        ("validate_temporal_predicates.py", "Temporal Predicate Resolution Validation"),
    ]
    
    results = []
    for script, description in validation_scripts:
        success, status = run_script(script, description)
        results.append((description, status, success))
    
    # Final Summary
    print(f"\n{'='*80}")
    print("FINAL SUMMARY")
    print(f"{'='*80}")
    
    for description, status, _ in results:
        print(f"{status}: {description}")
    
    all_passed = all(success for _, _, success in results)
    
    if all_passed:
        print(f"\n✓ All validation suites PASSED")
        sys.exit(0)
    else:
        print(f"\n✗ Some validation suites FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()
