# Makefile for LLM Agents Self-Consistency Project
# Uses uv for dependency management and virtual environment

.PHONY: help install test test-verbose test-coverage clean lint format check-env

# Default target
help:
	@echo "Available targets:"
	@echo "  install        - Install dependencies with uv"
	@echo "  test          - Run tests with pytest"
	@echo "  test-verbose  - Run tests with verbose output"
	@echo "  test-coverage - Run tests with coverage report"
	@echo "  lint          - Run linting checks"
	@echo "  format        - Format code"
	@echo "  clean         - Clean up temporary files"
	@echo "  check-env     - Check environment setup"

# Install dependencies
install:
	@echo "Installing dependencies with uv..."
	uv pip install pytest pytest-cov openai

# Run tests
test:
	@echo "Running tests..."
	uv run pytest llm_agents/tests/ -v

# Run tests with verbose output
test-verbose:
	@echo "Running tests with verbose output..."
	uv run pytest llm_agents/tests/ -v -s

# Run tests with coverage
test-coverage:
	@echo "Running tests with coverage..."
	uv run pytest llm_agents/tests/ --cov=llm_agents --cov-report=html --cov-report=term-missing

# Run specific test file
test-domain:
	@echo "Running domain tests..."
	uv run pytest llm_agents/tests/test_domain.py -v

test-agent:
	@echo "Running agent tests..."
	uv run pytest llm_agents/tests/test_agent.py -v

test-config:
	@echo "Running config tests..."
	uv run pytest llm_agents/tests/test_config.py -v

test-parsing:
	@echo "Running parsing tests..."
	uv run pytest llm_agents/tests/test_parsing.py -v

# Linting (if available)
lint:
	@echo "Running linting checks..."
	@if command -v ruff > /dev/null; then \
		uv run ruff check llm_agents/; \
	elif command -v flake8 > /dev/null; then \
		uv run flake8 llm_agents/; \
	else \
		echo "No linter found. Install ruff or flake8."; \
	fi

# Format code (if available)
format:
	@echo "Formatting code..."
	@if command -v ruff > /dev/null; then \
		uv run ruff format llm_agents/; \
	elif command -v black > /dev/null; then \
		uv run black llm_agents/; \
	else \
		echo "No formatter found. Install ruff or black."; \
	fi

# Clean up temporary files
clean:
	@echo "Cleaning up temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage .pytest_cache/ 2>/dev/null || true

# Check environment setup
check-env:
	@echo "Checking environment setup..."
	@echo "Python version:"
	@python --version
	@echo "uv version:"
	@uv --version
	@echo "Virtual environment:"
	@uv pip list | head -5
	@echo "Environment variables:"
	@echo "  LLM_MODEL: ${LLM_MODEL:-not set}"
	@echo "  LLM_TEMPERATURE: ${LLM_TEMPERATURE:-not set}"
	@echo "  LLM_BASE_URL: ${LLM_BASE_URL:-not set}"
	@echo "  LLM_API_KEY: ${LLM_API_KEY:-not set (will use default)}"

# Development setup
dev-setup: install
	@echo "Setting up development environment..."
	uv pip install ruff black pytest-watch
	@echo "Development environment ready!"
	@echo "Run 'make test' to run tests"
	@echo "Run 'make test-watch' for continuous testing"

# Watch tests (if pytest-watch is installed)
test-watch:
	@echo "Running tests in watch mode..."
	uv run ptw llm_agents/tests/ -- -v

# Integration test with environment variables
test-integration:
	@echo "Running integration tests with environment variables..."
	LLM_MODEL=gpt-3.5-turbo LLM_TEMPERATURE=0.7 LLM_BASE_URL=http://localhost:4000 LLM_API_KEY=sk-test uv run pytest llm_agents/tests/test_config.py::TestLiteLLMAdapterEnvironment -v

# Run all checks
check-all: lint test-coverage
	@echo "All checks completed!"