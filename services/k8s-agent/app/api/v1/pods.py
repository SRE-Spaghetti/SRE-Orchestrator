from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from typing import Optional

from app.models.pod_details import PodDetails
from app.services.k8s_client import get_pod_details, get_pod_logs

router = APIRouter()


@router.get("/pods/{namespace}/{name}", response_model=PodDetails)
async def read_pod(namespace: str, name: str):
    pod_details = get_pod_details(namespace, name)
    if pod_details is None:
        raise HTTPException(status_code=404, detail="Pod not found")
    return pod_details

@router.get("/pods/{namespace}/{name}/logs", response_class=PlainTextResponse)
async def read_pod_logs(
    namespace: str,
    name: str,
    container: Optional[str] = None,
    tail: int = 100
):
    logs = get_pod_logs(namespace, name, container, tail)
    if logs is None:
        raise HTTPException(status_code=404, detail="Pod logs not found or pod/container does not exist")
    return logs
