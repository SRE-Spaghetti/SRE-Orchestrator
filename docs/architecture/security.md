# Security

### Input Validation

- **Validation Library:** Pydantic (as part of FastAPI).
- **Validation Location:** All incoming API requests will be validated at the edge of the service by FastAPI using Pydantic models.
- **Required Rules:**
    - All external inputs MUST be validated.
    - Validation at API boundary before processing.
    - Whitelist approach preferred over blacklist.

### Authentication & Authorization

- **Auth Method:** No authentication will be implemented for the public API in the MVP. For future iterations, API Key authentication is recommended.
- **Session Management:** Not applicable.
- **Required Patterns:**
    - The Kubernetes Agent will use a Kubernetes Service Account with a read-only Role to authenticate with the Kubernetes API. This follows the principle of least privilege.

### Secrets Management

- **Development:** Secrets (e.g., LLM API key) will be managed via environment variables, loaded from a `.env` file which will be excluded from git.
- **Production:** Secrets will be managed using Kubernetes Secrets.
- **Code Requirements:**
    - NEVER hardcode secrets.
    - Access via environment variables or Kubernetes Secrets only.
    - No secrets in logs or error messages.

### API Security

- **Rate Limiting:** Not planned for the MVP, but a library like `slowapi` can be added later if needed.
- **CORS Policy:** A permissive CORS policy will be used for development, but it should be restricted to known origins in production.
- **Security Headers:** Standard security headers (e.g., `X-Content-Type-Options`, `X-Frame-Options`) will be added to all API responses using middleware.
- **HTTPS Enforcement:** HTTPS will be enforced at the ingress level in the Kubernetes cluster.

### Data Protection

- **Encryption at Rest:** Not applicable for the in-memory store. When a persistent database is added, it must be configured to encrypt data at rest.
- **Encryption in Transit:** All communication between services and with external APIs (LLM, Kubernetes) will use TLS.
- **PII Handling:** The system is not designed to handle Personally Identifiable Information (PII). Incident descriptions should be sanitized of any PII before being submitted.
- **Logging Restrictions:** Do not log raw incident descriptions or any data that might contain sensitive information.

### Dependency Security

- **Scanning Tool:** `pip-audit` or a similar tool will be integrated into the CI pipeline to scan for known vulnerabilities in Python dependencies.
- **Update Policy:** Dependencies will be reviewed and updated on a regular basis.
- **Approval Process:** New dependencies must be approved by the team before being added to the project.

### Security Testing

- **SAST Tool:** `bandit` will be integrated into the CI pipeline to perform static analysis security testing.
- **DAST Tool:** Not planned for the MVP.
- **Penetration Testing:** Not planned for the MVP.
