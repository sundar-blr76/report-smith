"""
Query Intent Analyzer Demo

Demonstrates the query intent analysis capabilities of ReportSmith.
Shows how natural language queries are parsed to extract:
- Intent type
- Entities via semantic search
- Time scope
- Aggregations
- Filters
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
from src.reportsmith.query_processing.intent_analyzer import QueryIntentAnalyzer, EXAMPLE_QUERIES
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
    """Run the query intent analyzer demo."""
    print_separator("ReportSmith Query Intent Analyzer Demo")
    
    # Step 1: Load configuration
    print("Step 1: Loading application configuration...")
    config_path = project_root / "config" / "applications"
    config_manager = ConfigurationManager(str(config_path))
    
    applications = config_manager.load_all_applications()
    
    if not applications:
        print("✗ No applications found!")
        return
    
    app_config = applications[0]
    print(f"✓ Loaded config for: {app_config.name}")
    print(f"  - {len(app_config.databases)} database instances")
    
    # Get the first database for schema info
    if not app_config.databases:
        print("✗ No databases found!")
        return
    
    db_config = app_config.databases[0]
    print(f"  - {len(db_config.tables)} tables")
    
    # Step 2: Initialize embedding manager
    print_separator()
    print("Step 2: Initializing embedding manager...")
    embedding_manager = EmbeddingManager()
    
    # Build schema config from database config
    schema_config = {"tables": {}}
    for table in db_config.tables:
        schema_config["tables"][table.name] = {
            "description": table.description or "",
            "primary_key": table.primary_key or "",
            "columns": table.columns
        }
    
    # Load schema embeddings
    print("Loading schema embeddings...")
    embedding_manager.load_schema_metadata(app_config.id, schema_config)
    schema_count = len(embedding_manager.collections['schema_metadata'].get()['ids'])
    print(f"✓ Loaded {schema_count} schema embeddings")
    
    # Load business context if available
    if db_config.business_context:
        print("Loading business context...")
        embedding_manager.load_business_context(app_config.id, db_config.business_context)
        context_count = len(embedding_manager.collections['business_context'].get()['ids'])
        print(f"✓ Loaded {context_count} business context embeddings")
    
    # Load dimensions (optional - requires database connection)
    db_url = os.environ.get('FINANCIAL_TESTDB_URL')
    if db_url:
        print("Loading dimension values from database...")
        from sqlalchemy import create_engine
        
        dimension_loader = DimensionLoader()
        dimensions = dimension_loader.identify_dimension_columns(schema_config)
        
        if dimensions:
            print(f"  Found {len(dimensions)} dimension columns")
            engine = create_engine(db_url)
            
            for dim_config in dimensions:
                values = dimension_loader.load_dimension_values(engine, dim_config)
                if values:
                    # Load into embedding manager
                    embedding_manager.load_dimension_values(
                        app_id=app_config.id,
                        table=dim_config.table,
                        column=dim_config.column,
                        values=values,
                        context=dim_config.context
                    )
            
            dimension_count = len(embedding_manager.collections['dimension_values'].get()['ids'])
            print(f"✓ Loaded {dimension_count} dimension value embeddings")
        else:
            print("  No dimensions configured with is_dimension: true")
    else:
        print("⚠ FINANCIAL_TESTDB_URL not set - skipping dimension loading")
    
    # Step 3: Initialize query intent analyzer
    print_separator()
    print("Step 3: Initializing query intent analyzer...")
    analyzer = QueryIntentAnalyzer(embedding_manager)
    print("✓ Query intent analyzer ready")
    
    # Step 4: Analyze example queries
    print_separator("Analyzing Example Queries")
    
    for i, query in enumerate(EXAMPLE_QUERIES, 1):
        print(f"\n{'='*80}")
        print(f"Example {i}: {query}")
        print(f"{'='*80}\n")
        
        # Analyze the query
        intent = analyzer.analyze(query)
        
        # Display results
        print(intent)
        
        # Show top entities with details
        if intent.entities:
            print(f"\nTop Semantic Matches:")
            for j, entity in enumerate(intent.entities[:3], 1):
                print(f"\n{j}. {entity.text}")
                print(f"   Type: {entity.entity_type}")
                print(f"   Confidence: {entity.confidence:.3f}")
                if entity.semantic_matches:
                    match = entity.semantic_matches[0]
                    if 'table' in match['metadata']:
                        print(f"   Table: {match['metadata']['table']}")
                    if 'column' in match['metadata']:
                        print(f"   Column: {match['metadata']['column']}")
                    if 'description' in match['metadata']:
                        desc = match['metadata']['description']
                        if len(desc) > 60:
                            desc = desc[:57] + "..."
                        print(f"   Description: {desc}")
        
        print_separator()
    
    # Step 5: Interactive mode (optional)
    print_separator("Interactive Mode")
    print("You can now enter your own queries (or press Ctrl+C to exit)")
    print()
    
    try:
        while True:
            query = input("\nEnter query: ").strip()
            if not query:
                continue
            
            print()
            intent = analyzer.analyze(query)
            print(intent)
            
            if intent.entities:
                print(f"\nTop 3 Entities:")
                for j, entity in enumerate(intent.entities[:3], 1):
                    print(f"{j}. {entity.text} ({entity.entity_type}, confidence: {entity.confidence:.3f})")
            
    except KeyboardInterrupt:
        print("\n\nExiting interactive mode...")
    
    print_separator("Demo Complete")
    print("✓ Query intent analyzer is working correctly")
    print("✓ Ready to proceed with schema mapping and SQL generation")


if __name__ == "__main__":
    main()
