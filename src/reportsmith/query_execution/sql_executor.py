"""SQL Query Executor."""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional
import psycopg2
import psycopg2.extras
from contextlib import contextmanager

from reportsmith.logger import get_logger

logger = get_logger(__name__)


class SQLExecutor:
    """Executes SQL queries against PostgreSQL database."""
    
    def __init__(self, connection_params: Optional[Dict[str, Any]] = None):
        """
        Initialize SQL executor.
        
        Args:
            connection_params: Database connection parameters.
                              If None, loads from environment variables.
        """
        if connection_params is None:
            # Load from environment
            self.connection_params = {
                "host": os.getenv("FINANCIAL_TESTDB_HOST", "localhost"),
                "port": int(os.getenv("FINANCIAL_TESTDB_PORT", "5432")),
                "database": os.getenv("FINANCIAL_TESTDB_NAME", os.getenv("DB_NAME", "financial_testdb")),
                "user": os.getenv("FINANCIAL_TESTDB_USER", os.getenv("DB_USER", "postgres")),
                "password": os.getenv("FINANCIAL_TESTDB_PASSWORD", os.getenv("DB_PASSWORD", "postgres")),
            }
        else:
            self.connection_params = connection_params
        
        # Schema (optional)
        self.schema = os.getenv("FINANCIAL_TESTDB_SCHEMA", "public")
    
    @contextmanager
    def get_connection(self):
        """Get database connection context manager."""
        conn = None
        try:
            conn = psycopg2.connect(**self.connection_params)
            # Set search path if schema is specified
            if self.schema and self.schema != "public":
                with conn.cursor() as cur:
                    cur.execute(f"SET search_path TO {self.schema}, public")
            yield conn
        finally:
            if conn:
                conn.close()
    
    def _format_datetime_values(
        self,
        rows: List[Dict[str, Any]],
        columns: List[str],
        column_types: List[int]
    ) -> List[Dict[str, Any]]:
        """
        Format datetime values to human-readable strings.
        
        Args:
            rows: List of row dictionaries
            columns: List of column names
            column_types: List of psycopg2 type OIDs
            
        Returns:
            Rows with formatted datetime values
        """
        # PostgreSQL type OIDs for datetime types
        # Reference: https://github.com/postgres/postgres/blob/master/src/include/catalog/pg_type.dat
        DATE_OID = 1082
        TIMESTAMP_OID = 1114
        TIMESTAMPTZ_OID = 1184
        
        datetime_oids = {DATE_OID, TIMESTAMP_OID, TIMESTAMPTZ_OID}
        
        # Build mapping of column index to format string
        format_map = {}
        for idx, (col_name, col_type) in enumerate(zip(columns, column_types)):
            if col_type not in datetime_oids:
                continue
                
            col_lower = col_name.lower()
            
            # Determine format based on column name patterns
            if any(pattern in col_lower for pattern in ['month', 'mon', 'ym']):
                # Month aggregations: YYYY-MM
                format_map[idx] = '%Y-%m'
            elif any(pattern in col_lower for pattern in ['quarter', 'qtr', 'q']):
                # Quarter aggregations: YYYY-Q1, YYYY-Q2, etc.
                format_map[idx] = 'quarter'
            elif any(pattern in col_lower for pattern in ['year', 'yr', 'y']):
                # Year aggregations: YYYY
                format_map[idx] = '%Y'
            elif col_type == DATE_OID or any(pattern in col_lower for pattern in ['date', 'day', 'dt']):
                # Date columns: YYYY-MM-DD
                format_map[idx] = '%Y-%m-%d'
            else:
                # Timestamp columns: YYYY-MM-DD HH:MM:SS
                format_map[idx] = '%Y-%m-%d %H:%M:%S'
        
        if not format_map:
            return rows
        
        # Format datetime values in rows
        formatted_rows = []
        for row in rows:
            formatted_row = dict(row)
            for idx, col_name in enumerate(columns):
                if idx not in format_map:
                    continue
                    
                value = formatted_row.get(col_name)
                if value is None:
                    continue
                
                try:
                    if isinstance(value, (date, datetime)):
                        fmt = format_map[idx]
                        if fmt == 'quarter':
                            # Special handling for quarters
                            quarter = (value.month - 1) // 3 + 1
                            formatted_row[col_name] = f"{value.year}-Q{quarter}"
                        else:
                            formatted_row[col_name] = value.strftime(fmt)
                except Exception as e:
                    logger.warning(f"[sql-exec] failed to format datetime column '{col_name}': {e}")
                    # Keep original value on error
                    
            formatted_rows.append(formatted_row)
        
        logger.debug(f"[sql-exec] formatted {len(format_map)} datetime columns")
        return formatted_rows

    
    def execute_query(
        self,
        sql: str,
        params: Optional[tuple] = None,
        max_rows: int = 1000
    ) -> Dict[str, Any]:
        """
        Execute SQL query and return results.
        
        Args:
            sql: SQL query string
            params: Query parameters (for parameterized queries)
            max_rows: Maximum number of rows to return
        
        Returns:
            Dictionary with:
                - columns: List of column names
                - rows: List of row dictionaries
                - row_count: Number of rows returned
                - truncated: Whether results were truncated
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    # Execute query
                    if params:
                        cur.execute(sql, params)
                    else:
                        cur.execute(sql)
                    
                    # Fetch results
                    rows = cur.fetchmany(max_rows + 1)  # Fetch one extra to detect truncation
                    
                    truncated = len(rows) > max_rows
                    if truncated:
                        rows = rows[:max_rows]
                    
                    # Extract column names and types
                    columns = [desc[0] for desc in cur.description] if cur.description else []
                    column_types = [desc[1] for desc in cur.description] if cur.description else []
                    
                    # Convert rows to list of dicts
                    result_rows = [dict(row) for row in rows]
                    
                    # Format datetime values to human-readable strings
                    if result_rows and column_types:
                        result_rows = self._format_datetime_values(result_rows, columns, column_types)
                    
                    logger.info(
                        f"[sql-exec] query executed successfully: "
                        f"{len(result_rows)} rows returned"
                        f"{' (truncated)' if truncated else ''}"
                    )
                    
                    return {
                        "columns": columns,
                        "rows": result_rows,
                        "row_count": len(result_rows),
                        "truncated": truncated,
                    }
        
        except psycopg2.Error as e:
            logger.error(f"[sql-exec] database error: {e}")
            return {
                "error": str(e),
                "error_type": "database_error",
                "columns": [],
                "rows": [],
                "row_count": 0,
                "truncated": False,
            }
        except Exception as e:
            logger.error(f"[sql-exec] execution error: {e}", exc_info=True)
            return {
                "error": str(e),
                "error_type": "execution_error",
                "columns": [],
                "rows": [],
                "row_count": 0,
                "truncated": False,
            }
    
    def validate_sql(self, sql: str) -> Dict[str, Any]:
        """
        Validate SQL query without executing it.
        
        Args:
            sql: SQL query string
        
        Returns:
            Dictionary with:
                - valid: Boolean indicating if SQL is valid
                - error: Error message if invalid
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Use EXPLAIN to validate without execution
                    cur.execute(f"EXPLAIN {sql}")
                    
            logger.info("[sql-exec] SQL validation passed")
            return {"valid": True, "error": None}
        
        except psycopg2.Error as e:
            logger.warning(f"[sql-exec] SQL validation failed: {e}")
            return {"valid": False, "error": str(e)}
        except Exception as e:
            logger.error(f"[sql-exec] validation error: {e}")
            return {"valid": False, "error": str(e)}
    
    def test_connection(self) -> bool:
        """
        Test database connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    result = cur.fetchone()
                    if result and result[0] == 1:
                        logger.info("[sql-exec] database connection test successful")
                        return True
            return False
        except Exception as e:
            logger.error(f"[sql-exec] connection test failed: {e}")
            return False
