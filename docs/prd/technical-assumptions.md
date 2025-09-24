# Technical Assumptions

*   **Repository Structure:** **Monorepo**
    *   **Rationale:** A monorepo is chosen to simplify dependency management and ensure consistency across the core orchestrator and the various agents, especially in the early stages of development.
*   **Service Architecture:** **Microservices**
    *   **Rationale:** A microservices architecture, where the orchestrator and each agent are independent services, is selected for scalability and resilience. This allows individual agents to be updated, scaled, or even fail without impacting the entire system.
*   **Testing Requirements:** **Unit + Integration Testing**
    *   **Rationale:** A comprehensive testing strategy is crucial for a reliability tool. We will require thorough unit tests for individual functions and integration tests to ensure that the orchestrator, agents, and external data sources work correctly together.
*   **Additional Technical Assumptions and Requests:**
    *   **Backend Language:** The primary language for development will be **Python** with **LangGraph** and **FastAPI**, leveraging its flexibility and suitability for Agentic tools and support for Kubernetes.
    *   **Poetry** will be used for Python dependency management  
    *   **Containerization:** All components will be containerized using **Docker**.
    *   **Deployment:** All components will be deployed and managed via **Helm** charts.
    *   **Knowledge Graph (MVP):** The initial implementation will use a simple, file-based (e.g., YAML or JSON) representation of the system's topology.
    *   **LLM Integration:** The system will initially integrate with a single, cloud-based LLM (specific provider to be determined by research).
    *   **Agent Framework:** New agents will be developed using the **LangGraph** framework to work with the **Model Context Protocol (MCP)**.
