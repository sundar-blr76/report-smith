#!/usr/bin/env python3
"""
Demonstration of Entity Refinement with Priority and Optimal Source Selection

This script demonstrates how the entity refinement system prioritizes entities
based on their data source optimality when multiple sources exist for the same data.
"""

import json
import yaml
from pathlib import Path


def demonstrate_entity_priority():
    """Demonstrate how entity priority system works."""
    
    print("=" * 80)
    print("Entity Refinement Priority System - Demonstration")
    print("=" * 80)
    print()
    
    # Scenario: User asks about "total AUM for equity funds"
    query = "What is the total AUM for equity funds?"
    print(f"User Query: {query}")
    print()
    
    # System might identify multiple entities for "AUM"
    print("Entities Detected:")
    print("-" * 80)
    
    entities = [
        {
            "index": 0,
            "text": "aum",
            "type": "column",
            "confidence": 1.0,
            "table": "funds",
            "column": "total_aum",
            "source": "local",
            "priority": "high",
            "optimal_source": True,
            "source_notes": "Primary source for AUM - preferred over aggregating from holdings or positions"
        },
        {
            "index": 1,
            "text": "equity",
            "type": "dimension_value",
            "confidence": 1.0,
            "table": "funds",
            "column": "fund_type",
            "source": "local"
        },
        {
            "index": 2,
            "text": "market_value",
            "type": "column",
            "confidence": 0.7,
            "table": "holdings",
            "column": "market_value",
            "source": "semantic",
            "priority": "low",
            "optimal_source": False,
            "source_notes": "Secondary source - requires SUM aggregation across holdings; prefer funds.total_aum for overall AUM"
        },
        {
            "index": 3,
            "text": "total_aum",
            "type": "column",
            "confidence": 0.6,
            "table": "performance_reports",
            "column": "total_aum",
            "source": "semantic",
            "priority": "low",
            "optimal_source": False,
            "source_notes": "Historical snapshot - prefer funds.total_aum for current AUM values"
        }
    ]
    
    for entity in entities:
        print(f"\nEntity #{entity['index']}:")
        print(f"  Text: {entity['text']}")
        print(f"  Type: {entity['type']}")
        print(f"  Source: {entity['source']} (confidence: {entity['confidence']})")
        print(f"  Location: {entity['table']}.{entity.get('column', 'N/A')}")
        if "priority" in entity:
            priority_emoji = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(entity["priority"], "⚪")
            print(f"  Priority: {priority_emoji} {entity['priority']}")
        if "optimal_source" in entity:
            optimal_emoji = "✅" if entity["optimal_source"] else "⚠️"
            print(f"  Optimal Source: {optimal_emoji} {entity['optimal_source']}")
        if "source_notes" in entity:
            print(f"  Notes: {entity['source_notes']}")
    
    print()
    print("-" * 80)
    print()
    
    # LLM Refinement Process
    print("LLM Refinement Process:")
    print("-" * 80)
    print()
    print("The LLM evaluates entities based on:")
    print("  1. ✅ Optimal source flag (prefer True)")
    print("  2. 🟢 Priority level (high > medium > low)")
    print("  3. 📝 Source notes context")
    print("  4. 🎯 Source type (local > llm > semantic)")
    print()
    
    # Selection Decision
    print("Selection Decision:")
    print("-" * 80)
    print()
    
    keep_indices = [0, 1]  # Keep funds.total_aum and equity
    drop_indices = [2, 3]  # Drop holdings.market_value and performance_reports.total_aum
    
    reasoning = (
        "Kept entity #0 (funds.total_aum) as it's marked optimal_source=true with high priority "
        "and provides direct access to AUM. Kept entity #1 (equity) for filtering. "
        "Dropped entities #2 and #3 as they are redundant, lower priority alternatives: "
        "#2 requires aggregation from holdings (less efficient), "
        "#3 provides historical snapshots rather than current values."
    )
    
    print(f"Keep Indices: {keep_indices}")
    print()
    print(f"Reasoning: {reasoning}")
    print()
    
    print("Entities Kept:")
    for idx in keep_indices:
        entity = entities[idx]
        print(f"  ✅ #{idx}: {entity['table']}.{entity.get('column', entity['text'])} ({entity['type']})")
    
    print()
    print("Entities Dropped:")
    for idx in drop_indices:
        entity = entities[idx]
        reason = "lower priority, redundant" if "priority" in entity and entity["priority"] == "low" else "redundant"
        print(f"  ❌ #{idx}: {entity['table']}.{entity.get('column', entity['text'])} ({reason})")
    
    print()
    print("-" * 80)
    print()
    
    # Final Query Plan
    print("Final Query Plan:")
    print("-" * 80)
    print()
    print("SELECT SUM(total_aum)")
    print("FROM funds")
    print("WHERE fund_type = 'Equity Growth'")
    print("  AND is_active = true")
    print()
    print("Benefits:")
    print("  ✓ Uses direct AUM column (no aggregation needed)")
    print("  ✓ Single table query (no joins required)")
    print("  ✓ Current values (not historical snapshots)")
    print("  ✓ Optimal performance and accuracy")
    print()
    
    print("=" * 80)
    print()


def load_and_display_mappings():
    """Load and display entity mappings with priorities."""
    
    print("=" * 80)
    print("Entity Mappings Configuration")
    print("=" * 80)
    print()
    
    mappings_file = Path(__file__).parent.parent / "config" / "entity_mappings.yaml"
    
    if not mappings_file.exists():
        print(f"❌ Entity mappings file not found: {mappings_file}")
        return
    
    with open(mappings_file, 'r') as f:
        data = yaml.safe_load(f)
    
    print("AUM-Related Column Mappings:")
    print("-" * 80)
    print()
    
    aum_columns = [
        ("aum", "Primary AUM Source"),
        ("aum_from_holdings", "Alternative: From Holdings"),
        ("aum_from_performance", "Alternative: From Performance Reports")
    ]
    
    for key, label in aum_columns:
        if key in data.get("columns", {}):
            mapping = data["columns"][key]
            print(f"{label}:")
            print(f"  Key: {key}")
            print(f"  Table: {mapping.get('table')}")
            print(f"  Column: {mapping.get('column')}")
            print(f"  Priority: {mapping.get('priority', 'not set')}")
            print(f"  Optimal Source: {mapping.get('optimal_source', False)}")
            print(f"  Source Notes: {mapping.get('source_notes', 'N/A')}")
            print()
    
    print("=" * 80)
    print()


if __name__ == "__main__":
    demonstrate_entity_priority()
    load_and_display_mappings()
