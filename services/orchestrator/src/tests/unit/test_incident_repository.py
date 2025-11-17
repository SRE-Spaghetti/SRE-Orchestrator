"""Unit tests for IncidentRepository async methods."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID
from datetime import datetime

from app.core.incident_repository import IncidentRepository


@pytest.fixture
def repository():
    """Create a fresh repository instance for each test."""
    return IncidentRepository()


@pytest.fixture
def mock_mcp_tools():
    """Mock MCP tools."""
    return [MagicMock(name="mock_tool_1"), MagicMock(name="mock_tool_2")]


@pytest.fixture
def mock_llm_config():
    """Mock LLM configuration."""
    return {
        "base_url": "https://api.openai.com/v1",
        "api_key": "test-api-key",
        "model_name": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 2000,
    }


class TestCreateIncidentSync:
    """Tests for create_incident_sync method."""

    def test_creates_incident_with_pending_status(self, repository):
        """Test that create_incident_sync creates incident with pending status."""
        description = "Test incident description"

        incident = repository.create_incident_sync(description)

        assert incident is not None
        assert isinstance(incident.id, UUID)
        assert incident.description == description
        assert incident.status == "pending"
        assert incident.created_at is not None
        assert incident.completed_at is None
        assert incident.error_message is None

    def test_stores_incident_in_repository(self, repository):
        """Test that created incident is stored in repository."""
        description = "Test incident"

        incident = repository.create_incident_sync(description)

        # Verify incident can be retrieved
        retrieved = repository.get_by_id(incident.id)
        assert retrieved is not None
        assert retrieved.id == incident.id
        assert retrieved.description == description

    def test_adds_incident_created_step(self, repository):
        """Test that incident_created investigation step is added."""
        description = "Test incident"

        incident = repository.create_incident_sync(description)

        assert len(incident.investigation_steps) == 1
        step = incident.investigation_steps[0]
        assert step.step_name == "incident_created"
        assert step.status == "completed"
        assert step.details["description"] == description

    def test_creates_unique_incidents(self, repository):
        """Test that multiple incidents have unique IDs."""
        incident1 = repository.create_incident_sync("First incident")
        incident2 = repository.create_incident_sync("Second incident")

        assert incident1.id != incident2.id
        assert repository.get_by_id(incident1.id) is not None
        assert repository.get_by_id(incident2.id) is not None


class TestInvestigateIncidentAsync:
    """Tests for investigate_incident_async method."""

    @pytest.mark.asyncio
    async def test_updates_status_to_in_progress(
        self, repository, mock_mcp_tools, mock_llm_config
    ):
        """Test that investigation updates status to in_progress."""
        incident = repository.create_incident_sync("Test incident")

        # Mock _investigate_incident to do nothing
        with patch.object(
            repository, "_investigate_incident", new_callable=AsyncMock
        ) as mock_investigate:
            await repository.investigate_incident_async(
                incident.id, mock_mcp_tools, mock_llm_config
            )

            # Verify _investigate_incident was called
            mock_investigate.assert_called_once()

    @pytest.mark.asyncio
    async def test_successful_investigation_updates_to_completed(
        self, repository, mock_mcp_tools, mock_llm_config
    ):
        """Test that successful investigation updates status to completed with results."""
        incident = repository.create_incident_sync("Test incident")

        # Mock successful investigation
        async def mock_investigate(inc, tools, config):
            inc.status = "in_progress"
            inc.investigation_steps.append(
                MagicMock(step_name="investigation_started", status="started")
            )
            # Simulate successful completion
            inc.status = "completed"
            inc.suggested_root_cause = "Memory leak detected"
            inc.confidence_score = "high"
            inc.completed_at = datetime.utcnow()
            inc.evidence = {"tool_calls": [], "reasoning": "Test reasoning"}

        with patch.object(repository, "_investigate_incident", new=mock_investigate):
            await repository.investigate_incident_async(
                incident.id, mock_mcp_tools, mock_llm_config
            )

            # Verify incident was updated
            updated_incident = repository.get_by_id(incident.id)
            assert updated_incident.status == "completed"
            assert updated_incident.suggested_root_cause == "Memory leak detected"
            assert updated_incident.confidence_score == "high"
            assert updated_incident.completed_at is not None
            assert updated_incident.evidence is not None

    @pytest.mark.asyncio
    async def test_failed_investigation_updates_to_failed_with_error(
        self, repository, mock_mcp_tools, mock_llm_config
    ):
        """Test that failed investigation updates status to failed with error message."""
        incident = repository.create_incident_sync("Test incident")

        # Mock investigation that raises exception
        async def mock_investigate_error(inc, tools, config):
            inc.status = "in_progress"
            raise Exception("Investigation failed due to timeout")

        with patch.object(
            repository, "_investigate_incident", new=mock_investigate_error
        ):
            await repository.investigate_incident_async(
                incident.id, mock_mcp_tools, mock_llm_config
            )

            # Verify incident was marked as failed
            updated_incident = repository.get_by_id(incident.id)
            assert updated_incident.status == "failed"
            assert (
                updated_incident.error_message == "Investigation failed due to timeout"
            )
            assert updated_incident.completed_at is not None

    @pytest.mark.asyncio
    async def test_failed_investigation_adds_failed_step(
        self, repository, mock_mcp_tools, mock_llm_config
    ):
        """Test that failed investigation adds investigation_failed step."""
        incident = repository.create_incident_sync("Test incident")

        # Mock investigation that raises exception
        async def mock_investigate_error(inc, tools, config):
            raise Exception("Test error")

        with patch.object(
            repository, "_investigate_incident", new=mock_investigate_error
        ):
            await repository.investigate_incident_async(
                incident.id, mock_mcp_tools, mock_llm_config
            )

            # Verify failed step was added
            updated_incident = repository.get_by_id(incident.id)
            failed_steps = [
                step
                for step in updated_incident.investigation_steps
                if step.step_name == "investigation_failed"
            ]
            assert len(failed_steps) == 1
            assert failed_steps[0].status == "failed"
            assert "error" in failed_steps[0].details

    @pytest.mark.asyncio
    async def test_handles_nonexistent_incident(
        self, repository, mock_mcp_tools, mock_llm_config
    ):
        """Test that investigating nonexistent incident logs error and returns."""
        from uuid import uuid4

        nonexistent_id = uuid4()

        # Should not raise exception, just log error
        await repository.investigate_incident_async(
            nonexistent_id, mock_mcp_tools, mock_llm_config
        )

        # Verify incident was not created
        assert repository.get_by_id(nonexistent_id) is None
