#!/bin/bash

# ReportSmith Application Restart Script
# Kills running processes, clears logs, and restarts application

set +e  # Don't exit on error for cleanup operations

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  ReportSmith Application Restart${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Step 1: Kill existing processes
echo -e "${YELLOW}[1/3] Stopping existing processes...${NC}"
PIDS=$(ps aux | grep -E "python.*reportsmith" | grep -v grep | grep -v restart.sh | awk '{print $2}')

if [ -n "$PIDS" ]; then
    echo -e "${YELLOW}Found running processes: $PIDS${NC}"
    kill -15 $PIDS 2>/dev/null || true
    sleep 2
    # Force kill if still running
    kill -9 $PIDS 2>/dev/null || true
    echo -e "${GREEN}✓ Processes terminated${NC}"
else
    echo -e "${GREEN}✓ No running processes found${NC}"
fi
echo ""

# Step 2: Clear logs
echo -e "${YELLOW}[2/3] Clearing previous logs...${NC}"
rm -f logs/app.log
mkdir -p logs
echo -e "${GREEN}✓ Logs cleared${NC}"
echo ""

# Step 3: Start application
echo -e "${YELLOW}[3/3] Starting application...${NC}"
echo ""

set -e  # Enable exit on error for startup
"$SCRIPT_DIR/start.sh"

exit 0
