from typing import List, Dict, Any, Tuple
from reportsmith.logger import get_logger
from .structures import SQLJoin

logger = get_logger(__name__)

class JoinBuilder:
    """Builds FROM and JOIN clauses for SQL queries."""

    def build_from_and_joins(self, plan: Dict[str, Any]) -> Tuple[str, List[SQLJoin]]:
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
