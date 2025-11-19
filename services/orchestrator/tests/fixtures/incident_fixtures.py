"""Reusable fixtures for incident-related testing."""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from typing import Dict, Any, List

from app.models.incidents import Incident, IncidentStatus, InvestigationStep


@pytest.fixture
def pending_incident() -> Incident:
    """
    Provides an incident in pending status.

    Returns:
        Incident: Incident awaiting investigation
    """
    return Incident(
        id=uuid4(),
        description="Service api-gateway is returning 503 errors",
        status=IncidentStatus.PENDING,
        created_at=datetime.now(timezone.utc),
        evidence={},
        extracted_entities={},
        investigation_steps=[],
    )


@pytest.fixture
def in_progress_incident() -> Incident:
    """
    Provides an incident in progress with some investigation steps.

    Returns:
        Incident: Incident currently being investigated
    """
    incident_id = uuid4()
    return Incident(
        id=incident_id,
        description="Database connection pool exhausted",
        status=IncidentStatus.IN_PROGRESS,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        evidence={
            "initial_symptoms": ["High connection count", "Slow query responses"]
        },
        extracted_entities={"service": "postgres-db", "component": "connection-pool"},
        investigation_steps=[
            InvestigationStep(
                step_name="get_pod_details",
                timestamp=datetime.now(timezone.utc) - timedelta(minutes=4),
                status="completed",
                details={
                    "tool": "get_pod_details",
                    "result": {"status": "Running", "restarts": 0},
                },
            ),
            InvestigationStep(
                step_name="check_database_connections",
                timestamp=datetime.now(timezone.utc) - timedelta(minutes=2),
                status="started",
                details={},
            ),
        ],
    )


@pytest.fixture
def completed_incident() -> Incident:
    """
    Provides a completed incident with full investigation results.

    Returns:
        Incident: Successfully investigated incident
    """
    return Incident(
        id=uuid4(),
        description="Redis cache unavailable",
        status=IncidentStatus.COMPLETED,
        created_at=datetime.now(timezone.utc) - timedelta(hours=1),
        completed_at=datetime.now(timezone.utc) - timedelta(minutes=30),
        evidence={
            "pod_status": "CrashLoopBackOff",
            "error_logs": ["Connection refused on port 6379"],
            "recent_changes": ["Deployment updated 2 hours ago"],
        },
        extracted_entities={
            "service": "redis-cache",
            "pod": "redis-cache-abc123",
            "namespace": "production",
        },
        suggested_root_cause="Redis configuration error after deployment update",
        confidence_score="high",
        investigation_steps=[
            InvestigationStep(
                step_name="get_pod_details",
                timestamp=datetime.now(timezone.utc) - timedelta(minutes=55),
                status="completed",
                details={
                    "tool": "get_pod_details",
                    "result": {"status": "CrashLoopBackOff", "restarts": 10},
                },
            ),
            InvestigationStep(
                step_name="get_pod_logs",
                timestamp=datetime.now(timezone.utc) - timedelta(minutes=50),
                status="completed",
                details={
                    "tool": "get_pod_logs",
                    "result": {"logs": "Error: Invalid configuration parameter"},
                },
            ),
            InvestigationStep(
                step_name="analyze_recent_changes",
                timestamp=datetime.now(timezone.utc) - timedelta(minutes=45),
                status="completed",
                details={
                    "tool": "get_deployment_history",
                    "result": {"recent_deployments": ["redis-cache updated 2h ago"]},
                },
            ),
        ],
    )


@pytest.fixture
def failed_incident() -> Incident:
    """
    Provides a failed incident where investigation encountered errors.

    Returns:
        Incident: Incident with failed investigation
    """
    return Incident(
        id=uuid4(),
        description="Unknown service degradation",
        status=IncidentStatus.FAILED,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=30),
        completed_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        evidence={"partial_data": ["Some metrics collected before failure"]},
        extracted_entities={},
        investigation_steps=[
            InvestigationStep(
                step_name="initial_analysis",
                timestamp=datetime.now(timezone.utc) - timedelta(minutes=25),
                status="completed",
                details={"tool": "get_metrics", "result": {"cpu": "80%"}},
            ),
            InvestigationStep(
                step_name="deep_analysis",
                timestamp=datetime.now(timezone.utc) - timedelta(minutes=15),
                status="failed",
                details={"error": "LLM API timeout"},
            ),
        ],
        error_message="Investigation failed: LLM API timeout after 3 retries",
    )


@pytest.fixture
def invalid_incident_data() -> List[Dict[str, Any]]:
    """
    Provides various invalid incident data for validation testing.

    Returns:
        List[Dict[str, Any]]: List of invalid incident data scenarios
    """
    return [
        # Empty description
        {"description": "", "status": "pending"},
        # Invalid status
        {"description": "Valid description", "status": "invalid_status"},
        # Missing required field
        {"status": "pending"},
        # Wrong type for status
        {"description": "Valid description", "status": 123},
        # Wrong type for evidence
        {"description": "Valid description", "evidence": "not a dict"},
        # Invalid confidence score type
        {
            "description": "Valid description",
            "confidence_score": 123,  # Should be string
        },
    ]


@pytest.fixture
def incident_with_complex_evidence() -> Incident:
    """
    Provides an incident with complex nested evidence structure.

    Returns:
        Incident: Incident with detailed evidence and entities
    """
    return Incident(
        id=uuid4(),
        description="Multi-service cascade failure",
        status=IncidentStatus.COMPLETED,
        created_at=datetime.now(timezone.utc) - timedelta(hours=2),
        completed_at=datetime.now(timezone.utc) - timedelta(hours=1),
        evidence={
            "affected_services": [
                {"name": "api-gateway", "status": "degraded", "error_rate": 0.15},
                {"name": "auth-service", "status": "down", "error_rate": 1.0},
                {"name": "user-service", "status": "degraded", "error_rate": 0.08},
            ],
            "timeline": [
                {
                    "timestamp": "2024-01-15T10:00:00Z",
                    "event": "auth-service pod crashed",
                },
                {
                    "timestamp": "2024-01-15T10:02:00Z",
                    "event": "api-gateway started returning 503",
                },
                {
                    "timestamp": "2024-01-15T10:05:00Z",
                    "event": "user-service degraded performance",
                },
            ],
            "metrics": {
                "cpu_usage": {"auth-service": 0.95, "api-gateway": 0.75},
                "memory_usage": {"auth-service": 0.98, "api-gateway": 0.65},
                "request_rate": {"api-gateway": 1500, "user-service": 800},
            },
        },
        extracted_entities={
            "primary_service": "auth-service",
            "affected_services": ["api-gateway", "user-service"],
            "root_pod": "auth-service-xyz789",
            "namespace": "production",
            "cluster": "prod-us-east-1",
        },
        suggested_root_cause="Auth service OOMKilled causing cascade failure",
        confidence_score="high",
    )


@pytest.fixture
def multiple_incidents() -> List[Incident]:
    """
    Provides a list of incidents in various states for bulk testing.

    Returns:
        List[Incident]: Multiple incidents with different statuses
    """
    return [
        Incident(
            id=uuid4(),
            description=f"Incident {i}: Test incident",
            status=status,
            created_at=datetime.now(timezone.utc) - timedelta(minutes=i * 10),
        )
        for i, status in enumerate(
            [
                IncidentStatus.PENDING,
                IncidentStatus.IN_PROGRESS,
                IncidentStatus.COMPLETED,
                IncidentStatus.FAILED,
            ]
        )
    ]
