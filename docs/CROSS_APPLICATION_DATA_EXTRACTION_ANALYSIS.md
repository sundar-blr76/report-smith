# Cross-Application Data Extraction Analysis

**Document Version**: 1.0  
**Date**: November 10, 2025  
**Status**: Analysis Only - No Code Changes  
**Purpose**: Analyze approaches for extracting data across multiple applications hosted on different database servers

---

## 1. Executive Summary

This document analyzes the requirements, challenges, and implementation approaches for cross-application data extraction in ReportSmith when applications reside on different database servers. The analysis covers federation patterns, data integration strategies, and architectural recommendations.

### Key Findings

1. **Current State**: ReportSmith supports multi-database connections but processes queries against single applications
2. **Federation Requirement**: Need to join/aggregate data across applications on different servers
3. **Recommended Approach**: Hybrid strategy combining application-layer joins, federated queries, and materialized views
4. **Complexity**: High - requires query planning, execution coordination, and data consolidation across databases

---

## 2. Current Architecture Analysis

### 2.1 Current Database Capabilities

ReportSmith currently supports:

#### Multi-Database Connection Support
- **Location**: `src/reportsmith/database/connection_manager.py`
- **Capability**: Can connect to multiple database types (PostgreSQL, MySQL, Oracle, SQL Server, SQLite)
- **Connection Pooling**: Yes, via SQLAlchemy with configurable pool sizes
- **Concurrent Connections**: Yes, thread-safe connection management

#### Configuration System
- **Location**: `config/applications/{app}/instances/{instance}.yaml`
- **Structure**: Each application has:
  - Application config (`app.yaml`) - business logic, relationships, metrics
  - Instance configs - connection details per database instance
  - Schema definitions - table/column metadata

#### Query Processing
- **Single Application Queries**: Fully supported
- **Cross-Application Queries**: **NOT CURRENTLY SUPPORTED**
- **Join Logic**: Knowledge graph builds joins within single application only

### 2.2 Architecture Gaps for Cross-Application Queries

| Capability | Current State | Required for Cross-App |
|------------|---------------|----------------------|
| Multi-DB connections | ✅ Supported | ✅ Already available |
| Cross-DB join planning | ❌ Not available | ✅ Required |
| Data federation layer | ❌ Not available | ✅ Required |
| Cross-DB query execution | ❌ Not available | ✅ Required |
| Result merging | ❌ Not available | ✅ Required |
| Transaction coordination | ❌ Not available | ⚠️ Optional (depends on use case) |

---

## 3. Use Cases for Cross-Application Data Extraction

### 3.1 Common Scenarios

#### Scenario 1: Client Portfolio Across Regions
**Business Need**: Get consolidated view of client holdings across APAC, EMEA, and Americas databases

**Example Query**:
```
"Show total AUM for client C001 across all regions"
```

**Technical Requirements**:
- Connect to 3 database servers (APAC_DB, EMEA_DB, AMERICAS_DB)
- Query `clients` and `holdings` tables in each
- Aggregate results by client
- Handle currency conversion if needed

#### Scenario 2: Cross-System Performance Reporting
**Business Need**: Combine fund performance from accounting system with market data from trading system

**Example Query**:
```
"Show fund returns with corresponding benchmark performance from market data"
```

**Technical Requirements**:
- Connect to fund_accounting_db and market_data_db
- Join funds table with benchmarks table across databases
- Match on fund identifier (may differ across systems)
- Handle temporal alignment (ensure same date ranges)

#### Scenario 3: Compliance Reporting Across Applications
**Business Need**: Generate compliance report combining client data, transactions, and regulatory filings

**Example Query**:
```
"List clients with transactions over $1M who are missing regulatory filings"
```

**Technical Requirements**:
- Connect to client_management_db, transaction_db, compliance_db
- Join across 3 databases
- Apply complex business rules
- Aggregate and filter results

---

## 4. Technical Approaches

### 4.1 Approach 1: Application-Layer Joins (Recommended for Initial Implementation)

#### Description
Execute separate queries against each database, retrieve results to application layer, then join/merge in memory.

#### How It Works
```
1. Query Decomposition:
   User query → Identify involved applications → Split into sub-queries
   
2. Parallel Execution:
   Execute sub-queries concurrently against each database
   
3. In-Memory Join:
   Load results into DataFrames → Join on common keys → Aggregate/filter
   
4. Result Formatting:
   Format combined results → Return to user
```

#### Advantages
- ✅ **Simple to implement** - No database-specific federation features required
- ✅ **Works with any database** - Database-agnostic approach
- ✅ **Full control** - Application controls join logic and optimization
- ✅ **No database modifications** - Works with existing databases as-is
- ✅ **Better error handling** - Can handle partial failures gracefully

#### Disadvantages
- ❌ **Memory intensive** - All data loaded into application memory
- ❌ **Network overhead** - Large datasets transferred over network
- ❌ **No DB optimization** - Can't leverage database query optimizer for joins
- ❌ **Limited scalability** - Performance degrades with large datasets
- ❌ **Latency** - Multiple round trips to different databases

#### Best For
- Small to medium datasets (<100K rows per table)
- Complex cross-database logic
- Heterogeneous database types
- Initial implementation/MVP

#### Implementation Considerations

