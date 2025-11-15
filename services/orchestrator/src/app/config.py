"""Application configuration management."""
import os
from pathlib import Path
from typing import Optional


def get_mcp_config_path() -> Path:
    """
    Get the MCP configuration file path.

    Priority order:
    1. MCP_CONFIG_PATH environment variable
    2. /config/mcp_config.yaml (Docker/Kubernetes mount)
    3. Default: <project_root>/mcp_config.yaml

    Returns:
        Path: The resolved path to the MCP configuration file
    """
    # Check environment variable first
    env_path = os.getenv("MCP_CONFIG_PATH")
    if env_path:
        return Path(env_path)

    # Check Docker/Kubernetes mount location
    docker_path = Path("/config/mcp_config.yaml")
    if docker_path.exists():
        return docker_path

    # Default to project root
    return Path(__file__).parent.parent.parent.parent / "mcp_config.yaml"


def get_llm_config() -> dict:
    """
    Get LLM configuration from environment variables.

    Returns:
        dict: LLM configuration with base_url, api_key, model_name, etc.
    """
    return {
        "base_url": os.getenv("LLM_BASE_URL"),
        "api_key": os.getenv("LLM_API_KEY"),
        "model_name": os.getenv("LLM_MODEL_NAME", "gpt-4"),
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "4096")),
    }
