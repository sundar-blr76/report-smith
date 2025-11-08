# ReportSmith - High-Level Design (HLD)

**Document Version**: 1.0  
**Last Updated**: November 7, 2025  
**Status**: Draft

---

## 1. Executive Summary

### 1.1 Purpose
This document provides a high-level design overview of ReportSmith, a multi-agent natural language to SQL system that enables users to query financial databases using plain English questions.

### 1.2 Scope
This HLD covers:
- System architecture and components
- Data flow and interactions
- Technology stack
- Deployment architecture
- Non-functional requirements

### 1.3 Target Audience
- Software Architects
- Development Teams
- Technical Stakeholders
- Operations Teams

---

## 2. System Overview

### 2.1 Business Context
ReportSmith enables business users to extract insights from complex financial databases without SQL knowledge. The system translates natural language questions into optimized SQL queries, executes them, and returns formatted results.

**Key Business Value:**
- Democratizes data access for non-technical users
- Reduces dependency on data analysts
- Accelerates decision-making with self-service analytics
- Maintains data governance through controlled query execution

### 2.2 System Objectives
1. **Accuracy**: >95% intent recognition accuracy
2. **Performance**: <2 second query generation latency
3. **Usability**: Natural language interface requiring no SQL knowledge
4. **Scalability**: Support concurrent users and multiple databases
5. **Auditability**: Complete tracking of all query executions

---

## 3. System Architecture

### 3.1 Architectural Style
ReportSmith follows a **multi-layered microservices architecture** with:
- **Presentation Layer**: Web UI (Streamlit) and REST API (FastAPI)
- **Orchestration Layer**: LangGraph-based multi-agent workflow
- **Processing Layer**: Intent analysis, schema intelligence, SQL generation
- **Data Layer**: PostgreSQL (metadata), ChromaDB (vectors), target databases

### 3.2 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌───────────────────┐              ┌────────────────────┐              │
│  │  Web Browser      │              │  API Client        │              │
│  │  (Streamlit UI)   │              │  (REST/SDK)        │              │
│  │  Port: 8501       │              │                    │              │
│  └─────────┬─────────┘              └──────────┬─────────┘              │
│            │                                   │                         │
└────────────┼───────────────────────────────────┼─────────────────────────┘
             │                                   │
             │         HTTP/REST                 │
             ▼                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          APPLICATION LAYER                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    FastAPI REST Server                             │  │
│  │                      (Port: 8000)                                  │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │  │
│  │  │  /query      │  │  /health     │  │  /ready      │            │  │
│  │  │  endpoint    │  │  endpoint    │  │  endpoint    │            │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘            │  │
│  └───────────────────────────┬───────────────────────────────────────┘  │
│                              │                                           │
│                              ▼                                           │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │              LangGraph Multi-Agent Orchestrator                    │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │  State Machine: QueryState                                   │  │  │
│  │  │                                                               │  │  │
│  │  │  Intent → Semantic → Filter → Refine → Schema → Plan → SQL  │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                           │
└───────────────────────────────┬───────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         PROCESSING LAYER                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
│  │ Query Processing │  │ Schema           │  │ Query Execution  │      │
│  │                  │  │ Intelligence     │  │                  │      │
│  ├──────────────────┤  ├──────────────────┤  ├──────────────────┤      │
│  │• Intent Analyzer │  │• Embedding Mgr   │  │• SQL Executor    │      │
│  │• Hybrid Analysis │  │• Knowledge Graph │  │• Connection Pool │      │
│  │• SQL Generator   │  │• Graph Builder   │  │• Result Format   │      │
│  │• SQL Validator   │  │• Dimension Loader│  │                  │      │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘      │
│           │                     │                     │                 │
└───────────┼─────────────────────┼─────────────────────┼─────────────────┘
            │                     │                     │
            ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │ PostgreSQL   │  │ ChromaDB     │  │ OpenAI API   │  │ Gemini API │  │
│  │              │  │              │  │              │  │            │  │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤  ├────────────┤  │
│  │• Metadata    │  │• Embeddings  │  │• Embeddings  │  │• LLM       │  │
│  │• Audit Logs  │  │• Vector      │  │• Vector      │  │• Analysis  │  │
│  │• Config      │  │  Search      │  │  Generation  │  │            │  │
│  │• Target DBs  │  │  (In-Memory) │  │              │  │            │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘  │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Component Overview

