"""
Main application entry point for ReportSmith.
"""

import os
import sys
from pathlib import Path

from reportsmith.logger import LoggerManager, get_logger
from reportsmith.config_system import ConfigurationManager
from reportsmith.database.simple_connection_manager import ConnectionManager
from reportsmith.schema_intelligence.embedding_manager import EmbeddingManager
from reportsmith.schema_intelligence.dimension_loader import DimensionLoader


class ReportSmithApp:
    """Main application class for ReportSmith."""
    
    def __init__(self):
        """Initialize the application."""
        # Setup logging first
        self.logger_manager = LoggerManager()
        self.logger_manager.setup_logging(level="INFO")
        self.logger = get_logger(__name__)
        
        self.logger.info("Initializing ReportSmith Application")
        
        # Initialize components
        self.config_manager: ConfigurationManager = None
        self.connection_manager: ConnectionManager = None
        self.embedding_manager: EmbeddingManager = None
        self.dimension_loader: DimensionLoader = None
        
    def initialize(self) -> None:
        """Initialize all application components."""
        try:
            self.logger.info("Loading configuration system...")
            self.config_manager = ConfigurationManager()
            applications = self.config_manager.load_all_applications()
            self.logger.info(f"Loaded {len(applications)} application configurations")
            
            self.logger.info("Initializing database connection manager...")
            self.connection_manager = ConnectionManager()
            self.logger.info("Database connection manager initialized")
            
            self.logger.info("Initializing embedding manager...")
            # Determine embedding provider/model from settings
            from reportsmith.config import settings as app_settings
            # Default to OpenAI when key is present; otherwise fallback to local
            provider = "openai" if app_settings.openai_api_key else "local"
            self.embedding_manager = EmbeddingManager(
                embedding_model=app_settings.embedding_model,
                provider=provider,
                openai_api_key=app_settings.openai_api_key
            )
            self.logger.info(f"Embedding manager initialized with provider={provider}")
            
            self.logger.info("Initializing dimension loader...")
            self.dimension_loader = DimensionLoader(
                connection_manager=self.connection_manager,
                embedding_manager=self.embedding_manager
            )
            self.logger.info("Dimension loader initialized")
            
            # Load all schema metadata and domain values
            self._load_all_embeddings()
            
            self.logger.info("=" * 60)
            self.logger.info("ReportSmith Application Initialized Successfully")
            self.logger.info("=" * 60)
            
        except Exception as e:
            self.logger.error(f"Failed to initialize application: {e}", exc_info=True)
            raise
    
    def _load_all_embeddings(self) -> None:
        """Load schema metadata and domain values for all applications."""
        self.logger.info("Loading schema metadata and domain values...")
        
        applications = self.config_manager.load_all_applications()
        
        for app in applications:
            self.logger.info(f"Processing application: {app.name}")
            
            # Load schema metadata from config
            for db in app.databases:
                self.logger.info(f"  Loading schema for database: {db.name}")
                
                # Build schema config from database model
                schema_config = {"tables": {}}
                for table in db.tables:
                    schema_config["tables"][table.name] = {
                        "description": table.description or "",
                        "primary_key": table.primary_key or "",
                        "columns": table.columns  # columns is already a dict
                    }
                
                # Load into embedding manager
                self.embedding_manager.load_schema_metadata(app.id, schema_config)
                
                # Load business context if available
                if db.business_context:
                    context_config = {
                        "metrics": db.business_context.get("metrics", {}),
                        "sample_queries": db.business_context.get("sample_queries", [])
                    }
                    self.embedding_manager.load_business_context(app.id, context_config)
                
                # Identify and load domain values
                self._load_dimensions_for_database(app.id, db.name, schema_config, db.dimensions or {})
        
        # Log final stats
        stats = self.embedding_manager.get_stats()
        self.logger.info(f"Embedding loading complete: {stats}")
    
    def _load_dimensions_for_database(
        self, app_id: str, db_name: str, schema_config: dict, dimensions_config: dict
    ) -> None:
        """Load domain values for a specific database."""
        # Create schema config with dimensions
        enhanced_schema_config = {**schema_config, "dimensions": dimensions_config}
        
        # Identify dimension columns
        dimensions = self.dimension_loader.identify_dimension_columns(enhanced_schema_config)
        
        if not dimensions:
            self.logger.info(f"  No dimensions found for {db_name}")
            return
        
        self.logger.info(f"  Found {len(dimensions)} dimension columns")
        
        # Get database connection
        conn = self.connection_manager.get_connection(db_name)
        if not conn:
            self.logger.warning(f"  Cannot connect to {db_name}, skipping dimensions")
            return
        
        try:
            # Create SQLAlchemy engine from connection
            from sqlalchemy import create_engine
            conn_info = self.connection_manager._get_connection_string(db_name)
            engine = create_engine(conn_info)
            
            # Load each dimension
            for dim in dimensions:
                self.logger.info(f"    Loading dimension: {dim.table}.{dim.column}")
                
                values = self.dimension_loader.load_domain_values(
                    engine=engine,
                    dimension_config=dim
                )
                
                if values:
                    # Store in embedding manager
                    self.embedding_manager.load_domain_values(
                        app_id=app_id,
                        table=dim.table,
                        column=dim.column,
                        values=values,
                        context=dim.context
                    )
            
            engine.dispose()
            
        except Exception as e:
            self.logger.error(f"  Error loading dimensions for {db_name}: {e}")
        finally:
            self.connection_manager.return_connection(db_name, conn)
    
    def test_components(self) -> None:
        """Test core components to ensure they're working."""
        self.logger.info("Running component tests...")
        
        try:
            # Test configuration loading
            self.logger.info("Testing configuration loading...")
            apps = self.config_manager.load_all_applications()
            for app in apps:
                self.logger.info(f"  - Application: {app.name} ({app.description})")
                self.logger.info(f"    Databases: {len(app.databases)}")
                for db in app.databases:
                    self.logger.info(f"      * {db.name}: {len(db.tables)} tables")
            
            # Test database connections
            self.logger.info("Testing database connections...")
            available_dbs = self.connection_manager.get_available_databases()
            self.logger.info(f"  Available databases: {available_dbs}")
            
            for db_name in available_dbs:
                conn = self.connection_manager.get_connection(db_name)
                if conn:
                    self.logger.info(f"  ✓ Successfully connected to: {db_name}")
                    self.connection_manager.return_connection(db_name, conn)
                else:
                    self.logger.warning(f"  ✗ Failed to connect to: {db_name}")
            
            # Test embedding manager
            self.logger.info("Testing embedding manager...")
            stats = self.embedding_manager.get_stats()
            self.logger.info(f"  Embedding stats: {stats}")
            
            # Test dimension loader
            self.logger.info("Testing dimension loader...")
            self.logger.info(f"  Dimension loader ready: {self.dimension_loader is not None}")
            
            self.logger.info("=" * 60)
            self.logger.info("All component tests completed successfully")
            self.logger.info("=" * 60)
            
        except Exception as e:
            self.logger.error(f"Component test failed: {e}", exc_info=True)
            raise
    
    def run(self) -> None:
        """Run the main application."""
        try:
            self.logger.info("Starting main application run...")
            
            # For now, just run tests
            # Later this will be the main application loop or API server
            self.test_components()
            
            self.logger.info("Application run completed successfully")
            
        except Exception as e:
            self.logger.error(f"Application run failed: {e}", exc_info=True)
            raise
    
    def shutdown(self) -> None:
        """Cleanup and shutdown the application."""
        self.logger.info("Shutting down ReportSmith Application...")
        
        try:
            if self.connection_manager:
                self.connection_manager.close_all()
                self.logger.info("All database connections closed")
            
            self.logger.info("=" * 60)
            self.logger.info("ReportSmith Application Shutdown Complete")
            self.logger.info("=" * 60)
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}", exc_info=True)


def main():
    """Main entry point for the application."""
    app = ReportSmithApp()
    
    try:
        app.initialize()
        app.run()
        return 0
    except KeyboardInterrupt:
        print("\n\nApplication interrupted by user")
        return 130
    except Exception as e:
        print(f"\nFatal error: {e}", file=sys.stderr)
        return 1
    finally:
        app.shutdown()


if __name__ == "__main__":
    sys.exit(main())
