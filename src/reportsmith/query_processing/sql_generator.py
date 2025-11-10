"""
SQL Generator - Converts query plans to executable SQL statements.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import re
import difflib

from reportsmith.schema_intelligence.knowledge_graph import SchemaKnowledgeGraph
from reportsmith.logger import get_logger
from reportsmith.query_processing.sql_validator import SQLValidator
from reportsmith.utils.cache_manager import get_cache_manager

logger = get_logger(__name__)


class AggregationType(str, Enum):
    """Supported aggregation types"""

    SUM = "sum"
    AVG = "avg"
    COUNT = "count"
    MIN = "min"
    MAX = "max"
    COUNT_DISTINCT = "count_distinct"


class IntentType(str, Enum):
    """Query intent types"""

    LIST = "list"
    AGGREGATE = "aggregate"
    COMPARISON = "comparison"
    TREND = "trend"
    TOP_N = "top_n"


@dataclass
class SQLColumn:
    """Represents a column in SQL query"""

    table: str
    column: str
    alias: Optional[str] = None
    aggregation: Optional[str] = None
    transformation: Optional[str] = (
        None  # SQL expression for transformation (e.g., "EXTRACT(MONTH FROM table.column)")
    )

    def to_sql(self) -> str:
        """Convert to SQL column expression"""
        # If transformation is specified, use it instead of table.column
        if self.transformation:
            base_expr = self.transformation
        elif self.aggregation:
            col_ref = f"{self.table}.{self.column}"
            agg_expr = f"{self.aggregation.upper()}({col_ref})"
            return f"{agg_expr} AS {self.alias or self.column}"
        else:
            col_ref = f"{self.table}.{self.column}"
            return (
                f"{col_ref} AS {self.alias or self.column}" if self.alias else col_ref
            )

        # For transformations, apply aggregation if specified
        if self.aggregation:
            agg_expr = f"{self.aggregation.upper()}({base_expr})"
            return f"{agg_expr} AS {self.alias or self.column}"
        else:
            return f"{base_expr} AS {self.alias or self.column}"


@dataclass
class SQLJoin:
    """Represents a JOIN clause"""

    table: str
    join_type: str  # INNER, LEFT, RIGHT, etc.
    on_condition: str

    def to_sql(self) -> str:
        """Convert to SQL JOIN clause"""
        return f"{self.join_type} JOIN {self.table} ON {self.on_condition}"


@dataclass
class SQLQuery:
    """Represents a complete SQL query"""

    select_columns: List[SQLColumn]
    from_table: str
    joins: List[SQLJoin]
    where_conditions: List[str]
    group_by: List[str]
    having_conditions: List[str]
    order_by: List[Tuple[str, str]]  # [(column, direction)]
    limit: Optional[int] = None

    def to_sql(self) -> str:
        """Generate complete SQL statement"""
        parts = []

        # SELECT clause
        select_cols = ",\n       ".join(col.to_sql() for col in self.select_columns)
        parts.append(f"SELECT {select_cols}")

        # FROM clause
        parts.append(f"  FROM {self.from_table}")

        # JOINs
        for join in self.joins:
            parts.append(f"  {join.to_sql()}")

        # WHERE clause
        if self.where_conditions:
            where_clause = "\n   AND ".join(self.where_conditions)
            parts.append(f" WHERE {where_clause}")

        # GROUP BY
        if self.group_by:
            group_clause = ", ".join(self.group_by)
            parts.append(f" GROUP BY {group_clause}")

        # HAVING
        if self.having_conditions:
            having_clause = "\n   AND ".join(self.having_conditions)
            parts.append(f" HAVING {having_clause}")

        # ORDER BY
        if self.order_by:
            order_clause = ", ".join(
                f"{col} {direction}" for col, direction in self.order_by
            )
            parts.append(f" ORDER BY {order_clause}")

        # LIMIT
        if self.limit:
            parts.append(f" LIMIT {self.limit}")

        return "\n".join(parts)


class SQLGenerator:
    """
    Generates SQL queries from query plans and entity metadata.

    Responsibilities:
    - Build SELECT clause from entities (columns, aggregations)
    - Construct JOIN paths using knowledge graph relationships
    - Generate WHERE conditions from filters and domain values
    - Add GROUP BY, ORDER BY, LIMIT based on intent
    - Enrich with implicit context columns using LLM
    """

    def __init__(
        self,
        knowledge_graph: SchemaKnowledgeGraph,
        llm_client=None,
        enable_extraction_enhancement: bool = True,
        enable_cache: bool = True,
        fail_on_llm_error: bool = False,  # If True, raise exceptions on LLM failures instead of fallback
    ):
        self.kg = knowledge_graph
        self.llm_client = llm_client  # Optional LLM for column enrichment
        self.enable_cache = enable_cache
        self.cache = get_cache_manager() if enable_cache else None
        self.fail_on_llm_error = fail_on_llm_error  # Control LLM error behavior
        
        # Detect and store LLM provider/model info
        if llm_client:
            self.llm_provider = self._detect_llm_provider()
            self.llm_model = self._detect_llm_model()
            logger.info(f"[sql-gen] LLM client detected: {self.llm_provider}/{self.llm_model}")
        else:
            self.llm_provider = None
            self.llm_model = None

        # Initialize SQL validator if LLM client available
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
        """
        Generate SQL query from query plan and entities.

        Args:
            question: Original user question
            intent: Intent analysis result
            entities: Discovered entities with mappings
            plan: Query plan with tables and join paths

        Returns:
            Dict with SQL query, explanation, and metadata
        """
        logger.info(f"[sql-gen] generating SQL for question: '{question}'")

        try:
            # Extract intent details
            intent_type = intent.get("type", "list")
            aggregations = intent.get("aggregations", [])
            filters = intent.get("filters", [])

            # Build query components
            select_columns = self._build_select_columns(
                entities, aggregations, intent_type
            )

            # Enrich with implicit context columns using LLM
            if self.llm_client:
                select_columns = self._enrich_with_context_columns(
                    question=question,
                    intent_type=intent_type,
                    select_columns=select_columns,
                    entities=entities,
                    plan=plan,
                    filters=filters,
                )

                # Refine existing columns based on user query (e.g., timestamp -> month)
                select_columns = self._refine_column_transformations(
                    question=question,
                    intent_type=intent_type,
                    select_columns=select_columns,
                    entities=entities,
                )
            
            # Determine column ordering using LLM and reorder columns (FR-2)
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
                
                # Apply the ordering to select_columns
                if column_ordering and column_ordering.ordered_columns:
                    logger.info(f"[sql-gen] applying LLM column ordering: {len(column_ordering.ordered_columns)} columns")
                    select_columns = self._apply_column_ordering(
                        select_columns, 
                        column_ordering.ordered_columns
                    )
            else:
                column_ordering = None

            from_table, joins = self._build_from_and_joins(plan)
            where_conditions = self._build_where_conditions(entities, filters)
            group_by = self._build_group_by(select_columns, intent_type)
            order_by = self._build_order_by(select_columns, intent_type)
            limit = self._determine_limit(intent_type, intent.get("limit"))

            # Construct SQL query object
            sql_query = SQLQuery(
                select_columns=select_columns,
                from_table=from_table,
                joins=joins,
                where_conditions=where_conditions,
                group_by=group_by,
                having_conditions=[],
                order_by=order_by,
                limit=limit,
            )

            sql_text = sql_query.to_sql()

            logger.info(f"[sql-gen] generated SQL ({len(sql_text)} chars)")
            logger.debug(f"[sql-gen] SQL:\n{sql_text}")

            # Build explanation
            explanation = self._build_explanation(
                question=question,
                intent_type=intent_type,
                select_columns=select_columns,
                joins=joins,
                where_conditions=where_conditions,
            )

            # Generate extraction summary using LLM (FR-1)
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

    def _build_select_columns(
        self,
        entities: List[Dict[str, Any]],
        aggregations: List[str],
        intent_type: str,
    ) -> List[SQLColumn]:
        """Build SELECT column list from entities"""
        columns = []

        # Separate entities by type
        table_entities = [e for e in entities if e.get("entity_type") == "table"]
        column_entities = [e for e in entities if e.get("entity_type") == "column"]
        dimension_entities = [
            e for e in entities if e.get("entity_type") == "domain_value"
        ]

        # Determine if we need aggregation based on intent type and presence of aggregations
        needs_aggregation = (
            intent_type in ["aggregate", "comparison", "top_n"] or len(aggregations) > 0
        )

        # If we have explicit column entities, use them
        if column_entities:
            for ent in column_entities:
                table = ent.get("table")
                column = ent.get("column")
                if not table or not column:
                    # Try to extract from top_match metadata
                    md = (ent.get("top_match") or {}).get("metadata") or {}
                    table = table or md.get("table")
                    column = column or md.get("column")

                if table and column:
                    # Check if this column needs aggregation
                    agg = None
                    if needs_aggregation:
                        # For numeric columns, apply first aggregation
                        # (More sophisticated logic could match specific aggs to specific columns)
                        md = (ent.get("top_match") or {}).get("metadata") or {}
                        data_type = md.get("data_type", "").lower()
                        if data_type in [
                            "numeric",
                            "integer",
                            "decimal",
                            "float",
                            "double",
                            "money",
                        ]:
                            agg = aggregations[0] if aggregations else "sum"

                    # Generate alias from entity text
                    alias = ent.get("text") or column

                    columns.append(
                        SQLColumn(
                            table=table,
                            column=column,
                            alias=alias,
                            aggregation=agg,
                        )
                    )
                    logger.debug(
                        f"[sql-gen][select] added column: {table}.{column}"
                        + (f" (agg={agg})" if agg else "")
                    )

        # NOTE: Domain value entities are used primarily for filtering (WHERE clause)
        # They should NOT be automatically added to SELECT unless explicitly needed
        # for grouping based on the query intent. The LLM enrichment step will add
        # them if they're truly needed for output context.
        # 
        # For example: "average fees for retail investors" should filter by
        # client_type='Individual' but NOT include client_type in SELECT/GROUP BY
        # since all results have the same client_type value.
        
        logger.debug(f"[sql-gen][select] skipping {len(dimension_entities)} domain_value entities - used for filtering only")

        # If no columns yet but we have tables, select primary keys or common display columns
        if not columns and table_entities:
            for tent in table_entities:
                table = tent.get("table") or tent.get("text")
                if table:
                    # Get table node from KG
                    table_node = self.kg.nodes.get(table)
                    if table_node:
                        # Add primary key
                        pk = table_node.metadata.get("primary_key", "id")
                        columns.append(SQLColumn(table=table, column=pk))
                        logger.debug(f"[sql-gen][select] added PK: {table}.{pk}")

                        # Add a few common display columns (name, code, etc.)
                        for col_name in [
                            "name",
                            f"{table[:-1]}_name",
                            "code",
                            f"{table[:-1]}_code",
                        ]:
                            col_node = self.kg.nodes.get(f"{table}.{col_name}")
                            if col_node:
                                columns.append(SQLColumn(table=table, column=col_name))
                                logger.debug(
                                    f"[sql-gen][select] added display col: {table}.{col_name}"
                                )
                                break
        
        # Add essential context columns for financial queries
        # If selecting monetary amounts, include currency (whether aggregated or not)
        monetary_columns = {'fee_amount', 'amount', 'fees', 'charges', 'price', 'cost', 'value', 'balance'}
        has_monetary_column = any(
            col.column in monetary_columns  # Check ANY monetary column (aggregated or not)
            for col in columns
        )
        
        if has_monetary_column:
            # Find the table with currency column
            currency_added = False
            for col in columns:
                if col.column in monetary_columns:
                    # Check if this table has a currency column
                    currency_node = self.kg.nodes.get(f"{col.table}.currency")
                    if currency_node and not any(c.column == 'currency' and c.table == col.table for c in columns):
                        columns.append(
                            SQLColumn(
                                table=col.table,
                                column='currency',
                                alias='currency'
                            )
                        )
                        logger.info(
                            f"[sql-gen][select] ✓ Auto-added currency column for monetary column: {col.table}.currency"
                        )
                        currency_added = True
                        break
            
            if not currency_added:
                logger.warning(
                    "[sql-gen][select] ⚠️  Monetary column detected but no currency column found in schema"
                )

        return columns

    def _build_from_and_joins(self, plan: Dict[str, Any]) -> Tuple[str, List[SQLJoin]]:
        """Build FROM and JOIN clauses from plan"""
        tables = plan.get("tables", [])
        if not tables:
            raise ValueError("No tables in plan")

        # First table is FROM
        from_table = tables[0]
        logger.debug(f"[sql-gen][from] using base table: {from_table}")

        joins = []

        # Single table - no joins needed
        if len(tables) == 1:
            return from_table, joins

        # Multi-table - use plan edges to construct joins
        strategy = plan.get("strategy", "")
        if strategy == "kg_shortest_paths":
            path_edges = plan.get("path_edges", [])

            # Track which tables we've already joined
            joined_tables = {from_table}

            for edge in path_edges:
                from_node = edge.get("from")
                to_node = edge.get("to")
                from_col = edge.get("from_column")
                to_col = edge.get("to_column")
                rel_type = edge.get("type")

                # Determine which table to join (skip if already joined)
                if to_node not in joined_tables and from_node in joined_tables:
                    # Join to_node to from_node
                    join_type = "INNER"  # Could be LEFT based on relationship
                    on_condition = f"{from_node}.{from_col} = {to_node}.{to_col}"

                    joins.append(
                        SQLJoin(
                            table=to_node,
                            join_type=join_type,
                            on_condition=on_condition,
                        )
                    )
                    joined_tables.add(to_node)
                    logger.debug(
                        f"[sql-gen][join] {join_type} JOIN {to_node} ON {on_condition}"
                    )

                elif from_node not in joined_tables and to_node in joined_tables:
                    # Join from_node to to_node (reverse direction)
                    join_type = "INNER"
                    on_condition = f"{to_node}.{to_col} = {from_node}.{from_col}"

                    joins.append(
                        SQLJoin(
                            table=from_node,
                            join_type=join_type,
                            on_condition=on_condition,
                        )
                    )
                    joined_tables.add(from_node)
                    logger.debug(
                        f"[sql-gen][join] {join_type} JOIN {from_node} ON {on_condition}"
                    )

        return from_table, joins

    def _normalize_filter_value(self, value_str: str) -> str:
        """
        Normalize filter values to valid SQL format.

        Handles:
        - Shorthand numeric values: 100M → 100000000, 1.5K → 1500, 2B → 2000000000
        - Already quoted strings: leave as-is
        - Plain numbers: leave as-is

        Args:
            value_str: The value string from filter (e.g., "100M", "'equity'", "2024")

        Returns:
            Normalized SQL-compatible value string
        """
        import re

        value_str = value_str.strip()

        # Pattern: number followed by K/M/B/T (thousands, millions, billions, trillions)
        # Handles: 100M, 1.5K, 2B, 0.5M, etc.
        shorthand_pattern = r"^(\d+(?:\.\d+)?)\s*([KMBT])$"
        match = re.match(shorthand_pattern, value_str, re.IGNORECASE)

        if match:
            number = float(match.group(1))
            suffix = match.group(2).upper()

            multipliers = {
                "K": 1_000,
                "M": 1_000_000,
                "B": 1_000_000_000,
                "T": 1_000_000_000_000,
            }

            result = number * multipliers[suffix]

            # Return as integer if it's a whole number, otherwise as float
            if result == int(result):
                normalized = str(int(result))
            else:
                normalized = str(result)

            logger.debug(
                f"[sql-gen][normalize] converted shorthand: {value_str} → {normalized}"
            )
            return normalized

        # Already a valid value (quoted string, number, boolean, etc.)
        return value_str

    def _normalize_column_reference(
        self,
        col_ref: str,
        entities: List[Dict[str, Any]],
    ) -> str:
        """
        Normalize column references in filters to use actual table/column names.

        This maps entity text (e.g., "AUM", "customers") to actual schema names
        (e.g., "funds.total_aum", "clients").

        Args:
            col_ref: Column reference from filter (e.g., "AUM", "customers.type", "customer_type")
            entities: List of discovered entities with mappings

        Returns:
            Normalized column reference (e.g., "funds.total_aum", "clients.client_type")
        """
        # If already in table.column format, check if table needs mapping
        if "." in col_ref:
            table_ref, col_name = col_ref.split(".", 1)

            # Check if table_ref is an entity text that needs mapping
            for ent in entities:
                if ent.get("text", "").lower() == table_ref.lower():
                    actual_table = ent.get("table")
                    if actual_table:
                        return f"{actual_table}.{col_name}"

            return col_ref

        # Single word reference - could be column name or entity text
        # First, try to find it as an entity text in the entities list
        for ent in entities:
            text = ent.get("text", "").lower()
            entity_type = ent.get("entity_type")

            if text == col_ref.lower():
                if entity_type == "column":
                    table = ent.get("table")
                    column = ent.get("column")
                    if table and column:
                        return f"{table}.{column}"
                elif entity_type == "table":
                    # Just return the actual table name
                    actual_table = ent.get("table")
                    if actual_table:
                        return actual_table

        # Not found in entities - try to find column in knowledge graph
        # This handles cases like "customer_type" → "clients.client_type"
        col_lower = col_ref.lower()

        # Try exact match first
        matching_nodes = []
        for node in self.kg.nodes.values():
            if node.type == "column" and node.name and node.name.lower() == col_lower:
                matching_nodes.append(node)

        # If no exact match, try fuzzy match (e.g., "customer_type" matches "client_type")
        if not matching_nodes:
            # Try removing common prefixes/suffixes and checking similarity
            candidates = []
            for node in self.kg.nodes.values():
                if node.type == "column" and node.name:
                    # Check similarity ratio
                    ratio = difflib.SequenceMatcher(
                        None, col_lower, node.name.lower()
                    ).ratio()
                    if ratio > 0.7:  # Increased threshold from 0.5 to 0.7 to avoid bad matches
                        candidates.append((node, ratio))

            # Sort by similarity and take best matches
            candidates.sort(key=lambda x: x[1], reverse=True)
            matching_nodes = [c[0] for c in candidates[:3]]  # Top 3 candidates

        # If we have matches, prefer ones from tables in our entity list
        if matching_nodes:
            # Get tables from entities
            entity_tables = set()
            for ent in entities:
                table = ent.get("table")
                if table:
                    entity_tables.add(table)
                # Also check metadata
                md = (ent.get("top_match") or {}).get("metadata") or {}
                table = md.get("table")
                if table:
                    entity_tables.add(table)

            # ONLY use columns from tables in our query - don't use fuzzy match from unrelated tables
            for node in matching_nodes:
                if node.table in entity_tables:
                    logger.info(
                        f"[sql-gen][normalize] mapped column '{col_ref}' → "
                        f"'{node.table}.{node.name}' (from KG, fuzzy match, confidence={difflib.SequenceMatcher(None, col_lower, node.name.lower()).ratio():.2f})"
                    )
                    return f"{node.table}.{node.name}"

            # No match in our tables - DON'T use fuzzy match from unrelated tables
            # This prevents bad mappings like portfolio_type → period_type
            logger.warning(
                f"[sql-gen][normalize] Fuzzy match found for '{col_ref}' but not in active query tables. "
                f"Best candidate: {matching_nodes[0].table}.{matching_nodes[0].name} (not used). "
                f"Returning as-is."
            )
            return col_ref

        # No mapping found - return as-is
        logger.warning(
            f"[sql-gen][normalize] could not normalize column reference '{col_ref}', "
            f"using as-is (may cause SQL errors)"
        )
        return col_ref

    def _build_where_conditions(
        self,
        entities: List[Dict[str, Any]],
        filters: List[str],
    ) -> List[str]:
        """Build WHERE clause conditions"""
        conditions = []
        
        logger.info(f"[sql-gen][where] Building WHERE conditions from {len(filters)} filter(s)")

        # Parse intent filters first to detect negations
        # Format examples: "fund_type != 'equity'", "risk_rating = 'High'", "amount > 1000"
        filter_metadata = {}  # Maps column to (operator, values)
        explicitly_filtered_columns = set()  # Track columns explicitly filtered by user

        for filter_str in filters:
            try:
                filter_str = filter_str.strip()
                
                # Log each filter being processed
                is_temporal = any(keyword in filter_str.upper() for keyword in 
                                 ['EXTRACT', 'QUARTER', 'MONTH', 'YEAR', 'CAST', 'DATE_TRUNC', 'BETWEEN'])
                filter_type = "TEMPORAL" if is_temporal else "STANDARD"
                logger.debug(f"[sql-gen][where] Processing [{filter_type}] filter: {filter_str}")

                # Parse filter to detect column, operator, and value
                # Patterns: "column != value", "column = value", "table.column op value"
                import re

                # Match patterns like: column_name != 'value' or table.column = value
                # IMPORTANT: Use word boundaries (\b) to avoid matching "in" within words like "investors"
                # Order matters: match longer operators first (NOT IN, NOT LIKE before IN, LIKE)
                pattern = r"([\w.]+)\s*(\bNOT\s+IN\b|\bNOT\s+LIKE\b|!=|=|>|<|>=|<=|\bIN\b|\bLIKE\b)\s*(.+)"
                match = re.match(pattern, filter_str, re.IGNORECASE)

                if match:
                    col_ref = match.group(1).strip()
                    operator = match.group(2).strip().upper()
                    value_part = match.group(3).strip()

                    # Normalize column reference (remove table prefix if present)
                    if "." in col_ref:
                        table_name = col_ref.split(".")[0]
                        col_name = col_ref.split(".")[-1]
                        explicitly_filtered_columns.add(f"{table_name}.{col_name}")
                    else:
                        col_name = col_ref
                        explicitly_filtered_columns.add(col_name)

                    # Store filter metadata to check for negations
                    filter_metadata[col_name] = {
                        "operator": operator,
                        "value": value_part,
                        "original": filter_str,
                    }
                    logger.debug(
                        f"[sql-gen][where] parsed filter: column={col_name}, op={operator}, value={value_part}"
                    )
                else:
                    logger.debug(
                        f"[sql-gen][where] could not parse filter pattern: {filter_str}"
                    )

            except Exception as e:
                logger.warning(
                    f"[sql-gen][where] failed to parse filter '{filter_str}': {e}"
                )

        # Process domain value entities
        dimension_entities = [
            e for e in entities if e.get("entity_type") == "domain_value"
        ]

        # Group dimension entities by table.column to handle multiple values (OR/IN)
        dim_groups: Dict[str, List[str]] = {}
        dim_negations: Dict[str, bool] = {}  # Track which columns have negations

        for ent in dimension_entities:
            table = ent.get("table")
            column = ent.get("column")
            
            # Try to get value from entity metadata
            md = (ent.get("top_match") or {}).get("metadata") or {}
            if not table:
                table = md.get("table")
            if not column:
                column = md.get("column")
            
            if not (table and column):
                continue
            
            key = f"{table}.{column}"
            
            # Check if this column has a negation filter from intent
            filter_info = filter_metadata.get(column, {})
            operator = filter_info.get("operator", "=")
            is_negation = operator in ("!=", "NOT IN", "NOT LIKE")
            
            if key not in dim_groups:
                dim_groups[key] = []
                dim_negations[key] = is_negation
            
            # Get ALL semantic matches for this entity (for partial matches like "equity" → ["Equity Growth", "Equity Value"])
            semantic_matches = ent.get("semantic_matches", [])
            
            # Use a threshold to determine which matches to include
            # If top match score is low (< 0.5), include all matches with similar scores
            top_score = (ent.get("top_match") or {}).get("score", 0.0)
            score_threshold = max(0.3, top_score * 0.8)  # Include matches within 80% of top score, min 0.3
            
            values_added = set()
            for match in semantic_matches:
                match_table = match.get("metadata", {}).get("table")
                match_column = match.get("metadata", {}).get("column")
                match_value = match.get("metadata", {}).get("value") or match.get("content")
                match_score = match.get("score", 0.0)
                
                # Only include if it's for the same column and score is close to top match
                if (match_table == table and match_column == column and 
                    match_value and match_score >= score_threshold and
                    match_value not in values_added):
                    
                    safe_value = match_value.replace("'", "''")
                    dim_groups[key].append(safe_value)
                    values_added.add(match_value)
                    
                    logger.debug(
                        f"[sql-gen][where] added domain value for partial match: "
                        f"{key} = '{match_value}' (score={match_score:.3f})"
                    )
            
            # If no values were added from semantic matches, use mapped value
            if not values_added:
                # Priority order for value resolution:
                # 1. Entity value field (from local mapping or LLM enrichment)
                # 2. Entity canonical_name (from local mapping)
                # 3. Top match value from semantic search
                # 4. User's input text (last resort - may not match database)
                value = (
                    ent.get("value") or 
                    ent.get("canonical_name") or
                    md.get("value") or 
                    ent.get("text")
                )
                if value:
                    safe_value = value.replace("'", "''")
                    dim_groups[key].append(safe_value)
                    values_added.add(value)
                    
                    # Log which source was used
                    if ent.get("value"):
                        logger.info(
                            f"[sql-gen][where] ✓ Using domain value from entity.value: "
                            f"{key} = '{value}' (source: {ent.get('source', 'unknown')})"
                        )
                    elif ent.get("canonical_name"):
                        logger.info(
                            f"[sql-gen][where] ✓ Using domain value from entity.canonical_name: "
                            f"{key} = '{value}' (source: local_mapping)"
                        )
                    elif md.get("value"):
                        logger.debug(
                            f"[sql-gen][where] using domain value from semantic match: "
                            f"{key} = '{value}'"
                        )
                    else:
                        logger.warning(
                            f"[sql-gen][where] ⚠️  Using user's input text as domain value: "
                            f"{key} = '{value}' - may not match database values!"
                        )

            
            # Track this as explicitly filtered
            if values_added:
                explicitly_filtered_columns.add(key)
                explicitly_filtered_columns.add(column)

        # Build conditions from grouped dimensions
        for key, values in dim_groups.items():
            is_negation = dim_negations.get(key, False)
            
            # Detect if this is a name/text column that should use partial matching
            column_name = key.split(".")[-1] if "." in key else key
            use_partial_match = any(keyword in column_name.lower() for keyword in 
                                   ['name', 'title', 'description', 'code', 'company'])

            if len(values) == 1:
                # Single value - simple equality or inequality
                if is_negation:
                    if use_partial_match:
                        condition = f"{key} NOT ILIKE '%{values[0]}%'"
                        logger.debug(
                            f"[sql-gen][where] added dimension filter (negation, partial): {condition}"
                        )
                    else:
                        condition = f"{key} != '{values[0]}'"
                        logger.debug(
                            f"[sql-gen][where] added dimension filter (negation): {condition}"
                        )
                else:
                    if use_partial_match:
                        condition = f"{key} ILIKE '%{values[0]}%'"
                        logger.info(
                            f"[sql-gen][where] ✓ Using partial match for name column: {condition}"
                        )
                    else:
                        condition = f"{key} = '{values[0]}'"
                        logger.debug(
                            f"[sql-gen][where] added dimension filter: {condition}"
                        )
                conditions.append(condition)
            else:
                # Multiple values - use IN/NOT IN clause (or multiple ILIKE for partial matches)
                if use_partial_match:
                    # For partial matches with multiple values, use OR conditions with ILIKE
                    ilike_conditions = [f"{key} ILIKE '%{v}%'" for v in values]
                    if is_negation:
                        condition = "(" + " AND ".join(f"{key} NOT ILIKE '%{v}%'" for v in values) + ")"
                        logger.debug(
                            f"[sql-gen][where] added dimension filter (multi-value negation, partial): {condition}"
                        )
                    else:
                        condition = "(" + " OR ".join(ilike_conditions) + ")"
                        logger.info(
                            f"[sql-gen][where] ✓ Using partial match for name column (multi): {condition}"
                        )
                    conditions.append(condition)
                else:
                    # Exact match with IN clause
                    values_str = ", ".join(f"'{v}'" for v in values)
                    if is_negation:
                        condition = f"{key} NOT IN ({values_str})"
                        logger.debug(
                            f"[sql-gen][where] added dimension filter (multi-value negation): {condition}"
                        )
                    else:
                        condition = f"{key} IN ({values_str})"
                        logger.debug(
                            f"[sql-gen][where] added dimension filter (multi-value): {condition}"
                        )
                    conditions.append(condition)

        # Add any remaining explicit filters not covered by dimension entities
        processed_columns = {key.split(".")[-1] for key in dim_groups.keys()}
        
        # Track filters by column to detect contradictions
        filters_by_column: Dict[str, List[Tuple[str, str, str]]] = {}  # col -> [(operator, value, filter_str)]

        for filter_str in filters:
            try:
                filter_str = filter_str.strip()

                # Check if this filter is for a column we already handled via dimension entities
                covered = False
                for col_name in processed_columns:
                    if col_name in filter_str:
                        covered = True
                        break

                if not covered:
                    # Parse and normalize the filter
                    import re
                    
                    # Check if this is a complex SQL expression (like EXTRACT, CAST, BETWEEN, etc.)
                    # that should be passed through as-is
                    if any(keyword in filter_str.upper() for keyword in ['EXTRACT(', 'CAST(', 'DATE_TRUNC(', 'TO_DATE(', 'TO_CHAR(', 'BETWEEN']):
                        # This is a SQL function/expression - pass through as-is
                        logger.info(
                            f"[predicate-resolution][sql-gen][where] ✓ Detected SQL expression filter - "
                            f"passing through as-is: {filter_str}"
                        )
                        conditions.append(filter_str)
                        
                        # Extract table references for tracking
                        table_refs = re.findall(r'(\w+)\.\w+', filter_str)
                        if table_refs:
                            logger.debug(
                                f"[predicate-resolution][sql-gen][where] Filter references table(s): "
                                f"{', '.join(set(table_refs))}"
                            )
                        continue

                    # Use word boundaries (\b) to avoid matching "in" within words like "investors"
                    # Order matters: match longer operators first (NOT IN, NOT LIKE before IN, LIKE)
                    pattern = r"([\w.]+)\s*(\bNOT\s+IN\b|\bNOT\s+LIKE\b|!=|=|>|<|>=|<=|\bIN\b|\bLIKE\b)\s*(.+)"
                    match = re.match(pattern, filter_str, re.IGNORECASE)

                    if match:
                        col_ref = match.group(1).strip()
                        operator = match.group(2).strip()
                        value_part = match.group(3).strip()
                        
                        # Extract column name (without table prefix)
                        col_name = col_ref.split(".")[-1] if "." in col_ref else col_ref

                        # Check if this filter's value is already covered by dimension entities
                        # E.g., "fund_type = 'conservative'" when "conservative" is a domain_value
                        # for fund_type
                        skip_filter = False
                        value_cleaned = value_part.strip("'\"")

                        for ent in dimension_entities:
                            ent_text = (ent.get("text") or "").lower()
                            ent_value = (
                                ent.get("top_match", {})
                                .get("metadata", {})
                                .get("value")
                                or ""
                            ).lower()

                            # If the filter value matches a dimension entity text/value
                            if value_cleaned.lower() in [ent_text, ent_value]:
                                # The dimension entity already handles this value
                                skip_filter = True
                                logger.info(
                                    f"[sql-gen][where] skipping redundant filter '{filter_str}' - "
                                    f"value '{value_cleaned}' already handled by dimension entity "
                                    f"'{ent_text}' → {ent.get('table')}.{ent.get('column')}"
                                )
                                break

                        if skip_filter:
                            continue
                        
                        # Track this filter by column to detect contradictions
                        if col_name not in filters_by_column:
                            filters_by_column[col_name] = []
                        filters_by_column[col_name].append((operator, value_cleaned, filter_str))

                    else:
                        # Could not parse - check if it's already covered by dimension entities
                        # before skipping
                        filter_terms = filter_str.lower().split()
                        is_covered_by_dimension = False

                        for ent in entities:
                            if ent.get("entity_type") == "domain_value":
                                # Check if dimension entity text is in this filter
                                ent_text = (ent.get("text") or "").lower()
                                if ent_text and ent_text in filter_terms:
                                    is_covered_by_dimension = True
                                    break

                        if is_covered_by_dimension:
                            logger.info(
                                f"[sql-gen][where] skipping unparsable filter '{filter_str}' - "
                                f"already handled by dimension entities"
                            )
                        else:
                            # Not covered by dimensions and can't parse - log warning and skip
                            # (Don't add to avoid SQL syntax errors)
                            logger.warning(
                                f"[sql-gen][where] skipping unparsable filter '{filter_str}' - "
                                f"no valid SQL pattern found and not covered by dimension entities"
                            )

            except Exception as e:
                logger.warning(
                    f"[sql-gen][where] failed to process filter '{filter_str}': {e}"
                )
        
        # Now process the grouped filters to detect and fix contradictions
        for col_name, col_filters in filters_by_column.items():
            # Check for contradictory equality filters (e.g., col = 'A' AND col = 'B')
            equality_filters = [(op, val, fs) for op, val, fs in col_filters if op == "="]
            
            if len(equality_filters) > 1:
                # Multiple equality filters on same column - this is contradictory!
                # Convert to IN clause instead
                values = [val for op, val, fs in equality_filters]
                unique_values = list(set(values))  # Remove duplicates
                
                # Find the best column reference from filters
                # Prefer table-qualified reference if available
                col_ref = col_name
                for op, val, fs in equality_filters:
                    match = re.match(r"([\w.]+)\s*=", fs)
                    if match and "." in match.group(1):
                        col_ref = match.group(1)
                        break
                
                # Create IN clause
                values_str = ", ".join(f"'{v}'" for v in unique_values)
                merged_condition = f"{col_ref} IN ({values_str})"
                conditions.append(merged_condition)
                
                logger.warning(
                    f"[sql-gen][where] detected contradictory equality filters for {col_name}: "
                    f"{[fs for op, val, fs in equality_filters]}. "
                    f"Merged into: {merged_condition}"
                )
            else:
                # No contradiction - add filters as-is
                for operator, value, filter_str in col_filters:
                    # Normalize column reference (map entity text to actual table.column)
                    normalized_col = None
                    for op, val, fs in col_filters:
                        match = re.match(r"([\w.]+)\s*" + re.escape(operator), fs)
                        if match:
                            normalized_col = self._normalize_column_reference(
                                match.group(1), entities
                            )
                            break
                    
                    if not normalized_col:
                        # Fallback to column name
                        normalized_col = self._normalize_column_reference(col_name, entities)
                    
                    # Normalize value (handle 100M, 1K, etc.)
                    normalized_value = self._normalize_filter_value(f"'{value}'")

                    # Build normalized filter
                    normalized_filter = (
                        f"{normalized_col} {operator} {normalized_value}"
                    )
                    conditions.append(normalized_filter)

                    if normalized_filter != filter_str:
                        logger.info(
                            f"[sql-gen][where] normalized filter: "
                            f"'{filter_str}' → '{normalized_filter}'"
                        )
                    else:
                        logger.debug(
                            f"[sql-gen][where] added explicit filter: {filter_str}"
                        )

        # Apply auto-filters for columns with auto_filter_on_default property
        # This applies default filters unless user explicitly mentions inactive/deactivated records
        auto_filter_conditions = self._build_auto_filter_conditions(
            entities, explicitly_filtered_columns
        )
        conditions.extend(auto_filter_conditions)

        # OPTIMIZATION: Merge multiple equality filters for same column into IN clause
        # This handles cases like: "col = 'A' AND col = 'B'" → "col IN ('A', 'B')"
        conditions = self._merge_equality_filters(conditions)
        
        # Log final WHERE conditions summary
        logger.info(f"[sql-gen][where] Built {len(conditions)} WHERE condition(s)")
        temporal_count = sum(1 for c in conditions if any(kw in c.upper() for kw in ['EXTRACT', 'QUARTER', 'MONTH', 'YEAR', 'BETWEEN']))
        if temporal_count > 0:
            logger.info(f"[predicate-resolution][sql-gen][where] ✓ {temporal_count} temporal condition(s) included")
        
        for i, cond in enumerate(conditions, 1):
            is_temporal = any(kw in cond.upper() for kw in ['EXTRACT', 'QUARTER', 'MONTH', 'YEAR', 'BETWEEN'])
            cond_type = "[TEMPORAL]" if is_temporal else "[STANDARD]"
            logger.debug(f"[sql-gen][where] {cond_type} Condition {i}: {cond}")

        return conditions

    def _merge_equality_filters(self, conditions: List[str]) -> List[str]:
        """
        Merge multiple equality filters for same column into IN clause.

        Example: ["col = 'A'", "col = 'B'"] → ["col IN ('A', 'B')"]
        This fixes impossible conditions like "col = 'A' AND col = 'B'"
        """
        import re

        # Group conditions by column for equality checks
        equality_groups: Dict[str, List[str]] = {}  # column -> [values]
        other_conditions = []

        for condition in conditions:
            # Match simple equality: table.column = 'value' or column = 'value'
            match = re.match(r"^([\w.]+)\s*=\s*'([^']*)'$", condition.strip())
            if match:
                column = match.group(1)
                value = match.group(2)

                if column not in equality_groups:
                    equality_groups[column] = []
                equality_groups[column].append(value)
            else:
                # Not a simple equality - keep as is
                other_conditions.append(condition)

        # Build merged conditions
        merged_conditions = other_conditions.copy()

        for column, values in equality_groups.items():
            if len(values) == 1:
                # Single value - use simple equality
                merged_conditions.append(f"{column} = '{values[0]}'")
            else:
                # Multiple values - use IN clause
                values_str = ", ".join(f"'{v}'" for v in values)
                in_clause = f"{column} IN ({values_str})"
                merged_conditions.append(in_clause)
                logger.info(
                    f"[sql-gen][where] merged {len(values)} equality filters for '{column}' "
                    f"into IN clause: {in_clause}"
                )

        return merged_conditions

    def _build_auto_filter_conditions(
        self,
        entities: List[Dict[str, Any]],
        explicitly_filtered_columns: set,
    ) -> List[str]:
        """
        Build auto-filter conditions for columns marked with auto_filter_on_default.

        This applies default filters (e.g., is_active = true) unless the user
        explicitly mentions inactive/deactive records in the query or filters.

        Args:
            entities: List of discovered entities
            explicitly_filtered_columns: Set of columns already filtered by user

        Returns:
            List of auto-filter condition strings
        """
        auto_conditions = []

        # Get all tables from entities
        tables = set()
        for ent in entities:
            table = ent.get("table")
            if not table:
                md = (ent.get("top_match") or {}).get("metadata") or {}
                table = md.get("table")
            if table:
                tables.add(table)

        # For each table, check if it has columns with auto_filter_on_default
        for table in tables:
            table_node = self.kg.nodes.get(table)
            if not table_node:
                continue

            # Scan all columns in this table
            for node_name, node in self.kg.nodes.items():
                if node.type == "column" and node.table == table:
                    # Check if this column has auto_filter_on_default property
                    auto_filter = node.metadata.get("auto_filter_on_default", False)
                    default_value = node.metadata.get("default")
                    data_type = node.metadata.get("data_type", "").lower()

                    if auto_filter and default_value is not None:
                        col_name = node.name
                        full_col_ref = f"{table}.{col_name}"

                        # Skip if user explicitly filtered this column
                        if (
                            full_col_ref in explicitly_filtered_columns
                            or col_name in explicitly_filtered_columns
                        ):
                            logger.debug(
                                f"[sql-gen][auto-filter] skipping {full_col_ref} - "
                                f"user explicitly filtered this column"
                            )
                            continue

                        # Build filter condition based on data type
                        if data_type in ["boolean", "bool"]:
                            # Boolean: use true/false
                            value_str = "true" if default_value else "false"
                            condition = f"{full_col_ref} = {value_str}"
                        elif data_type in ["varchar", "text", "char", "string"]:
                            # String: quote the value
                            safe_value = str(default_value).replace("'", "''")
                            condition = f"{full_col_ref} = '{safe_value}'"
                        else:
                            # Numeric or other: use as-is
                            condition = f"{full_col_ref} = {default_value}"

                        auto_conditions.append(condition)
                        logger.info(
                            f"[sql-gen][auto-filter] applied default filter: {condition} "
                            f"(auto_filter_on_default=true)"
                        )

        return auto_conditions

    def _build_group_by(
        self,
        select_columns: List[SQLColumn],
        intent_type: str,
    ) -> List[str]:
        """Build GROUP BY clause"""
        # Only add GROUP BY if we have aggregations
        has_agg = any(col.aggregation for col in select_columns)

        if not has_agg:
            return []

        # Group by all non-aggregated columns
        group_by = []
        for col in select_columns:
            if not col.aggregation:
                # Use transformation if present, otherwise use table.column
                if col.transformation:
                    group_by.append(col.transformation)
                else:
                    group_by.append(f"{col.table}.{col.column}")

        if group_by:
            logger.debug(f"[sql-gen][group-by] grouping by: {group_by}")

        return group_by

    def _build_order_by(
        self,
        select_columns: List[SQLColumn],
        intent_type: str,
    ) -> List[Tuple[str, str]]:
        """Build ORDER BY clause"""
        order_by = []

        # For TOP_N or RANKING queries, order by first column (usually the metric) DESC
        if intent_type in ["top_n", "ranking"]:
            if select_columns:
                col = select_columns[0]
                # If aggregated, use alias; otherwise use table.column
                if col.aggregation:
                    order_by.append((f"{col.alias or col.column}", "DESC"))
                else:
                    order_by.append((f"{col.table}.{col.column}", "DESC"))
                logger.debug(
                    f"[sql-gen][order-by] ranking ordering: {order_by[0][0]} DESC"
                )

        # For COMPARISON, order by dimension columns
        elif intent_type == "comparison":
            non_agg_cols = [col for col in select_columns if not col.aggregation]
            if non_agg_cols:
                col = non_agg_cols[0]
                order_by.append((f"{col.table}.{col.column}", "ASC"))
                logger.debug(
                    f"[sql-gen][order-by] comparison ordering: {col.table}.{col.column} ASC"
                )

        return order_by

    def _determine_limit(self, intent_type: str, intent_limit: Optional[int] = None) -> Optional[int]:
        """
        Determine LIMIT value based on intent.
        
        Priority:
        1. Use explicit limit from intent (e.g., "top 5" → limit=5)
        2. Fall back to default limits by intent type
        
        Args:
            intent_type: Type of query intent
            intent_limit: Explicit limit extracted from query (e.g., "top 5" → 5)
        
        Returns:
            Limit value or None
        """
        # First, check if intent has explicit limit
        if intent_limit is not None:
            logger.debug(f"[sql-gen][limit] using intent limit: {intent_limit}")
            return intent_limit
        
        # Fall back to default limits by intent type
        limits = {
            "list": 100,
            "top_n": 10,
            "ranking": 10,
        }

        limit = limits.get(intent_type)
        if limit:
            logger.debug(f"[sql-gen][limit] applying default limit for {intent_type}: {limit}")

        return limit
    
    def _apply_column_ordering(
        self,
        select_columns: List[SQLColumn],
        ordered_column_names: List[str],
    ) -> List[SQLColumn]:
        """
        Apply LLM-determined column ordering to select_columns list.
        
        Args:
            select_columns: Current list of SQLColumn objects
            ordered_column_names: Ordered list of "table.column" strings from LLM
            
        Returns:
            Reordered list of SQLColumn objects
        """
        # Create a map of "table.column" -> SQLColumn for quick lookup
        column_map = {}
        for col in select_columns:
            key = f"{col.table}.{col.column}"
            column_map[key] = col
        
        # Build reordered list based on LLM ordering
        reordered = []
        seen = set()
        
        for ordered_name in ordered_column_names:
            if ordered_name in column_map and ordered_name not in seen:
                reordered.append(column_map[ordered_name])
                seen.add(ordered_name)
        
        # Add any columns that weren't in the ordering (safety fallback)
        for col in select_columns:
            key = f"{col.table}.{col.column}"
            if key not in seen:
                reordered.append(col)
                logger.debug(f"[sql-gen] column not in LLM ordering, appending: {key}")
        
        logger.info(
            f"[sql-gen] column ordering applied: {len(reordered)} columns "
            f"(original: {len(select_columns)})"
        )
        
        return reordered

    def _enrich_with_context_columns(
        self,
        *,
        question: str,
        intent_type: str,
        select_columns: List[SQLColumn],
        entities: List[Dict[str, Any]],
        plan: Dict[str, Any],
        filters: List[str] = None,
    ) -> List[SQLColumn]:
        """
        Use LLM to identify and add implicit context columns that would make
        the query output more meaningful for human consumption.

        For example, for a query like "top 5 clients by fees", this would add
        client_name and client_id alongside the fee aggregation.

        Args:
            question: Original user question
            intent_type: Type of query intent
            select_columns: Currently selected columns
            entities: Discovered entities
            plan: Query plan with tables
            filters: List of filter conditions to avoid adding filter-only columns

        Returns:
            Enhanced list of SQLColumn objects with context columns added
        """
        import json
        import time
        import hashlib

        logger.info(
            "[sql-gen][llm-enrich] analyzing query for implicit context columns"
        )

        # Skip enrichment for simple list queries or if no LLM client
        if not self.llm_client or intent_type == "list":
            logger.debug("[sql-gen][llm-enrich] skipping (no LLM client or list query)")
            return select_columns

        # Generate cache key from question, intent_type, and current columns
        if self.enable_cache and self.cache:
            cols_key = json.dumps([{
                "table": col.table,
                "column": col.column,
                "aggregation": col.aggregation,
            } for col in select_columns], sort_keys=True)
            tables_key = json.dumps(sorted(plan.get("tables", [])))
            
            cached = self.cache.get(
                "llm_sql",
                "enrich_context",
                question.lower(),
                intent_type,
                cols_key,
                tables_key,
            )
            if cached:
                logger.info(f"[cache-hit] llm_sql: enrichment result")
                # Reconstruct SQLColumn objects from cached data
                enriched_columns = []
                for col_data in cached:
                    enriched_columns.append(SQLColumn(
                        table=col_data["table"],
                        column=col_data["column"],
                        alias=col_data.get("alias"),
                        aggregation=col_data.get("aggregation"),
                        transformation=col_data.get("transformation"),
                    ))
                return enriched_columns

        try:
            # Build context about current columns and available schema
            tables = plan.get("tables", [])

            # Get available columns for each table from knowledge graph
            available_columns = {}
            for table in tables:
                table_node = self.kg.nodes.get(table)
                if table_node:
                    cols = []
                    for node_name, node in self.kg.nodes.items():
                        if node.type == "column" and node.table == table:
                            col_info = {
                                "name": node.name,
                                "data_type": node.metadata.get("data_type", "unknown"),
                                "description": node.metadata.get("description", ""),
                                "is_pk": node.metadata.get("is_primary_key", False),
                                "is_fk": node.metadata.get("is_foreign_key", False),
                            }
                            cols.append(col_info)
                    available_columns[table] = cols

            # Current columns summary
            current_cols = [
                {
                    "table": col.table,
                    "column": col.column,
                    "aggregation": col.aggregation,
                    "alias": col.alias,
                }
                for col in select_columns
            ]

            # Extract filter columns to avoid adding them to SELECT
            # Parse filters to identify equality filter columns (e.g., "client_type = 'Individual'")
            filter_columns = set()
            if filters:
                import re
                for filter_str in filters:
                    # Match patterns like "table.column = 'value'" or "column = 'value'"
                    match = re.search(r"(\w+\.)?(\w+)\s*=\s*['\"]", filter_str)
                    if match:
                        column = match.group(2)
                        filter_columns.add(column)
                        logger.debug(f"[sql-gen][llm-enrich] identified filter column: {column}")

            filters_info = ""
            if filter_columns:
                filters_info = f"\n\nFilter Columns (DO NOT add these to SELECT):\n{list(filter_columns)}\nThese columns are used only for filtering with equality conditions, so including them in SELECT/GROUP BY adds no value."

            # Build LLM prompt
            # Extract the main entity being ranked/listed from the question
            ranking_entity_hint = ""
            if intent_type in ["ranking", "top_n"]:
                # Try to extract the entity (e.g., "clients", "funds", "managers")
                import re
                patterns = [
                    r'top\s+\d+\s+(\w+)',
                    r'list.*?(\w+)\s+by',
                    r'show.*?(\w+)\s+by',
                    r'rank.*?(\w+)\s+by',
                ]
                for pattern in patterns:
                    match = re.search(pattern, question.lower())
                    if match:
                        entity = match.group(1)
                        ranking_entity_hint = f"\nRANKING ENTITY: '{entity}' - MUST include identifying columns for this entity!"
                        break
            
            # Extract aggregation level from question (e.g., "by fund type", "by region", "by client")
            aggregation_level_hint = ""
            if intent_type in ["aggregation", "aggregate"]:
                import re
                # Look for "by X" pattern to identify intended grouping level
                by_match = re.search(r'\bby\s+(\w+(?:\s+\w+)?)', question.lower())
                if by_match:
                    grouping = by_match.group(1)
                    aggregation_level_hint = f"\n**AGGREGATION LEVEL**: User wants results grouped 'by {grouping}'. DO NOT add columns that would create finer granularity than this grouping level!"
            
            prompt = f"""You are a SQL expert helping to make query results more meaningful by identifying implicit context columns.

