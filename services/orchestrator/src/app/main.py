import logging
from fastapi import FastAPI
from app.api.v1 import incidents
from app.services.knowledge_graph_service import KnowledgeGraphService
from app.services.mcp_config_service import MCPConfigService
from app.services.mcp_connection_manager import MCPConnectionManager
from app.services.langchain_llm_client import get_langchain_llm_client, LangChainLLMClient
from pathlib import Path

app = FastAPI()


# Define a filter to exclude /health endpoint from logs
class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "GET /health" not in record.getMessage()


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add the filter to the uvicorn access logger
logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())

app.include_router(incidents.router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    app.state.knowledge_graph_service = KnowledgeGraphService(
        knowledge_graph_path=Path(__file__).parent.parent.parent.parent.parent
        / "knowledge_graph.yaml"
    )

    # Initialize LangChain LLM client (keep old LLM client for comparison)
    try:
        app.state.langchain_llm_client = get_langchain_llm_client()
        logger.info("LangChain LLM client initialized successfully.")
    except Exception as e:
        logger.warning(f"Failed to initialize LangChain LLM client: {e}")
        app.state.langchain_llm_client = None

    # TODO: Pass the mcp_server.yaml as a command line argument to the orchestrator instead of copying a file
    config_path = Path("/config/mcp_config.yaml")
    if not config_path.exists():
        config_path = (
            Path(__file__).parent.parent.parent.parent.parent / "mcp_config.yaml"
        )

    try:
        mcp_config_service = MCPConfigService(config_path=config_path)
        mcp_config = mcp_config_service.load_config()
        app.state.mcp_connection_manager = MCPConnectionManager(mcp_config)
        await app.state.mcp_connection_manager.connect_to_servers()
        logger.info("MCP Connection Manager initialized and connected to servers.")
    except Exception as e:
        logger.warning(
            f"Failed to initialize MCP Connection Manager or connect to servers: {e}"
        )
        app.state.mcp_connection_manager = (
            None  # Ensure manager is not set if connection fails
        )


@app.on_event("shutdown")
async def shutdown_event():
    if (
        hasattr(app.state, "mcp_connection_manager")
        and app.state.mcp_connection_manager
    ):
        await app.state.mcp_connection_manager.disconnect_from_servers()


@app.get("/health")
async def read_health():
    """
    Checks the health of the application and MCP connection status.
    """
    health_status = {"status": "ok"}

    # Check LangChain LLM client status
    if hasattr(app.state, "langchain_llm_client") and app.state.langchain_llm_client:
        health_status["langchain_llm"] = {
            "status": "initialized",
            "model": app.state.langchain_llm_client.config.model_name
        }
    else:
        health_status["langchain_llm"] = {"status": "not initialized"}

    # Check MCP connection status
    if (
        hasattr(app.state, "mcp_connection_manager")
        and app.state.mcp_connection_manager
    ):
        mcp_statuses = await app.state.mcp_connection_manager.get_connection_statuses()
        health_status["mcp_connections"] = mcp_statuses
    else:
        health_status["mcp_connections"] = {"status": "not initialized"}
    return health_status
