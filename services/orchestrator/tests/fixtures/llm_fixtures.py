"""Reusable fixtures for LLM-related testing."""

import pytest
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_chat_openai() -> Mock:
    """
    Provides a mock ChatOpenAI instance for testing.

    Returns:
        Mock: Mock LLM client with invoke and ainvoke methods
    """
    llm = Mock()
    llm.model_name = "gpt-4"
    llm.temperature = 0.7
    llm.max_tokens = 4096

    # Mock synchronous invoke
    llm.invoke = Mock(
        return_value=Mock(
            content="Based on the pod details, the issue is a CrashLoopBackOff.",
            tool_calls=[],
        )
    )

    # Mock async invoke
    llm.ainvoke = AsyncMock(
        return_value=Mock(
            content="Based on the pod details, the issue is a CrashLoopBackOff.",
            tool_calls=[],
        )
    )

    return llm


@pytest.fixture
def mock_llm_with_tool_calls() -> Mock:
    """
    Provides a mock LLM that returns responses with tool calls.

    Returns:
        Mock: Mock LLM that requests tool execution
    """
    llm = Mock()

    # First response with tool calls
    first_response = Mock()
    first_response.content = "I need to gather more information about the pod."
    first_response.tool_calls = [
        {
            "id": "call_abc123",
            "name": "get_pod_details",
            "args": {"pod_name": "nginx-deployment-abc123"},
        }
    ]

    # Second response with more tool calls
    second_response = Mock()
    second_response.content = "Let me check the logs."
    second_response.tool_calls = [
        {
            "id": "call_def456",
            "name": "get_pod_logs",
            "args": {"pod_name": "nginx-deployment-abc123"},
        }
    ]

    # Final response without tool calls
    final_response = Mock()
    final_response.content = (
        "Root cause: Memory limit exceeded. The pod is being OOMKilled."
    )
    final_response.tool_calls = []

    llm.ainvoke = AsyncMock(
        side_effect=[first_response, second_response, final_response]
    )

    return llm


@pytest.fixture
def mock_llm_with_error() -> Mock:
    """
    Provides a mock LLM that raises errors.

    Returns:
        Mock: Mock LLM that simulates API failures
    """
    llm = Mock()
    llm.invoke = Mock(side_effect=Exception("LLM API timeout"))
    llm.ainvoke = AsyncMock(side_effect=Exception("LLM API timeout"))
    return llm


@pytest.fixture
def llm_response_with_analysis() -> Dict[str, Any]:
    """
    Provides a complete LLM analysis response.

    Returns:
        Dict[str, Any]: Structured analysis from LLM
    """
    return {
        "content": """
# Investigation Analysis

## Root Cause
The pod nginx-deployment-abc123 is experiencing a CrashLoopBackOff due to memory exhaustion (OOMKilled).

## Evidence
1. Pod status shows CrashLoopBackOff with 5 restarts
2. Container logs indicate OOMKilled status
3. Memory usage reached the configured limit of 512Mi

## Confidence
High - Multiple data points confirm memory exhaustion

## Recommendations
1. Increase memory limit to 1Gi in deployment spec
2. Add memory request (e.g., 768Mi) for better scheduling
3. Monitor memory usage patterns to optimize further
4. Consider implementing memory profiling in the application
        """,
        "tool_calls": [],
    }


@pytest.fixture
def llm_tool_call_request() -> Dict[str, Any]:
    """
    Provides an LLM response requesting tool execution.

    Returns:
        Dict[str, Any]: Tool call request structure
    """
    return {
        "content": "I need to investigate the pod status first.",
        "tool_calls": [
            {
                "id": "call_123abc",
                "name": "get_pod_details",
                "args": {
                    "pod_name": "nginx-deployment-abc123",
                    "namespace": "production",
                },
            }
        ],
    }


@pytest.fixture
def llm_multiple_tool_calls() -> Dict[str, Any]:
    """
    Provides an LLM response with multiple tool calls.

    Returns:
        Dict[str, Any]: Multiple tool call requests
    """
    return {
        "content": "I need to gather comprehensive information.",
        "tool_calls": [
            {
                "id": "call_001",
                "name": "get_pod_details",
                "args": {"pod_name": "nginx-deployment-abc123"},
            },
            {
                "id": "call_002",
                "name": "get_pod_logs",
                "args": {"pod_name": "nginx-deployment-abc123", "tail_lines": 100},
            },
            {
                "id": "call_003",
                "name": "get_events",
                "args": {
                    "namespace": "production",
                    "resource_name": "nginx-deployment-abc123",
                },
            },
        ],
    }


