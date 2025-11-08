# Domain Value Selection - LLM Domain Enricher (Optional)

## Overview

This document provides the implementation for **OPTIONAL** LLM-based domain value enrichment.

## Key Design Principles

1. **LLM is OPTIONAL** - Not mandatory, disabled by default
2. **No raw user values** - Never use user input as-is when resolution fails
3. **Streamlined context** - No statistics or historical patterns
4. **Business metadata focus** - Table/column/domain knowledge only

## Configuration

```yaml
domain_value_matching:
  # Core strategy
  use_raw_user_value_fallback: false  # ❌ Never use raw values
  
  # LLM enrichment (optional)
  llm_enrichment:
    enabled: false  # Disabled by default
    provider: "gemini"
    model: "gemini-2.5-flash"
    timeout_ms: 3000
    fallback_on_error: true
    
    # When to invoke LLM
    use_for_categories: true
    semantic_threshold: 0.7  # Use LLM if score < 0.7
    
  # Fallback behavior
  show_suggestions_on_failure: true
  max_suggestions: 5
```

## Resolution Flow

```
User Term → Direct Match? 
           → Yes: Use it ✅
           → No ↓

Semantic Search (score > 0.7)?
           → Yes: Use it ✅
           → No ↓

LLM Enabled?
           → Yes: LLM Enrichment ↓
           → No: Skip to Fuzzy ↓

LLM Selection (confidence > 0.7)?
           → Yes: Use LLM result ✅
           → No ↓

Fuzzy Match (score > 0.6)?
           → Yes: Use fuzzy result ✅
           → No ↓

❌ UNRESOLVED - Return with suggestions
```

## Streamlined LLM Prompt Template

```python
DOMAIN_VALUE_SELECTION_PROMPT = """
Task: Select ALL applicable domain values that match the user's intent.

=== USER QUERY CONTEXT ===
Full Query: "{full_query}"
User mentioned term: "{user_term}"
Query Intent: {query_intent}

=== TABLE & COLUMN METADATA ===
Table: {table_name}
Description: {table_description}
Business Context: {table_context}
Domain: {application_domain}

Column: {column_name}
Data Type: {column_data_type}
Description: {column_description}
Business Context: {column_context}
Is Dimension: {is_dimension}
Cardinality: {cardinality}

=== AVAILABLE VALUES ===
Total: {value_count}
Values:
{available_values_json}

=== BUSINESS RULES ===
{business_rules}

=== DOMAIN KNOWLEDGE ===
Abbreviations:
{abbreviations}

Synonyms:
{synonyms}

Hierarchies:
{hierarchies}

=== ENTITY MAPPINGS ===
{entity_mapping_context}

=== INSTRUCTIONS ===
1. Analyze the user's full query to understand intent
2. Consider business context and domain knowledge
3. Select ALL matching values using these strategies:
   - Exact: "Bond" → ["Bond"]
   - Category: "equity" → ["Equity Growth", "Equity Value"]
   - Abbreviation: "tech" → ["Technology"]
   - Synonym: "stocks" → equity types
   - Case-insensitive

4. Guidelines:
   - Category terms → ALL subtypes
   - Specific terms → Exact match only
   - Prefer INCLUSIVE (more rather than less)
   - If NO match → Return empty array
   
5. Do NOT:
   - Invent values not in list
   - Return unrelated values
   - Ignore query context

=== OUTPUT FORMAT ===
Return JSON only:
{{
  "selected_values": ["value1", "value2"],
  "confidence": 0.95,
  "reasoning": "Explanation with business context",
  "match_type": "exact | partial_category | abbreviation | synonym"
}}
"""
```

## Implementation Classes

### 1. UnresolvedDomainValue

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class UnresolvedDomainValue:
    """Represents a domain value that couldn't be resolved"""
    user_term: str
    column: str
    table: Optional[str] = None
    suggestions: List[str] = None
    resolution_strategy: str = "user_clarification_needed"
    message: Optional[str] = None
    
    def __post_init__(self):
        if self.message is None:
            suggestions_str = ", ".join(self.suggestions[:5]) if self.suggestions else "none"
            self.message = (
                f"Could not match '{self.user_term}' to {self.table}.{self.column}. "
                f"Suggestions: {suggestions_str}"
            )
