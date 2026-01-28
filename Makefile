.PHONY: help setup verify test progress clean format lint hooks config

# Colors
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Konko Agent - Development Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'

setup: ## Initial setup (create venv, install deps, git hooks)
	@echo "$(BLUE)Setting up project...$(NC)"
	python3 -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip setuptools wheel
	. .venv/bin/activate && pip install -e ".[dev]"
	. .venv/bin/activate && pre-commit install
	@echo "$(GREEN)✓ Setup complete!$(NC)"
	@echo "Run 'source .venv/bin/activate' to activate virtual environment"

verify: ## Verify setup and dependencies
	@echo "$(BLUE)Verifying setup...$(NC)"
	. .venv/bin/activate && python scripts/verify_setup.py

test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	. .venv/bin/activate && pytest -v

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	. .venv/bin/activate && pytest tests/unit/ -v

test-integration: ## Run integration tests only
	@echo "$(BLUE)Running integration tests...$(NC)"
	. .venv/bin/activate && pytest tests/integration/ -v

test-cov: ## Run tests with coverage
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	. .venv/bin/activate && pytest --cov=packages --cov-report=html --cov-report=term

progress: ## Check implementation progress
	@echo "$(BLUE)Checking progress...$(NC)"
	. .venv/bin/activate && ./scripts/test_progress.sh

format: ## Format code with black and isort
	@echo "$(BLUE)Formatting code...$(NC)"
	. .venv/bin/activate && black packages/ tests/ || true
	. .venv/bin/activate && isort packages/ tests/ || true
	@echo "$(GREEN)✓ Code formatted$(NC)"

lint: ## Lint code with ruff and mypy
	@echo "$(BLUE)Linting code...$(NC)"
	. .venv/bin/activate && ruff check packages/ tests/ || true
	. .venv/bin/activate && mypy packages/ || true

hooks-install: ## Install pre-commit git hooks
	@echo "$(BLUE)Installing git hooks...$(NC)"
	. .venv/bin/activate && pre-commit install
	@echo "$(GREEN)✓ Git hooks installed$(NC)"

hooks-run: ## Run pre-commit on all files
	@echo "$(BLUE)Running pre-commit on all files...$(NC)"
	. .venv/bin/activate && pre-commit run --all-files

hooks-update: ## Update pre-commit hooks
	@echo "$(BLUE)Updating pre-commit hooks...$(NC)"
	. .venv/bin/activate && pre-commit autoupdate

hooks-uninstall: ## Uninstall pre-commit git hooks
	@echo "$(YELLOW)Uninstalling git hooks...$(NC)"
	. .venv/bin/activate && pre-commit uninstall
	@echo "$(GREEN)✓ Git hooks uninstalled$(NC)"

quality: ## Run all quality checks (format, lint, test, coverage)
	@echo "$(BLUE)Running all quality checks...$(NC)"
	@echo "$(YELLOW)1/5 Formatting code...$(NC)"
	. .venv/bin/activate && black packages/ tests/
	. .venv/bin/activate && isort packages/ tests/
	@echo "$(YELLOW)2/5 Running linters...$(NC)"
	. .venv/bin/activate && ruff check packages/ tests/ --fix || true
	. .venv/bin/activate && flake8 packages/ || true
	@echo "$(YELLOW)3/5 Type checking...$(NC)"
	. .venv/bin/activate && mypy packages/ || true
	@echo "$(YELLOW)4/5 Security scan...$(NC)"
	. .venv/bin/activate && bandit -r packages/ -c pyproject.toml || true
	@echo "$(YELLOW)5/5 Running tests with coverage...$(NC)"
	. .venv/bin/activate && pytest --cov=packages --cov-report=term --cov-report=html
	@echo "$(GREEN)✓ All quality checks complete!$(NC)"
	@echo "$(BLUE)Coverage report: htmlcov/index.html$(NC)"

quality-check: ## Check code quality without fixing (for CI)
	@echo "$(BLUE)Checking code quality...$(NC)"
	. .venv/bin/activate && black --check packages/ tests/
	. .venv/bin/activate && isort --check-only packages/ tests/
	. .venv/bin/activate && ruff check packages/ tests/
	. .venv/bin/activate && mypy packages/
	. .venv/bin/activate && pytest --cov=packages --cov-fail-under=80

security: ## Run security checks
	@echo "$(BLUE)Running security checks...$(NC)"
	. .venv/bin/activate && bandit -r packages/ -c pyproject.toml
	@echo "$(GREEN)✓ Security scan complete$(NC)"

api: ## Start FastAPI development server
	@echo "$(BLUE)Starting FastAPI server...$(NC)"
	. .venv/bin/activate && uvicorn main:app --reload

api-advanced: ## Start server with advanced config
	@echo "$(BLUE)Starting FastAPI server with advanced config...$(NC)"
	. .venv/bin/activate && AGENT_CONFIG_PATH=configs/advanced_agent.yaml uvicorn main:app --reload

# ==================== Configuration Commands ====================

config-list: ## List all available configurations
	@. .venv/bin/activate && python scripts/config_tools.py list

config-validate: ## Validate all configuration files
	@. .venv/bin/activate && python scripts/config_tools.py validate