@pytest.fixture
def llm_streaming_response() -> List[Dict[str, Any]]:
    """
    Provides a mock streaming response from LLM.

    Returns:
        List[Dict[str, Any]]: Chunks of streaming response
    """
    return [
        {"content": "Based ", "tool_calls": []},
        {"content": "on the ", "tool_calls": []},
        {"content": "analysis, ", "tool_calls": []},
        {"content": "the root cause ", "tool_calls": []},
        {"content": "is memory exhaustion.", "tool_calls": []},
    ]


@pytest.fixture
def llm_error_responses() -> List[Dict[str, Any]]:
    """
    Provides various LLM error scenarios.

    Returns:
        List[Dict[str, Any]]: Different error types
    """
    return [
        {
            "error": "rate_limit_exceeded",
            "message": "Rate limit exceeded. Please try again later.",
            "retry_after": 60,
        },
        {
            "error": "timeout",
            "message": "Request timed out after 30 seconds.",
        },
        {
            "error": "invalid_api_key",
            "message": "Invalid API key provided.",
        },
        {
            "error": "model_not_found",
            "message": "Model 'gpt-5' not found.",
        },
        {
            "error": "context_length_exceeded",
            "message": "Request exceeds maximum context length of 8192 tokens.",
        },
    ]


@pytest.fixture
def mock_langchain_message() -> Mock:
    """
    Provides a mock LangChain message object.

    Returns:
        Mock: Mock AIMessage or HumanMessage
    """
    message = Mock()
    message.content = "This is a test message"
    message.type = "ai"
    message.additional_kwargs = {}
    return message


@pytest.fixture
def mock_langchain_tool_message() -> Mock:
    """
    Provides a mock LangChain tool message.

    Returns:
        Mock: Mock ToolMessage with execution results
    """
    message = Mock()
    message.content = '{"status": "Running", "restarts": 0}'
    message.type = "tool"
    message.tool_call_id = "call_abc123"
    message.name = "get_pod_details"
    return message


@pytest.fixture
def mock_investigation_agent() -> Mock:
    """
    Provides a mock LangGraph investigation agent.

    Returns:
        Mock: Mock agent with invoke and ainvoke methods
    """
    agent = Mock()

    # Mock successful investigation result
    investigation_result = {
        "messages": [
            Mock(content="Initial analysis", type="ai"),
            Mock(content="Tool execution", type="tool"),
            Mock(
                content="Root cause: Memory limit exceeded",
                type="ai",
                tool_calls=[],
            ),
        ],
        "final_output": "Root cause: Memory limit exceeded. Recommendation: Increase memory limit to 1Gi.",
    }

    agent.invoke = Mock(return_value=investigation_result)
    agent.ainvoke = AsyncMock(return_value=investigation_result)

    return agent


@pytest.fixture
def mock_agent_with_failure() -> Mock:
    """
    Provides a mock agent that simulates investigation failure.

    Returns:
        Mock: Mock agent that raises errors
    """
    agent = Mock()
    agent.invoke = Mock(side_effect=Exception("Agent execution failed"))
    agent.ainvoke = AsyncMock(side_effect=Exception("Agent execution failed"))
    return agent


@pytest.fixture
def llm_prompt_templates() -> Dict[str, str]:
    """
    Provides sample prompt templates for testing.

    Returns:
        Dict[str, str]: Various prompt templates
    """
    return {
        "system_prompt": """You are an expert SRE assistant investigating Kubernetes incidents.
Analyze the provided information and determine the root cause.
Use available tools to gather necessary information.""",
        "investigation_prompt": """Investigate the following incident:

Description: {description}

Available tools:
{tools}

Provide a detailed analysis including:
1. Root cause
2. Evidence
3. Confidence level
4. Recommendations""",
        "tool_result_prompt": """Tool execution result:

Tool: {tool_name}
Result: {result}

Continue your analysis based on this information.""",
    }
