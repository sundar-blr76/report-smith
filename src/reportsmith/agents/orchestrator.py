from __future__ import annotations

from typing import Any, Callable

from langgraph.graph import StateGraph, END
from reportsmith.logger import get_logger
from reportsmith.utils.llm_tracker import LLMTracker

logger = get_logger(__name__)

from reportsmith.query_processing import HybridIntentAnalyzer
from reportsmith.schema_intelligence.graph_builder import KnowledgeGraphBuilder
from reportsmith.schema_intelligence.knowledge_graph import SchemaKnowledgeGraph

from .nodes import AgentNodes, QueryState


class MultiAgentOrchestrator:
    """LangGraph-based orchestrator for multi-agent query processing."""

    def __init__(
        self,
        *,
        intent_analyzer: HybridIntentAnalyzer,
        graph_builder: KnowledgeGraphBuilder,
        knowledge_graph: SchemaKnowledgeGraph,
    ) -> None:
        self.nodes = AgentNodes(
            intent_analyzer=intent_analyzer,
            graph_builder=graph_builder,
            knowledge_graph=knowledge_graph,
        )
        logger.info("[supervisor] building orchestration graph (intent -> semantic -> filter -> refine -> schema -> plan -> sql -> finalize)")
        self.graph = self._build_graph()

    def _build_graph(self):
        g = StateGraph(QueryState)

        # Define nodes
        g.add_node("intent", self.nodes.analyze_intent)
        g.add_node("semantic", self.nodes.semantic_enrich)
        g.add_node("semantic_filter", self.nodes.semantic_filter)
        g.add_node("refine", self.nodes.refine_entities)
        g.add_node("schema", self.nodes.map_schema)
        g.add_node("plan", self.nodes.plan_query)
        g.add_node("sql", self.nodes.generate_sql)
        g.add_node("finalize", self.nodes.finalize)

        # Edges
        g.add_edge("intent", "semantic")
        g.add_edge("semantic", "semantic_filter")
        g.add_edge("semantic_filter", "refine")
        g.add_edge("refine", "schema")
        g.add_edge("schema", "plan")
        g.add_edge("plan", "sql")
        g.add_edge("sql", "finalize")
        g.add_edge("finalize", END)

        # Entry
        g.set_entry_point("intent")
        return g.compile()

    def run(self, question: str, app_id: str | None = None) -> QueryState:
        logger.info("[supervisor] received payload; starting orchestration")
        
        # Initialize LLM tracker for this request
        llm_tracker = LLMTracker()
        
        # Set tracker in nodes so SQL validator can use it
        self.nodes._llm_tracker = llm_tracker
        
        state = QueryState(question=question, app_id=app_id)
        result = self.graph.invoke(state)
        
        # Handle both dict and QueryState returns from LangGraph
        if isinstance(result, dict):
            # Convert dict to QueryState
            final = QueryState(**result)
        else:
            final = result
        
        # Get LLM usage summary and add to state
        llm_summary = llm_tracker.get_summary()
        final.llm_usage = llm_summary
        
        # Log summary
        logger.info(
            f"💰 [llm-tracker:summary] Total: {llm_summary['total_calls']} calls, "
            f"{llm_summary['total_tokens']:,} tokens, "
            f"${llm_summary['total_cost_usd']:.6f}, "
            f"{llm_summary['total_latency_ms']:.1f}ms"
        )
        
        # Log by stage
        for stage, data in llm_summary.get('by_stage', {}).items():
            logger.info(
                f"💰 [llm-tracker:stage:{stage}] {data['calls']} calls, "
                f"{data['tokens']:,} tokens, ${data['cost_usd']:.6f}"
            )
        
        logger.info("[supervisor] orchestration complete")
        return final

    def run_stream(self, question: str, on_event: Callable[[str, dict], None]) -> QueryState:
        """Run graph and stream node events via callback. on_event(event, payload)."""
        logger.info("[supervisor] received payload; starting orchestration (stream)")
        state = QueryState(question=question)
        
        # Initialize LLM tracker for this request (for stream too)
        llm_tracker = LLMTracker()
        self.nodes._llm_tracker = llm_tracker
        
        # Map node functions to event names to stream progress
        steps = [
            ("intent", self.nodes.analyze_intent),
            ("semantic", self.nodes.semantic_enrich),
            ("semantic_filter", self.nodes.semantic_filter),
            ("refine", self.nodes.refine_entities),
            ("schema", self.nodes.map_schema),
            ("plan", self.nodes.plan_query),
            ("sql", self.nodes.generate_sql),
            ("finalize", self.nodes.finalize),
        ]
        
        import time
        
        for name, fn in steps:
            try:
                start_ts = time.time()
                on_event("node_start", {"name": name})
                
                state = fn(state)
                
                duration_ms = (time.time() - start_ts) * 1000
                state.timings[name] = duration_ms
                
                # Snapshot state for UI
                # We use model_dump(mode='json') for Pydantic v2 to ensure serializable output
                try:
                    snapshot = state.model_dump(mode='json') if hasattr(state, "model_dump") else state.dict()
                except Exception as e:
                    logger.warning(f"[supervisor] failed to serialize state at {name}: {e}")
                    snapshot = {"error": f"Serialization check failed: {str(e)}", "partial_state": str(state)}
                
                on_event("node_end", {
                    "name": name, 
                    "duration_ms": duration_ms,
                    "state": snapshot
                })
            except Exception as e:
                import traceback
                logger.error(f"[supervisor] stream error at {name}: {traceback.format_exc()}")
                on_event("error", {"name": name, "error": str(e)})
                raise
                
        # Final LLM summary
        llm_summary = llm_tracker.get_summary()
        state.llm_usage = llm_summary
        
        try:
            final_snapshot = state.model_dump(mode='json') if hasattr(state, "model_dump") else state.dict()
        except Exception as e:
            final_snapshot = {"error": f"Final serialization failed: {e}"}
            
        on_event("complete", {
            "name": "orchestration", 
            "result": final_snapshot
        })
        return state

