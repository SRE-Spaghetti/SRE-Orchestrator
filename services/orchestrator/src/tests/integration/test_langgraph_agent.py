"""Integration tests for LangGraph investigation agent."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.core.investigation_agent import (
    create_investigation_agent,
    investigate_incident,
    extract_root_cause,
    extract_confidence,
    extract_evidence,
    extract_recommendations,
    generate_correlation_id,
)


@pytest.fixture
def llm_config():
    """Create test LLM configuration."""
    return {
        "base_url": "https://api.example.com/v1",
        "api_key": "test-key-123",
        "model_name": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 2000,
    }


@pytest.fixture
def mock_tools():
    """Create mock MCP tools."""
    tool1 = Mock()
    tool1.name = "get_pod_details"
    tool1.description = "Get Kubernetes pod details"

    tool2 = Mock()
    tool2.name = "get_pod_logs"
    tool2.description = "Get Kubernetes pod logs"

    return [tool1, tool2]


class TestCreateInvestigationAgent:
    """Tests for create_investigation_agent function."""

    @pytest.mark.asyncio
    async def test_create_agent_success(self, llm_config, mock_tools):
        """Test successful agent creation."""
        with patch("app.core.investigation_agent.ChatOpenAI") as mock_chat:
            with patch(
                "app.core.investigation_agent.create_react_agent"
            ) as mock_create:
                mock_agent = Mock()
                mock_create.return_value = mock_agent

                agent = await create_investigation_agent(
                    mock_tools, llm_config, correlation_id="test-123"
                )

                assert agent == mock_agent
                mock_chat.assert_called_once()
                mock_create.assert_called_once()

                # Verify ChatOpenAI was called with correct config
                call_kwargs = mock_chat.call_args[1]
                assert call_kwargs["base_url"] == llm_config["base_url"]
                assert call_kwargs["api_key"] == llm_config["api_key"]
                assert call_kwargs["model"] == llm_config["model_name"]

    @pytest.mark.asyncio
    async def test_create_agent_missing_base_url(self, mock_tools):
        """Test agent creation with missing base_url."""
        config = {"api_key": "test-key"}

        with pytest.raises(ValueError, match="base_url"):
            await create_investigation_agent(mock_tools, config)

    @pytest.mark.asyncio
    async def test_create_agent_missing_api_key(self, mock_tools):
        """Test agent creation with missing api_key."""
        config = {"base_url": "https://api.example.com"}

        with pytest.raises(ValueError, match="api_key"):
            await create_investigation_agent(mock_tools, config)

    @pytest.mark.asyncio
    async def test_create_agent_with_defaults(self, mock_tools):
        """Test agent creation uses defaults for optional config."""
        config = {"base_url": "https://api.example.com/v1", "api_key": "test-key"}

        with patch("app.core.investigation_agent.ChatOpenAI") as mock_chat:
            with patch("app.core.investigation_agent.create_react_agent"):
                await create_investigation_agent(mock_tools, config)

                call_kwargs = mock_chat.call_args[1]
                assert call_kwargs["model"] == "gpt-4"
                assert call_kwargs["temperature"] == 0.7
                assert call_kwargs["max_tokens"] == 2000


class TestInvestigateIncident:
    """Tests for investigate_incident function."""

    @pytest.fixture
    def mock_agent(self):
        """Create mock agent."""
        agent = AsyncMock()
        return agent

    @pytest.fixture
    def mock_agent_response(self):
        """Create mock agent response."""
        # Create mock messages
        msg1 = Mock()
        msg1.type = "ai"
        msg1.content = "I will investigate this incident."
        msg1.tool_calls = [
            {"name": "get_pod_details", "args": {"pod_name": "test-pod"}}
        ]

        msg2 = Mock()
        msg2.type = "tool"
        msg2.name = "get_pod_details"
        msg2.content = '{"status": "CrashLoopBackOff", "restarts": 5}'

        msg3 = Mock()
        msg3.type = "ai"
        msg3.content = """Based on the evidence, I have determined the root cause.

