from fastapi import FastAPI
from app.api.v1 import incidents
from app.services.knowledge_graph_service import KnowledgeGraphService
from app.services.mcp_config_service import MCPConfigService
from app.services.mcp_connection_manager import MCPConnectionManager
from pathlib import Path

app = FastAPI()

app.include_router(incidents.router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    app.state.knowledge_graph_service = KnowledgeGraphService(
        knowledge_graph_path=Path(__file__).parent.parent.parent.parent
        / "knowledge_graph.yaml"
    )
    mcp_config_service = MCPConfigService(
        config_path=Path(__file__).parent.parent.parent.parent
        / "mcp_config.yaml"
    )
    mcp_config = mcp_config_service.load_config()
    app.state.mcp_connection_manager = MCPConnectionManager(mcp_config)
    await app.state.mcp_connection_manager.connect_to_servers()


@app.on_event("shutdown")
async def shutdown_event():
    if hasattr(app.state, "mcp_connection_manager"):
        await app.state.mcp_connection_manager.disconnect_from_servers()


@app.get("/health")
def read_health():
    """
    Checks the health of the application.
    """
    return {"status": "ok"}
