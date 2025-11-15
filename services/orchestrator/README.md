# SRE Orchestrator Service

FastAPI-based orchestrator service for SRE incident management and investigation.

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
