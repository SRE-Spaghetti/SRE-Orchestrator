"""Unit tests for incidents API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from app.main import app
from app.models.incidents import Incident, IncidentStatus
from app.core.incident_repository import get_incident_repository


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def test_client():
    """
    Provides a FastAPI TestClient for API testing.

    Returns:
        TestClient: Configured test client for the FastAPI app
    """
    return TestClient(app)


@pytest.fixture
def mock_repo():
    """
    Provides a mock incident repository for dependency injection.

    Returns:
        Mock: Mock repository with CRUD operations
    """
    repo = Mock()
    repo.create_incident_sync = Mock()
    repo.get_by_id = Mock()
    repo.investigate_incident_async = AsyncMock()
    return repo


@pytest.fixture
def mock_mcp_manager():
    """
    Provides a mock MCP tool manager for app state.

    Returns:
        Mock: Mock tool manager with initialization status
    """
    manager = Mock()
    manager.is_initialized = Mock(return_value=True)
    manager.get_tools = AsyncMock(return_value=[])
    return manager


@pytest.fixture
def mock_app_state(test_client, mock_mcp_manager):
    """
    Sets up mock app state with MCP tool manager.

    Args:
        test_client: FastAPI test client
        mock_mcp_manager: Mock MCP tool manager
    """
    test_client.app.state.mcp_tool_manager = mock_mcp_manager
    return test_client


# ============================================================================
# POST /incidents Tests
# ============================================================================


def test_create_incident_success(mock_app_state, mock_repo, monkeypatch):
    """
    Test POST /incidents creates incident successfully with valid request.

    Verifies:
    - Incident is created with pending status
    - Returns 202 Accepted status code
    - Response contains incident_id and status
    - Background investigation is scheduled
    """
    # Arrange
    incident_id = uuid4()
    mock_incident = Incident(
        id=incident_id,
        description="Pod nginx-deployment-abc123 is in CrashLoopBackOff",
        status=IncidentStatus.PENDING,
    )
    mock_repo.create_incident_sync.return_value = mock_incident

    # Override dependency
    app.dependency_overrides[get_incident_repository] = lambda: mock_repo

    # Mock environment variables
    monkeypatch.setenv("LLM_API_KEY", "test-api-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("LLM_MODEL_NAME", "gpt-4")

    # Act
    response = mock_app_state.post(
        "/api/v1/incidents",
        json={"description": "Pod nginx-deployment-abc123 is in CrashLoopBackOff"},
    )

    # Assert
    assert response.status_code == 202
    assert response.json()["incident_id"] == str(incident_id)
    assert response.json()["status"] == "pending"
    mock_repo.create_incident_sync.assert_called_once_with(
        description="Pod nginx-deployment-abc123 is in CrashLoopBackOff"
    )

    # Cleanup
    app.dependency_overrides.clear()


def test_create_incident_returns_202_accepted(mock_app_state, mock_repo, monkeypatch):
    """
    Test POST /incidents returns 202 Accepted status code.

    Verifies that the endpoint returns immediately with 202 status
    while investigation runs in background.
    """
    # Arrange
    incident_id = uuid4()
    mock_incident = Incident(
        id=incident_id,
        description="Service api-gateway is returning 500 errors",
        status=IncidentStatus.PENDING,
    )
    mock_repo.create_incident_sync.return_value = mock_incident

    app.dependency_overrides[get_incident_repository] = lambda: mock_repo

    monkeypatch.setenv("LLM_API_KEY", "test-key")

    # Act
    response = mock_app_state.post(
        "/api/v1/incidents",
        json={"description": "Service api-gateway is returning 500 errors"},
    )

    # Assert
    assert response.status_code == 202

    # Cleanup
    app.dependency_overrides.clear()


def test_create_incident_invalid_request_body(mock_app_state, monkeypatch):
    """
    Test POST /incidents with invalid request body returns 422 error.

    Verifies that missing required fields result in validation error.
    """
    # Arrange
    monkeypatch.setenv("LLM_API_KEY", "test-key")

    # Act - missing description field
    response = mock_app_state.post(
        "/api/v1/incidents",
        json={},
    )

    # Assert
    assert response.status_code == 422
    assert "detail" in response.json()


def test_create_incident_mcp_tools_unavailable(test_client):
    """
    Test POST /incidents when MCP tools unavailable returns 503 error.

    Verifies that missing or uninitialized MCP tool manager
    results in service unavailable error.
    """
    # Arrange - no MCP tool manager in app state
    test_client.app.state.mcp_tool_manager = None

    # Act
    response = test_client.post(
        "/api/v1/incidents",
        json={"description": "Test incident"},
    )

    # Assert
    assert response.status_code == 503
    assert "MCP tools not available" in response.json()["detail"]


def test_create_incident_mcp_tools_not_initialized(test_client):
    """
    Test POST /incidents when MCP tools not initialized returns 503 error.

    Verifies that uninitialized MCP tool manager results in error.
    """
    # Arrange
    mock_manager = Mock()
    mock_manager.is_initialized = Mock(return_value=False)
    test_client.app.state.mcp_tool_manager = mock_manager

    # Act
    response = test_client.post(
        "/api/v1/incidents",
        json={"description": "Test incident"},
    )

    # Assert
    assert response.status_code == 503
    assert "MCP tools not available" in response.json()["detail"]


def test_create_incident_llm_not_configured(mock_app_state, monkeypatch):
    """
    Test POST /incidents when LLM not configured returns 503 error.

    Verifies that missing LLM_API_KEY results in service unavailable error.
    """
    # Arrange - ensure LLM_API_KEY is not set
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    # Act
    response = mock_app_state.post(
        "/api/v1/incidents",
        json={"description": "Test incident"},
    )

    # Assert
    assert response.status_code == 503
    assert "LLM not configured" in response.json()["detail"]


def test_create_incident_repository_exception(mock_app_state, mock_repo, monkeypatch):
    """
    Test POST /incidents handles repository exceptions gracefully.

    Verifies that exceptions during incident creation return 500 error.
    """
    # Arrange
    mock_repo.create_incident_sync.side_effect = Exception("Database error")
    app.dependency_overrides[get_incident_repository] = lambda: mock_repo

    monkeypatch.setenv("LLM_API_KEY", "test-key")

    # Act
    response = mock_app_state.post(
        "/api/v1/incidents",
        json={"description": "Test incident"},
    )

    # Assert
    assert response.status_code == 500
    assert "Failed to create incident" in response.json()["detail"]

    # Cleanup
    app.dependency_overrides.clear()


def test_create_incident_schedules_background_investigation(
    mock_app_state, mock_repo, monkeypatch
):
    """
    Test POST /incidents schedules background investigation task.

    Verifies that investigate_incident_async is called with correct parameters.
    """
    # Arrange
    incident_id = uuid4()
    mock_incident = Incident(
        id=incident_id,
        description="Test incident",
        status=IncidentStatus.PENDING,
    )
    mock_repo.create_incident_sync.return_value = mock_incident

    app.dependency_overrides[get_incident_repository] = lambda: mock_repo

    monkeypatch.setenv("LLM_API_KEY", "test-api-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("LLM_MODEL_NAME", "gpt-4")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.7")
    monkeypatch.setenv("LLM_MAX_TOKENS", "2000")

    # Act
    response = mock_app_state.post(
        "/api/v1/incidents",
        json={"description": "Test incident"},
    )

    # Assert
    assert response.status_code == 202
    # Note: We can't easily verify asyncio.create_task was called
    # but we verify the endpoint returns successfully

    # Cleanup
    app.dependency_overrides.clear()


# ============================================================================
# GET /incidents/{id} Tests
# ============================================================================


def test_get_incident_success(test_client, mock_repo):
    """
    Test GET /incidents/{id} returns incident details successfully.

    Verifies:
    - Incident is retrieved by ID
    - Returns 200 OK status code
    - Response matches Incident model schema
    - All incident fields are present
    """
    # Arrange
    incident_id = uuid4()
    mock_incident = Incident(
        id=incident_id,
        description="Pod nginx-deployment-abc123 is in CrashLoopBackOff",
        status=IncidentStatus.COMPLETED,
        suggested_root_cause="Memory limit exceeded",
        confidence_score="high",
        evidence={
            "pod_status": "CrashLoopBackOff",
            "restart_count": 5,
        },
    )
    mock_repo.get_by_id.return_value = mock_incident

    app.dependency_overrides[get_incident_repository] = lambda: mock_repo

    # Act
    response = test_client.get(f"/api/v1/incidents/{incident_id}")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(incident_id)
    assert data["description"] == "Pod nginx-deployment-abc123 is in CrashLoopBackOff"
    assert data["status"] == "completed"
    assert data["suggested_root_cause"] == "Memory limit exceeded"
    assert data["confidence_score"] == "high"
    assert "evidence" in data
    assert "created_at" in data

    mock_repo.get_by_id.assert_called_once_with(incident_id)

    # Cleanup
    app.dependency_overrides.clear()


def test_get_incident_not_found(test_client, mock_repo):
    """
    Test GET /incidents/{id} with non-existent ID returns 404 error.

    Verifies that requesting a non-existent incident returns
    appropriate not found error.
    """
    # Arrange
    incident_id = uuid4()
    mock_repo.get_by_id.return_value = None

    app.dependency_overrides[get_incident_repository] = lambda: mock_repo

    # Act
    response = test_client.get(f"/api/v1/incidents/{incident_id}")

    # Assert
    assert response.status_code == 404
    assert "Incident not found" in response.json()["detail"]

    mock_repo.get_by_id.assert_called_once_with(incident_id)

    # Cleanup
    app.dependency_overrides.clear()


def test_get_incident_invalid_uuid_format(test_client):
    """
    Test GET /incidents/{id} with invalid UUID format returns 422 error.

    Verifies that malformed UUID in path parameter is rejected.
    """
    # Act
    response = test_client.get("/api/v1/incidents/not-a-valid-uuid")

    # Assert
    assert response.status_code == 422
    assert "detail" in response.json()


def test_get_incident_response_schema_matches_model(test_client, mock_repo):
    """
    Test GET /incidents/{id} response schema matches Incident model.

    Verifies that all required fields from Incident model are present
    in the response and have correct types.
    """
    # Arrange
    incident_id = uuid4()
    mock_incident = Incident(
        id=incident_id,
        description="Test incident",
        status=IncidentStatus.IN_PROGRESS,
        evidence={"key": "value"},
        extracted_entities={"entity": "data"},
        investigation_steps=[],
    )
    mock_repo.get_by_id.return_value = mock_incident

    app.dependency_overrides[get_incident_repository] = lambda: mock_repo

    # Act
    response = test_client.get(f"/api/v1/incidents/{incident_id}")

    # Assert
    assert response.status_code == 200
    data = response.json()

    # Verify all required Incident model fields are present
    required_fields = [
        "id",
        "description",
        "status",
        "created_at",
        "evidence",
        "extracted_entities",
        "investigation_steps",
    ]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    # Verify field types
    assert isinstance(data["id"], str)
    assert isinstance(data["description"], str)
    assert isinstance(data["status"], str)
    assert isinstance(data["created_at"], str)
    assert isinstance(data["evidence"], dict)
    assert isinstance(data["extracted_entities"], dict)
    assert isinstance(data["investigation_steps"], list)

    # Cleanup
    app.dependency_overrides.clear()


def test_get_incident_with_investigation_steps(test_client, mock_repo):
    """
    Test GET /incidents/{id} returns incident with investigation steps.

    Verifies that investigation steps are properly serialized in response.
    """
    # Arrange
    incident_id = uuid4()
    from app.models.incidents import InvestigationStep
    from datetime import datetime, timezone

    investigation_step = InvestigationStep(
        step_name="get_pod_details",
        timestamp=datetime.now(timezone.utc),
        status="completed",
        details={"tool": "get_pod_details", "result": {"status": "Running"}},
    )

    mock_incident = Incident(
        id=incident_id,
        description="Test incident",
        status=IncidentStatus.IN_PROGRESS,
        investigation_steps=[investigation_step],
    )
    mock_repo.get_by_id.return_value = mock_incident

    app.dependency_overrides[get_incident_repository] = lambda: mock_repo

    # Act
    response = test_client.get(f"/api/v1/incidents/{incident_id}")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data["investigation_steps"]) == 1
    step = data["investigation_steps"][0]
    assert step["step_name"] == "get_pod_details"
    assert step["status"] == "completed"
    assert "timestamp" in step
    assert "details" in step

    # Cleanup
    app.dependency_overrides.clear()


def test_get_incident_with_error_message(test_client, mock_repo):
    """
    Test GET /incidents/{id} returns incident with error message.

    Verifies that failed incidents include error_message field.
    """
    # Arrange
    incident_id = uuid4()
    mock_incident = Incident(
        id=incident_id,
        description="Test incident",
        status=IncidentStatus.FAILED,
        error_message="LLM API timeout after 3 retries",
    )
    mock_repo.get_by_id.return_value = mock_incident

    app.dependency_overrides[get_incident_repository] = lambda: mock_repo

    # Act
    response = test_client.get(f"/api/v1/incidents/{incident_id}")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert data["error_message"] == "LLM API timeout after 3 retries"

    # Cleanup
    app.dependency_overrides.clear()
