from pydantic import BaseModel, Field, SecretStr
from typing import List, Optional
from enum import Enum


class TransportType(str, Enum):
    HTTP = "http"
    HTTPS = "https"


class MCPAuthentication(BaseModel):
    username: str
    password: SecretStr


class MCPServerConfig(BaseModel):
    server_url: str
    transport_type: TransportType = Field(
        ..., description="The transport type (e.g., 'http', 'grpc')."
    )
    authentication: Optional[MCPAuthentication] = None


class MCPConfig(BaseModel):
    mcp_servers: List[MCPServerConfig]
