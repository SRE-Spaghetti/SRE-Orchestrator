# SRE Orchestrator - Configuration Guide

## Overview

The SRE Orchestrator service requires configuration for LLM integration and optional MCP server connections.

## Required Environment Variables

### LLM Configuration

The service uses LangChain to interact with OpenAI-compatible LLM endpoints. Configure these environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_BASE_URL` | **Yes** | - | Base URL for the OpenAI-compatible API endpoint (e.g., `https://api.openai.com/v1`) |
| `LLM_API_KEY` | **Yes** | - | API key for authentication |
| `LLM_MODEL_NAME` | No | `gpt-4` | Model name (e.g., `gpt-4`, `gpt-4-turbo`, `gemini-2.5-flash`) |
| `LLM_TEMPERATURE` | No | `0.7` | Temperature for response generation (0.0-1.0) |
| `LLM_MAX_TOKENS` | No | `2000` | Maximum number of tokens in the response |

**Source**: [`src/app/services/langchain_llm_client.py:87-104`](src/app/services/langchain_llm_client.py#L87-L104)

## Configuration Files

### 1. Environment Variables (`.env`)

Create a `.env` file in the `services/orchestrator` directory:

```bash
# Copy the example file
cp .env.example .env

# Edit with your configuration
vim .env
```

**Example `.env` file:**
```bash
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-api-key-here
LLM_MODEL_NAME=gpt-4
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
```

### 2. MCP Configuration (`mcp_config.yaml`)

The orchestrator uses the `langchain-mcp-adapters` library to connect to multiple MCP servers and access their tools. MCP servers provide capabilities like Kubernetes data collection, metrics querying, and other operational tools.

**Configuration file location**:
- Container: `/config/mcp_config.yaml`
- Local: `./mcp_config.yaml`

**Source**: [`src/app/main.py:49-53`](src/app/main.py#L49-L53)

#### Transport Types

##### 1. HTTP Transport (`streamable_http`)

Use this for MCP servers accessible via HTTP/HTTPS endpoints.

**Required Fields:**
- `url`: The HTTP endpoint URL of the MCP server
- `transport`: Must be set to `"streamable_http"`

**Optional Fields:**
- `headers`: Dictionary of HTTP headers (useful for authentication)

**Example:**
```yaml
kubernetes:
  url: "http://kubernetes-mcp-server:8080/mcp"
  transport: "streamable_http"
  headers:
    Authorization: "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    X-Custom-Header: "value"
```

##### 2. Stdio Transport (`stdio`)

Use this for MCP servers that run as local processes and communicate via stdin/stdout.

**Required Fields:**
- `command`: The command to execute (e.g., `"python"`, `"node"`, `"/usr/bin/mcp-server"`)
- `args`: List of command-line arguments
- `transport`: Must be set to `"stdio"`

**Optional Fields:**
- `env`: Dictionary of environment variables to set for the process

**Example:**
```yaml
local-tools:
  command: "python"
  args:
    - "/opt/mcp-servers/local_tools.py"
    - "--verbose"
  transport: "stdio"
  env:
    LOG_LEVEL: "DEBUG"
    DATA_DIR: "/var/data"
```

#### Complete Configuration Examples

**Single Kubernetes MCP Server:**
```yaml
kubernetes:
  url: "http://k8s-mcp-server.default.svc.cluster.local:8080/mcp"
  transport: "streamable_http"
```

**Multiple MCP Servers:**
```yaml
kubernetes:
  url: "http://k8s-mcp-server:8080/mcp"
  transport: "streamable_http"
  headers:
    Authorization: "Bearer ${K8S_TOKEN}"

prometheus:
  url: "http://prometheus-mcp-server:9090/mcp"
  transport: "streamable_http"

local-diagnostics:
  command: "python"
  args:
    - "/opt/mcp-servers/diagnostics.py"
  transport: "stdio"
  env:
    LOG_LEVEL: "INFO"
```

**Development Setup with Local Servers:**
```yaml
dev-k8s:
  command: "python"
  args:
    - "-m"
    - "k8s_mcp_server"
    - "--kubeconfig"
    - "${HOME}/.kube/config"
  transport: "stdio"
  env:
    PYTHONPATH: "/workspace/mcp-servers"
```

#### Environment Variables in MCP Config

You can use environment variables in the configuration file using the `${VAR_NAME}` syntax. This is useful for:
- API tokens and credentials
- Dynamic URLs
- User-specific paths

**Example:**
```yaml
kubernetes:
  url: "${K8S_MCP_URL}"
  transport: "streamable_http"
  headers:
    Authorization: "Bearer ${K8S_API_TOKEN}"
```

Then set the environment variables:
```bash
export K8S_MCP_URL="http://k8s-mcp-server:8080/mcp"
export K8S_API_TOKEN="your-token-here"
```

#### Tool Discovery

Once configured, the orchestrator will automatically:
1. Connect to all configured MCP servers on startup
2. Discover available tools from each server
3. Make tools available to the LangGraph agent

You can check tool availability via the health endpoint:
```bash
curl http://localhost:8000/health
```

### 3. Knowledge Graph (`knowledge_graph.yaml`)

Define service metadata and relationships:

```yaml
components:
  - name: orchestrator-service
    type: service
    relationships: []
  - name: database
    type: datastore
    relationships:
      - depends_on: orchestrator-service
```

**Source**: [`src/app/main.py:35-38`](src/app/main.py#L35-L38)

## Running the Service

### Local Development

1. **Check environment variables**:
   ```bash
   make env-check
   ```

2. **Run the service**:
   ```bash
   make run
   # Or use poetry directly:
   poetry run dev
   # Or use uvicorn directly:
   poetry run uvicorn app.main:app --reload --app-dir src
   ```

3. **Access the API**:
   - API Documentation: http://localhost:8000/redoc
   - Health Check: http://localhost:8000/health

### Docker Deployment

When running in Docker, set environment variables in your deployment configuration:

**Docker Compose:**
```yaml
services:
  orchestrator:
    image: sre-orchestrator:latest
    environment:
      - LLM_BASE_URL=https://api.openai.com/v1
      - LLM_API_KEY=sk-your-api-key-here
      - LLM_MODEL_NAME=gpt-4
    volumes:
      - ./mcp_config.yaml:/config/mcp_config.yaml
    ports:
      - "8000:80"
```

**Kubernetes:**

1. **Create ConfigMap for MCP configuration:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-config
data:
  mcp_config.yaml: |
    kubernetes:
      url: "http://k8s-mcp-server:8080/mcp"
      transport: "streamable_http"
```

2. **Create Secret for credentials:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: orchestrator-secrets
type: Opaque
stringData:
  llm-api-key: sk-your-api-key-here
  k8s-token: your-k8s-mcp-token-here
```

3. **Deploy orchestrator:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orchestrator
spec:
  template:
    spec:
      containers:
      - name: orchestrator
        image: sre-orchestrator:latest
        env:
        - name: LLM_BASE_URL
          value: "https://api.openai.com/v1"
        - name: LLM_API_KEY
          valueFrom:
            secretKeyRef:
              name: orchestrator-secrets
              key: llm-api-key
        - name: LLM_MODEL_NAME
          value: "gpt-4"
        - name: K8S_API_TOKEN
          valueFrom:
            secretKeyRef:
              name: orchestrator-secrets
              key: k8s-token
        volumeMounts:
        - name: mcp-config
          mountPath: /config
      volumes:
      - name: mcp-config
        configMap:
          name: mcp-config
```

## Health Check

The service exposes a `/health` endpoint that returns detailed status information:

```bash
curl http://localhost:8000/health
```

**Response structure:**
```json
{
  "status": "ok",
  "timestamp": "2025-01-14T12:00:00",
  "components": {
    "langchain_llm": {
      "status": "healthy",
      "model": "gpt-4",
      "base_url": "https://api.openai.com/v1"
    },
    "mcp_tools": {
      "status": "healthy",
      "tool_count": 5,
      "tools": ["get_pod_details", "get_pod_logs", ...]
    },
    "investigation_agent": {
      "status": "ready",
      "message": "Agent can be created on-demand"
    }
  }
}
```

**Source**: [`src/app/main.py:112-251`](src/app/main.py#L112-L251)

## Troubleshooting

### "LLM_BASE_URL environment variable not set"

**Solution**: Create a `.env` file with the required variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

### "Failed to initialize LangChain LLM client"

**Possible causes**:
1. Invalid API key
2. Wrong base URL
3. Network connectivity issues

**Check the logs** for detailed error messages and verify your configuration.

### "MCP Tool Manager not initialized"

**Possible causes**:
1. Invalid `mcp_config.yaml` format
2. MCP server not accessible
3. Authentication issues

**Solution**: Check the MCP configuration and ensure servers are reachable.

### MCP Connection Failures

If the orchestrator fails to connect to an MCP server:

1. **Check the logs:**
   ```bash
   kubectl logs deployment/orchestrator | grep MCP
   ```

2. **Verify the server is running:**
   ```bash
   curl http://k8s-mcp-server:8080/health
   ```

3. **Check network connectivity:**
   ```bash
   kubectl exec deployment/orchestrator -- curl http://k8s-mcp-server:8080/mcp
   ```

### No Tools Available

If no tools are discovered:

1. **Verify the MCP server implements the tools/list endpoint**
2. **Check the server logs for errors**
3. **Ensure the transport type matches the server implementation**

### Authentication Errors

If you get authentication errors:

1. **Verify the token/credentials are correct**
2. **Check the header format matches the server's expectations**
3. **Ensure environment variables are properly set**

## Development Tips

1. **Use environment-specific configurations**:
   - `.env.development` - Local development
   - `.env.staging` - Staging environment
   - `.env.production` - Production (use secrets management)

2. **Test configuration**:
   ```bash
   make env-check
   curl http://localhost:8000/health
   ```

3. **Enable debug logging** (add to `.env`):
   ```bash
   LOG_LEVEL=DEBUG
   ```

## Best Practices

1. **Use environment variables** for sensitive data (tokens, passwords)
2. **Use descriptive server names** in MCP config that indicate their purpose
3. **Document custom tools** provided by your MCP servers
4. **Monitor connection health** via the health endpoint
5. **Test configuration changes** in a development environment first
6. **Keep credentials secure** using Kubernetes Secrets or similar
7. **Use HTTPS** for production MCP servers when possible
8. **Use environment-specific configurations**:
   - `.env.development` - Local development
   - `.env.staging` - Staging environment
   - `.env.production` - Production (use secrets management)

## Security Notes

- **Never commit `.env` files** to version control
- Use secrets management systems (Kubernetes Secrets, AWS Secrets Manager, etc.) in production
- Rotate API keys regularly
- Use HTTPS for all external API endpoints
- Limit API key permissions to minimum required scope

## Adding Custom MCP Servers

To add a custom MCP server:

1. **Implement the MCP protocol** in your server
2. **Add the server configuration** to `mcp_config.yaml`
3. **Restart the orchestrator** to load the new configuration
4. **Verify tools are discovered** via the health endpoint

## References

- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [langchain-mcp-adapters Documentation](https://github.com/langchain-ai/langchain-mcp-adapters)
- [LangChain Tools Documentation](https://python.langchain.com/docs/modules/tools/)
