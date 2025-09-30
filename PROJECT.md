# ReportSmith Project

## Overview
ReportSmith is an intelligent financial data RAG (Retrieval-Augmented Generation) application designed to understand existing application schemas, relationships, indices, and business context to dynamically generate reports based on natural language queries.

---

## User Aspirations & Vision

The RAG agent should be intelligent enough to:
- **Schema Intelligence**: Understand existing application schema, relationships, indices, and business context
- **Natural Language Processing**: Dynamically capture report scope, data points needed, aggregation requirements from user queries
- **Dynamic Query Generation**: Generate appropriate dynamic queries and execute them across multiple data sources
- **Multi-Step Execution**: Support complex requirements through multi-step query execution
- **Temporary Tables**: Create and utilize temporary tables for subsequent query steps when needed
- **Cost-Aware Processing**: Assess query execution cost upfront and provide restructuring options or user confirmation
- **Cross-Application Intelligence**: Handle heterogeneous databases and multiple instances across different business regions

---

## Architecture Decisions

### Database & Storage
- **Primary Datastore**: PostgreSQL (CONFIRMED)
- **Database Name**: `reportsmith` (not reportsmith_db)
- **Data Ingestion**: Separate project/module (decoupled architecture)
- **Logging Datastore**: Separate datastore for application traffic and execution logs
- **Vector Storage**: ChromaDB or pgvector for schema/context embedding

### Application Scope & Data Characteristics
- **No Time Series Data**: Current application scope excludes time series data
- **Heterogeneous Databases**: Support multiple database vendors across different business applications
- **Multiple Instances**: Handle different business regions/areas with same database vendor per application
- **Cross-Application**: Different applications may use different database vendors
- **Regional Data Distribution**: Same application data (varying business regions) will always be in same database vendor
- **Cross-Application Orchestration**: Overall business function orchestrated by multiple applications with potentially different database vendors

### Configuration Approach
- **Selected**: Configuration-Based Approach (Option A)
- Use application config files (YAML) for database connections and schema definitions
- Vector search for schema/context matching
- Direct database queries for operational data
- No embedding generation in operational databases
- One YAML file per application

---

## Core Features Required

### 1. Intelligent Query Generation
- Natural language to SQL conversion
- Dynamic query generation based on context
- Multi-step query execution capability
- Temporary table creation and management

### 2. User Interaction & Confirmation
- **Extraction Flow Display**: Return extraction flow to user for confirmation before execution
- **Smart UI**: Intelligent UI for data extraction plan review and approval
- **Query Execution Cost Assessment**: Assess and display query execution cost upfront
- **Query Restructuring Options**: Offer query restructuring alternatives or require user confirmation for expensive operations
- **Interactive Confirmation**: Dialog-driven approach for major operations

### 3. Output & Reporting
- Excel (.xls) output generation
- Multiple output formats support
- Detailed execution insights and logs

### 4. Predefined Templates & Scopes
- **Fund Manager Templates**: Predefined queries for different fund managers and their specific needs
- **Report Scope Definitions**: Structured report templates (e.g., "TruePotential monthly fees report")
- **Context-Aware Templates**: Templates that understand business context and automatically apply appropriate filters and aggregations
- **Fund-Specific Configurations**: Customizable query configurations for specific funds or business units

### 5. Transparency & Logging
- **Detailed Execution Insights**: Provide users with complete execution steps visibility
- **Application Traffic Logging**: Log all application traffic and execution details in separate datastore
- **Connection Transparency**: Show which application datastore connections are being used
- **Query Execution Details**: Display executed queries, row counts returned, execution times
- **Full Execution Audit Trail**: Comprehensive logging of all operations for full transparency
- **Separate Logging Datastore**: Dedicated datastore for application traffic and execution logs

### 6. Configuration Management
- **Application Configuration**: Comprehensive config containing:
  - Database connection configurations for multiple instances
  - Schema and table definitions with metadata
  - Business context and relationship mappings
  - Regional/instance-specific configurations
- **Vector Search Integration**: Use vector search for schema/context matching
- **Direct Data Access**: Direct application data access (no RAG for operational data like account IDs/names)
- **Legacy System Support**: Support for legacy applications without embedding generation capability in operational databases

---

## Technical Decisions Log

### Decision 1: Database Strategy
- **Date**: Initial setup
- **Decision**: Use PostgreSQL as primary datastore
- **Rationale**: User preference for reliability and performance
- **Status**: Confirmed

### Decision 2: Project Architecture
- **Date**: Initial setup
- **Decision**: Separate data ingestion project (ReportSmith-DataIngestion)
- **Rationale**: Decoupled architecture for better maintainability
- **Status**: Confirmed

### Decision 3: Query Execution Strategy
- **Date**: Initial setup
- **Decision**: Multi-step query execution with temp tables
- **Rationale**: Support complex reporting requirements
- **Status**: Confirmed

### Decision 4: Test Database Setup
- **Date**: Initial setup
- **Decision**: Create FinancialTestDB with public financial data
- **Rationale**: Realistic testing environment with non-trivial relationships
- **Status**: Confirmed
- **Database Name**: `financial_testdb`

### Decision 5: Configuration Approach
- **Date**: Initial setup
- **Decision**: Configuration-based approach (Option A) rather than full RAG embedding
- **Rationale**: Simpler, more maintainable, version-controllable
- **Status**: Confirmed

