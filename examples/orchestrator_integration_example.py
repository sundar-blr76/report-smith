"""
Integration example showing how the Query Orchestrator integrates with
existing ReportSmith components.

This example demonstrates the full workflow from configuration loading
to SQL query generation.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def demonstrate_integration():
    """Show full integration with existing components."""
    
    print("="*80)
    print("Query Orchestrator Integration Example")
    print("="*80)
    print()
    
    # ========================================================================
    # STEP 1: Load Application Configuration
    # ========================================================================
    print("STEP 1: Load Application Configuration")
    print("-"*80)
    print()
    print("# Import config loader")
    print("from reportsmith.config_system.config_loader import ConfigLoader")
    print()
    print("# Load app configuration")
    print("config_loader = ConfigLoader()")
    print("app_config = config_loader.load_app_config('fund_accounting')")
    print()
    print("This loads:")
    print("  • Application metadata")
    print("  • Table relationships")
    print("  • Business context (metrics, rules)")
    print("  • Sample queries")
    print()
    
    # Simulate config structure
    sample_config = {
        "application": {
            "id": "fund_accounting",
            "name": "Fund Accounting System"
        },
        "relationships": [
            {
                "name": "funds_to_holdings",
                "parent": "funds.id",
                "child": "holdings.fund_id",
                "type": "one_to_many"
            },
            {
                "name": "funds_to_management_company",
                "parent": "management_companies.id",
                "child": "funds.management_company_id",
                "type": "one_to_many"
            }
        ]
    }
    print("Sample config loaded:")
    print(f"  App ID: {sample_config['application']['id']}")
    print(f"  Relationships: {len(sample_config['relationships'])}")
    print()
    
    # ========================================================================
    # STEP 2: Initialize Embedding Manager
    # ========================================================================
    print("STEP 2: Initialize Embedding Manager")
    print("-"*80)
    print()
    print("# Import and initialize")
    print("from reportsmith.schema_intelligence.embedding_manager import EmbeddingManager")
    print()
    print("embedding_manager = EmbeddingManager()")
    print("embedding_manager.load_schema_metadata('fund_accounting', app_config)")
    print()
    print("This creates embeddings for:")
    print("  • Schema metadata (tables, columns)")
    print("  • Dimension values (fund types, statuses)")
    print("  • Business context (metrics, formulas)")
    print()
    print("Embeddings stored in ChromaDB collections:")
    print("  • schema_metadata")
    print("  • dimension_values")
    print("  • business_context")
    print()
    
    # ========================================================================
    # STEP 3: Initialize Query Orchestrator
    # ========================================================================
    print("STEP 3: Initialize Query Orchestrator")
    print("-"*80)
    print()
    print("# Import and initialize")
    print("from reportsmith.query_orchestrator import QueryOrchestrator")
    print()
    print("orchestrator = QueryOrchestrator(")
    print("    embedding_manager=embedding_manager,")
    print("    app_config=app_config,")
    print("    max_refinement_iterations=3")
    print(")")
    print()
    print("The orchestrator initializes 5 MCP tools:")
    print("  1. EntityIdentificationTool")
    print("  2. RelationshipDiscoveryTool")
    print("  3. ContextExtractionTool")
    print("  4. FilterIdentificationTool")
    print("  5. GraphNavigationTool")
    print()
    
    # ========================================================================
    # STEP 4: Process User Query
    # ========================================================================
    print("STEP 4: Process User Query")
    print("-"*80)
    print()
    
    user_query = "Show me top 5 equity funds by AUM with their managers"
    print(f"User Query: \"{user_query}\"")
    print()
    
    print("# Analyze query")
    print("analysis = orchestrator.analyze_query(user_query)")
    print()
    
    # Simulate analysis result
    print("Analysis Results:")
    print("  Entities identified:")
    print("    • funds (table) - relevance: 0.95")
    print("    • funds.fund_type (column) - relevance: 0.92")
    print("    • funds.total_aum (column) - relevance: 0.94")
    print("    • fund_managers (table) - relevance: 0.88")
    print("    • fund_type=Equity (dimension value) - relevance: 0.90")
    print()
    print("  Relationships discovered:")
    print("    • funds → fund_manager_assignments → fund_managers")
    print()
    print("  Filters identified:")
    print("    • funds.fund_type = 'Equity' (confidence: HIGH)")
    print()
    print("  Context extracted:")
    print("    • Aggregation: None")
    print("    • Ordering: DESC by total_aum")
    print("    • Limit: 5")
    print()
    print("  Confidence: HIGH (score: 0.87)")
    print()
    
    # ========================================================================
    # STEP 5: Generate Query Plan
    # ========================================================================
    print("STEP 5: Generate Query Plan")
    print("-"*80)
    print()
    
    print("# Generate SQL plan")
    print("plan = orchestrator.generate_query_plan(analysis)")
    print()
    
    print("Query Plan:")
    print("  Primary table: funds")
    print("  Required tables: funds, fund_manager_assignments, fund_managers")
    print()
    print("  Selected columns:")
    print("    • funds.id")
    print("    • funds.fund_name")
    print("    • funds.total_aum")
    print("    • fund_managers.first_name")
    print("    • fund_managers.last_name")
    print()
    print("  JOIN clauses:")
    print("    • JOIN fund_manager_assignments ON funds.id = fund_manager_assignments.fund_id")
    print("    • JOIN fund_managers ON fund_manager_assignments.fund_manager_id = fund_managers.id")
    print()
    print("  WHERE clauses:")
    print("    • funds.fund_type = 'Equity'")
    print("    • funds.is_active = true")
    print()
    print("  ORDER BY:")
    print("    • funds.total_aum DESC")
    print()
    print("  LIMIT: 5")
    print()
    
    # ========================================================================
    # STEP 6: Validate and Refine
    # ========================================================================
    print("STEP 6: Validate and Refine")
    print("-"*80)
    print()
    
    print("# Validate plan")
    print("refined_plan = orchestrator.validate_and_refine(plan)")
    print()
    
    print("Validation Results:")
    print("  ✓ Primary table identified")
    print("  ✓ Columns selected")
    print("  ✓ Joins complete")
    print("  ✓ Filters applied")
    print("  ✓ Plan is valid")
    print()
    print("  Confidence: HIGH")
    print()
    
    # ========================================================================
    # STEP 7: Display Generated SQL
    # ========================================================================
    print("STEP 7: Generated SQL Query")
    print("-"*80)
    print()
    
    sql_query = """SELECT
    funds.id,
    funds.fund_name,
    funds.total_aum,
    fund_managers.first_name,
    fund_managers.last_name
