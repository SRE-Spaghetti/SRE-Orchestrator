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

## Docker

```bash
# Build Docker image
make docker-build

# The image expects MCP config at /config/mcp_config.yaml
# Mount your config file when running:
docker run -v /path/to/mcp_config.yaml:/config/mcp_config.yaml sre-orchestrator:latest
```
