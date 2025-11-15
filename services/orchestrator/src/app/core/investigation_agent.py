"""
LangGraph ReAct agent for incident investigation.

This module provides the agent factory and investigation execution functions
for autonomous incident investigation using LangGraph's ReAct pattern.
"""

import logging
import os
import re
import uuid
from typing import Any, Dict, List, Optional, Literal
from datetime import datetime

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from .retry_utils import retry_async, RetryConfig

logger = logging.getLogger(__name__)


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for tracing."""
    return str(uuid.uuid4())


# Default retry configuration for LLM calls
DEFAULT_LLM_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    max_delay=10.0,
    exponential_base=2.0
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


async def create_investigation_agent(mcp_tools: List[Any], llm_config: Dict[str, Any], correlation_id: Optional[str] = None):
    """
    Create a ReAct agent for incident investigation.

    This function creates a LangGraph ReAct agent configured with MCP tools
    and an LLM for autonomous incident investigation.

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
    """
    try:
        # Get LLM configuration from the required parameter
        base_url = llm_config.get("base_url")
        api_key = llm_config.get("api_key")
        model_name = llm_config.get("model_name", "gpt-4")
        temperature = llm_config.get("temperature", 0.7)
        max_tokens = llm_config.get("max_tokens", 2000)

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
            max_tokens=max_tokens
        )

        logger.info(
            "Creating investigation agent",
            extra={
                "correlation_id": correlation_id,
                "model": model_name,
                "tool_count": len(mcp_tools),
                "tool_names": [tool.name for tool in mcp_tools] if mcp_tools else []
            }
        )

        # Create ReAct agent with tools and system prompt
        agent = create_agent(
            model=model,
            tools=mcp_tools,
            system_prompt=INVESTIGATION_SYSTEM_PROMPT
        )

        logger.info(
            "Investigation agent created successfully",
            extra={"correlation_id": correlation_id}
        )
        return agent

    except Exception as e:
        logger.error(
            "Failed to create investigation agent",
            extra={"correlation_id": correlation_id, "error": str(e)},
            exc_info=True
        )
        raise


async def investigate_incident(
    agent: Any,
    incident_id: str,
    description: str,
    update_callback: Optional[callable] = None,
    correlation_id: Optional[str] = None
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

    start_time = datetime.utcnow()

    try:
        logger.info(
            "Starting incident investigation",
            extra={
                "correlation_id": correlation_id,
                "incident_id": incident_id,
                "description_length": len(description),
                "timestamp": start_time.isoformat()
            }
        )

        # Update status to investigating
        if update_callback:
            await update_callback(incident_id, "investigating", {
                "message": "Investigation started",
                "timestamp": start_time.isoformat(),
                "correlation_id": correlation_id
            })

        # Invoke the agent with the incident description
        logger.info(
            "Invoking agent for investigation",
            extra={
                "correlation_id": correlation_id,
                "incident_id": incident_id
            }
        )

        # Wrap agent invocation with retry logic.
        async def invoke_agent():
            return await agent.ainvoke({
                "messages": [
                    ("human", description)
                ]
            })

        result = await retry_async(
            invoke_agent,
            DEFAULT_LLM_RETRY_CONFIG,
            correlation_id
        )

        end_time = datetime.utcnow()
        duration_seconds = (end_time - start_time).total_seconds()

        logger.info(
            "Agent investigation completed",
            extra={
                "correlation_id": correlation_id,
                "incident_id": incident_id,
                "duration_seconds": duration_seconds
            }
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
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    tool_calls.append(tool_info)

                    # Log tool invocation
                    logger.info(
                        "Agent tool invocation",
                        extra={
                            "correlation_id": correlation_id,
                            "incident_id": incident_id,
                            "tool_name": tool_info["tool"],
                            "tool_args": tool_info["args"]
                        }
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
            "duration_seconds": duration_seconds
        }

        logger.info(
            "Investigation completed successfully",
            extra={
                "correlation_id": correlation_id,
                "incident_id": incident_id,
                "root_cause": root_cause,
                "confidence": confidence,
                "tool_count": len(tool_calls),
                "duration_seconds": duration_seconds
            }
        )

        # Update status to completed
        if update_callback:
            await update_callback(incident_id, "completed", investigation_result)

        return investigation_result

    except Exception as e:
        end_time = datetime.utcnow()
        duration_seconds = (end_time - start_time).total_seconds()

        logger.error(
            "Investigation failed",
            extra={
                "correlation_id": correlation_id,
                "incident_id": incident_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_seconds": duration_seconds
            },
            exc_info=True
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
            "duration_seconds": duration_seconds
        }

        # Update status to failed
        if update_callback:
            await update_callback(incident_id, "failed", {
                "error": str(e),
                "timestamp": end_time.isoformat(),
                "correlation_id": correlation_id
            })

        return error_result


def _log_agent_reasoning_steps(messages: List[Any], correlation_id: str, incident_id: str):
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
                        "content_preview": msg.content[:200] if len(msg.content) > 200 else msg.content
                    }
                )


def _log_tool_execution_results(messages: List[Any], correlation_id: str, incident_id: str):
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
                    "result_preview": str(content)[:200] if len(str(content)) > 200 else str(content)
                }
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
        r"(?:the\s+)?issue (?:is|appears to be)\s+(.+?)(?:\.|$)"
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

    high_indicators = ["definitely", "certainly", "clearly", "obviously", "high confidence"]
    low_indicators = ["possibly", "maybe", "might", "could be", "low confidence", "uncertain"]

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
                for next_msg in messages[i + 1:]:
                    if hasattr(next_msg, "content") and next_msg.content:
                        tool_response = next_msg.content
                        break

                evidence.append({
                    "source": tool_name,
                    "args": tool_args,
                    "content": tool_response or "No response",
                    "timestamp": datetime.utcnow().isoformat()
                })

    # Also extract explicit EVIDENCE markers from final response
    for msg in messages:
        if hasattr(msg, "content") and msg.content:
            match = re.search(r"EVIDENCE:\s*(.+?)(?:\n\n|\n[A-Z]+:|$)", msg.content, re.IGNORECASE | re.DOTALL)
            if match:
                evidence.append({
                    "source": "agent_analysis",
                    "content": match.group(1).strip(),
                    "timestamp": datetime.utcnow().isoformat()
                })

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
    match = re.search(r"RECOMMENDATIONS?:\s*(.+?)(?:\n\n|$)", content, re.IGNORECASE | re.DOTALL)
    if match:
        rec_text = match.group(1).strip()

        # Split by newlines or bullet points
        lines = re.split(r"\n[-•*]\s*|\n\d+\.\s*|\n", rec_text)
        for line in lines:
            line = line.strip()
            if line and len(line) > 10:  # Filter out very short lines
                recommendations.append(line)

    return recommendations
