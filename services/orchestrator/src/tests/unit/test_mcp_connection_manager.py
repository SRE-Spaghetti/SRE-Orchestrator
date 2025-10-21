import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.mcp_config import MCPConfig, MCPServerConfig
from app.services.mcp_connection_manager import MCPConnectionManager


@pytest.fixture
def mcp_config():
    return MCPConfig(
        mcp_servers=[
            MCPServerConfig(
                server_url="http://localhost:8080/mcp",
                transport_type="http",
            )
        ]
    )


@pytest.mark.asyncio
async def test_connect_to_servers_success(mcp_config):
    with patch("app.services.mcp_connection_manager.create_mcp_http_client", new_callable=AsyncMock) as mock_create_client:
        mock_client_instance = mock_create_client.return_value

        manager = MCPConnectionManager(mcp_config)
        await manager.connect_to_servers()

        assert "http://localhost:8080/mcp" in manager._clients
        mock_create_client.assert_called_once_with("http://localhost:8080/mcp")


@pytest.mark.asyncio
async def test_connect_to_servers_failure(mcp_config):
    with patch("app.services.mcp_connection_manager.create_mcp_http_client", new_callable=AsyncMock) as mock_create_client:
        mock_create_client.side_effect = Exception("Connection failed")

        manager = MCPConnectionManager(mcp_config)
        await manager.connect_to_servers()

        assert "http://localhost:8080/mcp" not in manager._clients
        assert mock_create_client.call_count == 3


@pytest.mark.asyncio
async def test_disconnect_from_servers(mcp_config):
    with patch("app.services.mcp_connection_manager.create_mcp_http_client", new_callable=AsyncMock) as mock_create_client:
        mock_client_instance = mock_create_client.return_value
        mock_client_instance.close = AsyncMock()

        manager = MCPConnectionManager(mcp_config)
        await manager.connect_to_servers()
        await manager.disconnect_from_servers()

        mock_client_instance.close.assert_called_once()