```

### 2. DomainValueResolver (Core)

```python
class DomainValueResolver:
    """
    Resolves user domain values to actual database values.
    NEVER uses raw user input as fallback.
    """
    
    def __init__(self, config: dict, kg_client, llm_client=None):
        self.config = config
        self.kg = kg_client
        self.llm = llm_client
        self.llm_enabled = config.get("llm_enrichment", {}).get("enabled", False)
        self.semantic_threshold = config.get("llm_enrichment", {}).get("semantic_threshold", 0.7)
        
    def resolve(
        self, 
        user_term: str, 
        column: str, 
        table: str,
        query_context: dict
    ) -> Union[List[str], UnresolvedDomainValue]:
        """
        Resolve user term to database values.
        Returns list of values or UnresolvedDomainValue.
        NEVER returns raw user_term.
        """
        
        # Get available values from KG
        available_values = self._get_available_values(table, column)
        if not available_values:
            return UnresolvedDomainValue(
                user_term=user_term,
                column=column,
                table=table,
                resolution_strategy="no_domain_values_found"
            )
        
        # Tier 1: Direct match
        direct_match = self._direct_match(user_term, available_values)
        if direct_match:
            logger.info(f"[domain-value] Direct match: {user_term} → {direct_match}")
            return [direct_match]
        
        # Tier 2: Semantic search
        semantic_result = self._semantic_search(user_term, table, column)
        if semantic_result and semantic_result.score >= self.semantic_threshold:
            logger.info(f"[domain-value] Semantic match: {user_term} → {semantic_result.value} (score={semantic_result.score:.2f})")
            return [semantic_result.value]
        
        # Tier 3: LLM enrichment (if enabled)
        if self.llm_enabled and self.llm:
            llm_result = self._llm_enrichment(
                user_term=user_term,
                table=table,
                column=column,
                available_values=available_values,
                query_context=query_context
            )
            if llm_result and llm_result.confidence >= 0.7:
                logger.info(f"[domain-value] LLM match: {user_term} → {llm_result.selected_values} (confidence={llm_result.confidence:.2f})")
                return llm_result.selected_values
        
        # Tier 4: Fuzzy matching
        fuzzy_result = self._fuzzy_match(user_term, available_values)
        if fuzzy_result and fuzzy_result.score >= 0.6:
            logger.info(f"[domain-value] Fuzzy match: {user_term} → {fuzzy_result.value} (score={fuzzy_result.score:.2f})")
            return [fuzzy_result.value]
        
        # Tier 5: UNRESOLVED - Get suggestions
        suggestions = self._get_suggestions(user_term, available_values, top_n=5)
        logger.warning(f"[domain-value] UNRESOLVED: {user_term} for {table}.{column}")
        
        return UnresolvedDomainValue(
            user_term=user_term,
            column=column,
            table=table,
            suggestions=suggestions,
            resolution_strategy="no_match_found"
        )
    
    def _direct_match(self, user_term: str, available_values: List[str]) -> Optional[str]:
        """Case-insensitive exact match"""
        user_lower = user_term.lower()
        for value in available_values:
            if value.lower() == user_lower:
                return value
        return None
    
    def _get_suggestions(self, user_term: str, available_values: List[str], top_n: int = 5) -> List[str]:
        """Get closest matching suggestions using fuzzy matching"""
        from difflib import SequenceMatcher
        
        scores = [
            (value, SequenceMatcher(None, user_term.lower(), value.lower()).ratio())
            for value in available_values
        ]
        scores.sort(key=lambda x: x[1], reverse=True)
        return [value for value, score in scores[:top_n]]
```

### 3. OptionalLLMEnricher

```python
class OptionalLLMEnricher:
    """
    Optional LLM-based domain value enrichment.
    Only used when enabled in config.
    """
    
    def __init__(self, llm_client, config: dict):
        self.llm = llm_client
        self.timeout_ms = config.get("timeout_ms", 3000)
        self.fallback_on_error = config.get("fallback_on_error", True)
        
    def enrich(
        self,
        user_term: str,
        table: str,
        column: str,
        available_values: List[str],
        query_context: dict
    ) -> Optional[LLMEnrichmentResult]:
        """
        Use LLM to select applicable domain values.
        Returns None if LLM fails and fallback_on_error=True.
        """
        try:
            # Gather metadata context
            context = self._gather_context(table, column, available_values, query_context)
            
            # Build prompt
            prompt = self._build_prompt(user_term, context)
            
            # Call LLM
            response = self.llm.generate(
                prompt=prompt,
                timeout_ms=self.timeout_ms,
                response_format="json"
            )
            
            # Parse response
            result = self._parse_response(response)
            return result
            
        except Exception as e:
            logger.error(f"[llm-enrichment] Error: {e}")
            if self.fallback_on_error:
                return None
            raise
    
    def _gather_context(self, table: str, column: str, available_values: List[str], query_context: dict) -> dict:
        """
        Gather metadata context (NO stats or historical patterns).
        """
        return {
            "table_metadata": self._get_table_metadata(table),
            "column_metadata": self._get_column_metadata(table, column),
            "available_values": available_values,
            "business_rules": self._get_business_rules(table, column),
            "domain_knowledge": self._get_domain_knowledge(table, column),
            "entity_mappings": self._get_entity_mappings(),
            "query_context": query_context
        }
