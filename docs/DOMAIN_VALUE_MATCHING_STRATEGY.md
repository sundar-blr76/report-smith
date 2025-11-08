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

**Key Insight:** For domain values, use LLM with full context and complete value list as the PRIMARY strategy, not fallback.

```
┌─────────────────────────────────────────┐
│  User Input: "equity"                    │
│  Query Context: "List equity funds"      │
└──────────────┬──────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│ Tier 1: Semantic Search (Quick Filter)       │
│ - Embedding similarity                        │
│ - Score threshold: 0.3                        │
│ Result: "Equity Growth" (score: 0.28)        │
│ Status: ⚠️  Below threshold → Need LLM       │
└──────────────┬───────────────────────────────┘
               │ score < 0.5 (needs verification)
               ▼
┌──────────────────────────────────────────────┐
│ Tier 2: LLM-Based Multi-Selection (PRIMARY)  │
│ Input:                                        │
│   - User query: "List equity funds"          │
│   - User term: "equity"                      │
│   - Column: funds.fund_type                  │
│   - ALL available values:                    │
│     ["Equity Growth", "Equity Value",        │
│      "Bond", "Technology", "REIT", ...]      │
│                                              │
│ LLM returns:                                 │
│   - ["Equity Growth", "Equity Value"]        │
│   - Confidence: 0.95                         │
│   - Reasoning: "'equity' matches both types" │
│                                              │
│ Result: Multiple values selected ✓           │
└──────────────┬───────────────────────────────┘
               │ LLM unavailable or low confidence
               ▼
┌──────────────────────────────────────────────┐
│ Tier 3: Fuzzy String Matching (Fallback)     │
│ - Levenshtein distance (typos)               │
│ - Token matching (word order)                │
│ Examples:                                     │
│   "equty" → "Equity" (distance=1)            │
│   "growth equity" → "Equity Growth" (tokens) │
└──────────────┬───────────────────────────────┘
               │ fuzzy_score < 0.6
               ▼
┌──────────────────────────────────────────────┐
│ Tier 4: Approximate Matching (Last Resort)   │
│ - ILIKE: WHERE col ILIKE '%equity%'          │
│ - Trigram similarity (PostgreSQL pg_trgm)    │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│ Tier 5: User Feedback (Always)               │
│ - Show confidence & method used              │
│ - Show which values were selected            │
│ - Suggest alternatives if uncertain          │
└───────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: LLM-Based Multi-Selection (PRIMARY - 2-3 days)

**Goal:** Use LLM to select ALL applicable domain values from complete list

**Why LLM First:**
- ✅ Understands context better than any algorithm
- ✅ Can select MULTIPLE applicable values (not just one)
- ✅ Handles synonyms, abbreviations, partial matches
- ✅ Reasoning makes results explainable
- ✅ One call handles all cases

**LLM Prompt Template:**
```python
DOMAIN_VALUE_SELECTION_PROMPT = """
Task: Select ALL applicable domain values that match the user's intent.

User Query: "{full_query}"
User mentioned: "{user_term}"
Column: {table}.{column}
Column description: {column_description}

ALL Available Values:
{available_values_json}

Instructions:
1. Analyze the user's intent from the full query context
2. Select ALL values that match the user's intent
3. Consider:
   - Exact matches
   - Partial matches (e.g., "equity" matches "Equity Growth" AND "Equity Value")
   - Abbreviations (e.g., "tech" → "Technology")
   - Synonyms (e.g., "stocks" → "Equity Growth", "Equity Value")
   - Context clues from the full query
4. If uncertain, prefer being INCLUSIVE (select more rather than less)
5. If NO values match, return empty array

Return JSON only:
{{
  "selected_values": ["Equity Growth", "Equity Value"],
  "confidence": 0.95,
  "reasoning": "'equity' is a partial match for both Equity Growth and Equity Value fund types",
  "excluded_count": 5,
  "excluded_examples": ["Bond", "Technology", "REIT"]
}}
"""
```

**Example Scenarios:**

**Scenario 1: Partial Match (Multiple Results)**
```
Query: "List equity funds"
User term: "equity"
Available: ["Equity Growth", "Equity Value", "Bond", "Technology", "REIT", "Money Market"]

