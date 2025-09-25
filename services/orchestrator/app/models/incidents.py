from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime
from typing import Dict, Any

class NewIncidentRequest(BaseModel):
    description: str

class NewIncidentResponse(BaseModel):
    incident_id: UUID

class Incident(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    description: str
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    evidence: Dict[str, Any] = Field(default_factory=dict)