**Query Planning**:
```python
# Pseudo-code for query decomposition
def plan_cross_app_query(user_query):
    # 1. Identify involved applications
    applications = identify_applications(user_query)
    
    # 2. For each application, generate sub-query
    sub_queries = []
    for app in applications:
        sub_query = generate_sub_query(user_query, app)
        sub_queries.append((app, sub_query))
    
    # 3. Identify join keys
    join_plan = identify_join_keys(applications)
    
    # 4. Identify aggregation requirements
    agg_plan = identify_aggregations(user_query)
    
    return ExecutionPlan(sub_queries, join_plan, agg_plan)
```

**Execution Strategy**:
```python
# Pseudo-code for execution
def execute_cross_app_query(execution_plan):
    # 1. Execute sub-queries in parallel
    results = {}
    with ThreadPoolExecutor() as executor:
        futures = []
        for app, sub_query in execution_plan.sub_queries:
            future = executor.submit(execute_query, app, sub_query)
            futures.append((app, future))
        
        for app, future in futures:
            results[app] = future.result()
    
    # 2. Join results
    df1 = pd.DataFrame(results['app1'])
    df2 = pd.DataFrame(results['app2'])
    joined = pd.merge(df1, df2, on=execution_plan.join_keys)
    
    # 3. Apply aggregations
    final = apply_aggregations(joined, execution_plan.agg_plan)
    
    return final
```

---

### 4.2 Approach 2: Database Link / Foreign Data Wrapper

#### Description
Use database-native federation features (Oracle DB Links, PostgreSQL FDW, SQL Server Linked Servers) to query remote databases.

#### How It Works
```
1. Setup Phase:
   Configure foreign data wrappers/links in primary database
   
2. Query Execution:
   Write SQL joining local and remote tables
   Database handles remote query execution
   
3. Result Return:
   Database returns joined results directly
```

#### Advantages
- ✅ **Database optimized** - Query optimizer handles join strategy
- ✅ **Transparent joins** - SQL looks like normal joins
- ✅ **Reduced network** - Only final results returned
- ✅ **Familiar SQL** - Standard SQL syntax

#### Disadvantages
- ❌ **Database specific** - Different setup for each database type
- ❌ **Requires configuration** - Need DB admin access to setup links
- ❌ **Security concerns** - Credential management across databases
- ❌ **Limited flexibility** - Bound by database capabilities
- ❌ **Performance variability** - Depends on database optimizer
- ❌ **Heterogeneous limitations** - Cross-vendor support varies

#### PostgreSQL Foreign Data Wrapper (FDW) Example
```sql
-- Setup (one-time)
CREATE EXTENSION postgres_fdw;

CREATE SERVER apac_server
  FOREIGN DATA WRAPPER postgres_fdw
  OPTIONS (host 'apac-db.example.com', dbname 'fund_accounting', port '5432');

CREATE USER MAPPING FOR local_user
  SERVER apac_server
  OPTIONS (user 'remote_user', password 'remote_pass');

CREATE FOREIGN TABLE apac_funds (
  fund_id INTEGER,
  fund_code VARCHAR(50),
  total_aum NUMERIC
) SERVER apac_server
  OPTIONS (schema_name 'public', table_name 'funds');

-- Query
SELECT 
  local.client_code,
  apac.fund_code,
  apac.total_aum
FROM local_clients local
JOIN apac_funds apac ON local.default_fund_id = apac.fund_id;
```

#### Best For
- Same database type across instances (e.g., all PostgreSQL)
- Small number of foreign databases
- Trusted network environment
- Performance-critical queries with large datasets

---

### 4.3 Approach 3: Materialized Views / Data Replication

#### Description
Replicate data from remote databases into local staging tables, then query locally.

#### How It Works
```
1. Replication Phase (scheduled):
   Extract data from remote databases
   Load into local staging schema
   
2. Query Execution:
   Query local staging tables only
   All joins happen locally
   
3. Refresh Strategy:
   Incremental updates or full refresh based on requirements
```

#### Advantages
- ✅ **Best performance** - All queries local, no remote calls
- ✅ **Consistency** - Snapshot consistency within refresh window
- ✅ **Simple queries** - Standard local joins
- ✅ **Database agnostic** - Works across any database types
- ✅ **Reduced load** - Less load on source databases

#### Disadvantages
- ❌ **Data staleness** - Data only as fresh as last refresh
- ❌ **Storage overhead** - Duplicate data storage
- ❌ **Complex ETL** - Need robust replication pipeline
- ❌ **Maintenance** - Need to manage refresh jobs
- ❌ **Not real-time** - Can't support real-time queries

#### Implementation Pattern
```python
# Pseudo-code for materialized view pattern
class CrossAppMaterializer:
    def __init__(self):
        self.staging_db = get_staging_database()
    
    def refresh_materialized_views(self, schedule='daily'):
        """Scheduled job to refresh cross-app views"""
        for app in applications:
            # Extract from source
            data = extract_data(app, last_sync_time)
            
            # Transform if needed
            transformed = transform_data(data, app)
            
            # Load to staging
            load_to_staging(self.staging_db, transformed, app)
            
            # Update sync timestamp
            update_sync_time(app)
    
    def query_materialized_views(self, user_query):
        """Query against local staging tables"""
        sql = generate_sql(user_query, use_staging=True)
        results = execute_local_query(self.staging_db, sql)
        return results
```

#### Best For
- Analytical/reporting queries (not transactional)
- Data that doesn't change frequently
- Large datasets where performance is critical
- Scenarios where eventual consistency is acceptable

