# SRE Orchestrator Service

FastAPI-based orchestrator service for SRE incident management and investigation using native LangGraph StateGraph implementation.

## Architecture

The SRE Orchestrator uses a **native LangGraph StateGraph** implementation for autonomous incident investigation. This provides:

- **Explicit Control**: Clear definition of workflow nodes, edges, and routing logic
- **Extensibility**: Easy to add custom nodes (validation, human-in-the-loop, etc.)
- **Observability**: Comprehensive logging at each node transition with correlation IDs
- **Flexibility**: Customizable routing logic and state management
- **ReAct Pattern**: Alternates between reasoning (LLM) and acting (tool execution)

The investigation workflow consists of:
1. **Agent Node**: LLM analyzes the incident and decides on actions
2. **Tool Node**: Executes MCP tools to gather evidence
3. **Routing Logic**: Determines whether to continue with tools or complete investigation

For detailed architecture documentation, see [docs/langgraph-workflow.md](../../docs/langgraph-workflow.md).

For production deployment and monitoring guidance, see [docs/native-langgraph-deployment-guide.md](../../docs/native-langgraph-deployment-guide.md).

## Configuration

### MCP Configuration Path

The MCP (Model Context Protocol) configuration file path can be customized using the `MCP_CONFIG_PATH` environment variable.

**Priority order:**
1. `MCP_CONFIG_PATH` environment variable (if set)
2. `/config/mcp_config.yaml` (Docker/Kubernetes mount location)
3. `./mcp_config.yaml` (default, relative to project root)

**Usage examples:**

```bash
# Use default location (./mcp_config.yaml)
make run

# Use custom path via environment variable
MCP_CONFIG_PATH=/path/to/custom/mcp_config.yaml make run

# Or export it first
export MCP_CONFIG_PATH=/path/to/custom/mcp_config.yaml
make run

# With uvicorn directly
MCP_CONFIG_PATH=/custom/path.yaml poetry run uvicorn app.main:app --reload --app-dir src
```

### Environment Variables

Required:
- `LLM_BASE_URL` - Base URL for the LLM API
- `LLM_API_KEY` - API key for LLM authentication

Optional:
- `MCP_CONFIG_PATH` - Path to MCP configuration file
- `LLM_MODEL_NAME` - LLM model name (default: `gpt-4`)
- `LLM_TEMPERATURE` - Temperature for LLM responses (default: `0.7`)
- `LLM_MAX_TOKENS` - Maximum tokens for LLM responses (default: `4096`)

Copy `.env.example` to `.env` and configure as needed.

## Development

```bash
# Install dependencies
make install

# Run the service
make run

# Run tests
make test

# Lint code
make lint

# Format code
make format
```

## Testing

The orchestrator service has comprehensive unit test coverage for all core components, services, models, and API endpoints.

### Running Tests

```bash
# Run all tests
make test

# Run tests with verbose output
poetry run pytest tests/ -v

# Run specific test file
poetry run pytest tests/unit/core/test_incident_repository.py -v

# Run tests with coverage report
poetry run pytest --cov=app --cov-report=term --cov-report=xml

# Run tests and show slowest durations
poetry run pytest --durations=10
```

### Test Structure

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── fixtures/                      # Reusable test fixtures
│   ├── incident_fixtures.py       # Incident-related test data
│   ├── mcp_fixtures.py            # MCP tool mocks
│   └── llm_fixtures.py            # LLM response mocks
└── unit/                          # Unit tests
    ├── api/                       # API endpoint tests
    ├── core/                      # Core business logic tests
    ├── services/                  # Service layer tests
    └── test_models.py             # Data model tests
```

### Coverage Requirements

The test suite maintains high coverage standards:
- Overall target: 85%
- Models: 95%
- API endpoints: 90%
- Core logic: 85-90%
- Services: 85%

Current coverage for tested modules:
- `api/v1/incidents.py`: 100%
- `core/incident_repository.py`: 86%
- `core/investigation_agent.py`: 90%
- `core/retry_utils.py`: 100%
- `models/incidents.py`: 100%
- `services/knowledge_graph_service.py`: 100%
- `services/mcp_config_service.py`: 97%
- `services/mcp_tool_manager.py`: 100%

### Test Fixtures

The test suite provides reusable fixtures for common testing scenarios:

#### Incident Fixtures
```python
@pytest.fixture
def sample_incident() -> Incident
    """Provides a sample incident for testing"""

@pytest.fixture
def sample_incident_dict() -> Dict[str, Any]
    """Provides incident data as dictionary for API tests"""
```

#### MCP Fixtures
```python
@pytest.fixture
def mock_mcp_tool(mocker)
    """Mock MCP tool for testing without actual tool execution"""

@pytest.fixture
def mock_mcp_config() -> Dict[str, Any]
    """Provides mock MCP configuration"""
```

#### LLM Fixtures
```python
@pytest.fixture
def mock_llm(mocker)
    """Mock ChatOpenAI for testing without actual LLM calls"""

@pytest.fixture
def mock_llm_response() -> Any
    """Provides mock LLM response with tool calls"""
```

### Writing New Tests

When adding new tests, follow these guidelines:

1. **Test Naming**: Use descriptive names that explain what is being tested
   ```python
   def test_create_incident_sync_creates_pending_incident()
   def test_investigate_incident_async_handles_llm_failure()
   ```

2. **AAA Pattern**: Structure tests with Arrange, Act, Assert
   ```python
   def test_example():
       # Arrange: Set up test data and mocks
       incident = Incident(description="Test")

       # Act: Execute the function under test
       result = function_under_test(incident)

       # Assert: Verify the expected outcome
       assert result.status == "completed"
   ```

3. **Use Fixtures**: Leverage existing fixtures for common setup
   ```python
   def test_with_fixture(sample_incident, mock_llm):
       result = investigate(sample_incident, mock_llm)
       assert result is not None
   ```

4. **Mock External Dependencies**: Never make real network calls or external service calls
   ```python
   @pytest.fixture
   def mock_external_service(mocker):
       return mocker.patch('app.services.external.call_api')
   ```

5. **Test Edge Cases**: Include tests for error scenarios and boundary conditions
   ```python
   def test_handles_empty_input()
   def test_handles_invalid_status()
   def test_handles_llm_timeout()
   ```

### Performance

The test suite is optimized for fast execution:
- All external dependencies are mocked
- No network calls or file I/O (except tmp_path)
- Current execution time: ~10 seconds for 173 tests
- Target: < 30 seconds for full suite

## Docker

```bash
# Build Docker image
make docker-build

# The image expects MCP config at /config/mcp_config.yaml
# Mount your config file when running:
docker run -v /path/to/mcp_config.yaml:/config/mcp_config.yaml sre-orchestrator:latest
```
