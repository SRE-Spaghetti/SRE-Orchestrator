import asyncio
import logging
from typing import Dict, Optional, Any

from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client

logger = logging.getLogger(__name__)


class MCPConnectionManager:
    """
    Manages connections to MCP servers.

    DEPRECATED: This is the legacy connection manager.
    Use MCPToolManager for new implementations.
    """

    def __init__(self, mcp_config: Dict[str, Any]):
        """
        Initializes the MCPConnectionManager.

        Args:
            mcp_config: Dictionary mapping server names to their configurations.
        """
        self._config = mcp_config
        self._clients: Dict[str, ClientSession] = {}

    async def connect_to_servers(self):
        """
        Connects to all configured MCP servers.
        """
        if not self._config:
            logger.info("No MCP servers configured")
            return

        logger.info(f"Found {len(self._config)} MCP servers to connect to.")
        for server_name, server_config in self._config.items():
            # Only connect to HTTP-based servers (stdio servers are handled by MCPToolManager)
            if server_config.get("transport") == "streamable_http":
                await self._connect_with_retry(server_name, server_config)

    async def _connect_with_retry(
        self,
        server_name: str,
        server_config: Dict[str, Any],
        max_retries: int = 3,
        delay: int = 5,
    ):
        """
        Connects to an MCP server with retry logic.
        Args:
            server_name: The name of the server.
            server_config: The server configuration dictionary.
            max_retries: The maximum number of retries.
            delay: The initial delay between retries.
        """
        server_url = server_config.get("url", "")
        logger.info(
            f"Attempting to connect to MCP server '{server_name}' at URL: {server_url}"
        )
        for attempt in range(max_retries):
            try:
                await self._connect(server_name, server_config)
                logger.info(
                    f"Successfully connected to MCP server '{server_name}' at URL: {server_url}"
                )
                return
            except Exception as e:
                logger.warning(
                    f"Attempt {attempt + 1} to connect to MCP server '{server_name}' at {server_url} failed: {e}"
                )
                logger.debug("Exception details:", exc_info=True)
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay * (2**attempt))
                else:
                    logger.error(
                        f"Failed to connect to MCP server '{server_name}' at {server_url} after {max_retries} attempts."
                    )

    async def _connect(self, server_name: str, server_config: Dict[str, Any]):
        """
        Connects to a single MCP server.

        Args:
            server_name: The name of the server.
            server_config: The server configuration dictionary.
        """
        server_url = server_config.get("url", "")
        headers = server_config.get("headers", {})

        async with create_mcp_http_client() as client:
            request_headers = {
                "Content-Type": "application/json",
                "Accept": "application/json,text/event-stream",
            }
            request_headers.update(headers)

            response = await client.post(
                server_url,
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                headers=request_headers,
            )
            if response.status_code == 200:
                logger.info(f"Successfully connected to MCP server: {server_name}")
                self._clients[server_name] = client
            else:
                raise AssertionError(f"Failed to connect to MCP server: {server_name}")

    def get_client(self, server_name: str) -> Optional[ClientSession]:
        """
        Gets the MCP client for a server.

        Args:
            server_name: The name of the server.

        Returns:
            The MCP client, or None if not found.
        """
        return self._clients.get(server_name)

    async def get_connection_statuses(self) -> Dict[str, str]:
        """
        Gets the connection status of all MCP servers.

        Returns:
            A dictionary with the connection status for each server.
        """
        statuses = {}
        for server_name, server_config in self._config.items():
            client = self._clients.get(server_name)
            # This is a guess, the actual attribute might be different
            if client and hasattr(client, "is_connected") and client.is_connected:
                statuses[server_name] = "connected"
            else:
                statuses[server_name] = "disconnected"
        return statuses

    async def disconnect_from_servers(self):
        """
        Disconnects from all MCP servers.
        """
        for server_name, client in self._clients.items():
            try:
                await client.close()
                logger.info(f"Successfully disconnected from MCP server: {server_name}")
            except Exception as e:
                logger.error(f"Failed to disconnect from MCP server {server_name}: {e}")
