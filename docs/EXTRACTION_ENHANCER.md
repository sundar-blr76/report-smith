# Extraction Enhancer Documentation

## Overview

The Extraction Enhancer is a comprehensive LLM-driven system that improves the NL→SQL extraction pipeline with advanced features for summary generation, column ordering, predicate coercion, and iterative SQL validation.

## Features

### FR-1: Extraction Summary Generation

Generates concise, human-readable summaries of extraction actions.

**Example:**
```python
from reportsmith.query_processing.extraction_enhancer import ExtractionEnhancer

enhancer = ExtractionEnhancer(llm_client=openai_client)

summary = enhancer.generate_summary(
    question="Show AUM for equity funds in Q4 2025",
    sql="SELECT SUM(total_aum) FROM funds WHERE fund_type='Equity' AND date >= '2025-10-01'",
    entities=[...],
    filters=["fund_type = 'Equity'", "date >= '2025-10-01'"],
    coercions=[...],
)

print(summary.summary)
# Output: "Retrieved total AUM for equity funds in Q4 2025 (2025-10-01 to 2025-12-31).
#          Applied filters: fund type = Equity, date range converted from Q4 2025."
```

### FR-2: Column Ordering

Optimizes column order for readability using LLM intelligence.

**Example:**
```python
ordering = enhancer.determine_column_order(
    question="Show funds with their AUM",
    columns=[
        {"table": "funds", "column": "total_aum", "aggregation": "sum"},
        {"table": "funds", "column": "fund_type", "aggregation": None},
        {"table": "funds", "column": "fund_name", "aggregation": None},
        {"table": "funds", "column": "fund_id", "aggregation": None},
    ],
    intent_type="aggregate",
)

print(ordering.ordered_columns)
# Output: ["funds.fund_id", "funds.fund_name", "funds.total_aum", "funds.fund_type"]
# Primary identifiers first, then metrics, then descriptive fields
```

### FR-3: Predicate Coercion

Converts user-friendly values to database-compatible formats.

**Supported Formats:**

#### Date/Quarter Formats
- `Q4 2025` → `date >= '2025-10-01' AND date <= '2025-12-31'`
- `Apr-2025` → `date >= '2025-04-01' AND date <= '2025-04-30'`
- `2025-Q1` → `date >= '2025-01-01' AND date <= '2025-03-31'`

#### Currency Formats
- `$1.2M` → `1200000`
- `INR 12,00,000` → `1200000`
- `€500K` → `500000`

#### Boolean Formats
- `Y` / `N` → `true` / `false`
- `yes` / `no` → `true` / `false`
- `1` / `0` → `true` / `false`

#### Numeric Formats
- `1,000` → `1000`
- `1.5K` → `1500`
- `2.5M` → `2500000`

**Example:**
```python
coercion = enhancer.coerce_predicate_value(
    column_name="report_date",
    column_type="date",
    user_value="Q4 2025",
    sample_values=["2025-01-15", "2025-06-20"],
    db_vendor="postgresql",
)

print(f"{coercion.original_value} → {coercion.canonical_value}")
# Output: Q4 2025 → date >= '2025-10-01' AND date <= '2025-12-31'
```

### FR-4: Iterative SQL Validation

Validates and refines SQL through multiple iterations.

**Validation Steps:**
1. **Syntactic Validation**: Checks SQL syntax using EXPLAIN
2. **Safety Check**: Ensures read-only (no DDL/DML)
3. **Sandboxed Execution**: Runs with LIMIT 5 to test semantics
4. **LLM Refinement**: Asks LLM to fix issues
5. **Iteration**: Repeats up to max_iterations (default: 3)

**Example:**
```python
final_sql, history = enhancer.validate_and_refine_sql(
    question="Show active funds",
    sql="SELECT fund_id, fund_name FROM funds WHERE is_active = true",
    entities=[...],
    intent={"type": "list"},
    sql_executor=executor,
)

for validation in history:
    print(f"Iteration {validation.iteration}: {'✓' if validation.valid else '✗'}")
    if validation.issues:
        print(f"  Issues: {validation.issues}")
    if validation.suggested_sql:
        print(f"  Refined SQL: {validation.suggested_sql[:50]}...")
```

