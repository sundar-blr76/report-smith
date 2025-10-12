#!/bin/bash

# Query Intent Analyzer Demo Runner
# Runs the intent analyzer demo with proper environment setup

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=================================================="
echo "  ReportSmith - Query Intent Analyzer Demo"
echo "=================================================="
echo ""

# Activate virtual environment
if [ -d "$PROJECT_ROOT/venv" ]; then
    echo "Activating virtual environment..."
    source "$PROJECT_ROOT/venv/bin/activate"
else
    echo "ERROR: Virtual environment not found at $PROJECT_ROOT/venv"
    exit 1
fi

# Load environment variables
if [ -f "$HOME/.bashrc" ]; then
    source "$HOME/.bashrc"
fi

# Construct database URL if components are set
if [ -n "$FINANCIAL_TESTDB_USER" ]; then
    export FINANCIAL_TESTDB_URL="postgresql://$FINANCIAL_TESTDB_USER:$FINANCIAL_TESTDB_PASSWORD@$FINANCIAL_TESTDB_HOST:$FINANCIAL_TESTDB_PORT/$FINANCIAL_TESTDB_NAME"
    echo "✓ Database URL configured"
else
    echo "⚠ Warning: FINANCIAL_TESTDB_* variables not set"
    echo "  Dimension loading will be skipped"
fi

# Create logs directory
LOGS_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOGS_DIR"

# Generate log filename with timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOGS_DIR/intent_analyzer_${TIMESTAMP}.log"

echo ""
echo "Running intent analyzer demo..."
echo "Log file: $LOG_FILE"
echo ""

# Run the demo with logging
python3 "$SCRIPT_DIR/intent_analyzer_demo.py" 2>&1 | tee "$LOG_FILE"

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
