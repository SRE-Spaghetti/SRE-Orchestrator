"""Reusable fixtures for MCP-related testing."""

import pytest
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_mcp_tool() -> Mock:
    """
    Provides a single mock MCP tool with standard interface.

    Returns:
        Mock: Mock tool with invoke and ainvoke methods
    """
    tool = Mock()
    tool.name = "get_pod_details"
    tool.description = "Get detailed information about a Kubernetes pod"
    tool.args_schema = {
        "type": "object",
        "properties": {"pod_name": {"type": "string"}},
        "required": ["pod_name"],
    }
    tool.invoke = Mock(
        return_value={
            "name": "nginx-deployment-abc123",
            "status": "Running",
            "restarts": 0,
            "ready": True,
        }
    )
    tool.ainvoke = AsyncMock(
        return_value={
            "name": "nginx-deployment-abc123",
            "status": "Running",
            "restarts": 0,
            "ready": True,
        }
    )
    return tool


@pytest.fixture
def mock_kubernetes_tools() -> List[Mock]:
    """
    Provides a set of mock Kubernetes MCP tools.

    Returns:
        List[Mock]: List of Kubernetes-related tools
    """
    # get_pod_details tool
    pod_tool = Mock()
    pod_tool.name = "get_pod_details"
    pod_tool.description = "Get detailed information about a Kubernetes pod"
    pod_tool.invoke = Mock(
        return_value={"status": "CrashLoopBackOff", "restarts": 5, "ready": False}
    )
    pod_tool.ainvoke = AsyncMock(
        return_value={"status": "CrashLoopBackOff", "restarts": 5, "ready": False}
    )

    # get_pod_logs tool
    logs_tool = Mock()
    logs_tool.name = "get_pod_logs"
    logs_tool.description = "Get logs from a Kubernetes pod"
    logs_tool.invoke = Mock(
        return_value={"logs": "Error: OOMKilled - container exceeded memory limit"}
    )
    logs_tool.ainvoke = AsyncMock(
        return_value={"logs": "Error: OOMKilled - container exceeded memory limit"}
    )

    # get_deployment_info tool
    deployment_tool = Mock()
    deployment_tool.name = "get_deployment_info"
    deployment_tool.description = "Get information about a Kubernetes deployment"
    deployment_tool.invoke = Mock(
        return_value={
            "name": "nginx-deployment",
            "replicas": 3,
            "available": 2,
            "unavailable": 1,
        }
    )
    deployment_tool.ainvoke = AsyncMock(
        return_value={
            "name": "nginx-deployment",
            "replicas": 3,
            "available": 2,
            "unavailable": 1,
        }
    )

    # get_events tool
    events_tool = Mock()
    events_tool.name = "get_events"
    events_tool.description = "Get recent Kubernetes events"
    events_tool.invoke = Mock(
        return_value={
            "events": [
                {
                    "type": "Warning",
                    "reason": "BackOff",
                    "message": "Back-off restarting failed container",
                },
                {"type": "Warning", "reason": "Failed", "message": "Error: OOMKilled"},
            ]
        }
    )
    events_tool.ainvoke = AsyncMock(
        return_value={
            "events": [
                {
                    "type": "Warning",
                    "reason": "BackOff",
                    "message": "Back-off restarting failed container",
                },
                {"type": "Warning", "reason": "Failed", "message": "Error: OOMKilled"},
            ]
        }
    )

    return [pod_tool, logs_tool, deployment_tool, events_tool]


@pytest.fixture
def mock_mcp_tool_with_error() -> Mock:
    """
    Provides a mock MCP tool that raises errors.

    Returns:
        Mock: Mock tool that simulates failures
    """
    tool = Mock()
    tool.name = "failing_tool"
    tool.description = "A tool that fails for testing error handling"
    tool.invoke = Mock(side_effect=Exception("Tool execution failed"))
    tool.ainvoke = AsyncMock(side_effect=Exception("Tool execution failed"))
    return tool


@pytest.fixture
def valid_mcp_config() -> Dict[str, Any]:
    """
    Provides a valid MCP configuration dictionary.

    Returns:
        Dict[str, Any]: Complete MCP configuration
    """
    return {
        "mcpServers": {
            "kubernetes": {
                "command": "uvx",
                "args": ["mcp-server-kubernetes"],
                "env": {"KUBECONFIG": "/path/to/kubeconfig"},
            },
            "prometheus": {
                "command": "uvx",
                "args": ["mcp-server-prometheus"],
                "env": {"PROMETHEUS_URL": "http://prometheus:9090"},
            },
        }
    }


