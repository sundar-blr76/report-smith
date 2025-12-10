from typing import List, Optional, Tuple, Dict, Any, Union
from enum import Enum
from dataclasses import dataclass

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
    RANKING = "ranking"


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
