from typing import List, Tuple, Optional
from reportsmith.logger import get_logger
from .structures import SQLColumn

logger = get_logger(__name__)

class ModifiersBuilder:
    """Builds GROUP BY, ORDER BY and LIMIT clauses for SQL queries."""

    def build_group_by(
        self,
        select_columns: List[SQLColumn],
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

    def build_order_by(
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

    def determine_limit(self, intent_type: str, intent_limit: Optional[int] = None) -> Optional[int]:
        """
        Determine LIMIT value based on intent.
        
        Priority:
        1. Use explicit limit from intent (e.g., "top 5" → limit=5)
        2. Fall back to default limits by intent type
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