@pytest.fixture
def invalid_mcp_configs() -> List[Dict[str, Any]]:
    """
    Provides various invalid MCP configurations for validation testing.

    Returns:
        List[Dict[str, Any]]: List of invalid configuration scenarios
    """
    return [
        # Missing mcpServers key
        {},
        # Empty mcpServers
        {"mcpServers": {}},
        # Missing command
        {"mcpServers": {"kubernetes": {"args": ["mcp-server-kubernetes"]}}},
        # Missing args
        {"mcpServers": {"kubernetes": {"command": "uvx"}}},
        # Invalid structure
        {"mcpServers": "not a dict"},
        # Server config is not a dict
        {"mcpServers": {"kubernetes": "not a dict"}},
    ]


@pytest.fixture
def mcp_config_yaml_content() -> str:
    """
    Provides valid MCP configuration as YAML string.

    Returns:
        str: YAML-formatted MCP configuration
    """
    return """
mcpServers:
  kubernetes:
    command: uvx
    args:
      - mcp-server-kubernetes
    env:
      KUBECONFIG: /path/to/kubeconfig

  prometheus:
    command: uvx
    args:
      - mcp-server-prometheus
    env:
      PROMETHEUS_URL: http://prometheus:9090
"""


@pytest.fixture
def mcp_config_file(tmp_path: Path, mcp_config_yaml_content: str) -> Path:
    """
    Creates a temporary MCP configuration file for testing.

    Args:
        tmp_path: Pytest tmp_path fixture
        mcp_config_yaml_content: YAML content fixture

    Returns:
        Path: Path to temporary MCP config file
    """
    config_file = tmp_path / "mcp_config.yaml"
    config_file.write_text(mcp_config_yaml_content)
    return config_file


@pytest.fixture
def invalid_mcp_config_file(tmp_path: Path) -> Path:
    """
    Creates a temporary MCP configuration file with invalid YAML.

    Args:
        tmp_path: Pytest tmp_path fixture

    Returns:
        Path: Path to temporary invalid config file
    """
    config_file = tmp_path / "invalid_mcp_config.yaml"
    config_file.write_text("invalid: yaml: content: [unclosed")
    return config_file


@pytest.fixture
def mock_mcp_client() -> Mock:
    """
    Provides a mock MCP client for testing.

    Returns:
        Mock: Mock MultiServerMCPClient
    """
    client = Mock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.list_tools = AsyncMock(
        return_value=[
            {"name": "get_pod_details", "description": "Get pod details"},
            {"name": "get_pod_logs", "description": "Get pod logs"},
        ]
    )
    client.call_tool = AsyncMock(return_value={"status": "Running", "restarts": 0})
    return client


@pytest.fixture
def mock_mcp_connection_manager() -> Mock:
    """
    Provides a mock MCP connection manager.

    Returns:
        Mock: Mock connection manager with lifecycle methods
    """
    manager = Mock()
    manager.initialize = AsyncMock()
    manager.cleanup = AsyncMock()
    manager.is_connected = Mock(return_value=True)
    manager.get_client = Mock()
    return manager


@pytest.fixture
def mock_tool_execution_result() -> Dict[str, Any]:
    """
    Provides a mock tool execution result.

    Returns:
        Dict[str, Any]: Typical tool execution response
    """
    return {
        "success": True,
        "data": {
            "pod_name": "nginx-deployment-abc123",
            "namespace": "production",
            "status": "Running",
            "containers": [
                {
                    "name": "nginx",
                    "image": "nginx:1.21",
                    "ready": True,
                    "restarts": 0,
                }
            ],
        },
        "metadata": {
            "execution_time_ms": 150,
            "tool_name": "get_pod_details",
        },
    }


@pytest.fixture
def mock_tool_execution_error() -> Dict[str, Any]:
    """
    Provides a mock tool execution error response.

    Returns:
        Dict[str, Any]: Error response from tool execution
    """
    return {
        "success": False,
        "error": "Pod not found: nginx-deployment-xyz999",
        "error_code": "NOT_FOUND",
        "metadata": {
            "execution_time_ms": 50,
            "tool_name": "get_pod_details",
        },
    }