---

### 4.4 Approach 4: Federated Query Engine / Data Virtualization

#### Description
Use specialized federated query engine (Apache Drill, Presto, Trino, Dremio) that can query multiple databases transparently.

#### How It Works
```
1. Configuration:
   Configure federated engine with data source connections
   
2. Query Submission:
   Submit SQL to federated engine
   
3. Query Planning:
   Federated engine plans optimal execution across sources
   
4. Execution:
   Engine executes sub-queries, joins results, returns
```

#### Advantages
- ✅ **Purpose-built** - Designed for cross-database queries
- ✅ **Optimized execution** - Smart query planning and pushdown
- ✅ **Scalable** - Can handle large-scale federation
- ✅ **Standard SQL** - SQL interface
- ✅ **Caching** - Built-in result caching

#### Disadvantages
- ❌ **Additional component** - New infrastructure to manage
- ❌ **Complexity** - Learning curve and operational overhead
- ❌ **Cost** - Commercial solutions can be expensive
- ❌ **Latency** - Additional hop in query path
- ❌ **Dependencies** - Another point of failure

#### Example with Presto
```sql
-- Configure catalogs in Presto
-- catalog/apac.properties
connector.name=postgresql
connection-url=jdbc:postgresql://apac-db:5432/fund_accounting
connection-user=user
connection-password=pass

-- catalog/emea.properties
connector.name=postgresql
connection-url=jdbc:postgresql://emea-db:5432/fund_accounting
connection-user=user
connection-password=pass

-- Query
SELECT 
  a.client_code,
  a.region,
  a.total_aum as apac_aum,
  e.total_aum as emea_aum,
  (a.total_aum + e.total_aum) as total_aum
FROM apac.public.clients a
FULL OUTER JOIN emea.public.clients e 
  ON a.client_code = e.client_code;
```

#### Best For
- Large-scale data federation
- Organizations already using federated engines
- Complex cross-database analytics
- When performance and scalability are critical

---

## 5. Recommended Architecture for ReportSmith

### 5.1 Phased Implementation Approach

#### Phase 1: Application-Layer Joins (Immediate - 2-4 weeks)
**Scope**: Support basic cross-application queries for small to medium datasets

**Components to Build**:
1. **Cross-App Query Analyzer**
   - Identify which applications are involved in query
   - Determine if cross-app query is feasible
   
2. **Query Decomposer**
   - Split user query into per-application sub-queries
   - Identify join keys and join types
   
3. **Parallel Executor**
   - Execute sub-queries concurrently
   - Collect results from multiple databases
   
4. **Result Merger**
   - Join/merge results in application memory
   - Apply aggregations and filters
   - Handle data type conversions
   
5. **Enhanced Knowledge Graph**
   - Extend to support cross-application relationships
   - Define canonical keys for joining across apps

**Limitations**:
- Dataset size limits (recommend <100K rows per table)
- Increased latency for complex queries
- Memory constraints on application server

#### Phase 2: Intelligent Optimization (3-6 months)
**Scope**: Optimize query execution with smart strategies

**Enhancements**:
1. **Query Optimizer**
   - Estimate result sizes and choose execution strategy
   - Push down filters to reduce data transfer
   - Decide whether to use app-layer join or federation
   
2. **Caching Layer**
   - Cache cross-app query results
   - Intelligent cache invalidation
   
3. **Data Sampling**
   - For large datasets, sample first to estimate results
   - Warn users about large data transfers
   
4. **Incremental Processing**
   - For very large results, support pagination
   - Stream results rather than load all in memory

#### Phase 3: Hybrid Federation (6-12 months)
**Scope**: Add database federation options for performance-critical queries

**Capabilities**:
1. **FDW Integration** (for PostgreSQL instances)
   - Auto-configure foreign data wrappers
   - Use FDW for same-vendor cross-db queries
   
2. **Materialized Views** (for analytical queries)
   - Identify common cross-app query patterns
   - Auto-create and refresh materialized views
   - Query optimizer chooses between live and materialized
   
3. **External Federation Engine** (optional)
   - Integration with Presto/Trino if needed
   - For very large-scale federation

---

### 5.2 Proposed Architecture Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                    User Interface Layer                        │
│  ┌──────────────────┐              ┌──────────────────┐       │
│  │  Streamlit UI    │              │   FastAPI        │       │
│  └──────────────────┘              └──────────────────┘       │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────┐
│               LangGraph Orchestration Layer                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Intent Analysis → Schema Mapping → Query Planning       │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────┐
│            NEW: Cross-Application Query Layer                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Cross-App Query Analyzer                                │  │
│  │  • Detect multi-app queries                              │  │
│  │  • Identify involved applications                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Query Decomposer                                        │  │
│  │  • Split into sub-queries per app                        │  │
│  │  • Identify join keys and strategy                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Execution Coordinator                                   │  │
│  │  • Parallel sub-query execution                          │  │
│  │  • Result collection and merging                         │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────┐
│              Existing: Database Connection Layer                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Connection Manager (already supports multi-DB)          │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬───────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┬──────────────┐
        │                │                │              │
        ▼                ▼                ▼              ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  APAC DB     │  │  EMEA DB     │  │  Americas DB │  │  Market Data │
│  PostgreSQL  │  │  PostgreSQL  │  │  Oracle      │  │  SQL Server  │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

---

## 6. Implementation Details for Phase 1

