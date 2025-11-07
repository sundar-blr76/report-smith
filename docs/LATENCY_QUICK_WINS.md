# Latency Quick Wins - Implementation Guide

**Target**: Reduce query latency from 3.6s to <2s  
**Timeline**: 1-2 weeks  
**Expected Impact**: 30-50% latency reduction

---

## Overview

This guide focuses on the **highest ROI, lowest complexity** improvements that can be implemented quickly to meet the <2s latency target.

---

## Quick Win #1: Query Result Caching

**Estimated Savings**: 100% on cache hits (3.6s → 0.01s)  
**Implementation Time**: 4-6 hours  
**Complexity**: ⭐⭐ Medium

### Implementation

```python
# src/reportsmith/cache/query_cache.py
import hashlib
import json
from typing import Optional, Dict, Any
import redis

class QueryResultCache:
    """Cache complete query results to avoid reprocessing."""
    
    def __init__(self, redis_client: redis.Redis, ttl: int = 3600):
        """
        Args:
            redis_client: Redis client instance
            ttl: Time-to-live in seconds (default 1 hour)
        """
        self.redis = redis_client
        self.ttl = ttl
        self.hit_count = 0
        self.miss_count = 0
    
    def _make_key(self, question: str, app_id: Optional[str]) -> str:
        """Generate cache key from question and app_id."""
        content = f"{app_id or 'default'}:{question.lower().strip()}"
        hash_val = hashlib.md5(content.encode()).hexdigest()
        return f"qcache:{hash_val}"
    
    def get(self, question: str, app_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve cached result if available."""
        key = self._make_key(question, app_id)
        try:
            cached = self.redis.get(key)
            if cached:
                self.hit_count += 1
                return json.loads(cached)
            self.miss_count += 1
            return None
        except Exception as e:
            logger.warning(f"Cache get failed: {e}")
            return None
    
    def set(self, question: str, result: Dict[str, Any], app_id: Optional[str] = None):
        """Store query result in cache."""
        key = self._make_key(question, app_id)
        try:
            self.redis.setex(key, self.ttl, json.dumps(result, default=str))
        except Exception as e:
            logger.warning(f"Cache set failed: {e}")
    
    def invalidate(self, question: str, app_id: Optional[str] = None):
        """Invalidate specific query cache."""
        key = self._make_key(question, app_id)
        self.redis.delete(key)
    
    def invalidate_all(self):
        """Clear all query caches (use after schema changes)."""
        for key in self.redis.scan_iter("qcache:*"):
            self.redis.delete(key)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total * 100) if total > 0 else 0
        return {
            "hits": self.hit_count,
            "misses": self.miss_count,
            "hit_rate_percent": round(hit_rate, 2),
            "total_requests": total
        }
```

### Integration with Orchestrator

```python
# src/reportsmith/agents/orchestrator.py

from reportsmith.cache.query_cache import QueryResultCache

class MultiAgentOrchestrator:
    def __init__(self, ..., redis_client: Optional[redis.Redis] = None):
        # ... existing init
        self.query_cache = QueryResultCache(redis_client) if redis_client else None
    
    def process_query(self, question: str, app_id: Optional[str] = None) -> Dict:
        """Process query with caching."""
        
        # Try cache first
        if self.query_cache:
            cached = self.query_cache.get(question, app_id)
            if cached:
                logger.info(f"[cache:hit] Returning cached result for: {question}")
                cached["cached"] = True
                return cached
            logger.debug(f"[cache:miss] No cache for: {question}")
        
        # Process query normally
        result = self._process_query_internal(question, app_id)
        
        # Cache the result
        if self.query_cache and not result.get("errors"):
            self.query_cache.set(question, result, app_id)
        
        result["cached"] = False
        return result
```

### Expected Impact
- **Cache Hit Rate**: 20-40% for typical usage
- **Latency on Hit**: 3.6s → <0.05s (99% improvement)
- **Average Savings**: 0.7-1.4s across all queries

---

## Quick Win #2: Adaptive LLM Model Selection