## Configuration

### Basic Configuration

```python
from reportsmith.query_processing.extraction_enhancer import ExtractionEnhancer

enhancer = ExtractionEnhancer(
    llm_client=your_llm_client,  # OpenAI, Anthropic, or Gemini client
    max_iterations=3,            # Maximum validation iterations
    sample_size=10,              # Sample rows for predicate coercion
    enable_validation=True,      # Enable iterative validation
    enable_summary=True,         # Enable summary generation
    enable_ordering=True,        # Enable column ordering
    enable_coercion=True,        # Enable predicate coercion
    rate_limit_rpm=60,          # Requests per minute limit
    cost_cap_tokens=100000,     # Max tokens per request
)
```

### Integration with SQL Generator

```python
from reportsmith.query_processing.sql_generator import SQLGenerator

# Enable extraction enhancement in SQL generator
sql_generator = SQLGenerator(
    knowledge_graph=kg,
    llm_client=llm_client,
    enable_extraction_enhancement=True,  # Enables all FR-1,2,3,4 features
)

# Generate SQL with enhancements
result = sql_generator.generate(
    question="Show AUM for equity funds",
    intent={...},
    entities=[...],
    plan={...},
)

# Result includes:
# - result["sql"]: Generated SQL
# - result["extraction_summary"]: Human-readable summary
# - result["column_ordering"]: Optimized column order
# - result["validation_history"]: Validation iterations
```

## Safety Features

### Read-Only Enforcement

The enhancer automatically rejects any SQL containing DDL/DML operations:

```python
# ✓ Allowed: SELECT queries
"SELECT * FROM funds"

# ✓ Allowed: CTEs with SELECT
"WITH totals AS (SELECT ...) SELECT * FROM totals"

# ✗ Rejected: INSERT
"INSERT INTO funds VALUES (...)"

# ✗ Rejected: UPDATE
"UPDATE funds SET ..."

# ✗ Rejected: DELETE, DROP, CREATE, ALTER, etc.
```

### Rate Limiting

Prevents excessive LLM API calls:

```python
# Configure rate limit
enhancer = ExtractionEnhancer(
    llm_client=client,
    rate_limit_rpm=60,  # Max 60 requests per minute
)

# Reset tracking between requests
enhancer.reset_usage_tracking()
```

### Cost Caps

Prevents runaway token usage:

```python
# Configure cost cap
enhancer = ExtractionEnhancer(
    llm_client=client,
    cost_cap_tokens=100000,  # Max 100k tokens per request
)

# Raises RuntimeError if exceeded
try:
    result = enhancer.generate_summary(...)
except RuntimeError as e:
    print(f"Cost cap exceeded: {e}")
```

## Best Practices

### 1. Use Appropriate Sample Size

For predicate coercion, collect enough samples to represent data distribution:

```python
# Good: 10-20 samples for typical use
enhancer = ExtractionEnhancer(sample_size=10)

# Too few: May miss patterns
enhancer = ExtractionEnhancer(sample_size=2)

# Too many: Wastes tokens and time
enhancer = ExtractionEnhancer(sample_size=100)
```

### 2. Set Reasonable Iteration Limits

Balance between quality and performance:

```python
# Fast queries: 1-2 iterations
enhancer = ExtractionEnhancer(max_iterations=2)

# Complex queries: 3-5 iterations
enhancer = ExtractionEnhancer(max_iterations=3)

# Avoid excessive iterations (diminishing returns)
enhancer = ExtractionEnhancer(max_iterations=10)  # Not recommended
```

### 3. Enable Features Selectively

Disable features you don't need to save tokens and latency:

```python
# Only validation, no summaries
enhancer = ExtractionEnhancer(
    enable_validation=True,
    enable_summary=False,
    enable_ordering=False,
    enable_coercion=False,
)
```

