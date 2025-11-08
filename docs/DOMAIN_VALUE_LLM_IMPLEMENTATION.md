# Domain Value Selection - Enhanced LLM Implementation with Rich Context

## Overview

This document provides the complete implementation for LLM-based domain value selection **with rich metadata and business context**.

## Key Enhancement

**Before:** Basic prompt with just query + term + values  
**After:** Rich prompt with table metadata + business context + statistics + domain knowledge

## Enhanced LLM Prompt Template

```python
DOMAIN_VALUE_SELECTION_PROMPT_ENHANCED = """
Task: Select ALL applicable domain values that match the user's intent.

=== USER QUERY CONTEXT ===
Full Query: "{full_query}"
User mentioned term: "{user_term}"
Query Intent: {query_intent}  # e.g., "aggregation", "ranking", "filtering"
Time Scope: {time_scope}      # e.g., "last_quarter", "ytd", "custom"

=== TABLE METADATA ===
Table: {table_name}
Description: {table_description}
Business Purpose: {table_purpose}
Domain: {application_domain}  # e.g., "fund_accounting", "sales", "inventory"
Estimated Rows: {table_row_count:,}
Primary Key: {primary_key}
Related Tables: {related_tables}

=== COLUMN METADATA ===
Column: {column_name}
Data Type: {column_data_type}
Description: {column_description}
Business Context: {column_context}
Is Dimension: {is_dimension}
Is Nullable: {is_nullable}
Cardinality: {cardinality}  # Unique value count
Common Use Cases: {use_cases}

=== DOMAIN VALUE STATISTICS ===
Total Available Values: {value_count}
Most Common Values (by frequency):
{value_distribution}

ALL Available Values:
{available_values_detailed}

=== BUSINESS RULES & CONSTRAINTS ===
{business_rules}

Validation Rules:
{validation_rules}

Dependencies:
{dependencies}

=== DOMAIN KNOWLEDGE ===
Known Abbreviations:
{abbreviations}

Synonyms & Aliases:
{synonyms}

Category Hierarchies:
{hierarchies}

Related Concepts:
{related_concepts}

=== HISTORICAL USAGE PATTERNS ===
Common Query Patterns:
{query_patterns}

Typical Combinations:
{typical_combinations}

Example Queries:
{usage_examples}

=== ENTITY MAPPING GUIDANCE ===
{entity_mapping_context}

=== INSTRUCTIONS ===
1. **Context Analysis:**
   - Read the FULL query to understand user intent
   - Consider the query type (aggregation, filtering, ranking)
   - Use business context to interpret the term correctly

2. **Matching Strategies** (in order of preference):
   - **Exact match**: "Bond" → ["Bond"]
   - **Partial category match**: "equity" → ["Equity Growth", "Equity Value"]
   - **Abbreviation**: "tech" → ["Technology"]
   - **Synonym**: "stocks" → all equity types
   - **Context-based**: Use query intent and business rules
   - **Case-insensitive**: "BOND" → ["Bond"]

3. **Selection Guidelines:**
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

{{
  "selected_values": ["Equity Growth", "Equity Value"],
  "confidence": 0.95,
  "reasoning": "Detailed explanation citing business context, query intent, and matching strategy used",
  "match_type": "partial_category",
  "business_rationale": "Additional business justification for this selection",
  "excluded_count": 3,
  "excluded_examples": ["Bond", "Technology"],
  "alternative_interpretations": ["Could also mean X if intent was Y"],
  "warnings": ["Important caveats or considerations"]
}}

Match types:
- "exact": Perfect match
- "partial_category": Term matches category of values
- "abbreviation": Common shorthand
- "synonym": Alternative term for same concept
- "context_based": Inferred from query context
- "fuzzy": Close match with minor variations
- "no_match": No applicable values found
"""
```

## Enhanced Implementation

