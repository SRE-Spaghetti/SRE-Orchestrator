import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.main import app


# Mock the MCPConfigService and MCPConnectionManager
@pytest.fixture
def mock_mcp_services():
    with patch("app.main.MCPConfigService") as MockMCPConfigService:
        with patch("app.main.MCPConnectionManager") as MockMCPConnectionManager:

            # Configure MockMCPConfigService
            mock_config_service_instance = MockMCPConfigService.return_value
            mock_config_service_instance.load_config.return_value = {"mcp_servers": []}

            # Configure MockMCPConnectionManager
            mock_connection_manager_instance = MockMCPConnectionManager.return_value
            mock_connection_manager_instance.connect_to_servers = AsyncMock()
            mock_connection_manager_instance.disconnect_from_servers = AsyncMock()
            mock_connection_manager_instance.get_connection_statuses = AsyncMock(
                return_value={}
            )

            yield MockMCPConfigService, MockMCPConnectionManager


@pytest.fixture
def client(mock_mcp_services):
    # Use the TestClient with the mocked services
    with TestClient(app) as c:
        yield c


def test_startup_success(client, mock_mcp_services):
    """Test that the application starts successfully and MCP services are initialized."""
    MockMCPConfigService, MockMCPConnectionManager = mock_mcp_services

    # Assert that config was loaded and connection manager was called
    MockMCPConfigService.return_value.load_config.assert_called_once()
    MockMCPConnectionManager.return_value.connect_to_servers.assert_called_once()

    # Test health endpoint
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mcp_connections": {}}


def test_startup_mcp_failure(mock_mcp_services):
    """Test that the application starts even if MCP connection fails."""
    MockMCPConfigService, MockMCPConnectionManager = mock_mcp_services
    MockMCPConnectionManager.return_value.connect_to_servers.side_effect = Exception(
        "Connection failed"
    )

    # Re-initialize client to pick up the new mock behavior
    with TestClient(app) as c:
        response = c.get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "mcp_connections": {"status": "not initialized"},
        }

    MockMCPConfigService.return_value.load_config.assert_called_once()
    MockMCPConnectionManager.return_value.connect_to_servers.assert_called_once()


def test_health_endpoint_mcp_connected(client, mock_mcp_services):
    """Test the health endpoint when MCP connections are successful."""
    MockMCPConfigService, MockMCPConnectionManager = mock_mcp_services
    MockMCPConnectionManager.return_value.get_connection_statuses.return_value = {
        "server1": "connected",
        "server2": "failed",
    }
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "mcp_connections": {"server1": "connected", "server2": "failed"},
    }


def test_health_endpoint_mcp_not_initialized(mock_mcp_services):
    """Test the health endpoint when MCP connection manager is not initialized."""
    MockMCPConfigService, MockMCPConnectionManager = mock_mcp_services
    MockMCPConnectionManager.return_value.connect_to_servers.side_effect = Exception(
        "Connection failed"
    )

    with TestClient(app) as c:
        response = c.get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "mcp_connections": {"status": "not initialized"},
        }
