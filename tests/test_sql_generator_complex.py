"""Tests for SQL generator complex query support."""

import pytest
from unittest.mock import Mock

from reportsmith.query_processing.sql_generator import (
    SQLGenerator,
    SQLQuery,
    SQLColumn,
    SQLJoin,
    SQLCTE,
)
from reportsmith.schema_intelligence.knowledge_graph import (
    SchemaKnowledgeGraph,
    SchemaNode,
)


class TestSQLCTE:
    """Tests for SQLCTE class."""
    
    def test_cte_creation(self):
        """Test CTE creation."""
        # Create a simple query
        inner_query = SQLQuery(
            select_columns=[SQLColumn(table="funds", column="fund_id")],
            from_table="funds",
            joins=[],
            where_conditions=[],
            group_by=[],
            having_conditions=[],
            order_by=[],
        )
        
        # Create CTE
        cte = SQLCTE(name="fund_summary", query=inner_query)
        
        assert cte.name == "fund_summary"
        assert cte.query == inner_query
    
    def test_cte_to_sql(self):
        """Test CTE SQL generation."""
        inner_query = SQLQuery(
            select_columns=[SQLColumn(table="funds", column="fund_id")],
            from_table="funds",
            joins=[],
            where_conditions=[],
            group_by=[],
            having_conditions=[],
            order_by=[],
        )
        
        cte = SQLCTE(name="fund_summary", query=inner_query)
        sql = cte.to_sql()
        
        assert "fund_summary AS" in sql
        assert "SELECT" in sql
        assert "funds.fund_id" in sql


class TestSQLQuery:
    """Tests for SQLQuery with CTE support."""
    
    def test_query_without_cte(self):
        """Test basic query without CTE."""
        query = SQLQuery(
            select_columns=[SQLColumn(table="funds", column="fund_name")],
            from_table="funds",
            joins=[],
            where_conditions=[],
            group_by=[],
            having_conditions=[],
            order_by=[],
        )
        
        sql = query.to_sql()
        
        assert "SELECT" in sql
        assert "funds.fund_name" in sql
        assert "FROM funds" in sql
        assert "WITH" not in sql  # No CTE
    
    def test_query_with_cte(self):
        """Test query with CTE."""
        # Inner query for CTE
        inner_query = SQLQuery(
            select_columns=[SQLColumn(table="funds", column="fund_id", aggregation="sum")],
            from_table="funds",
            joins=[],
            where_conditions=[],
            group_by=["funds.fund_type"],
            having_conditions=[],
            order_by=[],
        )
        
        cte = SQLCTE(name="aum_by_type", query=inner_query)
        
        # Outer query using CTE
        outer_query = SQLQuery(
            select_columns=[SQLColumn(table="aum_by_type", column="fund_id")],
            from_table="aum_by_type",
            joins=[],
            where_conditions=[],
            group_by=[],
            having_conditions=[],
            order_by=[],
            ctes=[cte],
        )
        
        sql = outer_query.to_sql()
        
        assert "WITH" in sql
        assert "aum_by_type AS" in sql
        assert sql.index("WITH") < sql.index("SELECT")  # CTE comes before SELECT
    
    def test_query_with_multiple_ctes(self):
        """Test query with multiple CTEs."""
        # First CTE
        cte1_query = SQLQuery(
            select_columns=[SQLColumn(table="funds", column="fund_id")],
            from_table="funds",
            joins=[],
            where_conditions=[],
            group_by=[],
            having_conditions=[],
            order_by=[],
        )
        cte1 = SQLCTE(name="cte1", query=cte1_query)
        
        # Second CTE
        cte2_query = SQLQuery(
            select_columns=[SQLColumn(table="clients", column="client_id")],
            from_table="clients",
            joins=[],
            where_conditions=[],
            group_by=[],
            having_conditions=[],
            order_by=[],
        )
        cte2 = SQLCTE(name="cte2", query=cte2_query)
        
        # Main query
        main_query = SQLQuery(
            select_columns=[SQLColumn(table="cte1", column="fund_id")],
            from_table="cte1",
            joins=[],
            where_conditions=[],
            group_by=[],
            having_conditions=[],
            order_by=[],
            ctes=[cte1, cte2],
        )
        
        sql = main_query.to_sql()
        
        assert "WITH" in sql
        assert "cte1 AS" in sql
        assert "cte2 AS" in sql
        assert sql.count("AS (") >= 2  # At least 2 CTEs


