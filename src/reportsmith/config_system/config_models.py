"""Pydantic models for application configuration."""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


class DatabaseType(str, Enum):
    """Supported database types."""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    ORACLE = "oracle"
    SQLSERVER = "sqlserver"
    SQLITE = "sqlite"


class Environment(str, Enum):
    """Deployment environments."""
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"
    TEST = "test"


class ConnectionPoolConfig(BaseModel):
    """Database connection pool configuration."""
    min_connections: int = Field(default=5, ge=1, le=100)
    max_connections: int = Field(default=25, ge=5, le=500)
    connection_timeout: int = Field(default=30, ge=5, le=300)
    idle_timeout: int = Field(default=600, ge=60, le=3600)
    max_lifetime: int = Field(default=3600, ge=300, le=86400)


class DatabaseConfig(BaseModel):
    """Database connection configuration."""
    database_type: DatabaseType
    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    database_name: str = Field(min_length=1)
    schema: Optional[str] = "public"
    username: Optional[str] = None
    password: Optional[str] = None
    connection_pool_config: Optional[ConnectionPoolConfig] = None
    
    # Oracle specific
    service_name: Optional[str] = None
    
    # Additional connection parameters
    connection_params: Dict[str, Any] = Field(default_factory=dict)


class DataCharacteristics(BaseModel):
    """Characteristics of data in the instance."""
    record_count_estimate: Optional[int] = None
    data_freshness: Optional[str] = None  # e.g., "T-1_business_day"
    update_frequency: Optional[str] = None  # e.g., "daily_23:00_local"
    business_hours: Optional[str] = None
    maintenance_window: Optional[str] = None


class ColumnDefinition(BaseModel):
    """Database column definition with business context."""
    column_name: Optional[str] = None
    data_type: str
    nullable: bool = True
    primary_key: bool = False
    foreign_key: Optional[str] = None
    business_meaning: Optional[str] = None
    sample_values: List[str] = Field(default_factory=list)
    valid_values: List[str] = Field(default_factory=list)


class IndexDefinition(BaseModel):
    """Database index definition."""
    index_name: str
    columns: List[str]
    index_type: str = "btree"
    unique: bool = False


class TableDefinition(BaseModel):
    """Database table definition with business context."""
    table_name: str
    primary_key: Union[str, List[str]]
    business_description: Optional[str] = None
    columns: Dict[str, ColumnDefinition] = Field(default_factory=dict)
    indexes: List[IndexDefinition] = Field(default_factory=list)
    estimated_rows: Optional[int] = None


class RelationshipDefinition(BaseModel):
    """Table relationship definition."""
    relationship_name: str
    parent_table: str
    parent_column: str
    child_table: str
    child_column: str
    relationship_type: str  # one_to_many, many_to_one, many_to_many
    business_meaning: Optional[str] = None


class SchemaDefinition(BaseModel):
    """Complete schema definition for an application."""
    tables: Dict[str, TableDefinition] = Field(default_factory=dict)
    relationships: List[RelationshipDefinition] = Field(default_factory=list)
    views: Dict[str, Any] = Field(default_factory=dict)  # Future enhancement


class BusinessRule(BaseModel):
    """Business rule definition."""
    rule_name: str
    rule_description: str
    rule_type: Optional[str] = None
    applies_to: List[str] = Field(default_factory=list)
    condition: Optional[str] = None
    severity: str = "info"


class MetricDefinition(BaseModel):
    """Business metric calculation definition."""
    metric_name: str
    calculation: str
    unit: str
    business_meaning: str
    dependencies: List[str] = Field(default_factory=list)


class BusinessContext(BaseModel):
    """Business context and rules for an application."""
    key_metrics: Dict[str, MetricDefinition] = Field(default_factory=dict)
    business_rules: List[BusinessRule] = Field(default_factory=list)
    data_quality_rules: List[BusinessRule] = Field(default_factory=list)
    calculation_methods: Dict[str, str] = Field(default_factory=dict)


class DatabaseInstanceConfig(BaseModel):
    """Configuration for a single database instance."""
    instance_id: str = Field(min_length=1)
    instance_name: str = Field(min_length=1)
    region: Optional[str] = None
    environment: Environment = Environment.PRODUCTION
    database_config: DatabaseConfig
    data_characteristics: Optional[DataCharacteristics] = None
    
    class Config:
        use_enum_values = True


class ApplicationConfig(BaseModel):
    """Complete configuration for a business application."""
    application_id: str = Field(min_length=1)
    application_name: str = Field(min_length=1)
    vendor: Optional[str] = None
    version: Optional[str] = None
    business_function: Optional[str] = None
    
    database_instances: Dict[str, DatabaseInstanceConfig] = Field(default_factory=dict)
    schema_definition: SchemaDefinition = Field(default_factory=SchemaDefinition)
    business_context: BusinessContext = Field(default_factory=BusinessContext)


class VectorSearchConfig(BaseModel):
    """Vector search configuration for schema intelligence."""
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    vector_store_type: str = "chromadb"
    vector_store_path: str = "./data/vector_store"
    
    schema_embeddings: Dict[str, bool] = Field(default_factory=lambda: {
        "table_descriptions": True,
        "column_descriptions": True,
        "business_context": True,
        "sample_queries": True
    })
    
    search_thresholds: Dict[str, float] = Field(default_factory=lambda: {
        "table_match_threshold": 0.75,
        "column_match_threshold": 0.70,
        "business_context_threshold": 0.65
    })


class OperationalConstraints(BaseModel):
    """Operational constraints and limitations."""
    no_rag_for_data_values: Dict[str, Any] = Field(default_factory=lambda: {
        "description": "Legacy applications don't have embeddings for operational data",
        "affected_data_types": ["account_ids", "customer_names", "transaction_ids"],
        "alternative_approach": "direct_sql_lookup_only"
    })
    
    data_access_patterns: Dict[str, str] = Field(default_factory=lambda: {
        "schema_discovery": "vector_search_enabled",
        "business_context": "vector_search_enabled",
        "operational_data": "sql_direct_access_only"
    })


class MasterConfig(BaseModel):
    """Master configuration containing all applications."""
    config_version: str = "2.1"
    config_id: str = "reportsmith_enterprise_config"
    last_updated: datetime = Field(default_factory=datetime.now)
    updated_by: str = "system"
    
    applications: Dict[str, ApplicationConfig] = Field(default_factory=dict)
    vector_search_config: VectorSearchConfig = Field(default_factory=VectorSearchConfig)
    operational_constraints: OperationalConstraints = Field(default_factory=OperationalConstraints)
    
    # Global settings
    audit_enabled: bool = True
    audit_database_config: Optional[DatabaseConfig] = None
    default_query_timeout: int = Field(default=300, ge=30, le=3600)
    max_temp_table_size_mb: int = Field(default=1000, ge=100, le=10000)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }