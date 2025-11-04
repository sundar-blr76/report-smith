#!/usr/bin/env python3
"""
Test script for SQL generation with LLM context column enrichment.
"""
import requests
import json
import time

# Test query that should trigger context column enrichment
test_query = "List the top 5 clients by total fees paid on bond funds in Q1 2025"

print("=" * 80)
print("Testing SQL Generation with LLM Context Column Enrichment")
print("=" * 80)
print(f"\nQuery: {test_query}")
print()

# Send query to API
url = "http://127.0.0.1:8000/query"
payload = {"question": test_query}

print("Sending request to API...")
t0 = time.time()

try:
    response = requests.post(url, json=payload, timeout=120)
    dt = time.time() - t0
    
    print(f"Response received in {dt:.1f}s")
    print()
    
    if response.status_code == 200:
        result = response.json()
        
        # Extract key information
        sql = result.get("sql", {}).get("sql", "")
        explanation = result.get("sql", {}).get("explanation", "")
        metadata = result.get("sql", {}).get("metadata", {})
        timings = result.get("timings", {})
        
        print("=" * 80)
        print("SQL QUERY GENERATED:")
        print("=" * 80)
        print(sql)
        print()
        
        print("=" * 80)
        print("METADATA:")
        print("=" * 80)
        print(json.dumps(metadata, indent=2))
        print()
        
        print("=" * 80)
        print("TIMINGS:")
        print("=" * 80)
        print(json.dumps(timings, indent=2))
        print()
        
        print("=" * 80)
        print("EXPLANATION:")
        print("=" * 80)
        print(explanation)
        print()
        
        # Save full response to file
        log_dir = Path(__file__).parent.parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "test_sql_enrichment_result.json"
        with open(log_file, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Full response saved to {log_file}")
        
    else:
        print(f"ERROR: Status code {response.status_code}")
        print(response.text)
        
except requests.exceptions.Timeout:
    print(f"ERROR: Request timed out after 120s")
except Exception as e:
    print(f"ERROR: {e}")

print()
print("=" * 80)
print("Check logs/app.log for detailed logging including LLM enrichment")
print("=" * 80)
