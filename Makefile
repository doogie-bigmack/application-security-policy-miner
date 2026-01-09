.PHONY: help install dev docker-up docker-down docker-rebuild test e2e lint lint-backend lint-frontend \
        damonnator damonnator-test damonnator-infra damonnator-all status clean

##@ General

help: ## Show this help message
	@echo "Poalo Policy Miner - Makefile Commands"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Installation

install: ## Install all dependencies
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && bun install
	@echo "Installing E2E test dependencies..."
	cd e2e && pip install -r requirements.txt || echo "⚠️  e2e/ not yet created"
	@echo "✅ All dependencies installed"

##@ Development

dev: ## Start development servers (frontend + backend)
	@echo "Starting development servers..."
	@echo "Frontend: http://localhost:3333"
	@echo "Backend: http://localhost:7777"
	@trap 'kill 0' INT; \
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 7777 & \
	cd frontend && bun run dev --port 3333 & \
	wait

docker-up: ## Start all Docker services
	@echo "Starting Docker services..."
	docker-compose up -d
	@echo "✅ Services started"
	@echo "Frontend: http://localhost:3333"
	@echo "Backend: http://localhost:7777"
	@echo "Prometheus: http://localhost:9090"
	@echo "Grafana: http://localhost:4000"

docker-down: ## Stop all Docker services
	@echo "Stopping Docker services..."
	docker-compose down
	@echo "✅ Services stopped"

docker-rebuild: ## Rebuild and restart Docker services
	@echo "Rebuilding Docker services..."
	docker-compose down
	docker-compose build
	docker-compose up -d
	@echo "✅ Services rebuilt and started"

##@ Testing

test: ## Run backend unit tests
	@echo "Running backend tests..."
	cd backend && pytest
	@echo "✅ Tests passed"

e2e: ## Run E2E tests manually (requires e2e/ infrastructure)
	@echo "Running E2E tests..."
	@if [ ! -d "e2e" ]; then \
		echo "❌ e2e/ directory not found. Run 'make damonnator-infra' first to build test infrastructure."; \
		exit 1; \
	fi
	e2e/.venv/bin/python3 e2e/e2e_runner.py --test-suite e2e-tests.json --prd prd.json --output test-results.json
	@echo "✅ E2E tests complete. See test-results.json"

##@ Code Quality

lint: lint-backend lint-frontend ## Run all linters

lint-backend: ## Run backend linter (Ruff)
	@echo "Linting backend..."
	cd backend && ruff check .
	@echo "✅ Backend linting passed"

lint-frontend: ## Run frontend linter (ESLint)
	@echo "Linting frontend..."
	cd frontend && bun run lint
	@echo "✅ Frontend linting passed"

##@ Autonomous Loops

damonnator: ## Run development loop (builds product features from prd.json)
	@echo "🤖 Starting Damonnator development loop..."
	@echo "Building product features from prd.json"
	@echo "Press Ctrl+C to stop"
	./damonnator.sh

damonnator-test: ## Run testing loop (validates completed features)
	@echo "🧪 Starting Damonnator testing loop..."
	@echo "Validating completed features from prd.json"
	@echo "Press Ctrl+C to stop"
	@if [ ! -d "e2e" ]; then \
		echo "❌ e2e/ directory not found. Run 'make damonnator-infra' first to build test infrastructure."; \
		exit 1; \
	fi
	./damonnator_test.sh

damonnator-infra: ## Run infrastructure loop (builds test infrastructure from test-prd.json)
	@echo "🏗️  Starting Damonnator infrastructure loop..."
	@echo "Building E2E test infrastructure from test-prd.json"
	@echo "Press Ctrl+C to stop"
	./damonnator_infra.sh

damonnator-all: ## Run all loops in parallel (infra + dev + test)
	@echo "🚀 Starting all Damonnator loops in parallel..."
	@echo "Infrastructure: builds test framework"
	@echo "Development: builds product features"
	@echo "Testing: validates features"
	@echo "Press Ctrl+C to stop all"
	@trap 'kill 0' INT; \
	./damonnator_infra.sh & \
	./damonnator.sh & \
	sleep 30 && ./damonnator_test.sh & \
	wait

##@ Status

status: ## Show service status and PRD progress
	@echo "=========================================="
	@echo "📊 Policy Miner Status"
	@echo "=========================================="
	@echo ""
	@echo "🐳 Docker Services:"
	@docker-compose ps 2>/dev/null || echo "  Services not running (run 'make docker-up')"
	@echo ""
	@echo "📋 Product Features (prd.json):"
	@python3 -c "import json; data=json.load(open('prd.json')); total=len(data['stories']); done=sum(1 for s in data['stories'] if s.get('passes')); print(f'  Total: {total}'); print(f'  Completed: {done} ({done*100//total}%)'); print(f'  Remaining: {total-done}')"
	@echo ""
	@echo "🧪 Test Infrastructure (test-prd.json):"
	@python3 -c "import json; data=json.load(open('test-prd.json')); total=len(data['stories']); done=sum(1 for s in data['stories'] if s.get('passes')); print(f'  Total: {total}'); print(f'  Completed: {done} ({done*100//total}%)'); print(f'  Remaining: {total-done}')" 2>/dev/null || echo "  Not yet started"
	@echo ""
	@if [ -f "test-results.json" ]; then \
		echo "📊 Latest E2E Test Results:"; \
		python3 -c "import json; data=json.load(open('test-results.json')); s=data['summary']; print(f'  Passed: {s[\"passed\"]}'); print(f'  Failed: {s[\"failed\"]}'); print(f'  Pass Rate: {s[\"pass_rate\"]}%')"; \
		echo ""; \
	fi

##@ Cleanup

clean: ## Clean temporary files and caches
	@echo "Cleaning temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	rm -rf e2e/screenshots/*.png 2>/dev/null || true
	@echo "✅ Cleaned"