### 6.1 Cross-Application Configuration

#### Enhanced Application Config
```yaml
# config/applications/fund_accounting/app.yaml

application:
  id: fund_accounting
  name: Fund Accounting System
  
# NEW: Cross-app relationships
cross_application_relationships:
  - related_app: market_data
    relationship_type: reference
    join_mappings:
      - local_table: funds
        local_key: isin_code
        remote_table: securities
        remote_key: isin
        description: "Join fund to market data via ISIN"
  
  - related_app: client_management
    relationship_type: reference
    join_mappings:
      - local_table: accounts
        local_key: client_id
        remote_table: clients
        remote_key: client_id
        description: "Join accounts to client master"
```

#### Cross-App Entity Mappings
```yaml
# config/cross_app_entity_mappings.yaml

cross_application_entities:
  client_portfolio:
    description: "Client portfolio across all regions"
    applications:
      - fund_accounting_apac
      - fund_accounting_emea
      - fund_accounting_americas
    join_strategy:
      type: union_all
      key: client_code
    example_query: "Show total AUM for client C001 across all regions"
  
  fund_performance:
    description: "Fund performance with market benchmarks"
    applications:
      - fund_accounting
      - market_data
    join_strategy:
      type: inner_join
      keys:
        - fund_accounting.funds.isin_code = market_data.securities.isin
    example_query: "Show fund returns with benchmark performance"
```

---

### 6.2 Query Decomposition Logic

```python
# src/reportsmith/query_processing/cross_app_query_decomposer.py

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from reportsmith.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SubQuery:
    """Sub-query to execute against single application"""
    application_id: str
    instance_id: str
    sql: str
    estimated_rows: int
    required_columns: List[str]


@dataclass
class JoinSpec:
    """Specification for joining results"""
    left_app: str
    right_app: str
    left_key: str
    right_key: str
    join_type: str  # inner, left, right, full
    

@dataclass
class CrossAppExecutionPlan:
    """Execution plan for cross-application query"""
    sub_queries: List[SubQuery]
    join_specs: List[JoinSpec]
    aggregations: List[Dict[str, Any]]
    filters: List[Dict[str, Any]]
    order_by: List[str]
    limit: int


class CrossAppQueryDecomposer:
    """Decomposes cross-app queries into sub-queries"""
    
    def __init__(self, config_loader, knowledge_graph):
        self.config = config_loader
        self.kg = knowledge_graph
    
    def is_cross_app_query(self, entities: List[Dict]) -> bool:
        """Determine if query involves multiple applications"""
        apps = set()
        for entity in entities:
            if 'application_id' in entity:
                apps.add(entity['application_id'])
        
        is_cross_app = len(apps) > 1
        if is_cross_app:
            logger.info(f"[cross_app] Detected cross-app query involving: {apps}")
        
        return is_cross_app
    
    def decompose(self, query_intent: Dict, entities: List[Dict]) -> CrossAppExecutionPlan:
        """
        Decompose cross-app query into execution plan
        
        Args:
            query_intent: Intent extracted from user query
            entities: Entities identified in query
        
        Returns:
            CrossAppExecutionPlan
        """
        logger.info("[cross_app] Decomposing cross-application query")
        
        # 1. Group entities by application
        entities_by_app = self._group_entities_by_app(entities)
        
        # 2. Identify join keys from cross-app relationships
        join_specs = self._identify_join_keys(entities_by_app)
        
        # 3. Generate sub-query for each application
        sub_queries = []
        for app_id, app_entities in entities_by_app.items():
            sub_query = self._generate_sub_query(
                app_id, 
                app_entities, 
                query_intent,
                join_specs
            )
            sub_queries.append(sub_query)
        
        # 4. Identify aggregations (if any)
        aggregations = query_intent.get('aggregations', [])
        
        # 5. Identify filters to apply after join
        post_join_filters = self._identify_post_join_filters(query_intent)
        
        # 6. Create execution plan
        plan = CrossAppExecutionPlan(
            sub_queries=sub_queries,
            join_specs=join_specs,
            aggregations=aggregations,
            filters=post_join_filters,
            order_by=query_intent.get('order_by', []),
            limit=query_intent.get('limit', 1000)
        )
        
        logger.info(f"[cross_app] Generated execution plan with {len(sub_queries)} sub-queries")
        return plan
    
    def _group_entities_by_app(self, entities: List[Dict]) -> Dict[str, List[Dict]]:
        """Group entities by application"""
        by_app = {}
        for entity in entities:
            app_id = entity.get('application_id', 'default')
            if app_id not in by_app:
                by_app[app_id] = []
            by_app[app_id].append(entity)
        
        return by_app
    
    def _identify_join_keys(self, entities_by_app: Dict) -> List[JoinSpec]:
        """Identify how to join results from different applications"""
        join_specs = []
        apps = list(entities_by_app.keys())
        
        # Check for configured cross-app relationships
        for i, app1 in enumerate(apps):
            for app2 in apps[i+1:]:
                # Look up cross-app relationship config
                relationship = self._find_cross_app_relationship(app1, app2)
                
                if relationship:
                    join_spec = JoinSpec(
                        left_app=app1,
                        right_app=app2,
                        left_key=relationship['left_key'],
                        right_key=relationship['right_key'],
                        join_type=relationship.get('join_type', 'inner')
                    )
                    join_specs.append(join_spec)
                    logger.info(f"[cross_app] Found join: {app1}.{relationship['left_key']} = {app2}.{relationship['right_key']}")
        
        return join_specs
    
    def _find_cross_app_relationship(self, app1: str, app2: str) -> Dict:
        """Look up cross-app relationship from configuration"""
        # This would load from config/cross_app_entity_mappings.yaml
        # Placeholder for now
        
        # Example hardcoded relationships
        relationships = {
            ('fund_accounting_apac', 'fund_accounting_emea'): {
                'left_key': 'client_code',
                'right_key': 'client_code',
                'join_type': 'full'
            },
            ('fund_accounting', 'market_data'): {
                'left_key': 'isin_code',
                'right_key': 'isin',
                'join_type': 'inner'
            }
        }
        
        return relationships.get((app1, app2)) or relationships.get((app2, app1))
    
    def _generate_sub_query(
        self, 
        app_id: str, 
        entities: List[Dict],
        intent: Dict,
        join_specs: List[JoinSpec]
    ) -> SubQuery:
        """Generate SQL sub-query for single application"""
        
        # Identify required columns (include join keys)
        required_columns = []
        for entity in entities:
            if entity.get('column'):
                required_columns.append(entity['column'])
        
        # Add join keys to required columns
        for join_spec in join_specs:
            if join_spec.left_app == app_id:
                required_columns.append(join_spec.left_key)
            elif join_spec.right_app == app_id:
                required_columns.append(join_spec.right_key)
        
        # Build SELECT clause
        select_cols = ', '.join(set(required_columns))
        
        # Build FROM clause (simplified - would use SQL generator in practice)
        tables = list(set([e['table'] for e in entities if 'table' in e]))
        from_clause = tables[0] if tables else 'unknown'
        
        # Build WHERE clause (push down filters)
        where_conditions = []
        for entity in entities:
            if entity.get('filter_value'):
                where_conditions.append(f"{entity['column']} = '{entity['filter_value']}'")
        
        where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""
        
        # Construct SQL
        sql = f"SELECT {select_cols} FROM {from_clause} {where_clause}"
        
        return SubQuery(
            application_id=app_id,
            instance_id=f"{app_id}_default",  # Would look up from config
            sql=sql,
            estimated_rows=10000,  # Would estimate from statistics
            required_columns=required_columns
        )
    
    def _identify_post_join_filters(self, intent: Dict) -> List[Dict]:
        """Identify filters to apply after joining results"""
        # Filters that involve columns from multiple apps must be applied post-join
        # This is a simplified version
        return intent.get('filters', [])
```

