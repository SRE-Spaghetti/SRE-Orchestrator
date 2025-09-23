# Epic List

*   **Epic 1: Foundational Orchestrator & API**
    *   **Goal:** Establish the core service framework, REST API endpoints for incident management, and the Helm chart for deployment, creating a runnable and testable application foundation.
*   **Epic 2: Kubernetes Data Collection Agent**
    *   **Goal:** Implement the first specialized agent that can connect to the Kubernetes cluster, retrieve essential diagnostic data (status, logs, configuration) from pods, and pass it back to the orchestrator.
*   **Epic 3: Intelligent Triage and Root Cause Suggestion**
    *   **Goal:** Integrate the LLM for parsing incoming requests, introduce the static knowledge graph for context, and implement the correlation engine to analyze the data from the Kubernetes agent and provide an initial root cause suggestion.
