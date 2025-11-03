#!/usr/bin/env python3
"""
Test script to verify SQL query execution end-to-end.
"""

import requests
import json
import time

API_BASE = "http://127.0.0.1:8000"

def test_query(question: str):
    """Send a query and display results."""
    print(f"\n{'='*80}")
    print(f"Question: {question}")
    print(f"{'='*80}")
    
    payload = {"question": question}
    
    try:
        start = time.time()
        response = requests.post(
            f"{API_BASE}/query",
            json=payload,
            timeout=120
        )
        elapsed = time.time() - start
        
        print(f"Response time: {elapsed:.2f}s")
        print(f"Status code: {response.status_code}")
        
        if response.ok:
            data = response.json()
            result = data.get("data", {})
            
            # Display execution results
            if result.get("result"):
                result_data = result["result"]
                execution = result_data.get("execution")
                
                if execution:
                    if execution.get("error"):
                        print(f"\n❌ Execution Error: {execution.get('error')}")
                    else:
                        print(f"\n✅ Query executed successfully!")
                        print(f"Rows returned: {execution.get('row_count')}")
                        
                        # Display first few rows
                        rows = execution.get("rows", [])
                        if rows:
                            print(f"\nSample Results (first 5 rows):")
                            print("-" * 80)
                            for i, row in enumerate(rows[:5], 1):
                                print(f"Row {i}: {json.dumps(row, default=str)}")
                
                # Display SQL
                sql_data = result_data.get("sql")
                if sql_data:
                    print(f"\n📝 Generated SQL:")
                    print("-" * 80)
                    print(sql_data.get("sql", ""))
                    print("-" * 80)
            
            # Display timings
            timings = result.get("timings_ms", {})
            if timings:
                print(f"\n⏱️  Timings (ms):")
                for stage, time_ms in timings.items():
                    print(f"  {stage}: {time_ms:.2f}ms")
            
        else:
            print(f"\n❌ Request failed: {response.status_code}")
            print(response.text)
    
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    # Test simple query
    test_query("Show AUM for all equity funds")
    
    # Test with filters
    test_query("List the top 5 clients by total fees")
    
    print(f"\n{'='*80}")
    print("Test complete!")
    print(f"{'='*80}\n")
