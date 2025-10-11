#!/usr/bin/env python3
"""
Knowledge Graph Demo

Demonstrates the schema knowledge graph capabilities:
1. Building graph from schema configuration
2. Finding paths between tables
3. Generating SQL JOIN paths
4. Visualizing relationships

Run:
    cd examples
    ./run_knowledge_graph_demo.sh
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reportsmith.config_system.config_loader import ConfigurationManager
from reportsmith.schema_intelligence import (
    build_knowledge_graph,
    SchemaKnowledgeGraph
)
from reportsmith.logger import get_logger

logger = get_logger(__name__)


def print_header(title):
    """Print a formatted header."""
    print("\n" + "="*80)
    print(title)
    print("="*80 + "\n")


def print_section(title):
    """Print a section header."""
    print(f"\n{'─'*80}")
    print(f"{title}")
    print(f"{'─'*80}\n")


def demo_build_graph(schema_config):
    """Demonstrate building the knowledge graph."""
    print_header("DEMO 1: Building Knowledge Graph from Schema")
    
    print("Building graph from schema configuration...")
    graph = build_knowledge_graph(schema_config)
    
    stats = graph.get_stats()
    
    print(f"✓ Graph built successfully!\n")
    print(f"Statistics:")
    print(f"  • Total nodes: {stats['total_nodes']}")
    print(f"  • Table nodes: {stats['table_nodes']}")
    print(f"  • Column nodes: {stats['column_nodes']}")
    print(f"  • Total relationships: {stats['total_edges']}")
    print(f"  • Avg connections per node: {stats['avg_connections_per_node']:.2f}")
    
    print(f"\nRelationship types:")
    for rel_type, count in stats['relationship_types'].items():
        print(f"  • {rel_type}: {count}")
    
    return graph


def demo_find_paths(graph: SchemaKnowledgeGraph):
    """Demonstrate finding paths between tables."""
    print_header("DEMO 2: Finding Paths Between Tables")
    
    test_cases = [
        ("clients", "transactions", "Direct relationship path"),
        ("clients", "funds", "Multi-hop path"),
        ("management_companies", "transactions", "Complex join path"),
        ("clients", "fund_managers", "Longest path"),
    ]
    
    for from_table, to_table, description in test_cases:
        print_section(f"Finding path: {from_table} → {to_table}")
        print(f"Description: {description}\n")
        
        # Find shortest path
        path = graph.find_shortest_path(from_table, to_table)
        
        if path:
            print(f"✓ Found path (length={path.length}):")
            print(f"  {path}\n")
            
            print(f"Detailed path:")
            for i, node in enumerate(path.nodes):
                if i > 0:
                    edge = path.edges[i-1]
                    print(f"    ↓ ({edge.relationship_type.value})")
                    if edge.from_column and edge.to_column:
                        print(f"      ON {path.nodes[i-1].name}.{edge.from_column} = {node.name}.{edge.to_column}")
                print(f"  {i+1}. {node.name}")
            
            # Generate SQL joins
            join_sql = graph.get_join_path_sql(path)
            if join_sql:
                print(f"\nGenerated SQL JOINs:")
                print(f"  FROM {path.nodes[0].name}")
                for join in join_sql:
                    print(f"  {join}")
        else:
            print(f"✗ No path found between {from_table} and {to_table}")


def demo_all_paths(graph: SchemaKnowledgeGraph):
    """Demonstrate finding all paths between tables."""
    print_header("DEMO 3: Finding All Paths (Multiple Routes)")
    
    from_table = "clients"
    to_table = "funds"
    
    print(f"Finding all paths: {from_table} → {to_table}")
    print(f"(Maximum depth: 5)\n")
    
    all_paths = graph.find_all_paths(from_table, to_table, max_depth=5)
    
    if all_paths:
        print(f"✓ Found {len(all_paths)} different paths:\n")
        
        for i, path in enumerate(all_paths[:5], 1):  # Show first 5
            print(f"Path {i} (length={path.length}):")
            route = " → ".join([node.name for node in path.nodes])
            print(f"  {route}\n")
        
        if len(all_paths) > 5:
            print(f"... and {len(all_paths) - 5} more paths")
        
        # Compare shortest vs alternative paths
        print(f"\n📊 Path Analysis:")
        print(f"  • Shortest path: {all_paths[0].length} hops")
        print(f"  • Longest path: {all_paths[-1].length} hops")
        print(f"  • Average path length: {sum(p.length for p in all_paths) / len(all_paths):.1f} hops")
    else:
        print(f"✗ No paths found")


def demo_table_relationships(graph: SchemaKnowledgeGraph):
    """Demonstrate getting relationships for a specific table."""
    print_header("DEMO 4: Table Relationship Analysis")
    
    tables_to_analyze = ["clients", "accounts", "funds"]
    
    for table_name in tables_to_analyze:
        print_section(f"Relationships for: {table_name}")
        
        relationships = graph.get_table_relationships(table_name)
        
        print(f"Outgoing relationships ({len(relationships['outgoing'])}):")
        for edge in relationships['outgoing']:
            to_node = graph.get_node(edge.to_node)
            print(f"  • {table_name} → {to_node.name if to_node else edge.to_node}")
            print(f"    Type: {edge.relationship_type.value}")
            if edge.from_column and edge.to_column:
                print(f"    Join: {table_name}.{edge.from_column} = {to_node.name if to_node else '?'}.{edge.to_column}")
        
        print(f"\nIncoming relationships ({len(relationships['incoming'])}):")
        for edge in relationships['incoming']:
            from_node = graph.get_node(edge.from_node)
            print(f"  • {from_node.name if from_node else edge.from_node} → {table_name}")
            print(f"    Type: {edge.relationship_type.value}")
            if edge.from_column and edge.to_column:
                print(f"    Join: {from_node.name if from_node else '?'}.{edge.from_column} = {table_name}.{edge.to_column}")


def demo_complex_query_path(graph: SchemaKnowledgeGraph):
    """Demonstrate path finding for the complex query from earlier example."""
    print_header("DEMO 5: Complex Query Join Path Planning")
    
    print("Query: 'Show clients with >$1M in TruePotential funds and their transaction history'\n")
    print("Required tables:")
    required_tables = [
        "clients",
        "accounts", 
        "holdings",
        "funds",
        "management_companies",
        "transactions"
    ]
    
    for table in required_tables:
        print(f"  • {table}")
    
    print("\n" + "─"*80)
    print("Finding optimal join paths...")
    print("─"*80 + "\n")
    
    # Find paths between key table pairs
    paths_to_find = [
        ("clients", "accounts"),
        ("accounts", "holdings"),
        ("holdings", "funds"),
        ("funds", "management_companies"),
        ("accounts", "transactions"),
    ]
    
    print("Join sequence:")
    for i, (from_table, to_table) in enumerate(paths_to_find, 1):
        path = graph.find_shortest_path(from_table, to_table)
        if path and path.length > 0:
            edge = path.edges[0]
            join_type = "INNER JOIN" if i < 5 else "LEFT JOIN"
            print(f"\n{i}. {join_type} {to_table}")
            if edge.from_column and edge.to_column:
                print(f"   ON {from_table}.{edge.from_column} = {to_table}.{edge.to_column}")
            else:
                print(f"   ON {from_table}.id = {to_table}.{from_table}_id")
    
    # Generate complete join path
    print("\n" + "─"*80)
    print("Complete SQL from knowledge graph:")
    print("─"*80 + "\n")
    
    print("SELECT ...")
    print("FROM clients c")
    
    # Use knowledge graph to generate joins
    for i, (from_table, to_table) in enumerate(paths_to_find, 1):
        path = graph.find_shortest_path(from_table, to_table)
        if path:
            joins = graph.get_join_path_sql(path)
            for join in joins:
                # Simplify table names with aliases
                alias_map = {
                    'clients': 'c',
                    'accounts': 'a',
                    'holdings': 'h',
                    'funds': 'f',
                    'management_companies': 'mc',
                    'transactions': 't'
                }
                
                for full_name, alias in alias_map.items():
                    join = join.replace(f" {full_name} ", f" {full_name} {alias} ")
                    join = join.replace(f"{full_name}.", f"{alias}.")
                
                print(join)


def demo_visualization(graph: SchemaKnowledgeGraph):
    """Demonstrate graph visualization."""
    print_header("DEMO 6: Graph Visualization")
    
    print(graph.visualize(max_nodes=15))


def main():
    """Run the knowledge graph demo."""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*18 + "Schema Knowledge Graph Demo" + " "*23 + "║")
    print("╚" + "="*78 + "╝")
    
    print("\n🎯 Demonstrating in-memory knowledge graph for schema relationships")
    print("   Path finding between tables for intelligent JOIN generation\n")
    
    try:
        # Load schema configuration
        project_root = Path(__file__).parent.parent
        config_path = project_root / "config" / "applications"
        
        config_manager = ConfigurationManager(str(config_path))
        applications = config_manager.load_all_applications()
        
        if not applications:
            print("✗ No applications found!")
            return
        
        app = applications[0]
        db = app.databases[0]
        
        # Build schema config
        schema_config = {"tables": {}}
        for table in db.tables:
            schema_config["tables"][table.name] = {
                "description": table.description or "",
                "primary_key": table.primary_key or "",
                "columns": table.columns
            }
        
        print(f"✓ Loaded schema: {app.name}")
        print(f"✓ Database: {db.name} ({len(db.tables)} tables)\n")
        
        # Run demos
        graph = demo_build_graph(schema_config)
        demo_find_paths(graph)
        demo_all_paths(graph)
        demo_table_relationships(graph)
        demo_complex_query_path(graph)
        demo_visualization(graph)
        
        print("\n" + "="*80)
        print("✅ Knowledge Graph Demo Complete!")
        print("="*80)
        print("\n💡 Key Takeaways:")
        print("   • Graph automatically inferred from schema relationships")
        print("   • Bidirectional path finding between any two tables")
        print("   • Multiple path discovery for optimal join selection")
        print("   • Automatic SQL JOIN generation from graph paths")
        print("   • Ready for integration into query generation pipeline\n")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
