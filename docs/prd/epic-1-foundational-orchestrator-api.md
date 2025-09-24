# Epic 1: Foundational Orchestrator & API

**Goal:** This epic focuses on establishing the essential bedrock of the SRE Orchestrator. The objective is to create a runnable, deployable, and testable application foundation. By the end of this epic, we will have a core service with a working API for incident management and a Helm chart for consistent Kubernetes deployments, but no diagnostic capabilities yet.

### Story 1.1: Project Scaffolding & Health Check

*   **As a** DevOps Engineer,
*   **I want** to initialize the Python project structure with LangGraph at the core of the orchestrator and create a basic HTTP server with FastAPI with a `/health` endpoint,
*   **so that** I have a runnable application to build upon and a way to verify it's running correctly.

**Acceptance Criteria:**

1.  A new Python project is initialized with a standard, scalable layout.
2.  A basic HTTP server is implemented using the standard library or a lightweight framework (e.g., FastAPI).
3.  A `GET /health` endpoint is created.
4.  When called, the `/health` endpoint returns a `200 OK` status code and a JSON body: `{"status": "ok"}`.

### Story 1.2: Basic Helm Chart

*   **As a** DevOps Engineer,
*   **I want** a basic Helm chart that deploys the application to Kubernetes,
*   **so that** I can automate and manage its deployment lifecycle.

**Acceptance Criteria:**

1.  A new Helm chart is created within the project repository (e.g., in a `/charts` directory).
2.  The chart includes templates for a Deployment, a Service, and a ServiceAccount.
3.  The application's Docker image can be built and used by the Helm chart.
4.  The application can be successfully deployed to a local Kubernetes cluster (e.g., Kind, Minikube) using `helm install`.
5.  The `/health` endpoint is accessible within the cluster via the created Service.

### Story 1.3: Incident Creation API Endpoint

*   **As an** SRE,
*   **I want** to create a new incident investigation by sending a `POST` request to `/api/v1/incidents`,
*   **so that** I can programmatically trigger the diagnostic process.

**Acceptance Criteria:**

1.  A `POST /api/v1/incidents` endpoint is implemented.
2.  The endpoint accepts a JSON payload containing at least a `description` field (e.g., `{"description": "Pod 'auth-service-xyz' is in CrashLoopBackOff"}`).
3.  Upon receiving a valid request, the endpoint returns a `202 Accepted` status code.
4.  The response body is a JSON object containing a unique, system-generated `incident_id`.
5.  The new incident (with its ID, description, and an initial status of "pending") is stored in a simple in-memory data store for now.

### Story 1.4: Incident Status API Endpoint

*   **As an** SRE,
*   **I want** to check the status of an ongoing investigation by sending a `GET` request to `/api/v1/incidents/{id}`,
*   **so that** I can monitor its progress and retrieve the results when it's complete.

**Acceptance Criteria:**

1.  A `GET /api/v1/incidents/{id}` endpoint is implemented, where `{id}` is the incident ID.
2.  If a valid `incident_id` is provided, the endpoint returns a `200 OK` status.
3.  The response body is a JSON object containing the `incident_id`, the original `description`, a `status` field (e.g., "pending"), and a timestamp for when it was created.
4.  If the provided `incident_id` does not exist, the endpoint returns a `404 Not Found` error.
