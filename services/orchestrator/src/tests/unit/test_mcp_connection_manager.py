from unittest.mock import AsyncMock, patch

import pytest
from app.services.mcp_connection_manager import MCPConnectionManager


@pytest.fixture
def mcp_config():
    """Return a dictionary config as expected by MCPConnectionManager."""
    return {
        "test-server": {
            "url": "http://localhost:8080/mcp",
            "transport": "streamable_http",
        }
    }


@pytest.mark.asyncio
async def test_connect_to_servers_success(mcp_config):
    # Create a mock for the client instance
    mock_client_instance = AsyncMock()
    mock_client_instance.post.return_value.status_code = 200

    # Create an async context manager mock
    async_context_manager_mock = AsyncMock()
    async_context_manager_mock.__aenter__.return_value = mock_client_instance

    with patch(
        "app.services.mcp_connection_manager.create_mcp_http_client",
        return_value=async_context_manager_mock,
    ) as mock_create_client:
        manager = MCPConnectionManager(mcp_config)
        await manager.connect_to_servers()

        # Assert that the http client creator was called
        mock_create_client.assert_called_once()

        # Assert that the post method was called on the client instance
        mock_client_instance.post.assert_called_once_with(
            "http://localhost:8080/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json,text/event-stream",
            },
        )

        # Check if the client was added to the manager
        assert "test-server" in manager._clients


@pytest.mark.asyncio
async def test_connect_to_servers_failure(mcp_config):
    with patch(
        "app.services.mcp_connection_manager.create_mcp_http_client",
        new_callable=AsyncMock,
    ) as mock_create_client:
        mock_create_client.side_effect = Exception("Connection failed")

        manager = MCPConnectionManager(mcp_config)
        await manager.connect_to_servers()

        assert "test-server" not in manager._clients
        assert mock_create_client.call_count == 3


@pytest.mark.asyncio
async def test_disconnect_from_servers(mcp_config):
    # Create a mock for the client instance
    mock_client_instance = AsyncMock()
    mock_client_instance.post.return_value.status_code = 200
    mock_client_instance.close = AsyncMock()

    # Create an async context manager mock
    async_context_manager_mock = AsyncMock()
    async_context_manager_mock.__aenter__.return_value = mock_client_instance

    with patch(
        "app.services.mcp_connection_manager.create_mcp_http_client",
        return_value=async_context_manager_mock,
    ):
        manager = MCPConnectionManager(mcp_config)
        await manager.connect_to_servers()
        await manager.disconnect_from_servers()

        mock_client_instance.close.assert_called_once()
