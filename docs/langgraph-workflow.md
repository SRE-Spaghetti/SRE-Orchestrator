# LangGraph Workflow Documentation

## Overview

The SRE Orchestrator uses LangGraph's ReAct (Reasoning + Acting) agent pattern to autonomously investigate incidents. This document explains how the workflow operates, how MCP tools are integrated, and provides examples of agent investigations.

## ReAct Agent Pattern

The ReAct pattern combines two key capabilities:

1. **Reasoning**: The LLM analyzes the situation and decides what to do next
2. **Acting**: The agent executes tools to gather information

This creates an autonomous investigation loop where the agent:
- Analyzes the incident description
- Determines what information is needed
- Selects and executes appropriate tools
- Interprets the results
- Continues until sufficient evidence is gathered
- Determines the root cause with confidence level

## Architecture

```mermaid
graph TD
    A[Incident Created] --> B[Initialize Agent]
    B --> C[LLM Reasoning]
    C --> D{Need More Info?}
    D -->|Yes| E[Select Tool]
    E --> F[Execute MCP Tool]
    F --> G[Process Results]
    G --> C
    D -->|No| H[Determine Root Cause]
    H --> I[Update Incident]
    I --> J[Investigation Complete]
```

## Agent Components

### System Prompt

The agent is guided by a system prompt that defines its role and behavior:

```python
system_prompt = """You are an expert SRE assistant investigating production incidents.

When given an incident description, follow this process:
1. Analyze the description to understand the problem
2. Use available Kubernetes tools to gather evidence:
   - Get pod details and status
   - Retrieve pod logs
   - Check resource usage and limits
   - View recent events
3. Correlate the evidence to identify patterns
4. Determine the root cause with confidence level
5. Provide actionable recommendations

Always explain your reasoning and cite specific evidence from the tools."""
```

### LLM Configuration

The agent uses LangChain's `init_chat_model` for flexible LLM provider support:

```python
model = init_chat_model(
    model=os.getenv("LLM_MODEL", "gpt-4"),
    base_url=os.getenv("LLM_BASE_URL"),
    api_key=os.getenv("LLM_API_KEY")
)
```

Supported providers:
- OpenAI (GPT-4, GPT-3.5)
- Google Gemini (via OpenAI-compatible proxy)
- Local LLMs (Ollama, LM Studio, etc.)

### Tool Integration

Tools are provided by MCP servers and automatically converted to LangChain format:

```python
# Initialize MCP client
mcp_client = MultiServerMCPClient(mcp_config)

# Get all tools from all connected MCP servers
tools = await mcp_client.get_tools()

# Create ReAct agent with tools
agent = create_react_agent(
    model=model,
    tools=tools,
    state_modifier=system_prompt
)
```

## MCP Tool Integration

### Tool Discovery

When the orchestrator starts, it connects to all configured MCP servers and discovers available tools:

```python
# From mcp_config.yaml
mcp_servers:
  kubernetes:
    url: "http://kubernetes-mcp-server:8080/mcp"
    transport: "streamable_http"
  prometheus:
    command: "python"
    args: ["/path/to/prometheus_server.py"]
    transport: "stdio"
```

Each MCP server exposes tools that the agent can use:

**Kubernetes MCP Tools:**
- `get_pod_details`: Get pod status, conditions, and configuration
- `get_pod_logs`: Retrieve pod logs with optional tail and timestamps
- `get_pod_events`: Get recent events for a pod
- `list_pods`: List pods in a namespace with filtering

**Prometheus MCP Tools:**
- `query_metrics`: Execute PromQL queries
- `get_alerts`: Retrieve active alerts
- `get_metric_history`: Get time-series data for a metric

### Tool Execution Flow

```mermaid
sequenceDiagram
    participant Agent as LangGraph Agent
    participant LLM as LLM
    participant MCPMgr as MCP Tool Manager
    participant MCP as MCP Server

    Agent->>LLM: Analyze incident
    LLM-->>Agent: Decision: Use get_pod_details
    Agent->>MCPMgr: Execute tool with params
    MCPMgr->>MCP: Call MCP tool
    MCP-->>MCPMgr: Return results
    MCPMgr-->>Agent: Tool output
    Agent->>LLM: Analyze results
    LLM-->>Agent: Next action or conclusion
```

