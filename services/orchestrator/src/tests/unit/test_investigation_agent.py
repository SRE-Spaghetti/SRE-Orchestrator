"""
Unit tests for the investigation agent module.

This module tests the core components of the investigation agent including:
- State schema
- Routing logic
- Agent node execution
- Helper functions
"""

import pytest
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.core.investigation_agent import (
    should_continue,
    extract_root_cause,
    extract_confidence,
    extract_evidence,
    extract_recommendations,
)


class TestShouldContinueRouting:
    """Test suite for the should_continue routing function."""

    def test_should_continue_with_tool_calls(self):
        """Test routing when LLM requests tools - returns 'tools'."""
        # Create a message with tool calls
        ai_message = AIMessage(
            content="I need to check the pod status",
            tool_calls=[
                {
                    "name": "get_pod_details",
                    "args": {"pod_name": "test-pod"},
                    "id": "call_123",
                }
            ],
        )

        state = {
            "messages": [ai_message],
            "incident_id": "inc-123",
            "correlation_id": "corr-456",
            "investigation_status": "in_progress",
        }

        result = should_continue(state)
        assert result == "tools"

    def test_should_continue_without_tool_calls(self):
        """Test routing when LLM provides final answer - returns 'end'."""
        # Create a message without tool calls
        ai_message = AIMessage(content="ROOT CAUSE: Memory leak in application")

        state = {
            "messages": [ai_message],
            "incident_id": "inc-123",
            "correlation_id": "corr-456",
            "investigation_status": "in_progress",
        }

        result = should_continue(state)
        assert result == "end"

    def test_should_continue_with_empty_tool_calls(self):
        """Test routing when tool_calls attribute exists but is empty."""
        # Create a message with empty tool calls list
        ai_message = AIMessage(content="Analysis complete", tool_calls=[])

        state = {
            "messages": [ai_message],
            "incident_id": "inc-123",
            "correlation_id": "corr-456",
            "investigation_status": "in_progress",
        }

        result = should_continue(state)
        assert result == "end"

    def test_should_continue_with_empty_messages(self):
        """Test routing with empty messages list."""
        # This is an edge case that shouldn't happen in practice
        # but we should handle it gracefully
        state = {
            "messages": [],
            "incident_id": "inc-123",
            "correlation_id": "corr-456",
            "investigation_status": "in_progress",
        }

        # Should raise IndexError or handle gracefully
        # In the current implementation, this will raise IndexError
        # which is acceptable for an invalid state
        with pytest.raises(IndexError):
            should_continue(state)

    def test_should_continue_with_multiple_tool_calls(self):
        """Test routing when LLM requests multiple tools."""
        # Create a message with multiple tool calls
        ai_message = AIMessage(
            content="I need to gather more information",
            tool_calls=[
                {
                    "name": "get_pod_details",
                    "args": {"pod_name": "test-pod"},
                    "id": "call_123",
                },
                {
                    "name": "get_pod_logs",
                    "args": {"pod_name": "test-pod"},
                    "id": "call_124",
                },
            ],
        )

        state = {
            "messages": [ai_message],
            "incident_id": "inc-123",
            "correlation_id": "corr-456",
            "investigation_status": "in_progress",
        }

        result = should_continue(state)
        assert result == "tools"

    def test_should_continue_with_message_history(self):
        """Test routing with multiple messages in history."""
        # Create a conversation with multiple messages
        human_message = HumanMessage(content="Pod is crashing")
        ai_message_1 = AIMessage(
            content="Let me check the pod",
            tool_calls=[{"name": "get_pod_details", "args": {}, "id": "call_1"}],
        )
        tool_message = ToolMessage(
            content="Pod status: CrashLoopBackOff", tool_call_id="call_1"
        )
        ai_message_2 = AIMessage(content="ROOT CAUSE: Application crash")

        state = {
            "messages": [human_message, ai_message_1, tool_message, ai_message_2],
            "incident_id": "inc-123",
            "correlation_id": "corr-456",
            "investigation_status": "in_progress",
        }

        # Should route based on the last message (ai_message_2)
        result = should_continue(state)
        assert result == "end"

    def test_should_continue_without_correlation_id(self):
        """Test routing when correlation_id is missing."""
        ai_message = AIMessage(content="Final answer")

        state = {
            "messages": [ai_message],
            "incident_id": "inc-123",
            "investigation_status": "in_progress",
        }

        # Should still work without correlation_id
        result = should_continue(state)
        assert result == "end"

    def test_should_continue_without_incident_id(self):
        """Test routing when incident_id is missing."""
        ai_message = AIMessage(
            content="", tool_calls=[{"name": "get_pod", "args": {}, "id": "call_1"}]
        )

        state = {
            "messages": [ai_message],
            "correlation_id": "corr-456",
            "investigation_status": "in_progress",
        }

        # Should still work without incident_id
        result = should_continue(state)
        assert result == "tools"

    def test_should_continue_logging(self, caplog):
        """Test that routing function logs decisions correctly."""
        import logging

        caplog.set_level(logging.INFO)

        # Test routing to tools
        ai_message_tools = AIMessage(
            content="Checking pod",
            tool_calls=[{"name": "get_pod", "args": {}, "id": "call_1"}],
        )

        state_tools = {
            "messages": [ai_message_tools],
            "incident_id": "inc-123",
            "correlation_id": "corr-456",
            "investigation_status": "in_progress",
        }

        result = should_continue(state_tools)
        assert result == "tools"

        # Check that logging occurred with correlation ID
        assert any(
            "Routing to tools node" in record.message for record in caplog.records
        )
        assert any(
            "corr-456" in str(record.__dict__.get("correlation_id", ""))
            for record in caplog.records
        )

        caplog.clear()

        # Test routing to end
        ai_message_end = AIMessage(content="Final answer")

        state_end = {
            "messages": [ai_message_end],
            "incident_id": "inc-123",
            "correlation_id": "corr-789",
            "investigation_status": "in_progress",
        }

        result = should_continue(state_end)
        assert result == "end"

        # Check that logging occurred with correlation ID
        assert any("Routing to end" in record.message for record in caplog.records)
        assert any(
            "corr-789" in str(record.__dict__.get("correlation_id", ""))
            for record in caplog.records
        )


