# Makefile for k8s-agent service


.PHONY: help docker-build lint test run install format lock

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  install                Install dependencies using Poetry. Poetry >= 2.2.1 must be already installed."
	@echo "  run                    Run the FastAPI application with Uvicorn"
	@echo "  lint                   Lint the code with Ruff"
	@echo "  test                   Run tests with Pytest"
	@echo "  docker-build           Build the Docker image. Docker must be already installed."
	@echo "  format                 Format the code with Black."
	@echo "  lock                   Generate poetry.lock file."


install:
	@echo "Installing dependencies from poetry.lock..."
	@poetry install

run:
	@echo "Starting Uvicorn server..."
	@echo "Go to localhost:8001/redoc"
	@poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

lint:
	@echo "Linting code with Ruff..."
	@poetry run ruff check .

test:
	@echo "Running tests with Pytest..."
	@poetry run pytest

docker-build:
	@echo "Building Docker image k8s-agent:latest..."
	@docker build -t k8s-agent:latest .
	@trivy image -q --severity HIGH,CRITICAL k8s-agent:latest
	@echo Image OK: sre-orchestrator:latest

format:
	@echo "Formatting code with Black..."
	@poetry run black .

lock:
	@echo "Generating poetry.lock file..."
	@poetry lock
