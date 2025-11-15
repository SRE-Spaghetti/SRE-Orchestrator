"""
MCP Tool Configuration Loader

This module provides functionality to load MCP server configuration
in the format expected by MultiServerMCPClient.
"""

import logging
import os
import yaml
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class MCPToolConfigLoader:
    """
    Loads MCP server configuration from YAML files.

    This loader supports the MultiServerMCPClient configuration format
    which differs from the legacy MCPConfig format.
    """

    def __init__(self, config_path: Path):
        """
        Initialize the config loader.

        Args:
            config_path: Path to the mcp_config.yaml file
        """
        self.config_path = config_path

    def load_config(self) -> Dict[str, Any]:
        """
        Load MCP server configuration from YAML file.

        The configuration format is a dictionary where keys are server names
        and values are connection configurations.

        Returns:
            Dictionary mapping server names to their configurations.
            Returns empty dict if file doesn't exist or is empty.

        Raises:
            yaml.YAMLError: If the YAML file is malformed
            IOError: If there's an error reading the file
        """
        if not self.config_path.exists():
            logger.warning(f"MCP config file not found at {self.config_path}")
            return {}

        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)

            if config is None:
                logger.info("MCP config file is empty, no servers configured")
                return {}

            if not isinstance(config, dict):
                logger.error(f"Invalid MCP config format: expected dict, got {type(config)}")
                return {}

            # Expand environment variables in the configuration
            config = self._expand_env_vars(config)

            logger.info(f"Loaded MCP configuration with {len(config)} server(s)")
            return config

        except yaml.YAMLError as e:
            logger.error(f"Failed to parse MCP config YAML: {e}")
            raise
        except IOError as e:
            logger.error(f"Failed to read MCP config file: {e}")
            raise

    def _expand_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively expand environment variables in configuration values.

        Supports ${VAR_NAME} syntax for environment variable substitution.

        Args:
            config: Configuration dictionary

        Returns:
            Configuration with environment variables expanded
        """
        if isinstance(config, dict):
            return {k: self._expand_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._expand_env_vars(item) for item in config]
        elif isinstance(config, str):
            return os.path.expandvars(config)
        else:
            return config

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate the MCP server configuration.

        Args:
            config: Configuration dictionary to validate

        Returns:
            True if valid, False otherwise
        """
        if not config:
            return True  # Empty config is valid

        for server_name, server_config in config.items():
            if not isinstance(server_config, dict):
                logger.error(f"Invalid config for server '{server_name}': must be a dict")
                return False

            transport = server_config.get('transport')
            if not transport:
                logger.error(f"Server '{server_name}' missing required 'transport' field")
                return False

            if transport == 'streamable_http':
                if 'url' not in server_config:
                    logger.error(f"Server '{server_name}' with HTTP transport missing 'url' field")
                    return False
            elif transport == 'stdio':
                if 'command' not in server_config:
                    logger.error(f"Server '{server_name}' with stdio transport missing 'command' field")
                    return False
                if 'args' not in server_config:
                    logger.error(f"Server '{server_name}' with stdio transport missing 'args' field")
                    return False
            else:
                logger.error(f"Server '{server_name}' has unsupported transport type: {transport}")
                return False

        return True