class TestInvestigationState:
    """Test suite for the InvestigationState schema."""

    def test_investigation_state_creation_with_all_fields(self):
        """Test that InvestigationState can be created with all required fields."""
        state = {
            "messages": [HumanMessage(content="Test incident")],
            "incident_id": "inc-123",
            "correlation_id": "corr-456",
            "investigation_status": "in_progress",
        }

        # Verify all fields are accessible
        assert state["messages"] is not None
        assert len(state["messages"]) == 1
        assert state["incident_id"] == "inc-123"
        assert state["correlation_id"] == "corr-456"
        assert state["investigation_status"] == "in_progress"

    def test_investigation_state_with_multiple_messages(self):
        """Test InvestigationState with multiple messages."""
        messages = [
            HumanMessage(content="Pod is crashing"),
            AIMessage(content="Let me investigate"),
            ToolMessage(content="Pod status: CrashLoopBackOff", tool_call_id="call_1"),
        ]

        state = {
            "messages": messages,
            "incident_id": "inc-456",
            "correlation_id": "corr-789",
            "investigation_status": "in_progress",
        }

        assert len(state["messages"]) == 3
        assert isinstance(state["messages"][0], HumanMessage)
        assert isinstance(state["messages"][1], AIMessage)
        assert isinstance(state["messages"][2], ToolMessage)

    def test_investigation_state_partial_update(self):
        """Test that state can be partially updated."""
        state = {
            "messages": [HumanMessage(content="Test")],
            "incident_id": "inc-123",
            "correlation_id": "corr-456",
            "investigation_status": "in_progress",
        }

        # Simulate partial state update
        update = {"investigation_status": "completed"}
        state.update(update)

        assert state["investigation_status"] == "completed"
        assert state["incident_id"] == "inc-123"  # Other fields unchanged
        assert state["correlation_id"] == "corr-456"  # Other fields unchanged

    def test_investigation_state_add_messages_behavior(self):
        """Test add_messages reducer behavior by simulating message appending."""
        # Initial state
        state = {
            "messages": [HumanMessage(content="Initial message")],
            "incident_id": "inc-123",
            "correlation_id": "corr-456",
            "investigation_status": "in_progress",
        }

        # Simulate what add_messages reducer does - append new messages
        new_message = AIMessage(content="Agent response")
        state["messages"] = state["messages"] + [new_message]

        assert len(state["messages"]) == 2
        assert state["messages"][0].content == "Initial message"
        assert state["messages"][1].content == "Agent response"

        # Add another message
        tool_message = ToolMessage(content="Tool result", tool_call_id="call_1")
        state["messages"] = state["messages"] + [tool_message]

        assert len(state["messages"]) == 3
        assert isinstance(state["messages"][2], ToolMessage)

    def test_investigation_state_empty_messages(self):
        """Test InvestigationState with empty messages list."""
        state = {
            "messages": [],
            "incident_id": "inc-123",
            "correlation_id": "corr-456",
            "investigation_status": "in_progress",
        }

        assert state["messages"] == []
        assert len(state["messages"]) == 0

    def test_investigation_state_different_statuses(self):
        """Test InvestigationState with different status values."""
        statuses = ["in_progress", "completed", "failed"]

        for status in statuses:
            state = {
                "messages": [HumanMessage(content="Test")],
                "incident_id": "inc-123",
                "correlation_id": "corr-456",
                "investigation_status": status,
            }

            assert state["investigation_status"] == status

    def test_investigation_state_message_update_preserves_other_fields(self):
        """Test that updating messages preserves other state fields."""
        state = {
            "messages": [HumanMessage(content="Initial")],
            "incident_id": "inc-123",
            "correlation_id": "corr-456",
            "investigation_status": "in_progress",
        }

        # Update only messages
        state["messages"] = state["messages"] + [AIMessage(content="Response")]

        # Verify other fields are unchanged
        assert state["incident_id"] == "inc-123"
        assert state["correlation_id"] == "corr-456"
        assert state["investigation_status"] == "in_progress"
        assert len(state["messages"]) == 2