---

### 6.3 Cross-App Execution Coordinator

```python
# src/reportsmith/query_execution/cross_app_executor.py

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List
import pandas as pd
from reportsmith.logger import get_logger
from reportsmith.database.connection_manager import DatabaseConnectionManager
from reportsmith.query_processing.cross_app_query_decomposer import CrossAppExecutionPlan

logger = get_logger(__name__)


class CrossAppExecutor:
    """Executes cross-application queries"""
    
    def __init__(self, connection_manager: DatabaseConnectionManager):
        self.conn_mgr = connection_manager
        self.max_workers = 5  # Concurrent query limit
    
    def execute(self, execution_plan: CrossAppExecutionPlan) -> Dict[str, Any]:
        """
        Execute cross-app query plan
        
        Args:
            execution_plan: CrossAppExecutionPlan
        
        Returns:
            Query results
        """
        logger.info(f"[cross_app] Executing cross-app query with {len(execution_plan.sub_queries)} sub-queries")
        
        # 1. Execute sub-queries in parallel
        sub_results = self._execute_sub_queries_parallel(execution_plan.sub_queries)
        
        # 2. Join results
        if len(sub_results) == 1:
            # Single app query (shouldn't happen but handle it)
            merged = list(sub_results.values())[0]
        else:
            merged = self._join_results(sub_results, execution_plan.join_specs)
        
        # 3. Apply post-join filters
        if execution_plan.filters:
            merged = self._apply_filters(merged, execution_plan.filters)
        
        # 4. Apply aggregations
        if execution_plan.aggregations:
            merged = self._apply_aggregations(merged, execution_plan.aggregations)
        
        # 5. Apply ordering and limit
        if execution_plan.order_by:
            merged = self._apply_ordering(merged, execution_plan.order_by)
        
        if execution_plan.limit:
            merged = merged.head(execution_plan.limit)
        
        # 6. Convert to result format
        result = {
            'columns': list(merged.columns),
            'rows': merged.to_dict('records'),
            'row_count': len(merged),
            'truncated': False
        }
        
        logger.info(f"[cross_app] Query completed, returned {len(merged)} rows")
        return result
    
    def _execute_sub_queries_parallel(self, sub_queries) -> Dict[str, pd.DataFrame]:
        """Execute sub-queries in parallel"""
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all sub-queries
            future_to_app = {}
            for sub_query in sub_queries:
                future = executor.submit(
                    self._execute_single_query,
                    sub_query.instance_id,
                    sub_query.sql
                )
                future_to_app[future] = sub_query.application_id
            
            # Collect results as they complete
            for future in as_completed(future_to_app):
                app_id = future_to_app[future]
                try:
                    df = future.result()
                    results[app_id] = df
                    logger.info(f"[cross_app] Sub-query for {app_id} returned {len(df)} rows")
                except Exception as e:
                    logger.error(f"[cross_app] Sub-query failed for {app_id}: {e}")
                    raise
        
        return results
    
    def _execute_single_query(self, instance_id: str, sql: str) -> pd.DataFrame:
        """Execute single query and return as DataFrame"""
        with self.conn_mgr.get_connection(instance_id) as conn:
            df = pd.read_sql(sql, conn)
            return df
    
    def _join_results(self, sub_results: Dict[str, pd.DataFrame], join_specs) -> pd.DataFrame:
        """Join results from multiple applications"""
        logger.info(f"[cross_app] Joining results from {len(sub_results)} applications")
        
        # Start with first dataframe
        apps = list(sub_results.keys())
        merged = sub_results[apps[0]]
        merged_apps = {apps[0]}
        
        # Iteratively join with other dataframes
        for join_spec in join_specs:
            left_app = join_spec.left_app
            right_app = join_spec.right_app
            
            # Determine which one we already have
            if left_app in merged_apps and right_app not in merged_apps:
                # Join right to current merged
                right_df = sub_results[right_app]
                merged = pd.merge(
                    merged,
                    right_df,
                    left_on=join_spec.left_key,
                    right_on=join_spec.right_key,
                    how=join_spec.join_type,
                    suffixes=('', f'_{right_app}')
                )
                merged_apps.add(right_app)
                logger.info(f"[cross_app] Joined {right_app}, result size: {len(merged)} rows")
            
            elif right_app in merged_apps and left_app not in merged_apps:
                # Join left to current merged
                left_df = sub_results[left_app]
                merged = pd.merge(
                    left_df,
                    merged,
                    left_on=join_spec.left_key,
                    right_on=join_spec.right_key,
                    how=join_spec.join_type,
                    suffixes=(f'_{left_app}', '')
                )
                merged_apps.add(left_app)
                logger.info(f"[cross_app] Joined {left_app}, result size: {len(merged)} rows")
        
        return merged
    
    def _apply_filters(self, df: pd.DataFrame, filters: List[Dict]) -> pd.DataFrame:
        """Apply filters to dataframe"""
        for filter_spec in filters:
            # Simplified - would need more robust filter parsing
            column = filter_spec['column']
            operator = filter_spec.get('operator', '=')
            value = filter_spec['value']
            
            if operator == '=':
                df = df[df[column] == value]
            elif operator == '>':
                df = df[df[column] > value]
            # ... more operators
        
        return df
    
    def _apply_aggregations(self, df: pd.DataFrame, aggregations: List[Dict]) -> pd.DataFrame:
        """Apply aggregations to dataframe"""
        # Simplified - would need more robust aggregation logic
        agg_funcs = {}
        for agg in aggregations:
            column = agg['column']
            func = agg['function']  # sum, avg, count, etc.
            agg_funcs[column] = func
        
        group_by = aggregations[0].get('group_by', [])
        if group_by:
            df = df.groupby(group_by).agg(agg_funcs).reset_index()
        else:
            df = df.agg(agg_funcs).to_frame().T
        
        return df
    
    def _apply_ordering(self, df: pd.DataFrame, order_by: List[str]) -> pd.DataFrame:
        """Apply ordering to dataframe"""
        # Simplified - would parse ASC/DESC
        return df.sort_values(order_by)
```

