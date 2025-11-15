
IMAGE_NAME ?= sre-orchestrator
IMAGE_TAG ?= latest

# Load environment variables from .env file if it exists
-include .env
export

.PHONY: help docker-build lint test run install format lock install-tools env-check

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  install-tools          Install development tools like trivy."
	@echo "  install                Install dependencies using Poetry. Poetry >= 2.2.1 must be already installed."
	@echo "  env-check              Check if required environment variables are set"
	@echo "  run                    Run the FastAPI application with Uvicorn"
	@echo "  lint                   Lint the code with Ruff"
	@echo "  test                   Run tests with Pytest"
	@echo "  docker-build           Build the Docker image. Docker must be already installed."
	@echo "  format                 Format the code with Black."
	@echo "  lock                   Generate poetry.lock file."

env-check:
	@echo "Checking required environment variables..."
	@test -n "$(LLM_BASE_URL)" || (echo "ERROR: LLM_BASE_URL not set. Copy .env.example to .env and configure it." && exit 1)
	@test -n "$(LLM_API_KEY)" || (echo "ERROR: LLM_API_KEY not set. Copy .env.example to .env and configure it." && exit 1)
	@echo "✓ Required environment variables are set"
	@echo "  LLM_BASE_URL: $(LLM_BASE_URL)"
	@echo "  LLM_MODEL_NAME: $(or $(LLM_MODEL_NAME),gpt-4 (default))"


install:
	@echo "Installing dependencies from poetry.lock..."
	@poetry install

install-tools:
	@if command -v brew > /dev/null; then \
		echo "Installing tools with Homebrew..."; \
		brew install trivy; \
	else \
		echo "Homebrew not found. Please install trivy manually."; \
	fi

run: env-check
	@echo "Starting Uvicorn server..."
	@echo "Go to localhost:8000/redoc"
	@poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir src

lint:
	@echo "Linting code with Ruff..."
	@poetry run ruff check .

test:
	@echo "Running tests with Pytest..."
	@poetry run pytest

docker-build: lint format security
	@echo "Building Docker image sre-orchestrator:latest..."
	@docker build -t sre-orchestrator:latest -f Dockerfile ../..
	@if ! command -v trivy > /dev/null; then \
		echo "Trivy not found, skipping image scan."; \
	else \
		trivy image -q --severity HIGH,CRITICAL sre-orchestrator:latest; \
	fi
	@echo Image OK: sre-orchestrator:latest

format:
	@echo "Formatting code with Black..."
	@poetry run black .

lock:
	@echo "Generating poetry.lock file..."
	@poetry lock

security:
	@if ! command -v trivy > /dev/null; then \
		echo "Trivy not found, skipping security scan."; \
	else \
		echo "Running trivy filesystem scan..."; \
		trivy fs .; \
	fi

kind-load: docker-build
	@echo "Loading image into kind..."
	@kind load docker-image $(IMAGE_NAME):$(IMAGE_TAG)