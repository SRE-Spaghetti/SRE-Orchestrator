# Requirements

### Functional

1.  **FR1:** The system shall provide a secure REST API endpoint (`/api/v1/incidents`) that accepts `POST` requests with a JSON payload to create a new incident investigation.
2.  **FR2:** The system shall integrate with a cloud-based LLM to parse the `description` field from the incident creation payload.
3.  **FR3:** The system shall include a Kubernetes Agent capable of connecting to the in-cluster Kubernetes API.
4.  **FR4:** The Kubernetes Agent shall be able to retrieve the status, logs, and configuration details (e.g., resource limits, environment variables) for a specified pod.
5.  **FR5:** The system shall use a static, file-based knowledge graph to represent the basic components of the monitored application.
6.  **FR6:** The system shall implement a basic rules engine to correlate data from the Kubernetes Agent and pod logs to suggest a root cause.
7.  **FR7:** The system shall provide a REST API endpoint (`/api/v1/incidents/{id}`) that accepts `GET` requests to return the status and results of an investigation.
8.  **FR8:** The investigation results shall be returned in a structured JSON format, including the initial problem, evidence collected, and a suggested root cause with a confidence score.

### Non-Functional

1.  **NFR1:** The entire system must be deployable via a single Helm chart.
2.  **NFR2:** The system's components, under normal load, must not consume more than 0.5 vCPU and 512MiB of RAM combined.
3.  **NFR3:** All communication with external systems (e.g., the LLM API) must be encrypted using TLS.
4.  **NFR4:** The system must be granted read-only access to the Kubernetes API; it must not have permissions to modify any cluster resources.
5.  **NFR5:** The REST API endpoints must respond within 500ms for all valid requests.
6.  **NFR6:** The system should be able to complete a standard investigation (e.g., for a pod OOMKilled) in under 2 minutes.
