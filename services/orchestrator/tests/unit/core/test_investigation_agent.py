"""Unit tests for investigation agent module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.core.investigation_agent import (
    create_investigation_agent,
    create_investigation_agent_native,
    investigate_incident,
    should_continue,
    create_agent_node,
    create_tool_node_with_logging,
    extract_root_cause,
    extract_confidence,
    extract_evidence,
    extract_recommendations,
    InvestigationState,
)


# ============================================================================
# Agent Creation Tests (Task 4.1)
# ============================================================================


class TestAgentCreation:
    """Tests for create_investigation_agent with valid configuration."""

    @pytest.mark.asyncio
    async def test_create_investigation_agent_with_valid_config(self, mock_llm_config):
        """Test creating investigation agent with valid configuration."""
        # Arrange - Mock ChatOpenAI, bind_tools, and ToolNode
        with patch("app.core.investigation_agent.ChatOpenAI") as mock_chat_class, patch(
            "app.core.investigation_agent.ToolNode"
        ) as mock_tool_node_class:
            mock_llm = Mock()
            mock_chat_class.return_value = mock_llm

            # Mock bind_tools to return a mock LLM
            mock_llm_with_tools = AsyncMock()
            mock_llm.bind_tools = Mock(return_value=mock_llm_with_tools)

            # Mock ToolNode
            mock_tool_node_class.return_value = AsyncMock()

            # Mock tools list
            mock_tools = [Mock(name="get_pod_details")]

            # Act
            agent = await create_investigation_agent(
                mcp_tools=mock_tools,
                llm_config=mock_llm_config,
                correlation_id="test-corr-123",
            )

            # Assert
            assert agent is not None
            assert hasattr(agent, "ainvoke") or hasattr(agent, "invoke")
            mock_llm.bind_tools.assert_called_once_with(mock_tools)

    @pytest.mark.asyncio
    async def test_create_investigation_agent_native_with_valid_config(
        self, mock_llm_config
    ):
        """Test creating native investigation agent with valid configuration."""
        # Arrange
        with patch("app.core.investigation_agent.ChatOpenAI") as mock_chat_class, patch(
            "app.core.investigation_agent.ToolNode"
        ) as mock_tool_node_class:
            mock_llm = Mock()
            mock_chat_class.return_value = mock_llm

            mock_llm_with_tools = AsyncMock()
            mock_llm.bind_tools = Mock(return_value=mock_llm_with_tools)

            # Mock ToolNode
            mock_tool_node_class.return_value = AsyncMock()

            mock_tools = [Mock(name="get_pod_logs")]

            # Act
            agent = await create_investigation_agent_native(
                mcp_tools=mock_tools,
                llm_config=mock_llm_config,
                correlation_id="test-corr-456",
            )

            # Assert
            assert agent is not None
            assert hasattr(agent, "ainvoke")
            mock_llm.bind_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_agent_with_missing_base_url(self, mock_llm_config):
        """Test creating agent with missing base_url raises ValueError."""
        # Arrange
        invalid_config = mock_llm_config.copy()
        del invalid_config["base_url"]

        mock_tools = [Mock()]

        # Act & Assert
        with pytest.raises(ValueError, match="base_url"):
            await create_investigation_agent(
                mcp_tools=mock_tools,
                llm_config=invalid_config,
                correlation_id="test-corr-789",
            )

    @pytest.mark.asyncio
    async def test_create_agent_with_missing_api_key(self, mock_llm_config):
        """Test creating agent with missing api_key raises ValueError."""
        # Arrange
        invalid_config = mock_llm_config.copy()
        del invalid_config["api_key"]

        mock_tools = [Mock()]

        # Act & Assert
        with pytest.raises(ValueError, match="api_key"):
            await create_investigation_agent(
                mcp_tools=mock_tools,
                llm_config=invalid_config,
                correlation_id="test-corr-abc",
            )

    @pytest.mark.asyncio
    async def test_create_agent_with_custom_model_name(self, mock_llm_config):
        """Test creating agent with custom model name."""
        # Arrange
        custom_config = mock_llm_config.copy()
        custom_config["model_name"] = "gpt-3.5-turbo"

        with patch("app.core.investigation_agent.ChatOpenAI") as mock_chat_class, patch(
            "app.core.investigation_agent.ToolNode"
        ) as mock_tool_node_class:
            mock_llm = Mock()
            mock_chat_class.return_value = mock_llm
            mock_llm.bind_tools = Mock(return_value=AsyncMock())

            # Mock ToolNode
            mock_tool_node_class.return_value = AsyncMock()

            mock_tools = [Mock()]

            # Act
            agent = await create_investigation_agent(
                mcp_tools=mock_tools,
                llm_config=custom_config,
                correlation_id="test-corr-custom",
            )

            # Assert
            assert agent is not None
            # Verify ChatOpenAI was called with custom model
            mock_chat_class.assert_called_once()
            call_kwargs = mock_chat_class.call_args[1]
            assert call_kwargs["model"] == "gpt-3.5-turbo"

    @pytest.mark.asyncio
    async def test_create_agent_initializes_with_mcp_tools(self, mock_llm_config):
        """Test agent initialization binds MCP tools correctly."""
        # Arrange
        with patch("app.core.investigation_agent.ChatOpenAI") as mock_chat_class, patch(
            "app.core.investigation_agent.ToolNode"
        ) as mock_tool_node_class:
            mock_llm = Mock()
            mock_chat_class.return_value = mock_llm
            mock_llm.bind_tools = Mock(return_value=AsyncMock())

            # Mock ToolNode
            mock_tool_node_class.return_value = AsyncMock()

            # Multiple mock tools
            mock_tools = [Mock(name=f"tool_{i}") for i in range(3)]

            # Act
            agent = await create_investigation_agent(
                mcp_tools=mock_tools,
                llm_config=mock_llm_config,
                correlation_id="test-corr-tools",
            )

            # Assert
            assert agent is not None
            assert hasattr(agent, "ainvoke")
            # Verify bind_tools was called with all tools
            mock_llm.bind_tools.assert_called_once_with(mock_tools)


# ============================================================================
# Investigation Execution Tests (Task 4.2)
# ============================================================================


class TestInvestigationExecution:
    """Tests for investigate_incident with mocked LLM."""

    @pytest.mark.asyncio
    async def test_investigate_incident_successful_completion(self, mock_llm_config):
        """Test investigate_incident completes successfully with final answer."""
        # Arrange
        with patch("app.core.investigation_agent.ChatOpenAI") as mock_chat_class, patch(
            "app.core.investigation_agent.ToolNode"
        ) as mock_tool_node_class:
            mock_llm = AsyncMock()
            mock_chat_class.return_value = mock_llm
            mock_llm.bind_tools = Mock(return_value=mock_llm)

            # Mock ToolNode
            mock_tool_node_class.return_value = AsyncMock()

            # Mock LLM response with final answer (no tool calls)
            final_response = AIMessage(
                content="""ROOT CAUSE: Memory limit exceeded causing OOMKilled
