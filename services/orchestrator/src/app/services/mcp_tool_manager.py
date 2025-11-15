"""
MCP Tool Manager for integrating MCP servers with LangChain.

This module provides the MCPToolManager class which wraps MultiServerMCPClient
to manage MCP server connections and provide LangChain-compatible tools.
"""

import logging
from typing import Any, Dict, List, Optional

from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger(__name__)


class MCPToolManager:
    """
    Manages MCP server connections and tool access using MultiServerMCPClient.

    This class wraps the MultiServerMCPClient from langchain-mcp-adapters to provide
    a simplified interface for discovering and accessing tools from multiple MCP servers.
    """

    def __init__(self, mcp_config: Dict[str, Any]):
        """
        Initialize the MCP Tool Manager.

        Args:
            mcp_config: Dictionary mapping server names to connection configs.
                Example:
                {
                    "kubernetes": {
                        "url": "http://k8s-mcp-server:8080/mcp",
                        "transport": "streamable_http",
                        "headers": {"Authorization": "Bearer token"}
                    },
                    "prometheus": {
                        "command": "python",
                        "args": ["/path/to/prometheus_server.py"],
                        "transport": "stdio"
                    }
                }
        """
        self._config = mcp_config
        self._client: Optional[MultiServerMCPClient] = None
        self._tools: Optional[List[Any]] = None
        self._initialized = False

    async def initialize(self) -> List[Any]:
        """
        Initialize the MCP client and load all tools from configured servers.

        This method connects to all configured MCP servers and discovers their
        available tools. The tools are converted to LangChain-compatible format.

        Returns:
            List of LangChain-compatible tools from all MCP servers.

        Raises:
            Exception: If initialization fails or no servers are configured.
        """
        if self._initialized:
            logger.info("MCP Tool Manager already initialized")
            return self._tools

        if not self._config:
            logger.warning("No MCP servers configured")
            self._tools = []
            self._initialized = True
            return self._tools

        try:
            logger.info(f"Initializing MCP Tool Manager with {len(self._config)} server(s)")

            # Create MultiServerMCPClient with the configuration
            self._client = MultiServerMCPClient(self._config)

            # Get tools from all servers
            self._tools = await self._client.get_tools()

            logger.info(f"Successfully loaded {len(self._tools)} tool(s) from MCP servers")

            # Log tool names for debugging
            tool_names = [tool.name for tool in self._tools] if self._tools else []
            logger.debug(f"Available tools: {tool_names}")

            self._initialized = True
            return self._tools

        except Exception as e:
            logger.error(f"Failed to initialize MCP Tool Manager: {e}", exc_info=True)
            self._tools = []
            self._initialized = True
            raise

    async def get_tools(self) -> List[Any]:
        """
        Get LangChain-compatible tools from all MCP servers.

        If not already initialized, this method will call initialize() first.

        Returns:
            List of LangChain-compatible tools.
        """
        if not self._initialized:
            await self.initialize()

        return self._tools if self._tools is not None else []

    async def cleanup(self):
        """
        Clean up MCP connections and resources.

        This method should be called during application shutdown to properly
        close all MCP server connections.
        """
        if self._client:
            try:
                logger.info("Cleaning up MCP Tool Manager connections")
                # MultiServerMCPClient handles cleanup automatically
                # but we can explicitly close if needed
                await self._client.__aexit__(None, None, None)
                logger.info("MCP Tool Manager cleanup completed")
            except Exception as e:
                logger.error(f"Error during MCP Tool Manager cleanup: {e}", exc_info=True)
            finally:
                self._client = None
                self._tools = None
                self._initialized = False

    def is_initialized(self) -> bool:
        """
        Check if the tool manager has been initialized.

        Returns:
            True if initialized, False otherwise.
        """
        return self._initialized

    def get_tool_count(self) -> int:
        """
        Get the number of available tools.

        Returns:
            Number of tools, or 0 if not initialized.
        """
        return len(self._tools) if self._tools else 0

    def get_tool_names(self) -> List[str]:
        """
        Get the names of all available tools.

        Returns:
            List of tool names, or empty list if not initialized.
        """
        if not self._tools:
            return []
        return [tool.name for tool in self._tools]
