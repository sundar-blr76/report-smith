-- ============================================================================
-- ReportSmith Database Schema
-- PostgreSQL 12+
-- Total Tables: 6
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- EXECUTION TRACKING
-- ============================================================================

CREATE TABLE execution_sessions (
    session_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    query_type VARCHAR(50),
    original_query TEXT,
    template_id VARCHAR(50),
    execution_start TIMESTAMP WITH TIME ZONE NOT NULL,
    execution_end TIMESTAMP WITH TIME ZONE,
    total_duration INTERVAL,
    status VARCHAR(20),
    total_databases_accessed INTEGER,
    total_queries_executed INTEGER,
    total_rows_examined BIGINT,
    total_rows_returned BIGINT,
    output_file_path TEXT,
    output_format VARCHAR(50),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled'))
);

CREATE INDEX idx_sessions_user ON execution_sessions(user_id);
CREATE INDEX idx_sessions_status ON execution_sessions(status);

CREATE TABLE execution_steps (
    step_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(50) NOT NULL REFERENCES execution_sessions(session_id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    step_name VARCHAR(100) NOT NULL,
    step_type VARCHAR(50),
    database_name VARCHAR(100),
    application_name VARCHAR(100),
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    duration INTERVAL,
    query_executed TEXT,
    query_parameters JSONB,
    rows_examined BIGINT,
    rows_returned BIGINT,
    status VARCHAR(20),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(session_id, step_number),
    CHECK (status IN ('completed', 'completed_with_warnings', 'failed'))
);

CREATE INDEX idx_steps_session ON execution_steps(session_id);

CREATE TABLE query_executions (
    query_execution_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    step_id UUID NOT NULL REFERENCES execution_steps(step_id) ON DELETE CASCADE,
    sql_query TEXT NOT NULL,
    query_hash VARCHAR(64) NOT NULL,
    query_parameters JSONB,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    duration INTERVAL,
    rows_examined BIGINT,
    rows_returned BIGINT,
    status VARCHAR(20),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CHECK (status IN ('success', 'failed', 'cancelled', 'timeout'))
);

CREATE INDEX idx_query_exec_step ON query_executions(step_id);
CREATE INDEX idx_query_exec_hash ON query_executions(query_hash);

-- ============================================================================
-- SAVED QUERIES
-- ============================================================================

CREATE TABLE saved_queries (
    saved_query_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100) NOT NULL,
    query_name VARCHAR(200) NOT NULL,
    query_description TEXT,
    query_type VARCHAR(50),
    query_content TEXT NOT NULL,
    query_parameters JSONB,
    execution_count INTEGER DEFAULT 0,
    last_executed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_saved_queries_user ON saved_queries(user_id);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_saved_queries_updated_at
    BEFORE UPDATE ON saved_queries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VECTOR STORE
-- ============================================================================

CREATE TABLE schema_embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type VARCHAR(50),
    source_id VARCHAR(100) NOT NULL,
    application_id VARCHAR(50),
    content_text TEXT NOT NULL,
    content_metadata JSONB,
    embedding_model VARCHAR(100),
    embedding_dimensions INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_embeddings_source ON schema_embeddings(source_type, source_id);
CREATE INDEX idx_embeddings_application ON schema_embeddings(application_id);
