# SRE Orchestrator Product Requirements Document (PRD)

### Goals and Background Context

#### Goals

*   Automate the initial triage and investigation of production incidents.
*   Reduce Mean Time to Resolution (MTTR) for SRE teams.
*   Provide a centralized, intelligent view of diagnostic data.
*   Codify expert SRE knowledge into a repeatable, automated process.
*   Enable developer self-service for incident investigation.

#### Background Context

This project aims to address the significant operational overhead faced by SRE teams in modern cloud-native environments. The current process for diagnosing production failures is manual, time-consuming, and requires a high level of expertise. The SRE Orchestrator will fill the gap between incident detection and resolution by acting as a virtual SRE, intelligently coordinating AI agents to perform automated diagnostics and provide actionable insights. This will free up valuable engineering time for more proactive reliability work.

#### Change Log

| Date       | Version | Description      | Author     |
| :--------- | :------ | :--------------- | :--------- |
| 2025-09-15 | 1.0     | Initial draft    | John (PM)  |

---

### Requirements

#### Functional

1.  **FR1:** The system shall provide a secure REST API endpoint (`/api/v1/incidents`) that accepts `POST` requests with a JSON payload to create a new incident investigation.
2.  **FR2:** The system shall integrate with a cloud-based LLM to parse the `description` field from the incident creation payload.
3.  **FR3:** The system shall include a Kubernetes Agent capable of connecting to the in-cluster Kubernetes API.
4.  **FR4:** The Kubernetes Agent shall be able to retrieve the status, logs, and configuration details (e.g., resource limits, environment variables) for a specified pod.
5.  **FR5:** The system shall use a static, file-based knowledge graph to represent the basic components of the monitored application.
6.  **FR6:** The system shall implement a basic rules engine to correlate data from the Kubernetes Agent and pod logs to suggest a root cause.
7.  **FR7:** The system shall provide a REST API endpoint (`/api/v1/incidents/{id}`) that accepts `GET` requests to return the status and results of an investigation.
8.  **FR8:** The investigation results shall be returned in a structured JSON format, including the initial problem, evidence collected, and a suggested root cause with a confidence score.

#### Non-Functional

1.  **NFR1:** The entire system must be deployable via a single Helm chart.
2.  **NFR2:** The system's components, under normal load, must not consume more than 0.5 vCPU and 512MiB of RAM combined.
3.  **NFR3:** All communication with external systems (e.g., the LLM API) must be encrypted using TLS.
4.  **NFR4:** The system must be granted read-only access to the Kubernetes API; it must not have permissions to modify any cluster resources.
5.  **NFR5:** The REST API endpoints must respond within 500ms for all valid requests.
6.  **NFR6:** The system should be able to complete a standard investigation (e.g., for a pod OOMKilled) in under 2 minutes.

---

### Technical Assumptions

*   **Repository Structure:** **Monorepo**
    *   **Rationale:** A monorepo is chosen to simplify dependency management and ensure consistency across the core orchestrator and the various agents, especially in the early stages of development.
*   **Service Architecture:** **Microservices**
    *   **Rationale:** A microservices architecture, where the orchestrator and each agent are independent services, is selected for scalability and resilience. This allows individual agents to be updated, scaled, or even fail without impacting the entire system.
*   **Testing Requirements:** **Unit + Integration Testing**
    *   **Rationale:** A comprehensive testing strategy is crucial for a reliability tool. We will require thorough unit tests for individual functions and integration tests to ensure that the orchestrator, agents, and external data sources work correctly together.
*   **Additional Technical Assumptions and Requests:**
    *   **Backend Language:** The primary language for development will be **Go**, leveraging its strong performance and excellent support for Kubernetes.
    *   **Containerization:** All components will be containerized using **Docker**.
    *   **Deployment:** All components will be deployed and managed via **Helm** charts.
    *   **Knowledge Graph (MVP):** The initial implementation will use a simple, file-based (e.g., YAML or JSON) representation of the system's topology.
    *   **LLM Integration:** The system will initially integrate with a single, cloud-based LLM (specific provider to be determined by research).
    *   **Agent Framework:** New agents will be developed using the **Langgraph** framework to work within the **Model Context Protocol (MCP)**.