LLM Response:
{
  "selected_values": ["Equity Growth", "Equity Value"],
  "confidence": 0.95,
  "reasoning": "'equity' is a category that includes both Equity Growth and Equity Value types"
}

Generated SQL:
WHERE fund_type IN ('Equity Growth', 'Equity Value')
```

**Scenario 2: Abbreviation**
```
Query: "Show tech funds"
User term: "tech"
Available: ["Equity Growth", "Bond", "Technology", "REIT"]

LLM Response:
{
  "selected_values": ["Technology"],
  "confidence": 0.90,
  "reasoning": "'tech' is a common abbreviation for Technology"
}

Generated SQL:
WHERE fund_type = 'Technology'
```

**Scenario 3: Synonym with Multiple Matches**
```
Query: "List stock funds"
User term: "stock"
Available: ["Equity Growth", "Equity Value", "Bond", "Technology"]

LLM Response:
{
  "selected_values": ["Equity Growth", "Equity Value"],
  "confidence": 0.85,
  "reasoning": "'stock' is a synonym for equity investments, matching both Equity Growth and Equity Value"
}

Generated SQL:
WHERE fund_type IN ('Equity Growth', 'Equity Value')
```

**Scenario 4: Context-Aware Selection**
```
Query: "Show growth-oriented funds"
User term: "growth"
Available: ["Equity Growth", "Equity Value", "Bond", "Technology Growth"]

LLM Response:
{
  "selected_values": ["Equity Growth", "Technology Growth"],
  "confidence": 0.88,
  "reasoning": "'growth-oriented' suggests growth strategies, matching Equity Growth and Technology Growth"
}

Generated SQL:
WHERE fund_type IN ('Equity Growth', 'Technology Growth')
```

**Scenario 5: No Match**
```
Query: "List cryptocurrency funds"
User term: "cryptocurrency"
Available: ["Equity Growth", "Bond", "Technology", "REIT"]

LLM Response:
{
  "selected_values": [],
  "confidence": 0.95,
  "reasoning": "No fund types match cryptocurrency. Available types are equity, bond, technology, and REIT based."
}