CONFIDENCE: high
EVIDENCE: Pod logs show OOMKilled status, container restart count is 5
RECOMMENDATIONS: Increase memory limit to 1Gi, add memory request for QoS"""
            )
            mock_llm.ainvoke = AsyncMock(return_value=final_response)

            # Create agent
            agent = await create_investigation_agent(
                mcp_tools=[Mock()],
                llm_config=mock_llm_config,
                correlation_id="test-exec-001",
            )

            # Act
            result = await investigate_incident(
                agent=agent,
                incident_id="inc-test-001",
                description="Pod nginx-deployment-abc123 is in CrashLoopBackOff",
                correlation_id="test-exec-001",
            )

            # Assert
            assert result["status"] == "completed"
            assert result["root_cause"] is not None
            assert result["confidence"] in ["high", "medium", "low"]
            assert "correlation_id" in result
            assert result["correlation_id"] == "test-exec-001"

    @pytest.mark.asyncio
    async def test_investigate_incident_with_tool_calls(self, mock_llm_config):
        """Test investigate_incident executes tool calls correctly."""
        # Arrange
        with patch("app.core.investigation_agent.ChatOpenAI") as mock_chat_class, patch(
            "app.core.investigation_agent.ToolNode"
        ) as mock_tool_node_class:
            mock_llm = AsyncMock()
            mock_chat_class.return_value = mock_llm
            mock_llm.bind_tools = Mock(return_value=mock_llm)

            # Mock ToolNode
            mock_tool_node_class.return_value = AsyncMock()

            # First response with tool call
            tool_call_response = AIMessage(
                content="I need to check the pod details.",
                tool_calls=[
                    {
                        "id": "call_123",
                        "name": "get_pod_details",
                        "args": {"pod_name": "nginx-deployment-abc123"},
                    }
                ],
            )

            # Second response with final answer
            final_response = AIMessage(
                content="""ROOT CAUSE: Pod is crashing due to configuration error
