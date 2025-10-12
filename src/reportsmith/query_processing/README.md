# Query Processing Module

Natural language query analysis for ReportSmith.

## Components

### 1. LLM Intent Analyzer ⭐ (Recommended)

**File**: `llm_intent_analyzer.py`

Uses OpenAI/Anthropic LLMs with structured output for robust intent extraction.

**Features**:
- ✅ Zero maintenance (no patterns to update)
- ✅ Natural language understanding
- ✅ Structured JSON output (Pydantic models)
- ✅ Provides reasoning for analysis
- ✅ 25% less code than pattern-based

**Usage**:
```python
from reportsmith.query_processing import LLMIntentAnalyzer

analyzer = LLMIntentAnalyzer(
    embedding_manager=embedding_mgr,
    llm_provider="openai",  # or "anthropic"
    model="gpt-4o-mini"     # fast & cheap
)

intent = analyzer.analyze("Show monthly fees for equity funds")
```

**Cost**: ~$0.0001 per query (negligible!)

### 2. Pattern Intent Analyzer (Fallback)

**File**: `intent_analyzer.py`

Uses regex patterns + semantic search for intent extraction.

**Features**:
- ✅ Free (no API costs)
- ✅ Fast (<100ms)
- ✅ No external dependencies
- ⚠️ Requires pattern maintenance

**Usage**:
```python
from reportsmith.query_processing import QueryIntentAnalyzer

analyzer = QueryIntentAnalyzer(embedding_manager)
intent = analyzer.analyze("Show monthly fees")
```

## Data Models

### QueryIntent
```python
@dataclass
class QueryIntent:
    original_query: str
    intent_type: IntentType
    entities: List[EnrichedEntity]
    time_scope: TimeScope
    aggregations: List[AggregationType]
    filters: List[str]
    limit: Optional[int]
    order_by: Optional[str]
    order_direction: str
    llm_reasoning: str
```

### IntentType (Enum)
- `RETRIEVAL` - Get raw data
- `AGGREGATION` - Sum, count, average
- `FILTERING` - Filter by conditions
- `COMPARISON` - Compare across dimensions
- `RANKING` - Top N, bottom N
- `TREND` - Time-based analysis

### TimeScope (Enum)
- `DAILY`, `WEEKLY`, `MONTHLY`, `QUARTERLY`, `YEARLY`
- `YTD`, `MTD`
- `CUSTOM`, `NONE`

### AggregationType (Enum)
- `SUM`, `COUNT`, `AVERAGE`, `MIN`, `MAX`, `DISTINCT_COUNT`

## Demos

### LLM Analyzer Demo
```bash
export OPENAI_API_KEY="sk-..."
cd examples
./run_llm_intent_demo.sh
```

### Pattern Analyzer Demo
```bash
cd examples
./run_intent_analyzer_demo.sh
```

## Documentation

- **LLM_INTENT_ANALYZER.md** - Complete implementation guide
- **INTENT_ANALYZER_COMPARISON.md** - Detailed comparison
- **PHASE_1_1_SUMMARY.md** - Phase summary

## Recommendation

**Use LLM-based analyzer for production:**
1. Better maintenance (no pattern updates)
2. Better accuracy (natural language)
3. Negligible cost (~$0.0001/query)
4. Cleaner code (280 vs 380 lines)

## API Keys

### OpenAI (Recommended)
```bash
export OPENAI_API_KEY="sk-..."
# Model: gpt-4o-mini (~$0.00012/query)
```

### Anthropic (Cheaper)
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
# Model: claude-3-haiku (~$0.00004/query)
```

---

**Status**: Phase 1.1 Complete ✅  
**Next**: Schema Mapper (Phase 1.2)
