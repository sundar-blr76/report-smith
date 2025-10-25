from typing import Any, Dict

from fastapi import FastAPI, HTTPException
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


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    if rs_app is None:
        raise HTTPException(status_code=503, detail="ReportSmith not initialized")

    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    # Run multi-agent graph for the question
    try:
        final_state = orchestrator.run(req.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Orchestration failed: {e}")

    data = {
        "question": req.question,
        "intent": final_state.intent,
        "entities": final_state.entities,
        "tables": final_state.tables,
        "plan": final_state.plan,
        "result": final_state.result,
        "errors": final_state.errors,
    }
    return QueryResponse(status="ok", data=data)
