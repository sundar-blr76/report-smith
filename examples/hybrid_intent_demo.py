"""
Hybrid Intent Analyzer Demo

Demonstrates the hybrid approach combining:
1. Local entity mappings (fast, precise, free)
2. LLM analysis (flexible, smart)
3. Semantic search (discovers unknowns)
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.reportsmith.config_system.config_loader import ConfigurationManager
from src.reportsmith.schema_intelligence.embedding_manager import EmbeddingManager
from src.reportsmith.schema_intelligence.dimension_loader import DimensionLoader
from src.reportsmith.query_processing.llm_intent_analyzer import LLMIntentAnalyzer
from src.reportsmith.query_processing.hybrid_intent_analyzer import HybridIntentAnalyzer
from src.reportsmith.logger import get_logger

logger = get_logger(__name__)


EXAMPLE_QUERIES = [
    # Local mappings should catch these precisely
    "Show AUM for all equity funds",  # AUM → total_aum, equity → Equity Growth
    "List fees for TruePotential clients",  # fees → fee_amount, TruePotential → exact match
    "What's the total balance for institutional investors?",  # balance, institutional
    
    # LLM handles variations
    "I need the managed assets for stock portfolios",  # managed assets = AUM, stock = equity
    "Show me charges for TP customers",  # charges = fees, TP = TruePotential, customers = clients
    
    # Complex queries need both
    "Compare AUM between conservative and aggressive funds",  # conservative=low risk, aggressive=high risk
    "What are the average fees by fund type for all our retail investors?",  # retail=individual
]


def print_separator(title: str = ""):
    """Print a visual separator."""
    if title:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")
    else:
        print(f"\n{'-'*80}\n")


def main():
    """Run the hybrid intent analyzer demo."""
    print_separator("ReportSmith Hybrid Intent Analyzer Demo")
    print("Combines: Local Mappings + LLM + Semantic Search\n")
    
    # Check for LLM API key (optional for hybrid)
    has_llm = bool(os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    if has_llm:
        if os.getenv("OPENAI_API_KEY"):
            provider = "openai"
        elif os.getenv("ANTHROPIC_API_KEY"):
            provider = "anthropic"
        else:
            provider = "gemini"
        print(f"✓ LLM available: {provider.upper()}")
    else:
        print("⚠ No LLM API key - will use local + semantic only")
    
    # Step 1: Load configuration
    print_separator("Step 1: Loading Configuration")
    config_path = project_root / "config" / "applications"
    config_manager = ConfigurationManager(str(config_path))
    
    applications = config_manager.load_all_applications()
    if not applications:
        print("✗ No applications found!")
        return
    
    app_config = applications[0]
    db_config = app_config.databases[0] if app_config.databases else None
    
    if not db_config:
        print("✗ No database config found!")
        return
    
    print(f"✓ Loaded: {app_config.name}")
    print(f"  Tables: {len(db_config.tables)}")
    
    # Step 2: Initialize embedding manager
    print_separator("Step 2: Loading Embeddings")
    embedding_manager = EmbeddingManager()
    
    # Build schema config
    schema_config = {"tables": {}}
    for table in db_config.tables:
        schema_config["tables"][table.name] = {
            "description": table.description or "",
            "primary_key": table.primary_key or "",
            "columns": table.columns
        }
    
    # Load embeddings
    embedding_manager.load_schema_metadata(app_config.id, schema_config)
    schema_count = len(embedding_manager.collections['schema_metadata'].get()['ids'])
    print(f"✓ Schema: {schema_count} embeddings")
    
    if db_config.business_context:
        embedding_manager.load_business_context(app_config.id, db_config.business_context)
        context_count = len(embedding_manager.collections['business_context'].get()['ids'])
        print(f"✓ Context: {context_count} embeddings")
    
    # Load dimensions
    db_url = os.environ.get('FINANCIAL_TESTDB_URL')
    if db_url:
        from sqlalchemy import create_engine
        dimension_loader = DimensionLoader()
        dimensions = dimension_loader.identify_dimension_columns(schema_config)
        
        if dimensions:
            engine = create_engine(db_url)
            for dim_config in dimensions:
                values = dimension_loader.load_dimension_values(engine, dim_config)
                if values:
                    embedding_manager.load_dimension_values(
                        app_id=app_config.id,
                        table=dim_config.table,
                        column=dim_config.column,
                        values=values,
                        context=dim_config.context
                    )
            
            dim_count = len(embedding_manager.collections['dimension_values'].get()['ids'])
            print(f"✓ Dimensions: {dim_count} embeddings")
    
    # Step 3: Initialize LLM analyzer (if available)
    llm_analyzer = None
    if has_llm:
        print_separator("Step 3: Initialize LLM Analyzer")
        llm_analyzer = LLMIntentAnalyzer(
            embedding_manager=embedding_manager,
            llm_provider=provider
        )
        print(f"✓ LLM analyzer ready ({provider})")
    
    # Step 4: Initialize hybrid analyzer
    print_separator("Step 4: Initialize Hybrid Analyzer")
    mappings_file = project_root / "config" / "entity_mappings.yaml"
    
    hybrid_analyzer = HybridIntentAnalyzer(
        embedding_manager=embedding_manager,
        llm_analyzer=llm_analyzer,
        mappings_file=mappings_file
    )
    print(f"✓ Hybrid analyzer ready")
    print(f"  Local mappings file: {mappings_file}")
    
    # Step 5: Analyze example queries
    print_separator("Analyzing Example Queries")
    
    for i, query in enumerate(EXAMPLE_QUERIES, 1):
        print(f"\n{'='*80}")
        print(f"Example {i}: {query}")
        print(f"{'='*80}\n")
        
        try:
            # Analyze with hybrid approach
            intent = hybrid_analyzer.analyze(query, use_llm=has_llm)
            
            # Display results
            print(intent)
            
            # Show entity sources
            if intent.entities:
                print(f"\n📊 Entity Analysis:")
                local_count = sum(1 for e in intent.entities if e.source == "local")
                llm_count = sum(1 for e in intent.entities if e.source == "llm")
                semantic_count = sum(1 for e in intent.entities if e.source == "semantic")
                
                print(f"  📌 Local mappings: {local_count}")
                print(f"  🤖 LLM extracted: {llm_count}")
                print(f"  🔍 Semantic search: {semantic_count}")
                
                print(f"\n  Details:")
                for j, entity in enumerate(intent.entities[:5], 1):
                    print(f"  {j}. {entity}")
                    if entity.local_mapping:
                        print(f"     Mapped: {entity.local_mapping.term} → {entity.canonical_name}")
                        if entity.local_mapping.aliases:
                            print(f"     Aliases: {', '.join(entity.local_mapping.aliases[:3])}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            logger.error(f"Analysis failed: {e}", exc_info=True)
        
        print_separator()
    
    # Step 6: Interactive mode
    print_separator("Interactive Mode")
    print("Enter your queries to see how hybrid analysis works\n")
    print("Legend: 📌 = Local mapping | 🤖 = LLM | 🔍 = Semantic search\n")
    
    try:
        while True:
            query = input("\n📝 Enter query: ").strip()
            if not query:
                continue
            
            print()
            try:
                intent = hybrid_analyzer.analyze(query, use_llm=has_llm)
                print(intent)
                
                if intent.entities:
                    print(f"\n📊 Sources: {intent.local_mappings_used} local, {intent.llm_entities_found} LLM")
            
            except Exception as e:
                print(f"❌ Error: {e}")
    
    except KeyboardInterrupt:
        print("\n\n👋 Exiting...")
    
    print_separator("Demo Complete")
    print("✅ Hybrid analyzer combines the best of all approaches:")
    print("  📌 Local mappings for precision and speed")
    print("  🤖 LLM for natural language flexibility")
    print("  🔍 Semantic search for discovery")


if __name__ == "__main__":
    main()
