"""
Query Orchestrator Module

Provides LangChain-based orchestration for query analysis and SQL generation.
"""

# Import models directly (no heavy dependencies)
from .models import (
    QueryAnalysisResult,
    EntityInfo,
    RelationshipInfo,
    FilterInfo,
    ContextInfo,
    QueryPlan,
    ConfidenceScore,
    ConfidenceLevel,
    EntityType,
    FilterType,
    AggregationType,
    NavigationPath,
)

# Lazy imports for heavy dependencies
def _get_orchestrator():
    from .orchestrator import QueryOrchestrator
    return QueryOrchestrator

def _get_tools():
    from .mcp_tools import (
        EntityIdentificationTool,
        RelationshipDiscoveryTool,
        ContextExtractionTool,
        FilterIdentificationTool,
        GraphNavigationTool,
    )
    return (
        EntityIdentificationTool,
        RelationshipDiscoveryTool,
        ContextExtractionTool,
        FilterIdentificationTool,
        GraphNavigationTool,
    )

# Make classes available via attribute access
def __getattr__(name):
    if name == "QueryOrchestrator":
        return _get_orchestrator()
    elif name in ["EntityIdentificationTool", "RelationshipDiscoveryTool", 
                  "ContextExtractionTool", "FilterIdentificationTool", 
                  "GraphNavigationTool"]:
        tools = _get_tools()
        tool_map = {
            "EntityIdentificationTool": tools[0],
            "RelationshipDiscoveryTool": tools[1],
            "ContextExtractionTool": tools[2],
            "FilterIdentificationTool": tools[3],
            "GraphNavigationTool": tools[4],
        }
        return tool_map[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "QueryOrchestrator",
    "EntityIdentificationTool",
    "RelationshipDiscoveryTool",
    "ContextExtractionTool",
    "FilterIdentificationTool",
    "GraphNavigationTool",
    "QueryAnalysisResult",
    "EntityInfo",
    "RelationshipInfo",
    "FilterInfo",
    "ContextInfo",
    "QueryPlan",
    "ConfidenceScore",
    "ConfidenceLevel",
    "EntityType",
    "FilterType",
    "AggregationType",
    "NavigationPath",
]
