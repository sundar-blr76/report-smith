# Domain Value Handling

This document consolidates all domain value matching and resolution strategies.

## Overview

Domain values are categorical data values from database columns (e.g., fund types, client types, transaction statuses). ReportSmith uses a multi-layered approach to match user-provided values to actual database values:

1. **Local Mappings** - Predefined aliases in entity_mappings.yaml (fastest, most precise)
2. **Semantic Search** - Embedding-based similarity matching (good for synonyms)
3. **LLM Enrichment** - AI-powered intelligent matching when semantic search fails (NEW)

## Matching Strategy

### Layer 1: Local Mappings

Defined in `config/entity_mappings.yaml`:

```yaml
domain_values:
  bond:
    canonical_name: Bond
    table: funds
    column: fund_type
    value: Bond
    aliases: [bonds, fixed-income, "bond funds", debt]
    description: "Bond and fixed income funds"
```

**When to use**: For well-known, frequently-used domain values.

### Layer 2: Semantic Search

Uses embeddings to find similar values in the database:
- Searches across all domain value embeddings
- Scores based on semantic similarity (0-1)
- Threshold: typically 0.5-0.7

**When to use**: Automatic fallback when local mapping not found.

### Layer 3: LLM Enrichment (NEW)

When semantic search yields low confidence (<0.6), the system:
1. Retrieves ALL possible values for the relevant column from database
2. Provides context (table description, column description, business context)
3. Asks LLM to intelligently match user value to database values
4. Returns match only if LLM has reasonable confidence (>0.6)

**Example**:
- User says: "truepotential"
- Database has: "TruePotential Asset Management", "TrustPoint Capital", "Pinnacle Investments"
- LLM correctly matches to "TruePotential Asset Management" with confidence 0.95

**Implementation**: See `src/reportsmith/query_processing/domain_value_enricher.py`

## Configuration

### Dimension Definitions

Dimensions are defined in schema YAML files:

```yaml
dimensions:
  - table: funds
    column: fund_type
    description: "Fund investment strategy classification"
    context: "Used to categorize funds by investment approach and asset class"
    # Optional: dictionary table for enhanced descriptions
    dictionary_table: fund_type_definitions
    dictionary_value_column: type_code
    dictionary_description_column: full_description
```

### When Domain Values Are Loaded

Domain values are loaded lazily:
- On first query that references the column
- Cached in embedding database for fast lookup
- Refreshed periodically or on schema changes

## Troubleshooting

### User Value Not Matching

**Symptoms**: User mentions "equity" but query fails to find equity funds.

**Diagnostics**:
1. Check logs for `[domain-enricher]` or `[semantic]` entries
2. Look for semantic search scores (should be >0.5)
3. Check if LLM enrichment was triggered

**Solutions**:
1. Add local mapping in entity_mappings.yaml
2. Verify dimension is properly defined in schema
3. Check database actually has the expected values
4. Ensure embeddings are up to date

### LLM Enrichment Not Working

**Symptoms**: Low confidence matches still being used directly.

**Diagnostics**:
1. Check `GEMINI_API_KEY` is set
2. Look for `[domain-enricher]` log entries
3. Verify available values are being retrieved from database

**Solutions**:
1. Ensure domain_value_enricher is properly initialized
2. Check threshold settings (default: 0.6 for LLM match confidence)
3. Verify database column has data

## Best Practices

1. **Define Common Values Locally**: Add frequently-used domain values to entity_mappings.yaml
2. **Use Descriptive Names**: When creating database values, use clear, searchable names
3. **Include Synonyms**: Add common variations and abbreviations as aliases
4. **Provide Context**: Fill in descriptions and business context for better matching
5. **Monitor Match Confidence**: Track semantic search scores to identify problem areas

## Performance Considerations

- Local mappings: ~1ms lookup time
- Semantic search: ~50-100ms (with caching)
- LLM enrichment: ~500-1000ms (only when needed)

**Recommendation**: Define local mappings for 80% most common values, let semantic search + LLM handle the long tail.

---

*Consolidated from: DOMAIN_VALUE_MATCHING_STRATEGY.md, DOMAIN_VALUE_LLM_IMPLEMENTATION.md*
