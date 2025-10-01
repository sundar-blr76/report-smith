"""
MCP Tools for query analysis.

These tools are designed to be used with LangChain agents for:
- Entity identification
- Relationship discovery
- Context extraction
- Filter identification
- Graph navigation
"""

from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from ..schema_intelligence.embedding_manager import EmbeddingManager, SearchResult
from ..logger import get_logger
from .models import (
    EntityInfo,
    RelationshipInfo,
    FilterInfo,
    ContextInfo,
    NavigationPath,
    EntityType,
    FilterType,
    ConfidenceLevel,
    ConfidenceScore,
)

logger = get_logger(__name__)


class BaseMCPTool(ABC):
    """Base class for MCP tools."""
    
    def __init__(self, embedding_manager: EmbeddingManager, config: Optional[Dict[str, Any]] = None):
        self.embedding_manager = embedding_manager
        self.config = config or {}
        self.app_id = self.config.get("app_id", "fund_accounting")
    
    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Execute the tool."""
        pass
    
    def _calculate_confidence(self, score: float, reasoning: str = "") -> ConfidenceScore:
        """Calculate confidence based on score."""
        if score >= 0.8:
            level = ConfidenceLevel.HIGH
        elif score >= 0.6:
            level = ConfidenceLevel.MEDIUM
        else:
            level = ConfidenceLevel.LOW
        
        return ConfidenceScore(
            level=level,
            score=score,
            reasoning=reasoning or f"Score: {score:.2f}"
        )


class EntityIdentificationTool(BaseMCPTool):
    """Tool for identifying entities (tables, columns, dimension values) from natural language."""
    
    def execute(self, query: str, top_k: int = 10) -> List[EntityInfo]:
        """
        Identify relevant entities from the query.
        
        Args:
            query: Natural language query
            top_k: Number of results to return
            
        Returns:
            List of identified entities
        """
        logger.info(f"Identifying entities for query: {query}")
        
        entities = []
        
        # Search schema metadata
        schema_results = self.embedding_manager.search_schema(
            query=query,
            app_id=self.app_id,
            top_k=top_k
        )
        
        for result in schema_results:
            entity_type = self._determine_entity_type(result.metadata)
            entity = EntityInfo(
                name=result.metadata.get("full_path", result.metadata.get("table_name", "unknown")),
                entity_type=entity_type,
                table_name=result.metadata.get("table_name"),
                column_name=result.metadata.get("column_name"),
                description=result.metadata.get("description", ""),
                relevance_score=result.score,
                metadata=result.metadata
            )
            entities.append(entity)
        
        # Search dimension values
        try:
            dimension_results = self.embedding_manager.search_dimensions(
                query=query,
                app_id=self.app_id,
                top_k=5
            )
            
            for result in dimension_results:
                entity = EntityInfo(
                    name=f"{result.metadata.get('full_path', 'unknown')}={result.metadata.get('value', '')}",
                    entity_type=EntityType.DIMENSION_VALUE,
                    table_name=result.metadata.get("table_name"),
                    column_name=result.metadata.get("column_name"),
                    description=f"Dimension value: {result.metadata.get('value', '')}",
                    relevance_score=result.score,
                    metadata=result.metadata
                )
                entities.append(entity)
        except Exception as e:
            logger.warning(f"Could not search dimensions: {e}")
        
        # Sort by relevance
        entities.sort(key=lambda x: x.relevance_score, reverse=True)
        
        logger.info(f"Identified {len(entities)} entities")
        return entities[:top_k]
    
    def _determine_entity_type(self, metadata: Dict[str, Any]) -> EntityType:
        """Determine entity type from metadata."""
        if metadata.get("column_name"):
            return EntityType.COLUMN
        elif metadata.get("table_name"):
            return EntityType.TABLE
        else:
            return EntityType.METRIC


class RelationshipDiscoveryTool(BaseMCPTool):
    """Tool for discovering relationships between entities."""
    
    def __init__(self, embedding_manager: EmbeddingManager, config: Optional[Dict[str, Any]] = None):
        super().__init__(embedding_manager, config)
        self.relationships_cache: Dict[str, List[RelationshipInfo]] = {}
    
    def execute(self, tables: List[str], config: Optional[Dict[str, Any]] = None) -> List[RelationshipInfo]:
        """
        Discover relationships between tables.
        
        Args:
            tables: List of table names
            config: Optional configuration (should include 'relationships' from app.yaml)
            
        Returns:
            List of relationships
        """
        logger.info(f"Discovering relationships for tables: {tables}")
        
        relationships = []
        
        # Use provided config or self.config
        app_config = config or self.config
        relationship_defs = app_config.get("relationships", [])
        
        for rel_def in relationship_defs:
            parent_table = rel_def.get("parent", "").split(".")[0]
            child_table = rel_def.get("child", "").split(".")[0]
            
            # Check if relationship is relevant to our tables
            if parent_table in tables or child_table in tables:
                parent_col = rel_def.get("parent", "").split(".")[-1]
                child_col = rel_def.get("child", "").split(".")[-1]
                
                relationship = RelationshipInfo(
                    name=rel_def.get("name", f"{parent_table}_{child_table}"),
                    parent_table=parent_table,
                    parent_column=parent_col,
                    child_table=child_table,
                    child_column=child_col,
                    relationship_type=rel_def.get("type", "one_to_many"),
                    confidence=ConfidenceScore(
                        level=ConfidenceLevel.HIGH,
                        score=1.0,
                        reasoning="Defined in application schema"
                    )
                )
                relationships.append(relationship)
        
        logger.info(f"Discovered {len(relationships)} relationships")
        return relationships


class ContextExtractionTool(BaseMCPTool):
    """Tool for extracting business context and identifying metrics."""
    
    def execute(self, query: str, entities: List[EntityInfo]) -> ContextInfo:
        """
        Extract business context from query.
        
        Args:
            query: Natural language query
            entities: List of identified entities
            
        Returns:
            Context information
        """
        logger.info(f"Extracting context for query: {query}")
        
        context = ContextInfo()
        
        # Search business context
        try:
            business_results = self.embedding_manager.search_business_context(
                query=query,
                app_id=self.app_id,
                top_k=3
            )
            
            for result in business_results:
                metric_name = result.metadata.get("metric_name")
                if metric_name:
                    context.metric_name = metric_name
                    context.formula = result.metadata.get("formula")
                
                rules = result.metadata.get("business_rules", [])
                if rules:
                    context.business_rules.extend(rules)
        except Exception as e:
            logger.warning(f"Could not search business context: {e}")
        
        # Identify aggregations from query
        query_lower = query.lower()
        if any(word in query_lower for word in ["sum", "total", "aggregate"]):
            from .models import AggregationType
            context.aggregations.append(AggregationType.SUM)
        if any(word in query_lower for word in ["average", "avg", "mean"]):
            from .models import AggregationType
            context.aggregations.append(AggregationType.AVG)
        if any(word in query_lower for word in ["count", "number of", "how many"]):
            from .models import AggregationType
            context.aggregations.append(AggregationType.COUNT)
        if any(word in query_lower for word in ["group by", "by", "per"]):
            from .models import AggregationType
            context.aggregations.append(AggregationType.GROUP_BY)
        
        # Extract temporal context
        temporal_keywords = ["last", "this", "previous", "current", "month", "quarter", "year", "week", "day"]
        if any(word in query_lower for word in temporal_keywords):
            # Extract temporal phrase
            words = query.split()
            for i, word in enumerate(words):
                if word.lower() in temporal_keywords:
                    context.temporal_context = " ".join(words[max(0, i-1):min(len(words), i+3)])
                    break
        
        logger.info(f"Extracted context: {context}")
        return context


class FilterIdentificationTool(BaseMCPTool):
    """Tool for identifying filter conditions from natural language."""
    
    def execute(self, query: str, entities: List[EntityInfo]) -> List[FilterInfo]:
        """
        Identify filter conditions from query.
        
        Args:
            query: Natural language query
            entities: List of identified entities
            
        Returns:
            List of filter conditions
        """
        logger.info(f"Identifying filters for query: {query}")
        
        filters = []
        query_lower = query.lower()
        
        # Look for dimension values as filters
        for entity in entities:
            if entity.entity_type == EntityType.DIMENSION_VALUE:
                value = entity.metadata.get("value")
                if value and entity.table_name and entity.column_name:
                    filter_info = FilterInfo(
                        filter_type=FilterType.EQUALITY,
                        column=entity.column_name,
                        table=entity.table_name,
                        value=value,
                        operator="=",
                        confidence=self._calculate_confidence(
                            entity.relevance_score,
                            f"Dimension value found: {value}"
                        ),
                        original_text=value
                    )
                    filters.append(filter_info)
        
        # Identify temporal filters
        if "last" in query_lower or "previous" in query_lower:
            for entity in entities:
                if entity.column_name and "date" in entity.column_name.lower():
                    filter_info = FilterInfo(
                        filter_type=FilterType.TEMPORAL,
                        column=entity.column_name,
                        table=entity.table_name or "",
                        value=None,  # Will be determined later
                        operator=">=",
                        confidence=self._calculate_confidence(0.7, "Temporal keyword detected"),
                        original_text="last/previous period"
                    )
                    filters.append(filter_info)
                    break
        
        # Identify range filters
        if "top" in query_lower or "bottom" in query_lower:
            # Extract number
            import re
            match = re.search(r'\b(top|bottom)\s+(\d+)\b', query_lower)
            if match:
                limit_value = int(match.group(2))
                # This is actually a LIMIT clause, not a WHERE filter
                # But we'll track it as metadata
                logger.info(f"Identified limit clause: {limit_value}")
        
        logger.info(f"Identified {len(filters)} filters")
        return filters


class GraphNavigationTool(BaseMCPTool):
    """Tool for navigating the entity relationship graph."""
    
    def execute(
        self,
        start_tables: List[str],
        target_tables: List[str],
        relationships: List[RelationshipInfo],
        max_hops: int = 3
    ) -> List[NavigationPath]:
        """
        Find paths through the relationship graph.
        
        Args:
            start_tables: Starting tables
            target_tables: Target tables to reach
            relationships: Available relationships
            max_hops: Maximum number of joins allowed
            
        Returns:
            List of navigation paths
        """
        logger.info(f"Finding paths from {start_tables} to {target_tables}")
        
        # Build adjacency graph
        graph: Dict[str, List[tuple]] = {}
        for rel in relationships:
            if rel.parent_table not in graph:
                graph[rel.parent_table] = []
            if rel.child_table not in graph:
                graph[rel.child_table] = []
            
            graph[rel.parent_table].append((rel.child_table, rel))
            graph[rel.child_table].append((rel.parent_table, rel))
        
        # Find all paths
        all_paths = []
        for start in start_tables:
            for target in target_tables:
                if start == target:
                    continue
                paths = self._find_paths(start, target, graph, max_hops)
                all_paths.extend(paths)
        
        logger.info(f"Found {len(all_paths)} navigation paths")
        return all_paths
    
    def _find_paths(
        self,
        start: str,
        target: str,
        graph: Dict[str, List[tuple]],
        max_hops: int
    ) -> List[NavigationPath]:
        """Find all paths between start and target using BFS."""
        from collections import deque
        
        paths = []
        queue = deque([(start, [start], [])])  # (current, path, relationships)
        
        while queue:
            current, path, rels = queue.popleft()
            
            if len(path) > max_hops + 1:
                continue
            
            if current == target:
                # Found a path
                nav_path = NavigationPath(
                    tables=path,
                    relationships=rels,
                    joins=self._generate_joins(rels),
                    confidence=self._calculate_confidence(
                        1.0 / len(path),  # Shorter paths are better
                        f"Path found with {len(rels)} joins"
                    )
                )
                paths.append(nav_path)
                continue
            
            if current not in graph:
                continue
            
            for next_table, rel in graph[current]:
                if next_table not in path:  # Avoid cycles
                    queue.append((next_table, path + [next_table], rels + [rel]))
        
        return paths
    
    def _generate_joins(self, relationships: List[RelationshipInfo]) -> List[str]:
        """Generate JOIN clauses from relationships."""
        joins = []
        for rel in relationships:
            join_clause = (
                f"JOIN {rel.child_table} ON "
                f"{rel.parent_table}.{rel.parent_column} = "
                f"{rel.child_table}.{rel.child_column}"
            )
            joins.append(join_clause)
        return joins
