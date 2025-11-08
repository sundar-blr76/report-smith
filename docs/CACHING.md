# Caching System - ReportSmith

## Overview

ReportSmith implements a comprehensive multi-level caching system to dramatically improve performance by caching:
- LLM responses (intent extraction, domain value matching, SQL refinement)
- Semantic search results  
- Embedding vectors
- Schema metadata lookups

## Architecture

### Three-Level Cache Hierarchy

1. **L1: In-Memory LRU Cache** (fastest, per-instance)
   - Per-category LRU caches with configurable size limits
   - TTL-based expiration
   - Ideal for single-request or single-instance scenarios
   - Typical latency: <0.1ms

2. **L2: Redis Cache** (persistent, cross-instance)
   - Shared across multiple ReportSmith instances
   - Persistent cache survives restarts
   - Ideal for production deployments with multiple workers
   - Typical latency: 1-5ms

3. **L3: Disk Cache** (fallback for large objects)
   - Pickle-based file storage
   - Automatically used for cache misses in L1/L2
   - Ideal for development or when Redis is unavailable
   - Typical latency: 5-20ms

### Cache Categories

Different cache categories have different TTLs optimized for their use cases:

| Category | TTL | Description |
|----------|-----|-------------|
| `llm_intent` | 1 hour | Intent extraction results from LLM |
| `llm_domain` | 2 hours | Domain value matching results |
| `llm_sql` | 30 min | SQL refinement suggestions |
| `semantic` | 2 hours | Semantic search results (embeddings) |
| `embedding` | 24 hours | Raw embedding vectors |
| `sql_result` | 5 min | SQL query result caching |
| `schema` | 24 hours | Schema metadata lookups |

## Usage

### Initialization

The cache manager is automatically initialized when you import any component that uses it:

```python
from reportsmith.utils.cache_manager import get_cache_manager, init_cache_manager

# Get existing instance (or create default)
cache = get_cache_manager()

# Or initialize with custom configuration
cache = init_cache_manager(
    redis_url="redis://localhost:6379/1",
    enable_redis=True,
    enable_disk=True,
    disk_cache_dir="/tmp/reportsmith_cache",
    l1_max_size=1000
)
```

### Basic Operations

```python
from reportsmith.utils.cache_manager import get_cache_manager

cache = get_cache_manager()

# Get from cache
result = cache.get("llm_intent", query.lower())

# Set in cache (uses default TTL for category)
cache.set("llm_intent", result, query.lower())

# Set with custom TTL
cache.set("llm_intent", result, query.lower(), ttl=7200)

# Invalidate specific category
cache.invalidate("llm_intent")

# Invalidate all caches
cache.invalidate()

# Get statistics
stats = cache.get_stats("llm_intent")
print(f"Hit rate: {stats.hit_rate:.1%}")

# Print all statistics
cache.print_stats()
```

### Integration Examples

#### LLM Intent Analyzer

```python
def _extract_with_llm(self, query: str) -> LLMQueryIntent:
    # Check cache first
    if self.enable_cache and self.cache:
        cached = self.cache.get("llm_intent", query.lower())
        if cached:
            logger.info(f"[cache] Using cached intent result")
            return cached
    
    # ... LLM call ...
    result = self.client.generate_content(...)
    
    # Cache result
    if self.enable_cache and self.cache:
        self.cache.set("llm_intent", result, query.lower())
    
    return result
```

#### Domain Value Enricher

```python
def enrich_domain_value(self, user_value: str, table: str, column: str, ...):
    # Check cache
    if self.enable_cache and self.cache:
        cached = self.cache.get("llm_domain", user_value.lower(), table, column, values_hash)
        if cached:
            return cached
    
    # ... LLM enrichment ...
    
    # Cache result
    if self.enable_cache and self.cache:
        self.cache.set("llm_domain", result, user_value.lower(), table, column, values_hash)
    
    return result
```

#### Semantic Search

```python
def search_schema(self, query: str, app_id: str, top_k: int):
    # Check cache
    if self.enable_semantic_cache and self.cache:
        cached = self.cache.get("semantic", "schema", query.lower(), str(app_id), str(top_k))
        if cached:
            return cached
    
    # ... vector search ...
    
    # Cache results
    if self.enable_semantic_cache and self.cache:
        self.cache.set("semantic", results, "schema", query.lower(), str(app_id), str(top_k))
    
    return results
```

## Configuration

### Environment Variables

```bash
# Redis configuration (optional)
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_DB=1  # Use DB 1 for cache (DB 0 is for embeddings)

# Redis URL (alternative)
export REDIS_URL=redis://localhost:6379/1
```

### Disabling Caching

You can disable caching for specific components:

