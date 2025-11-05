"""
Tests for LLM-driven Extraction Enhancer.

Tests cover:
- FR-1: Extraction summary generation
- FR-2: Column ordering
- FR-3: Predicate coercion (dates, currency, booleans, numerics)
- FR-4: Iterative SQL validation
"""

import json
import pytest
from unittest.mock import Mock, MagicMock, patch

from reportsmith.query_processing.extraction_enhancer import (
    ExtractionEnhancer,
    PredicateCoercion,
    ColumnOrdering,
    ValidationResult,
    ExtractionSummary,
)


class TestExtractionEnhancer:
    """Test suite for ExtractionEnhancer class."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client for testing."""
        client = Mock()
        
        # Mock OpenAI-style client
        client.chat = Mock()
        client.chat.completions = Mock()
        
        return client
    
    @pytest.fixture
    def enhancer(self, mock_llm_client):
        """Create ExtractionEnhancer instance for testing."""
        return ExtractionEnhancer(
            llm_client=mock_llm_client,
            max_iterations=3,
            sample_size=10,
        )
    
    def test_initialization(self, enhancer):
        """Test enhancer initialization."""
        assert enhancer.max_iterations == 3
        assert enhancer.sample_size == 10
        assert enhancer.enable_validation is True
        assert enhancer.enable_summary is True
        assert enhancer.enable_ordering is True
        assert enhancer.enable_coercion is True
    
    def test_provider_detection_openai(self, mock_llm_client):
        """Test OpenAI provider detection."""
        enhancer = ExtractionEnhancer(llm_client=mock_llm_client)
        assert enhancer.provider == "openai"
    
    def test_provider_detection_anthropic(self):
        """Test Anthropic provider detection."""
        client = Mock()
        client.messages = Mock()
        enhancer = ExtractionEnhancer(llm_client=client)
        assert enhancer.provider == "anthropic"
    
    def test_provider_detection_gemini(self):
        """Test Gemini provider detection."""
        client = Mock()
        # No chat.completions or messages attribute
        enhancer = ExtractionEnhancer(llm_client=client)
        assert enhancer.provider == "gemini"
    
    def test_provider_detection_none(self):
        """Test no provider case."""
        enhancer = ExtractionEnhancer(llm_client=None)
        assert enhancer.provider == "none"


