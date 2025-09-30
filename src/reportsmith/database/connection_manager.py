"""Database connection management for multiple database types."""

from typing import Dict, Any, Optional
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
from loguru import logger
import threading
from contextlib import contextmanager

from ..config_system.config_models import DatabaseInstanceConfig, DatabaseType


class DatabaseConnectionManager:
    """Manages connections to multiple database instances."""
    
    def __init__(self):
        self._engines: Dict[str, Engine] = {}
        self._lock = threading.Lock()
    
    def register_database_instance(self, instance_key: str, instance_config: DatabaseInstanceConfig) -> None:
        """Register a database instance and create connection engine."""
        with self._lock:
            try:
                connection_url = self._build_connection_url(instance_config)
                
                # Configure engine based on database type and pool settings
                engine_kwargs = self._get_engine_kwargs(instance_config)
                
                engine = create_engine(connection_url, **engine_kwargs)
                
                # Test connectivity
                with engine.connect() as conn:
                    self._test_connection(conn, instance_config.database_config.database_type)
                
                self._engines[instance_key] = engine
                
                logger.info(f"Registered database instance: {instance_key} ({instance_config.database_config.database_type.value})")
                
            except Exception as e:
                logger.error(f"Failed to register database instance {instance_key}: {e}")
                raise
    
    def get_engine(self, instance_key: str) -> Engine:
        """Get engine for a registered database instance."""
        if instance_key not in self._engines:
            raise ValueError(f"Database instance '{instance_key}' not registered")
        
        return self._engines[instance_key]
    
    @contextmanager
    def get_connection(self, instance_key: str):
        """Get a database connection context manager."""
        engine = self.get_engine(instance_key)
        
        with engine.connect() as connection:
            yield connection
    
    def _build_connection_url(self, instance_config: DatabaseInstanceConfig) -> str:
        """Build SQLAlchemy connection URL."""
        db_config = instance_config.database_config
        
        # Build base URL components
        username = db_config.username or ""
        password = db_config.password or ""
        host = db_config.host
        port = db_config.port
        
        # Build URL based on database type
        if db_config.database_type == DatabaseType.POSTGRESQL:
            database = db_config.database_name
            url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
            
        elif db_config.database_type == DatabaseType.MYSQL:
            database = db_config.database_name
            url = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
            
        elif db_config.database_type == DatabaseType.ORACLE:
            service_name = db_config.service_name
            if not service_name:
                raise ValueError("Oracle database requires service_name")
            url = f"oracle+cx_oracle://{username}:{password}@{host}:{port}/?service_name={service_name}"
            
        elif db_config.database_type == DatabaseType.SQLSERVER:
            database = db_config.database_name
            url = f"mssql+pyodbc://{username}:{password}@{host}:{port}/{database}?driver=ODBC+Driver+17+for+SQL+Server"
            
        elif db_config.database_type == DatabaseType.SQLITE:
            # For SQLite, database_name is the file path
            url = f"sqlite:///{db_config.database_name}"
            
        else:
            raise ValueError(f"Unsupported database type: {db_config.database_type}")
        
        return url
    
    def _get_engine_kwargs(self, instance_config: DatabaseInstanceConfig) -> Dict[str, Any]:
        """Get SQLAlchemy engine configuration."""
        db_config = instance_config.database_config
        
        kwargs = {
            "echo": False,  # Set to True for SQL debugging
        }
        
        # Configure connection pooling if specified
        if db_config.connection_pool_config:
            pool_config = db_config.connection_pool_config
            
            kwargs.update({
                "poolclass": QueuePool,
                "pool_size": pool_config.min_connections,
                "max_overflow": pool_config.max_connections - pool_config.min_connections,
                "pool_timeout": pool_config.connection_timeout,
                "pool_recycle": pool_config.max_lifetime,
            })
        
        # Database-specific configurations
        if db_config.database_type == DatabaseType.POSTGRESQL:
            kwargs["connect_args"] = {
                "options": f"-csearch_path={db_config.schema or 'public'}"
            }
        
        elif db_config.database_type == DatabaseType.MYSQL:
            kwargs["connect_args"] = {
                "charset": "utf8mb4",
            }
        
        elif db_config.database_type == DatabaseType.ORACLE:
            kwargs["connect_args"] = {
                "threaded": True,
            }
        
        # Add any additional connection parameters
        if db_config.connection_params:
            if "connect_args" not in kwargs:
                kwargs["connect_args"] = {}
            kwargs["connect_args"].update(db_config.connection_params)
        
        return kwargs
    
    def _test_connection(self, connection, database_type: DatabaseType) -> None:
        """Test database connectivity with a simple query."""
        test_queries = {
            DatabaseType.POSTGRESQL: "SELECT 1",
            DatabaseType.MYSQL: "SELECT 1",
            DatabaseType.ORACLE: "SELECT 1 FROM DUAL",
            DatabaseType.SQLSERVER: "SELECT 1",
            DatabaseType.SQLITE: "SELECT 1",
        }
        
        test_query = test_queries.get(database_type, "SELECT 1")
        
        try:
            result = connection.execute(text(test_query))
            result.fetchone()
            logger.debug(f"Database connectivity test passed for {database_type.value}")
            
        except Exception as e:
            logger.error(f"Database connectivity test failed for {database_type.value}: {e}")
            raise
    
    def get_database_info(self, instance_key: str) -> Dict[str, Any]:
        """Get information about a database instance."""
        engine = self.get_engine(instance_key)
        
        with engine.connect() as conn:
            # Get database-specific information
            if 'postgresql' in str(engine.url):
                version_result = conn.execute(text("SELECT version()"))
                version = version_result.fetchone()[0]
                
                # Get current schema
                schema_result = conn.execute(text("SELECT current_schema()"))
                current_schema = schema_result.fetchone()[0]
                
                return {
                    'database_type': 'postgresql',
                    'version': version,
                    'current_schema': current_schema,
                    'url': str(engine.url).split('@')[1] if '@' in str(engine.url) else str(engine.url)
                }
            
            elif 'mysql' in str(engine.url):
                version_result = conn.execute(text("SELECT VERSION()"))
                version = version_result.fetchone()[0]
                
                return {
                    'database_type': 'mysql',
                    'version': version,
                    'url': str(engine.url).split('@')[1] if '@' in str(engine.url) else str(engine.url)
                }
            
            elif 'oracle' in str(engine.url):
                version_result = conn.execute(text("SELECT * FROM v$version WHERE ROWNUM = 1"))
                version = version_result.fetchone()[0]
                
                return {
                    'database_type': 'oracle',
                    'version': version,
                    'url': str(engine.url).split('@')[1] if '@' in str(engine.url) else str(engine.url)
                }
            
            else:
                return {
                    'database_type': 'unknown',
                    'url': str(engine.url)
                }
    
    def test_all_connections(self) -> Dict[str, Dict[str, Any]]:
        """Test all registered database connections."""
        results = {}
        
        for instance_key, engine in self._engines.items():
            try:
                with engine.connect() as conn:
                    # Test with simple query
                    conn.execute(text("SELECT 1"))
                    
                results[instance_key] = {
                    'status': 'connected',
                    'info': self.get_database_info(instance_key)
                }
                
            except Exception as e:
                results[instance_key] = {
                    'status': 'failed',
                    'error': str(e)
                }
                logger.error(f"Connection test failed for {instance_key}: {e}")
        
        return results
    
    def close_all_connections(self) -> None:
        """Close all database connections."""
        with self._lock:
            for instance_key, engine in self._engines.items():
                try:
                    engine.dispose()
                    logger.info(f"Closed connection for {instance_key}")
                except Exception as e:
                    logger.error(f"Error closing connection for {instance_key}: {e}")
            
            self._engines.clear()