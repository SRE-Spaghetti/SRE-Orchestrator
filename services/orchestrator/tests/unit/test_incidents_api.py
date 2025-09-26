from fastapi.testclient import TestClient
from app.main import app
import uuid

client = TestClient(app)


def test_create_incident_success():
    response = client.post("/api/v1/incidents", json={"description": "Test incident"})
    assert response.status_code == 202
    assert "incident_id" in response.json()


def test_create_incident_invalid_payload():
    response = client.post("/api/v1/incidents", json={"desc": "Invalid payload"})
    assert response.status_code == 422  # Unprocessable Entity


def test_get_incident_success():
    # First, create an incident
    create_response = client.post(
        "/api/v1/incidents", json={"description": "Test incident for GET"}
    )
    incident_id = create_response.json()["incident_id"]

    # Now, get the incident
    get_response = client.get(f"/api/v1/incidents/{incident_id}")
    assert get_response.status_code == 200
    incident_data = get_response.json()
    assert incident_data["id"] == incident_id
    assert incident_data["description"] == "Test incident for GET"
    assert incident_data["status"] == "pending"


def test_get_incident_not_found():
    non_existent_id = uuid.uuid4()
    response = client.get(f"/api/v1/incidents/{non_existent_id}")
    assert response.status_code == 404
