"""Unit tests for TemplateGenerator."""

import pytest
import yaml

from src.reportsmith.onboarding.template_generator import TemplateGenerator
from src.reportsmith.onboarding.schema_introspector import (
    TableInfo,
    ColumnInfo,
    ForeignKeyInfo,
)
from src.reportsmith.config_system.config_models import DatabaseType


@pytest.fixture
def template_generator():
    """Create a TemplateGenerator instance."""
    return TemplateGenerator(
        application_id='test_app',
        application_name='Test Application',
        database_type=DatabaseType.POSTGRESQL
    )


@pytest.fixture
def sample_table_info():
    """Create sample table information."""
    columns = [
        ColumnInfo(
            name='id',
            data_type='integer',
            nullable=False,
            primary_key=True
        ),
        ColumnInfo(
            name='name',
            data_type='varchar',
            nullable=False,
            comment='User name'
        ),
        ColumnInfo(
            name='email',
            data_type='varchar',
            nullable=False
        ),
        ColumnInfo(
            name='status',
            data_type='varchar',
            nullable=True
        ),
        ColumnInfo(
            name='total_amount',
            data_type='numeric',
            nullable=True
        ),
        ColumnInfo(
            name='created_at',
            data_type='timestamp',
            nullable=False
        )
    ]
    
    return TableInfo(
        name='users',
        schema='public',
        columns=columns,
        primary_keys=['id'],
        foreign_keys=[],
        indexes=[],
        comment='User accounts table',
        row_count_estimate=1000
    )


@pytest.fixture
def sample_relationships():
    """Create sample relationships."""
    return [
        {
            'name': 'orders_to_customers',
            'parent': 'customers.id',
            'child': 'orders.customer_id',
            'type': 'one_to_many',
            'description': 'Foreign key from orders to customers'
        }
    ]


