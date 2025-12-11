"""Database schema introspection for multiple database vendors.

This module connects to database system catalogs to extract schema metadata:
- Tables, columns, data types, constraints
- Primary keys, foreign keys, indexes
- Relationships between tables

System catalogs queried (via SQLAlchemy Inspector):
- PostgreSQL: pg_catalog (pg_tables, pg_attribute, pg_constraint, pg_class)
- MySQL: information_schema (tables, columns, referential_constraints)
- Oracle: all_tables, all_tab_columns, all_constraints
- SQL Server: sys.tables, sys.columns, sys.foreign_keys, sys.dm_db_partition_stats
- SQLite: sqlite_master and internal schema tables

The inspector uses SQLAlchemy's database-agnostic Inspector API which internally
queries the appropriate system catalogs for each database vendor.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import sqlalchemy as sa
from sqlalchemy import inspect, MetaData, Table
from sqlalchemy.engine import Engine

from ..logger import get_logger
from ..config_system.config_models import DatabaseType

logger = get_logger(__name__)


@dataclass
class ColumnInfo:
    """Information about a database column."""
    name: str
    data_type: str
    nullable: bool
    default: Optional[Any] = None
    primary_key: bool = False
    foreign_key: Optional[str] = None
    comment: Optional[str] = None


@dataclass
class ForeignKeyInfo:
    """Information about a foreign key relationship."""
    constraint_name: str
    source_table: str
    source_columns: List[str]
    target_table: str
    target_columns: List[str]


@dataclass
class TableInfo:
    """Information about a database table."""
    name: str
    schema: Optional[str]
    columns: List[ColumnInfo]
    primary_keys: List[str]
    foreign_keys: List[ForeignKeyInfo]
    indexes: List[Dict[str, Any]]
    comment: Optional[str] = None
    row_count_estimate: Optional[int] = None


class SchemaIntrospector:
    """Introspect database schemas across different database vendors."""
    
    def __init__(self, engine: Engine, database_type: DatabaseType):
        """
        Initialize the schema introspector.
        
        Args:
            engine: SQLAlchemy engine for database connection
            database_type: Type of database (PostgreSQL, MySQL, etc.)
        """
        self.engine = engine
        self.database_type = database_type
        self.inspector = inspect(engine)
        self.metadata = MetaData()
        
        logger.info(f"Initialized SchemaIntrospector for {database_type.value}")
    
    def introspect_schema(
        self, 
        schema: Optional[str] = None,
        tables: Optional[List[str]] = None
    ) -> Dict[str, TableInfo]:
        """
        Introspect database schema and extract table information.
        
        Args:
            schema: Specific schema to introspect (default: use database default)
            tables: Specific tables to introspect (default: all tables)
            
        Returns:
            Dictionary mapping table names to TableInfo objects
        """
        logger.info(f"Starting schema introspection for schema: {schema or 'default'}")
        
        # Get list of tables
        if tables is None:
            tables = self._get_table_names(schema)
        
        table_info_dict = {}
        
        for table_name in tables:
            try:
                table_info = self._introspect_table(table_name, schema)
                table_info_dict[table_name] = table_info
                logger.info(f"Successfully introspected table: {table_name}")
            except Exception as e:
                logger.error(f"Failed to introspect table {table_name}: {e}")
                continue
        
        logger.info(f"Completed introspection of {len(table_info_dict)} tables")
        return table_info_dict
    
    def _get_table_names(self, schema: Optional[str] = None) -> List[str]:
        """Get list of table names in the schema."""
        try:
            table_names = self.inspector.get_table_names(schema=schema)
            logger.debug(f"Found {len(table_names)} tables in schema {schema or 'default'}")
            return table_names
        except Exception as e:
            logger.error(f"Failed to get table names: {e}")
            raise
    
    def _introspect_table(self, table_name: str, schema: Optional[str] = None) -> TableInfo:
        """Introspect a single table."""
        # Get columns
        columns = self._get_columns(table_name, schema)
        
        # Get primary keys
        primary_keys = self._get_primary_keys(table_name, schema)
        
        # Get foreign keys
        foreign_keys = self._get_foreign_keys(table_name, schema)
        
        # Get indexes
        indexes = self._get_indexes(table_name, schema)
        
        # Get table comment
        comment = self._get_table_comment(table_name, schema)
        
        # Get row count estimate
        row_count = self._estimate_row_count(table_name, schema)
        
        return TableInfo(
            name=table_name,
            schema=schema,
            columns=columns,
            primary_keys=primary_keys,
            foreign_keys=foreign_keys,
            indexes=indexes,
            comment=comment,
            row_count_estimate=row_count
        )
    
    def _get_columns(self, table_name: str, schema: Optional[str] = None) -> List[ColumnInfo]:
        """Get column information for a table."""
        columns = []
        
        try:
            column_defs = self.inspector.get_columns(table_name, schema=schema)
            pk_columns = self._get_primary_keys(table_name, schema)
            fk_map = self._build_foreign_key_map(table_name, schema)
            
            for col in column_defs:
                col_name = col['name']
                columns.append(ColumnInfo(
                    name=col_name,
                    data_type=self._normalize_data_type(str(col['type'])),
                    nullable=col.get('nullable', True),
                    default=col.get('default'),
                    primary_key=col_name in pk_columns,
                    foreign_key=fk_map.get(col_name),
                    comment=col.get('comment')
                ))
            
            return columns
        except Exception as e:
            logger.error(f"Failed to get columns for {table_name}: {e}")
            raise
    
    def _get_primary_keys(self, table_name: str, schema: Optional[str] = None) -> List[str]:
        """Get primary key columns for a table."""
        try:
            pk_constraint = self.inspector.get_pk_constraint(table_name, schema=schema)
            return pk_constraint.get('constrained_columns', []) if pk_constraint else []
        except Exception as e:
            logger.error(f"Failed to get primary keys for {table_name}: {e}")
            return []
    
    def _get_foreign_keys(
        self, 
        table_name: str, 
        schema: Optional[str] = None
    ) -> List[ForeignKeyInfo]:
        """Get foreign key information for a table."""
        foreign_keys = []
        
        try:
            fk_constraints = self.inspector.get_foreign_keys(table_name, schema=schema)
            
            for fk in fk_constraints:
                foreign_keys.append(ForeignKeyInfo(
                    constraint_name=fk.get('name', ''),
                    source_table=table_name,
                    source_columns=fk.get('constrained_columns', []),
                    target_table=fk.get('referred_table', ''),
                    target_columns=fk.get('referred_columns', [])
                ))
            
            return foreign_keys
        except Exception as e:
            logger.error(f"Failed to get foreign keys for {table_name}: {e}")
            return []
    
    def _build_foreign_key_map(
        self, 
        table_name: str, 
        schema: Optional[str] = None
    ) -> Dict[str, str]:
        """Build a map of column names to their foreign key references."""
        fk_map = {}
        foreign_keys = self._get_foreign_keys(table_name, schema)
        
        for fk in foreign_keys:
            for i, source_col in enumerate(fk.source_columns):
                target_col = fk.target_columns[i] if i < len(fk.target_columns) else ''
                fk_map[source_col] = f"{fk.target_table}.{target_col}"
        
        return fk_map
    
    def _get_indexes(self, table_name: str, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get index information for a table."""
        try:
            indexes = self.inspector.get_indexes(table_name, schema=schema)
            return [
                {
                    'name': idx.get('name', ''),
                    'columns': idx.get('column_names', []),
                    'unique': idx.get('unique', False)
                }
                for idx in indexes
            ]
        except Exception as e:
            logger.error(f"Failed to get indexes for {table_name}: {e}")
            return []
    
    def _get_table_comment(self, table_name: str, schema: Optional[str] = None) -> Optional[str]:
        """Get table comment/description."""
        try:
            table_info = self.inspector.get_table_comment(table_name, schema=schema)
            return table_info.get('text') if table_info else None
        except Exception as e:
            logger.debug(f"No comment available for {table_name}: {e}")
            return None
    
    def _estimate_row_count(self, table_name: str, schema: Optional[str] = None) -> Optional[int]:
        """Estimate row count for a table."""
        try:
            schema_prefix = f"{schema}." if schema else ""
            
            # Database-specific row count estimation
            if self.database_type == DatabaseType.POSTGRESQL:
                query = sa.text(f"""
                    SELECT reltuples::bigint AS estimate
                    FROM pg_class
                    WHERE relname = :table_name
                """)
                with self.engine.connect() as conn:
                    result = conn.execute(query, {"table_name": table_name}).scalar()
                    return int(result) if result else None
            
            elif self.database_type == DatabaseType.MYSQL:
                query = sa.text(f"""
                    SELECT table_rows
                    FROM information_schema.tables
                    WHERE table_name = :table_name
                    AND table_schema = DATABASE()
                """)
                with self.engine.connect() as conn:
                    result = conn.execute(query, {"table_name": table_name}).scalar()
                    return int(result) if result else None
            
            elif self.database_type == DatabaseType.ORACLE:
                query = sa.text(f"""
                    SELECT num_rows
                    FROM all_tables
                    WHERE table_name = :table_name
                """)
                with self.engine.connect() as conn:
                    result = conn.execute(query, {"table_name": table_name.upper()}).scalar()
                    return int(result) if result else None
            
            elif self.database_type == DatabaseType.SQLSERVER:
                query = sa.text(f"""
                    SELECT SUM(row_count)
                    FROM sys.dm_db_partition_stats
                    WHERE object_id = OBJECT_ID(:table_name)
                    AND index_id < 2
                """)
                with self.engine.connect() as conn:
                    full_table_name = f"{schema_prefix}{table_name}"
                    result = conn.execute(query, {"table_name": full_table_name}).scalar()
                    return int(result) if result else None
            
            else:
                # Fallback: actual COUNT (can be slow for large tables)
                query = sa.text(f"SELECT COUNT(*) FROM {schema_prefix}{table_name}")
                with self.engine.connect() as conn:
                    result = conn.execute(query).scalar()
                    return int(result) if result else None
        
        except Exception as e:
            logger.debug(f"Failed to estimate row count for {table_name}: {e}")
            return None
    
    def _normalize_data_type(self, data_type: str) -> str:
        """Normalize database-specific data types to common types."""
        data_type_upper = data_type.upper()
        
        # Integer types
        if any(t in data_type_upper for t in ['INT', 'SERIAL', 'BIGSERIAL', 'SMALLINT', 'BIGINT', 'NUMBER']):
            return 'integer'
        
        # Numeric/Decimal types
        if any(t in data_type_upper for t in ['NUMERIC', 'DECIMAL', 'FLOAT', 'DOUBLE', 'REAL']):
            return 'numeric'
        
        # String types
        if any(t in data_type_upper for t in ['VARCHAR', 'CHAR', 'TEXT', 'NVARCHAR', 'NCHAR', 'VARCHAR2', 'CLOB']):
            return 'varchar'
        
        # Boolean
        if 'BOOL' in data_type_upper:
            return 'boolean'
        
        # Date/Time types
        if any(t in data_type_upper for t in ['DATE', 'TIME']):
            if 'TIMESTAMP' in data_type_upper:
                return 'timestamp'
            return 'date'
        
        # JSON types
        if 'JSON' in data_type_upper:
            return 'json'
        
        # Binary types
        if any(t in data_type_upper for t in ['BLOB', 'BYTEA', 'BINARY', 'VARBINARY']):
            return 'binary'
        
        # Default: return as-is
        return data_type.lower()
    
    def detect_relationships(
        self, 
        table_info_dict: Dict[str, TableInfo]
    ) -> List[Dict[str, Any]]:
        """
        Detect relationships between tables based on foreign keys.
        
        Args:
            table_info_dict: Dictionary of table information
            
        Returns:
            List of relationship definitions
        """
        relationships = []
        
        for table_name, table_info in table_info_dict.items():
            for fk in table_info.foreign_keys:
                # Determine relationship type
                rel_type = self._determine_relationship_type(
                    fk, table_info_dict
                )
                
                # Create relationship definition
                relationship = {
                    'name': f"{fk.source_table}_to_{fk.target_table}",
                    'parent': f"{fk.target_table}.{fk.target_columns[0]}",
                    'child': f"{fk.source_table}.{fk.source_columns[0]}",
                    'type': rel_type,
                    'description': f"Foreign key from {fk.source_table} to {fk.target_table}"
                }
                relationships.append(relationship)
        
        logger.info(f"Detected {len(relationships)} relationships")
        return relationships
    
    def _determine_relationship_type(
        self, 
        fk: ForeignKeyInfo, 
        table_info_dict: Dict[str, TableInfo]
    ) -> str:
        """
        Determine the type of relationship (one-to-many, many-to-one, etc.).
        
        Args:
            fk: Foreign key information
            table_info_dict: Dictionary of table information
            
        Returns:
            Relationship type string
        """
        # Check if the foreign key column is part of a unique constraint or primary key
        source_table = table_info_dict.get(fk.source_table)
        if not source_table:
            return 'one_to_many'
        
        # If FK columns are primary keys, might be one-to-one or many-to-many
        fk_is_pk = all(col in source_table.primary_keys for col in fk.source_columns)
        
        if fk_is_pk:
            # Check if it's a junction table (has multiple FKs and composite PK)
            if len(source_table.foreign_keys) >= 2 and len(source_table.primary_keys) >= 2:
                return 'many_to_many'
            return 'one_to_one'
        
        return 'one_to_many'
