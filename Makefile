# Makefile for SRE-Orchestrator

SERVICES := services/orchestrator services/k8s-agent

.PHONY: help build lint test run install

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  install                Install dependencies for all services"
	@echo "  lint                   Lint all services"
	@echo "  test                   Test all services"
	@echo "  build                  Build all services"
	@echo ""
	@echo "To run a command on a specific service:"
	@echo "  make -C <service_directory> <target>"
	@echo "  e.g.: make -C services/orchestrator run"


install lint test build:
	@for service in $(SERVICES); do \
		echo "Running '$@' for $$service..."; \
		$(MAKE) -C $$service $@; \
	done

run:
	@echo "Running multiple services from the root Makefile is not supported."
	@echo "Please run each service in a separate terminal:"
	@echo "  make -C services/orchestrator run"
	@echo "  make -C services/k8s-agent run"
