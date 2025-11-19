from fastapi import APIRouter, Depends, status, HTTPException, Request
from app.models.incidents import NewIncidentRequest, NewIncidentResponse, Incident
from app.core.incident_repository import IncidentRepository, get_incident_repository
from uuid import UUID
import logging
import os
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/incidents",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=NewIncidentResponse,
)
async def create_incident(
    fastapi_req: Request,
    request: NewIncidentRequest,
    repo: IncidentRepository = Depends(get_incident_repository),
):
    """
    Create a new incident and initiate investigation using LangGraph agent.

    The investigation runs asynchronously using MCP tools and LLM.
    Returns immediately with incident_id while investigation proceeds in background.
    """
    # Get MCP tools from app state
    mcp_tool_manager = getattr(fastapi_req.app.state, "mcp_tool_manager", None)
    if not mcp_tool_manager or not mcp_tool_manager.is_initialized():
        logger.error("MCP Tool Manager not initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MCP tools not available. Investigation cannot proceed.",
        )

    mcp_tools = await mcp_tool_manager.get_tools()

    # Get LLM configuration
    llm_config = {
        "base_url": os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        "api_key": os.getenv("LLM_API_KEY"),
        "model_name": os.getenv("LLM_MODEL_NAME", "gpt-4"),
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "2000")),
    }

    if not llm_config["api_key"]:
        logger.error("LLM_API_KEY not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM not configured. Investigation cannot proceed.",
        )

    # Create incident synchronously with pending status
    try:
        incident = repo.create_incident_sync(description=request.description)

        # Schedule background investigation as an async task
        # This runs in the event loop without blocking the thread pool
        asyncio.create_task(
            repo.investigate_incident_async(incident.id, mcp_tools, llm_config)
        )

        return NewIncidentResponse(incident_id=incident.id, status=incident.status)
    except Exception as e:
        logger.error(f"Failed to create incident: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create incident: {str(e)}",
        )


@router.get("/incidents/{incident_id}", response_model=Incident)
def get_incident(
    incident_id: UUID,
    repo: IncidentRepository = Depends(get_incident_repository),
):
    """
    Retrieve an incident by ID.

    Returns the incident with current status and investigation results.
    """
    incident = repo.get_by_id(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found"
        )
    return incident
