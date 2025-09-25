import httpx
import pytest
from unittest.mock import patch, MagicMock
from app.services.k8s_agent_client import K8sAgentClient

@pytest.fixture
def k8s_agent_client():
    return K8sAgentClient(base_url="http://mock-k8s-agent")

def test_get_pod_details_success(k8s_agent_client):
    mock_response_json = {
        "status": "Running",
        "restart_count": 0,
        "container_statuses": [
            {"name": "test-container", "state": "running", "ready": True}
        ],
        "resource_limits": {"cpu": "100m", "memory": "128Mi"},
        "resource_requests": {"cpu": "50m", "memory": "64Mi"},
    }
    with patch.object(k8s_agent_client.client, "get") as mock_get:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_json
        mock_response.raise_for_status.return_value = None # No error
        mock_get.return_value = mock_response

        pod_details = k8s_agent_client.get_pod_details("test-namespace", "test-pod")

        assert pod_details is not None
        assert pod_details.status == "Running"
        assert pod_details.restart_count == 0
        assert len(pod_details.container_statuses) == 1
        assert pod_details.container_statuses[0].name == "test-container"
        assert pod_details.resource_limits.cpu == "100m"
        mock_get.assert_called_once_with("http://mock-k8s-agent/api/v1/pods/test-namespace/test-pod")

def test_get_pod_details_not_found(k8s_agent_client):
    with patch.object(k8s_agent_client.client, "get") as mock_get:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("Not Found", request=httpx.Request("GET", "url"), response=mock_response)
        mock_get.return_value = mock_response

        pod_details = k8s_agent_client.get_pod_details("test-namespace", "nonexistent-pod")

        assert pod_details is None
        mock_get.assert_called_once_with("http://mock-k8s-agent/api/v1/pods/test-namespace/nonexistent-pod")

def test_get_pod_logs_success(k8s_agent_client):
    mock_logs = "log line 1\nlog line 2"
    with patch.object(k8s_agent_client.client, "get") as mock_get:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = mock_logs
        mock_response.raise_for_status.return_value = None # No error
        mock_get.return_value = mock_response

        logs = k8s_agent_client.get_pod_logs("test-namespace", "test-pod")

        assert logs == mock_logs
        mock_get.assert_called_once_with("http://mock-k8s-agent/api/v1/pods/test-namespace/test-pod/logs", params={"tail": 100})

def test_get_pod_logs_with_params_success(k8s_agent_client):
    mock_logs = "container log line 1\ncontainer log line 2"
    with patch.object(k8s_agent_client.client, "get") as mock_get:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = mock_logs
        mock_response.raise_for_status.return_value = None # No error
        mock_get.return_value = mock_response

        logs = k8s_agent_client.get_pod_logs("test-namespace", "test-pod", container="my-container", tail=50)

        assert logs == mock_logs
        mock_get.assert_called_once_with("http://mock-k8s-agent/api/v1/pods/test-namespace/test-pod/logs", params={"container": "my-container", "tail": 50})

def test_get_pod_logs_not_found(k8s_agent_client):
    with patch.object(k8s_agent_client.client, "get") as mock_get:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("Not Found", request=httpx.Request("GET", "url"), response=mock_response)
        mock_get.return_value = mock_response

        logs = k8s_agent_client.get_pod_logs("test-namespace", "nonexistent-pod")

        assert logs is None
        mock_get.assert_called_once_with("http://mock-k8s-agent/api/v1/pods/test-namespace/nonexistent-pod/logs", params={"tail": 100})
