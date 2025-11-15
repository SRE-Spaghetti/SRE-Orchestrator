# Configuration Guide

## MCP Configuration Path

The orchestrator service now supports configurable MCP (Model Context Protocol) configuration file paths.

### How It Works

The service looks for the MCP configuration file in the following order:

1. **Environment Variable** (`MCP_CONFIG_PATH`) - Highest priority
2. **Docker/Kubernetes Mount** (`/config/mcp_config.yaml`) - For containerized deployments
3. **Default Location** (`./mcp_config.yaml`) - Project root

### Usage Examples

#### Local Development

```bash
# Use default location (./mcp_config.yaml)
make run

# Use custom path
MCP_CONFIG_PATH=/path/to/my/mcp_config.yaml make run

# Or set it in your .env file
echo "MCP_CONFIG_PATH=/path/to/my/mcp_config.yaml" >> .env
make run
```

#### Docker

```bash
# Mount custom config file
docker run \
  -v /host/path/to/mcp_config.yaml:/config/mcp_config.yaml \
  -e LLM_BASE_URL=https://api.openai.com/v1 \
  -e LLM_API_KEY=your-key \
  sre-orchestrator:latest

# Or use environment variable to specify a different path
docker run \
  -v /host/path/to/custom.yaml:/app/custom.yaml \
  -e MCP_CONFIG_PATH=/app/custom.yaml \
  -e LLM_BASE_URL=https://api.openai.com/v1 \
  -e LLM_API_KEY=your-key \
  sre-orchestrator:latest
```

#### Kubernetes

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-config
data:
  mcp_config.yaml: |
    local-tools:
      command: "npx"
      args:
        - "mcp-server-kubernetes"
      transport: "stdio"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sre-orchestrator
spec:
  template:
    spec:
      containers:
      - name: orchestrator
        image: sre-orchestrator:latest
        env:
        - name: MCP_CONFIG_PATH
          value: "/config/mcp_config.yaml"
        volumeMounts:
        - name: mcp-config
          mountPath: /config
      volumes:
      - name: mcp-config
        configMap:
          name: mcp-config
```

#### Multiple Environments

```bash
# Development
export MCP_CONFIG_PATH=./config/mcp_dev.yaml
make run

# Staging
export MCP_CONFIG_PATH=./config/mcp_staging.yaml
make run

# Production
export MCP_CONFIG_PATH=./config/mcp_prod.yaml
make run
```

### Benefits

- **Flexibility**: Use different MCP configurations for different environments
- **Security**: Keep sensitive configurations outside the codebase
- **CI/CD**: Easily inject configurations during deployment
- **Testing**: Use test-specific MCP configurations without modifying defaults

### Validation

The service logs the MCP configuration path on startup:

```
INFO - Using MCP configuration from: /path/to/mcp_config.yaml
INFO - Loading MCP tool configuration from /path/to/mcp_config.yaml
```

Check the logs to verify the correct configuration file is being used.
