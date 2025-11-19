"""
LangGraph native StateGraph agent for incident investigation.

This module provides a native LangGraph StateGraph implementation for autonomous
incident investigation using the ReAct (Reasoning + Acting) pattern. The native
implementation provides explicit control over the workflow graph structure,
enabling better observability, extensibility, and customization compared to
prebuilt agent functions.

Key Components:
    - InvestigationState: TypedDict schema defining the state structure
    - agent_node: LLM reasoning node that decides on actions
    - tool_node: Tool execution node that runs MCP tools
    - should_continue: Routing function that determines workflow transitions
    - create_investigation_agent_native: Factory function for native graph
    - investigate_incident: Main entry point for executing investigations

Architecture:
    The investigation workflow is implemented as a StateGraph with explicit nodes
    and edges:

    Start → Agent Node → Routing Logic → Tool Node → Agent Node → ... → End
                              ↓
                            End (if final answer)

    The agent alternates between reasoning (agent node) and acting (tool node)
    until it reaches a final conclusion. The routing logic checks if the LLM
    requested tool calls to determine the next step.

Features:
    - Native LangGraph StateGraph implementation with explicit nodes and edges
    - Comprehensive logging with correlation IDs for tracing
    - Retry logic for transient LLM failures
    - Error handling at node and graph levels
    - Backward compatible with existing API and tests
    - Extensible design for adding custom nodes and routing logic

Usage:
    >>> # Create agent
    >>> agent = await create_investigation_agent(
    ...     mcp_tools=tools,
    ...     llm_config={"base_url": "...", "api_key": "..."},
    ...     correlation_id="corr-123"
    ... )
    >>>
    >>> # Execute investigation
    >>> result = await investigate_incident(
    ...     agent=agent,
    ...     incident_id="inc-456",
    ...     description="Pod is crashing",
    ...     correlation_id="corr-123"
    ... )
    >>>
    >>> # Access results
    >>> print(result["root_cause"])
    >>> print(result["confidence"])
    >>> print(result["recommendations"])

For more information on extending the graph, see:
    docs/extending-investigation-graph.md
"""

import logging
import re
import uuid
from typing import Any, Dict, List, Optional, Literal, TypedDict, Annotated, Sequence
from datetime import datetime, timezone

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    BaseMessage,
    ToolMessage,
    SystemMessage,
    HumanMessage,
)
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from .retry_utils import retry_async, RetryConfig

logger = logging.getLogger(__name__)


class InvestigationState(TypedDict):
    """
    State schema for the investigation workflow.

    This TypedDict defines the structure of the state that flows through the
    LangGraph investigation workflow. The state is passed between nodes and
    tracks the entire investigation process.

    Attributes:
        messages: Conversation history including human messages, AI responses,
                 and tool execution results. Uses the add_messages reducer to
                 automatically append new messages to the list.
        incident_id: Unique identifier for the incident being investigated.
        correlation_id: Unique identifier for tracing the investigation across
                       logs and services.
        investigation_status: Current status of the investigation. Valid values:
                             "in_progress", "completed", "failed".

    Example:
        >>> state = InvestigationState(
        ...     messages=[HumanMessage(content="Pod is crashing")],
        ...     incident_id="inc-123",
        ...     correlation_id="corr-456",
        ...     investigation_status="in_progress"
        ... )

    Note:
        The messages field uses the add_messages reducer annotation, which means
        when nodes return partial state updates with new messages, those messages
        are automatically appended to the existing messages list rather than
        replacing it. This is essential for maintaining conversation history.

        Additional fields can be added to this schema in the future without
        breaking existing nodes, as long as they are optional or have defaults.
    """

    messages: Annotated[Sequence[BaseMessage], add_messages]
    incident_id: str
    correlation_id: str
    investigation_status: str


