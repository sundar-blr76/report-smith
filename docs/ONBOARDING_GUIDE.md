# Database Onboarding Guide

## Overview

The ReportSmith onboarding module provides automated database schema introspection and configuration generation to streamline the setup of new applications. It supports multiple database vendors and generates ready-to-use configuration templates.

## Features

- **Multi-Database Support**: PostgreSQL, MySQL, Oracle, SQL Server, SQLite
- **Automated Schema Detection**: Extract tables, columns, data types, and constraints
- **Relationship Inference**: Automatically detect foreign keys and relationships
- **Smart Templates**: Generate configuration files with intelligent suggestions
- **Business Context Mapping**: Template for adding business metadata

## Quick Start

### Prerequisites

- Python 3.12+
- Database credentials with read access to schema metadata
- Database-specific driver installed (psycopg2, pymysql, cx_Oracle, pyodbc)

### Installation

The onboarding module is included with ReportSmith. Ensure you have the required database drivers:

```bash
# PostgreSQL
pip install psycopg2-binary

# MySQL
pip install pymysql

# Oracle
pip install cx_Oracle

# SQL Server
pip install pyodbc

# SQLite (built-in)
```

### Basic Usage

Run the onboarding CLI tool to introspect your database:

```bash
python -m reportsmith.onboarding.cli \
  --app-id my_app \
  --app-name "My Application" \
  --db-type postgresql \
  --host localhost \
  --port 5432 \
  --database mydb \
  --username user \
  --password pass \
  --output-dir ./config/applications
```

This will generate:
- `config/applications/my_app/app.yaml` - Application configuration
- `config/applications/my_app/schema.yaml` - Schema definition
- `config/applications/my_app/user_input_template.yaml` - Business context template
- `config/applications/my_app/README.md` - Setup instructions

## Database-Specific Examples

### PostgreSQL

```bash
python -m reportsmith.onboarding.cli \
  --app-id fund_accounting \
  --app-name "Fund Accounting System" \
  --db-type postgresql \
  --host localhost \
  --port 5432 \
  --database fund_db \
  --schema public \
  --username postgres \
  --password postgres \
  --business-function "Fund Management & Client Portfolio Tracking" \
  --output-dir ./config/applications
```

### MySQL

```bash
python -m reportsmith.onboarding.cli \
  --app-id inventory_system \
  --app-name "Inventory Management" \
  --db-type mysql \
  --host db.example.com \
  --port 3306 \
  --database inventory \
  --username dbuser \
  --password dbpass \
  --business-function "Inventory Tracking and Management" \
  --output-dir ./config/applications
```

### Oracle

```bash
python -m reportsmith.onboarding.cli \
  --app-id erp_system \
  --app-name "ERP System" \
  --db-type oracle \
  --host oracle.example.com \
  --port 1521 \
  --service-name ORCL \
  --username system \
  --password oracle \
  --business-function "Enterprise Resource Planning" \
  --output-dir ./config/applications
```

### SQL Server

```bash
python -m reportsmith.onboarding.cli \
  --app-id sales_app \
  --app-name "Sales Application" \
  --db-type sqlserver \
  --host sqlserver.example.com \
  --port 1433 \
  --database sales \
  --username sa \
  --password Password123 \
  --business-function "Sales Tracking and Reporting" \
  --output-dir ./config/applications
```

### SQLite

```bash
python -m reportsmith.onboarding.cli \
  --app-id local_app \
  --app-name "Local Application" \
  --db-type sqlite \
  --database /path/to/database.db \
  --output-dir ./config/applications
```

## Advanced Options

### Introspect Specific Tables

Only introspect selected tables:

```bash
python -m reportsmith.onboarding.cli \
  --app-id sales_app \
  --app-name "Sales Application" \
  --db-type postgresql \
  --host localhost \
  --port 5432 \
  --database sales \
  --username user \
  --password pass \
  --tables customers orders products \
  --output-dir ./config/applications
```

### Specify Schema

For databases with multiple schemas:

```bash
python -m reportsmith.onboarding.cli \
  --app-id analytics \
  --app-name "Analytics Application" \
  --db-type postgresql \
  --host localhost \
  --port 5432 \
  --database mydb \
  --schema analytics \
  --username user \
  --password pass \
  --output-dir ./config/applications
```

## Generated Files

### 1. app.yaml

Main application configuration with:
- Application metadata
- Database vendor information
- Detected relationships between tables
- Business context templates (metrics, rules, sample queries)

**Example:**

```yaml
---
# ================================================================================
# APPLICATION DEFINITION
# ================================================================================

application:
  id: fund_accounting
  name: Fund Accounting System
  database_vendor: postgresql
  business_function: Fund Management & Client Portfolio Tracking
  description: TODO: Add detailed application description

# ================================================================================
# RELATIONSHIPS
# ================================================================================

relationships:
  - name: orders_to_customers
    parent: customers.id
    child: orders.customer_id
    type: one_to_many
    description: Foreign key from orders to customers

# ================================================================================
# BUSINESS CONTEXT
# ================================================================================

business_context:
  metrics:
    example_metric:
      name: TODO: Metric Name
      formula: TODO: SUM(column) FROM table WHERE condition
      unit: TODO: currency/percentage/count
      description: TODO: Business meaning of this metric
```

### 2. schema.yaml

Schema definition with:
- Table definitions
- Column details (type, nullable, constraints)
- Primary keys
- Foreign keys
- Estimated row counts
- Auto-suggested aliases

**Example:**

