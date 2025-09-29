from fastapi import APIRouter, Depends, status, HTTPException
from app.models.incidents import NewIncidentRequest, NewIncidentResponse, Incident
from app.core.incident_repository import IncidentRepository, get_incident_repository
from app.services.k8s_agent_client import K8sAgentClient, get_k8s_agent_client
from app.services.llm_client import LLMClient, get_llm_client
from uuid import UUID

router = APIRouter()


@router.post(
    "/incidents",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=NewIncidentResponse,
)
def create_incident(
    request: NewIncidentRequest,
    repo: IncidentRepository = Depends(get_incident_repository),
    k8s_agent_client: K8sAgentClient = Depends(get_k8s_agent_client),
    llm_client: LLMClient = Depends(get_llm_client),
):
    incident = repo.create(
        description=request.description, k8s_agent_client=k8s_agent_client, llm_client=llm_client
    )
    return NewIncidentResponse(incident_id=incident.id)


@router.get("/incidents/{incident_id}", response_model=Incident)
def get_incident(
    incident_id: UUID,
    repo: IncidentRepository = Depends(get_incident_repository),
):
    incident = repo.get_by_id(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found"
        )
    return incident
