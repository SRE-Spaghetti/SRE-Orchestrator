# CLI User Guide

## Overview

The SRE Orchestrator CLI provides an interactive command-line interface for investigating incidents using natural language. It connects to the Orchestrator service and provides a user-friendly way to create incidents, view investigation results, and manage your configuration.

## Installation

### Prerequisites

- Python 3.12 or higher
- Access to a running SRE Orchestrator service

### Install via pip

```bash
pip install sre-orchestrator-cli
```

### Install via pipx (Recommended)

[pipx](https://pipx.pypa.io/) installs the CLI in an isolated environment:

```bash
# Install pipx if you don't have it
python -m pip install --user pipx
python -m pipx ensurepath

# Install the CLI
pipx install sre-orchestrator-cli
```

### Install from Source

```bash
# Clone the repository
git clone https://github.com/your-org/sre-orchestrator.git
cd sre-orchestrator/cli

# Install with poetry
poetry install

# Or install with pip
pip install -e .
```

### Verify Installation

```bash
sre-orchestrator --version
```

## Quick Start

### 1. Configure the CLI

Set the orchestrator URL:

```bash
sre-orchestrator config set orchestrator-url http://localhost:8000
```

If your orchestrator requires authentication:

```bash
sre-orchestrator config set api-key your-api-key-here
```

### 2. Start an Interactive Session

```bash
sre-orchestrator chat
```

### 3. Investigate an Incident

```
You: Pod auth-service-xyz is crashing in production namespace

Orchestrator: Creating incident...
Incident ID: 123e4567-e89b-12d3-a456-426614174000

Investigating...
✓ Analyzing incident description
✓ Getting pod details
✓ Retrieving pod logs
✓ Determining root cause

Root Cause: Database connection failure
Confidence: High

Evidence:
- Pod status: CrashLoopBackOff (15 restarts)
- Exit code: 1
- Log error: "Failed to connect to database: Connection refused"

Recommendations:
1. Check if PostgreSQL service is running
2. Verify network policies allow traffic
3. Confirm database credentials are correct
```

## Commands

### chat

Start an interactive chat session with the orchestrator.

```bash
sre-orchestrator chat
```

**Features:**
- Natural language interaction
- Real-time investigation progress
- Syntax highlighting for logs and JSON
- Command history (use ↑/↓ arrows)
- Auto-completion

**Special Commands:**
- `/help` - Show available commands
- `/list` - List recent incidents
- `/show <id>` - Show incident details
- `/clear` - Clear screen
- `/exit` or `/quit` - Exit chat session

**Example Session:**

```
$ sre-orchestrator chat

Welcome to SRE Orchestrator CLI
Type '/help' for available commands or describe an incident to investigate.

You: /help

Available commands:
  /help              Show this help message
  /list              List recent incidents
  /show <id>         Show details for an incident
  /clear             Clear the screen
  /exit, /quit       Exit the chat session

You: Pod payment-service is OOMKilled

Orchestrator: Creating incident...
[Investigation output...]

You: /list

Recent Incidents:
1. 123e4567... - Pod payment-service is OOMKilled - completed
2. 234f5678... - API gateway returning 503 errors - completed
3. 345g6789... - Database connection timeout - failed

You: /show 123e4567

Incident: 123e4567-e89b-12d3-a456-426614174000
Status: completed
Created: 2024-01-15 10:23:45
Completed: 2024-01-15 10:24:12

Description: Pod payment-service is OOMKilled

Root Cause: Memory limit too low for batch processing workload
Confidence: High

[Full details...]

You: /exit

Goodbye!
```

### investigate

Perform a one-shot investigation without entering interactive mode.

```bash
sre-orchestrator investigate "Pod auth-service-xyz is crashing"
```

**Options:**
- `--wait` - Wait for investigation to complete (default: true)
- `--no-wait` - Return immediately with incident ID
- `--format` - Output format: `text`, `json`, `yaml` (default: text)
- `--output` - Write output to file instead of stdout

**Examples:**

```bash
# Basic investigation
sre-orchestrator investigate "API returning 500 errors"

# Return immediately without waiting
sre-orchestrator investigate "Pod crashing" --no-wait

# Get JSON output
sre-orchestrator investigate "High memory usage" --format json

# Save to file
sre-orchestrator investigate "Database timeout" --output incident.txt
```

### list

List recent incidents.

```bash
sre-orchestrator list
```

**Options:**
- `--limit` - Number of incidents to show (default: 10)
- `--status` - Filter by status: `pending`, `investigating`, `completed`, `failed`
- `--format` - Output format: `table`, `json`, `yaml` (default: table)

**Examples:**

```bash
# List last 20 incidents
sre-orchestrator list --limit 20

# Show only completed incidents
sre-orchestrator list --status completed

# Get JSON output
sre-orchestrator list --format json
```

**Output:**

```
ID                                   Description                          Status      Created
123e4567-e89b-12d3-a456-426614174000 Pod auth-service-xyz is crashing    completed   2024-01-15 10:23:45
234f5678-f90c-23e4-b567-537725285111 API gateway returning 503 errors    completed   2024-01-15 09:15:30
345g6789-g01d-34f5-c678-648836396222 Database connection timeout         failed      2024-01-15 08:45:12
```

### show

Show detailed information about a specific incident.

```bash
sre-orchestrator show <incident-id>
```

**Options:**
- `--format` - Output format: `text`, `json`, `yaml` (default: text)
- `--output` - Write output to file

**Examples:**

```bash
# Show incident details
sre-orchestrator show 123e4567-e89b-12d3-a456-426614174000

# Get JSON output
sre-orchestrator show 123e4567 --format json

# Save to file
sre-orchestrator show 123e4567 --output incident-report.txt
```

**Output:**

```
Incident: 123e4567-e89b-12d3-a456-426614174000
Status: completed
Created: 2024-01-15 10:23:45
Completed: 2024-01-15 10:24:12
Duration: 27 seconds

Description:
Pod auth-service-xyz is crashing in production namespace

Extracted Entities:
- Pod Name: auth-service-xyz
- Namespace: production
- Error Type: crash

Root Cause:
Database connection failure. The auth-service cannot connect to the PostgreSQL
database at postgresql://db:5432. The database service may be down or there may
be a network connectivity issue.

Confidence: High

Evidence:
1. Pod Status: CrashLoopBackOff
   - Restart count: 15
   - Exit code: 1
   - Last termination reason: Error

2. Pod Logs:
   2024-01-15 10:23:45 ERROR Failed to connect to database
   2024-01-15 10:23:45 ERROR Connection refused: postgresql://db:5432
   2024-01-15 10:23:45 FATAL Application startup failed

Investigation Steps:
1. [10:23:46] Analyzed incident description
2. [10:23:48] Retrieved pod details from Kubernetes
3. [10:23:52] Retrieved pod logs
4. [10:24:10] Determined root cause

Recommendations:
1. Check if the PostgreSQL service is running
2. Verify network policies allow traffic from production namespace to database
3. Confirm database credentials are correct
4. Check if database is accepting connections
```

### config

Manage CLI configuration.

```bash
# View all configuration
sre-orchestrator config show

# Set a configuration value
sre-orchestrator config set <key> <value>

# Get a configuration value
sre-orchestrator config get <key>

# Delete a configuration value
sre-orchestrator config delete <key>
```

**Configuration Keys:**
- `orchestrator-url` - URL of the orchestrator service
- `api-key` - API key for authentication (optional)
- `timeout` - Request timeout in seconds (default: 30)
- `format` - Default output format (default: text)

**Examples:**

```bash
# Set orchestrator URL
sre-orchestrator config set orchestrator-url http://orchestrator.example.com

# Set API key
sre-orchestrator config set api-key sk-abc123...

# Set default timeout
sre-orchestrator config set timeout 60

# View configuration
sre-orchestrator config show

# Get specific value
sre-orchestrator config get orchestrator-url

# Delete API key
sre-orchestrator config delete api-key
```

## Configuration

### Configuration File

The CLI stores configuration in `~/.sre-orchestrator/config.yaml`:

```yaml
orchestrator_url: http://localhost:8000
api_key: your-api-key-here
timeout: 30
format: text
```

### Environment Variables

Configuration can also be set via environment variables:

```bash
export SRE_ORCHESTRATOR_URL=http://orchestrator.example.com
export SRE_ORCHESTRATOR_API_KEY=your-api-key-here
export SRE_ORCHESTRATOR_TIMEOUT=60
```

Environment variables take precedence over configuration file values.

### Command-Line Options

Configuration can be overridden per-command:

```bash
sre-orchestrator --url http://other-orchestrator.com investigate "Pod crashing"
```

**Global Options:**
- `--url` - Orchestrator URL
- `--api-key` - API key
- `--timeout` - Request timeout
- `--verbose` - Enable verbose logging
- `--debug` - Enable debug logging

## Output Formats

### Text Format (Default)

Human-readable output with formatting and colors:

```bash
sre-orchestrator show 123e4567
```

### JSON Format

Machine-readable JSON output:

```bash
sre-orchestrator show 123e4567 --format json
```

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "description": "Pod auth-service-xyz is crashing",
  "status": "completed",
  "created_at": "2024-01-15T10:23:45Z",
  "completed_at": "2024-01-15T10:24:12Z",
  "suggested_root_cause": "Database connection failure",
  "confidence_score": "high",
  "evidence": {
    "pod_details": {...},
    "pod_logs": "..."
  }
}
```

### YAML Format

YAML output for readability:

```bash
sre-orchestrator show 123e4567 --format yaml
```

```yaml
id: 123e4567-e89b-12d3-a456-426614174000
description: Pod auth-service-xyz is crashing
status: completed
created_at: 2024-01-15T10:23:45Z
completed_at: 2024-01-15T10:24:12Z
suggested_root_cause: Database connection failure
confidence_score: high
evidence:
  pod_details: {...}
  pod_logs: "..."
