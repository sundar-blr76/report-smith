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
# Domain Value Resolution Fixes - Summary

## Date: 2025-11-08

## Issues Fixed

### 1. Domain Value Canonical Name Not Used in SQL Generation
**Problem**: When local mapping mapped "retail" to "Individual", the SQL generator used the user's text ("retail") instead of the canonical value ("Individual"), causing query failures.

**Solution**: 
- Updated entity dict conversion in `nodes.py` to include `canonical_name` and `value` fields
- Modified SQL generator to use value priority: `entity.value` → `entity.canonical_name` → `semantic_match.value` → `entity.text`
- Added logging to show which source is being used for domain values

**Files Changed**:
- `src/reportsmith/agents/nodes.py` (lines 129-148)
- `src/reportsmith/query_processing/sql_generator.py` (lines 840-877)

### 2. Domain Value Enrichment Not Called for Local Mappings  
**Problem**: LLM enrichment was only called when semantic search failed completely, missing cases where local mapping succeeded but the value needed verification against actual database values.

**Solution**:
- Added enrichment logic for domain values that have table/column mapping
- Enrichment now attempts to verify local mapping values against actual database values
- Added condition to enrich when source is "local" with no semantic verification

**Files Changed**:
- `src/reportsmith/agents/nodes.py` (lines 1078-1138)

### 3. Enhanced Logging for Domain Value Resolution
**Problem**: Insufficient visibility into how domain values are resolved, making debugging difficult.

**Solution**:
- Added comprehensive logging at each stage of domain value resolution
- Logs show: value source, confidence, enrichment attempts, database verification
- Added warnings when user's input text is used directly without verification

**Files Changed**:
- `src/reportsmith/agents/nodes.py` (enrichment logging)
- `src/reportsmith/query_processing/sql_generator.py` (value resolution logging)

### 4. Semantic Match Threshold Too Aggressive
**Problem**: Enrichment skipped when semantic match score >= 0.7, even if value wasn't set.

**Solution**:
- Raised threshold to 0.85 for skipping enrichment
- Only skip if both high confidence match AND value is already set
- Added logging to show when enrichment is skipped and why

**Files Changed**:
- `src/reportsmith/agents/nodes.py` (lines 756-782)

## Testing Recommendations

1. **Test Query**: "What are the average fees by fund type for all our retail investors?"
   - Should now use `clients.client_type = 'Individual'` instead of `'retail'`
   - Check logs for domain value enrichment attempts
   - Verify SQL uses canonical value from local mapping or LLM enrichment

2. **Test Query**: "List fees for TruePotential clients"
   - Should trigger LLM enrichment to match "TruePotential" to "TruePotential Asset Management"
   - Check enrichment logs for fuzzy matching logic

3. **Test Query**: "Show equity products"
   - Should match multiple values: "Equity Growth", "Equity Value", etc.
   - Verify all matching domain values are included in SQL

## Logging Keywords to Monitor

- `[domain-enricher]` - LLM enrichment attempts and results
- `[schema][map][domain-enrichment]` - Schema mapping enrichment flow
- `[sql-gen][where] ✓ Using domain value from` - Shows which value source was used
- `⚠️  Using user's input text as domain value` - Warning when unverified value is used

## Known Limitations

1. Enrichment requires table/column hints to be present
2. LLM enrichment may incur API costs for each domain value verification
3. Enrichment currently only works for single domain values, not complex expressions

## Future Enhancements

1. Cache enrichment results to avoid repeated LLM calls for same values
2. Add support for compound domain values (e.g., "equity or bond")
3. Implement confidence-based fallback when enrichment fails
4. Add user feedback mechanism to improve matching over time
