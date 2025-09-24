from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_incident_success():
    response = client.post("/api/v1/incidents", json={"description": "Test incident"})
    assert response.status_code == 202
    assert "incident_id" in response.json()

def test_create_incident_invalid_payload():
    response = client.post("/api/v1/incidents", json={"desc": "Invalid payload"})
    assert response.status_code == 422  # Unprocessable Entity
