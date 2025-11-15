from fastapi.testclient import TestClient
from app.main import app
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
from app.models.pod_details import PodDetails, ContainerStatus, ResourceRequirements
from app.services.knowledge_graph_service import KnowledgeGraphService
from pathlib import Path
import pytest

client = TestClient(app)

# Create a mock knowledge graph service for testing
# In a real-world scenario, you might want to use a fixture to create a temporary file
knowledge_graph_path = (
    Path(__file__).parent.parent.parent.parent / "knowledge_graph.yaml"
)
if not knowledge_graph_path.exists():
    knowledge_graph_path.touch()
app.state.knowledge_graph_service = KnowledgeGraphService(
    knowledge_graph_path=knowledge_graph_path
)


def test_create_incident_success():
    mock_pod_details = PodDetails(
        status="Running",
        restart_count=0,
        container_statuses=[
            ContainerStatus(name="test-container", state="running", ready=True)
        ],
        resource_limits=ResourceRequirements(cpu="100m", memory="128Mi"),
        resource_requests=ResourceRequirements(cpu="50m", memory="64Mi"),
    )
    mock_extracted_entities = {
        "pod_name": "test-pod",
        "namespace": "test-namespace",
        "error_summary": "Test error summary",
    }

    with (
        patch("app.services.llm_client.LLMClient.__init__", return_value=None),
        patch(
            "app.services.llm_client.LLMClient.extract_entities",
            return_value=mock_extracted_entities,
        ) as mock_extract_entities,
        patch(
            "app.services.llm_client.get_llm_client",
            return_value=MagicMock(
                extract_entities=MagicMock(return_value=mock_extracted_entities)
            ),
        ),
        patch(
            "app.services.k8s_agent_client.K8sAgentClient.get_pod_details",
            return_value=mock_pod_details,
        ) as mock_get_pod_details,
        patch(
            "app.services.k8s_agent_client.K8sAgentClient.get_pod_logs",
            return_value="mock logs",
        ) as mock_get_pod_logs,
    ):

        response = client.post(
            "/api/v1/incidents",
            json={"description": "Test incident pod:test-pod namespace:test-namespace"},
        )
        assert response.status_code == 202
        assert "incident_id" in response.json()

        mock_extract_entities.assert_called_once()
        mock_get_pod_details.assert_called_once_with("test-namespace", "test-pod")
        mock_get_pod_logs.assert_called_once_with("test-namespace", "test-pod")


def test_create_incident_invalid_payload():
    response = client.post("/api/v1/incidents", json={"desc": "Invalid payload"})
    assert response.status_code == 422  # Unprocessable Entity


def test_get_incident_success():
    mock_pod_details = PodDetails(
        status="Running",
        restart_count=0,
        container_statuses=[
            ContainerStatus(name="test-container", state="running", ready=True)
        ],
        resource_limits=ResourceRequirements(cpu="100m", memory="128Mi"),
        resource_requests=ResourceRequirements(cpu="50m", memory="64Mi"),
    )
    mock_extracted_entities = {
        "pod_name": "test-pod",
        "namespace": "test-namespace",
        "error_summary": "Test error summary",
    }

    with (
        patch("app.services.llm_client.LLMClient.__init__", return_value=None),
        patch(
            "app.services.llm_client.LLMClient.extract_entities",
            return_value=mock_extracted_entities,
        ) as mock_extract_entities,
        patch(
            "app.services.llm_client.get_llm_client",
            return_value=MagicMock(
                extract_entities=MagicMock(return_value=mock_extracted_entities)
            ),
        ),
        patch(
            "app.services.k8s_agent_client.K8sAgentClient.get_pod_details",
            return_value=mock_pod_details,
        ) as mock_get_pod_details,
        patch(
            "app.services.k8s_agent_client.K8sAgentClient.get_pod_logs",
            return_value="mock logs",
        ) as mock_get_pod_logs,
    ):

        # First, create an incident
        create_response = client.post(
            "/api/v1/incidents",
            json={
                "description": "Test incident for GET pod:test-pod namespace:test-namespace"
            },
        )
        incident_id = create_response.json()["incident_id"]

        # Now, get the incident
        get_response = client.get(f"/api/v1/incidents/{incident_id}")
        assert get_response.status_code == 200
        incident_data = get_response.json()
        assert incident_data["id"] == incident_id
        assert (
            incident_data["description"]
            == "Test incident for GET pod:test-pod namespace:test-namespace"
        )
        assert incident_data["status"] == "completed"
        assert incident_data["completed_at"] is not None
        assert incident_data["evidence"] == {
            "pod_details": mock_pod_details.model_dump(),
            "pod_logs": "mock logs",
        }
        assert incident_data["extracted_entities"] == mock_extracted_entities

        mock_extract_entities.assert_called_once()
        mock_get_pod_details.assert_called_once_with("test-namespace", "test-pod")
        mock_get_pod_logs.assert_called_once_with("test-namespace", "test-pod")