| Component | Responsibility | Technology |
|-----------|---------------|------------|
| Streamlit UI | Interactive web interface | Python, Streamlit |
| FastAPI Server | REST API endpoints | Python, FastAPI |
| LangGraph Orchestrator | Multi-agent workflow coordination | LangGraph, Python |
| Intent Analyzer | Extract entities and intent from NL | LLM, Local Mappings |
| Embedding Manager | Semantic search for entities | OpenAI API, ChromaDB |
| Knowledge Graph | Table relationships and join paths | NetworkX, Python |
| SQL Generator | Convert plans to executable SQL | Python |
| SQL Executor | Execute queries and format results | SQLAlchemy, Python |
| PostgreSQL | Metadata and audit storage | PostgreSQL 12+ |
| ChromaDB | Vector embeddings storage | ChromaDB (in-memory) |

---

## 4. Data Flow Architecture

### 4.1 Query Processing Flow

```
┌──────────────┐
│ User Input   │ "Show AUM for all equity funds"
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│ Stage 1: Intent Analysis                                  │
│ Input: Natural language question                          │
│ Output: Intent type, entities, filters                    │
│ Duration: ~250ms                                           │
└──────┬───────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│ Stage 2: Semantic Enrichment                              │
│ Input: Extracted entities                                 │
│ Output: Entity matches with scores                        │
│ Duration: ~150ms                                           │
└──────┬───────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│ Stage 3: Semantic Filtering (LLM)                         │
│ Input: Semantic matches                                   │
│ Output: Filtered, relevant entities                       │
│ Duration: ~2500ms                                          │
└──────┬───────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│ Stage 4: Schema Mapping                                   │
│ Input: Filtered entities                                  │
│ Output: Tables, columns, relationships                    │
│ Duration: ~50ms                                            │
└──────┬───────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│ Stage 5: Query Planning                                   │
│ Input: Schema mappings                                    │
│ Output: Execution plan with join paths                   │
│ Duration: ~100ms                                           │
└──────┬───────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│ Stage 6: SQL Generation                                   │
│ Input: Execution plan                                     │
│ Output: Executable SQL query                              │
│ Duration: <1ms                                             │
└──────┬───────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│ Stage 7: SQL Execution                                    │
│ Input: SQL query                                          │
│ Output: Query results (JSON/table)                        │
│ Duration: ~500ms                                           │
└──────┬───────────────────────────────────────────────────┘
       │
       ▼
┌──────────────┐
│ User Output  │ Formatted results with metadata
└──────────────┘

Total Latency: ~3.6 seconds
```

### 4.2 Data Flow Patterns

#### Pattern 1: Request-Response (Synchronous)
- Used for: Single queries via UI or API
- Flow: User → API → Orchestrator → Processor → Database → Response
- Timeout: 30 seconds

#### Pattern 2: Event-Driven (Planned)
- Used for: Batch queries, scheduled reports
- Flow: Scheduler → Queue → Worker → Database → Notification
- Status: Future enhancement

---

## 5. Technology Stack

### 5.1 Runtime Environment
- **Language**: Python 3.12+
- **Package Manager**: pip
- **Virtual Environment**: venv/conda

### 5.2 Core Frameworks
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Orchestration | LangGraph | Latest | Multi-agent workflow |
| API Server | FastAPI | 0.100+ | REST API |
| Web UI | Streamlit | 1.24+ | Interactive interface |
| Database ORM | SQLAlchemy | 2.0+ | Database abstraction |
| Vector Store | ChromaDB | Latest | Embedding storage |
| LLM Provider | OpenAI API | Latest | Embeddings |
| LLM Provider | Google Gemini | Latest | Intent analysis |

### 5.3 Data Stores
| Store | Purpose | Persistence |
|-------|---------|-------------|
| PostgreSQL | Metadata, audit logs, target data | Persistent |
| ChromaDB | Vector embeddings | In-memory |
| Redis (optional) | Embedding cache | Persistent (24h TTL) |

### 5.4 External APIs
- **OpenAI API**: Text embedding generation
- **Google Gemini API**: LLM-based intent analysis and filtering

---

## 6. Deployment Architecture

### 6.1 Deployment Options

