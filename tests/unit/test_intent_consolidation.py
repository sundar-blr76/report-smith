
import unittest
from reportsmith.query_processing.base_intent_analyzer import BaseIntentAnalyzer, BaseQueryIntent, IntentType
from reportsmith.query_processing.llm_intent_analyzer import LLMIntentAnalyzer
from reportsmith.query_processing.hybrid_intent_analyzer import HybridIntentAnalyzer, HybridQueryIntent

class TestIntentAnalyzerConsolidation(unittest.TestCase):
    def test_inheritance(self):
        """Verify that analyzers inherit from BaseIntentAnalyzer."""
        self.assertTrue(issubclass(LLMIntentAnalyzer, BaseIntentAnalyzer))
        self.assertTrue(issubclass(HybridIntentAnalyzer, BaseIntentAnalyzer))
        
    def test_query_intent_inheritance(self):
        """Verify that HybridQueryIntent inherits from BaseQueryIntent."""
        self.assertTrue(issubclass(HybridQueryIntent, BaseQueryIntent))

    def test_shared_types(self):
        """Verify that shared types are accessible."""
        self.assertEqual(IntentType.RETRIEVAL, "retrieval")
        
    def test_instantiation(self):
        """Verify we can instantiate the classes (mocking dependencies)."""
        # We won't actually instantiate completely as it requires EmbeddingManager which needs DB/API keys
        # But we can check if the classes are importable and have the expected methods
        self.assertTrue(hasattr(HybridIntentAnalyzer, 'analyze'))
        self.assertTrue(hasattr(LLMIntentAnalyzer, 'analyze'))

if __name__ == '__main__':
    unittest.main()
