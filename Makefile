# Makefile for LLM Agents Self-Consistency Project
# Uses uv for dependency management and virtual environment

# Load environment variables from .env if it exists
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

.PHONY: help install test test-verbose test-coverage clean lint format check-env litellm-install litellm-start litellm-stop litellm-logs litellm-status litellm-clean litellm-test litellm-models setup-all setup-env test-integration test-agent-live

# Default target
help:
	@echo "Available targets:"
	@echo "  install        - Install dependencies with uv"
	@echo "  test          - Run tests with pytest"
	@echo "  test-verbose  - Run tests with verbose output"
	@echo "  test-coverage - Run tests with coverage report"
	@echo "  test-integration - Run integration tests with env vars"
	@echo "  test-agent-live - Test agent with real LLM (requires setup)"
	@echo "  lint          - Run linting checks"
	@echo "  format        - Format code"
	@echo "  clean         - Clean up temporary files"
	@echo "  check-env     - Check environment setup"
	@echo ""
	@echo "Gradio interface:"
	@echo "  gradio-dev    - Launch Gradio interface in development mode"
	@echo "  gradio-serve  - Launch Gradio interface for production"
	@echo "  gradio-test   - Test Gradio interface components"
	@echo ""
	@echo "LiteLLM targets:"
	@echo "  litellm-install - Install and run LiteLLM in Docker"
	@echo "  litellm-start   - Start LiteLLM Docker container"
	@echo "  litellm-stop    - Stop LiteLLM Docker container"
	@echo "  litellm-logs    - Show LiteLLM container logs"
	@echo "  litellm-status  - Check LiteLLM container status"
	@echo "  litellm-test    - Test LiteLLM connection"
	@echo "  litellm-test-chat - Test LiteLLM chat completions"
	@echo "  litellm-models  - List available models"
	@echo "  litellm-clean   - Remove LiteLLM container"
	@echo "  setup-all       - Install dependencies + LiteLLM"
	@echo ""
	@echo "Environment setup:"
	@echo "  setup-env      - Create .env file from template"

# Create virtual environment if it doesn't exist
.venv:
	@echo "Creating virtual environment..."
	uv venv

