# Outstanding Issues & Action Items

## ✅ FIXED

### 1. Missing Client Identifiers in Ranking Queries
**Issue**: Query "List the top 5 clients by total fees paid on bond funds in Q1 2025" was missing client identifiers in SELECT and GROUP BY.

**Root Cause**: LLM enrichment sometimes failed to add entity identifiers for ranking queries.

**Fix Applied**: 
- Enhanced LLM enrichment prompt to explicitly detect and handle ranking entities
- Added fallback heuristic logic (`_fallback_add_ranking_identifiers`) to add entity identifiers when LLM fails
- Improved entity extraction from user questions using regex patterns

**Status**: ✅ FIXED - Verified in logs, now includes `clients.id`, `clients.client_code`, `clients.first_name` in GROUP BY

### 2. Stale Cache Results
**Issue**: Query was returning cached results from previous runs with different intents.

**Fix Applied**: 
- Cleared SQL cache
- Cache key already includes tables and columns for proper differentiation

**Status**: ✅ FIXED

### 3. Documentation Consolidation  
**Issue**: Too many temporary MD files (TASK_SUMMARY, IMPLEMENTATION_NOTES, etc.)

**Fix Applied**: 
- Consolidated into IMPLEMENTATION_HISTORY.md
- Kept only strategic docs: README, SETUP, CHANGELOG, CONTRIBUTING, TESTING_GUIDE

**Status**: ✅ FIXED

---

## 🔍 TO INVESTIGATE

### 4. Q1 2025 Temporal Predicate Resolution
**Issue**: "Q1 2025" was being marked as `entity_type=unknown` instead of being resolved to filter predicate by LLM intent analyzer.

**Expected Behavior**: LLM intent analyzer should convert "Q1 2025" to:
```python
filters: ["EXTRACT(QUARTER FROM fee_period_start) = 1 AND EXTRACT(YEAR FROM fee_period_start) = 2025"]
```

