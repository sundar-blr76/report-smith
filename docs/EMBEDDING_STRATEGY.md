# Minimal Embedding Strategy

## Overview

ReportSmith uses a **minimal embedding strategy** for semantic search to improve precision and reduce noise in entity matching. Instead of embedding complex documents with lots of metadata, we embed just the entity name or synonym and store full context in metadata.

## Strategy

### 1. Multiple Embeddings Per Entity

Each entity can have multiple embeddings:
- **Primary embedding**: The actual entity name
- **Synonym embeddings**: One embedding for each synonym/alias

This allows the system to:
- Match on exact names with high confidence
- Match on synonyms with high confidence
- Distinguish between different match types (primary vs synonym)

### 2. Minimal Document Content

Each embedding contains ONLY:
- For tables: table name (e.g., "funds")
- For columns: column name (e.g., "total_aum")
- For dimension values: the value itself (e.g., "High", "Conservative")
- For synonyms: the synonym text (e.g., "managed assets", "aggressive")

### 3. Rich Metadata Storage

All context is stored in metadata fields:
```python
{
    "entity_type": "column",           # table, column, dimension_value, metric
    "entity_name": "total_aum",        # canonical name
    "application": "fund_accounting",
    "table": "funds",
    "column": "total_aum",
    "full_path": "funds.total_aum",
    "data_type": "decimal",
    "description": "Total assets under management",
    "match_type": "synonym",           # primary or synonym
    "synonym": "managed assets"        # if match_type=synonym
}
```

## Benefits

### 1. Higher Precision

- Minimal documents reduce semantic noise
- Exact matches score higher
- Fuzzy matches are clearer (they match the synonym, not random metadata)

### 2. Better Deduplication

When a query term matches multiple synonyms of the same entity, we can:
- Detect these are the same entity via metadata
- Boost confidence score (synonym convergence)
- Reduce result set noise

### 3. Interpretable Results

Each match is traceable:
- What was the matched text? (content)
- Was it a primary or synonym match? (match_type)
- What entity does it refer to? (table/column/value in metadata)
- How many different ways did it match? (match_count)

## Implementation

### Schema Metadata Loading

```python
# Table: Create one embedding for table name, one for each synonym
documents.append("funds")  # Primary
metadatas.append({
    "entity_type": "table",
    "entity_name": "funds",
    "table": "funds",
    "match_type": "primary",
    ...
})

documents.append("portfolios")  # Synonym
metadatas.append({
    "entity_type": "table", 
    "entity_name": "funds",  # Points to canonical name
    "table": "funds",
    "match_type": "synonym",
    "synonym": "portfolios",
    ...
})
```

### Dimension Values Loading

```python
# Each value gets one minimal embedding
for value in ["Low", "Medium", "High"]:
    documents.append(value)  # Just the value
    metadatas.append({
        "entity_type": "dimension_value",
        "entity_name": value,
        "table": "funds",
        "column": "risk_rating",
        "value": value,
        "match_type": "primary",
        ...
    })
```

### Search & Deduplication

When semantic search returns results:

1. **Group by entity**: All matches pointing to the same table/column/value are grouped
2. **Compute best score**: Take the highest score in the group
3. **Apply convergence boost**: If multiple synonyms matched, boost confidence slightly
4. **Annotate**: Add match_count, primary_count, synonym_count to results

Example:
```python
Query: "show managed assets"

Raw matches:
  - "total_aum" (primary) score=0.65
  - "assets under management" (synonym) score=0.82
  - "managed assets" (synonym) score=0.92

After deduplication:
  - funds.total_aum, score=0.92 (boosted to 0.97), match_count=3, synonym_count=2
```

## Configuration

### Embedding Models

Supports two providers:

1. **Local (sentence-transformers)**
   ```python
   EmbeddingManager(
       embedding_model="sentence-transformers/all-MiniLM-L6-v2",
       provider="local"
   )
   ```
   - Free, runs locally
   - Fast for small datasets
   - Good for development

2. **OpenAI**
   ```python
   EmbeddingManager(
       embedding_model="text-embedding-3-small",
       provider="openai",
       openai_api_key=os.getenv("OPENAI_API_KEY")
   )
   ```
   - Paid API ($0.02 per 1M tokens)
   - Better semantic understanding
   - Recommended for production
   - **Currently configured as default**

### Search Thresholds

Configured in `LLMIntentAnalyzer`:
```python
schema_score_threshold = 0.3      # Tables/columns
dimension_score_threshold = 0.3   # Dimension values  
context_score_threshold = 0.4     # Business metrics
```

Lower thresholds = more matches but more noise
Higher thresholds = fewer matches but higher precision

## Example

Query: **"Show AUM for aggressive funds"**

### Step 1: Intent Analysis
Extracts entities: ["aum", "aggressive", "funds"]

### Step 2: Local Mapping (Fast Path)
- "aum" → mapped to funds.total_aum (via entity_mappings.yaml)
- "aggressive" → mapped to funds.risk_rating = "High" (via entity_mappings.yaml)
- "funds" → mapped to funds table (via entity_mappings.yaml)

Result: All entities resolved locally, semantic search not needed ✓

### Step 3: Semantic Enrichment (Fallback)
If local mapping fails for any entity:
1. Search all 3 collections (schema, dimensions, context)
2. Filter by score threshold
3. Deduplicate by entity
4. Boost scores for synonym convergence

### Step 4: Result
```json
{
  "entities": [
    {
      "text": "aum",
      "table": "funds",
      "column": "total_aum",
      "source": "local",  // or "semantic" if from embeddings
      "semantic_match_count": 0
    },
    {
      "text": "aggressive", 
      "table": "funds",
      "column": "risk_rating",
      "value": "High",
      "source": "local",
      "semantic_match_count": 0
    }
  ]
}
```

## Monitoring

### Embedding Stats
Check via API:
```bash
curl http://localhost:8000/health
```

Returns:
```json
{
  "embeddings": {
    "schema_metadata": 174,      // Tables + columns + synonyms
    "dimension_values": 62,      // Actual values from DB
    "business_context": 10,      // Metrics + sample queries
    "model": "text-embedding-3-small"
  }
}
```

### Search Debug Files

Located in `logs/semantic_debug/`:
- `semantic_input.json`: What entity is being searched
- `semantic_output.json`: How many matches, top result

## Future Enhancements

1. **Weighted embeddings**: Apply different importance to primary vs synonym matches
2. **Entity-type specific thresholds**: Different thresholds for tables, columns, values
3. **Context-aware search**: Include query context in search to improve relevance
4. **Hybrid ranking**: Combine semantic score with other signals (frequency, freshness)
5. **A/B testing**: Compare different embedding models and strategies