---

### Epic List

*   **Epic 1: Foundational Orchestrator & API**
    *   **Goal:** Establish the core service framework, REST API endpoints for incident management, and the Helm chart for deployment, creating a runnable and testable application foundation.
*   **Epic 2: Kubernetes Data Collection Agent**
    *   **Goal:** Implement the first specialized agent that can connect to the Kubernetes cluster, retrieve essential diagnostic data (status, logs, configuration) from pods, and pass it back to the orchestrator.
*   **Epic 3: Intelligent Triage and Root Cause Suggestion**
    *   **Goal:** Integrate the LLM for parsing incoming requests, introduce the static knowledge graph for context, and implement the correlation engine to analyze the data from the Kubernetes agent and provide an initial root cause suggestion.

---

### Epic 1: Foundational Orchestrator & API

**Goal:** This epic focuses on establishing the essential bedrock of the SRE Orchestrator. The objective is to create a runnable, deployable, and testable application foundation. By the end of this epic, we will have a core service with a working API for incident management and a Helm chart for consistent Kubernetes deployments, but no diagnostic capabilities yet.

#### Story 1.1: Project Scaffolding & Health Check

*   **As a** DevOps Engineer,
*   **I want** to initialize the Go project structure and create a basic HTTP server with a `/health` endpoint,
*   **so that** I have a runnable application to build upon and a way to verify it's running correctly.

**Acceptance Criteria:**

1.  A new Go project is initialized with a standard, scalable layout (e.g., `/cmd`, `/internal`, `/pkg`).
2.  A basic HTTP server is implemented using the standard library or a lightweight framework (e.g., Gin).
3.  A `GET /health` endpoint is created.
4.  When called, the `/health` endpoint returns a `200 OK` status code and a JSON body: `{"status": "ok"}`.

#### Story 1.2: Basic Helm Chart

*   **As a** DevOps Engineer,
*   **I want** a basic Helm chart that deploys the application to Kubernetes,
*   **so that** I can automate and manage its deployment lifecycle.

**Acceptance Criteria:**

1.  A new Helm chart is created within the project repository (e.g., in a `/charts` directory).
2.  The chart includes templates for a Deployment, a Service, and a ServiceAccount.
3.  The application's Docker image can be built and used by the Helm chart.
4.  The application can be successfully deployed to a local Kubernetes cluster (e.g., Kind, Minikube) using `helm install`.
5.  The `/health` endpoint is accessible within the cluster via the created Service.

#### Story 1.3: Incident Creation API Endpoint

*   **As an** SRE,
*   **I want** to create a new incident investigation by sending a `POST` request to `/api/v1/incidents`,
*   **so that** I can programmatically trigger the diagnostic process.

**Acceptance Criteria:**

1.  A `POST /api/v1/incidents` endpoint is implemented.
2.  The endpoint accepts a JSON payload containing at least a `description` field (e.g., `{"description": "Pod 'auth-service-xyz' is in CrashLoopBackOff"}`).
3.  Upon receiving a valid request, the endpoint returns a `202 Accepted` status code.
4.  The response body is a JSON object containing a unique, system-generated `incident_id`.
5.  The new incident (with its ID, description, and an initial status of "pending") is stored in a simple in-memory data store for now.

#### Story 1.4: Incident Status API Endpoint

*   **As an** SRE,
*   **I want** to check the status of an ongoing investigation by sending a `GET` request to `/api/v1/incidents/{id}`,
*   **so that** I can monitor its progress and retrieve the results when it's complete.

**Acceptance Criteria:**

1.  A `GET /api/v1/incidents/{id}` endpoint is implemented, where `{id}` is the incident ID.
2.  If a valid `incident_id` is provided, the endpoint returns a `200 OK` status.
3.  The response body is a JSON object containing the `incident_id`, the original `description`, a `status` field (e.g., "pending"), and a timestamp for when it was created.
4.  If the provided `incident_id` does not exist, the endpoint returns a `404 Not Found` error.

---

### Epic 2: Kubernetes Data Collection Agent

