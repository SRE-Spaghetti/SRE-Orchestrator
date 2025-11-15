# CI/CD Pipeline

This directory contains GitHub Actions workflows for the SRE Orchestrator project.

## Workflows

### CI/CD Pipeline (`ci.yml`)

The main CI/CD pipeline runs on push and pull requests to `main` and `develop` branches.

#### Jobs

1. **orchestrator-test**: Tests the orchestrator service
   - Runs linting with Ruff
   - Runs formatting checks with Black
   - Runs unit, integration, and e2e tests with pytest
   - Uploads coverage reports

2. **cli-test**: Tests the CLI application
   - Runs linting with Ruff
   - Runs formatting checks with Black
   - Runs CLI tests with pytest
   - Uploads coverage reports

3. **orchestrator-build**: Builds the orchestrator Docker image
   - Builds Docker image using BuildKit
   - Runs Trivy security scanning
   - Uploads security scan results to GitHub Security

4. **cli-build**: Builds the CLI distribution package
   - Builds wheel and source distribution
   - Uploads artifacts for deployment

## Required Secrets

Configure these secrets in your GitHub repository settings:

- `REGISTRY_URL`: Container registry URL (e.g., `ghcr.io/your-org`)
- `REGISTRY_USERNAME`: Container registry username
- `REGISTRY_PASSWORD`: Container registry password or token
- `PYPI_TOKEN`: PyPI API token for publishing CLI package (optional)

## Architecture Changes

This CI/CD pipeline reflects the refactored architecture:

- **Removed**: k8s-agent build and test jobs (service eliminated)
- **Added**: CLI build and test jobs
- **Updated**: Orchestrator tests now include LangChain/LangGraph components
- **Updated**: Docker build uses optimized Dockerfile with new dependencies

## Local Testing

Run the same checks locally before pushing:

```bash
# Test orchestrator
make -C services/orchestrator lint
make -C services/orchestrator test

# Test CLI
make -C cli lint
make -C cli test

# Build Docker image
make docker-build

# Build CLI package
make -C cli build
```

## Notes

- The pipeline uses Poetry for dependency management
- Docker images are cached using GitHub Actions cache
- Security scanning is performed on all Docker images
- Coverage reports are uploaded to Codecov (optional)
