# Application Configurations

## 📁 Structure

**One YAML file per application** - Each file contains everything about that application:
- Database connections (all regions)
- Complete table schemas
- Column definitions with business context
- Table relationships
- Business metrics and rules
- Sample queries

```
applications/
├── fund_accounting.yaml    # Fund Accounting System (complete)
├── crm_system.yaml         # CRM (to be added)
└── erp_system.yaml         # ERP (to be added)
```

## 📝 YAML File Structure

Each application config has these sections:

```yaml
application:              # Basic info (name, vendor, version)
  
database_instances:       # Regional databases (APAC, EMEA, etc)
  apac_primary:          # Connection details per region
  emea_primary:
  
schema:                   # Complete schema definition
  tables:                # One entry per table
    funds:              # Table name
      description:      # What this table contains
      columns:          # All columns with types and meaning
      indexes:          # Performance indexes
      common_queries:   # Typical queries on this table
    
relationships:            # How tables connect
  
business_context:         # Business rules and metrics
  metrics:               # Calculated metrics (return, fees, etc)
  rules:                 # Business rules and constraints
  sample_queries:        # Example queries with SQL
```

## 🎯 Key Features

### Human Readable
- Comments explaining everything
- Clear structure
- Business terminology

### LLM Friendly
- Column descriptions include business meaning
- Sample queries show usage patterns
- Relationships explicitly defined

### Version Controlled
- Git tracks all changes
- Easy to diff and review
- Rollback friendly

## 📖 Example

See **[fund_accounting.yaml](fund_accounting.yaml)** for a complete example.

## ✅ Validation

Before using, validate the YAML:

```bash
python scripts/validate_config.py config/applications/fund_accounting.yaml
```

## 🔄 Sync to Database

After editing, sync to ReportSmith database:

```bash
python scripts/sync_config_to_db.py config/applications/fund_accounting.yaml
```

This will:
1. Parse and validate the YAML
2. Store in PostgreSQL (reportsmith)
3. Generate embeddings for vector search
4. Update cache

## 📋 Adding a New Application

1. Copy `fund_accounting.yaml` as a template
2. Edit with your application details
3. Validate: `python scripts/validate_config.py your_app.yaml`
4. Sync: `python scripts/sync_config_to_db.py your_app.yaml`