### Tool Error Handling

The agent handles tool failures gracefully:

```python
try:
    result = await tool.execute(params)
except MCPToolError as e:
    # Log error
    logger.error(f"Tool execution failed: {e}")
    # Agent continues with available information
    # LLM decides whether to retry or use alternative approach
```

## Investigation Examples

### Example 1: CrashLoopBackOff Investigation

**Incident Description:**
```
Pod auth-service-xyz is in CrashLoopBackOff in namespace production
```

**Agent Investigation Steps:**

1. **Initial Reasoning**
   ```
   LLM: "The pod is in CrashLoopBackOff, which means it's repeatedly crashing.
   I need to check the pod details to understand the current state and then
   examine the logs to see why it's crashing."
   ```

2. **Tool: get_pod_details**
   ```python
   tool_call = {
       "name": "get_pod_details",
       "arguments": {
           "namespace": "production",
           "pod_name": "auth-service-xyz"
       }
   }
   ```

   **Result:**
   ```json
   {
       "status": "CrashLoopBackOff",
       "restart_count": 15,
       "last_state": {
           "terminated": {
               "exit_code": 1,
               "reason": "Error"
           }
       },
       "containers": [{
           "name": "auth-service",
           "image": "auth-service:v2.1.0",
           "ready": false
       }]
   }
   ```

3. **Reasoning After Tool Result**
   ```
   LLM: "The pod has restarted 15 times with exit code 1. This indicates an
   application error. I need to check the logs to see the specific error message."
   ```

4. **Tool: get_pod_logs**
   ```python
   tool_call = {
       "name": "get_pod_logs",
       "arguments": {
           "namespace": "production",
           "pod_name": "auth-service-xyz",
           "tail": 50
       }
   }
   ```

   **Result:**
   ```
   2024-01-15 10:23:45 ERROR Failed to connect to database
   2024-01-15 10:23:45 ERROR Connection refused: postgresql://db:5432
   2024-01-15 10:23:45 FATAL Application startup failed
   ```

5. **Final Analysis**
   ```
   LLM: "Based on the evidence:
   1. Pod is crashing with exit code 1
   2. Logs show database connection failure
   3. Error: Connection refused to postgresql://db:5432

   Root Cause: The auth-service cannot connect to the PostgreSQL database.
   The database service may be down, or there may be a network connectivity issue.

   Confidence: High

   Recommendations:
   1. Check if the PostgreSQL service is running
   2. Verify network policies allow traffic from production namespace to database
   3. Confirm database credentials are correct
   4. Check if database is accepting connections"
   ```

### Example 2: OOMKilled Investigation

**Incident Description:**
```
Payment service pods are being OOMKilled in the prod namespace
```

**Agent Investigation Steps:**

1. **Initial Reasoning**
   ```
   LLM: "OOMKilled means the pod exceeded its memory limit. I need to check
   the pod details to see the memory limits and usage, then examine logs to
   understand what caused the high memory usage."
   ```

2. **Tool: list_pods**
   ```python
   tool_call = {
       "name": "list_pods",
       "arguments": {
           "namespace": "prod",
           "label_selector": "app=payment-service"
       }
   }
   ```

   **Result:**
   ```json
   {
       "pods": [
           {
               "name": "payment-service-abc",
               "status": "Running",
               "restart_count": 3,
               "last_state": {
                   "terminated": {
                       "reason": "OOMKilled"
                   }
               }
           }
       ]
   }
   ```

3. **Tool: get_pod_details**
   ```python
   tool_call = {
       "name": "get_pod_details",
       "arguments": {
           "namespace": "prod",
           "pod_name": "payment-service-abc"
       }
   }
   ```

   **Result:**
   ```json
   {
       "resources": {
           "limits": {
               "memory": "512Mi"
           },
           "requests": {
               "memory": "256Mi"
           }
       },
       "status": {
           "container_statuses": [{
               "last_state": {
                   "terminated": {
                       "reason": "OOMKilled",
                       "exit_code": 137
                   }
               }
           }]
       }
   }
   ```

