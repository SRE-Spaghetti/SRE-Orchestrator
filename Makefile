# Makefile for SRE-Orchestrator

SERVICES := services/orchestrator services/k8s-agent

.PHONY: help docker-build lint test run install format lock security kind-load
.SHELLFLAGS := -ec

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  install                Install dependencies for all services"
	@echo "  lint                   Lint all services"
	@echo "  test                   Test all services"
	@echo "  docker-build           Build all services"
	@echo "  format                 Format all services"
	@echo "  lock                   Generate poetry.lock for all services"
	@echo "  security               Run trivy filesystem scan"
	@echo "  kind-load              Load docker images into kind for all services"
	@echo ""
	@echo "To run a command on a specific service:"
	@echo "  make -C <service_directory> <target>"
	@echo "  e.g.: make -C services/orchestrator run"


install lint test docker-build format lock security kind-load:
	@for service in $(SERVICES); do \
		echo "Running '$@' for $$service..."; \
		$(MAKE) -C $$service $@; \
	done

run:
	@echo "Running multiple services from the root Makefile is not supported."
	@echo "Please run each service in a separate terminal:"
	@echo "  make -C services/orchestrator run"
	@echo "  make -C services/k8s-agent run"

