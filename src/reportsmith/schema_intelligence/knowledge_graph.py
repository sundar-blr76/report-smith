"""
Schema Knowledge Graph

In-memory knowledge graph representing table and column relationships from schema.
Enables path finding between any two nodes (tables/columns) for join planning.

Features:
- Graph-based representation of schema relationships
- Foreign key relationship mapping
- Path finding between tables (BFS, DFS, shortest path)
- Relationship type inference
- Bidirectional relationship traversal
"""

from dataclasses import dataclass
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict, deque
from enum import Enum
import logging
import os

logger = logging.getLogger(__name__)
VERBOSE_KG_LOG = os.getenv("RS_KG_VERBOSE", "0").lower() in {"1", "true", "yes", "y"}


class RelationshipType(Enum):
    """Types of relationships in the schema."""
    FOREIGN_KEY = "foreign_key"
    PRIMARY_KEY = "primary_key"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"
    ONE_TO_ONE = "one_to_one"
    MANY_TO_MANY = "many_to_many"


@dataclass
class Node:
    """Represents a node in the knowledge graph (table or column)."""
    id: str  # Unique identifier (table.column or just table)
    type: str  # 'table' or 'column'
    name: str
    table: Optional[str] = None  # Parent table (for columns)
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        return isinstance(other, Node) and self.id == other.id


@dataclass
class Edge:
    """Represents a relationship between two nodes."""
    from_node: str  # Node ID
    to_node: str  # Node ID
    relationship_type: RelationshipType
    from_column: Optional[str] = None
    to_column: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Path:
    """Represents a path between two nodes in the graph."""
    nodes: List[Node]
    edges: List[Edge]
    length: int
    
    def __repr__(self):
        path_str = " → ".join([node.name for node in self.nodes])
        return f"Path(length={self.length}, path={path_str})"


