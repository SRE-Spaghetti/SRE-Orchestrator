from app.models.mcp_config import MCPServerConfig
import yaml
from pathlib import Path
from pydantic import ValidationError
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class MCPConfigService:
    """
    Service for loading and managing MCP server configurations.

    Supports the new dictionary-based format compatible with MultiServerMCPClient.
    """

    def __init__(self, config_path: Path):
        self._config_path = config_path

    def load_config(self) -> Dict[str, Any]:
        """
        Load MCP configuration from YAML file.

        Returns:
            Dictionary mapping server names to their configurations.
            Returns empty dict if file doesn't exist or is empty.

        Raises:
            ValueError: If config validation fails
            IOError: If file cannot be read
        """
        if not self._config_path.is_file():
            logger.warning(f"MCP config file not found at {self._config_path}")
            return {}

        try:
            with open(self._config_path, "r") as f:
                config_data = yaml.safe_load(f)

                if not config_data:
                    logger.info("MCP config file is empty")
                    return {}

                if not isinstance(config_data, dict):
                    raise ValueError(f"Invalid MCP config format: expected dict, got {type(config_data)}")

                # Validate the configuration
                self._validate_config(config_data)

                logger.info(f"Loaded MCP configuration with {len(config_data)} server(s)")
                return config_data

        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing MCP config YAML: {e}") from e
        except IOError as e:
            logger.error(f"Could not read MCP config file: {e}")
            raise IOError(f"Could not read MCP config file: {e}") from e

    def _validate_config(self, config_data: Dict[str, Any]) -> None:
        """
        Validate MCP server configuration.

        Args:
            config_data: Configuration dictionary to validate

        Raises:
            ValueError: If validation fails
        """
        for server_name, server_config in config_data.items():
            if not isinstance(server_config, dict):
                raise ValueError(f"Invalid config for server '{server_name}': must be a dict")

            transport = server_config.get('transport')
            if not transport:
                raise ValueError(f"Server '{server_name}' missing required 'transport' field")

            # Validate based on transport type
            if transport == 'streamable_http':
                if 'url' not in server_config:
                    raise ValueError(f"Server '{server_name}' with HTTP transport missing 'url' field")
            elif transport == 'stdio':
                if 'command' not in server_config:
                    raise ValueError(f"Server '{server_name}' with stdio transport missing 'command' field")
                if 'args' not in server_config:
                    raise ValueError(f"Server '{server_name}' with stdio transport missing 'args' field")
            else:
                raise ValueError(f"Server '{server_name}' has unsupported transport type: {transport}")

            # Try to parse with Pydantic model for additional validation
            try:
                MCPServerConfig(**server_config)
            except ValidationError as e:
                raise ValueError(f"Validation error for server '{server_name}': {e}") from e
