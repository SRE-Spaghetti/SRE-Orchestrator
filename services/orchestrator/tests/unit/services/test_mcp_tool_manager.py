"""Unit tests for MCPToolManager."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

from app.services.mcp_tool_manager import MCPToolManager


class TestMCPToolManager:
    """Test suite for MCPToolManager."""

    @pytest.fixture
    def valid_mcp_config(self) -> Dict[str, Any]:
        """Provides valid MCP configuration for testing."""
        return {
            "kubernetes": {
                "command": "uvx",
                "args": ["mcp-server-kubernetes"],
                "transport": "stdio",
                "env": {},
            },
            "prometheus": {
                "url": "http://prometheus-mcp:8080/mcp",
                "transport": "streamable_http",
                "headers": {"Authorization": "Bearer token123"},
            },
        }

    @pytest.fixture
    def mock_tools(self):
        """Provides mock LangChain-compatible tools."""
        tool1 = Mock()
        tool1.name = "get_pod_details"
        tool1.description = "Get Kubernetes pod details"
        tool1.ainvoke = AsyncMock(return_value={"status": "Running"})

        tool2 = Mock()
        tool2.name = "query_prometheus"
        tool2.description = "Query Prometheus metrics"
        tool2.ainvoke = AsyncMock(return_value={"value": 42})

        return [tool1, tool2]

    def test_initialization_with_valid_config(self, valid_mcp_config):
        """Test MCPToolManager initialization with valid configuration."""
        # Act
        manager = MCPToolManager(valid_mcp_config)

        # Assert
        assert manager._config == valid_mcp_config
        assert manager._client is None
        assert manager._tools is None
        assert manager._initialized is False

    def test_initialization_with_empty_config(self):
        """Test MCPToolManager initialization with empty configuration."""
        # Act
        manager = MCPToolManager({})

        # Assert
        assert manager._config == {}
        assert manager._initialized is False

    @pytest.mark.asyncio
    async def test_initialize_discovers_tools_from_servers(
        self, valid_mcp_config, mock_tools
    ):
        """Test that initialize discovers tools from configured servers."""
        # Arrange
        manager = MCPToolManager(valid_mcp_config)

        with patch(
            "app.services.mcp_tool_manager.MultiServerMCPClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_tools = AsyncMock(return_value=mock_tools)
            mock_client_class.return_value = mock_client

            # Act
            tools = await manager.initialize()

            # Assert
            assert tools == mock_tools
            assert manager._initialized is True
            assert manager._tools == mock_tools
            mock_client_class.assert_called_once_with(valid_mcp_config)
            mock_client.get_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_with_empty_config_returns_empty_list(self):
        """Test that initialize with empty config returns empty tool list."""
        # Arrange
        manager = MCPToolManager({})

        # Act
        tools = await manager.initialize()

        # Assert
        assert tools == []
        assert manager._initialized is True
        assert manager._tools == []

    @pytest.mark.asyncio
    async def test_initialize_only_runs_once(self, valid_mcp_config, mock_tools):
        """Test that initialize only runs once even if called multiple times."""
        # Arrange
        manager = MCPToolManager(valid_mcp_config)

        with patch(
            "app.services.mcp_tool_manager.MultiServerMCPClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_tools = AsyncMock(return_value=mock_tools)
            mock_client_class.return_value = mock_client

            # Act
            tools1 = await manager.initialize()
            tools2 = await manager.initialize()

            # Assert
            assert tools1 == tools2
            assert mock_client_class.call_count == 1
            assert mock_client.get_tools.call_count == 1

    @pytest.mark.asyncio
    async def test_initialize_raises_exception_on_failure(self, valid_mcp_config):
        """Test that initialize raises exception when client initialization fails."""
        # Arrange
        manager = MCPToolManager(valid_mcp_config)

        with patch(
            "app.services.mcp_tool_manager.MultiServerMCPClient"
        ) as mock_client_class:
            mock_client_class.side_effect = Exception("Connection failed")

            # Act & Assert
            with pytest.raises(Exception, match="Connection failed"):
                await manager.initialize()

            assert manager._initialized is True
            assert manager._tools == []

    @pytest.mark.asyncio
    async def test_get_tools_returns_langchain_compatible_tools(
        self, valid_mcp_config, mock_tools
    ):
        """Test that get_tools returns LangChain-compatible tools."""
        # Arrange
        manager = MCPToolManager(valid_mcp_config)

        with patch(
            "app.services.mcp_tool_manager.MultiServerMCPClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_tools = AsyncMock(return_value=mock_tools)
            mock_client_class.return_value = mock_client

            await manager.initialize()

            # Act
            tools = await manager.get_tools()

            # Assert
            assert len(tools) == 2
            assert tools[0].name == "get_pod_details"
            assert tools[1].name == "query_prometheus"

    @pytest.mark.asyncio
    async def test_get_tools_initializes_if_not_initialized(
        self, valid_mcp_config, mock_tools
    ):
        """Test that get_tools calls initialize if not already initialized."""
        # Arrange
        manager = MCPToolManager(valid_mcp_config)

        with patch(
            "app.services.mcp_tool_manager.MultiServerMCPClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_tools = AsyncMock(return_value=mock_tools)
            mock_client_class.return_value = mock_client

            # Act
            tools = await manager.get_tools()

            # Assert
            assert manager._initialized is True
            assert tools == mock_tools

    @pytest.mark.asyncio
    async def test_get_tools_returns_empty_list_when_not_initialized(self):
        """Test that get_tools returns empty list when tools are None."""
        # Arrange
        manager = MCPToolManager({})

        # Act
        tools = await manager.get_tools()

        # Assert
        assert tools == []

    @pytest.mark.asyncio
    async def test_cleanup_releases_resources(self, valid_mcp_config, mock_tools):
        """Test that cleanup properly releases MCP client resources."""
        # Arrange
        manager = MCPToolManager(valid_mcp_config)

        with patch(
            "app.services.mcp_tool_manager.MultiServerMCPClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_tools = AsyncMock(return_value=mock_tools)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client

            await manager.initialize()

            # Act
            await manager.cleanup()

            # Assert
            mock_client.__aexit__.assert_called_once_with(None, None, None)
            assert manager._client is None
            assert manager._tools is None
            assert manager._initialized is False

    @pytest.mark.asyncio
    async def test_cleanup_handles_errors_gracefully(
        self, valid_mcp_config, mock_tools
    ):
        """Test that cleanup handles errors during resource cleanup."""
        # Arrange
        manager = MCPToolManager(valid_mcp_config)

        with patch(
            "app.services.mcp_tool_manager.MultiServerMCPClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_tools = AsyncMock(return_value=mock_tools)
            mock_client.__aexit__ = AsyncMock(side_effect=Exception("Cleanup error"))
            mock_client_class.return_value = mock_client

            await manager.initialize()

            # Act - should not raise exception
            await manager.cleanup()

            # Assert
            assert manager._client is None
            assert manager._tools is None
            assert manager._initialized is False

    @pytest.mark.asyncio
    async def test_cleanup_when_not_initialized(self):
        """Test that cleanup works when manager is not initialized."""
        # Arrange
        manager = MCPToolManager({})

        # Act - should not raise exception
        await manager.cleanup()

        # Assert
        assert manager._client is None
        assert manager._initialized is False

    def test_is_initialized_returns_correct_status(self, valid_mcp_config):
        """Test that is_initialized tracks initialization status correctly."""
        # Arrange
        manager = MCPToolManager(valid_mcp_config)

        # Assert - before initialization
        assert manager.is_initialized() is False

        # Act - manually set initialized
        manager._initialized = True

        # Assert - after initialization
        assert manager.is_initialized() is True

    def test_get_tool_count_returns_correct_count(self, valid_mcp_config, mock_tools):
        """Test that get_tool_count returns correct number of tools."""
        # Arrange
        manager = MCPToolManager(valid_mcp_config)
        manager._tools = mock_tools

        # Act
        count = manager.get_tool_count()

        # Assert
        assert count == 2

    def test_get_tool_count_returns_zero_when_not_initialized(self, valid_mcp_config):
        """Test that get_tool_count returns 0 when not initialized."""
        # Arrange
        manager = MCPToolManager(valid_mcp_config)

        # Act
        count = manager.get_tool_count()

        # Assert
        assert count == 0

    def test_get_tool_names_returns_correct_names(self, valid_mcp_config, mock_tools):
        """Test that get_tool_names returns list of tool names."""
        # Arrange
        manager = MCPToolManager(valid_mcp_config)
        manager._tools = mock_tools

        # Act
        names = manager.get_tool_names()

        # Assert
        assert len(names) == 2
        assert "get_pod_details" in names
        assert "query_prometheus" in names

    def test_get_tool_names_returns_empty_list_when_not_initialized(
        self, valid_mcp_config
    ):
        """Test that get_tool_names returns empty list when not initialized."""
        # Arrange
        manager = MCPToolManager(valid_mcp_config)

        # Act
        names = manager.get_tool_names()

        # Assert
        assert names == []

    @pytest.mark.asyncio
    async def test_execute_tool_with_logging_executes_tool(
        self, valid_mcp_config, mock_tools
    ):
        """Test that execute_tool_with_logging executes the specified tool."""
        # Arrange
        manager = MCPToolManager(valid_mcp_config)
        manager._tools = mock_tools
        manager._initialized = True

        # Act
        result = await manager.execute_tool_with_logging(
            "get_pod_details", {"pod_name": "test-pod"}, "corr-123"
        )

        # Assert
        assert result == {"status": "Running"}
        mock_tools[0].ainvoke.assert_called_once_with({"pod_name": "test-pod"})

    @pytest.mark.asyncio
    async def test_execute_tool_with_logging_raises_error_for_unknown_tool(
        self, valid_mcp_config, mock_tools
    ):
        """Test that execute_tool_with_logging raises ValueError for unknown tool."""
        # Arrange
        manager = MCPToolManager(valid_mcp_config)
        manager._tools = mock_tools
        manager._initialized = True

        # Act & Assert
        with pytest.raises(ValueError, match="Tool 'unknown_tool' not found"):
            await manager.execute_tool_with_logging("unknown_tool", {}, "corr-123")

    @pytest.mark.asyncio
    async def test_execute_tool_with_logging_propagates_tool_errors(
        self, valid_mcp_config, mock_tools
    ):
        """Test that execute_tool_with_logging propagates tool execution errors."""
        # Arrange
        manager = MCPToolManager(valid_mcp_config)
        mock_tools[0].ainvoke = AsyncMock(
            side_effect=Exception("Tool execution failed")
        )
        manager._tools = mock_tools
        manager._initialized = True

        # Act & Assert
        with pytest.raises(Exception, match="Tool execution failed"):
            await manager.execute_tool_with_logging(
                "get_pod_details", {"pod_name": "test-pod"}
            )
