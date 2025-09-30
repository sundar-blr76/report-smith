"""
ReportSmith Embedding System Demo

Demonstrates the refactored embedding system:
1. Config-driven dimension loading (is_dimension: true in schema.yaml)
2. Unlimited dimension values (no artificial max_values=100 limits)
3. Dictionary table support with predicates (when available)
4. Linked dimensions directly in column definitions

USAGE:
    # Option 1: Use the run script (RECOMMENDED)
    cd examples
    ./run_embedding_demo.sh
    
    # Option 2: Run directly (ensure venv is activated)
    source venv/bin/activate
    export PYTHONPATH="${PWD}/src:${PYTHONPATH}"
    python3 examples/embedding_demo.py
    
REQUIREMENTS:
    - Virtual environment activated (venv/)
    - All dependencies installed: pip install -r requirements.txt
    - Database connection to financial_testdb (for dimension loading)
"""

import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reportsmith.config_system.config_loader import ConfigurationManager
from reportsmith.schema_intelligence import EmbeddingManager, DimensionLoader
from reportsmith.logger import get_logger

logger = get_logger(__name__)


def demo_config_driven_dimensions():
    """Demonstrate the new config-driven dimension system."""
    print("\n" + "="*80)
    print("DEMO: Config-Driven Dimension Loading (NEW APPROACH)")
    print("="*80)
    
    # Get project root directory
    project_root = Path(__file__).parent.parent
    config_path = project_root / "config" / "applications"
    
    # Initialize managers
    config_manager = ConfigurationManager(str(config_path))
    embedding_manager = EmbeddingManager()
    dimension_loader = DimensionLoader()
    
    # Load applications
    applications = config_manager.load_all_applications()
    print(f"\n✓ Loaded {len(applications)} applications")
    
    if not applications:
        print("✗ No applications found!")
        print(f"   Config path: {config_path}")
        return
    
    app = applications[0]
    print(f"  Application: {app.name}")
    print(f"  Databases: {len(app.databases)}")
    
    if not app.databases:
        print("✗ No databases found!")
        return
    
    db = app.databases[0]
    print(f"  Database: {db.name} ({len(db.tables)} tables)")
    
    # Build schema config
    schema_config = {"tables": {}}
    for table in db.tables:
        schema_config["tables"][table.name] = {
            "description": table.description or "",
            "primary_key": table.primary_key or "",
            "columns": table.columns
        }
    
    print(f"\n✓ Built schema config with {len(schema_config['tables'])} tables")
    
    # Identify dimensions using new approach
    dimensions = dimension_loader.identify_dimension_columns(schema_config)
    print(f"✓ Identified {len(dimensions)} dimensions from column markers")
    
    for dim in dimensions:
        print(f"  - {dim.table}.{dim.column}: {dim.description}")
        if dim.context:
            print(f"    Context: {dim.context}")
    
    return app, db, dimensions, embedding_manager, dimension_loader


def demo_unlimited_dimension_loading(dimensions, embedding_manager, dimension_loader):
    """Demonstrate loading ALL dimension values without limits."""
    print("\n" + "="*80) 
    print("DEMO: Unlimited Dimension Value Loading")
    print("="*80)
    
    # Check database connection
    try:
        engine = create_engine(f"postgresql://postgres:postgres@192.168.29.69:5432/financial_testdb")
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print(f"\n✓ Connected to financial_testdb")
        
        # Load each dimension
        total_values = 0
        for dim in dimensions:
            print(f"\n📊 Loading dimension: {dim.table}.{dim.column}")
            
            values = dimension_loader.load_dimension_values(engine, dim)
            
            if values:
                print(f"  ✓ Loaded ALL {len(values)} values (no artificial limits)")
                total_values += len(values)
                
                # Show top values
                for i, val in enumerate(values[:5], 1):
                    desc = val.get('description', val['value'])
                    print(f"    {i}. '{val['value']}' (used {val['count']} times)")
                    if desc != val['value']:
                        print(f"       Description: {desc}")
                
                if len(values) > 5:
                    print(f"    ... and {len(values) - 5} more values")
                
                # Load into embedding manager
                embedding_manager.load_dimension_values(
                    app_id="fund_accounting",
                    table=dim.table,
                    column=dim.column,
                    values=values,
                    context=dim.context or dim.description
                )
            else:
                print(f"  ⚠ No values found")
        
        print(f"\n✅ Total dimension values loaded: {total_values}")
        print("🎯 Key improvement: NO artificial max_values=100 or min_count limits!")
        
        engine.dispose()
        return True
        
    except Exception as e:
        print(f"\n✗ Database connection failed: {e}")
        return False


