from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from app.models.pod_details import PodDetails
from app.services.k8s_client import get_pod_details, initialize_kubernetes_client

router = APIRouter()


@router.get("/pods/{namespace}/{name}", response_model=PodDetails)
async def read_pod(namespace: str, name: str):
    pod_details = get_pod_details(namespace, name)
    if pod_details is None:
        raise HTTPException(status_code=404, detail="Pod not found")
    return pod_details