User Question: "{question}"
Query Intent: {intent_type}{ranking_entity_hint}{aggregation_level_hint}

Currently Selected Columns:
{json.dumps(current_cols, indent=2)}

Available Schema (columns per table):
{json.dumps(available_columns, indent=2)}{filters_info}

Task: Identify additional columns that would make the query output more meaningful for human consumption.

**CRITICAL FOR AGGREGATION QUERIES** (intent_type="{intent_type}"):
When the query asks to aggregate data (e.g., "average fees by fund type", "total sales by region"):
  1. **RESPECT THE GROUPING LEVEL**: If user asks for "by fund type", DO NOT add fund_name, fund_code, or other fund-level details
  2. **ONLY ADD THE GROUPING COLUMN**: Only suggest the actual grouping column mentioned (e.g., fund_type for "by fund type")
  3. **AVOID EXPLOSION**: Adding extra columns will break the aggregation and create too many rows
  4. Examples:
     - "average fees by fund type" → Add ONLY fund_type (not fund_name, fund_code)
     - "total sales by region" → Add ONLY region (not city, country, branch_name)
     - "count by client type" → Add ONLY client_type (not client_name, client_id)

**CRITICAL FOR RANKING/TOP_N QUERIES** (intent_type="{intent_type}"):
When the query asks for "top N" entities (e.g., "top 5 clients", "top 10 funds"), you MUST:
  1. Identify which table represents the entity being ranked
  2. Add the entity's name column (e.g., client_name, fund_name, first_name+last_name)
  3. Add the entity's ID for uniqueness
  
