# MCP Integration Documentation

## MCP Configuration File Format

The SRE Orchestrator uses a YAML configuration file (`mcp_config.yaml`) to define external Model Context Protocol (MCP) servers. This file is loaded during application startup to establish connections to these servers.

### Example `mcp_config.yaml`

```yaml
mcp_servers:
  - name: "example-mcp-server-1"
    url: "http://localhost:8080/mcp"
    transport: "http"
    auth_token: "your_auth_token_if_any"
  - name: "example-mcp-server-2"
    url: "https://some-external-mcp.com/api"
    transport: "https"
    auth_token: "another_token"
```

### Configuration Fields

- `name`: (Required) A unique identifier for the MCP server.
- `url`: (Required) The base URL of the MCP server.
- `transport`: (Required) The communication protocol to use (e.g., `http`, `https`).
- `auth_token`: (Optional) An authentication token if the MCP server requires it.

## Troubleshooting MCP Connection Issues

If you encounter issues with MCP server connections, consider the following:

1.  **Check `mcp_config.yaml` Syntax:** Ensure your `mcp_config.yaml` file is valid YAML and adheres to the specified schema. Incorrect formatting can prevent the configuration from loading.
2.  **Verify Server Reachability:** Confirm that the MCP server URLs are correct and the servers are accessible from where the SRE Orchestrator is running. Use `ping` or `curl` to test connectivity.
3.  **Authentication Token:** If `auth_token` is configured, ensure it is correct and has the necessary permissions on the MCP server.
4.  **Firewall Rules:** Check if any firewall rules are blocking communication between the Orchestrator and the MCP servers.
5.  **Orchestrator Logs:** Review the SRE Orchestrator's startup logs for any warnings or errors related to MCP connection initialization. Failed connections are logged as warnings and include details about the failure.
6.  **MCP Server Logs:** Check the logs of the MCP server itself for any errors or indications of connection attempts.

## Health Check Endpoint Enhancements

The `/health` endpoint of the SRE Orchestrator has been enhanced to provide detailed status of MCP server connections.

### Example Health Check Response

```json
{
  "status": "ok",
  "mcp_connections": {
    "example-mcp-server-1": "connected",
    "example-mcp-server-2": "failed",
    "status": "not initialized" // If MCP Connection Manager failed to initialize
  }
}
```

- `status`: Indicates the overall health of the SRE Orchestrator.
- `mcp_connections`: A dictionary detailing the connection status of each configured MCP server. Possible statuses include `connected`, `failed`, or `not initialized` if the MCP Connection Manager itself failed to start.
