"""
LLM-driven SQL Validator for ReportSmith.

This module implements SQL validation and refinement features including:
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
from reportsmith.utils.llm_tracker import LLMTracker
from reportsmith.utils.cache_manager import get_cache_manager

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


class SQLValidator:
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
        max_iterations: int = 10,
        sample_size: int = 10,
        enable_validation: bool = True,
        enable_summary: bool = True,
        enable_ordering: bool = True,
        enable_coercion: bool = True,
        rate_limit_rpm: int = 60,  # Requests per minute
        cost_cap_tokens: int = 100000,  # Max tokens per request
        llm_tracker: Optional[LLMTracker] = None,  # For cost tracking
        enable_cache: bool = True,  # Enable caching
    ):
        """
        Initialize SQL validator.
        
        Args:
            llm_client: LLM client (OpenAI, Anthropic, or Gemini)
            max_iterations: Maximum validation iterations (default: 10)
            sample_size: Sample rows for predicate coercion (default: 10)
            enable_validation: Enable iterative validation (FR-4)
            enable_summary: Enable summary generation (FR-1)
            enable_ordering: Enable column ordering (FR-2)
            enable_coercion: Enable predicate coercion (FR-3)
            rate_limit_rpm: Rate limit in requests per minute (default: 60)
            cost_cap_tokens: Cost cap in total tokens per request (default: 100k)
            llm_tracker: Optional LLM tracker for cost estimation
            enable_cache: Enable caching of LLM responses (default: True)
        """
        self.llm_client = llm_client
        self.max_iterations = max_iterations
        self.sample_size = sample_size
        self.enable_validation = enable_validation
        self.enable_summary = enable_summary
        self.enable_ordering = enable_ordering
        self.enable_coercion = enable_coercion
        self.rate_limit_rpm = rate_limit_rpm
        self.cost_cap_tokens = cost_cap_tokens
        self.llm_tracker = llm_tracker
        self.enable_cache = enable_cache
        self.cache = get_cache_manager() if enable_cache else None
        
        # Rate limiting state
        self._request_timestamps = []
        self._total_tokens_used = 0
        
        # Detect LLM provider type
        self.provider = self._detect_provider()
        logger.info(
            f"[sql-validator] initialized with provider={self.provider}, "
            f"max_iterations={max_iterations}, sample_size={sample_size}, "
            f"rate_limit={rate_limit_rpm} rpm, cost_cap={cost_cap_tokens} tokens"
        )
    
    def _check_rate_limit(self) -> bool:
        """
        Check if rate limit is exceeded.
        
        Returns:
            True if within rate limit, False if exceeded
        """
        import time
        
        now = time.time()
        # Remove timestamps older than 1 minute
        self._request_timestamps = [
            ts for ts in self._request_timestamps if now - ts < 60
        ]
        
        if len(self._request_timestamps) >= self.rate_limit_rpm:
            logger.warning(
                f"[sql-validator] rate limit exceeded: "
                f"{len(self._request_timestamps)}/{self.rate_limit_rpm} requests in last minute"
            )
            return False
        
        return True
    
    def _check_cost_cap(self, additional_tokens: int = 0) -> bool:
        """
        Check if cost cap is exceeded.
        
        Args:
            additional_tokens: Estimated tokens for next request
            
        Returns:
            True if within cost cap, False if exceeded
        """
        estimated_total = self._total_tokens_used + additional_tokens
        
        if estimated_total > self.cost_cap_tokens:
            logger.warning(
                f"[sql-validator] cost cap exceeded: "
                f"{estimated_total}/{self.cost_cap_tokens} tokens"
            )
            return False
        
        return True
    
    def reset_usage_tracking(self):
        """Reset usage tracking for new request."""
        self._request_timestamps = []
        self._total_tokens_used = 0
        logger.debug("[sql-validator] usage tracking reset")
    
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
        
        # Check rate limit
        if not self._check_rate_limit():
            raise RuntimeError("Rate limit exceeded, please retry later")
        
        # Estimate token usage (rough approximation: 1 token ~= 4 chars)
        estimated_tokens = len(prompt) // 4 + 200  # Prompt + expected response
        
        # Check cost cap
        if not self._check_cost_cap(estimated_tokens):
            raise RuntimeError("Cost cap exceeded for this request")
        
        import time
        t0 = time.perf_counter()
        
        # Record request timestamp for rate limiting
        self._request_timestamps.append(time.time())
        
        # Log LLM call request payload (FULL prompt for debugging)
        logger.info(f"[sql-validator:llm] Sending refinement request to {self.provider}")
        logger.info(f"[sql-validator:llm:request] Full Prompt ({len(prompt)} chars):\n{prompt}")
        
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
                # Update total tokens used
                self._total_tokens_used += tokens["total"]
            
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
                # Update total tokens used
                self._total_tokens_used += tokens["total"]
            
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
                # Use rough estimate
                tokens = {
                    "prompt": len(prompt) // 4,
                    "completion": len(result_text) // 4,
                    "total": (len(prompt) + len(result_text)) // 4,
                }
                # Update total tokens used (estimate)
                self._total_tokens_used += tokens["total"]
            
            dt_ms = (time.perf_counter() - t0) * 1000.0
            
            metrics = {
                "provider": self.provider,
                "model": model,
                "latency_ms": round(dt_ms, 2),
                "prompt_chars": len(prompt),
                "response_chars": len(result_text),
                "tokens": tokens,
                "total_tokens_used": self._total_tokens_used,
            }
            
            # Track LLM call for cost estimation
            if self.llm_tracker:
                self.llm_tracker.track_call(
                    stage="sql_validation",
                    provider=self.provider,
                    model=model,
                    prompt_tokens=tokens["prompt"],
                    completion_tokens=tokens["completion"],
                    latency_ms=dt_ms,
                    prompt_chars=len(prompt),
                    response_chars=len(result_text),
                    request_payload=prompt,  # Store full prompt for debugging
                    response_payload=result_text,  # Store full response for debugging
                )
            
            # Log response payload (FULL response for debugging)
            logger.info(
                f"[sql-validator:llm:response] tokens={tokens['total']} "
                f"(prompt={tokens['prompt']}, completion={tokens['completion']}) "
                f"latency={dt_ms:.0f}ms total_used={self._total_tokens_used}/{self.cost_cap_tokens}"
            )
            logger.info(f"[sql-validator:llm:response] Full Response ({len(result_text)} chars):\n{result_text}")
            
            return result_text, metrics
        
        except Exception as e:
            logger.error(f"[sql-validator] LLM call failed: {e}")
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
        
        logger.info("[sql-validator] generating extraction summary")
        
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
                f"[sql-validator] summary generated: {summary.summary[:100]}... "
                f"(latency={metrics['latency_ms']}ms)"
            )
            
            return summary
        
        except Exception as e:
            logger.warning(f"[sql-validator] summary generation failed: {e}")
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
        
        logger.info("[sql-validator] determining column order")
        
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
                f"[sql-validator] column ordering determined: {len(ordering.ordered_columns)} columns "
                f"(latency={metrics['latency_ms']}ms)"
            )
            
            return ordering
        
        except Exception as e:
            logger.warning(f"[sql-validator] column ordering failed: {e}")
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
        
        logger.info(f"[sql-validator] coercing predicate: {column_name}={user_value}")
        
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
                f"[sql-validator] coercion: '{user_value}' → '{coercion.canonical_value}' "
                f"(type={coercion.value_type}, confidence={coercion.confidence}, "
                f"latency={metrics['latency_ms']}ms)"
            )
            
            return coercion
        
        except Exception as e:
            logger.warning(f"[sql-validator] predicate coercion failed: {e}")
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
        
        logger.info("[sql-validator] starting iterative SQL validation")
        
        # Safety check: ensure SQL is read-only (no DDL/DML)
        if not self._is_read_only_sql(sql):
            logger.error("[sql-validator] SQL contains DDL/DML operations, rejecting")
            return sql, [
                ValidationResult(
                    iteration=0,
                    valid=False,
                    issues=["SQL contains unsafe DDL/DML operations"],
                    reasoning="Safety violation: only SELECT queries are allowed",
                )
            ]
        
        validation_history = []
        current_sql = sql
        previous_attempts = []  # Track SQL attempts to avoid loops
        
        for iteration in range(self.max_iterations):
            logger.info(f"[sql-validator] validation iteration {iteration + 1}/{self.max_iterations}")
            logger.info(f"[sql-validator] Current SQL:\n{current_sql}")
            
            issues = []
            warnings = []
            
            # Step 1: Syntactic validation (parse check)
            validation = sql_executor.validate_sql(current_sql)
            if not validation.get("valid"):
                issues.append(f"Syntax error: {validation.get('error')}")
                logger.warning(f"[sql-validator] SQL syntax invalid: {validation.get('error')}")
            
            # Step 2: Limited execution test (LIMIT 5) - sandboxed
            if validation.get("valid"):
                test_sql = self._add_limit(current_sql, 5)
                
                # Double-check test SQL is still read-only
                if not self._is_read_only_sql(test_sql):
                    issues.append("Safety violation: SQL modified to non-read-only")
                    logger.error("[sql-validator] Test SQL safety check failed")
                else:
                    exec_result = sql_executor.execute_query(test_sql, max_rows=5)
                    
                    if exec_result.get("error"):
                        issues.append(f"Execution error: {exec_result.get('error')}")
                        logger.warning(f"[sql-validator] SQL execution failed: {exec_result.get('error')}")
                    else:
                        # Check for semantic issues
                        columns_returned = exec_result.get("columns", [])
                        rows_returned = exec_result.get("row_count", 0)
                        
                        logger.info(
                            f"[sql-validator] test execution: {rows_returned} rows, "
                            f"{len(columns_returned)} columns"
                        )
                        
                        # Check if expected entities are in output
                        expected_columns = self._extract_expected_columns(entities)
                        missing_columns = [col for col in expected_columns if col not in columns_returned]
                        
                        if missing_columns:
                            warnings.append(f"Missing expected columns: {missing_columns}")
                            logger.info(f"[sql-validator] warning: {warnings[-1]}")
            
            # Log current validation status
            if issues:
                logger.warning(f"[sql-validator] Found {len(issues)} issue(s): {issues}")
            if warnings:
                logger.info(f"[sql-validator] Found {len(warnings)} warning(s): {warnings}")
            
            # If no issues, we're done
            # Warnings are acceptable - they're just suggestions for improvement
            if not issues:
                if warnings:
                    logger.info("[sql-validator] validation successful (with warnings - acceptable)")
                else:
                    logger.info("[sql-validator] validation successful")
                validation_history.append(
                    ValidationResult(
                        iteration=iteration + 1,
                        valid=True,
                        issues=[],
                        warnings=warnings,  # Keep warnings for reference
                        reasoning="SQL validated successfully" + (f" with {len(warnings)} warning(s)" if warnings else ""),
                    )
                )
                break
            
            # Step 3: Ask LLM to refine SQL ONLY if there are issues (not warnings)
            if issues:
                logger.info(f"[sql-validator] requesting LLM refinement for {len(issues)} issue(s)")
                
                refined_sql, refinement_metrics = self._refine_sql_with_llm(
                    question=question,
                    current_sql=current_sql,
                    issues=issues,
                    warnings=warnings,
                    entities=entities,
                    intent=intent,
                    previous_attempts=previous_attempts,  # Pass history to avoid loops
                    schema_metadata=schema_metadata,  # Pass schema for context
                )
                
                if refined_sql and refined_sql != current_sql:
                    # Check if we've seen this SQL before (loop detection)
                    if refined_sql in [attempt["sql"] for attempt in previous_attempts]:
                        logger.warning(
                            f"[sql-validator] Loop detected: LLM suggested previously failed SQL. "
                            f"Stopping iterations at {iteration + 1}/{self.max_iterations}"
                        )
                        validation_history.append(
                            ValidationResult(
                                iteration=iteration + 1,
                                valid=False,
                                issues=issues,
                                warnings=warnings,
                                reasoning="Loop detected: LLM repeated a previous failed attempt",
                            )
                        )
                        break
                    
                    # Safety check refined SQL
                    if not self._is_read_only_sql(refined_sql):
                        logger.error("[sql-validator] Refined SQL contains unsafe operations, rejecting")
                        validation_history.append(
                            ValidationResult(
                                iteration=iteration + 1,
                                valid=False,
                                issues=issues + ["Refined SQL contains unsafe DDL/DML operations"],
                                warnings=warnings,
                                reasoning="Refined SQL rejected due to safety violation",
                            )
                        )
                        break
                    
                    logger.info("[sql-validator] SQL refined by LLM")
                    
                    # Track this attempt before moving to it
                    previous_attempts.append({
                        "iteration": iteration + 1,
                        "sql": current_sql,
                        "issues": issues.copy(),
                        "warnings": warnings.copy(),
                    })
                    
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
                    logger.info("[sql-validator] no further refinement suggested")
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
            f"[sql-validator] validation complete after {len(validation_history)} iteration(s)"
        )
        
        return current_sql, validation_history
    
    def _is_read_only_sql(self, sql: str) -> bool:
        """
        Check if SQL is read-only (SELECT only, no DDL/DML).
        
        Args:
            sql: SQL query to check
            
        Returns:
            True if read-only, False otherwise
        """
        sql_upper = sql.upper().strip()
        
        # Must start with SELECT or WITH (for CTEs)
        if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
            return False
        
        # Forbidden keywords that indicate DDL/DML
        forbidden_keywords = [
            "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
            "TRUNCATE", "REPLACE", "MERGE", "GRANT", "REVOKE",
            "EXEC", "EXECUTE", "CALL", "PROCEDURE",
        ]
        
        for keyword in forbidden_keywords:
            # Use word boundaries to avoid false positives
            # e.g., don't match "INSERT" in column name "INSERT_DATE"
            if re.search(r'\b' + keyword + r'\b', sql_upper):
                logger.warning(
                    f"[sql-validator] SQL contains forbidden keyword: {keyword}"
                )
                return False
        
        return True
    
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
    
    def _extract_tables_from_sql(self, sql: str) -> List[str]:
        """
        Extract table names from SQL query.
        
        Args:
            sql: SQL query
            
        Returns:
            List of table names found in SQL
        """
        tables = set()
        sql_upper = sql.upper()
        
        # Pattern: FROM table_name or JOIN table_name
        patterns = [
            r'\bFROM\s+(\w+)',
            r'\bJOIN\s+(\w+)',
            r'\bINTO\s+(\w+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, sql_upper)
            tables.update(match.lower() for match in matches)
        
        return list(tables)
    
    def _build_schema_context(
        self,
        sql: str,
        schema_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build schema context for LLM prompt showing relevant tables and columns.
        
        Args:
            sql: SQL query to extract tables from
            schema_metadata: Schema metadata dict
            
        Returns:
            Formatted schema context string
        """
        if not schema_metadata or "tables" not in schema_metadata:
            return ""
        
        # Extract tables used in SQL
        tables_in_query = self._extract_tables_from_sql(sql)
        if not tables_in_query:
            return ""
        
        schema_context = "\n=== AVAILABLE SCHEMA ===\n"
        schema_context += "Tables and columns in your query:\n\n"
        
        for table_name in tables_in_query:
            table_info = schema_metadata["tables"].get(table_name, {})
            if not table_info:
                continue
            
            schema_context += f"Table: {table_name}\n"
            
            # Get columns
            columns = table_info.get("columns", {})
            if columns:
                # Group columns by type for better readability
                date_cols = []
                numeric_cols = []
                text_cols = []
                other_cols = []
                
                for col_name, col_info in columns.items():
                    col_type = col_info.get("type", "unknown")
                    col_desc = col_info.get("description", "")
                    aliases = col_info.get("aliases", [])
                    
                    col_entry = f"  - {col_name} ({col_type})"
                    if col_desc:
                        col_entry += f": {col_desc}"
                    if aliases:
                        col_entry += f" [aliases: {', '.join(aliases)}]"
                    
                    # Categorize by type
                    if col_type in ["date", "datetime", "timestamp"]:
                        # Add business context hints for date columns
                        if col_name in ["created_at", "updated_at", "deleted_at"]:
                            col_entry += " ⚠️ METADATA ONLY - Do not use for business logic"
                        elif "payment" in col_name.lower():
                            col_entry += " ✓ Business date - use for payment timing queries"
                        elif "transaction" in col_name.lower():
                            col_entry += " ✓ Business date - use for transaction timing queries"
                        date_cols.append(col_entry)
                    elif col_type in ["integer", "numeric", "decimal", "float", "money"]:
                        numeric_cols.append(col_entry)
                    elif col_type in ["varchar", "text", "char"]:
                        text_cols.append(col_entry)
                    else:
                        other_cols.append(col_entry)
                
                # Output grouped columns
                if date_cols:
                    schema_context += "\n  Date/Time Columns:\n"
                    schema_context += "\n".join(date_cols) + "\n"
                
                if numeric_cols:
                    schema_context += "\n  Numeric Columns:\n"
                    for col in numeric_cols[:10]:  # Limit to avoid too long prompt
                        schema_context += col + "\n"
                    if len(numeric_cols) > 10:
                        schema_context += f"    ... and {len(numeric_cols) - 10} more\n"
                
                if text_cols:
                    schema_context += "\n  Text Columns:\n"
                    for col in text_cols[:8]:  # Limit to avoid too long prompt
                        schema_context += col + "\n"
                    if len(text_cols) > 8:
                        schema_context += f"    ... and {len(text_cols) - 8} more\n"
                
                if other_cols:
                    for col in other_cols[:5]:
                        schema_context += col + "\n"
            
            schema_context += "\n"
        
        schema_context += "⚠️ IMPORTANT:\n"
        schema_context += "- Use payment_date/transaction_date for business queries, NOT created_at\n"
        schema_context += "- created_at/updated_at are metadata timestamps, not business dates\n"
        schema_context += "- Check column descriptions to understand business meaning\n"
        schema_context += "=========================\n"
        
        return schema_context
    
    def _refine_sql_with_llm(
        self,
        *,
        question: str,
        current_sql: str,
        issues: List[str],
        warnings: List[str],
        entities: List[Dict[str, Any]],
        intent: Dict[str, Any],
        previous_attempts: List[Dict[str, Any]] = None,
        schema_metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """Ask LLM to refine SQL based on validation issues and previous failed attempts."""
        
        if previous_attempts is None:
            previous_attempts = []
        
        # Build schema context
        schema_context = self._build_schema_context(current_sql, schema_metadata)
        
        # Build previous attempts context
        previous_context = ""
        if previous_attempts:
            previous_context = "\n\nPrevious Failed Attempts (DO NOT REPEAT THESE):\n"
            for attempt in previous_attempts[-3:]:  # Only show last 3 to keep prompt manageable
                previous_context += f"""
Attempt #{attempt['iteration']}:
SQL: {attempt['sql']}
Issues: {', '.join(attempt['issues'])}
Warnings: {', '.join(attempt['warnings'])}
"""
            previous_context += "\n⚠️ IMPORTANT: Do NOT suggest any of the above SQL queries again. They have already failed.\n"
        
        prompt = f"""Refine SQL query to address validation issues.

User Question: "{question}"

Current SQL:
{current_sql}

{schema_context}

Validation Issues:
{json.dumps(issues, indent=2)}

Warnings:
{json.dumps(warnings, indent=2)}

Expected Entities:
{json.dumps([{"text": e.get("text"), "type": e.get("entity_type")} for e in entities], indent=2)}

Query Intent:
{json.dumps(intent, indent=2)}{previous_context}

Task: Fix the SQL to address the issues while maintaining the intent.

Common fixes:
- Add missing columns to SELECT and GROUP BY
- Fix syntax errors
- Ensure proper join conditions
- Add necessary type casts
- Check table and column names match schema exactly
- Use business date columns (payment_date, transaction_date) NOT metadata timestamps (created_at, updated_at)

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
                f"[sql-validator] LLM refinement: {len(changes)} changes, "
                f"reasoning: {reasoning[:100]}..."
            )
            
            return refined_sql, metrics
        
        except Exception as e:
            logger.warning(f"[sql-validator] SQL refinement failed: {e}")
            return None, {}