```yaml
---
# ================================================================================
# TABLE DEFINITIONS
# ================================================================================

tables:
  customers:
    description: Customer accounts table
    aliases:
      - TODO: Add aliases for customers
    primary_key: id
    estimated_rows: 1000
    columns:
      id:
        type: integer
        nullable: false
        primary_key: true
        description: Unique customer identifier
      name:
        type: varchar
        nullable: false
        description: Customer name
        aliases:
          - title
          - label
```

### 3. user_input_template.yaml

Template for business context:
- Application details
- Table business context
- Column aliases and meanings
- Business metrics definitions
- Business rules
- Common query patterns

**Example:**

```yaml
application_details:
  business_function: 'TODO: Describe what this application does'
  description: 'TODO: Add detailed description'
  key_business_processes:
    - 'TODO: List main business processes'

table_business_context:
  customers:
    business_name: 'TODO: Business name for customers'
    description: 'TODO: Describe the business purpose of customers'
    aliases:
      - 'TODO: Add natural language aliases'
    key_columns:
      - id
      - name
      - status

column_aliases:
  customers.name:
    aliases:
      - 'TODO: Add natural language aliases for name'
    business_meaning: 'TODO: Describe what name represents'
```

## Post-Onboarding Steps

After running the onboarding tool:

### 1. Review Generated Schema

Check `schema.yaml` and verify:
- Table and column definitions are accurate
- Data types are correctly normalized
- Relationships are properly detected
- Add missing aliases

### 2. Fill Business Context

Edit `user_input_template.yaml`:
- Add business names for tables
- Define natural language aliases for columns
- Document business metrics
- Define business rules
- Add sample queries

### 3. Update Application Config

Copy relevant business context from `user_input_template.yaml` to `app.yaml`:
- Business metrics
- Business rules
- Sample queries

### 4. Test Configuration

Test your configuration with ReportSmith:

```bash
# Start ReportSmith
./start.sh

# Try a sample query
curl -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Show all customers"}'
```

## Programmatic Usage

You can also use the onboarding module programmatically:

```python
from reportsmith.onboarding import OnboardingManager
from reportsmith.config_system.config_models import DatabaseConfig, DatabaseType

# Create database configuration
db_config = DatabaseConfig(
    database_type=DatabaseType.POSTGRESQL,
    host='localhost',
    port=5432,
    database_name='mydb',
    schema='public',
    username='user',
    password='pass'
)

# Initialize onboarding manager
manager = OnboardingManager(
    application_id='my_app',
    application_name='My Application',
    database_config=db_config
)

# Run onboarding
output_paths = manager.run_onboarding(
    output_dir='./config/applications',
    schema='public',
    tables=None,  # All tables
    business_function='My business function'
)

print(f"Generated files: {output_paths}")
```

## Features and Capabilities

### Schema Introspection

The introspector extracts:
- **Tables**: Names, descriptions, row counts
- **Columns**: Names, data types, nullability, defaults
- **Constraints**: Primary keys, foreign keys, unique constraints
- **Indexes**: Index definitions
- **Comments**: Table and column comments (if available)

### Data Type Normalization

Database-specific types are normalized to common types:
- `INTEGER`, `BIGINT`, `SERIAL` → `integer`
- `NUMERIC`, `DECIMAL`, `FLOAT` → `numeric`
- `VARCHAR`, `TEXT`, `CHAR` → `varchar`
- `BOOLEAN`, `BOOL` → `boolean`
- `TIMESTAMP` → `timestamp`
- `DATE` → `date`

### Relationship Detection

The tool automatically detects:
- **One-to-Many**: Standard foreign key relationships
- **One-to-One**: Foreign key that is also a primary key
- **Many-to-Many**: Junction tables with composite primary keys

### Smart Suggestions

The template generator provides:
- **Column Aliases**: Auto-suggests for common patterns (AUM, NAV, etc.)
- **Dimension Detection**: Identifies categorical columns (type, status, category)
- **Key Columns**: Highlights important columns for business context
- **Business Metrics**: Templates for metric definitions

## Troubleshooting

### Connection Issues

**Error**: `Failed to connect to database`

**Solution**: 
- Verify database credentials
- Check network connectivity
- Ensure database driver is installed
- For Oracle, verify service name is correct

### Permission Issues

**Error**: `Permission denied to access schema metadata`

**Solution**: Ensure your database user has:
- SELECT permission on system tables
- For PostgreSQL: access to `information_schema` and `pg_catalog`
- For MySQL: access to `information_schema`
- For Oracle: access to `ALL_TABLES`, `ALL_CONSTRAINTS`, etc.

### Large Database Performance

For databases with many tables:
- Use `--tables` to introspect specific tables only
- Consider introspecting in batches
- Use database-specific optimizations for row count estimation

## Best Practices

1. **Start Small**: Introspect a subset of tables first to verify configuration
2. **Review Carefully**: Always review generated configurations before using
3. **Add Business Context**: The more context you add, the better query results
4. **Test Iteratively**: Test queries and refine configuration
5. **Document Custom Changes**: Keep notes on manual edits to generated files
6. **Version Control**: Commit generated configurations to version control

## Examples

See the `examples/onboarding/` directory for complete examples of:
- PostgreSQL fund accounting system
- MySQL inventory system
- Oracle ERP system
- Multi-schema applications

## Support

For issues or questions:
- Check the main ReportSmith documentation
- Review example configurations
- Open an issue on GitHub

## Future Enhancements

Planned features:
- View detection and introspection
- Stored procedure detection
- Data quality analysis
- Automatic metric suggestions based on column names
- Interactive onboarding wizard
- Configuration validation