WITHOUT these columns, the result will only show aggregated metrics without identifying WHICH entities they belong to!

For other query types, consider adding:
- Identifying columns (names, codes, IDs) for entities being aggregated or listed
- Descriptive columns that provide context
- Columns that help interpret the results (e.g., currency for monetary amounts)

Return a JSON object with:
{{
  "add_columns": [
    {{
      "table": "table_name",
      "column": "column_name",
      "reason": "why this column makes output more meaningful"
    }}
  ],
  "reasoning": "overall explanation of column selections"
}}

Guidelines:
- **FOR AGGREGATION QUERIES**: Only suggest the grouping column explicitly mentioned in the query. DO NOT add detail columns.
- For ranking queries, adding entity identifiers is MANDATORY, not optional
- Don't suggest columns already selected
- **DO NOT suggest columns that are used only for equality filtering** (listed above as Filter Columns)
- Prioritize human-readable identifiers (names over IDs, but include both when helpful)
- Keep the list focused (max 10 additional columns)
- **All suggested columns must be compatible with GROUP BY if aggregations are present**
- **DO NOT add columns that would increase granularity beyond what user requested**
- Focus on columns that will vary across result rows (not constant filter values)
"""

            # Log the prompt payload
            logger.info(
                f"[sql-gen][llm-enrich] prompt payload (chars={len(prompt)}):\n{prompt}"
            )

            t0 = time.perf_counter()

            # Detect provider type and call appropriately
            provider_type = self._detect_llm_provider()

            if provider_type == "openai":
                response = self.llm_client.chat.completions.create(
                    model="gpt-4o-mini",  # Fast and cheap for this task
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a SQL expert assistant.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0,
                )
                result_text = response.choices[0].message.content

            elif provider_type == "anthropic":
                response = self.llm_client.messages.create(
                    model="claude-3-haiku-20240307",  # Fast and cheap
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                )
                result_text = response.content[0].text
                # Extract JSON from response
                start = result_text.find("{")
                end = result_text.rfind("}") + 1
                if start >= 0 and end > start:
                    result_text = result_text[start:end]

            else:  # gemini
                import google.generativeai as genai

                gen_config = {
                    "temperature": 0,
                    "response_mime_type": "application/json",
                }
                response = self.llm_client.generate_content(
                    prompt, generation_config=gen_config
                )
                result_text = response.text

            dt_ms = (time.perf_counter() - t0) * 1000.0

            # Log the response
            logger.info(
                f"[llm-result] provider={self.llm_provider} model={self.llm_model} "
                f"latency_ms={dt_ms:.1f} response_chars={len(result_text)}"
            )
            logger.debug(f"[llm-result] Response text:\n{result_text}")

            # Parse response
            result = json.loads(result_text)
            add_columns = result.get("add_columns", [])
            reasoning = result.get("reasoning", "")

            logger.info(
                f"[sql-gen][llm-enrich] LLM suggested {len(add_columns)} context column(s); reasoning: {reasoning}"
            )

            # Add suggested columns
            added_count = 0
            for col_suggestion in add_columns:
                table = col_suggestion.get("table")
                column = col_suggestion.get("column")
                reason = col_suggestion.get("reason", "")

                # Validate column exists in schema
                if table not in available_columns:
                    logger.debug(
                        f"[sql-gen][llm-enrich] skipping {table}.{column} - table not in plan"
                    )
                    continue

                col_exists = any(c["name"] == column for c in available_columns[table])
                if not col_exists:
                    logger.debug(
                        f"[sql-gen][llm-enrich] skipping {table}.{column} - column not found"
                    )
                    continue

                # Check if column already selected
                already_selected = any(
                    c.table == table and c.column == column for c in select_columns
                )
                if already_selected:
                    logger.debug(
                        f"[sql-gen][llm-enrich] skipping {table}.{column} - already selected"
                    )
                    continue

                # Add the context column
                new_col = SQLColumn(
                    table=table,
                    column=column,
                    alias=column,  # Use column name as alias
                )
                select_columns.append(new_col)
                added_count += 1

                logger.info(
                    f"[sql-gen][llm-enrich] added context column: {table}.{column} "
                    f"(reason: {reason})"
                )

            logger.info(
                f"[sql-gen][llm-enrich] enrichment complete: added {added_count} column(s)"
            )

            # Cache the enriched columns
            if self.enable_cache and self.cache:
                tables_key = json.dumps(sorted(plan.get("tables", [])))
                
                # Serialize enriched columns for caching
                cached_data = [{
                    "table": col.table,
                    "column": col.column,
                    "alias": col.alias,
                    "aggregation": col.aggregation,
                    "transformation": col.transformation,
                } for col in select_columns]
                
                self.cache.set(
                    "llm_sql",
                    cached_data,
                    "enrich_context",
                    question.lower(),
                    intent_type,
                    cols_key,  # Use the cache key we created at the start
                    tables_key,
                )
                logger.debug(f"[sql-gen][llm-enrich] Cached enrichment result")

            return select_columns

        except Exception as e:
            # Enhanced error logging with detailed context
            import traceback
            
            # Determine if this should be treated as a critical error
            error_level = logger.error if self.fail_on_llm_error else logger.warning
            
            error_level("=" * 80)
            error_level("[sql-gen][llm-enrich] ENRICHMENT FAILED - DETAILED ERROR REPORT")
            error_level("=" * 80)
            error_level(f"Exception Type: {type(e).__name__}")
            error_level(f"Exception Message: {str(e)}")
            error_level(f"Fail on LLM Error: {self.fail_on_llm_error}")
            error_level("-" * 80)
            error_level("Context Information:")
            error_level(f"  Question: {question}")
            error_level(f"  Intent Type: {intent_type}")
            error_level(f"  Current Columns: {len(select_columns)}")
            error_level(f"  Tables in Plan: {plan.get('tables', [])}")
            error_level(f"  Entities Count: {len(entities) if entities else 0}")
            error_level(f"  Has LLM Client: {self.llm_client is not None}")
            error_level(f"  LLM Provider: {self.llm_provider or 'unknown'}")
            error_level(f"  LLM Model: {self.llm_model or 'unknown'}")
            
            # Log available columns if populated
            if 'available_columns' in locals():
                error_level(f"  Available Columns Tables: {list(available_columns.keys())}")
                total_cols = sum(len(cols) for cols in available_columns.values())
                error_level(f"  Total Available Columns: {total_cols}")
            
            # Log prompt info if available
            if 'prompt' in locals():
                error_level(f"  Prompt Length: {len(prompt)} chars")
                error_level(f"  Prompt Preview (first 300 chars): {prompt[:300]}...")
            
            # Log response info if available
            if 'result_text' in locals():
                error_level(f"  Response Length: {len(result_text)} chars")
                error_level(f"  Response Text: {result_text}")
            elif 'response' in locals():
                error_level(f"  Response Object Type: {type(response)}")
                error_level(f"  Response Object: {response}")
            
            error_level("-" * 80)
            error_level("Full Traceback:")
            error_level(traceback.format_exc())
            error_level("=" * 80)
            
            # If configured to fail on LLM errors, re-raise the exception
            if self.fail_on_llm_error:
                logger.error("[sql-gen][llm-enrich] Re-raising exception due to fail_on_llm_error=True")
                raise
            
            logger.warning(f"[sql-gen][llm-enrich] Using fallback logic after error")
            
            # Fallback: For ranking queries, add entity identifiers heuristically
            if intent_type in ["ranking", "top_n"]:
                logger.info("[sql-gen][llm-enrich] Applying fallback logic for ranking query")
                return self._fallback_add_ranking_identifiers(
                    select_columns=select_columns,
                    plan=plan,
                    question=question,
                )
            
            return select_columns

    def _fallback_add_ranking_identifiers(
        self,
        select_columns: List[SQLColumn],
        plan: Dict[str, Any],
        question: str,
    ) -> List[SQLColumn]:
        """
        Fallback method to add entity identifiers for ranking queries when LLM enrichment fails.
        
        Heuristically identifies which table represents the entity being ranked and adds
        its identifying columns (name, ID, etc.)
        """
        import re
        
        tables = plan.get("tables", [])
        if not tables:
            return select_columns
        
        # Try to extract entity from question
        entity_patterns = [
            r'top\s+\d+\s+(\w+)',
            r'list.*?(\w+)\s+by',
            r'show.*?(\w+)\s+by',
            r'rank.*?(\w+)\s+by',
        ]
        
        entity_keyword = None
        for pattern in entity_patterns:
            match = re.search(pattern, question.lower())
            if match:
                entity_keyword = match.group(1).rstrip('s')  # singular form
                break
        
        if not entity_keyword:
            logger.debug("[sql-gen][fallback] Could not extract entity keyword from question")
            return select_columns
        
        logger.info(f"[sql-gen][fallback] Detected ranking entity keyword: '{entity_keyword}'")
        
        # Find matching table
        candidate_table = None
        for table in tables:
            # Check if table name contains the entity keyword
            if entity_keyword in table.lower() or table.lower() in entity_keyword:
                candidate_table = table
                break
        
        if not candidate_table:
            # Default to first table with joins
            candidate_table = tables[0]
            logger.debug(f"[sql-gen][fallback] No exact match, using first table: {candidate_table}")
        else:
            logger.info(f"[sql-gen][fallback] Matched entity to table: {candidate_table}")
        
        # Get table schema from knowledge graph
        table_node = self.kg.nodes.get(candidate_table)
        if not table_node:
            logger.warning(f"[sql-gen][fallback] Table node not found in KG: {candidate_table}")
            return select_columns
        
        # Find identifier columns (name, id, code, etc.)
        identifier_patterns = [
            f"{candidate_table[:-1]}_name",  # e.g., client_name from clients
            "name",
            f"{candidate_table[:-1]}_id",
            "id",
            f"{candidate_table[:-1]}_code",
            "code",
            "first_name",  # for people tables
            "last_name",
        ]
        
        added_count = 0
        for col_name in identifier_patterns:
            col_node = self.kg.nodes.get(f"{candidate_table}.{col_name}")
            if col_node:
                # Check if already selected
                already_selected = any(
                    c.table == candidate_table and c.column == col_name
                    for c in select_columns
                )
                if not already_selected:
                    select_columns.append(SQLColumn(
                        table=candidate_table,
                        column=col_name,
                        alias=col_name,
                    ))
                    added_count += 1
                    logger.info(
                        f"[sql-gen][fallback] Added identifier column: {candidate_table}.{col_name}"
                    )
                    
                    # Stop after adding 2-3 identifiers
                    if added_count >= 3:
                        break
        
        if added_count == 0:
            logger.warning(
                f"[sql-gen][fallback] No identifier columns found for table: {candidate_table}"
            )
        else:
            logger.info(
                f"[sql-gen][fallback] Added {added_count} identifier column(s) for ranking query"
            )
        
        return select_columns

    def _refine_column_transformations(
        self,
        question: str,
        intent_type: str,
        select_columns: List[SQLColumn],
        entities: List[Dict[str, Any]],
    ) -> List[SQLColumn]:
        """
        Refine existing column selections based on user query.

        For example:
        - If user asks for "by month" but we selected timestamp, transform to MONTH(timestamp)
        - If user asks for "year" but we selected date, transform to YEAR(date)
        - If user asks for "day of week" but we selected date, transform to DAYOFWEEK(date)

        Args:
            question: Original user question
            intent_type: Type of query intent
            select_columns: Currently selected columns
            entities: Discovered entities

        Returns:
            Refined list of SQLColumn objects with transformations applied
        """
        import json
        import time

        logger.info(
            "[sql-gen][llm-refine] analyzing columns for potential transformations"
        )

        # Skip if no LLM client
        if not self.llm_client:
            logger.debug("[sql-gen][llm-refine] skipping (no LLM client)")
            return select_columns

        # Generate cache key from question, intent_type, and current columns
        if self.enable_cache and self.cache:
            cols_key = json.dumps([{
                "table": col.table,
                "column": col.column,
                "aggregation": col.aggregation,
                "data_type": self._get_column_data_type(col.table, col.column),
            } for col in select_columns], sort_keys=True)
            
            cached = self.cache.get(
                "llm_sql",
                "refine_transforms",
                question.lower(),
                intent_type,
                cols_key,
            )
            if cached:
                logger.info(f"[cache-hit] llm_sql: transformation result")
                # Reconstruct SQLColumn objects from cached data
                refined_columns = []
                for col_data in cached:
                    refined_columns.append(SQLColumn(
                        table=col_data["table"],
                        column=col_data["column"],
                        alias=col_data.get("alias"),
                        aggregation=col_data.get("aggregation"),
                        transformation=col_data.get("transformation"),
                    ))
                return refined_columns

        try:
            # Build context about current columns
            current_cols = [
                {
                    "table": col.table,
                    "column": col.column,
                    "aggregation": col.aggregation,
                    "alias": col.alias,
                    "data_type": self._get_column_data_type(col.table, col.column),
                }
                for col in select_columns
            ]

            prompt = f"""You are a SQL expert helping to refine column selections based on user intent.

