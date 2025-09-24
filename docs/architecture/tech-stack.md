# Tech Stack

### Cloud Infrastructure

- **Provider:** Cloud-Agnostic (initially). The system is designed to run on any standard Kubernetes cluster.
- **Key Services:** Kubernetes (for orchestration), Docker (for containerization), Cloud-based LLM (Provider TBD).
- **Deployment Regions:** TBD based on final cloud provider selection and user location.

### Technology Stack Table

| Category | Technology | Version | Purpose | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Language** | Python | 3.12.11 | Primary development language | Modern, robust, with excellent support for AI/ML and web frameworks. Specified in PRD. |
| **Framework (API)** | FastAPI | 0.116.1 | High-performance web framework for building REST APIs | Offers modern Python features, automatic docs, and dependency injection. Specified in PRD. |
| **Framework (Agent)**| LangGraph | 0.6.7 | Framework for building stateful, multi-actor agent applications | Provides a robust way to create and coordinate AI agents. Specified in PRD. |
| **Dependency Mgt** | Poetry | 2.2.2 | Dependency management and packaging | Simplifies dependency resolution and ensures reproducible builds. Specified in PRD. |
| **Containerization**| Docker | 28.4.0 | Container runtime and tooling | Standard for containerizing applications for consistent deployment. Specified in PRD. |
| **Orchestration** | Kubernetes | 1.34.1 | Container orchestration platform | Industry standard for deploying and managing containerized applications at scale. |
| **Deployment** | Helm | 3.19.0 | Package manager for Kubernetes | Simplifies the deployment and management of applications on Kubernetes. Specified in PRD. |
| **LLM Provider** | TBD | TBD | For natural language understanding and generation | A specific provider will be chosen based on performance, cost, and features. |
| **Data Storage (MVP)| In-Memory Dict | N/A | Temporary storage for incident data | Simple, no-dependency solution for the MVP, to be replaced later. |
| **Knowledge Graph**| YAML File | N/A | Static representation of system topology | Simple, human-readable format for the initial knowledge graph implementation. |
