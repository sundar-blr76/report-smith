#!/usr/bin/env python3
"""
Test script to demonstrate caching performance improvements.

Usage:
    python test_cache_performance.py
"""

import time
from reportsmith.utils.cache_manager import get_cache_manager, init_cache_manager

def test_basic_caching():
    """Test basic cache operations."""
    print("=" * 80)
    print("BASIC CACHING TEST")
    print("=" * 80)
    
    # Initialize cache
    cache = init_cache_manager(enable_redis=False, enable_disk=True)
    
    # Test LLM intent caching
    print("\n1. Testing LLM Intent Caching")
    print("-" * 40)
    
    query = "Show me total sales for last quarter"
    fake_result = {"intent": "aggregation", "entities": ["sales"], "time_scope": "quarterly"}
    
    # First call - cache miss
    t0 = time.perf_counter()
    result = cache.get("llm_intent", query.lower())
    t1 = time.perf_counter()
    print(f"Cache GET (miss): {(t1-t0)*1000:.2f}ms - Result: {result}")
    
    # Store result
    t0 = time.perf_counter()
    cache.set("llm_intent", fake_result, query.lower())
    t1 = time.perf_counter()
    print(f"Cache SET: {(t1-t0)*1000:.2f}ms")
    
    # Second call - cache hit
    t0 = time.perf_counter()
    result = cache.get("llm_intent", query.lower())
    t1 = time.perf_counter()
    print(f"Cache GET (hit): {(t1-t0)*1000:.2f}ms - Result: {result}")
    
    # Test domain value caching
    print("\n2. Testing Domain Value Caching")
    print("-" * 40)
    
    user_value = "equity"
    table = "funds"
    column = "fund_type"
    values_hash = "abc123"
    fake_matches = [{"value": "Equity Growth", "confidence": 0.95}]
    
    # Cache miss
    result = cache.get("llm_domain", user_value.lower(), table, column, values_hash)
    print(f"Domain value GET (miss): {result}")
    
    # Store and retrieve
    cache.set("llm_domain", fake_matches, user_value.lower(), table, column, values_hash)
    result = cache.get("llm_domain", user_value.lower(), table, column, values_hash)
    print(f"Domain value GET (hit): {result}")
    
    # Test semantic search caching
    print("\n3. Testing Semantic Search Caching")
    print("-" * 40)
    
    search_query = "client fees"
    app_id = "fund_accounting"
    top_k = 5
    fake_results = [
        {"table": "fee_transactions", "score": 0.95},
        {"table": "clients", "score": 0.85}
    ]
    
    result = cache.get("semantic", "schema", search_query.lower(), str(app_id), str(top_k))
    print(f"Semantic GET (miss): {result}")
    
    cache.set("semantic", fake_results, "schema", search_query.lower(), str(app_id), str(top_k))
    result = cache.get("semantic", "schema", search_query.lower(), str(app_id), str(top_k))
    print(f"Semantic GET (hit): {result}")
    
    # Print statistics
    print("\n4. Cache Statistics")
    print("-" * 40)
    cache.print_stats()


def test_performance_comparison():
    """Compare performance with and without caching."""
    print("\n" + "=" * 80)
    print("PERFORMANCE COMPARISON TEST")
    print("=" * 80)
    
    cache = get_cache_manager()
    
    # Simulate expensive operation
    def expensive_operation(query: str):
        """Simulate LLM call."""
        time.sleep(0.1)  # Simulate 100ms latency
        return {"intent": "aggregation", "query": query}
    
    test_queries = [
        "Show me total sales",
        "List all clients",
        "Show me total sales",  # Duplicate
        "What are the fees",
        "Show me total sales",  # Duplicate
        "List all clients",     # Duplicate
    ]
    
    print("\nWithout Caching:")
    print("-" * 40)
    t0 = time.perf_counter()
    for query in test_queries:
        result = expensive_operation(query)
        print(f"  Query: '{query}' -> took ~100ms")
    t_no_cache = time.perf_counter() - t0
    print(f"Total time: {t_no_cache:.2f}s")
    
    print("\nWith Caching:")
    print("-" * 40)
    t0 = time.perf_counter()
    for query in test_queries:
        # Check cache
        result = cache.get("llm_intent", query.lower())
        if result is None:
            # Cache miss - do expensive operation
            result = expensive_operation(query)
            cache.set("llm_intent", result, query.lower())
            print(f"  Query: '{query}' -> MISS, took ~100ms")
        else:
            print(f"  Query: '{query}' -> HIT, took <1ms")
    t_with_cache = time.perf_counter() - t0
    print(f"Total time: {t_with_cache:.2f}s")
    
    print(f"\nSpeedup: {t_no_cache/t_with_cache:.1f}x faster with caching")
    print(f"Time saved: {(t_no_cache - t_with_cache):.2f}s")
    
    # Print final stats
    print("\nFinal Cache Statistics:")
    print("-" * 40)
    stats = cache.get_stats("llm_intent")
    print(f"  Hits: {stats.hits}")
    print(f"  Misses: {stats.misses}")
    print(f"  Hit Rate: {stats.hit_rate:.1%}")
    print(f"  Time saved (estimated): {stats.hits * 0.1:.2f}s")


def test_cache_invalidation():
    """Test cache invalidation."""
    print("\n" + "=" * 80)
    print("CACHE INVALIDATION TEST")
    print("=" * 80)
    
    cache = get_cache_manager()
    
    # Add some data
    cache.set("llm_intent", {"intent": "test1"}, "query1")
    cache.set("llm_domain", {"match": "test2"}, "query2")
    cache.set("semantic", {"results": "test3"}, "query3")
    
    print("\nBefore invalidation:")
    print(f"  llm_intent: {cache.get('llm_intent', 'query1')}")
    print(f"  llm_domain: {cache.get('llm_domain', 'query2')}")
    print(f"  semantic: {cache.get('semantic', 'query3')}")
    
    # Invalidate only LLM intent
    print("\nInvalidating llm_intent cache...")
    cache.invalidate("llm_intent")
    
    print("\nAfter invalidation:")
    print(f"  llm_intent: {cache.get('llm_intent', 'query1')}")
    print(f"  llm_domain: {cache.get('llm_domain', 'query2')}")
    print(f"  semantic: {cache.get('semantic', 'query3')}")
    
    # Invalidate all
    print("\nInvalidating all caches...")
    cache.invalidate()
    
    print("\nAfter full invalidation:")
    print(f"  llm_intent: {cache.get('llm_intent', 'query1')}")
    print(f"  llm_domain: {cache.get('llm_domain', 'query2')}")
    print(f"  semantic: {cache.get('semantic', 'query3')}")


if __name__ == "__main__":
    test_basic_caching()
    test_performance_comparison()
    test_cache_invalidation()
    
    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETED")
    print("=" * 80)