Fallback: Use ILIKE or inform user
```

**Implementation:**
```python
async def _llm_select_domain_values(
    user_query: str,
    user_term: str,
    column: str,
    available_values: List[str],
    column_metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Use LLM to select ALL applicable domain values
    
    Args:
        user_query: Full user question for context
        user_term: Specific term user mentioned (e.g., "equity")
        column: Table.column (e.g., "funds.fund_type")
        available_values: Complete list of possible values
        column_metadata: Column description, context, etc.
    
    Returns:
        {
            "selected_values": ["Value1", "Value2"],
            "confidence": 0.95,
            "reasoning": "explanation",
            "method": "llm_multi_select"
        }
    """
    # Build prompt
    table, col = column.split('.')
    prompt = DOMAIN_VALUE_SELECTION_PROMPT.format(
        full_query=user_query,
        user_term=user_term,
        table=table,
        column=col,
        column_description=column_metadata.get('description', ''),
        available_values_json=json.dumps(available_values, indent=2)
    )
    
    # Call LLM with caching
    cache_key = f"domain_select:{column}:{user_term}:{hash(tuple(available_values))}"
    
    try:
        response = await self.llm_client.generate(
            prompt,
            response_format="json",
            cache_key=cache_key,
            cache_ttl=3600,  # Cache for 1 hour
            timeout_ms=3000   # Fail fast if slow
        )
        
        result = json.loads(response)
        
        # Validate all selected values exist in available_values
        valid_values = [
            v for v in result.get("selected_values", [])
            if v in available_values
        ]
        
        if not valid_values:
            logger.warning(
                f"[llm-select] LLM returned no valid values for '{user_term}' "
                f"in {column}"
            )
            return None
        
        # Log the selection
        logger.info(
            f"[llm-select] '{user_term}' → {valid_values} "
            f"(confidence={result.get('confidence', 0):.2f}) "
            f"Reasoning: {result.get('reasoning', '')[:100]}"
        )
        
        return {
            "selected_values": valid_values,
            "confidence": result.get("confidence", 0.5),
            "reasoning": result.get("reasoning", ""),
            "method": "llm_multi_select"
        }
        
    except Exception as e:
        logger.error(f"[llm-select] Failed to call LLM: {e}")
        return None
```

**Integration with SQL Generator:**
```python
# In sql_generator.py - domain value processing

for ent in dimension_entities:
    table = ent.get("table")
    column = ent.get("column")
    user_term = ent.get("text")
    
    # Get semantic match score
    top_match = ent.get("top_match", {})
    semantic_score = top_match.get("score", 0.0)
    
    # If semantic score is low or ambiguous, use LLM multi-select
    if semantic_score < 0.5:
        # Fetch all available values for this column
        available_values = self._get_domain_values(table, column)
        
        # Call LLM to select applicable values
        llm_result = await self._llm_select_domain_values(
            user_query=self.state.question,
            user_term=user_term,
            column=f"{table}.{column}",
            available_values=available_values,
            column_metadata=self.kg.get_column_metadata(table, column)
        )
        
        if llm_result and llm_result["selected_values"]:
            # Use LLM-selected values
            selected_values = llm_result["selected_values"]
            
            # Add to dimension groups (will create IN clause if multiple)
            for val in selected_values:
                safe_value = val.replace("'", "''")
                dim_groups[key].append(safe_value)
            
            logger.info(
                f"[sql-gen][where] LLM selected {len(selected_values)} value(s) "
                f"for '{user_term}': {selected_values}"
            )
            
            # Add to warnings for transparency
            if llm_result["confidence"] < 0.8:
                warnings.append({
                    "type": "llm_selection",
                    "user_term": user_term,
                    "selected_values": selected_values,
                    "confidence": llm_result["confidence"],
                    "reasoning": llm_result["reasoning"]
                })
            
            continue  # Skip other matching strategies
    
    # Fallback to existing logic (semantic matches, fuzzy, etc.)
    ...
```

**Caching Strategy:**
- Cache LLM results by (column, user_term, available_values_hash)
- TTL: 1 hour (values don't change frequently)
- Invalidate cache when domain values are updated

**Performance Considerations:**
- First call: ~1-2 seconds (LLM latency)
- Cached calls: <10ms
- Parallel processing: Can call LLM for multiple columns simultaneously
- Timeout: 3 seconds max (fallback to fuzzy match)

### Phase 2: Score Detection & Warnings (1 day)

**Goal:** Detect and warn about LLM selections for transparency

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

### Phase 3: Fuzzy Matching (Fallback - 2-3 days)

**Goal:** Fallback when LLM unavailable or fails

**Use Cases:**
- LLM timeout or unavailable
- LLM returns low confidence (< 0.3)
- Simple typos that don't need LLM

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

### Phase 4: Database Optimization (2-3 days)

**Goal:** Efficient domain value storage and retrieval

**Tasks:**
1. **Cache Domain Values:**
```python
class DomainValueCache:
    """Cache all available values per column for fast LLM access"""
    
    def __init__(self, kg):
        self.kg = kg
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour
    
    async def get_values(self, table: str, column: str) -> List[str]:
        """Get all available values for a column"""
        key = f"{table}.{column}"
        
        if key in self.cache:
            cached_at, values = self.cache[key]
            if time.time() - cached_at < self.cache_ttl:
                return values
        
        # Query database for distinct values
        query = f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL ORDER BY {column}"
        values = await self.kg.execute_query(query)
        
        self.cache[key] = (time.time(), values)
        return values
```

2. **Add Trigram Indexes (for fuzzy fallback):**
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
