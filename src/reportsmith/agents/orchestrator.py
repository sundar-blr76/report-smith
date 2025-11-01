from __future__ import annotations

from typing import Any

from langgraph.graph import StateGraph, END
from reportsmith.logger import get_logger

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
        logger.info("[supervisor] building orchestration graph (intent -> schema -> plan -> finalize)")
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
        g.add_node("finalize", self.nodes.finalize)

        # Edges
        g.add_edge("intent", "semantic")
        g.add_edge("semantic", "semantic_filter")
        g.add_edge("semantic_filter", "refine")
        g.add_edge("refine", "schema")
        g.add_edge("schema", "plan")
        g.add_edge("plan", "finalize")
        g.add_edge("finalize", END)

        # Entry
        g.set_entry_point("intent")
        return g.compile()

    def run(self, question: str, app_id: str | None = None) -> QueryState:
        logger.info("[supervisor] received payload; starting orchestration")
        state = QueryState(question=question, app_id=app_id)
        final: QueryState = self.graph.invoke(state)  # type: ignore
        logger.info("[supervisor] orchestration complete")
        return final

    def run_stream(self, question: str, on_event: Callable[[str, dict], None]) -> QueryState:
        """Run graph and stream node events via callback. on_event(event, payload)."""
        logger.info("[supervisor] received payload; starting orchestration (stream)")
        state = QueryState(question=question)
        # Map node functions to event names to stream progress
        steps = [
            ("intent", self.nodes.analyze_intent),
            ("semantic", self.nodes.semantic_enrich),
            ("semantic_filter", self.nodes.semantic_filter),
            ("refine", self.nodes.refine_entities),
            ("schema", self.nodes.map_schema),
            ("plan", self.nodes.plan_query),
            ("finalize", self.nodes.finalize),
        ]
        for name, fn in steps:
            try:
                on_event("node_start", {"name": name})
                state = fn(state)
                on_event("node_end", {"name": name})
            except Exception as e:
                on_event("error", {"name": name, "error": str(e)})
                raise
        on_event("complete", {"name": "orchestration"})
        return state
