import pytest
from unittest.mock import patch, MagicMock
import os
import json
from app.services.llm_client import LLMClient


@pytest.fixture
def llm_client():
    # Temporarily set the environment variable for the test
    os.environ["GEMINI_API_KEY"] = "mock_api_key"
    client = LLMClient()
    del os.environ["GEMINI_API_KEY"]
    return client


def test_llm_client_initialization_no_api_key():
    if "GEMINI_API_KEY" in os.environ:
        del os.environ["GEMINI_API_KEY"]
    with pytest.raises(
        ValueError, match="GEMINI_API_KEY environment variable not set."
    ):
        LLMClient()


def test_extract_entities_success(llm_client):
    mock_llm_response_text = json.dumps(
        {
            "pod_name": "test-pod-123",
            "namespace": "test-ns",
            "error_summary": "Container restart loop",
        }
    )
    mock_llm_response = MagicMock()
    # The response from the LLM can come back in json escaped in Markdown format
    mock_llm_response.text = f"```json {mock_llm_response_text}```"

    with patch(
        "google.generativeai.GenerativeModel.generate_content",
        return_value=mock_llm_response,
    ) as mock_generate_content:
        description = (
            "Incident: Pod test-pod-123 in namespace test-ns is in a restart loop."
        )
        extracted_data = llm_client.extract_entities(description)

        assert extracted_data == {
            "pod_name": "test-pod-123",
            "namespace": "test-ns",
            "error_summary": "Container restart loop",
        }
        mock_generate_content.assert_called_once()
        args, kwargs = mock_generate_content.call_args
        assert "Incident Description:" in args[0]
        assert "test-pod-123" in args[0]


def test_extract_entities_llm_returns_invalid_json(llm_client):
    mock_llm_response = MagicMock()
    mock_llm_response.text = "invalid json response"

    with patch(
        "google.generativeai.GenerativeModel.generate_content",
        return_value=mock_llm_response,
    ):
        description = (
            "Incident: Pod test-pod-123 in namespace test-ns is in a restart loop."
        )
        extracted_data = llm_client.extract_entities(description)

        assert extracted_data is None


def test_extract_entities_llm_api_error(llm_client):
    with patch(
        "google.generativeai.GenerativeModel.generate_content",
        side_effect=Exception("API Error"),
    ):
        description = (
            "Incident: Pod test-pod-123 in namespace test-ns is in a restart loop."
        )
        extracted_data = llm_client.extract_entities(description)

        assert extracted_data is None