class TestTemplateGenerator:
    """Test cases for TemplateGenerator."""
    
    def test_initialization(self):
        """Test TemplateGenerator initialization."""
        generator = TemplateGenerator(
            application_id='my_app',
            application_name='My Application',
            database_type=DatabaseType.MYSQL
        )
        
        assert generator.application_id == 'my_app'
        assert generator.application_name == 'My Application'
        assert generator.database_type == DatabaseType.MYSQL
    
    def test_generate_app_yaml(self, template_generator, sample_table_info, sample_relationships):
        """Test app.yaml generation."""
        table_info_dict = {'users': sample_table_info}
        
        app_yaml = template_generator.generate_app_yaml(
            table_info_dict,
            sample_relationships,
            business_function='User Management'
        )
        
        # Verify it's valid YAML
        app_config = yaml.safe_load(app_yaml)
        
        assert app_config['application']['id'] == 'test_app'
        assert app_config['application']['name'] == 'Test Application'
        assert app_config['application']['database_vendor'] == 'postgresql'
        assert app_config['application']['business_function'] == 'User Management'
        assert 'relationships' in app_config
        assert 'business_context' in app_config
        assert 'metadata' in app_config
    
    def test_generate_schema_yaml(self, template_generator, sample_table_info):
        """Test schema.yaml generation."""
        table_info_dict = {'users': sample_table_info}
        
        schema_yaml = template_generator.generate_schema_yaml(table_info_dict)
        
        # Verify it's valid YAML
        schema_config = yaml.safe_load(schema_yaml)
        
        assert 'tables' in schema_config
        assert 'users' in schema_config['tables']
        
        users_table = schema_config['tables']['users']
        assert users_table['primary_key'] == 'id'
        assert users_table['estimated_rows'] == 1000
        assert 'columns' in users_table
        assert 'id' in users_table['columns']
        assert 'name' in users_table['columns']
    
    def test_generate_user_input_template(self, template_generator, sample_table_info):
        """Test user input template generation."""
        table_info_dict = {'users': sample_table_info}
        
        user_input_yaml = template_generator.generate_user_input_template(table_info_dict)
        
        # Verify it's valid YAML
        user_input = yaml.safe_load(user_input_yaml)
        
        assert 'application_details' in user_input
        assert 'table_business_context' in user_input
        assert 'column_aliases' in user_input
        assert 'business_metrics' in user_input
        assert 'business_rules' in user_input
        assert 'common_queries' in user_input
        
        # Check table context
        assert 'users' in user_input['table_business_context']
        assert 'key_columns' in user_input['table_business_context']['users']
    
    def test_format_column_definition_primary_key(self, template_generator):
        """Test column definition formatting for primary key."""
        column = ColumnInfo(
            name='id',
            data_type='integer',
            nullable=False,
            primary_key=True
        )
        
        col_def = template_generator._format_column_definition(column)
        
        assert col_def['type'] == 'integer'
        assert col_def['nullable'] is False
        assert col_def['primary_key'] is True
    
    def test_format_column_definition_foreign_key(self, template_generator):
        """Test column definition formatting for foreign key."""
        column = ColumnInfo(
            name='customer_id',
            data_type='integer',
            nullable=False,
            foreign_key='customers.id'
        )
        
        col_def = template_generator._format_column_definition(column)
        
        assert col_def['type'] == 'integer'
        assert col_def['foreign_key'] == 'customers.id'
    
    def test_format_column_definition_with_default(self, template_generator):
        """Test column definition formatting with default value."""
        column = ColumnInfo(
            name='status',
            data_type='varchar',
            nullable=True,
            default='active'
        )
        
        col_def = template_generator._format_column_definition(column)
        
        assert col_def['default'] == 'active'
    
    def test_suggest_column_aliases_aum(self, template_generator):
        """Test alias suggestions for AUM column."""
        aliases = template_generator._suggest_column_aliases('total_aum')
        
        assert 'assets under management' in aliases
        assert 'managed assets' in aliases
    
    def test_suggest_column_aliases_nav(self, template_generator):
        """Test alias suggestions for NAV column."""
        aliases = template_generator._suggest_column_aliases('nav_per_share')
        
        assert 'net asset value' in aliases
        assert 'fund value' in aliases
    
    def test_suggest_column_aliases_no_match(self, template_generator):
        """Test alias suggestions for column with no matches."""
        aliases = template_generator._suggest_column_aliases('unknown_column')
        
        assert aliases == []
    
    def test_is_potential_dimension_type(self, template_generator):
        """Test dimension detection for type columns."""
        column = ColumnInfo(
            name='user_type',
            data_type='varchar',
            nullable=False
        )
        
        assert template_generator._is_potential_dimension(column) is True
    
    def test_is_potential_dimension_status(self, template_generator):
        """Test dimension detection for status columns."""
        column = ColumnInfo(
            name='order_status',
            data_type='varchar',
            nullable=False
        )
        
        assert template_generator._is_potential_dimension(column) is True
    
    def test_is_potential_dimension_category(self, template_generator):
        """Test dimension detection for category columns."""
        column = ColumnInfo(
            name='product_category',
            data_type='varchar',
            nullable=False
        )
        
        assert template_generator._is_potential_dimension(column) is True
    
    def test_is_potential_dimension_non_dimension(self, template_generator):
        """Test dimension detection for non-dimension columns."""
        column = ColumnInfo(
            name='description',
            data_type='varchar',
            nullable=True
        )
        
        assert template_generator._is_potential_dimension(column) is False
    
    def test_suggest_key_columns(self, template_generator, sample_table_info):
        """Test key column suggestions."""
        key_columns = template_generator._suggest_key_columns(sample_table_info)
        
        # Should include status (dimension) and total_amount (numeric metric)
        assert 'status' in key_columns
        assert 'total_amount' in key_columns
        
        # Should exclude technical columns
        assert 'id' not in key_columns
        assert 'created_at' not in key_columns
    
    def test_format_relationships(self, template_generator, sample_relationships):
        """Test relationship formatting."""
        formatted = template_generator._format_relationships(sample_relationships)
        
        assert len(formatted) == 1
        assert formatted[0]['name'] == 'orders_to_customers'
        assert formatted[0]['parent'] == 'customers.id'
        assert formatted[0]['child'] == 'orders.customer_id'
        assert formatted[0]['type'] == 'one_to_many'
    
    def test_to_yaml_valid_format(self, template_generator):
        """Test YAML output is valid."""
        data = {
            'key1': 'value1',
            'key2': {'nested': 'value2'},
            'key3': ['item1', 'item2']
        }
        
        yaml_str = template_generator._to_yaml(data)
        
        # Should be valid YAML
        parsed = yaml.safe_load(yaml_str)
        assert parsed['key1'] == 'value1'
        assert parsed['key2']['nested'] == 'value2'
        assert parsed['key3'] == ['item1', 'item2']
        
        # Should have document start marker
        assert yaml_str.startswith('---\n')