class TestSQLGenerator:
    """Tests for SQLGenerator complex query detection."""
    
    @pytest.fixture
    def mock_knowledge_graph(self):
        """Create mock knowledge graph."""
        kg = SchemaKnowledgeGraph()
        
        # Add funds table
        kg.nodes["funds"] = SchemaNode(
            name="funds",
            type="table",
            metadata={"primary_key": "fund_id"}
        )
        
        kg.nodes["funds.fund_id"] = SchemaNode(
            name="fund_id",
            type="column",
            table="funds",
            metadata={"data_type": "integer"}
        )
        
        kg.nodes["funds.total_aum"] = SchemaNode(
            name="total_aum",
            type="column",
            table="funds",
            metadata={"data_type": "numeric"}
        )
        
        return kg
    
    def test_generator_init_with_complex_query_support(self, mock_knowledge_graph):
        """Test that generator initializes with complex query support."""
        generator = SQLGenerator(knowledge_graph=mock_knowledge_graph)
        
        assert generator.supports_complex_queries is True
    
    def test_needs_complex_query_for_ranking(self, mock_knowledge_graph):
        """Test detection of complex query need for ranking."""
        generator = SQLGenerator(knowledge_graph=mock_knowledge_graph)
        
        result = generator._needs_complex_query(
            intent_type="ranking",
            aggregations=["sum"],
            filters=[],
            plan={"tables": ["funds"]},
        )
        
        # Ranking with aggregation should need complex query
        assert result is True
    
    def test_needs_complex_query_for_top_n(self, mock_knowledge_graph):
        """Test detection of complex query need for top_n."""
        generator = SQLGenerator(knowledge_graph=mock_knowledge_graph)
        
        result = generator._needs_complex_query(
            intent_type="top_n",
            aggregations=["sum"],
            filters=[],
            plan={"tables": ["funds"]},
        )
        
        # top_n with aggregation should need complex query
        assert result is True
    
    def test_needs_complex_query_for_aggregated_filter(self, mock_knowledge_graph):
        """Test detection of complex query need for aggregated filters."""
        generator = SQLGenerator(knowledge_graph=mock_knowledge_graph)
        
        result = generator._needs_complex_query(
            intent_type="list",
            aggregations=[],
            filters=["total_aum > 100M"],  # Filter on aggregated value
            plan={"tables": ["funds"]},
        )
        
        # Filter referencing aggregation keyword should need complex query
        assert result is True
    
    def test_no_complex_query_for_simple_list(self, mock_knowledge_graph):
        """Test that simple list query doesn't need complex structure."""
        generator = SQLGenerator(knowledge_graph=mock_knowledge_graph)
        
        result = generator._needs_complex_query(
            intent_type="list",
            aggregations=[],
            filters=[],
            plan={"tables": ["funds"]},
        )
        
        # Simple list should not need complex query
        assert result is False
    
    def test_generate_marks_complex_query_in_metadata(self, mock_knowledge_graph):
        """Test that generate method marks complex query in metadata."""
        generator = SQLGenerator(knowledge_graph=mock_knowledge_graph)
        
        result = generator.generate(
            question="Show top 10 funds by total AUM",
            intent={
                "type": "top_n",
                "aggregations": ["sum"],
                "filters": [],
            },
            entities=[
                {
                    "text": "funds",
                    "entity_type": "table",
                    "table": "funds",
                }
            ],
            plan={"tables": ["funds"]},
        )
        
        # Check that metadata includes complex_query flag
        assert "metadata" in result
        assert "complex_query" in result["metadata"]


class TestComplexQueryGeneration:
    """Integration tests for complex query generation."""
    
    @pytest.fixture
    def full_knowledge_graph(self):
        """Create a more complete knowledge graph."""
        kg = SchemaKnowledgeGraph()
        
        # Funds table
        kg.nodes["funds"] = SchemaNode(
            name="funds",
            type="table",
            metadata={"primary_key": "fund_id"}
        )
        
        for col in ["fund_id", "fund_name", "fund_type", "total_aum"]:
            data_type = "numeric" if col == "total_aum" else "integer" if col == "fund_id" else "varchar"
            kg.nodes[f"funds.{col}"] = SchemaNode(
                name=col,
                type="column",
                table="funds",
                metadata={"data_type": data_type}
            )
        
        return kg
    
    def test_generate_simple_query(self, full_knowledge_graph):
        """Test generation of simple query (no CTE)."""
        generator = SQLGenerator(knowledge_graph=full_knowledge_graph)
        
        result = generator.generate(
            question="List all funds",
            intent={"type": "list", "aggregations": [], "filters": []},
            entities=[{"text": "funds", "entity_type": "table", "table": "funds"}],
            plan={"tables": ["funds"]},
        )
        
        sql = result["sql"]
        
        # Should be simple SELECT
        assert "SELECT" in sql
        assert "FROM funds" in sql
        assert "WITH" not in sql  # No CTE for simple query
    
    def test_generate_ranking_query(self, full_knowledge_graph):
        """Test generation of ranking query."""
        generator = SQLGenerator(knowledge_graph=full_knowledge_graph)
        
        result = generator.generate(
            question="Top 5 funds by AUM",
            intent={
                "type": "top_n",
                "aggregations": ["sum"],
                "filters": [],
            },
            entities=[
                {"text": "funds", "entity_type": "table", "table": "funds"},
                {"text": "aum", "entity_type": "column", "table": "funds", "column": "total_aum"},
            ],
            plan={"tables": ["funds"]},
        )
        
        # Should generate SQL (may or may not have CTE depending on implementation)
        assert "sql" in result
        assert len(result["sql"]) > 0
        
        # Should mark as complex
        assert result["metadata"]["complex_query"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
