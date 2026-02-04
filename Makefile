.PHONY: help dev build test e2e lint format docker-up docker-down docker-restart \
        damonnator damonnator-test damonnator-both status logs clean install

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Application Security Policy Miner - Makefile$(NC)"
	@echo ""
	@echo "$(GREEN)Available targets:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(BLUE)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

# =============================================================================
# Development
# =============================================================================

install: ## Install all dependencies (frontend + backend)
	@echo "$(GREEN)Installing frontend dependencies...$(NC)"
	cd frontend && bun install
	@echo "$(GREEN)Installing backend dependencies...$(NC)"
	cd backend && pip install -r requirements.txt
	@echo "$(GREEN)Installing E2E test dependencies...$(NC)"
	cd e2e && pip install -r requirements.txt || echo "E2E not set up yet"
	@echo "$(GREEN)✓ All dependencies installed$(NC)"

dev: docker-up ## Start development servers (frontend + backend)
	@echo "$(GREEN)Starting development servers...$(NC)"
	@echo "Frontend: http://localhost:3333"
	@echo "Backend API: http://localhost:7777"
	@echo "Grafana: http://localhost:4000"
	@echo "Prometheus: http://localhost:9090"

build: ## Build Docker containers
	@echo "$(BLUE)Building Docker containers...$(NC)"
	docker-compose build

# =============================================================================
# Docker
# =============================================================================

docker-up: ## Start all Docker services
	@echo "$(GREEN)Starting Docker services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Services started$(NC)"
	@echo "Waiting 10 seconds for services to be ready..."
	@sleep 10
	@$(MAKE) status

docker-down: ## Stop all Docker services
	@echo "$(YELLOW)Stopping Docker services...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ Services stopped$(NC)"

docker-restart: docker-down docker-up ## Restart all Docker services

docker-logs: ## Show Docker logs (follow mode)
	docker-compose logs -f

docker-clean: docker-down ## Stop services and remove volumes
	@echo "$(RED)Removing Docker volumes...$(NC)"
	docker-compose down -v
	@echo "$(GREEN)✓ Cleaned up$(NC)"

# =============================================================================
# Testing
# =============================================================================

test: ## Run all tests (backend unit tests)
	@echo "$(BLUE)Running backend tests...$(NC)"
	cd backend && pytest tests/ -v

test-watch: ## Run backend tests in watch mode
	cd backend && pytest-watch tests/

e2e: docker-up ## Run E2E tests manually
	@echo "$(BLUE)Running E2E tests...$(NC)"
	@if [ -d "e2e" ]; then \
		python3 e2e/e2e_runner.py --test-suite e2e-tests.json --prd prd.json --output test-results.json; \
		echo "$(GREEN)✓ E2E tests complete. See test-results.json$(NC)"; \
	else \
		echo "$(RED)E2E infrastructure not set up yet. Run: make setup-e2e$(NC)"; \
	fi

e2e-watch: ## Run E2E tests on file changes
	@echo "$(BLUE)Watching for changes and running E2E tests...$(NC)"
	@while true; do \
		$(MAKE) e2e; \
		sleep 30; \
	done

setup-e2e: ## Setup E2E testing infrastructure (Phase 1)
	@echo "$(YELLOW)Setting up E2E testing infrastructure...$(NC)"
	@echo "This will implement GitHub issue #53"
	@echo "$(RED)TODO: This needs to be implemented first!$(NC)"
	@echo "Run: claude --dangerously-skip-permissions -p 'Implement GitHub issue #53'"

# =============================================================================
# Code Quality
# =============================================================================

lint: ## Run linters (backend + frontend)
	@echo "$(BLUE)Linting backend...$(NC)"
	cd backend && ruff check .
	@echo "$(BLUE)Linting frontend...$(NC)"
	cd frontend && bun run lint
	@echo "$(GREEN)✓ Linting complete$(NC)"

format: ## Format code (backend + frontend)
	@echo "$(BLUE)Formatting backend...$(NC)"
	cd backend && ruff format .
	@echo "$(BLUE)Formatting frontend...$(NC)"
	cd frontend && bun run format
	@echo "$(GREEN)✓ Formatting complete$(NC)"

lint-fix: ## Fix linting issues automatically
	@echo "$(BLUE)Auto-fixing linting issues...$(NC)"
	cd backend && ruff check --fix .
	cd frontend && bun run lint:fix
	@echo "$(GREEN)✓ Auto-fix complete$(NC)"

# =============================================================================
# Autonomous Loops
# =============================================================================

damonnator: ## Run development loop (builds features)
	@echo "$(GREEN)Starting Damonnator development loop...$(NC)"
	@echo "This will build features from prd.json"
	@read -p "How many iterations? [default: 100]: " iterations; \
	./damonnator.sh $${iterations:-100}

