"""
SQL Generator - Converts query plans to executable SQL statements.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from reportsmith.schema_intelligence.knowledge_graph import SchemaKnowledgeGraph
from reportsmith.logger import get_logger
from reportsmith.query_processing.sql_validator import SQLValidator
from reportsmith.utils.cache_manager import get_cache_manager

from reportsmith.query_processing.sql_generation import (
    SQLColumn,
    SQLJoin,
    SQLQuery,
    IntentType,
    AggregationType,
    SelectBuilder,
    JoinBuilder,
    FilterBuilder,
    ModifiersBuilder,
    ContextEnricher,
)

logger = get_logger(__name__)


class SQLGenerator:
    """
    Generates SQL queries from query plans and entity metadata.

    Responsibilities:
    - Orchestrates SQL generation using specialized builders
    - Manages higher-level logic like validation and explanation
    """

    def __init__(
        self,
        knowledge_graph: SchemaKnowledgeGraph,
        llm_client=None,
        enable_extraction_enhancement: bool = True,
        enable_cache: bool = True,
        fail_on_llm_error: bool = False,
    ):
        self.kg = knowledge_graph
        self.llm_client = llm_client
        self.enable_cache = enable_cache
        self.cache = get_cache_manager() if enable_cache else None
        
        # Initialize sub-components
        self.select_builder = SelectBuilder(knowledge_graph)
        self.join_builder = JoinBuilder()
        self.filter_builder = FilterBuilder(knowledge_graph)
        self.modifiers_builder = ModifiersBuilder()
        self.context_enricher = ContextEnricher(
            knowledge_graph, 
            llm_client, 
            self.cache, 
            fail_on_llm_error
        )

        # Initialize SQL validator
        self.validator = None
        if llm_client and enable_extraction_enhancement:
            self.validator = SQLValidator(
                llm_client=llm_client,
                max_iterations=10,
                sample_size=10,
                enable_cache=enable_cache,
            )
            logger.info("[sql-gen] SQL validator initialized")

    def generate(
        self,
        *,
        question: str,
        intent: Dict[str, Any],
        entities: List[Dict[str, Any]],
        plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate SQL query from query plan and entities."""
        logger.info(f"[sql-gen] generating SQL for question: '{question}'")

        try:
            intent_type = intent.get("type", "list")
            aggregations = intent.get("aggregations", [])
            filters = intent.get("filters", [])

            # 1. Build SELECT columns
            select_columns = self.select_builder.build_select_columns(
                entities, aggregations, intent_type
            )

            # 2. Enrich with context (LLM)
            if self.llm_client:
                select_columns = self.context_enricher.enrich_with_context_columns(
                    question=question,
                    intent_type=intent_type,
                    select_columns=select_columns,
                    plan=plan,
                    entities=entities,
                    filters=filters,
                )
                
                select_columns = self.context_enricher.refine_column_transformations(
                    question=question,
                    intent_type=intent_type,
                    select_columns=select_columns,
                )

            # 3. Apply column ordering (Validator/LLM)
            column_ordering = None
            if self.validator:
                column_metadata = [
                    {
                        "table": col.table,
                        "column": col.column,
                        "aggregation": col.aggregation,
                        "alias": col.alias,
                    }
                    for col in select_columns
                ]
                column_ordering = self.validator.determine_column_order(
                    question=question,
                    columns=column_metadata,
                    intent_type=intent_type,
                )
                
                if column_ordering and column_ordering.ordered_columns:
                    logger.info(f"[sql-gen] applying LLM column ordering: {len(column_ordering.ordered_columns)} columns")
                    select_columns = self.context_enricher.apply_column_ordering(
                        select_columns, 
                        column_ordering.ordered_columns
                    )

            # 4. Build other clauses
            from_table, joins = self.join_builder.build_from_and_joins(plan)
            all_conditions = self.filter_builder.build_where_conditions(entities, filters)
            
            # Fix any invalid column references in conditions
            all_conditions = [
                self.filter_builder.fix_column_references(cond) 
                for cond in all_conditions
            ]
            
            # Separate WHERE and HAVING conditions (aggregations must go to HAVING)
            where_conditions, having_conditions = self.filter_builder.separate_having_conditions(all_conditions)
            
            group_by = self.modifiers_builder.build_group_by(select_columns)
            order_by = self.modifiers_builder.build_order_by(select_columns, intent_type)
            limit = self.modifiers_builder.determine_limit(intent_type, intent.get("limit"))

            # 5. Construct Query
            sql_query = SQLQuery(
                select_columns=select_columns,
                from_table=from_table,
                joins=joins,
                where_conditions=where_conditions,
                group_by=group_by,
                having_conditions=having_conditions,
                order_by=order_by,
                limit=limit,
            )

            sql_text = sql_query.to_sql()
            logger.info(f"[sql-gen] generated SQL ({len(sql_text)} chars)")
            logger.debug(f"[sql-gen] SQL:\n{sql_text}")

            # 6. Build Explanation
            explanation = self._build_explanation(
                question=question,
                intent_type=intent_type,
                select_columns=select_columns,
                joins=joins,
                where_conditions=where_conditions,
            )

            # 7. Generate Summary (Validator)
            extraction_summary = None
            if self.validator:
                extraction_summary = self.validator.generate_summary(
                    question=question,
                    sql=sql_text,
                    entities=entities,
                    filters=filters,
                )

            return {
                "sql": sql_text,
                "explanation": explanation,
                "metadata": {
                    "intent_type": intent_type,
                    "tables": plan.get("tables", []),
                    "join_count": len(joins),
                    "where_count": len(where_conditions),
                    "aggregations": aggregations,
                    "columns_count": len(select_columns),
                },
                "extraction_summary": (
                    {
                        "summary": extraction_summary.summary,
                        "filters_applied": extraction_summary.filters_applied,
                        "transformations": extraction_summary.transformations,
                        "assumptions": extraction_summary.assumptions,
                    }
                    if extraction_summary
                    else None
                ),
                "column_ordering": (
                    {
                        "ordered_columns": column_ordering.ordered_columns,
                        "reasoning": column_ordering.reasoning,
                    }
                    if column_ordering
                    else None
                ),
            }

        except Exception as e:
            logger.error(f"[sql-gen] failed: {e}", exc_info=True)
            raise

    def _build_explanation(
        self,
        *,
        question: str,
        intent_type: str,
        select_columns: List[SQLColumn],
        joins: List[SQLJoin],
        where_conditions: List[str],
    ) -> str:
        """Build human-readable explanation of the SQL query"""
        parts = []

        parts.append(f"Query Intent: {intent_type}")
        parts.append(f"Question: '{question}'")
        parts.append("")

        # Columns
        parts.append("Selected Columns:")
        for col in select_columns:
            desc = f"  - {col.table}.{col.column}"
            if col.aggregation:
                desc += f" ({col.aggregation.upper()})"
            if col.alias and col.alias != col.column:
                desc += f" as '{col.alias}'"
            parts.append(desc)
        parts.append("")

        # Joins
        if joins:
            parts.append("Joins:")
            for join in joins:
                parts.append(f"  - {join.join_type} JOIN {join.table}")
                parts.append(f"    ON {join.on_condition}")
            parts.append("")

        # Filters
        if where_conditions:
            parts.append("Filters:")
            for cond in where_conditions:
                parts.append(f"  - {cond}")
            parts.append("")

        return "\n".join(parts)
