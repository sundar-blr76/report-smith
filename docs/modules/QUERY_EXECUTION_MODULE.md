# Query Execution Module - Functional Documentation

**Module Path**: `src/reportsmith/query_execution/`  
**Version**: 1.0  
**Last Updated**: November 7, 2025

---

## Overview

The `query_execution` module handles SQL query execution against target databases and result formatting.

### Purpose
- Execute SQL queries against multiple database types
- Manage database connections and connection pooling
- Format query results in various formats (JSON, table, CSV)
- Handle execution errors and timeouts

### Key Components
- **SQLExecutor**: Main execution engine
- **ConnectionManager**: Database connection management

---

## Core Classes

### 1. SQLExecutor

**File**: `sql_executor.py`

#### Description
Executes SQL queries against target databases and formats results.

#### Features
- Multi-database support (PostgreSQL, Oracle, SQL Server)
- Connection pooling for performance
- Result formatting (JSON, table, CSV)
- Execution logging and auditing
- Error handling and retry logic

#### Key Methods

##### execute()
```python
def execute(
    self,
    sql: str,
    database: str,
    format: str = "json",
    timeout: int = 30
) -> ExecutionResult
```

**Parameters:**
- `sql`: SQL query to execute
- `database`: Database identifier from config
- `format`: Output format ("json", "table", "csv")
- `timeout`: Query timeout in seconds

**Returns**: ExecutionResult with data, row_count, execution_time

**Example:**
```python
executor = SQLExecutor(connection_manager)

result = executor.execute(
    sql="SELECT * FROM funds WHERE fund_type = 'Equity Growth'",
    database="financial_db",
    format="json"
)

print(f"Rows: {result.row_count}")
print(f"Time: {result.execution_time_ms}ms")
print(f"Data: {result.data}")
```

---

### 2. ConnectionManager

**File**: `connection_manager.py`

#### Description
Manages database connections with pooling and health checks.

#### Features
- Connection pooling (configurable pool size)
- Health checks and automatic reconnection
- Support for multiple database vendors
- Connection timeout handling
- Credential management

#### Key Methods

##### get_connection()
```python
def get_connection(self, database: str) -> Connection
```

Retrieves connection from pool or creates new one.

##### release_connection()
```python
def release_connection(self, database: str, connection: Connection)
```

Returns connection to pool for reuse.

**Example:**
```python
conn_mgr = ConnectionManager(database_configs)

# Get connection
conn = conn_mgr.get_connection("financial_db")

# Use connection
cursor = conn.cursor()
cursor.execute("SELECT * FROM funds")
results = cursor.fetchall()

# Release back to pool
conn_mgr.release_connection("financial_db", conn)
```

---

## Data Structures

### ExecutionResult

```python
@dataclass
class ExecutionResult:
    status: str                      # "success" or "error"
    data: List[Dict[str, Any]]       # Query results
    row_count: int                   # Number of rows returned
    execution_time_ms: int           # Query execution time
    columns: List[str]               # Column names
    error: Optional[str]             # Error message if failed
```

---

## Usage Examples

### Basic Query Execution

```python
from reportsmith.query_execution import SQLExecutor

executor = SQLExecutor(connection_manager)

# Execute query
result = executor.execute(
    sql="SELECT fund_code, total_aum FROM funds",
    database="financial_db"
)

# Process results
if result.status == "success":
    for row in result.data:
        print(f"{row['fund_code']}: ${row['total_aum']:,.2f}")
```

### Error Handling

```python
try:
    result = executor.execute(sql, database)
except QueryExecutionError as e:
    logger.error(f"Query failed: {e}")
    # Handle error
except DatabaseConnectionError as e:
    logger.error(f"Connection failed: {e}")
    # Retry or fail gracefully
```

---

## Performance Considerations

- **Connection Pooling**: Reuse connections for better performance
- **Query Timeout**: Set appropriate timeout values
- **Result Streaming**: Use for large result sets (future enhancement)

---

**See Also:**
- [Agents Module](AGENTS_MODULE.md)
- [Low-Level Design](../LLD.md)
