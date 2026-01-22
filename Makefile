.PHONY: help setup verify test progress clean format lint

# Colors
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Konko Agent - Development Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'

setup: ## Initial setup (create venv, install deps)
	@echo "$(BLUE)Setting up project...$(NC)"
	python3 -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip setuptools wheel
	. .venv/bin/activate && pip install -e ".[dev]"
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

api: ## Start FastAPI development server
	@echo "$(BLUE)Starting FastAPI server...$(NC)"
	. .venv/bin/activate && uvicorn app.main:app --reload

cli: ## Run CLI with example config
	@echo "$(BLUE)Starting CLI...$(NC)"
	. .venv/bin/activate && python cli.py examples/basic_agent.yaml

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
