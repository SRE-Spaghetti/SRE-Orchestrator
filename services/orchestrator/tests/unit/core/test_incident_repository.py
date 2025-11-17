"""Unit tests for IncidentRepository CRUD operations."""

import pytest
from datetime import datetime
from uuid import uuid4

from app.core.incident_repository import IncidentRepository
from app.models.incidents import IncidentStatus


class TestIncidentRepositoryCRUD:
    """Test CRUD operations in IncidentRepository."""

    def test_create_incident_sync_creates_pending_incident(self):
        """Test that create_incident_sync creates an incident with pending status."""
        # Arrange
        repo = IncidentRepository()
        description = "Pod nginx-deployment-abc123 is in CrashLoopBackOff"

        # Act
        incident = repo.create_incident_sync(description)

        # Assert
        assert incident is not None
        assert incident.id is not None
        assert incident.description == description
        assert incident.status == IncidentStatus.PENDING
        assert incident.created_at is not None
        assert isinstance(incident.created_at, datetime)
        assert incident.completed_at is None
        assert incident.evidence == {}
        assert incident.extracted_entities == {}

    def test_create_incident_sync_adds_initial_investigation_step(self):
        """Test that create_incident_sync adds an initial investigation step."""
        # Arrange
        repo = IncidentRepository()
        description = "Service api-gateway is returning 503 errors"

        # Act
        incident = repo.create_incident_sync(description)

        # Assert
        assert len(incident.investigation_steps) == 1
        step = incident.investigation_steps[0]
        assert step.step_name == "incident_created"
        assert step.status == "completed"
        assert step.details == {"description": description}

    def test_create_incident_sync_stores_incident_in_repository(self):
        """Test that create_incident_sync stores the incident for later retrieval."""
        # Arrange
        repo = IncidentRepository()
        description = "Database connection pool exhausted"

        # Act
        incident = repo.create_incident_sync(description)

        # Assert
        retrieved = repo.get_by_id(incident.id)
        assert retrieved is not None
        assert retrieved.id == incident.id
        assert retrieved.description == description

    def test_get_by_id_returns_correct_incident(self):
        """Test that get_by_id returns the correct incident."""
        # Arrange
        repo = IncidentRepository()
        repo.create_incident_sync("Incident 1")
        incident2 = repo.create_incident_sync("Incident 2")
        repo.create_incident_sync("Incident 3")

        # Act
        retrieved = repo.get_by_id(incident2.id)

        # Assert
        assert retrieved is not None
        assert retrieved.id == incident2.id
        assert retrieved.description == "Incident 2"

    def test_get_by_id_returns_none_for_nonexistent_id(self):
        """Test that get_by_id returns None for non-existent incident IDs."""
        # Arrange
        repo = IncidentRepository()
        repo.create_incident_sync("Existing incident")
        nonexistent_id = uuid4()

        # Act
        result = repo.get_by_id(nonexistent_id)

        # Assert
        assert result is None

    def test_update_status_changes_incident_status(self):
        """Test that update_status correctly changes incident status."""
        # Arrange
        repo = IncidentRepository()
        incident = repo.create_incident_sync("Test incident")
        assert incident.status == IncidentStatus.PENDING

        # Act
        repo.update_status(incident.id, IncidentStatus.IN_PROGRESS)

        # Assert
        updated = repo.get_by_id(incident.id)
        assert updated.status == IncidentStatus.IN_PROGRESS

    def test_update_status_accepts_string_status(self):
        """Test that update_status accepts status as string and converts to enum."""
        # Arrange
        repo = IncidentRepository()
        incident = repo.create_incident_sync("Test incident")

        # Act
        repo.update_status(incident.id, "in_progress")

        # Assert
        updated = repo.get_by_id(incident.id)
        assert updated.status == IncidentStatus.IN_PROGRESS

    def test_update_status_sets_completed_at_for_completed_status(self):
        """Test that update_status sets completed_at when status is completed."""
        # Arrange
        repo = IncidentRepository()
        incident = repo.create_incident_sync("Test incident")
        assert incident.completed_at is None

        # Act
        repo.update_status(incident.id, IncidentStatus.COMPLETED)

        # Assert
        updated = repo.get_by_id(incident.id)
        assert updated.status == IncidentStatus.COMPLETED
        assert updated.completed_at is not None
        assert isinstance(updated.completed_at, datetime)

    def test_update_status_sets_error_message_for_failed_status(self):
        """Test that update_status sets error_message when status is failed with error details."""
        # Arrange
        repo = IncidentRepository()
        incident = repo.create_incident_sync("Test incident")
        error_details = {"error": "LLM API timeout"}

        # Act
        repo.update_status(incident.id, IncidentStatus.FAILED, details=error_details)

        # Assert
        updated = repo.get_by_id(incident.id)
        assert updated.status == IncidentStatus.FAILED
        assert updated.error_message == "LLM API timeout"
        assert updated.completed_at is not None

    def test_status_transition_pending_to_in_progress(self):
        """Test status transition from pending to in_progress."""
        # Arrange
        repo = IncidentRepository()
        incident = repo.create_incident_sync("Test incident")

        # Act
        repo.update_status(incident.id, IncidentStatus.IN_PROGRESS)

        # Assert
        updated = repo.get_by_id(incident.id)
        assert updated.status == IncidentStatus.IN_PROGRESS

    def test_status_transition_in_progress_to_completed(self):
        """Test status transition from in_progress to completed."""
        # Arrange
        repo = IncidentRepository()
        incident = repo.create_incident_sync("Test incident")
        repo.update_status(incident.id, IncidentStatus.IN_PROGRESS)

        # Act
        repo.update_status(incident.id, IncidentStatus.COMPLETED)

        # Assert
        updated = repo.get_by_id(incident.id)
        assert updated.status == IncidentStatus.COMPLETED
        assert updated.completed_at is not None

    def test_status_transition_in_progress_to_failed(self):
        """Test status transition from in_progress to failed."""
        # Arrange
        repo = IncidentRepository()
        incident = repo.create_incident_sync("Test incident")
        repo.update_status(incident.id, IncidentStatus.IN_PROGRESS)

        # Act
        repo.update_status(
            incident.id,
            IncidentStatus.FAILED,
            details={"error": "Investigation failed"},
        )

        # Assert
        updated = repo.get_by_id(incident.id)
        assert updated.status == IncidentStatus.FAILED
        assert updated.error_message == "Investigation failed"
        assert updated.completed_at is not None

    def test_status_transition_pending_to_completed(self):
        """Test direct status transition from pending to completed."""
        # Arrange
        repo = IncidentRepository()
        incident = repo.create_incident_sync("Test incident")

        # Act
        repo.update_status(incident.id, IncidentStatus.COMPLETED)

        # Assert
        updated = repo.get_by_id(incident.id)
        assert updated.status == IncidentStatus.COMPLETED
        assert updated.completed_at is not None

    def test_status_transition_pending_to_failed(self):
        """Test direct status transition from pending to failed."""
        # Arrange
        repo = IncidentRepository()
        incident = repo.create_incident_sync("Test incident")

        # Act
        repo.update_status(
            incident.id, IncidentStatus.FAILED, details={"error": "Setup failed"}
        )

        # Assert
        updated = repo.get_by_id(incident.id)
        assert updated.status == IncidentStatus.FAILED
        assert updated.error_message == "Setup failed"


