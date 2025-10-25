# ReportSmith

## Overview
ReportSmith is an intelligent natural language to SQL application for financial data reporting. It understands database schemas across multiple heterogeneous databases and dynamically generates SQL queries from natural language requests.

## What It Does
- **Natural Language to SQL**: Ask questions in plain English, get SQL queries
- **Multi-Database Support**: Query across PostgreSQL, Oracle, SQL Server databases
- **Schema Intelligence**: Understands table relationships and business context
- **Multi-Step Execution**: Break complex queries into manageable steps
- **Cost Assessment**: Evaluate query cost before execution
- **Excel Output**: Generate formatted Excel reports
- **Complete Audit**: Track all executions with full transparency

## Key Features
- YAML-based application configs (one file per business application)
- Vector embeddings for semantic schema search
- User confirmation for expensive queries
- Saved queries for reuse
- Multi-database query federation
- Comprehensive execution logging

## Architecture
- **PostgreSQL Database**: 5 tables for execution tracking and metadata
- **YAML Configs**: Application schemas in `config/applications/`
- **Python Backend**: FastAPI + SQLAlchemy + LangChain
- **Vector Store**: Semantic search for schema matching

## Project Structure

```
ReportSmith/
├── src/reportsmith/       # Application code
├── config/
│   └── applications/      # YAML configs (one per app)
├── db_setup/              # Database setup scripts
├── docs/                  # Documentation
├── tests/                 # Tests
└── PROJECT.md             # Complete requirements & decisions
```

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 12+
- Environment variables configured

### Setup

1. **Create Database**
   ```bash
   cd db_setup
   python3 setup_database.py
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Applications**
   - Add YAML files to `config/applications/`
   - See `fund_accounting.yaml` for example

### Documentation
- **[SETUP.md](SETUP.md)** - Detailed setup guide
- **[docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md)** - Database schema details

## Example Use Case
```
User: "Show monthly fees for all TruePotential equity funds"

ReportSmith:
1. Identifies relevant tables (funds, fee_schedules)
2. Generates SQL across multiple regional databases
3. Executes with user confirmation if expensive
4. Outputs Excel report with audit trail
```

## Status
✅ Database schema created (5 tables)  
✅ Config system designed (YAML-based)  
🚧 Core RAG engine (in progress)  
📋 UI for query confirmation (planned)

## License
TBD