#### Option 1: Single Server Deployment (Current)
```
┌────────────────────────────────────────┐
│        Application Server               │
│                                         │
│  ┌──────────────┐  ┌────────────────┐  │
│  │ FastAPI      │  │ Streamlit UI   │  │
│  │ :8000        │  │ :8501          │  │
│  └──────────────┘  └────────────────┘  │
│                                         │
│  ┌──────────────┐  ┌────────────────┐  │
│  │ ChromaDB     │  │ File System    │  │
│  │ (in-memory)  │  │ (YAML configs) │  │
│  └──────────────┘  └────────────────┘  │
└────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────┐
│     PostgreSQL Database Server          │
│  • Metadata DB                          │
│  • Target Financial DBs                 │
└────────────────────────────────────────┘
```

#### Option 2: Containerized Deployment (Planned)
```
┌────────────────────────────────────────────────────┐
│              Docker Compose / Kubernetes            │
├────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │ API Container│  │ UI Container │  │ Worker   │ │
│  │ FastAPI      │  │ Streamlit    │  │ (future) │ │
│  └──────────────┘  └──────────────┘  └──────────┘ │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐               │
│  │ PostgreSQL   │  │ Redis        │               │
│  │ Container    │  │ Container    │               │
│  └──────────────┘  └──────────────┘               │
└────────────────────────────────────────────────────┘
```

### 6.2 Network Architecture
```
                  Internet
                     │
                     ▼
           ┌─────────────────┐
           │  Load Balancer  │
           │   (Optional)    │
           └────────┬────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
┌───────────────┐      ┌───────────────┐
│  API Server   │      │  UI Server    │
│  :8000        │      │  :8501        │
└───────┬───────┘      └───────────────┘
        │
        ▼
┌────────────────────────┐
│  Internal Network      │
│                        │
│  ┌──────────────────┐  │
│  │  PostgreSQL      │  │
│  │  :5432           │  │
│  └──────────────────┘  │
│                        │
│  ┌──────────────────┐  │
│  │  Redis (optional)│  │
│  │  :6379           │  │
│  └──────────────────┘  │
└────────────────────────┘
```

---

## 7. Non-Functional Requirements

### 7.1 Performance
| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Query Latency (P50) | <2s | 3.6s | 🔴 In Progress |
| Query Latency (P95) | <5s | 5.2s | 🟡 Acceptable |
| Intent Accuracy | >95% | 95% | 🟢 Met |
| Concurrent Users | 50 | 10 | 🔴 Planned |
| Uptime | 99.5% | N/A | 🔴 Planned |

### 7.2 Scalability
- **Vertical**: Scale up to 16 CPU cores, 32GB RAM
- **Horizontal**: Multi-instance deployment with load balancer (planned)
- **Data**: Support up to 1000 tables, 10K columns per application

### 7.3 Security
| Requirement | Status | Implementation |
|-------------|--------|----------------|
| API Authentication | 🔴 Planned | OAuth 2.0 / API Keys |
| SQL Injection Prevention | 🟢 Implemented | Parameterized queries |
| Data Encryption (transit) | 🟢 Implemented | HTTPS/TLS |
| Data Encryption (rest) | 🟡 Partial | Database-level |
| Audit Logging | 🟢 Implemented | All queries logged |
| RBAC | 🔴 Planned | Role-based access |

### 7.4 Availability
- **Target Uptime**: 99.5% (monthly)
- **Recovery Time Objective (RTO)**: <30 minutes
- **Recovery Point Objective (RPO)**: <5 minutes
- **Backup Strategy**: Daily database backups, config version control

### 7.5 Maintainability
- **Code Coverage**: Target 80%
- **Documentation**: Inline docstrings, module docs, architecture docs
- **Logging**: Structured logging with request IDs
- **Monitoring**: Health checks, metrics collection (planned)

---

## 8. Integration Architecture

### 8.1 External System Integrations

```
┌─────────────────────────────────────────────────────────┐
│                    ReportSmith                          │
└──────┬───────────────────┬───────────────────┬──────────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐   ┌─────────────────┐   ┌──────────────┐
│ OpenAI API  │   │  Google Gemini  │   │  PostgreSQL  │
│             │   │      API        │   │   Databases  │
├─────────────┤   ├─────────────────┤   ├──────────────┤
│• Embeddings │   │• LLM Analysis   │   │• Financial   │
│• API Key    │   │• API Key        │   │  Data        │
│  Auth       │   │  Auth           │   │• Metadata    │
└─────────────┘   └─────────────────┘   └──────────────┘
```

