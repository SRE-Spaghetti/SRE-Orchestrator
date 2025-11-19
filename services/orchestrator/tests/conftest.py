"""Pytest configuration and shared fixtures for orchestrator tests."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock

from app.models.incidents import (
    Incident,
    IncidentStatus,
    InvestigationStep,
    NewIncidentRequest,
)

# Import fixtures from fixture modules to make them available
pytest_plugins = [
    "tests.fixtures.incident_fixtures",
    "tests.fixtures.mcp_fixtures",
    "tests.fixtures.llm_fixtures",
]


# ============================================================================
# Core Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_incident() -> Incident:
    """
    Provides a sample incident in pending status for testing.

    Returns:
        Incident: A basic incident with minimal required fields
    """
    return Incident(
        id=uuid4(),
        description="Pod nginx-deployment-abc123 is in CrashLoopBackOff",
        status=IncidentStatus.PENDING,
        created_at=datetime.now(timezone.utc),
        evidence={},
        extracted_entities={},
        investigation_steps=[],
    )


@pytest.fixture
def sample_incident_dict() -> Dict[str, Any]:
    """
    Provides incident data as dictionary for API tests.

    Returns:
        Dict[str, Any]: Incident data suitable for JSON serialization
    """
    return {
        "description": "Pod nginx-deployment-abc123 is in CrashLoopBackOff",
    }


@pytest.fixture
def sample_new_incident_request() -> NewIncidentRequest:
    """
    Provides a sample new incident request for API testing.

    Returns:
        NewIncidentRequest: A valid incident creation request
    """
    return NewIncidentRequest(
        description="Pod nginx-deployment-abc123 is in CrashLoopBackOff"
    )


@pytest.fixture
def sample_investigation_step() -> InvestigationStep:
    """
    Provides a sample investigation step for testing.

    Returns:
        InvestigationStep: A completed investigation step with details
    """
    return InvestigationStep(
        step_name="get_pod_details",
        timestamp=datetime.now(timezone.utc),
        status="completed",
        details={
            "tool": "get_pod_details",
            "args": {"pod_name": "nginx-deployment-abc123"},
            "result": {"status": "CrashLoopBackOff", "restarts": 5},
        },
    )


@pytest.fixture
def sample_investigation_result() -> Dict[str, Any]:
    """
    Provides a mock investigation result for testing.

    Returns:
        Dict[str, Any]: Complete investigation result with all fields
    """
    return {
        "status": "completed",
        "root_cause": "Memory limit exceeded causing OOMKilled",
        "confidence": "high",
        "evidence": [
            "Pod logs show OOMKilled status",
            "Container restart count: 5",
            "Memory usage at 512Mi (limit reached)",
        ],
        "reasoning": "Analysis of pod events and logs indicates memory exhaustion",
        "tool_calls": [
            {
                "tool": "get_pod_details",
                "args": {"pod_name": "nginx-deployment-abc123"},
                "result": {"status": "CrashLoopBackOff", "restarts": 5},
            },
            {
                "tool": "get_pod_logs",
                "args": {"pod_name": "nginx-deployment-abc123"},
                "result": {"logs": "OOMKilled: process killed due to memory limit"},
            },
        ],
        "recommendations": [
            "Increase memory limit to 1Gi",
            "Add memory request to ensure QoS",
            "Monitor memory usage patterns",
        ],
    }


# ============================================================================
# LLM Configuration Fixtures
# ============================================================================


@pytest.fixture
def mock_llm_config() -> Dict[str, Any]:
    """
    Provides mock LLM configuration for testing.

    Returns:
        Dict[str, Any]: LLM configuration with all required fields
    """
    return {
        "base_url": "https://api.openai.com/v1",
        "api_key": "test-api-key-12345",
        "model_name": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 4096,
    }


@pytest.fixture
def mock_llm_response() -> Dict[str, Any]:
    """
    Provides a mock LLM response with tool calls for testing.

    Returns:
        Dict[str, Any]: LLM response structure with tool calls
    """
    return {
        "content": "I need to gather more information about the pod.",
        "tool_calls": [
            {
                "id": "call_abc123",
                "name": "get_pod_details",
                "args": {"pod_name": "nginx-deployment-abc123"},
            }
        ],
    }


@pytest.fixture
def mock_llm_final_response() -> Dict[str, Any]:
    """
    Provides a mock final LLM response without tool calls.

    Returns:
        Dict[str, Any]: Final analysis response from LLM
    """
    return {
        "content": "Root cause: Memory limit exceeded. The pod is being OOMKilled.",
        "tool_calls": [],
    }


# ============================================================================
# MCP Tool Fixtures
# ============================================================================


@pytest.fixture
def mock_mcp_tools() -> List[Mock]:
    """
    Provides mock MCP tools for testing.

    Returns:
        List[Mock]: List of mock tool objects with standard interface
    """
    tool1 = Mock()
    tool1.name = "get_pod_details"
    tool1.description = "Get detailed information about a Kubernetes pod"
    tool1.invoke = Mock(
        return_value={"status": "CrashLoopBackOff", "restarts": 5, "ready": False}
    )
    tool1.ainvoke = AsyncMock(
        return_value={"status": "CrashLoopBackOff", "restarts": 5, "ready": False}
    )

    tool2 = Mock()
    tool2.name = "get_pod_logs"
    tool2.description = "Get logs from a Kubernetes pod"
    tool2.invoke = Mock(
        return_value={"logs": "OOMKilled: process killed due to memory limit"}
    )
    tool2.ainvoke = AsyncMock(
        return_value={"logs": "OOMKilled: process killed due to memory limit"}
    )

    return [tool1, tool2]


@pytest.fixture
def mock_mcp_config() -> Dict[str, Any]:
    """
    Provides mock MCP configuration for testing.

    Returns:
        Dict[str, Any]: MCP configuration with server definitions
    """
    return {
        "mcpServers": {
            "kubernetes": {
                "command": "uvx",
                "args": ["mcp-server-kubernetes"],
                "env": {},
            }
        }
    }


# ============================================================================
# Mock Service Fixtures
# ============================================================================


@pytest.fixture
def mock_incident_repository():
    """
    Provides a mock incident repository for testing.

    Returns:
        Mock: Mock repository with standard CRUD methods
    """
    repo = Mock()
    repo.create_incident_sync = Mock()
    repo.get_by_id = Mock()
    repo.update_status = Mock()
    repo.investigate_incident_async = AsyncMock()
    return repo


@pytest.fixture
def mock_mcp_tool_manager():
    """
    Provides a mock MCP tool manager for testing.

    Returns:
        Mock: Mock tool manager with initialization and tool access
    """
    manager = Mock()
    manager.is_initialized = Mock(return_value=True)
    manager.get_tools = Mock(return_value=[])
    manager.cleanup = AsyncMock()
    return manager


@pytest.fixture
def mock_knowledge_graph_service():
    """
    Provides a mock knowledge graph service for testing.

    Returns:
        Mock: Mock service with component and dependency queries
    """
    service = Mock()
    service.get_component = Mock(return_value=None)
    service.get_dependencies = Mock(return_value=[])
    return service


# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "asyncio: mark test as async")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
