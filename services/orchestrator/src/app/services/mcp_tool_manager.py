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
        from datetime import datetime

        if self._initialized:
            logger.info("MCP Tool Manager already initialized")
            return self._tools

        if not self._config:
            logger.warning("No MCP servers configured")
            self._tools = []
            self._initialized = True
            return self._tools

        start_time = datetime.utcnow()

        try:
            logger.info(
                "Initializing MCP Tool Manager",
                extra={
                    "server_count": len(self._config),
                    "server_names": list(self._config.keys()),
                    "timestamp": start_time.isoformat()
                }
            )

            # Create MultiServerMCPClient with the configuration
            self._client = MultiServerMCPClient(self._config)

            # Get tools from all servers
            logger.info("Discovering MCP tools from configured servers")
            self._tools = await self._client.get_tools()

            end_time = datetime.utcnow()
            duration_seconds = (end_time - start_time).total_seconds()

            # Log tool discovery results
            tool_names = [tool.name for tool in self._tools] if self._tools else []
            logger.info(
                "MCP tool discovery completed",
                extra={
                    "tool_count": len(self._tools),
                    "tool_names": tool_names,
                    "duration_seconds": duration_seconds,
                    "timestamp": end_time.isoformat()
                }
            )

            # Log individual tool details
            for tool in self._tools:
                logger.debug(
                    "MCP tool discovered",
                    extra={
                        "tool_name": tool.name,
                        "tool_description": getattr(tool, "description", "No description"),
                        "tool_schema": str(getattr(tool, "args_schema", "No schema"))[:200]
                    }
                )

            self._initialized = True
            return self._tools

        except Exception as e:
            end_time = datetime.utcnow()
            duration_seconds = (end_time - start_time).total_seconds()

            logger.error(
                "Failed to initialize MCP Tool Manager",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_seconds": duration_seconds,
                    "server_count": len(self._config),
                    "server_names": list(self._config.keys())
                },
                exc_info=True
            )
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
        from datetime import datetime

        if self._client:
            start_time = datetime.utcnow()
            try:
                logger.info(
                    "Cleaning up MCP Tool Manager connections",
                    extra={
                        "tool_count": len(self._tools) if self._tools else 0,
                        "timestamp": start_time.isoformat()
                    }
                )
                # MultiServerMCPClient handles cleanup automatically
                # but we can explicitly close if needed
                await self._client.__aexit__(None, None, None)

                end_time = datetime.utcnow()
                duration_seconds = (end_time - start_time).total_seconds()

                logger.info(
                    "MCP Tool Manager cleanup completed",
                    extra={
                        "duration_seconds": duration_seconds,
                        "timestamp": end_time.isoformat()
                    }
                )
            except Exception as e:
                end_time = datetime.utcnow()
                duration_seconds = (end_time - start_time).total_seconds()

                logger.error(
                    "Error during MCP Tool Manager cleanup",
                    extra={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "duration_seconds": duration_seconds
                    },
                    exc_info=True
                )
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

    async def execute_tool_with_logging(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> Any:
        """
        Execute an MCP tool with comprehensive logging.

        This method wraps tool execution with timing and error logging.

        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments to pass to the tool
            correlation_id: Optional correlation ID for tracing

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool is not found
            Exception: If tool execution fails
        """
        from datetime import datetime

        # Find the tool
        tool = None
        for t in self._tools:
            if t.name == tool_name:
                tool = t
                break

        if not tool:
            logger.error(
                "MCP tool not found",
                extra={
                    "correlation_id": correlation_id,
                    "tool_name": tool_name,
                    "available_tools": self.get_tool_names()
                }
            )
            raise ValueError(f"Tool '{tool_name}' not found")

        start_time = datetime.utcnow()

        try:
            logger.info(
                "Executing MCP tool",
                extra={
                    "correlation_id": correlation_id,
                    "tool_name": tool_name,
                    "tool_args": tool_args,
                    "timestamp": start_time.isoformat()
                }
            )

            # Execute the tool
            result = await tool.ainvoke(tool_args)

            end_time = datetime.utcnow()
            duration_seconds = (end_time - start_time).total_seconds()

            logger.info(
                "MCP tool execution completed",
                extra={
                    "correlation_id": correlation_id,
                    "tool_name": tool_name,
                    "duration_seconds": duration_seconds,
                    "result_length": len(str(result)),
                    "timestamp": end_time.isoformat()
                }
            )

            return result

        except Exception as e:
            end_time = datetime.utcnow()
            duration_seconds = (end_time - start_time).total_seconds()

            logger.error(
                "MCP tool execution failed",
                extra={
                    "correlation_id": correlation_id,
                    "tool_name": tool_name,
                    "tool_args": tool_args,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_seconds": duration_seconds,
                    "timestamp": end_time.isoformat()
                },
                exc_info=True
            )
            raise