class TestSummaryGeneration:
    """Test FR-1: Extraction summary generation."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create mock OpenAI client."""
        client = Mock()
        client.chat = Mock()
        client.chat.completions = Mock()
        
        # Mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = json.dumps({
            "summary": "Retrieved AUM for equity funds, filtered by active status.",
            "filters_applied": ["is_active = true", "fund_type = 'Equity Growth'"],
            "transformations": [],
            "assumptions": ["Date range assumed to be current fiscal year"],
        })
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 500
        mock_response.usage.completion_tokens = 100
        mock_response.usage.total_tokens = 600
        
        client.chat.completions.create = Mock(return_value=mock_response)
        
        return client
    
    def test_summary_generation_basic(self, mock_llm_client):
        """Test basic summary generation."""
        enhancer = ExtractionEnhancer(llm_client=mock_llm_client)
        
        summary = enhancer.generate_summary(
            question="Show AUM for equity funds",
            sql="SELECT SUM(total_aum) FROM funds WHERE fund_type = 'Equity Growth'",
            entities=[
                {"text": "AUM", "entity_type": "column"},
                {"text": "equity", "entity_type": "dimension_value"},
            ],
            filters=["fund_type = 'Equity Growth'"],
        )
        
        assert isinstance(summary, ExtractionSummary)
        assert "AUM" in summary.summary or "equity" in summary.summary.lower()
        assert len(summary.filters_applied) > 0
    
    def test_summary_with_date_coercion(self, mock_llm_client):
        """Test summary with date coercion (Q4 2025)."""
        # Update mock to return date-specific summary
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = json.dumps({
            "summary": "Retrieved quarterly data for Q4 2025 (2025-10-01 to 2025-12-31).",
            "filters_applied": ["date >= '2025-10-01'", "date <= '2025-12-31'"],
            "transformations": ["Q4 2025 converted to date range"],
            "assumptions": [],
        })
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 500
        mock_response.usage.completion_tokens = 100
        mock_response.usage.total_tokens = 600
        
        mock_llm_client.chat.completions.create = Mock(return_value=mock_response)
        
        enhancer = ExtractionEnhancer(llm_client=mock_llm_client)
        
        coercions = [
            PredicateCoercion(
                original_value="Q4 2025",
                canonical_value="date >= '2025-10-01' AND date <= '2025-12-31'",
                value_type="date",
                reasoning="Q4 2025 converted to fiscal quarter date range",
            )
        ]
        
        summary = enhancer.generate_summary(
            question="Show revenue for Q4 2025",
            sql="SELECT SUM(revenue) FROM sales WHERE date >= '2025-10-01' AND date <= '2025-12-31'",
            entities=[{"text": "revenue", "entity_type": "column"}],
            filters=["date >= '2025-10-01'", "date <= '2025-12-31'"],
            coercions=coercions,
        )
        
        assert "Q4 2025" in summary.summary or "2025-10" in summary.summary
        assert len(summary.transformations) > 0
    
    def test_summary_with_currency_coercion(self, mock_llm_client):
        """Test summary with currency coercion ($1.2M)."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = json.dumps({
            "summary": "Retrieved funds with AUM exceeding $1.2M (1,200,000).",
            "filters_applied": ["total_aum > 1200000"],
            "transformations": ["$1.2M converted to 1,200,000"],
            "assumptions": ["Currency: USD"],
        })
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 500
        mock_response.usage.completion_tokens = 100
        mock_response.usage.total_tokens = 600
        
        mock_llm_client.chat.completions.create = Mock(return_value=mock_response)
        
        enhancer = ExtractionEnhancer(llm_client=mock_llm_client)
        
        coercions = [
            PredicateCoercion(
                original_value="$1.2M",
                canonical_value="1200000",
                value_type="currency",
                reasoning="$1.2M converted to numeric value",
            )
        ]
        
        summary = enhancer.generate_summary(
            question="Show funds with AUM > $1.2M",
            sql="SELECT * FROM funds WHERE total_aum > 1200000",
            entities=[{"text": "AUM", "entity_type": "column"}],
            filters=["total_aum > 1200000"],
            coercions=coercions,
        )
        
        assert "1.2M" in summary.summary or "1200000" in summary.summary or "1,200,000" in summary.summary
    
    def test_summary_disabled(self):
        """Test summary generation when disabled."""
        enhancer = ExtractionEnhancer(llm_client=None, enable_summary=False)
        
        summary = enhancer.generate_summary(
            question="Test",
            sql="SELECT * FROM test",
            entities=[],
            filters=[],
        )
        
        assert summary.summary == "Query executed successfully."


class TestColumnOrdering:
    """Test FR-2: LLM-driven column ordering."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create mock OpenAI client."""
        client = Mock()
        client.chat = Mock()
        client.chat.completions = Mock()
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = json.dumps({
            "ordered_columns": [
                "funds.fund_id",
                "funds.fund_name",
                "funds.total_aum",
                "funds.fund_type",
            ],
            "reasoning": "Primary identifiers first (ID, name), then metrics (AUM), then descriptive attributes (type)",
        })
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 400
        mock_response.usage.completion_tokens = 80
        mock_response.usage.total_tokens = 480
        
        client.chat.completions.create = Mock(return_value=mock_response)
        
        return client
    
    def test_column_ordering_basic(self, mock_llm_client):
        """Test basic column ordering."""
        enhancer = ExtractionEnhancer(llm_client=mock_llm_client)
        
        columns = [
            {"table": "funds", "column": "total_aum", "aggregation": "sum"},
            {"table": "funds", "column": "fund_type", "aggregation": None},
            {"table": "funds", "column": "fund_name", "aggregation": None},
            {"table": "funds", "column": "fund_id", "aggregation": None},
        ]
        
        ordering = enhancer.determine_column_order(
            question="Show AUM by fund type",
            columns=columns,
            intent_type="aggregate",
        )
        
        assert isinstance(ordering, ColumnOrdering)
        assert len(ordering.ordered_columns) == 4
        # Check that ID/name come before metrics
        id_idx = next(i for i, col in enumerate(ordering.ordered_columns) if "fund_id" in col)
        aum_idx = next(i for i, col in enumerate(ordering.ordered_columns) if "total_aum" in col)
        assert id_idx < aum_idx
    
    def test_column_ordering_disabled(self):
        """Test column ordering when disabled."""
        enhancer = ExtractionEnhancer(llm_client=None, enable_ordering=False)
        
        columns = [
            {"table": "funds", "column": "total_aum"},
            {"table": "funds", "column": "fund_name"},
        ]
        
        ordering = enhancer.determine_column_order(
            question="Test",
            columns=columns,
            intent_type="list",
        )
        
        assert len(ordering.ordered_columns) == 2
        assert "using original order" in ordering.reasoning.lower()