class SchemaKnowledgeGraph:
    """
    In-memory knowledge graph for schema relationships.
    
    Represents tables and columns as nodes, relationships as edges.
    Enables path finding for join planning.
    """
    
    def __init__(self):
        """Initialize an empty knowledge graph."""
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self.adjacency_list: Dict[str, List[Tuple[str, Edge]]] = defaultdict(list)
        self.reverse_adjacency_list: Dict[str, List[Tuple[str, Edge]]] = defaultdict(list)
        
    def add_node(self, node: Node) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node
        if VERBOSE_KG_LOG:
            logger.debug(f"Added node: {node.id} (type: {node.type})")
        
    def add_edge(self, edge: Edge) -> None:
        """Add an edge (relationship) to the graph."""
        self.edges.append(edge)
        
        # Add to adjacency list (forward direction)
        self.adjacency_list[edge.from_node].append((edge.to_node, edge))
        
        # Add to reverse adjacency list (backward direction)
        self.reverse_adjacency_list[edge.to_node].append((edge.from_node, edge))
        
        if VERBOSE_KG_LOG:
            logger.debug(
                f"Added edge: {edge.from_node} → {edge.to_node} "
                f"({edge.relationship_type.value})"
            )
    
    def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node by its ID."""
        return self.nodes.get(node_id)
    
    def get_neighbors(self, node_id: str, bidirectional: bool = True) -> List[Tuple[str, Edge]]:
        """
        Get all neighbors of a node.
        
        Args:
            node_id: Node to get neighbors for
            bidirectional: If True, include both forward and backward edges
            
        Returns:
            List of (neighbor_id, edge) tuples
        """
        neighbors = list(self.adjacency_list.get(node_id, []))
        
        if bidirectional:
            neighbors.extend(self.reverse_adjacency_list.get(node_id, []))
        
        return neighbors
    
    def find_shortest_path(
        self, 
        from_node_id: str, 
        to_node_id: str,
        bidirectional: bool = True
    ) -> Optional[Path]:
        """
        Find the shortest path between two nodes using BFS.
        
        Args:
            from_node_id: Starting node
            to_node_id: Target node
            bidirectional: If True, allow traversal in both directions
            
        Returns:
            Path object or None if no path exists
        """
        if from_node_id not in self.nodes or to_node_id not in self.nodes:
            logger.warning(f"Node not found: {from_node_id} or {to_node_id}")
            return None
        
        if from_node_id == to_node_id:
            return Path(nodes=[self.nodes[from_node_id]], edges=[], length=0)
        
        # BFS
        queue = deque([(from_node_id, [from_node_id], [])])
        visited = {from_node_id}
        
        while queue:
            current_id, path_nodes, path_edges = queue.popleft()
            
            # Get neighbors
            for neighbor_id, edge in self.get_neighbors(current_id, bidirectional):
                if neighbor_id in visited:
                    continue
                
                new_path_nodes = path_nodes + [neighbor_id]
                new_path_edges = path_edges + [edge]
                
                if neighbor_id == to_node_id:
                    # Found the target
                    nodes = [self.nodes[nid] for nid in new_path_nodes]
                    return Path(
                        nodes=nodes,
                        edges=new_path_edges,
                        length=len(new_path_edges)
                    )
                
                visited.add(neighbor_id)
                queue.append((neighbor_id, new_path_nodes, new_path_edges))
        
        # No path found
        logger.info(f"No path found between {from_node_id} and {to_node_id}")
        return None
    
    def find_all_paths(
        self,
        from_node_id: str,
        to_node_id: str,
        max_depth: int = 5,
        bidirectional: bool = True
    ) -> List[Path]:
        """
        Find all paths between two nodes up to a maximum depth.
        
        Args:
            from_node_id: Starting node
            to_node_id: Target node
            max_depth: Maximum path length to search
            bidirectional: If True, allow traversal in both directions
            
        Returns:
            List of Path objects
        """
        if from_node_id not in self.nodes or to_node_id not in self.nodes:
            return []
        
        if from_node_id == to_node_id:
            return [Path(nodes=[self.nodes[from_node_id]], edges=[], length=0)]
        
        all_paths = []
        
        def dfs(current_id: str, path_nodes: List[str], path_edges: List[Edge], visited: Set[str]):
            if len(path_edges) >= max_depth:
                return
            
            if current_id == to_node_id:
                nodes = [self.nodes[nid] for nid in path_nodes]
                all_paths.append(Path(
                    nodes=nodes,
                    edges=list(path_edges),
                    length=len(path_edges)
                ))
                return
            
            for neighbor_id, edge in self.get_neighbors(current_id, bidirectional):
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    dfs(
                        neighbor_id,
                        path_nodes + [neighbor_id],
                        path_edges + [edge],
                        visited
                    )
                    visited.remove(neighbor_id)
        
        dfs(from_node_id, [from_node_id], [], {from_node_id})
        
        # Sort by length (shortest first)
        all_paths.sort(key=lambda p: p.length)
        
        return all_paths
    
    def get_table_relationships(self, table_name: str) -> Dict[str, List[Edge]]:
        """
        Get all relationships involving a specific table.
        
        Returns:
            Dict with 'outgoing' and 'incoming' edges
        """
        table_id = table_name
        
        return {
            'outgoing': [edge for edge in self.edges if edge.from_node == table_id],
            'incoming': [edge for edge in self.edges if edge.to_node == table_id]
        }
    
    def get_join_path_sql(self, path: Path) -> List[str]:
        """
        Convert a path to SQL JOIN clauses.
        
        Args:
            path: Path object from find_shortest_path or find_all_paths
            
        Returns:
            List of SQL JOIN strings
        """
        if not path or len(path.edges) == 0:
            return []
        
        joins = []
        
        for i, edge in enumerate(path.edges):
            from_table = path.nodes[i].name
            to_table = path.nodes[i + 1].name
            
            # Determine join type based on relationship
            if edge.relationship_type == RelationshipType.MANY_TO_ONE:
                join_type = "INNER JOIN"
            elif edge.relationship_type == RelationshipType.ONE_TO_MANY:
                join_type = "LEFT JOIN"
            else:
                join_type = "INNER JOIN"
            
            # Build join condition
            if edge.from_column and edge.to_column:
                join_sql = (
                    f"{join_type} {to_table} "
                    f"ON {from_table}.{edge.from_column} = {to_table}.{edge.to_column}"
                )
            else:
                # Infer from common patterns
                join_sql = f"{join_type} {to_table} ON {from_table}.id = {to_table}.{from_table}_id"
            
            joins.append(join_sql)
        
        return joins
    
    def visualize(self, max_nodes: int = 20) -> str:
        """
        Create a text visualization of the graph.
        
        Args:
            max_nodes: Maximum number of nodes to show
            
        Returns:
            String representation of the graph
        """
        lines = ["Schema Knowledge Graph:", "=" * 60]
        
        # Show nodes
        table_nodes = [n for n in self.nodes.values() if n.type == 'table']
        lines.append(f"\nTables ({len(table_nodes)} nodes):")
        for node in list(table_nodes)[:max_nodes]:
            lines.append(f"  • {node.name}")
        
        if len(table_nodes) > max_nodes:
            lines.append(f"  ... and {len(table_nodes) - max_nodes} more")
        
        # Show relationships
        lines.append(f"\nRelationships ({len(self.edges)} edges):")
        for edge in self.edges[:max_nodes]:
            from_node = self.nodes.get(edge.from_node)
            to_node = self.nodes.get(edge.to_node)
            if from_node and to_node:
                rel_type = edge.relationship_type.value
                lines.append(f"  • {from_node.name} → {to_node.name} ({rel_type})")
        
        if len(self.edges) > max_nodes:
            lines.append(f"  ... and {len(self.edges) - max_nodes} more")
        
        lines.append("\n" + "=" * 60)
        
        return "\n".join(lines)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the graph."""
        table_count = sum(1 for n in self.nodes.values() if n.type == 'table')
        column_count = sum(1 for n in self.nodes.values() if n.type == 'column')
        
        relationship_types = defaultdict(int)
        for edge in self.edges:
            relationship_types[edge.relationship_type.value] += 1
        
        return {
            'total_nodes': len(self.nodes),
            'table_nodes': table_count,
            'column_nodes': column_count,
            'total_edges': len(self.edges),
            'relationship_types': dict(relationship_types),
            'avg_connections_per_node': len(self.edges) * 2 / len(self.nodes) if self.nodes else 0
        }
