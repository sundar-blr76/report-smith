# ReportSmith - Outstanding Issues to Fix

## Date: November 9, 2025

Based on user feedback and latest log analysis, here are the confirmed issues requiring fixes:

---

## 🔴 CRITICAL ISSUES

### 1. Caching Bug - Wrong SQL Being Cached
**Log Evidence**:
```
Query: "List the top 5 clients by total fees paid on bond funds in Q1 2025"
SQL Generated: SELECT fee_transactions.fee_amount AS fees... (wrong - not aggregated)
```

**Problem**: Cache is returning wrong SQL. Possible causes:
- Cache key not unique enough (missing query nuances)
- SQL being cached before validation/refinement
- Cache invalidation not working properly

**Files to Check**:
- `src/reportsmith/utils/cache_manager.py`
- `src/reportsmith/agents/nodes.py` (SQL generation caching)
- `src/reportsmith/query_processing/sql_generator.py`

**Fix Required**:
1. Review cache key generation for SQL
2. Ensure cache key includes: query text, intent type, selected columns, aggregations
3. Add cache invalidation when SQL is refined/corrected
4. Add logging to show cache hits/misses with keys

---

### 2. Currency Missing in Aggregation Queries
**User Query**: "List the top 5 clients by total fees paid..."
**Expected**: Should include currency column  
**Actual**: Currency missing

**Problem**: Despite auto-inclusion code existing, currency not appearing in aggregated fee queries

**Files to Check**:
- `src/reportsmith/query_processing/sql_generator.py` (lines 438-471 - currency auto-inclusion)
- Check if currency is being removed during GROUP BY optimization
- Check if it's being filtered out in column selection

**Fix Required**:
1. Debug why currency auto-inclusion isn't working
2. Ensure currency is in SELECT and GROUP BY for monetary aggregations
3. Add test case for this scenario

---

### 3. Quarter Predicates (Q1 2025) Not Resolved Early
**Log Evidence**:
```
[schema][UNMAPPED] >>> Q1 2025 (type=unknown, conf=0.0)
```

**Problem**: Temporal predicates like "Q1 2025" should be resolved by LLM intent analyzer into SQL predicates, not left as unmapped entities

**Current Flow** (WRONG):
1. Intent analyzer extracts "Q1 2025" as entity
2. Entity mapper tries to map it (fails)
3. Left as unmapped

**Desired Flow** (CORRECT):
1. Intent analyzer recognizes "Q1 2025" as temporal predicate
2. Converts to SQL: `BETWEEN '2025-01-01' AND '2025-03-31'`
3. Adds to filters list
4. No entity created for "Q1 2025"

**Files to Fix**:
- `src/reportsmith/query_processing/llm_intent_analyzer.py`
  - Enhance prompt to better detect temporal expressions
  - Add examples showing Q1/Q2/Q3/Q4 should become BETWEEN clauses
  - Pass table context to help identify which date column to use

**Fix Required**:
1. Update LLM intent analyzer prompt with better temporal examples
2. Add post-processing to catch common temporal patterns (Q1-Q4, "last quarter", etc.)
3. When temporal entities detected, immediately convert to SQL predicates
4. Add logging to show: "Resolved 'Q1 2025' → BETWEEN '2025-01-01' AND '2025-03-31'"

---

### 4. Fee Period vs Payment Date Confusion
**User Query**: "fees paid in Q1 2025"  
**Current**: Uses `fee_period_start` (WRONG - this is the period being charged FOR)
**Correct**: Should use `payment_date` (when fee was actually PAID)

**Problem**: LLM not distinguishing between:
- "fees FOR Q1" → fee_period_start
- "fees PAID IN Q1" → payment_date

**Files to Fix**:
- `src/reportsmith/query_processing/llm_intent_analyzer.py` (temporal column selection)
- Enhance prompt to explain the distinction

**Fix Required**:
1. Add examples to LLM prompt showing this distinction
2. Extract not just the date range but WHICH temporal column
3. Add logging: "Temporal filter: 'paid in Q1' → using payment_date (not fee_period)"

---

### 5. Domain Value Matching - Multiple Values Not Handled
**Example**: User says "equity products"
- Database has: "Equity Growth", "Equity Value", "Equity Income"
- Current: May only pick one
- Expected: Should match ALL equity-related values (OR clause)

**Problem**: Domain enricher returns array but SQL generator may not use all matches

**Files to Check**:
- `src/reportsmith/agents/nodes.py` (domain enrichment - stores all_llm_matches)
- `src/reportsmith/query_processing/sql_generator.py` (WHERE clause generation)

**Fix Required**:
1. When domain enricher returns multiple matches, create OR clause
2. Example: `fund_type IN ('Equity Growth', 'Equity Value', 'Equity Income')`
3. Add logging: "Domain value 'equity' matched 3 values: Equity Growth, Equity Value, Equity Income"

---

