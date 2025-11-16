# Quick Test Guide - Post Implementation

## Critical Test Query
Run this query first to validate the enhancements:

**Query**: "List the top 5 clients by total fees paid on bond funds in Q1 2025"

**What to Check**:
1. ✅ **client_name** column appears in results (NEW - prompt enhancement)
2. ✅ **client_id** column appears in results (NEW - prompt enhancement)
3. ✅ **currency** column appears in results (should already work)
4. ✅ **payment_date** used in WHERE clause, not fee_period_start (should already work)
5. ✅ GROUP BY includes client columns (should already work)

**Expected SQL Structure**:
```sql
SELECT 
  SUM(fee_transactions.fee_amount) AS fees,
  clients.client_name,              -- ← Should now appear
  clients.client_id,                -- ← Should now appear
  funds.fund_type,
  fee_transactions.currency
FROM funds
  INNER JOIN fee_transactions ON ...
  INNER JOIN accounts ON ...
  INNER JOIN clients ON ...
WHERE payment_date BETWEEN '2025-01-01' AND '2025-03-31'
  AND funds.fund_type = 'Bond'
  AND funds.is_active = true
GROUP BY 
  clients.client_name,              -- ← Should now appear
  clients.client_id,                -- ← Should now appear
  funds.fund_type,
  fee_transactions.currency
ORDER BY fees DESC
LIMIT 5
```

## Log Checks

### 1. Token Tracking (Already Implemented)
Look for in logs:
```
[local-mapping] Query tokens analysis:
[local-mapping]   Matched tokens: ['bond', 'clients', 'fees', 'funds']
[local-mapping]   Dropped tokens (non-stopwords): ['q1', '2025']
```

### 2. Domain Enrichment (Already Implemented)
Look for in logs:
```
[domain-enricher] Enriching 'bond' for funds.fund_type
[domain-enricher] ✓ Successfully enriched 'bond' → 'Bond' (confidence=0.95)
```

### 3. LLM Column Enrichment (Enhanced)
Look for in logs:
```
[sql-gen][llm-enrich] analyzing query for implicit context columns
[sql-gen][llm-enrich] LLM suggested adding: clients.client_name
[sql-gen][llm-enrich] LLM suggested adding: clients.client_id
```

### 4. Temporal Predicate (Already Implemented)
Look for in logs:
```
[predicate-resolution] ✓ Temporal predicate resolved in filters
Intent filters: ['payment_date BETWEEN \'2025-01-01\' AND \'2025-03-31\'']
```

## Other Test Queries from Suite

### Test: Equity Products Matching
**Query**: "Show equity products"
**Expected**: Should match BOTH "Equity Growth" AND "Equity Value"
**Check**: Multiple fund types returned, not just one

### Test: Partial Company Name
**Query**: "Show fees for TruePotential clients"
**Expected**: Should match "TruePotential Asset Management"
**Check**: Results should include TruePotential company

### Test: Average Fees with Domain Value
**Query**: "What are the average fees by fund type for retail investors?"
**Expected**: 
- Domain value 'retail' matches 'Retail'
- Currency column included
- GROUP BY includes client_type

### Test: Currency Auto-Inclusion
**Query**: "Show total fees by fund type"
**Expected**: Currency column automatically included in SELECT and GROUP BY

## Validation Commands

```bash
# Navigate to project
cd /home/sundar/sundar_projects/report-smith

# Check application is running
ps aux | grep -E "streamlit|uvicorn" | grep -v grep

# Access UI
# Open browser: http://127.0.0.1:8501

# Check recent logs
tail -100 logs/app.log | grep -E "UNMAPPED|domain-enricher|llm-enrich|local-mapping"

# Run comprehensive test (if script exists)
python validate_test_queries.py test_queries.yaml

# Clear cache if needed (to test fresh)
# Redis: redis-cli FLUSHDB
# Or set env: CACHE_ENABLED=false
```

## Success Criteria

### Must Pass
- [ ] Client name/ID appear in ranking queries
- [ ] Currency always included with fee amounts
- [ ] Temporal predicates use correct column (payment_date for "paid")
- [ ] GROUP BY includes all non-aggregated columns
- [ ] No SQL execution errors

### Should Pass
- [ ] "Equity" matches multiple fund types
- [ ] "TruePotential" matches full company name
- [ ] Token tracking visible in logs
- [ ] Domain enrichment logging appears
- [ ] Cache hit rate > 30% after warm-up

### Nice to Have
- [ ] All 28 test queries execute successfully
- [ ] Query response time < 5s with warm cache
- [ ] No unnecessary SQL refinement iterations
- [ ] LLM enrichment confidence scores > 0.8

## If Issues Found

### Problem: Client columns still missing
**Check**: 
1. Look for `[sql-gen][llm-enrich]` logs
2. Verify LLM response includes client columns
3. Check if enrichment is being called (intent_type=ranking?)

**Fix**: May need to make prompt even more explicit or add programmatic fallback

### Problem: Wrong temporal column used
**Check**:
1. Look for intent extraction logs
2. Check filter predicates in intent
3. Verify SQL WHERE clause

**Fix**: May need to enhance prompt with more examples

### Problem: Domain values not matching
**Check**:
1. Look for `[domain-enricher]` logs
2. Check if enrichment is being called
3. Verify confidence scores

**Fix**: May need to add local mappings for common patterns

### Problem: Cache causing issues
**Solution**: 
```bash
# Clear Redis cache
redis-cli FLUSHDB

# Or disable cache temporarily
export CACHE_ENABLED=false
```

## Next Steps After Testing

1. **If tests pass**: Convert test suite to automated regression tests
2. **If tests fail**: Document failures, adjust prompts/logic
3. **Add local mappings** for common patterns (equity, etc.)
4. **Monitor performance** with cache statistics
5. **Iterate on prompts** based on LLM response quality

## Contact Points for Issues

- **Caching**: Check `src/reportsmith/utils/cache_manager.py`
- **Domain enrichment**: Check `src/reportsmith/query_processing/domain_value_enricher.py`
- **Column selection**: Check `src/reportsmith/query_processing/sql_generator.py:1367-1600`
- **Intent extraction**: Check `src/reportsmith/query_processing/llm_intent_analyzer.py`
- **Logging**: Check `logs/app.log`

## Files to Reference

- **Implementation details**: `IMPLEMENTATION_NOTES.md`
- **Test queries**: `test_queries.yaml` (canonical version)
- **Task summary**: `TASK_SUMMARY_2025-11-08.md`
- **Setup guide**: `SETUP.md`
- **Changelog**: `CHANGELOG.md`
