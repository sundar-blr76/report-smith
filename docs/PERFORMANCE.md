# Performance Optimization Guide

This document consolidates all performance-related optimizations and strategies.

## Overview

ReportSmith has undergone several performance optimization iterations focusing on:
1. Embedding generation and caching
2. Semantic search optimization
3. LLM call reduction
4. Database query optimization

## Key Optimizations Implemented

### 1. Embedding Caching Strategy

**Problem**: Generating embeddings for the same text repeatedly was costly.

**Solution**:
- Cache embeddings at multiple levels (query, schema, domain values)
- Use content-based hashing for cache keys
- Persist cache to disk for reuse across sessions

**Impact**: 70-80% reduction in embedding API calls for repeat queries.

See EMBEDDING_STRATEGY.md for implementation details.

### 2. Batch Embedding Generation

**Problem**: Multiple sequential embedding calls for entity enrichment.

**Solution**:
- Batch all entity texts into single embedding API call
- Process results in parallel

**Impact**: 5-10x faster entity enrichment phase.

### 3. Minimal Embedding Strategy

**Problem**: Embedding full column descriptions was expensive and sometimes less accurate.

**Solution**:
- Embed only entity names/primary identifiers
- Use synonyms as separate embeddings for better matching
- Include business context separately

**Impact**: 40% reduction in embedding costs, improved accuracy.

### 4. LLM Intent Analyzer Optimization

**Problem**: Multiple LLM calls for intent extraction and entity enrichment.

**Solution**:
- Single structured LLM call with JSON schema
- Temporal context provided upfront to resolve date predicates
- Local mappings checked first before LLM

**Impact**: Average query latency reduced from 8-12s to 3-5s.

## Performance Metrics

| Phase | Before | After | Improvement |
|-------|--------|-------|-------------|
| Embedding Generation | 2-4s | 0.5-1s | 60-75% |
| Intent Analysis | 6-8s | 2-3s | 60-65% |
| Entity Enrichment | 3-5s | 0.5-1s | 80-90% |
| Total Query Time | 12-18s | 4-6s | 65-70% |

## Quick Wins

For immediate performance gains:

1. **Enable caching**: Ensure embedding cache is enabled in config
2. **Use local mappings**: Define common terms in entity_mappings.yaml
3. **Batch operations**: Process multiple queries together when possible
4. **Optimize prompts**: Keep LLM prompts focused and concise

## Future Optimization Opportunities

1. **Parallel LLM + Semantic Search**: Run LLM intent analysis and semantic enrichment in parallel
2. **Streaming SQL Generation**: Start SQL generation as soon as entities are identified
3. **Query Result Caching**: Cache SQL results for identical queries
4. **Adaptive Thresholds**: Dynamically adjust semantic search thresholds based on result quality

## Monitoring and Profiling

Key metrics to monitor:
- `timings.intent_ms` - LLM intent extraction time
- `timings.schema_ms` - Entity-to-table mapping time  
- `timings.plan_ms` - Query plan generation time
- `timings.sql_ms` - SQL generation and validation time

Use the `/query` endpoint's response to track these metrics per query.

---

*Consolidated from: LATENCY_IMPROVEMENTS.md, LATENCY_QUICK_WINS.md, LATENCY_SUMMARY.md, EMBEDDING_CACHING.md*
