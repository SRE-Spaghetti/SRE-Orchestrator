# MCP Configuration Guide

This guide explains how to configure MCP (Model Context Protocol) servers for the SRE Orchestrator.

## Overview

The orchestrator uses the `langchain-mcp-adapters` library to connect to multiple MCP servers and access their tools. MCP servers provide capabilities like Kubernetes data collection, metrics querying, and other operational tools.

## Configuration File

The MCP configuration is stored in `mcp_config.yaml`. This file defines all MCP servers that the orchestrator will connect to.

## Configuration Format

The configuration file uses YAML format with server names as keys and connection details as values:

```yaml
server-name:
  transport: "streamable_http" | "stdio"
  # Additional fields depend on transport type
```

## Transport Types

### 1. HTTP Transport (`streamable_http`)

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

### 2. Stdio Transport (`stdio`)

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

## Complete Configuration Examples

### Example 1: Single Kubernetes MCP Server

```yaml
kubernetes:
  url: "http://k8s-mcp-server.default.svc.cluster.local:8080/mcp"
  transport: "streamable_http"
```

### Example 2: Multiple MCP Servers

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

### Example 3: Development Setup with Local Servers

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

## Environment Variables

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

## Kubernetes Deployment

When deploying to Kubernetes, you can:

1. **Mount the config file as a ConfigMap:**

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

2. **Use environment variables with Secrets:**

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mcp-credentials
type: Opaque
stringData:
  k8s-token: "your-token-here"
---
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: orchestrator
        env:
        - name: K8S_API_TOKEN
          valueFrom:
            secretKeyRef:
              name: mcp-credentials
              key: k8s-token
```

## Tool Discovery

Once configured, the orchestrator will automatically:
1. Connect to all configured MCP servers on startup
2. Discover available tools from each server
3. Make tools available to the LangGraph agent

You can check tool availability via the health endpoint:

```bash
curl http://localhost:8000/health
```

Response:

```json
{
  "status": "ok",
  "mcp_tools": {
    "status": "initialized",
    "tool_count": 5,
    "tools": [
      "get_pod_details",
      "get_pod_logs",
      "list_pods",
      "get_events",
      "get_resource_usage"
    ]
  }
}
```

## Troubleshooting

### Connection Failures

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

## Adding Custom MCP Servers

To add a custom MCP server:

1. **Implement the MCP protocol** in your server
2. **Add the server configuration** to `mcp_config.yaml`
3. **Restart the orchestrator** to load the new configuration
4. **Verify tools are discovered** via the health endpoint

## Best Practices

1. **Use environment variables** for sensitive data (tokens, passwords)
2. **Use descriptive server names** that indicate their purpose
3. **Document custom tools** provided by your MCP servers
4. **Monitor connection health** via the health endpoint
5. **Test configuration changes** in a development environment first
6. **Keep credentials secure** using Kubernetes Secrets
7. **Use HTTPS** for production MCP servers when possible

## References

- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [langchain-mcp-adapters Documentation](https://github.com/langchain-ai/langchain-mcp-adapters)
- [LangChain Tools Documentation](https://python.langchain.com/docs/modules/tools/)
