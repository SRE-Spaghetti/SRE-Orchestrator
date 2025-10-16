from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class MCPAuthentication(BaseModel):
    """Authentication details for an MCP server."""
    username: str
    password: str

class MCPServer(BaseModel):
    """Configuration for a single MCP server."""
    server_url: str
    transport_type: Literal["http", "https"]
    authentication: Optional[MCPAuthentication] = None

class MCPConfig(BaseModel):
    """Root model for the MCP configuration file."""
    mcp_servers: List[MCPServer] = Field(default_factory=list)