FROM funds
JOIN fund_manager_assignments ON funds.id = fund_manager_assignments.fund_id
JOIN fund_managers ON fund_manager_assignments.fund_manager_id = fund_managers.id
WHERE
    funds.fund_type = 'Equity'
    AND funds.is_active = true
ORDER BY
    funds.total_aum DESC
LIMIT 5"""
    
    print("Generated SQL:")
    print(sql_query)
    print()
    
    # ========================================================================
    # STEP 8: Execute Query (with Connection Manager)
    # ========================================================================
    print("STEP 8: Execute Query")
    print("-"*80)
    print()
    
    print("# Execute using Connection Manager")
    print("from reportsmith.database.simple_connection_manager import ConnectionManager")
    print()
    print("conn_manager = ConnectionManager()")
    print()
    print("if refined_plan.confidence.level == 'high':")
    print("    with conn_manager.connection('financial_testdb') as conn:")
    print("        with conn.cursor() as cursor:")
    print("            cursor.execute(refined_plan.sql_query)")
    print("            results = cursor.fetchall()")
    print("            ")
    print("    # Process results")
    print("    for row in results:")
    print("        print(f'Fund: {row[1]}, AUM: ${row[2]:,.2f}, Manager: {row[3]} {row[4]}')")
    print()
    
    # ========================================================================
    # Summary
    # ========================================================================
    print("="*80)
    print("Integration Summary")
    print("="*80)
    print()
    print("The Query Orchestrator integrates with:")
    print()
    print("1. Config System")
    print("   • Loads application configuration")
    print("   • Provides relationships and business context")
    print()
    print("2. Schema Intelligence")
    print("   • Uses EmbeddingManager for semantic search")
    print("   • Searches schema, dimensions, business context")
    print()
    print("3. Database Layer")
    print("   • Uses ConnectionManager for query execution")
    print("   • Handles connection pooling and transactions")
    print()
    print("4. Logger")
    print("   • Logs all analysis steps")
    print("   • Tracks confidence scores")
    print("   • Records SQL queries")
    print()
    print("Benefits:")
    print("  ✓ Natural language to SQL conversion")
    print("  ✓ Confidence-based validation")
    print("  ✓ Iterative refinement")
    print("  ✓ Semantic search using embeddings")
    print("  ✓ Graph-based relationship navigation")
    print()


if __name__ == "__main__":
    demonstrate_integration()