ROOT CAUSE: Pod is in CrashLoopBackOff due to application startup failure
CONFIDENCE: high
EVIDENCE: Pod has restarted 5 times and is in CrashLoopBackOff status
RECOMMENDATIONS: Check application logs for startup errors, verify configuration, review resource limits"""
        msg3.tool_calls = []

        return {"messages": [msg1, msg2, msg3]}

    @pytest.mark.asyncio
    async def test_investigate_incident_success(self, mock_agent, mock_agent_response):
        """Test successful incident investigation."""
        mock_agent.ainvoke.return_value = mock_agent_response

        result = await investigate_incident(
            mock_agent,
            "incident-123",
            "Pod test-pod is crashing",
            correlation_id="test-123",
        )

        assert result["status"] == "completed"
        assert (
            result["root_cause"]
            == "Pod is in CrashLoopBackOff due to application startup failure"
        )
        assert result["confidence"] == "high"
        assert len(result["evidence"]) > 0
        assert len(result["recommendations"]) > 0
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["tool"] == "get_pod_details"
        assert result["correlation_id"] == "test-123"
        mock_agent.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_investigate_incident_with_callback(
        self, mock_agent, mock_agent_response
    ):
        """Test investigation with status update callback."""
        mock_agent.ainvoke.return_value = mock_agent_response
        callback = AsyncMock()

        result = await investigate_incident(
            mock_agent,
            "incident-123",
            "Pod test-pod is crashing",
            update_callback=callback,
            correlation_id="test-123",
        )

        assert result["status"] == "completed"
        # Callback should be called twice: investigating and completed
        assert callback.call_count == 2

        # Check first call (investigating)
        first_call = callback.call_args_list[0]
        assert first_call[0][0] == "incident-123"
        assert first_call[0][1] == "investigating"

        # Check second call (completed)
        second_call = callback.call_args_list[1]
        assert second_call[0][0] == "incident-123"
        assert second_call[0][1] == "completed"

    @pytest.mark.asyncio
    async def test_investigate_incident_failure(self, mock_agent):
        """Test investigation failure."""
        mock_agent.ainvoke.side_effect = Exception("Agent execution failed")

        result = await investigate_incident(
            mock_agent,
            "incident-123",
            "Pod test-pod is crashing",
            correlation_id="test-123",
        )

        assert result["status"] == "failed"
        assert result["error"] == "Agent execution failed"
        assert result["root_cause"] is None
        assert result["confidence"] is None
        assert result["correlation_id"] == "test-123"

    @pytest.mark.asyncio
    async def test_investigate_incident_with_retry(
        self, mock_agent, mock_agent_response
    ):
        """Test investigation with retry on transient failure."""
        # First call fails, second succeeds
        mock_agent.ainvoke.side_effect = [
            ConnectionError("Temporary failure"),
            mock_agent_response,
        ]

        with patch("time.sleep"):  # Skip actual sleep
            result = await investigate_incident(
                mock_agent,
                "incident-123",
                "Pod test-pod is crashing",
                correlation_id="test-123",
            )

        assert result["status"] == "completed"
        assert mock_agent.ainvoke.call_count == 2

    @pytest.mark.asyncio
    async def test_investigate_incident_generates_correlation_id(
        self, mock_agent, mock_agent_response
    ):
        """Test investigation generates correlation ID if not provided."""
        mock_agent.ainvoke.return_value = mock_agent_response

        result = await investigate_incident(
            mock_agent, "incident-123", "Pod test-pod is crashing"
        )

        assert "correlation_id" in result
        assert result["correlation_id"] is not None
        assert len(result["correlation_id"]) > 0

    @pytest.mark.asyncio
    async def test_investigate_incident_no_response(self, mock_agent):
        """Test investigation with no response from agent."""
        mock_agent.ainvoke.return_value = {"messages": []}

        result = await investigate_incident(
            mock_agent,
            "incident-123",
            "Pod test-pod is crashing",
            correlation_id="test-123",
        )

        assert result["status"] == "failed"
        assert "No response from agent" in result["error"]


class TestExtractionFunctions:
    """Tests for extraction helper functions."""

    def test_extract_root_cause_explicit_marker(self):
        """Test extracting root cause with explicit marker."""
        content = """Analysis complete.

ROOT CAUSE: Pod OOMKilled due to memory limit exceeded