```

## Advanced Usage

### Scripting

Use the CLI in scripts for automated incident investigation:

```bash
#!/bin/bash

# Investigate an incident
INCIDENT_ID=$(sre-orchestrator investigate "Pod crashing" --no-wait --format json | jq -r '.incident_id')

echo "Created incident: $INCIDENT_ID"

# Wait for completion
while true; do
    STATUS=$(sre-orchestrator show $INCIDENT_ID --format json | jq -r '.status')

    if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
        break
    fi

    echo "Status: $STATUS"
    sleep 5
done

# Get results
sre-orchestrator show $INCIDENT_ID --output incident-report.txt

echo "Investigation complete. Report saved to incident-report.txt"
```

### CI/CD Integration

Use the CLI in CI/CD pipelines:

```yaml
# GitHub Actions example
name: Investigate Deployment Issues

on:
  deployment_status:
    types: [failure]

jobs:
  investigate:
    runs-on: ubuntu-latest
    steps:
      - name: Install CLI
        run: pip install sre-orchestrator-cli

      - name: Configure CLI
        run: |
          sre-orchestrator config set orchestrator-url ${{ secrets.ORCHESTRATOR_URL }}
          sre-orchestrator config set api-key ${{ secrets.ORCHESTRATOR_API_KEY }}

      - name: Investigate
        run: |
          sre-orchestrator investigate "Deployment failed for ${{ github.event.deployment.environment }}" \
            --format json \
            --output investigation.json

      - name: Upload Report
        uses: actions/upload-artifact@v2
        with:
          name: investigation-report
          path: investigation.json
