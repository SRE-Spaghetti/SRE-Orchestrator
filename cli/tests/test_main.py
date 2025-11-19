"""Tests for CLI main commands."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from click.testing import CliRunner

from sre_orchestrator_cli.main import cli


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_config():
    """Mock config with test values."""
    config = Mock()
    config.get.side_effect = lambda key: {
        "orchestrator_url": "http://localhost:8000",
        "api_key": "test-key",
    }.get(key)
    config.get_all.return_value = {
        "orchestrator_url": "http://localhost:8000",
        "api_key": "test-key",
    }
    return config


class TestInvestigateCommand:
    """Tests for investigate command."""

    def test_investigate_success(self, runner, mock_config):
        """Test successful investigation."""
        with patch("sre_orchestrator_cli.main.Config", return_value=mock_config):
            with patch(
                "sre_orchestrator_cli.main.OrchestratorClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client.create_incident.return_value = {
                    "incident_id": "incident-123",
                    "status": "investigating",
                }
                mock_client.get_incident.return_value = {
                    "id": "incident-123",
                    "status": "completed",
                    "root_cause": "Memory issue",
                    "confidence": "high",
                }
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client_class.return_value = mock_client

                result = runner.invoke(
                    cli, ["investigate", "Pod is crashing", "--wait"]
                )

                assert result.exit_code == 0
                assert "incident-123" in result.output

    def test_investigate_no_wait(self, runner, mock_config):
        """Test investigation without waiting."""
        with patch("sre_orchestrator_cli.main.Config", return_value=mock_config):
            with patch(
                "sre_orchestrator_cli.main.OrchestratorClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client.create_incident.return_value = {
                    "incident_id": "incident-123",
                    "status": "investigating",
                }
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client_class.return_value = mock_client

                result = runner.invoke(
                    cli, ["investigate", "Pod is crashing", "--no-wait"]
                )

                assert result.exit_code == 0
                assert "incident-123" in result.output
                # Should not call get_incident when not waiting
                mock_client.get_incident.assert_not_called()

    def test_investigate_with_url_override(self, runner):
        """Test investigation with URL override."""
        mock_config = Mock()
        mock_config.get.return_value = None

        with patch("sre_orchestrator_cli.main.Config", return_value=mock_config):
            with patch(
                "sre_orchestrator_cli.main.OrchestratorClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client.create_incident.return_value = {
                    "incident_id": "incident-123",
                    "status": "investigating",
                }
                mock_client.get_incident.return_value = {
                    "id": "incident-123",
                    "status": "completed",
                }
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client_class.return_value = mock_client

                result = runner.invoke(
                    cli,
                    [
                        "investigate",
                        "Pod is crashing",
                        "--url",
                        "http://custom:8000",
                        "--wait",
                    ],
                )

                assert result.exit_code == 0
                # Verify client was created with custom URL
                mock_client_class.assert_called_once()
                call_kwargs = mock_client_class.call_args[1]
                assert call_kwargs["base_url"] == "http://custom:8000"

    def test_investigate_no_url_configured(self, runner):
        """Test investigation with no URL configured."""
        mock_config = Mock()
        mock_config.get.return_value = None

        with patch("sre_orchestrator_cli.main.Config", return_value=mock_config):
            result = runner.invoke(cli, ["investigate", "Pod is crashing"])

            assert result.exit_code == 0
            assert "not configured" in result.output


class TestListCommand:
    """Tests for list command."""

    def test_list_success(self, runner, mock_config):
        """Test successful incident listing."""
        with patch("sre_orchestrator_cli.main.Config", return_value=mock_config):
            with patch(
                "sre_orchestrator_cli.main.OrchestratorClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client.list_incidents.return_value = [
                    {"id": "incident-1", "status": "completed"},
                    {"id": "incident-2", "status": "investigating"},
                ]
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client_class.return_value = mock_client

                result = runner.invoke(cli, ["list"])

                assert result.exit_code == 0
                mock_client.list_incidents.assert_called_once_with(limit=10)

    def test_list_with_limit(self, runner, mock_config):
        """Test listing with custom limit."""
        with patch("sre_orchestrator_cli.main.Config", return_value=mock_config):
            with patch(
                "sre_orchestrator_cli.main.OrchestratorClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client.list_incidents.return_value = []
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client_class.return_value = mock_client

                result = runner.invoke(cli, ["list", "--limit", "20"])

                assert result.exit_code == 0
                mock_client.list_incidents.assert_called_once_with(limit=20)


class TestShowCommand:
    """Tests for show command."""

    def test_show_success(self, runner, mock_config):
        """Test successful incident display."""
        with patch("sre_orchestrator_cli.main.Config", return_value=mock_config):
            with patch(
                "sre_orchestrator_cli.main.OrchestratorClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get_incident.return_value = {
                    "id": "incident-123",
                    "status": "completed",
                    "root_cause": "Memory issue",
                }
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client_class.return_value = mock_client

                result = runner.invoke(cli, ["show", "incident-123"])

                assert result.exit_code == 0
                mock_client.get_incident.assert_called_once_with("incident-123")


class TestConfigCommands:
    """Tests for config commands."""

    def test_config_set(self, runner):
        """Test setting config value."""
        mock_config = Mock()

        with patch("sre_orchestrator_cli.main.Config", return_value=mock_config):
            result = runner.invoke(
                cli, ["config", "set", "orchestrator-url", "http://localhost:8000"]
            )

            assert result.exit_code == 0
            mock_config.set.assert_called_once_with(
                "orchestrator-url", "http://localhost:8000"
            )

    def test_config_get(self, runner):
        """Test getting config value."""
        mock_config = Mock()
        mock_config.get.return_value = "http://localhost:8000"

        with patch("sre_orchestrator_cli.main.Config", return_value=mock_config):
            result = runner.invoke(cli, ["config", "get", "orchestrator-url"])

            assert result.exit_code == 0
            assert "http://localhost:8000" in result.output
            mock_config.get.assert_called_once_with("orchestrator-url")

    def test_config_get_nonexistent(self, runner):
        """Test getting nonexistent config value."""
        mock_config = Mock()
        mock_config.get.return_value = None

        with patch("sre_orchestrator_cli.main.Config", return_value=mock_config):
            result = runner.invoke(cli, ["config", "get", "nonexistent"])

            assert result.exit_code == 0
            assert "not set" in result.output

    def test_config_list(self, runner, mock_config):
        """Test listing all config values."""
        with patch("sre_orchestrator_cli.main.Config", return_value=mock_config):
            result = runner.invoke(cli, ["config", "list"])

            assert result.exit_code == 0
            assert "orchestrator_url" in result.output

    def test_config_list_masks_api_key(self, runner):
        """Test that config list masks API key."""
        mock_config = Mock()
        mock_config.get_all.return_value = {
            "orchestrator_url": "http://localhost:8000",
            "api_key": "secret-key-12345",
        }

        with patch("sre_orchestrator_cli.main.Config", return_value=mock_config):
            result = runner.invoke(cli, ["config", "list"])

            assert result.exit_code == 0
            assert "secret-key-12345" not in result.output
            assert "****" in result.output or "2345" in result.output