**Estimated Savings**: 30-40% average (1.0-1.4s)  
**Implementation Time**: 6-8 hours  
**Complexity**: ⭐⭐ Medium

### Implementation

```python
# src/reportsmith/query_processing/llm_selector.py

class AdaptiveLLMSelector:
    """Select optimal LLM model based on query complexity."""
    
    # Model configurations: (provider, model, avg_latency_s, accuracy)
    MODELS = {
        "fast": ("openai", "gpt-3.5-turbo", 0.8, 0.85),
        "balanced": ("anthropic", "claude-3-haiku-20240307", 1.2, 0.90),
        "accurate": ("openai", "gpt-4-turbo-preview", 2.5, 0.95),
    }
    
    def __init__(self, default_tier: str = "balanced"):
        self.default_tier = default_tier
    
    def select_model(self, query: str) -> tuple[str, str]:
        """
        Select model based on query complexity.
        
        Returns:
            (provider, model_name)
        """
        complexity = self._assess_complexity(query)
        
        if complexity == "simple":
            tier = "fast"
        elif complexity == "complex":
            tier = "accurate"
        else:
            tier = self.default_tier
        
        provider, model, _, _ = self.MODELS[tier]
        logger.info(f"[llm:selector] query_complexity={complexity}, selected={tier} ({provider}/{model})")
        return provider, model
    
    def _assess_complexity(self, query: str) -> str:
        """Assess query complexity using heuristics."""
        query_lower = query.lower()
        word_count = len(query.split())
        
        # Simple query indicators
        simple_patterns = [
            query_lower.startswith(("show", "list", "display")),
            word_count <= 6,
            not any(word in query_lower for word in ["compare", "vs", "versus", "trend", "over time"])
        ]
        
        # Complex query indicators
        complex_patterns = [
            any(word in query_lower for word in ["compare", "correlate", "forecast", "predict"]),
            word_count >= 15,
            query_lower.count("and") >= 2,
            "between" in query_lower and "and" in query_lower,
        ]
        
        # Scoring
        if sum(simple_patterns) >= 2:
            return "simple"
        elif sum(complex_patterns) >= 2:
            return "complex"
        else:
            return "medium"
```

### Integration

```python
# src/reportsmith/query_processing/llm_intent_analyzer.py

class LLMIntentAnalyzer:
    def __init__(self, ..., use_adaptive_model: bool = True):
        # ... existing init
        self.use_adaptive = use_adaptive_model
        self.model_selector = AdaptiveLLMSelector() if use_adaptive else None
    
    def analyze(self, query: str) -> QueryIntent:
        """Analyze query with adaptive model selection."""
        
        # Select model dynamically
        if self.model_selector:
            provider, model = self.model_selector.select_model(query)
            # Update client for this request
            self._switch_model(provider, model)
        
        # Proceed with analysis
        return self._analyze_with_llm(query)
```

### Expected Impact
- **Simple Queries (60%)**: 3.6s → 0.8s (78% improvement)
- **Medium Queries (30%)**: 3.6s → 1.2s (67% improvement)
- **Complex Queries (10%)**: 3.6s → 2.5s (31% improvement)
- **Average**: ~1.4s savings (39% improvement)

---

## Quick Win #3: Fast Path Detection

**Estimated Savings**: 3s for 20-30% of queries  
**Implementation Time**: 4-6 hours  
**Complexity**: ⭐⭐ Medium

### Implementation

