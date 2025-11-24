"""Onboarding manager to orchestrate database schema inference and configuration generation.

This manager connects to your database and extracts schema information by:
1. Creating a SQLAlchemy engine with your database credentials
2. Using SchemaIntrospector to query system catalogs (pg_catalog, information_schema, etc.)
3. Detecting tables, columns, data types, constraints, and relationships
4. Generating YAML configuration files ready for ReportSmith

The introspection process reads directly from database system catalogs to ensure
accurate schema extraction across PostgreSQL, MySQL, Oracle, SQL Server, and SQLite.
"""

from typing import Dict, Optional, Any, List
from pathlib import Path
import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from .schema_introspector import SchemaIntrospector, TableInfo
from .template_generator import TemplateGenerator
from ..logger import get_logger
from ..config_system.config_models import DatabaseType, DatabaseConfig

logger = get_logger(__name__)


class OnboardingManager:
    """Manage the complete onboarding process."""
    
    def __init__(
        self,
        application_id: str,
        application_name: str,
        database_config: DatabaseConfig
    ):
        """
        Initialize the onboarding manager.
        
        Args:
            application_id: Unique identifier for the application
            application_name: Human-readable name for the application
            database_config: Database configuration
        """
        self.application_id = application_id
        self.application_name = application_name
        self.database_config = database_config
        
        # Create database engine
        self.engine = self._create_engine()
        
        # Initialize components
        self.introspector = SchemaIntrospector(
            self.engine,
            database_config.database_type
        )
        self.template_generator = TemplateGenerator(
            application_id,
            application_name,
            database_config.database_type
        )
        
        logger.info(f"Initialized OnboardingManager for {application_id}")
    
    def run_onboarding(
        self,
        output_dir: str,
        schema: Optional[str] = None,
        tables: Optional[list] = None,
        business_function: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Run the complete onboarding process.
        
        Args:
            output_dir: Directory to write configuration files
            schema: Specific database schema to introspect
            tables: Specific tables to introspect (default: all)
            business_function: Optional business function description
            
        Returns:
            Dictionary with paths to generated files
        """
        logger.info("Starting onboarding process")
        
        try:
            # Step 1: Introspect database schema
            logger.info("Step 1: Introspecting database schema...")
            table_info_dict = self.introspector.introspect_schema(schema, tables)
            
            if not table_info_dict:
                raise ValueError("No tables found in database")
            
            logger.info(f"Found {len(table_info_dict)} tables")
            
            # Step 2: Detect relationships
            logger.info("Step 2: Detecting relationships...")
            relationships = self.introspector.detect_relationships(table_info_dict)
            logger.info(f"Detected {len(relationships)} relationships")
            
            # Step 3: Generate configuration templates
            logger.info("Step 3: Generating configuration templates...")
            
            app_yaml = self.template_generator.generate_app_yaml(
                table_info_dict,
                relationships,
                business_function
            )
            
            schema_yaml = self.template_generator.generate_schema_yaml(
                table_info_dict
            )
            
            user_input_template = self.template_generator.generate_user_input_template(
                table_info_dict
            )
            
            # Step 4: Write files to output directory
            logger.info("Step 4: Writing configuration files...")
            output_paths = self._write_configuration_files(
                output_dir,
                app_yaml,
                schema_yaml,
                user_input_template
            )
            
            logger.info("Onboarding process completed successfully")
            
            # Generate summary
            self._print_summary(table_info_dict, relationships, output_paths)
            
            return output_paths
            
        except Exception as e:
            logger.error(f"Onboarding process failed: {e}")
            raise
    
    def _create_engine(self) -> Engine:
        """Create SQLAlchemy engine from database configuration."""
        connection_url = self._build_connection_url()
        
        engine_kwargs = {
            'pool_pre_ping': True,
            'pool_recycle': 3600,
            'echo': False
        }
        
        engine = create_engine(connection_url, **engine_kwargs)
        
        # Test connection
        try:
            with engine.connect() as conn:
                from sqlalchemy import text
                conn.execute(text("SELECT 1"))
            logger.info("Database connection successful")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
        
        return engine
    
    def _build_connection_url(self) -> str:
        """Build SQLAlchemy connection URL from configuration."""
        db = self.database_config
        
        username = db.username or ""
        password = db.password or ""
        host = db.host
        port = db.port
        
        if db.database_type == DatabaseType.POSTGRESQL:
            url = f"postgresql://{username}:{password}@{host}:{port}/{db.database_name}"
        
        elif db.database_type == DatabaseType.MYSQL:
            url = f"mysql+pymysql://{username}:{password}@{host}:{port}/{db.database_name}"
        
        elif db.database_type == DatabaseType.ORACLE:
            service_name = db.service_name
            if not service_name:
                raise ValueError("Oracle database requires service_name")
            url = f"oracle+cx_oracle://{username}:{password}@{host}:{port}/?service_name={service_name}"
        
        elif db.database_type == DatabaseType.SQLSERVER:
            url = f"mssql+pyodbc://{username}:{password}@{host}:{port}/{db.database_name}?driver=ODBC+Driver+17+for+SQL+Server"
        
        elif db.database_type == DatabaseType.SQLITE:
            url = f"sqlite:///{db.database_name}"
        
        else:
            raise ValueError(f"Unsupported database type: {db.database_type}")
        
        return url
    
    def _write_configuration_files(
        self,
        output_dir: str,
        app_yaml: str,
        schema_yaml: str,
        user_input_template: str
    ) -> Dict[str, str]:
        """Write configuration files to output directory."""
        # Create output directory structure
        app_dir = Path(output_dir) / self.application_id
        app_dir.mkdir(parents=True, exist_ok=True)
        
        # Write files
        files = {
            'app_yaml': app_dir / 'app.yaml',
            'schema_yaml': app_dir / 'schema.yaml',
            'user_input': app_dir / 'user_input_template.yaml',
            'readme': app_dir / 'README.md'
        }
        
        # Write app.yaml
        with open(files['app_yaml'], 'w') as f:
            f.write(app_yaml)
        logger.info(f"Written app.yaml to {files['app_yaml']}")
        
        # Write schema.yaml
        with open(files['schema_yaml'], 'w') as f:
            f.write(schema_yaml)
        logger.info(f"Written schema.yaml to {files['schema_yaml']}")
        
        # Write user input template
        with open(files['user_input'], 'w') as f:
            f.write(user_input_template)
        logger.info(f"Written user input template to {files['user_input']}")
        
        # Write README
        readme_content = self._generate_readme()
        with open(files['readme'], 'w') as f:
            f.write(readme_content)
        logger.info(f"Written README to {files['readme']}")
        
        return {k: str(v) for k, v in files.items()}
    
    def _generate_readme(self) -> str:
        """Generate README for the onboarded application."""
        return f"""# {self.application_name} Configuration

This configuration was auto-generated by the ReportSmith onboarding process.

## Files Generated

- **app.yaml**: Application configuration with relationships and business context
- **schema.yaml**: Database schema definition with table and column details
- **user_input_template.yaml**: Template for adding business context and metadata

## Next Steps

1. Review the generated `schema.yaml` and verify table/column definitions
2. Fill in the business context in `user_input_template.yaml`:
   - Add business names and descriptions for tables
   - Add natural language aliases for columns
   - Define business metrics and rules
   - Provide sample queries
3. Copy relevant business context from `user_input_template.yaml` to `app.yaml`
4. Test your configuration with ReportSmith

## Configuration Structure

```
{self.application_id}/
├── app.yaml                    # Main application config (EDIT THIS)
├── schema.yaml                 # Schema definition (REVIEW & EDIT)
├── user_input_template.yaml    # Business context template (FILL THIS OUT)
└── README.md                   # This file
```

## Tips

- Focus on adding business context first (table descriptions, aliases)
- Define key business metrics used in queries
- Document common query patterns in sample_queries
- Set up business rules for automatic filters

## Database Details

- **Database Type**: {self.database_config.database_type.value}
- **Host**: {self.database_config.host}
- **Database**: {self.database_config.database_name}
- **Schema**: {self.database_config.schema or 'default'}

## Support

For more information, see the ReportSmith documentation.
"""
    
    def _print_summary(
        self,
        table_info_dict: Dict[str, TableInfo],
        relationships: List[Dict[str, Any]],
        output_paths: Dict[str, str]
    ):
        """Print summary of onboarding process."""
        print("\n" + "=" * 80)
        print(f"ONBOARDING COMPLETED: {self.application_name}")
        print("=" * 80)
        print(f"\nApplication ID: {self.application_id}")
        print(f"Database Type: {self.database_config.database_type.value}")
        print(f"\nSchema Analysis:")
        print(f"  - Tables introspected: {len(table_info_dict)}")
        print(f"  - Relationships detected: {len(relationships)}")
        
        total_columns = sum(len(t.columns) for t in table_info_dict.values())
        print(f"  - Total columns: {total_columns}")
        
        print(f"\nGenerated Files:")
        for file_type, file_path in output_paths.items():
            print(f"  - {file_type}: {file_path}")
        
        print(f"\nNext Steps:")
        print(f"  1. Review schema.yaml and verify definitions")
        print(f"  2. Fill out user_input_template.yaml with business context")
        print(f"  3. Update app.yaml with business metrics and rules")
        print(f"  4. Test your configuration with ReportSmith")
        
        print("\n" + "=" * 80 + "\n")
