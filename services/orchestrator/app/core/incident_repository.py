from uuid import UUID
from typing import Dict, Optional
from app.models.incidents import Incident
from app.models.pod_details import PodDetails
from app.services.k8s_agent_client import K8sAgentClient
import re


class IncidentRepository:
    def __init__(self):
        self._incidents: Dict[UUID, Incident] = {}

    def create(self, description: str, k8s_agent_client: K8sAgentClient) -> Incident:
        incident = Incident(description=description)

        # Placeholder Logic: Extract pod name and namespace from description
        pod_name_match = re.search(r"pod:(\S+)", description)
        namespace_match = re.search(r"namespace:(\S+)", description)

        pod_name = pod_name_match.group(1) if pod_name_match else None
        namespace = (
            namespace_match.group(1) if namespace_match else "default"
        )  # Default to 'default' namespace

        if pod_name:
            pod_details: Optional[PodDetails] = k8s_agent_client.get_pod_details(
                namespace, pod_name
            )
            if pod_details:
                incident.evidence["pod_details"] = pod_details.model_dump()

            pod_logs: Optional[str] = k8s_agent_client.get_pod_logs(namespace, pod_name)
            if pod_logs:
                incident.evidence["pod_logs"] = pod_logs

        self._incidents[incident.id] = incident
        return incident

    def get_by_id(self, incident_id: UUID) -> Optional[Incident]:
        return self._incidents.get(incident_id)


# A single instance to act as our in-memory database
incident_repository = IncidentRepository()


def get_incident_repository() -> IncidentRepository:
    return incident_repository