### 4. Monitor Token Usage

Track token consumption for cost management:

```python
# Reset before each request
enhancer.reset_usage_tracking()

# Generate results
summary = enhancer.generate_summary(...)

# Check usage
print(f"Tokens used: {enhancer._total_tokens_used}")
```

## Error Handling

### Rate Limit Exceeded

```python
try:
    summary = enhancer.generate_summary(...)
except RuntimeError as e:
    if "rate limit" in str(e).lower():
        # Wait and retry
        time.sleep(60)
        summary = enhancer.generate_summary(...)
```

### Cost Cap Exceeded

```python
try:
    final_sql, history = enhancer.validate_and_refine_sql(...)
except RuntimeError as e:
    if "cost cap" in str(e).lower():
        # Use original SQL without refinement
        logger.warning("Cost cap exceeded, using unrefined SQL")
        final_sql = original_sql
```

### Unsafe SQL Detected

```python
final_sql, history = enhancer.validate_and_refine_sql(
    sql="INSERT INTO funds ...",  # Unsafe
    ...
)

# Check history for safety violations
if history and not history[0].valid:
    if any("DDL/DML" in issue for issue in history[0].issues):
        logger.error("SQL rejected due to safety violation")
```

## API Response Format

### Extraction Summary

```json
{
  "summary": "Retrieved total AUM for equity funds in Q4 2025 (Oct-Dec 2025).",
  "filters_applied": [
    "fund_type = 'Equity Growth'",
    "date >= '2025-10-01'",
    "date <= '2025-12-31'"
  ],
  "transformations": [
    "Q4 2025 converted to date range 2025-10-01 to 2025-12-31"
  ],
  "assumptions": [
    "Currency: USD assumed from column metadata"
  ]
}
```

### Column Ordering

```json
{
  "ordered_columns": [
    "funds.fund_id",
    "funds.fund_name",
    "funds.total_aum",
    "funds.fund_type"
  ],
  "reasoning": "Primary identifiers (ID, name) first, followed by metrics (AUM), then descriptive attributes (type)"
}
```

### Validation History

```json
[
  {
    "iteration": 1,
    "valid": false,
    "issues": ["Missing column 'currency_code' in SELECT and GROUP BY"],
    "warnings": [],
    "suggested_sql": "SELECT fund_type, currency_code, SUM(total_aum) ...",
    "reasoning": "Added currency_code to SELECT and GROUP BY",
    "token_usage": {"prompt": 500, "completion": 100, "total": 600}
  },
  {
    "iteration": 2,
    "valid": true,
    "issues": [],
    "warnings": [],
    "reasoning": "SQL validated successfully"
  }
]
```

## Testing

Run the test suite:

```bash
# Run all extraction enhancer tests
pytest tests/unit/test_extraction_enhancer.py -v

# Run specific test category
pytest tests/unit/test_extraction_enhancer.py::TestPredicateCoercion -v

# Run with coverage
pytest tests/unit/test_extraction_enhancer.py --cov=reportsmith.query_processing.extraction_enhancer
```

## Troubleshooting

### Issue: LLM returns non-JSON response

**Solution:** Ensure provider is correctly detected. For Anthropic, JSON is extracted from markdown code blocks.

### Issue: Validation always fails

**Solution:** Check SQL executor configuration. Ensure database connection is working and EXPLAIN is supported.

### Issue: High token usage

**Solution:** Reduce max_iterations, disable unused features, or use a more efficient model (e.g., gpt-4o-mini instead of gpt-4).

### Issue: Column names with spaces fail

**Solution:** Use proper quoting in SQL. The enhancer should handle this through LLM refinement.

## Changelog

### Version 1.0.0 (2025-11-05)
- Initial release
- FR-1: Extraction summary generation
- FR-2: Column ordering optimization
- FR-3: Predicate coercion (dates, currency, booleans, numerics)
- FR-4: Iterative SQL validation and refinement
- Safety features: Read-only enforcement, rate limiting, cost caps
