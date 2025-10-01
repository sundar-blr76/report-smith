"""
Tests for Query Orchestrator Models (no external dependencies).
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def test_models_import():
    """Test that models can be imported."""
    # Import only models, not the whole package
    from reportsmith.query_orchestrator.models import (
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
    )
    
    # Test creating a confidence score
    conf = ConfidenceScore(
        level=ConfidenceLevel.HIGH,
        score=0.95,
        reasoning="Test"
    )
    assert conf.score == 0.95
    assert conf.level == ConfidenceLevel.HIGH
    print("✓ ConfidenceScore created successfully")
    
    # Test creating an entity
    entity = EntityInfo(
        name="funds",
        entity_type=EntityType.TABLE,
        table_name="funds",
        relevance_score=0.9
    )
    assert entity.name == "funds"
    assert entity.entity_type == EntityType.TABLE
    print("✓ EntityInfo created successfully")


def test_entity_info_creation():
    """Test creating EntityInfo objects."""
    from reportsmith.query_orchestrator.models import EntityInfo, EntityType
    
    entity = EntityInfo(
        name="funds.fund_name",
        entity_type=EntityType.COLUMN,
        table_name="funds",
        column_name="fund_name",
        description="Name of the fund",
        relevance_score=0.85,
        metadata={"sample_values": ["Fund A", "Fund B"]}
    )
    
    assert entity.name == "funds.fund_name"
    assert entity.entity_type == EntityType.COLUMN
    assert entity.table_name == "funds"
    assert entity.column_name == "fund_name"
    assert entity.relevance_score == 0.85
    assert "sample_values" in entity.metadata
    print("✓ EntityInfo with metadata created successfully")


def test_relationship_info_creation():
    """Test creating RelationshipInfo objects."""
    from reportsmith.query_orchestrator.models import (
        RelationshipInfo,
        ConfidenceScore,
        ConfidenceLevel,
    )
    
    relationship = RelationshipInfo(
        name="funds_to_holdings",
        parent_table="funds",
        parent_column="id",
        child_table="holdings",
        child_column="fund_id",
        relationship_type="one_to_many",
        confidence=ConfidenceScore(
            level=ConfidenceLevel.HIGH,
            score=1.0,
            reasoning="Schema defined"
        )
    )
    
    assert relationship.name == "funds_to_holdings"
    assert relationship.parent_table == "funds"
    assert relationship.child_table == "holdings"
    assert relationship.confidence.level == ConfidenceLevel.HIGH
    print("✓ RelationshipInfo created successfully")


def test_filter_info_creation():
    """Test creating FilterInfo objects."""
    from reportsmith.query_orchestrator.models import (
        FilterInfo,
        FilterType,
        ConfidenceScore,
        ConfidenceLevel,
    )
    
    filter_info = FilterInfo(
        filter_type=FilterType.EQUALITY,
        column="fund_type",
        table="funds",
        value="Equity",
        operator="=",
        confidence=ConfidenceScore(
            level=ConfidenceLevel.HIGH,
            score=0.9,
            reasoning="Exact match"
        ),
        original_text="equity funds"
    )
    
    assert filter_info.filter_type == FilterType.EQUALITY
    assert filter_info.column == "fund_type"
    assert filter_info.value == "Equity"
    print("✓ FilterInfo created successfully")


def test_query_analysis_result_creation():
    """Test creating QueryAnalysisResult."""
    from reportsmith.query_orchestrator.models import (
        QueryAnalysisResult,
        EntityInfo,
        EntityType,
        ContextInfo,
        ConfidenceScore,
        ConfidenceLevel,
    )
    
    entity = EntityInfo(
        name="funds",
        entity_type=EntityType.TABLE,
        table_name="funds",
        relevance_score=0.9
    )
    
    context = ContextInfo(
        metric_name="Total AUM",
        temporal_context="last quarter"
    )
    
    confidence = ConfidenceScore(
        level=ConfidenceLevel.HIGH,
        score=0.85,
        reasoning="Strong matches"
    )
    
    result = QueryAnalysisResult(
        user_query="Show me equity funds",
        entities=[entity],
        relationships=[],
        filters=[],
        context=context,
        navigation_paths=[],
        confidence=confidence,
        iteration_count=1
    )
    
    assert result.user_query == "Show me equity funds"
    assert len(result.entities) == 1
    assert result.context.metric_name == "Total AUM"
    assert result.confidence.level == ConfidenceLevel.HIGH
    print("✓ QueryAnalysisResult created successfully")


def test_query_plan_creation():
    """Test creating QueryPlan."""
    from reportsmith.query_orchestrator.models import (
        QueryPlan,
        QueryAnalysisResult,
        EntityInfo,
        EntityType,
        ContextInfo,
        ConfidenceScore,
        ConfidenceLevel,
    )
    
    # Create a simple analysis
    entity = EntityInfo(
        name="funds",
        entity_type=EntityType.TABLE,
        table_name="funds",
        relevance_score=0.9
    )
    
    analysis = QueryAnalysisResult(
        user_query="Show funds",
        entities=[entity],
        relationships=[],
        filters=[],
        context=ContextInfo(),
        navigation_paths=[],
        confidence=ConfidenceScore(
            level=ConfidenceLevel.HIGH,
            score=0.9,
            reasoning="Test"
        )
    )
    
    plan = QueryPlan(
        analysis=analysis,
        primary_table="funds",
        required_tables=["funds"],
        selected_columns=["funds.id", "funds.fund_name"],
        join_clauses=[],
        where_clauses=[],
        group_by_clauses=[],
        order_by_clauses=[],
        sql_query="SELECT funds.id, funds.fund_name FROM funds"
    )
    
    assert plan.primary_table == "funds"
    assert len(plan.selected_columns) == 2
    assert "SELECT" in plan.sql_query
    print("✓ QueryPlan created successfully")


if __name__ == "__main__":
    # Run tests
    print("Running Query Orchestrator Model Tests...\n")
    
    tests = [
        ("Models Import", test_models_import),
        ("EntityInfo Creation", test_entity_info_creation),
        ("RelationshipInfo Creation", test_relationship_info_creation),
        ("FilterInfo Creation", test_filter_info_creation),
        ("QueryAnalysisResult Creation", test_query_analysis_result_creation),
        ("QueryPlan Creation", test_query_plan_creation),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {test_name} failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"Tests passed: {passed}/{len(tests)}")
    print(f"Tests failed: {failed}/{len(tests)}")
    print(f"{'='*60}")