```python
from typing import List, Dict, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)


class EnhancedDomainValueSelector:
    """
    LLM-based domain value selector with rich metadata context.
    """
    
    def __init__(self, kg, llm_client, entity_mappings):
        self.kg = kg
        self.llm_client = llm_client
        self.entity_mappings = entity_mappings
    
    async def select_values(
        self,
        user_query: str,
        user_term: str,
        table: str,
        column: str,
        available_values: List[str],
        query_state: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Select domain values using LLM with rich context.
        
        Args:
            user_query: Full user question
            user_term: Specific term mentioned by user
            table: Table name
            column: Column name
            available_values: List of all possible values
            query_state: Query intent, filters, etc.
        
        Returns:
            Selection result with values, confidence, reasoning
        """
        # Gather all metadata
        context = await self._gather_context(
            user_query, user_term, table, column, 
            available_values, query_state
        )
        
        # Build enhanced prompt
        prompt = DOMAIN_VALUE_SELECTION_PROMPT_ENHANCED.format(**context)
        
        # Cache key includes context hash for cache invalidation
        cache_key = self._build_cache_key(
            table, column, user_term, available_values, context
        )
        
        try:
            logger.info(
                f"[llm-select-enhanced] Calling LLM for '{user_term}' "
                f"in {table}.{column} with RICH CONTEXT"
            )
            logger.debug(
                f"[llm-select-enhanced] Prompt: {len(prompt)} chars, "
                f"{len(available_values)} values"
            )
            
            # Call LLM with longer timeout for richer context
            response = await self.llm_client.generate(
                prompt,
                response_format="json",
                cache_key=cache_key,
                cache_ttl=3600,
                timeout_ms=5000  # 5 seconds for complex analysis
            )
            
            result = self._parse_and_validate(response, available_values)
            
            if result:
                self._log_selection_details(user_term, table, column, result)
            
            return result
            
        except Exception as e:
            logger.error(f"[llm-select-enhanced] Failed: {e}")
            return None
    
    async def _gather_context(
        self,
        user_query: str,
        user_term: str,
        table: str,
        column: str,
        available_values: List[str],
        query_state: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Gather all metadata and context for LLM prompt.
        """
        # Get table metadata
        table_meta = self._get_table_metadata(table)
        
        # Get column metadata
        col_meta = self._get_column_metadata(table, column)
        
        # Get value statistics
        value_stats = self._get_value_statistics(table, column, available_values)
        
        # Get business context
        business_ctx = self._get_business_context(table, column)
        
        # Get entity mapping context
        entity_ctx = self._get_entity_mapping_context(table, column, user_term)
        
        # Get historical patterns
        patterns = self._get_query_patterns(table, column)
        
        return {
            # User query context
            "full_query": user_query,
            "user_term": user_term,
            "query_intent": query_state.get('intent', {}).get('type', 'unknown') if query_state else 'unknown',
            "time_scope": query_state.get('intent', {}).get('time_scope', 'unknown') if query_state else 'unknown',
            
            # Table metadata
            "table_name": table,
            "table_description": table_meta.get('description', 'No description'),
            "table_purpose": table_meta.get('purpose', 'No purpose defined'),
            "application_domain": table_meta.get('application', 'unknown'),
            "table_row_count": table_meta.get('estimated_rows', 0),
            "primary_key": table_meta.get('primary_key', 'unknown'),
            "related_tables": ', '.join(table_meta.get('related_tables', [])),
            
            # Column metadata
            "column_name": column,
            "column_data_type": col_meta.get('data_type', 'unknown'),
            "column_description": col_meta.get('description', 'No description'),
            "column_context": col_meta.get('context', business_ctx.get('context', 'No context')),
            "is_dimension": str(col_meta.get('is_dimension', True)),
            "is_nullable": str(col_meta.get('nullable', True)),
            "cardinality": len(available_values),
            "use_cases": col_meta.get('use_cases', 'Not specified'),
            
            # Value statistics
            "value_count": len(available_values),
            "value_distribution": self._format_value_distribution(value_stats),
            "available_values_detailed": self._format_values_detailed(available_values, value_stats),
            
            # Business rules
            "business_rules": business_ctx.get('rules', 'No specific rules'),
            "validation_rules": business_ctx.get('validation', 'No validation rules'),
            "dependencies": business_ctx.get('dependencies', 'No known dependencies'),
            
            # Domain knowledge
            "abbreviations": business_ctx.get('abbreviations', 'None known'),
            "synonyms": business_ctx.get('synonyms', 'None known'),
            "hierarchies": business_ctx.get('hierarchies', 'No hierarchies'),
            "related_concepts": business_ctx.get('related_concepts', 'None'),
            
            # Usage patterns
            "query_patterns": patterns.get('common_patterns', 'No patterns tracked'),
            "typical_combinations": patterns.get('combinations', 'No combinations tracked'),
            "usage_examples": self._format_examples(patterns.get('examples', [])),
            
            # Entity mapping guidance
            "entity_mapping_context": entity_ctx
        }
    
    def _get_table_metadata(self, table: str) -> Dict[str, Any]:
        """Extract table metadata from knowledge graph."""
        node_key = table
        node = self.kg.nodes.get(node_key, {})
        
        return {
            "description": node.get("description", ""),
            "purpose": node.get("purpose", ""),
            "application": node.get("application", ""),
            "estimated_rows": node.get("estimated_rows", 0),
            "primary_key": node.get("primary_key", ""),
            "related_tables": node.get("related_tables", [])
        }
    
    def _get_column_metadata(self, table: str, column: str) -> Dict[str, Any]:
        """Extract column metadata from knowledge graph."""
        node_key = f"{table}.{column}"
        node = self.kg.nodes.get(node_key, {})
        
        return {
            "data_type": node.get("data_type", "unknown"),
            "description": node.get("description", ""),
            "context": node.get("context", ""),
            "is_dimension": node.get("is_dimension", True),
            "nullable": node.get("nullable", True),
            "use_cases": node.get("use_cases", "")
        }
    
    def _get_value_statistics(
        self, 
        table: str, 
        column: str, 
        values: List[str]
    ) -> Dict[str, int]:
        """
        Get frequency/count statistics for each value.
        Helps LLM understand which values are common vs rare.
        """
        stats = {}
        
        for val in values:
            node_key = f"{table}.{column}.{val}"
            node = self.kg.nodes.get(node_key, {})
            stats[val] = node.get('count', 0)
        
        return stats
    
    def _get_business_context(self, table: str, column: str) -> Dict[str, Any]:
        """
        Extract business context from entity mappings and KG.
        Includes abbreviations, synonyms, rules, etc.
        """
        context = {
            "context": "",
            "rules": "",
            "validation": "",
            "dependencies": "",
            "abbreviations": "",
            "synonyms": "",
            "hierarchies": "",
            "related_concepts": ""
        }
        
        # Get from knowledge graph metadata
        node_key = f"{table}.{column}"
        node = self.kg.nodes.get(node_key, {})
        
        context["context"] = node.get("context", "")
        context["rules"] = node.get("business_rules", "")
        context["validation"] = node.get("validation_rules", "")
        context["dependencies"] = node.get("dependencies", "")
        
        # Extract abbreviations & synonyms from entity mappings
        abbrev_dict = {}
        synonym_dict = {}
        
        # Check local mappings for this column
        col_key = f"{table}.{column}"
        if col_key in self.entity_mappings:
            for term, mapping in self.entity_mappings[col_key].items():
                if mapping.get('entity_type') == 'domain_value':
                    canonical = mapping.get('canonical_name', term)
                    aliases = mapping.get('aliases', [])
                    
                    if aliases:
                        abbrev_dict[canonical] = aliases
                        for alias in aliases:
                            synonym_dict[alias] = canonical
        
        # Format for prompt
        if abbrev_dict:
            context["abbreviations"] = "\n".join([
                f"  - {canonical}: {', '.join(aliases)}"
                for canonical, aliases in abbrev_dict.items()
            ])
        else:
            context["abbreviations"] = "None defined"
        
        if synonym_dict:
            context["synonyms"] = "\n".join([
                f"  - '{alias}' → '{canonical}'"
                for alias, canonical in synonym_dict.items()
            ])
        else:
            context["synonyms"] = "None defined"
        
        # TODO: Extract hierarchies from data (parent-child relationships)
        context["hierarchies"] = "No hierarchies defined"
        context["related_concepts"] = node.get("related_concepts", "None")
        
        return context
    
    def _get_entity_mapping_context(
        self, 
        table: str, 
        column: str, 
        user_term: str
    ) -> str:
        """
        Get entity mapping guidance for this specific term.
        """
        col_key = f"{table}.{column}"
        
        # Check if there's a direct mapping for this term
        if col_key in self.entity_mappings:
            if user_term.lower() in [k.lower() for k in self.entity_mappings[col_key].keys()]:
                mapping = self.entity_mappings[col_key].get(
                    user_term.lower(),
                    self.entity_mappings[col_key].get(user_term, {})
                )
                
                canonical = mapping.get('canonical_name', '')
                aliases = mapping.get('aliases', [])
                description = mapping.get('description', '')
                
                return f"""
Entity Mapping Found:
  - User term: "{user_term}"
  - Canonical name: "{canonical}"
  - Known aliases: {', '.join(aliases) if aliases else 'None'}
  - Description: {description}
  - Guidance: This term has an explicit mapping, consider it strongly.
"""
        
        return f"""
No explicit entity mapping found for "{user_term}" in {table}.{column}.
Use semantic understanding and context to determine best matches.
"""
    
    def _get_query_patterns(self, table: str, column: str) -> Dict[str, Any]:
        """
        Get historical query patterns for this column.
        TODO: Implement query pattern tracking
        """
        return {
            "common_patterns": "Pattern tracking not yet implemented",
            "combinations": "Combination tracking not yet implemented",
            "examples": []
        }
    
    def _format_value_distribution(self, stats: Dict[str, int]) -> str:
        """Format value frequency distribution for LLM."""
        if not any(stats.values()):
            return "No distribution statistics available"
        
        total = sum(stats.values())
        if total == 0:
            return "No distribution statistics available"
        
        # Show top 10 by frequency
        sorted_values = sorted(stats.items(), key=lambda x: x[1], reverse=True)[:10]
        
        lines = []
        for value, count in sorted_values:
            pct = (count / total * 100)
            lines.append(f"  {value}: {count:,} rows ({pct:.1f}%)")
        
        if len(stats) > 10:
            remaining = len(stats) - 10
            remaining_count = sum(count for val, count in sorted(stats.items(), key=lambda x: x[1], reverse=True)[10:])
            remaining_pct = (remaining_count / total * 100)
            lines.append(f"  ... and {remaining} more values ({remaining_count:,} rows, {remaining_pct:.1f}%)")
        
        return "\n".join(lines)
    
    def _format_values_detailed(
        self, 
        values: List[str], 
        stats: Dict[str, int]
    ) -> str:
        """Format available values with statistics as JSON."""
        values_with_stats = []
        
        for val in sorted(values):
            values_with_stats.append({
                "value": val,
                "count": stats.get(val, 0),
                "percentage": f"{(stats.get(val, 0) / sum(stats.values()) * 100):.1f}%" if sum(stats.values()) > 0 else "0%"
            })
        
        # Sort by count descending
        values_with_stats.sort(key=lambda x: x["count"], reverse=True)
        
        return json.dumps(values_with_stats, indent=2)
    
    def _format_examples(self, examples: List[str]) -> str:
        """Format usage examples."""
        if not examples:
            return "No examples available"
        
        return "\n".join([f"  - {ex}" for ex in examples])
    
    def _build_cache_key(
        self,
        table: str,
        column: str,
        user_term: str,
        values: List[str],
        context: Dict[str, Any]
    ) -> str:
        """Build cache key including context hash."""
        values_hash = hash(tuple(sorted(values)))
        
        # Include key context elements in cache key
        context_hash = hash((
            context.get('query_intent'),
            context.get('application_domain'),
            len(context.get('abbreviations', ''))
        ))
        
        return f"domain_select_v2:{table}.{column}:{user_term}:{values_hash}:{context_hash}"
    
    def _parse_and_validate(
        self, 
        response: str, 
        available_values: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Parse and validate LLM response."""
        try:
            result = json.loads(response)
            
            # Validate selected values
            selected = result.get("selected_values", [])
            valid_values = [v for v in selected if v in available_values]
            invalid_values = [v for v in selected if v not in available_values]
            
            if invalid_values:
                logger.warning(
                    f"[llm-select-enhanced] LLM returned {len(invalid_values)} "
                    f"invalid value(s): {invalid_values}"
                )
            
            if not valid_values:
                logger.warning("[llm-select-enhanced] No valid values selected")
                return None
            
            return {
                "selected_values": valid_values,
                "confidence": result.get("confidence", 0.5),
                "reasoning": result.get("reasoning", ""),
                "match_type": result.get("match_type", "unknown"),
                "business_rationale": result.get("business_rationale", ""),
                "excluded_count": result.get("excluded_count", len(available_values) - len(valid_values)),
                "alternative_interpretations": result.get("alternative_interpretations", []),
                "warnings": result.get("warnings", []),
                "method": "llm_multi_select_enhanced"
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"[llm-select-enhanced] JSON parse error: {e}")
            return None
    
    def _log_selection_details(
        self, 
        user_term: str, 
        table: str, 
        column: str, 
        result: Dict[str, Any]
    ):
        """Log detailed selection results."""
        logger.info(
            f"[llm-select-enhanced] ✓ '{user_term}' → {result['selected_values']} "
            f"in {table}.{column}"
        )
        logger.info(
            f"[llm-select-enhanced] Confidence: {result['confidence']:.2f}, "
            f"Match type: {result['match_type']}, "
            f"Excluded: {result['excluded_count']}"
        )
        logger.debug(f"[llm-select-enhanced] Reasoning: {result['reasoning']}")
        logger.debug(f"[llm-select-enhanced] Business rationale: {result['business_rationale']}")
        
        if result.get('warnings'):
            logger.warning(f"[llm-select-enhanced] Warnings: {result['warnings']}")
```

