"""
Unit tests for data models.

Tests cover:
- Valid model creation with all fields
- Status enum validation
- InvestigationStep model validation
- Serialization and deserialization
- Invalid data scenarios
"""

import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4
from pydantic import ValidationError

from app.models.incidents import (
    Incident,
    IncidentStatus,
    InvestigationStep,
    NewIncidentRequest,
    NewIncidentResponse,
)


class TestIncidentStatus:
    """Tests for IncidentStatus enum"""

    def test_incident_status_values(self):
        """Test all incident status enum values are correct"""
        assert IncidentStatus.PENDING.value == "pending"
        assert IncidentStatus.IN_PROGRESS.value == "in_progress"
        assert IncidentStatus.COMPLETED.value == "completed"
        assert IncidentStatus.FAILED.value == "failed"

    def test_incident_status_from_string(self):
        """Test creating IncidentStatus from string values"""
        assert IncidentStatus("pending") == IncidentStatus.PENDING
        assert IncidentStatus("in_progress") == IncidentStatus.IN_PROGRESS
        assert IncidentStatus("completed") == IncidentStatus.COMPLETED
        assert IncidentStatus("failed") == IncidentStatus.FAILED

    def test_incident_status_invalid_value(self):
        """Test that invalid status values raise ValueError"""
        with pytest.raises(ValueError):
            IncidentStatus("invalid_status")


class TestInvestigationStep:
    """Tests for InvestigationStep model"""

    def test_investigation_step_valid_creation(self):
        """Test creating a valid investigation step with all fields"""
        step = InvestigationStep(
            step_name="analyze_logs",
            status="started",
            details={"tool": "kubectl", "action": "logs"},
        )

        assert step.step_name == "analyze_logs"
        assert step.status == "started"
        assert step.details == {"tool": "kubectl", "action": "logs"}
        assert isinstance(step.timestamp, datetime)

    def test_investigation_step_default_timestamp(self):
        """Test that timestamp is automatically set"""
        step = InvestigationStep(step_name="test_step", status="started")
        assert isinstance(step.timestamp, datetime)

    def test_investigation_step_default_details(self):
        """Test that details defaults to empty dict"""
        step = InvestigationStep(step_name="test_step", status="started")
        assert step.details == {}

    def test_investigation_step_all_status_values(self):
        """Test all valid status literal values"""
        for status in ["started", "completed", "failed"]:
            step = InvestigationStep(step_name="test", status=status)
            assert step.status == status

    def test_investigation_step_invalid_status(self):
        """Test that invalid status raises validation error"""
        with pytest.raises(ValidationError) as exc_info:
            InvestigationStep(step_name="test", status="invalid")

        errors = exc_info.value.errors()
        assert any("status" in str(error) for error in errors)

    def test_investigation_step_missing_required_fields(self):
        """Test that missing required fields raise validation error"""
        with pytest.raises(ValidationError) as exc_info:
            InvestigationStep()

        errors = exc_info.value.errors()
        assert len(errors) >= 2  # step_name and status are required