```python
# Disable caching in LLM intent analyzer
analyzer = LLMIntentAnalyzer(
    embedding_manager=emb_mgr,
    enable_cache=False
)

# Disable caching in domain value enricher
enricher = DomainValueEnricher(
    enable_cache=False
)

# Disable Redis while keeping L1 and L3
cache = init_cache_manager(
    enable_redis=False,
    enable_disk=True
)
```

## Performance Benefits

### Expected Performance Improvements

Based on typical usage patterns:

| Operation | Without Cache | With Cache | Speedup |
|-----------|---------------|------------|---------|
| LLM Intent Extraction | 2-5s | <1ms | 2000-5000x |
| Domain Value Matching | 1-3s | <1ms | 1000-3000x |
| Semantic Search | 50-200ms | <1ms | 50-200x |
| Repeat Queries | Full latency | <1ms | 100-10000x |

### Real-World Impact

For a typical session with 10 queries where 30% are repeats:
- Without caching: ~40s total
- With caching: ~30s total (25% faster)
- Repeat queries: 2-5s → <10ms (200-500x faster)

## Monitoring

### Cache Statistics

```python
cache = get_cache_manager()

# Per-category stats
stats = cache.get_stats("llm_intent")
print(f"Category: llm_intent")
print(f"  Hits: {stats.hits}")
print(f"  Misses: {stats.misses}")
print(f"  Hit Rate: {stats.hit_rate:.1%}")
print(f"  Sets: {stats.sets}")
print(f"  Evictions: {stats.evictions}")

# All categories
cache.print_stats()
```

Example output:
```
================================================================================
CACHE STATISTICS
================================================================================
llm_intent           L1_size= 15  CacheStats(hits=23, misses=15, hit_rate=60.53%, sets=15, evictions=0)
llm_domain           L1_size=  8  CacheStats(hits=12, misses=8, hit_rate=60.00%, sets=8, evictions=0)
semantic             L1_size= 42  CacheStats(hits=58, misses=42, hit_rate=58.00%, sets=42, evictions=0)
llm_sql              L1_size=  5  CacheStats(hits=3, misses=5, hit_rate=37.50%, sets=5, evictions=0)
embedding            L1_size=120  CacheStats(hits=180, misses=120, hit_rate=60.00%, sets=120, evictions=0)
sql_result           L1_size=  0  CacheStats(hits=0, misses=0, hit_rate=0.00%, sets=0, evictions=0)
schema               L1_size= 10  CacheStats(hits=25, misses=10, hit_rate=71.43%, sets=10, evictions=0)
================================================================================
```

## Cache Invalidation

### When to Invalidate

Invalidate caches when:
1. Schema changes (new tables, columns, or metadata)
2. Domain values change significantly
3. Business rules or mappings updated
4. Testing or debugging requires fresh results

### Invalidation Strategies

```python
cache = get_cache_manager()

# Invalidate specific category (recommended)
cache.invalidate("llm_intent")
cache.invalidate("semantic")

# Invalidate all (use sparingly)
cache.invalidate()
```

## Best Practices

1. **Enable caching in production**: Significant performance benefits with minimal risk
2. **Monitor hit rates**: Aim for >50% hit rate for frequently-used operations
3. **Tune TTLs**: Adjust based on data change frequency
4. **Use category-specific invalidation**: More surgical than full cache clear
5. **Test without cache**: Ensure functionality works with caching disabled
6. **Size L1 appropriately**: Default 1000 entries should suffice for most use cases
7. **Use Redis in production**: Shared cache across workers improves overall performance

## Troubleshooting

### Cache Not Working

1. Check if caching is enabled:
   ```python
   component.enable_cache  # Should be True
   component.cache  # Should not be None
   ```

2. Verify cache manager is initialized:
   ```python
   from reportsmith.utils.cache_manager import get_cache_manager
   cache = get_cache_manager()
   print(cache)  # Should show CacheManager instance
   ```

3. Check Redis connection (if using Redis):
   ```python
   cache.redis_enabled  # Should be True
   cache.redis_client.ping()  # Should return True
   ```

### Low Hit Rates

1. Check TTLs aren't too short
2. Verify cache keys are consistent (use `.lower()` for query strings)
3. Ensure sufficient L1 cache size
4. Monitor for high eviction rates

### High Memory Usage

1. Reduce L1 cache size:
   ```python
   cache = init_cache_manager(l1_max_size=500)
   ```

2. Disable disk cache if not needed:
   ```python
   cache = init_cache_manager(enable_disk=False)
   ```

3. Use shorter TTLs for frequently-changing data

## Testing

Run the cache performance test:

```bash
python test_cache_performance.py
```

This will demonstrate:
- Basic cache operations
- Performance improvements
- Cache invalidation
- Statistics tracking
