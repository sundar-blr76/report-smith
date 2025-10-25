from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from reportsmith.app import ReportSmithApp

app = FastAPI(title="ReportSmith API", version="0.1.0")


class QueryRequest(BaseModel):
    question: str
    app_id: str | None = None


class QueryResponse(BaseModel):
    status: str
    message: str | None = None
    data: Dict[str, Any] | None = None


# Lazily initialize the core app on startup
rs_app: ReportSmithApp | None = None


@app.on_event("startup")
def startup_event() -> None:
    global rs_app
    try:
        rs_app = ReportSmithApp()
        rs_app.initialize()
    except Exception as e:
        # If initialization fails, the API can still respond with 503
        rs_app = None


@app.on_event("shutdown")
def shutdown_event() -> None:
    if rs_app is not None:
        rs_app.shutdown()


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/info")
def info() -> Dict[str, Any]:
    return {
        "app": app.title,
        "version": app.version,
        "initialized": rs_app is not None,
    }


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    if rs_app is None:
        raise HTTPException(status_code=503, detail="ReportSmith not initialized")

    # Placeholder for wiring in actual NL → SQL logic
    # For now, just echo the request and report readiness of components
    try:
        data = {
            "question": req.question,
            "app_id": req.app_id,
            "components": {
                "config_manager": rs_app.config_manager is not None,
                "connection_manager": rs_app.connection_manager is not None,
                "embedding_manager": rs_app.embedding_manager is not None,
                "dimension_loader": rs_app.dimension_loader is not None,
            },
        }
        return QueryResponse(status="ok", data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