This is the primary issue."""

        result = extract_root_cause(content)
        assert result == "Pod OOMKilled due to memory limit exceeded"

    def test_extract_root_cause_pattern_match(self):
        """Test extracting root cause with pattern matching."""
        content = (
            "The root cause is insufficient memory allocation for the application."
        )

        result = extract_root_cause(content)
        assert "insufficient memory allocation" in result

    def test_extract_root_cause_caused_by_pattern(self):
        """Test extracting root cause with 'caused by' pattern."""
        content = "This issue is caused by network connectivity problems."

        result = extract_root_cause(content)
        assert "network connectivity problems" in result

    def test_extract_root_cause_fallback(self):
        """Test extracting root cause fallback to first sentence."""
        content = "The pod is failing to start. Additional details follow."

        result = extract_root_cause(content)
        assert result == "The pod is failing to start"

    def test_extract_root_cause_empty(self):
        """Test extracting root cause from empty content."""
        result = extract_root_cause("")
        assert result is None

    def test_extract_confidence_explicit_marker(self):
        """Test extracting confidence with explicit marker."""
        content = "CONFIDENCE: high\nThe analysis is complete."

        result = extract_confidence(content)
        assert result == "high"

    def test_extract_confidence_medium_marker(self):
        """Test extracting medium confidence."""
        content = "CONFIDENCE: medium\nMore investigation needed."

        result = extract_confidence(content)
        assert result == "medium"

    def test_extract_confidence_high_indicators(self):
        """Test extracting confidence from high indicators."""
        content = "This is definitely the root cause based on clear evidence."

        result = extract_confidence(content)
        assert result == "high"

    def test_extract_confidence_low_indicators(self):
        """Test extracting confidence from low indicators."""
        content = "This might be the issue, but more investigation is needed."

        result = extract_confidence(content)
        assert result == "low"

    def test_extract_confidence_default(self):
        """Test extracting confidence defaults to medium."""
        content = "The pod is experiencing issues."

        result = extract_confidence(content)
        assert result == "medium"

    def test_extract_evidence_from_tool_calls(self):
        """Test extracting evidence from tool calls."""
        msg1 = Mock()
        msg1.tool_calls = [
            {"name": "get_pod_details", "args": {"pod_name": "test-pod"}}
        ]

        msg2 = Mock()
        msg2.content = '{"status": "Running"}'
        msg2.tool_calls = []

        messages = [msg1, msg2]

        result = extract_evidence(messages)

        assert len(result) == 1
        assert result[0]["source"] == "get_pod_details"
        assert result[0]["args"] == {"pod_name": "test-pod"}
        assert '{"status": "Running"}' in result[0]["content"]

    def test_extract_evidence_from_explicit_marker(self):
        """Test extracting evidence from explicit marker."""
        msg = Mock()
        msg.content = """Analysis:

EVIDENCE: Pod logs show OOM errors and memory usage exceeded limits

RECOMMENDATIONS: Increase memory"""
        msg.tool_calls = []

        messages = [msg]

        result = extract_evidence(messages)

        assert len(result) == 1
        assert result[0]["source"] == "agent_analysis"
        assert "OOM errors" in result[0]["content"]

    def test_extract_recommendations_explicit_marker(self):
        """Test extracting recommendations with explicit marker."""
        content = """ROOT CAUSE: Memory issue

RECOMMENDATIONS:
- Increase memory limits to 2Gi
- Optimize memory usage in application
- Add memory monitoring alerts"""

        result = extract_recommendations(content)

        assert len(result) == 3
        assert "Increase memory limits" in result[0]
        assert "Optimize memory usage" in result[1]
        assert "Add memory monitoring" in result[2]

    def test_extract_recommendations_numbered_list(self):
        """Test extracting recommendations from numbered list."""
        content = """RECOMMENDATIONS:
1. Check application logs
2. Verify configuration
3. Review resource limits"""

        result = extract_recommendations(content)

        assert len(result) == 3
        assert "Check application logs" in result[0]

    def test_extract_recommendations_empty(self):
        """Test extracting recommendations from content without recommendations."""
        content = "ROOT CAUSE: Memory issue\nCONFIDENCE: high"

        result = extract_recommendations(content)

        assert result == []


def test_generate_correlation_id():
    """Test correlation ID generation."""
    id1 = generate_correlation_id()
    id2 = generate_correlation_id()

    assert id1 != id2
    assert len(id1) > 0
    assert len(id2) > 0