```

## Key Differences from Original

| Aspect | Original | Refined |
|--------|----------|---------|
| LLM Usage | Mandatory/Primary | **Optional/Enricher** |
| Raw User Value | Used as fallback | **NEVER used** ❌ |
| Statistics | Included | **Removed** |
| Historical Patterns | Included | **Removed** |
| Context Size | 1500-2000 tokens | **~800-1000 tokens** |
| Default State | Enabled | **Disabled** |
| Failure Behavior | Use raw value | **Return suggestions** |

## Usage Example

```python
# Configuration
config = {
    "use_raw_user_value_fallback": False,  # ❌ Critical!
    "llm_enrichment": {
        "enabled": False,  # Optional - start disabled
        "provider": "gemini",
        "timeout_ms": 3000
    }
}

# Resolve domain value
resolver = DomainValueResolver(config, kg_client, llm_client)
result = resolver.resolve(
    user_term="equity",
    column="fund_type", 
    table="funds",
    query_context={"query": "List equity funds", "intent": "aggregation"}
)

if isinstance(result, UnresolvedDomainValue):
    # Show suggestions to user
    print(f"Error: {result.message}")
    print(f"Suggestions: {', '.join(result.suggestions)}")
else:
    # Use resolved values
    print(f"Resolved to: {result}")
    # WHERE fund_type IN ('Equity Growth', 'Equity Value')
```
   - **Category terms** (e.g., "equity"): Include ALL matching subtypes
   - **Specific terms** (e.g., "Equity Growth"): Match only that value
   - **Ambiguous terms**: Prefer being INCLUSIVE based on query intent
   - **Aggregation queries**: Broader selection often appropriate
   - **Ranking queries**: May need more specific selection
   - **No matches**: Return empty array

4. **Confidence Assessment:**
   - 0.9-1.0: Exact or obvious match
   - 0.7-0.9: Clear partial/category match
   - 0.5-0.7: Reasonable match based on synonyms
   - 0.3-0.5: Contextual match with uncertainty
   - 0.0-0.3: Low confidence, may need fallback

5. **Validation:**
   - ONLY return values from the provided list
   - Do NOT invent new values
   - Check against business rules if provided
   - Consider dependencies and constraints

=== OUTPUT FORMAT ===
Return ONLY valid JSON (no markdown, no explanations outside JSON):

## Summary: Key Changes

### What Was Removed ❌
- **Value statistics** (frequency distribution, percentages)
- **Historical patterns** (query patterns, combinations, examples)
- **Usage tracking** (typical combinations, example queries)

### What Was Kept ✅
- **Table metadata** (description, business purpose, domain)
- **Column metadata** (type, description, business context, cardinality)
- **Business rules** (constraints, validations, dependencies)
- **Domain knowledge** (abbreviations, synonyms, hierarchies)
- **Entity mappings** (term mappings, canonical names, aliases)

### Architecture Changes

| Aspect | Old Design | New Design |
|--------|-----------|------------|
| **LLM Role** | Primary/Mandatory | **Optional Enricher** |
| **Raw Values** | Used as fallback | **NEVER used** |
| **Statistics** | Included | **Removed** |
| **Patterns** | Included | **Removed** |
| **Context Tokens** | ~1500-2000 | **~800-1000** |
| **Default State** | Enabled | **Disabled** |
| **On Failure** | Use raw value | **Return suggestions** |

## Configuration Example

```yaml
domain_value_matching:
  # Critical: Never use raw user values
  use_raw_user_value_fallback: false  # ❌
  
  # Show suggestions when resolution fails
  show_suggestions_on_failure: true
  max_suggestions: 5
  
  # LLM enrichment (optional)
  llm_enrichment:
    enabled: false  # Start disabled
    provider: "gemini"
    model: "gemini-2.5-flash"
    timeout_ms: 3000
    fallback_on_error: true
    semantic_threshold: 0.7
```

## Decision Flow

```
┌─────────────────────────────────────┐
│ User provides domain value          │
│ Example: "equity"                   │
└──────────────┬──────────────────────┘
               │
               ▼
        Direct Match?
               │
       ┌───────┴───────┐
       │ Yes           │ No
       ▼               ▼
    Use it ✅    Semantic Search
                       │
                ┌──────┴──────┐
                │ Score > 0.7  │ Score < 0.7
                ▼              ▼
             Use it ✅    LLM Enabled?
                              │
                       ┌──────┴──────┐
                       │ Yes         │ No
                       ▼             ▼
                 LLM Enrichment    Fuzzy
                       │             Match
                ┌──────┴──────┐       │
                │ Conf > 0.7  │<0.7 ┌─┴─┐
                ▼             ▼     │>0.6│
             Use LLM ✅     Fuzzy  ▼  ▼
                            Match  Use ✅
                              │
                       ┌──────┴──────┐
                       │ Score > 0.6  │ < 0.6
                       ▼              ▼
                    Use it ✅   UNRESOLVED ❌
                              Return suggestions