CONFIDENCE: high
EVIDENCE: Pod details show invalid configuration
RECOMMENDATIONS: Fix the configuration and redeploy"""
            )

            mock_llm.ainvoke = AsyncMock(
                side_effect=[tool_call_response, final_response]
            )

            agent = await create_investigation_agent(
                mcp_tools=[Mock()],
                llm_config=mock_llm_config,
                correlation_id="test-exec-002",
            )

            # Act
            result = await investigate_incident(
                agent=agent,
                incident_id="inc-test-002",
                description="Pod is crashing",
                correlation_id="test-exec-002",
            )

            # Assert
            assert result["status"] == "completed"
            assert len(result["tool_calls"]) > 0
            assert result["tool_calls"][0]["tool"] == "get_pod_details"

    @pytest.mark.asyncio
    async def test_investigate_incident_parses_final_results(self, mock_llm_config):
        """Test investigate_incident correctly parses structured results."""
        # Arrange
        with patch("app.core.investigation_agent.ChatOpenAI") as mock_chat_class, patch(
            "app.core.investigation_agent.ToolNode"
        ) as mock_tool_node_class:
            mock_llm = AsyncMock()
            mock_chat_class.return_value = mock_llm
            mock_llm.bind_tools = Mock(return_value=mock_llm)

            # Mock ToolNode
            mock_tool_node_class.return_value = AsyncMock()

            final_response = AIMessage(
                content="""ROOT CAUSE: Memory exhaustion in container
