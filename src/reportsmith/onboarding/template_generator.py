"""Generate YAML configuration templates from introspected schema."""

from typing import Dict, List, Optional, Any
from datetime import datetime
import yaml

from .schema_introspector import TableInfo, ColumnInfo, ForeignKeyInfo
from ..logger import get_logger
from ..config_system.config_models import DatabaseType

logger = get_logger(__name__)


class TemplateGenerator:
    """Generate configuration templates for onboarding."""
    
    def __init__(self, application_id: str, application_name: str, database_type: DatabaseType):
        """
        Initialize the template generator.
        
        Args:
            application_id: Unique identifier for the application
            application_name: Human-readable name for the application
            database_type: Type of database (PostgreSQL, MySQL, etc.)
        """
        self.application_id = application_id
        self.application_name = application_name
        self.database_type = database_type
        
        logger.info(f"Initialized TemplateGenerator for {application_id}")
    
    def generate_app_yaml(
        self,
        table_info_dict: Dict[str, TableInfo],
        relationships: List[Dict[str, Any]],
        business_function: Optional[str] = None
    ) -> str:
        """
        Generate app.yaml template.
        
        Args:
            table_info_dict: Dictionary of table information
            relationships: List of detected relationships
            business_function: Optional business function description
            
        Returns:
            YAML string for app.yaml
        """
        logger.info("Generating app.yaml template")
        
        app_config = {
            'application': {
                'id': self.application_id,
                'name': self.application_name,
                'database_vendor': self.database_type.value,
                'business_function': business_function or 'TODO: Describe business function',
                'description': 'TODO: Add detailed application description'
            },
            'relationships': self._format_relationships(relationships),
            'business_context': self._generate_business_context_template(table_info_dict),
            'metadata': {
                'version': '1.0',
                'last_updated': datetime.now().strftime('%Y-%m-%d'),
                'description': 'Auto-generated configuration from database introspection'
            }
        }
        
        return self._to_yaml(app_config)
    
    def generate_schema_yaml(
        self,
        table_info_dict: Dict[str, TableInfo]
    ) -> str:
        """
        Generate schema.yaml template.
        
        Args:
            table_info_dict: Dictionary of table information
            
        Returns:
            YAML string for schema.yaml
        """
        logger.info("Generating schema.yaml template")
        
        tables_config = {}
        
        for table_name, table_info in table_info_dict.items():
            tables_config[table_name] = self._format_table_definition(table_info)
        
        schema_config = {'tables': tables_config}
        
        return self._to_yaml(schema_config)
    
    def generate_user_input_template(
        self,
        table_info_dict: Dict[str, TableInfo]
    ) -> str:
        """
        Generate a user input template for business context mapping.
        
        Args:
            table_info_dict: Dictionary of table information
            
        Returns:
            YAML string with placeholders for user input
        """
        logger.info("Generating user input template")
        
        user_input = {
            'application_details': {
                'business_function': 'TODO: Describe what this application does (e.g., "Fund Management & Client Portfolio Tracking")',
                'description': 'TODO: Add detailed description of the application purpose and scope',
                'key_business_processes': [
                    'TODO: List main business processes (e.g., "Client Onboarding", "Portfolio Management")'
                ]
            },
            'table_business_context': {},
            'column_aliases': {},
            'business_metrics': {
                'example_metric': {
                    'name': 'TODO: Metric name',
                    'formula': 'TODO: SQL formula',
                    'unit': 'TODO: currency/percentage/count',
                    'description': 'TODO: Business meaning'
                }
            },
            'business_rules': [
                {
                    'name': 'TODO: Rule name',
                    'description': 'TODO: Rule description',
                    'applies_to': ['TODO: table names'],
                    'filter': 'TODO: SQL filter condition (optional)'
                }
            ],
            'common_queries': [
                {
                    'question': 'TODO: Natural language question',
                    'description': 'TODO: What business question does this answer?'
                }
            ]
        }
        
        # Add table-specific context templates
        for table_name, table_info in table_info_dict.items():
            user_input['table_business_context'][table_name] = {
                'business_name': f"TODO: Business name for {table_name}",
                'description': table_info.comment or f"TODO: Describe the business purpose of {table_name}",
                'aliases': [f"TODO: Add natural language aliases (e.g., 'portfolio', 'fund')"],
                'key_columns': self._suggest_key_columns(table_info)
            }
            
            # Add column alias templates
            for column in table_info.columns:
                if column.name not in ['id', 'created_at', 'updated_at']:
                    user_input['column_aliases'][f"{table_name}.{column.name}"] = {
                        'aliases': [f"TODO: Add natural language aliases for {column.name}"],
                        'business_meaning': column.comment or f"TODO: Describe what {column.name} represents"
                    }
        
        return self._to_yaml(user_input)
    
    def _format_relationships(self, relationships: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Format relationships for YAML output."""
        formatted = []
        
        for rel in relationships:
            formatted.append({
                'name': rel['name'],
                'parent': rel['parent'],
                'child': rel['child'],
                'type': rel['type'],
                'description': rel['description']
            })
        
        return formatted
    
    def _format_table_definition(self, table_info: TableInfo) -> Dict[str, Any]:
        """Format table definition for schema.yaml."""
        table_def = {
            'description': table_info.comment or f'TODO: Add description for {table_info.name}',
            'aliases': [f'TODO: Add aliases for {table_info.name}'],
            'primary_key': table_info.primary_keys[0] if len(table_info.primary_keys) == 1 else table_info.primary_keys,
            'estimated_rows': table_info.row_count_estimate or 1000,
            'columns': {}
        }
        
        for column in table_info.columns:
            col_def = self._format_column_definition(column)
            table_def['columns'][column.name] = col_def
        
        return table_def
    
    def _format_column_definition(self, column: ColumnInfo) -> Dict[str, Any]:
        """Format column definition for schema.yaml."""
        col_def = {
            'type': column.data_type,
            'nullable': column.nullable,
            'description': column.comment or f'TODO: Add description for {column.name}'
        }
        
        if column.primary_key:
            col_def['primary_key'] = True
        
        if column.foreign_key:
            col_def['foreign_key'] = column.foreign_key
        
        if column.default is not None:
            col_def['default'] = str(column.default)
        
        # Add alias suggestions for commonly named columns
        aliases = self._suggest_column_aliases(column.name)
        if aliases:
            col_def['aliases'] = aliases
        
        # Suggest if this might be a dimension
        if self._is_potential_dimension(column):
            col_def['is_dimension'] = True
            col_def['dimension_context'] = f'TODO: Describe dimension context for {column.name}'
        
        return col_def
    
    def _suggest_column_aliases(self, column_name: str) -> List[str]:
        """Suggest natural language aliases for common column patterns."""
        column_lower = column_name.lower()
        
        # Common patterns
        alias_patterns = {
            'aum': ['assets under management', 'managed assets', 'total assets'],
            'nav': ['net asset value', 'fund value', 'unit price'],
            'amount': ['value', 'total'],
            'date': ['when', 'time'],
            'name': ['title', 'label'],
            'code': ['identifier', 'id'],
            'type': ['category', 'kind'],
            'status': ['state', 'condition'],
            'description': ['details', 'info']
        }
        
        for pattern, aliases in alias_patterns.items():
            if pattern in column_lower:
                return aliases
        
        return []
    
    def _is_potential_dimension(self, column: ColumnInfo) -> bool:
        """Determine if a column is likely a dimension (categorical data)."""
        column_lower = column.name.lower()
        
        # Common dimension patterns
        dimension_indicators = [
            'type', 'category', 'status', 'classification', 'class',
            'code', 'rating', 'level', 'grade', 'tier'
        ]
        
        return any(indicator in column_lower for indicator in dimension_indicators)
    
    def _suggest_key_columns(self, table_info: TableInfo) -> List[str]:
        """Suggest key columns users should provide business context for."""
        key_columns = []
        
        for column in table_info.columns:
            # Skip technical columns
            if column.name in ['id', 'created_at', 'updated_at', 'deleted_at']:
                continue
            
            # Include primary keys, foreign keys, and likely dimensions
            if column.primary_key or column.foreign_key or self._is_potential_dimension(column):
                key_columns.append(column.name)
            
            # Include numeric columns (likely metrics)
            if column.data_type in ['numeric', 'integer'] and not column.name.endswith('_id'):
                key_columns.append(column.name)
        
        return key_columns[:10]  # Limit to top 10
    
    def _generate_business_context_template(
        self,
        table_info_dict: Dict[str, TableInfo]
    ) -> Dict[str, Any]:
        """Generate business context template with examples."""
        return {
            'metrics': {
                'example_metric': {
                    'name': 'TODO: Metric Name',
                    'formula': 'TODO: SUM(column) FROM table WHERE condition',
                    'unit': 'TODO: currency/percentage/count',
                    'description': 'TODO: Business meaning of this metric'
                }
            },
            'rules': [
                {
                    'name': 'TODO: Rule Name',
                    'description': 'TODO: Describe the business rule',
                    'applies_to': ['TODO: table_names'],
                    'filter': 'TODO: SQL filter condition (optional)'
                }
            ],
            'sample_queries': [
                {
                    'question': 'TODO: Natural language question',
                    'sql': 'TODO: Example SQL query'
                }
            ]
        }
    
    def _to_yaml(self, data: Dict[str, Any]) -> str:
        """Convert dictionary to YAML string with proper formatting."""
        # Custom YAML formatting for better readability
        yaml_str = yaml.dump(
            data,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=100
        )
        
        # Add section separators
        yaml_str = self._add_section_separators(yaml_str)
        
        return yaml_str
    
    def _add_section_separators(self, yaml_str: str) -> str:
        """Add visual separators between major sections."""
        import re
        
        separators = {
            'application:': '# ' + '=' * 78 + '\n# APPLICATION DEFINITION\n# ' + '=' * 78,
            'relationships:': '\n# ' + '=' * 78 + '\n# RELATIONSHIPS\n# ' + '=' * 78,
            'business_context:': '\n# ' + '=' * 78 + '\n# BUSINESS CONTEXT\n# ' + '=' * 78,
            'metadata:': '\n# ' + '=' * 78 + '\n# METADATA\n# ' + '=' * 78,
            'tables:': '# ' + '=' * 78 + '\n# TABLE DEFINITIONS\n# ' + '=' * 78
        }
        
        # Only replace keys at the beginning of lines (top-level keys)
        for key, separator in separators.items():
            pattern = r'^(' + re.escape(key) + r')'
            replacement = f"{separator}\n\n\\1"
            yaml_str = re.sub(pattern, replacement, yaml_str, flags=re.MULTILINE)
        
        # Add document start marker
        yaml_str = '---\n' + yaml_str
        
        return yaml_str
