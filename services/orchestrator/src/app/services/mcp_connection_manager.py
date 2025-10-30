import asyncio
import logging
from typing import Dict, Optional

from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client

from app.models.mcp_config import MCPConfig, MCPServerConfig

logger = logging.getLogger(__name__)


class MCPConnectionManager:
    """
    Manages connections to MCP servers.
    """

    def __init__(self, mcp_config: MCPConfig):
        """
        Initializes the MCPConnectionManager.

        Args:
            mcp_config: The MCP configuration.
        """
        self._config = mcp_config
        self._clients: Dict[str, ClientSession] = {}

    async def connect_to_servers(self):
        """
        Connects to all configured MCP servers.
        """
        logger.info(f"Found {len(self._config.mcp_servers)} MCP servers to connect to.")
        for server_config in self._config.mcp_servers:
            await self._connect_with_retry(server_config.server_url, server_config)

    async def _connect_with_retry(
        self,
        server_name: str,
        server_config: MCPServerConfig,
        max_retries: int = 3,
        delay: int = 5,
    ):
        """
        Connects to an MCP server with retry logic.
        Args:
            server_name: The name of the server.
            server_config: The server configuration.
            max_retries: The maximum number of retries.
            delay: The initial delay between retries.
        """
        logger.info(
            f"Attempting to connect to MCP server at URL: {server_config.server_url}"
        )
        for attempt in range(max_retries):
            try:
                await self._connect(server_name, server_config)
                logger.info(
                    f"Successfully connected to MCP server at URL: {server_config.server_url}"
                )
                return
            except Exception as e:
                logger.warning(
                    f"Attempt {attempt + 1} to connect to MCP server at {server_config.server_url} failed: {e}"
                )
                logger.debug("Exception details:", exc_info=True)
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay * (2**attempt))
                else:
                    logger.error(
                        f"Failed to connect to MCP server at {server_config.server_url} after {max_retries} attempts."
                    )

    async def _connect(self, server_name: str, server_config: MCPServerConfig):
        """
        Connects to a single MCP server.

        Args:
            server_name: The name of the server.
            server_config: The server configuration.
        """
        async with create_mcp_http_client() as client:
            response = await client.get(
                f"{server_config.transport_type.value}://{server_config.server_url}"
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
        for server_config in self._config.mcp_servers:
            server_url = server_config.server_url
            client = self._clients.get(server_url)
            # This is a guess, the actual attribute might be different
            if client and hasattr(client, "is_connected") and client.is_connected:
                statuses[server_url] = "connected"
            else:
                statuses[server_url] = "disconnected"
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
