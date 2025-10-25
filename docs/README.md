# Documentation

## 📚 Core Documentation

- **[DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)** - Database schema (5 tables)
- **[../SETUP.md](../SETUP.md)** - Setup guide

## Database

ReportSmith uses PostgreSQL with 5 tables:

1. **Execution Tracking (3 tables)**
   - `execution_sessions` - Overall query execution
   - `execution_steps` - Multi-step breakdown
   - `query_executions` - SQL query metrics

2. **Saved Queries (1 table)**
   - `saved_queries` - User-saved queries

3. **Vector Store (1 table)**
   - `schema_embeddings` - Semantic search embeddings

## Application Configurations

Application schemas stored in YAML files:

```
config/applications/
├── fund_accounting.yaml    # Example
├── your_app.yaml          # Your configs
```

Each YAML contains:
- Database connections
- Table schemas
- Business context
- Relationships

**See:** [config/applications/README.md](../config/applications/README.md)
