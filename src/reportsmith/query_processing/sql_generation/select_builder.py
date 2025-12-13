from typing import List, Dict, Any, Set
from reportsmith.schema_intelligence.knowledge_graph import SchemaKnowledgeGraph
from reportsmith.logger import get_logger
from .structures import SQLColumn

logger = get_logger(__name__)

class SelectBuilder:
    """Builds SELECT clauses for SQL queries."""

    def __init__(self, knowledge_graph: SchemaKnowledgeGraph):
        self.kg = knowledge_graph

    def build_select_columns(
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
        monetary_columns = {
            'fee_amount', 'amount', 'fees', 'charges', 'price', 'cost', 'value', 'balance',
            'total_aum', 'aum', 'nav_per_share', 'nav', 'market_value', 'net_amount', 'gross_amount',
            'total_invested', 'current_value', 'cost_basis', 'unrealized_gain_loss'
        }
        
        # Also check for columns with monetary suffixes/aliases
        aum_aliases = {'aum'}  # Alias might be used instead of column name
        
        has_monetary_column = any(
            col.column in monetary_columns or col.alias in aum_aliases
            for col in columns
        )
        
        if has_monetary_column:
            # Find the table with currency column
            currency_added = False
            for col in columns:
                if col.column in monetary_columns or col.alias in aum_aliases:
                    # Check for currency column (try multiple possible names)
                    for currency_col in ['currency', 'base_currency']:
                        currency_node = self.kg.nodes.get(f"{col.table}.{currency_col}")
                        if currency_node and not any(
                            c.column == currency_col and c.table == col.table for c in columns
                        ):
                            columns.append(
                                SQLColumn(
                                    table=col.table,
                                    column=currency_col,
                                    alias='currency' if currency_col == 'base_currency' else currency_col
                                )
                            )
                            logger.info(
                                f"[sql-gen][select] ✓ Auto-added currency column for monetary column: {col.table}.{currency_col}"
                            )
                            currency_added = True
                            break
                    if currency_added:
                        break
            
            if not currency_added:
                logger.warning(
                    "[sql-gen][select] ⚠️  Monetary column detected but no currency column found in schema"
                )

        return columns
