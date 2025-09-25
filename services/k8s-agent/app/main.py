from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.v1.pods import router as pods_router
from app.services.k8s_client import initialize_kubernetes_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    initialize_kubernetes_client()
    yield
    # Shutdown logic (if any)

app = FastAPI(lifespan=lifespan)

@app.get("/health")
def read_health():
    return {"status": "ok"}

app.include_router(pods_router, prefix="/api/v1")