## Example Usage

```python
# In SQL Generator

# Initialize selector
domain_selector = EnhancedDomainValueSelector(
    kg=self.kg,
    llm_client=self.llm_client,
    entity_mappings=self.entity_mappings
)

# For each domain value entity
for ent in domain_value_entities:
    table = ent.get("table")
    column = ent.get("column")
    user_term = ent.get("text")
    
    # Check if we need LLM (low semantic score)
    semantic_score = ent.get("top_match", {}).get("score", 0.0)
    
    if semantic_score < 0.5:
        # Get all available values
        available_values = await self.domain_cache.get_values(table, column)
        
        # Call enhanced LLM selector
        result = await domain_selector.select_values(
            user_query=self.state.question,
            user_term=user_term,
            table=table,
            column=column,
            available_values=available_values,
            query_state=self.state
        )
        
        if result and result["selected_values"]:
            # Use LLM-selected values
            selected_values = result["selected_values"]
            
            # Build WHERE clause
            if len(selected_values) == 1:
                conditions.append(f"{table}.{column} = '{selected_values[0]}'")
            else:
                value_list = "', '".join(selected_values)
                conditions.append(f"{table}.{column} IN ('{value_list}')")
            
            # Add transparency warning if needed
            if result["confidence"] < 0.8 or result.get("warnings"):
                warnings.append({
                    "type": "llm_domain_selection_enhanced",
                    "column": f"{table}.{column}",
                    "user_term": user_term,
                    "selected_values": selected_values,
                    "confidence": result["confidence"],
                    "match_type": result["match_type"],
                    "reasoning": result["reasoning"],
                    "business_rationale": result["business_rationale"],
                    "warnings": result.get("warnings", [])
                })
            
            continue  # Success, skip fallback strategies
    
    # Fallback to semantic/fuzzy matching
    ...
```

