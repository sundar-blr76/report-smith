#!/bin/bash
# Run the embedding demo with proper environment setup and logging

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Create logs directory
LOGS_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOGS_DIR"

# Generate log filename with timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOGS_DIR/embedding_demo_${TIMESTAMP}.log"

echo -e "${GREEN}Running ReportSmith Embedding Demo${NC}"
echo -e "${YELLOW}Output will be logged to: $LOG_FILE${NC}"
echo ""

# Check if virtual environment exists
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo -e "${RED}Error: Virtual environment not found at $PROJECT_DIR/venv${NC}"
    echo -e "${YELLOW}Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt${NC}"
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source "$PROJECT_DIR/venv/bin/activate"

# Set PYTHONPATH
export PYTHONPATH="$PROJECT_DIR/src:$PYTHONPATH"

# Run the demo with tee to show output and save to log
echo -e "${GREEN}Starting embedding demo...${NC}"
echo ""
echo "Log file: $LOG_FILE" > "$LOG_FILE"
echo "Started at: $(date)" >> "$LOG_FILE"
echo "================================================" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

python3 "$SCRIPT_DIR/embedding_demo.py" 2>&1 | tee -a "$LOG_FILE"

exit_code=$?

echo "" | tee -a "$LOG_FILE"
echo "================================================" | tee -a "$LOG_FILE"
echo "Completed at: $(date)" | tee -a "$LOG_FILE"

if [ $exit_code -eq 0 ]; then
    echo "" 
    echo -e "${GREEN}✓ Demo completed successfully${NC}"
    echo -e "${GREEN}✓ Log saved to: $LOG_FILE${NC}"
else
    echo ""
    echo -e "${RED}✗ Demo failed with exit code: $exit_code${NC}"
    echo -e "${YELLOW}Check log file: $LOG_FILE${NC}"
fi

exit $exit_code
