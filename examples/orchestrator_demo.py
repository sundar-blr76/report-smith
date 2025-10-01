"""
Example usage of Query Orchestrator.

This demonstrates how to use the LangChain-based orchestrator for query analysis.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def demo_orchestrator_workflow():
    """Demonstrate the complete orchestration workflow."""
    print("="*80)
    print("Query Orchestrator Demo")
    print("="*80)
    print()
    
    # Note: This demo shows the structure without actual embedding manager
    # In production, you would initialize with:
    # from reportsmith.schema_intelligence.embedding_manager import EmbeddingManager
    # embedding_manager = EmbeddingManager()
    # orchestrator = QueryOrchestrator(embedding_manager, app_config)
    
    print("Step 1: Initialize Orchestrator")
    print("-" * 40)
    print("from reportsmith.query_orchestrator import QueryOrchestrator")
    print("orchestrator = QueryOrchestrator(embedding_manager, app_config)")
    print()
    
    print("Step 2: Analyze User Query")
    print("-" * 40)
    user_query = "Show me top 5 equity funds by AUM with their managers"
    print(f"User Query: {user_query}")
    print()
    print("analysis = orchestrator.analyze_query(user_query)")
    print()
    print("This performs:")
    print("  - Entity identification (tables, columns, dimension values)")
    print("  - Relationship discovery (joins between tables)")
    print("  - Context extraction (metrics, aggregations, temporal context)")
    print("  - Filter identification (WHERE clauses)")
    print("  - Graph navigation (finding paths through relationships)")
    print()
    
    print("Step 3: Generate Query Plan")
    print("-" * 40)
    print("plan = orchestrator.generate_query_plan(analysis)")
    print()
    print("This generates:")
    print("  - Primary table identification")
    print("  - Column selection")
    print("  - JOIN clauses")
    print("  - WHERE clauses")
    print("  - ORDER BY clauses")
    print("  - LIMIT clauses")
    print("  - Complete SQL query")
    print()
    
    print("Step 4: Validate and Refine")
    print("-" * 40)
    print("refined_plan = orchestrator.validate_and_refine(plan)")
    print()
    print("This performs:")
    print("  - Cross-checking against user query")
    print("  - Confidence assessment")
    print("  - Iterative refinement if needed")
    print()
    
    print("Step 5: Execute Query")
    print("-" * 40)
    print("if refined_plan.confidence.level == ConfidenceLevel.HIGH:")
    print("    results = execute_sql(refined_plan.sql_query)")
    print()


def demo_model_usage():
    """Demonstrate model usage."""
    from reportsmith.query_orchestrator.models import (
        EntityInfo,
        EntityType,
        RelationshipInfo,
        FilterInfo,
        FilterType,
        ConfidenceScore,
        ConfidenceLevel,
        ContextInfo,
        AggregationType,
    )
    
    print("="*80)
    print("Model Usage Examples")
    print("="*80)
    print()
    
    print("1. Creating an Entity")
    print("-" * 40)
    entity = EntityInfo(
        name="funds.fund_name",
        entity_type=EntityType.COLUMN,
        table_name="funds",
        column_name="fund_name",
        description="Name of the fund",
        relevance_score=0.92
    )
    print(f"Entity: {entity.name}")
    print(f"Type: {entity.entity_type}")
    print(f"Relevance: {entity.relevance_score}")
    print()
    
    print("2. Creating a Relationship")
    print("-" * 40)
    relationship = RelationshipInfo(
        name="funds_to_holdings",
        parent_table="funds",
        parent_column="id",
        child_table="holdings",
        child_column="fund_id",
        relationship_type="one_to_many"
    )
    print(f"Relationship: {relationship.name}")
    print(f"Join: {relationship.parent_table}.{relationship.parent_column} -> "
          f"{relationship.child_table}.{relationship.child_column}")
    print()
    
    print("3. Creating a Filter")
    print("-" * 40)
    filter_info = FilterInfo(
        filter_type=FilterType.EQUALITY,
        column="fund_type",
        table="funds",
        value="Equity",
        operator="=",
        confidence=ConfidenceScore(
            level=ConfidenceLevel.HIGH,
            score=0.95,
            reasoning="Exact dimension value match"
        )
    )
    print(f"Filter: {filter_info.table}.{filter_info.column} {filter_info.operator} {filter_info.value}")
    print(f"Confidence: {filter_info.confidence.level} ({filter_info.confidence.score:.2f})")
    print()
    
    print("4. Creating Context")
    print("-" * 40)
    context = ContextInfo(
        metric_name="Total AUM",
        temporal_context="last quarter",
        aggregations=[AggregationType.SUM],
        grouping_columns=["fund_type"]
    )
    print(f"Metric: {context.metric_name}")
    print(f"Temporal: {context.temporal_context}")
    print(f"Aggregations: {[a.value for a in context.aggregations]}")
    print(f"Group By: {context.grouping_columns}")
    print()


def demo_mcp_tools():
    """Demonstrate MCP tool concepts."""
    print("="*80)
    print("MCP Tool Concepts")
    print("="*80)
    print()
    
    print("The orchestrator uses the following MCP tools:")
    print()
    
    tools = [
        ("EntityIdentificationTool", 
         "Identifies entities (tables, columns, dimension values) from natural language",
         ["Uses semantic search on schema metadata", 
          "Searches dimension value embeddings",
          "Returns relevance-scored entities"]),
        
        ("RelationshipDiscoveryTool",
         "Discovers relationships between identified tables",
         ["Loads relationships from app.yaml",
          "Filters to relevant relationships",
          "Returns relationship definitions with join info"]),
        
        ("ContextExtractionTool",
         "Extracts business context and identifies metrics",
         ["Searches business context embeddings",
          "Identifies aggregation keywords",
          "Extracts temporal context",
          "Identifies grouping requirements"]),
        
        ("FilterIdentificationTool",
         "Identifies filter conditions from natural language",
         ["Matches dimension values to filters",
          "Identifies temporal filters",
          "Extracts range/equality conditions",
          "Returns confidence-scored filters"]),
        
        ("GraphNavigationTool",
         "Navigates the entity relationship graph",
         ["Builds relationship graph",
          "Finds shortest paths between tables",
          "Generates JOIN clauses",
          "Handles multiple path options"]),
    ]
    
    for tool_name, description, features in tools:
        print(f"{tool_name}")
        print("-" * 40)
        print(f"Purpose: {description}")
        print("Features:")
        for feature in features:
            print(f"  • {feature}")
        print()


if __name__ == "__main__":
    demo_orchestrator_workflow()
    print()
    demo_model_usage()
    print()
    demo_mcp_tools()
    print()
    print("="*80)
    print("Demo completed successfully!")
    print("="*80)