CONFIDENCE: high
EVIDENCE: OOMKilled events, high memory usage metrics
RECOMMENDATIONS: Increase memory limit to 2Gi, optimize application memory usage"""
            )
            mock_llm.ainvoke = AsyncMock(return_value=final_response)

            agent = await create_investigation_agent(
                mcp_tools=[Mock()],
                llm_config=mock_llm_config,
                correlation_id="test-exec-003",
            )

            # Act
            result = await investigate_incident(
                agent=agent,
                incident_id="inc-test-003",
                description="Container OOMKilled",
                correlation_id="test-exec-003",
            )

            # Assert
            assert result["status"] == "completed"
            assert "Memory exhaustion" in result["root_cause"]
            assert result["confidence"] == "high"
            assert len(result["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_investigate_incident_handles_llm_errors(self, mock_llm_config):
        """Test investigate_incident handles LLM errors gracefully."""
        # Arrange
        with patch("app.core.investigation_agent.ChatOpenAI") as mock_chat_class, patch(
            "app.core.investigation_agent.ToolNode"
        ) as mock_tool_node_class:
            mock_llm = AsyncMock()
            mock_chat_class.return_value = mock_llm
            mock_llm.bind_tools = Mock(return_value=mock_llm)

            # Mock ToolNode
            mock_tool_node_class.return_value = AsyncMock()

            # Simulate LLM error - the agent will retry 3 times then fail
            mock_llm.ainvoke = AsyncMock(side_effect=Exception("LLM API timeout"))

            agent = await create_investigation_agent(
                mcp_tools=[Mock()],
                llm_config=mock_llm_config,
                correlation_id="test-exec-004",
            )

            # Act
            result = await investigate_incident(
                agent=agent,
                incident_id="inc-test-004",
                description="Test incident",
                correlation_id="test-exec-004",
            )

            # Assert
            # The agent retries and eventually completes
            # Even with LLM errors, the investigation completes (with fallback behavior)
            assert result["status"] == "completed"
            # The correlation_id should be preserved
            assert result["correlation_id"] == "test-exec-004"
            # Tool calls should be empty since LLM never succeeded
            assert len(result["tool_calls"]) == 0


# ============================================================================
# Routing and State Management Tests (Task 4.3)
# ============================================================================


class TestRoutingAndStateManagement:
    """Tests for routing logic and state management."""

    def test_should_continue_routes_to_tools_with_tool_calls(self):
        """Test should_continue routes to 'tools' when message has tool calls."""
        # Arrange
        message_with_tools = AIMessage(
            content="Let me check the pod.",
            tool_calls=[
                {
                    "id": "call_abc",
                    "name": "get_pod_details",
                    "args": {"pod_name": "test-pod"},
                }
            ],
        )

        state: InvestigationState = {
            "messages": [message_with_tools],
            "incident_id": "inc-123",
            "correlation_id": "corr-456",
            "investigation_status": "in_progress",
        }

        # Act
        result = should_continue(state)

        # Assert
        assert result == "tools"

    def test_should_continue_routes_to_end_without_tool_calls(self):
        """Test should_continue routes to 'end' when message has no tool calls."""
        # Arrange
        final_message = AIMessage(
            content="ROOT CAUSE: Configuration error. CONFIDENCE: high"
        )

        state: InvestigationState = {
            "messages": [final_message],
            "incident_id": "inc-789",
            "correlation_id": "corr-abc",
            "investigation_status": "in_progress",
        }

        # Act
        result = should_continue(state)

        # Assert
        assert result == "end"

    def test_should_continue_with_multiple_tool_calls(self):
        """Test should_continue handles multiple tool calls correctly."""
        # Arrange
        message_with_multiple_tools = AIMessage(
            content="Gathering comprehensive data.",
            tool_calls=[
                {"id": "call_1", "name": "get_pod_details", "args": {}},
                {"id": "call_2", "name": "get_pod_logs", "args": {}},
                {"id": "call_3", "name": "get_events", "args": {}},
            ],
        )

        state: InvestigationState = {
            "messages": [message_with_multiple_tools],
            "incident_id": "inc-multi",
            "correlation_id": "corr-multi",
            "investigation_status": "in_progress",
        }

        # Act
        result = should_continue(state)

        # Assert
        assert result == "tools"

    @pytest.mark.asyncio
    async def test_agent_node_updates_state_correctly(self):
        """Test agent_node updates investigation state with LLM response."""
        # Arrange
        mock_llm = AsyncMock()
        mock_response = AIMessage(content="Analysis in progress")
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        agent_node = create_agent_node(mock_llm)

        state: InvestigationState = {
            "messages": [HumanMessage(content="Investigate this incident")],
            "incident_id": "inc-node-test",
            "correlation_id": "corr-node-test",
            "investigation_status": "in_progress",
        }

        # Act
        result = await agent_node(state)

        # Assert
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert result["messages"][0].content == "Analysis in progress"

    @pytest.mark.asyncio
    async def test_agent_node_handles_errors_gracefully(self):
        """Test agent_node handles LLM errors and updates status."""
        # Arrange
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=Exception("LLM failure"))

        agent_node = create_agent_node(mock_llm)

        state: InvestigationState = {
            "messages": [HumanMessage(content="Test")],
            "incident_id": "inc-error",
            "correlation_id": "corr-error",
            "investigation_status": "in_progress",
        }

        # Act
        result = await agent_node(state)

        # Assert
        assert result["investigation_status"] == "failed"

    @pytest.mark.asyncio
    async def test_tool_node_executes_tools_and_updates_messages(self):
        """Test tool_node executes tools and adds results to messages."""
        # Arrange - Mock ToolNode at the module level
        with patch("app.core.investigation_agent.ToolNode") as mock_tool_node_class:
            mock_tool_node_instance = AsyncMock()
            mock_tool_node_class.return_value = mock_tool_node_instance

            # Mock tool execution result
            mock_tool_node_instance.ainvoke = AsyncMock(
                return_value={
                    "messages": [
                        ToolMessage(
                            content='{"status": "Running"}',
                            tool_call_id="call_xyz",
                            name="get_pod_details",
                        )
                    ]
                }
            )

            tool_node = create_tool_node_with_logging([Mock()])

            # Create a message with tool calls
            message_with_tool_call = AIMessage(
                content="Checking pod",
                tool_calls=[
                    {
                        "id": "call_xyz",
                        "name": "get_pod_details",
                        "args": {"pod_name": "test-pod"},
                    }
                ],
            )

            state: InvestigationState = {
                "messages": [message_with_tool_call],
                "incident_id": "inc-tool-test",
                "correlation_id": "corr-tool-test",
                "investigation_status": "in_progress",
            }

            # Act
            result = await tool_node(state)

            # Assert
            assert "messages" in result
            assert len(result["messages"]) > 0

    @pytest.mark.asyncio
    async def test_tool_node_handles_no_tool_calls(self):
        """Test tool_node handles state with no tool calls."""
        # Arrange
        with patch("app.core.investigation_agent.ToolNode"):
            tool_node = create_tool_node_with_logging([Mock()])

            # Message without tool calls
            message_without_tools = AIMessage(content="Final answer")

            state: InvestigationState = {
                "messages": [message_without_tools],
                "incident_id": "inc-no-tools",
                "correlation_id": "corr-no-tools",
                "investigation_status": "in_progress",
            }

            # Act
            result = await tool_node(state)

            # Assert
            assert "messages" in result
            assert len(result["messages"]) == 0


# ============================================================================
# Helper Function Tests
# ============================================================================


class TestHelperFunctions:
    """Tests for helper functions used in investigation."""

    def test_extract_root_cause_with_explicit_marker(self):
        """Test extracting root cause with explicit ROOT CAUSE marker."""
        # Arrange
        content = """ROOT CAUSE: Memory limit exceeded