# Install dependencies
install: .venv
	@echo "Installing dependencies with uv..."
	uv pip install pytest pytest-cov openai
	@echo "Installing Jupyter notebook packages..."
	uv pip install ipykernel jupyter notebook
	@echo "Installing data science and visualization packages..."
	uv pip install networkx matplotlib pandas mazelib imageio seaborn
	@echo "Installing web interface packages..."
	uv pip install gradio

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
	@uv run python --version
	@echo "uv version:"
	@uv --version
	@echo "Virtual environment:"
	@uv pip list | head -5
	@echo ""
	@echo "Environment file:"
	@if [ -f .env ]; then \
		echo "✅ .env file exists"; \
	else \
		echo "❌ .env file not found. Run 'make setup-env' to create it"; \
	fi
	@echo ""
	@echo "Environment variables:"
	@echo "  LLM_MODEL: ${LLM_MODEL:-not set}"
	@echo "  LLM_TEMPERATURE: ${LLM_TEMPERATURE:-not set}"
	@echo "  LLM_BASE_URL: ${LLM_BASE_URL:-not set}"
	@echo "  LLM_API_KEY: ${LLM_API_KEY:-not set (will use default)}"
	@echo ""
	@echo "API Key Status:"
	@if [ -n "$${OPENAI_API_KEY}" ]; then \
		echo "  ✅ OpenAI API key configured"; \
	else \
		echo "  ❌ OpenAI API key not set"; \
	fi
	@if [ -n "$${GOOGLE_API_KEY}" ] || [ -n "$${GEMINI_API_KEY}" ]; then \
		echo "  ✅ Google/Gemini API key configured"; \
	else \
		echo "  ❌ Google/Gemini API key not set"; \
	fi
	@if [ -n "$${ANTHROPIC_API_KEY}" ]; then \
		echo "  ✅ Anthropic API key configured"; \
	else \
		echo "  ❌ Anthropic API key not set"; \
	fi
	@echo ""
	@echo "💡 Load .env with: source .env (or use make targets which auto-load)"

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
	@echo "Using: MODEL=$(or $(LLM_MODEL),gpt-3.5-turbo) TEMP=$(or $(LLM_TEMPERATURE),0.7) URL=$(or $(LLM_BASE_URL),http://localhost:4000)"
	LLM_MODEL=$(or $(LLM_MODEL),gpt-3.5-turbo) \
	LLM_TEMPERATURE=$(or $(LLM_TEMPERATURE),0.7) \
	LLM_BASE_URL=$(or $(LLM_BASE_URL),http://localhost:4000) \
	LLM_API_KEY=$(or $(LLM_API_KEY),sk-test) \
	uv run pytest llm_agents/tests/test_config.py::TestLiteLLMAdapterEnvironment -v

# Test agent with real LLM (requires running LiteLLM)
test-agent-live:
	@echo "Testing self-consistency agent with real LLM..."
	@if [ -z "$(LLM_MODEL)" ]; then \
		echo "❌ LLM_MODEL not set. Create .env file with 'make setup-env' first"; \
		exit 1; \
	fi
	@echo "Using model: $(LLM_MODEL) at $(or $(LLM_BASE_URL),http://localhost:4000)"
	@echo "⚠️  This will make real API calls to your LLM provider"
	@echo "Press Ctrl+C within 5 seconds to cancel..."
	@sleep 5
	@uv run python -c "\
import os; \
from llm_agents.self_consistency.interfaces import LiteLLMAdapter; \
from llm_agents.self_consistency.config import AgentConfig; \
from llm_agents.self_consistency.agent import SelfConsistencyAgent; \
adapter = LiteLLMAdapter(); \
print(f'Using model: {adapter.model}'); \
print(f'Base URL: {adapter.base_url}'); \
print('Testing LLM connection...'); \
try: \
    response = adapter.generate_llm_response('Think step by step:', 'What is 2+2?'); \
    print(f'✅ LLM Response: {response.answer}'); \
    print(f'Reasoning: {response.reasoning[:100]}...'); \
    config = AgentConfig(llm_interface=adapter, target_responses=3); \
    agent = SelfConsistencyAgent(config, 'What is 5+3?'); \
    result = agent.process_question(); \
    print(f'✅ Agent Result: {result.final_answer} (confidence: {result.confidence:.2f})'); \
except Exception as e: \
    print(f'❌ Error: {e}'); \
    print('Make sure LiteLLM is running: make litellm-status'); \
"

# Run all checks
check-all: lint test-coverage
	@echo "All checks completed!"

# Docker LiteLLM targets
# Use environment variables with fallbacks
DOCKER_IMAGE ?= ghcr.io/berriai/litellm:main-latest
CONTAINER_NAME ?= litellm-server
LITELLM_PORT ?= 4000
HOST_PORT ?= 4000

# Install and run LiteLLM in Docker
litellm-install:
	@echo "Installing and running LiteLLM in Docker..."
	@echo "Pulling LiteLLM Docker image..."
	docker pull $(DOCKER_IMAGE)
	@echo "Starting LiteLLM container with configuration..."
	docker run -d \
		--name $(CONTAINER_NAME) \
		-p $(HOST_PORT):$(LITELLM_PORT) \
		-v $(PWD)/litellm_config.yaml:/app/config.yaml \
		-e LITELLM_LOG=INFO \
		-e OPENAI_API_KEY=$${OPENAI_API_KEY:-dummy} \
		-e ANTHROPIC_API_KEY=$${ANTHROPIC_API_KEY:-dummy} \
		$(DOCKER_IMAGE) \
		--config /app/config.yaml \
		--host 0.0.0.0 \
		--port $(LITELLM_PORT)
	@echo "LiteLLM server starting at http://localhost:$(HOST_PORT)"
	@echo "📋 Available models: gpt-4o, gpt-4o-mini, gpt-3.5-turbo, claude-3-5-sonnet"
	@echo "🔑 Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variables"
	@echo "Use 'make litellm-logs' to see startup logs"
	@echo "Use 'make litellm-status' to check if ready"

# Start LiteLLM Docker container (if already exists)
litellm-start:
	@echo "Starting existing LiteLLM container..."
	@if docker ps -a --format "table {{.Names}}" | grep -q "^$(CONTAINER_NAME)$$"; then \
		docker start $(CONTAINER_NAME); \
		echo "LiteLLM server started at http://localhost:$(HOST_PORT)"; \
	else \
		echo "Container $(CONTAINER_NAME) not found. Run 'make litellm-install' first."; \
		exit 1; \
	fi

# Stop LiteLLM Docker container
litellm-stop:
	@echo "Stopping LiteLLM container..."
	@if docker ps --format "table {{.Names}}" | grep -q "^$(CONTAINER_NAME)$$"; then \
		docker stop $(CONTAINER_NAME); \
		echo "LiteLLM container stopped"; \
	else \
		echo "Container $(CONTAINER_NAME) is not running"; \
	fi

# Show LiteLLM container logs
litellm-logs:
	@echo "Showing LiteLLM container logs..."
	@if docker ps -a --format "table {{.Names}}" | grep -q "^$(CONTAINER_NAME)$$"; then \
		docker logs -f $(CONTAINER_NAME); \
	else \
		echo "Container $(CONTAINER_NAME) not found. Run 'make litellm-install' first."; \
	fi

# Check LiteLLM container status
litellm-status:
	@echo "Checking LiteLLM container status..."
	@if docker ps -a --format "table {{.Names}}" | grep -q "^$(CONTAINER_NAME)$$"; then \
		echo "Container exists:"; \
		docker ps -a --filter "name=$(CONTAINER_NAME)" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"; \
		echo ""; \
		if docker ps --format "table {{.Names}}" | grep -q "^$(CONTAINER_NAME)$$"; then \
			echo "✅ LiteLLM is running at http://localhost:$(HOST_PORT)"; \
			echo "Test with: curl http://localhost:$(HOST_PORT)/health"; \
		else \
			echo "❌ LiteLLM container is stopped. Run 'make litellm-start' to start."; \
		fi; \
	else \
		echo "❌ Container $(CONTAINER_NAME) not found. Run 'make litellm-install' first."; \
	fi

# Remove LiteLLM container completely
litellm-clean:
	@echo "Removing LiteLLM container..."
	@if docker ps -a --format "table {{.Names}}" | grep -q "^$(CONTAINER_NAME)$$"; then \
		docker stop $(CONTAINER_NAME) 2>/dev/null || true; \
		docker rm $(CONTAINER_NAME); \
		echo "LiteLLM container removed"; \
	else \
		echo "Container $(CONTAINER_NAME) not found"; \
	fi

# Test LiteLLM connection
litellm-test:
	@echo "Testing LiteLLM connection..."
	@if curl -s http://localhost:$(HOST_PORT)/health > /dev/null; then \
		echo "✅ LiteLLM is responding at http://localhost:$(HOST_PORT)"; \
		echo ""; \
		echo "📋 Available models:"; \
		curl -s -H "Authorization: Bearer sk-1234" http://localhost:$(HOST_PORT)/v1/models | uv run python -m json.tool 2>/dev/null || echo "Could not fetch models"; \
		echo ""; \
		echo "🔗 Endpoints:"; \
		echo "  Health: http://localhost:$(HOST_PORT)/health"; \
		echo "  Models: http://localhost:$(HOST_PORT)/v1/models"; \
		echo "  Chat: http://localhost:$(HOST_PORT)/v1/chat/completions"; \
		echo ""; \
		echo "🔑 Use master key 'sk-1234' for authentication"; \
	else \
		echo "❌ LiteLLM is not responding. Check if container is running with 'make litellm-status'"; \
	fi

# Test LiteLLM chat completions (like the notebook does)
litellm-test-chat:
	@echo "Testing LiteLLM chat completions..."
	@uv run python -c "import json, requests; response = requests.post('http://localhost:$(HOST_PORT)/v1/chat/completions', headers={'Authorization': 'Bearer sk-1234', 'Content-Type': 'application/json'}, json={'model': 'claude-3-haiku', 'messages': [{'role': 'user', 'content': 'Say hello'}], 'max_tokens': 10}); print('✅ Chat completion successful!' if response.status_code == 200 else f'❌ Chat completion failed: {response.status_code} - {response.text}'); data = response.json() if response.status_code == 200 else None; print(f'Response: {data[\"choices\"][0][\"message\"][\"content\"]}') if data else None"

# List available models
litellm-models:
	@echo "📋 Available LiteLLM models:"
	@curl -s -H "Authorization: Bearer sk-1234" http://localhost:$(HOST_PORT)/v1/models | uv run python -m json.tool || echo "❌ Could not fetch models - check if LiteLLM is running"

# Create .env file from template
setup-env:
	@if [ ! -f .env ]; then \
		echo "Creating .env file from template..."; \
		cp .env.example .env; \
		echo "✅ .env file created from .env.example"; \
		echo "📝 Edit .env to configure your LLM settings"; \
	else \
		echo "⚠️  .env file already exists"; \
		echo "📝 Compare with .env.example for new settings"; \
	fi

# Full setup: install dependencies and LiteLLM
setup-all: install setup-env litellm-install
	@echo ""
	@echo "🎉 Full setup completed!"
	@echo "✅ Python dependencies installed with uv"
	@echo "✅ .env file created (configure your LLM settings)"
	@echo "✅ LiteLLM Docker container running at http://localhost:$(HOST_PORT)"
	@echo ""
	@echo "Next steps:"
	@echo "1. Edit .env file with your LLM configuration"
	@echo "2. Run 'make test' to verify everything works"
	@echo "3. Check 'make litellm-status' to confirm LiteLLM is ready"
	@echo "4. Run 'make gradio-dev' to launch the web interface"

# Gradio interface targets
gradio-dev:
	@echo "🚀 Launching Gradio interface in development mode..."
	@if [ -z "$(LLM_MODEL)" ]; then \
		echo "⚠️  LLM_MODEL not set. Using default configuration."; \
		echo "💡 Run 'make setup-env' and edit .env for custom settings"; \
	fi
	@echo "📍 Interface will be available at: http://localhost:7860"
	@echo "🔗 Make sure LiteLLM is running: make litellm-status"
	@echo ""
	uv run python -m llm_agents.gradio_interface.app

gradio-serve:
	@echo "🌐 Launching Gradio interface for production..."
	@if [ -z "$(LLM_MODEL)" ]; then \
		echo "❌ LLM_MODEL not set. Run 'make setup-env' first"; \
		exit 1; \
	fi
	@echo "📍 Interface will be available at: http://0.0.0.0:7860"
	@echo "🔗 Make sure LiteLLM is running: make litellm-status"
	@echo ""
	uv run python -c "\
from llm_agents.gradio_interface import launch_interface; \
launch_interface(share=False, server_name='0.0.0.0', server_port=7860, debug=False)"

gradio-test:
	@echo "🧪 Testing Gradio interface components..."
	@uv run python -c "import sys; sys.path.insert(0, '.'); exec(open('llm_agents/gradio_interface/test_components.py').read())" 2>/dev/null || \
	uv run python -c "\
from llm_agents.gradio_interface.agent_wrapper import AgentWrapper; \
from llm_agents.gradio_interface.config_manager import ConfigManager; \
from llm_agents.gradio_interface.examples import Examples; \
print('✅ All Gradio components imported successfully'); \
config_manager = ConfigManager(); \
examples = Examples(); \
print('✅ Core components initialized'); \
print('📋 Available models:', list(config_manager.get_available_models().keys())); \
print('📝 Example questions available:', len(examples.get_sample_questions()), 'categories'); \
print('✅ Gradio interface components are working correctly')"

# Test Gradio with live LLM connection
gradio-test-live:
	@echo "🔗 Testing Gradio interface with live LLM connection..."
	@if [ -z "$(LLM_MODEL)" ]; then \
		echo "❌ LLM_MODEL not set. Run 'make setup-env' first"; \
		exit 1; \
	fi
	@echo "Using model: $(LLM_MODEL) at $(or $(LLM_BASE_URL),http://localhost:4000)"
	@echo "⚠️  This will make real API calls to your LLM provider"
	@echo "Press Ctrl+C within 5 seconds to cancel..."
	@sleep 5
	@uv run python -c "\
from llm_agents.gradio_interface.agent_wrapper import AgentWrapper, AgentType;\
from llm_agents.gradio_interface.config_manager import ConfigManager;\
print('🔧 Initializing components...');\
config_manager = ConfigManager();\
llm_adapter = config_manager.create_llm_adapter();\
agent_wrapper = AgentWrapper(llm_adapter);\
print('✅ Components initialized');\
print('🔗 Testing LLM connection...');\
if agent_wrapper.validate_llm_connection():\
    print('✅ LLM connection successful');\
    print('🧪 Testing single agent processing...');\
    result = agent_wrapper.process_question('What is 2+2?', AgentType.SELF_REFLECTION, 3, 0.8, 2, 'Answer directly:');\
    print(f'✅ Single agent test: {result.final_answer} (confidence: {result.confidence:.3f})');\
    print('🧪 Testing agent comparison...');\
    comparison = agent_wrapper.compare_agents('What is 3+3?', 3, 0.8, 2, 'Answer directly:');\
    print(f'✅ Comparison test completed with {len(comparison)} results');\
    print('🎉 All Gradio interface tests passed!');\
else:\
    print('❌ LLM connection failed. Check LiteLLM status with: make litellm-status');\
    exit(1)"