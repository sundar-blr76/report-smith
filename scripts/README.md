# ReportSmith Scripts

This directory contains convenience scripts for common ReportSmith operations.

## Database Onboarding

The onboarding scripts make it easy to connect to any database and automatically generate ReportSmith configuration files.

### Quick Start

#### Option 1: Python Script (Cross-platform)

```bash
python scripts/onboard_database.py \
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

#### Option 2: Bash Script (Unix/Linux/Mac)

```bash
./scripts/onboard_database.sh \
  --app-id my_app \
  --app-name "My Application" \
  --db-type postgresql \
  --host localhost \
  --port 5432 \
  --database mydb \
  --username user \
  --password pass
```

### What These Scripts Do

1. **Connect to your database** using the credentials you provide
2. **Extract the schema** - tables, columns, data types, constraints, foreign keys
3. **Detect relationships** - one-to-many, one-to-one, many-to-many
4. **Generate configuration files** in `config/applications/<app_id>/`:
   - `app.yaml` - Application configuration with relationships
   - `schema.yaml` - Complete schema definition
   - `user_input_template.yaml` - Template for business context
   - `README.md` - Next steps guide

### Supported Databases

- **PostgreSQL** - Full support
- **MySQL** - Full support
- **Oracle** - Full support (requires cx_Oracle driver)
- **SQL Server** - Full support (requires pyodbc driver)
- **SQLite** - Full support

### Examples

#### PostgreSQL Database

```bash
python scripts/onboard_database.py \
  --app-id fund_accounting \
  --app-name "Fund Accounting System" \
  --db-type postgresql \
  --host localhost \
  --port 5432 \
  --database fund_db \
  --username postgres \
  --password postgres \
  --business-function "Fund Management & Portfolio Tracking"
```

#### MySQL Database

```bash
./scripts/onboard_database.sh \
  --app-id inventory \
  --app-name "Inventory System" \
  --db-type mysql \
  --host localhost \
  --port 3306 \
  --database inventory \
  --username root \
  --password pass \
  --business-function "Inventory and Stock Management"
```

#### SQLite Database

```bash
python scripts/onboard_database.py \
  --app-id local_app \
  --app-name "Local Application" \
  --db-type sqlite \
  --database /path/to/database.db
```

#### Oracle Database

```bash
./scripts/onboard_database.sh \
  --app-id erp_system \
  --app-name "ERP System" \
  --db-type oracle \
  --host oracle.example.com \
  --port 1521 \
  --service-name ORCL \
  --username system \
  --password oracle
```

#### Specific Tables Only

Only extract specific tables:

```bash
python scripts/onboard_database.py \
  --app-id sales \
  --app-name "Sales System" \
  --db-type postgresql \
  --host localhost \
  --port 5432 \
  --database sales \
  --username user \
  --password pass \
  --tables customers orders products invoices
```

### Getting Help

View all available options:

```bash
python scripts/onboard_database.py --help
```

or

```bash
./scripts/onboard_database.sh --help
```

### After Running the Script

1. Navigate to the generated directory:
   ```bash
   cd config/applications/<your_app_id>
   ```

2. Review the generated files:
   ```bash
   cat schema.yaml        # Verify schema definitions
   cat app.yaml           # Review application config
   ```

3. Fill in business context:
   ```bash
   vi user_input_template.yaml  # Add business names, aliases, metrics
   ```

4. Update app.yaml with your business context:
   ```bash
   # Copy relevant sections from user_input_template.yaml to app.yaml
   ```

5. Test with ReportSmith:
   ```bash
   ./start.sh
   # Then query your new application
   ```

### Output Directory Structure

```
config/applications/<app_id>/
├── app.yaml                     # Application configuration (EDIT THIS)
├── schema.yaml                  # Schema definition (REVIEW & EDIT)
├── user_input_template.yaml     # Business context template (FILL OUT)
└── README.md                    # Setup instructions
```

### Troubleshooting

**Connection Issues:**
- Verify database credentials
- Check network connectivity
- Ensure database is running
- For Oracle, verify service name is correct

**Permission Issues:**
- Ensure database user has read access to schema metadata
- For PostgreSQL: access to `information_schema` and `pg_catalog`
- For MySQL: access to `information_schema`

**Driver Not Found:**
Install the required Python database driver:
```bash
pip install psycopg2-binary  # PostgreSQL
pip install pymysql          # MySQL
pip install cx_Oracle        # Oracle
pip install pyodbc           # SQL Server
```

### Advanced Usage

See the full documentation: [docs/ONBOARDING_GUIDE.md](../docs/ONBOARDING_GUIDE.md)

## Other Scripts

(Additional scripts will be documented here as they are added)
