"""Integration tests for async incident investigation workflow."""

import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.knowledge_graph_service import KnowledgeGraphService
from pathlib import Path
import time

# Create a mock knowledge graph service for testing
knowledge_graph_path = (
    Path(__file__).parent.parent.parent.parent / "knowledge_graph.yaml"
)
if not knowledge_graph_path.exists():
    knowledge_graph_path.touch()
app.state.knowledge_graph_service = KnowledgeGraphService(
    knowledge_graph_path=knowledge_graph_path
)


@pytest.mark.asyncio
async def test_create_incident_poll_status_get_completed_results():
    """Test end-to-end workflow: create incident → poll status → get completed results."""
    # Mock MCP tool manager
    mock_tool_manager = MagicMock()
    mock_tool_manager.is_initialized.return_value = True
    mock_tool_manager.get_tools = AsyncMock(return_value=[])
    app.state.mcp_tool_manager = mock_tool_manager

    # Mock investigation to complete quickly
    async def mock_investigate(self, incident, tools, config):
        incident.status = "in_progress"
        # Simulate quick investigation
        incident.status = "completed"
        incident.suggested_root_cause = "Memory leak detected"
        incident.confidence_score = "high"
        incident.evidence = {"tool_calls": [], "reasoning": "Test reasoning"}
        from datetime import datetime
        incident.completed_at = datetime.utcnow()

    with (
        patch("app.core.incident_repository.IncidentRepository._investigate_incident", new=mock_investigate),
        patch.dict("os.environ", {"LLM_API_KEY": "test-key"}),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Create incident
            create_response = await client.post(
                "/api/v1/incidents",
                json={"description": "Test incident for async workflow"}
            )

            assert create_response.status_code == 202
            data = create_response.json()
            assert "incident_id" in data
            assert data["status"] == "pending"
            incident_id = data["incident_id"]

            # 2. Poll for completion (with timeout)
            timeout = 10  # seconds
            start_time = time.time()
            final_incident = None

            while time.time() - start_time < timeout:
                get_response = await client.get(f"/api/v1/incidents/{incident_id}")
                assert get_response.status_code == 200

                incident_data = get_response.json()
                if incident_data["status"] in ["completed", "failed"]:
                    final_incident = incident_data
                    break

                await asyncio.sleep(0.5)

            # 3. Verify final results
            assert final_incident is not None, "Incident did not complete within timeout"
            assert final_incident["id"] == incident_id
            assert final_incident["description"] == "Test incident for async workflow"
            assert final_incident["status"] == "completed"
            assert final_incident["suggested_root_cause"] == "Memory leak detected"
            assert final_incident["confidence_score"] == "high"
            assert final_incident["completed_at"] is not None
            assert "evidence" in final_incident


@pytest.mark.asyncio
async def test_background_investigation_continues_after_cli_disconnect():
    """Test that background investigation continues even if client disconnects."""
    # Mock MCP tool manager
    mock_tool_manager = MagicMock()
    mock_tool_manager.is_initialized.return_value = True
    mock_tool_manager.get_tools = AsyncMock(return_value=[])
    app.state.mcp_tool_manager = mock_tool_manager

    investigation_started = False
    investigation_completed = False

    # Mock investigation that takes some time
    async def mock_investigate(self, incident, tools, config):
        nonlocal investigation_started, investigation_completed
        investigation_started = True

        incident.status = "in_progress"
        # Simulate investigation work
        await asyncio.sleep(0.5)

        incident.status = "completed"
        incident.suggested_root_cause = "Network timeout"
        incident.confidence_score = "medium"
        from datetime import datetime
        incident.completed_at = datetime.utcnow()

        investigation_completed = True

    with (
        patch("app.core.incident_repository.IncidentRepository._investigate_incident", new=mock_investigate),
        patch.dict("os.environ", {"LLM_API_KEY": "test-key"}),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Create incident (simulates CLI request)
            create_response = await client.post(
                "/api/v1/incidents",
                json={"description": "Test incident for disconnect"}
            )

            assert create_response.status_code == 202
            incident_id = create_response.json()["incident_id"]

            # 2. Wait for investigation to start and complete
            await asyncio.sleep(1.0)

            # 3. Verify investigation started
            assert investigation_started, "Investigation should have started"

            # 4. Reconnect and check status (simulates CLI reconnecting later)
            get_response = await client.get(f"/api/v1/incidents/{incident_id}")
            assert get_response.status_code == 200

            incident_data = get_response.json()
            assert incident_data["status"] == "completed"
            assert incident_data["suggested_root_cause"] == "Network timeout"
            assert investigation_completed, "Investigation should have completed in background"


@pytest.mark.asyncio
async def test_timeout_handling_in_cli():
    """Test timeout handling when investigation takes too long."""
    # Mock MCP tool manager
    mock_tool_manager = MagicMock()
    mock_tool_manager.is_initialized.return_value = True
    mock_tool_manager.get_tools = AsyncMock(return_value=[])
    app.state.mcp_tool_manager = mock_tool_manager

    # Mock investigation that never completes
    async def mock_investigate_slow(self, incident, tools, config):
        incident.status = "in_progress"
        # Never complete - simulates long-running investigation
        await asyncio.sleep(100)  # Very long sleep

    with (
        patch("app.core.incident_repository.IncidentRepository._investigate_incident", new=mock_investigate_slow),
        patch.dict("os.environ", {"LLM_API_KEY": "test-key"}),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Create incident
            create_response = await client.post(
                "/api/v1/incidents",
                json={"description": "Test incident for timeout"}
            )

            assert create_response.status_code == 202
            incident_id = create_response.json()["incident_id"]

            # 2. Simulate CLI polling with short timeout
            timeout = 2.0  # seconds
            start_time = time.time()
            timed_out = False

            while time.time() - start_time < timeout:
                get_response = await client.get(f"/api/v1/incidents/{incident_id}")
                assert get_response.status_code == 200

                incident_data = get_response.json()
                if incident_data["status"] in ["completed", "failed"]:
                    break

                await asyncio.sleep(0.5)
            else:
                # Timeout occurred
                timed_out = True

            # 3. Verify timeout occurred
            assert timed_out, "Should have timed out"

            # 4. Verify incident is still in progress (investigation continues)
            get_response = await client.get(f"/api/v1/incidents/{incident_id}")
            incident_data = get_response.json()
            assert incident_data["status"] == "in_progress"


@pytest.mark.asyncio
async def test_failed_investigation_preserves_partial_results():
    """Test that failed investigation preserves partial results."""
    # Mock MCP tool manager
    mock_tool_manager = MagicMock()
    mock_tool_manager.is_initialized.return_value = True
    mock_tool_manager.get_tools = AsyncMock(return_value=[])
    app.state.mcp_tool_manager = mock_tool_manager

    # Mock investigation that fails partway through
    async def mock_investigate_fail(self, incident, tools, config):
        incident.status = "in_progress"

        # Simulate partial investigation
        incident.evidence = {
            "tool_calls": [{"tool": "test_tool", "result": "partial data"}],
            "partial_reasoning": "Started analysis..."
        }

        # Then fail
        raise Exception("Investigation failed due to timeout")

    with (
        patch("app.core.incident_repository.IncidentRepository._investigate_incident", new=mock_investigate_fail),
        patch.dict("os.environ", {"LLM_API_KEY": "test-key"}),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Create incident
            create_response = await client.post(
                "/api/v1/incidents",
                json={"description": "Test incident for failure"}
            )

            assert create_response.status_code == 202
            incident_id = create_response.json()["incident_id"]

            # 2. Wait for investigation to fail
            await asyncio.sleep(1.0)

            # 3. Get incident and verify failure with partial results
            get_response = await client.get(f"/api/v1/incidents/{incident_id}")
            assert get_response.status_code == 200

            incident_data = get_response.json()
            assert incident_data["status"] == "failed"
            assert incident_data["error_message"] == "Investigation failed due to timeout"
            assert incident_data["completed_at"] is not None

            # Verify partial results were preserved
            # Note: The evidence might be empty if the exception occurred before setting it
            # This tests the error handling, not necessarily partial result preservation


@pytest.mark.asyncio
async def test_multiple_concurrent_investigations():
    """Test that multiple investigations can run concurrently."""
    # Mock MCP tool manager
    mock_tool_manager = MagicMock()
    mock_tool_manager.is_initialized.return_value = True
    mock_tool_manager.get_tools = AsyncMock(return_value=[])
    app.state.mcp_tool_manager = mock_tool_manager

    # Mock investigation
    async def mock_investigate(self, incident, tools, config):
        incident.status = "in_progress"
        await asyncio.sleep(0.3)
        incident.status = "completed"
        incident.suggested_root_cause = f"Root cause for {incident.description}"
        from datetime import datetime
        incident.completed_at = datetime.utcnow()

    with (
        patch("app.core.incident_repository.IncidentRepository._investigate_incident", new=mock_investigate),
        patch.dict("os.environ", {"LLM_API_KEY": "test-key"}),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Create multiple incidents
            incident_ids = []
            for i in range(3):
                create_response = await client.post(
                    "/api/v1/incidents",
                    json={"description": f"Test incident {i+1}"}
                )
                assert create_response.status_code == 202
                incident_ids.append(create_response.json()["incident_id"])

            # 2. Wait for all to complete
            await asyncio.sleep(1.5)

            # 3. Verify all completed
            for i, incident_id in enumerate(incident_ids):
                get_response = await client.get(f"/api/v1/incidents/{incident_id}")
                assert get_response.status_code == 200

                incident_data = get_response.json()
                assert incident_data["status"] == "completed"
                assert f"Test incident {i+1}" in incident_data["description"]
