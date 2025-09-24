from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def read_health():
    """
    Checks the health of the application.
    """
    return {"status": "ok"}
