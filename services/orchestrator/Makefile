
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
	@echo "Go to localhost:8000/redoc"
	@poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

lint:
	@echo "Linting code with Ruff..."
	@poetry run ruff check .

test:
	@echo "Running tests with Pytest..."
	@poetry run pytest

docker-build: lint format security
	@echo "Building Docker image sre-orchestrator:latest..."
	@docker build -t sre-orchestrator:latest .
	@trivy image -q --severity HIGH,CRITICAL sre-orchestrator:latest
	@echo Image OK: sre-orchestrator:latest

format:
	@echo "Formatting code with Black..."
	@poetry run black .

lock:
	@echo "Generating poetry.lock file..."
	@poetry lock

security:
	@echo "Running trivy filesystem scan..."
	trivy fs .