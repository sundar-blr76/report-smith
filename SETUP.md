# ReportSmith - Setup Guide

## Prerequisites

- Python 3.11+
- PostgreSQL 12+
- Access to target databases you want to query

## Environment Setup

### 1. Configure Environment Variables

Add to `~/.bashrc`:

```bash
# ReportSmith Database
export REPORTSMITH_DB_HOST="192.168.29.69"
export REPORTSMITH_DB_PORT="5432"
export REPORTSMITH_DB_NAME="reportsmith"
export REPORTSMITH_DB_USER="postgres"
export REPORTSMITH_DB_PASSWORD="your_password"

# Financial Test Database (optional)
export FINANCIAL_TESTDB_HOST="192.168.29.69"
export FINANCIAL_TESTDB_PORT="5432"
export FINANCIAL_TESTDB_NAME="financial_testdb"
export FINANCIAL_TESTDB_USER="postgres"
export FINANCIAL_TESTDB_PASSWORD="your_password"
```

Then:
```bash
source ~/.bashrc
```

## Database Setup

### Create ReportSmith Database

```bash
cd scripts
python3 setup_database.py
```

This creates:
- `reportsmith` database
- 5 tables (execution tracking, saved queries, vector embeddings)

### Verify Installation

```bash
# Should show 5 tables
psql -U postgres -h $REPORTSMITH_DB_HOST -d reportsmith \
  -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';"
```

## Application Configuration

### Add Your Applications

Create one YAML file per application in `config/applications/`:

```bash
# Example
cp config/applications/fund_accounting.yaml config/applications/your_app.yaml
vim config/applications/your_app.yaml
```

### YAML Structure

```yaml
application:
  name: "Fund Accounting System"
  vendor: "YourVendor"
  database_vendor: "postgresql"

database_instances:
  - instance_id: "fund_accounting_apac"
    region: "APAC"
    host: "db.example.com"
    port: 5432
    database: "fund_accounting"

schema:
  tables:
    funds:
      description: "Fund master data"
      columns:
        fund_id: "Unique fund identifier"
        fund_name: "Fund name"
      indexes:
        - "fund_id"
```

**See:** `config/applications/fund_accounting.yaml` for complete example

## Python Environment

```bash
# Install dependencies
pip install -r requirements.txt

# Verify
python -c "import reportsmith; print('OK')"
```

## Workflow

### 1. Define Application Schema
Edit YAML files in `config/applications/`

### 2. Application Reads Config
YAML files are loaded at runtime (no sync needed)

### 3. Vector Embeddings
Schema embeddings generated and stored in `schema_embeddings` table

### 4. Query Execution
Natural language → SQL → Execution → Audit log

## Documentation

- **[PROJECT.md](PROJECT.md)** - Complete requirements & decisions
- **[docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md)** - Database schema
- **[config/applications/README.md](config/applications/README.md)** - Config guide

## Next Steps

1. ✅ Create database (done if setup_database.py succeeded)
2. 📝 Add your first application YAML config
3. 🚀 Run ReportSmith and test queries

## Troubleshooting

### Database Connection Issues
```bash
# Test connection
psql -U $REPORTSMITH_DB_USER -h $REPORTSMITH_DB_HOST -d $REPORTSMITH_DB_NAME -c "SELECT 1;"
```

### Check Tables
```bash
psql -U $REPORTSMITH_DB_USER -h $REPORTSMITH_DB_HOST -d $REPORTSMITH_DB_NAME \
  -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
```
