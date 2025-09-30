"""Simple connection manager for accessing configured databases."""

import os
from typing import Dict, Optional, Any
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager

from ..logger import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Manages database connections using connection pools."""
    
    def __init__(self):
        """Initialize the connection manager."""
        self._pools: Dict[str, SimpleConnectionPool] = {}
        self._config: Dict[str, Dict[str, Any]] = {}
        logger.info("Connection manager initialized")
        
        # Auto-register databases from environment
        self._register_from_environment()
    
    def _register_from_environment(self) -> None:
        """Register databases from environment variables."""
        # Register financial_testdb if environment variables are set
        if all([
            os.getenv('FINANCIAL_TESTDB_HOST'),
            os.getenv('FINANCIAL_TESTDB_PORT'),
            os.getenv('FINANCIAL_TESTDB_NAME'),
            os.getenv('FINANCIAL_TESTDB_USER'),
            os.getenv('FINANCIAL_TESTDB_PASSWORD')
        ]):
            self.register_database(
                db_name='financial_testdb',
                host=os.getenv('FINANCIAL_TESTDB_HOST'),
                port=int(os.getenv('FINANCIAL_TESTDB_PORT')),
                database=os.getenv('FINANCIAL_TESTDB_NAME'),
                user=os.getenv('FINANCIAL_TESTDB_USER'),
                password=os.getenv('FINANCIAL_TESTDB_PASSWORD')
            )
            logger.info("Registered financial_testdb from environment variables")
        
        # Register reportsmith database if environment variables are set
        if all([
            os.getenv('REPORTSMITH_DB_HOST'),
            os.getenv('REPORTSMITH_DB_PORT'),
            os.getenv('REPORTSMITH_DB_NAME'),
            os.getenv('REPORTSMITH_DB_USER'),
            os.getenv('REPORTSMITH_DB_PASSWORD')
        ]):
            self.register_database(
                db_name='reportsmith',
                host=os.getenv('REPORTSMITH_DB_HOST'),
                port=int(os.getenv('REPORTSMITH_DB_PORT')),
                database=os.getenv('REPORTSMITH_DB_NAME'),
                user=os.getenv('REPORTSMITH_DB_USER'),
                password=os.getenv('REPORTSMITH_DB_PASSWORD')
            )
            logger.info("Registered reportsmith database from environment variables")
    
    def register_database(
        self,
        db_name: str,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        min_conn: int = 2,
        max_conn: int = 10
    ) -> None:
        """
        Register a database connection pool.
        
        Args:
            db_name: Logical name for the database
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
            min_conn: Minimum connections in pool
            max_conn: Maximum connections in pool
        """
        try:
            # Store configuration
            self._config[db_name] = {
                'host': host,
                'port': port,
                'database': database,
                'user': user,
                'password': password
            }
            
            # Create connection pool
            pool = SimpleConnectionPool(
                minconn=min_conn,
                maxconn=max_conn,
                host=host,
                port=port,
                database=database,
                user=user,
                password=password
            )
            
            self._pools[db_name] = pool
            logger.info(f"Registered database pool: {db_name} ({host}:{port}/{database})")
            
        except Exception as e:
            logger.error(f"Failed to register database {db_name}: {e}", exc_info=True)
            raise
    
    def get_connection(self, db_name: str):
        """
        Get a connection from the pool.
        
        Args:
            db_name: Logical database name
            
        Returns:
            Database connection
        """
        if db_name not in self._pools:
            raise ValueError(f"Database {db_name} not registered")
        
        try:
            conn = self._pools[db_name].getconn()
            logger.debug(f"Retrieved connection for {db_name}")
            return conn
        except Exception as e:
            logger.error(f"Failed to get connection for {db_name}: {e}", exc_info=True)
            raise
    
    def return_connection(self, db_name: str, conn) -> None:
        """
        Return a connection to the pool.
        
        Args:
            db_name: Logical database name
            conn: Connection to return
        """
        if db_name not in self._pools:
            logger.warning(f"Attempted to return connection for unknown database: {db_name}")
            return
        
        try:
            self._pools[db_name].putconn(conn)
            logger.debug(f"Returned connection for {db_name}")
        except Exception as e:
            logger.error(f"Failed to return connection for {db_name}: {e}", exc_info=True)
    
    @contextmanager
    def connection(self, db_name: str):
        """
        Context manager for database connections.
        
        Args:
            db_name: Logical database name
            
        Yields:
            Database connection
        """
        conn = self.get_connection(db_name)
        try:
            yield conn
        finally:
            self.return_connection(db_name, conn)
    
    def get_available_databases(self) -> list:
        """Get list of registered database names."""
        return list(self._pools.keys())
    
    def close_all(self) -> None:
        """Close all connection pools."""
        for db_name, pool in self._pools.items():
            try:
                pool.closeall()
                logger.info(f"Closed connection pool for {db_name}")
            except Exception as e:
                logger.error(f"Error closing pool for {db_name}: {e}", exc_info=True)
        
        self._pools.clear()
        self._config.clear()
        logger.info("All connection pools closed")
    
    def _get_connection_string(self, db_name: str) -> str:
        """
        Get SQLAlchemy connection string for a database.
        
        Args:
            db_name: Logical database name
            
        Returns:
            SQLAlchemy connection URL
        """
        if db_name not in self._config:
            raise ValueError(f"Database {db_name} not registered")
        
        config = self._config[db_name]
        return (
            f"postgresql://{config['user']}:{config['password']}"
            f"@{config['host']}:{config['port']}/{config['database']}"
        )
    
    def test_connection(self, db_name: str) -> bool:
        """
        Test if a database connection works.
        
        Args:
            db_name: Logical database name
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.connection(db_name) as conn:
                with conn.cursor() as cursor:
                    logger.debug(f"SQL: SELECT 1 (connection test for {db_name})")
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    if result and result[0] == 1:
                        logger.info(f"Connection test successful for {db_name}")
                        return True
            return False
        except Exception as e:
            logger.error(f"Connection test failed for {db_name}: {e}", exc_info=True)
            return False
