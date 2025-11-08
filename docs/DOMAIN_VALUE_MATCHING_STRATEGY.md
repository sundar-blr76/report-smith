# Domain Value Mismatch Handling Strategy

## Problem Statement

When users provide domain values that don't match well in the database:
- **Current behavior:** Use raw user input as-is → Often results in 0 rows
- **Desired behavior:** Intelligent fallback with user feedback

**Example Issue:**
```
User: "List equity growth funds"
Poor match (score < 0.3)
Generated: WHERE fund_type = 'equity growth'  ← Won't match 'Equity Growth'!
Result: 0 rows ❌
```

## Proposed Multi-Tier Fallback Strategy

```
┌─────────────────────────────────────────┐
│  User Input: "equity growth"            │
└──────────────┬──────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│ Tier 1: Semantic Search (Current)            │
│ - Embedding similarity                        │
│ - Score threshold: 0.3                        │
│ Result: "Equity Growth" (score: 0.28)        │
│ Status: ❌ Below threshold                    │
└──────────────┬───────────────────────────────┘
               │ score < 0.3
               ▼
┌──────────────────────────────────────────────┐
│ Tier 2: Fuzzy String Matching                │
│ - Levenshtein distance (typos)               │
│ - Token matching (word order)                │
│ Examples:                                     │
│   "equty" → "Equity" (distance=1)            │
│   "growth equity" → "Equity Growth" (tokens) │
└──────────────┬───────────────────────────────┘
               │ fuzzy_score < 0.6
               ▼
┌──────────────────────────────────────────────┐
│ Tier 3: LLM-Based Mapping                    │
│ - Handles abbreviations ("tech"→"Technology")│
│ - Context-aware reasoning                     │
│ Example: "tech" → "Technology" (conf: 0.85)  │
└──────────────┬───────────────────────────────┘
               │ confidence < 0.5
               ▼
┌──────────────────────────────────────────────┐
│ Tier 4: Approximate Matching                 │
│ - ILIKE: WHERE col ILIKE '%equity%growth%'   │
│ - Trigram similarity (PostgreSQL pg_trgm)    │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│ Tier 5: User Feedback                        │
│ - Show confidence & alternatives in response │
└───────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Quick Wins (1-2 days)

**Goal:** Detect and warn about poor matches

**Tasks:**
1. Add score threshold check (< 0.3) in SQL generator
2. Add "warnings" array to API response
3. Log low-confidence matches

**Example Response:**
```json
{
  "sql": "...",
  "warnings": [{
    "type": "low_confidence_match",
    "input": "equity growth",
    "matched": "Equity Growth",
    "confidence": 0.28,
    "column": "funds.fund_type",
    "suggestion": "Match confidence is low. Verify results.",
    "alternatives": ["Equity Growth", "Equity Value", "Bond"]
  }]
}
```

**Code Location:** `src/reportsmith/query_processing/sql_generator.py`

**Implementation:**
```python
def _build_where_conditions(...):
    # ... existing code ...
    
    # Check for low confidence matches
    warnings = []
    for ent in dimension_entities:
        top_match = ent.get("top_match", {})
        score = top_match.get("score", 0.0)
        
        if score < 0.3:
            warnings.append({
                "type": "low_confidence_match",
                "input": ent.get("text"),
                "matched": top_match.get("content"),
                "confidence": score,
                "column": f"{ent.get('table')}.{ent.get('column')}",
                "suggestion": "Match confidence is low. Results may be empty."
            })
    
    return conditions, warnings
```

### Phase 2: Fuzzy Matching (3-5 days)

**Goal:** Handle typos and word order variations

**Dependencies:**
```bash
pip install rapidfuzz  # Faster than fuzzywuzzy
```

**Use Cases:**
- Typos: "equty" → "Equity"
- Word order: "growth equity" → "Equity Growth"
- Case sensitivity: "equity" → "Equity"

**Implementation:**
```python
from rapidfuzz import fuzz, process

def _fuzzy_match_domain_value(
    user_input: str,
    available_values: List[str],
    threshold: float = 0.6
) -> Optional[str]:
    """
    Find best fuzzy match for user input
    
    Returns:
        Best matching value if score >= threshold, else None
    """
    if not available_values:
        return None
    
    # Try different matching strategies
    best_match, score, _ = process.extractOne(
        user_input,
        available_values,
        scorer=fuzz.ratio
    )
    
    normalized_score = score / 100.0
    
    if normalized_score >= threshold:
        logger.info(
            f"[fuzzy-match] '{user_input}' → '{best_match}' "
            f"(score={normalized_score:.2f})"
        )
        return best_match
    
    return None
