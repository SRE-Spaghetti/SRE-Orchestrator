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

def test_read_pod_logs_success():
    mock_logs = "This is a log line 1\nThis is a log line 2"
    with patch("app.api.v1.pods.get_pod_logs", return_value=mock_logs) as mock_get_pod_logs:
        response = client.get("/api/v1/pods/test-namespace/test-pod/logs")
        assert response.status_code == 200
        assert response.text == mock_logs
        mock_get_pod_logs.assert_called_once_with("test-namespace", "test-pod", None, 100)

def test_read_pod_logs_with_params_success():
    mock_logs = "Container log line 1\nContainer log line 2"
    with patch("app.api.v1.pods.get_pod_logs", return_value=mock_logs) as mock_get_pod_logs:
        response = client.get("/api/v1/pods/test-namespace/test-pod/logs?container=my-container&tail=50")
        assert response.status_code == 200
        assert response.text == mock_logs
        mock_get_pod_logs.assert_called_once_with("test-namespace", "test-pod", "my-container", 50)

def test_read_pod_logs_not_found():
    with patch("app.api.v1.pods.get_pod_logs", return_value=None) as mock_get_pod_logs:
        response = client.get("/api/v1/pods/test-namespace/nonexistent-pod/logs")
        assert response.status_code == 404
        assert response.json() == {"detail": "Pod logs not found or pod/container does not exist"}
        mock_get_pod_logs.assert_called_once_with("test-namespace", "nonexistent-pod", None, 100)
