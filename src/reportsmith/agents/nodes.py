from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from reportsmith.query_processing import HybridIntentAnalyzer
from reportsmith.schema_intelligence.knowledge_graph import SchemaKnowledgeGraph
from reportsmith.schema_intelligence.graph_builder import KnowledgeGraphBuilder
from reportsmith.logger import get_logger

logger = get_logger(__name__)


class QueryState(BaseModel):
    question: str
    intent: Dict[str, Any] | None = None
    entities: List[Dict[str, Any]] = Field(default_factory=list)
    tables: List[str] = Field(default_factory=list)
    plan: Dict[str, Any] | None = None
    result: Dict[str, Any] | None = None
    errors: List[str] = Field(default_factory=list)
    timings: Dict[str, float] = Field(default_factory=dict)
    llm_summaries: List[Dict[str, Any]] = Field(default_factory=list)


class AgentNodes:
    def __init__(
        self,
        *,
        intent_analyzer: HybridIntentAnalyzer,
        graph_builder: KnowledgeGraphBuilder,
        knowledge_graph: SchemaKnowledgeGraph,
    ) -> None:
        self.intent_analyzer = intent_analyzer
        self.graph_builder = graph_builder
        self.knowledge_graph = knowledge_graph

    # Node: analyze intent
    def analyze_intent(self, state: QueryState) -> QueryState:
        logger.info("[supervisor] received question; delegating to intent analyzer")
        import time
        t0 = time.perf_counter()
        try:
            intent = self.intent_analyzer.analyze(state.question)
            dt_ms = (time.perf_counter() - t0) * 1000.0
            state.timings["intent_ms"] = round(dt_ms, 2)
            logger.info(
                f"[intent] analyzed question; type={intent.intent_type.value}, time_scope={intent.time_scope.value}, aggs={len(intent.aggregations)}, filters={len(intent.filters)} in {dt_ms:.1f}ms"
            )
            # Capture LLM summary if present
            lm = getattr(self.intent_analyzer, "last_metrics", None)
            if lm:
                state.llm_summaries.append(lm)
                logger.info(
                    f"[intent][llm] provider={lm.get('provider')} model={lm.get('model')} prompt_chars={lm.get('prompt_chars')} latency_ms={lm.get('latency_ms')} tokens={lm.get('tokens')}"
                )
            entities = [
                {
                    "text": e.text,
                    "entity_type": e.entity_type,
                    "confidence": e.confidence,
                    "top_match": (e.semantic_matches[0] if e.semantic_matches else None),
                }
                for e in intent.entities
            ]
            logger.info(f"[intent] extracted {len(entities)} entities")
            state.intent = {
                "type": intent.intent_type.value,
                "time_scope": intent.time_scope.value,
                "aggregations": [a.value for a in intent.aggregations],
                "filters": intent.filters,
            }
            state.entities = entities
            return state
        except Exception as e:
            logger.error(f"[intent] error: {e}")
            state.errors.append(f"intent_error: {e}")
            return state

    # Node: map to schema tables
    def map_schema(self, state: QueryState) -> QueryState:
        logger.info("[supervisor] delegating to schema mapper")
        import time
        t0 = time.perf_counter()
        try:
            tables: List[str] = []
            for ent in state.entities:
                match = ent.get("top_match") or {}
                md = match.get("metadata") or {}
                table = md.get("table")
                if table and table not in tables:
                    tables.append(table)
                if ent.get("entity_type") == "table" and ent.get("text") not in tables:
                    tables.append(ent["text"]) 
            state.tables = tables
            dt_ms = (time.perf_counter() - t0) * 1000.0
            state.timings["schema_ms"] = round(dt_ms, 2)
            logger.info(f"[schema] mapped entities to {len(tables)} table(s): {tables} in {dt_ms:.1f}ms")
            return state
        except Exception as e:
            logger.error(f"[schema] error: {e}")
            state.errors.append(f"schema_map_error: {e}")
            return state

    # Node: plan (placeholder)
    def plan_query(self, state: QueryState) -> QueryState:
        logger.info("[supervisor] delegating to planner")
        import time
        t0 = time.perf_counter()
        try:
            state.plan = {
                "strategy": "single_db_join",
                "tables": state.tables,
                "notes": "Planning is a placeholder. Next step: derive join path from knowledge graph and generate SQL.",
            }
            dt_ms = (time.perf_counter() - t0) * 1000.0
            state.timings["plan_ms"] = round(dt_ms, 2)
            logger.info(f"[planner] produced plan for {len(state.tables)} table(s) in {dt_ms:.1f}ms")
            return state
        except Exception as e:
            logger.error(f"[planner] error: {e}")
            state.errors.append(f"plan_error: {e}")
            return state

    # Node: finalize response (no execution)
    def finalize(self, state: QueryState) -> QueryState:
        logger.info("[supervisor] finalizing response")
        import time
        t0 = time.perf_counter()
        state.result = {
            "summary": "Planning complete (execution not implemented)",
            "tables": state.tables,
            "plan": state.plan,
        }
        dt_ms = (time.perf_counter() - t0) * 1000.0
        state.timings["finalize_ms"] = round(dt_ms, 2)
        total = sum(state.timings.values())
        state.timings["total_ms"] = round(total, 2)
        logger.info("[supervisor] done")
        return state
