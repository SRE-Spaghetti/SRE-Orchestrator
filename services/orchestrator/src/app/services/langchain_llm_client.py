"""
LangChain-based LLM client for the SRE Orchestrator.

This module provides a unified interface for LLM interactions using LangChain,
supporting OpenAI-compatible API endpoints and structured output generation.
"""

import logging
import os
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


# Common retryable exceptions for LLM calls
RETRYABLE_LLM_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    # Add other transient errors as needed
)


# Structured Output Models
class ExtractedEntities(BaseModel):
    """Structured model for entities extracted from incident descriptions."""

    pod_name: Optional[str] = Field(
        default=None, description="Name of the Kubernetes pod involved in the incident"
    )
    namespace: str = Field(
        default="default",
        description="Kubernetes namespace where the incident occurred",
    )
    error_summary: str = Field(description="Brief summary of the error or issue")
    error_type: Optional[str] = Field(
        default=None,
        description="Type of error (e.g., 'crash', 'oom', 'network', 'timeout')",
    )


class AnalysisResult(BaseModel):
    """Structured model for incident analysis results."""

    root_cause: str = Field(description="Identified root cause of the incident")
    confidence: Literal["high", "medium", "low"] = Field(
        description="Confidence level in the root cause determination"
    )
    reasoning: str = Field(
        description="Explanation of how the root cause was determined"
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="List of recommended actions to resolve or prevent the issue",
    )


# Configuration
class LLMConfig(BaseModel):
    """Configuration for LLM client."""

    base_url: str = Field(description="Base URL for the OpenAI-compatible API endpoint")
    api_key: str = Field(description="API key for authentication")
    model_name: str = Field(
        description="Name of the model to use (e.g., 'gpt-4', 'gemini-2.5-flash')"
    )
    temperature: float = Field(
        default=0.7, description="Temperature for response generation (0.0-1.0)"
    )
    max_tokens: int = Field(
        default=2000, description="Maximum number of tokens in the response"
    )

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Create configuration from environment variables."""
        base_url = os.getenv("LLM_BASE_URL")
        api_key = os.getenv("LLM_API_KEY")
        model_name = os.getenv("LLM_MODEL_NAME", "gpt-4")

        if not base_url:
            raise ValueError("LLM_BASE_URL environment variable not set")
        if not api_key:
            raise ValueError("LLM_API_KEY environment variable not set")

        return cls(
            base_url=base_url,
            api_key=api_key,
            model_name=model_name,
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2000")),
        )


# LangChain LLM Client
class LangChainLLMClient:
    """
    LangChain-based LLM client with support for structured outputs.

    This client uses LangChain's ChatOpenAI to interact with OpenAI-compatible
    LLM endpoints and provides methods for entity extraction and analysis.
    """

    def __init__(self, config: LLMConfig):
        """
        Initialize the LangChain LLM client.

        Args:
            config: LLM configuration including API endpoint and credentials
        """
        self.config = config
        self.llm = ChatOpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            model=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
        logger.info(
            f"Initialized LangChain LLM client with model {config.model_name} "
            f"at {config.base_url}"
        )

    def extract_entities(
        self, description: str, max_retries: int = 3
    ) -> Optional[ExtractedEntities]:
        """
        Extract structured entities from an incident description.

        Uses LangChain's structured output capabilities to parse the incident
        description and extract relevant entities like pod name, namespace,
        error summary, and error type.

        Args:
            description: The incident description text
            max_retries: Maximum number of retry attempts for transient failures

        Returns:
            ExtractedEntities object with parsed information, or None if extraction fails
        """
        import time

        for attempt in range(1, max_retries + 1):
            try:
                # Create a structured output LLM
                structured_llm = self.llm.with_structured_output(ExtractedEntities)

                # Create the extraction prompt
                prompt = f"""You are an expert SRE assistant. Analyze the following incident description and extract key information.

Incident Description: {description}

Extract the following information:
- pod_name: The name of the Kubernetes pod (if mentioned or can be inferred)
- namespace: The Kubernetes namespace (default to "default" if not mentioned)
- error_summary: A brief summary of the error or issue
- error_type: The type of error (e.g., "crash", "oom", "network", "timeout")

