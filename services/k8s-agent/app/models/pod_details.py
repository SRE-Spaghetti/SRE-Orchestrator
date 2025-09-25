from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class ContainerStatus(BaseModel):
    name: str
    state: str
    ready: bool

class ResourceRequirements(BaseModel):
    cpu: Optional[str] = None
    memory: Optional[str] = None

class PodDetails(BaseModel):
    status: str
    restart_count: int
    container_statuses: List[ContainerStatus]
    resource_limits: Optional[ResourceRequirements] = None
    resource_requests: Optional[ResourceRequirements] = None
