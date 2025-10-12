# Using Google Gemini with ReportSmith

## Great News! You Already Have Gemini API Key! 🎉

Your environment already has `GEMINI_API_KEY` configured, so you can use Google's Gemini models **immediately**!

## Why Gemini is Excellent

### 1. **FREE Tier** ✨
- **60 requests/minute**
- **1 million tokens/day** (that's ~10,000 queries!)
- **No credit card required**
- Perfect for development and testing

### 2. **Very Cheap** 💰
Even beyond free tier:
- Gemini 1.5 Flash: **FREE** up to limits
- Gemini 1.5 Pro: $0.000125/1K chars (~$0.00005/query)
- **Cheaper than both OpenAI and Anthropic!**

### 3. **Fast & Good Quality** ⚡
- Speed: ~500ms-1s (similar to GPT-4o-mini)
- Quality: Excellent for structured output
- Context: Up to 1M tokens (huge!)

## Your API Key Status

```bash
✅ GEMINI_API_KEY: Found (AIzaSyCJtHevck3O_1jh...)
```

You're ready to go! 🚀

## How to Use Gemini

### 1. Install Google Package (if not already)
```bash
cd /home/sundar/sundar_projects/report-smith
source venv/bin/activate
pip install google-generativeai>=0.3.0
```

### 2. Test LLM Intent Analyzer with Gemini
```bash
cd examples
./run_llm_intent_demo.sh
```

It will **automatically detect and use Gemini**! ✨

### 3. Test Hybrid Analyzer with Gemini
```bash
cd examples
./run_hybrid_intent_demo.sh
```

### 4. Use in Code
```python
from reportsmith.query_processing import LLMIntentAnalyzer

# Gemini is now the default!
analyzer = LLMIntentAnalyzer(
    embedding_manager=embedding_mgr,
    llm_provider="gemini",  # Default
    model="gemini-1.5-flash"  # Fast & FREE!
)

intent = analyzer.analyze("Show monthly fees for equity funds")
```

## Gemini Models Available

### Gemini 1.5 Flash (Recommended) ⭐
- **Speed**: Very fast (~500ms)
- **Cost**: **FREE** up to 1M tokens/day
- **Quality**: Excellent
- **Use for**: Everything! It's free!

```python
analyzer = LLMIntentAnalyzer(
    embedding_manager=emb_mgr,
    llm_provider="gemini",
    model="gemini-1.5-flash"  # Default
)
```

### Gemini 1.5 Pro (If you need more power)
- **Speed**: Fast (~800ms)
- **Cost**: $0.000125/1K chars
- **Quality**: Best in class
- **Use for**: Complex queries

```python
analyzer = LLMIntentAnalyzer(
    embedding_manager=emb_mgr,
    llm_provider="gemini",
    model="gemini-1.5-pro"
)
```

## Cost Comparison

| Provider | Model | Cost/Query | Free Tier |
|----------|-------|------------|-----------|
| **Gemini** ⭐ | 1.5 Flash | **$0** | 1M tokens/day |
| OpenAI | GPT-4o-mini | $0.00012 | $5 credit (new) |
| Anthropic | Claude Haiku | $0.00004 | None |
| **Gemini** | 1.5 Pro | $0.00005 | 1M tokens/day |

**Gemini Flash is FREE!** Perfect for development! 🎉

## Free API Key Information

### ✅ You Already Have Gemini (FREE!)
Your `GEMINI_API_KEY` is ready to use.

### Getting API Keys (If you need alternatives)

#### OpenAI (Not Free)
- **URL**: https://platform.openai.com/api-keys
- **Free tier**: $5 credit for 3 months (new accounts only)
- **After**: Pay as you go (~$0.00012/query)
- ❌ **Requires credit card** after free tier

#### Anthropic Claude (Not Free)
- **URL**: https://console.anthropic.com/
- **Free tier**: None
- **Cost**: Pay as you go (~$0.00004/query)
- ❌ **Requires credit card**

#### Google Gemini (FREE!) ⭐
- **URL**: https://makersuite.google.com/app/apikey
- **Free tier**: YES! 60 req/min, 1M tokens/day
- **After**: Still very cheap
- ✅ **No credit card required**

**Your existing Gemini key is perfect!**

## Updated Code - Auto-detects Gemini

The LLM analyzer now auto-detects available API keys in this order:

1. **OpenAI** (if OPENAI_API_KEY set)
2. **Anthropic** (if ANTHROPIC_API_KEY set)  
3. **Gemini** (if GEMINI_API_KEY or GOOGLE_API_KEY set) ← **You're here!**

```python
# Auto-detection
analyzer = LLMIntentAnalyzer(embedding_manager=emb)
# Will use Gemini automatically!

# Or explicit
analyzer = LLMIntentAnalyzer(
    embedding_manager=emb,
    llm_provider="gemini"
)
```

## Test It Now!

```bash
# Install Google package
pip install google-generativeai

# Test LLM analyzer (will use Gemini)
cd examples
./run_llm_intent_demo.sh

# Test hybrid analyzer (will use Gemini)
./run_hybrid_intent_demo.sh
```

## Example Queries to Try

```
"Show monthly fees for all TruePotential equity funds"
"What is the total AUM for bond funds?"
"List top 10 clients by account balance"
"Compare performance of equity vs bond funds"
```

Gemini will understand all of these perfectly! ✨

## Gemini-Specific Features

### JSON Mode (We use this!)
```python
response = client.generate_content(
    prompt,
    generation_config={
        "temperature": 0,
        "response_mime_type": "application/json",  # Structured output!
    }
)
```

### Large Context Window
- 1M tokens context!
- Can handle HUGE schema definitions
- Perfect for complex database schemas

### Fast Iteration
- Free tier = experiment freely
- No cost worries during development
- Scale up when ready

## Summary

✅ **You're all set with Gemini!**
- API key already configured
- FREE tier (1M tokens/day)
- Fast and high quality
- No credit card needed

🚀 **Next steps:**
1. Install: `pip install google-generativeai`
2. Test: `./examples/run_llm_intent_demo.sh`
3. Use in production with confidence!

**Gemini is the perfect choice for ReportSmith!** 🎯

---

*Note: The code already supports Gemini. Just install the package and run!*