### Decision 6: Application Config Structure
- **Date**: Setup
- **Decision**: One YAML file per application
- **Rationale**: Human readable, self-contained, easy to maintain
- **Status**: Confirmed

### Decision 7: Database Naming Convention
- **Date**: Setup
- **Decision**: Use simple names without redundant suffixes (reportsmith not reportsmith_db)
- **Rationale**: Cleaner, less verbose, implicit context
- **Status**: Confirmed

---

## Development Preferences

### Collaborative Approach
- **Dialog-driven development**: Take detailed inputs before major implementations
- **Iterative process**: Build incrementally with feedback
- **Confirmation required**: For major architectural decisions
- **Minimal documentation**: Concise and to the point
- **Less autonomous**: Ask before doing heavy lifting

### Code Style
- Minimal comments (only when necessary)
- Comprehensive documentation for APIs
- Clean, readable code

---

## User Preferences Summary

1. **PostgreSQL** as primary database (CONFIRMED)
2. **Decoupled architecture** with separate data ingestion project
3. **Interactive confirmation** for extraction plans and major operations
4. **Excel output** generation capability (.xls format)
5. **Comprehensive logging** and execution insights with separate datastore
6. **Multi-database vendor** support across heterogeneous environments
7. **Cost assessment** before query execution with restructuring options
8. **Predefined report templates** for fund managers (e.g., TruePotential monthly fees report)
9. **Configuration-based approach** (Option A) rather than full RAG embedding
10. **Dialog-driven development** - take detailed inputs before major implementations
11. **Smart UI** for data extraction plan review and user confirmation
12. **Multi-step query execution** with temporary table support
13. **Cross-application intelligence** for heterogeneous database environments
14. **Separate test database** (financial_testdb) for comprehensive testing

---

## Development Phases

### Phase 1: Foundation
- Set up PostgreSQL as primary datastore
- Create configuration management system
- Implement basic natural language to SQL conversion
- Set up logging infrastructure

### Phase 2: Core Features
- Implement multi-step query execution
- Add user confirmation workflows
- Create basic UI for extraction plan review
- Implement Excel output generation

### Phase 3: Advanced Features
- Add predefined query templates
- Implement cost assessment
- Enhanced logging and transparency features
- Support for multiple database vendors

### Phase 4: Testing & Optimization
- Use FinancialTestDB for comprehensive testing
- Performance optimization
- User experience refinement

---

## Testing Strategy

- Create separate FinancialTestDB project with meaningful financial data
- Connect to existing local PostgreSQL database
- Populate with data from public repositories
- Test with non-trivial relationships and decent data volume
- Database name: `financial_testdb`

---

## What We Built

### Database
- **reportsmith**: 35 tables for ReportSmith metadata
- **financial_testdb**: Test database with realistic financial data
  - 5 management companies (TruePotential, Horizon, Meridian, Sterling, Apex)
  - 50 fund managers with specializations
  - 53 active funds across multiple types
  - 500 clients (Individual, Corporate, Institutional)
  - 608 active accounts
  - Real portfolio positions with market values
  - 5 different fee structures
  - Sample: 12 TruePotential funds with $5B+ combined AUM

### Configuration System
- Application configs in `config/applications/` (one YAML per app)
- Example: `fund_accounting.yaml`
- Environment variables for connections (REPORTSMITH_DB_*, FINANCIAL_TESTDB_*)

### Documentation
- Database schema documentation
- Setup guide
- This project overview

---

## Technology Stack

### Backend
- Python 3.11+ with FastAPI for REST APIs
- SQLAlchemy for database abstraction
- PostgreSQL as primary data store
- Vector Database (ChromaDB/Pinecone) for embeddings

### AI/ML
- LangChain for RAG orchestration
- OpenAI GPT-4 or Anthropic Claude for query generation
- Sentence Transformers for embedding generation
- Pandas for data manipulation

### Frontend (Future)
- React with TypeScript for UI
- D3.js for query flow visualization
- AG-Grid for data display
- ExcelJS for report generation

### Infrastructure
- Docker for containerization
- Redis for caching
- Nginx for load balancing
- Grafana for monitoring

---

## Success Metrics

### Accuracy
- **>95%** correct SQL generation for standard queries
- **>90%** correct results for multi-step queries
- **<5%** false positive schema matches

### Performance
- **<3 seconds** for simple query responses
- **<30 seconds** for complex multi-table joins
- **<60 seconds** for report generation with Excel export

### User Experience
- **>4.5/5** user satisfaction rating
- **<10%** queries requiring manual correction
- **>80%** adoption rate among target users

---

## Timeline (Estimated)

### Phase 1: Core RAG Engine (4-6 weeks)
- Schema analysis module
- Natural language processor
- Query executor

### Phase 2: Smart UI & User Experience (3-4 weeks)
- Query planning interface
- Report generation
- Real-time execution logging

### Phase 3: Advanced Features (4-5 weeks)
- Predefined templates
- Multi-database support
- Cross-database query federation

### Phase 4: Monitoring & Analytics (2-3 weeks)
- Execution logging
- Performance metrics tracking
- Administrative features

---

## Risk Mitigation

### Data Security
- Query sanitization and injection prevention
- Role-based access control for sensitive data
- Audit logging for all data access

### Performance
- Query timeout limits and cost thresholds
- Connection pooling and caching strategies
- Incremental loading for large datasets

### Reliability
- Graceful handling of database outages
- Query failure recovery and retry logic
- Comprehensive error logging and alerting

---

*Last updated: 2024-12-01*
