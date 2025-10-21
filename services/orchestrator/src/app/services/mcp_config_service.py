from app.models.mcp_config import MCPConfig
import yaml
from pathlib import Path
from pydantic import ValidationError
import logging

logger = logging.getLogger(__name__)


class MCPConfigService:
    def __init__(self, config_path: Path):
        self._config_path = config_path

    def load_config(self) -> MCPConfig:
        if not self._config_path.is_file():
            return MCPConfig(mcp_servers=[])
        try:
            with open(self._config_path, "r") as f:
                config_data = yaml.safe_load(f)
                if not config_data:
                    return MCPConfig(mcp_servers=[])
                return MCPConfig(**config_data)
        except (yaml.YAMLError, ValidationError) as e:
            raise ValueError(f"Error loading or validating MCP config: {e}") from e
        except IOError as e:
            logger.error(f"Could not read MCP config file: {e}")
            raise IOError(f"Could not read MCP config file: {e}") from e