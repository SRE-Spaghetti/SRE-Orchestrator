from uuid import UUID
from typing import Dict, Optional
from app.models.incidents import Incident

class IncidentRepository:
    def __init__(self):
        self._incidents: Dict[UUID, Incident] = {}

    def create(self, description: str) -> Incident:
        incident = Incident(description=description)
        self._incidents[incident.id] = incident
        return incident

    def get_by_id(self, incident_id: UUID) -> Optional[Incident]:
        return self._incidents.get(incident_id)

# A single instance to act as our in-memory database
incident_repository = IncidentRepository()

def get_incident_repository() -> IncidentRepository:
    return incident_repository
