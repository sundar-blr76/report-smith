# ReportSmith Database Schema

## 🎯 Overview

ReportSmith uses a minimal PostgreSQL database for:
1. **Execution Audit Logs** - Track query executions and performance
2. **Saved Queries** - User-saved queries for reuse
3. **Vector Embeddings** - Semantic search for natural language to SQL

**Note:** Application and template configurations are stored in YAML files under `config/applications/`, not in the database.

---

## 📊 Database Tables (5 Total)

### 1. Execution Tracking (3 tables)

#### 1.1. `execution_sessions`
Track each query execution from start to finish

```sql
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
```

**Purpose:** Overall execution tracking - what ran, when, status, results

#### 1.2. `execution_steps`
Break down multi-step execution into individual steps

```sql
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
```

**Purpose:** Multi-step query execution tracking (e.g., Step 1: APAC data, Step 2: EMEA data, Step 3: Merge)

#### 1.3. `query_executions`
Detailed metrics for each SQL query executed

```sql
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
```

**Purpose:** Detailed SQL query metrics for performance analysis and debugging

---

### 2. Saved Queries (1 table)

#### 2.1. `saved_queries`
User-saved queries for reuse

```sql
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
```

**Purpose:** Let users save frequently used queries (e.g., "Monthly TruePotential Report")

---

### 3. Vector Store (1 table)

#### 3.1. `schema_embeddings`
Vector embeddings for semantic search

```sql
CREATE TABLE schema_embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type VARCHAR(50),
    source_id VARCHAR(100) NOT NULL,
    application_id VARCHAR(50),
    content_text TEXT NOT NULL,
    content_metadata JSONB,
    embedding_model VARCHAR(100),
    -- embedding_vector vector(384),  -- Uncomment if using pgvector extension
    embedding_dimensions INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Purpose:** Store vector embeddings for semantic search to match natural language queries to database tables

**Example:** "funds table contains TruePotential fund data" → vector embedding → when user asks "show TruePotential performance", find relevant tables

---

## 📈 Table Relationships

```
execution_sessions (1) ──< (N) execution_steps
execution_steps (1) ─────< (N) query_executions
```

**Cascade Delete:** When an execution session is deleted, all related steps and queries are also deleted.

---

## 🚀 Setup

### Create Database & Schema

```bash
# Recommended: Use Python script
cd scripts
python3 setup_database.py

# Or manually with psql
psql -U postgres -h localhost -c "CREATE DATABASE reportsmith;"
psql -U postgres -h localhost -d reportsmith -f scripts/create_reportsmith_schema.sql
```

### Verify Installation

```sql
-- Check table count (should be 5)
SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';

-- List all tables
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- Check extensions
SELECT extname FROM pg_extension;
```

---

## 📝 Example Usage

### Log a Query Execution

```sql
-- 1. Create execution session
INSERT INTO execution_sessions (
    session_id, user_id, query_type, original_query,
    execution_start, status
) VALUES (
    'exec_20241201_103000',
    'user@example.com',
    'natural_language',
    'Show TruePotential fund performance for last month',
    NOW(),
    'running'
);

-- 2. Add execution step
INSERT INTO execution_steps (
    session_id, step_number, step_name, 
    database_name, application_name,
    start_time, status, query_executed
) VALUES (
    'exec_20241201_103000',
    1,
    'Query APAC fund accounting',
    'fund_accounting_apac',
    'fund_accounting',
    NOW(),
    'completed',
    'SELECT * FROM funds WHERE fund_family = ''TruePotential'''
);

-- 3. Log SQL query execution
INSERT INTO query_executions (
    step_id, sql_query, query_hash,
    start_time, end_time, rows_returned, status
) VALUES (
    'step_uuid_here',
    'SELECT * FROM funds WHERE fund_family = ''TruePotential''',
    md5('SELECT * FROM funds WHERE fund_family = ''TruePotential'''),
    NOW(),
    NOW() + INTERVAL '2 seconds',
    12,
    'success'
);

-- 4. Mark session complete
UPDATE execution_sessions
SET status = 'completed',
    execution_end = NOW(),
    total_duration = execution_end - execution_start,
    total_queries_executed = 1,
    total_rows_returned = 12
