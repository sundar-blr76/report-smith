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
                    "table": getattr(e, "table", None),
                    "column": getattr(e, "column", None),
                    "source": getattr(e, "source", None),
                    "local_mapping": getattr(e, "local_mapping", None),
                }
                for e in intent.entities
            ]
            logger.info(f"[intent] extracted {len(entities)} entities")
            # Print entities by default for comprehension
            try:
                lines = []
                for ent in entities:
                    md = ((ent.get("top_match") or {}).get("metadata") or {})
                    table_hint = ent.get("table") or md.get("table")
                    col_hint = ent.get("column") or md.get("column")
                    src = ent.get("source")
                    line = f"  - {ent.get('text')} (type={ent.get('entity_type')}, conf={ent.get('confidence')})"
                    if src:
                        line += f", src={src}"
                    if table_hint:
                        line += f", table={table_hint}"
                    if col_hint:
                        line += f", column={col_hint}"
                    lines.append(line)
                if lines:
                    logger.info("[intent] entities:\n" + "\n".join(lines))
            except Exception:
                logger.debug("[intent] entities: (unserializable)")
            state.intent = {
    # Node: refine entities with LLM selection
    def refine_entities(self, state: QueryState) -> QueryState:
        logger.info("[supervisor] delegating to entity refiner")
        try:
            if not state.entities:
                return state
            keep_idx, keep_reason = self.intent_analyzer.refine_entities_with_llm(state.question, state.entities)
            kept_entities = [e for i, e in enumerate(state.entities) if i in set(keep_idx)]
            dropped_entities = [e for i, e in enumerate(state.entities) if i not in set(keep_idx)]
            logger.info(f"[refine] kept {len(kept_entities)}/{len(state.entities)} entities; reason={keep_reason}")
    # Node: semantic enrichment for entities using embeddings search
    def semantic_enrich(self, state: QueryState) -> QueryState:
        logger.info("[supervisor] delegating to semantic enricher")
        try:
            if not state.entities:
                return state
            em = getattr(self.intent_analyzer, "embedding_manager", None)
            if em is None:
                la = getattr(self.intent_analyzer, "llm_analyzer", None)
                em = getattr(la, "embedding_manager", None) if la else None
            if em is None:
                logger.warning("[semantic] embedding manager not available; skipping enrichment")
                return state
            # Thresholds (fallback defaults if not available from LLM analyzer)
            la = getattr(self.intent_analyzer, "llm_analyzer", None)
            schema_thr = getattr(la, "schema_score_threshold", 0.3)
            dim_thr = getattr(la, "dimension_score_threshold", 0.3)
            ctx_thr = getattr(la, "context_score_threshold", 0.4)
            updated = 0
            for ent in state.entities:
                text = ent.get("text") or ""
                search_text = f"{state.question} {text}".strip()
                try:
                    schema_res = em.search_schema(search_text, top_k=100)
                    dim_res = em.search_dimensions(search_text, top_k=100)
                    ctx_res = em.search_business_context(search_text, top_k=100)
                    best = None
                    # pick best above thresholds
                    for r in schema_res:
                        if r.score >= schema_thr and (best is None or r.score > best["score"]):
                            best = {"content": r.content, "metadata": r.metadata, "score": r.score, "type": "schema"}
                    for r in dim_res:
                        if r.score >= dim_thr and (best is None or r.score > best["score"]):
                            best = {"content": r.content, "metadata": r.metadata, "score": r.score, "type": "dimension_value"}
                    for r in ctx_res:
                        if r.score >= ctx_thr and (best is None or r.score > best["score"]):
                            best = {"content": r.content, "metadata": r.metadata, "score": r.score, "type": "business_context"}
                    if best:
                        prev = ent.get("top_match")
                        ent["top_match"] = best
                        # hydrate table/column hints if missing
                        md = best.get("metadata") or {}
                        if not ent.get("table") and md.get("table"):
                            ent["table"] = md.get("table")
                        if not ent.get("column") and md.get("column"):
                            ent["column"] = md.get("column")
                        updated += 1 if (best != prev) else 0
                        # brief log
                        tb = (md.get("table") or "?")
                        col = (md.get("column") or "?")
                        logger.debug(f"[semantic] entity='{text}' top={tb}.{col} score={best['score']:.3f} type={best['type']}")
                except Exception as e:
                    logger.warning(f"[semantic] enrichment failed for '{text}': {e}")
            logger.info(f"[semantic] enriched {len(state.entities)} entities; updated={updated}")
            return state
        except Exception as e:
            logger.warning(f"[semantic] failed: {e}")
            return state

            if dropped_entities:
                logger.info("[refine] dropped entities:\n" + "\n".join([f"  - {e.get('text')} ({e.get('entity_type')})" for e in dropped_entities]))
            state.entities = kept_entities
            return state
        except Exception as e:
            logger.warning(f"[refine] failed: {e}; leaving entities unchanged")
            return state

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
        # Print entities supplied to schema mapper in a readable format
        try:
            if state.entities:
                lines = []
                for ent in state.entities:
                    md = ((ent.get("top_match") or {}).get("metadata") or {})
                    table_hint = ent.get("table") or md.get("table")
                    conf = ent.get("confidence")
                    line = f"  - {ent.get('text')} (type={ent.get('entity_type')}, conf={conf})"
                    if table_hint:
                        line += f", table_hint={table_hint}"
                    col_hint = ent.get("column") or md.get("column")
                    if col_hint:
                        line += f", column_hint={col_hint}"
                    lines.append(line)
                logger.info("[schema] entities:\n" + "\n".join(lines))
        except Exception:
            logger.debug("[schema] entities: (unserializable)")
        import time
        t0 = time.perf_counter()
        try:
            tables: List[str] = []
            unmapped: List[Dict[str, Any]] = []
            for ent in state.entities:
                mapped_table = None
                reason = None
                ent_text = (ent.get("text") or "").strip()
                ent_type = ent.get("entity_type")
                if ent_type == "table" and ent_text:
                    mapped_table = ent_text
                    reason = "entity_type=table"
                else:
                    match = ent.get("top_match") or {}
                    md = match.get("metadata") or {}
                    mapped_table = md.get("table")
                    if mapped_table:
                        reason = "top_match.metadata.table"
                    # If still not mapped and it's a column, try KG column lookup
                    if not mapped_table and ent_type == "column" and ent_text:
                        et_lower = ent_text.lower()
                        # exact column name match
                        candidates = [n for n in self.knowledge_graph.nodes.values() if n.type == "column" and (n.name or "").lower() == et_lower and n.table]
                        # fallback: substring match (e.g., 'fees' -> 'fee_amount')
                        if not candidates:
                            candidates = [n for n in self.knowledge_graph.nodes.values() if n.type == "column" and et_lower in (n.name or "").lower() and n.table]
                        cand_tables = sorted({n.table for n in candidates if n.table})
                        if cand_tables:
                            # Add all candidate tables; planner will resolve join path
                            for tb in cand_tables:
                                if tb not in tables:
                                    tables.append(tb)
                            mapped_table = ",".join(cand_tables)
                            reason = "kg.column_lookup"
                    # If still not mapped and it's a dimension value, attach using hints or KG
                    if not mapped_table and ent_type == "dimension_value" and ent_text:
                        # Prefer explicit table hint from entity (if present)
                        ent_table_hint = ent.get("table")
                        if ent_table_hint:
                            mapped_table = ent_table_hint
                            reason = "entity.table_hint"
                        elif len(tables) == 1:
                            # If a single mapped table exists and it has dimension columns, assume this value applies there
                            tb = tables[0]
                            has_dim_cols = any(
                                (n.type == "column" and n.table == tb and bool(n.metadata.get("is_dimension")))
                                for n in self.knowledge_graph.nodes.values()
                            )
                            if has_dim_cols:
                                mapped_table = tb
                                reason = "assumed_dimension_on_single_table"
                        # As a final fallback, try KG dimension column lookup by name/substring
                        if not mapped_table:
                            et_lower = ent_text.lower()
                            dim_cols = [
                                n for n in self.knowledge_graph.nodes.values()
                                if n.type == "column" and bool(n.metadata.get("is_dimension"))
                                and n.table and ((n.name or "").lower() == et_lower or et_lower in (n.name or "").lower())
                            ]
                            dim_tables = sorted({n.table for n in dim_cols})
                            if len(dim_tables) == 1:
                                mapped_table = dim_tables[0]
                                reason = "kg.dimension_column_lookup"
                            elif len(dim_tables) > 1:
                                # Add all candidates conservatively
                                mapped_table = ",".join(dim_tables)
                                reason = "kg.dimension_column_multi"
                        # Semantic dimension search to catch domain table or attr table links
                        if not mapped_table:
                            try:
                                dim_results = self.intent_analyzer.embedding_manager.search_dimensions(ent_text, top_k=3)
                                cand_tables = []
                                for r in dim_results:
                                    md = getattr(r, 'metadata', {}) or {}
                                    tb = md.get('table')
                                    if not tb:
                                        content = getattr(r, 'content', '') or ''
                                        if 'Column:' in content:
                                            piece = content.split('Column:')[1].split('|')[0].strip()
                                            if '.' in piece:
                                                tb = piece.split('.')[0].strip()
                                        elif 'Table:' in content:
                                            piece = content.split('Table:')[1].split('|')[0].strip()
                                            tb = piece
                                    if tb:
                                        cand_tables.append(tb)
                                cand_tables = sorted(set([t for t in cand_tables if t]))
                                if cand_tables:
                                    mapped_table = ",".join(cand_tables)
                                    reason = "semantic.dimension_search"
                            except Exception:
                                pass
                if mapped_table:
                    # mapped_table may be comma-joined list; ensure we log cleanly and add individually
                    for tb in str(mapped_table).split(","):
                        tb = tb.strip()
                        if tb and tb not in tables:
                            tables.append(tb)
                    logger.debug(
                        f"[schema][map] entity='{ent_text}' type={ent_type} -> table='{mapped_table}' via {reason}"
                    )
                else:
                    unmapped.append(ent)
                    logger.debug(
                        f"[schema][map] entity='{ent_text}' type={ent_type} -> unmapped"
                    )
            state.tables = tables
            dt_ms = (time.perf_counter() - t0) * 1000.0
            state.timings["schema_ms"] = round(dt_ms, 2)
            if unmapped:
                for e in unmapped:
                    logger.warning(
                        f"[schema][UNMAPPED] >>> {e.get('text')} (type={e.get('entity_type')}, conf={e.get('confidence')})"
                    )
                logger.warning(
                    f"[schema][UNMAPPED] {len(unmapped)} entity(ies) not mapped to any table: {[e.get('text') for e in unmapped]}"
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
