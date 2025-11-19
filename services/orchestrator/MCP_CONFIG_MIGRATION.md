# MCP Configuration Migration Guide

## Summary of Changes

The MCP configuration system has been updated to use a consistent dictionary-based format that's compatible with `MultiServerMCPClient` from `langchain-mcp-adapters`.

## What Changed

### 1. Configuration Format

**Old Format (Legacy):**
```yaml
mcp_servers:
  - server_url: "kubernetes-mcp-server:8080"
    transport_type: "http"
    authentication:
      username: "user"
      password: "pass"
```

**New Format (Current):**
```yaml
# Dictionary with server names as keys
local-tools:
  command: "npx"
  args:
    - "mcp-server-kubernetes"
  transport: "stdio"

kubernetes:
  url: "http://kubernetes-mcp-server:8080/mcp"
  transport: "streamable_http"
  headers:
    Authorization: "Bearer YOUR_TOKEN"
```

### 2. Transport Types

**Supported transports:**
- `stdio`: For local MCP servers running as processes
  - Required: `command`, `args`, `transport`
  - Optional: `env` (environment variables)

- `streamable_http`: For HTTP-based MCP servers
  - Required: `url`, `transport`
  - Optional: `headers` (for authentication)

### 3. Code Changes

#### `mcp_config.py` (Models)
- Removed legacy `MCPConfig` class with `mcp_servers` list
- Added `MCPServerConfig` for validation
- Added `StdioServerConfig` and `HttpServerConfig` for specific transport types
- Updated to use Pydantic V2 `ConfigDict`

#### `mcp_config_service.py`
- Now returns `Dict[str, Any]` instead of `MCPConfig` object
- Added comprehensive validation for both transport types
- Better error messages for configuration issues

#### `mcp_connection_manager.py`
- Updated to accept `Dict[str, Any]` instead of `MCPConfig`
- Now iterates over dictionary items instead of list
- Only connects to HTTP-based servers (stdio handled by `MCPToolManager`)
- Marked as DEPRECATED (use `MCPToolManager` for new code)

#### `main.py`
- Uses `get_mcp_config_path()` from `config.py` for configurable path
- Single config path used for both managers
- Removed TODO comment about command-line arguments

### 4. Configuration Path

The MCP config path is now configurable via environment variable:

**Priority order:**
1. `MCP_CONFIG_PATH` environment variable
2. `/config/mcp_config.yaml` (Docker/K8s mount)
3. `./mcp_config.yaml` (default)

**Usage:**
```bash
# Set via environment variable
export MCP_CONFIG_PATH=/custom/path/mcp_config.yaml
make run

# Or inline
MCP_CONFIG_PATH=/custom/path/mcp_config.yaml make run
```

## Migration Steps

If you have an existing `mcp_config.yaml` with the old format:

1. **Backup your current config:**
   ```bash
   cp mcp_config.yaml mcp_config.yaml.backup
   ```

2. **Convert to new format:**

   Old:
   ```yaml
   mcp_servers:
     - server_url: "k8s-server:8080"
       transport_type: "http"
   ```

   New:
   ```yaml
   kubernetes:
     url: "http://k8s-server:8080/mcp"
     transport: "streamable_http"
   ```

3. **Update transport types:**
   - `http` or `https` → `streamable_http`
   - Add `stdio` for local process-based servers

4. **Test the configuration:**
   ```bash
   make run
   # Check logs for: "Using MCP configuration from: ..."
   # Check health endpoint: curl http://localhost:8000/health
   ```

## Validation

The configuration is validated on startup. Common errors:

- **Missing transport field:** Each server must have a `transport` field
- **Invalid transport type:** Must be `stdio` or `streamable_http`
- **Missing required fields:**
  - `stdio`: requires `command` and `args`
  - `streamable_http`: requires `url`

## Testing

Run the test suite to verify configuration parsing:

```bash
poetry run pytest tests/test_mcp_config_service.py -v
```

## Examples

See `mcp_config.yaml` for complete examples of both transport types.

## Backward Compatibility

The legacy `MCPConnectionManager` still works but is deprecated. New code should use `MCPToolManager` which fully supports the new format.