```

### Monitoring Integration

Trigger investigations from monitoring alerts:

```python
#!/usr/bin/env python3
"""
Webhook handler for Prometheus Alertmanager.
Triggers SRE Orchestrator investigations for alerts.
"""
from flask import Flask, request
import subprocess
import json

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def handle_alert():
    alert = request.json

    # Extract alert details
    alert_name = alert['commonLabels']['alertname']
    severity = alert['commonLabels']['severity']
    description = alert['commonAnnotations']['description']

    # Create incident description
    incident_description = f"{alert_name}: {description}"

    # Trigger investigation
    result = subprocess.run(
        ['sre-orchestrator', 'investigate', incident_description, '--format', 'json'],
        capture_output=True,
        text=True
    )

    incident = json.loads(result.stdout)

    return {
        'status': 'ok',
        'incident_id': incident['incident_id']
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

## Troubleshooting

### Connection Errors

**Symptom**: `Error: Failed to connect to orchestrator`

**Solutions**:

1. Verify orchestrator URL:
   ```bash
   sre-orchestrator config get orchestrator-url
   ```

2. Test connectivity:
   ```bash
   curl http://your-orchestrator-url/health
   ```

3. Check if orchestrator is running:
   ```bash
   kubectl get pods -n sre -l app=orchestrator
   ```

4. Verify network access:
   ```bash
   # If using port-forward
   kubectl port-forward -n sre svc/orchestrator 8000:80
   ```

### Authentication Errors

**Symptom**: `Error: Unauthorized (401)`

**Solutions**:

1. Set API key:
   ```bash
   sre-orchestrator config set api-key your-api-key-here
   ```

2. Verify API key is correct:
   ```bash
   sre-orchestrator config get api-key
   ```

3. Test with curl:
   ```bash
   curl -H "Authorization: Bearer your-api-key" \
     http://your-orchestrator-url/health
   ```

### Timeout Errors

**Symptom**: `Error: Request timeout`

**Solutions**:

1. Increase timeout:
   ```bash
   sre-orchestrator config set timeout 120
   ```

2. Use `--no-wait` for long investigations:
   ```bash
   sre-orchestrator investigate "Complex issue" --no-wait
   ```

3. Check investigation status separately:
   ```bash
   sre-orchestrator show <incident-id>
   ```

### Installation Issues

**Symptom**: `Command not found: sre-orchestrator`

**Solutions**:

1. Verify installation:
   ```bash
   pip list | grep sre-orchestrator
   ```

2. Check PATH:
   ```bash
   echo $PATH
   ```

3. Reinstall with pipx:
   ```bash
   pipx install --force sre-orchestrator-cli
   ```

4. Use full path:
   ```bash
   python -m sre_orchestrator_cli.main --help
   ```

## Tips and Tricks

### 1. Use Aliases

Create shell aliases for common commands:

```bash
# Add to ~/.bashrc or ~/.zshrc
alias sre='sre-orchestrator'
alias sre-chat='sre-orchestrator chat'
alias sre-list='sre-orchestrator list'
```

### 2. Tab Completion

Enable tab completion (bash):

```bash
eval "$(_SRE_ORCHESTRATOR_COMPLETE=bash_source sre-orchestrator)"
```

Enable tab completion (zsh):

```bash
eval "$(_SRE_ORCHESTRATOR_COMPLETE=zsh_source sre-orchestrator)"
```

### 3. Output Piping

Pipe output to other tools:

```bash
# Search incidents
sre-orchestrator list --format json | jq '.[] | select(.status=="failed")'

# Count incidents by status
sre-orchestrator list --format json | jq -r '.[].status' | sort | uniq -c

# Extract root causes
sre-orchestrator list --format json | jq -r '.[].suggested_root_cause'
```

### 4. Quick Investigation

Create a function for quick investigations:

```bash
# Add to ~/.bashrc or ~/.zshrc
investigate() {
    sre-orchestrator investigate "$*" --format text | less
}

# Usage
investigate Pod auth-service is crashing
```

### 5. Watch Mode

Monitor investigation progress:

```bash
# Create incident
INCIDENT_ID=$(sre-orchestrator investigate "Pod issue" --no-wait --format json | jq -r '.incident_id')

# Watch status
watch -n 2 "sre-orchestrator show $INCIDENT_ID --format json | jq -r '.status'"
```

## Best Practices

### 1. Descriptive Incident Descriptions

Provide clear, detailed descriptions:

✅ Good:
```
Pod auth-service-xyz in production namespace is in CrashLoopBackOff with exit code 1
```

❌ Bad:
```
Pod broken
```

### 2. Include Context

Add relevant context to help the investigation:

```
API gateway returning 503 errors when calling user-service. Started after deployment at 10:00 AM.
```

### 3. Use Structured Queries

Structure your queries for better results:

```
Service: payment-service
Namespace: prod
Issue: High memory usage leading to OOMKilled
Frequency: Every 2 hours during batch processing
```

### 4. Review Investigation Steps

Always review the investigation steps to understand the agent's reasoning:

```bash
sre-orchestrator show <incident-id> | grep "Investigation Steps" -A 20
```

### 5. Save Important Reports

Save investigation reports for documentation:

```bash
sre-orchestrator show <incident-id> --output reports/incident-$(date +%Y%m%d-%H%M%S).txt
```

## Getting Help

### Command Help

Get help for any command:

```bash
sre-orchestrator --help
sre-orchestrator investigate --help
sre-orchestrator config --help
```

### Verbose Output

Enable verbose logging for debugging:

```bash
sre-orchestrator --verbose investigate "Pod issue"
```

### Debug Mode

Enable debug mode for detailed logs:

```bash
sre-orchestrator --debug investigate "Pod issue"
```

### Report Issues

Report bugs or request features:
- GitHub Issues: https://github.com/your-org/sre-orchestrator/issues
- Email: support@example.com

## Next Steps

1. **Configure the CLI**: Set up your orchestrator URL and API key
2. **Try the chat mode**: Start an interactive session
3. **Investigate an incident**: Test with a real incident
4. **Explore output formats**: Try JSON and YAML formats
5. **Integrate with tools**: Use the CLI in scripts and CI/CD

## Additional Resources

- [Architecture Documentation](./architecture.md)
- [LangGraph Workflow Guide](./langgraph-workflow.md)
- [MCP Integration Guide](./mcp-integration.md)
- [API Documentation](./rest-api-spec.md)
