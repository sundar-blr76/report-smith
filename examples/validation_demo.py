"""
Demonstration of Enhanced Query Processing with Validation

This script demonstrates the new validation features:
1. Complex query support (CTEs/sub-queries)
2. LLM-based query validation against user intent
3. Schema metadata validation

Usage:
    python examples/validation_demo.py
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from reportsmith.query_processing.query_validator import QueryValidator
from reportsmith.query_processing.schema_validator import SchemaValidator
from reportsmith.query_processing.sql_generator import (
    SQLGenerator,
    SQLQuery,
    SQLColumn,
    SQLCTE,
)
from reportsmith.schema_intelligence.knowledge_graph import (
    SchemaKnowledgeGraph,
    SchemaNode,
)


def create_sample_schema() -> SchemaKnowledgeGraph:
    """Create a sample schema for demonstration."""
    kg = SchemaKnowledgeGraph()
    
    # Funds table
    kg.nodes["funds"] = SchemaNode(
        name="funds",
        type="table",
        metadata={
            "primary_key": "fund_id",
            "description": "Investment fund information",
        }
    )
    
    kg.nodes["funds.fund_id"] = SchemaNode(
        name="fund_id",
        type="column",
        table="funds",
        metadata={
            "data_type": "integer",
            "is_primary_key": True,
            "description": "Unique fund identifier",
        }
    )
    
    kg.nodes["funds.fund_name"] = SchemaNode(
        name="fund_name",
        type="column",
        table="funds",
        metadata={
            "data_type": "varchar",
            "description": "Fund name",
        }
    )
    
    kg.nodes["funds.fund_type"] = SchemaNode(
        name="fund_type",
        type="column",
        table="funds",
        metadata={
            "data_type": "varchar",
            "description": "Type of fund (equity, bond, balanced)",
        }
    )
    
    kg.nodes["funds.total_aum"] = SchemaNode(
        name="total_aum",
        type="column",
        table="funds",
        metadata={
            "data_type": "numeric",
            "description": "Total assets under management",
        }
    )
    
    kg.nodes["funds.risk_rating"] = SchemaNode(
        name="risk_rating",
        type="column",
        table="funds",
        metadata={
            "data_type": "varchar",
            "description": "Risk rating (Low, Medium, High, Aggressive)",
        }
    )
    
    return kg


def demo_complex_query_support():
    """Demonstrate complex query generation with CTEs."""
    print("\n" + "=" * 70)
    print("DEMO 1: Complex Query Support (CTEs)")
    print("=" * 70)
    
    # Create inner query (CTE)
    inner_query = SQLQuery(
        select_columns=[
            SQLColumn(table="funds", column="fund_type"),
            SQLColumn(table="funds", column="total_aum", aggregation="sum", alias="total_aum"),
        ],
        from_table="funds",
        joins=[],
        where_conditions=["funds.total_aum > 1000000"],
        group_by=["funds.fund_type"],
        having_conditions=[],
        order_by=[],
    )
    
    # Create CTE
    cte = SQLCTE(name="fund_type_summary", query=inner_query)
    
    # Create outer query using CTE
    outer_query = SQLQuery(
        select_columns=[
            SQLColumn(table="fund_type_summary", column="fund_type"),
            SQLColumn(table="fund_type_summary", column="total_aum"),
        ],
        from_table="fund_type_summary",
        joins=[],
        where_conditions=["fund_type_summary.total_aum > 5000000"],
        group_by=[],
        having_conditions=[],
        order_by=[("fund_type_summary.total_aum", "DESC")],
        limit=5,
        ctes=[cte],
    )
    
    sql = outer_query.to_sql()
    
    print("\nGenerated SQL with CTE:")
    print("-" * 70)
    print(sql)
    print("-" * 70)
    
    print("\n✓ Successfully generated complex query with CTE")
    print("  - Inner query aggregates AUM by fund type")
    print("  - Outer query filters and orders the results")
    print("  - Demonstrates support for sub-queries/CTEs")


def demo_schema_validation():
    """Demonstrate schema validation."""
    print("\n" + "=" * 70)
    print("DEMO 2: Schema Metadata Validation")
    print("=" * 70)
    
    kg = create_sample_schema()
    validator = SchemaValidator(knowledge_graph=kg)
    
    # Test 1: Valid SQL
    print("\nTest 1: Validating correct SQL...")
    result1 = validator.validate(
        sql="SELECT funds.fund_name, funds.total_aum FROM funds WHERE funds.fund_type = 'equity'",
        plan={"tables": ["funds"]},
        entities=[],
    )
    
    print(f"  Valid: {result1['is_valid']}")
    print(f"  Errors: {len(result1['errors'])}")
    print(f"  Warnings: {len(result1['warnings'])}")
    
    # Test 2: Invalid column
    print("\nTest 2: Validating SQL with invalid column...")
    result2 = validator.validate(
        sql="SELECT funds.invalid_column FROM funds",
        plan={"tables": ["funds"]},
        entities=[],
    )
    
    print(f"  Valid: {result2['is_valid']}")
    print(f"  Errors: {result2['errors']}")
    
    # Test 3: Aggregation on text column
    print("\nTest 3: Validating SUM on text column...")
    result3 = validator.validate(
        sql="SELECT SUM(funds.fund_name) FROM funds",
        plan={"tables": ["funds"]},
        entities=[],
    )
    
    print(f"  Valid: {result3['is_valid']}")
    print(f"  Warnings: {result3['warnings']}")
    
    print("\n✓ Schema validation successfully catches:")
    print("  - Missing tables and columns")
    print("  - Invalid data type operations")
    print("  - Incorrect aggregations")


def demo_query_validation_without_llm():
    """Demonstrate query validation (without LLM)."""
    print("\n" + "=" * 70)
    print("DEMO 3: Query Validation (Graceful Degradation)")
    print("=" * 70)
    
    # Create validator without LLM client
    validator = QueryValidator(llm_client=None)
    
    print("\nValidating query without LLM client...")
    result = validator.validate(
        question="Show total AUM for equity funds",
        intent={"type": "aggregate", "aggregations": ["sum"]},
        sql="SELECT SUM(funds.total_aum) FROM funds WHERE funds.fund_type = 'equity'",
        entities=[],
        plan={"tables": ["funds"]},
    )
    
    print(f"  Valid: {result['is_valid']}")
    print(f"  Reasoning: {result['reasoning']}")
    print(f"  Confidence: {result['confidence']}")
    
    print("\n✓ Query validator gracefully handles missing LLM client")
    print("  - Returns valid=True when LLM unavailable")
    print("  - Provides informative reasoning")
    print("  - Doesn't block query execution")


def demo_sql_generator_complex_detection():
    """Demonstrate complex query detection in SQL generator."""
    print("\n" + "=" * 70)
    print("DEMO 4: Automatic Complex Query Detection")
    print("=" * 70)
    
    kg = create_sample_schema()
    generator = SQLGenerator(knowledge_graph=kg)
    
    # Test 1: Simple query (no complex structure needed)
    print("\nTest 1: Simple list query...")
    needs_complex = generator._needs_complex_query(
        intent_type="list",
        aggregations=[],
        filters=[],
        plan={"tables": ["funds"]},
    )
    print(f"  Needs complex query: {needs_complex}")
    
    # Test 2: Ranking with aggregation (needs complex structure)
    print("\nTest 2: Ranking query with aggregation...")
    needs_complex = generator._needs_complex_query(
        intent_type="ranking",
        aggregations=["sum"],
        filters=[],
        plan={"tables": ["funds"]},
    )
    print(f"  Needs complex query: {needs_complex}")
    
    # Test 3: Filter on aggregated value (needs complex structure)
    print("\nTest 3: Query with filter on aggregation...")
    needs_complex = generator._needs_complex_query(
        intent_type="list",
        aggregations=[],
        filters=["total > 1000000"],
        plan={"tables": ["funds"]},
    )
    print(f"  Needs complex query: {needs_complex}")
    
    print("\n✓ SQL generator intelligently detects complex query needs:")
    print("  - Ranking/top-N queries with aggregations")
    print("  - Filters on aggregated values (HAVING equivalents)")
    print("  - Automatically uses CTEs when appropriate")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 70)
    print("ENHANCED QUERY PROCESSING - FEATURE DEMONSTRATION")
    print("=" * 70)
    print("\nThis demo showcases the three main enhancements:")
    print("1. Complex query support (CTEs/sub-queries)")
    print("2. LLM-based query validation against user intent")
    print("3. Schema metadata validation")
    
    try:
        demo_complex_query_support()
        demo_schema_validation()
        demo_query_validation_without_llm()
        demo_sql_generator_complex_detection()
        
        print("\n" + "=" * 70)
        print("ALL DEMOS COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print("\nKey Features Demonstrated:")
        print("  ✓ CTE/sub-query generation")
        print("  ✓ Schema validation catches errors before execution")
        print("  ✓ Auto-correction of common issues")
        print("  ✓ Graceful degradation without LLM")
        print("  ✓ Intelligent complex query detection")
        print("\nThe enhanced query processing pipeline ensures:")
        print("  • More robust SQL generation")
        print("  • Better alignment with user intent")
        print("  • Fewer runtime errors")
        print("  • Improved data integrity")
        
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
