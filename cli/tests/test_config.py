"""Tests for CLI configuration management."""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from sre_orchestrator_cli.config import Config, ConfigError


@pytest.fixture
def temp_config_file(tmp_path):
    """Create temporary config file."""
    config_file = tmp_path / "config.yaml"
    return config_file


class TestConfig:
    """Tests for Config class."""

    def test_initialization_no_file(self, temp_config_file):
        """Test initialization when config file doesn't exist."""
        config = Config(config_file=temp_config_file)

        assert config.config_file == temp_config_file
        assert config._config == {}

    def test_initialization_with_existing_file(self, temp_config_file):
        """Test initialization with existing config file."""
        # Create config file
        temp_config_file.write_text("orchestrator_url: http://localhost:8000\napi_key: test-key")

        config = Config(config_file=temp_config_file)

        assert config.get("orchestrator_url") == "http://localhost:8000"
        assert config.get("api_key") == "test-key"

    def test_set_and_get(self, temp_config_file):
        """Test setting and getting config values."""
        config = Config(config_file=temp_config_file)

        config.set("orchestrator_url", "http://localhost:8000")
        config.set("api_key", "test-key-123")

        assert config.get("orchestrator_url") == "http://localhost:8000"
        assert config.get("api_key") == "test-key-123"

    def test_set_creates_directory(self, tmp_path):
        """Test that set creates config directory if it doesn't exist."""
        config_file = tmp_path / "subdir" / "config.yaml"
        config = Config(config_file=config_file)

        config.set("test_key", "test_value")

        assert config_file.exists()
        assert config_file.parent.exists()

    def test_set_creates_secure_permissions(self, temp_config_file):
        """Test that config file has secure permissions."""
        config = Config(config_file=temp_config_file)

        config.set("api_key", "secret-key")

        # Check file permissions (should be 0600)
        stat_info = temp_config_file.stat()
        permissions = oct(stat_info.st_mode)[-3:]
        assert permissions == "600"

    def test_get_from_environment_variable(self, temp_config_file):
        """Test getting value from environment variable."""
        config = Config(config_file=temp_config_file)
        config.set("orchestrator_url", "http://file-url:8000")

        # Environment variable should override file
        with patch.dict(os.environ, {"SRE_ORCHESTRATOR_URL": "http://env-url:8000"}):
            assert config.get("orchestrator_url") == "http://env-url:8000"

    def test_get_nonexistent_key(self, temp_config_file):
        """Test getting nonexistent key returns None."""
        config = Config(config_file=temp_config_file)

        assert config.get("nonexistent_key") is None

    def test_get_all(self, temp_config_file):
        """Test getting all config values."""
        config = Config(config_file=temp_config_file)
        config.set("orchestrator_url", "http://localhost:8000")
        config.set("api_key", "test-key")

        all_config = config.get_all()

        assert all_config["orchestrator_url"] == "http://localhost:8000"
        assert all_config["api_key"] == "test-key"

    def test_get_all_with_env_override(self, temp_config_file):
        """Test get_all with environment variable override."""
        config = Config(config_file=temp_config_file)
        config.set("orchestrator_url", "http://file-url:8000")

        with patch.dict(os.environ, {"SRE_ORCHESTRATOR_URL": "http://env-url:8000"}):
            all_config = config.get_all()

            assert all_config["orchestrator_url"] == "http://env-url:8000"

    def test_delete(self, temp_config_file):
        """Test deleting config value."""
        config = Config(config_file=temp_config_file)
        config.set("test_key", "test_value")

        assert config.get("test_key") == "test_value"

        config.delete("test_key")

        assert config.get("test_key") is None

    def test_delete_nonexistent_key(self, temp_config_file):
        """Test deleting nonexistent key doesn't raise error."""
        config = Config(config_file=temp_config_file)

        # Should not raise error
        config.delete("nonexistent_key")

    def test_load_invalid_yaml(self, temp_config_file):
        """Test loading invalid YAML raises ConfigError."""
        temp_config_file.write_text("invalid: yaml: content:")

        with pytest.raises(ConfigError, match="Failed to load config"):
            Config(config_file=temp_config_file)
