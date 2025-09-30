from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch
from app.models.pod_details import PodDetails, ContainerStatus, ResourceRequirements
from app.services.knowledge_graph_service import KnowledgeGraphService
from pathlib import Path
import time

client = TestClient(app)

# Create a mock knowledge graph service for testing
knowledge_graph_path = (
    Path(__file__).parent.parent.parent.parent / "knowledge_graph.yaml"
)
if not knowledge_graph_path.exists():
    knowledge_graph_path.touch()
app.state.knowledge_graph_service = KnowledgeGraphService(
    knowledge_graph_path=knowledge_graph_path
)


def test_incident_end_to_end_workflow():
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
    mock_suggested_root_cause = "This is a mock root cause."
    mock_confidence_score = "High"

    with (
        patch("app.services.llm_client.LLMClient.__init__", return_value=None),
        patch(
            "app.services.llm_client.LLMClient.extract_entities",
            return_value=mock_extracted_entities,
        ),
        patch(
            "app.services.k8s_agent_client.K8sAgentClient.get_pod_details",
            return_value=mock_pod_details,
        ),
        patch(
            "app.services.k8s_agent_client.K8sAgentClient.get_pod_logs",
            return_value="mock logs",
        ),
        patch(
            "app.core.correlation_engine.CorrelationEngine.correlate",
            return_value=(mock_suggested_root_cause, mock_confidence_score),
        ),
    ):
        # 1. Create an incident
        create_response = client.post(
            "/api/v1/incidents",
            json={
                "description": "Test incident for end-to-end workflow pod:test-pod namespace:test-namespace"
            },
        )
        assert create_response.status_code == 202
        incident_id = create_response.json()["incident_id"]

        # 2. Poll for completion
        timeout = 30  # seconds
        start_time = time.time()
        while time.time() - start_time < timeout:
            get_response = client.get(f"/api/v1/incidents/{incident_id}")
            if get_response.status_code == 200:
                incident_data = get_response.json()
                if incident_data["status"] == "completed":
                    break
            time.sleep(1)
        else:
            assert False, "Incident did not complete within timeout."

        # 3. Assert the final report
        assert incident_data["id"] == incident_id
        assert (
            incident_data["description"]
            == "Test incident for end-to-end workflow pod:test-pod namespace:test-namespace"
        )
        assert incident_data["status"] == "completed"
        assert incident_data["completed_at"] is not None
        assert incident_data["evidence"] == {
            "pod_details": mock_pod_details.model_dump(),
            "pod_logs": "mock logs",
        }
        assert incident_data["extracted_entities"] == mock_extracted_entities
        assert incident_data["suggested_root_cause"] == mock_suggested_root_cause
        assert incident_data["confidence_score"] == mock_confidence_score
