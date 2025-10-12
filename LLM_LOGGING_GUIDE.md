# LLM Request/Response Logging Guide

## Overview

Comprehensive logging has been added to all LLM interactions in `LLMIntentAnalyzer` to help with debugging, monitoring, and understanding the LLM's behavior.

## What's Logged

### 1. Intent Extraction (`_extract_with_llm`)

Logs for the initial query analysis where LLM extracts structured intent.

#### INFO Level Logs
- **Request initiation**: Query being analyzed
- **Parsed result**: Final structured intent extracted

#### DEBUG Level Logs
- **Provider & Model**: Which LLM provider and model being used
- **Request payload**: Full request including prompts, temperature, etc.
- **Raw response**: Unprocessed response from LLM
- **Response metadata**: Model used, token usage, candidates
- **Full prompt**: Complete prompt sent to LLM

### 2. Match Refinement (`_llm_refine_matches`)

Logs for the contextual filtering where LLM drops irrelevant matches.

#### INFO Level Logs
- **Request initiation**: Entity being refined
- **Parsed result**: Filtered indices and reasoning
- **Refinement summary**: How many matches kept/dropped

#### DEBUG Level Logs
- **Request details**: Provider, model, query, match count
- **Full prompt**: Complete refinement prompt with all matches
- **Request payload**: Provider-specific request structure
- **Raw response**: Unprocessed LLM response
- **Response metadata**: Usage statistics, model info
- **Match details**: Number of refined matches returned

#### WARNING Level Logs
- **All matches filtered**: When LLM drops everything (fallback triggered)
- **LLM failure**: When refinement fails (fallback to original matches)

#### ERROR Level Logs
- **Exception details**: Full stack trace when LLM calls fail

## Log Output Examples

### Intent Extraction Example

```
INFO: LLM Intent Extraction Request for query: 'Show monthly fees for equity funds'
DEBUG: Request - Provider: gemini, Model: gemini-2.5-flash
DEBUG: Gemini Intent Extraction Request - Prompt length: 1245 chars
DEBUG: Gemini Intent Extraction Request - Generation config: {
  "temperature": 0,
  "response_mime_type": "application/json"
}
DEBUG: Gemini Prompt:
You are a SQL query intent analyzer for a financial data system...
[full prompt]

DEBUG: Gemini Raw Response: {
  "intent_type": "aggregation",
  "entities": ["fees", "equity funds"],
  "time_scope": "monthly",
  ...
}
DEBUG: Gemini Response Metadata - Candidates: 1
DEBUG: Gemini Usage: total_tokens=523, prompt_tokens=456, candidates_tokens=67

INFO: Gemini Intent Extraction Result: {
  "intent_type": "aggregation",
  "entities": ["fees", "equity funds"],
  "time_scope": "monthly",
  "aggregations": ["sum"],
  "reasoning": "User wants monthly aggregated fee data for equity funds"
}
```

### Match Refinement Example

```
INFO: LLM Refinement Request for entity: 'equity funds'
DEBUG: Request - Provider: gemini, Model: gemini-2.5-flash
DEBUG: Request - Query: Show monthly fees for equity funds
DEBUG: Request - Matches count: 8
DEBUG: Request - Prompt:
Given the user's query: "Show monthly fees for equity funds"
They are looking for: "equity funds"
Here are the semantic matches found (sorted by similarity score):
[
  {"index": 0, "content": "funds.fund_type", "type": "schema", "score": 0.85},
  {"index": 1, "content": "Equity", "type": "dimension_value", "score": 0.82},
  {"index": 2, "content": "Equity Derivatives", "type": "dimension_value", "score": 0.78},
  ...
]
...

DEBUG: Gemini Raw Response: {
  "relevant_indices": [0, 1, 4, 5],
  "reasoning": "Filtered out 'Equity Derivatives' and 'Equity Options' as user asked for general equity funds, not derivatives"
}

INFO: LLM Refinement Result: {
  "relevant_indices": [0, 1, 4, 5],
  "reasoning": "Filtered out 'Equity Derivatives' and 'Equity Options' as user asked for general equity funds, not derivatives"
}

INFO: LLM refinement for 'equity funds': kept 4/8 matches. Reasoning: Filtered out 'Equity Derivatives' and 'Equity Options' as user asked for general equity funds, not derivatives

DEBUG: Returning 4 refined matches out of 8 original matches
```

### Error/Fallback Example

