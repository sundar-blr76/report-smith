# ReportSmith Implementation Guide

This guide consolidates implementation strategies, performance optimizations, and best practices.

## Table of Contents
1. [Embedding Strategy](#embedding-strategy)
2. [Performance Optimization](#performance-optimization)
3. [Query Processing Best Practices](#query-processing-best-practices)

---

## Embedding Strategy

### Overview
ReportSmith uses a **minimal embedding strategy** for semantic search to improve precision and reduce noise in entity matching.

### Key Principles
1. **Embed minimal text**: Just entity name or synonym
2. **Store context in metadata**: Full descriptions, relationships stored separately
3. **Separate entity types**: Different embeddings for tables, columns, domain values
4. **Caching**: Avoid redundant embedding calls

### Implementation
See `docs/EMBEDDING_STRATEGY.md` for full details (merged into this guide).

---

## Performance Optimization  

### Database Query Optimization
- Connection pooling with configurable min/max connections
- Query timeout configuration
- Prepared statement caching

### LLM Call Optimization
- Rate limiting to prevent API throttling
- Token usage tracking and cost monitoring
- Response caching for identical queries

### Embedding Search Optimization
- Top-k limiting (typically 3-5 results)
- Score thresholding to filter low-quality matches
- Batch embedding for multiple entities

### Memory Management
- Lazy loading of embeddings
- Periodic cache cleanup
- Connection pool size limits

See `docs/PERFORMANCE.md` for detailed metrics (merged into this guide).

---

## Query Processing Best Practices

### Entity Resolution
1. Try local mappings first (fast, free, precise)
2. Fall back to semantic search
3. Use LLM enrichment for ambiguous cases
4. Always log resolution source for debugging

### Domain Value Matching
1. Check local mappings
2. Perform semantic search
3. Call LLM enrichment to verify against database values
4. Use canonical values in SQL, not user input

### SQL Generation
1. Validate table relationships before generating SQL
2. Use knowledge graph for join path discovery
3. Include currency columns for monetary values
4. Apply appropriate date filters for temporal queries

### Error Handling
1. Log detailed error context
2. Provide helpful error messages to users
3. Implement fallback strategies
4. Track error patterns for improvement

---

For detailed module documentation, see `docs/modules/`
