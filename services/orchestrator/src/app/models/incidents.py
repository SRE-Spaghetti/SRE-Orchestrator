from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime
from typing import Dict, Any, List, Literal
from enum import Enum


class IncidentStatus(str, Enum):
    """Enumeration of possible incident investigation statuses"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class NewIncidentRequest(BaseModel):
    description: str


class NewIncidentResponse(BaseModel):
    incident_id: UUID
    status: str


class InvestigationStep(BaseModel):
    """Track each step in the investigation workflow"""
    step_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: Literal["started", "completed", "failed"]
    details: Dict[str, Any] = Field(default_factory=dict)


class Incident(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    description: str
    status: IncidentStatus = IncidentStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    evidence: Dict[str, Any] = Field(default_factory=dict)
    extracted_entities: Dict[str, Any] = Field(default_factory=dict)
    suggested_root_cause: str | None = None
    confidence_score: str | None = None
    investigation_steps: List[InvestigationStep] = Field(default_factory=list)
    error_message: str | None = None
