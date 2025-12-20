"""
SQL Integrity Validator for ReportSmith.

Provides granular LLM-based validation of SQL queries with specific checks
for temporal aggregation, comparison dimensions, ranking queries, time filters,
and semantic coherence, plus final holistic validation.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from reportsmith.logger import get_logger
from reportsmith.utils.cache_manager import get_cache_manager

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of a specific integrity validation check."""
    
    validator_name: str
    is_valid: bool
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    severity: str = "medium"  # high, medium, low
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""


@dataclass
class HolisticValidationResult:
    """Result of final holistic integrity validation."""
    
    is_valid: bool
    overall_quality: str  # excellent, good, acceptable, poor
    specific_checks_passed: int
    specific_checks_failed: int
    critical_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    confidence: float = 1.0
    reasoning: str = ""


@dataclass
class RefinementRecord:
    """Record of a successful SQL refinement for learning."""
    
    question: str
    issue_type: str  # temporal, comparison, ranking, etc.
    original_sql: str
    refined_sql: str
    issues: List[str]
    timestamp: datetime = field(default_factory=datetime.now)
    success_count: int = 1


class SQLIntegrityValidator:
    """
    Granular integrity validation for SQL queries using LLM.
    
    Provides specific validators for:
    - Temporal aggregation (DATE_TRUNC vs EXTRACT)
    - Comparison dimensions (GROUP BY comparison field)
    - Ranking queries (ORDER BY + LIMIT)
    - Time filters (proper date ranges)
    - Semantic coherence (SQL matches question)
    
    Plus final holistic validation.
    """
    
    CACHE_VERSION = "v1"
    
    def __init__(
        self,
        llm_client=None,
        enable_cache: bool = True,
        enable_selective_validation: bool = True,
    ):
        """
        Initialize SQL integrity validator.
        
        Args:
            llm_client: LLM client (OpenAI, Anthropic, or Gemini)
            enable_cache: Enable caching of validation results
            enable_selective_validation: Only run relevant validators based on intent
        """
        self.llm_client = llm_client
        self.enable_cache = enable_cache
        self.enable_selective_validation = enable_selective_validation
        self.cache = get_cache_manager() if enable_cache else None
        
        # Refinement history for learning
        self.refinement_history: List[RefinementRecord] = []
        self.max_history = 100
        
        # Detect LLM provider
        self.provider = self._detect_provider()
        
        logger.info(
            f"[integrity-validator] initialized with provider={self.provider}, "
            f"cache={enable_cache}, selective={enable_selective_validation}"
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
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM with provider-specific logic."""
        if not self.llm_client:
            raise ValueError("LLM client not configured")
        
        logger.debug(f"[integrity-validator] LLM call ({len(prompt)} chars)")
        
        try:
            if self.provider == "openai":
                response = self.llm_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an expert SQL validator."},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0,
                )
                return response.choices[0].message.content
            
            elif self.provider == "anthropic":
                response = self.llm_client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                )
                result_text = response.content[0].text
                # Extract JSON
                start = result_text.find("{")
                end = result_text.rfind("}") + 1
                if start >= 0 and end > start:
                    return result_text[start:end]
                return result_text
            
            else:  # gemini
                gen_config = {
                    "temperature": 0,
                    "response_mime_type": "application/json",
                }
                response = self.llm_client.generate_content(prompt, generation_config=gen_config)
                return response.text
        
        except Exception as e:
            logger.error(f"[integrity-validator] LLM call failed: {e}")
            raise
    
    def validate_temporal_aggregation(
        self,
        question: str,
        sql: str,
        intent: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate temporal aggregation implementation.
        
        Checks if queries asking for "by month/quarter/year" use DATE_TRUNC
        instead of EXTRACT for aggregation.
        """
        logger.info("[integrity-validator] Running temporal aggregation check")
        
        # Check cache
        cache_key = f"{question}:{sql}:temporal"
        if self.enable_cache and self.cache:
            cached = self.cache.get("integrity_temporal", cache_key, version=self.CACHE_VERSION)
            if cached:
                logger.debug("[integrity-validator] Cache hit for temporal check")
                return cached
        
        prompt = f"""TASK: Validate temporal aggregation in SQL query.

USER QUESTION: {question}
GENERATED SQL: {sql}
INTENT TYPE: {intent.get('type', 'unknown')}

VALIDATION RULES:
1. If question asks for "by month", "by quarter", "by year" → SQL MUST use DATE_TRUNC
2. EXTRACT should only be used for filtering, not aggregation/grouping
3. Temporal columns in SELECT must match GROUP BY

CHECK:
- Does question request temporal aggregation? (by month/quarter/year)
- If yes, does SQL use DATE_TRUNC('month'/'quarter'/'year', column)?
- Are temporal columns in both SELECT and GROUP BY?
- Is EXTRACT being misused for aggregation instead of DATE_TRUNC?

Return JSON:
{{
    "is_valid": true/false,
    "issues": ["issue 1", "issue 2"],
    "suggestions": ["Use DATE_TRUNC('month', column) instead of EXTRACT(MONTH FROM column) for aggregation"],
    "severity": "high/medium/low",
    "reasoning": "brief explanation"
}}"""
        
        try:
            result_text = self._call_llm(prompt)
            result = json.loads(result_text)
            
            validation = ValidationResult(
                validator_name="temporal_aggregation",
                is_valid=result.get("is_valid", True),
                issues=result.get("issues", []),
                suggestions=result.get("suggestions", []),
                severity=result.get("severity", "medium"),
                reasoning=result.get("reasoning", ""),
            )
            
            # Cache result
            if self.enable_cache and self.cache:
                self.cache.set("integrity_temporal", validation, cache_key, version=self.CACHE_VERSION)
            
            logger.info(
                f"[integrity-validator] Temporal check: "
                f"{'✓ PASS' if validation.is_valid else '✗ FAIL'} "
                f"({len(validation.issues)} issues)"
            )
            
            return validation
        
        except Exception as e:
            logger.warning(f"[integrity-validator] Temporal validation failed: {e}")
            return ValidationResult(
                validator_name="temporal_aggregation",
                is_valid=True,  # Fail open
                reasoning=f"Validation error: {e}",
            )
    
    def validate_comparison_dimension(
        self,
        question: str,
        sql: str,
        entities: List[Dict[str, Any]]
    ) -> ValidationResult:
        """
        Validate comparison query structure.
        
        Checks if queries comparing "X between A and B" include the
        comparison dimension in SELECT and GROUP BY.
        """
        logger.info("[integrity-validator] Running comparison dimension check")
        
        # Check cache
        cache_key = f"{question}:{sql}:comparison"
        if self.enable_cache and self.cache:
            cached = self.cache.get("integrity_comparison", cache_key, version=self.CACHE_VERSION)
            if cached:
                logger.debug("[integrity-validator] Cache hit for comparison check")
                return cached
        
        prompt = f"""TASK: Validate comparison query structure.

USER QUESTION: {question}
GENERATED SQL: {sql}
ENTITIES: {json.dumps(entities, indent=2)}

VALIDATION RULES:
1. If question compares "X between A and B" → column for A/B must be in SELECT
2. Comparison dimension must be in GROUP BY
3. Query must return separate rows for each comparison value

CHECK:
- Does question request comparison? (compare, between, vs, versus)
- If yes, what is being compared? (e.g., equity vs bond → fund_type)
- Is comparison dimension in SELECT clause?
- Is comparison dimension in GROUP BY clause?
- Will query return comparable results?

Return JSON:
{{
    "is_valid": true/false,
    "comparison_detected": true/false,
    "comparison_dimension": "column_name or null",
    "in_select": true/false,
    "in_group_by": true/false,
    "issues": ["issue 1"],
    "suggestions": ["Add fund_type to SELECT and GROUP BY for comparison"],
    "severity": "high/medium/low",
    "reasoning": "brief explanation"
}}"""
        
        try:
            result_text = self._call_llm(prompt)
            result = json.loads(result_text)
            
            validation = ValidationResult(
                validator_name="comparison_dimension",
                is_valid=result.get("is_valid", True),
                issues=result.get("issues", []),
                suggestions=result.get("suggestions", []),
                severity=result.get("severity", "medium"),
                reasoning=result.get("reasoning", ""),
                metadata={
                    "comparison_detected": result.get("comparison_detected", False),
                    "comparison_dimension": result.get("comparison_dimension"),
                    "in_select": result.get("in_select", False),
                    "in_group_by": result.get("in_group_by", False),
                },
            )
            
            # Cache result
            if self.enable_cache and self.cache:
                self.cache.set("integrity_comparison", validation, cache_key, version=self.CACHE_VERSION)
            
            logger.info(
                f"[integrity-validator] Comparison check: "
                f"{'✓ PASS' if validation.is_valid else '✗ FAIL'} "
                f"({len(validation.issues)} issues)"
            )
            
            return validation
        
        except Exception as e:
            logger.warning(f"[integrity-validator] Comparison validation failed: {e}")
            return ValidationResult(
                validator_name="comparison_dimension",
                is_valid=True,  # Fail open
                reasoning=f"Validation error: {e}",
            )
    
    def validate_ranking_query(
        self,
        question: str,
        sql: str,
        intent: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate ranking query structure.
        
        Checks if queries requesting "top N" or "best" have proper
        ORDER BY and LIMIT clauses.
        """
        logger.info("[integrity-validator] Running ranking query check")
        
        # Check cache
        cache_key = f"{question}:{sql}:ranking"
        if self.enable_cache and self.cache:
            cached = self.cache.get("integrity_ranking", cache_key, version=self.CACHE_VERSION)
            if cached:
                logger.debug("[integrity-validator] Cache hit for ranking check")
                return cached
        
        prompt = f"""TASK: Validate ranking query structure.

USER QUESTION: {question}
GENERATED SQL: {sql}
INTENT TYPE: {intent.get('type', 'unknown')}

VALIDATION RULES:
1. Ranking queries must have ORDER BY clause
2. Must have LIMIT clause (explicit or implicit from "top N")
3. ORDER BY direction must match intent (DESC for top/highest, ASC for bottom/lowest)

CHECK:
- Does question request ranking? (top, best, highest, lowest, worst, top-rated)
- If yes, does SQL have ORDER BY?
- Does SQL have LIMIT?
- Is ORDER BY direction correct?
- Does LIMIT match requested count?

Return JSON:
{{
    "is_valid": true/false,
    "ranking_detected": true/false,
    "has_order_by": true/false,
    "has_limit": true/false,
    "order_direction": "ASC/DESC/null",
    "expected_direction": "ASC/DESC/null",
    "limit_value": number or null,
    "issues": ["issue 1"],
    "suggestions": ["Add ORDER BY column DESC LIMIT N"],
    "severity": "high/medium/low",
    "reasoning": "brief explanation"
}}"""
        
        try:
            result_text = self._call_llm(prompt)
            result = json.loads(result_text)
            
            validation = ValidationResult(
                validator_name="ranking_query",
                is_valid=result.get("is_valid", True),
                issues=result.get("issues", []),
                suggestions=result.get("suggestions", []),
                severity=result.get("severity", "medium"),
                reasoning=result.get("reasoning", ""),
                metadata={
                    "ranking_detected": result.get("ranking_detected", False),
                    "has_order_by": result.get("has_order_by", False),
                    "has_limit": result.get("has_limit", False),
                    "order_direction": result.get("order_direction"),
                    "limit_value": result.get("limit_value"),
                },
            )
            
            # Cache result
            if self.enable_cache and self.cache:
                self.cache.set("integrity_ranking", validation, cache_key, version=self.CACHE_VERSION)
            
            logger.info(
                f"[integrity-validator] Ranking check: "
                f"{'✓ PASS' if validation.is_valid else '✗ FAIL'} "
                f"({len(validation.issues)} issues)"
            )
            
            return validation
        
        except Exception as e:
            logger.warning(f"[integrity-validator] Ranking validation failed: {e}")
            return ValidationResult(
                validator_name="ranking_query",
                is_valid=True,  # Fail open
                reasoning=f"Validation error: {e}",
            )
    
    def validate_time_filters(
        self,
        question: str,
        sql: str
    ) -> ValidationResult:
        """
        Validate temporal filter implementation.
        
        Checks if queries mentioning time periods have proper WHERE clauses
        with date filters.
        """
        logger.info("[integrity-validator] Running time filter check")
        
        # Check cache
        cache_key = f"{question}:{sql}:timefilter"
        if self.enable_cache and self.cache:
            cached = self.cache.get("integrity_timefilter", cache_key, version=self.CACHE_VERSION)
            if cached:
                logger.debug("[integrity-validator] Cache hit for time filter check")
                return cached
        
        prompt = f"""TASK: Validate temporal filters in SQL query.

USER QUESTION: {question}
GENERATED SQL: {sql}

VALIDATION RULES:
1. Year ranges ("over 2024", "in 2024") → date >= 'YYYY-01-01' AND date < 'YYYY+1-01-01'
2. Quarters ("Q1 2025") → BETWEEN or EXTRACT(QUARTER) = N
3. Relative dates ("last 12 months") → date >= CURRENT_DATE - INTERVAL

CHECK:
- Does question mention time periods?
- If yes, what type? (year range, quarter, relative, specific date)
- Does SQL have appropriate WHERE clause with date filter?
- Is the filter correctly formatted?

Return JSON:
{{
    "is_valid": true/false,
    "time_filter_detected": true/false,
    "filter_type": "year_range/quarter/relative/specific_date/null",
    "has_where_clause": true/false,
    "filter_correct": true/false,
    "issues": ["issue 1"],
    "suggestions": ["Add WHERE payment_date >= '2024-01-01' AND payment_date < '2025-01-01'"],
    "severity": "high/medium/low",
    "reasoning": "brief explanation"
}}"""
        
        try:
            result_text = self._call_llm(prompt)
            result = json.loads(result_text)
            
            validation = ValidationResult(
                validator_name="time_filters",
                is_valid=result.get("is_valid", True),
                issues=result.get("issues", []),
                suggestions=result.get("suggestions", []),
                severity=result.get("severity", "medium"),
                reasoning=result.get("reasoning", ""),
                metadata={
                    "time_filter_detected": result.get("time_filter_detected", False),
                    "filter_type": result.get("filter_type"),
                    "has_where_clause": result.get("has_where_clause", False),
                    "filter_correct": result.get("filter_correct", False),
                },
            )
            
            # Cache result
            if self.enable_cache and self.cache:
                self.cache.set("integrity_timefilter", validation, cache_key, version=self.CACHE_VERSION)
            
            logger.info(
                f"[integrity-validator] Time filter check: "
                f"{'✓ PASS' if validation.is_valid else '✗ FAIL'} "
                f"({len(validation.issues)} issues)"
            )
            
            return validation
        
        except Exception as e:
            logger.warning(f"[integrity-validator] Time filter validation failed: {e}")
            return ValidationResult(
                validator_name="time_filters",
                is_valid=True,  # Fail open
                reasoning=f"Validation error: {e}",
            )
    
    def validate_semantic_coherence(
        self,
        question: str,
        sql: str,
        intent: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate semantic coherence between question and SQL.
        
        Checks if SQL logically answers the question asked.
        """
        logger.info("[integrity-validator] Running semantic coherence check")
        
        # Check cache
        cache_key = f"{question}:{sql}:semantic"
        if self.enable_cache and self.cache:
            cached = self.cache.get("integrity_semantic", cache_key, version=self.CACHE_VERSION)
            if cached:
                logger.debug("[integrity-validator] Cache hit for semantic check")
                return cached
        
        prompt = f"""TASK: Validate semantic coherence between question and SQL.

USER QUESTION: {question}
GENERATED SQL: {sql}
INTENT: {json.dumps(intent, indent=2)}

VALIDATION RULES:
1. SQL must answer the question asked
2. Selected columns must match requested information
3. Filters must align with question constraints
4. Aggregations must match requested metrics

CHECK:
- What information does the question request?
- Does SQL SELECT the right columns?
- Are all question constraints in WHERE clause?
- Do aggregations match what was asked?
- Will SQL return meaningful results?

Return JSON:
{{
    "is_valid": true/false,
    "semantic_match": true/false,
    "missing_columns": ["column1"],
    "extra_columns": ["column2"],
    "missing_filters": ["filter1"],
    "wrong_aggregations": ["agg1"],
    "issues": ["issue 1"],
    "suggestions": ["suggestion 1"],
    "severity": "high/medium/low",
    "reasoning": "brief explanation"
}}"""
        
        try:
            result_text = self._call_llm(prompt)
            result = json.loads(result_text)
            
            validation = ValidationResult(
                validator_name="semantic_coherence",
                is_valid=result.get("is_valid", True),
                issues=result.get("issues", []),
                suggestions=result.get("suggestions", []),
                severity=result.get("severity", "medium"),
                reasoning=result.get("reasoning", ""),
                metadata={
                    "semantic_match": result.get("semantic_match", True),
                    "missing_columns": result.get("missing_columns", []),
                    "extra_columns": result.get("extra_columns", []),
                    "missing_filters": result.get("missing_filters", []),
                    "wrong_aggregations": result.get("wrong_aggregations", []),
                },
            )
            
            # Cache result
            if self.enable_cache and self.cache:
                self.cache.set("integrity_semantic", validation, cache_key, version=self.CACHE_VERSION)
            
            logger.info(
                f"[integrity-validator] Semantic check: "
                f"{'✓ PASS' if validation.is_valid else '✗ FAIL'} "
                f"({len(validation.issues)} issues)"
            )
            
            return validation
        
        except Exception as e:
            logger.warning(f"[integrity-validator] Semantic validation failed: {e}")
            return ValidationResult(
                validator_name="semantic_coherence",
                is_valid=True,  # Fail open
                reasoning=f"Validation error: {e}",
            )
    
    def validate_column_order(
        self,
        question: str,
        sql: str,
        intent: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate logical column ordering in SELECT clause.
        
        Checks if columns follow logical order:
        1. Identifiers (IDs, keys)
        2. Descriptive (names, titles)
        3. Categorical (types, statuses)
        4. Temporal (dates)
        5. Metrics (aggregations)
        """
        logger.info("[integrity-validator] Running column order check")
        
        # Check cache
        cache_key = f"{question}:{sql}:column_order"
        if self.enable_cache and self.cache:
            cached = self.cache.get("integrity_column_order", cache_key, version=self.CACHE_VERSION)
            if cached:
                logger.debug("[integrity-validator] Cache hit for column order check")
                return cached
        
        prompt = f"""TASK: Validate column ordering in SQL SELECT clause.

USER QUESTION: {question}
GENERATED SQL: {sql}
INTENT: {json.dumps(intent, indent=2)}

LOGICAL COLUMN ORDER RULES:
1. Identifiers first (IDs, keys) - only if needed for context
2. Descriptive columns (names, titles, descriptions)
3. Categorical dimensions (types, categories, statuses)
4. Temporal columns (dates, timestamps)
5. Metrics last (counts, sums, averages, aggregations)

CHECK:
- Extract columns from SELECT clause
- Classify each column by type (identifier/descriptive/categorical/temporal/metric)
- Check if order follows logical rules
- Identify any out-of-order columns

Return JSON:
{{
    "is_valid": true/false,
    "current_order": ["col1", "col2", ...],
    "column_types": {{"col1": "identifier", "col2": "metric", ...}},
    "suggested_order": ["col1", "col2", ...],
    "issues": ["Metrics appear before dimensions"],
    "suggestions": ["Move total_fees to end of SELECT"],
    "severity": "low/medium",
    "reasoning": "brief explanation"
}}"""
        
        try:
            result_text = self._call_llm(prompt)
            result = json.loads(result_text)
            
            validation = ValidationResult(
                validator_name="column_order",
                is_valid=result.get("is_valid", True),
                issues=result.get("issues", []),
                suggestions=result.get("suggestions", []),
                severity=result.get("severity", "low"),
                reasoning=result.get("reasoning", ""),
                metadata={
                    "current_order": result.get("current_order", []),
                    "column_types": result.get("column_types", {}),
                    "suggested_order": result.get("suggested_order", []),
                },
            )
            
            # Cache result
            if self.enable_cache and self.cache:
                self.cache.set("integrity_column_order", validation, cache_key, version=self.CACHE_VERSION)
            
            logger.info(
                f"[integrity-validator] Column order check: "
                f"{'✓ PASS' if validation.is_valid else '✗ FAIL'} "
                f"({len(validation.issues)} issues)"
            )
            
            return validation
        
        except Exception as e:
            logger.warning(f"[integrity-validator] Column order validation failed: {e}")
            return ValidationResult(
                validator_name="column_order",
                is_valid=True,  # Fail open
                reasoning=f"Validation error: {e}",
            )
    
    def add_refinement_history(
        self,
        question: str,
        issue_type: str,
        original_sql: str,
        refined_sql: str,
        issues: List[str]
    ) -> None:
        """
        Add successful refinement to history for learning.
        
        Args:
            question: Original user question
            issue_type: Type of issue fixed (temporal, comparison, etc.)
            original_sql: Original incorrect SQL
            refined_sql: Corrected SQL
            issues: List of issues that were fixed
        """
        record = RefinementRecord(
            question=question,
            issue_type=issue_type,
            original_sql=original_sql,
            refined_sql=refined_sql,
            issues=issues
        )
        
        self.refinement_history.append(record)
        
        # Trim history if too large
        if len(self.refinement_history) > self.max_history:
            self.refinement_history.pop(0)
        
        logger.info(
            f"[integrity-validator] Added refinement to history: "
            f"issue_type={issue_type}, history_size={len(self.refinement_history)}"
        )
    
    def get_refinement_examples(
        self,
        issue_type: str,
        question: str,
        limit: int = 2
    ) -> List[RefinementRecord]:
        """
        Get relevant refinement examples for learning.
        
        Args:
            issue_type: Type of issue to get examples for
            question: Current question (for similarity matching)
            limit: Maximum number of examples to return
            
        Returns:
            List of relevant refinement records
        """
        # Filter by issue type
        relevant = [
            r for r in self.refinement_history
            if r.issue_type == issue_type
        ]
        
        # Sort by success count and recency
        relevant.sort(
            key=lambda r: (r.success_count, r.timestamp),
            reverse=True
        )
        
        return relevant[:limit]
    
    def format_refinement_history(
        self,
        examples: List[RefinementRecord]
    ) -> str:
        """
        Format refinement history for inclusion in prompts.
        
        Args:
            examples: List of refinement examples
            
        Returns:
            Formatted string for prompt inclusion
        """
        if not examples:
            return ""
        
        formatted = "PREVIOUS SUCCESSFUL REFINEMENTS (for reference):\n\n"
        
        for i, example in enumerate(examples, 1):
            formatted += f"Example {i}:\n"
            formatted += f"  Question: {example.question}\n"
            formatted += f"  Issues: {', '.join(example.issues)}\n"
            formatted += f"  Original SQL: {example.original_sql[:100]}...\n"
            formatted += f"  Fixed SQL: {example.refined_sql[:100]}...\n"
            formatted += f"  Success count: {example.success_count}\n\n"
        
        return formatted
    
    def validate_schema_references(
        self,
        question: str,
        sql: str,
        entities: List[Dict[str, Any]]
    ) -> ValidationResult:
        """
        Validate that all table and column references in SQL exist in discovered entities.
        
        Uses LLM to extract references (handles CTEs, subqueries, nested queries),
        then validates against entity metadata.
        
        Args:
            question: Original user question
            sql: Generated SQL query
            entities: Discovered entities with schema information
            
        Returns:
            ValidationResult with schema validation status
        """
        logger.info("[integrity-validator] Running schema reference check")
        
        # Check cache
        cache_key = f"{question}:{sql}:schema_refs"
        if self.enable_cache and self.cache:
            cached = self.cache.get("integrity_schema_refs", cache_key, version=self.CACHE_VERSION)
            if cached:
                logger.debug("[integrity-validator] Cache hit for schema reference check")
                return cached
        
        # Build valid references from entities
        valid_tables = set()
        valid_columns = {}  # table -> set of columns
        
        for entity in entities:
            table = entity.get('table')
            column = entity.get('column')
            
            if table:
                valid_tables.add(table)
                
                if column:
                    if table not in valid_columns:
                        valid_columns[table] = set()
                    valid_columns[table].add(column)
                
                # Also get columns from semantic match metadata
                top_match = entity.get('top_match', {})
                metadata = top_match.get('metadata', {})
                
                # If this is a table entity, get all its columns
                if entity.get('entity_type') == 'table' and 'columns' in metadata:
                    if table not in valid_columns:
                        valid_columns[table] = set()
                    for col_info in metadata.get('columns', []):
                        if isinstance(col_info, dict):
                            valid_columns[table].add(col_info.get('name'))
                        else:
                            valid_columns[table].add(col_info)
        
        # Use LLM to extract all table.column references from SQL
        prompt = f"""TASK: Extract all table and column references from SQL query.

SQL QUERY:
{sql}

INSTRUCTIONS:
Extract ALL table and column references, including:
- Main query SELECT, FROM, WHERE, GROUP BY, HAVING, ORDER BY
- JOIN clauses
- Subqueries
- CTEs (WITH clauses)
- Nested queries

CRITICAL: Resolve table aliases to actual table names!
- If SQL uses "FROM funds f", the table is "funds" (not "f")
- If SQL uses "f.fund_name", map it to "funds.fund_name"
- If SQL uses "fm.manager_name", map it to "fund_managers.manager_name"

Return JSON with ACTUAL table names (not aliases):
{{
    "tables": ["table1", "table2", ...],
    "columns": {{
        "table1": ["col1", "col2", ...],
        "table2": ["col3", "col4", ...]
    }}
}}

Example 1 (with aliases):
SQL: SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id
Result:
{{
    "tables": ["users", "orders"],
    "columns": {{
        "users": ["name", "id"],
        "orders": ["total", "user_id"]
    }}
}}

Example 2 (no aliases):
SQL: SELECT users.name, orders.total FROM users JOIN orders ON users.id = orders.user_id
Result:
{{
    "tables": ["users", "orders"],
    "columns": {{
        "users": ["name", "id"],
        "orders": ["total", "user_id"]
    }}
}}
"""
        
        try:
            result_text = self._call_llm(prompt)
            result = json.loads(result_text)
            
            sql_tables = set(result.get("tables", []))
            sql_columns = result.get("columns", {})
            
            # Validate tables
            invalid_tables = sql_tables - valid_tables
            
            # Validate columns (only for tables where we have column info)
            invalid_columns = []
            for table, columns in sql_columns.items():
                if table not in valid_tables:
                    # Table itself is invalid, already captured
                    continue
                
                # IMPORTANT: Only validate if we have explicit column information for this table
                # Don't flag columns as invalid just because we don't have info - avoid false positives
                if table not in valid_columns or len(valid_columns[table]) == 0:
                    logger.debug(
                        f"[integrity-validator] No column info for table '{table}', skipping column validation (avoid false positives)"
                    )
                    continue
                
                # Only validate columns if we have a reasonably complete column list
                # (i.e., more than just 1-2 columns which might be incomplete)
                if len(valid_columns[table]) < 3:
                    logger.debug(
                        f"[integrity-validator] Limited column info for table '{table}' ({len(valid_columns[table])} columns), skipping validation"
                    )
                    continue
                
                for column in columns:
                    if column not in valid_columns[table]:
                        invalid_columns.append(f"{table}.{column}")
            
            # Build issues and suggestions
            issues = []
            suggestions = []
            
            if invalid_tables:
                for table in invalid_tables:
                    issues.append(f"Table '{table}' not found in discovered entities")
                    # Suggest similar table names
                    similar = self._find_similar_name(table, valid_tables)
                    if similar:
                        suggestions.append(f"Did you mean table '{similar}'?")
            
            if invalid_columns:
                for col_ref in invalid_columns:
                    issues.append(f"Column '{col_ref}' does not exist in schema")
                    # Suggest similar column names
                    table, column = col_ref.split('.')
                    if table in valid_columns:
                        similar = self._find_similar_name(column, valid_columns[table])
                        if similar:
                            suggestions.append(f"Did you mean '{table}.{similar}'?")
            
            is_valid = len(issues) == 0
            
            validation = ValidationResult(
                validator_name="schema_references",
                is_valid=is_valid,
                issues=issues,
                suggestions=suggestions,
                severity="high" if not is_valid else "low",
                reasoning=f"Validated {len(sql_tables)} tables and {sum(len(cols) for cols in sql_columns.values())} column references",
                metadata={
                    "sql_tables": list(sql_tables),
                    "sql_columns": sql_columns,
                    "invalid_tables": list(invalid_tables),
                    "invalid_columns": invalid_columns,
                }
            )
            
            # Cache result
            if self.enable_cache and self.cache:
                self.cache.set("integrity_schema_refs", validation, cache_key, version=self.CACHE_VERSION)
            
            logger.info(
                f"[integrity-validator] Schema reference check: "
                f"{'✓ PASS' if validation.is_valid else '✗ FAIL'} "
                f"({len(issues)} issues)"
            )
            
            return validation
        
        except Exception as e:
            logger.warning(f"[integrity-validator] Schema reference validation failed: {e}")
            return ValidationResult(
                validator_name="schema_references",
                is_valid=True,  # Fail open
                reasoning=f"Validation error: {e}",
            )
    
    def _find_similar_name(self, name: str, candidates: set) -> Optional[str]:
        """
        Find similar name in candidates using simple string similarity.
        
        Args:
            name: Name to find similar match for
            candidates: Set of candidate names
            
        Returns:
            Most similar name if similarity > 0.6, else None
        """
        if not candidates:
            return None
        
        name_lower = name.lower()
        best_match = None
        best_score = 0.0
        
        for candidate in candidates:
            candidate_lower = candidate.lower()
            
            # Simple similarity: ratio of common characters
            common = sum(1 for a, b in zip(name_lower, candidate_lower) if a == b)
            max_len = max(len(name_lower), len(candidate_lower))
            score = common / max_len if max_len > 0 else 0
            
            # Boost score if one is substring of other
            if name_lower in candidate_lower or candidate_lower in name_lower:
                score += 0.3
            
            if score > best_score:
                best_score = score
                best_match = candidate
        
        return best_match if best_score > 0.6 else None
    
    def validate_all_specific(
        self,
        question: str,
        sql: str,
        intent: Dict[str, Any],
        entities: List[Dict[str, Any]]
    ) -> Dict[str, ValidationResult]:
        """
        Run all specific validators.
        
        Returns:
            Dictionary mapping validator name to ValidationResult
        """
        logger.info("[integrity-validator] Running all specific checks")
        
        results = {}
        
        # Selective validation based on intent
        if self.enable_selective_validation:
            # TEMPORARILY DISABLED: Schema validator has false positives due to incomplete entity info
            # TODO: Re-enable when we can pass full schema from knowledge graph
            # results['schema'] = self.validate_schema_references(question, sql, entities)
            
            # Always run semantic check
            results['semantic'] = self.validate_semantic_coherence(question, sql, intent)
            
            # Run temporal check if time-related
            if intent.get('time_scope') and intent.get('time_scope') != 'none':
                results['temporal'] = self.validate_temporal_aggregation(question, sql, intent)
                results['time_filter'] = self.validate_time_filters(question, sql)
            
            # Run comparison check if comparison intent
            if intent.get('type') == 'comparison':
                results['comparison'] = self.validate_comparison_dimension(question, sql, entities)
            
            # Run ranking check if ranking/top_n intent
            if intent.get('type') in ['ranking', 'top_n']:
                results['ranking'] = self.validate_ranking_query(question, sql, intent)
            
            # Always run column order check (low cost, high value)
            results['column_order'] = self.validate_column_order(question, sql, intent)
        else:
            # Run all validators
            # TEMPORARILY DISABLED: Schema validator
            # results['schema'] = self.validate_schema_references(question, sql, entities)
            results['temporal'] = self.validate_temporal_aggregation(question, sql, intent)
            results['comparison'] = self.validate_comparison_dimension(question, sql, entities)
            results['ranking'] = self.validate_ranking_query(question, sql, intent)
            results['time_filter'] = self.validate_time_filters(question, sql)
            results['semantic'] = self.validate_semantic_coherence(question, sql, intent)
            results['column_order'] = self.validate_column_order(question, sql, intent)
        
        # Log summary
        passed = sum(1 for r in results.values() if r.is_valid)
        failed = len(results) - passed
        logger.info(
            f"[integrity-validator] Specific checks complete: "
            f"{passed} passed, {failed} failed (out of {len(results)} run)"
        )
        
        return results
    
    def validate_full_integrity(
        self,
        question: str,
        sql: str,
        intent: Dict[str, Any],
        specific_results: Dict[str, ValidationResult]
    ) -> HolisticValidationResult:
        """
        Final holistic validation of query integrity.
        
        Reviews all specific validation results and performs comprehensive
        assessment of overall query quality.
        """
        logger.info("[integrity-validator] Running final holistic validation")
        
        # Prepare specific results summary
        results_summary = {}
        for name, result in specific_results.items():
            results_summary[name] = {
                "valid": result.is_valid,
                "issues": result.issues,
                "suggestions": result.suggestions,
                "severity": result.severity,
            }
        
        prompt = f"""TASK: Final holistic validation of SQL query integrity.

USER QUESTION: {question}
GENERATED SQL: {sql}
INTENT: {json.dumps(intent, indent=2)}

SPECIFIC VALIDATION RESULTS:
{json.dumps(results_summary, indent=2)}

HOLISTIC CHECKS:
1. Does SQL comprehensively answer the question?
2. Are all specific validations passing or acceptable?
3. Is query structure sound and efficient?
4. Will query return meaningful results?
5. Are there any conflicting requirements?
6. Is SQL idiomatic and follows best practices?

OVERALL ASSESSMENT:
- Review all specific validation results
- Check for any missed issues
- Verify query completeness
- Assess query quality

Return JSON:
{{
    "is_valid": true/false,
    "overall_quality": "excellent/good/acceptable/poor",
    "critical_issues": ["issue 1"],
    "warnings": ["warning 1"],
    "suggestions": ["suggestion 1"],
    "confidence": 0.0-1.0,
    "reasoning": "detailed explanation"
}}"""
        
        try:
            result_text = self._call_llm(prompt)
            result = json.loads(result_text)
            
            passed = sum(1 for r in specific_results.values() if r.is_valid)
            failed = len(specific_results) - passed
            
            validation = HolisticValidationResult(
                is_valid=result.get("is_valid", True),
                overall_quality=result.get("overall_quality", "acceptable"),
                specific_checks_passed=passed,
                specific_checks_failed=failed,
                critical_issues=result.get("critical_issues", []),
                warnings=result.get("warnings", []),
                suggestions=result.get("suggestions", []),
                confidence=result.get("confidence", 1.0),
                reasoning=result.get("reasoning", ""),
            )
            
            logger.info(
                f"[integrity-validator] Holistic validation: "
                f"{'✓ PASS' if validation.is_valid else '✗ FAIL'} "
                f"(quality={validation.overall_quality}, "
                f"confidence={validation.confidence:.2f})"
            )
            
            return validation
        
        except Exception as e:
            logger.warning(f"[integrity-validator] Holistic validation failed: {e}")
            passed = sum(1 for r in specific_results.values() if r.is_valid)
            failed = len(specific_results) - passed
            
            return HolisticValidationResult(
                is_valid=True,  # Fail open
                overall_quality="acceptable",
                specific_checks_passed=passed,
                specific_checks_failed=failed,
                reasoning=f"Validation error: {e}",
            )
