import httpx
import os
from typing import Optional

from app.models.pod_details import PodDetails


class K8sAgentClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.Client()

    def get_pod_details(self, namespace: str, name: str) -> Optional[PodDetails]:
        url = f"{self.base_url}/api/v1/pods/{namespace}/{name}"
        try:
            response = self.client.get(url)
            response.raise_for_status()
            return PodDetails(**response.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except httpx.RequestError:
            raise

    def get_pod_logs(
        self,
        namespace: str,
        name: str,
        container: Optional[str] = None,
        tail: int = 100,
    ) -> Optional[str]:
        url = f"{self.base_url}/api/v1/pods/{namespace}/{name}/logs"
        params = {}
        if container:
            params["container"] = container
        if tail:
            params["tail"] = tail

        try:
            response = self.client.get(url, params=params)
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except httpx.RequestError:
            raise


k8s_agent_client_instance: Optional[K8sAgentClient] = None


def get_k8s_agent_client() -> K8sAgentClient:
    global k8s_agent_client_instance
    if k8s_agent_client_instance is None:
        k8s_agent_base_url = os.getenv(
            "K8S_AGENT_BASE_URL", "http://localhost:8001"
        )  # Default for local testing
        k8s_agent_client_instance = K8sAgentClient(k8s_agent_base_url)
    return k8s_agent_client_instance
