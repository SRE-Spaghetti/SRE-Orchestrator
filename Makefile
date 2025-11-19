# Makefile for SRE-Orchestrator

# Note: k8s-agent service removed in refactoring - now using MCP servers
SERVICES := services/orchestrator
CLI := cli

.PHONY: help docker-build lint test run install format lock security kind-load cli-install cli-test
.SHELLFLAGS := -ec

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  install                Install dependencies for orchestrator service"
	@echo "  lint                   Lint orchestrator service"
	@echo "  test                   Test orchestrator service"
	@echo "  docker-build           Build orchestrator Docker image"
	@echo "  format                 Format orchestrator service"
	@echo "  lock                   Generate poetry.lock for orchestrator"
	@echo "  security               Run trivy filesystem scan"
	@echo "  kind-load              Load docker images into kind"
	@echo "  cli-install            Install CLI dependencies"
	@echo "  cli-test               Test CLI"
	@echo ""
	@echo "To run a command on a specific service:"
	@echo "  make -C <service_directory> <target>"
	@echo "  e.g.: make -C services/orchestrator run"


install lint test docker-build format lock security kind-load:
	@for service in $(SERVICES); do \
		echo "Running '$@' for $$service..."; \
		$(MAKE) -C $$service $@; \
	done

cli-install:
	@echo "Installing CLI dependencies..."
	@$(MAKE) -C $(CLI) install

cli-test:
	@echo "Testing CLI..."
	@$(MAKE) -C $(CLI) test

run:
	@echo "Starting orchestrator service..."
	@echo "Run: make -C services/orchestrator run"