**Current Behavior**: 
- The filter IS being generated correctly (verified in logs)
- But "Q1 2025" is still appearing in entities list as unmapped
- This is benign (entity is safely ignored since it's in filters) but logs show warnings

**Action Needed**: 
- Add check in entity extraction to skip temporal phrases that are already handled by filters
- Or suppress warnings for temporal entities that exist in filters

**Priority**: LOW (cosmetic logging issue, not affecting functionality)

---

### 5. Fee Period Selection Logic  
**Issue**: Query asks for "fees paid in last quarter" but filter uses `fee_period_start` instead of `payment_date`.

**Question**: Which is correct for "fees paid"?
- `payment_date` - when fee was actually paid
- `fee_period_start` - period the fee covers

**Action Needed**: 
- Review business requirements with domain expert
- Update entity mappings and LLM context if needed
- May need to add business rules: "fees paid" → payment_date, "fees for period" → fee_period_start

**Priority**: MEDIUM (affects correctness of temporal queries)

---

### 6. Domain Value Matching - Partial Matches
**Issue**: Query "List fees for TruePotential clients" fails because it searches for exact "truepotential" but database has "TruePotential Asset Management".

**Current Behavior**: 
- Direct search: Fails (case/partial mismatch)  
- Semantic search: May fail if below threshold
- LLM enrichment: Should succeed but need to verify it's being called

**Potential Improvements**:
1. **Better fuzzy matching** - Use edit distance for company names
2. **Partial match patterns** - "TruePotential" should match "TruePotential Asset Management"
3. **LLM enrichment with context** - Already implemented, need to verify effectiveness

**Action Needed**:
- Test this specific query
- Check if LLM enrichment is being triggered
- If not, lower semantic search threshold or improve matching

**Priority**: HIGH (affects user experience)

---

### 7. Equity Value Fund Type Not Included
**Issue**: Query "equity products" matches "Equity Growth" but not "Equity Value" in predicate.

**Expected**: Both fund types should be matched:
```sql
WHERE funds.fund_type IN ('Equity Growth', 'Equity Value')
```

**Current**: Only gets one:
```sql
WHERE funds.fund_type = 'Equity Growth'
```

**Root Cause**: Domain value enricher is finding multiple matches but SQL generator is only using the first one.

**Fix Needed**: 
- When domain value enricher returns multiple matches, SQL generator should use `IN (...)` instead of `=`
- Update `_build_where_conditions` in sql_generator.py

**Priority**: HIGH (affects query correctness)

---

### 8. Currency Missing from Reports
**Issue**: Some monetary queries return results without currency column.

**Expected**: Any query with monetary amounts should automatically include currency.

**Current Status**: Logic exists in `_build_select_columns` (lines 443-466) to auto-add currency.

**Action Needed**:
- Verify this logic is working
- Test queries that should have currency
- Check if currency is being filtered out somewhere downstream

**Priority**: MEDIUM (data quality issue)

---

## 📋 ENHANCEMENT REQUESTS

### 9. Better Logging for Domain Value Resolution
**Request**: Print LLM prompts and responses for domain value matching.

**Status**: Already implemented in domain_value_enricher.py:
- Lines 195-198: Logs full prompt
- Lines 215: Logs LLM raw response  
- Lines 242-247: Logs all matches with confidence scores

**Action**: Verify logs are visible at appropriate level (INFO/DEBUG)

**Priority**: LOW (already done)

---

### 10. Local Mapping Search Logging
**Request**: "While searching for local mapping, print the dropped query tokens vs lookup tokens for developer comprehension"

**Action Needed**:
- Add logging in HybridIntentAnalyzer where local mappings are searched
- Show which tokens from query were used vs dropped
- Example: `Query tokens: ['list', 'top', 'clients', 'fees'] → Lookup tokens: ['clients', 'fees'] (dropped: ['list', 'top'])`

**Priority**: LOW (developer UX)

---

### 11. Intent Extraction LLM Prompt Logging
**Request**: Print the full LLM prompt at "Gemini Intent Extraction Request"

**Status**: Need to verify if already implemented.

**Action Needed**:
- Check llm_intent_analyzer.py for prompt logging
- Add if missing: `logger.info(f"[intent][llm] Full prompt:\n{prompt}")`

**Priority**: LOW (debugging aid)

---

### 12. Unnecessary Iteration Detection
**Request**: "Does it look like we are making unnecessary iterations at this point?"

**Context**: SQL refinement may be making extra LLM calls.

**Action Needed**:
- Review refinement iteration logic in sql_validator.py
- Check if refinement is being triggered unnecessarily
- Add metrics: iteration count, success rate, time per iteration

**Priority**: MEDIUM (performance optimization)

---

### 13. Test Query Suite
**Request**: Create 20+ meaningful queries of varying complexity as regression tests.

**Action Needed**:
- Review schema, data, and current capabilities
- Create comprehensive test suite covering:
  - Simple retrievals
  - Aggregations
  - Ranking/top-N
  - Temporal queries (quarters, months, years)
  - Multi-table joins
  - Domain value matching
  - Complex filters
  - Edge cases
  
**Priority**: HIGH (quality assurance)

**File**: `tests/test_queries_regression.yaml`

---

## 🎯 PRIORITY SUMMARY

### High Priority
1. ✅ Missing Client Identifiers in Ranking Queries - **FIXED**
2. Domain Value Matching - Partial Matches (#6)
3. Equity Value Fund Type Not Included (#7)  
4. Test Query Suite (#13)

### Medium Priority  
5. Fee Period Selection Logic (#5)
6. Currency Missing from Reports (#8)
7. Unnecessary Iteration Detection (#12)

### Low Priority
8. Q1 2025 Temporal Entity Logging (#4) - cosmetic
9. Domain Value Resolution Logging (#9) - already done
10. Local Mapping Search Logging (#10)
11. Intent Extraction Prompt Logging (#11)

---

## 📝 NOTES

- Cache has been cleared to fix stale results
- LLM enrichment for ranking queries now has fallback logic
- Documentation consolidated to essential files only
- All changes committed to git

---

Last Updated: 2025-11-09
