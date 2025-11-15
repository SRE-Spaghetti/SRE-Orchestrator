from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Optional
from enum import Enum


class TransportType(str, Enum):
    """Supported MCP transport types."""
    STREAMABLE_HTTP = "streamable_http"
    STDIO = "stdio"


class StdioServerConfig(BaseModel):
    """Configuration for stdio-based MCP servers (local processes)."""
    command: str = Field(..., description="Command to execute (e.g., 'npx', 'python')")
    args: List[str] = Field(..., description="Command arguments")
    transport: str = Field("stdio", description="Transport type (must be 'stdio')")
    env: Optional[Dict[str, str]] = Field(None, description="Environment variables")

    model_config = ConfigDict(extra="forbid")


class HttpServerConfig(BaseModel):
    """Configuration for HTTP-based MCP servers."""
    url: str = Field(..., description="Server URL")
    transport: str = Field("streamable_http", description="Transport type (must be 'streamable_http')")
    headers: Optional[Dict[str, str]] = Field(None, description="HTTP headers (e.g., for authentication)")

    model_config = ConfigDict(extra="forbid")


class MCPServerConfig(BaseModel):
    """
    Generic MCP server configuration.
    Can be either stdio or HTTP-based.

    This model is used for validation purposes. The actual configuration
    is stored as a dictionary for compatibility with MultiServerMCPClient.
    """
    transport: TransportType = Field(..., description="Transport type")

    # Stdio fields
    command: Optional[str] = Field(None, description="Command for stdio transport")
    args: Optional[List[str]] = Field(None, description="Arguments for stdio transport")
    env: Optional[Dict[str, str]] = Field(None, description="Environment variables for stdio transport")

    # HTTP fields
    url: Optional[str] = Field(None, description="URL for HTTP transport")
    headers: Optional[Dict[str, str]] = Field(None, description="Headers for HTTP transport")

    model_config = ConfigDict(extra="allow")
