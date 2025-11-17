"""End-to-end tests for full orchestrator workflow.

These tests verify the complete workflow from incident creation through
investigation to final results, including MCP tool integration.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def test_client():
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_mcp_tools():
    """Create mock MCP tools for testing."""
    # Mock get_pod_details tool
    pod_details_tool = Mock()
    pod_details_tool.name = "get_pod_details"
    pod_details_tool.description = "Get Kubernetes pod details"
    pod_details_tool.ainvoke = AsyncMock(
        return_value={
            "status": "CrashLoopBackOff",
            "restarts": 5,
            "reason": "Error",
            "message": "Back-off restarting failed container",
        }
    )

    # Mock get_pod_logs tool
    pod_logs_tool = Mock()
    pod_logs_tool.name = "get_pod_logs"
    pod_logs_tool.description = "Get Kubernetes pod logs"
    pod_logs_tool.ainvoke = AsyncMock(
        return_value="""
2024-01-15 10:30:45 ERROR: Failed to connect to database
2024-01-15 10:30:46 ERROR: Connection timeout after 30s
2024-01-15 10:30:47 FATAL: Application startup failed
"""
    )

    return [pod_details_tool, pod_logs_tool]


@pytest.fixture
def mock_llm_response():
    """Create mock LLM response for investigation."""
    msg1 = Mock()
    msg1.type = "ai"
    msg1.content = "I will investigate this pod crash issue."
    msg1.tool_calls = [
        {
            "name": "get_pod_details",
            "args": {"pod_name": "test-pod", "namespace": "default"},
        }
    ]

    msg2 = Mock()
    msg2.type = "tool"
    msg2.name = "get_pod_details"
    msg2.content = '{"status": "CrashLoopBackOff", "restarts": 5}'

    msg3 = Mock()
    msg3.type = "ai"
    msg3.content = "Let me check the logs."
    msg3.tool_calls = [
        {
            "name": "get_pod_logs",
            "args": {"pod_name": "test-pod", "namespace": "default"},
        }
    ]

    msg4 = Mock()
    msg4.type = "tool"
    msg4.name = "get_pod_logs"
    msg4.content = "ERROR: Failed to connect to database"

    msg5 = Mock()
    msg5.type = "ai"
    msg5.content = """Based on my investigation:

ROOT CAUSE: Pod is crashing due to database connection failure
CONFIDENCE: high
EVIDENCE: Pod logs show repeated database connection errors and timeouts
RECOMMENDATIONS:
- Verify database service is running and accessible
- Check database credentials in pod configuration
- Review network policies for database connectivity"""
    msg5.tool_calls = []

    return {"messages": [msg1, msg2, msg3, msg4, msg5]}


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""

    @pytest.mark.asyncio
    async def test_complete_incident_investigation_workflow(
        self, test_client, mock_mcp_tools, mock_llm_response
    ):
        """Test complete workflow from incident creation to investigation completion."""
        # Mock MCP tool manager
        with patch("app.main.MCPToolManager") as mock_tool_manager_class:
            mock_tool_manager = AsyncMock()
            mock_tool_manager.initialize.return_value = mock_mcp_tools
            mock_tool_manager.get_tools.return_value = mock_mcp_tools
            mock_tool_manager_class.return_value = mock_tool_manager

            # Mock LangChain LLM client
            with patch("app.services.langchain_llm_client.ChatOpenAI"):
                # Mock agent creation and execution
                with patch(
                    "app.core.investigation_agent.create_react_agent"
                ) as mock_create_agent:
                    mock_agent = AsyncMock()
                    mock_agent.ainvoke.return_value = mock_llm_response
                    mock_create_agent.return_value = mock_agent

                    # Create incident
                    response = test_client.post(
                        "/api/v1/incidents",
                        json={
                            "description": "Pod test-pod in namespace default is crashing"
                        },
                    )

                    assert response.status_code == 202
                    incident_id = response.json()["id"]
                    assert incident_id is not None

                    # Wait for investigation to complete
                    max_attempts = 30
                    for _ in range(max_attempts):
                        get_response = test_client.get(
                            f"/api/v1/incidents/{incident_id}"
                        )

                        if get_response.status_code == 200:
                            incident = get_response.json()
                            if incident["status"] in ["completed", "failed"]:
                                break

                        await asyncio.sleep(0.5)

                    # Verify final incident state
                    assert incident["status"] == "completed"
                    assert incident["root_cause"] is not None
                    assert (
                        "database connection failure" in incident["root_cause"].lower()
                    )
                    assert incident["confidence"] == "high"
                    assert len(incident["evidence"]) > 0

    @pytest.mark.asyncio
    async def test_incident_investigation_with_tool_failure(
        self, test_client, mock_mcp_tools
    ):
        """Test workflow handles MCP tool failures gracefully."""
        # Make one tool fail
        mock_mcp_tools[0].ainvoke = AsyncMock(
            side_effect=Exception("Tool execution failed")
        )

        with patch("app.main.MCPToolManager") as mock_tool_manager_class:
            mock_tool_manager = AsyncMock()
            mock_tool_manager.initialize.return_value = mock_mcp_tools
            mock_tool_manager.get_tools.return_value = mock_mcp_tools
            mock_tool_manager_class.return_value = mock_tool_manager

            with patch("app.services.langchain_llm_client.ChatOpenAI"):
                with patch(
                    "app.core.investigation_agent.create_react_agent"
                ) as mock_create_agent:
                    # Agent should handle tool failure and continue
                    mock_agent = AsyncMock()
                    msg = Mock()
                    msg.type = "ai"
                    msg.content = """ROOT CAUSE: Unable to fully investigate due to tool failure
