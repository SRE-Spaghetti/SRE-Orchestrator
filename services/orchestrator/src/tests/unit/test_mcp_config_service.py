import pytest
from unittest.mock import patch, mock_open
from pathlib import Path
import yaml
from pydantic import ValidationError

from app.models.mcp_config import MCPConfig
from app.services.mcp_config_service import MCPConfigService

VALID_YAML = """
mcp_servers:
  - server_url: "https://test.com"
    transport_type: "https"
    authentication:
      username: "user"
      password: "password"
"""

INVALID_SCHEMA_YAML = """
mcp_servers:
  - server_url: "http://invalid.com"
    transport_type: "ftp"
"""

MALFORMED_YAML = "mcp_servers: [ server_url: 'bad'"

@pytest.fixture
def mock_path() -> Path:
    return Path("/fake/path/mcp_config.yaml")

def test_load_valid_config(mock_path):
    with patch("builtins.open", mock_open(read_data=VALID_YAML)) as mock_file:
        with patch("pathlib.Path.is_file", return_value=True):
            service = MCPConfigService(mock_path)
            config = service.get_config()
            assert config is not None
            assert len(config.mcp_servers) == 1
            assert config.mcp_servers[0].server_url == "https://test.com"
            mock_file.assert_called_once_with(mock_path, "r")

def test_missing_config_file(mock_path):
    with patch("pathlib.Path.is_file", return_value=False):
        service = MCPConfigService(mock_path)
        config = service.get_config()
        assert config is None

def test_empty_config_file(mock_path):
    with patch("builtins.open", mock_open(read_data="")) as mock_file:
        with patch("pathlib.Path.is_file", return_value=True):
            service = MCPConfigService(mock_path)
            config = service.get_config()
            assert config is not None
            assert len(config.mcp_servers) == 0

def test_invalid_schema(mock_path):
    with patch("builtins.open", mock_open(read_data=INVALID_SCHEMA_YAML)):
        with patch("pathlib.Path.is_file", return_value=True):
            with pytest.raises(ValueError, match="Error loading or validating MCP config"):
                MCPConfigService(mock_path)

def test_malformed_yaml(mock_path):
    with patch("builtins.open", mock_open(read_data=MALFORMED_YAML)):
        with patch("pathlib.Path.is_file", return_value=True):
            with pytest.raises(ValueError, match="Error loading or validating MCP config"):
                MCPConfigService(mock_path)

def test_io_error(mock_path):
    with patch("builtins.open", side_effect=IOError("File not readable")):
        with patch("pathlib.Path.is_file", return_value=True):
            with pytest.raises(IOError, match="Could not read MCP config file"):
                MCPConfigService(mock_path)

