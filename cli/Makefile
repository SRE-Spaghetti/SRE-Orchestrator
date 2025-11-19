.PHONY: help install test lint format build clean

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  install                Install dependencies using Poetry"
	@echo "  test                   Run tests with Pytest"
	@echo "  lint                   Lint the code with Ruff"
	@echo "  format                 Format the code with Black"
	@echo "  build                  Build distribution package"
	@echo "  clean                  Clean build artifacts"

install:
	@echo "Installing CLI dependencies..."
	@poetry install

test:
	@echo "Running CLI tests..."
	@poetry run pytest

lint:
	@echo "Linting CLI code..."
	@poetry run ruff check .

format:
	@echo "Formatting CLI code..."
	@poetry run black .

build:
	@echo "Building CLI distribution package..."
	@poetry build

clean:
	@echo "Cleaning build artifacts..."
	@rm -rf dist/ build/ *.egg-info