CONFIDENCE: low
EVIDENCE: Tool execution failed
RECOMMENDATIONS: Check MCP server connectivity"""
                    msg.tool_calls = []

                    mock_agent.ainvoke.return_value = {"messages": [msg]}
                    mock_create_agent.return_value = mock_agent

                    response = test_client.post(
                        "/api/v1/incidents", json={"description": "Pod is crashing"}
                    )

                    assert response.status_code == 202
                    incident_id = response.json()["id"]

                    # Wait for completion
                    max_attempts = 30
                    for _ in range(max_attempts):
                        get_response = test_client.get(
                            f"/api/v1/incidents/{incident_id}"
                        )
                        if get_response.status_code == 200:
                            incident = get_response.json()
                            if incident["status"] in ["completed", "failed"]:
                                break
                        await asyncio.sleep(0.5)

                    # Should complete even with tool failure
                    assert incident["status"] in ["completed", "failed"]

    @pytest.mark.asyncio
    async def test_health_endpoint_shows_mcp_status(self, test_client):
        """Test health endpoint includes MCP tool status."""
        with patch("app.main.MCPToolManager") as mock_tool_manager_class:
            mock_tool_manager = AsyncMock()
            mock_tool_manager.is_initialized.return_value = True
            mock_tool_manager.get_tool_count.return_value = 5
            mock_tool_manager.get_tool_names.return_value = [
                "get_pod_details",
                "get_pod_logs",
                "get_pod_events",
                "list_pods",
                "describe_pod",
            ]
            mock_tool_manager_class.return_value = mock_tool_manager

            # Ensure tool manager is in app state
            app.state.mcp_tool_manager = mock_tool_manager

            response = test_client.get("/health")

            assert response.status_code == 200
            health_data = response.json()

            assert health_data["status"] == "healthy"
            # Should include MCP information
            assert "mcp_tools" in health_data or "tools" in health_data

    def test_list_incidents_endpoint(self, test_client):
        """Test listing incidents endpoint."""
        # Create a few incidents first
        for i in range(3):
            test_client.post(
                "/api/v1/incidents", json={"description": f"Test incident {i}"}
            )

        # List incidents
        response = test_client.get("/api/v1/incidents")

        assert response.status_code == 200
        incidents = response.json()
        assert isinstance(incidents, list)

    def test_get_nonexistent_incident(self, test_client):
        """Test getting nonexistent incident returns 404."""
        response = test_client.get("/api/v1/incidents/nonexistent-id")

        assert response.status_code == 404

    def test_create_incident_invalid_payload(self, test_client):
        """Test creating incident with invalid payload."""
        response = test_client.post(
            "/api/v1/incidents", json={"invalid_field": "value"}
        )

        assert response.status_code == 422  # Validation error


class TestCLIIntegration:
    """Tests for CLI integration with orchestrator."""

    @pytest.mark.asyncio
    async def test_cli_create_and_retrieve_incident(self, test_client):
        """Test CLI workflow of creating and retrieving incident."""
        from sre_orchestrator_cli.client import OrchestratorClient

        # Use test client's base URL
        base_url = "http://testserver"

        with patch("httpx.AsyncClient") as mock_client_class:
            # Mock HTTP client responses
            mock_http_client = AsyncMock()

            # Mock create incident response
            create_response = Mock()
            create_response.status_code = 202
            create_response.json.return_value = {"id": "test-incident-123"}
            mock_http_client.post.return_value = create_response

            # Mock get incident response
            get_response = Mock()
            get_response.status_code = 200
            get_response.json.return_value = {
                "id": "test-incident-123",
                "status": "completed",
                "root_cause": "Test root cause",
                "confidence": "high",
            }
            mock_http_client.get.return_value = get_response

            mock_client_class.return_value = mock_http_client

            # Create CLI client
            cli_client = OrchestratorClient(base_url=base_url)

            # Create incident via CLI
            incident_id = await cli_client.create_incident("Pod is crashing")
            assert incident_id == "test-incident-123"

            # Retrieve incident via CLI
            incident = await cli_client.get_incident(incident_id)
            assert incident["id"] == "test-incident-123"
            assert incident["status"] == "completed"

            await cli_client.close()
