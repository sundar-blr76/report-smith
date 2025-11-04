"""Tests for query and schema validators."""

import pytest
from unittest.mock import Mock, MagicMock
import json

from reportsmith.query_processing.query_validator import QueryValidator
from reportsmith.query_processing.schema_validator import SchemaValidator
from reportsmith.schema_intelligence.knowledge_graph import (
    SchemaKnowledgeGraph,
    SchemaNode,
    SchemaEdge,
    RelationshipType,
)


class TestQueryValidator:
    """Tests for QueryValidator class."""
    
    def test_validator_init_without_llm(self):
        """Test validator initialization without LLM client."""
        validator = QueryValidator(llm_client=None)
        assert validator.llm_client is None
        assert validator.provider == "gemini"
    
    def test_validator_init_with_llm(self):
        """Test validator initialization with LLM client."""
        mock_client = Mock()
        validator = QueryValidator(llm_client=mock_client, provider="openai")
        assert validator.llm_client == mock_client
        assert validator.provider == "openai"
    
    def test_validate_without_llm_client(self):
        """Test validation when no LLM client is available."""
        validator = QueryValidator(llm_client=None)
        
        result = validator.validate(
            question="Show all funds",
            intent={"type": "list"},
            sql="SELECT * FROM funds",
            entities=[],
            plan={},
        )
        
        assert result["is_valid"] is True
        assert result["issues"] == []
        assert result["corrected_sql"] is None
        assert "no LLM client" in result["reasoning"]
        assert result["confidence"] == 0.0
    
    def test_validate_with_openai(self):
        """Test validation with OpenAI client."""
        # Mock OpenAI client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=json.dumps({
            "is_valid": True,
            "issues": [],
            "corrected_sql": None,
            "reasoning": "SQL correctly captures user intent",
            "confidence": 0.95,
        })))]
        mock_client.chat.completions.create.return_value = mock_response
        
        validator = QueryValidator(llm_client=mock_client, provider="openai")
        
        result = validator.validate(
            question="Show total AUM of equity funds",
            intent={"type": "aggregate", "aggregations": ["sum"]},
            sql="SELECT SUM(total_aum) FROM funds WHERE fund_type = 'equity'",
            entities=[
                {"text": "aum", "entity_type": "column", "table": "funds", "column": "total_aum"}
            ],
            plan={"tables": ["funds"]},
        )
        
        assert result["is_valid"] is True
        assert result["confidence"] == 0.95
        assert mock_client.chat.completions.create.called
    
    def test_validate_with_issues(self):
        """Test validation that finds issues."""
        # Mock client returning issues
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=json.dumps({
            "is_valid": False,
            "issues": ["Missing GROUP BY clause for aggregation"],
            "corrected_sql": "SELECT fund_type, SUM(total_aum) FROM funds GROUP BY fund_type",
            "reasoning": "Aggregation without GROUP BY",
            "confidence": 0.85,
        })))]
        mock_client.chat.completions.create.return_value = mock_response
        
        validator = QueryValidator(llm_client=mock_client, provider="openai")
        
        result = validator.validate(
            question="Show total AUM by fund type",
            intent={"type": "aggregate", "aggregations": ["sum"]},
            sql="SELECT SUM(total_aum) FROM funds",
            entities=[],
            plan={"tables": ["funds"]},
        )
        
        assert result["is_valid"] is False
        assert len(result["issues"]) > 0
        assert result["corrected_sql"] is not None


