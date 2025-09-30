from ..services.knowledge_graph_service import KnowledgeGraphService


class CorrelationEngine:
    def __init__(self, knowledge_graph_service: KnowledgeGraphService):
        self.knowledge_graph_service = knowledge_graph_service

    def correlate(self, evidence: dict) -> tuple[str | None, str | None]:
        """
        Correlates evidence to suggest a root cause.

        Args:
            evidence: A dictionary containing evidence from the Kubernetes agent.

        Returns:
            A tuple containing the suggested root cause and a confidence score.
        """
        # Rule 1: OOMKilled
        if (
            "logs" in evidence
            and "OOMKilled" in evidence["logs"]
            and "restarts" in evidence
            and evidence["restarts"] > 0
        ):
            return "Insufficient Memory", "high"

        # Rule 2: FailedScheduling
        if "events" in evidence and "FailedScheduling" in evidence["events"]:
            return "Insufficient Cluster Resources", "high"

        # Rule 3: Database Unreachable
        if "logs" in evidence and "connection refused" in evidence["logs"]:
            # This rule is a bit more complex, as we need to check dependencies.
            # For the MVP, we'll just check for the log message.
            return "Database Unreachable", "medium"

        return None, None
