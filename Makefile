.PHONY: help clean clean-coverage clean-logs clean-cache clean-temp install test lint format

# Default target
help:
	@echo "ReportSmith Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  make install        - Install package in development mode"
	@echo "  make test           - Run all tests"
	@echo "  make lint           - Run code quality checks"
	@echo "  make format         - Format code with black and isort"
	@echo "  make clean          - Clean all generated files"
	@echo "  make clean-coverage - Clean coverage reports"
	@echo "  make clean-logs     - Clean log files"
	@echo "  make clean-cache    - Clean Python cache files"
	@echo "  make clean-temp     - Clean temporary files"

# Installation
install:
	pip install -e ".[dev]"

# Testing
test:
	pytest tests/ -v

test-coverage:
	pytest tests/ -v --cov=src/reportsmith --cov-report=html --cov-report=term-missing

# Code quality
lint:
	flake8 src/ tests/
	mypy src/

format:
	black src/ tests/
	isort src/ tests/

# Cleanup targets
clean:
	@./scripts/cleanup.sh all

clean-coverage:
	@./scripts/cleanup.sh coverage

clean-logs:
	@./scripts/cleanup.sh logs

clean-cache:
	@./scripts/cleanup.sh cache

clean-temp:
	@./scripts/cleanup.sh temp
