# Onboarding Module

The onboarding module provides automated database schema introspection and configuration generation for ReportSmith applications.

## Quick Start

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

## Features

- **Multi-Database Support**: PostgreSQL, MySQL, Oracle, SQL Server, SQLite
- **Automated Schema Detection**: Extract tables, columns, types, constraints
- **Relationship Inference**: Detect foreign keys and relationships
- **Smart Templates**: Generate configurations with intelligent suggestions
- **Business Context Mapping**: Templates for adding business metadata

## Components

### SchemaIntrospector

Introspects database schemas and extracts metadata:

```python
from reportsmith.onboarding import SchemaIntrospector
from reportsmith.config_system.config_models import DatabaseType

introspector = SchemaIntrospector(engine, DatabaseType.POSTGRESQL)
table_info = introspector.introspect_schema(schema='public')
relationships = introspector.detect_relationships(table_info)
```

### TemplateGenerator

Generates YAML configuration templates:

```python
from reportsmith.onboarding import TemplateGenerator

generator = TemplateGenerator(
    application_id='my_app',
    application_name='My Application',
    database_type=DatabaseType.POSTGRESQL
)

app_yaml = generator.generate_app_yaml(table_info, relationships)
schema_yaml = generator.generate_schema_yaml(table_info)
user_input = generator.generate_user_input_template(table_info)
```

### OnboardingManager

Orchestrates the complete onboarding workflow:

```python
from reportsmith.onboarding import OnboardingManager
from reportsmith.config_system.config_models import DatabaseConfig, DatabaseType

db_config = DatabaseConfig(
    database_type=DatabaseType.POSTGRESQL,
    host='localhost',
    port=5432,
    database_name='mydb',
    username='user',
    password='pass'
)

manager = OnboardingManager(
    application_id='my_app',
    application_name='My Application',
    database_config=db_config
)

output_paths = manager.run_onboarding(
    output_dir='./config/applications',
    business_function='My business function'
)
```

## Architecture

```
onboarding/
├── __init__.py              # Module exports
├── __main__.py              # CLI entry point
├── cli.py                   # Command-line interface
├── schema_introspector.py   # Database schema introspection
├── template_generator.py    # YAML template generation
└── onboarding_manager.py    # Workflow orchestration
```

## Testing

Run unit tests:

```bash
pytest tests/unit/onboarding/ -v
```

Test coverage:
- 31 unit tests
- Schema introspection (14 tests)
- Template generation (17 tests)
- All database vendors covered

## Documentation

See [ONBOARDING_GUIDE.md](../../docs/ONBOARDING_GUIDE.md) for complete documentation.

## Examples

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
  --output-dir ./config/applications
```

### MySQL

```bash
python -m reportsmith.onboarding.cli \
  --app-id inventory \
  --app-name "Inventory System" \
  --db-type mysql \
  --host localhost \
  --port 3306 \
  --database inventory \
  --username root \
  --password pass \
  --output-dir ./config/applications
```

### Specific Tables Only

```bash
python -m reportsmith.onboarding.cli \
  --app-id sales \
  --app-name "Sales System" \
  --db-type postgresql \
  --host localhost \
  --port 5432 \
  --database sales \
  --username user \
  --password pass \
  --tables customers orders products \
  --output-dir ./config/applications
```

## License

MIT
