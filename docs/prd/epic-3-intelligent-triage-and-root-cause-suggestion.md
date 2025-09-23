# Epic 3: Intelligent Triage and Root Cause Suggestion

**Goal:** This epic brings together the foundational work from the previous two. The objective is to introduce the "brains" of the operation by integrating the LLM for intelligent parsing, using a knowledge graph for context, and implementing a correlation engine to generate a meaningful root cause suggestion. By the end of this epic, the SRE Orchestrator will be able to perform a basic, end-to-end, intelligent diagnosis.

### Story 3.1: LLM Integration for Intent Extraction

*   **As the** Orchestrator,
*   **I want** to send the description from a new incident to an LLM,
*   **so that** I can extract key entities like the pod name, namespace, and the nature of the problem.

**Acceptance Criteria:**

1.  The orchestrator service is configured with the credentials to connect to a cloud-based LLM API (e.g., OpenAI, Google AI).
2.  When a new incident is created, the orchestrator constructs a specific prompt for the LLM, asking it to extract the pod name, namespace, and a summary of the error from the incident's `description` field.
3.  The orchestrator sends the prompt to the LLM and parses the structured response (e.g., JSON) to get the extracted entities.
4.  The extracted entities are stored with the incident data.
5.  The hard-coded pod name from Story 2.4 is replaced with the pod name extracted by the LLM.

### Story 3.2: Static Knowledge Graph Implementation

*   **As the** Orchestrator,
*   **I want** to load a simple, file-based knowledge graph on startup,
*   **so that** I have a basic understanding of the application's components and their relationships.

**Acceptance Criteria:**

1.  A YAML or JSON file is created in the repository to represent the knowledge graph (e.g., `knowledge_graph.yaml`).
2.  The file defines a simple schema with `components` (e.g., services, databases) and their `relationships` (e.g., `depends_on`).
3.  The orchestrator service parses this file on startup and loads the graph into an in-memory data structure.
4.  The orchestrator can perform a basic query on the graph, such as "find all components that component X depends on."

### Story 3.3: Root Cause Correlation Engine

*   **As the** Orchestrator,
*   **I want** to use a simple rules engine to correlate the evidence from the Kubernetes Agent with context from the knowledge graph,
*   **so that** I can generate a suggested root cause.

**Acceptance Criteria:**

1.  A new "correlation" module is created in the orchestrator.
2.  The module takes the collected evidence (pod status, logs) and the knowledge graph as input.
3.  A few basic correlation rules are implemented, for example:
    *   **Rule 1:** IF a pod's restart count is high AND its logs contain "OOMKilled", THEN the suggested root cause is "Insufficient Memory".
    *   **Rule 2:** IF a pod's status is `Pending` AND its events show "FailedScheduling", THEN the suggested root cause is "Insufficient Cluster Resources".
    *   **Rule 3:** IF a pod's logs show "connection refused" to a database it `depends_on` (from the knowledge graph), THEN the suggested root cause is "Database Unreachable".
4.  The output of the engine is a suggested root cause and a confidence score (e.g., "high", "medium", "low").

### Story 3.4: Final Report Generation

*   **As an** SRE,
*   **I want** the final investigation report to include the LLM's analysis and the correlation engine's suggested root cause,
*   **so that** I have a complete, actionable summary of the incident.

**Acceptance Criteria:**

1.  The orchestrator's main investigation workflow is updated to call the new correlation engine after gathering evidence.
2.  The `status` of the incident is updated from "pending" to "completed" once the correlation is finished.
3.  The `GET /api/v1/incidents/{id}` endpoint is updated to include the final report.
4.  The response body now includes the `suggested_root_cause`, the `confidence_score`, and the supporting `evidence`.
