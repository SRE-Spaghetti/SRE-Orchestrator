"""Unit tests for MCPConfigService."""

import pytest
import yaml

from app.services.mcp_config_service import MCPConfigService


class TestMCPConfigService:
    """Test suite for MCPConfigService."""

    def test_load_valid_stdio_config(self, tmp_path):
        """Test loading valid stdio-based MCP configuration."""
        # Arrange
        config_file = tmp_path / "mcp_config.yaml"
        config_data = {
            "kubernetes": {
                "command": "uvx",
                "args": ["mcp-server-kubernetes"],
                "transport": "stdio",
                "env": {"DEBUG": "true"},
            }
        }
        config_file.write_text(yaml.dump(config_data))
        service = MCPConfigService(config_file)

        # Act
        config = service.load_config()

        # Assert
        assert config == config_data
        assert "kubernetes" in config
        assert config["kubernetes"]["command"] == "uvx"
        assert config["kubernetes"]["transport"] == "stdio"

    def test_load_valid_http_config(self, tmp_path):
        """Test loading valid HTTP-based MCP configuration."""
        # Arrange
        config_file = tmp_path / "mcp_config.yaml"
        config_data = {
            "prometheus": {
                "url": "http://prometheus-mcp:8080/mcp",
                "transport": "streamable_http",
                "headers": {"Authorization": "Bearer token123"},
            }
        }
        config_file.write_text(yaml.dump(config_data))
        service = MCPConfigService(config_file)

        # Act
        config = service.load_config()

        # Assert
        assert config == config_data
        assert "prometheus" in config
        assert config["prometheus"]["url"] == "http://prometheus-mcp:8080/mcp"
        assert config["prometheus"]["transport"] == "streamable_http"

    def test_load_multiple_servers_config(self, tmp_path):
        """Test loading configuration with multiple MCP servers."""
        # Arrange
        config_file = tmp_path / "mcp_config.yaml"
        config_data = {
            "kubernetes": {
                "command": "uvx",
                "args": ["mcp-server-kubernetes"],
                "transport": "stdio",
            },
            "prometheus": {
                "url": "http://prometheus-mcp:8080/mcp",
                "transport": "streamable_http",
            },
        }
        config_file.write_text(yaml.dump(config_data))
        service = MCPConfigService(config_file)

        # Act
        config = service.load_config()

        # Assert
        assert len(config) == 2
        assert "kubernetes" in config
        assert "prometheus" in config

    def test_load_config_returns_empty_dict_for_missing_file(self, tmp_path):
        """Test that load_config returns empty dict when file doesn't exist."""
        # Arrange
        config_file = tmp_path / "nonexistent.yaml"
        service = MCPConfigService(config_file)

        # Act
        config = service.load_config()

        # Assert
        assert config == {}

    def test_load_config_returns_empty_dict_for_empty_file(self, tmp_path):
        """Test that load_config returns empty dict for empty file."""
        # Arrange
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")
        service = MCPConfigService(config_file)

        # Act
        config = service.load_config()

        # Assert
        assert config == {}

    def test_load_config_raises_error_for_invalid_yaml(self, tmp_path):
        """Test that load_config raises ValueError for invalid YAML syntax."""
        # Arrange
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: [unclosed")
        service = MCPConfigService(config_file)

        # Act & Assert
        with pytest.raises(ValueError, match="Error parsing MCP config YAML"):
            service.load_config()

    def test_load_config_raises_error_for_non_dict_content(self, tmp_path):
        """Test that load_config raises ValueError for non-dict YAML content."""
        # Arrange
        config_file = tmp_path / "list.yaml"
        config_file.write_text("- item1\n- item2")
        service = MCPConfigService(config_file)

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid MCP config format"):
            service.load_config()

    def test_validate_config_raises_error_for_missing_transport(self, tmp_path):
        """Test that validation fails when transport field is missing."""
        # Arrange
        config_file = tmp_path / "mcp_config.yaml"
        config_data = {
            "kubernetes": {
                "command": "uvx",
                "args": ["mcp-server-kubernetes"],
            }
        }
        config_file.write_text(yaml.dump(config_data))
        service = MCPConfigService(config_file)

        # Act & Assert
        with pytest.raises(ValueError, match="missing required 'transport' field"):
            service.load_config()

    def test_validate_config_raises_error_for_stdio_missing_command(self, tmp_path):
        """Test that validation fails for stdio transport without command."""
        # Arrange
        config_file = tmp_path / "mcp_config.yaml"
        config_data = {
            "kubernetes": {
                "transport": "stdio",
                "args": ["mcp-server-kubernetes"],
            }
        }
        config_file.write_text(yaml.dump(config_data))
        service = MCPConfigService(config_file)

        # Act & Assert
        with pytest.raises(ValueError, match="missing 'command' field"):
            service.load_config()

    def test_validate_config_raises_error_for_stdio_missing_args(self, tmp_path):
        """Test that validation fails for stdio transport without args."""
        # Arrange
        config_file = tmp_path / "mcp_config.yaml"
        config_data = {
            "kubernetes": {
                "transport": "stdio",
                "command": "uvx",
            }
        }
        config_file.write_text(yaml.dump(config_data))
        service = MCPConfigService(config_file)

        # Act & Assert
        with pytest.raises(ValueError, match="missing 'args' field"):
            service.load_config()

    def test_validate_config_raises_error_for_http_missing_url(self, tmp_path):
        """Test that validation fails for HTTP transport without url."""
        # Arrange
        config_file = tmp_path / "mcp_config.yaml"
        config_data = {
            "prometheus": {
                "transport": "streamable_http",
                "headers": {"Authorization": "Bearer token"},
            }
        }
        config_file.write_text(yaml.dump(config_data))
        service = MCPConfigService(config_file)

        # Act & Assert
        with pytest.raises(ValueError, match="missing 'url' field"):
            service.load_config()

    def test_validate_config_raises_error_for_unsupported_transport(self, tmp_path):
        """Test that validation fails for unsupported transport type."""
        # Arrange
        config_file = tmp_path / "mcp_config.yaml"
        config_data = {
            "custom": {
                "transport": "websocket",
                "url": "ws://example.com",
            }
        }
        config_file.write_text(yaml.dump(config_data))
        service = MCPConfigService(config_file)

        # Act & Assert
        with pytest.raises(ValueError, match="unsupported transport type"):
            service.load_config()

    def test_validate_config_raises_error_for_non_dict_server_config(self, tmp_path):
        """Test that validation fails when server config is not a dict."""
        # Arrange
        config_file = tmp_path / "mcp_config.yaml"
        config_data = {"kubernetes": "invalid-string-config"}
        config_file.write_text(yaml.dump(config_data))
        service = MCPConfigService(config_file)

        # Act & Assert
        with pytest.raises(ValueError, match="must be a dict"):
            service.load_config()

    def test_validate_config_with_optional_env_field(self, tmp_path):
        """Test that validation passes with optional env field."""
        # Arrange
        config_file = tmp_path / "mcp_config.yaml"
        config_data = {
            "kubernetes": {
                "command": "uvx",
                "args": ["mcp-server-kubernetes"],
                "transport": "stdio",
                "env": {"DEBUG": "true", "LOG_LEVEL": "info"},
            }
        }
        config_file.write_text(yaml.dump(config_data))
        service = MCPConfigService(config_file)

        # Act
        config = service.load_config()

        # Assert
        assert config["kubernetes"]["env"]["DEBUG"] == "true"
        assert config["kubernetes"]["env"]["LOG_LEVEL"] == "info"

    def test_validate_config_with_optional_headers_field(self, tmp_path):
        """Test that validation passes with optional headers field."""
        # Arrange
        config_file = tmp_path / "mcp_config.yaml"
        config_data = {
            "prometheus": {
                "url": "http://prometheus-mcp:8080/mcp",
                "transport": "streamable_http",
                "headers": {
                    "Authorization": "Bearer token123",
                    "X-Custom-Header": "value",
                },
            }
        }
        config_file.write_text(yaml.dump(config_data))
        service = MCPConfigService(config_file)

        # Act
        config = service.load_config()

        # Assert
        assert config["prometheus"]["headers"]["Authorization"] == "Bearer token123"
        assert config["prometheus"]["headers"]["X-Custom-Header"] == "value"

    def test_validate_config_passes_pydantic_validation(self, tmp_path):
        """Test that config passes Pydantic model validation."""
        # Arrange
        config_file = tmp_path / "mcp_config.yaml"
        config_data = {
            "kubernetes": {
                "command": "uvx",
                "args": ["mcp-server-kubernetes"],
                "transport": "stdio",
            }
        }
        config_file.write_text(yaml.dump(config_data))
        service = MCPConfigService(config_file)

        # Act
        config = service.load_config()

        # Assert - should not raise any validation errors
        assert config is not None
        assert "kubernetes" in config

    def test_load_config_handles_io_error(self, tmp_path):
        """Test that load_config raises IOError for file read errors."""
        # Arrange
        config_file = tmp_path / "mcp_config.yaml"
        config_file.write_text("test: data")
        config_file.chmod(0o000)  # Remove all permissions
        service = MCPConfigService(config_file)

        # Act & Assert
        with pytest.raises(IOError, match="Could not read MCP config file"):
            service.load_config()

        # Cleanup
        config_file.chmod(0o644)