### 6. TruePotential Partial Match Issue
**User Query**: "List fees for TruePotential clients"
**Database Value**: "TruePotential Asset Management"
**Current**: Fails with exact match
**Expected**: Should fuzzy match or use LLM enrichment

**Problem**: Direct match fails, semantic search may not catch it

**Fix Required**:
1. Ensure domain enricher is called for management company names
2. LLM should easily match "TruePotential" → "TruePotential Asset Management"
3. Log the enrichment: "Enriched 'TruePotential' → 'TruePotential Asset Management'"

---

## 🟡 MEDIUM PRIORITY

### 7. Domain Value - Don't Add User Text As-Is
**Problem**: When semantic search fails and domain enricher fails, system adds user value directly to query
**Example**: User says "retail", database has "Retail", query uses "retail" (fails due to case sensitivity)

**Current Code** (to find and remove):
```python
# Fallback: use entity text as-is 
value = ent.get("text")
```

**Fix Required**:
1. Remove fallback that uses raw user text
2. If domain enricher returns no confident match, return error to user:
   "Could not find matching value for 'retail'. Available values are: Retail, Institutional, High-Net-Worth"
3. Let user refine their query

---

### 8. Logging Improvements

#### A. Domain Value Enricher - Show Full LLM Call
**Required Logs**:
- `[domain-enricher][llm-call] Sending request to gemini (model: gemini-2.5-flash)`
- `[domain-enricher][llm-call] Prompt (XXXX chars):` (then full prompt)
- `[domain-enricher][llm-call] Response (XXms): [JSON array]`
- `[domain-enricher][llm-call] Parsed X matches: ...`

**File**: `src/reportsmith/query_processing/domain_value_enricher.py`

#### B. Intent Analyzer - Token Analysis
**Current**: Already logging dropped vs. lookup tokens
**Verify**: Ensure this happens at DEBUG or INFO level

#### C. Predicate Resolution - Visual Flow
**Required**: Show how unmapped entities are resolved step-by-step
- `[predicate-resolution] Found 2 unmapped entities`
- `[predicate-resolution] Attempting enrichment for 'retail'...`
- `[predicate-resolution] ✓ Enriched 'retail' → 'Retail' (conf=0.95)`
- `[predicate-resolution] ✗ Failed to enrich 'Q1 2025' - will leave unmapped`

---

## 🟢 LOW PRIORITY / CLEANUP

### 9. Consolidate Markdown Files
**Current**: Multiple summary files with overlapping content
**Required**:
- Delete: CACHING_IMPLEMENTATION.md, CACHING_IMPLEMENTATION_COMPLETE.md
- Keep: FINAL_SUMMARY.md (rename to CHANGELOG_RECENT.md)
- Keep: IMPLEMENTATION_SUMMARY.md (rename to TECHNICAL_NOTES.md)
- Merge older changes into CHANGELOG.md

### 10. Unnecessary SQL Refinement Iterations
**Log**: Shows SQL going through refinement even when already valid
**Check**: `src/reportsmith/query_processing/sql_validator.py`
**Fix**: Skip refinement if SQL is already valid and returns reasonable results

---

## 📋 TESTING REQUIRED AFTER FIXES

### Test Queries to Verify:
1. "List the top 5 clients by total fees paid on bond funds in Q1 2025"
   - ✓ Should use payment_date (not fee_period)
   - ✓ Should include currency
   - ✓ Should aggregate (SUM) fees
   - ✓ Should resolve Q1 2025 early (not unmapped entity)

2. "What are the average fees by fund type for all our retail investors?"
   - ✓ Should match "retail" to "Retail" via LLM enrichment
   - ✓ Should include currency

3. "For equity products, show total fees by month for the last 12 months"
   - ✓ Should match ALL equity fund types (Equity Growth, Equity Value, Equity Income)
   - ✓ Should group by month properly

4. "List fees for TruePotential clients"
   - ✓ Should match "TruePotential" → "TruePotential Asset Management"

---

## 🔧 IMPLEMENTATION PRIORITY

**Phase 1** (Do First):
1. Fix caching bug (#1) - Critical for performance and correctness
2. Fix Q1 2025 resolution (#3) - Fundamental design issue
3. Fix currency inclusion (#2) - Affects many queries

**Phase 2** (Do Next):
4. Fee period vs payment date (#4) - Important for correctness
5. Multiple domain value matches (#5) - Better UX

**Phase 3** (Do Last):
6. TruePotential matching (#6) - Should work once domain enricher is properly called
7. Remove user text fallback (#7)
8. Logging improvements (#8)

**Phase 4** (Cleanup):
9. Consolidate MD files
10. Remove unnecessary refinement iterations

---

## 📊 SUCCESS METRICS

After fixes, the system should:
- ✅ Cache hit rate > 60% for repeated similar queries
- ✅ Domain enrichment success rate > 85%
- ✅ Temporal predicates resolved in intent phase (not entity phase)
- ✅ Currency always included in monetary aggregations
- ✅ Clear, visual logging showing decision flow
- ✅ Zero incorrect cache hits (wrong SQL)
