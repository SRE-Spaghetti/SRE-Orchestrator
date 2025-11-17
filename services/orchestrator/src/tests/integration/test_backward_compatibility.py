"""
Tests for native LangGraph implementation.

This module tests that the native LangGraph implementation can be created
with proper configuration and validation.
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.core.investigation_agent import create_investigation_agent_native


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
    """Create empty mock tools list."""
    return []


class TestNativeImplementation:
    """Test suite for native LangGraph implementation."""

    @pytest.mark.asyncio
    async def test_native_agent_creation_succeeds(self, llm_config, mock_tools):
        """Test that native agent can be created successfully."""
        with patch(
            "app.core.investigation_agent.ChatOpenAI"
        ) as mock_chat_openai, patch(
            "app.core.investigation_agent.ToolNode"
        ) as mock_tool_node_class:

            mock_llm = AsyncMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_chat_openai.return_value = mock_llm

            # Mock ToolNode
            mock_tool_node = AsyncMock()
            mock_tool_node_class.return_value = mock_tool_node

            # Create native agent - should not raise
            agent = await create_investigation_agent_native(
                mcp_tools=mock_tools, llm_config=llm_config
            )

            # Verify agent was created
            assert agent is not None

    @pytest.mark.asyncio
    async def test_native_agent_accepts_config(self, mock_tools):
        """Test that native agent accepts configuration correctly."""
        config = {
            "base_url": "https://api.example.com/v1",
            "api_key": "test-key",
            "model_name": "gpt-4",
            "temperature": 0.5,
            "max_tokens": 1000,
        }

        with patch(
            "app.core.investigation_agent.ChatOpenAI"
        ) as mock_chat_openai, patch(
            "app.core.investigation_agent.ToolNode"
        ) as mock_tool_node_class:

            mock_llm = AsyncMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_chat_openai.return_value = mock_llm

            mock_tool_node = AsyncMock()
            mock_tool_node_class.return_value = mock_tool_node

            # Should accept the config
            native_agent = await create_investigation_agent_native(
                mcp_tools=mock_tools, llm_config=config
            )

            # Should be created successfully
            assert native_agent is not None

            # Verify ChatOpenAI was called with correct config
            mock_chat_openai.assert_called_once()
            call_kwargs = mock_chat_openai.call_args[1]
            assert call_kwargs["base_url"] == config["base_url"]
            assert call_kwargs["api_key"] == config["api_key"]
            assert call_kwargs["model"] == config["model_name"]
            assert call_kwargs["temperature"] == config["temperature"]
            assert call_kwargs["max_tokens"] == config["max_tokens"]

    @pytest.mark.asyncio
    async def test_native_agent_validates_required_config(self, mock_tools):
        """Test that native agent validates required configuration."""
        # Missing base_url
        config_no_base_url = {"api_key": "test-key"}

        with pytest.raises(ValueError, match="base_url"):
            await create_investigation_agent_native(
                mcp_tools=mock_tools, llm_config=config_no_base_url
            )

        # Missing api_key
        config_no_api_key = {"base_url": "https://api.example.com"}

        with pytest.raises(ValueError, match="api_key"):
            await create_investigation_agent_native(
                mcp_tools=mock_tools, llm_config=config_no_api_key
            )

    @pytest.mark.asyncio
    async def test_native_agent_uses_default_values(self, mock_tools):
        """Test that native agent uses default values for optional config."""
        config = {
            "base_url": "https://api.example.com/v1",
            "api_key": "test-key",
            # No model_name, temperature, or max_tokens
        }

        with patch(
            "app.core.investigation_agent.ChatOpenAI"
        ) as mock_chat_openai, patch(
            "app.core.investigation_agent.ToolNode"
        ) as mock_tool_node_class:

            mock_llm = AsyncMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_chat_openai.return_value = mock_llm

            mock_tool_node = AsyncMock()
            mock_tool_node_class.return_value = mock_tool_node

            await create_investigation_agent_native(
                mcp_tools=mock_tools, llm_config=config
            )

            # Verify defaults were used
            mock_chat_openai.assert_called_once()
            call_kwargs = mock_chat_openai.call_args[1]
            assert call_kwargs["model"] == "gpt-4"  # default
            assert call_kwargs["temperature"] == 0.7  # default
            assert call_kwargs["max_tokens"] == 2000  # default

    @pytest.mark.asyncio
    async def test_native_agent_accepts_correlation_id(self, llm_config, mock_tools):
        """Test that native agent accepts correlation_id parameter."""
        with patch(
            "app.core.investigation_agent.ChatOpenAI"
        ) as mock_chat_openai, patch(
            "app.core.investigation_agent.ToolNode"
        ) as mock_tool_node_class:

            mock_llm = AsyncMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_chat_openai.return_value = mock_llm

            mock_tool_node = AsyncMock()
            mock_tool_node_class.return_value = mock_tool_node

            # Should accept correlation_id without error
            agent = await create_investigation_agent_native(
                mcp_tools=mock_tools,
                llm_config=llm_config,
                correlation_id="test-corr-123",
            )

            assert agent is not None
