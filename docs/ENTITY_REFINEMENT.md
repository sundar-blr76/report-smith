# Entity Refinement with Priority and Optimal Source Selection

## Overview

The entity refinement system now prioritizes entities based on their data source optimality. This ensures that when multiple sources exist for the same data (e.g., AUM), the system prefers the most authoritative and efficient source.

## Key Concepts

### Priority Levels
- **high**: Primary, authoritative sources (e.g., `funds.total_aum`)
- **medium**: Alternative sources with some trade-offs
- **low**: Derived or historical sources that require aggregation or may be outdated

### Optimal Source Flag
- `optimal_source: true` marks entities as the preferred/authoritative source
- Helps distinguish between primary sources and derived/aggregated alternatives

### Source Notes
- Provides context on when and why to prefer specific sources
- Guides the LLM in making intelligent selection decisions

## Example: AUM (Assets Under Management)

### Primary Source (High Priority)
```yaml
aum:
  canonical_name: total_aum
  table: funds
  column: total_aum
  priority: high
  optimal_source: true
  source_notes: "Primary source for AUM - preferred over aggregating from holdings or positions"
```

### Alternative Sources (Low Priority)

#### From Holdings (Requires Aggregation)
```yaml
aum_from_holdings:
  canonical_name: market_value
  table: holdings
  column: market_value
  priority: low
  optimal_source: false
  source_notes: "Secondary source - requires SUM aggregation across holdings; prefer funds.total_aum for overall AUM"
```

#### From Performance Reports (Historical Snapshot)
```yaml
aum_from_performance:
  canonical_name: total_aum
  table: performance_reports
  column: total_aum
  priority: low
  optimal_source: false
  source_notes: "Historical snapshot - prefer funds.total_aum for current AUM values"
```

## How It Works

### 1. Entity Extraction
When a user asks about "AUM" or "assets under management", the system may identify multiple matching entities from different tables.

### 2. Entity Refinement
The `refine_entities_with_llm` function uses an LLM to select which entities to keep, with the following guidance:

```
SELECTION GUIDELINES:
1. Prefer entities marked with 'optimal_source': true
2. Prioritize entities with 'priority': 'high' over 'medium' or 'low'
3. When multiple entities represent the same concept, prefer:
   - Direct table columns over derived/aggregated values
   - Primary sources (e.g., funds.total_aum) over secondary sources
   - Current values over historical snapshots
4. Drop ambiguous, redundant, or less optimal duplicate entities
5. Consider 'source_notes' field for context
6. Prefer 'source': 'local' entities as they are pre-verified
```

### 3. Result
The system keeps only the most relevant entity (`funds.total_aum`) and drops redundant or less optimal alternatives.

## Benefits

1. **Efficiency**: Queries use direct sources instead of requiring complex aggregations
2. **Accuracy**: Primary sources are more reliable than derived values
3. **Performance**: Reduces unnecessary table joins
4. **Clarity**: Makes entity selection reasoning transparent

## Adding New Entity Mappings

When adding new entity mappings to `config/entity_mappings.yaml`, consider:

1. **Set appropriate priority**: `high` for primary sources, `low` for alternatives
2. **Mark optimal sources**: Set `optimal_source: true` for authoritative data
3. **Add source notes**: Explain when and why to prefer this source
4. **Use aliases sparingly**: Only add aliases to high-priority mappings to avoid confusion

### Example Template

```yaml
columns:
  your_entity:
    canonical_name: column_name
    table: primary_table
    column: column_name
    aliases: [alias1, alias2]
    description: "What this entity represents"
    priority: high  # high, medium, or low
    optimal_source: true  # true if this is the best source
    source_notes: "Why this source is optimal and when to prefer it"
```

## Testing

Run the entity refinement tests to verify the configuration:

```bash
pytest tests/test_entity_refinement.py -v
```

The tests verify:
- Priority fields are loaded correctly
- Optimal source flags work as expected
- Entity refinement prompt includes priority guidance