class TestPredicateCoercion:
    """Test FR-3: Sample-driven predicate coercion."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create mock OpenAI client."""
        client = Mock()
        client.chat = Mock()
        client.chat.completions = Mock()
        return client
    
    def test_date_quarter_coercion(self, mock_llm_client):
        """Test date coercion for Q4 2025."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = json.dumps({
            "canonical_value": "date >= '2025-10-01' AND date <= '2025-12-31'",
            "value_type": "date",
            "reasoning": "Q4 2025 represents fiscal quarter 4 of 2025 (October-December)",
            "confidence": 0.95,
        })
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 300
        mock_response.usage.completion_tokens = 60
        mock_response.usage.total_tokens = 360
        
        mock_llm_client.chat.completions.create = Mock(return_value=mock_response)
        
        enhancer = ExtractionEnhancer(llm_client=mock_llm_client)
        
        coercion = enhancer.coerce_predicate_value(
            column_name="report_date",
            column_type="date",
            user_value="Q4 2025",
            sample_values=["2025-01-15", "2025-06-20", "2025-09-10"],
            db_vendor="postgresql",
        )
        
        assert coercion.original_value == "Q4 2025"
        assert "2025-10" in coercion.canonical_value
        assert "2025-12" in coercion.canonical_value
        assert coercion.value_type == "date"
        assert coercion.confidence > 0.9
    
    def test_date_month_coercion(self, mock_llm_client):
        """Test date coercion for Apr-2025."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = json.dumps({
            "canonical_value": "date >= '2025-04-01' AND date <= '2025-04-30'",
            "value_type": "date",
            "reasoning": "Apr-2025 represents April 2025 month range",
            "confidence": 0.98,
        })
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 300
        mock_response.usage.completion_tokens = 60
        mock_response.usage.total_tokens = 360
        
        mock_llm_client.chat.completions.create = Mock(return_value=mock_response)
        
        enhancer = ExtractionEnhancer(llm_client=mock_llm_client)
        
        coercion = enhancer.coerce_predicate_value(
            column_name="transaction_date",
            column_type="date",
            user_value="Apr-2025",
            sample_values=["2025-01-01", "2025-02-15"],
        )
        
        assert "2025-04" in coercion.canonical_value
        assert coercion.value_type == "date"
    
    def test_currency_dollar_million_coercion(self, mock_llm_client):
        """Test currency coercion for $1.2M."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = json.dumps({
            "canonical_value": "1200000",
            "value_type": "currency",
            "reasoning": "$1.2M equals 1.2 million dollars = 1,200,000",
            "confidence": 1.0,
        })
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 300
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 350
        
        mock_llm_client.chat.completions.create = Mock(return_value=mock_response)
        
        enhancer = ExtractionEnhancer(llm_client=mock_llm_client)
        
        coercion = enhancer.coerce_predicate_value(
            column_name="total_aum",
            column_type="numeric",
            user_value="$1.2M",
            sample_values=[1000000, 2500000, 5000000],
        )
        
        assert coercion.canonical_value == "1200000"
        assert coercion.value_type == "currency"
        assert coercion.confidence == 1.0
    
    def test_currency_inr_lakh_coercion(self, mock_llm_client):
        """Test currency coercion for INR 12,00,000."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = json.dumps({
            "canonical_value": "1200000",
            "value_type": "currency",
            "reasoning": "INR 12,00,000 in Indian numbering (12 lakh) = 1,200,000",
            "confidence": 1.0,
        })
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 300
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 350
        
        mock_llm_client.chat.completions.create = Mock(return_value=mock_response)
        
        enhancer = ExtractionEnhancer(llm_client=mock_llm_client)
        
        coercion = enhancer.coerce_predicate_value(
            column_name="amount",
            column_type="decimal",
            user_value="INR 12,00,000",
            sample_values=[1000000, 1500000],
        )
        
        assert coercion.canonical_value == "1200000"
        assert coercion.value_type == "currency"
    
    def test_boolean_yn_coercion(self, mock_llm_client):
        """Test boolean coercion for Y/N."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = json.dumps({
            "canonical_value": "true",
            "value_type": "boolean",
            "reasoning": "Y represents Yes/True in boolean context",
            "confidence": 1.0,
        })
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 250
        mock_response.usage.completion_tokens = 40
        mock_response.usage.total_tokens = 290
        
        mock_llm_client.chat.completions.create = Mock(return_value=mock_response)
        
        enhancer = ExtractionEnhancer(llm_client=mock_llm_client)
        
        coercion = enhancer.coerce_predicate_value(
            column_name="is_active",
            column_type="boolean",
            user_value="Y",
            sample_values=[True, False, True],
        )
        
        assert coercion.canonical_value == "true"
        assert coercion.value_type == "boolean"
    
    def test_boolean_numeric_coercion(self, mock_llm_client):
        """Test boolean coercion for 1/0."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = json.dumps({
            "canonical_value": "true",
            "value_type": "boolean",
            "reasoning": "1 represents true in boolean context",
            "confidence": 1.0,
        })
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 250
        mock_response.usage.completion_tokens = 40
        mock_response.usage.total_tokens = 290
        
        mock_llm_client.chat.completions.create = Mock(return_value=mock_response)
        
        enhancer = ExtractionEnhancer(llm_client=mock_llm_client)
        
        coercion = enhancer.coerce_predicate_value(
            column_name="is_verified",
            column_type="boolean",
            user_value="1",
            sample_values=[1, 0, 1, 1],
        )
        
        assert coercion.canonical_value == "true"
        assert coercion.value_type == "boolean"
    
    def test_predicate_coercion_disabled(self):
        """Test predicate coercion when disabled."""
        enhancer = ExtractionEnhancer(llm_client=None, enable_coercion=False)
        
        coercion = enhancer.coerce_predicate_value(
            column_name="test",
            column_type="text",
            user_value="Q4 2025",
            sample_values=[],
        )
        
        assert coercion.original_value == "Q4 2025"
        assert coercion.canonical_value == "Q4 2025"
        assert "disabled" in coercion.reasoning.lower()