class TestHelperFunctions:
    """Test suite for helper functions."""

    def test_extract_root_cause_with_marker(self):
        """Test extracting root cause with explicit marker."""
        content = "ROOT CAUSE: Memory leak in application"
        result = extract_root_cause(content)
        assert result == "Memory leak in application"

    def test_extract_confidence_with_marker(self):
        """Test extracting confidence with explicit marker."""
        content = "CONFIDENCE: high"
        result = extract_confidence(content)
        assert result == "high"

    def test_extract_confidence_default(self):
        """Test confidence defaults to medium when not specified."""
        content = "Some analysis without confidence marker"
        result = extract_confidence(content)
        assert result == "medium"

    def test_extract_recommendations_with_marker(self):
        """Test extracting recommendations with explicit marker."""
        content = "RECOMMENDATIONS:\n- Increase memory limit\n- Add health checks"
        result = extract_recommendations(content)
        assert len(result) > 0

    def test_extract_evidence_from_messages(self):
        """Test extracting evidence from message history."""
        messages = [
            AIMessage(
                content="Let me check",
                tool_calls=[{"name": "get_pod", "args": {}, "id": "call_1"}],
            ),
            ToolMessage(content="Pod status: CrashLoopBackOff", tool_call_id="call_1"),
        ]
        result = extract_evidence(messages)
        assert len(result) > 0


