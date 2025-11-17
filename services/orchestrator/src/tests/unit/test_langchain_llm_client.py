"""Unit tests for LangChain LLM client."""

import pytest
from unittest.mock import Mock, patch
import os

from app.services.langchain_llm_client import (
    LLMConfig,
    LangChainLLMClient,
    ExtractedEntities,
    AnalysisResult,
    get_langchain_llm_client,
)


class TestLLMConfig:
    """Tests for LLMConfig class."""

    def test_from_env_success(self):
        """Test creating config from environment variables."""
        with patch.dict(
            os.environ,
            {
                "LLM_BASE_URL": "https://api.example.com/v1",
                "LLM_API_KEY": "test-key-123",
                "LLM_MODEL_NAME": "gpt-4",
                "LLM_TEMPERATURE": "0.5",
                "LLM_MAX_TOKENS": "1000",
            },
        ):
            config = LLMConfig.from_env()

            assert config.base_url == "https://api.example.com/v1"
            assert config.api_key == "test-key-123"
            assert config.model_name == "gpt-4"
            assert config.temperature == 0.5
            assert config.max_tokens == 1000

    def test_from_env_defaults(self):
        """Test config defaults when optional env vars not set."""
        with patch.dict(
            os.environ,
            {
                "LLM_BASE_URL": "https://api.example.com/v1",
                "LLM_API_KEY": "test-key-123",
            },
            clear=True,
        ):
            config = LLMConfig.from_env()

            assert config.model_name == "gpt-4"
            assert config.temperature == 0.7
            assert config.max_tokens == 2000

    def test_from_env_missing_base_url(self):
        """Test error when LLM_BASE_URL not set."""
        with patch.dict(os.environ, {"LLM_API_KEY": "test-key"}, clear=True):
            with pytest.raises(ValueError, match="LLM_BASE_URL"):
                LLMConfig.from_env()

    def test_from_env_missing_api_key(self):
        """Test error when LLM_API_KEY not set."""
        with patch.dict(
            os.environ, {"LLM_BASE_URL": "https://api.example.com"}, clear=True
        ):
            with pytest.raises(ValueError, match="LLM_API_KEY"):
                LLMConfig.from_env()