class TestSQLValidation:
    """Test FR-4: Iterative SQL validation and refinement."""
    
    @pytest.fixture
    def mock_sql_executor(self):
        """Create mock SQL executor."""
        executor = Mock()
        
        # Mock successful validation
        executor.validate_sql = Mock(return_value={"valid": True, "error": None})
        
        # Mock successful execution
        executor.execute_query = Mock(
            return_value={
                "columns": ["fund_id", "fund_name", "total_aum"],
                "rows": [
                    {"fund_id": 1, "fund_name": "Fund A", "total_aum": 1000000},
                    {"fund_id": 2, "fund_name": "Fund B", "total_aum": 2000000},
                ],
                "row_count": 2,
                "error": None,
            }
        )
        
        return executor
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create mock OpenAI client."""
        client = Mock()
        client.chat = Mock()
        client.chat.completions = Mock()
        return client
    
    def test_validation_success_no_iteration(self, mock_llm_client, mock_sql_executor):
        """Test validation succeeds without iteration."""
        enhancer = ExtractionEnhancer(llm_client=mock_llm_client)
        
        sql = "SELECT fund_id, fund_name, total_aum FROM funds WHERE is_active = true"
        
        final_sql, history = enhancer.validate_and_refine_sql(
            question="Show active funds",
            sql=sql,
            entities=[
                {"text": "fund_id", "entity_type": "column", "column": "fund_id"},
                {"text": "fund_name", "entity_type": "column", "column": "fund_name"},
                {"text": "total_aum", "entity_type": "column", "column": "total_aum"},
            ],
            intent={"type": "list"},
            sql_executor=mock_sql_executor,
        )
        
        assert final_sql == sql
        assert len(history) == 1
        assert history[0].valid is True
        assert len(history[0].issues) == 0
    
    def test_validation_syntax_error(self, mock_llm_client, mock_sql_executor):
        """Test validation catches syntax errors."""
        # Mock syntax error
        mock_sql_executor.validate_sql = Mock(
            return_value={"valid": False, "error": "syntax error near 'SELECTT'"}
        )
        
        # Mock LLM refinement
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = json.dumps({
            "refined_sql": "SELECT fund_id FROM funds",
            "changes_made": ["Fixed SELECTT typo to SELECT"],
            "reasoning": "Corrected syntax error",
        })
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 500
        mock_response.usage.completion_tokens = 100
        mock_response.usage.total_tokens = 600
        
        mock_llm_client.chat.completions.create = Mock(return_value=mock_response)
        
        enhancer = ExtractionEnhancer(llm_client=mock_llm_client, max_iterations=2)
        
        sql = "SELECTT fund_id FROM funds"
        
        final_sql, history = enhancer.validate_and_refine_sql(
            question="Show funds",
            sql=sql,
            entities=[{"text": "fund_id", "entity_type": "column", "column": "fund_id"}],
            intent={"type": "list"},
            sql_executor=mock_sql_executor,
        )
        
        # Should have attempted refinement
        assert len(history) >= 1
        assert not history[0].valid
        assert len(history[0].issues) > 0
        assert "syntax error" in history[0].issues[0].lower()
    
    def test_validation_max_iterations(self, mock_llm_client, mock_sql_executor):
        """Test validation respects max iterations."""
        # Mock persistent validation failure
        mock_sql_executor.validate_sql = Mock(
            return_value={"valid": False, "error": "persistent error"}
        )
        
        # Mock LLM always returns same SQL
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = json.dumps({
            "refined_sql": "SELECT * FROM funds",
            "changes_made": [],
            "reasoning": "No changes possible",
        })
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 500
        mock_response.usage.completion_tokens = 100
        mock_response.usage.total_tokens = 600
        
        mock_llm_client.chat.completions.create = Mock(return_value=mock_response)
        
        enhancer = ExtractionEnhancer(llm_client=mock_llm_client, max_iterations=3)
        
        sql = "SELECT * FROM funds"
        
        final_sql, history = enhancer.validate_and_refine_sql(
            question="Show funds",
            sql=sql,
            entities=[],
            intent={"type": "list"},
            sql_executor=mock_sql_executor,
        )
        
        # Should stop at max iterations
        assert len(history) <= 3
    
    def test_validation_disabled(self, mock_sql_executor):
        """Test validation when disabled."""
        enhancer = ExtractionEnhancer(llm_client=None, enable_validation=False)
        
        sql = "SELECT * FROM funds"
        
        final_sql, history = enhancer.validate_and_refine_sql(
            question="Test",
            sql=sql,
            entities=[],
            intent={"type": "list"},
            sql_executor=mock_sql_executor,
        )
        
        assert final_sql == sql
        assert len(history) == 0


class TestSafetyAndCompliance:
    """Test safety features and compliance requirements."""
    
    @pytest.fixture
    def enhancer(self):
        """Create enhancer for testing."""
        client = Mock()
        client.chat = Mock()
        client.chat.completions = Mock()
        return ExtractionEnhancer(
            llm_client=client,
            rate_limit_rpm=10,
            cost_cap_tokens=1000,
        )
    
    def test_read_only_sql_select(self, enhancer):
        """Test read-only check passes for SELECT."""
        sql = "SELECT * FROM funds WHERE is_active = true"
        assert enhancer._is_read_only_sql(sql) is True
    
    def test_read_only_sql_with_cte(self, enhancer):
        """Test read-only check passes for WITH (CTE)."""
        sql = """
        WITH fund_totals AS (
            SELECT fund_type, SUM(total_aum) AS total
            FROM funds
            GROUP BY fund_type
        )
        SELECT * FROM fund_totals
        """
        assert enhancer._is_read_only_sql(sql) is True
    
    def test_read_only_sql_insert(self, enhancer):
        """Test read-only check fails for INSERT."""
        sql = "INSERT INTO funds (fund_name) VALUES ('Test')"
        assert enhancer._is_read_only_sql(sql) is False
    
    def test_read_only_sql_update(self, enhancer):
        """Test read-only check fails for UPDATE."""
        sql = "UPDATE funds SET is_active = false WHERE fund_id = 1"
        assert enhancer._is_read_only_sql(sql) is False
    
    def test_read_only_sql_delete(self, enhancer):
        """Test read-only check fails for DELETE."""
        sql = "DELETE FROM funds WHERE fund_id = 1"
        assert enhancer._is_read_only_sql(sql) is False
    
    def test_read_only_sql_drop(self, enhancer):
        """Test read-only check fails for DROP."""
        sql = "DROP TABLE funds"
        assert enhancer._is_read_only_sql(sql) is False
    
    def test_read_only_sql_create(self, enhancer):
        """Test read-only check fails for CREATE."""
        sql = "CREATE TABLE test (id INT)"
        assert enhancer._is_read_only_sql(sql) is False
    
    def test_read_only_sql_column_with_insert_keyword(self, enhancer):
        """Test read-only check doesn't false positive on column names."""
        # Column named INSERT_DATE should not trigger false positive
        sql = "SELECT fund_id, INSERT_DATE FROM funds"
        assert enhancer._is_read_only_sql(sql) is True
    
    def test_rate_limiting(self, enhancer):
        """Test rate limiting functionality."""
        import time
        
        # Reset tracking
        enhancer.reset_usage_tracking()
        
        # Should allow initial requests up to limit
        for i in range(10):
            assert enhancer._check_rate_limit() is True
            enhancer._request_timestamps.append(time.time())
        
        # 11th request should fail
        assert enhancer._check_rate_limit() is False
    
    def test_cost_cap(self, enhancer):
        """Test cost cap functionality."""
        # Reset tracking
        enhancer.reset_usage_tracking()
        
        # Use 500 tokens
        assert enhancer._check_cost_cap(500) is True
        enhancer._total_tokens_used = 500
        
        # Another 400 tokens should pass (900 total)
        assert enhancer._check_cost_cap(400) is True
        enhancer._total_tokens_used = 900
        
        # Another 200 tokens should fail (would be 1100 total, over 1000 cap)
        assert enhancer._check_cost_cap(200) is False
    
    def test_usage_tracking_reset(self, enhancer):
        """Test usage tracking reset."""
        import time
        
        # Add some usage
        enhancer._request_timestamps.append(time.time())
        enhancer._total_tokens_used = 500
        
        # Reset
        enhancer.reset_usage_tracking()
        
        # Should be cleared
        assert len(enhancer._request_timestamps) == 0
        assert enhancer._total_tokens_used == 0
    
    def test_validation_rejects_unsafe_sql(self):
        """Test validation rejects SQL with DDL/DML."""
        client = Mock()
        client.chat = Mock()
        client.chat.completions = Mock()
        
        enhancer = ExtractionEnhancer(llm_client=client)
        
        sql_executor = Mock()
        
        # Try to validate an INSERT statement
        sql = "INSERT INTO funds (fund_name) VALUES ('Malicious')"
        
        final_sql, history = enhancer.validate_and_refine_sql(
            question="Test",
            sql=sql,
            entities=[],
            intent={"type": "list"},
            sql_executor=sql_executor,
        )
        
        # Should reject immediately
        assert len(history) == 1
        assert history[0].valid is False
        assert any("DDL/DML" in issue for issue in history[0].issues)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
