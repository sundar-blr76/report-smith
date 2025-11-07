# ReportSmith - Architecture Diagrams

**Document Version**: 1.0  
**Last Updated**: November 7, 2025

This document contains comprehensive architecture diagrams for ReportSmith in Mermaid format.

---

## 1. System Context Diagram

```mermaid
graph TB
    subgraph "External Actors"
        User[Business User]
        Admin[System Administrator]
        Analyst[Data Analyst]
    end
    
    subgraph "ReportSmith System"
        UI[Web Interface<br/>Streamlit]
        API[REST API<br/>FastAPI]
    end
    
    subgraph "External Services"
        OpenAI[OpenAI API<br/>Embeddings]
        Gemini[Google Gemini<br/>LLM Analysis]
        FinDB[(Financial<br/>Databases)]
        MetaDB[(Metadata<br/>Database)]
    end
    
    User -->|Natural Language<br/>Queries| UI
    User -->|REST Requests| API
    Admin -->|Configuration| UI
    Analyst -->|Query Analysis| UI
    
    UI -->|Query Processing| API
    API -->|Embeddings| OpenAI
    API -->|Intent Analysis| Gemini
    API -->|Execute Queries| FinDB
    API -->|Store Metadata| MetaDB
    
    style UI fill:#e1f5ff
    style API fill:#e1f5ff
    style OpenAI fill:#fff3e0
    style Gemini fill:#fff3e0
    style FinDB fill:#f3e5f5
    style MetaDB fill:#f3e5f5
```

---

## 2. High-Level Architecture

```mermaid
graph TB
    subgraph "Presentation Layer"
        StreamlitUI[Streamlit UI<br/>:8501]
        RestAPI[FastAPI Server<br/>:8000]
    end
    
    subgraph "Orchestration Layer"
        LangGraph[LangGraph Orchestrator<br/>Multi-Agent Workflow]
    end
    
    subgraph "Processing Layer"
        QueryProc[Query Processing<br/>Intent Analysis<br/>SQL Generation]
        SchemaInt[Schema Intelligence<br/>Embeddings<br/>Knowledge Graph]
        QueryExec[Query Execution<br/>SQL Executor<br/>Result Formatting]
    end
    
    subgraph "Data Layer"
        PostgreSQL[(PostgreSQL<br/>Metadata & Audit)]
        ChromaDB[(ChromaDB<br/>Vector Store)]
        TargetDB[(Target Databases<br/>Financial Data)]
    end
    
    subgraph "External APIs"
        OpenAIAPI[OpenAI API]
        GeminiAPI[Gemini API]
    end
    
    StreamlitUI --> RestAPI
    RestAPI --> LangGraph
    
    LangGraph --> QueryProc
    LangGraph --> SchemaInt
    LangGraph --> QueryExec
    
    QueryProc --> GeminiAPI
    SchemaInt --> OpenAIAPI
    SchemaInt --> ChromaDB
    SchemaInt --> PostgreSQL
    QueryExec --> TargetDB
    QueryExec --> PostgreSQL
    
    style StreamlitUI fill:#4fc3f7
    style RestAPI fill:#4fc3f7
    style LangGraph fill:#81c784
    style QueryProc fill:#ffb74d
    style SchemaInt fill:#ffb74d
    style QueryExec fill:#ffb74d
```

---

## 3. Query Processing Flow

```mermaid
sequenceDiagram
    participant User
    participant UI as Streamlit UI
    participant API as FastAPI
    participant Orch as LangGraph Orchestrator
    participant Intent as Intent Analyzer
    participant Embed as Embedding Manager
    participant KG as Knowledge Graph
    participant SQL as SQL Generator
    participant Exec as SQL Executor
    participant DB as Database
    
    User->>UI: Enter question
    UI->>API: POST /query
    API->>Orch: process_query()
    
    Note over Orch: Stage 1: Intent Analysis
    Orch->>Intent: analyze_intent()
    Intent->>Intent: Extract entities
    Intent-->>Orch: Intent + Entities
    
    Note over Orch: Stage 2: Semantic Enrichment
    Orch->>Embed: semantic_search()
    Embed->>Embed: Vector search
    Embed-->>Orch: Matches + Scores
    
    Note over Orch: Stage 3: Schema Mapping
    Orch->>KG: find_join_path()
    KG->>KG: BFS graph search
    KG-->>Orch: Join plan
    
    Note over Orch: Stage 4: SQL Generation
    Orch->>SQL: generate_sql()
    SQL->>SQL: Build query
    SQL-->>Orch: SQL Query
    
    Note over Orch: Stage 5: Execution
    Orch->>Exec: execute()
    Exec->>DB: Run SQL
    DB-->>Exec: Results
    Exec-->>Orch: Formatted results
    
    Orch-->>API: QueryResult
    API-->>UI: JSON Response
    UI-->>User: Display results
```