damonnator-test: docker-up ## Run testing loop (validates features)
	@echo "$(BLUE)Starting Damonnator test loop...$(NC)"
	@echo "This will validate completed features with E2E tests"
	@read -p "How many iterations? [default: 50]: " iterations; \
	./damonnator_test.sh $${iterations:-50}

damonnator-both: ## Run both loops in parallel (advanced)
	@echo "$(YELLOW)Starting BOTH loops in parallel...$(NC)"
	@echo "Dev loop will build features, test loop will validate them"
	@echo "$(RED)Warning: This is resource intensive!$(NC)"
	@read -p "Continue? (y/N): " confirm; \
	if [ "$$confirm" = "y" ]; then \
		./damonnator.sh 100 & \
		sleep 30; \
		./damonnator_test.sh 50 & \
		wait; \
	fi

damonnator-stop: ## Stop all damonnator loops
	@echo "$(RED)Stopping damonnator loops...$(NC)"
	@pkill -f damonnator.sh || true
	@pkill -f damonnator_test.sh || true
	@echo "$(GREEN)✓ Loops stopped$(NC)"

# =============================================================================
# Status & Monitoring
# =============================================================================

status: ## Show status of all services
	@echo "$(BLUE)Service Status:$(NC)"
	@docker-compose ps
	@echo ""
	@echo "$(BLUE)PRD Progress:$(NC)"
	@if [ -f prd.json ]; then \
		total=$$(jq '.stories | length' prd.json); \
		passed=$$(jq '[.stories[] | select(.passes == true)] | length' prd.json); \
		echo "  Stories: $$passed / $$total completed ($$(echo "scale=1; $$passed * 100 / $$total" | bc)%)"; \
	fi
	@echo ""
	@if [ -f test-results.json ]; then \
		echo "$(BLUE)Last Test Run:$(NC)"; \
		jq -r '"  Passed: \(.summary.passed)"' test-results.json; \
		jq -r '"  Failed: \(.summary.failed)"' test-results.json; \
		jq -r '"  Pass Rate: \(.summary.pass_rate)%"' test-results.json; \
	fi

logs: ## Show application logs
	@echo "$(BLUE)Recent logs from progress.txt:$(NC)"
	@tail -50 progress.txt

test-report: ## Show latest test results
	@if [ -f test-results.json ]; then \
		echo "$(BLUE)Test Results:$(NC)"; \
		jq '.' test-results.json; \
	else \
		echo "$(RED)No test results found. Run: make e2e$(NC)"; \
	fi

metrics: ## Open monitoring dashboards
	@echo "$(GREEN)Opening monitoring dashboards...$(NC)"
	@open http://localhost:4000  # Grafana
	@open http://localhost:9090  # Prometheus

# =============================================================================
# Database
# =============================================================================

db-shell: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U policy_miner -d policy_miner

db-migrate: ## Run database migrations
	@echo "$(BLUE)Running migrations...$(NC)"
	cd backend && alembic upgrade head

db-reset: ## Reset database (WARNING: deletes all data)
	@echo "$(RED)WARNING: This will delete ALL database data!$(NC)"
	@read -p "Are you sure? (type 'yes'): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		docker-compose down -v; \
		docker-compose up -d postgres; \
		sleep 5; \
		$(MAKE) db-migrate; \
		echo "$(GREEN)✓ Database reset$(NC)"; \
	fi

# =============================================================================
# Cleanup
# =============================================================================

clean: ## Clean temporary files and caches
	@echo "$(YELLOW)Cleaning temporary files...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf e2e/screenshots/*.png 2>/dev/null || true
	@echo "$(GREEN)✓ Cleaned$(NC)"

clean-all: clean docker-clean ## Deep clean (Docker + files)
	@echo "$(GREEN)✓ Deep clean complete$(NC)"

# =============================================================================
# Git & PRs
# =============================================================================

pr-list: ## List open PRs
	@gh pr list

pr-status: ## Show PR status for current branch
	@gh pr status

commit-stats: ## Show commit statistics
	@echo "$(BLUE)Recent commits:$(NC)"
	@git log --oneline -10

# =============================================================================
# Quick Actions
# =============================================================================

quick-test: docker-up lint test ## Quick validation (lint + unit tests)
	@echo "$(GREEN)✓ Quick validation passed$(NC)"

full-test: docker-up lint test e2e ## Full validation (all tests)
	@echo "$(GREEN)✓ Full validation passed$(NC)"

validate: full-test ## Alias for full-test

deploy-check: lint test build ## Pre-deployment validation
	@echo "$(GREEN)✓ Ready for deployment$(NC)"

# Default target
.DEFAULT_GOAL := help
