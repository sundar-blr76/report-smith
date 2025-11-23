"""
Utility functions for SQL generation.

This module contains helper functions used throughout the SQL generation process.
"""

import re
import difflib
from typing import Any, Dict, List, TYPE_CHECKING

from reportsmith.logger import get_logger

if TYPE_CHECKING:
    from reportsmith.schema_intelligence.knowledge_graph import SchemaKnowledgeGraph

logger = get_logger(__name__)


def normalize_filter_value(value_str: str) -> str:
    """
    Normalize filter values to valid SQL format.

    Handles:
    - Shorthand numeric values: 100M → 100000000, 1.5K → 1500, 2B → 2000000000
    - Already quoted strings: leave as-is
    - Plain numbers: leave as-is

    Args:
        value_str: The value string from filter (e.g., "100M", "'equity'", "2024")

    Returns:
        Normalized SQL-compatible value string
    """
    value_str = value_str.strip()

    # Pattern: number followed by K/M/B/T (thousands, millions, billions, trillions)
    # Handles: 100M, 1.5K, 2B, 0.5M, etc.
    shorthand_pattern = r"^(\d+(?:\.\d+)?)\s*([KMBT])$"
    match = re.match(shorthand_pattern, value_str, re.IGNORECASE)

    if match:
        number = float(match.group(1))
        suffix = match.group(2).upper()

        multipliers = {
            "K": 1_000,
            "M": 1_000_000,
            "B": 1_000_000_000,
            "T": 1_000_000_000_000,
        }

        result = number * multipliers[suffix]

        # Return as integer if it's a whole number, otherwise as float
        if result == int(result):
            normalized = str(int(result))
        else:
            normalized = str(result)

        logger.debug(
            f"[sql-gen][normalize] converted shorthand: {value_str} → {normalized}"
        )
        return normalized

    # Already a valid value (quoted string, number, boolean, etc.)
    return value_str


def normalize_column_reference(
    col_ref: str,
    entities: List[Dict[str, Any]],
    knowledge_graph: "SchemaKnowledgeGraph",
) -> str:
    """
    Normalize column references in filters to use actual table/column names.

    This maps entity text (e.g., "AUM", "customers") to actual schema names
    (e.g., "funds.total_aum", "clients").

    Args:
        col_ref: Column reference from filter (e.g., "AUM", "customers.type", "customer_type")
        entities: List of discovered entities with mappings
        knowledge_graph: Knowledge graph instance for schema lookups

    Returns:
        Normalized column reference (e.g., "funds.total_aum", "clients.client_type")
    """
    # If already in table.column format, check if table needs mapping
    if "." in col_ref:
        table_ref, col_name = col_ref.split(".", 1)

        # Check if table_ref is an entity text that needs mapping
        for ent in entities:
            if ent.get("text", "").lower() == table_ref.lower():
                actual_table = ent.get("table")
                if actual_table:
                    return f"{actual_table}.{col_name}"

        return col_ref

    # Single word reference - could be column name or entity text
    # First, try to find it as an entity text in the entities list
    for ent in entities:
        text = ent.get("text", "").lower()
        entity_type = ent.get("entity_type")

        if text == col_ref.lower():
            if entity_type == "column":
                table = ent.get("table")
                column = ent.get("column")
                if table and column:
                    return f"{table}.{column}"
            elif entity_type == "table":
                # Just return the actual table name
                actual_table = ent.get("table")
                if actual_table:
                    return actual_table

    # Not found in entities - try to find column in knowledge graph
    # This handles cases like "customer_type" → "clients.client_type"
    col_lower = col_ref.lower()

    # Try exact match first
    matching_nodes = []
    for node in knowledge_graph.nodes.values():
        if node.type == "column" and node.name and node.name.lower() == col_lower:
            matching_nodes.append(node)

    # If no exact match, try fuzzy match (e.g., "customer_type" matches "client_type")
    if not matching_nodes:
        # Try removing common prefixes/suffixes and checking similarity
        candidates = []
        for node in knowledge_graph.nodes.values():
            if node.type == "column" and node.name:
                # Check similarity ratio
                ratio = difflib.SequenceMatcher(
                    None, col_lower, node.name.lower()
                ).ratio()
                if ratio > 0.7:  # Increased threshold from 0.5 to 0.7 to avoid bad matches
                    candidates.append((node, ratio))

        # Sort by similarity and take best matches
        candidates.sort(key=lambda x: x[1], reverse=True)
        matching_nodes = [c[0] for c in candidates[:3]]  # Top 3 candidates

    # If we have matches, prefer ones from tables in our entity list
    if matching_nodes:
        # Get tables from entities
        entity_tables = set()
        for ent in entities:
            table = ent.get("table")
            if table:
                entity_tables.add(table)
            # Also check metadata
            md = (ent.get("top_match") or {}).get("metadata") or {}
            table = md.get("table")
            if table:
                entity_tables.add(table)

        # ONLY use columns from tables in our query - don't use fuzzy match from unrelated tables
        for node in matching_nodes:
            if node.table in entity_tables:
                logger.info(
                    f"[sql-gen][normalize] mapped column '{col_ref}' → "
                    f"'{node.table}.{node.name}' (from KG, fuzzy match, confidence={difflib.SequenceMatcher(None, col_lower, node.name.lower()).ratio():.2f})"
                )
                return f"{node.table}.{node.name}"

        # No match in our tables - DON'T use fuzzy match from unrelated tables
        # This prevents bad mappings like portfolio_type → period_type
        logger.warning(
            f"[sql-gen][normalize] Fuzzy match found for '{col_ref}' but not in active query tables. "
            f"Best candidate: {matching_nodes[0].table}.{matching_nodes[0].name} (not used). "
            f"Returning as-is."
        )
        return col_ref

    # No mapping found - return as-is
    logger.warning(
        f"[sql-gen][normalize] could not normalize column reference '{col_ref}', "
        f"using as-is (may cause SQL errors)"
    )
    return col_ref


def detect_llm_provider(llm_client: Any) -> str:
    """Detect which LLM provider is being used"""
    if not llm_client:
        return "none"
    if hasattr(llm_client, "chat") and hasattr(llm_client.chat, "completions"):
        return "openai"
    elif hasattr(llm_client, "messages"):
        return "anthropic"
    else:
        return "gemini"


def detect_llm_model(llm_client: Any) -> str:
    """Detect which LLM model is being used"""
    if not llm_client:
        return "none"

    provider = detect_llm_provider(llm_client)

    # Try to get model from client attributes
    if provider == "openai":
        # OpenAI clients don't store default model, return common default
        return "gpt-4o-mini"
    elif provider == "anthropic":
        return "claude-3-haiku-20240307"
    elif provider == "gemini":
        # Try to get from client
        if hasattr(llm_client, "model_name"):
            return llm_client.model_name
        return "gemini-2.5-flash"

    return "unknown"