```

**Integration Point:** Call after semantic search fails (score < 0.3)

### Phase 3: LLM-Based Mapping (5-7 days)

**Goal:** Handle abbreviations and synonyms contextually

**Use Cases:**
- Abbreviations: "tech" → "Technology"
- Synonyms: "stocks" → "Equity"
- Domain knowledge: "crypto" → suggest alternatives or fail gracefully

**LLM Prompt Template:**
```python
DOMAIN_VALUE_MAPPING_PROMPT = """
Task: Map user input to the best matching database value.

Column: {table}.{column}
Available values: {available_values}
User input: "{user_input}"
Query context: "{query}"

Instructions:
1. Map the user input to the BEST matching value from the available list
2. Consider abbreviations, synonyms, and common terms
3. If no good match exists, return null for best_match
4. Provide reasoning for your choice

Return JSON only:
{{
  "best_match": "Technology" or null,
  "confidence": 0.85,
  "alternatives": ["Alternative1", "Alternative2"],
  "reasoning": "Brief explanation"
}}
"""
```

**Implementation:**
```python
async def _llm_map_domain_value(
    user_input: str,
    column: str,
    available_values: List[str],
    query_context: str
) -> Dict[str, Any]:
    """Use LLM to map user input to domain value"""
    
    # Build prompt
    prompt = DOMAIN_VALUE_MAPPING_PROMPT.format(
        table=column.split('.')[0],
        column=column.split('.')[1],
        available_values=json.dumps(available_values[:20]),  # Limit for token efficiency
        user_input=user_input,
        query=query_context
    )
    
    # Call LLM (with caching)
    response = await self.llm_client.generate(
        prompt,
        response_format="json",
        cache_key=f"domain_map:{column}:{user_input}"
    )
    
    result = json.loads(response)
    
    # Validate best_match exists in available_values
    if result.get("best_match") and result["best_match"] not in available_values:
        logger.warning(
            f"[llm-map] LLM suggested invalid value: {result['best_match']}"
        )
        result["best_match"] = None
    
    return result
```

**Caching:** Cache LLM results for 1 hour to avoid repeated calls

### Phase 4: Database Optimization (3-5 days)

**Goal:** Use PostgreSQL trigram similarity for better partial matching

**Setup:**
```sql
-- Enable trigram extension
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Add trigram index for fund_type
CREATE INDEX idx_fund_type_trgm 
ON funds USING gin (fund_type gin_trgm_ops);

-- Similar for other dimension columns
CREATE INDEX idx_client_type_trgm 
ON clients USING gin (client_type gin_trgm_ops);
```

**Usage in SQL:**
```sql
-- Option 1: Similarity threshold
SELECT * FROM funds
WHERE similarity(fund_type, 'equity growth') > 0.3
ORDER BY similarity(fund_type, 'equity growth') DESC;

-- Option 2: % operator (shorthand for similarity > 0.3)
SELECT * FROM funds
WHERE fund_type % 'equity growth';
```

**Integration:**
```python
def _build_approximate_filter(self, column: str, user_input: str) -> str:
    """Build approximate matching filter using trigram similarity"""
    
    if self.config.get("use_trigram_similarity", True):
        # PostgreSQL trigram similarity
        return f"similarity({column}, '{user_input}') > 0.3"
    else:
        # Fallback to ILIKE
        return f"{column} ILIKE '%{user_input}%'"
```

### Phase 5: User Feedback Loop (Ongoing)

**Metrics to Track:**
```python
class DomainValueMetrics:
    """Track domain value matching metrics"""
    
    def __init__(self):
        self.total_queries = 0
        self.low_confidence_matches = 0
        self.fuzzy_matches = 0
        self.llm_matches = 0
        self.zero_row_results = 0
        self.user_feedback = []
    
    def log_match(self, method: str, score: float, result_count: int):
        """Log matching results for analysis"""
        ...
```

**Feedback Collection:**
- Add feedback endpoint: `POST /api/feedback`
- Track: query_id, helpful (yes/no), suggested_correction
- Use feedback to improve entity mappings

## Configuration

**File:** `config/domain_value_matching.yaml`

```yaml
domain_value_matching:
  # Score thresholds
  thresholds:
    semantic_good: 0.5        # High confidence, use directly
    semantic_acceptable: 0.3  # Use with warning
    fuzzy_acceptable: 0.6     # Fuzzy match threshold
    llm_acceptable: 0.5       # LLM confidence threshold
  
  # Fallback strategy order
  fallback_strategy:
    order: ["semantic", "fuzzy", "llm", "trigram", "ilike"]
    skip_llm_for_names: true  # Names already use ILIKE
  
  # Fuzzy matching settings
  fuzzy_matching:
    enabled: true
    algorithm: "ratio"  # ratio | partial_ratio | token_sort_ratio
    max_distance: 2     # Max Levenshtein distance
    cache_results: true
  
  # LLM mapping settings
  llm_mapping:
    enabled: true
    max_calls_per_query: 1
    cache_ttl: 3600          # Cache for 1 hour
    max_alternatives: 3
    timeout_ms: 2000         # Fail fast if LLM slow
  
  # Database settings
  database:
    use_trigram_similarity: true
    trigram_threshold: 0.3
  
  # User feedback
  user_feedback:
    show_warnings: true
    show_confidence: true
    suggest_alternatives: true
    max_suggestions: 5
    include_available_values: true  # List all available values
