"""
LLM Intent Analyzer Demo

Demonstrates the LLM-based intent analysis - cleaner and more maintainable
than pattern-based approach.
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
from src.reportsmith.query_processing.llm_intent_analyzer import (
    LLMIntentAnalyzer, 
    EXAMPLE_QUERIES
)
from src.reportsmith.logger import get_logger

logger = get_logger(__name__)


def print_separator(title: str = ""):
    """Print a visual separator."""
    if title:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")
    else:
        print(f"\n{'-'*80}\n")


def main():
    """Run the LLM intent analyzer demo."""
    print_separator("ReportSmith LLM Intent Analyzer Demo")
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ Error: No LLM API key found!")
        print("\nPlease set one of:")
        print("  export OPENAI_API_KEY='your-key'")
        print("  export ANTHROPIC_API_KEY='your-key'")
        print("  export GEMINI_API_KEY='your-key'")
        return
    
    # Determine provider
    if os.getenv("OPENAI_API_KEY"):
        provider = "openai"
    elif os.getenv("ANTHROPIC_API_KEY"):
        provider = "anthropic"
    else:
        provider = "gemini"
    
    print(f"✓ Using {provider.upper()} LLM")
    
    # Step 1: Load configuration
    print_separator("Step 1: Loading Configuration")
    config_path = project_root / "config" / "applications"
    config_manager = ConfigurationManager(str(config_path))
    
    applications = config_manager.load_all_applications()
    if not applications:
        print("✗ No applications found!")
        return
    
    app_config = applications[0]
    print(f"✓ Loaded: {app_config.name}")
    print(f"  Databases: {len(app_config.databases)}")
    
    if not app_config.databases:
        print("✗ No databases found!")
        return
    
    db_config = app_config.databases[0]
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
    
    print(f"\n✓ Total embeddings ready for semantic search")
    
    # Step 3: Initialize LLM analyzer
    print_separator("Step 3: Initialize LLM Analyzer")
    analyzer = LLMIntentAnalyzer(
        embedding_manager=embedding_manager,
        llm_provider=provider
    )
    print(f"✓ LLM analyzer ready ({provider})")
    
    # Step 4: Analyze example queries
    print_separator("Analyzing Example Queries")
    
    for i, query in enumerate(EXAMPLE_QUERIES, 1):
        print(f"\n{'='*80}")
        print(f"Example {i}: {query}")
        print(f"{'='*80}\n")
        
        try:
            # Analyze with LLM
            intent = analyzer.analyze(query)
            
            # Display results
            print(intent)
            
            # Show top semantic matches
            if intent.entities:
                print(f"\n📊 Top Semantic Matches:")
                for j, entity in enumerate(intent.entities[:3], 1):
                    print(f"\n{j}. {entity.text}")
                    print(f"   Type: {entity.entity_type}")
                    print(f"   Confidence: {entity.confidence:.3f}")
                    
                    if entity.semantic_matches:
                        match = entity.semantic_matches[0]
                        meta = match['metadata']
                        if 'table' in meta:
                            print(f"   Table: {meta['table']}")
                        if 'column' in meta:
                            print(f"   Column: {meta['column']}")
                        if 'description' in meta:
                            desc = meta['description']
                            if len(desc) > 60:
                                desc = desc[:57] + "..."
                            print(f"   Description: {desc}")
            
        except Exception as e:
            print(f"❌ Error analyzing query: {e}")
            logger.error(f"Analysis failed: {e}", exc_info=True)
        
        print_separator()
    
    # Step 5: Interactive mode
    print_separator("Interactive Mode")
    print("Enter your own queries (or press Ctrl+C to exit)\n")
    
    try:
        while True:
            query = input("\n📝 Enter query: ").strip()
            if not query:
                continue
            
            print()
            try:
                intent = analyzer.analyze(query)
                print(intent)
                
                if intent.entities:
                    print(f"\n📊 Top 3 Entities:")
                    for j, entity in enumerate(intent.entities[:3], 1):
                        print(f"  {j}. {entity}")
            
            except Exception as e:
                print(f"❌ Error: {e}")
    
    except KeyboardInterrupt:
        print("\n\n👋 Exiting...")
    
    print_separator("Demo Complete")
    print("✅ LLM-based intent analyzer is working!")
    print("✅ Much simpler and more maintainable than patterns")
    print("✅ Ready for Schema Mapper (Phase 1.2)")


if __name__ == "__main__":
    main()
