# Extending the Investigation Graph

## Overview

The native LangGraph StateGraph implementation provides a flexible foundation for extending the investigation workflow. This guide explains how to add new nodes, implement conditional edges, extend the state schema, and provides practical examples for common extensions.

## Table of Contents

- [Adding New Nodes](#adding-new-nodes)
- [Adding Conditional Edges](#adding-conditional-edges)
- [Extending State Schema](#extending-state-schema)
- [Example: Validation Node](#example-validation-node)
- [Example: Human-in-the-Loop](#example-human-in-the-loop)
- [Example: Multi-Phase Investigation](#example-multi-phase-investigation)
- [Best Practices](#best-practices)

## Adding New Nodes

Nodes are the building blocks of the LangGraph workflow. Each node is an async function that takes the current state and returns a partial state update.

### Node Function Signature

```python
async def my_custom_node(state: InvestigationState) -> InvestigationState:
    """
    Custom node that performs some operation.

    Args:
        state: Current investigation state

    Returns:
        Partial state update (only fields that changed)
    """
    # Extract information from state
    correlation_id = state.get("correlation_id")
    incident_id = state.get("incident_id")

    # Perform node logic
    # ...

    # Return partial state update
    return {
        "investigation_status": "validated",
        # Only include fields that changed
    }
```

### Adding Node to Graph

```python
from langgraph.graph import StateGraph, END

# Create graph
graph = StateGraph(InvestigationState)

# Add your custom node
graph.add_node("my_custom_node", my_custom_node)

# Connect it to other nodes
graph.add_edge("agent", "my_custom_node")
graph.add_edge("my_custom_node", "tools")
```

### Node Best Practices

1. **Single Responsibility**: Each node should do one thing well
2. **Logging**: Include comprehensive logging with correlation ID
3. **Error Handling**: Wrap logic in try/except and update state on errors
4. **Partial Updates**: Only return fields that changed
5. **Type Hints**: Use proper type hints for state input/output
6. **Documentation**: Add clear docstrings explaining node purpose

## Adding Conditional Edges

Conditional edges allow dynamic routing based on state. They use a routing function to determine the next node.

### Routing Function Signature

```python
from typing import Literal

def my_routing_function(state: InvestigationState) -> Literal["option1", "option2", "end"]:
    """
    Routing function to determine next step.

    Args:
        state: Current investigation state

    Returns:
        String indicating which edge to follow
    """
    # Examine state to make routing decision
    if state.get("needs_validation"):
        return "option1"
    elif state.get("needs_approval"):
        return "option2"
    else:
        return "end"
```

### Adding Conditional Edge to Graph

```python
# Add conditional edge from a node
graph.add_conditional_edges(
    "my_node",              # Source node
    my_routing_function,    # Routing function
    {
        "option1": "validation_node",  # Map routing result to target node
        "option2": "approval_node",
        "end": END                      # Special END node
    }
)
```

### Routing Best Practices

1. **Use Literal Types**: Define all possible return values with `Literal`
2. **Log Decisions**: Log routing decisions for debugging
3. **Clear Logic**: Keep routing logic simple and understandable
4. **Handle All Cases**: Ensure all possible states are handled
5. **Default Behavior**: Provide sensible default routing

## Extending State Schema

The state schema can be extended to track additional information throughout the workflow.

### Adding New Fields

```python
from typing import TypedDict, Annotated, Sequence, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class ExtendedInvestigationState(TypedDict):
    """Extended state schema with additional fields."""

    # Original fields
    messages: Annotated[Sequence[BaseMessage], add_messages]
    incident_id: str
    correlation_id: str
    investigation_status: str

    # New fields
    iteration_count: int
    validation_passed: bool
    confidence_score: float
    investigation_phase: str  # "initial", "deep_dive", "validation"
    human_approval_required: bool
    error_message: Optional[str]
```

### Using Extended State

```python
# Create graph with extended state
graph = StateGraph(ExtendedInvestigationState)

# Nodes can now access and update new fields
async def my_node(state: ExtendedInvestigationState) -> ExtendedInvestigationState:
    iteration_count = state.get("iteration_count", 0)

    # Update new fields
    return {
        "iteration_count": iteration_count + 1,
        "investigation_phase": "deep_dive"
    }
```

### State Extension Best Practices

1. **Optional Fields**: Make new fields optional with defaults
2. **Backward Compatibility**: Ensure existing nodes work with new schema
3. **Type Safety**: Use proper type hints for all fields
4. **Documentation**: Document purpose of each new field
5. **Initialization**: Provide sensible defaults in initial state

## Example: Validation Node

This example adds a validation node that checks investigation quality before completion.

### Implementation

```python
async def validation_node(state: InvestigationState) -> InvestigationState:
    """
    Validate investigation results before completing.

    Checks:
    - Root cause is identified
    - Confidence level is acceptable
    - Sufficient evidence is gathered

    Args:
        state: Current investigation state

    Returns:
        Updated state with validation status
    """
    correlation_id = state.get("correlation_id")
    incident_id = state.get("incident_id")

    logger.info(
        "Validation node executing",
        extra={
            "correlation_id": correlation_id,
            "incident_id": incident_id
        }
    )

    messages = state["messages"]
    last_message = messages[-1] if messages else None

    if not last_message or not hasattr(last_message, "content"):
        logger.warning(
            "Validation failed: No final message",
            extra={"correlation_id": correlation_id, "incident_id": incident_id}
        )
        return {
            "investigation_status": "validation_failed",
            "validation_passed": False
        }

    content = last_message.content

    # Check for root cause
    has_root_cause = "ROOT CAUSE:" in content.upper()

    # Check for confidence level
    has_confidence = "CONFIDENCE:" in content.upper()

    # Check for evidence
    has_evidence = "EVIDENCE:" in content.upper()

    # Check for recommendations
    has_recommendations = "RECOMMENDATIONS:" in content.upper()

    validation_passed = all([
        has_root_cause,
        has_confidence,
        has_evidence,
        has_recommendations
    ])

    if validation_passed:
        logger.info(
            "Validation passed",
            extra={
                "correlation_id": correlation_id,
                "incident_id": incident_id
            }
        )
        return {
            "investigation_status": "validated",
            "validation_passed": True
        }
    else:
        logger.warning(
            "Validation failed: Missing required sections",
            extra={
                "correlation_id": correlation_id,
                "incident_id": incident_id,
                "has_root_cause": has_root_cause,
                "has_confidence": has_confidence,
                "has_evidence": has_evidence,
                "has_recommendations": has_recommendations
            }
        )
        return {
            "investigation_status": "validation_failed",
            "validation_passed": False
        }
```

### Routing with Validation

```python
def should_continue_with_validation(state: InvestigationState) -> Literal["tools", "validate", "end"]:
    """
    Enhanced routing function that includes validation step.

    Args:
        state: Current investigation state

    Returns:
        "tools" to execute tools, "validate" to validate results, or "end" to finish
    """
    messages = state["messages"]
    last_message = messages[-1]

    # Check if the last message has tool calls
    has_tool_calls = hasattr(last_message, "tool_calls") and bool(last_message.tool_calls)

    if has_tool_calls:
        return "tools"

    # Check if validation already failed (retry investigation)
    if state.get("validation_passed") is False:
        return "end"  # Don't retry indefinitely

    # If no tool calls and not yet validated, go to validation
    if state.get("validation_passed") is None:
        return "validate"

    # Validation passed, end investigation
    return "end"
```

### Graph Construction with Validation

```python
# Create graph
graph = StateGraph(InvestigationState)

# Add nodes
graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)
graph.add_node("validation", validation_node)

# Add conditional edges
graph.add_conditional_edges(
    "agent",
    should_continue_with_validation,
    {
        "tools": "tools",
        "validate": "validation",
        "end": END
    }
)

# Tools go back to agent
graph.add_edge("tools", "agent")

# Validation can either end or go back to agent for retry
graph.add_conditional_edges(
    "validation",
    lambda state: "end" if state.get("validation_passed") else "agent",
    {
        "end": END,
        "agent": "agent"
    }
)

# Set entry point
graph.set_entry_point("agent")

# Compile
agent = graph.compile()
```

## Example: Human-in-the-Loop

This example adds a human approval step before completing the investigation.

### Extended State Schema

```python
class HumanApprovalState(TypedDict):
    """State schema with human approval fields."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    incident_id: str
    correlation_id: str
    investigation_status: str

    # Human approval fields
    approval_requested: bool
    approval_granted: Optional[bool]
    approval_timestamp: Optional[str]
    approver_id: Optional[str]
```

### Human Approval Node

```python
import asyncio
from datetime import datetime

async def human_approval_node(state: HumanApprovalState) -> HumanApprovalState:
    """
    Request human approval for investigation results.

    This node:
    1. Sends notification to human approver
    2. Waits for approval response
    3. Updates state with approval status

    Args:
        state: Current investigation state

    Returns:
        Updated state with approval status
    """
    correlation_id = state.get("correlation_id")
    incident_id = state.get("incident_id")

    logger.info(
        "Requesting human approval",
        extra={
            "correlation_id": correlation_id,
            "incident_id": incident_id
        }
    )

    # Send notification to human approver
    # This could be via Slack, email, webhook, etc.
    await send_approval_request(
        incident_id=incident_id,
        correlation_id=correlation_id,
        investigation_summary=extract_summary(state["messages"])
    )

    # Wait for approval (with timeout)
    # In a real implementation, this would use a callback mechanism
    # rather than blocking
    try:
        approval_response = await wait_for_approval(
            incident_id=incident_id,
            timeout_seconds=300  # 5 minutes
        )

        logger.info(
            "Human approval received",
            extra={
                "correlation_id": correlation_id,
                "incident_id": incident_id,
                "approved": approval_response["approved"],
                "approver_id": approval_response["approver_id"]
            }
        )

        return {
            "approval_granted": approval_response["approved"],
            "approval_timestamp": datetime.utcnow().isoformat(),
            "approver_id": approval_response["approver_id"],
            "investigation_status": "approved" if approval_response["approved"] else "rejected"
        }

    except TimeoutError:
        logger.warning(
            "Human approval timeout",
            extra={
                "correlation_id": correlation_id,
                "incident_id": incident_id
            }
        )

        return {
            "approval_granted": False,
            "investigation_status": "approval_timeout"
        }


async def send_approval_request(incident_id: str, correlation_id: str, investigation_summary: str):
    """Send approval request to human approver."""
    # Implementation depends on notification system
    # Example: Slack, email, webhook, etc.
    pass


async def wait_for_approval(incident_id: str, timeout_seconds: int) -> dict:
    """Wait for human approval response."""
    # Implementation depends on callback mechanism
    # Example: polling database, webhook endpoint, message queue, etc.
    pass


def extract_summary(messages: List[BaseMessage]) -> str:
    """Extract investigation summary from messages."""
    # Get last AI message
    for msg in reversed(messages):
        if hasattr(msg, "content") and msg.content:
            return msg.content[:500]  # First 500 chars
    return "No summary available"
```

### Graph with Human Approval

```python
# Create graph with extended state
graph = StateGraph(HumanApprovalState)

# Add nodes
graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)
graph.add_node("validation", validation_node)
graph.add_node("human_approval", human_approval_node)

# Add edges
graph.add_conditional_edges(
    "agent",
    should_continue_with_validation,
    {
        "tools": "tools",
        "validate": "validation",
        "end": END
    }
)

graph.add_edge("tools", "agent")

# After validation, go to human approval
graph.add_conditional_edges(
    "validation",
    lambda state: "human_approval" if state.get("validation_passed") else "end",
    {
        "human_approval": "human_approval",
        "end": END
    }
)

# After human approval, end
graph.add_edge("human_approval", END)

# Set entry point
graph.set_entry_point("agent")

# Compile
agent = graph.compile()
```

## Example: Multi-Phase Investigation

This example implements a multi-phase investigation with initial triage, deep dive, and final analysis.

### Extended State Schema

```python
class MultiPhaseState(TypedDict):
    """State schema for multi-phase investigation."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    incident_id: str
    correlation_id: str
    investigation_status: str

    # Multi-phase fields
    investigation_phase: str  # "triage", "deep_dive", "analysis"
    iteration_count: int
    max_iterations_per_phase: int
    triage_complete: bool
    deep_dive_complete: bool
```

### Phase-Specific Nodes

```python
async def triage_agent_node(state: MultiPhaseState) -> MultiPhaseState:
    """
    Triage phase: Quick assessment of the incident.

    Goals:
    - Identify incident type
    - Determine severity
    - Select relevant tools for deep dive
    """
    correlation_id = state.get("correlation_id")
    incident_id = state.get("incident_id")

    logger.info(
        "Triage phase executing",
        extra={
            "correlation_id": correlation_id,
            "incident_id": incident_id,
            "phase": "triage"
        }
    )

    # Use a triage-specific prompt
    triage_prompt = """You are performing initial triage of an incident.

    Your goals:
    1. Quickly identify the incident type (pod crash, OOM, network issue, etc.)
    2. Assess severity (critical, high, medium, low)
    3. Identify which tools to use for deeper investigation

    Be concise and focus on quick assessment."""

    # Create triage-specific model
    triage_model = model_with_tools.bind(
        system_message=triage_prompt,
        max_tokens=500  # Shorter responses for triage
    )

    response = await triage_model.ainvoke(state["messages"])

    return {
        "messages": [response],
        "investigation_phase": "triage",
        "iteration_count": state.get("iteration_count", 0) + 1
    }


async def deep_dive_agent_node(state: MultiPhaseState) -> MultiPhaseState:
    """
    Deep dive phase: Detailed investigation.

    Goals:
    - Gather comprehensive evidence
    - Execute multiple tools
    - Build detailed understanding
    """
    correlation_id = state.get("correlation_id")
    incident_id = state.get("incident_id")

    logger.info(
        "Deep dive phase executing",
        extra={
            "correlation_id": correlation_id,
            "incident_id": incident_id,
            "phase": "deep_dive"
        }
    )

    deep_dive_prompt = """You are performing deep investigation of an incident.

    Your goals:
    1. Gather comprehensive evidence using available tools
    2. Examine logs, metrics, and events in detail
    3. Identify patterns and correlations
    4. Build a complete picture of what happened

    Be thorough and use multiple tools to gather evidence."""

    deep_dive_model = model_with_tools.bind(
        system_message=deep_dive_prompt,
        max_tokens=2000
    )

    response = await deep_dive_model.ainvoke(state["messages"])

    return {
        "messages": [response],
        "investigation_phase": "deep_dive",
        "iteration_count": state.get("iteration_count", 0) + 1
    }


async def analysis_agent_node(state: MultiPhaseState) -> MultiPhaseState:
    """
    Analysis phase: Final root cause determination.

    Goals:
    - Synthesize all evidence
    - Determine root cause
    - Provide recommendations
    """
    correlation_id = state.get("correlation_id")
    incident_id = state.get("incident_id")

    logger.info(
        "Analysis phase executing",
        extra={
            "correlation_id": correlation_id,
            "incident_id": incident_id,
            "phase": "analysis"
        }
    )

    analysis_prompt = """You are performing final analysis of an incident.

    Your goals:
    1. Synthesize all evidence gathered
    2. Determine the root cause with confidence level
    3. Provide actionable recommendations
    4. Format your response with ROOT CAUSE, CONFIDENCE, EVIDENCE, and RECOMMENDATIONS sections

    Be decisive and provide clear conclusions."""

    analysis_model = model_with_tools.bind(
        system_message=analysis_prompt,
        max_tokens=1500
    )

    response = await analysis_model.ainvoke(state["messages"])

    return {
        "messages": [response],
        "investigation_phase": "analysis",
        "investigation_status": "completed"
    }
```

### Multi-Phase Routing

```python
def multi_phase_routing(state: MultiPhaseState) -> Literal["tools", "next_phase", "end"]:
    """
    Route between phases based on state.

    Args:
        state: Current investigation state

    Returns:
        "tools" to execute tools, "next_phase" to advance phase, or "end" to finish
    """
    phase = state.get("investigation_phase", "triage")
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations_per_phase", 3)

    messages = state["messages"]
    last_message = messages[-1] if messages else None

    # Check if agent requested tools
    has_tool_calls = (
        last_message and
        hasattr(last_message, "tool_calls") and
        bool(last_message.tool_calls)
    )

    if has_tool_calls:
        return "tools"

    # Check if we should advance to next phase
    if phase == "triage" and iteration_count >= 2:
        return "next_phase"  # Move to deep_dive

    if phase == "deep_dive" and iteration_count >= max_iterations:
        return "next_phase"  # Move to analysis

    if phase == "analysis":
        return "end"  # Investigation complete

    # Continue in current phase
    return "tools" if has_tool_calls else "next_phase"


def phase_transition(state: MultiPhaseState) -> str:
    """
    Determine which phase to transition to.

    Args:
        state: Current investigation state

    Returns:
        Next phase node name
    """
    phase = state.get("investigation_phase", "triage")

    if phase == "triage":
        return "deep_dive_agent"
    elif phase == "deep_dive":
        return "analysis_agent"
    else:
        return "end"
```

### Multi-Phase Graph Construction

```python
# Create graph
graph = StateGraph(MultiPhaseState)

# Add phase-specific agent nodes
graph.add_node("triage_agent", triage_agent_node)
graph.add_node("deep_dive_agent", deep_dive_agent_node)
graph.add_node("analysis_agent", analysis_agent_node)

# Add tool node (shared across phases)
graph.add_node("tools", tool_node)

# Set entry point to triage
graph.set_entry_point("triage_agent")

# Add conditional edges from triage agent
graph.add_conditional_edges(
    "triage_agent",
    multi_phase_routing,
    {
        "tools": "tools",
        "next_phase": "deep_dive_agent",
        "end": END
    }
)

# Add conditional edges from deep dive agent
graph.add_conditional_edges(
    "deep_dive_agent",
    multi_phase_routing,
    {
        "tools": "tools",
        "next_phase": "analysis_agent",
        "end": END
    }
)

# Add conditional edges from analysis agent
graph.add_conditional_edges(
    "analysis_agent",
    multi_phase_routing,
    {
        "tools": "tools",
        "next_phase": END,
        "end": END
    }
)

# Tools go back to current phase agent
graph.add_conditional_edges(
    "tools",
    lambda state: f"{state.get('investigation_phase', 'triage')}_agent",
    {
        "triage_agent": "triage_agent",
        "deep_dive_agent": "deep_dive_agent",
        "analysis_agent": "analysis_agent"
    }
)

# Compile
agent = graph.compile()
```

### Executing Multi-Phase Investigation

```python
# Create initial state
initial_state = {
    "messages": [
        SystemMessage(content="You are an expert SRE investigating incidents."),
        HumanMessage(content=incident_description)
    ],
    "incident_id": incident_id,
    "correlation_id": correlation_id,
    "investigation_status": "in_progress",
    "investigation_phase": "triage",
    "iteration_count": 0,
    "max_iterations_per_phase": 3,
    "triage_complete": False,
    "deep_dive_complete": False
}

# Execute investigation
result = await agent.ainvoke(initial_state)

# Extract results
final_phase = result.get("investigation_phase")
messages = result.get("messages", [])
```

## Best Practices

### Node Design

1. **Keep Nodes Focused**: Each node should have a single, clear responsibility
2. **Use Async**: All nodes should be async functions for non-blocking execution
3. **Log Extensively**: Include correlation ID and incident ID in all logs
4. **Handle Errors**: Wrap node logic in try/except and update state on errors
5. **Return Partial State**: Only return fields that changed, not entire state
6. **Document Thoroughly**: Add clear docstrings explaining node purpose and behavior

### Routing Design

1. **Use Type Hints**: Define all possible routing outcomes with `Literal`
2. **Keep Logic Simple**: Complex routing logic should be split into helper functions
3. **Log Decisions**: Always log routing decisions for debugging
4. **Handle Edge Cases**: Ensure all possible states are handled
5. **Provide Defaults**: Have sensible default routing behavior

### State Design

1. **Make Fields Optional**: New fields should be optional with defaults
2. **Use Type Hints**: Properly type all state fields
3. **Document Fields**: Add comments explaining purpose of each field
4. **Consider Backward Compatibility**: Ensure existing nodes work with extended schema
5. **Initialize Properly**: Provide sensible defaults in initial state

### Testing

1. **Unit Test Nodes**: Test each node in isolation with mock state
2. **Test Routing**: Test routing functions with various state configurations
3. **Integration Test**: Test complete graph execution end-to-end
4. **Test Error Handling**: Verify nodes handle errors gracefully
5. **Test State Updates**: Verify state is updated correctly through workflow

### Performance

1. **Avoid Blocking**: Use async/await for all I/O operations
2. **Limit Iterations**: Add maximum iteration limits to prevent infinite loops
3. **Optimize Tool Calls**: Minimize unnecessary tool executions
4. **Cache Results**: Cache tool results when appropriate
5. **Monitor Execution**: Track node execution times and identify bottlenecks

### Observability

1. **Structured Logging**: Use structured logs with correlation IDs
2. **Log State Transitions**: Log when moving between nodes
3. **Log Routing Decisions**: Log why routing chose a particular path
4. **Track Metrics**: Measure node execution times and success rates
5. **Error Context**: Include full context in error logs

## Conclusion

The native LangGraph StateGraph implementation provides a powerful and flexible foundation for building complex investigation workflows. By following the patterns and best practices in this guide, you can extend the investigation agent to meet your specific requirements while maintaining code quality, observability, and maintainability.

For more information, see:
- [LangGraph Workflow Documentation](./langgraph-workflow.md)
- [LangGraph Official Documentation](https://langchain-ai.github.io/langgraph/)
- [Investigation Agent Source Code](../services/orchestrator/src/app/core/investigation_agent.py)
