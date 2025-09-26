from kubernetes import config, client
import logging
from typing import Optional

from app.models.pod_details import PodDetails, ContainerStatus, ResourceRequirements

logger = logging.getLogger(__name__)

core_v1_api: Optional[client.CoreV1Api] = None

def initialize_kubernetes_client():
    global core_v1_api
    try:
        config.load_incluster_config()
        core_v1_api = client.CoreV1Api()
        logger.info("Kubernetes client initialized successfully.")
        # Verify connection by listing pods in the current namespace
        namespace = open("/var/run/secrets/kubernetes.io/serviceaccount/namespace").read()
        pods = core_v1_api.list_namespaced_pod(namespace=namespace)
        logger.info(f"Successfully listed {len(pods.items)} pods in namespace {namespace}.")
        return core_v1_api
    except config.ConfigException:
        logger.error("Could not load in-cluster Kubernetes config. Are we running in a cluster?")
        return None
    except client.ApiException as e:
        logger.error(f"Kubernetes API error during initialization: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during Kubernetes client initialization: {e}")
        return None

def get_pod_details(namespace: str, name: str) -> Optional[PodDetails]:
    if core_v1_api is None:
        logger.error("Kubernetes client not initialized.")
        return None

    try:
        pod = core_v1_api.read_namespaced_pod(name=name, namespace=namespace)

        container_statuses = []
        if pod.status.container_statuses:
            for cs in pod.status.container_statuses:
                state = "unknown"
                if cs.state.running:
                    state = "running"
                elif cs.state.waiting:
                    state = "waiting"
                elif cs.state.terminated:
                    state = "terminated"
                container_statuses.append(ContainerStatus(name=cs.name, state=state, ready=cs.ready))

        resource_limits = None
        resource_requests = None
        if pod.spec.containers and pod.spec.containers[0].resources:
            if pod.spec.containers[0].resources.limits:
                resource_limits = ResourceRequirements(
                    cpu=pod.spec.containers[0].resources.limits.get("cpu"),
                    memory=pod.spec.containers[0].resources.limits.get("memory")
                )
            if pod.spec.containers[0].resources.requests:
                resource_requests = ResourceRequirements(
                    cpu=pod.spec.containers[0].resources.requests.get("cpu"),
                    memory=pod.spec.containers[0].resources.requests.get("memory")
                )

        return PodDetails(
            status=pod.status.phase,
            restart_count=sum(cs.restart_count for cs in pod.status.container_statuses) if pod.status.container_statuses else 0,
            container_statuses=container_statuses,
            resource_limits=resource_limits,
            resource_requests=resource_requests
        )
    except client.ApiException as e:
        if e.status == 404:
            logger.info(f"Pod {name} not found in namespace {namespace}.")
            return None
        logger.error(f"Kubernetes API error when getting pod details: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred when getting pod details: {e}")
        return None

def get_pod_logs(namespace: str, name: str, container: Optional[str] = None, tail: int = 100) -> Optional[str]:
    if core_v1_api is None:
        logger.error("Kubernetes client not initialized.")
        return None

    try:
        logs = core_v1_api.read_namespaced_pod_log(name=name, namespace=namespace, container=container, tail_lines=tail)
        return logs
    except client.ApiException as e:
        if e.status == 404:
            logger.info(f"Pod {name} or container {container} not found in namespace {namespace}.")
            return None
        logger.error(f"Kubernetes API error when getting pod logs: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred when getting pod logs: {e}")
        return None
