"""Unit tests for MCP Tool Manager."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.services.mcp_tool_manager import MCPToolManager


@pytest.fixture
def mcp_config():
    """Create test MCP configuration."""
    return {
        "kubernetes": {
            "url": "http://k8s-mcp-server:8080/mcp",
            "transport": "streamable_http",
        },
        "prometheus": {
            "command": "python",
            "args": ["/path/to/prometheus_server.py"],
            "transport": "stdio",
        },
    }


@pytest.fixture
def empty_config():
    """Create empty MCP configuration."""
    return {}


@pytest.fixture
def mock_tools():
    """Create mock tools."""
    tool1 = Mock()
    tool1.name = "get_pod_details"
    tool1.description = "Get Kubernetes pod details"

    tool2 = Mock()
    tool2.name = "get_pod_logs"
    tool2.description = "Get Kubernetes pod logs"

    return [tool1, tool2]


class TestMCPToolManager:
    """Tests for MCPToolManager class."""

    @pytest.mark.asyncio
    async def test_initialization(self, mcp_config):
        """Test tool manager initialization."""
        manager = MCPToolManager(mcp_config)

        assert manager._config == mcp_config
        assert manager._client is None
        assert manager._tools is None
        assert not manager.is_initialized()

    @pytest.mark.asyncio
    async def test_initialize_success(self, mcp_config, mock_tools):
        """Test successful initialization with tool discovery."""
        with patch(
            "app.services.mcp_tool_manager.MultiServerMCPClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_tools.return_value = mock_tools
            mock_client_class.return_value = mock_client

            manager = MCPToolManager(mcp_config)
            tools = await manager.initialize()

            assert tools == mock_tools
            assert manager.is_initialized()
            assert manager.get_tool_count() == 2
            assert manager.get_tool_names() == ["get_pod_details", "get_pod_logs"]
            mock_client.get_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_empty_config(self, empty_config):
        """Test initialization with empty config."""
        manager = MCPToolManager(empty_config)
        tools = await manager.initialize()

        assert tools == []
        assert manager.is_initialized()
        assert manager.get_tool_count() == 0

    @pytest.mark.asyncio
    async def test_initialize_failure(self, mcp_config):
        """Test initialization failure."""
        with patch(
            "app.services.mcp_tool_manager.MultiServerMCPClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_tools.side_effect = Exception("Connection failed")
            mock_client_class.return_value = mock_client

            manager = MCPToolManager(mcp_config)

            with pytest.raises(Exception, match="Connection failed"):
                await manager.initialize()

            assert manager.is_initialized()
            assert manager.get_tool_count() == 0

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, mcp_config, mock_tools):
        """Test that initialize can be called multiple times safely."""
        with patch(
            "app.services.mcp_tool_manager.MultiServerMCPClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_tools.return_value = mock_tools
            mock_client_class.return_value = mock_client

            manager = MCPToolManager(mcp_config)

            tools1 = await manager.initialize()
            tools2 = await manager.initialize()

            assert tools1 == tools2
            # Should only call get_tools once
            mock_client.get_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_tools_auto_initialize(self, mcp_config, mock_tools):
        """Test get_tools auto-initializes if not initialized."""
        with patch(
            "app.services.mcp_tool_manager.MultiServerMCPClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_tools.return_value = mock_tools
            mock_client_class.return_value = mock_client

            manager = MCPToolManager(mcp_config)
            tools = await manager.get_tools()

            assert tools == mock_tools
            assert manager.is_initialized()

    @pytest.mark.asyncio
    async def test_get_tools_when_initialized(self, mcp_config, mock_tools):
        """Test get_tools returns cached tools when already initialized."""
        with patch(
            "app.services.mcp_tool_manager.MultiServerMCPClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_tools.return_value = mock_tools
            mock_client_class.return_value = mock_client

            manager = MCPToolManager(mcp_config)
            await manager.initialize()

            tools = await manager.get_tools()

            assert tools == mock_tools
            # Should only call get_tools once during initialize
            mock_client.get_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_success(self, mcp_config, mock_tools):
        """Test successful cleanup."""
        with patch(
            "app.services.mcp_tool_manager.MultiServerMCPClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_tools.return_value = mock_tools
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client

            manager = MCPToolManager(mcp_config)
            await manager.initialize()
            await manager.cleanup()

            mock_client.__aexit__.assert_called_once()
            assert manager._client is None
            assert manager._tools is None
            assert not manager.is_initialized()

    @pytest.mark.asyncio
    async def test_cleanup_without_client(self, mcp_config):
        """Test cleanup when no client exists."""
        manager = MCPToolManager(mcp_config)
        # Should not raise error
        await manager.cleanup()

        assert not manager.is_initialized()

    @pytest.mark.asyncio
    async def test_cleanup_with_error(self, mcp_config, mock_tools):
        """Test cleanup handles errors gracefully."""
        with patch(
            "app.services.mcp_tool_manager.MultiServerMCPClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_tools.return_value = mock_tools
            mock_client.__aexit__ = AsyncMock(side_effect=Exception("Cleanup error"))
            mock_client_class.return_value = mock_client

            manager = MCPToolManager(mcp_config)
            await manager.initialize()

            # Should not raise, just log error
            await manager.cleanup()

            assert manager._client is None
            assert not manager.is_initialized()

    @pytest.mark.asyncio
    async def test_execute_tool_with_logging_success(self, mcp_config, mock_tools):
        """Test successful tool execution with logging."""
        with patch(
            "app.services.mcp_tool_manager.MultiServerMCPClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_tools.return_value = mock_tools
            mock_client_class.return_value = mock_client

            # Setup tool to return result
            mock_tools[0].ainvoke = AsyncMock(return_value={"status": "Running"})

            manager = MCPToolManager(mcp_config)
            await manager.initialize()

            result = await manager.execute_tool_with_logging(
                "get_pod_details",
                {"pod_name": "test-pod", "namespace": "default"},
                correlation_id="test-123",
            )

            assert result == {"status": "Running"}
            mock_tools[0].ainvoke.assert_called_once_with(
                {"pod_name": "test-pod", "namespace": "default"}
            )

    @pytest.mark.asyncio
    async def test_execute_tool_with_logging_tool_not_found(
        self, mcp_config, mock_tools
    ):
        """Test tool execution with non-existent tool."""
        with patch(
            "app.services.mcp_tool_manager.MultiServerMCPClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_tools.return_value = mock_tools
            mock_client_class.return_value = mock_client

            manager = MCPToolManager(mcp_config)
            await manager.initialize()

            with pytest.raises(ValueError, match="Tool 'non_existent' not found"):
                await manager.execute_tool_with_logging(
                    "non_existent", {}, correlation_id="test-123"
                )

    @pytest.mark.asyncio
    async def test_execute_tool_with_logging_execution_error(
        self, mcp_config, mock_tools
    ):
        """Test tool execution with execution error."""
        with patch(
            "app.services.mcp_tool_manager.MultiServerMCPClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_tools.return_value = mock_tools
            mock_client_class.return_value = mock_client

            # Setup tool to raise error
            mock_tools[0].ainvoke = AsyncMock(
                side_effect=Exception("Tool execution failed")
            )

            manager = MCPToolManager(mcp_config)
            await manager.initialize()

            with pytest.raises(Exception, match="Tool execution failed"):
                await manager.execute_tool_with_logging(
                    "get_pod_details",
                    {"pod_name": "test-pod"},
                    correlation_id="test-123",
                )

    def test_get_tool_count_not_initialized(self, mcp_config):
        """Test get_tool_count when not initialized."""
        manager = MCPToolManager(mcp_config)
        assert manager.get_tool_count() == 0

    def test_get_tool_names_not_initialized(self, mcp_config):
        """Test get_tool_names when not initialized."""
        manager = MCPToolManager(mcp_config)
        assert manager.get_tool_names() == []

    @pytest.mark.asyncio
    async def test_get_tool_names_after_initialization(self, mcp_config, mock_tools):
        """Test get_tool_names after initialization."""
        with patch(
            "app.services.mcp_tool_manager.MultiServerMCPClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_tools.return_value = mock_tools
            mock_client_class.return_value = mock_client

            manager = MCPToolManager(mcp_config)
            await manager.initialize()

            names = manager.get_tool_names()
            assert names == ["get_pod_details", "get_pod_logs"]
