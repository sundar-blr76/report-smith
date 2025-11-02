# Embedding Filter Improvements

## Problem
Generic and numeric dimension values were being embedded unnecessarily, causing:
- **Wasted embedding costs**: 46 numeric values for `performance_rating` column
- **Poor semantic search quality**: Numbers like "3.82", "4.44" don't provide meaningful semantic matches
- **Increased vector DB size**: Storing useless embeddings

## Solution
Added intelligent filtering in `EmbeddingManager._is_embeddable_dimension_value()` that skips:

### 1. Pure Numbers
- Integer or decimal values: `123`, `3.82`, `-45.6`
- Regex: `^-?\d+\.?\d*$`

### 2. Generic IDs
- Values like `id`, `ID`, `client_id`, `fund_id`
- Regex: `^id$|^[a-z_]*_?id$` (case-insensitive)

### 3. Too Short Values
- Single character values
- Length check: `< 2 chars`

### 4. UUIDs
- Pattern: `8-4-4-4-12` hex digits
- Regex: `^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$`

### 5. Hash-like Strings
- Long hexadecimal strings (32+ chars)
- Regex: `^[a-f0-9]+$` with length >= 32

## Results

### Before
```
Loaded 46 dimension values for fund_managers.performance_rating
Values: ['3.82', '4.44', '3.84', '2.99', '3.28', '3.88', ...]
```

### After
```
No embeddable dimension values for fund_accounting.fund_managers.performance_rating 
(all 46 values were generic/numeric)
Skipped values: ['3.82', '4.44', '3.84', '2.99', '3.28', '3.88', ...]
```

### Statistics
- **fund_type**: ✅ 10 embeddable values (text: "Equity Growth", "Balanced", etc.)
- **risk_rating**: ✅ 3 embeddable values (text: "Moderate", "Conservative", "Aggressive")
- **client_type**: ✅ 3 embeddable values (text: "Individual", "Corporate", "Institutional")
- **performance_rating**: ⚠️ 0 embeddable values (all 46 were numeric)

### Total Embeddings
- **Before**: 62 dimension value embeddings
- **After**: 16 dimension value embeddings (74% reduction)
- **Embedding requests saved**: ~46 OpenAI API calls

## Impact

### Cost Savings
With OpenAI's `text-embedding-3-small`:
- Price: $0.02 per 1M tokens
- Avg token per value: ~5 tokens
- Saved per seed: 46 values × 5 tokens = 230 tokens
- **Negligible cost impact**, but **cleaner vector DB**

### Quality Improvements
- More focused semantic search results
- No false matches on numeric values
- Better separation of semantic vs. exact-match entities

## Logging Enhancements
Added detailed logging to track filtering:
- INFO: Shows count of embeddable values loaded
- WARNING: Alerts when all values are filtered out
- DEBUG: Lists first 10 skipped values for inspection

## Configuration
No configuration needed. Filter is automatic and embedded in the `EmbeddingManager` class.

## Future Considerations
1. **Metric columns**: Consider adding specific handling for numeric metrics (like `performance_rating`) to use exact match instead of semantic search
2. **Date values**: May want to filter out date/timestamp strings
3. **Domain-specific patterns**: Can add custom filters for specific business patterns
4. **Configuration**: Could make filter rules configurable if needed

## Files Modified
- `src/reportsmith/schema_intelligence/embedding_manager.py`:
  - Added `_is_embeddable_dimension_value()` static method
  - Updated `load_dimension_values()` to filter and log results
  - Added import for `re` module
