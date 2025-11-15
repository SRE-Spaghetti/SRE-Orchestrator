"""
LangGraph ReAct agent for incident investigation.

This module provides the agent factory and investigation execution functions
for autonomous incident investigation using LangGraph's ReAct pattern.
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional, Literal
from datetime import datetime

from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


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


async def create_investigation_agent(mcp_tools: List[Any], llm_config: Dict[str, Any]):
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
            f"Creating investigation agent with model {model_name} "
            f"and {len(mcp_tools)} tool(s)"
        )

        # Create ReAct agent with tools and system prompt
        agent = create_react_agent(
            model=model,
            tools=mcp_tools,
            state_modifier=INVESTIGATION_SYSTEM_PROMPT
        )

        logger.info("Investigation agent created successfully")
        return agent

    except Exception as e:
        logger.error(f"Failed to create investigation agent: {e}", exc_info=True)
        raise


async def investigate_incident(
    agent: Any,
    incident_id: str,
    description: str,
    update_callback: Optional[callable] = None
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

    Returns:
        Dictionary containing:
            - root_cause: Identified root cause
            - confidence: Confidence level (high/medium/low)
            - evidence: List of evidence items
            - reasoning: Full reasoning from the agent
            - tool_calls: List of tools used during investigation
            - status: Investigation status (completed/failed)
            - error: Error message if investigation failed

    Raises:
        Exception: If agent execution fails critically
    """
    try:
        logger.info(f"Starting investigation for incident {incident_id}")

        # Update status to investigating
        if update_callback:
            await update_callback(incident_id, "investigating", {
                "message": "Investigation started",
                "timestamp": datetime.utcnow().isoformat()
            })

        # Invoke the agent with the incident description
        result = await agent.ainvoke({
            "messages": [
                ("system", "Investigate this incident and provide root cause analysis."),
                ("human", description)
            ]
        })

        logger.info(f"Agent investigation completed for incident {incident_id}")

        # Extract messages from the result
        messages = result.get("messages", [])

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

        # Extract tool calls from messages
        tool_calls = []
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_calls.append({
                        "tool": tool_call.get("name", "unknown"),
                        "args": tool_call.get("args", {}),
                        "timestamp": datetime.utcnow().isoformat()
                    })

        investigation_result = {
            "root_cause": root_cause,
            "confidence": confidence,
            "evidence": evidence,
            "reasoning": final_content,
            "recommendations": recommendations,
            "tool_calls": tool_calls,
            "status": "completed"
        }

        logger.info(
            f"Investigation completed for incident {incident_id}: "
            f"root_cause={root_cause}, confidence={confidence}"
        )

        # Update status to completed
        if update_callback:
            await update_callback(incident_id, "completed", investigation_result)

        return investigation_result

    except Exception as e:
        logger.error(
            f"Investigation failed for incident {incident_id}: {e}",
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
            "error": str(e)
        }

        # Update status to failed
        if update_callback:
            await update_callback(incident_id, "failed", {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })

        return error_result


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
