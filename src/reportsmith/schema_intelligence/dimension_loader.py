"""
Dimension Loader for ReportSmith

Loads domain values from actual database tables to create embeddings.
Handles lazy loading and caching of dimension data.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import sqlalchemy as sa
from sqlalchemy import text
from ..logger import get_logger

logger = get_logger(__name__)


@dataclass
class DimensionConfig:
    """Configuration for a dimension field."""
    table: str
    column: str
    description: Optional[str] = None
    context: Optional[str] = None  # Business context for better embeddings
    
    # Dictionary table support for enhanced descriptions
    dictionary_table: Optional[str] = None  # Table containing value descriptions
    dictionary_value_column: Optional[str] = None  # Column with the domain value
    dictionary_description_column: Optional[str] = None  # Column with description/label
    dictionary_predicates: Optional[List[str]] = None  # Additional WHERE conditions for dictionary table


class DimensionLoader:
    """
    Loads ALL domain values from database tables.
    
    Dimensions are now explicitly configured in YAML schema files.
    Supports optional dictionary tables for enhanced descriptions.
    """
    
    def __init__(self, connection_manager=None, embedding_manager=None):
        """
        Initialize dimension loader.
        
        Args:
            connection_manager: Connection manager instance
            embedding_manager: Embedding manager instance
        """
        self._loaded_dimensions: Dict[str, bool] = {}
        self.connection_manager = connection_manager
        self.embedding_manager = embedding_manager
    
    def load_domain_values(
        self,
        engine: sa.engine.Engine,
        dimension_config: DimensionConfig
    ) -> List[Dict[str, Any]]:
        """
        Load ALL distinct values for a dimension column with optional dictionary enrichment.
        
        Args:
            engine: SQLAlchemy engine for database connection
            dimension_config: DimensionConfig with table, column, and optional dictionary info
            
        Returns:
            List of dicts with 'value', 'count', and optional 'description' keys
        """
        cache_key = f"{dimension_config.table}.{dimension_config.column}"
        
        try:
            # Build base query for domain values
            base_query = f"""
                SELECT 
                    {dimension_config.column} as value,
                    COUNT(*) as count
                FROM {dimension_config.table}
                WHERE {dimension_config.column} IS NOT NULL
                GROUP BY {dimension_config.column}
                ORDER BY count DESC
            """
            
            # If dictionary table is configured, enhance with descriptions
            if dimension_config.dictionary_table:
                # Build dictionary WHERE clause from predicates
                dict_where_clause = "WHERE " + " AND ".join(dimension_config.dictionary_predicates) if dimension_config.dictionary_predicates else ""
                
                query_text = f"""
                    WITH domain_values AS ({base_query})
                    SELECT 
                        dv.value,
                        dv.count,
                        COALESCE(dt.{dimension_config.dictionary_description_column}, dv.value) as description
                    FROM domain_values dv
                    LEFT JOIN (
                        SELECT * FROM {dimension_config.dictionary_table} {dict_where_clause}
                    ) dt ON dv.value = dt.{dimension_config.dictionary_value_column}
                    ORDER BY dv.count DESC
                """
            else:
                query_text = base_query
            
            logger.debug(f"SQL: {query_text.strip()}")
            
            query = text(query_text)
            
            with engine.connect() as conn:
                result = conn.execute(query)
                
                if dimension_config.dictionary_table:
                    values = [
                        {"value": row[0], "count": row[1], "description": row[2]}
                        for row in result
                    ]
                else:
                    values = [
                        {"value": row[0], "count": row[1]}
                        for row in result
                    ]
            
            self._loaded_dimensions[cache_key] = True
            logger.info(
                f"Loaded {len(values)} domain values from {cache_key}"
            )
            
            return values
            
        except Exception as e:
            logger.error(f"Failed to load domain values from {cache_key}: {e}")
            return []
    
    def identify_dimension_columns(
        self,
        schema_config: Dict[str, Any]
    ) -> List[DimensionConfig]:
        """
        Identify dimension columns from table column definitions.
        Scans tables for columns marked as dimensions.
        
        Args:
            schema_config: Parsed schema section from YAML
            
        Returns:
            List of DimensionConfig objects
        """
        dimensions = []
        
        # Scan tables for columns marked as dimensions
        tables = schema_config.get("tables", {})
        
        for table_name, table_def in tables.items():
            columns = table_def.get("columns", {})
            
            for col_name, col_def in columns.items():
                # Check if column is marked as a dimension
                if col_def.get("is_dimension", False):
                    dimension_config = DimensionConfig(
                        table=table_name,
                        column=col_name,
                        description=col_def.get("description"),
                        context=col_def.get("dimension_context") or col_def.get("context"),
                        dictionary_table=col_def.get("dictionary_table"),
                        dictionary_value_column=col_def.get("dictionary_value_column"),
                        dictionary_description_column=col_def.get("dictionary_description_column"),
                        dictionary_predicates=col_def.get("dictionary_predicates", [])
                    )
                    
                    dimensions.append(dimension_config)
                    logger.debug(f"Found dimension: {table_name}.{col_name}")
        
        logger.info(f"Identified {len(dimensions)} dimension columns from table definitions")
        return dimensions
    
    def get_dimension_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded dimensions."""
        return {
            "total_loaded": len(self._loaded_dimensions),
            "dimensions": list(self._loaded_dimensions.keys())
        }
