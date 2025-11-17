"""Smoke tests to verify test infrastructure is working correctly."""

import pytest
from app.models.incidents import Incident, IncidentStatus


def test_pytest_is_working():
    """Verify pytest is configured correctly."""
    assert True


def test_fixtures_are_available(sample_incident):
    """Verify shared fixtures from conftest.py are accessible."""
    assert sample_incident is not None
    assert isinstance(sample_incident, Incident)
    assert sample_incident.status == IncidentStatus.PENDING


def test_incident_fixtures_are_available(pending_incident):
    """Verify incident fixtures are accessible."""
    assert pending_incident is not None
    assert isinstance(pending_incident, Incident)
    assert pending_incident.status == IncidentStatus.PENDING


def test_mcp_fixtures_are_available(mock_mcp_tools):
    """Verify MCP fixtures are accessible."""
    assert mock_mcp_tools is not None
    assert len(mock_mcp_tools) > 0


def test_llm_fixtures_are_available(mock_llm_config):
    """Verify LLM fixtures are accessible."""
    assert mock_llm_config is not None
    assert "base_url" in mock_llm_config
    assert "api_key" in mock_llm_config


@pytest.mark.asyncio
async def test_async_tests_work():
    """Verify async tests are configured correctly."""
    result = await async_helper()
    assert result == "async works"


async def async_helper():
    """Helper function to test async functionality."""
    return "async works"
