"""Configuration management for ReportSmith."""

from typing import Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_name: str = "ReportSmith"
    debug: bool = False
    
    # Configuration Management
    config_directory: str = Field(default="./config", env="CONFIG_DIRECTORY")
    master_config_file: str = Field(default="master_config.json", env="MASTER_CONFIG_FILE")
    
    # API Keys
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    alpha_vantage_key: Optional[str] = Field(default=None, env="ALPHA_VANTAGE_API_KEY")
    
    # Database
    database_url: str = Field(default="sqlite:///reportsmith.db", env="DATABASE_URL")
    
    # Audit Database (for logging and monitoring)
    audit_database_url: str = Field(default="sqlite:///reportsmith_audit.db", env="AUDIT_DATABASE_URL")
    
    # Vector Store
    vector_store_path: str = "./data/vector_store"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # RAG Configuration
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_retrieval_results: int = 5
    
    # LLM Configuration
    llm_model: str = "gpt-3.5-turbo"
    max_tokens: int = 2048
    temperature: float = 0.7
    
    # Data Sources
    data_directory: str = "./data"
    reports_directory: str = "./data/reports"
    
    # Enterprise Configuration
    enable_audit_logging: bool = True
    enable_cost_assessment: bool = True
    enable_schema_intelligence: bool = True
    
    # Query Execution
    default_query_timeout: int = 300  # seconds
    max_temp_table_size_mb: int = 1000
    max_concurrent_queries: int = 10
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()