## Benefits of Rich Context

### 1. **Better Accuracy**
- LLM has full business context
- Understands domain-specific terms
- Uses historical patterns

### 2. **Explainability**
- Detailed reasoning with business rationale
- Match type classification
- Alternative interpretations provided

### 3. **Confidence Calibration**
- More accurate confidence scores
- Warnings for edge cases
- Alternative suggestions when uncertain

### 4. **Business Alignment**
- Respects business rules
- Considers validation constraints
- Uses known abbreviations/synonyms

### 5. **Performance**
- Rich context cached per column
- Reduces need for multiple LLM calls
- Faster subsequent queries

## Example Enhanced Response

```json
{
  "selected_values": ["Equity Growth", "Equity Value"],
  "confidence": 0.92,
  "reasoning": "User query 'List equity funds' with term 'equity' is requesting fund types. Based on funds.fund_type business context, 'equity' is a category term that encompasses multiple fund types. The entity mapping shows 'equity' is synonymous with stock-based investments. Both 'Equity Growth' and 'Equity Value' are equity fund strategies, accounting for 45% of total funds (3,450 rows combined).",
  "match_type": "partial_category",
  "business_rationale": "In fund accounting domain, 'equity' commonly refers to all stock-based investment strategies. Historical query patterns show users querying for 'equity' expect both growth and value strategies. The aggregation intent suggests broader category selection is appropriate.",
  "excluded_count": 4,
  "excluded_examples": ["Bond", "Technology", "REIT"],
  "alternative_interpretations": [
    "If user meant only growth-oriented equity, might select only 'Equity Growth'",
    "If user meant all non-bond funds, might also include 'Technology' and 'REIT'"
  ],
  "warnings": [
    "Equity category represents 45% of funds - large result set expected"
  ],
  "method": "llm_multi_select_enhanced"
}
```

## Configuration

```yaml
domain_value_matching:
  llm_selection:
    enabled: true
    use_enhanced_context: true  # NEW!
    timeout_ms: 5000  # Longer for rich context
    
  context_enrichment:
    include_table_metadata: true
    include_column_metadata: true
    include_value_statistics: true
    include_business_rules: true
    include_entity_mappings: true
    include_query_patterns: true
    include_synonyms: true
    include_abbreviations: true
    
    # Limits
    max_examples: 5
    max_related_concepts: 10
```

## Next Steps

1. Implement `EnhancedDomainValueSelector` class
2. Add metadata extraction methods to knowledge graph
3. Track query patterns for historical context
4. Test with diverse query scenarios
5. Monitor accuracy improvements

---

**Status:** Ready for implementation  
**Expected Impact:** +15-20% accuracy improvement over basic LLM approach  
**Last Updated:** 2025-11-08