```python
# src/reportsmith/query_processing/fast_path.py

class FastPathDetector:
    """Detect queries that can bypass LLM analysis."""
    
    def __init__(self, entity_mappings: Dict[str, Any]):
        self.mappings = entity_mappings
        self._build_index()
    
    def _build_index(self):
        """Build lookup index for fast matching."""
        self.entity_index = {}
        for entity_name, config in self.mappings.items():
            # Index by entity name
            self.entity_index[entity_name.lower()] = config
            # Index by synonyms
            for synonym in config.get("synonyms", []):
                self.entity_index[synonym.lower()] = config
    
    def try_fast_path(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to resolve query without LLM.
        
        Returns:
            Intent dict if fast path successful, None otherwise
        """
        query_lower = query.lower().strip()
        
        # Pattern 1: "show [entity]" or "list [entity]"
        if match := self._match_simple_retrieval(query_lower):
            return match
        
        # Pattern 2: "count [entity]"
        if match := self._match_simple_count(query_lower):
            return match
        
        # Pattern 3: Direct entity mention with high confidence
        if match := self._match_direct_entity(query_lower):
            return match
        
        return None
    
    def _match_simple_retrieval(self, query: str) -> Optional[Dict]:
        """Match: show|list|display [entity]"""
        import re
        pattern = r'^(show|list|display)\s+(all\s+)?(\w+)$'
        if match := re.match(pattern, query):
            entity = match.group(3)
            if entity in self.entity_index:
                config = self.entity_index[entity]
                return {
                    "intent_type": "retrieval",
                    "entities": [entity],
                    "table": config.get("table"),
                    "confidence": 0.95,
                    "fast_path": True
                }
        return None
    
    def _match_simple_count(self, query: str) -> Optional[Dict]:
        """Match: count [entity]"""
        import re
        pattern = r'^count\s+(\w+)$'
        if match := re.match(pattern, query):
            entity = match.group(1)
            if entity in self.entity_index:
                config = self.entity_index[entity]
                return {
                    "intent_type": "aggregation",
                    "entities": [entity],
                    "aggregations": ["count"],
                    "table": config.get("table"),
                    "confidence": 0.95,
                    "fast_path": True
                }
        return None
    
    def _match_direct_entity(self, query: str) -> Optional[Dict]:
        """Match queries where 70%+ words are known entities."""
        words = query.split()
        matched_entities = []
        
        for word in words:
            if word in self.entity_index:
                matched_entities.append(word)
        
        # If 70%+ words are entities, likely a simple query
        if len(matched_entities) / len(words) >= 0.7:
            # Build intent from matched entities
            return {
                "intent_type": "retrieval",
                "entities": matched_entities,
                "confidence": 0.85,
                "fast_path": True
            }
        
        return None
```

### Integration

```python
# src/reportsmith/query_processing/hybrid_intent_analyzer.py

class HybridIntentAnalyzer:
    def __init__(self, ..., enable_fast_path: bool = True):
        # ... existing init
        self.fast_path = FastPathDetector(entity_mappings) if enable_fast_path else None
    
    def analyze(self, question: str) -> QueryIntent:
        """Analyze with fast path detection."""
        
        # Try fast path first
        if self.fast_path:
            if intent := self.fast_path.try_fast_path(question):
                logger.info(f"[fast_path:hit] Resolved without LLM: {question}")
                return self._build_query_intent_from_fast_path(intent, question)
        
        # Fall back to full LLM analysis
        logger.debug(f"[fast_path:miss] Using LLM analysis")
        return self._analyze_with_llm(question)
```

### Expected Impact
- **Fast Path Hit Rate**: 20-30%
- **Latency on Hit**: 3.6s → 0.1s (97% improvement)
- **Average Savings**: 0.6-0.9s across all queries

---

## Quick Win #4: Reduce Semantic Search Top-K

**Estimated Savings**: 20-50ms per query  
**Implementation Time**: 1 hour  
**Complexity**: ⭐ Easy

### Implementation

```python
# src/reportsmith/agents/nodes.py

# Current (line ~250)
batch_results = em.search_all_batch(
    search_texts,
    app_id=state.app_id,
    schema_top_k=100,     # Too high
    dimension_top_k=100,  # Too high
    context_top_k=100,    # Too high
)

# Optimized
batch_results = em.search_all_batch(
    search_texts,
    app_id=state.app_id,
    schema_top_k=50,      # Reduced by 50%
    dimension_top_k=50,   # Reduced by 50%
    context_top_k=20,     # Reduced by 80% (least used)
)
```

### Testing

```python
# Test script to validate recall isn't impacted
def test_top_k_impact():
    test_queries = load_test_queries()
    
    for query in test_queries:
        # Original k=100
        results_100 = process_with_k(query, k=100)
        
        # Reduced k=50
        results_50 = process_with_k(query, k=50)
        
        # Compare accuracy
        assert results_50.accuracy >= results_100.accuracy * 0.95  # Allow 5% drop
```