class TestLangChainLLMClient:
    """Tests for LangChainLLMClient class."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        return LLMConfig(
            base_url="https://api.example.com/v1",
            api_key="test-key-123",
            model_name="gpt-4",
            temperature=0.7,
            max_tokens=2000,
        )

    @pytest.fixture
    def client(self, config):
        """Create test client."""
        with patch("app.services.langchain_llm_client.ChatOpenAI"):
            return LangChainLLMClient(config)

    def test_initialization(self, config):
        """Test client initialization."""
        with patch("app.services.langchain_llm_client.ChatOpenAI") as mock_chat:
            client = LangChainLLMClient(config)

            mock_chat.assert_called_once_with(
                base_url=config.base_url,
                api_key=config.api_key,
                model=config.model_name,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
            assert client.config == config

    def test_extract_entities_success(self, client):
        """Test successful entity extraction."""
        # Mock the structured output
        mock_result = ExtractedEntities(
            pod_name="test-pod-123",
            namespace="production",
            error_summary="Pod is crashing",
            error_type="crash",
        )

        mock_structured_llm = Mock()
        mock_structured_llm.invoke.return_value = mock_result
        client.llm.with_structured_output = Mock(return_value=mock_structured_llm)

        result = client.extract_entities("Pod test-pod-123 in production is crashing")

        assert result == mock_result
        assert result.pod_name == "test-pod-123"
        assert result.namespace == "production"
        assert result.error_type == "crash"
        mock_structured_llm.invoke.assert_called_once()

    def test_extract_entities_with_retry(self, client):
        """Test entity extraction with retry on transient error."""
        mock_result = ExtractedEntities(
            pod_name="test-pod",
            namespace="default",
            error_summary="Error",
            error_type="crash",
        )

        mock_structured_llm = Mock()
        # First call fails, second succeeds
        mock_structured_llm.invoke.side_effect = [
            ConnectionError("Temporary failure"),
            mock_result,
        ]
        client.llm.with_structured_output = Mock(return_value=mock_structured_llm)

        with patch("time.sleep"):  # Skip actual sleep
            result = client.extract_entities("Test description")

        assert result == mock_result
        assert mock_structured_llm.invoke.call_count == 2

    def test_extract_entities_max_retries_exceeded(self, client):
        """Test entity extraction fails after max retries."""
        mock_structured_llm = Mock()
        mock_structured_llm.invoke.side_effect = ConnectionError("Persistent failure")
        client.llm.with_structured_output = Mock(return_value=mock_structured_llm)

        with patch("time.sleep"):
            result = client.extract_entities("Test description", max_retries=3)

        assert result is None
        assert mock_structured_llm.invoke.call_count == 3

    def test_extract_entities_non_retryable_error(self, client):
        """Test entity extraction with non-retryable error."""
        mock_structured_llm = Mock()
        mock_structured_llm.invoke.side_effect = ValueError("Invalid input")
        client.llm.with_structured_output = Mock(return_value=mock_structured_llm)

        result = client.extract_entities("Test description")

        assert result is None
        assert mock_structured_llm.invoke.call_count == 1

    def test_analyze_evidence_success(self, client):
        """Test successful evidence analysis."""
        mock_result = AnalysisResult(
            root_cause="Pod OOMKilled due to memory limit",
            confidence="high",
            reasoning="Pod logs show OOM errors and memory usage exceeded limits",
            recommendations=["Increase memory limits", "Optimize memory usage"],
        )

        mock_structured_llm = Mock()
        mock_structured_llm.invoke.return_value = mock_result
        client.llm.with_structured_output = Mock(return_value=mock_structured_llm)

        evidence = {
            "pod_details": {"status": "OOMKilled"},
            "pod_logs": "Out of memory error",
        }

        result = client.analyze_evidence(evidence)

        assert result == mock_result
        assert result.root_cause == "Pod OOMKilled due to memory limit"
        assert result.confidence == "high"
        assert len(result.recommendations) == 2
        mock_structured_llm.invoke.assert_called_once()

    def test_analyze_evidence_with_knowledge_graph(self, client):
        """Test evidence analysis with knowledge graph context."""
        mock_result = AnalysisResult(
            root_cause="Known issue",
            confidence="high",
            reasoning="Matches known pattern",
            recommendations=["Apply fix"],
        )

        mock_structured_llm = Mock()
        mock_structured_llm.invoke.return_value = mock_result
        client.llm.with_structured_output = Mock(return_value=mock_structured_llm)

        evidence = {"pod_details": {"status": "Failed"}}
        knowledge_graph = {"patterns": ["pattern1"]}

        result = client.analyze_evidence(evidence, knowledge_graph)

        assert result == mock_result
        # Verify knowledge graph was included in prompt
        call_args = mock_structured_llm.invoke.call_args[0][0]
        assert "Knowledge Graph Context" in call_args

    def test_analyze_evidence_with_retry(self, client):
        """Test evidence analysis with retry."""
        mock_result = AnalysisResult(
            root_cause="Test cause",
            confidence="medium",
            reasoning="Test reasoning",
            recommendations=[],
        )

        mock_structured_llm = Mock()
        mock_structured_llm.invoke.side_effect = [TimeoutError("Timeout"), mock_result]
        client.llm.with_structured_output = Mock(return_value=mock_structured_llm)

        with patch("time.sleep"):
            result = client.analyze_evidence({"test": "data"})

        assert result == mock_result
        assert mock_structured_llm.invoke.call_count == 2

    def test_generate_investigation_plan_success(self, client):
        """Test successful investigation plan generation."""
        mock_response = Mock()
        mock_response.content = '["get_pod_details", "get_pod_logs", "get_pod_events"]'
        client.llm.invoke = Mock(return_value=mock_response)

        entities = ExtractedEntities(
            pod_name="test-pod",
            namespace="default",
            error_summary="Pod crashing",
            error_type="crash",
        )
        available_tools = ["get_pod_details", "get_pod_logs", "get_pod_events"]

        result = client.generate_investigation_plan(entities, available_tools)

        assert result == ["get_pod_details", "get_pod_logs", "get_pod_events"]
        client.llm.invoke.assert_called_once()

    def test_generate_investigation_plan_invalid_json(self, client):
        """Test investigation plan with invalid JSON response."""
        mock_response = Mock()
        mock_response.content = "This is not JSON"
        client.llm.invoke = Mock(return_value=mock_response)

        entities = ExtractedEntities(
            pod_name="test-pod",
            namespace="default",
            error_summary="Error",
            error_type="crash",
        )

        result = client.generate_investigation_plan(entities, [])

        assert result == []

    def test_generate_investigation_plan_error(self, client):
        """Test investigation plan generation with error."""
        client.llm.invoke = Mock(side_effect=Exception("LLM error"))

        entities = ExtractedEntities(
            pod_name="test-pod",
            namespace="default",
            error_summary="Error",
            error_type="crash",
        )

        result = client.generate_investigation_plan(entities, [])

        assert result == []


def test_get_langchain_llm_client_singleton():
    """Test singleton instance management."""
    with patch.dict(
        os.environ,
        {"LLM_BASE_URL": "https://api.example.com/v1", "LLM_API_KEY": "test-key"},
    ):
        with patch("app.services.langchain_llm_client.ChatOpenAI"):
            # Reset singleton
            import app.services.langchain_llm_client as module

            module._langchain_llm_client_instance = None

            client1 = get_langchain_llm_client()
            client2 = get_langchain_llm_client()

            assert client1 is client2