WHERE session_id = 'exec_20241201_103000';
```

### Save a Query

```sql
INSERT INTO saved_queries (
    user_id, query_name, query_description, 
    query_type, query_content
) VALUES (
    'user@example.com',
    'Monthly TruePotential Fees',
    'Generate monthly fee report for all TruePotential funds',
    'natural_language',
    'Show monthly management fees for all TruePotential equity funds'
);
```

### View Execution History

```sql
SELECT 
    s.session_id,
    s.original_query,
    s.execution_start,
    s.total_duration,
    s.status,
    s.total_rows_returned,
    COUNT(st.step_id) as step_count
FROM execution_sessions s
LEFT JOIN execution_steps st ON s.session_id = st.session_id
WHERE s.user_id = 'user@example.com'
  AND s.execution_start >= NOW() - INTERVAL '7 days'
GROUP BY s.session_id, s.original_query, s.execution_start, 
         s.total_duration, s.status, s.total_rows_returned
ORDER BY s.execution_start DESC;
```

---

## 📊 Monitoring & Maintenance

### Table Sizes

```sql
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size('public.'||tablename)) AS size,
    pg_size_pretty(pg_relation_size('public.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size('public.'||tablename) - 
                   pg_relation_size('public.'||tablename)) AS index_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size('public.'||tablename) DESC;
```

### Cleanup Old Logs

```sql
-- Delete execution logs older than 90 days
DELETE FROM execution_sessions
WHERE execution_start < NOW() - INTERVAL '90 days'
  AND status IN ('completed', 'failed');

-- Verify cleanup
SELECT 
    status,
    COUNT(*) as count,
    MIN(execution_start) as oldest,
    MAX(execution_start) as newest
FROM execution_sessions
GROUP BY status;
```

### Performance Statistics

```sql
-- Query execution performance over last 7 days
SELECT 
    DATE(s.execution_start) as date,
    COUNT(*) as total_executions,
    AVG(EXTRACT(EPOCH FROM s.total_duration)) as avg_duration_seconds,
    MAX(EXTRACT(EPOCH FROM s.total_duration)) as max_duration_seconds,
    SUM(s.total_rows_returned) as total_rows_returned
FROM execution_sessions s
WHERE s.execution_start >= NOW() - INTERVAL '7 days'
  AND s.status = 'completed'
GROUP BY DATE(s.execution_start)
ORDER BY date DESC;
```

---

## 🔐 Security Considerations

### Credentials
- Database passwords stored in environment variables (never in YAML or database)
- Use connection pooling to minimize connection overhead
- Encrypt sensitive data at rest if required

### Access Control
- Grant minimal permissions to application database user
- Use read-only connections where possible
- Implement row-level security if needed

### Audit Trail
- All executions are logged with user_id
- Query content is stored for transparency
- Failed queries are logged with error messages

---

## 🔄 Backup & Recovery

### Backup

```bash
# Full backup
pg_dump -U postgres -d reportsmith -F c -f reportsmith_backup_$(date +%Y%m%d).dump

# Schema only (for version control)
pg_dump -U postgres -d reportsmith -s -f reportsmith_schema.sql
```

### Restore

```bash
# From custom format
pg_restore -U postgres -d reportsmith -c reportsmith_backup_20241201.dump

# From SQL
psql -U postgres -d reportsmith -f reportsmith_backup.sql
```

---

## 📚 Additional Information

### Extensions Used
- **uuid-ossp** - Generate UUIDs for primary keys
- **pgcrypto** - Cryptographic functions (if needed)
- **vector** (optional) - pgvector extension for semantic search

### Indexes Created
All critical indexes are automatically created by the schema script:
- Foreign key indexes for joins
- Status indexes for filtering
- User ID indexes for user queries
- Query hash indexes for deduplication

### Triggers
- `update_updated_at_column()` - Automatically update `updated_at` on saved_queries

---

## 🎯 Summary

**5 tables for:**
- ✅ Complete execution tracking and audit trail
- ✅ User query management
- ✅ Semantic search capabilities

**Configuration stored in:**
- 📁 YAML files (`config/applications/`) - Application schemas
- 📁 YAML files (`config/templates/`) - Report templates
- 🔐 Environment variables - Database credentials

**Design principles:**
- Minimal database footprint
- Complete audit transparency
- Performance optimized with proper indexes
- Easy to maintain and extend

---

**Last Updated:** 2024-12-01  
**Database Version:** 1.0  
**PostgreSQL:** 12+