---

## 7. Challenges and Mitigation Strategies

### 7.1 Technical Challenges

| Challenge | Impact | Mitigation Strategy |
|-----------|--------|-------------------|
| **Data Volume** | Large datasets cause memory issues | • Implement row limits<br>• Add data sampling<br>• Stream results<br>• Warn users |
| **Network Latency** | Multiple DB calls increase latency | • Parallel execution<br>• Connection pooling<br>• Result caching<br>• Push down filters |
| **Join Key Mismatch** | Different identifiers across systems | • Canonical key mapping<br>• Fuzzy matching<br>• LLM-based entity resolution |
| **Data Type Differences** | Type conflicts in joins | • Type conversion rules<br>• Schema normalization<br>• Validation before join |
| **Transaction Consistency** | Data changes during query | • Document eventual consistency<br>• Snapshot isolation (where possible)<br>• Timestamp all queries |
| **Error Handling** | Partial failures | • Graceful degradation<br>• Retry logic<br>• Return partial results with warnings |
| **Security** | Cross-database access control | • Application-level RBAC<br>• Audit all cross-app queries<br>• Principle of least privilege |

### 7.2 Query Planning Challenges

**Challenge: Identifying Join Keys**
- User asks "Show client portfolios across regions"
- Need to identify that `client_code` is the join key
- Different apps may use different column names

**Solution**:
- Maintain cross-app entity mapping config
- Use LLM to infer join relationships
- Learn from successful queries

**Challenge: Optimizing Execution Order**
- Which sub-query to execute first?
- How to minimize data transfer?

**Solution**:
- Estimate result sizes
- Execute most selective queries first
- Push filters down to databases
- Consider data locality

---

## 8. Performance Considerations

### 8.1 Latency Analysis

**Single Application Query (Current)**:
- Intent Analysis: 250ms
- Schema Mapping: 50ms
- SQL Generation: 1ms
- Execution: 500ms
- **Total: ~800ms**

**Cross-Application Query (Estimated)**:
- Intent Analysis: 250ms
- Cross-App Planning: 200ms (new)
- Sub-query Generation: 10ms
- Parallel Execution: 800ms (3 DBs in parallel, ~max 800ms)
- Result Merging: 100ms (new)
- Post-processing: 50ms (new)
- **Total: ~1.4s**