User Question: "{question}"
Query Intent: {intent_type}

Currently Selected Columns:
{json.dumps(current_cols, indent=2)}

Task: Identify if any columns should be transformed to better match the user's request.

Examples of transformations:
- User asks "by month" but timestamp selected → DATE_TRUNC('month', timestamp) AS month (if grouping needed)
- User asks "by month" for display → TO_CHAR(DATE_TRUNC('month', timestamp), 'YYYY-MM') AS month (formatted)
- User asks "by year" but date selected → EXTRACT(YEAR FROM date) AS year
- User asks "day name" but date selected → TO_CHAR(date, 'Day') AS day_name
- User asks "quarter" but date selected → EXTRACT(QUARTER FROM date) AS quarter
- User asks "hour" but timestamp selected → EXTRACT(HOUR FROM timestamp) AS hour
- For month grouping/display, use TO_CHAR to format: TO_CHAR(DATE_TRUNC('month', date), 'YYYY-MM') or 'Mon YYYY'

Return a JSON object with:
{{
  "transform_columns": [
    {{
      "table": "table_name",
      "column": "original_column_name",
      "transformation": "SQL expression (e.g., EXTRACT(MONTH FROM column_name))",
      "new_alias": "suggested alias for transformed column",
      "reason": "why this transformation matches user intent"
    }}
  ],
  "reasoning": "overall explanation"
}}