config-show: ## Show config details (usage: make config-show CONFIG=basic_agent)
	@if [ -z "$(CONFIG)" ]; then \
		echo "$(RED)Usage: make config-show CONFIG=<config_name>$(NC)"; \
		echo "Example: make config-show CONFIG=basic_agent"; \
		exit 1; \
	fi
	@. .venv/bin/activate && python scripts/config_tools.py show $(CONFIG)

cli: ## Run CLI with example config
	@echo "$(BLUE)Starting CLI...$(NC)"
	. .venv/bin/activate && python cli.py configs/basic_agent.yaml

docker-up: ## Start Docker Compose services
	@echo "$(BLUE)Starting Docker services...$(NC)"
	docker-compose up --build

docker-down: ## Stop Docker Compose services
	@echo "$(BLUE)Stopping Docker services...$(NC)"
	docker-compose down

clean: ## Clean generated files
	@echo "$(YELLOW)Cleaning generated files...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	@echo "$(GREEN)✓ Cleaned$(NC)"

status: ## Show git status and branch info
	@echo "$(BLUE)Git Status:$(NC)"
	@git status -sb
	@echo ""
	@echo "$(BLUE)Recent commits:$(NC)"
	@git log --oneline -5

push: ## Push current branch to origin
	@echo "$(BLUE)Pushing branch...$(NC)"
	git push origin $$(git branch --show-current)

# ==================== Monitoring & Observability ====================

up: ## Start all services with monitoring (agent + prometheus + grafana)
	@echo "$(BLUE)Starting all services with monitoring...$(NC)"
	docker-compose --profile monitoring up -d --build
	@echo "$(GREEN)✓ Services started!$(NC)"
	@echo ""
	@echo "$(BLUE)Available endpoints:$(NC)"
	@echo "  API:        http://localhost:8000"
	@echo "  API Docs:   http://localhost:8000/docs"
	@echo "  Metrics:    http://localhost:8000/metrics/"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Grafana:    http://localhost:3000 (admin/admin)"
	@echo "  LangSmith:  https://smith.langchain.com"

down: ## Stop all services
	@echo "$(YELLOW)Stopping all services...$(NC)"
	docker-compose --profile monitoring down
	@echo "$(GREEN)✓ Services stopped$(NC)"

restart: ## Restart all services
	@echo "$(BLUE)Restarting services...$(NC)"
	docker-compose --profile monitoring restart
	@echo "$(GREEN)✓ Services restarted$(NC)"

logs: ## Show logs from all services
	docker-compose --profile monitoring logs -f

logs-agent: ## Show logs from agent only
	docker logs -f konko-agent

rebuild: ## Full rebuild without cache
	@echo "$(BLUE)Rebuilding all services (no cache)...$(NC)"
	docker-compose --profile monitoring down
	docker-compose --profile monitoring build --no-cache
	docker-compose --profile monitoring up -d
	@echo "$(GREEN)✓ Rebuild complete!$(NC)"

metrics: ## Show current metrics
	@echo "$(BLUE)Current Konko Metrics:$(NC)"
	@curl -s http://localhost:8000/metrics/ | grep -E "^konko_" | grep -v "bucket\|created" || echo "$(YELLOW)No metrics yet - make some API calls first$(NC)"

health: ## Check health of all services
	@echo "$(BLUE)Checking service health...$(NC)"
	@echo -n "Agent:      " && curl -s http://localhost:8000/health | jq -r '.status' || echo "DOWN"
	@echo -n "Prometheus: " && curl -s http://localhost:9090/-/healthy && echo "UP" || echo "DOWN"
	@echo -n "Grafana:    " && curl -s http://localhost:3000/api/health | jq -r '.database' || echo "DOWN"

test-flow: ## Run a test conversation flow
	@echo "$(BLUE)Running test conversation flow...$(NC)"
	@SESSION=$$(curl -s -X POST http://localhost:8000/conversations | jq -r '.session_id') && \
	echo "Session: $$SESSION" && \
	echo "" && \
	echo "Sending name..." && \
	curl -s -X POST "http://localhost:8000/conversations/$$SESSION/messages" \
		-H "Content-Type: application/json" \
		-d '{"content": "My name is Test User"}' | jq '.response' && \
	echo "" && \
	echo "Sending email..." && \
	curl -s -X POST "http://localhost:8000/conversations/$$SESSION/messages" \
		-H "Content-Type: application/json" \
		-d '{"content": "test@example.com"}' | jq '.response' && \
	echo "" && \
	echo "$(GREEN)✓ Test flow complete! Check Grafana for metrics.$(NC)"

test-ws: ## Start interactive WebSocket conversation (requires wscat)
	@echo "$(BLUE)Starting WebSocket conversation...$(NC)"
	@which wscat > /dev/null || (echo "$(YELLOW)wscat not found. Install with: npm install -g wscat$(NC)" && exit 1)
	@echo "$(GREEN)Connected! Send messages as JSON:$(NC)"
	@echo '  {"type": "message", "content": "My name is Luis"}'
	@echo '  {"type": "message", "content": "luis@example.com"}'
	@echo ""
	@wscat -c ws://localhost:8000/ws
