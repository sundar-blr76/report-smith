#!/bin/bash
# View the latest embedding demo log

LOGS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/logs"

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ ! -d "$LOGS_DIR" ]; then
    echo "No logs directory found at: $LOGS_DIR"
    exit 1
fi

# Find the latest log file
LATEST_LOG=$(ls -t "$LOGS_DIR"/embedding_demo_*.log 2>/dev/null | head -1)

if [ -z "$LATEST_LOG" ]; then
    echo "No log files found in: $LOGS_DIR"
    exit 1
fi

echo -e "${GREEN}Latest Embedding Demo Log:${NC}"
echo -e "${YELLOW}File: $LATEST_LOG${NC}"
echo ""
echo "================================================================================"
cat "$LATEST_LOG"
echo ""
echo "================================================================================"
echo -e "${GREEN}Log file location: $LATEST_LOG${NC}"