class TestAgentNode:
    """Test suite for the agent node function."""

    @pytest.mark.asyncio
    async def test_agent_node_with_mock_llm(self):
        """Test agent node execution with mock LLM."""
        from unittest.mock import AsyncMock
        from app.core.investigation_agent import create_agent_node

        # Create mock LLM
        mock_llm = AsyncMock()
        mock_response = AIMessage(content="I will investigate this issue")
        mock_llm.ainvoke.return_value = mock_response

        # Create agent node
        agent_node = create_agent_node(mock_llm)

        # Create test state
        state = {
            "messages": [HumanMessage(content="Pod is crashing")],
            "incident_id": "inc-123",
            "correlation_id": "corr-456",
            "investigation_status": "in_progress",
        }

        # Execute agent node
        result = await agent_node(state)

        # Verify result
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert result["messages"][0] == mock_response
        mock_llm.ainvoke.assert_called_once_with(state["messages"])

    @pytest.mark.asyncio
    async def test_agent_node_with_tool_calls(self):
        """Test agent node when LLM requests tool calls."""
        from unittest.mock import AsyncMock
        from app.core.investigation_agent import create_agent_node

        # Create mock LLM that returns tool calls
        mock_llm = AsyncMock()
        mock_response = AIMessage(
            content="Let me check the pod",
            tool_calls=[
                {
                    "name": "get_pod_details",
                    "args": {"pod_name": "test-pod"},
                    "id": "call_1",
                }
            ],
        )
        mock_llm.ainvoke.return_value = mock_response

        # Create agent node
        agent_node = create_agent_node(mock_llm)

        # Create test state
        state = {
            "messages": [HumanMessage(content="Pod is crashing")],
            "incident_id": "inc-123",
            "correlation_id": "corr-456",
            "investigation_status": "in_progress",
        }

        # Execute agent node
        result = await agent_node(state)

        # Verify result contains tool calls
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert hasattr(result["messages"][0], "tool_calls")
        assert len(result["messages"][0].tool_calls) == 1
        assert result["messages"][0].tool_calls[0]["name"] == "get_pod_details"

    @pytest.mark.asyncio
    async def test_agent_node_error_handling(self):
        """Test agent node error handling when LLM fails."""
        from unittest.mock import AsyncMock
        from app.core.investigation_agent import create_agent_node

        # Create mock LLM that raises an exception
        mock_llm = AsyncMock()
        mock_llm.ainvoke.side_effect = Exception("LLM API error")

        # Create agent node
        agent_node = create_agent_node(mock_llm)

        # Create test state
        state = {
            "messages": [HumanMessage(content="Pod is crashing")],
            "incident_id": "inc-123",
            "correlation_id": "corr-456",
            "investigation_status": "in_progress",
        }

        # Execute agent node
        result = await agent_node(state)

        # Verify error handling
        assert "investigation_status" in result
        assert result["investigation_status"] == "failed"
        assert "messages" in result
        assert result["messages"] == []

    @pytest.mark.asyncio
    async def test_agent_node_logging(self, caplog):
        """Test that agent node logs execution correctly."""
        import logging
        from unittest.mock import AsyncMock
        from app.core.investigation_agent import create_agent_node

        caplog.set_level(logging.INFO)

        # Create mock LLM
        mock_llm = AsyncMock()
        mock_response = AIMessage(content="Investigation complete")
        mock_llm.ainvoke.return_value = mock_response

        # Create agent node
        agent_node = create_agent_node(mock_llm)

        # Create test state
        state = {
            "messages": [HumanMessage(content="Pod is crashing")],
            "incident_id": "inc-123",
            "correlation_id": "corr-456",
            "investigation_status": "in_progress",
        }

        # Execute agent node
        await agent_node(state)

        # Verify logging occurred
        assert any(
            "Agent node executing" in record.message for record in caplog.records
        )
        assert any(
            "Agent node completed successfully" in record.message
            for record in caplog.records
        )
        assert any(
            "corr-456" in str(record.__dict__.get("correlation_id", ""))
            for record in caplog.records
        )
        assert any(
            "inc-123" in str(record.__dict__.get("incident_id", ""))
            for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_agent_node_retry_logic(self):
        """Test agent node retry logic on transient failures."""
        from unittest.mock import AsyncMock
        from app.core.investigation_agent import create_agent_node

        # Create mock LLM that fails once then succeeds
        mock_llm = AsyncMock()
        mock_response = AIMessage(content="Success after retry")
        mock_llm.ainvoke.side_effect = [
            ConnectionError("Temporary failure"),
            mock_response,
        ]

        # Create agent node
        agent_node = create_agent_node(mock_llm)

        # Create test state
        state = {
            "messages": [HumanMessage(content="Pod is crashing")],
            "incident_id": "inc-123",
            "correlation_id": "corr-456",
            "investigation_status": "in_progress",
        }

        # Execute agent node - retry logic should handle the first failure
        result = await agent_node(state)

        # Verify success after retry
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert result["messages"][0].content == "Success after retry"
        assert mock_llm.ainvoke.call_count == 2

    @pytest.mark.asyncio
    async def test_agent_node_with_message_history(self):
        """Test agent node with existing message history."""
        from unittest.mock import AsyncMock
        from app.core.investigation_agent import create_agent_node

        # Create mock LLM
        mock_llm = AsyncMock()
        mock_response = AIMessage(content="Based on the logs, the issue is clear")
        mock_llm.ainvoke.return_value = mock_response

        # Create agent node
        agent_node = create_agent_node(mock_llm)

        # Create test state with message history
        state = {
            "messages": [
                HumanMessage(content="Pod is crashing"),
                AIMessage(
                    content="Let me check",
                    tool_calls=[{"name": "get_pod", "args": {}, "id": "call_1"}],
                ),
                ToolMessage(
                    content="Pod status: CrashLoopBackOff", tool_call_id="call_1"
                ),
            ],
            "incident_id": "inc-123",
            "correlation_id": "corr-456",
            "investigation_status": "in_progress",
        }

        # Execute agent node
        result = await agent_node(state)

        # Verify LLM was called with full message history
        mock_llm.ainvoke.assert_called_once_with(state["messages"])
        assert len(result["messages"]) == 1

    @pytest.mark.asyncio
    async def test_agent_node_error_logging(self, caplog):
        """Test that agent node logs errors correctly."""
        import logging
        from unittest.mock import AsyncMock
        from app.core.investigation_agent import create_agent_node

        caplog.set_level(logging.ERROR)

        # Create mock LLM that raises an exception
        mock_llm = AsyncMock()
        mock_llm.ainvoke.side_effect = ValueError("Invalid input")

        # Create agent node
        agent_node = create_agent_node(mock_llm)

        # Create test state
        state = {
            "messages": [HumanMessage(content="Pod is crashing")],
            "incident_id": "inc-123",
            "correlation_id": "corr-456",
            "investigation_status": "in_progress",
        }

        # Execute agent node
        await agent_node(state)

        # Verify error logging
        assert any("Agent node failed" in record.message for record in caplog.records)
        assert any(
            "corr-456" in str(record.__dict__.get("correlation_id", ""))
            for record in caplog.records
        )


class TestNativeGraphConstruction:
    """Test suite for native LangGraph construction."""

    @pytest.mark.asyncio
    async def test_create_investigation_agent_native_success(self):
        """Test successful creation of native LangGraph agent."""
        from unittest.mock import AsyncMock, patch
        from app.core.investigation_agent import create_investigation_agent_native

        # Mock tools
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mcp_tools = [mock_tool]

        # LLM config
        llm_config = {
            "base_url": "http://test-llm.com",
            "api_key": "test-key",
            "model_name": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        # Mock ChatOpenAI to avoid actual LLM initialization
        with patch(
            "app.core.investigation_agent.ChatOpenAI"
        ) as mock_chat_openai, patch(
            "app.core.investigation_agent.create_agent_node"
        ) as mock_create_agent_node, patch(
            "app.core.investigation_agent.create_tool_node_with_logging"
        ) as mock_create_tool_node:

            mock_llm = MagicMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_chat_openai.return_value = mock_llm

            # Mock the node creation functions
            mock_agent_node = AsyncMock()
            mock_tool_node = AsyncMock()
            mock_create_agent_node.return_value = mock_agent_node
            mock_create_tool_node.return_value = mock_tool_node

            # Create the agent
            agent = await create_investigation_agent_native(
                mcp_tools=mcp_tools,
                llm_config=llm_config,
                correlation_id="test-corr-123",
            )

            # Verify agent was created
            assert agent is not None

            # Verify ChatOpenAI was called with correct parameters
            mock_chat_openai.assert_called_once_with(
                base_url="http://test-llm.com",
                api_key="test-key",
                model="gpt-4",
                temperature=0.7,
                max_tokens=2000,
            )

            # Verify bind_tools was called
            mock_llm.bind_tools.assert_called_once_with(mcp_tools)

            # Verify node creation functions were called
            mock_create_agent_node.assert_called_once()
            mock_create_tool_node.assert_called_once_with(mcp_tools)

    @pytest.mark.asyncio
    async def test_create_investigation_agent_native_missing_base_url(self):
        """Test that missing base_url raises ValueError."""
        from app.core.investigation_agent import create_investigation_agent_native

        llm_config = {"api_key": "test-key"}

        with pytest.raises(
            ValueError, match="llm_config missing required key: base_url"
        ):
            await create_investigation_agent_native(mcp_tools=[], llm_config=llm_config)

    @pytest.mark.asyncio
    async def test_create_investigation_agent_native_missing_api_key(self):
        """Test that missing api_key raises ValueError."""
        from app.core.investigation_agent import create_investigation_agent_native

        llm_config = {"base_url": "http://test-llm.com"}

        with pytest.raises(
            ValueError, match="llm_config missing required key: api_key"
        ):
            await create_investigation_agent_native(mcp_tools=[], llm_config=llm_config)

    @pytest.mark.asyncio
    async def test_create_investigation_agent_native_with_defaults(self):
        """Test that default values are used when not specified."""
        from unittest.mock import patch, AsyncMock
        from app.core.investigation_agent import create_investigation_agent_native

        llm_config = {
            "base_url": "http://test-llm.com",
            "api_key": "test-key",
            # No model_name, temperature, or max_tokens
        }

        with patch(
            "app.core.investigation_agent.ChatOpenAI"
        ) as mock_chat_openai, patch(
            "app.core.investigation_agent.create_agent_node"
        ) as mock_create_agent_node, patch(
            "app.core.investigation_agent.create_tool_node_with_logging"
        ) as mock_create_tool_node:

            mock_llm = MagicMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_chat_openai.return_value = mock_llm

            # Mock the node creation functions
            mock_agent_node = AsyncMock()
            mock_tool_node = AsyncMock()
            mock_create_agent_node.return_value = mock_agent_node
            mock_create_tool_node.return_value = mock_tool_node

            await create_investigation_agent_native(mcp_tools=[], llm_config=llm_config)

            # Verify defaults were used
            mock_chat_openai.assert_called_once_with(
                base_url="http://test-llm.com",
                api_key="test-key",
                model="gpt-4",  # default
                temperature=0.7,  # default
                max_tokens=2000,  # default
            )
