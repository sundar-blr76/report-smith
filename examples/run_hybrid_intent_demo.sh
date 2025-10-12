#!/bin/bash

# Hybrid Intent Analyzer Demo Runner

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=================================================="
echo "  ReportSmith - Hybrid Intent Analyzer Demo"
echo "  Local Mappings + LLM + Semantic Search"
echo "=================================================="
echo ""

# Activate virtual environment
if [ -d "$PROJECT_ROOT/venv" ]; then
    echo "Activating virtual environment..."
    source "$PROJECT_ROOT/venv/bin/activate"
else
    echo "ERROR: Virtual environment not found"
    exit 1
fi

# Load environment variables
if [ -f "$HOME/.bashrc" ]; then
    source "$HOME/.bashrc"
fi

# Check for LLM API key (optional)
if [ -n "$OPENAI_API_KEY" ]; then
    echo "✓ OpenAI API key found (LLM enabled)"
elif [ -n "$ANTHROPIC_API_KEY" ]; then
    echo "✓ Anthropic API key found (LLM enabled)"
else
    echo "⚠ No LLM API key (will use local + semantic only)"
fi

# Construct database URL
if [ -n "$FINANCIAL_TESTDB_USER" ]; then
    export FINANCIAL_TESTDB_URL="postgresql://$FINANCIAL_TESTDB_USER:$FINANCIAL_TESTDB_PASSWORD@$FINANCIAL_TESTDB_HOST:$FINANCIAL_TESTDB_PORT/$FINANCIAL_TESTDB_NAME"
    echo "✓ Database URL configured"
fi

# Create logs directory
LOGS_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOGS_DIR"

# Generate log filename
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOGS_DIR/hybrid_intent_${TIMESTAMP}.log"

echo ""
echo "Running hybrid intent analyzer demo..."
echo "Log file: $LOG_FILE"
echo ""

# Run the demo
python3 "$SCRIPT_DIR/hybrid_intent_demo.py" 2>&1 | tee "$LOG_FILE"

EXIT_CODE=$?

echo ""
echo "=================================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ Demo completed successfully"
else
    echo "✗ Demo failed with exit code: $EXIT_CODE"
fi
echo "=================================================="

exit $EXIT_CODE