4. **Tool: get_pod_logs**
   ```python
   tool_call = {
       "name": "get_pod_logs",
       "arguments": {
           "namespace": "prod",
           "pod_name": "payment-service-abc",
           "previous": true,
           "tail": 100
       }
   }
   ```

   **Result:**
   ```
   2024-01-15 14:30:12 INFO Processing batch payment job
   2024-01-15 14:30:15 INFO Loading 50000 transactions into memory
   2024-01-15 14:30:18 WARN Memory usage: 480MB
   2024-01-15 14:30:20 WARN Memory usage: 510MB
   ```

5. **Final Analysis**
   ```
   LLM: "Based on the evidence:
   1. Pod has memory limit of 512Mi
   2. Pod was OOMKilled (exit code 137)
   3. Logs show batch job loading 50000 transactions
   4. Memory usage reached 510MB before termination

   Root Cause: The payment service's batch processing job loads too much data
   into memory, exceeding the 512Mi limit. The memory limit is insufficient
   for the workload.

   Confidence: High

   Recommendations:
   1. Increase memory limit to at least 1Gi
   2. Optimize batch processing to use streaming instead of loading all data
   3. Implement pagination for large transaction sets
   4. Add memory usage monitoring and alerts"
   ```

### Example 3: Network Connectivity Issue

**Incident Description:**
```
API gateway is returning 503 errors when calling user-service
```

**Agent Investigation Steps:**

1. **Initial Reasoning**
   ```
   LLM: "503 errors typically indicate service unavailability. I need to check
   if the user-service pods are running and healthy, then examine the API
   gateway logs to see the specific error."
   ```

2. **Tool: list_pods**
   ```python
   tool_call = {
       "name": "list_pods",
       "arguments": {
           "namespace": "default",
           "label_selector": "app=user-service"
       }
   }
   ```

   **Result:**
   ```json
   {
       "pods": [
           {
               "name": "user-service-123",
               "status": "Running",
               "ready": "1/1"
           },
           {
               "name": "user-service-456",
               "status": "Running",
               "ready": "1/1"
           }
       ]
   }
   ```

3. **Reasoning**
   ```
   LLM: "The user-service pods are running and ready. The issue might be with
   the API gateway's ability to reach them. Let me check the API gateway logs."
   ```

4. **Tool: get_pod_logs**
   ```python
   tool_call = {
       "name": "get_pod_logs",
       "arguments": {
           "namespace": "default",
           "label_selector": "app=api-gateway",
           "tail": 50
       }
   }
   ```

   **Result:**
   ```
   2024-01-15 16:45:23 ERROR Failed to connect to user-service.default.svc.cluster.local:8080
   2024-01-15 16:45:23 ERROR Connection timeout after 5s
   2024-01-15 16:45:23 WARN Returning 503 Service Unavailable
   ```

5. **Tool: get_pod_events**
   ```python
   tool_call = {
       "name": "get_pod_events",
       "arguments": {
           "namespace": "default",
           "pod_name": "user-service-123"
       }
   }
   ```

   **Result:**
   ```
   No recent events found
   ```

6. **Final Analysis**
   ```
   LLM: "Based on the evidence:
   1. User-service pods are running and ready
   2. API gateway cannot connect to user-service
   3. Connection timeout after 5 seconds
   4. No pod events indicating issues

   Root Cause: Network connectivity issue between API gateway and user-service.
   The pods are healthy but cannot communicate. This is likely a NetworkPolicy
   or Service configuration issue.

   Confidence: Medium (would need to check NetworkPolicies and Service config)

   Recommendations:
   1. Verify Service 'user-service' exists and has correct selector
   2. Check NetworkPolicies in default namespace
   3. Verify Service endpoints are populated
   4. Test connectivity from API gateway pod using curl/nc
   5. Check if Service port matches container port"
   ```

## Agent Configuration

### Environment Variables

