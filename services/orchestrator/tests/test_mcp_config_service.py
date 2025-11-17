"""Tests for MCP configuration service."""

import pytest
import yaml
from app.services.mcp_config_service import MCPConfigService


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file."""
    config_path = tmp_path / "mcp_config.yaml"
    return config_path


def test_load_empty_config(temp_config_file):
    """Test loading an empty config file."""
    temp_config_file.write_text("")

    service = MCPConfigService(temp_config_file)
    config = service.load_config()

    assert config == {}


def test_load_stdio_config(temp_config_file):
    """Test loading a stdio-based server config."""
    config_data = {
        "local-tools": {
            "command": "npx",
            "args": ["mcp-server-kubernetes"],
            "transport": "stdio",
        }
    }
    temp_config_file.write_text(yaml.dump(config_data))

    service = MCPConfigService(temp_config_file)
    config = service.load_config()

    assert "local-tools" in config
    assert config["local-tools"]["command"] == "npx"
    assert config["local-tools"]["args"] == ["mcp-server-kubernetes"]
    assert config["local-tools"]["transport"] == "stdio"


def test_load_http_config(temp_config_file):
    """Test loading an HTTP-based server config."""
    config_data = {
        "kubernetes": {
            "url": "http://k8s-mcp:8080/mcp",
            "transport": "streamable_http",
            "headers": {"Authorization": "Bearer token123"},
        }
    }
    temp_config_file.write_text(yaml.dump(config_data))

    service = MCPConfigService(temp_config_file)
    config = service.load_config()

    assert "kubernetes" in config
    assert config["kubernetes"]["url"] == "http://k8s-mcp:8080/mcp"
    assert config["kubernetes"]["transport"] == "streamable_http"
    assert config["kubernetes"]["headers"]["Authorization"] == "Bearer token123"


def test_load_multiple_servers(temp_config_file):
    """Test loading multiple server configs."""
    config_data = {
        "local-tools": {
            "command": "npx",
            "args": ["mcp-server-kubernetes"],
            "transport": "stdio",
        },
        "prometheus": {
            "url": "http://prometheus:9090/mcp",
            "transport": "streamable_http",
        },
    }
    temp_config_file.write_text(yaml.dump(config_data))

    service = MCPConfigService(temp_config_file)
    config = service.load_config()

    assert len(config) == 2
    assert "local-tools" in config
    assert "prometheus" in config


def test_missing_config_file(tmp_path):
    """Test handling of missing config file."""
    config_path = tmp_path / "nonexistent.yaml"

    service = MCPConfigService(config_path)
    config = service.load_config()

    assert config == {}


def test_invalid_transport_type(temp_config_file):
    """Test validation of invalid transport type."""
    config_data = {
        "invalid-server": {
            "url": "http://example.com",
            "transport": "invalid_transport",
        }
    }
    temp_config_file.write_text(yaml.dump(config_data))

    service = MCPConfigService(temp_config_file)

    with pytest.raises(ValueError, match="unsupported transport type"):
        service.load_config()


def test_missing_required_field_stdio(temp_config_file):
    """Test validation when stdio config is missing required fields."""
    config_data = {
        "incomplete-server": {
            "command": "npx",
            # Missing 'args' field
            "transport": "stdio",
        }
    }
    temp_config_file.write_text(yaml.dump(config_data))

    service = MCPConfigService(temp_config_file)

    with pytest.raises(ValueError, match="missing 'args' field"):
        service.load_config()


def test_missing_required_field_http(temp_config_file):
    """Test validation when HTTP config is missing required fields."""
    config_data = {
        "incomplete-server": {
            # Missing 'url' field
            "transport": "streamable_http"
        }
    }
    temp_config_file.write_text(yaml.dump(config_data))

    service = MCPConfigService(temp_config_file)

    with pytest.raises(ValueError, match="missing 'url' field"):
        service.load_config()


def test_stdio_with_env_vars(temp_config_file):
    """Test stdio config with environment variables."""
    config_data = {
        "python-tools": {
            "command": "python",
            "args": ["/path/to/server.py"],
            "transport": "stdio",
            "env": {"LOG_LEVEL": "DEBUG", "PYTHONPATH": "/custom/path"},
        }
    }
    temp_config_file.write_text(yaml.dump(config_data))

    service = MCPConfigService(temp_config_file)
    config = service.load_config()

    assert config["python-tools"]["env"]["LOG_LEVEL"] == "DEBUG"
    assert config["python-tools"]["env"]["PYTHONPATH"] == "/custom/path"