**Overhead**: ~600ms (75% increase)

### 8.2 Optimization Strategies

1. **Query Result Caching**
   - Cache cross-app query results (TTL: 5-30 minutes)
   - 100% speedup on cache hits
   
2. **Materialized Views** (for common patterns)
   - Pre-compute common cross-app joins
   - Query materialized view instead of live data
   
3. **Intelligent Filter Pushdown**
   - Push as many filters as possible to source databases
   - Reduce data transfer and memory usage
   
4. **Connection Pool Warming**
   - Keep connections to frequently used DBs warm
   - Avoid connection setup overhead
   
5. **Parallel Execution**
   - Already planned in design
   - Use ThreadPoolExecutor for I/O-bound operations

---

## 9. Security and Governance

### 9.1 Access Control

**Challenges**:
- User has access to App A but not App B
- Cross-app query joins data from both

**Approach**:
1. **Application-level RBAC**
   - Check user permissions for ALL involved applications
   - Reject query if user lacks access to any application
   
2. **Column-level Security**
   - Mask sensitive columns user doesn't have access to
   - Apply data masking rules per application

3. **Row-level Security**
   - Filter rows based on user's data access rules
   - Apply filters from each application separately

### 9.2 Audit and Compliance

**Requirements**:
- Log all cross-app queries with user identity
- Track which databases were accessed
- Record data lineage for compliance

**Implementation**:
```python
def audit_cross_app_query(user_id, query, applications, results):
    audit_log = {
        'timestamp': datetime.now(),
        'user_id': user_id,
        'query_type': 'cross_application',
        'user_query': query,
        'applications_accessed': applications,
        'database_instances': [app['instance'] for app in applications],
        'row_count': len(results),
        'execution_time_ms': results['execution_time']
    }
    
    # Write to audit database
    write_audit_log(audit_log)
    
    # Alert on sensitive data access (if configured)
    if involves_sensitive_data(applications):
        send_alert(audit_log)
```

---

## 10. Configuration and Deployment

### 10.1 Required Configuration Changes

**New Configuration Files**:

1. `config/cross_app_entity_mappings.yaml`
   - Cross-application entity definitions
   - Join key mappings
   - Query patterns

2. `config/cross_app_rules.yaml`
   - Access control rules
   - Data size limits
   - Performance budgets

3. Per-application updates to `app.yaml`:
   - Add cross_application_relationships section

### 10.2 Deployment Considerations

**Network**:
- Ensure application server can reach all database servers
- Configure firewalls to allow connections
- Consider network latency between regions

**Resource Requirements**:
- Increased memory for result merging
- More CPU for parallel execution
- Additional connection pool capacity

**Monitoring**:
- Add metrics for cross-app queries
- Track sub-query execution times
- Monitor memory usage during joins

---

## 11. Testing Strategy

### 11.1 Test Scenarios

**Functional Tests**:
1. Simple cross-app join (2 apps, inner join)
2. Multi-app join (3+ apps)
3. Cross-app aggregation
4. Cross-app with filtering
5. Error handling (DB unavailable)
6. Partial failure scenarios

**Performance Tests**:
1. Small datasets (100 rows per app)
2. Medium datasets (10K rows per app)
3. Large datasets (100K+ rows per app)
4. Network latency simulation
5. Concurrent cross-app queries

**Security Tests**:
1. Access control enforcement
2. Data masking verification
3. Audit log completeness

### 11.2 Test Data Setup

```sql
-- APAC Database
INSERT INTO clients (client_code, name, region, aum)
VALUES ('C001', 'Client APAC', 'APAC', 1000000);

-- EMEA Database
INSERT INTO clients (client_code, name, region, aum)
VALUES ('C001', 'Client EMEA', 'EMEA', 2000000);

-- Expected Result after Cross-App Query
SELECT 
  client_code,
  SUM(aum) as total_aum
FROM (
  SELECT * FROM apac_clients
  UNION ALL
  SELECT * FROM emea_clients
)
GROUP BY client_code;

-- Should return: C001, 3000000
```

---

## 12. Rollout Plan

### 12.1 Phase 1: Foundation (Weeks 1-2)
- [x] Document requirements (this document)
- [ ] Design API interfaces
- [ ] Create configuration schema
- [ ] Set up test environments

### 12.2 Phase 2: Core Implementation (Weeks 3-6)
- [ ] Implement CrossAppQueryDecomposer
- [ ] Implement CrossAppExecutor
- [ ] Add cross-app relationships to knowledge graph
- [ ] Create configuration files
- [ ] Unit tests for core components

### 12.3 Phase 3: Integration (Weeks 7-8)
- [ ] Integrate with LangGraph orchestrator
- [ ] Add cross-app detection to intent analyzer
- [ ] Update SQL generator for sub-queries
- [ ] Integration testing

### 12.4 Phase 4: Optimization (Weeks 9-10)
- [ ] Add result caching
- [ ] Implement filter pushdown optimization
- [ ] Performance testing and tuning
- [ ] Add monitoring and metrics

### 12.5 Phase 5: Production Rollout (Weeks 11-12)
- [ ] Beta testing with limited users
- [ ] Documentation and training
- [ ] Production deployment
- [ ] Monitor and iterate

---

## 13. Alternatives Considered

