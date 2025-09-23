# External APIs

### Cloud LLM API

- **Purpose:** To parse natural language incident descriptions and extract structured entities (e.g., pod name, namespace, error type).
- **Documentation:** TBD (depends on the selected provider, e.g., OpenAI, Google AI, Anthropic).
- **Base URL(s):** TBD
- **Authentication:** TBD (likely API Key-based, e.g., `Authorization: Bearer $API_KEY`). Secrets will be managed via Kubernetes secrets.
- **Rate Limits:** TBD (will need to be considered when selecting a provider and plan).

**Key Endpoints Used:**
- `POST /v1/chat/completions` (or similar endpoint for generating text): Used to send the incident description and a prompt to the LLM.

**Integration Notes:** The Orchestrator's `LLM Client` will be responsible for all communication with this API. The client will need to be designed with a clear interface so that different LLM providers can be swapped in or out with minimal changes to the core application logic. Error handling will need to account for API rate limits, timeouts, and transient failures.
