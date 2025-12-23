# Onboarding Module - Technical Flow

This document explains how the onboarding scripts connect to database system catalogs to extract schema information.

## Flow Diagram

```
scripts/onboard_database.py
    │
    ├─> reportsmith.onboarding.cli.main()
    │
    ├─> OnboardingManager.__init__()
    │   └─> Creates SQLAlchemy engine with database credentials
    │
    ├─> OnboardingManager.run_onboarding()
    │   │
    │   ├─> SchemaIntrospector.introspect_schema()
    │   │   │
    │   │   ├─> _get_table_names()
    │   │   │   └─> inspector.get_table_names()
    │   │   │       └─> Queries system catalogs:
    │   │   │           • PostgreSQL: SELECT * FROM pg_catalog.pg_tables
    │   │   │           • MySQL: SELECT * FROM information_schema.tables
    │   │   │           • Oracle: SELECT * FROM all_tables
    │   │   │           • SQL Server: SELECT * FROM sys.tables
    │   │   │
    │   │   ├─> _get_columns()
    │   │   │   └─> inspector.get_columns()
    │   │   │       └─> Queries system catalogs:
    │   │   │           • PostgreSQL: SELECT * FROM pg_catalog.pg_attribute
    │   │   │           • MySQL: SELECT * FROM information_schema.columns
    │   │   │           • Oracle: SELECT * FROM all_tab_columns
    │   │   │           • SQL Server: SELECT * FROM sys.columns
    │   │   │
    │   │   ├─> _get_primary_keys()
    │   │   │   └─> inspector.get_pk_constraint()
    │   │   │       └─> Queries system catalogs:
    │   │   │           • PostgreSQL: SELECT * FROM pg_catalog.pg_constraint
    │   │   │           • MySQL: SELECT * FROM information_schema.key_column_usage
    │   │   │           • Oracle: SELECT * FROM all_constraints
    │   │   │           • SQL Server: SELECT * FROM sys.key_constraints
    │   │   │
    │   │   ├─> _get_foreign_keys()
    │   │   │   └─> inspector.get_foreign_keys()
    │   │   │       └─> Queries system catalogs:
    │   │   │           • PostgreSQL: SELECT * FROM pg_catalog.pg_constraint
    │   │   │           • MySQL: SELECT * FROM information_schema.referential_constraints
    │   │   │           • Oracle: SELECT * FROM all_constraints
    │   │   │           • SQL Server: SELECT * FROM sys.foreign_keys
    │   │   │
    │   │   ├─> _get_indexes()
    │   │   │   └─> inspector.get_indexes()
    │   │   │       └─> Queries system catalogs:
    │   │   │           • PostgreSQL: SELECT * FROM pg_catalog.pg_indexes
    │   │   │           • MySQL: SELECT * FROM information_schema.statistics
    │   │   │           • Oracle: SELECT * FROM all_indexes
    │   │   │           • SQL Server: SELECT * FROM sys.indexes
    │   │   │
    │   │   └─> _estimate_row_count()
    │   │       └─> Direct SQL queries to system catalogs:
    │   │           • PostgreSQL: SELECT reltuples FROM pg_class WHERE relname = :table
    │   │           • MySQL: SELECT table_rows FROM information_schema.tables WHERE table_name = :table
    │   │           • Oracle: SELECT num_rows FROM all_tables WHERE table_name = :table
    │   │           • SQL Server: SELECT SUM(row_count) FROM sys.dm_db_partition_stats WHERE object_id = OBJECT_ID(:table)
    │   │
    │   ├─> SchemaIntrospector.detect_relationships()
    │   │   └─> Analyzes foreign keys to determine relationship types
    │   │       (one-to-many, one-to-one, many-to-many)
    │   │
    │   ├─> TemplateGenerator.generate_app_yaml()
    │   │   └─> Creates app.yaml with detected relationships
    │   │
    │   ├─> TemplateGenerator.generate_schema_yaml()
    │   │   └─> Creates schema.yaml with normalized data types
    │   │
    │   └─> TemplateGenerator.generate_user_input_template()
    │       └─> Creates user_input_template.yaml for business context
    │
    └─> Writes files to config/applications/<app_id>/
```