---

## 4. Multi-Agent Workflow

```mermaid
stateDiagram-v2
    [*] --> IntentAnalysis: User Question
    
    IntentAnalysis --> SemanticEnrichment: Entities Extracted
    
    SemanticEnrichment --> SemanticFilter: Vector Search Complete
    
    SemanticFilter --> RefineEntities: LLM Filtering Done
    
    RefineEntities --> SchemaMapping: Entities Refined
    
    SchemaMapping --> QueryPlanning: Tables Identified
    
    QueryPlanning --> SQLGeneration: Join Paths Found
    
    SQLGeneration --> Finalize: SQL Generated
    
    Finalize --> [*]: Results Ready
    
    IntentAnalysis --> Error: No Entities Found
    SemanticEnrichment --> Error: Search Failed
    SemanticFilter --> Error: LLM Error
    SchemaMapping --> Error: Table Not Found
    QueryPlanning --> Error: No Join Path
    SQLGeneration --> Error: Invalid SQL
    
    Error --> [*]: Return Error
```

---

## 5. Component Architecture

```mermaid
graph TB
    subgraph "agents"
        Orch[orchestrator.py<br/>MultiAgentOrchestrator]
        Nodes[nodes.py<br/>AgentNodes]
    end
    
    subgraph "query_processing"
        Hybrid[hybrid_intent_analyzer.py<br/>HybridIntentAnalyzer]
        LLMIntent[llm_intent_analyzer.py<br/>LLMIntentAnalyzer]
        SQLGen[sql_generator.py<br/>SQLGenerator]
        SQLVal[sql_validator.py<br/>SQLValidator]
    end
    
    subgraph "schema_intelligence"
        EmbedMgr[embedding_manager.py<br/>EmbeddingManager]
        KGraph[knowledge_graph.py<br/>SchemaKnowledgeGraph]
        GraphBuild[graph_builder.py<br/>KnowledgeGraphBuilder]
        DimLoad[dimension_loader.py<br/>DimensionLoader]
    end
    
    subgraph "query_execution"
        Executor[sql_executor.py<br/>SQLExecutor]
        ConnMgr[connection_manager.py<br/>ConnectionManager]
    end
    
    subgraph "api"
        Server[server.py<br/>FastAPI App]
    end
    
    subgraph "ui"
        UIApp[app.py<br/>Streamlit App]
    end
    
    Server --> Orch
    UIApp --> Server
    
    Orch --> Nodes
    Nodes --> Hybrid
    Nodes --> EmbedMgr
    Nodes --> KGraph
    Nodes --> SQLGen
    Nodes --> Executor
    
    Hybrid --> LLMIntent
    SQLGen --> SQLVal
    SQLGen --> KGraph
    
    EmbedMgr --> GraphBuild
    KGraph --> GraphBuild
    GraphBuild --> DimLoad
    
    Executor --> ConnMgr
    
    style Orch fill:#81c784
    style Server fill:#4fc3f7
    style UIApp fill:#4fc3f7
```

---

## 6. Data Flow Architecture

