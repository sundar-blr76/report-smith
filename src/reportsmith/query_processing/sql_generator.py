"""
SQL Generator - Converts query plans to executable SQL statements.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import re

from reportsmith.schema_intelligence.knowledge_graph import SchemaKnowledgeGraph
from reportsmith.logger import get_logger

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
    
    def to_sql(self) -> str:
        """Convert to SQL column expression"""
        if self.aggregation:
            col_ref = f"{self.table}.{self.column}"
            agg_expr = f"{self.aggregation.upper()}({col_ref})"
            return f"{agg_expr} AS {self.alias or self.column}"
        else:
            col_ref = f"{self.table}.{self.column}"
            return f"{col_ref} AS {self.alias or self.column}" if self.alias else col_ref


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
            order_clause = ", ".join(f"{col} {direction}" for col, direction in self.order_by)
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
    - Generate WHERE conditions from filters and dimension values
    - Add GROUP BY, ORDER BY, LIMIT based on intent
    - Enrich with implicit context columns using LLM
    """
    
    def __init__(self, knowledge_graph: SchemaKnowledgeGraph, llm_client=None):
        self.kg = knowledge_graph
        self.llm_client = llm_client  # Optional LLM for column enrichment
    
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
            select_columns = self._build_select_columns(entities, aggregations, intent_type)
            
            # Enrich with implicit context columns using LLM
            if self.llm_client:
                select_columns = self._enrich_with_context_columns(
                    question=question,
                    intent_type=intent_type,
                    select_columns=select_columns,
                    entities=entities,
                    plan=plan,
                )
            
            from_table, joins = self._build_from_and_joins(plan)
            where_conditions = self._build_where_conditions(entities, filters)
            group_by = self._build_group_by(select_columns, intent_type)
            order_by = self._build_order_by(select_columns, intent_type)
            limit = self._determine_limit(intent_type)
            
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
        dimension_entities = [e for e in entities if e.get("entity_type") == "dimension_value"]
        
        # Determine if we need aggregation based on intent type and presence of aggregations
        needs_aggregation = (
            intent_type in ["aggregate", "comparison", "top_n"] 
            or len(aggregations) > 0
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
                        if data_type in ["numeric", "integer", "decimal", "float", "double", "money"]:
                            agg = aggregations[0] if aggregations else "sum"
                    
                    # Generate alias from entity text
                    alias = ent.get("text") or column
                    
                    columns.append(SQLColumn(
                        table=table,
                        column=column,
                        alias=alias,
                        aggregation=agg,
                    ))
                    logger.debug(f"[sql-gen][select] added column: {table}.{column}" + (f" (agg={agg})" if agg else ""))
        
        # Add dimension columns for grouping
        dimension_tables = set()
        for ent in dimension_entities:
            table = ent.get("table")
            column = ent.get("column")
            if not table or not column:
                md = (ent.get("top_match") or {}).get("metadata") or {}
                table = table or md.get("table")
                column = column or md.get("column")
            
            if table and column and table not in dimension_tables:
                # Add the dimension column for grouping/filtering
                columns.append(SQLColumn(
                    table=table,
                    column=column,
                    alias=column,
                ))
                dimension_tables.add(table)
                logger.debug(f"[sql-gen][select] added dimension: {table}.{column}")
        
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
                        for col_name in ["name", f"{table[:-1]}_name", "code", f"{table[:-1]}_code"]:
                            col_node = self.kg.nodes.get(f"{table}.{col_name}")
                            if col_node:
                                columns.append(SQLColumn(table=table, column=col_name))
                                logger.debug(f"[sql-gen][select] added display col: {table}.{col_name}")
                                break
        
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
                    
                    joins.append(SQLJoin(
                        table=to_node,
                        join_type=join_type,
                        on_condition=on_condition,
                    ))
                    joined_tables.add(to_node)
                    logger.debug(f"[sql-gen][join] {join_type} JOIN {to_node} ON {on_condition}")
                
                elif from_node not in joined_tables and to_node in joined_tables:
                    # Join from_node to to_node (reverse direction)
                    join_type = "INNER"
                    on_condition = f"{to_node}.{to_col} = {from_node}.{from_col}"
                    
                    joins.append(SQLJoin(
                        table=from_node,
                        join_type=join_type,
                        on_condition=on_condition,
                    ))
                    joined_tables.add(from_node)
                    logger.debug(f"[sql-gen][join] {join_type} JOIN {from_node} ON {on_condition}")
        
        return from_table, joins
    
    def _build_where_conditions(
        self,
        entities: List[Dict[str, Any]],
        filters: List[str],
    ) -> List[str]:
        """Build WHERE clause conditions"""
        conditions = []
        
        # Add dimension value filters
        dimension_entities = [e for e in entities if e.get("entity_type") == "dimension_value"]
        
        # Group dimension entities by table.column to handle multiple values (OR/IN)
        dim_groups: Dict[str, List[str]] = {}
        
        for ent in dimension_entities:
            table = ent.get("table")
            column = ent.get("column")
            value = None
            
            # Try to get value from entity metadata
            md = (ent.get("top_match") or {}).get("metadata") or {}
            if not table:
                table = md.get("table")
            if not column:
                column = md.get("column")
            
            # Get the actual dimension value
            value = md.get("value") or ent.get("text")
            
            if table and column and value:
                key = f"{table}.{column}"
                if key not in dim_groups:
                    dim_groups[key] = []
                # Escape single quotes in value
                safe_value = value.replace("'", "''")
                dim_groups[key].append(safe_value)
        
        # Build conditions from grouped dimensions
        for key, values in dim_groups.items():
            if len(values) == 1:
                # Single value - simple equality
                condition = f"{key} = '{values[0]}'"
                conditions.append(condition)
                logger.debug(f"[sql-gen][where] added dimension filter: {condition}")
            else:
                # Multiple values - use IN clause
                values_str = ", ".join(f"'{v}'" for v in values)
                condition = f"{key} IN ({values_str})"
                conditions.append(condition)
                logger.debug(f"[sql-gen][where] added dimension filter (multi-value): {condition}")
        
        # Parse explicit filters from intent
        # Format: "column op value" or "table.column op value"
        for filter_str in filters:
            try:
                # Simple parsing - could be enhanced with proper parser
                # Example: "fund_type = 'Equity'" or "risk_rating IN ('Low', 'Medium')"
                filter_str = filter_str.strip()
                
                # Skip if already covered by dimension entities
                if any(ent.get("text", "").lower() in filter_str.lower() for ent in dimension_entities):
                    continue
                
                # Add filter as-is (assumes it's already in valid SQL format from intent analyzer)
                # In production, would parse and validate
                conditions.append(filter_str)
                logger.debug(f"[sql-gen][where] added explicit filter: {filter_str}")
            
            except Exception as e:
                logger.warning(f"[sql-gen][where] failed to parse filter '{filter_str}': {e}")
        
        return conditions
    
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
                logger.debug(f"[sql-gen][order-by] ranking ordering: {order_by[0][0]} DESC")
        
        # For COMPARISON, order by dimension columns
        elif intent_type == "comparison":
            non_agg_cols = [col for col in select_columns if not col.aggregation]
            if non_agg_cols:
                col = non_agg_cols[0]
                order_by.append((f"{col.table}.{col.column}", "ASC"))
                logger.debug(f"[sql-gen][order-by] comparison ordering: {col.table}.{col.column} ASC")
        
        return order_by
    
    def _determine_limit(self, intent_type: str) -> Optional[int]:
        """Determine LIMIT value based on intent"""
        # Default limits by intent type
        limits = {
            "list": 100,
            "top_n": 10,
            "ranking": 10,  # Add ranking as well
        }
        
        limit = limits.get(intent_type)
        if limit:
            logger.debug(f"[sql-gen][limit] applying limit: {limit}")
        
        return limit
    
    def _enrich_with_context_columns(
        self,
        *,
        question: str,
        intent_type: str,
        select_columns: List[SQLColumn],
        entities: List[Dict[str, Any]],
        plan: Dict[str, Any],
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
        
        Returns:
            Enhanced list of SQLColumn objects with context columns added
        """
        import json
        import time
        
        logger.info("[sql-gen][llm-enrich] analyzing query for implicit context columns")
        
        # Skip enrichment for simple list queries or if no LLM client
        if not self.llm_client or intent_type == "list":
            logger.debug("[sql-gen][llm-enrich] skipping (no LLM client or list query)")
            return select_columns
        
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
            
            # Build LLM prompt
            prompt = f"""You are a SQL expert helping to make query results more meaningful by identifying implicit context columns.

User Question: "{question}"
Query Intent: {intent_type}

Currently Selected Columns:
{json.dumps(current_cols, indent=2)}

Available Schema (columns per table):
{json.dumps(available_columns, indent=2)}

Task: Identify additional columns that would make the query output more meaningful for human consumption.
Consider adding:
- Identifying columns (names, codes, IDs) for entities being aggregated
- Descriptive columns that provide context
- Columns that help interpret the results

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
- Only suggest columns that truly add value
- Don't suggest columns already selected
- Prioritize human-readable identifiers (names over IDs when both exist)
- Keep the list minimal (max 5 additional columns)
- If aggregating, ensure suggested columns are compatible with GROUP BY
"""
            
            t0 = time.perf_counter()
            
            # Detect provider type and call appropriately
            provider_type = self._detect_llm_provider()
            
            if provider_type == "openai":
                response = self.llm_client.chat.completions.create(
                    model="gpt-4o-mini",  # Fast and cheap for this task
                    messages=[
                        {"role": "system", "content": "You are a SQL expert assistant."},
                        {"role": "user", "content": prompt}
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
                start = result_text.find('{')
                end = result_text.rfind('}') + 1
                if start >= 0 and end > start:
                    result_text = result_text[start:end]
            
            else:  # gemini
                import google.generativeai as genai
                gen_config = {
                    "temperature": 0,
                    "response_mime_type": "application/json",
                }
                response = self.llm_client.generate_content(
                    prompt,
                    generation_config=gen_config
                )
                result_text = response.text
            
            dt_ms = (time.perf_counter() - t0) * 1000.0
            
            # Parse response
            result = json.loads(result_text)
            add_columns = result.get("add_columns", [])
            reasoning = result.get("reasoning", "")
            
            logger.info(
                f"[sql-gen][llm-enrich] LLM suggested {len(add_columns)} context column(s) "
                f"in {dt_ms:.1f}ms; reasoning: {reasoning[:100]}"
            )
            
            # Add suggested columns
            added_count = 0
            for col_suggestion in add_columns:
                table = col_suggestion.get("table")
                column = col_suggestion.get("column")
                reason = col_suggestion.get("reason", "")
                
                # Validate column exists in schema
                if table not in available_columns:
                    logger.debug(f"[sql-gen][llm-enrich] skipping {table}.{column} - table not in plan")
                    continue
                
                col_exists = any(c["name"] == column for c in available_columns[table])
                if not col_exists:
                    logger.debug(f"[sql-gen][llm-enrich] skipping {table}.{column} - column not found")
                    continue
                
                # Check if column already selected
                already_selected = any(
                    c.table == table and c.column == column
                    for c in select_columns
                )
                if already_selected:
                    logger.debug(f"[sql-gen][llm-enrich] skipping {table}.{column} - already selected")
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
            
            return select_columns
        
        except Exception as e:
            logger.warning(f"[sql-gen][llm-enrich] failed: {e}; using original columns")
            return select_columns
    
    def _detect_llm_provider(self) -> str:
        """Detect which LLM provider is being used"""
        if hasattr(self.llm_client, 'chat') and hasattr(self.llm_client.chat, 'completions'):
            return "openai"
        elif hasattr(self.llm_client, 'messages'):
            return "anthropic"
        else:
            return "gemini"
    
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