Guidelines:
- Only suggest transformations that match user's explicit or implicit intent
- Use standard SQL functions (EXTRACT, TO_CHAR, DATE_TRUNC, etc.)
- Preserve aggregations if they exist
- Return empty list if no transformations needed
- Focus on date/time transformations based on temporal granularity in question
- Can suggest up to 10 transformations if needed
"""

            # Log the prompt payload
            logger.info(
                f"[sql-gen][llm-refine] prompt payload (chars={len(prompt)}):\n{prompt}"
            )

            t0 = time.perf_counter()

            # Detect provider type and call appropriately
            provider_type = self._detect_llm_provider()

            if provider_type == "openai":
                response = self.llm_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a SQL expert assistant.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0,
                )
                result_text = response.choices[0].message.content

            elif provider_type == "anthropic":
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
                    result_text = result_text[start:end]

            else:  # gemini
                import google.generativeai as genai

                gen_config = {
                    "temperature": 0,
                    "response_mime_type": "application/json",
                }
                response = self.llm_client.generate_content(
                    prompt, generation_config=gen_config
                )
                result_text = response.text

            dt_ms = (time.perf_counter() - t0) * 1000.0

            # Log the response
            logger.info(
                f"[llm-result] provider={self.llm_provider} model={self.llm_model} "
                f"latency_ms={dt_ms:.1f} response_chars={len(result_text)}"
            )
            logger.debug(f"[llm-result] Response text:\n{result_text}")

            # Parse response
            result = json.loads(result_text)
            transform_columns = result.get("transform_columns", [])
            reasoning = result.get("reasoning", "")

            if not transform_columns:
                logger.info("[sql-gen][llm-refine] no column transformations suggested")
                
                # Cache the result even if no transformations
                if self.enable_cache and self.cache:
                    cached_data = [{
                        "table": col.table,
                        "column": col.column,
                        "alias": col.alias,
                        "aggregation": col.aggregation,
                        "transformation": col.transformation,
                    } for col in select_columns]
                    
                    self.cache.set(
                        "llm_sql",
                        cached_data,
                        "refine_transforms",
                        question.lower(),
                        intent_type,
                        cols_key,
                    )
                    logger.debug(f"[sql-gen][llm-refine] Cached no-transformation result")
                
                return select_columns

            logger.info(
                f"[sql-gen][llm-refine] LLM suggested {len(transform_columns)} transformation(s); reasoning: {reasoning}"
            )

            # Apply transformations
            transformed_count = 0
            new_columns = []

            for col in select_columns:
                # Check if this column should be transformed
                transform = None
                for t in transform_columns:
                    if t.get("table") == col.table and t.get("column") == col.column:
                        transform = t
                        break

                if transform:
                    # Apply transformation
                    transformation = transform.get("transformation")
                    new_alias = transform.get("new_alias", col.alias)
                    reason = transform.get("reason", "")

                    logger.info(
                        f"[sql-gen][llm-refine] transforming {col.table}.{col.column} → {transformation} AS {new_alias} (reason: {reason})"
                    )

                    # Create new column with transformation
                    transformed_col = SQLColumn(
                        table=col.table,
                        column=col.column,
                        alias=new_alias,
                        aggregation=col.aggregation,  # Preserve aggregation
                        transformation=transformation,  # Add transformation
                    )
                    new_columns.append(transformed_col)
                    transformed_count += 1
                else:
                    # Keep original column
                    new_columns.append(col)

            logger.info(
                f"[sql-gen][llm-refine] refinement complete: transformed {transformed_count} column(s)"
            )

            # Cache the refined columns
            if self.enable_cache and self.cache:
                cached_data = [{
                    "table": col.table,
                    "column": col.column,
                    "alias": col.alias,
                    "aggregation": col.aggregation,
                    "transformation": col.transformation,
                } for col in new_columns]
                
                self.cache.set(
                    "llm_sql",
                    cached_data,
                    "refine_transforms",
                    question.lower(),
                    intent_type,
                    cols_key,
                )
                logger.debug(f"[sql-gen][llm-refine] Cached transformation result")

            return new_columns

        except Exception as e:
            # Enhanced error logging with detailed context
            import traceback
            
            # Determine if this should be treated as a critical error
            error_level = logger.error if self.fail_on_llm_error else logger.warning
            
            error_level("=" * 80)
            error_level("[sql-gen][llm-refine] TRANSFORMATION REFINEMENT FAILED - DETAILED ERROR REPORT")
            error_level("=" * 80)
            error_level(f"Exception Type: {type(e).__name__}")
            error_level(f"Exception Message: {str(e)}")
            error_level(f"Fail on LLM Error: {self.fail_on_llm_error}")
            error_level("-" * 80)
            error_level("Context Information:")
            error_level(f"  Question: {question}")
            error_level(f"  Intent Type: {intent_type}")
            error_level(f"  Current Columns: {len(select_columns)}")
            error_level(f"  Entities Count: {len(entities) if entities else 0}")
            error_level(f"  Has LLM Client: {self.llm_client is not None}")
            error_level(f"  LLM Provider: {self.llm_provider or 'unknown'}")
            error_level(f"  LLM Model: {self.llm_model or 'unknown'}")
            
            # Log column details
            error_level("  Selected Columns:")
            for col in select_columns[:5]:  # First 5 columns
                error_level(f"    - {col.table}.{col.column} (agg={col.aggregation}, transform={col.transformation})")
            if len(select_columns) > 5:
                error_level(f"    ... and {len(select_columns) - 5} more columns")
            
            # Log prompt info if available
            if 'prompt' in locals():
                error_level(f"  Prompt Length: {len(prompt)} chars")
                error_level(f"  Prompt Preview (first 300 chars): {prompt[:300]}...")
            
            # Log response info if available
            if 'result_text' in locals():
                error_level(f"  Response Length: {len(result_text)} chars")
                error_level(f"  Response Text: {result_text}")
            elif 'response' in locals():
                error_level(f"  Response Object Type: {type(response)}")
                error_level(f"  Response Object: {response}")
            
            error_level("-" * 80)
            error_level("Full Traceback:")
            error_level(traceback.format_exc())
            error_level("=" * 80)
            
            # If configured to fail on LLM errors, re-raise the exception
            if self.fail_on_llm_error:
                logger.error("[sql-gen][llm-refine] Re-raising exception due to fail_on_llm_error=True")
                raise
            
            logger.warning(f"[sql-gen][llm-refine] Using original columns after error")
            return select_columns

    def _get_column_data_type(self, table: str, column: str) -> str:
        """Get data type for a column from knowledge graph"""
        node_name = f"{table}.{column}"
        node = self.kg.nodes.get(node_name)
        if node and node.metadata:
            return node.metadata.get("data_type", "unknown")
        return "unknown"

    def _detect_llm_provider(self) -> str:
        """Detect which LLM provider is being used"""
        if not self.llm_client:
            return "none"
        if hasattr(self.llm_client, "chat") and hasattr(
            self.llm_client.chat, "completions"
        ):
            return "openai"
        elif hasattr(self.llm_client, "messages"):
            return "anthropic"
        else:
            return "gemini"
    
    def _detect_llm_model(self) -> str:
        """Detect which LLM model is being used"""
        if not self.llm_client:
            return "none"
        
        provider = self._detect_llm_provider()
        
        # Try to get model from client attributes
        if provider == "openai":
            # OpenAI clients don't store default model, return common default
            return "gpt-4o-mini"
        elif provider == "anthropic":
            return "claude-3-haiku-20240307"
        elif provider == "gemini":
            # Try to get from client
            if hasattr(self.llm_client, "model_name"):
                return self.llm_client.model_name
            return "gemini-2.5-flash"
        
        return "unknown"

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
