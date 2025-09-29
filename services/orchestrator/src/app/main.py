from fastapi import FastAPI
from app.api.v1 import incidents
from app.services.knowledge_graph_service import KnowledgeGraphService
from pathlib import Path

app = FastAPI()

app.include_router(incidents.router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    app.state.knowledge_graph_service = KnowledgeGraphService(knowledge_graph_path=Path(__file__).parent.parent.parent.parent / "knowledge_graph.yaml")

@app.get("/health")
def read_health():
    """
    Checks the health of the application.
    """
    return {"status": "ok"}