def should_continue(state: InvestigationState) -> Literal["tools", "end"]:
    """
    Routing function to determine if the workflow should continue to tools or end.

    This function checks the last message from the agent to determine the next
    step in the investigation workflow:
    - If the last message contains tool calls, route to the "tools" node
    - If the last message is a final answer (no tool calls), route to "end"

    This routing logic implements the core ReAct pattern where the agent
    alternates between reasoning (agent node) and acting (tool node) until
    it reaches a final conclusion.

    Args:
        state: Current investigation state containing messages and metadata

    Returns:
        "tools" to execute tools, or "end" to finish the workflow

    Example:
        >>> # Agent requests tool execution
        >>> state = {
        ...     "messages": [AIMessage(content="", tool_calls=[{"name": "get_pod"}])],
        ...     "correlation_id": "corr-123",
        ...     "incident_id": "inc-456"
        ... }
        >>> should_continue(state)
        'tools'

        >>> # Agent provides final answer
        >>> state = {
        ...     "messages": [AIMessage(content="ROOT CAUSE: Memory leak")],
        ...     "correlation_id": "corr-123",
        ...     "incident_id": "inc-456"
        ... }
        >>> should_continue(state)
        'end'

    Note:
        This function logs routing decisions with correlation ID for debugging
        and observability. The routing logic can be extended in the future to
        support additional conditions such as:
        - Maximum iteration limits
        - Confidence thresholds for early termination
        - Validation requirements before completion
    """
    correlation_id = state.get("correlation_id")
    incident_id = state.get("incident_id")

    messages = state["messages"]
    last_message = messages[-1]

    # Check if the last message has tool calls
    has_tool_calls = hasattr(last_message, "tool_calls") and bool(
        last_message.tool_calls
    )

    if has_tool_calls:
        tool_count = len(last_message.tool_calls)
        tool_names = [tc.get("name", "unknown") for tc in last_message.tool_calls]

        logger.info(
            "Routing to tools node",
            extra={
                "correlation_id": correlation_id,
                "incident_id": incident_id,
                "tool_count": tool_count,
                "tool_names": tool_names,
                "routing_decision": "tools",
            },
        )
        return "tools"
    else:
        logger.info(
            "Routing to end - investigation complete",
            extra={
                "correlation_id": correlation_id,
                "incident_id": incident_id,
                "routing_decision": "end",
                "final_message_preview": (
                    last_message.content[:100]
                    if hasattr(last_message, "content") and last_message.content
                    else "No content"
                ),
            },
        )
        return "end"


def create_agent_node(model_with_tools: Any) -> callable:
    """
    Create an agent node function for the LangGraph workflow.

    This function creates an agent node that invokes the LLM with tools bound
    for reasoning and decision-making. The node includes comprehensive error
    handling, retry logic, and logging for observability.

    The agent node:
    1. Extracts correlation_id and incident_id from state for logging
    2. Invokes the LLM with the current message history
    3. Returns a partial state update with the LLM's response
    4. Handles errors gracefully and updates investigation status
    5. Uses retry logic for transient failures

    Args:
        model_with_tools: LLM instance with tools bound via bind_tools()

    Returns:
        Async function that executes the agent node

    Example:
        >>> model_with_tools = model.bind_tools(mcp_tools)
        >>> agent_node = create_agent_node(model_with_tools)
        >>> result = await agent_node(state)

    Note:
        The agent node uses the retry_async utility with DEFAULT_LLM_RETRY_CONFIG
        to handle transient LLM failures. All operations are logged with
        correlation ID and incident ID for tracing.
    """

    async def agent_node(state: InvestigationState) -> InvestigationState:
        """
        Agent node that invokes the LLM for reasoning and decision-making.

        This node takes the current investigation state (including message history),
        invokes the LLM with tools bound, and returns an updated state with the
        LLM's response. The response may include tool calls or a final answer.

        Args:
            state: Current investigation state containing messages and metadata

        Returns:
            Updated state with LLM response added to messages, or error status
            if the invocation fails

        Raises:
            Does not raise exceptions - errors are captured in the state
        """
        correlation_id = state.get("correlation_id")
        incident_id = state.get("incident_id")

        logger.info(
            "Agent node executing",
            extra={
                "correlation_id": correlation_id,
                "incident_id": incident_id,
                "message_count": len(state["messages"]),
                "investigation_status": state.get("investigation_status", "unknown"),
            },
        )

        try:
            # Define the LLM invocation function for retry wrapper
            async def invoke_llm():
                """Invoke the LLM with current messages."""
                return await model_with_tools.ainvoke(state["messages"])

            # Invoke the LLM with retry logic
            response = await retry_async(
                invoke_llm, DEFAULT_LLM_RETRY_CONFIG, correlation_id
            )

            # Check if response has tool calls
            has_tool_calls = hasattr(response, "tool_calls") and bool(
                response.tool_calls
            )

            logger.info(
                "Agent node completed successfully",
                extra={
                    "correlation_id": correlation_id,
                    "incident_id": incident_id,
                    "has_tool_calls": has_tool_calls,
                    "tool_count": len(response.tool_calls) if has_tool_calls else 0,
                    "response_length": (
                        len(response.content)
                        if hasattr(response, "content") and response.content
                        else 0
                    ),
                },
            )

            # Return partial state update - add_messages reducer will append the response
            return {"messages": [response]}

        except Exception as e:
            logger.error(
                "Agent node failed",
                extra={
                    "correlation_id": correlation_id,
                    "incident_id": incident_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "investigation_status": state.get(
                        "investigation_status", "unknown"
                    ),
                },
                exc_info=True,
            )

            # Update investigation status to failed
            return {"messages": [], "investigation_status": "failed"}

    return agent_node


