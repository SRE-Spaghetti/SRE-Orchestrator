from fastapi import APIRouter, Depends, status
from app.models.incidents import NewIncidentRequest, NewIncidentResponse
from app.core.incident_repository import IncidentRepository, get_incident_repository

router = APIRouter()

@router.post("/incidents", status_code=status.HTTP_202_ACCEPTED, response_model=NewIncidentResponse)
def create_incident(
    request: NewIncidentRequest,
    repo: IncidentRepository = Depends(get_incident_repository),
):
    incident = repo.create(description=request.description)
    return NewIncidentResponse(incident_id=incident.id)