```
ERROR: LLM refinement failed for 'equity funds': JSONDecodeError: Expecting value: line 1 column 1 (char 0)
DEBUG: Exception details:
Traceback (most recent call last):
  ...
WARNING: Using all 8 original matches due to LLM failure
```

## Provider-Specific Logging

### OpenAI
- Logs request payload with messages, model, temperature
- Logs usage stats (prompt_tokens, completion_tokens, total_tokens)
- Logs model that actually processed the request

### Anthropic
- Logs request payload with system prompt and user messages
- Logs usage stats (input_tokens, output_tokens)
- Extracts JSON from markdown-wrapped responses if needed

### Gemini
- Logs prompt length and generation config
- Logs full prompt text
- Logs usage metadata (total_tokens, prompt_tokens, candidates_tokens)
- Logs number of response candidates

## Configuration

Logging level can be controlled via the ReportSmith logger configuration:

```python
import logging
from reportsmith.logger import get_logger

# Set to DEBUG for detailed request/response logs
logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)

# Set to INFO for high-level summaries only
logger.setLevel(logging.INFO)

# Set to WARNING to only see errors/warnings
logger.setLevel(logging.WARNING)
```

## Log Levels Breakdown

| Level | What Gets Logged |
|-------|------------------|
| **DEBUG** | Everything: full prompts, payloads, raw responses, metadata, detailed flow |
| **INFO** | High-level: request initiation, parsed results, summary stats |
| **WARNING** | Issues: fallbacks triggered, unusual conditions |
| **ERROR** | Failures: exceptions, errors requiring attention |

## Use Cases

### 1. Debugging LLM Behavior
**Set to DEBUG** to see:
- Exact prompts being sent
- Raw responses received
- How JSON is being parsed
- Provider-specific metadata

### 2. Monitoring Production
**Set to INFO** to see:
- Which queries are being processed
- What intents are being extracted
- How many matches are being refined
- LLM's reasoning for decisions

### 3. Troubleshooting Errors
**Set to WARNING/ERROR** to:
- Catch LLM API failures
- See when fallbacks are triggered
- Monitor unusual patterns

### 4. Cost Tracking
**Check DEBUG logs for**:
- Token usage per request
- Number of LLM calls per query
- Model being used (affects pricing)

## Performance Impact

- **DEBUG logging**: Minimal overhead (~1-2ms per log statement)
- **INFO logging**: Negligible overhead
- Logs are asynchronous and non-blocking
- JSON serialization is the main cost (still <5ms typically)

## Tips

1. **In Development**: Use DEBUG to understand LLM behavior
2. **In Staging**: Use INFO to validate intent extraction accuracy
3. **In Production**: Use INFO or WARNING, enable DEBUG for specific troubleshooting
4. **Cost Analysis**: Parse DEBUG logs to track token usage over time
5. **Quality Metrics**: Parse INFO logs to measure refinement effectiveness

## Examples of What You Can Learn

### From Intent Extraction Logs
- How well the LLM understands different query types
- What entities are being extracted
- LLM's reasoning process
- Token costs per query type

### From Refinement Logs
- Which semantically similar matches are contextually wrong
- LLM's reasoning for filtering decisions
- How many false positives are being caught
- Effectiveness of different score thresholds

## Log File Organization

Suggested log file structure:

```
logs/
  llm_intent_analyzer.log        # All LLM-related logs
  llm_intent_analyzer.debug.log  # DEBUG level only
  llm_costs.log                  # Extract usage metadata for cost tracking
```

Configure in your logging setup:

```python
import logging.config

LOGGING_CONFIG = {
    'version': 1,
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/llm_intent_analyzer.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'detailed',
        },
    },
    'formatters': {
        'detailed': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
    },
    'loggers': {
        'reportsmith.query_processing.llm_intent_analyzer': {
            'level': 'DEBUG',
            'handlers': ['file'],
        },
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
```

## Summary

With comprehensive logging now in place, you can:

✅ **Debug**: See exactly what's sent to and received from LLMs
✅ **Monitor**: Track query processing and intent extraction
✅ **Analyze**: Understand LLM decisions and reasoning
✅ **Optimize**: Identify areas for prompt or threshold tuning
✅ **Cost Track**: Monitor token usage across providers
✅ **Troubleshoot**: Quickly identify and fix issues

All logs include context (query, entity, provider) making it easy to trace specific requests through the system.