def create_tool_node_with_logging(mcp_tools: List[Any]) -> callable:
    """
    Create a tool node with custom logging wrapper.

    This function creates a wrapper around LangGraph's prebuilt ToolNode that
    adds comprehensive logging for tool invocations, results, and errors.

    The wrapper logs:
    - Tool invocations with correlation ID and incident ID
    - Tool execution timing information
    - Tool results with content preview
    - Tool errors with full context

    Args:
        mcp_tools: List of LangChain-compatible MCP tools

    Returns:
        Async function that executes tools with logging

    Example:
        >>> tool_node = create_tool_node_with_logging(mcp_tools)
        >>> result = await tool_node(state)

    Note:
        This wrapper uses LangGraph's prebuilt ToolNode for actual tool
        execution, ensuring compatibility with LangGraph's tool calling
        conventions while adding observability through structured logging.
    """
    # Create the prebuilt ToolNode
    base_tool_node = ToolNode(mcp_tools)

    async def tool_node_with_logging(state: InvestigationState) -> InvestigationState:
        """
        Tool node that executes tools with comprehensive logging.

        This node:
        1. Extracts tool calls from the last message
        2. Logs tool invocations with correlation ID
        3. Executes tools using LangGraph's ToolNode
        4. Logs tool results with timing information
        5. Logs tool errors with context

        Args:
            state: Current investigation state

        Returns:
            Updated state with tool results added to messages
        """
        correlation_id = state.get("correlation_id")
        incident_id = state.get("incident_id")

        messages = state["messages"]
        last_message = messages[-1] if messages else None

        # Extract tool calls for logging
        tool_calls = []
        if (
            last_message
            and hasattr(last_message, "tool_calls")
            and last_message.tool_calls
        ):
            tool_calls = last_message.tool_calls

        if not tool_calls:
            logger.warning(
                "Tool node called but no tool calls found",
                extra={
                    "correlation_id": correlation_id,
                    "incident_id": incident_id,
                    "message_count": len(messages),
                },
            )
            return {"messages": []}

        # Log tool invocations
        logger.info(
            "Tool node executing",
            extra={
                "correlation_id": correlation_id,
                "incident_id": incident_id,
                "tool_count": len(tool_calls),
                "tool_names": [tc.get("name", "unknown") for tc in tool_calls],
            },
        )

        # Log each tool invocation
        for tool_call in tool_calls:
            tool_name = tool_call.get("name", "unknown")
            tool_args = tool_call.get("args", {})

            logger.info(
                "Executing tool",
                extra={
                    "correlation_id": correlation_id,
                    "incident_id": incident_id,
                    "tool_name": tool_name,
                    "tool_args": tool_args,
                    "tool_call_id": tool_call.get("id", "unknown"),
                },
            )

        # Execute tools using the base ToolNode
        start_time = datetime.now(timezone.utc)

        try:
            result = await base_tool_node.ainvoke(state)

            end_time = datetime.now(timezone.utc)
            duration_ms = (end_time - start_time).total_seconds() * 1000

            # Log tool execution completion
            logger.info(
                "Tool node completed",
                extra={
                    "correlation_id": correlation_id,
                    "incident_id": incident_id,
                    "tool_count": len(tool_calls),
                    "duration_ms": duration_ms,
                },
            )

            # Log individual tool results
            result_messages = result.get("messages", [])
            for msg in result_messages:
                if isinstance(msg, ToolMessage):
                    tool_name = getattr(msg, "name", "unknown")
                    content = getattr(msg, "content", "")
                    tool_call_id = getattr(msg, "tool_call_id", "unknown")

                    logger.info(
                        "Tool execution result",
                        extra={
                            "correlation_id": correlation_id,
                            "incident_id": incident_id,
                            "tool_name": tool_name,
                            "tool_call_id": tool_call_id,
                            "result_length": len(str(content)),
                            "result_preview": (
                                str(content)[:200]
                                if len(str(content)) > 200
                                else str(content)
                            ),
                        },
                    )

            return result

        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration_ms = (end_time - start_time).total_seconds() * 1000

            logger.error(
                "Tool node execution failed",
                extra={
                    "correlation_id": correlation_id,
                    "incident_id": incident_id,
                    "tool_count": len(tool_calls),
                    "tool_names": [tc.get("name", "unknown") for tc in tool_calls],
                    "duration_ms": duration_ms,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )

            # Return error messages for each tool call
            error_messages = []
            for tool_call in tool_calls:
                error_msg = ToolMessage(
                    content=f"Error executing tool: {str(e)}",
                    tool_call_id=tool_call.get("id", "unknown"),
                    name=tool_call.get("name", "unknown"),
                )
                error_messages.append(error_msg)

            return {"messages": error_messages}

    return tool_node_with_logging


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for tracing."""
    return str(uuid.uuid4())


# Default retry configuration for LLM calls
DEFAULT_LLM_RETRY_CONFIG = RetryConfig(
    max_attempts=3, initial_delay=1.0, max_delay=10.0, exponential_base=2.0
)


# System prompt for the SRE investigation agent
INVESTIGATION_SYSTEM_PROMPT = """You are an expert SRE assistant investigating production incidents.

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

Always explain your reasoning and cite specific evidence from the tools.

When you have gathered sufficient evidence and determined the root cause, provide your final analysis in this format:

ROOT CAUSE: [Your determined root cause]
CONFIDENCE: [high/medium/low]
EVIDENCE: [Key evidence that supports your conclusion]
RECOMMENDATIONS: [Actionable recommendations]

Be thorough but concise. Focus on the most relevant information."""


async def create_investigation_agent_native(
    mcp_tools: List[Any],
    llm_config: Dict[str, Any],
    correlation_id: Optional[str] = None,
):
    """
    Create a native LangGraph StateGraph agent for incident investigation.

    This function creates a native LangGraph StateGraph implementation with
    explicit nodes and edges for the investigation workflow. This provides
    greater control and extensibility compared to the prebuilt create_agent.

    The native graph includes:
    - Explicit agent node for LLM reasoning
    - Explicit tool node for tool execution
    - Conditional routing logic between nodes
    - Comprehensive logging and error handling

    Args:
        mcp_tools: List of LangChain-compatible MCP tools
        llm_config: LLM configuration dictionary containing:
                   - base_url: LLM API endpoint
                   - api_key: API authentication key
                   - model_name: Model name (default: "gpt-4")
                   - temperature: Temperature setting (default: 0.7)
                   - max_tokens: Max tokens (default: 2000)
        correlation_id: Optional correlation ID for tracing

    Returns:
        Compiled LangGraph agent ready for investigation

    Raises:
        ValueError: If required configuration keys are missing
        Exception: If graph construction fails

    Example:
        >>> agent = await create_investigation_agent_native(
        ...     mcp_tools=tools,
        ...     llm_config={"base_url": "...", "api_key": "..."},
        ...     correlation_id="corr-123"
        ... )
        >>> result = await agent.ainvoke({
        ...     "messages": [HumanMessage(content="Pod is crashing")],
        ...     "incident_id": "inc-456",
        ...     "correlation_id": "corr-123",
        ...     "investigation_status": "in_progress"
        ... })
    """
    try:
        # Extract LLM configuration
        base_url = llm_config.get("base_url")
        api_key = llm_config.get("api_key")
        model_name = llm_config.get("model_name", "gpt-4")
        temperature = llm_config.get("temperature", 0.7)
        max_tokens = llm_config.get("max_tokens", 2000)

        # Validate required configuration
        if not base_url:
            raise ValueError("llm_config missing required key: base_url")
        if not api_key:
            raise ValueError("llm_config missing required key: api_key")

        # Initialize the LLM
        model = ChatOpenAI(
            base_url=base_url,
            api_key=api_key,
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Bind tools to the model
        model_with_tools = model.bind_tools(mcp_tools)

        logger.info(
            "Creating native LangGraph investigation agent",
            extra={
                "correlation_id": correlation_id,
                "model": model_name,
                "tool_count": len(mcp_tools),
                "tool_names": [tool.name for tool in mcp_tools] if mcp_tools else [],
                "implementation": "native",
            },
        )

        # Import StateGraph and END
        from langgraph.graph import StateGraph, END

        # Create the state graph with InvestigationState schema
        graph = StateGraph(InvestigationState)

        # Create agent node with model_with_tools in closure
        agent_node = create_agent_node(model_with_tools)

        # Create tool node with logging
        tool_node = create_tool_node_with_logging(mcp_tools)

        # Add nodes to the graph
        graph.add_node("agent", agent_node)
        graph.add_node("tools", tool_node)

        # Add conditional edges from agent using should_continue
        graph.add_conditional_edges(
            "agent", should_continue, {"tools": "tools", "end": END}
        )

        # Add edge from tools back to agent
        graph.add_edge("tools", "agent")

        # Set entry point to agent node
        graph.set_entry_point("agent")

        logger.info(
            "Compiling native LangGraph investigation agent",
            extra={
                "correlation_id": correlation_id,
                "node_count": 2,
                "nodes": ["agent", "tools"],
            },
        )

        # Compile the graph to create executable agent
        agent = graph.compile()

        logger.info(
            "Native LangGraph investigation agent created successfully",
            extra={
                "correlation_id": correlation_id,
                "implementation": "native",
                "model": model_name,
                "tool_count": len(mcp_tools),
            },
        )

        return agent

    except Exception as e:
        logger.error(
            "Failed to create native LangGraph investigation agent",
            extra={
                "correlation_id": correlation_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "implementation": "native",
            },
            exc_info=True,
        )
        raise


async def create_investigation_agent(
    mcp_tools: List[Any],
    llm_config: Dict[str, Any],
    correlation_id: Optional[str] = None,
):
    """
    Create a native LangGraph StateGraph agent for incident investigation.

    This function creates a native LangGraph StateGraph implementation with
    explicit nodes and edges for the investigation workflow. This provides
    greater control and extensibility compared to prebuilt agent functions.

    The native graph includes:
    - Explicit agent node for LLM reasoning
    - Explicit tool node for tool execution
    - Conditional routing logic between nodes
    - Comprehensive logging and error handling

    Args:
        mcp_tools: List of LangChain-compatible MCP tools
        llm_config: LLM configuration dictionary containing:
                   - base_url: LLM API endpoint
                   - api_key: API authentication key
                   - model_name: Model name (default: "gpt-4")
                   - temperature: Temperature setting (default: 0.7)
                   - max_tokens: Max tokens (default: 2000)
        correlation_id: Optional correlation ID for tracing

    Returns:
        Compiled LangGraph agent ready for investigation

    Raises:
        ValueError: If required configuration keys are missing
        Exception: If graph construction fails

    Example:
        >>> agent = await create_investigation_agent(
        ...     mcp_tools=tools,
        ...     llm_config={"base_url": "...", "api_key": "..."},
        ...     correlation_id="corr-123"
        ... )
        >>> result = await agent.ainvoke({
        ...     "messages": [HumanMessage(content="Pod is crashing")],
        ...     "incident_id": "inc-456",
        ...     "correlation_id": "corr-123",
        ...     "investigation_status": "in_progress"
        ... })
    """
    return await create_investigation_agent_native(
        mcp_tools, llm_config, correlation_id
    )


async def investigate_incident(
    agent: Any,
    incident_id: str,
    description: str,
    update_callback: Optional[callable] = None,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute incident investigation using the ReAct agent.

    This function invokes the agent with the incident description and
    extracts structured results from the agent's investigation.

    Args:
        agent: The compiled LangGraph ReAct agent
        incident_id: Unique identifier for the incident
        description: The incident description to investigate
        update_callback: Optional callback function to update incident status
                        during investigation. Should accept (incident_id, status, details)
        correlation_id: Optional correlation ID for tracing

    Returns:
        Dictionary containing:
            - root_cause: Identified root cause
            - confidence: Confidence level (high/medium/low)
            - evidence: List of evidence items
            - reasoning: Full reasoning from the agent
            - tool_calls: List of tools used during investigation
            - status: Investigation status (completed/failed)
            - error: Error message if investigation failed
            - correlation_id: Correlation ID for tracing

    Raises:
        Exception: If agent execution fails critically
    """
    # Generate correlation ID if not provided
    if not correlation_id:
        correlation_id = generate_correlation_id()

    start_time = datetime.now(timezone.utc)

    try:
        logger.info(
            "Starting incident investigation",
            extra={
                "correlation_id": correlation_id,
                "incident_id": incident_id,
                "description_length": len(description),
                "timestamp": start_time.isoformat(),
            },
        )

        # Update status to investigating
        if update_callback:
            await update_callback(
                incident_id,
                "investigating",
                {
                    "message": "Investigation started",
                    "timestamp": start_time.isoformat(),
                    "correlation_id": correlation_id,
                },
            )

        # Invoke the agent with the incident description
        logger.info(
            "Invoking agent for investigation",
            extra={"correlation_id": correlation_id, "incident_id": incident_id},
        )

        # Create initial state with messages, incident_id, correlation_id, investigation_status
        initial_state = {
            "messages": [
                SystemMessage(content=INVESTIGATION_SYSTEM_PROMPT),
                HumanMessage(content=description),
            ],
            "incident_id": incident_id,
            "correlation_id": correlation_id,
            "investigation_status": "in_progress",
        }

        logger.info(
            "Created initial investigation state",
            extra={
                "correlation_id": correlation_id,
                "incident_id": incident_id,
                "message_count": len(initial_state["messages"]),
                "investigation_status": initial_state["investigation_status"],
            },
        )

        # Wrap agent invocation with retry logic.
        async def invoke_agent():
            return await agent.ainvoke(initial_state)

        result = await retry_async(
            invoke_agent, DEFAULT_LLM_RETRY_CONFIG, correlation_id
        )

        end_time = datetime.now(timezone.utc)
        duration_seconds = (end_time - start_time).total_seconds()

        logger.info(
            "Agent investigation completed",
            extra={
                "correlation_id": correlation_id,
                "incident_id": incident_id,
                "duration_seconds": duration_seconds,
            },
        )

        # Extract messages from the result
        messages = result.get("messages", [])

        # Log agent reasoning steps
        _log_agent_reasoning_steps(messages, correlation_id, incident_id)

        # Extract the final response (last message from the agent)
        final_message = None
        for msg in reversed(messages):
            if hasattr(msg, "content") and msg.content:
                final_message = msg
                break

        if not final_message:
            raise ValueError("No response from agent")

        final_content = final_message.content

        # Extract structured information from the response
        root_cause = extract_root_cause(final_content)
        confidence = extract_confidence(final_content)
        evidence = extract_evidence(messages)
        recommendations = extract_recommendations(final_content)

        # Extract and log tool calls from messages
        tool_calls = []
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_info = {
                        "tool": tool_call.get("name", "unknown"),
                        "args": tool_call.get("args", {}),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    tool_calls.append(tool_info)

                    # Log tool invocation
                    logger.info(
                        "Agent tool invocation",
                        extra={
                            "correlation_id": correlation_id,
                            "incident_id": incident_id,
                            "tool_name": tool_info["tool"],
                            "tool_args": tool_info["args"],
                        },
                    )

        # Log tool execution results
        _log_tool_execution_results(messages, correlation_id, incident_id)

        investigation_result = {
            "root_cause": root_cause,
            "confidence": confidence,
            "evidence": evidence,
            "reasoning": final_content,
            "recommendations": recommendations,
            "tool_calls": tool_calls,
            "status": "completed",
            "correlation_id": correlation_id,
            "duration_seconds": duration_seconds,
        }

        logger.info(
            "Investigation completed successfully",
            extra={
                "correlation_id": correlation_id,
                "incident_id": incident_id,
                "root_cause": root_cause,
                "confidence": confidence,
                "tool_count": len(tool_calls),
                "duration_seconds": duration_seconds,
            },
        )

        # Update status to completed
        if update_callback:
            await update_callback(incident_id, "completed", investigation_result)

        return investigation_result

    except Exception as e:
        end_time = datetime.now(timezone.utc)
        duration_seconds = (end_time - start_time).total_seconds()

        logger.error(
            "Investigation failed",
            extra={
                "correlation_id": correlation_id,
                "incident_id": incident_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_seconds": duration_seconds,
            },
            exc_info=True,
        )

        error_result = {
            "root_cause": None,
            "confidence": None,
            "evidence": [],
            "reasoning": None,
            "recommendations": [],
            "tool_calls": [],
            "status": "failed",
            "error": str(e),
            "correlation_id": correlation_id,
            "duration_seconds": duration_seconds,
        }

        # Update status to failed
        if update_callback:
            await update_callback(
                incident_id,
                "failed",
                {
                    "error": str(e),
                    "timestamp": end_time.isoformat(),
                    "correlation_id": correlation_id,
                },
            )

        return error_result


def _log_agent_reasoning_steps(
    messages: List[Any], correlation_id: str, incident_id: str
):
    """
    Log agent reasoning steps from the conversation messages.

    Args:
        messages: List of messages from the agent conversation
        correlation_id: Correlation ID for tracing
        incident_id: Incident ID
    """
    step_number = 0
    for msg in messages:
        if hasattr(msg, "content") and msg.content:
            # Check if this is an agent reasoning message (not a tool call or system message)
            if hasattr(msg, "type") and msg.type == "ai":
                step_number += 1
                logger.info(
                    "Agent reasoning step",
                    extra={
                        "correlation_id": correlation_id,
                        "incident_id": incident_id,
                        "step_number": step_number,
                        "content_preview": (
                            msg.content[:200] if len(msg.content) > 200 else msg.content
                        ),
                    },
                )


def _log_tool_execution_results(
    messages: List[Any], correlation_id: str, incident_id: str
):
    """
    Log tool execution results from the conversation messages.

    Args:
        messages: List of messages from the agent conversation
        correlation_id: Correlation ID for tracing
        incident_id: Incident ID
    """
    for msg in messages:
        # Check if this is a tool response message
        if hasattr(msg, "type") and msg.type == "tool":
            tool_name = getattr(msg, "name", "unknown")
            content = getattr(msg, "content", "")

            logger.info(
                "Tool execution result",
                extra={
                    "correlation_id": correlation_id,
                    "incident_id": incident_id,
                    "tool_name": tool_name,
                    "result_length": len(str(content)),
                    "result_preview": (
                        str(content)[:200] if len(str(content)) > 200 else str(content)
                    ),
                },
            )


def extract_root_cause(content: str) -> Optional[str]:
    """
    Extract root cause from agent response.

    Looks for patterns like "ROOT CAUSE: ..." in the agent's response.

    Args:
        content: The agent's response content

    Returns:
        Extracted root cause or None if not found
    """
    if not content:
        return None

    # Try to find explicit ROOT CAUSE marker
    match = re.search(r"ROOT CAUSE:\s*(.+?)(?:\n|$)", content, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Fallback: look for common root cause patterns
    patterns = [
        r"(?:the\s+)?root cause (?:is|appears to be|seems to be)\s+(.+?)(?:\.|$)",
        r"(?:this\s+)?(?:is\s+)?(?:likely\s+)?caused by\s+(.+?)(?:\.|$)",
        r"(?:the\s+)?issue (?:is|appears to be)\s+(.+?)(?:\.|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    # If no pattern matches, return first sentence as fallback
    sentences = content.split(".")
    if sentences:
        return sentences[0].strip()

    return None


def extract_confidence(content: str) -> Literal["high", "medium", "low"]:
    """
    Extract confidence level from agent response.

    Looks for patterns like "CONFIDENCE: high" in the agent's response.

    Args:
        content: The agent's response content

    Returns:
        Confidence level: "high", "medium", or "low" (defaults to "medium")
    """
    if not content:
        return "medium"

    # Try to find explicit CONFIDENCE marker
    match = re.search(r"CONFIDENCE:\s*(high|medium|low)", content, re.IGNORECASE)
    if match:
        return match.group(1).lower()

    # Fallback: look for confidence indicators in text
    content_lower = content.lower()

    high_indicators = [
        "definitely",
        "certainly",
        "clearly",
        "obviously",
        "high confidence",
    ]
    low_indicators = [
        "possibly",
        "maybe",
        "might",
        "could be",
        "low confidence",
        "uncertain",
    ]

    for indicator in high_indicators:
        if indicator in content_lower:
            return "high"

    for indicator in low_indicators:
        if indicator in content_lower:
            return "low"

    return "medium"


def extract_evidence(messages: List[Any]) -> List[Dict[str, Any]]:
    """
    Extract evidence from agent messages.

    Parses tool calls and their responses to build a list of evidence items.

    Args:
        messages: List of messages from the agent conversation

    Returns:
        List of evidence dictionaries with source and content
    """
    evidence = []

    for i, msg in enumerate(messages):
        # Check for tool calls
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tool_call in msg.tool_calls:
                tool_name = tool_call.get("name", "unknown")
                tool_args = tool_call.get("args", {})

                # Look for the corresponding tool response in next messages
                tool_response = None
                for next_msg in messages[i + 1 :]:
                    if hasattr(next_msg, "content") and next_msg.content:
                        tool_response = next_msg.content
                        break

                evidence.append(
                    {
                        "source": tool_name,
                        "args": tool_args,
                        "content": tool_response or "No response",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )

    # Also extract explicit EVIDENCE markers from final response
    for msg in messages:
        if hasattr(msg, "content") and msg.content:
            match = re.search(
                r"EVIDENCE:\s*(.+?)(?:\n\n|\n[A-Z]+:|$)",
                msg.content,
                re.IGNORECASE | re.DOTALL,
            )
            if match:
                evidence.append(
                    {
                        "source": "agent_analysis",
                        "content": match.group(1).strip(),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )

    return evidence


def extract_recommendations(content: str) -> List[str]:
    """
    Extract recommendations from agent response.

    Looks for patterns like "RECOMMENDATIONS: ..." in the agent's response.

    Args:
        content: The agent's response content

    Returns:
        List of recommendation strings
    """
    if not content:
        return []

    recommendations = []

    # Try to find explicit RECOMMENDATIONS marker
    match = re.search(
        r"RECOMMENDATIONS?:\s*(.+?)(?:\n\n|$)", content, re.IGNORECASE | re.DOTALL
    )
    if match:
        rec_text = match.group(1).strip()

        # Split by newlines or bullet points
        lines = re.split(r"\n[-•*]\s*|\n\d+\.\s*|\n", rec_text)
        for line in lines:
            line = line.strip()
            if line and len(line) > 10:  # Filter out very short lines
                recommendations.append(line)

    return recommendations