**Goal:** This epic focuses on creating the first specialized diagnostic agent. The objective is to build a standalone service that can connect to the Kubernetes cluster, retrieve essential data about pods, and make that data available to the orchestrator. By the end of this epic, the orchestrator will be able to delegate a request to this new agent to get real, live data from the cluster.

#### Story 2.1: K8s Agent Service & Cluster Connection

*   **As a** Developer,
*   **I want** to create a new Go microservice for the Kubernetes Agent and configure it to connect to the in-cluster Kubernetes API,
*   **so that** it has the foundational structure and permissions to perform its diagnostic tasks.

**Acceptance Criteria:**

1.  A new Go application is created in the monorepo (e.g., in `/cmd/k8s-agent`).
2.  The agent is configured to use a Kubernetes Service Account to authenticate with the in-cluster API.
3.  The agent's Helm chart is updated to include the necessary RBAC roles and role bindings for read-only access to pods and their logs.
4.  Upon startup, the agent successfully initializes a Kubernetes client and can perform a basic API call (e.g., listing pods in its own namespace) to verify the connection.
5.  The agent exposes its own `/health` endpoint.

#### Story 2.2: Retrieve Pod Details

*   **As the** Orchestrator,
*   **I want** to request the detailed status and configuration of a specific pod from the Kubernetes Agent,
*   **so that** I can gather basic diagnostic information.

**Acceptance Criteria:**

1.  The Kubernetes Agent exposes an internal API endpoint (e.g., `GET /api/v1/pods/{namespace}/{name}`).
2.  When called, the agent uses the Kubernetes API to fetch the full Pod resource for the specified pod.
3.  The agent extracts and returns a simplified JSON object containing key details: status (e.g., `Running`, `Pending`, `Failed`), container statuses, restart counts, and resource limits/requests.
4.  If the pod is not found, the agent returns a `404 Not Found` error.

#### Story 2.3: Retrieve Pod Logs

*   **As the** Orchestrator,
*   **I want** to request the logs from a specific pod's container from the Kubernetes Agent,
*   **so that** I can analyze them for error messages.

**Acceptance Criteria:**

1.  The Kubernetes Agent exposes an internal API endpoint (e.g., `GET /api/v1/pods/{namespace}/{name}/logs`).
2.  The endpoint accepts optional query parameters to specify the container name and the number of log lines to retrieve (e.g., `?container=app&tail=100`).
3.  When called, the agent uses the Kubernetes API to stream the logs from the specified container.
4.  The agent returns the logs as a plain text or JSON response.
5.  If the pod or container is not found, or if logs are not available, an appropriate error is returned.

#### Story 2.4: Orchestrator Integration

*   **As the** Orchestrator,
*   **I want** to call the Kubernetes Agent's internal API to retrieve pod details and logs,
*   **so that** I can incorporate this data into my investigation process.

**Acceptance Criteria:**

1.  The main orchestrator service is updated to be able to discover and communicate with the Kubernetes Agent service (e.g., via Kubernetes service DNS).
2.  When an incident is created (from Story 1.3), the orchestrator's internal logic is updated to make a placeholder call to the Kubernetes Agent.
3.  For now, the orchestrator will be hard-coded to request details and logs for a pod name it extracts from the incident description.
4.  The data returned from the agent is stored as part of the incident's data in the in-memory store.
5.  The `GET /api/v1/incidents/{id}` endpoint is updated to include a new `evidence` field containing the data collected from the agent.

---

### Epic 3: Intelligent Triage and Root Cause Suggestion

**Goal:** This epic brings together the foundational work from the previous two. The objective is to introduce the "brains" of the operation by integrating the LLM for intelligent parsing, using a knowledge graph for context, and implementing a correlation engine to generate a meaningful root cause suggestion. By the end of this epic, the SRE Orchestrator will be able to perform a basic, end-to-end, intelligent diagnosis.

#### Story 3.1: LLM Integration for Intent Extraction

*   **As the** Orchestrator,
*   **I want** to send the description from a new incident to an LLM,
*   **so that** I can extract key entities like the pod name, namespace, and the nature of the problem.

**Acceptance Criteria:**

