from fastapi.testclient import TestClient
from app.main import app
import uuid
from unittest.mock import patch, MagicMock
from app.models.pod_details import PodDetails, ContainerStatus, ResourceRequirements
from app.services.knowledge_graph_service import KnowledgeGraphService
from pathlib import Path

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