```bash
# LLM Configuration
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4

# MCP Configuration
MCP_CONFIG_PATH=/app/mcp_config.yaml
```

### MCP Configuration File

```yaml
mcp_servers:
  kubernetes:
    url: "http://kubernetes-mcp-server:8080/mcp"
    transport: "streamable_http"
    headers:
      Authorization: "Bearer ${K8S_MCP_TOKEN}"

  prometheus:
    url: "http://prometheus-mcp-server:9090/mcp"
    transport: "streamable_http"
```

## Monitoring and Observability

### Agent Metrics

The system tracks key metrics for agent performance:

```python
# Workflow execution time
workflow_execution_duration_seconds

# Tool execution time
mcp_tool_execution_duration_seconds{tool_name="get_pod_details"}

# LLM call metrics
llm_request_duration_seconds{operation="reasoning"}
llm_tokens_used_total{operation="reasoning"}

# Investigation outcomes
investigation_completed_total{status="success"}
investigation_completed_total{status="failed"}
```

### Logging

All agent actions are logged with structured context:

```json
{
  "timestamp": "2024-01-15T10:23:45Z",
  "level": "INFO",
  "incident_id": "123e4567-e89b-12d3-a456-426614174000",
  "event": "tool_executed",
  "tool_name": "get_pod_details",
  "tool_args": {
    "namespace": "production",
    "pod_name": "auth-service-xyz"
  },
  "execution_time_ms": 234,
  "success": true
}
```

## Best Practices

### System Prompt Design

1. **Be Specific**: Clearly define the agent's role and responsibilities
2. **Provide Structure**: Outline the investigation process step-by-step
3. **Set Expectations**: Explain what constitutes a complete investigation
4. **Encourage Transparency**: Ask the agent to explain its reasoning

### Tool Design

1. **Single Responsibility**: Each tool should do one thing well
2. **Clear Parameters**: Use descriptive parameter names and types
3. **Comprehensive Output**: Return all relevant information
4. **Error Messages**: Provide actionable error messages

### Investigation Quality

1. **Evidence-Based**: All conclusions should cite specific evidence
2. **Confidence Levels**: Always include confidence assessment
3. **Actionable Recommendations**: Provide specific next steps
4. **Transparent Reasoning**: Log all decision points

## Troubleshooting

### Agent Not Using Tools

**Symptom**: Agent provides generic responses without using tools

**Possible Causes**:
1. Tools not properly registered with agent
2. System prompt doesn't encourage tool use
3. LLM model doesn't support function calling

**Solutions**:
1. Verify tools are loaded: Check MCP connection logs
2. Update system prompt to explicitly mention available tools
3. Use a model that supports function calling (GPT-4, GPT-3.5-turbo)

### Tool Execution Failures

**Symptom**: Tools fail to execute or return errors

**Possible Causes**:
1. MCP server not reachable
2. Invalid tool parameters
3. Insufficient permissions

**Solutions**:
1. Check MCP server health endpoints
2. Validate tool parameters match schema
3. Verify service account permissions

### Incomplete Investigations

**Symptom**: Agent stops before gathering sufficient evidence

**Possible Causes**:
1. Token limit reached
2. Agent thinks it has enough information
3. Tool execution timeout

**Solutions**:
1. Increase max_tokens in LLM config
2. Adjust system prompt to require more evidence
3. Increase tool execution timeout

## Future Enhancements

### Planned Features

1. **Multi-Agent Collaboration**: Multiple specialized agents working together
2. **Investigation Checkpointing**: Save and resume long-running investigations
3. **Learning from Past Incidents**: Use historical data to improve investigations
4. **Custom Tool Development**: Framework for creating domain-specific tools
5. **Streaming Responses**: Real-time investigation progress updates

### Extensibility

The ReAct agent pattern is highly extensible:

- **New MCP Servers**: Just add to configuration, tools automatically available
- **Custom Prompts**: Modify system prompt for different investigation styles
- **Alternative LLMs**: Swap LLM provider via environment variables
- **Tool Filtering**: Selectively enable/disable tools per investigation type
