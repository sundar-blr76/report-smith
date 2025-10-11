"""
Schema Knowledge Graph Builder

Builds a knowledge graph from schema configuration by:
1. Parsing table and column definitions
2. Identifying foreign key relationships
3. Inferring relationship types
4. Creating graph nodes and edges
"""

from typing import Dict, List, Any, Optional
import re
import logging

from .knowledge_graph import (
    SchemaKnowledgeGraph,
    Node,
    Edge,
    RelationshipType
)

logger = logging.getLogger(__name__)


class KnowledgeGraphBuilder:
    """Builds a knowledge graph from schema configuration."""
    
    def __init__(self):
        """Initialize the builder."""
        self.graph = SchemaKnowledgeGraph()
        
    def build_from_schema(self, schema_config: Dict[str, Any]) -> SchemaKnowledgeGraph:
        """
        Build a knowledge graph from schema configuration.
        
        Args:
            schema_config: Schema configuration dict with tables
            
        Returns:
            Populated SchemaKnowledgeGraph
        """
        tables = schema_config.get('tables', {})
        
        logger.info(f"Building knowledge graph from {len(tables)} tables")
        
        # Step 1: Add table nodes
        for table_name, table_def in tables.items():
            self._add_table_node(table_name, table_def)
        
        # Step 2: Add column nodes and identify relationships
        for table_name, table_def in tables.items():
            self._add_column_nodes(table_name, table_def)
        
        # Step 3: Identify and add foreign key relationships
        for table_name, table_def in tables.items():
            self._add_foreign_key_relationships(table_name, table_def, tables)
        
        stats = self.graph.get_stats()
        logger.info(
            f"Knowledge graph built: {stats['table_nodes']} tables, "
            f"{stats['total_edges']} relationships"
        )
        
        return self.graph
    
    def _add_table_node(self, table_name: str, table_def: Dict[str, Any]) -> None:
        """Add a table node to the graph."""
        node = Node(
            id=table_name,
            type='table',
            name=table_name,
            metadata={
                'description': table_def.get('description', ''),
                'primary_key': table_def.get('primary_key', ''),
                'indexes': table_def.get('indexes', [])
            }
        )
        self.graph.add_node(node)
    
    def _add_column_nodes(self, table_name: str, table_def: Dict[str, Any]) -> None:
        """Add column nodes for a table."""
        columns = table_def.get('columns', {})
        
        for column_name, column_def in columns.items():
            node = Node(
                id=f"{table_name}.{column_name}",
                type='column',
                name=column_name,
                table=table_name,
                metadata={
                    'data_type': column_def.get('type', ''),
                    'description': column_def.get('description', ''),
                    'nullable': column_def.get('nullable', True),
                    'is_dimension': column_def.get('is_dimension', False)
                }
            )
            self.graph.add_node(node)
    
    def _add_foreign_key_relationships(
        self,
        table_name: str,
        table_def: Dict[str, Any],
        all_tables: Dict[str, Any]
    ) -> None:
        """Identify and add foreign key relationships."""
        columns = table_def.get('columns', {})
        
        for column_name, column_def in columns.items():
            # Check for explicit foreign key definition
            fk_table, fk_column = self._parse_foreign_key(column_def, all_tables)
            
            if not fk_table:
                # Try to infer from naming patterns
                fk_table, fk_column = self._infer_foreign_key(
                    table_name, column_name, all_tables
                )
            
            if fk_table and fk_table in all_tables:
                # Add foreign key relationship
                self._add_relationship(
                    from_table=table_name,
                    to_table=fk_table,
                    from_column=column_name,
                    to_column=fk_column,
                    relationship_type=RelationshipType.MANY_TO_ONE
                )
                
                # Add reverse relationship (ONE_TO_MANY)
                self._add_relationship(
                    from_table=fk_table,
                    to_table=table_name,
                    from_column=fk_column,
                    to_column=column_name,
                    relationship_type=RelationshipType.ONE_TO_MANY
                )
    
    def _parse_foreign_key(
        self,
        column_def: Dict[str, Any],
        all_tables: Dict[str, Any]
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Parse explicit foreign key definition from column.
        
        Looks for patterns like:
        - description: "FK to clients"
        - description: "Foreign key to clients.client_id"
        """
        description = column_def.get('description', '')
        
        # Pattern: "FK to <table>" or "Foreign key to <table>"
        fk_pattern = r'FK\s+to\s+(\w+)|Foreign\s+key\s+to\s+(\w+)'
        match = re.search(fk_pattern, description, re.IGNORECASE)
        
        if match:
            table_name = match.group(1) or match.group(2)
            if table_name in all_tables:
                # Try to determine the referenced column
                pk = all_tables[table_name].get('primary_key', 'id')
                return table_name, pk
        
        # Pattern: "FK to <table>.<column>"
        fk_pattern2 = r'FK\s+to\s+(\w+)\.(\w+)|Foreign\s+key\s+to\s+(\w+)\.(\w+)'
        match = re.search(fk_pattern2, description, re.IGNORECASE)
        
        if match:
            table_name = match.group(1) or match.group(3)
            column_name = match.group(2) or match.group(4)
            if table_name in all_tables:
                return table_name, column_name
        
        return None, None
    
    def _infer_foreign_key(
        self,
        table_name: str,
        column_name: str,
        all_tables: Dict[str, Any]
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Infer foreign key relationships from naming patterns.
        
        Patterns:
        - <table>_id → references <table>.id
        - <singular>_id → references <plural>.id (e.g., client_id → clients.id)
        """
        # Pattern 1: exact table name + _id
        if column_name.endswith('_id'):
            potential_table = column_name[:-3]  # Remove '_id'
            
            # Try exact match
            if potential_table in all_tables:
                pk = all_tables[potential_table].get('primary_key', 'id')
                return potential_table, pk
            
            # Try plural form (simple: add 's')
            potential_table_plural = potential_table + 's'
            if potential_table_plural in all_tables:
                pk = all_tables[potential_table_plural].get('primary_key', 'id')
                return potential_table_plural, pk
            
            # Try removing 's' (singular to plural)
            if potential_table.endswith('s'):
                potential_table_singular = potential_table[:-1]
                if potential_table_singular in all_tables:
                    pk = all_tables[potential_table_singular].get('primary_key', 'id')
                    return potential_table_singular, pk
        
        return None, None
    
    def _add_relationship(
        self,
        from_table: str,
        to_table: str,
        from_column: Optional[str],
        to_column: Optional[str],
        relationship_type: RelationshipType
    ) -> None:
        """Add a relationship edge to the graph."""
        edge = Edge(
            from_node=from_table,
            to_node=to_table,
            relationship_type=relationship_type,
            from_column=from_column,
            to_column=to_column,
            metadata={
                'inferred': True  # Mark as inferred (vs. explicit in schema)
            }
        )
        self.graph.add_edge(edge)


def build_knowledge_graph(schema_config: Dict[str, Any]) -> SchemaKnowledgeGraph:
    """
    Convenience function to build a knowledge graph from schema config.
    
    Args:
        schema_config: Schema configuration with tables
        
    Returns:
        Populated SchemaKnowledgeGraph
    """
    builder = KnowledgeGraphBuilder()
    return builder.build_from_schema(schema_config)
