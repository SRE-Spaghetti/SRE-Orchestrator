from uuid import UUID
from typing import Dict, Optional, Any, List
from datetime import datetime
import logging
from ..models.incidents import Incident, InvestigationStep
from ..core.investigation_agent import create_investigation_agent, investigate_incident

logger = logging.getLogger(__name__)


class IncidentRepository:
    def __init__(self):
        self._incidents: Dict[UUID, Incident] = {}

    def create_incident_sync(self, description: str) -> Incident:
        """
        Synchronously create incident with pending status.
        Does NOT start investigation.

        Args:
            description: The incident description

        Returns:
            Incident with status="pending"
        """
        incident = Incident(description=description, status="pending")
        self._incidents[incident.id] = incident

        logger.info(f"Created incident {incident.id} with status 'pending'")

        # Add initial investigation step
        incident.investigation_steps.append(
            InvestigationStep(
                step_name="incident_created",
                status="completed",
                details={"description": description}
            )
        )

        return incident

    async def investigate_incident_async(
        self,
        incident_id: UUID,
        mcp_tools: List[Any],
        llm_config: Dict[str, Any],
    ):
        """
        Execute investigation as background task.
        Updates incident status and results in-place.

        Args:
            incident_id: The incident UUID
            mcp_tools: List of LangChain-compatible MCP tools
            llm_config: LLM configuration dictionary
        """
        incident = self._incidents.get(incident_id)
        if not incident:
            logger.error(f"Incident {incident_id} not found")
            return

        try:
            # Run investigation (existing logic)
            await self._investigate_incident(incident, mcp_tools, llm_config)
        except Exception as e:
            logger.error(f"Background investigation failed for incident {incident_id}: {e}", exc_info=True)
            incident.status = "failed"
            incident.error_message = str(e)
            incident.completed_at = datetime.utcnow()

            # Add failed investigation step
            incident.investigation_steps.append(
                InvestigationStep(
                    step_name="investigation_failed",
                    status="failed",
                    details={"error": str(e)}
                )
            )

    async def create(
        self,
        description: str,
        mcp_tools: List[Any],
        llm_config: Dict[str, Any],
    ) -> Incident:
        """
        Create a new incident and initiate investigation using LangGraph agent.

        DEPRECATED: Use create_incident_sync() + investigate_incident_async() instead.

        Args:
            description: The incident description
            mcp_tools: List of LangChain-compatible MCP tools
            llm_config: LLM configuration dictionary

        Returns:
            Created incident with initial status "pending"
        """
        incident = self.create_incident_sync(description)
        await self.investigate_incident_async(incident.id, mcp_tools, llm_config)
        return incident

    async def _investigate_incident(
        self,
        incident: Incident,
        mcp_tools: List[Any],
        llm_config: Dict[str, Any],
    ):
        """
        Execute the investigation workflow using LangGraph agent.

        Args:
            incident: The incident to investigate
            mcp_tools: List of LangChain-compatible MCP tools
            llm_config: LLM configuration dictionary
        """
        incident_id = str(incident.id)

        # Update status to in_progress
        incident.status = "in_progress"
        incident.investigation_steps.append(
            InvestigationStep(
                step_name="investigation_started",
                status="started",
                details={"timestamp": datetime.utcnow().isoformat()}
            )
        )

        logger.info(f"Starting investigation for incident {incident_id}")

        # Create the investigation agent
        try:
            agent = await create_investigation_agent(mcp_tools, llm_config)

            incident.investigation_steps.append(
                InvestigationStep(
                    step_name="agent_created",
                    status="completed",
                    details={"tool_count": len(mcp_tools)}
                )
            )
        except Exception as e:
            logger.error(f"Failed to create agent for incident {incident_id}: {e}")
            raise

        # Define callback to update incident during investigation
        async def update_callback(inc_id: str, status: str, details: Dict[str, Any]):
            """Callback to update incident status during investigation"""
            if status == "investigating":
                incident.investigation_steps.append(
                    InvestigationStep(
                        step_name="investigation_progress",
                        status="started",
                        details=details
                    )
                )
            elif status == "completed":
                # Investigation completed successfully
                pass
            elif status == "failed":
                # Investigation failed
                pass

        # Execute the investigation
        result = await investigate_incident(
            agent=agent,
            incident_id=incident_id,
            description=incident.description,
            update_callback=update_callback
        )

        # Update incident with investigation results
        if result["status"] == "completed":
            incident.status = "completed"
            incident.suggested_root_cause = result["root_cause"]
            incident.confidence_score = result["confidence"]
            incident.completed_at = datetime.utcnow()

            # Store evidence from tool calls
            incident.evidence = {
                "tool_calls": result["tool_calls"],
                "reasoning": result["reasoning"],
                "recommendations": result.get("recommendations", [])
            }

            # Add evidence from investigation
            if result.get("evidence"):
                incident.evidence["collected_evidence"] = result["evidence"]

            incident.investigation_steps.append(
                InvestigationStep(
                    step_name="investigation_completed",
                    status="completed",
                    details={
                        "root_cause": result["root_cause"],
                        "confidence": result["confidence"],
                        "tool_calls_count": len(result["tool_calls"])
                    }
                )
            )

            logger.info(
                f"Investigation completed for incident {incident_id}: "
                f"root_cause={result['root_cause']}, confidence={result['confidence']}"
            )
        else:
            # Investigation failed - preserve partial results
            incident.status = "failed"
            incident.error_message = result.get("error", "Unknown error")
            incident.completed_at = datetime.utcnow()

            # Preserve partial investigation results even on failure
            partial_evidence = {}

            # Store any tool calls that were executed before failure
            if result.get("tool_calls"):
                partial_evidence["tool_calls"] = result["tool_calls"]
                logger.info(
                    f"Preserved {len(result['tool_calls'])} tool call(s) from failed investigation"
                )

            # Store any evidence collected before failure
            if result.get("evidence"):
                partial_evidence["collected_evidence"] = result["evidence"]
                logger.info(
                    f"Preserved {len(result['evidence'])} evidence item(s) from failed investigation"
                )

            # Store any partial reasoning
            if result.get("reasoning"):
                partial_evidence["partial_reasoning"] = result["reasoning"]

            # Store partial root cause if available
            if result.get("root_cause"):
                incident.suggested_root_cause = result["root_cause"]
                incident.confidence_score = result.get("confidence", "low")
                partial_evidence["partial_root_cause"] = result["root_cause"]
                logger.info(
                    f"Preserved partial root cause from failed investigation: {result['root_cause']}"
                )

            if partial_evidence:
                incident.evidence = partial_evidence

            incident.investigation_steps.append(
                InvestigationStep(
                    step_name="investigation_failed",
                    status="failed",
                    details={
                        "error": result.get("error", "Unknown error"),
                        "partial_results_preserved": bool(partial_evidence),
                        "tool_calls_count": len(result.get("tool_calls", [])),
                        "evidence_count": len(result.get("evidence", []))
                    }
                )
            )

            logger.error(
                f"Investigation failed for incident {incident_id}: {result.get('error')}. "
                f"Partial results preserved: {bool(partial_evidence)}"
            )

    def get_by_id(self, incident_id: UUID) -> Optional[Incident]:
        """
        Retrieve an incident by its ID.

        Args:
            incident_id: The incident UUID

        Returns:
            The incident if found, None otherwise
        """
        return self._incidents.get(incident_id)

    def update_status(
        self,
        incident_id: UUID,
        status: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Update the status of an incident.

        Args:
            incident_id: The incident UUID
            status: New status value
            details: Optional details about the status change
        """
        incident = self._incidents.get(incident_id)
        if incident:
            incident.status = status

            if status == "failed" and details and "error" in details:
                incident.error_message = details["error"]
                incident.completed_at = datetime.utcnow()
            elif status == "completed":
                incident.completed_at = datetime.utcnow()

            logger.info(f"Updated incident {incident_id} status to '{status}'")


# A single instance to act as our in-memory database
incident_repository = IncidentRepository()


def get_incident_repository() -> IncidentRepository:
    return incident_repository
