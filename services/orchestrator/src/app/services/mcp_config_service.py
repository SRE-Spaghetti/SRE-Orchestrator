import yaml
from pathlib import Path
from typing import Optional
from ..models.mcp_config import MCPConfig
from pydantic import ValidationError

class MCPConfigService:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._config: Optional[MCPConfig] = self._load_config()

    def _load_config(self) -> Optional[MCPConfig]:
        if not self.config_path.is_file():
            # Handle missing file gracefully as per AC 5
            return None
        try:
            with open(self.config_path, "r") as f:
                data = yaml.safe_load(f)
                if data is None:
                    # Handle empty file
                    return MCPConfig(mcp_servers=[])
                return MCPConfig(**data)
        except (yaml.YAMLError, ValidationError) as e:
            # Broad exception for parsing/validation errors
            raise ValueError(f"Error loading or validating MCP config: {self.config_path}\n{e}") from e
        except Exception as e:
            raise IOError(f"Could not read MCP config file: {self.config_path}") from e

    def get_config(self) -> Optional[MCPConfig]:
        """Returns the loaded MCP configuration."""
        return self._config
