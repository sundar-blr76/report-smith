"""Simple configuration manager for ReportSmith."""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from ..logger import get_logger

logger = get_logger(__name__)


@dataclass
class TableConfig:
    """Table configuration."""
    name: str
    description: str
    primary_key: str
    columns: Dict[str, Any]


@dataclass
class DatabaseConfig:
    """Database configuration."""
    name: str
    type: str
    tables: List[TableConfig]
    dimensions: Optional[Dict[str, Any]] = None  # Dimensions from schema.yaml
    business_context: Optional[Dict[str, Any]] = None


@dataclass
class ApplicationConfig:
    """Application configuration."""
    id: str  # Application ID (used for embedding keys)
    name: str
    description: str
    databases: List[DatabaseConfig]


class ConfigurationManager:
    """Manages application configuration loaded from YAML files."""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Path to configuration directory (default: ./config/applications)
        """
        if config_dir is None:
            # Use project root relative path
            project_root = Path(__file__).parent.parent.parent.parent
            config_dir = project_root / "config" / "applications"
        
        self.config_dir = Path(config_dir)
        self._applications: Dict[str, ApplicationConfig] = {}
        
        logger.info(f"Configuration manager initialized with config_dir: {self.config_dir}")
    
    def load_all_applications(self) -> List[ApplicationConfig]:
        """
        Load all application configurations from nested directory structure.
        
        Structure expected:
            config/applications/
                <app_name>/
                    app.yaml       - Application metadata and business logic
                    schema.yaml    - Table definitions
                    instances/
                        <instance_name>.yaml - Instance connections
        
        Returns:
            List of ApplicationConfig objects
        """
        applications = []
        
        if not self.config_dir.exists():
            logger.warning(f"Config directory does not exist: {self.config_dir}")
            return applications
        
        # Find all application directories (contains app.yaml)
        app_dirs = [d for d in self.config_dir.iterdir() 
                   if d.is_dir() and (d / "app.yaml").exists()]
        
        logger.info(f"Found {len(app_dirs)} application directories")
        
        for app_dir in app_dirs:
            try:
                app_config = self.load_application_dir(app_dir)
                if app_config:
                    applications.append(app_config)
                    self._applications[app_config.name] = app_config
            except Exception as e:
                logger.error(f"Failed to load application from {app_dir}: {e}", exc_info=True)
        
        logger.info(f"Successfully loaded {len(applications)} application configurations")
        return applications
    
    def load_application_dir(self, app_dir: Path) -> Optional[ApplicationConfig]:
        """
        Load application configuration from directory structure.
        
        Args:
            app_dir: Path to application directory
            
        Returns:
            ApplicationConfig object or None if loading failed
        """
        logger.debug(f"Loading application from directory: {app_dir}")
        
        try:
            # Load app.yaml
            app_file = app_dir / "app.yaml"
            with open(app_file, 'r') as f:
                app_data = yaml.safe_load(f)
            
            if not app_data or 'application' not in app_data:
                logger.warning(f"Invalid app.yaml in {app_dir}")
                return None
            
            app_info = app_data['application']
            app_id = app_info.get('id', app_dir.name)
            app_name = app_info.get('name', app_dir.name)
            app_desc = app_info.get('description', '')
            
            # Extract business context
            business_context = app_data.get('business_context', None)
            
            # Load schema.yaml
            schema_file = app_dir / "schema.yaml"
            schema_data = {}
            if schema_file.exists():
                with open(schema_file, 'r') as f:
                    schema_data = yaml.safe_load(f) or {}
            
            # Load instances
            databases = []
            instances_dir = app_dir / "instances"
            if instances_dir.exists():
                instance_files = list(instances_dir.glob("*.yaml")) + list(instances_dir.glob("*.yml"))
                logger.debug(f"Found {len(instance_files)} instance files")
                
                for inst_file in instance_files:
                    db_config = self._parse_instance_config(
                        inst_file, 
                        app_id,
                        schema_data.get('tables', {}),
                        schema_data.get('dimensions', {}),  # Pass dimensions from schema
                        business_context
                    )
                    if db_config:
                        databases.append(db_config)
            
            app_config = ApplicationConfig(
                id=app_id,
                name=app_name,
                description=app_desc,
                databases=databases
            )
            
            logger.info(f"Loaded application: {app_name} ({app_id}) with {len(databases)} database instances")
            return app_config
            
        except Exception as e:
            logger.error(f"Error loading application from {app_dir}: {e}", exc_info=True)
            return None
    
    def _parse_instance_config(
        self, 
        instance_file: Path, 
        app_id: str, 
        schema_tables: Dict[str, Any],
        schema_dimensions: Dict[str, Any],
        business_context: Optional[Dict[str, Any]] = None
    ) -> Optional[DatabaseConfig]:
        """
        Parse database instance configuration.
        
        Args:
            instance_file: Path to instance YAML file
            app_id: Application ID
            schema_tables: Table definitions from schema.yaml
            business_context: Business context from app.yaml
            
        Returns:
            DatabaseConfig or None
        """
        try:
            with open(instance_file, 'r') as f:
                inst_data = yaml.safe_load(f) or {}
            
            if 'instance' not in inst_data:
                logger.warning(f"Invalid instance file {instance_file}: missing 'instance' key")
                return None
            
            inst_info = inst_data['instance']
            instance_id = inst_info.get('instance_id', instance_file.stem)
            instance_name = inst_info.get('instance_name', instance_id)
            
            # Parse tables from schema
            tables = []
            for table_name, table_data in schema_tables.items():
                table_config = TableConfig(
                    name=table_name,
                    description=table_data.get('description', ''),
                    primary_key=table_data.get('primary_key', 'id'),
                    columns=table_data.get('columns', {})
                )
                tables.append(table_config)
            
            db_config = DatabaseConfig(
                name=instance_id,
                type='postgresql',
                tables=tables,
                dimensions=schema_dimensions,  # Include dimensions from schema
                business_context=business_context
            )
            
            logger.debug(f"Parsed instance config: {instance_id} ({instance_name}) with {len(tables)} tables")
            return db_config
            
        except Exception as e:
            logger.error(f"Error parsing instance config {instance_file}: {e}", exc_info=True)
            return None
    
    def get_application(self, name: str) -> Optional[ApplicationConfig]:
        """
        Get application configuration by name.
        
        Args:
            name: Application name
            
        Returns:
            ApplicationConfig or None if not found
        """
        return self._applications.get(name)
    
    def get_all_applications(self) -> List[ApplicationConfig]:
        """Get all loaded application configurations."""
        return list(self._applications.values())
