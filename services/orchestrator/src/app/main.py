import logging
from fastapi import FastAPI
from app.api.v1 import incidents
from app.services.knowledge_graph_service import KnowledgeGraphService
from app.services.mcp_config_service import MCPConfigService
from app.services.mcp_connection_manager import MCPConnectionManager
from app.services.langchain_llm_client import get_langchain_llm_client, LangChainLLMClient
from app.services.mcp_tool_manager import MCPToolManager
from app.services.mcp_tool_config_loader import MCPToolConfigLoader
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

    # Initialize MCP Tool Manager (new LangChain-based approach)
    mcp_tool_config_path = Path("/config/mcp_config.yaml")
    if not mcp_tool_config_path.exists():
        mcp_tool_config_path = (
            Path(__file__).parent.parent.parent.parent / "mcp_config.yaml"
        )

    try:
        logger.info(f"Loading MCP tool configuration from {mcp_tool_config_path}")
        config_loader = MCPToolConfigLoader(config_path=mcp_tool_config_path)
        mcp_tool_config = config_loader.load_config()

        if config_loader.validate_config(mcp_tool_config):
            app.state.mcp_tool_manager = MCPToolManager(mcp_tool_config)
            await app.state.mcp_tool_manager.initialize()
            logger.info(
                f"MCP Tool Manager initialized successfully with "
                f"{app.state.mcp_tool_manager.get_tool_count()} tool(s)"
            )
        else:
            logger.error("MCP tool configuration validation failed")
            app.state.mcp_tool_manager = None
    except Exception as e:
        logger.warning(f"Failed to initialize MCP Tool Manager: {e}", exc_info=True)
        app.state.mcp_tool_manager = None

    # TODO: Pass the mcp_server.yaml as a command line argument to the orchestrator instead of copying a file
    # Keep legacy MCP Connection Manager for backward compatibility (will be removed later)
    legacy_config_path = Path("/config/mcp_config.yaml")
    if not legacy_config_path.exists():
        legacy_config_path = (
            Path(__file__).parent.parent.parent.parent.parent / "mcp_config.yaml"
        )

    try:
        mcp_config_service = MCPConfigService(config_path=legacy_config_path)
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
    # Cleanup MCP Tool Manager
    if hasattr(app.state, "mcp_tool_manager") and app.state.mcp_tool_manager:
        await app.state.mcp_tool_manager.cleanup()
        logger.info("MCP Tool Manager cleaned up")

    # Cleanup legacy MCP Connection Manager
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

    # Check MCP Tool Manager status (new LangChain-based approach)
    if hasattr(app.state, "mcp_tool_manager") and app.state.mcp_tool_manager:
        if app.state.mcp_tool_manager.is_initialized():
            health_status["mcp_tools"] = {
                "status": "initialized",
                "tool_count": app.state.mcp_tool_manager.get_tool_count(),
                "tools": app.state.mcp_tool_manager.get_tool_names()
            }
        else:
            health_status["mcp_tools"] = {"status": "not initialized"}
    else:
        health_status["mcp_tools"] = {"status": "not initialized"}

    # Check legacy MCP connection status (will be removed later)
    if (
        hasattr(app.state, "mcp_connection_manager")
        and app.state.mcp_connection_manager
    ):
        mcp_statuses = await app.state.mcp_connection_manager.get_connection_statuses()
        health_status["mcp_connections"] = mcp_statuses
    else:
        health_status["mcp_connections"] = {"status": "not initialized"}
    return health_status