```mermaid
flowchart LR
    subgraph Input
        Q[Natural Language<br/>Question]
    end
    
    subgraph "Stage 1: Intent"
        I1[Extract<br/>Entities]
        I2[Identify<br/>Intent Type]
    end
    
    subgraph "Stage 2: Semantic"
        S1[Embed<br/>Query]
        S2[Vector<br/>Search]
        S3[Find<br/>Matches]
    end
    
    subgraph "Stage 3: Filter"
        F1[LLM<br/>Analysis]
        F2[Filter<br/>Results]
    end
    
    subgraph "Stage 4: Schema"
        SC1[Map<br/>Tables]
        SC2[Map<br/>Columns]
        SC3[Find<br/>Relations]
    end
    
    subgraph "Stage 5: Plan"
        P1[Build<br/>Join Path]
        P2[Apply<br/>Filters]
        P3[Create<br/>Plan]
    end
    
    subgraph "Stage 6: SQL"
        SQ1[Generate<br/>SELECT]
        SQ2[Generate<br/>FROM/JOIN]
        SQ3[Generate<br/>WHERE]
        SQ4[Assemble<br/>SQL]
    end
    
    subgraph "Stage 7: Execute"
        E1[Connect<br/>DB]
        E2[Run<br/>Query]
        E3[Format<br/>Results]
    end
    
    subgraph Output
        R[Query<br/>Results]
    end
    
    Q --> I1 --> I2
    I2 --> S1 --> S2 --> S3
    S3 --> F1 --> F2
    F2 --> SC1 --> SC2 --> SC3
    SC3 --> P1 --> P2 --> P3
    P3 --> SQ1 --> SQ2 --> SQ3 --> SQ4
    SQ4 --> E1 --> E2 --> E3
    E3 --> R
```

---

## 7. Knowledge Graph Structure

```mermaid
graph LR
    subgraph Tables
        Funds[funds]
        MgmtCo[management_companies]
        Clients[clients]
        Accounts[accounts]
        Holdings[holdings]
        Transactions[transactions]
        FeeTransactions[fee_transactions]
    end
    
    Funds -->|management_company_id| MgmtCo
    Accounts -->|client_id| Clients
    Holdings -->|account_id| Accounts
    Holdings -->|fund_id| Funds
    Transactions -->|account_id| Accounts
    Transactions -->|fund_id| Funds
    FeeTransactions -->|fund_id| Funds
    
    style Funds fill:#ffeb3b
    style MgmtCo fill:#ffeb3b
    style Clients fill:#4caf50
    style Accounts fill:#4caf50
    style Holdings fill:#2196f3
    style Transactions fill:#2196f3
    style FeeTransactions fill:#f44336
```

---

## 8. Embedding Collections Architecture

```mermaid
graph TB
    subgraph "ChromaDB In-Memory"
        subgraph "Schema Collection"
            S1[tables<br/>columns<br/>relationships]
        end
        
        subgraph "Dimension Collection"
            D1[fund_type values<br/>client names<br/>account codes]
        end
        
        subgraph "Context Collection"
            C1[business rules<br/>metrics<br/>sample queries]
        end
    end
    
    subgraph "Embedding Manager"
        EM[EmbeddingManager]
    end
    
    subgraph "OpenAI API"
        OA[text-embedding-3-small]
    end
    
    subgraph "Cache Layers"
        RC[Request Cache<br/>In-Memory]
        PC[Persistent Cache<br/>Redis]
    end
    
    EM -->|populate| S1
    EM -->|populate| D1
    EM -->|populate| C1
    
    EM -->|generate| OA
    EM -->|check| RC
    EM -->|check| PC
    
    OA -->|store| PC
    OA -->|store| RC
    
    style S1 fill:#e3f2fd
    style D1 fill:#f3e5f5
    style C1 fill:#fff9c4
```

---

## 9. SQL Generation Process

```mermaid
flowchart TD
    Start[Query Plan] --> SelectCols{Has<br/>Aggregations?}
    
    SelectCols -->|Yes| AggSelect[Build SELECT<br/>with AGG functions]
    SelectCols -->|No| SimpleSelect[Build SELECT<br/>with columns]
    
    AggSelect --> BaseTable[Identify<br/>Base Table]
    SimpleSelect --> BaseTable
    
    BaseTable --> CheckJoins{Joins<br/>Required?}
    
    CheckJoins -->|Yes| BuildJoins[Build JOIN<br/>clauses]
    CheckJoins -->|No| BuildWhere
    
    BuildJoins --> BuildWhere[Build WHERE<br/>clause]
    
    BuildWhere --> AutoFilters[Apply Auto<br/>Filters]
    
    AutoFilters --> CheckGroup{Has<br/>Aggregations?}
    
    CheckGroup -->|Yes| GroupBy[Add GROUP BY]
    CheckGroup -->|No| OrderBy
    
    GroupBy --> OrderBy{Has<br/>Ordering?}
    
    OrderBy -->|Yes| AddOrder[Add ORDER BY]
    OrderBy -->|No| CheckLimit
    
    AddOrder --> CheckLimit{Has<br/>Limit?}
    
    CheckLimit -->|Yes| AddLimit[Add LIMIT]
    CheckLimit -->|No| Validate
    
    AddLimit --> Validate[Validate SQL]
    
    Validate --> End[SQL Query]
    
    style Start fill:#e8f5e9
    style End fill:#c8e6c9
    style AggSelect fill:#fff9c4
    style BuildJoins fill:#fff9c4
    style AutoFilters fill:#ffccbc
    style Validate fill:#b2dfdb
```

