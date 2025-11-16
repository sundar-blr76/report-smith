#!/bin/bash
# Cleanup script for ReportSmith generated files
#
# Usage: 
#   ./scripts/cleanup.sh          # Clean all
#   ./scripts/cleanup.sh coverage # Clean coverage only
#   ./scripts/cleanup.sh logs     # Clean logs only
#   ./scripts/cleanup.sh cache    # Clean cache only

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Function to clean coverage reports
clean_coverage() {
    echo "Cleaning coverage reports..."
    rm -rf htmlcov/ .coverage .coverage.* 2>/dev/null || true
    print_info "Coverage reports cleaned"
}

# Function to clean pytest cache
clean_pytest() {
    echo "Cleaning pytest cache..."
    rm -rf .pytest_cache/ 2>/dev/null || true
    print_info "Pytest cache cleaned"
}

# Function to clean logs (keep directory structure)
clean_logs() {
    echo "Cleaning logs..."
    rm -f logs/*.log logs/*.json 2>/dev/null || true
    rm -rf logs/semantic_debug/*.json 2>/dev/null || true
    print_info "Logs cleaned"
}

# Function to clean Python cache
clean_python_cache() {
    echo "Cleaning Python cache..."
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name "*.pyo" -delete 2>/dev/null || true
    print_info "Python cache cleaned"
}

# Function to clean temporary files
clean_temp() {
    echo "Cleaning temporary files..."
    rm -rf /tmp/reportsmith_* 2>/dev/null || true
    rm -f *.tmp 2>/dev/null || true
    print_info "Temporary files cleaned"
}

# Function to clean all
clean_all() {
    echo "======================================"
    echo "Cleaning all generated files..."
    echo "======================================"
    clean_coverage
    clean_pytest
    clean_logs
    clean_python_cache
    clean_temp
    echo ""
    print_info "All cleanup complete!"
}

# Main script logic
case "${1:-all}" in
    coverage)
        clean_coverage
        clean_pytest
        ;;
    logs)
        clean_logs
        ;;
    cache)
        clean_python_cache
        ;;
    temp)
        clean_temp
        ;;
    all)
        clean_all
        ;;
    *)
        print_error "Unknown option: $1"
        echo "Usage: $0 [coverage|logs|cache|temp|all]"
        exit 1
        ;;
esac

exit 0