### Expected Impact
- **Latency Savings**: 20-50ms per query
- **Recall Impact**: <2% (negligible)
- **Risk**: Very low

---

## Combined Impact Summary

Implementing all four quick wins:

```
Current:     3.6s average latency
After QW#1:  3.6s → 2.5s (query cache @ 30% hit rate)
After QW#2:  2.5s → 1.5s (adaptive LLM)
After QW#3:  1.5s → 1.2s (fast path @ 25% hit rate)
After QW#4:  1.2s → 1.15s (reduced top-k)

Final:       1.15s average latency
Improvement: 68% reduction ✅ EXCEEDS TARGET
```

**P95 Latency** (95th percentile):
```
Current:     5.0s
Target:      <2.5s
After:       1.8s ✅ EXCEEDS TARGET
```

---

## Implementation Order

### Day 1: Setup & Infrastructure
- [ ] Add Redis client to orchestrator initialization
- [ ] Create `src/reportsmith/cache/query_cache.py`
- [ ] Add unit tests for QueryResultCache

### Day 2-3: Core Implementations
- [ ] Implement QueryResultCache and integrate
- [ ] Create AdaptiveLLMSelector
- [ ] Create FastPathDetector
- [ ] Add configuration flags for each feature

### Day 4: Integration & Testing
- [ ] Integrate all components with orchestrator
- [ ] Update API server to use new features
- [ ] Add monitoring/metrics for each optimization
- [ ] Run integration tests

### Day 5: Tuning & Validation
- [ ] Reduce semantic search top-k values
- [ ] Run performance benchmarks
- [ ] Adjust thresholds based on results
- [ ] Update documentation

---

## Configuration

Add to `.env`:
```bash
# Query Result Cache
ENABLE_QUERY_CACHE=true
QUERY_CACHE_TTL=3600

# Adaptive LLM Selection
ENABLE_ADAPTIVE_LLM=true
LLM_DEFAULT_TIER=balanced  # fast|balanced|accurate

# Fast Path Detection
ENABLE_FAST_PATH=true

# Semantic Search
SEMANTIC_SEARCH_SCHEMA_K=50
SEMANTIC_SEARCH_DIMENSION_K=50
SEMANTIC_SEARCH_CONTEXT_K=20
```

---

## Monitoring

Add to logging:
```python
# Cache stats
logger.info(f"[perf:cache] hit_rate={cache.get_stats()['hit_rate_percent']}%")

# Model selection
logger.info(f"[perf:llm] tier={tier}, model={model}, latency={latency}ms")

# Fast path
logger.info(f"[perf:fast_path] hit_rate={fast_path_hits/total_queries*100}%")
```

Add to `/health` endpoint:
```json
{
  "performance": {
    "avg_latency_ms": 1150,
    "p95_latency_ms": 1800,
    "cache_hit_rate": 0.32,
    "fast_path_rate": 0.25,
    "llm_avg_latency_ms": 1200
  }
}
```

---

## Rollback Plan

Each optimization can be disabled independently via config:

```python
# Disable query cache
ENABLE_QUERY_CACHE=false

# Disable adaptive LLM
ENABLE_ADAPTIVE_LLM=false

# Disable fast path
ENABLE_FAST_PATH=false
```

If issues occur, disable the problematic feature and investigate.

---

## Success Criteria

✅ **Primary Goal**: Average query latency < 2.0s  
✅ **P95 Goal**: 95th percentile latency < 2.5s  
✅ **Quality**: Intent accuracy maintained at ≥95%  
✅ **Stability**: Error rate < 1%  

---

## Next Steps

After implementing quick wins:
1. Monitor performance for 1 week
2. Collect user feedback
3. Measure cache hit rates and adjust TTLs
4. Consider Phase 2 improvements (streaming, pre-computation)

See `docs/LATENCY_IMPROVEMENTS.md` for comprehensive analysis and long-term roadmap.
