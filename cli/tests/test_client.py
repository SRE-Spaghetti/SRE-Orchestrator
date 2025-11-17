"""Tests for orchestrator API client."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx

from sre_orchestrator_cli.client import (
    OrchestratorClient,
    ConnectionError,
    AuthenticationError,
    NotFoundError,
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
                "/api/v1/incidents", json={"description": "Pod is crashing"}
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
            "root_cause": "Memory issue",
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
            {"id": "incident-2", "status": "investigating"},
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
                "/api/v1/incidents", params={"limit": 10}
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


class TestAsyncIncidentWorkflow:
    """Tests for async incident workflow in CLI client."""

    @pytest.mark.asyncio
    async def test_create_incident_parses_new_response_format(self, base_url, api_key):
        """Test create_incident() parses new 202 response format with incident_id and status."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.json.return_value = {
            "incident_id": "test-incident-123",
            "status": "pending",
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            client = OrchestratorClient(base_url, api_key)
            result = await client.create_incident("Pod is crashing")

            assert result["incident_id"] == "test-incident-123"
            assert result["status"] == "pending"
            mock_client.post.assert_called_once_with(
                "/api/v1/incidents", json={"description": "Pod is crashing"}
            )

    @pytest.mark.asyncio
    async def test_poll_incident_polls_until_completion(self, base_url, api_key):
        """Test poll_incident() polls until status is completed."""
        # Mock responses: pending -> in_progress -> completed
        mock_responses = [
            {"id": "incident-123", "status": "pending", "description": "Test"},
            {"id": "incident-123", "status": "in_progress", "description": "Test"},
            {
                "id": "incident-123",
                "status": "completed",
                "description": "Test",
                "suggested_root_cause": "Memory leak",
            },
        ]

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()

            # Create side effect that returns different responses
            call_count = 0

            async def mock_get(*args, **kwargs):
                nonlocal call_count
                response = Mock()
                response.status_code = 200
                response.json.return_value = mock_responses[
                    min(call_count, len(mock_responses) - 1)
                ]
                call_count += 1
                return response

            mock_client.get.side_effect = mock_get
            mock_client_class.return_value = mock_client

            client = OrchestratorClient(base_url, api_key)
            result = await client.poll_incident(
                "incident-123", interval=0.1, timeout=10.0
            )

            assert result["status"] == "completed"
            assert result["suggested_root_cause"] == "Memory leak"
            assert call_count == 3  # Should have polled 3 times

    @pytest.mark.asyncio
    async def test_poll_incident_stops_on_failed_status(self, base_url, api_key):
        """Test poll_incident() stops polling when status is failed."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "incident-123",
            "status": "failed",
            "description": "Test",
            "error_message": "Investigation timeout",
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            client = OrchestratorClient(base_url, api_key)
            result = await client.poll_incident(
                "incident-123", interval=0.1, timeout=10.0
            )

            assert result["status"] == "failed"
            assert result["error_message"] == "Investigation timeout"

    @pytest.mark.asyncio
    async def test_poll_incident_raises_timeout_error(self, base_url, api_key):
        """Test poll_incident() raises TimeoutError after timeout duration."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "incident-123",
            "status": "in_progress",
            "description": "Test",
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            client = OrchestratorClient(base_url, api_key)

            with pytest.raises(
                TimeoutError, match="Polling timed out after 0.5 seconds"
            ):
                await client.poll_incident("incident-123", interval=0.1, timeout=0.5)

    @pytest.mark.asyncio
    async def test_poll_incident_handles_keyboard_interrupt(self, base_url, api_key):
        """Test poll_incident() propagates KeyboardInterrupt for graceful handling."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()

            # Simulate KeyboardInterrupt on get request
            mock_client.get.side_effect = KeyboardInterrupt()
            mock_client_class.return_value = mock_client

            client = OrchestratorClient(base_url, api_key)

            with pytest.raises(KeyboardInterrupt):
                await client.poll_incident("incident-123", interval=0.1, timeout=10.0)

    @pytest.mark.asyncio
    async def test_poll_incident_calls_callback(self, base_url, api_key):
        """Test poll_incident() calls callback on each poll."""
        mock_responses = [
            {"id": "incident-123", "status": "pending", "description": "Test"},
            {"id": "incident-123", "status": "completed", "description": "Test"},
        ]

        callback_calls = []

        def test_callback(incident):
            callback_calls.append(incident["status"])

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()

            call_count = 0

            async def mock_get(*args, **kwargs):
                nonlocal call_count
                response = Mock()
                response.status_code = 200
                response.json.return_value = mock_responses[
                    min(call_count, len(mock_responses) - 1)
                ]
                call_count += 1
                return response

            mock_client.get.side_effect = mock_get
            mock_client_class.return_value = mock_client

            client = OrchestratorClient(base_url, api_key)
            await client.poll_incident(
                "incident-123", interval=0.1, timeout=10.0, callback=test_callback
            )

            assert callback_calls == ["pending", "completed"]

    @pytest.mark.asyncio
    async def test_poll_incident_respects_interval(self, base_url, api_key):
        """Test poll_incident() respects polling interval."""
        import time

        mock_responses = [
            {"id": "incident-123", "status": "pending", "description": "Test"},
            {"id": "incident-123", "status": "completed", "description": "Test"},
        ]

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()

            call_count = 0
            call_times = []

            async def mock_get(*args, **kwargs):
                nonlocal call_count
                call_times.append(time.time())
                response = Mock()
                response.status_code = 200
                response.json.return_value = mock_responses[
                    min(call_count, len(mock_responses) - 1)
                ]
                call_count += 1
                return response

            mock_client.get.side_effect = mock_get
            mock_client_class.return_value = mock_client

            client = OrchestratorClient(base_url, api_key)
            await client.poll_incident("incident-123", interval=0.2, timeout=10.0)

            # Check that there was at least 0.2 seconds between calls
            if len(call_times) > 1:
                time_diff = call_times[1] - call_times[0]
                assert (
                    time_diff >= 0.2
                ), f"Interval was {time_diff:.3f}s, expected >= 0.2s"
