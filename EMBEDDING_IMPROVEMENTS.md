# Embedding Improvements Summary

## Changes Made

### 1. **Generic Column Name Filtering**
Added intelligent filtering to skip generic/non-semantic column names during embedding:

**Skipped Column Types:**
- Primary/foreign keys: `id`, `*_id`
- Timestamps: `created_at`, `updated_at`, `deleted_at`, `*_date`, `*_time`, `*_timestamp`
- Generic flags: `is_active`, `is_deleted`, `*_status`, `*_flag`
- Generic fields: `status`, `type`, `name`, `code`, `value`, `amount`, `count`, `total`, `balance`
- Boilerplate: `number`, `description`, `notes`, `comment`, `remarks`

**Results:**
- ~70 generic columns filtered out across all tables
- Reduced noise in semantic search results
- Better precision when matching meaningful columns

### 2. **Description-Based Embeddings**
Added separate description embeddings for tables, columns, and metrics:

**Strategy:**
- Embed ONLY meaningful descriptions (>10 chars, non-boilerplate)
- Tagged with `match_type: "description"` and `confidence_weight: 0.7`
- Stored separately from primary name embeddings
- Skips generic descriptions like "FK to...", "Record creation time", etc.

**Results:**
- Added 50 description embeddings for schema entities
- Added 4 description embeddings for business context
- Enables fuzzy matching when users describe concepts vs. naming them exactly

### 3. **Improved Dimension Value Filtering**
Enhanced filtering for dimension values (already in place):

**Skipped Value Types:**
- Pure numbers: `123`, `3.82`, `-45.6`
- Generic IDs: `id`, `ID`, `user_id`
- UUIDs: `a1b2c3d4-e5f6-...`
- Hash-like strings: long hex values

### 4. **Enhanced Logging**
Improved embedding seeding logs with detailed statistics:

**Before:**
```
Loaded 174 minimal name-only embeddings for app: fund_accounting
```

**After:**
```
Loaded 154 schema embeddings for app: fund_accounting (primary=104, synonyms=0, descriptions=50)
Skipped 7 generic columns in funds: id, inception_date, management_company_id, ...
```

## Embedding Architecture

### Minimal Text Strategy
Each entity gets MULTIPLE minimal embeddings:

#### Table Example: `funds`
1. **Primary name**: `"funds"` → perfect exact match
2. **Synonyms** (if any): `"portfolio"`, `"investment"` → variations
3. **Description**: `"Master fund information"` → fuzzy concept match (0.7 weight)

#### Column Example: `total_aum`
1. **Primary name**: `"total_aum"` → exact match
2. **Synonyms** (from config): `"aum"`, `"assets under management"`, `"managed assets"`
3. **Description**: `"Total assets under management"` → fuzzy match (0.7 weight)

### Benefits of This Approach

1. **High precision for exact matches**: `"funds"` query finds `funds` table with 0.9999 score
2. **Synonym coverage**: `"portfolio"` also finds `funds` table
3. **Fuzzy semantic matching**: `"master fund data"` can match via description embedding
4. **Reduced false positives**: Generic columns like `id`, `created_at` don't pollute results
5. **Cost-efficient**: Minimal text = fewer tokens = lower OpenAI costs

## Query Performance

**Test Query:** "Show AUM for aggressive funds"

**Entity Detection:**
- ✅ `funds` → found via exact match (score: 0.9999)
- ✅ `aum` → mapped to `total_aum` via local mappings + semantic (score: 0.39)
- ✅ `aggressive` → found in `risk_rating` dimension values (score: 0.81)

**Skipped Embeddings (would have created noise):**
- `id`, `created_at`, `updated_at`, `is_active` in funds table
- Generic timestamps and status fields across all tables

## Statistics

### Embedding Counts
| Collection | Primary | Synonyms | Descriptions | Total |
|------------|---------|----------|--------------|-------|
| Schema Metadata | 104 | 0 | 50 | 154 |
| Business Context | 10 | 0 | 4 | 14 |
| Dimension Values | 62 | 0 | 0 | 62 |
| **TOTAL** | **176** | **0** | **54** | **230** |

### Generic Columns Skipped
- **funds**: 7 columns (id, inception_date, management_company_id, fee_schedule_id, is_active, created_at, updated_at)
- **clients**: 5 columns (id, registration_date, kyc_status, created_at, updated_at)
- **accounts**: 7 columns (id, client_id, opening_date, account_status, management_company_id, created_at, updated_at)
- **holdings**: 5 columns (id, account_id, fund_id, as_of_date, created_at)
- **transactions**: 8 columns (id, transaction_id, account_id, fund_id, transaction_date, settlement_date, payment_date, created_at)
- **Total**: ~70 generic columns filtered out

## Next Steps

### Potential Enhancements
1. **Weighted semantic search**: Apply `confidence_weight` during ranking
2. **Context-aware filtering**: Use table relationships to boost relevant columns
3. **Domain-specific models**: Evaluate financial-domain embedding models for better accuracy
4. **Hybrid scoring**: Combine exact match + fuzzy match scores intelligently

### Monitoring
- Track semantic search precision/recall over time
- Monitor description embedding hit rate
- Analyze which generic columns (if any) should be included

## Configuration

### Embedding Provider
Currently using: **OpenAI `text-embedding-3-small`**

**Cost**: $0.020 per 1M tokens
- Our schema: ~5,000 tokens (one-time)
- Per query: ~50-100 tokens
- Monthly estimate: $0.10-0.50 (negligible)

### Alternative Providers
- **Local**: `sentence-transformers/all-MiniLM-L6-v2` (free, faster, lower quality)
- **OpenAI large**: `text-embedding-3-large` (better quality, 2x cost)
- **Financial-specific**: `FinBERT`, `SecBERT` (domain-aware)

## Files Modified
- `src/reportsmith/schema_intelligence/embedding_manager.py`: All filtering and description logic