If a field cannot be determined, use null for optional fields."""

                # Invoke the LLM with structured output
                result = structured_llm.invoke(prompt)

                if attempt > 1:
                    logger.info(
                        f"Successfully extracted entities after {attempt} attempt(s): {result}"
                    )
                else:
                    logger.info(f"Successfully extracted entities: {result}")

                return result

            except RETRYABLE_LLM_EXCEPTIONS as e:
                if attempt < max_retries:
                    delay = 2 ** (attempt - 1)  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        f"Retryable error extracting entities (attempt {attempt}/{max_retries}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Error extracting entities after {max_retries} attempts: {e}",
                        exc_info=True,
                    )

            except Exception as e:
                # Non-retryable exception
                logger.error(
                    f"Non-retryable error extracting entities: {e}", exc_info=True
                )
                return None

        return None

    def analyze_evidence(
        self,
        evidence: Dict[str, Any],
        knowledge_graph: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> Optional[AnalysisResult]:
        """
        Analyze collected evidence and suggest root causes.

        Takes the evidence collected during investigation and uses the LLM
        to determine the root cause with confidence level and recommendations.

        Args:
            evidence: Dictionary containing collected evidence from various sources
            knowledge_graph: Optional knowledge graph for additional context
            max_retries: Maximum number of retry attempts for transient failures

        Returns:
            AnalysisResult object with root cause analysis, or None if analysis fails
        """
        import time

        for attempt in range(1, max_retries + 1):
            try:
                # Create a structured output LLM
                structured_llm = self.llm.with_structured_output(AnalysisResult)

                # Build the analysis prompt
                prompt = f"""You are an expert SRE assistant analyzing a production incident.

Evidence collected:
{self._format_evidence(evidence)}
"""

                if knowledge_graph:
                    prompt += f"\nKnowledge Graph Context:\n{self._format_knowledge_graph(knowledge_graph)}\n"

                prompt += """
Based on the evidence above, determine:
1. The root cause of the incident
2. Your confidence level (high, medium, or low)
3. Your reasoning for this determination
4. Recommended actions to resolve or prevent this issue

Provide a thorough analysis based on the available evidence."""

                # Invoke the LLM with structured output
                result = structured_llm.invoke(prompt)

                if attempt > 1:
                    logger.info(
                        f"Successfully analyzed evidence after {attempt} attempt(s): "
                        f"root_cause={result.root_cause}, confidence={result.confidence}"
                    )
                else:
                    logger.info(
                        f"Successfully analyzed evidence: "
                        f"root_cause={result.root_cause}, confidence={result.confidence}"
                    )

                return result

            except RETRYABLE_LLM_EXCEPTIONS as e:
                if attempt < max_retries:
                    delay = 2 ** (attempt - 1)  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        f"Retryable error analyzing evidence (attempt {attempt}/{max_retries}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Error analyzing evidence after {max_retries} attempts: {e}",
                        exc_info=True,
                    )

            except Exception as e:
                # Non-retryable exception
                logger.error(
                    f"Non-retryable error analyzing evidence: {e}", exc_info=True
                )
                return None

        return None

    def generate_investigation_plan(
        self, entities: ExtractedEntities, available_tools: List[str]
    ) -> List[str]:
        """
        Generate an investigation plan based on extracted entities and available tools.

        Args:
            entities: Extracted entities from the incident description
            available_tools: List of available tool names

        Returns:
            List of tool names to execute in order
        """
        try:
            prompt = f"""You are an expert SRE assistant planning an incident investigation.

Incident Information:
- Pod: {entities.pod_name or "unknown"}
- Namespace: {entities.namespace}
- Error Summary: {entities.error_summary}
- Error Type: {entities.error_type or "unknown"}

Available Tools:
{chr(10).join(f"- {tool}" for tool in available_tools)}

Based on the incident information, determine which tools should be used and in what order to investigate this issue.
Respond with a JSON array of tool names in the order they should be executed.

Example: ["get_pod_details", "get_pod_logs", "get_pod_events"]"""

            response = self.llm.invoke(prompt)

            # Parse the response to extract tool names
            import json

            content = response.content

            # Try to extract JSON array from the response
            start_idx = content.find("[")
            end_idx = content.rfind("]")

            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx : end_idx + 1]
                tools = json.loads(json_str)
                logger.info(f"Generated investigation plan: {tools}")
                return tools
            else:
                logger.warning("Could not parse investigation plan from LLM response")
                return []

        except Exception as e:
            logger.error(f"Error generating investigation plan: {e}", exc_info=True)
            return []

    def _format_evidence(self, evidence: Dict[str, Any]) -> str:
        """Format evidence dictionary for prompt inclusion."""
        import json

        return json.dumps(evidence, indent=2)

    def _format_knowledge_graph(self, knowledge_graph: Dict[str, Any]) -> str:
        """Format knowledge graph for prompt inclusion."""
        import json

        return json.dumps(knowledge_graph, indent=2)


# Singleton instance management
_langchain_llm_client_instance: Optional[LangChainLLMClient] = None


def get_langchain_llm_client() -> LangChainLLMClient:
    """
    Get or create the singleton LangChain LLM client instance.

    Returns:
        LangChainLLMClient instance configured from environment variables
    """
    global _langchain_llm_client_instance
    if _langchain_llm_client_instance is None:
        config = LLMConfig.from_env()
        _langchain_llm_client_instance = LangChainLLMClient(config)
    return _langchain_llm_client_instance
