"""Configuration management for CLI."""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any


class ConfigError(Exception):
    """Raised when configuration operations fail."""

    pass


class Config:
    """Manages CLI configuration from file and environment variables."""

    DEFAULT_CONFIG_DIR = Path.home() / ".sre-orchestrator"
    DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.yaml"

    # Environment variable mappings
    ENV_VARS = {
        "orchestrator_url": "SRE_ORCHESTRATOR_URL",
        "api_key": "SRE_ORCHESTRATOR_API_KEY",
    }

    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize configuration manager.

        Args:
            config_file: Path to config file (defaults to ~/.sre-orchestrator/config.yaml)
        """
        self.config_file = config_file or self.DEFAULT_CONFIG_FILE
        self._config: Dict[str, Any] = {}
        self._load()

    def _load(self):
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    self._config = yaml.safe_load(f) or {}
            except Exception as e:
                raise ConfigError(f"Failed to load config from {self.config_file}: {e}")
        else:
            self._config = {}

    def _save(self):
        """Save configuration to file."""
        try:
            # Create config directory if it doesn't exist
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            # Write config file with secure permissions
            with open(self.config_file, "w") as f:
                yaml.safe_dump(self._config, f, default_flow_style=False)

            # Set file permissions to 0600 (owner read/write only)
            self.config_file.chmod(0o600)

        except Exception as e:
            raise ConfigError(f"Failed to save config to {self.config_file}: {e}")

    def get(self, key: str) -> Optional[str]:
        """
        Get a configuration value.

        Checks in order:
        1. Environment variable
        2. Config file

        Args:
            key: Configuration key

        Returns:
            Configuration value or None if not found
        """
        # Check environment variable first
        env_var = self.ENV_VARS.get(key)
        if env_var:
            env_value = os.environ.get(env_var)
            if env_value:
                return env_value

        # Check config file
        return self._config.get(key)

    def set(self, key: str, value: str):
        """
        Set a configuration value in the config file.

        Args:
            key: Configuration key
            value: Configuration value
        """
        self._config[key] = value
        self._save()

    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration values.

        Returns:
            Dictionary of all config values (from file and environment)
        """
        result = dict(self._config)

        # Override with environment variables
        for key, env_var in self.ENV_VARS.items():
            env_value = os.environ.get(env_var)
            if env_value:
                result[key] = env_value

        return result

    def delete(self, key: str):
        """
        Delete a configuration value from the config file.

        Args:
            key: Configuration key
        """
        if key in self._config:
            del self._config[key]
            self._save()
