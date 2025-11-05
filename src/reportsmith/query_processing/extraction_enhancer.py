"""
LLM-driven Extraction Enhancer for ReportSmith.

This module implements enhanced extraction features including:
- Natural language summary generation (FR-1)
- LLM-driven column ordering (FR-2)
- Sample-driven predicate coercion (FR-3)
- Iterative SQL validation and refinement (FR-4)
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from reportsmith.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PredicateCoercion:
    """Result of predicate value coercion."""
    
    original_value: str
    canonical_value: str
    value_type: str  # date, currency, boolean, numeric
    reasoning: str
    confidence: float = 1.0
    

@dataclass
class ColumnOrdering:
    """Column ordering recommendation from LLM."""
    
    ordered_columns: List[str]
    reasoning: str
    confidence: float = 1.0


@dataclass
class ValidationResult:
    """Result of SQL validation iteration."""
    
    iteration: int
    valid: bool
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggested_sql: Optional[str] = None
    reasoning: str = ""
    token_usage: Dict[str, int] = field(default_factory=dict)


@dataclass
class ExtractionSummary:
    """Natural language summary of extraction action."""
    
    summary: str
    filters_applied: List[str] = field(default_factory=list)
    transformations: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)


class ExtractionEnhancer:
    """
    Enhances SQL extraction with LLM-driven features.
    
    Implements:
    - FR-1: Extraction summary generation
    - FR-2: Column ordering optimization
    - FR-3: Predicate value coercion
    - FR-4: Iterative SQL validation
    """
    
    def __init__(
        self,
        llm_client=None,
        max_iterations: int = 3,
        sample_size: int = 10,
        enable_validation: bool = True,
        enable_summary: bool = True,
        enable_ordering: bool = True,
        enable_coercion: bool = True,
    ):
        """
        Initialize extraction enhancer.
        
        Args:
            llm_client: LLM client (OpenAI, Anthropic, or Gemini)
            max_iterations: Maximum validation iterations (default: 3)
            sample_size: Sample rows for predicate coercion (default: 10)
            enable_validation: Enable iterative validation (FR-4)
            enable_summary: Enable summary generation (FR-1)
            enable_ordering: Enable column ordering (FR-2)
            enable_coercion: Enable predicate coercion (FR-3)
        """
        self.llm_client = llm_client
        self.max_iterations = max_iterations
        self.sample_size = sample_size
        self.enable_validation = enable_validation
        self.enable_summary = enable_summary
        self.enable_ordering = enable_ordering
        self.enable_coercion = enable_coercion
        
        # Detect LLM provider type
        self.provider = self._detect_provider()
        logger.info(
            f"[extraction-enhancer] initialized with provider={self.provider}, "
            f"max_iterations={max_iterations}, sample_size={sample_size}"
        )
    
    def _detect_provider(self) -> str:
        """Detect LLM provider type."""
        if not self.llm_client:
            return "none"
        
        if hasattr(self.llm_client, "chat") and hasattr(self.llm_client.chat, "completions"):
            return "openai"
        elif hasattr(self.llm_client, "messages"):
            return "anthropic"
        else:
            return "gemini"
    
    def _call_llm(self, prompt: str, model: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Call LLM with provider-specific logic.
        
        Args:
            prompt: Prompt to send to LLM
            model: Optional model override
            
        Returns:
            Tuple of (response_text, metrics)
        """
        if not self.llm_client:
            raise ValueError("LLM client not configured")
        
        t0 = time.perf_counter()
        
        try:
            if self.provider == "openai":
                model = model or "gpt-4o-mini"
                response = self.llm_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are an expert SQL assistant."},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0,
                )
                result_text = response.choices[0].message.content
                tokens = {
                    "prompt": response.usage.prompt_tokens,
                    "completion": response.usage.completion_tokens,
                    "total": response.usage.total_tokens,
                }
            
            elif self.provider == "anthropic":
                model = model or "claude-3-haiku-20240307"
                response = self.llm_client.messages.create(
                    model=model,
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                )
                result_text = response.content[0].text
                # Extract JSON from response
                start = result_text.find("{")
                end = result_text.rfind("}") + 1
                if start >= 0 and end > start:
                    result_text = result_text[start:end]
                tokens = {
                    "prompt": response.usage.input_tokens,
                    "completion": response.usage.output_tokens,
                    "total": response.usage.input_tokens + response.usage.output_tokens,
                }
            
            else:  # gemini
                import google.generativeai as genai
                model = model or "gemini-1.5-flash"
                gen_config = {
                    "temperature": 0,
                    "response_mime_type": "application/json",
                }
                response = self.llm_client.generate_content(prompt, generation_config=gen_config)
                result_text = response.text
                # Gemini doesn't provide token counts in the same way
                tokens = {"prompt": 0, "completion": 0, "total": 0}
            
            dt_ms = (time.perf_counter() - t0) * 1000.0
            
            metrics = {
                "provider": self.provider,
                "model": model,
                "latency_ms": round(dt_ms, 2),
                "prompt_chars": len(prompt),
                "response_chars": len(result_text),
                "tokens": tokens,
            }
            
            return result_text, metrics
        
        except Exception as e:
            logger.error(f"[extraction-enhancer] LLM call failed: {e}")
            raise
    
    def generate_summary(
        self,
        *,
        question: str,
        sql: str,
        entities: List[Dict[str, Any]],
        filters: List[str],
        coercions: Optional[List[PredicateCoercion]] = None,
    ) -> ExtractionSummary:
        """
        Generate natural language summary of extraction (FR-1).
        
        Args:
            question: Original user question
            sql: Generated SQL query
            entities: Discovered entities
            filters: Applied filters
            coercions: Predicate coercions applied
            
        Returns:
            ExtractionSummary with human-readable description
        """
        if not self.enable_summary or not self.llm_client:
            return ExtractionSummary(summary="Query executed successfully.")
        
        logger.info("[extraction-enhancer] generating extraction summary")
        
        # Build context for LLM
        coercion_details = []
        if coercions:
            for c in coercions:
                coercion_details.append({
                    "original": c.original_value,
                    "canonical": c.canonical_value,
                    "type": c.value_type,
                    "reasoning": c.reasoning,
                })
        
        prompt = f"""Generate a concise 1-3 sentence summary explaining this SQL extraction.

User Question: "{question}"

Generated SQL:
{sql}

Entities Discovered: {json.dumps([{"text": e.get("text"), "type": e.get("entity_type")} for e in entities], indent=2)}

Filters Applied: {json.dumps(filters, indent=2)}

Predicate Coercions: {json.dumps(coercion_details, indent=2) if coercion_details else "None"}

Requirements:
- Explain what was extracted (which data/metrics)
- Mention major filters applied
- Note any important transformations or assumptions
- If predicates were coerced, explain the conversion (e.g., "Q4 2025 → 2025-10-01 to 2025-12-31")

Return JSON:
{{
  "summary": "1-3 sentence description",
  "filters_applied": ["filter 1", "filter 2"],
  "transformations": ["transformation 1"],
  "assumptions": ["assumption 1"]
}}
"""
        
        try:
            result_text, metrics = self._call_llm(prompt)
            result = json.loads(result_text)
            
            summary = ExtractionSummary(
                summary=result.get("summary", "Query executed."),
                filters_applied=result.get("filters_applied", []),
                transformations=result.get("transformations", []),
                assumptions=result.get("assumptions", []),
            )
            
            logger.info(
                f"[extraction-enhancer] summary generated: {summary.summary[:100]}... "
                f"(latency={metrics['latency_ms']}ms)"
            )
            
            return summary
        
        except Exception as e:
            logger.warning(f"[extraction-enhancer] summary generation failed: {e}")
            return ExtractionSummary(summary="Query executed successfully.")
    
    def determine_column_order(
        self,
        *,
        question: str,
        columns: List[Dict[str, Any]],
        intent_type: str,
    ) -> ColumnOrdering:
        """
        Determine optimal column ordering using LLM (FR-2).
        
        Args:
            question: Original user question
            columns: List of column dicts with table, column, aggregation info
            intent_type: Query intent type (aggregate, list, etc.)
            
        Returns:
            ColumnOrdering with ordered column list
        """
        if not self.enable_ordering or not self.llm_client:
            # Default ordering: keep original
            return ColumnOrdering(
                ordered_columns=[f"{c.get('table')}.{c.get('column')}" for c in columns],
                reasoning="LLM ordering disabled, using original order",
            )
        
        logger.info("[extraction-enhancer] determining column order")
        
        prompt = f"""Determine the optimal column ordering for query results.

User Question: "{question}"
Query Intent: {intent_type}

Available Columns:
{json.dumps(columns, indent=2)}

Guidelines:
- Primary identifiers first (IDs, names, codes)
- Aggregated metrics next (sums, counts, averages)
- Denominators/ratios last
- Group related columns together
- Prioritize human-readable columns

Return JSON:
{{
  "ordered_columns": ["table.column1", "table.column2", ...],
  "reasoning": "explanation of ordering choices"
}}
"""
        
        try:
            result_text, metrics = self._call_llm(prompt)
            result = json.loads(result_text)
            
            ordering = ColumnOrdering(
                ordered_columns=result.get("ordered_columns", []),
                reasoning=result.get("reasoning", ""),
            )
            
            logger.info(
                f"[extraction-enhancer] column ordering determined: {len(ordering.ordered_columns)} columns "
                f"(latency={metrics['latency_ms']}ms)"
            )
            
            return ordering
        
        except Exception as e:
            logger.warning(f"[extraction-enhancer] column ordering failed: {e}")
            return ColumnOrdering(
                ordered_columns=[f"{c.get('table')}.{c.get('column')}" for c in columns],
                reasoning=f"LLM ordering failed: {e}, using original order",
            )
    
    def coerce_predicate_value(
        self,
        *,
        column_name: str,
        column_type: str,
        user_value: str,
        sample_values: List[Any],
        db_vendor: str = "postgresql",
    ) -> PredicateCoercion:
        """
        Coerce user predicate value to DB-compatible format (FR-3).
        
        Args:
            column_name: Column name
            column_type: Column data type
            user_value: User-provided value
            sample_values: Sample values from the column
            db_vendor: Database vendor (postgresql, mysql, oracle, sqlserver)
            
        Returns:
            PredicateCoercion with canonical value
        """
        if not self.enable_coercion or not self.llm_client:
            return PredicateCoercion(
                original_value=user_value,
                canonical_value=user_value,
                value_type="unknown",
                reasoning="Coercion disabled, using original value",
            )
        
        logger.info(f"[extraction-enhancer] coercing predicate: {column_name}={user_value}")
        
        prompt = f"""Convert user-provided predicate value to database-compatible format.

Column: {column_name}
Data Type: {column_type}
User Value: "{user_value}"
Database Vendor: {db_vendor}

Sample Values from Column:
{json.dumps(sample_values[:10], indent=2, default=str)}

Task: Convert the user value to the canonical database format.

Common conversions:
- Date/Quarter: "Q4 2025" → date range "2025-10-01 to 2025-12-31"
- Date/Month: "Apr-2025" → "2025-04-01" or "2025-04-01 to 2025-04-30"
- Currency: "$1.2M" → 1200000, "INR 12,00,000" → 1200000
- Boolean: "Y/N" → true/false, "yes/no" → true/false, "1/0" → true/false
- Numeric: "1,000" → 1000, "1.5K" → 1500

Return JSON:
{{
  "canonical_value": "converted value or expression",
  "value_type": "date|currency|boolean|numeric|text",
  "reasoning": "explanation of conversion",
  "confidence": 0.0-1.0
}}

If value is a date range, return SQL expression like "column >= '2025-10-01' AND column <= '2025-12-31'"
"""
        
        try:
            result_text, metrics = self._call_llm(prompt)
            result = json.loads(result_text)
            
            coercion = PredicateCoercion(
                original_value=user_value,
                canonical_value=result.get("canonical_value", user_value),
                value_type=result.get("value_type", "unknown"),
                reasoning=result.get("reasoning", ""),
                confidence=result.get("confidence", 1.0),
            )
            
            logger.info(
                f"[extraction-enhancer] coercion: '{user_value}' → '{coercion.canonical_value}' "
                f"(type={coercion.value_type}, confidence={coercion.confidence}, "
                f"latency={metrics['latency_ms']}ms)"
            )
            
            return coercion
        
        except Exception as e:
            logger.warning(f"[extraction-enhancer] predicate coercion failed: {e}")
            return PredicateCoercion(
                original_value=user_value,
                canonical_value=user_value,
                value_type="unknown",
                reasoning=f"Coercion failed: {e}, using original value",
                confidence=0.0,
            )
    
    def validate_and_refine_sql(
        self,
        *,
        question: str,
        sql: str,
        entities: List[Dict[str, Any]],
        intent: Dict[str, Any],
        sql_executor,
        schema_metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, List[ValidationResult]]:
        """
        Iteratively validate and refine SQL (FR-4).
        
        Args:
            question: Original user question
            sql: Initial SQL query
            entities: Discovered entities
            intent: Query intent
            sql_executor: SQL executor for validation
            schema_metadata: Optional schema metadata
            
        Returns:
            Tuple of (final_sql, validation_history)
        """
        if not self.enable_validation or not self.llm_client:
            return sql, []
        
        logger.info("[extraction-enhancer] starting iterative SQL validation")
        
        validation_history = []
        current_sql = sql
        
        for iteration in range(self.max_iterations):
            logger.info(f"[extraction-enhancer] validation iteration {iteration + 1}/{self.max_iterations}")
            
            issues = []
            warnings = []
            
            # Step 1: Syntactic validation (parse check)
            validation = sql_executor.validate_sql(current_sql)
            if not validation.get("valid"):
                issues.append(f"Syntax error: {validation.get('error')}")
                logger.warning(f"[extraction-enhancer] SQL syntax invalid: {validation.get('error')}")
            
            # Step 2: Limited execution test (LIMIT 5)
            if validation.get("valid"):
                test_sql = self._add_limit(current_sql, 5)
                exec_result = sql_executor.execute_query(test_sql, max_rows=5)
                
                if exec_result.get("error"):
                    issues.append(f"Execution error: {exec_result.get('error')}")
                    logger.warning(f"[extraction-enhancer] SQL execution failed: {exec_result.get('error')}")
                else:
                    # Check for semantic issues
                    columns_returned = exec_result.get("columns", [])
                    rows_returned = exec_result.get("row_count", 0)
                    
                    logger.info(
                        f"[extraction-enhancer] test execution: {rows_returned} rows, "
                        f"{len(columns_returned)} columns"
                    )
                    
                    # Check if expected entities are in output
                    expected_columns = self._extract_expected_columns(entities)
                    missing_columns = [col for col in expected_columns if col not in columns_returned]
                    
                    if missing_columns:
                        warnings.append(f"Missing expected columns: {missing_columns}")
            
            # If no issues, we're done
            if not issues and not warnings:
                logger.info("[extraction-enhancer] validation successful")
                validation_history.append(
                    ValidationResult(
                        iteration=iteration + 1,
                        valid=True,
                        issues=[],
                        warnings=[],
                        reasoning="SQL validated successfully",
                    )
                )
                break
            
            # Step 3: Ask LLM to refine SQL
            if issues or (warnings and iteration < self.max_iterations - 1):
                logger.info("[extraction-enhancer] requesting LLM refinement")
                
                refined_sql, refinement_metrics = self._refine_sql_with_llm(
                    question=question,
                    current_sql=current_sql,
                    issues=issues,
                    warnings=warnings,
                    entities=entities,
                    intent=intent,
                )
                
                if refined_sql and refined_sql != current_sql:
                    logger.info("[extraction-enhancer] SQL refined by LLM")
                    validation_history.append(
                        ValidationResult(
                            iteration=iteration + 1,
                            valid=False,
                            issues=issues,
                            warnings=warnings,
                            suggested_sql=refined_sql,
                            reasoning="SQL refined to address issues",
                            token_usage=refinement_metrics.get("tokens", {}),
                        )
                    )
                    current_sql = refined_sql
                else:
                    # No refinement suggested, break
                    logger.info("[extraction-enhancer] no further refinement suggested")
                    validation_history.append(
                        ValidationResult(
                            iteration=iteration + 1,
                            valid=len(issues) == 0,
                            issues=issues,
                            warnings=warnings,
                            reasoning="No further refinement possible",
                        )
                    )
                    break
        
        logger.info(
            f"[extraction-enhancer] validation complete after {len(validation_history)} iteration(s)"
        )
        
        return current_sql, validation_history
    
    def _add_limit(self, sql: str, limit: int) -> str:
        """Add LIMIT clause to SQL if not present."""
        sql = sql.strip()
        if re.search(r'\bLIMIT\s+\d+', sql, re.IGNORECASE):
            # Already has LIMIT, replace it
            sql = re.sub(r'\bLIMIT\s+\d+', f'LIMIT {limit}', sql, flags=re.IGNORECASE)
        else:
            # Add LIMIT
            sql = f"{sql}\n LIMIT {limit}"
        return sql
    
    def _extract_expected_columns(self, entities: List[Dict[str, Any]]) -> List[str]:
        """Extract expected column names from entities."""
        columns = []
        for ent in entities:
            if ent.get("entity_type") == "column":
                col = ent.get("column") or ent.get("text")
                if col:
                    columns.append(col.lower())
        return columns
    
    def _refine_sql_with_llm(
        self,
        *,
        question: str,
        current_sql: str,
        issues: List[str],
        warnings: List[str],
        entities: List[Dict[str, Any]],
        intent: Dict[str, Any],
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """Ask LLM to refine SQL based on validation issues."""
        
        prompt = f"""Refine SQL query to address validation issues.

User Question: "{question}"

Current SQL:
{current_sql}

Validation Issues:
{json.dumps(issues, indent=2)}

Warnings:
{json.dumps(warnings, indent=2)}

Expected Entities:
{json.dumps([{"text": e.get("text"), "type": e.get("entity_type")} for e in entities], indent=2)}

Query Intent:
{json.dumps(intent, indent=2)}

Task: Fix the SQL to address the issues while maintaining the intent.

Common fixes:
- Add missing columns to SELECT and GROUP BY
- Fix syntax errors
- Ensure proper join conditions
- Add necessary type casts

Return JSON:
{{
  "refined_sql": "corrected SQL query",
  "changes_made": ["change 1", "change 2"],
  "reasoning": "explanation of fixes"
}}

If no refinement is needed or possible, return the original SQL.
"""
        
        try:
            result_text, metrics = self._call_llm(prompt)
            result = json.loads(result_text)
            
            refined_sql = result.get("refined_sql", "").strip()
            changes = result.get("changes_made", [])
            reasoning = result.get("reasoning", "")
            
            logger.info(
                f"[extraction-enhancer] LLM refinement: {len(changes)} changes, "
                f"reasoning: {reasoning[:100]}..."
            )
            
            return refined_sql, metrics
        
        except Exception as e:
            logger.warning(f"[extraction-enhancer] SQL refinement failed: {e}")
            return None, {}
