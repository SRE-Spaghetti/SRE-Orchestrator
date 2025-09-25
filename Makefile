# Makefile for SRE-Orchestrator

# Variables
SERVICE_DIR := services/k8s-agent
IMAGE_NAME := sre-orchestrator
TAG := latest
PYTHON_VERSION := 3.11

.PHONY: help build lint test run install

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  install                Install dependencies using Poetry. Poetry >= 2.2.1 must be already installed."
	@echo "  run                    Run the FastAPI application with Uvicorn"
	@echo "  lint                   Lint the code with Ruff"
	@echo "  test                   Run tests with Pytest"
	@echo "  build                  Build the Docker image. Docker must be already installed."


install:
	@echo "Installing dependencies from poetry.lock..."
	@cd $(SERVICE_DIR) && poetry install

run:
	@echo "Starting Uvicorn server..."
	@echo "Go to localhost:8000/redoc"
	@cd $(SERVICE_DIR) && poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

lint:
	@echo "Linting code with Ruff..."
	@cd $(SERVICE_DIR) && poetry run ruff check .

test:
	@echo "Running tests with Pytest..."
	@cd $(SERVICE_DIR) && poetry run pytest

build:
	@echo "Building Docker image $(IMAGE_NAME):$(TAG)..."
	@docker build -t $(IMAGE_NAME):$(TAG) $(SERVICE_DIR)

