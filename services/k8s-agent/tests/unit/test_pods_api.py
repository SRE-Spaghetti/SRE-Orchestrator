from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from app.models.pod_details import PodDetails, ContainerStatus, ResourceRequirements

client = TestClient(app)

def test_read_pod_success():
    mock_pod_details = PodDetails(
        status="Running",
        restart_count=0,
        container_statuses=[
            ContainerStatus(name="test-container", state="running", ready=True)
        ],
        resource_limits=ResourceRequirements(cpu="100m", memory="128Mi"),
        resource_requests=ResourceRequirements(cpu="50m", memory="64Mi"),
    )
    with patch("app.api.v1.pods.get_pod_details", return_value=mock_pod_details) as mock_get_pod_details:
        response = client.get("/api/v1/pods/test-namespace/test-pod")
        assert response.status_code == 200
        assert response.json() == mock_pod_details.model_dump()
        mock_get_pod_details.assert_called_once_with("test-namespace", "test-pod")

def test_read_pod_not_found():
    with patch("app.api.v1.pods.get_pod_details", return_value=None) as mock_get_pod_details:
        response = client.get("/api/v1/pods/test-namespace/nonexistent-pod")
        assert response.status_code == 404
        assert response.json() == {"detail": "Pod not found"}
        mock_get_pod_details.assert_called_once_with("test-namespace", "nonexistent-pod")