1.  The orchestrator service is configured with the credentials to connect to a cloud-based LLM API (e.g., OpenAI, Google AI).
2.  When a new incident is created, the orchestrator constructs a specific prompt for the LLM, asking it to extract the pod name, namespace, and a summary of the error from the incident's `description` field.
3.  The orchestrator sends the prompt to the LLM and parses the structured response (e.g., JSON) to get the extracted entities.
4.  The extracted entities are stored with the incident data.
5.  The hard-coded pod name from Story 2.4 is replaced with the pod name extracted by the LLM.

#### Story 3.2: Static Knowledge Graph Implementation

*   **As the** Orchestrator,
*   **I want** to load a simple, file-based knowledge graph on startup,
*   **so that** I have a basic understanding of the application's components and their relationships.

**Acceptance Criteria:**

1.  A YAML or JSON file is created in the repository to represent the knowledge graph (e.g., `knowledge_graph.yaml`).
2.  The file defines a simple schema with `components` (e.g., services, databases) and their `relationships` (e.g., `depends_on`).
3.  The orchestrator service parses this file on startup and loads the graph into an in-memory data structure.
4.  The orchestrator can perform a basic query on the graph, such as "find all components that component X depends on."

#### Story 3.3: Root Cause Correlation Engine

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

#### Story 3.4: Final Report Generation

*   **As an** SRE,
*   **I want** the final investigation report to include the LLM's analysis and the correlation engine's suggested root cause,
*   **so that** I have a complete, actionable summary of the incident.

**Acceptance Criteria:**

1.  The orchestrator's main investigation workflow is updated to call the new correlation engine after gathering evidence.
2.  The `status` of the incident is updated from "pending" to "completed" once the correlation is finished.
3.  The `GET /api/v1/incidents/{id}` endpoint is updated to include the final report.
4.  The response body now includes the `suggested_root_cause`, the `confidence_score`, and the supporting `evidence`.


### Checklist Results Report

#### Executive Summary

*   **Overall PRD Completeness:** 95%
*   **MVP Scope Appropriateness:** Just Right
*   **Readiness for Architecture Phase:** Ready
*   **Most Critical Gaps or Concerns:** The PRD is very strong. The only minor gap is the lack of explicit user experience requirements, but this was a deliberate decision for the API-only MVP and is acceptable.

#### Category Analysis Table

| Category                         | Status | Critical Issues                                |
| -------------------------------- | ------ | ---------------------------------------------- |
| 1. Problem Definition & Context  | ✅ PASS | None.                                          |
| 2. MVP Scope Definition          | ✅ PASS | None. The scope is well-defined and realistic. |
| 3. User Experience Requirements  | ⚪ N/A  | Not applicable for the API-only MVP.           |
| 4. Functional Requirements       | ✅ PASS | None. Requirements are clear and testable.     |
| 5. Non-Functional Requirements   | ✅ PASS | None. NFRs are specific and cover key areas.   |
| 6. Epic & Story Structure        | ✅ PASS | None. The epics are logical and stories are well-sized. |
| 7. Technical Guidance            | ✅ PASS | None. Clear constraints are provided for the architect. |
| 8. Cross-Functional Requirements | ✅ PASS | None.                                          |
| 9. Clarity & Communication       | ✅ PASS | None. The document is well-structured and clear. |

#### Top Issues by Priority

*   **BLOCKERS:** None.
*   **HIGH:** None.
*   **MEDIUM:** None.
*   **LOW:** None.

#### MVP Scope Assessment

The MVP scope is well-defined and appropriate. It focuses on delivering a core, valuable piece of functionality (automated data collection and basic analysis) without getting bogged down in non-essential features. The decision to defer the UI, advanced agents, and metrics integration is a good one.

#### Technical Readiness

The PRD provides clear technical constraints and guidance for the Architect. The decisions on the monorepo, microservices architecture, and the primary technology (Go) give a strong starting point. The identified areas for further research (LLMs, graph databases) are also well-noted.

#### Recommendations

No major recommendations. The PRD is in excellent shape.

### Final Decision

✅ **READY FOR ARCHITECT**: The PRD and epics are comprehensive, properly structured, and ready for the architectural design phase.
