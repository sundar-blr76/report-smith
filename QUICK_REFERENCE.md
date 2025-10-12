# Quick Reference - LLM Intent Analyzer Changes

## What Changed

### 1. Configuration (all backward compatible)
```python
analyzer = LLMIntentAnalyzer(
    embedding_manager=em,
    llm_provider="gemini",
    max_search_results=100,           # NEW: was hardcoded 3/2
    schema_score_threshold=0.3,        # NEW: configurable
    dimension_score_threshold=0.3,     # NEW: configurable  
    context_score_threshold=0.4,       # NEW: configurable
    max_matches_warning=20             # NEW: warn users
)
```

### 2. Entity Enrichment Flow
```
Old: top_k=3 → filter → done (might miss matches!)
New: top_k=100 → score filter → LLM refinement → warn if >20
```

### 3. Logging (44 new statements)
- DEBUG: Full prompts, payloads, responses, metadata
- INFO: Requests, results, summaries
- WARNING: Fallbacks, issues
- ERROR: Exceptions with traces

## When to Tune Parameters

| Parameter | Increase If... | Decrease If... |
|-----------|----------------|----------------|
| `max_search_results` | Schema is huge (>1000 tables) | Memory concerns |
| `schema_score_threshold` | Too many irrelevant matches | Missing relevant matches |
| `dimension_score_threshold` | Too many dimension values | Missing important values |
| `context_score_threshold` | Context pollution | Missing business rules |
| `max_matches_warning` | Too many warnings | Not enough warnings |

## Logging Levels for Different Scenarios

| Scenario | Log Level | What You'll See |
|----------|-----------|-----------------|
| Development | DEBUG | Everything: prompts, responses, reasoning |
| Staging | INFO | Requests, results, match counts |
| Production | INFO | High-level tracking |
| Troubleshooting | DEBUG | Full detail for specific issues |
| Cost Tracking | DEBUG | Token usage per request |

## Common Use Cases

### See what LLM is doing
```python
import logging
logger = logging.getLogger('reportsmith.query_processing.llm_intent_analyzer')
logger.setLevel(logging.DEBUG)
```

### Monitor production
```python
logger.setLevel(logging.INFO)
# You'll see: requests, results, match counts, warnings
```

### Tune thresholds based on data
```python
# Start with defaults, then adjust based on logs
analyzer = LLMIntentAnalyzer(
    em, "gemini",
    schema_score_threshold=0.4,  # Stricter if too many false positives
    max_matches_warning=10        # Lower if users need more guidance
)
```

## Files Modified
- `src/reportsmith/query_processing/llm_intent_analyzer.py` (639 lines, +279)

## Documentation
- `ENRICHMENT_REFACTOR.md` - Detailed design and rationale
- `LLM_LOGGING_GUIDE.md` - Complete logging guide
- `CHANGES_SUMMARY.md` - Overview of all changes
- `QUICK_REFERENCE.md` - This file

## Key Improvements
✅ No arbitrary limits → All relevant matches captured
✅ Score-based filtering → Quality over quantity  
✅ LLM refinement → Contextual understanding
✅ Comprehensive logging → Full observability
✅ Configurable → Tunable for your use case
✅ Backward compatible → Existing code works unchanged
