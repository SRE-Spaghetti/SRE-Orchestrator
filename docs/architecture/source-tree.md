# Source Tree

```plaintext
sre-orchestrator/
├── .gitignore
├── README.md
├── poetry.lock
├── pyproject.toml          # Monorepo-level dependencies and workspace config
├── services/
│   ├── orchestrator/
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── api/          # FastAPI routers and endpoints
│   │   │   │   ├── __init__.py
│   │   │   │   └── v1/
│   │   │   ├── core/         # Core business logic, correlation engine
│   │   │   ├── models/       # Pydantic data models
│   │   │   ├── services/     # Clients for external services (LLM, K8s Agent)
│   │   │   └── main.py       # FastAPI application entrypoint
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── pyproject.toml    # Service-specific dependencies
│   │
│   └── k8s-agent/
│       ├── app/
│       │   ├── __init__.py
│       │   ├── api/
│       │   │   ├── __init__.py
│       │   │   └── v1/
│       │   ├── services/     # Kubernetes client logic
│       │   └── main.py
│       ├── tests/
│       ├── Dockerfile
│       └── pyproject.toml
│
├── charts/
│   ├── sre-orchestrator/     # Helm chart for the entire application
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   └── templates/
│   │       ├── _helpers.tpl
│   │       ├── deployment-orchestrator.yaml
│   │       ├── deployment-k8s-agent.yaml
│   │       ├── service-orchestrator.yaml
│   │       └── ...
│
└── knowledge_graph.yaml      # Static knowledge graph for the MVP
```