## System Catalog Queries

### PostgreSQL System Catalogs

The script queries the following PostgreSQL system catalogs:

1. **pg_catalog.pg_tables** - List of tables
2. **pg_catalog.pg_attribute** - Column definitions
3. **pg_catalog.pg_constraint** - Primary keys and foreign keys
4. **pg_catalog.pg_indexes** - Index definitions
5. **pg_catalog.pg_class** - Row count estimates

### MySQL Information Schema

The script queries the following MySQL information schema views:

1. **information_schema.tables** - List of tables and row counts
2. **information_schema.columns** - Column definitions
3. **information_schema.key_column_usage** - Primary key definitions
4. **information_schema.referential_constraints** - Foreign key relationships
5. **information_schema.statistics** - Index definitions

### Oracle System Catalogs

The script queries the following Oracle system catalogs:

1. **all_tables** - List of tables and row counts
2. **all_tab_columns** - Column definitions
3. **all_constraints** - Primary keys and foreign keys
4. **all_indexes** - Index definitions

### SQL Server System Catalogs

The script queries the following SQL Server system catalogs:

1. **sys.tables** - List of tables
2. **sys.columns** - Column definitions
3. **sys.key_constraints** - Primary key definitions
4. **sys.foreign_keys** - Foreign key relationships
5. **sys.indexes** - Index definitions
6. **sys.dm_db_partition_stats** - Row count estimates

## Example Output

When you run:

```bash
python scripts/onboard_database.py \
  --app-id my_app \
  --db-type postgresql \
  --host localhost \
  --port 5432 \
  --database mydb \
  --username user \
  --password pass
```

The script will:

1. **Connect** to PostgreSQL at localhost:5432
2. **Query pg_catalog** to discover tables, columns, constraints
3. **Extract schema** including:
   - 3 tables discovered
   - 12 columns with data types
   - 2 foreign key relationships detected
4. **Generate configs** in `config/applications/my_app/`:
   - `app.yaml` with relationship definitions
   - `schema.yaml` with complete table/column details
   - `user_input_template.yaml` for business context
   - `README.md` with next steps

## Code References

### Schema Introspector

File: `src/reportsmith/onboarding/schema_introspector.py`

Key methods that query system catalogs:
- `_get_table_names()` - Discovers all tables in the schema
- `_get_columns()` - Extracts column definitions, types, and nullability
- `_get_primary_keys()` - Identifies primary key columns
- `_get_foreign_keys()` - Detects foreign key relationships
- `_get_indexes()` - Retrieves index definitions
- `_estimate_row_count()` - Queries system catalogs for row count estimates (direct SQL)

### SQLAlchemy Inspector

The script uses SQLAlchemy's `Inspector` class which abstracts system catalog access:

```python
from sqlalchemy import inspect

inspector = inspect(engine)
# These methods query system catalogs internally:
inspector.get_table_names()    # -> pg_tables, information_schema.tables, etc.
inspector.get_columns()        # -> pg_attribute, information_schema.columns, etc.
inspector.get_pk_constraint()  # -> pg_constraint, information_schema.key_column_usage, etc.
inspector.get_foreign_keys()   # -> pg_constraint, information_schema.referential_constraints, etc.
```

## Verification

To verify the script connects to system catalogs, run with debug logging:

```bash
# Enable debug logging to see system catalog queries
python scripts/onboard_database.py --app-id test --db-type sqlite --database test.db
```

You'll see log output showing:
- Database connection established
- Tables discovered from system catalog
- Columns extracted with data types
- Foreign keys detected
- Configuration files generated
