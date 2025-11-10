"""Unit tests for SchemaIntrospector."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from src.reportsmith.onboarding.schema_introspector import (
    SchemaIntrospector,
    ColumnInfo,
    ForeignKeyInfo,
    TableInfo,
)
from src.reportsmith.config_system.config_models import DatabaseType


@pytest.fixture
def mock_engine():
    """Create a mock SQLAlchemy engine."""
    engine = Mock(spec=Engine)
    engine.connect = MagicMock()
    return engine


@pytest.fixture
def mock_inspector():
    """Create a mock SQLAlchemy inspector."""
    inspector = Mock()
    return inspector


class TestSchemaIntrospector:
    """Test cases for SchemaIntrospector."""
    
    def test_initialization(self, mock_engine):
        """Test SchemaIntrospector initialization."""
        with patch('src.reportsmith.onboarding.schema_introspector.inspect'):
            introspector = SchemaIntrospector(mock_engine, DatabaseType.POSTGRESQL)
            
            assert introspector.engine == mock_engine
            assert introspector.database_type == DatabaseType.POSTGRESQL
    
    def test_normalize_data_type_integer(self, mock_engine):
        """Test data type normalization for integers."""
        with patch('src.reportsmith.onboarding.schema_introspector.inspect'):
            introspector = SchemaIntrospector(mock_engine, DatabaseType.POSTGRESQL)
            
            assert introspector._normalize_data_type('INTEGER') == 'integer'
            assert introspector._normalize_data_type('BIGINT') == 'integer'
            assert introspector._normalize_data_type('SERIAL') == 'integer'
    
    def test_normalize_data_type_numeric(self, mock_engine):
        """Test data type normalization for numeric types."""
        with patch('src.reportsmith.onboarding.schema_introspector.inspect'):
            introspector = SchemaIntrospector(mock_engine, DatabaseType.POSTGRESQL)
            
            assert introspector._normalize_data_type('NUMERIC') == 'numeric'
            assert introspector._normalize_data_type('DECIMAL(10,2)') == 'numeric'
            assert introspector._normalize_data_type('FLOAT') == 'numeric'
    
    def test_normalize_data_type_varchar(self, mock_engine):
        """Test data type normalization for string types."""
        with patch('src.reportsmith.onboarding.schema_introspector.inspect'):
            introspector = SchemaIntrospector(mock_engine, DatabaseType.POSTGRESQL)
            
            assert introspector._normalize_data_type('VARCHAR') == 'varchar'
            assert introspector._normalize_data_type('VARCHAR(255)') == 'varchar'
            assert introspector._normalize_data_type('TEXT') == 'varchar'
            assert introspector._normalize_data_type('CHAR(10)') == 'varchar'
    
    def test_normalize_data_type_boolean(self, mock_engine):
        """Test data type normalization for boolean."""
        with patch('src.reportsmith.onboarding.schema_introspector.inspect'):
            introspector = SchemaIntrospector(mock_engine, DatabaseType.POSTGRESQL)
            
            assert introspector._normalize_data_type('BOOLEAN') == 'boolean'
            assert introspector._normalize_data_type('BOOL') == 'boolean'
    
    def test_normalize_data_type_timestamp(self, mock_engine):
        """Test data type normalization for timestamp."""
        with patch('src.reportsmith.onboarding.schema_introspector.inspect'):
            introspector = SchemaIntrospector(mock_engine, DatabaseType.POSTGRESQL)
            
            assert introspector._normalize_data_type('TIMESTAMP') == 'timestamp'
            assert introspector._normalize_data_type('TIMESTAMP WITH TIME ZONE') == 'timestamp'
    
    def test_normalize_data_type_date(self, mock_engine):
        """Test data type normalization for date."""
        with patch('src.reportsmith.onboarding.schema_introspector.inspect'):
            introspector = SchemaIntrospector(mock_engine, DatabaseType.POSTGRESQL)
            
            assert introspector._normalize_data_type('DATE') == 'date'
    
    def test_get_table_names(self, mock_engine, mock_inspector):
        """Test getting table names from database."""
        with patch('src.reportsmith.onboarding.schema_introspector.inspect', return_value=mock_inspector):
            mock_inspector.get_table_names.return_value = ['table1', 'table2', 'table3']
            
            introspector = SchemaIntrospector(mock_engine, DatabaseType.POSTGRESQL)
            tables = introspector._get_table_names()
            
            assert tables == ['table1', 'table2', 'table3']
            mock_inspector.get_table_names.assert_called_once()
    
    def test_get_primary_keys(self, mock_engine, mock_inspector):
        """Test getting primary keys for a table."""
        with patch('src.reportsmith.onboarding.schema_introspector.inspect', return_value=mock_inspector):
            mock_inspector.get_pk_constraint.return_value = {
                'constrained_columns': ['id', 'version']
            }
            
            introspector = SchemaIntrospector(mock_engine, DatabaseType.POSTGRESQL)
            pk_columns = introspector._get_primary_keys('test_table')
            
            assert pk_columns == ['id', 'version']
    
    def test_get_foreign_keys(self, mock_engine, mock_inspector):
        """Test getting foreign keys for a table."""
        with patch('src.reportsmith.onboarding.schema_introspector.inspect', return_value=mock_inspector):
            mock_inspector.get_foreign_keys.return_value = [
                {
                    'name': 'fk_user_id',
                    'constrained_columns': ['user_id'],
                    'referred_table': 'users',
                    'referred_columns': ['id']
                }
            ]
            
            introspector = SchemaIntrospector(mock_engine, DatabaseType.POSTGRESQL)
            fks = introspector._get_foreign_keys('test_table')
            
            assert len(fks) == 1
            assert fks[0].constraint_name == 'fk_user_id'
            assert fks[0].source_table == 'test_table'
            assert fks[0].source_columns == ['user_id']
            assert fks[0].target_table == 'users'
            assert fks[0].target_columns == ['id']
    
    def test_determine_relationship_type_one_to_many(self, mock_engine):
        """Test determining relationship type: one-to-many."""
        with patch('src.reportsmith.onboarding.schema_introspector.inspect'):
            introspector = SchemaIntrospector(mock_engine, DatabaseType.POSTGRESQL)
            
            fk = ForeignKeyInfo(
                constraint_name='fk_test',
                source_table='orders',
                source_columns=['customer_id'],
                target_table='customers',
                target_columns=['id']
            )
            
            table_info_dict = {
                'orders': TableInfo(
                    name='orders',
                    schema=None,
                    columns=[],
                    primary_keys=['id'],
                    foreign_keys=[fk],
                    indexes=[]
                )
            }
            
            rel_type = introspector._determine_relationship_type(fk, table_info_dict)
            assert rel_type == 'one_to_many'
    
    def test_determine_relationship_type_one_to_one(self, mock_engine):
        """Test determining relationship type: one-to-one."""
        with patch('src.reportsmith.onboarding.schema_introspector.inspect'):
            introspector = SchemaIntrospector(mock_engine, DatabaseType.POSTGRESQL)
            
            fk = ForeignKeyInfo(
                constraint_name='fk_test',
                source_table='user_profiles',
                source_columns=['user_id'],
                target_table='users',
                target_columns=['id']
            )
            
            table_info_dict = {
                'user_profiles': TableInfo(
                    name='user_profiles',
                    schema=None,
                    columns=[],
                    primary_keys=['user_id'],  # FK is also PK
                    foreign_keys=[fk],
                    indexes=[]
                )
            }
            
            rel_type = introspector._determine_relationship_type(fk, table_info_dict)
            assert rel_type == 'one_to_one'
    
    def test_determine_relationship_type_many_to_many(self, mock_engine):
        """Test determining relationship type: many-to-many."""
        with patch('src.reportsmith.onboarding.schema_introspector.inspect'):
            introspector = SchemaIntrospector(mock_engine, DatabaseType.POSTGRESQL)
            
            fk1 = ForeignKeyInfo(
                constraint_name='fk_student',
                source_table='student_courses',
                source_columns=['student_id'],
                target_table='students',
                target_columns=['id']
            )
            
            fk2 = ForeignKeyInfo(
                constraint_name='fk_course',
                source_table='student_courses',
                source_columns=['course_id'],
                target_table='courses',
                target_columns=['id']
            )
            
            table_info_dict = {
                'student_courses': TableInfo(
                    name='student_courses',
                    schema=None,
                    columns=[],
                    primary_keys=['student_id', 'course_id'],  # Composite PK
                    foreign_keys=[fk1, fk2],  # Multiple FKs
                    indexes=[]
                )
            }
            
            rel_type = introspector._determine_relationship_type(fk1, table_info_dict)
            assert rel_type == 'many_to_many'
    
    def test_detect_relationships(self, mock_engine):
        """Test detecting relationships from table information."""
        with patch('src.reportsmith.onboarding.schema_introspector.inspect'):
            introspector = SchemaIntrospector(mock_engine, DatabaseType.POSTGRESQL)
            
            fk = ForeignKeyInfo(
                constraint_name='fk_customer',
                source_table='orders',
                source_columns=['customer_id'],
                target_table='customers',
                target_columns=['id']
            )
            
            table_info_dict = {
                'orders': TableInfo(
                    name='orders',
                    schema=None,
                    columns=[],
                    primary_keys=['id'],
                    foreign_keys=[fk],
                    indexes=[]
                ),
                'customers': TableInfo(
                    name='customers',
                    schema=None,
                    columns=[],
                    primary_keys=['id'],
                    foreign_keys=[],
                    indexes=[]
                )
            }
            
            relationships = introspector.detect_relationships(table_info_dict)
            
            assert len(relationships) == 1
            assert relationships[0]['name'] == 'orders_to_customers'
            assert relationships[0]['parent'] == 'customers.id'
            assert relationships[0]['child'] == 'orders.customer_id'
            assert relationships[0]['type'] == 'one_to_many'