class TestIncident:
    """Tests for Incident model"""

    def test_incident_valid_creation_minimal(self):
        """Test creating incident with only required fields"""
        incident = Incident(description="Pod is crashing")

        assert incident.description == "Pod is crashing"
        assert incident.status == IncidentStatus.PENDING
        assert isinstance(incident.id, UUID)
        assert isinstance(incident.created_at, datetime)
        assert incident.completed_at is None
        assert incident.evidence == {}
        assert incident.extracted_entities == {}
        assert incident.suggested_root_cause is None
        assert incident.confidence_score is None
        assert incident.investigation_steps == []
        assert incident.error_message is None

    def test_incident_valid_creation_all_fields(self):
        """Test creating incident with all fields populated"""
        incident_id = uuid4()
        created_at = datetime.now(timezone.utc)
        completed_at = datetime.now(timezone.utc)

        investigation_step = InvestigationStep(
            step_name="analyze_logs",
            status="completed",
            details={"result": "found error"},
        )

        incident = Incident(
            id=incident_id,
            description="Pod nginx-deployment-abc123 is in CrashLoopBackOff",
            status=IncidentStatus.COMPLETED,
            created_at=created_at,
            completed_at=completed_at,
            evidence={
                "logs": ["Error: OOMKilled"],
                "events": ["Memory limit exceeded"],
            },
            extracted_entities={
                "pod_name": "nginx-deployment-abc123",
                "namespace": "default",
            },
            suggested_root_cause="Memory limit exceeded",
            confidence_score="high",
            investigation_steps=[investigation_step],
            error_message=None,
        )

        assert incident.id == incident_id
        assert (
            incident.description == "Pod nginx-deployment-abc123 is in CrashLoopBackOff"
        )
        assert incident.status == IncidentStatus.COMPLETED
        assert incident.created_at == created_at
        assert incident.completed_at == completed_at
        assert "logs" in incident.evidence
        assert incident.extracted_entities["pod_name"] == "nginx-deployment-abc123"
        assert incident.suggested_root_cause == "Memory limit exceeded"
        assert incident.confidence_score == "high"
        assert len(incident.investigation_steps) == 1
        assert incident.investigation_steps[0].step_name == "analyze_logs"

    def test_incident_default_values(self):
        """Test that default values are set correctly"""
        incident = Incident(description="Test incident")

        assert isinstance(incident.id, UUID)
        assert incident.status == IncidentStatus.PENDING
        assert isinstance(incident.created_at, datetime)
        assert incident.evidence == {}
        assert incident.extracted_entities == {}
        assert incident.investigation_steps == []

    def test_incident_status_enum_validation(self):
        """Test that status field accepts valid IncidentStatus enum values"""
        for status in IncidentStatus:
            incident = Incident(description="Test", status=status)
            assert incident.status == status

    def test_incident_empty_description_allowed(self):
        """Test that empty description is allowed by the model"""
        # Note: The model doesn't enforce non-empty strings
        incident = Incident(description="")
        assert incident.description == ""

    def test_incident_missing_description_fails(self):
        """Test that missing description raises validation error"""
        with pytest.raises(ValidationError) as exc_info:
            Incident()

        errors = exc_info.value.errors()
        assert any("description" in str(error) for error in errors)

    def test_incident_invalid_status_type(self):
        """Test that invalid status type raises validation error"""
        with pytest.raises(ValidationError):
            Incident(description="Test", status="invalid_status")

    def test_incident_invalid_id_type(self):
        """Test that invalid UUID type raises validation error"""
        with pytest.raises(ValidationError):
            Incident(description="Test", id="not-a-uuid")

    def test_incident_invalid_created_at_type(self):
        """Test that invalid datetime type raises validation error"""
        with pytest.raises(ValidationError):
            Incident(description="Test", created_at="not-a-datetime")

    def test_incident_invalid_evidence_type(self):
        """Test that invalid evidence type raises validation error"""
        with pytest.raises(ValidationError):
            Incident(description="Test", evidence="not-a-dict")

    def test_incident_invalid_investigation_steps_type(self):
        """Test that invalid investigation_steps type raises validation error"""
        with pytest.raises(ValidationError):
            Incident(description="Test", investigation_steps="not-a-list")

    def test_incident_serialization_to_dict(self):
        """Test incident serialization to dictionary"""
        incident = Incident(
            description="Test incident",
            status=IncidentStatus.IN_PROGRESS,
            evidence={"key": "value"},
        )

        incident_dict = incident.model_dump()

        assert isinstance(incident_dict, dict)
        assert incident_dict["description"] == "Test incident"
        assert incident_dict["status"] == "in_progress"
        assert incident_dict["evidence"] == {"key": "value"}
        assert "id" in incident_dict
        assert "created_at" in incident_dict

    def test_incident_serialization_to_json(self):
        """Test incident serialization to JSON string"""
        incident = Incident(description="Test incident", status=IncidentStatus.PENDING)

        json_str = incident.model_dump_json()

        assert isinstance(json_str, str)
        assert "Test incident" in json_str
        assert "pending" in json_str

    def test_incident_deserialization_from_dict(self):
        """Test incident deserialization from dictionary"""
        incident_id = uuid4()
        incident_dict = {
            "id": str(incident_id),
            "description": "Test incident",
            "status": "completed",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
            "evidence": {"result": "success"},
            "extracted_entities": {},
            "suggested_root_cause": "Network timeout",
            "confidence_score": "medium",
            "investigation_steps": [],
            "error_message": None,
        }

        incident = Incident(**incident_dict)

        assert incident.description == "Test incident"
        assert incident.status == IncidentStatus.COMPLETED
        assert incident.evidence == {"result": "success"}
        assert incident.suggested_root_cause == "Network timeout"

    def test_incident_with_nested_investigation_steps(self):
        """Test incident with nested InvestigationStep objects"""
        steps = [
            InvestigationStep(step_name="step1", status="completed", details={"a": 1}),
            InvestigationStep(step_name="step2", status="started", details={"b": 2}),
        ]

        incident = Incident(description="Test", investigation_steps=steps)

        assert len(incident.investigation_steps) == 2
        assert incident.investigation_steps[0].step_name == "step1"
        assert incident.investigation_steps[1].step_name == "step2"

    def test_incident_serialization_with_investigation_steps(self):
        """Test serialization of incident with investigation steps"""
        step = InvestigationStep(
            step_name="analyze", status="completed", details={"tool": "kubectl"}
        )

        incident = Incident(description="Test", investigation_steps=[step])

        incident_dict = incident.model_dump()

        assert len(incident_dict["investigation_steps"]) == 1
        assert incident_dict["investigation_steps"][0]["step_name"] == "analyze"
        assert incident_dict["investigation_steps"][0]["status"] == "completed"


class TestNewIncidentRequest:
    """Tests for NewIncidentRequest model"""

    def test_new_incident_request_valid(self):
        """Test creating valid NewIncidentRequest"""
        request = NewIncidentRequest(description="Pod is crashing")
        assert request.description == "Pod is crashing"

    def test_new_incident_request_empty_description_allowed(self):
        """Test that empty description is allowed by the model"""
        # Note: The model doesn't enforce non-empty strings
        request = NewIncidentRequest(description="")
        assert request.description == ""

    def test_new_incident_request_missing_description_fails(self):
        """Test that missing description raises validation error"""
        with pytest.raises(ValidationError):
            NewIncidentRequest()


class TestNewIncidentResponse:
    """Tests for NewIncidentResponse model"""

    def test_new_incident_response_valid(self):
        """Test creating valid NewIncidentResponse"""
        incident_id = uuid4()
        response = NewIncidentResponse(incident_id=incident_id, status="pending")

        assert response.incident_id == incident_id
        assert response.status == "pending"

    def test_new_incident_response_invalid_uuid(self):
        """Test that invalid UUID raises validation error"""
        with pytest.raises(ValidationError):
            NewIncidentResponse(incident_id="not-a-uuid", status="pending")

    def test_new_incident_response_missing_fields(self):
        """Test that missing required fields raise validation error"""
        with pytest.raises(ValidationError):
            NewIncidentResponse()