def demo_semantic_search(embedding_manager):
    """Demonstrate semantic search on loaded embeddings."""
    print("\n" + "="*80)
    print("DEMO: Semantic Search on Unlimited Dimensions")
    print("="*80)
    
    search_examples = [
        ("equity investments", "Should find fund_type values"),
        ("individual clients", "Should find client_type values"), 
        ("high performing managers", "Should find performance_rating values"),
        ("conservative risk", "Should find risk_rating values"),
    ]
    
    for query, expected in search_examples:
        print(f"\n🔍 Query: '{query}'")
        print(f"   Expected: {expected}")
        
        results = embedding_manager.search_dimensions(
            query, 
            app_id="fund_accounting",
            top_k=3
        )
        
        if results:
            print(f"   Results: {len(results)}")
            for i, result in enumerate(results, 1):
                full_path = result.metadata.get('full_path', 'unknown')
                value = result.metadata.get('value', 'unknown')
                count = result.metadata.get('count', 0)
                score = result.score
                print(f"     {i}. [{score:.3f}] {full_path} = '{value}' ({count} records)")
        else:
            print(f"   No results found")


def demo_dictionary_table_config():
    """Show dictionary table configuration examples."""
    print("\n" + "="*80)
    print("DEMO: Dictionary Table Configuration (Future Enhancement)")
    print("="*80)
    
    examples = [
        {
            "column": "fund_type",
            "description": "Enhanced with fund type dictionary",
            "config": {
                "dictionary_table": "fund_type_dictionary",
                "dictionary_value_column": "fund_type_code", 
                "dictionary_description_column": "description",
                "dictionary_predicates": [
                    "is_active = true",
                    "effective_date <= CURRENT_DATE"
                ]
            }
        },
        {
            "column": "risk_rating", 
            "description": "Enhanced with risk rating dictionary",
            "config": {
                "dictionary_table": "risk_rating_dictionary",
                "dictionary_value_column": "risk_code",
                "dictionary_description_column": "description"
            }
        }
    ]
    
    for example in examples:
        print(f"\n📖 {example['column']} - {example['description']}")
        print("   Configuration in schema.yaml:")
        print(f"     dictionary_table: {example['config']['dictionary_table']}")
        print(f"     dictionary_value_column: {example['config']['dictionary_value_column']}")
        print(f"     dictionary_description_column: {example['config']['dictionary_description_column']}")
        if 'dictionary_predicates' in example['config']:
            print("     dictionary_predicates:")
            for predicate in example['config']['dictionary_predicates']:
                print(f"       - \"{predicate}\"")
    
    print("\n🔧 To enable: Create dictionary tables in FinancialTestDB project")
    print("🔧 Then: Uncomment dictionary settings in schema.yaml")


def main():
    """Run the updated embedding demo."""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*18 + "ReportSmith Embedding System Demo" + " "*18 + "║")
    print("╚" + "="*78 + "╝")
    print("🚀 Showcasing: Config-driven dimensions, unlimited loading, dictionary support")
    
    # Demo 1: Config-driven dimension identification
    try:
        result = demo_config_driven_dimensions()
        if not result:
            print("\n✗ Configuration demo failed")
            return
        
        app, db, dimensions, embedding_manager, dimension_loader = result
        
        # Demo 2: Unlimited dimension loading  
        if dimensions:
            success = demo_unlimited_dimension_loading(dimensions, embedding_manager, dimension_loader)
            
            if success:
                # Demo 3: Semantic search
                demo_semantic_search(embedding_manager)
        
        # Demo 4: Dictionary table configuration
        demo_dictionary_table_config()
        
        # Show final stats
        print("\n" + "="*80)
        print("📊 Final Embedding Statistics:")
        print("="*80)
        stats = embedding_manager.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        print(f"\n✅ Demo complete!")
        print("🎯 Key improvements demonstrated:")
        print("   • Config-driven dimensions (is_dimension: true)")
        print("   • Unlimited value loading (no artificial limits)")
        print("   • Linked dimensions in column definitions")
        print("   • Dictionary table support ready")
        
    except Exception as e:
        print(f"\n✗ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()