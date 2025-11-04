"""
Query Validator - Validates generated SQL queries against user intent using LLM.

This module provides LLM-based validation to ensure generated SQL queries
accurately reflect the user's original question and intent.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from reportsmith.logger import get_logger

logger = get_logger(__name__)


class QueryValidator:
    """
    Validates SQL queries against user intent using LLM.
    
    This validator checks if the generated SQL query correctly captures
    the user's intent by analyzing:
    - Column selections match requested data
    - Filters align with user conditions
    - Aggregations match user requirements
    - Join logic is appropriate
    
    If discrepancies are detected, it can suggest corrections.
    """
    
    def __init__(self, llm_client=None, provider: str = "gemini"):
        """
        Initialize query validator.
        
        Args:
            llm_client: LLM client instance (OpenAI, Anthropic, or Gemini)
            provider: LLM provider type ("openai", "anthropic", or "gemini")
        """
        self.llm_client = llm_client
        self.provider = provider
        logger.info(f"[query-validator] initialized with provider={provider}")
    
    def validate(
        self,
        *,
        question: str,
        intent: Dict[str, Any],
        sql: str,
        entities: List[Dict[str, Any]],
        plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate SQL query against user intent.
        
        Args:
            question: Original user question
            intent: Parsed intent from analysis
            sql: Generated SQL query
            entities: Extracted entities
            plan: Query execution plan
        
        Returns:
            Dict with:
                - is_valid: bool - Whether query matches intent
                - issues: List[str] - Detected issues
                - corrected_sql: Optional[str] - Corrected SQL if issues found
                - reasoning: str - Explanation of validation
                - confidence: float - Confidence in validation (0-1)
        """
        logger.info("[query-validator] validating SQL against user intent")
        
        if not self.llm_client:
            logger.warning("[query-validator] no LLM client available, skipping validation")
            return {
                "is_valid": True,
                "issues": [],
                "corrected_sql": None,
                "reasoning": "Validation skipped - no LLM client configured",
                "confidence": 0.0,
            }
        
        try:
            # Build validation prompt
            prompt = self._build_validation_prompt(
                question=question,
                intent=intent,
                sql=sql,
                entities=entities,
                plan=plan,
            )
            
            # Call LLM for validation
            t0 = time.perf_counter()
            validation_result = self._call_llm(prompt)
            dt_ms = (time.perf_counter() - t0) * 1000.0
            
            logger.info(
                f"[query-validator] validation complete in {dt_ms:.1f}ms: "
                f"valid={validation_result.get('is_valid')}, "
                f"issues={len(validation_result.get('issues', []))}, "
                f"confidence={validation_result.get('confidence', 0.0):.2f}"
            )
            
            # Log issues if any
            if validation_result.get("issues"):
                for i, issue in enumerate(validation_result["issues"], 1):
                    logger.warning(f"[query-validator] issue #{i}: {issue}")
            
            # Log corrected SQL if provided
            if validation_result.get("corrected_sql"):
                logger.info("[query-validator] corrected SQL provided:")
                logger.info(validation_result["corrected_sql"])
            
            return validation_result
            
        except Exception as e:
            logger.error(f"[query-validator] validation failed: {e}", exc_info=True)
            return {
                "is_valid": True,  # Default to valid on error to not block execution
                "issues": [f"Validation error: {str(e)}"],
                "corrected_sql": None,
                "reasoning": f"Validation failed with error: {str(e)}",
                "confidence": 0.0,
            }
    
    def _build_validation_prompt(
        self,
        *,
        question: str,
        intent: Dict[str, Any],
        sql: str,
        entities: List[Dict[str, Any]],
        plan: Dict[str, Any],
    ) -> str:
        """Build LLM prompt for query validation."""
        
        # Extract key intent details
        intent_type = intent.get("type", "unknown")
        aggregations = intent.get("aggregations", [])
        filters = intent.get("filters", [])
        
        # Extract entity details
        entity_summary = []
        for ent in entities:
            ent_info = {
                "text": ent.get("text"),
                "type": ent.get("entity_type"),
                "table": ent.get("table"),
                "column": ent.get("column"),
            }
            entity_summary.append(ent_info)
        
        # Build prompt
        prompt = f"""You are a SQL query validation expert. Your task is to validate if a generated SQL query accurately captures the user's intent.

**User Question**: "{question}"

**Parsed Intent**:
- Type: {intent_type}
- Aggregations: {', '.join(aggregations) if aggregations else 'None'}
- Filters: {', '.join(filters) if filters else 'None'}

**Extracted Entities**:
{json.dumps(entity_summary, indent=2)}

**Generated SQL Query**:
```sql
{sql}
```

**Query Plan**:
{json.dumps(plan, indent=2)}

**Validation Tasks**:
1. Check if the SELECT clause includes all data requested by the user
2. Verify filters/WHERE conditions match user's requirements
3. Confirm aggregations (SUM, COUNT, AVG, etc.) align with intent
4. Ensure JOINs are appropriate for the question
5. Check for any missing or unnecessary components
6. Validate that sub-queries (if any) are correctly structured

**Return JSON with**:
{{
  "is_valid": true/false,
  "issues": ["list of specific issues found, if any"],
  "corrected_sql": "corrected SQL query if issues found, otherwise null",
  "reasoning": "detailed explanation of validation",
  "confidence": 0.0-1.0
}}

**Guidelines**:
- Be precise and specific about any issues
- If providing corrected SQL, ensure it's syntactically correct
- Consider the complexity of the query (simple vs sub-queries)
- Confidence should reflect how certain you are about the validation
- If query is valid, set is_valid=true and corrected_sql=null
"""
        
        return prompt
    
    def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """Call LLM with validation prompt."""
        try:
            if self.provider == "openai":
                response = self.llm_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a SQL query validation expert."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0,
                )
                result_text = response.choices[0].message.content
            
            elif self.provider == "anthropic":
                response = self.llm_client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                )
                result_text = response.content[0].text
                # Extract JSON from response
                start = result_text.find('{')
                end = result_text.rfind('}') + 1
                if start >= 0 and end > start:
                    result_text = result_text[start:end]
            
            else:  # gemini
                gen_config = {
                    "temperature": 0,
                    "response_mime_type": "application/json",
                }
                response = self.llm_client.generate_content(
                    prompt,
                    generation_config=gen_config
                )
                result_text = response.text
            
            # Parse JSON response
            result = json.loads(result_text)
            
            # Ensure required fields exist
            if "is_valid" not in result:
                result["is_valid"] = True
            if "issues" not in result:
                result["issues"] = []
            if "confidence" not in result:
                result["confidence"] = 0.5
            
            return result
            
        except Exception as e:
            logger.error(f"[query-validator] LLM call failed: {e}", exc_info=True)
            raise
