"""Tests for orchestrator API client."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx

from sre_orchestrator_cli.client import (
    OrchestratorClient,
    OrchestratorClientError,
    ConnectionError,
    AuthenticationError,
    NotFoundError
)


@pytest.fixture
def base_url():
    """Test base URL."""
    return "http://localhost:8000"


@pytest.fixture
def api_key():
    """Test API key."""
    return "test-api-key-123"


class TestOrchestratorClient:
    """Tests for OrchestratorClient class."""

    def test_initialization(self, base_url, api_key):
        """Test client initialization."""
        client = OrchestratorClient(base_url, api_key, timeout=60.0)

        assert client.base_url == base_url
        assert client.api_key == api_key
        assert client.timeout == 60.0

    def test_initialization_strips_trailing_slash(self):
        """Test base URL trailing slash is stripped."""
        client = OrchestratorClient("http://localhost:8000/", "key")

        assert client.base_url == "http://localhost:8000"

    @pytest.mark.asyncio
    async def test_context_manager(self, base_url, api_key):
        """Test async context manager."""
        async with OrchestratorClient(base_url, api_key) as client:
            assert client._client is not None

    @pytest.mark.asyncio
    async def test_create_incident_success(self, base_url, api_key):
        """Test successful incident creation."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.json.return_value = {"id": "incident-123"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            client = OrchestratorClient(base_url, api_key)
            incident_id = await client.create_incident("Pod is crashing")

            assert incident_id == "incident-123"
            mock_client.post.assert_called_once_with(
                "/api/v1/incidents",
                json={"description": "Pod is crashing"}
            )

    @pytest.mark.asyncio
    async def test_create_incident_authentication_error(self, base_url, api_key):
        """Test incident creation with authentication error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"detail": "Unauthorized"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            client = OrchestratorClient(base_url, api_key)

            with pytest.raises(AuthenticationError, match="Authentication failed"):
                await client.create_incident("Pod is crashing")

    @pytest.mark.asyncio
    async def test_create_incident_connection_error(self, base_url, api_key):
        """Test incident creation with connection error."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")
            mock_client_class.return_value = mock_client

            client = OrchestratorClient(base_url, api_key)

            with pytest.raises(ConnectionError, match="Failed to connect"):
                await client.create_incident("Pod is crashing")

    @pytest.mark.asyncio
    async def test_create_incident_timeout(self, base_url, api_key):
        """Test incident creation with timeout."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("Timeout")
            mock_client_class.return_value = mock_client

            client = OrchestratorClient(base_url, api_key)

            with pytest.raises(ConnectionError, match="timed out"):
                await client.create_incident("Pod is crashing")

    @pytest.mark.asyncio
    async def test_get_incident_success(self, base_url, api_key):
        """Test successful incident retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "incident-123",
            "status": "completed",
            "root_cause": "Memory issue"
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            client = OrchestratorClient(base_url, api_key)
            incident = await client.get_incident("incident-123")

            assert incident["id"] == "incident-123"
            assert incident["status"] == "completed"
            mock_client.get.assert_called_once_with("/api/v1/incidents/incident-123")

    @pytest.mark.asyncio
    async def test_get_incident_not_found(self, base_url, api_key):
        """Test incident retrieval with not found error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"detail": "Not found"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            client = OrchestratorClient(base_url, api_key)

            with pytest.raises(NotFoundError, match="not found"):
                await client.get_incident("incident-123")

    @pytest.mark.asyncio
    async def test_list_incidents_success(self, base_url, api_key):
        """Test successful incident listing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "incident-1", "status": "completed"},
            {"id": "incident-2", "status": "investigating"}
        ]

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            client = OrchestratorClient(base_url, api_key)
            incidents = await client.list_incidents(limit=10)

            assert len(incidents) == 2
            assert incidents[0]["id"] == "incident-1"
            mock_client.get.assert_called_once_with(
                "/api/v1/incidents",
                params={"limit": 10}
            )

    @pytest.mark.asyncio
    async def test_list_incidents_authentication_error(self, base_url, api_key):
        """Test incident listing with authentication error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"detail": "Unauthorized"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            client = OrchestratorClient(base_url, api_key)

            with pytest.raises(AuthenticationError):
                await client.list_incidents()

    @pytest.mark.asyncio
    async def test_close(self, base_url, api_key):
        """Test client close."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            client = OrchestratorClient(base_url, api_key)
            # Trigger client creation
            client._get_client()

            await client.close()

            mock_client.aclose.assert_called_once()
            assert client._client is None
