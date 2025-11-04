from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Callable
from pydantic import BaseModel, Field
import json

from reportsmith.query_processing import HybridIntentAnalyzer
from reportsmith.query_processing.sql_generator import SQLGenerator
from reportsmith.query_processing.query_validator import QueryValidator
from reportsmith.query_processing.schema_validator import SchemaValidator
from reportsmith.schema_intelligence.knowledge_graph import SchemaKnowledgeGraph
from reportsmith.schema_intelligence.graph_builder import KnowledgeGraphBuilder
from reportsmith.query_execution import SQLExecutor
from reportsmith.logger import get_logger

logger = get_logger(__name__)


class QueryState(BaseModel):
    question: str
    app_id: Optional[str] = None
    intent: Dict[str, Any] | None = None
    entities: List[Dict[str, Any]] = Field(default_factory=list)
    tables: List[str] = Field(default_factory=list)
    plan: Dict[str, Any] | None = None
    sql: Dict[str, Any] | None = None
    validation: Dict[str, Any] | None = None  # Query validation results
    schema_validation: Dict[str, Any] | None = None  # Schema validation results
    result: Dict[str, Any] | None = None
    errors: List[str] = Field(default_factory=list)
    timings: Dict[str, float] = Field(default_factory=dict)
    llm_summaries: List[Dict[str, Any]] = Field(default_factory=list)
    debug_files: Dict[str, Any] = Field(default_factory=dict)


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
        
        # Pass LLM client to SQL generator for column enrichment
        llm_client = None
        llm_provider = "gemini"  # default
        if hasattr(intent_analyzer, 'llm_analyzer') and intent_analyzer.llm_analyzer:
            llm_client = getattr(intent_analyzer.llm_analyzer, 'client', None)
            llm_provider = getattr(intent_analyzer.llm_analyzer, 'provider', 'gemini')
        
        self.sql_generator = SQLGenerator(
            knowledge_graph=knowledge_graph,
            llm_client=llm_client
        )
        
        # Initialize validators
        self.query_validator = QueryValidator(
            llm_client=llm_client,
            provider=llm_provider
        )
        
        self.schema_validator = SchemaValidator(
            knowledge_graph=knowledge_graph
        )
        
        # SQL executor for query execution
        self.sql_executor = SQLExecutor()
        
        # output directory for debug payloads
        self.debug_dir = "/home/sundar/sundar_projects/report-smith/logs/semantic_debug"
    
    def _write_debug(self, filename: str, data: Any) -> None:
        """Write debug data to file"""
        try:
            import os, json, tempfile
            os.makedirs(self.debug_dir, exist_ok=True)
            path = os.path.join(self.debug_dir, filename)
            # Serialize first with default=str to avoid partial writes on non-serializable objects
            payload = json.dumps(data, indent=2, ensure_ascii=False, default=str)
            tmp_path = path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(payload)
            os.replace(tmp_path, path)
        except Exception as e:
            logger.warning(f"[debug] failed to write {filename}: {e}")


    # helper to dump state compactly for start logs
    def _dump_state(self, state: QueryState) -> str:
        try:
            return json.dumps(state.model_dump(), default=str)
        except Exception:
            return "(unserializable)"

    # Node: analyze intent
    def analyze_intent(self, state: QueryState) -> QueryState:
        # Color-coded node start for visibility
        logger.info("\x1b[1;36m=== NODE START: INTENT ===\x1b[0m")
        logger.debug("[state@intent:start] " + self._dump_state(state))
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
                    # For table entities, use canonical_name as table name if table is not set
                    "table": (
                        getattr(e, "table", None) or 
                        (e.canonical_name if e.entity_type == "table" else None)
                    ),
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

    # Node: refine entities with LLM selection
    def refine_entities(self, state: QueryState) -> QueryState:
        logger.info("\x1b[1;34m=== NODE START: REFINE ENTITIES ===\x1b[0m")
        logger.debug("[state@refine:start] " + self._dump_state(state))
        try:
            if not state.entities:
                return state
            keep_idx, keep_reason = self.intent_analyzer.refine_entities_with_llm(state.question, state.entities)
            kept_entities = [e for i, e in enumerate(state.entities) if i in set(keep_idx)]
            dropped_entities = [e for i, e in enumerate(state.entities) if i not in set(keep_idx)]
            logger.info(f"[refine] kept {len(kept_entities)}/{len(state.entities)} entities; reason={keep_reason}")
            if dropped_entities:
                logger.info("[refine] dropped entities:\n" + "\n".join([f"  - {e.get('text')} ({e.get('entity_type')})" for e in dropped_entities]))
            state.entities = kept_entities
            return state
        except Exception as e:
            logger.warning(f"[refine] failed: {e}; leaving entities unchanged")
            return state

    # Node: semantic enrichment for entities using embeddings search
    def semantic_enrich(self, state: QueryState) -> QueryState:
        logger.info("\x1b[1;35m=== NODE START: SEMANTIC ENRICH ===\x1b[0m")
        logger.debug("[state@semantic:start] " + self._dump_state(state))
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
            # Lower thresholds since we're now using minimal embeddings (more precise)
            schema_thr = getattr(la, "schema_score_threshold", 0.5)
            dim_thr = getattr(la, "dimension_score_threshold", 0.5)
            ctx_thr = getattr(la, "context_score_threshold", 0.5)

            updated = 0
            for ent in state.entities:
                text = ent.get("text") or ""
                # NEW: Search with entity text ONLY (not full question)
                # This matches our minimal embedding strategy
                search_text = text.strip()
                try:
                    # Write semantic search input payload
                    self._write_debug("semantic_input.json", {
                        "question": state.question,
                        "entity": ent,
                        "search_text": search_text,
                        "strategy": "minimal_name_only",
                        "thresholds": {"schema": schema_thr, "dimension": dim_thr, "context": ctx_thr}
                    })

                    # Pull top 100 per collection (reduced from 1000 since we expect higher precision)
                    schema_res = em.search_schema(search_text, app_id=state.app_id, top_k=100)
                    dim_res = em.search_dimensions(search_text, app_id=state.app_id, top_k=100)
                    ctx_res = em.search_business_context(search_text, app_id=state.app_id, top_k=100)

                    # If app_id filter yields nothing, retry without filter
                    if not (schema_res or dim_res or ctx_res) and state.app_id:
                        logger.info("[semantic] no matches with app filter; retrying without app_id")
                        schema_res = em.search_schema(search_text, app_id=None, top_k=100)
                        dim_res = em.search_dimensions(search_text, app_id=None, top_k=100)
                        ctx_res = em.search_business_context(search_text, app_id=None, top_k=100)

                    all_matches = []

                    for r in schema_res:
                        if r.score >= schema_thr:
                            all_matches.append({"content": r.content, "metadata": r.metadata, "score": r.score, "source_type": "schema"})
                    for r in dim_res:
                        if r.score >= dim_thr:
                            all_matches.append({"content": r.content, "metadata": r.metadata, "score": r.score, "source_type": "dimension_value"})
                    for r in ctx_res:
                        if r.score >= ctx_thr:
                            all_matches.append({"content": r.content, "metadata": r.metadata, "score": r.score, "source_type": "business_context"})

                    # Deduplicate and boost confidence for entities with multiple synonym matches
                    # Group by entity (table.column or table or metric)
                    entity_groups: Dict[str, List[Dict[str, Any]]] = {}
                    for m in all_matches:
                        md = m.get("metadata") or {}
                        # Create unique key for this entity
                        entity_key = None
                        if md.get("entity_type") == "table":
                            entity_key = f"table:{md.get('table')}"
                        elif md.get("entity_type") == "column":
                            entity_key = f"column:{md.get('table')}.{md.get('column')}"
                        elif md.get("entity_type") == "dimension_value":
                            entity_key = f"dim:{md.get('table')}.{md.get('column')}={md.get('value')}"
                        elif md.get("entity_type") == "metric":
                            entity_key = f"metric:{md.get('metric_name')}"
                        else:
                            entity_key = f"other:{md.get('entity_name', 'unknown')}"
                        
                        if entity_key not in entity_groups:
                            entity_groups[entity_key] = []
                        entity_groups[entity_key].append(m)
                    
                    # For each entity group, compute best score and count synonym hits
                    deduplicated_matches = []
                    for entity_key, group in entity_groups.items():
                        # Best score in group
                        best_score = max(m["score"] for m in group)
                        # Count primary vs synonym matches
                        primary_count = sum(1 for m in group if m.get("metadata", {}).get("match_type") == "primary")
                        synonym_count = sum(1 for m in group if m.get("metadata", {}).get("match_type") == "synonym")
                        
                        # Boost score if we have multiple hits (synonym convergence)
                        boosted_score = best_score
                        if len(group) > 1:
                            # Modest boost: +0.05 per additional match, max +0.15
                            boost = min(0.05 * (len(group) - 1), 0.15)
                            boosted_score = min(1.0, best_score + boost)
                        
                        # Use the match with best score as representative
                        best_match = max(group, key=lambda m: m["score"])
                        best_match["score"] = boosted_score
                        best_match["match_count"] = len(group)
                        best_match["primary_count"] = primary_count
                        best_match["synonym_count"] = synonym_count
                        deduplicated_matches.append(best_match)

                    # Always write output payload for review (overwrite with full details)
                    try:
                        output_data = {
                            "entity": ent.get("text"),
                            "entity_type": ent.get("entity_type"),
                            "search_text": search_text,
                            "counts": {
                                "schema_raw": len(schema_res),
                                "dimensions_raw": len(dim_res),
                                "context_raw": len(ctx_res),
                                "above_threshold": len(all_matches),
                                "deduplicated": len(deduplicated_matches)
                            },
                            "thresholds": {
                                "schema": schema_thr,
                                "dimension": dim_thr,
                                "context": ctx_thr
                            },
                            "top_5_matches": sorted(deduplicated_matches, key=lambda x: x["score"], reverse=True)[:5],
                            "score_distribution": {
                                "max": max((m["score"] for m in deduplicated_matches), default=0),
                                "min": min((m["score"] for m in deduplicated_matches), default=0),
                                "avg": sum(m["score"] for m in deduplicated_matches) / len(deduplicated_matches) if deduplicated_matches else 0
                            }
                        }
                        self._write_debug("semantic_output.json", output_data)
                    except Exception as e:
                        logger.debug(f"[semantic] failed to write debug output: {e}")

                    if not deduplicated_matches:
                        logger.info(f"[semantic] no matches for entity='{text}' (searched with threshold: schema={schema_thr}, dim={dim_thr}, ctx={ctx_thr})")
                    else:
                        # sort high to low
                        deduplicated_matches.sort(key=lambda x: x["score"], reverse=True)
                        prev = ent.get("semantic_matches")
                        ent["semantic_matches"] = deduplicated_matches
                        best = deduplicated_matches[0]
                        ent["top_match"] = best
                        md = best.get("metadata") or {}
                        if not ent.get("table") and md.get("table"):
                            ent["table"] = md.get("table")
                        if not ent.get("column") and md.get("column"):
                            ent["column"] = md.get("column")
                        updated += 1 if (prev != deduplicated_matches) else 0
                        tb = (md.get("table") or "?")
                        col = (md.get("column") or "?")
                        src_type = best.get('source_type', '?')
                        match_count = best.get('match_count', 1)
                        embedded_txt = md.get("embedded_text", "?")
                        logger.info(
                            f"[semantic] entity='{text}' → matched='{embedded_txt}' "
                            f"table={tb} col={col} score={best['score']:.3f} "
                            f"source={src_type} hits={match_count} total_candidates={len(deduplicated_matches)}"
                        )
                except Exception as e:
                    logger.warning(f"[semantic] enrichment failed for '{text}': {e}")
            # Stats after semantic enrichment
            try:
                tables_set = set()
                cols_per_table: Dict[str, set] = {}
                rel_edges: List[Dict[str, Any]] = []
                ctx_matches = 0
                for ent in state.entities:
                    # table/column from entity or top_match metadata
                    md = ((ent.get("top_match") or {}).get("metadata") or {})
                    tb = ent.get("table") or md.get("table")
                    col = ent.get("column") or md.get("column")
                    if tb:
                        tables_set.add(tb)
                        if col:
                            cols_per_table.setdefault(tb, set()).add(col)
                    # count business context matches
                    for m in (ent.get("semantic_matches") or []):
                        if (m.get("source_type") == "business_context"):
                            ctx_matches += 1
                # relationships between discovered tables via KG shortest paths
                tables_list = sorted(list(tables_set))
                if len(tables_list) > 1:
                    root = tables_list[0]
                    for tb in tables_list[1:]:
                        path = self.knowledge_graph.find_shortest_path(root, tb)
                        if path:
                            for e in path.edges:
                                rel_edges.append({
                                    "from": e.from_node,
                                    "to": e.to_node,
                                    "type": e.relationship_type.value,
                                    "from_column": e.from_column,
                                    "to_column": e.to_column,
                                })
                # Log compact summary
                cols_count = {k: len(v) for k, v in cols_per_table.items()}
                logger.info(
                    "[semantic][stats] tables=%s columns_per_table=%s relationships=%d business_context_matches=%d",
                    tables_list, cols_count, len(rel_edges), ctx_matches,
                )
            except Exception as e:
                logger.debug(f"[semantic][stats] failed: {e}")
            logger.info(f"[semantic] enriched {len(state.entities)} entities; updated={updated}")
            return state
        except Exception as e:
            logger.warning(f"[semantic] failed: {e}")
            return state
            # add per-entity match counts for downstream consumers/UI
            try:
                for ent in state.entities:
                    ent["semantic_match_count"] = len(ent.get("semantic_matches") or [])
            except Exception:
                pass


    # Node: LLM filter semantic candidates per-entity with full context
    def semantic_filter(self, state: QueryState) -> QueryState:
        logger.info("\x1b[1;33m=== NODE START: SEMANTIC FILTER (LLM) ===\x1b[0m")
        logger.debug("[state@semantic_filter:start] " + self._dump_state(state))
        try:
            if not state.entities:
                return state
            la = getattr(self.intent_analyzer, "llm_analyzer", None)
            if not la:
                logger.warning("[semantic-filter] LLM analyzer not available; skipping")
                return state
            import json, time
            kept = []
            # Tuning knobs for semantic filtering
            max_candidates = getattr(la, 'semantic_filter_max_candidates', 30)  # reduced to keep prompt manageable
            max_keep = getattr(la, 'semantic_filter_max_keep', 5)
            min_score = getattr(la, 'semantic_filter_min_score', 0.50)
            
            for ent in state.entities:
                matches = ent.get("semantic_matches") or []
                # Pre-trim by score and cap to max_candidates to avoid huge prompts
                if matches:
                    matches = [m for m in matches if (m.get('score') or 0) >= min_score]
                    matches = matches[:max_candidates]

                if not matches:
                    kept.append(ent)
                    continue
                
                # Build enriched prompt with full entity metadata and relationship context
                candidates_detail = []
                for i, m in enumerate(matches):
                    md = m.get("metadata") or {}
                    detail = {
                        "index": i,
                        "embedded_text": m.get("content"),
                        "score": round(m.get("score"), 3),
                        "source_type": m.get("source_type"),
                        "entity_type": md.get("entity_type"),
                    }
                    
                    # Add type-specific details
                    # Deserialize JSON fields from ChromaDB metadata
                    import json as json_module
                    if md.get("entity_type") == "table":
                        detail["table"] = md.get("table")
                        detail["description"] = md.get("description", "")
                        # Deserialize related_tables from JSON string
                        try:
                            related_tables_json = md.get("related_tables_json", "[]")
                            detail["related_tables"] = json_module.loads(related_tables_json) if related_tables_json else []
                        except Exception:
                            detail["related_tables"] = []
                    elif md.get("entity_type") == "column":
                        detail["table"] = md.get("table")
                        detail["column"] = md.get("column")
                        detail["description"] = md.get("description", "")
                        detail["data_type"] = md.get("data_type", "")
                    elif md.get("entity_type") == "dimension_value":
                        detail["table"] = md.get("table")
                        detail["column"] = md.get("column")
                        detail["value"] = md.get("value")
                        detail["context"] = md.get("context", "")
                    elif md.get("entity_type") == "metric":
                        detail["metric_name"] = md.get("metric_name")
                        detail["description"] = md.get("description", "")
                        # Deserialize tables from JSON string
                        try:
                            tables_json = md.get("tables_json", "[]")
                            detail["tables"] = json_module.loads(tables_json) if tables_json else []
                        except Exception:
                            detail["tables"] = []
                    
                    # Add match type info
                    detail["match_type"] = md.get("match_type", "unknown")
                    if md.get("match_type") == "synonym":
                        detail["synonym"] = md.get("synonym")
                    
                    candidates_detail.append(detail)
                
                prompt = (
                    f"User Query: '{state.question}'\n"
                    f"Entity to Match: '{ent.get('text')}' (type: {ent.get('entity_type')})\n\n"
                    f"Task: Filter semantic search candidates to keep ONLY those truly relevant "
                    f"to the entity '{ent.get('text')}' in the context of the user query.\n\n"
                    f"Candidates (with full metadata and relationships):\n"
                    f"{json.dumps(candidates_detail, indent=2)}\n\n"
                    f"Return JSON with:\n"
                    f"{{\n"
                    f'  "relevant_indices": [list of relevant candidate indices],\n'
                    f'  "reasoning": "brief explanation of why you kept/dropped candidates"\n'
                    f"}}\n"
                )
                
                provider = getattr(la, "llm_provider", "gemini")
                t0 = time.perf_counter()
                data = None
                try:
                    if provider == "openai":
                        req = {
                            "model": la.model,
                            "messages": [
                                {"role": "system", "content": "You are an expert at filtering semantic search results for database entities using full schema context and relationships."},
                                {"role": "user", "content": prompt},
                            ],
                            "response_format": {"type": "json_object"},
                            "temperature": 0,
                        }
                        resp = la.client.chat.completions.create(**req)
                        data = json.loads(resp.choices[0].message.content)
                    elif provider == "anthropic":
                        resp = la.client.messages.create(
                            model=la.model,
                            max_tokens=1000,
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0,
                        )
                        content = resp.content[0].text
                        s = content.find('{'); e = content.rfind('}') + 1
                        data = json.loads(content[s:e] if s >= 0 else content)
                    else:
                        gen_cfg = {"temperature": 0, "response_mime_type": "application/json"}
                        resp = la.client.generate_content(prompt, generation_config=gen_cfg)
                        data = json.loads(resp.text)
                except Exception as e:
                    logger.warning(f"[semantic-filter] LLM failed for entity '{ent.get('text')}': {e}; keeping top-1")
                    # Keep only top-1 to be conservative
                    ent["semantic_matches"] = matches[:1]
                    ent["top_match"] = matches[0]
                    kept.append(ent)
                    continue
                finally:
                    dt_ms = (time.perf_counter() - t0) * 1000.0
                    logger.info(f"[llm] completion provider={provider} model={getattr(la,'model',None)} prompt_chars={len(prompt)} latency_ms={round(dt_ms,2)}")
                
                # Post-filter: enforce a maximum kept count after LLM indices are chosen
                idxs = (data or {}).get("relevant_indices", [])
                reason = (data or {}).get("reasoning", "")
                filtered = [matches[i] for i in idxs if i < len(matches)]
                if not filtered:
                    filtered = matches[:1]
                    reason = "No LLM-selected matches; keeping top-1 by score"
                if len(filtered) > max_keep:
                    filtered = filtered[:max_keep]
                # Ensure best candidate at top after trimming
                filtered.sort(key=lambda x: x.get('score', 0), reverse=True)

                logger.info(
                    f"[semantic-filter] entity='{ent.get('text')}': {len(matches)} → {len(filtered)} candidates; "
                    f"reason: {reason[:100]}"
                )
                
                ent["semantic_matches"] = filtered
                ent["top_match"] = filtered[0]
                kept.append(ent)
            
            state.entities = kept
            # update count after filtering
            try:
                for ent in state.entities:
                    ent["semantic_match_count"] = len(ent.get("semantic_matches") or [])
            except Exception:
                pass
            
            logger.info("[semantic-filter] completed per-entity filtering")
            return state
        except Exception as e:
            logger.warning(f"[semantic-filter] failed: {e}")
            return state

    # Node: map to schema tables
    def map_schema(self, state: QueryState) -> QueryState:
        logger.info("\x1b[1;32m=== NODE START: SCHEMA MAP ===\x1b[0m")
        logger.debug("[state@schema:start] " + self._dump_state(state))
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
                    # First try to get actual table name from entity metadata
                    mapped_table = ent.get("table")
                    if mapped_table:
                        reason = "entity.table"
                    else:
                        # Try top_match metadata
                        match = ent.get("top_match") or {}
                        md = match.get("metadata") or {}
                        mapped_table = md.get("table")
                        if mapped_table:
                            reason = "top_match.metadata.table"
                        else:
                            # Try local_mapping canonical_name
                            local_map = ent.get("local_mapping") or {}
                            canonical = local_map.get("canonical_name")
                            if canonical:
                                mapped_table = canonical
                                reason = "local_mapping.canonical_name"
                            else:
                                # Last resort: use entity text as-is (may be wrong!)
                                mapped_table = ent_text
                                reason = "entity_text_fallback"
                                logger.warning(
                                    f"[schema][map] table entity '{ent_text}' has no table/canonical_name mapping, using text as-is"
                                )
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
        logger.info("\x1b[1;31m=== NODE START: PLAN ===\x1b[0m")
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

    # Node: generate SQL
    def generate_sql(self, state: QueryState) -> QueryState:
        logger.info("\x1b[1;36m=== NODE START: SQL GENERATION ===\x1b[0m")
        logger.debug("[state@sql:start] " + self._dump_state(state))
        logger.info("[supervisor] delegating to SQL generator")
        import time
        t0 = time.perf_counter()
        try:
            if not state.plan:
                raise ValueError("No plan available for SQL generation")
            if not state.intent:
                raise ValueError("No intent available for SQL generation")
            
            # Generate SQL using the SQL generator
            sql_result = self.sql_generator.generate(
                question=state.question,
                intent=state.intent,
                entities=state.entities,
                plan=state.plan,
            )
            
            state.sql = sql_result
            dt_ms = (time.perf_counter() - t0) * 1000.0
            state.timings["sql_ms"] = round(dt_ms, 2)
            
            # Log generated SQL
            sql_text = sql_result.get("sql", "")
            logger.info(f"[sql-gen] generated SQL query ({len(sql_text)} chars) in {dt_ms:.1f}ms")
            logger.info(f"[sql-gen] SQL:\n{sql_text}")
            
            # Log explanation
            explanation = sql_result.get("explanation", "")
            if explanation:
                logger.debug(f"[sql-gen] Explanation:\n{explanation}")
            
            # Log metadata
            metadata = sql_result.get("metadata", {})
            logger.info(
                f"[sql-gen] metadata: tables={metadata.get('tables')}, "
                f"joins={metadata.get('join_count')}, filters={metadata.get('where_count')}, "
                f"columns={metadata.get('columns_count')}"
            )
            
            return state
        except Exception as e:
            logger.error(f"[sql-gen] error: {e}", exc_info=True)
            state.errors.append(f"sql_generation_error: {e}")
            return state

    # Node: validate query against user intent using LLM
    def validate_query(self, state: QueryState) -> QueryState:
        logger.info("\x1b[1;35m=== NODE START: QUERY VALIDATION ===\x1b[0m")
        logger.debug("[state@validate:start] " + self._dump_state(state))
        logger.info("[supervisor] validating SQL against user intent")
        import time
        t0 = time.perf_counter()
        try:
            if not state.sql or not state.sql.get("sql"):
                logger.warning("[query-validation] no SQL available, skipping validation")
                state.validation = {
                    "is_valid": True,
                    "issues": [],
                    "reasoning": "Validation skipped - no SQL generated",
                    "confidence": 0.0,
                }
                return state
            
            # Validate query against intent
            validation_result = self.query_validator.validate(
                question=state.question,
                intent=state.intent or {},
                sql=state.sql.get("sql"),
                entities=state.entities,
                plan=state.plan or {},
            )
            
            state.validation = validation_result
            dt_ms = (time.perf_counter() - t0) * 1000.0
            state.timings["validation_ms"] = round(dt_ms, 2)
            
            # If corrected SQL is provided, update state
            if validation_result.get("corrected_sql"):
                logger.info("[query-validation] using corrected SQL from validator")
                state.sql["sql"] = validation_result["corrected_sql"]
                state.sql["corrected_by_validator"] = True
            
            logger.info(
                f"[query-validation] validation complete in {dt_ms:.1f}ms: "
                f"valid={validation_result.get('is_valid')}, "
                f"issues={len(validation_result.get('issues', []))}"
            )
            
            return state
        except Exception as e:
            logger.error(f"[query-validation] error: {e}", exc_info=True)
            state.errors.append(f"query_validation_error: {e}")
            # Don't block on validation errors
            state.validation = {
                "is_valid": True,
                "issues": [str(e)],
                "reasoning": f"Validation failed: {e}",
                "confidence": 0.0,
            }
            return state

    # Node: validate SQL against schema metadata
    def validate_schema(self, state: QueryState) -> QueryState:
        logger.info("\x1b[1;33m=== NODE START: SCHEMA VALIDATION ===\x1b[0m")
        logger.debug("[state@schema-validate:start] " + self._dump_state(state))
        logger.info("[supervisor] validating SQL against schema metadata")
        import time
        t0 = time.perf_counter()
        try:
            if not state.sql or not state.sql.get("sql"):
                logger.warning("[schema-validation] no SQL available, skipping validation")
                state.schema_validation = {
                    "is_valid": True,
                    "errors": [],
                    "warnings": [],
                    "corrections_applied": [],
                }
                return state
            
            # Validate against schema
            schema_result = self.schema_validator.validate(
                sql=state.sql.get("sql"),
                plan=state.plan or {},
                entities=state.entities,
            )
            
            state.schema_validation = schema_result
            dt_ms = (time.perf_counter() - t0) * 1000.0
            state.timings["schema_validation_ms"] = round(dt_ms, 2)
            
            # If corrected SQL is provided, update state
            if schema_result.get("corrected_sql"):
                logger.info("[schema-validation] using corrected SQL from schema validator")
                state.sql["sql"] = schema_result["corrected_sql"]
                state.sql["corrected_by_schema_validator"] = True
            
            # Add errors to state.errors if validation failed
            if not schema_result.get("is_valid"):
                for error in schema_result.get("errors", []):
                    state.errors.append(f"schema_validation: {error}")
            
            logger.info(
                f"[schema-validation] validation complete in {dt_ms:.1f}ms: "
                f"valid={schema_result.get('is_valid')}, "
                f"errors={len(schema_result.get('errors', []))}, "
                f"warnings={len(schema_result.get('warnings', []))}"
            )
            
            return state
        except Exception as e:
            logger.error(f"[schema-validation] error: {e}", exc_info=True)
            state.errors.append(f"schema_validation_error: {e}")
            # Don't block on validation errors
            state.schema_validation = {
                "is_valid": True,
                "errors": [str(e)],
                "warnings": [],
                "corrections_applied": [],
            }
            return state

    # Node: finalize response with SQL execution
    def finalize(self, state: QueryState) -> QueryState:
        logger.info("\x1b[1;37m=== NODE START: FINALIZE ===\x1b[0m")
        logger.debug("[state@finalize:start] " + self._dump_state(state))
        logger.info("[supervisor] finalizing response")
        import time
        t0 = time.perf_counter()
        
        # Execute SQL if available
        execution_result = None
        if state.sql and state.sql.get("sql"):
            sql_text = state.sql.get("sql")
            logger.info("[finalize] executing SQL query")
            
            # Validate SQL first
            validation = self.sql_executor.validate_sql(sql_text)
            if validation.get("valid"):
                logger.info("[finalize] SQL validation passed, executing query")
                execution_result = self.sql_executor.execute_query(sql_text)
                
                if execution_result.get("error"):
                    logger.error(f"[finalize] SQL execution failed: {execution_result.get('error')}")
                else:
                    logger.info(
                        f"[finalize] SQL execution successful: "
                        f"{execution_result.get('row_count')} rows returned"
                    )
            else:
                logger.error(f"[finalize] SQL validation failed: {validation.get('error')}")
                execution_result = {
                    "error": f"SQL validation failed: {validation.get('error')}",
                    "error_type": "validation_error",
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                }
        
        state.result = {
            "summary": "Query processed successfully" if not execution_result or not execution_result.get("error") else "Query processing completed with errors",
            "tables": state.tables,
            "plan": state.plan,
            "sql": state.sql,
            "validation": state.validation,
            "schema_validation": state.schema_validation,
            "execution": execution_result,
        }
        dt_ms = (time.perf_counter() - t0) * 1000.0
        state.timings["finalize_ms"] = round(dt_ms, 2)
        total = sum(state.timings.values())
        state.timings["total_ms"] = round(total, 2)
        logger.info("[supervisor] done")
        return state