class TestSchemaValidator:
    """Tests for SchemaValidator class."""
    
    @pytest.fixture
    def mock_knowledge_graph(self):
        """Create a mock knowledge graph with sample schema."""
        kg = SchemaKnowledgeGraph()
        
        # Add funds table
        funds_table = SchemaNode(
            name="funds",
            type="table",
            metadata={
                "primary_key": "fund_id",
                "description": "Fund information",
            }
        )
        kg.nodes["funds"] = funds_table
        
        # Add columns to funds table
        fund_id_col = SchemaNode(
            name="fund_id",
            type="column",
            table="funds",
            metadata={
                "data_type": "integer",
                "is_primary_key": True,
            }
        )
        kg.nodes["funds.fund_id"] = fund_id_col
        
        fund_name_col = SchemaNode(
            name="fund_name",
            type="column",
            table="funds",
            metadata={
                "data_type": "varchar",
            }
        )
        kg.nodes["funds.fund_name"] = fund_name_col
        
        total_aum_col = SchemaNode(
            name="total_aum",
            type="column",
            table="funds",
            metadata={
                "data_type": "numeric",
            }
        )
        kg.nodes["funds.total_aum"] = total_aum_col
        
        # Add clients table
        clients_table = SchemaNode(
            name="clients",
            type="table",
            metadata={
                "primary_key": "client_id",
            }
        )
        kg.nodes["clients"] = clients_table
        
        client_id_col = SchemaNode(
            name="client_id",
            type="column",
            table="clients",
            metadata={
                "data_type": "integer",
                "is_primary_key": True,
            }
        )
        kg.nodes["clients.client_id"] = client_id_col
        
        return kg
    
    def test_validator_init(self, mock_knowledge_graph):
        """Test validator initialization."""
        validator = SchemaValidator(knowledge_graph=mock_knowledge_graph)
        assert validator.kg == mock_knowledge_graph
    
    def test_validate_valid_sql(self, mock_knowledge_graph):
        """Test validation of valid SQL."""
        validator = SchemaValidator(knowledge_graph=mock_knowledge_graph)
        
        result = validator.validate(
            sql="SELECT funds.fund_name, funds.total_aum FROM funds",
            plan={"tables": ["funds"]},
            entities=[],
        )
        
        assert result["is_valid"] is True
        assert len(result["errors"]) == 0
        assert result["corrected_sql"] is None
    
    def test_validate_invalid_table(self, mock_knowledge_graph):
        """Test validation with invalid table."""
        validator = SchemaValidator(knowledge_graph=mock_knowledge_graph)
        
        result = validator.validate(
            sql="SELECT * FROM nonexistent_table",
            plan={"tables": ["nonexistent_table"]},
            entities=[],
        )
        
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0
        assert any("not found" in err for err in result["errors"])
    
    def test_validate_invalid_column(self, mock_knowledge_graph):
        """Test validation with invalid column."""
        validator = SchemaValidator(knowledge_graph=mock_knowledge_graph)
        
        result = validator.validate(
            sql="SELECT funds.invalid_column FROM funds",
            plan={"tables": ["funds"]},
            entities=[],
        )
        
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0
        assert any("Column" in err and "not found" in err for err in result["errors"])
    
    def test_validate_data_type_warning(self, mock_knowledge_graph):
        """Test validation generates warning for data type issues."""
        validator = SchemaValidator(knowledge_graph=mock_knowledge_graph)
        
        # Arithmetic on varchar column should generate warning
        result = validator.validate(
            sql="SELECT funds.fund_name * 2 FROM funds",
            plan={"tables": ["funds"]},
            entities=[],
        )
        
        # Should have warning about type mismatch
        assert len(result["warnings"]) > 0 or len(result["errors"]) > 0
    
    def test_validate_aggregation_on_numeric(self, mock_knowledge_graph):
        """Test validation of aggregation on numeric column."""
        validator = SchemaValidator(knowledge_graph=mock_knowledge_graph)
        
        result = validator.validate(
            sql="SELECT SUM(funds.total_aum) FROM funds",
            plan={"tables": ["funds"]},
            entities=[],
        )
        
        # Should be valid - numeric aggregation
        assert result["is_valid"] is True
        assert len(result["errors"]) == 0
    
    def test_validate_aggregation_on_text(self, mock_knowledge_graph):
        """Test validation of aggregation on text column."""
        validator = SchemaValidator(knowledge_graph=mock_knowledge_graph)
        
        result = validator.validate(
            sql="SELECT SUM(funds.fund_name) FROM funds",
            plan={"tables": ["funds"]},
            entities=[],
        )
        
        # Should generate warning about SUM on text
        assert len(result["warnings"]) > 0
        assert any("non-numeric" in warn for warn in result["warnings"])
    
    def test_auto_correction_case_sensitivity(self, mock_knowledge_graph):
        """Test auto-correction of case sensitivity issues."""
        validator = SchemaValidator(knowledge_graph=mock_knowledge_graph)
        
        # Use wrong case for column name
        result = validator.validate(
            sql="SELECT funds.FUND_NAME FROM funds",
            plan={"tables": ["funds"]},
            entities=[],
        )
        
        # Should either correct it or report error
        # (Implementation may vary - checking both possibilities)
        is_corrected = result["corrected_sql"] is not None and len(result["corrections_applied"]) > 0
        has_error = len(result["errors"]) > 0
        
        assert is_corrected or has_error
    
    def test_validate_join_columns(self, mock_knowledge_graph):
        """Test validation of join columns."""
        validator = SchemaValidator(knowledge_graph=mock_knowledge_graph)
        
        # Valid join
        plan = {
            "tables": ["funds", "clients"],
            "path_edges": [
                {
                    "from": "funds",
                    "to": "clients",
                    "from_column": "fund_id",
                    "to_column": "client_id",
                }
            ]
        }
        
        result = validator.validate(
            sql="SELECT * FROM funds JOIN clients ON funds.fund_id = clients.client_id",
            plan=plan,
            entities=[],
        )
        
        # Should be valid (columns exist)
        # Note: May have warnings about type mismatch but should validate structure
        assert result["is_valid"] is True or len(result["errors"]) == 0


class TestValidatorIntegration:
    """Integration tests for validators working together."""
    
    def test_validators_complement_each_other(self):
        """Test that query and schema validators complement each other."""
        # Schema validator catches structural issues
        # Query validator catches semantic issues
        
        # This would be tested with real data in integration tests
        # Here we just ensure they can be used together
        
        mock_kg = SchemaKnowledgeGraph()
        schema_val = SchemaValidator(knowledge_graph=mock_kg)
        query_val = QueryValidator(llm_client=None)
        
        # Both validators should be independent
        assert schema_val is not None
        assert query_val is not None
    
    def test_validation_error_handling(self):
        """Test that validators handle errors gracefully."""
        validator = QueryValidator(llm_client=None)
        
        # Should not raise exception even with invalid inputs
        result = validator.validate(
            question=None,  # Invalid
            intent={},
            sql="",
            entities=[],
            plan={},
        )
        
        # Should return valid result structure
        assert "is_valid" in result
        assert "issues" in result
        assert "reasoning" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
