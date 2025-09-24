# Epic 2: Kubernetes Data Collection Agent

**Goal:** This epic focuses on creating the first specialized diagnostic agent. The objective is to build a standalone service that can connect to the Kubernetes cluster, retrieve essential data about pods, and make that data available to the orchestrator. By the end of this epic, the orchestrator will be able to delegate a request to this new agent to get real, live data from the cluster.

### Story 2.1: K8s Agent Service & Cluster Connection

*   **As a** Developer,
*   **I want** to create a new Python microservice for the Kubernetes Agent and configure it to connect to the in-cluster Kubernetes API,
*   **so that** it has the foundational structure and permissions to perform its diagnostic tasks.

**Acceptance Criteria:**

1.  A new Python application is created in the monorepo (e.g., in `k8s-agent`).
2.  The agent is configured to use a Kubernetes Service Account to authenticate with the in-cluster API.
3.  The agent's Helm chart is updated to include the necessary RBAC roles and role bindings for read-only access to pods and their logs.
4.  Upon startup, the agent successfully initializes a Kubernetes client and can perform a basic API call (e.g., listing pods in its own namespace) to verify the connection.
5.  The agent exposes its own `/health` endpoint.

### Story 2.2: Retrieve Pod Details

*   **As the** Orchestrator,
*   **I want** to request the detailed status and configuration of a specific pod from the Kubernetes Agent,
*   **so that** I can gather basic diagnostic information.

**Acceptance Criteria:**

1.  The Kubernetes Agent exposes an internal API endpoint (e.g., `GET /api/v1/pods/{namespace}/{name}`).
2.  When called, the agent uses the Kubernetes API to fetch the full Pod resource for the specified pod.
3.  The agent extracts and returns a simplified JSON object containing key details: status (e.g., `Running`, `Pending`, `Failed`), container statuses, restart counts, and resource limits/requests.
4.  If the pod is not found, the agent returns a `404 Not Found` error.

### Story 2.3: Retrieve Pod Logs

*   **As the** Orchestrator,
*   **I want** to request the logs from a specific pod's container from the Kubernetes Agent,
*   **so that** I can analyze them for error messages.

**Acceptance Criteria:**

1.  The Kubernetes Agent exposes an internal API endpoint (e.g., `GET /api/v1/pods/{namespace}/{name}/logs`).
2.  The endpoint accepts optional query parameters to specify the container name and the number of log lines to retrieve (e.g., `?container=app&tail=100`).
3.  When called, the agent uses the Kubernetes API to stream the logs from the specified container.
4.  The agent returns the logs as a plain text or JSON response.
5.  If the pod or container is not found, or if logs are not available, an appropriate error is returned.

### Story 2.4: Orchestrator Integration

*   **As the** Orchestrator,
*   **I want** to call the Kubernetes Agent's internal API to retrieve pod details and logs,
*   **so that** I can incorporate this data into my investigation process.

**Acceptance Criteria:**

1.  The main orchestrator service is updated to be able to discover and communicate with the Kubernetes Agent service (e.g., via Kubernetes service DNS).
2.  When an incident is created (from Story 1.3), the orchestrator's internal logic is updated to make a placeholder call to the Kubernetes Agent.
3.  For now, the orchestrator will be hard-coded to request details and logs for a pod name it extracts from the incident description.
4.  The data returned from the agent is stored as part of the incident's data in the in-memory store.
5.  The `GET /api/v1/incidents/{id}` endpoint is updated to include a new `evidence` field containing the data collected from the agent.