Additional analysis here."""

        # Act
        result = extract_root_cause(content)

        # Assert
        assert result == "Memory limit exceeded"

    def test_extract_root_cause_with_pattern(self):
        """Test extracting root cause using pattern matching."""
        # Arrange
        content = "The root cause is a configuration error in the deployment."

        # Act
        result = extract_root_cause(content)

        # Assert
        assert "configuration error" in result.lower()

    def test_extract_root_cause_returns_none_for_empty(self):
        """Test extract_root_cause returns None for empty content."""
        # Act
        result = extract_root_cause("")

        # Assert
        assert result is None

    def test_extract_confidence_with_explicit_marker(self):
        """Test extracting confidence with explicit CONFIDENCE marker."""
        # Arrange
        content = "CONFIDENCE: high\nOther content here"

        # Act
        result = extract_confidence(content)

        # Assert
        assert result == "high"

    def test_extract_confidence_defaults_to_medium(self):
        """Test extract_confidence defaults to medium without markers."""
        # Arrange
        content = "Some analysis without confidence indicators"

        # Act
        result = extract_confidence(content)

        # Assert
        assert result == "medium"

    def test_extract_confidence_detects_high_indicators(self):
        """Test extract_confidence detects high confidence indicators."""
        # Arrange
        content = "This is definitely the root cause based on clear evidence."

        # Act
        result = extract_confidence(content)

        # Assert
        assert result == "high"

    def test_extract_confidence_detects_low_indicators(self):
        """Test extract_confidence detects low confidence indicators."""
        # Arrange
        content = "This might be the issue, but I'm uncertain."

        # Act
        result = extract_confidence(content)

        # Assert
        assert result == "low"

    def test_extract_evidence_from_tool_calls(self):
        """Test extracting evidence from tool call messages."""
        # Arrange
        tool_call_msg = AIMessage(
            content="Checking pod",
            tool_calls=[
                {
                    "id": "call_1",
                    "name": "get_pod_details",
                    "args": {"pod_name": "test-pod"},
                }
            ],
        )
        tool_response_msg = ToolMessage(
            content='{"status": "CrashLoopBackOff"}',
            tool_call_id="call_1",
            name="get_pod_details",
        )

        messages = [tool_call_msg, tool_response_msg]

        # Act
        result = extract_evidence(messages)

        # Assert
        assert len(result) > 0
        assert result[0]["source"] == "get_pod_details"

    def test_extract_evidence_from_explicit_marker(self):
        """Test extracting evidence from EVIDENCE marker in content."""
        # Arrange
        analysis_msg = AIMessage(
            content="""EVIDENCE: Pod logs show OOMKilled, restart count is 5

RECOMMENDATIONS: Increase memory"""
        )

        messages = [analysis_msg]

        # Act
        result = extract_evidence(messages)

        # Assert
        assert len(result) > 0
        assert any("OOMKilled" in str(e["content"]) for e in result)

    def test_extract_recommendations_with_explicit_marker(self):
        """Test extracting recommendations with RECOMMENDATIONS marker."""
        # Arrange
        content = """RECOMMENDATIONS:
- Increase memory limit to 1Gi
- Add memory request for QoS
- Monitor memory usage patterns"""

        # Act
        result = extract_recommendations(content)

        # Assert
        assert len(result) >= 2
        assert any("memory limit" in r.lower() for r in result)

    def test_extract_recommendations_returns_empty_for_none(self):
        """Test extract_recommendations returns empty list for no recommendations."""
        # Arrange
        content = "Analysis without recommendations"

        # Act
        result = extract_recommendations(content)

        # Assert
        assert result == []
