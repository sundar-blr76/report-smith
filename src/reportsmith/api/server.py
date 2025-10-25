from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from reportsmith.app import ReportSmithApp
from reportsmith.query_processing import HybridIntentAnalyzer

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
intent_analyzer: HybridIntentAnalyzer | None = None


@app.on_event("startup")
def startup_event() -> None:
    global rs_app, intent_analyzer
    try:
        rs_app = ReportSmithApp()
        rs_app.initialize()
        # Initialize hybrid analyzer using existing embedding manager
        intent_analyzer = HybridIntentAnalyzer(embedding_manager=rs_app.embedding_manager)
    except Exception:
        # If initialization fails, the API can still respond with 503
        rs_app = None
        intent_analyzer = None


@app.on_event("shutdown")
def shutdown_event() -> None:
    global intent_analyzer
    if rs_app is not None:
        rs_app.shutdown()
    intent_analyzer = None


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

    if intent_analyzer is None:
        raise HTTPException(status_code=503, detail="Intent analyzer not initialized")

    # Step 1: Analyze intent
    try:
        intent = intent_analyzer.analyze(req.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Intent analysis failed: {e}")

    # Step 2: Retrieve matched entities and a simple plan (placeholder)
    data = {
        "question": req.question,
        "intent": {
            "type": intent.intent_type.value,
            "time_scope": intent.time_scope.value,
            "aggregations": [a.value for a in intent.aggregations],
            "filters": intent.filters,
            "limit": intent.limit,
            "order_by": intent.order_by,
            "order_direction": intent.order_direction,
            "entities": [
                {
                    "text": e.text,
                    "entity_type": e.entity_type,
                    "confidence": e.confidence,
                    "top_match": (e.semantic_matches[0] if e.semantic_matches else None),
                }
                for e in intent.entities
            ],
        },
        "components": {
            "config_manager": rs_app.config_manager is not None,
            "connection_manager": rs_app.connection_manager is not None,
            "embedding_manager": rs_app.embedding_manager is not None,
            "dimension_loader": rs_app.dimension_loader is not None,
        },
    }
    return QueryResponse(status="ok", data=data)
