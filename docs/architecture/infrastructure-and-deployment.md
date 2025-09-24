# Infrastructure and Deployment

### Infrastructure as Code

- **Tool:** Helm 3.15.1
- **Location:** `charts/sre-orchestrator`
- **Approach:** A single parent Helm chart will manage the deployment of all microservices (the Orchestrator and the Kubernetes Agent). This simplifies the deployment process and ensures that all components of the application are deployed and versioned together.

### Deployment Strategy

- **Strategy:** Rolling Update. This is the default Kubernetes deployment strategy and is a good starting point. It ensures zero-downtime deployments by incrementally updating pods with the new version.
- **CI/CD Platform:** TBD (e.g., GitHub Actions, GitLab CI, Jenkins). This will be decided based on the project's hosting and team preferences.
- **Pipeline Configuration:** TBD (will be located in the repository root, e.g., `.github/workflows/` or `.gitlab-ci.yml`).

### Environments

- **`development`:** Local developer environment, likely running on Minikube or Docker Desktop.
- **`staging`:** A shared, production-like environment for integration testing and QA.
- **`production`:** The live environment for end-users.

### Environment Promotion Flow

A simple, linear promotion flow will be used:
`development` -> `staging` -> `production`

Code will be merged to a `main` branch, which will trigger a deployment to `staging`. Production deployments will be triggered manually by creating a git tag.

### Rollback Strategy

- **Primary Method:** `helm rollback`. Helm's built-in rollback capabilities will be used to revert to a previous stable release in case of a failed deployment.
- **Trigger Conditions:** Failed health checks after deployment, significant increase in error rates, or manual trigger by an SRE.
- **Recovery Time Objective:** < 15 minutes.
