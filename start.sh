#!/bin/bash

# ReportSmith Application Startup Script

set -e

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${GREEN}Starting ReportSmith Application...${NC}"

# Create logs directory
mkdir -p logs

# Check required environment variables
echo -e "${YELLOW}Checking environment variables...${NC}"
REQUIRED_VARS=(
    "REPORTSMITH_DB_HOST"
    "REPORTSMITH_DB_PORT"
    "REPORTSMITH_DB_NAME"
    "REPORTSMITH_DB_USER"
    "REPORTSMITH_DB_PASSWORD"
    "FINANCIAL_TESTDB_HOST"
    "FINANCIAL_TESTDB_PORT"
    "FINANCIAL_TESTDB_NAME"
    "FINANCIAL_TESTDB_USER"
    "FINANCIAL_TESTDB_PASSWORD"
)

MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo -e "${RED}Error: Missing required environment variables:${NC}"
    printf '%s\n' "${MISSING_VARS[@]}"
    echo -e "${YELLOW}Please set these in your ~/.bashrc and reload your shell${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All environment variables are set${NC}"

# Construct database URL
export FINANCIAL_TESTDB_URL="postgresql://${FINANCIAL_TESTDB_USER}:${FINANCIAL_TESTDB_PASSWORD}@${FINANCIAL_TESTDB_HOST}:${FINANCIAL_TESTDB_PORT}/${FINANCIAL_TESTDB_NAME}"
echo -e "${GREEN}✓ Database URL constructed${NC}"

# Check virtual environment
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Install/update dependencies
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}Checking dependencies...${NC}"
    pip install -q -r requirements.txt
    echo -e "${GREEN}✓ Dependencies up to date${NC}"
fi

# Set Python path
export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH}"

echo -e "${GREEN}✓ Environment initialized${NC}"
echo -e "${GREEN}✓ Logs will be written to: logs/app.log${NC}"
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ReportSmith Application Starting${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Start API (uvicorn --reload) and UI (streamlit) in background
echo -e "${YELLOW}Starting FastAPI (uvicorn --reload)...${NC}"
nohup uvicorn reportsmith.api.server:app --reload --host 127.0.0.1 --port 8000 > logs/api.log 2>&1 &
API_PID=$!
echo $API_PID > logs/api.pid
echo -e "${GREEN}✓ API started (PID: $API_PID) -> http://127.0.0.1:8000${NC}"

echo -e "${YELLOW}Starting UI (streamlit)...${NC}"
nohup streamlit run src/reportsmith/ui/app.py --server.port 8501 --server.address 127.0.0.1 > logs/ui.log 2>&1 &
UI_PID=$!
echo $UI_PID > logs/ui.pid
echo -e "${GREEN}✓ UI started (PID: $UI_PID) -> http://127.0.0.1:8501${NC}"

echo ""
echo -e "${GREEN}Use these to stop:${NC}"
echo "  kill \$(cat logs/api.pid)  # API"
echo "  kill \$(cat logs/ui.pid)   # UI"
echo ""

exit 0