---

## 10. Deployment Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        Browser[Web Browser]
        APIClient[API Client]
    end
    
    subgraph "Load Balancer (Optional)"
        LB[Nginx/HAProxy]
    end
    
    subgraph "Application Servers"
        subgraph "Server 1"
            API1[FastAPI<br/>:8000]
            UI1[Streamlit<br/>:8501]
        end
        
        subgraph "Server 2 (Future)"
            API2[FastAPI<br/>:8000]
            UI2[Streamlit<br/>:8501]
        end
    end
    
    subgraph "Data Services"
        PostgreSQL[(PostgreSQL<br/>:5432)]
        Redis[(Redis<br/>:6379)]
    end
    
    subgraph "External Services"
        OpenAI[OpenAI API]
        Gemini[Gemini API]
    end
    
    Browser --> LB
    APIClient --> LB
    
    LB --> API1
    LB --> UI1
    LB -.-> API2
    LB -.-> UI2
    
    API1 --> PostgreSQL
    API1 --> Redis
    API1 --> OpenAI
    API1 --> Gemini
    
    UI1 --> API1
    
    API2 -.-> PostgreSQL
    API2 -.-> Redis
    API2 -.-> OpenAI
    API2 -.-> Gemini
    
    UI2 -.-> API2
    
    style API1 fill:#4fc3f7
    style UI1 fill:#4fc3f7
    style API2 fill:#b0bec5
    style UI2 fill:#b0bec5
    style PostgreSQL fill:#f48fb1
    style Redis fill:#f48fb1
```

---

## 11. Security Architecture

```mermaid
graph TB
    subgraph "External"
        Client[Client]
    end
    
    subgraph "Security Layers"
        TLS[TLS/HTTPS<br/>Transport Security]
        Auth[Authentication<br/>API Keys/OAuth]
        AuthZ[Authorization<br/>RBAC]
        InputVal[Input Validation<br/>Sanitization]
        SQLInj[SQL Injection<br/>Prevention]
        Audit[Audit Logging<br/>All Queries]
    end
    
    subgraph "Application"
        API[FastAPI Server]
    end
    
    subgraph "Data"
        DB[(Database)]
    end
    
    Client --> TLS
    TLS --> Auth
    Auth --> AuthZ
    AuthZ --> InputVal
    InputVal --> API
    API --> SQLInj
    SQLInj --> DB
    
    API --> Audit
    
    style TLS fill:#c8e6c9
    style Auth fill:#c8e6c9
    style AuthZ fill:#c8e6c9
    style InputVal fill:#fff9c4
    style SQLInj fill:#ffccbc
    style Audit fill:#b2dfdb
```

---

## 12. Error Handling Flow

```mermaid
flowchart TD
    Start[Request] --> TryCatch{Try<br/>Execute}
    
    TryCatch -->|Success| Return[Return Result]
    TryCatch -->|Error| ErrorType{Error<br/>Type?}
    
    ErrorType -->|Config Error| LogConfig[Log Config Error]
    ErrorType -->|Intent Error| LogIntent[Log Intent Error]
    ErrorType -->|Schema Error| LogSchema[Log Schema Error]
    ErrorType -->|SQL Error| LogSQL[Log SQL Error]
    ErrorType -->|DB Error| LogDB[Log DB Error]
    
    LogConfig --> Retry{Retryable?}
    LogIntent --> Retry
    LogSchema --> Retry
    LogSQL --> Retry
    LogDB --> Retry
    
    Retry -->|Yes| Backoff[Exponential<br/>Backoff]
    Retry -->|No| Format[Format Error<br/>Response]
    
    Backoff --> TryCatch
    
    Format --> ReturnError[Return Error<br/>to Client]
    
    Return --> End[Done]
    ReturnError --> End
    
    style Start fill:#e8f5e9
    style Return fill:#c8e6c9
    style ReturnError fill:#ffcdd2
    style End fill:#e0e0e0