```

## Expected Impact

### Before Implementation

- ❌ 15% of queries return 0 rows due to poor matches
- ❌ No feedback on match quality
- ❌ User doesn't know why query failed
- ❌ Users need exact value names

### After Implementation

- ✅ <5% queries return 0 rows
- ✅ Clear warnings for low confidence matches
- ✅ Alternative suggestions provided
- ✅ Handles typos, abbreviations, variations
- ✅ Better user experience

### Metrics to Monitor

1. **Match Score Distribution:**
   - Track semantic, fuzzy, LLM match scores
   - Identify patterns in low-confidence queries

2. **Zero-Row Query Percentage:**
   - Target: <5% (from current ~15%)
   - Break down by match method

3. **Fuzzy Match Success Rate:**
   - % of fuzzy matches that return results
   - Calibrate threshold based on data

4. **LLM Mapping Accuracy:**
   - Manual review of LLM suggestions
   - User feedback on correctness
   - Refine prompts based on failures

5. **User Satisfaction:**
   - Feedback ratings
   - Query retry rate
   - Time to successful query

## Examples

### Example 1: Typo Handling

```
User: "List equty funds"

Tier 1: Semantic search → score: 0.25 (low)
Tier 2: Fuzzy match → "Equity" (score: 0.83) ✓

Result: WHERE fund_type IN ('Equity Growth', 'Equity Value')
Warning: "Used fuzzy matching: 'equty' → 'Equity'"
```

### Example 2: Abbreviation

```
User: "Show tech funds"

Tier 1: Semantic search → score: 0.15 (low)
Tier 2: Fuzzy match → no good match
Tier 3: LLM mapping → "Technology" (confidence: 0.85) ✓

Result: WHERE fund_type = 'Technology'
Warning: "Interpreted 'tech' as 'Technology'"
```

### Example 3: Unknown Value

```
User: "List cryptocurrency funds"

Tier 1-3: No matches
Tier 4: ILIKE → WHERE fund_type ILIKE '%crypto%'

Result: 0 rows
Warning: {
  "type": "no_match_found",
  "input": "cryptocurrency",
  "column": "funds.fund_type",
  "available_values": ["Equity Growth", "Bond", "Technology", ...],
  "suggestion": "No cryptocurrency funds available. Try one of the listed types."
}
```

## Code Structure

**New Files:**
```
src/reportsmith/query_processing/
  ├── domain_value_matcher.py  (NEW)
  │   ├── DomainValueMatcher
  │   ├── FuzzyMatcher
  │   └── LLMMapper
  └── sql_generator.py  (MODIFIED)
```

**Class Design:**
```python
class DomainValueMatcher:
    """Handle domain value matching with multiple fallback strategies"""
    
    def __init__(self, config, llm_client, kg):
        self.config = config
        self.llm_client = llm_client
        self.kg = kg
        self.fuzzy_matcher = FuzzyMatcher(config)
        self.llm_mapper = LLMMapper(llm_client, config)
        self.metrics = DomainValueMetrics()
    
    def match_value(
        self,
        user_input: str,
        column: str,
        semantic_result: Optional[Dict],
        query_context: str
    ) -> MatchResult:
        """
        Match user input to domain value using multi-tier strategy
        
        Returns:
            MatchResult with value, confidence, method, warnings
        """
        # Implementation of multi-tier strategy
        ...
```

## Testing Strategy

**Unit Tests:**
```python
def test_fuzzy_match_typo():
    matcher = DomainValueMatcher(config)
    result = matcher.match_value(
        user_input="equty",
        column="funds.fund_type",
        semantic_result={"score": 0.2},
        query_context="List equty funds"
    )
    assert result.value in ["Equity Growth", "Equity Value"]
    assert result.method == "fuzzy"
    assert result.confidence > 0.6

def test_llm_abbreviation():
    matcher = DomainValueMatcher(config, llm_client, kg)
    result = matcher.match_value(
        user_input="tech",
        column="funds.fund_type",
        semantic_result={"score": 0.15},
        query_context="Show tech funds"
    )
    assert result.value == "Technology"
    assert result.method == "llm"
    assert result.confidence > 0.5
```

**Integration Tests:**
```python
def test_end_to_end_typo_handling():
    response = query_api("List equty funds")
    assert response.status == 200
    assert "Equity" in response.sql
    assert any(w["type"] == "fuzzy_match_used" for w in response.warnings)
```

## Rollout Plan

1. **Phase 1 (Week 1):** Score detection & warnings
2. **Phase 2 (Week 2-3):** Fuzzy matching
3. **Phase 3 (Week 4-5):** LLM mapping
4. **Phase 4 (Week 6):** Database optimization
5. **Phase 5 (Ongoing):** Metrics & feedback loop

Each phase can be feature-flagged for gradual rollout.

## Success Criteria

- ✅ Zero-row query percentage < 5%
- ✅ 95% of typos handled correctly
- ✅ 90% of abbreviations mapped correctly
- ✅ User feedback rating > 4.0/5.0
- ✅ No performance degradation (< 100ms added latency)

---

**Status:** Proposed  
**Owner:** TBD  
**Last Updated:** 2025-11-08
