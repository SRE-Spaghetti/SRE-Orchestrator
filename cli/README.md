# SRE Orchestrator CLI

Interactive command-line interface for investigating incidents using the SRE Orchestrator.

## Installation

```bash
cd cli
poetry install
```

## Usage

```bash
# Interactive chat mode
sre-orchestrator chat

# One-shot investigation
sre-orchestrator investigate "Pod auth-service-xyz is crashing"

# List recent incidents
sre-orchestrator list

# View incident details
sre-orchestrator show <incident-id>

# Configuration
sre-orchestrator config set orchestrator-url http://localhost:8000
sre-orchestrator config set api-key <your-api-key>
```

## Configuration

The CLI stores configuration in `~/.sre-orchestrator/config.yaml`.

You can also use environment variables:
- `SRE_ORCHESTRATOR_URL`: Orchestrator service URL
- `SRE_ORCHESTRATOR_API_KEY`: API key for authentication
