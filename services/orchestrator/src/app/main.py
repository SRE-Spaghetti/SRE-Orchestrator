import logging
from dotenv import load_dotenv
from fastapi import FastAPI
from app.api.v1 import incidents
from app.services.knowledge_graph_service import KnowledgeGraphService
from app.services.mcp_config_service import MCPConfigService
from app.services.mcp_connection_manager import MCPConnectionManager
from app.services.langchain_llm_client import get_langchain_llm_client
from app.services.mcp_tool_manager import MCPToolManager
from app.services.mcp_tool_config_loader import MCPToolConfigLoader
from app.config import get_mcp_config_path
from pathlib import Path

load_dotenv()
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

    # Get MCP config path from environment variable or default locations
    mcp_config_path = get_mcp_config_path()
    logger.info(f"Using MCP configuration from: {mcp_config_path}")

    # Initialize MCP Tool Manager (new LangChain-based approach)
    try:
        logger.info(f"Loading MCP tool configuration from {mcp_config_path}")
        config_loader = MCPToolConfigLoader(config_path=mcp_config_path)
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

    # Keep legacy MCP Connection Manager for backward compatibility (will be removed later)
    try:
        mcp_config_service = MCPConfigService(config_path=mcp_config_path)
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

    Returns detailed health information including:
    - Overall application status
    - LangChain LLM client status
    - MCP tool availability
    - Agent initialization status
    """
    from datetime import datetime

    health_status = {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {},
    }

    # Track if any component is unhealthy
    all_healthy = True

    # Check LangChain LLM client status
    if hasattr(app.state, "langchain_llm_client") and app.state.langchain_llm_client:
        try:
            health_status["components"]["langchain_llm"] = {
                "status": "healthy",
                "model": app.state.langchain_llm_client.config.model_name,
                "base_url": app.state.langchain_llm_client.config.base_url,
                "temperature": app.state.langchain_llm_client.config.temperature,
                "max_tokens": app.state.langchain_llm_client.config.max_tokens,
            }
        except Exception as e:
            health_status["components"]["langchain_llm"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            all_healthy = False
    else:
        health_status["components"]["langchain_llm"] = {
            "status": "not_initialized",
            "message": "LangChain LLM client not initialized",
        }
        all_healthy = False

    # Check MCP Tool Manager status (new LangChain-based approach)
    if hasattr(app.state, "mcp_tool_manager") and app.state.mcp_tool_manager:
        try:
            if app.state.mcp_tool_manager.is_initialized():
                tool_count = app.state.mcp_tool_manager.get_tool_count()
                tool_names = app.state.mcp_tool_manager.get_tool_names()

                health_status["components"]["mcp_tools"] = {
                    "status": "healthy" if tool_count > 0 else "degraded",
                    "tool_count": tool_count,
                    "tools": tool_names,
                    "message": (
                        f"{tool_count} tool(s) available"
                        if tool_count > 0
                        else "No tools available"
                    ),
                }

                if tool_count == 0:
                    all_healthy = False
            else:
                health_status["components"]["mcp_tools"] = {
                    "status": "not_initialized",
                    "message": "MCP Tool Manager not initialized",
                }
                all_healthy = False
        except Exception as e:
            health_status["components"]["mcp_tools"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            all_healthy = False
    else:
        health_status["components"]["mcp_tools"] = {
            "status": "not_initialized",
            "message": "MCP Tool Manager not available",
        }
        all_healthy = False

    # Check agent initialization status
    # Agent is created on-demand, so we check if prerequisites are available
    agent_prerequisites_met = (
        hasattr(app.state, "langchain_llm_client")
        and app.state.langchain_llm_client
        and hasattr(app.state, "mcp_tool_manager")
        and app.state.mcp_tool_manager
        and app.state.mcp_tool_manager.is_initialized()
    )

    if agent_prerequisites_met:
        health_status["components"]["investigation_agent"] = {
            "status": "ready",
            "message": "Agent can be created on-demand",
            "prerequisites": {"llm_client": "available", "mcp_tools": "available"},
        }
    else:
        missing_prerequisites = []
        if not (
            hasattr(app.state, "langchain_llm_client")
            and app.state.langchain_llm_client
        ):
            missing_prerequisites.append("llm_client")
        if not (
            hasattr(app.state, "mcp_tool_manager")
            and app.state.mcp_tool_manager
            and app.state.mcp_tool_manager.is_initialized()
        ):
            missing_prerequisites.append("mcp_tools")

        health_status["components"]["investigation_agent"] = {
            "status": "not_ready",
            "message": "Agent prerequisites not met",
            "missing_prerequisites": missing_prerequisites,
        }
        all_healthy = False

    # Check legacy MCP connection status (will be removed later)
    if (
        hasattr(app.state, "mcp_connection_manager")
        and app.state.mcp_connection_manager
    ):
        try:
            mcp_statuses = (
                await app.state.mcp_connection_manager.get_connection_statuses()
            )
            health_status["components"]["mcp_connections_legacy"] = {
                "status": "healthy",
                "connections": mcp_statuses,
                "message": "Legacy MCP connections (deprecated)",
            }
        except Exception as e:
            health_status["components"]["mcp_connections_legacy"] = {
                "status": "unhealthy",
                "error": str(e),
                "message": "Legacy MCP connections (deprecated)",
            }
    else:
        health_status["components"]["mcp_connections_legacy"] = {
            "status": "not_initialized",
            "message": "Legacy MCP connections not available (deprecated)",
        }

    # Set overall status based on component health
    if not all_healthy:
        health_status["status"] = "degraded"

    return health_status