### 8.2 Integration Patterns
- **REST API**: Synchronous HTTP calls to OpenAI, Gemini
- **Database**: Connection pooling with SQLAlchemy
- **Configuration**: YAML-based file configuration
- **Caching**: Optional Redis for embedding cache

---

## 9. Configuration Management

### 9.1 Configuration Hierarchy
```
config/
├── applications/           # Per-application configs
│   └── {app_name}/
│       ├── app.yaml       # Application metadata
│       └── schema.yaml    # Database schema definition
└── entity_mappings.yaml   # Global entity mappings
```

### 9.2 Configuration Types
1. **Application Config**: Database connections, vendor info
2. **Schema Config**: Tables, columns, relationships, filters
3. **Entity Mappings**: Business term to schema mappings
4. **Environment Variables**: API keys, secrets, runtime settings

---

## 10. Monitoring and Observability

### 10.1 Logging Strategy
- **Application Logs**: `logs/app.log`
- **UI Logs**: `logs/ui.log`
- **Semantic Debug**: `logs/semantic_debug/`
- **Log Format**: Structured JSON with request IDs
- **Retention**: 30 days

### 10.2 Metrics (Planned)
- Query throughput (queries/second)
- Latency percentiles (P50, P95, P99)
- Error rates by stage
- LLM API costs
- Cache hit rates
- Database connection pool utilization

### 10.3 Health Checks
- `/health`: Basic liveness check
- `/ready`: Readiness check (dependencies available)

---

## 11. Security Architecture

### 11.1 Security Layers
```
┌────────────────────────────────────────┐
│  Transport Security (HTTPS/TLS)        │
├────────────────────────────────────────┤
│  Authentication (API Keys/OAuth)       │
├────────────────────────────────────────┤
│  Authorization (RBAC)                  │
├────────────────────────────────────────┤
│  Input Validation & Sanitization       │
├────────────────────────────────────────┤
│  SQL Injection Prevention              │
├────────────────────────────────────────┤
│  Audit Logging                         │
└────────────────────────────────────────┘
```

### 11.2 Threat Model
| Threat | Mitigation | Status |
|--------|------------|--------|
| SQL Injection | Parameterized queries, input validation | 🟢 Implemented |
| API Abuse | Rate limiting, authentication | 🔴 Planned |
| Credential Exposure | Environment variables, secrets manager | 🟡 Partial |
| Data Leakage | RBAC, query auditing | 🔴 Planned |
| LLM Prompt Injection | Input sanitization, prompt hardening | 🟡 Partial |

---

## 12. Disaster Recovery

### 12.1 Backup Strategy
- **Database Backups**: Daily automated backups
- **Configuration**: Version controlled in Git
- **Code**: Version controlled in Git
- **Logs**: Archived to object storage (planned)

### 12.2 Recovery Procedures
1. **Service Failure**: Automatic restart via systemd/Docker
2. **Database Failure**: Restore from latest backup
3. **Config Corruption**: Rollback to previous Git version
4. **Complete Disaster**: Rebuild from infrastructure as code

---

## 13. Future Enhancements

### 13.1 Planned Features
- [ ] Streaming UI with real-time progress
- [ ] Query result caching
- [ ] Natural language result explanations
- [ ] Multi-turn conversations
- [ ] Advanced query optimization
- [ ] Multi-database federation

### 13.2 Scalability Roadmap
- [ ] Async workflow processing
- [ ] Horizontal scaling with load balancer
- [ ] Distributed caching (Redis)
- [ ] Message queue for batch processing
- [ ] Microservices decomposition

---

## 14. References

### 14.1 Related Documentation
- [Low-Level Design (LLD)](LLD.md)
- [Architecture Overview](ARCHITECTURE.md)
- [Database Schema](DATABASE_SCHEMA.md)
- [Current State](CURRENT_STATE.md)

### 14.2 External References
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)

---

**Document Control**  
**Version**: 1.0  
**Last Updated**: November 7, 2025  
**Author**: Development Team  
**Approver**: [Pending]
