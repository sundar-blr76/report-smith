"""
Domain Value Enricher - Uses LLM to match user-provided values to database domain values.

When semantic search fails to find a good match for a domain value (e.g., user says "truepotential"
but database has "TruePotential Asset Management"), this enricher asks an LLM to intelligently 
match the user input to the actual database values.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import json
import time

from ..logger import get_logger
from ..schema_intelligence.embedding_manager import EmbeddingManager

logger = get_logger(__name__)


@dataclass
class DomainValueMatch:
    """Result of domain value matching."""
    user_value: str
    matched_value: Optional[str]
    confidence: float
    reasoning: str
    table: str
    column: str


class DomainValueEnricher:
    """
    Enriches user-provided domain values using LLM when direct/semantic search fails.
    
    When a user mentions a value that doesn't directly match database values,
    this enricher retrieves all possible values for the relevant column and asks
    the LLM to perform intelligent matching based on context.
    """
    
    def __init__(self, llm_provider: str = "gemini", model: Optional[str] = None):
        """
        Initialize domain value enricher.
        
        Args:
            llm_provider: LLM provider ("gemini", "openai", "anthropic")
            model: Model name (uses default if not specified)
        """
        self.llm_provider = llm_provider
        
        if llm_provider == "gemini":
            import google.generativeai as genai
            import os
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable not set")
            genai.configure(api_key=api_key)
            self.model = model or "gemini-2.5-flash"
            self.client = genai.GenerativeModel(self.model)
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")
        
        logger.info(f"Initialized Domain Value Enricher with {llm_provider}/{self.model}")
    
    def enrich_domain_value(
        self,
        user_value: str,
        table: str,
        column: str,
        available_values: List[Dict[str, Any]],
        query_context: str,
        table_description: Optional[str] = None,
        column_description: Optional[str] = None,
        business_context: Optional[str] = None
    ) -> DomainValueMatch:
        """
        Use LLM to match user-provided value to actual database values.
        
        Args:
            user_value: Value provided by user (e.g., "truepotential", "equity")
            table: Table name
            column: Column name  
            available_values: List of actual database values with metadata
                             [{"value": "...", "count": N, "description": "..."}, ...]
            query_context: The original user query for context
            table_description: Description of the table (optional)
            column_description: Description of the column (optional)
            business_context: Additional business context (optional)
            
        Returns:
            DomainValueMatch with matched value and confidence
        """
        logger.info(
            f"[domain-enricher] Enriching user value '{user_value}' for {table}.{column} "
            f"with {len(available_values)} possible values"
        )
        
        # Build context for LLM
        context_parts = []
        if table_description:
            context_parts.append(f"Table Description: {table_description}")
        if column_description:
            context_parts.append(f"Column Description: {column_description}")
        if business_context:
            context_parts.append(f"Business Context: {business_context}")
        
        context_str = "\n".join(context_parts) if context_parts else "No additional context available."
        
        # Format available values for LLM
        values_str = self._format_values_for_llm(available_values)
        
        # Build prompt
        prompt = f"""You are a database query assistant helping match user-provided values to actual database values.

User Query: "{query_context}"
User Mentioned: "{user_value}"

Database Column: {table}.{column}
{context_str}

Available Values in Database:
{values_str}

Task: Determine which database value (if any) the user is referring to when they said "{user_value}".

Consider:
1. Exact matches (case-insensitive)
2. Partial matches (user might use abbreviation or subset of full name)
3. Semantic similarity (user might use different phrasing)
4. Business context (what makes sense given the query)
5. Value frequency/importance (more common values might be more likely)

Return a JSON object with:
{{
  "matched_value": "exact database value or null if no confident match",
  "confidence": 0.0-1.0 score,
  "reasoning": "brief explanation of match or why no match"
}}

Important:
- Only return a match if you have reasonable confidence (>0.6)
- If multiple values could match, choose the most likely one based on context
- If no good match exists, return null for matched_value and explain why
- Return ONLY the JSON, no other text"""

        logger.debug(f"[domain-enricher] LLM prompt ({len(prompt)} chars):")
        logger.debug(f"--- DOMAIN ENRICHER PROMPT START ---")
        logger.debug(prompt)
        logger.debug(f"--- DOMAIN ENRICHER PROMPT END ---")
        
        try:
            t0 = time.perf_counter()
            
            if self.llm_provider == "gemini":
                generation_config = {
                    "temperature": 0,
                    "response_mime_type": "application/json",
                }
                
                response = self.client.generate_content(
                    prompt,
                    generation_config=generation_config
                )
                
                json_text = response.text
                result = json.loads(json_text)
                
                dt_ms = (time.perf_counter() - t0) * 1000.0
                logger.info(
                    f"[domain-enricher] LLM response ({dt_ms:.1f}ms): "
                    f"matched='{result.get('matched_value')}' confidence={result.get('confidence'):.2f}"
                )
                logger.debug(f"[domain-enricher] LLM reasoning: {result.get('reasoning')}")
                
                return DomainValueMatch(
                    user_value=user_value,
                    matched_value=result.get("matched_value"),
                    confidence=result.get("confidence", 0.0),
                    reasoning=result.get("reasoning", ""),
                    table=table,
                    column=column
                )
            
        except Exception as e:
            logger.error(f"[domain-enricher] LLM enrichment failed: {e}", exc_info=True)
            return DomainValueMatch(
                user_value=user_value,
                matched_value=None,
                confidence=0.0,
                reasoning=f"LLM enrichment error: {str(e)}",
                table=table,
                column=column
            )
    
    def _format_values_for_llm(self, values: List[Dict[str, Any]], max_values: int = 50) -> str:
        """Format available values for LLM prompt."""
        lines = []
        for i, val_info in enumerate(values[:max_values], 1):
            value = val_info.get("value", "")
            count = val_info.get("count", 0)
            description = val_info.get("description", "")
            
            parts = [f"{i}. \"{value}\""]
            if count:
                parts.append(f"(used {count} times)")
            if description and description != value:
                parts.append(f"- {description}")
            
            lines.append(" ".join(parts))
        
        if len(values) > max_values:
            lines.append(f"... and {len(values) - max_values} more values")
        
        return "\n".join(lines)
