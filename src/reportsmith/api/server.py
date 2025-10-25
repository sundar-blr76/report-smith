from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel

from reportsmith.app import ReportSmithApp
from reportsmith.query_processing import HybridIntentAnalyzer
from reportsmith.agents import MultiAgentOrchestrator

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
orchestrator: MultiAgentOrchestrator | None = None


# Request ID middleware
from uuid import uuid4
from reportsmith.logger import bind_request_id, clear_request_id


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    rid = request.headers.get("x-request-id") or uuid4().hex
    bind_request_id(rid)
    try:
        response: Response = await call_next(request)
    finally:
        clear_request_id()
    response.headers["X-Request-ID"] = rid
    return response


@app.on_event("startup")
def startup_event() -> None:
    global rs_app, intent_analyzer, orchestrator
    try:
        rs_app = ReportSmithApp()
        rs_app.initialize()
        # Initialize hybrid analyzer and orchestrator
        intent_analyzer = HybridIntentAnalyzer(embedding_manager=rs_app.embedding_manager)
        from reportsmith.schema_intelligence.graph_builder import KnowledgeGraphBuilder
        gb = KnowledgeGraphBuilder()
        # Build KG from first app's schema
        apps = rs_app.config_manager.load_all_applications()
        kg = None
        if apps:
            app0 = apps[0]
            for db in app0.databases:
                schema_config = {
                    "tables": {t.name: {"description": t.description or "", "primary_key": t.primary_key or "", "columns": t.columns} for t in db.tables}
                }
                kg = gb.build_from_schema(schema_config)
                break
        from reportsmith.agents import MultiAgentOrchestrator
        orchestrator = MultiAgentOrchestrator(
            intent_analyzer=intent_analyzer,
            graph_builder=gb,
            knowledge_graph=kg or gb.build_from_schema({"tables": {}}),
        )
    except Exception:
        # If initialization fails, the API can still respond with 503
        rs_app = None
        intent_analyzer = None
        orchestrator = None


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


@app.get("/ready")
def ready() -> Dict[str, Any]:
    components = {
        "rs_app": rs_app is not None,
        "intent_analyzer": intent_analyzer is not None,
        "orchestrator": orchestrator is not None,
    }
    is_ready = all(components.values())
    if not is_ready:
        # 503 with component breakdown
        raise HTTPException(status_code=503, detail={"ready": False, "components": components})
    return {"ready": True, "components": components}


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    if rs_app is None:
        raise HTTPException(status_code=503, detail="ReportSmith not initialized")

    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    # Run multi-agent graph for the question
    try:
        from reportsmith.logger import get_logger
        get_logger(__name__).info("[api] supervisor handling /query; delegating to orchestrator")
        final_state = orchestrator.run(req.question)
    except Exception as e:
        from reportsmith.logger import get_logger
        get_logger(__name__).error(f"[api] orchestration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Orchestration failed: {e}")

    def _get(obj, key):
        return obj.get(key) if isinstance(obj, dict) else getattr(obj, key, None)

    data = {
        "question": req.question,
        "intent": _get(final_state, "intent"),
        "entities": _get(final_state, "entities"),
        "tables": _get(final_state, "tables"),
        "plan": _get(final_state, "plan"),
        "result": _get(final_state, "result"),
        "errors": _get(final_state, "errors"),
    }
    return QueryResponse(status="ok", data=data)
