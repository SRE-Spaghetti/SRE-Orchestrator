from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_read_health():
    """
    Tests the /health endpoint.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "mcp_connections" in response.json()