class TestIncidentRepositoryInvestigationWorkflow:
    """Test investigation workflow in IncidentRepository with mocked dependencies."""

    @pytest.mark.asyncio
    async def test_investigate_incident_async_successful_investigation(
        self, mock_mcp_tools, mock_llm_config, sample_investigation_result, mocker
    ):
        """Test investigate_incident_async with successful investigation."""
        # Arrange
        repo = IncidentRepository()
        incident = repo.create_incident_sync("Pod nginx-deployment-abc123 is crashing")

        # Mock the create_investigation_agent function
        mock_agent = mocker.AsyncMock()
        mocker.patch(
            "app.core.incident_repository.create_investigation_agent",
            return_value=mock_agent,
        )

        # Mock the investigate_incident function to return successful result
        mocker.patch(
            "app.core.incident_repository.investigate_incident",
            return_value=sample_investigation_result,
        )

        # Act
        await repo.investigate_incident_async(
            incident.id, mock_mcp_tools, mock_llm_config
        )

        # Assert
        updated = repo.get_by_id(incident.id)
        assert updated.status == IncidentStatus.COMPLETED
        assert updated.suggested_root_cause == sample_investigation_result["root_cause"]
        assert updated.confidence_score == sample_investigation_result["confidence"]
        assert updated.completed_at is not None
        assert "tool_calls" in updated.evidence
        assert "reasoning" in updated.evidence
        assert len(updated.investigation_steps) > 1

    @pytest.mark.asyncio
    async def test_investigate_incident_async_stores_tool_calls(
        self, mock_mcp_tools, mock_llm_config, sample_investigation_result, mocker
    ):
        """Test that investigate_incident_async stores tool calls in evidence."""
        # Arrange
        repo = IncidentRepository()
        incident = repo.create_incident_sync("Database connection issues")

        mock_agent = mocker.AsyncMock()
        mocker.patch(
            "app.core.incident_repository.create_investigation_agent",
            return_value=mock_agent,
        )
        mocker.patch(
            "app.core.incident_repository.investigate_incident",
            return_value=sample_investigation_result,
        )

        # Act
        await repo.investigate_incident_async(
            incident.id, mock_mcp_tools, mock_llm_config
        )

        # Assert
        updated = repo.get_by_id(incident.id)
        assert "tool_calls" in updated.evidence
        assert len(updated.evidence["tool_calls"]) == len(
            sample_investigation_result["tool_calls"]
        )
        assert (
            updated.evidence["tool_calls"] == sample_investigation_result["tool_calls"]
        )

    @pytest.mark.asyncio
    async def test_investigate_incident_async_stores_recommendations(
        self, mock_mcp_tools, mock_llm_config, sample_investigation_result, mocker
    ):
        """Test that investigate_incident_async stores recommendations in evidence."""
        # Arrange
        repo = IncidentRepository()
        incident = repo.create_incident_sync("Service degradation")

        mock_agent = mocker.AsyncMock()
        mocker.patch(
            "app.core.incident_repository.create_investigation_agent",
            return_value=mock_agent,
        )
        mocker.patch(
            "app.core.incident_repository.investigate_incident",
            return_value=sample_investigation_result,
        )

        # Act
        await repo.investigate_incident_async(
            incident.id, mock_mcp_tools, mock_llm_config
        )

        # Assert
        updated = repo.get_by_id(incident.id)
        assert "recommendations" in updated.evidence
        assert (
            updated.evidence["recommendations"]
            == sample_investigation_result["recommendations"]
        )

    @pytest.mark.asyncio
    async def test_investigate_incident_async_with_llm_failure(
        self, mock_mcp_tools, mock_llm_config, mocker
    ):
        """Test investigate_incident_async handles LLM failures gracefully."""
        # Arrange
        repo = IncidentRepository()
        incident = repo.create_incident_sync("Test incident")

        # Mock create_investigation_agent to raise an exception
        mocker.patch(
            "app.core.incident_repository.create_investigation_agent",
            side_effect=Exception("LLM API timeout"),
        )

        # Act
        await repo.investigate_incident_async(
            incident.id, mock_mcp_tools, mock_llm_config
        )

        # Assert
        updated = repo.get_by_id(incident.id)
        assert updated.status == IncidentStatus.FAILED
        assert updated.error_message == "LLM API timeout"
        assert updated.completed_at is not None
        # Check that a failed investigation step was added
        failed_steps = [
            step for step in updated.investigation_steps if step.status == "failed"
        ]
        assert len(failed_steps) > 0
        assert "error" in failed_steps[-1].details

    @pytest.mark.asyncio
    async def test_investigate_incident_async_with_investigation_failure(
        self, mock_mcp_tools, mock_llm_config, mocker
    ):
        """Test investigate_incident_async handles investigation failures."""
        # Arrange
        repo = IncidentRepository()
        incident = repo.create_incident_sync("Test incident")

        mock_agent = mocker.AsyncMock()
        mocker.patch(
            "app.core.incident_repository.create_investigation_agent",
            return_value=mock_agent,
        )

        # Mock investigate_incident to return failed result
        failed_result = {
            "status": "failed",
            "error": "Tool execution failed",
            "root_cause": None,
            "confidence": None,
            "tool_calls": [],
            "evidence": [],
            "reasoning": None,
        }
        mocker.patch(
            "app.core.incident_repository.investigate_incident",
            return_value=failed_result,
        )

        # Act
        await repo.investigate_incident_async(
            incident.id, mock_mcp_tools, mock_llm_config
        )

        # Assert
        updated = repo.get_by_id(incident.id)
        assert updated.status == IncidentStatus.FAILED
        assert updated.error_message == "Tool execution failed"
        assert updated.completed_at is not None

    @pytest.mark.asyncio
    async def test_investigate_incident_async_preserves_partial_results_on_failure(
        self, mock_mcp_tools, mock_llm_config, mocker
    ):
        """Test that partial investigation results are preserved on failure."""
        # Arrange
        repo = IncidentRepository()
        incident = repo.create_incident_sync("Test incident")

        mock_agent = mocker.AsyncMock()
        mocker.patch(
            "app.core.incident_repository.create_investigation_agent",
            return_value=mock_agent,
        )

        # Mock investigate_incident to return failed result with partial data
        partial_result = {
            "status": "failed",
            "error": "Investigation timeout",
            "root_cause": "Partial analysis: Memory issue",
            "confidence": "low",
            "tool_calls": [
                {
                    "tool": "get_pod_details",
                    "args": {"pod_name": "test-pod"},
                    "result": {"status": "CrashLoopBackOff"},
                }
            ],
            "evidence": ["Pod is in CrashLoopBackOff state"],
            "reasoning": "Started analysis but timed out",
        }
        mocker.patch(
            "app.core.incident_repository.investigate_incident",
            return_value=partial_result,
        )

        # Act
        await repo.investigate_incident_async(
            incident.id, mock_mcp_tools, mock_llm_config
        )

        # Assert
        updated = repo.get_by_id(incident.id)
        assert updated.status == IncidentStatus.FAILED
        assert updated.error_message == "Investigation timeout"
        # Verify partial results are preserved
        assert updated.suggested_root_cause == "Partial analysis: Memory issue"
        assert updated.confidence_score == "low"
        assert "tool_calls" in updated.evidence
        assert len(updated.evidence["tool_calls"]) == 1
        assert "collected_evidence" in updated.evidence
        assert len(updated.evidence["collected_evidence"]) == 1

    @pytest.mark.asyncio
    async def test_investigate_incident_async_with_tool_execution_failure(
        self, mock_mcp_tools, mock_llm_config, mocker
    ):
        """Test investigate_incident_async handles tool execution failures."""
        # Arrange
        repo = IncidentRepository()
        incident = repo.create_incident_sync("Test incident")

        mock_agent = mocker.AsyncMock()
        mocker.patch(
            "app.core.incident_repository.create_investigation_agent",
            return_value=mock_agent,
        )

        # Mock investigate_incident to raise exception during execution
        mocker.patch(
            "app.core.incident_repository.investigate_incident",
            side_effect=Exception("Tool execution failed: Connection refused"),
        )

        # Act
        await repo.investigate_incident_async(
            incident.id, mock_mcp_tools, mock_llm_config
        )

        # Assert
        updated = repo.get_by_id(incident.id)
        assert updated.status == IncidentStatus.FAILED
        assert "Tool execution failed" in updated.error_message
        assert updated.completed_at is not None

    @pytest.mark.asyncio
    async def test_investigate_incident_async_updates_status_to_in_progress(
        self, mock_mcp_tools, mock_llm_config, sample_investigation_result, mocker
    ):
        """Test that investigate_incident_async updates status to in_progress during investigation."""
        # Arrange
        repo = IncidentRepository()
        incident = repo.create_incident_sync("Test incident")

        mock_agent = mocker.AsyncMock()
        mocker.patch(
            "app.core.incident_repository.create_investigation_agent",
            return_value=mock_agent,
        )

        # Track status changes
        status_changes = []

        async def mock_investigate(*args, **kwargs):
            # Capture status at this point
            current = repo.get_by_id(incident.id)
            status_changes.append(current.status)
            return sample_investigation_result

        mocker.patch(
            "app.core.incident_repository.investigate_incident",
            side_effect=mock_investigate,
        )

        # Act
        await repo.investigate_incident_async(
            incident.id, mock_mcp_tools, mock_llm_config
        )

        # Assert
        # Status should have been IN_PROGRESS during investigation
        assert IncidentStatus.IN_PROGRESS in status_changes

    @pytest.mark.asyncio
    async def test_investigate_incident_async_adds_investigation_steps(
        self, mock_mcp_tools, mock_llm_config, sample_investigation_result, mocker
    ):
        """Test that investigate_incident_async adds investigation steps."""
        # Arrange
        repo = IncidentRepository()
        incident = repo.create_incident_sync("Test incident")
        initial_step_count = len(incident.investigation_steps)

        mock_agent = mocker.AsyncMock()
        mocker.patch(
            "app.core.incident_repository.create_investigation_agent",
            return_value=mock_agent,
        )
        mocker.patch(
            "app.core.incident_repository.investigate_incident",
            return_value=sample_investigation_result,
        )

        # Act
        await repo.investigate_incident_async(
            incident.id, mock_mcp_tools, mock_llm_config
        )

        # Assert
        updated = repo.get_by_id(incident.id)
        assert len(updated.investigation_steps) > initial_step_count
        # Check for specific steps
        step_names = [step.step_name for step in updated.investigation_steps]
        assert "investigation_started" in step_names
        assert "agent_created" in step_names
        assert "investigation_completed" in step_names

    @pytest.mark.asyncio
    async def test_investigate_incident_async_with_nonexistent_incident(
        self, mock_mcp_tools, mock_llm_config, mocker
    ):
        """Test investigate_incident_async handles non-existent incident gracefully."""
        # Arrange
        repo = IncidentRepository()
        nonexistent_id = uuid4()

        # Act
        await repo.investigate_incident_async(
            nonexistent_id, mock_mcp_tools, mock_llm_config
        )

        # Assert - should not raise exception, just log error
        # Verify incident still doesn't exist
        result = repo.get_by_id(nonexistent_id)
        assert result is None
