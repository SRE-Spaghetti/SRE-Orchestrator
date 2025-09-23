# Test Strategy and Standards

### Testing Philosophy

- **Approach:** Test-After. While Test-Driven Development (TDD) is valuable, a test-after approach is more pragmatic for the initial rapid prototyping and development phase of this project.
- **Coverage Goals:** A project-wide target of 80% line coverage is required. This will be enforced in the CI pipeline.
- **Test Pyramid:** We will follow a standard test pyramid approach, with a large base of fast unit tests, a smaller layer of integration tests, and a minimal set of end-to-end tests for critical user journeys.

### Test Types and Organization

#### Unit Tests
- **Framework:** `pytest`
- **File Convention:** `test_*.py` inside the `tests/` directory of each service.
- **Location:** `services/*/tests/unit/`
- **Mocking Library:** `unittest.mock`
- **Coverage Requirement:** 80%

**AI Agent Requirements:**
- Generate tests for all public methods.
- Cover edge cases and error conditions.
- Follow AAA pattern (Arrange, Act, Assert).
- Mock all external dependencies (e.g., other services, databases, external APIs).

#### Integration Tests
- **Scope:** Testing the interaction between the Orchestrator service and the Kubernetes Agent, and between the services and external APIs (like the Kubernetes API).
- **Location:** `services/*/tests/integration/`
- **Test Infrastructure:**
    - **Kubernetes:** A real Kubernetes cluster (e.g., `kind` or `k3s`) will be used for integration tests in the CI pipeline.
    - **External APIs:** `pytest-httpserver` or a similar library will be used to mock the LLM API.

#### End-to-End Tests
- **Framework:** `pytest` with `requests` library.
- **Scope:** Testing the full user journey from creating an incident via the public REST API to retrieving the final report.
- **Environment:** These tests will run against the `staging` environment.
- **Test Data:** Pre-defined incident descriptions will be used to trigger different investigation scenarios.

### Test Data Management

- **Strategy:** Test data will be managed within the test files themselves for simplicity.
- **Fixtures:** `pytest` fixtures will be used to create reusable test data and resources.
- **Factories:** Not planned for the MVP.
- **Cleanup:** The test environment (e.g., the `kind` cluster) will be created and destroyed for each CI run to ensure a clean state.

### Continuous Testing

- **CI Integration:** The CI pipeline will run all unit and integration tests on every commit to the `main` branch.
- **Performance Tests:** Not planned for the MVP.
- **Security Tests:** A static analysis security testing (SAST) tool like `bandit` will be integrated into the CI pipeline.