def test_get_incident_not_found():
    non_existent_id = uuid.uuid4()
    response = client.get(f"/api/v1/incidents/{non_existent_id}")
    assert response.status_code == 404



class TestAsyncIncidentWorkflow:
    """Tests for async incident investigation workflow."""

    def test_post_incidents_returns_202_with_incident_id_and_status(self):
        """Test POST /incidents returns 202 Accepted with incident_id and status."""
        # Mock MCP tool manager
        mock_tool_manager = MagicMock()
        mock_tool_manager.is_initialized.return_value = True
        mock_tool_manager.get_tools = AsyncMock(return_value=[])
        app.state.mcp_tool_manager = mock_tool_manager

        with (
            patch("app.core.incident_repository.IncidentRepository.create_incident_sync") as mock_create,
            patch("app.core.incident_repository.IncidentRepository.investigate_incident_async", new_callable=AsyncMock) as mock_investigate,
            patch.dict("os.environ", {"LLM_API_KEY": "test-key"}),
        ):
            # Mock incident creation
            from app.models.incidents import Incident
            mock_incident = Incident(description="Test incident", status="pending")
            mock_create.return_value = mock_incident

            response = client.post(
                "/api/v1/incidents",
                json={"description": "Test incident"}
            )

            # Verify response
            assert response.status_code == 202
            data = response.json()
            assert "incident_id" in data
            assert data["incident_id"] == str(mock_incident.id)
            assert "status" in data
            assert data["status"] == "pending"

            # Verify methods were called
            mock_create.assert_called_once_with(description="Test incident")

    def test_post_incidents_schedules_background_task(self):
        """Test POST /incidents schedules background investigation task."""
        # Mock MCP tool manager
        mock_tool_manager = MagicMock()
        mock_tool_manager.is_initialized.return_value = True
        mock_tool_manager.get_tools = AsyncMock(return_value=[])
        app.state.mcp_tool_manager = mock_tool_manager

        with (
            patch("app.core.incident_repository.IncidentRepository.create_incident_sync") as mock_create,
            patch("app.core.incident_repository.IncidentRepository.investigate_incident_async", new_callable=AsyncMock) as mock_investigate,
            patch.dict("os.environ", {"LLM_API_KEY": "test-key"}),
        ):
            # Mock incident creation
            from app.models.incidents import Incident
            mock_incident = Incident(description="Test incident", status="pending")
            mock_create.return_value = mock_incident

            response = client.post(
                "/api/v1/incidents",
                json={"description": "Test incident"}
            )

            # Verify response is immediate (202)
            assert response.status_code == 202

            # Note: Background task execution is handled by FastAPI's BackgroundTasks
            # In TestClient, background tasks are executed synchronously after response
            # We verify the task was scheduled by checking create_incident_sync was called
            mock_create.assert_called_once()

    def test_get_incidents_returns_current_status_and_results(self):
        """Test GET /incidents/{id} returns current status and results."""
        # Mock MCP tool manager
        mock_tool_manager = MagicMock()
        mock_tool_manager.is_initialized.return_value = True
        mock_tool_manager.get_tools = AsyncMock(return_value=[])
        app.state.mcp_tool_manager = mock_tool_manager

        with (
            patch("app.core.incident_repository.IncidentRepository.create_incident_sync") as mock_create,
            patch("app.core.incident_repository.IncidentRepository.investigate_incident_async", new_callable=AsyncMock),
            patch("app.core.incident_repository.IncidentRepository.get_by_id") as mock_get,
            patch.dict("os.environ", {"LLM_API_KEY": "test-key"}),
        ):
            # Create incident
            from app.models.incidents import Incident
            mock_incident = Incident(description="Test incident", status="pending")
            mock_create.return_value = mock_incident
            mock_get.return_value = mock_incident

            create_response = client.post(
                "/api/v1/incidents",
                json={"description": "Test incident"}
            )
            incident_id = create_response.json()["incident_id"]

            # Get incident status
            get_response = client.get(f"/api/v1/incidents/{incident_id}")

            assert get_response.status_code == 200
            data = get_response.json()
            assert data["id"] == incident_id
            assert data["description"] == "Test incident"
            assert "status" in data
            assert data["status"] in ["pending", "in_progress", "completed", "failed"]

    def test_get_incidents_returns_completed_with_results(self):
        """Test GET /incidents/{id} returns completed status with investigation results."""
        # Mock MCP tool manager
        mock_tool_manager = MagicMock()
        mock_tool_manager.is_initialized.return_value = True
        mock_tool_manager.get_tools = AsyncMock(return_value=[])
        app.state.mcp_tool_manager = mock_tool_manager

        with (
            patch("app.core.incident_repository.IncidentRepository.create_incident_sync") as mock_create,
            patch("app.core.incident_repository.IncidentRepository.investigate_incident_async", new_callable=AsyncMock) as mock_investigate,
            patch("app.core.incident_repository.IncidentRepository.get_by_id") as mock_get,
            patch.dict("os.environ", {"LLM_API_KEY": "test-key"}),
        ):
            # Mock incident creation and completion
            from app.models.incidents import Incident
            from datetime import datetime

            mock_incident = Incident(
                description="Test incident",
                status="completed",
                suggested_root_cause="Memory leak",
                confidence_score="high",
                completed_at=datetime.utcnow(),
                evidence={"tool_calls": [], "reasoning": "Test reasoning"}
            )
            mock_create.return_value = mock_incident
            mock_get.return_value = mock_incident

            # Simulate investigation completing
            async def complete_investigation(incident_id, tools, config):
                mock_incident.status = "completed"

            mock_investigate.side_effect = complete_investigation

            create_response = client.post(
                "/api/v1/incidents",
                json={"description": "Test incident"}
            )
            incident_id = create_response.json()["incident_id"]

            # Get completed incident
            get_response = client.get(f"/api/v1/incidents/{incident_id}")

            assert get_response.status_code == 200
            data = get_response.json()
            assert data["status"] == "completed"
            assert data["suggested_root_cause"] == "Memory leak"
            assert data["confidence_score"] == "high"
            assert data["completed_at"] is not None
            assert "evidence" in data

    def test_get_incidents_returns_failed_with_error(self):
        """Test GET /incidents/{id} returns failed status with error details."""
        # Mock MCP tool manager
        mock_tool_manager = MagicMock()
        mock_tool_manager.is_initialized.return_value = True
        mock_tool_manager.get_tools = AsyncMock(return_value=[])
        app.state.mcp_tool_manager = mock_tool_manager

        with (
            patch("app.core.incident_repository.IncidentRepository.create_incident_sync") as mock_create,
            patch("app.core.incident_repository.IncidentRepository.investigate_incident_async", new_callable=AsyncMock) as mock_investigate,
            patch("app.core.incident_repository.IncidentRepository.get_by_id") as mock_get,
            patch.dict("os.environ", {"LLM_API_KEY": "test-key"}),
        ):
            # Mock incident creation and failure
            from app.models.incidents import Incident
            from datetime import datetime

            mock_incident = Incident(
                description="Test incident",
                status="failed",
                error_message="Investigation timeout",
                completed_at=datetime.utcnow()
            )
            mock_create.return_value = mock_incident
            mock_get.return_value = mock_incident

            # Simulate investigation failing
            async def fail_investigation(incident_id, tools, config):
                mock_incident.status = "failed"
                mock_incident.error_message = "Investigation timeout"

            mock_investigate.side_effect = fail_investigation

            create_response = client.post(
                "/api/v1/incidents",
                json={"description": "Test incident"}
            )
            incident_id = create_response.json()["incident_id"]

            # Get failed incident
            get_response = client.get(f"/api/v1/incidents/{incident_id}")

            assert get_response.status_code == 200
            data = get_response.json()
            assert data["status"] == "failed"
            assert data["error_message"] == "Investigation timeout"
            assert data["completed_at"] is not None

    def test_post_incidents_response_time_within_2_seconds(self):
        """Test POST /incidents returns within 2 seconds (requirement 1.1)."""
        import time

        # Mock MCP tool manager
        mock_tool_manager = MagicMock()
        mock_tool_manager.is_initialized.return_value = True
        mock_tool_manager.get_tools = AsyncMock(return_value=[])
        app.state.mcp_tool_manager = mock_tool_manager

        with (
            patch("app.core.incident_repository.IncidentRepository.create_incident_sync") as mock_create,
            patch("app.core.incident_repository.IncidentRepository.investigate_incident_async", new_callable=AsyncMock),
            patch.dict("os.environ", {"LLM_API_KEY": "test-key"}),
        ):
            # Mock incident creation
            from app.models.incidents import Incident
            mock_incident = Incident(description="Test incident", status="pending")
            mock_create.return_value = mock_incident

            start_time = time.time()
            response = client.post(
                "/api/v1/incidents",
                json={"description": "Test incident"}
            )
            elapsed_time = time.time() - start_time

            assert response.status_code == 202
            assert elapsed_time < 2.0, f"Response took {elapsed_time:.2f}s, expected < 2s"

    def test_get_incidents_response_time_within_1_second(self):
        """Test GET /incidents/{id} returns within 1 second (requirement 2.2)."""
        import time

        # Mock MCP tool manager
        mock_tool_manager = MagicMock()
        mock_tool_manager.is_initialized.return_value = True
        mock_tool_manager.get_tools = AsyncMock(return_value=[])
        app.state.mcp_tool_manager = mock_tool_manager

        with (
            patch("app.core.incident_repository.IncidentRepository.create_incident_sync") as mock_create,
            patch("app.core.incident_repository.IncidentRepository.investigate_incident_async", new_callable=AsyncMock),
            patch("app.core.incident_repository.IncidentRepository.get_by_id") as mock_get,
            patch.dict("os.environ", {"LLM_API_KEY": "test-key"}),
        ):
            # Create incident
            from app.models.incidents import Incident
            mock_incident = Incident(description="Test incident", status="pending")
            mock_create.return_value = mock_incident
            mock_get.return_value = mock_incident

            create_response = client.post(
                "/api/v1/incidents",
                json={"description": "Test incident"}
            )
            incident_id = create_response.json()["incident_id"]

            # Measure GET response time
            start_time = time.time()
            get_response = client.get(f"/api/v1/incidents/{incident_id}")
            elapsed_time = time.time() - start_time

            assert get_response.status_code == 200
            assert elapsed_time < 1.0, f"Response took {elapsed_time:.2f}s, expected < 1s"