### 13.1 ETL + Data Warehouse Approach
**Description**: Extract all data to central warehouse, query warehouse only

**Pros**: 
- Single source of truth
- Best query performance
- Consistent data model

**Cons**:
- High initial setup cost
- Data staleness
- Storage costs
- ETL maintenance burden

**Decision**: Not chosen as initial approach due to complexity and timeline

### 13.2 API-Based Federation
**Description**: Expose REST APIs per application, call APIs and merge in application

**Pros**:
- Service-oriented architecture
- Clear API contracts
- Independent scaling

**Cons**:
- Higher latency (HTTP overhead)
- More complex for SQL-like queries
- API versioning challenges

**Decision**: Not chosen; direct database access is more efficient for reporting

### 13.3 Federated Query Engine (Presto/Trino)
**Description**: Use purpose-built federated query engine

**Pros**:
- Purpose-built for this use case
- Handles optimization automatically
- Scalable

**Cons**:
- Additional infrastructure
- Operational complexity
- Cost

**Decision**: Consider for Phase 3 if needed; overkill for initial implementation

---

## 14. Success Metrics

### 14.1 Functional Success Criteria
- ✅ Can execute queries across 2+ applications
- ✅ Correct join logic and results
- ✅ Proper error handling for failures
- ✅ Access control enforced
- ✅ Complete audit trail

### 14.2 Performance Success Criteria
- ✅ Cross-app queries complete in <5 seconds for datasets <10K rows
- ✅ <10% failure rate due to timeouts
- ✅ Concurrent execution of sub-queries
- ✅ Memory usage within acceptable limits (<2GB per query)

### 14.3 User Experience Success Criteria
- ✅ Users can ask natural language questions across applications
- ✅ System automatically detects and handles cross-app queries
- ✅ Clear error messages for unsupported scenarios
- ✅ Query results clearly indicate data sources

---

## 15. Risks and Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Performance degradation** | High | High | • Row limits<br>• Caching<br>• Monitoring<br>• Fallback to single-app |
| **Data inconsistency** | Medium | Medium | • Document consistency model<br>• Timestamp queries<br>• Warn users |
| **Complex joins fail** | Medium | High | • Start with simple joins<br>• Incremental complexity<br>• Extensive testing |
| **Security vulnerabilities** | Low | Critical | • Mandatory RBAC checks<br>• Security review<br>• Audit all queries |
| **Memory exhaustion** | Medium | High | • Result size limits<br>• Streaming<br>• Memory monitoring |
| **Network failures** | Low | High | • Retry logic<br>• Graceful degradation<br>• Connection pooling |

---

## 16. Open Questions

1. **Data Consistency Model**
   - Q: What level of consistency do users expect?
   - A: TBD - Likely eventual consistency is acceptable for reporting

2. **Maximum Dataset Size**
   - Q: What's the largest dataset users need to join?
   - A: TBD - Need to survey users and set limits

3. **Real-time vs Batch**
   - Q: Do users need real-time cross-app queries, or can we batch some?
   - A: TBD - Some queries could use materialized views

4. **Cost Model**
   - Q: Should we charge differently for cross-app queries?
   - A: TBD - May need usage-based pricing

5. **Supported Join Types**
   - Q: Do we support all join types (inner, left, right, full, cross)?
   - A: TBD - Start with inner and left, add others as needed

---

## 17. Conclusion

### 17.1 Summary

Cross-application data extraction is feasible with ReportSmith's current architecture. The recommended approach is a phased implementation:

1. **Phase 1**: Application-layer joins for MVP functionality
2. **Phase 2**: Optimization and caching
3. **Phase 3**: Hybrid federation with FDW and materialized views (optional)

### 17.2 Key Recommendations

1. **Start Simple**: Begin with application-layer joins for 2-application scenarios
2. **Limit Scope**: Impose row limits (100K) to ensure performance
3. **Monitor Closely**: Track query performance and failures
4. **Iterate**: Gather user feedback and optimize based on real usage
5. **Security First**: Enforce RBAC and audit all cross-app queries

### 17.3 Next Steps

1. Review this analysis with stakeholders
2. Prioritize use cases and create detailed requirements
3. Design API contracts for new components
4. Set up test environment with multiple database instances
5. Begin implementation of Phase 1

---

## 18. References

### 18.1 Internal Documentation
- [ReportSmith Architecture](./ARCHITECTURE.md)
- [High-Level Design](./HLD.md)
- [Database Schema](./DATABASE_SCHEMA.md)
- [Outstanding Issues](../OUTSTANDING_ISSUES.md)

### 18.2 External Resources
- [PostgreSQL Foreign Data Wrappers](https://www.postgresql.org/docs/current/postgres-fdw.html)
- [Oracle Database Links](https://docs.oracle.com/en/database/oracle/oracle-database/19/admin/managing-a-distributed-database.html)
- [Apache Presto](https://prestodb.io/)
- [Trino](https://trino.io/)
- [Pandas DataFrame Joins](https://pandas.pydata.org/docs/user_guide/merging.html)

### 18.3 Academic Papers
- "Principles of Distributed Database Systems" - Özsu & Valduriez
- "Federated Database Systems for Managing Distributed, Heterogeneous, and Autonomous Databases"

---

**Document Owner**: Architecture Team  
**Review Date**: November 10, 2025  
**Next Review**: After Phase 1 Implementation  
**Status**: ✅ Analysis Complete - Ready for Review