```

---

## 13. Monitoring and Observability

```mermaid
graph TB
    subgraph "Application"
        API[FastAPI Server]
        UI[Streamlit UI]
    end
    
    subgraph "Logging"
        AppLog[Application Logs<br/>logs/app.log]
        UILog[UI Logs<br/>logs/ui.log]
        DebugLog[Debug Logs<br/>logs/semantic_debug/]
    end
    
    subgraph "Metrics (Future)"
        Metrics[Prometheus<br/>Metrics]
        Dashboard[Grafana<br/>Dashboard]
    end
    
    subgraph "Health Checks"
        Health[/health endpoint]
        Ready[/ready endpoint]
    end
    
    subgraph "Monitoring System (Future)"
        Monitor[Monitoring Service<br/>Datadog/New Relic]
    end
    
    API --> AppLog
    API --> Metrics
    API --> Health
    API --> Ready
    
    UI --> UILog
    
    API --> DebugLog
    
    Metrics --> Dashboard
    
    AppLog --> Monitor
    UILog --> Monitor
    Metrics --> Monitor
    Health --> Monitor
    Ready --> Monitor
    
    style API fill:#4fc3f7
    style UI fill:#4fc3f7
    style Monitor fill:#ffb74d
```

---

## 14. Database Schema (Metadata)

```mermaid
erDiagram
    execution_sessions ||--o{ execution_steps : contains
    execution_sessions ||--o{ query_executions : contains
    
    execution_sessions {
        varchar session_id PK
        text original_query
        timestamp created_at
        timestamp completed_at
        varchar status
        integer total_duration_ms
        varchar request_id
        varchar user_id
    }
    
    execution_steps {
        serial step_id PK
        varchar session_id FK
        integer step_number
        varchar step_type
        varchar database_name
        text query_executed
        integer rows_examined
        integer rows_returned
        integer duration_ms
        varchar status
        text error_message
        timestamp created_at
    }
    
    query_executions {
        serial execution_id PK
        varchar session_id FK
        text sql_query
        varchar database_name
        integer execution_time_ms
        integer rows_returned
        varchar status
        text error_message
        timestamp created_at
    }
```

---

## 15. Configuration Management

```mermaid
graph TB
    subgraph "Configuration Files"
        AppYAML[app.yaml<br/>Application Config]
        SchemaYAML[schema.yaml<br/>Schema Definition]
        EntityYAML[entity_mappings.yaml<br/>Entity Mappings]
    end
    
    subgraph "Config Loader"
        Loader[ConfigLoader]
        Validator[YAMLValidator]
    end
    
    subgraph "In-Memory Structures"
        AppConfig[ApplicationConfig]
        SchemaConfig[SchemaConfig]
        EntityMap[EntityMappings]
    end
    
    subgraph "Consumers"
        KG[Knowledge Graph]
        Intent[Intent Analyzer]
        SQL[SQL Generator]
    end
    
    AppYAML --> Loader
    SchemaYAML --> Loader
    EntityYAML --> Loader
    
    Loader --> Validator
    
    Validator --> AppConfig
    Validator --> SchemaConfig
    Validator --> EntityMap
    
    AppConfig --> SQL
    SchemaConfig --> KG
    SchemaConfig --> SQL
    EntityMap --> Intent
    
    style Loader fill:#81c784
    style Validator fill:#ffb74d
```

---

## How to View These Diagrams

These diagrams are written in Mermaid syntax and can be viewed in:

1. **GitHub**: Automatically rendered in `.md` files
2. **VS Code**: Install "Markdown Preview Mermaid Support" extension
3. **Online**: Copy to https://mermaid.live/
4. **Documentation Sites**: Render with MkDocs, Docusaurus, etc.

---

**Document Control**  
**Version**: 1.0  
**Last Updated**: November 7, 2025  
**Author**: Development Team