```

## Expected Behavior Examples

### Example 1: Direct Match
```
User: "List Bond funds"
Term: "Bond"
Available: ["Bond", "Equity Growth", "Technology"]

Resolution: Direct match ✅
Result: ["Bond"]
Method: direct_match
```

### Example 2: Semantic Match (High Confidence)
```
User: "Show tech funds"
Term: "tech"
Available: ["Technology", "Bond", "Equity"]

Resolution: Semantic score 0.88 ✅
Result: ["Technology"]
Method: semantic_search
```

### Example 3: LLM Enrichment (Low Semantic Confidence)
```
User: "List equity funds"
Term: "equity"
Available: ["Equity Growth", "Equity Value", "Bond"]
Semantic: 0.45 (too low)

LLM Enabled: Yes
LLM Result: ["Equity Growth", "Equity Value"]
LLM Confidence: 0.92 ✅

Resolution: LLM enrichment ✅
Result: ["Equity Growth", "Equity Value"]
Method: llm_enrichment
```

### Example 4: No LLM, Fuzzy Fallback
```
User: "Show equty funds"  (typo)
Term: "equty"
Available: ["Equity Growth", "Equity Value", "Bond"]
Semantic: 0.35 (too low)

LLM Enabled: No (disabled)

Fuzzy Match: "Equity Growth" (score 0.85) ✅
Resolution: Fuzzy match ✅
Result: ["Equity Growth"]
Method: fuzzy_match
```

### Example 5: Unresolved (No Match)
```
User: "List cryptocurrency funds"
Term: "cryptocurrency"
Available: ["Equity Growth", "Bond", "Technology"]
Semantic: 0.15 (too low)
LLM: Enabled
LLM Result: [] (no match, confidence 0.0)
Fuzzy: < 0.6 (no good match)

Resolution: UNRESOLVED ❌
Result: UnresolvedDomainValue(
  user_term="cryptocurrency",
  column="fund_type",
  table="funds",
  suggestions=["Technology", "Equity Growth", "Bond"],
  message="Could not match 'cryptocurrency' to funds.fund_type. 
           Available: Technology, Equity Growth, Bond, ..."
)
Method: unresolved

❌ OLD: WHERE fund_type = 'cryptocurrency' → 0 rows
✅ NEW: Return suggestions, ask user to clarify
```

## Implementation Priority

### Phase 1: Stop Using Raw Values (CRITICAL - Day 1)
- [x] Remove raw value fallback
- [x] Add UnresolvedDomainValue class
- [x] Return suggestions on failure
- [x] Update configuration

### Phase 2: Make LLM Optional (Day 2-3)
- [x] Add llm_enrichment config
- [x] Default to disabled
- [x] Implement OptionalLLMEnricher
- [x] Graceful fallback on LLM errors

### Phase 3: Streamline Context (Day 2-3)
- [x] Remove statistics gathering
- [x] Remove historical patterns
- [x] Keep business metadata only
- [x] Reduce token usage 50%

## Testing Checklist

- [ ] Test with LLM disabled (most common case)
- [ ] Test direct match (case-insensitive)
- [ ] Test semantic match (high confidence)
- [ ] Test LLM enrichment (when enabled)
- [ ] Test fuzzy matching
- [ ] Test unresolved with suggestions
- [ ] Verify raw value NEVER used
- [ ] Test LLM timeout/error handling
- [ ] Test configuration changes
- [ ] Test with empty available_values

## Migration Notes

**For existing deployments:**
1. Set `use_raw_user_value_fallback: false` immediately
2. Keep `llm_enrichment.enabled: false` initially
3. Monitor unresolved rate
4. Enable LLM selectively if needed
5. Tune semantic_threshold based on data

**Breaking Changes:**
- Queries with poorly matching domain values will now return suggestions instead of 0 rows
- This is GOOD - users get helpful feedback instead of empty results

## Conclusion

This streamlined approach:
- ✅ **Safer** - Never uses raw user values
- ✅ **More flexible** - LLM is optional
- ✅ **More efficient** - 50% fewer tokens
- ✅ **Better UX** - Suggestions on failure
- ✅ **Configurable** - Enable LLM per deployment
- ✅ **Focused** - Business metadata only

The LLM acts as an **optional enricher**, not a mandatory component. Core resolution works without it.
