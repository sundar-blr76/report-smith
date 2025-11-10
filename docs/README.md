# ReportSmith Documentation

This directory contains all technical documentation for ReportSmith.

## Quick Navigation

### Getting Started
- **[../README.md](../README.md)** - Project overview and quick start
- **[../SETUP.md](../SETUP.md)** - Detailed setup instructions
- **[../CONTRIBUTING.md](../CONTRIBUTING.md)** - Contribution guidelines

### Architecture & Design
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture overview
- **[HLD.md](HLD.md)** - High-level design
- **[LLD.md](LLD.md)** - Low-level design
- **[CROSS_APPLICATION_DATA_EXTRACTION_ANALYSIS.md](CROSS_APPLICATION_DATA_EXTRACTION_ANALYSIS.md)** - Analysis for cross-application data extraction

### Implementation & Best Practices
- **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - Implementation strategies, performance optimization
- **[DOMAIN_VALUES.md](DOMAIN_VALUES.md)** - Domain value handling and resolution
- **[DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)** - Database schema and tables

### Module Documentation
- **[modules/](modules/)** - Detailed module documentation
  - [AGENTS_MODULE.md](modules/AGENTS_MODULE.md) - Query orchestration
  - [QUERY_PROCESSING_MODULE.md](modules/QUERY_PROCESSING_MODULE.md) - Intent analysis, SQL generation
  - [SCHEMA_INTELLIGENCE_MODULE.md](modules/SCHEMA_INTELLIGENCE_MODULE.md) - Knowledge graph, embeddings
  - [QUERY_EXECUTION_MODULE.md](modules/QUERY_EXECUTION_MODULE.md) - SQL execution
  - [API_MODULE.md](modules/API_MODULE.md) - REST API
  - [UI_MODULE.md](modules/UI_MODULE.md) - Streamlit UI

### Historical Documentation
- **[archive/](archive/)** - Archived analysis and historical docs

## Documentation Structure

```
docs/
├── README.md                                    # This file - documentation index
├── ARCHITECTURE.md                              # System architecture
├── HLD.md                                       # High-level design
├── LLD.md                                       # Low-level design  
├── CROSS_APPLICATION_DATA_EXTRACTION_ANALYSIS.md # Cross-app data extraction analysis
├── IMPLEMENTATION_GUIDE.md                      # Implementation & performance
├── DOMAIN_VALUES.md                             # Domain value handling
├── DATABASE_SCHEMA.md                           # Database design
├── modules/                                     # Module-specific docs
│   ├── AGENTS_MODULE.md
│   ├── QUERY_PROCESSING_MODULE.md
│   ├── SCHEMA_INTELLIGENCE_MODULE.md
│   ├── QUERY_EXECUTION_MODULE.md
│   ├── API_MODULE.md
│   └── UI_MODULE.md
└── archive/                                     # Historical documentation
    ├── IMPLEMENTATION_HISTORY.md
    ├── SQL_VALIDATION_FAILURE_ANALYSIS.md
    ├── EMBEDDING_STRATEGY.md (merged into IMPLEMENTATION_GUIDE)
    └── PERFORMANCE.md (merged into IMPLEMENTATION_GUIDE)
```

## For Different Audiences

### 👨‍💻 Developers
Start with:
1. [ARCHITECTURE.md](ARCHITECTURE.md) - System overview
2. [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) - Best practices
3. [modules/](modules/) - Module details

### 🚀 DevOps
Start with:
1. [../SETUP.md](../SETUP.md) - Setup and deployment
2. [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) - Database requirements
3. [ARCHITECTURE.md](ARCHITECTURE.md) - System components

### 🏗️ Architects
Start with:
1. [HLD.md](HLD.md) - High-level design
2. [LLD.md](LLD.md) - Low-level design
3. [ARCHITECTURE.md](ARCHITECTURE.md) - Architecture details
4. [CROSS_APPLICATION_DATA_EXTRACTION_ANALYSIS.md](CROSS_APPLICATION_DATA_EXTRACTION_ANALYSIS.md) - Cross-app federation analysis

---

**Last Updated**: November 10, 2025  
**Version**: Added cross-application data extraction analysis
