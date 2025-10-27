from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
import json

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
        try:
            logger.debug("[state@intent:start] " + json.dumps(state.model_dump(), default=str) )
        except Exception:
            logger.debug("[state@intent:start] (unserializable)")
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
            # Prefer full events list (may include refine steps). If absent, fallback to last_metrics
            events = getattr(self.intent_analyzer, "metrics_events", None)
            if isinstance(events, list) and events:
                state.llm_summaries.extend(events)
                logger.info(f"[intent][llm] captured {len(events)} LLM event(s)")
            else:
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
        try:
            logger.debug("[state@schema:start] " + json.dumps(state.model_dump(), default=str))
        except Exception:
            logger.debug("[state@schema:start] (unserializable)")
        logger.info("[supervisor] delegating to schema mapper")
        import time
        t0 = time.perf_counter()
        try:
            tables: List[str] = []
            unmapped: List[Dict[str, Any]] = []
            for ent in state.entities:
                mapped_table = None
                reason = None
                if ent.get("entity_type") == "table":
                    mapped_table = ent.get("text")
                    reason = "entity_type=table"
                else:
                    match = ent.get("top_match") or {}
                    md = match.get("metadata") or {}
                    mapped_table = md.get("table")
                    if mapped_table:
                        reason = "top_match.metadata.table"
                if mapped_table:
                    if mapped_table not in tables:
                        tables.append(mapped_table)
                    logger.debug(
                        f"[schema][map] entity='{ent.get('text')}' type={ent.get('entity_type')} -> table='{mapped_table}' via {reason}"
                    )
                else:
                    unmapped.append(ent)
                    logger.debug(
                        f"[schema][map] entity='{ent.get('text')}' type={ent.get('entity_type')} -> unmapped"
                    )
            state.tables = tables
            dt_ms = (time.perf_counter() - t0) * 1000.0
            state.timings["schema_ms"] = round(dt_ms, 2)
            if unmapped:
                logger.warning(
                    f"[schema] {len(unmapped)} entity(ies) not mapped to any table: {[e.get('text') for e in unmapped]}"
                )
            logger.info(f"[schema] mapped entities to {len(tables)} table(s): {tables} in {dt_ms:.1f}ms")
            return state
        except Exception as e:
            logger.error(f"[schema] error: {e}")
            state.errors.append(f"schema_map_error: {e}")
            return state

    # Node: plan (placeholder)
    def plan_query(self, state: QueryState) -> QueryState:
        try:
            logger.debug("[state@plan:start] " + json.dumps(state.model_dump(), default=str))
        except Exception:
            logger.debug("[state@plan:start] (unserializable)")
        logger.info("[supervisor] delegating to planner")
        import time
        t0 = time.perf_counter()
        try:
            tables = state.tables or []
            plan: Dict[str, Any] = {"tables": tables}
            if len(tables) <= 1:
                plan.update({
                    "strategy": "single_table" if tables else "no_tables",
                    "notes": "No joins required.",
                })
            else:
                # Use knowledge graph to stitch shortest paths from the first table to others
                root = tables[0]
                ordered_tables: List[str] = [root]
                path_edges_all: List[Dict[str, Any]] = []
                missing: List[str] = []
                for tb in tables[1:]:
                    path = self.knowledge_graph.find_shortest_path(root, tb)
                    if not path:
                        missing.append(tb)
                        continue
                    # Append intermediate tables from path (nodes names)
                    for node in path.nodes:
                        if node.type == "table" and node.name not in ordered_tables:
                            ordered_tables.append(node.name)
                    # Collect edge summaries
                    for e in path.edges:
                        path_edges_all.append({
                            "from": e.from_node,
                            "to": e.to_node,
                            "type": e.relationship_type.value,
                            "from_column": e.from_column,
                            "to_column": e.to_column,
                        })
                plan.update({
                    "strategy": "kg_shortest_paths",
                    "path_tables": ordered_tables,
                    "path_edges": path_edges_all,
                    "unreachable": missing,
                    "notes": "Join order derived via knowledge graph shortest paths from first table.",
                })
            state.plan = plan
            dt_ms = (time.perf_counter() - t0) * 1000.0
            state.timings["plan_ms"] = round(dt_ms, 2)
            logger.info(
                f"[planner] produced plan for {len(tables)} table(s); strategy={state.plan.get('strategy')} in {dt_ms:.1f}ms"
            )
            if state.plan.get("unreachable"):
                logger.warning(f"[planner] unreachable tables via KG: {state.plan['unreachable']}")
            else:
                logger.debug(f"[planner] KG path tables: {state.plan.get('path_tables')}")
            return state
        except Exception as e:
            logger.error(f"[planner] error: {e}")
            state.errors.append(f"plan_error: {e}")
            return state

    # Node: finalize response (no execution)
    def finalize(self, state: QueryState) -> QueryState:
        try:
            logger.debug("[state@finalize:start] " + json.dumps(state.model_dump(), default=str))
        except Exception:
            logger.debug("[state@finalize:start] (unserializable)")
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
