from fastapi import FastAPI
from app.api.v1 import incidents

app = FastAPI()

app.include_router(incidents.router, prefix="/api/v1")

@app.get("/health")
def read_health():
    """
    Checks the health of the application.
    """
    return {"status": "ok"}
