"""
LangChain-based Query Orchestrator.

Orchestrates the query analysis process using MCP tools:
1. Entity identification
2. Relationship discovery
3. Context extraction
4. Filter identification
5. Graph navigation
6. Result validation and refinement
7. SQL query generation
"""

from typing import Dict, List, Optional, Any
from ..schema_intelligence.embedding_manager import EmbeddingManager
from ..logger import get_logger
from .mcp_tools import (
    EntityIdentificationTool,
    RelationshipDiscoveryTool,
    ContextExtractionTool,
    FilterIdentificationTool,
    GraphNavigationTool,
)
from .models import (
    QueryAnalysisResult,
    QueryPlan,
    EntityInfo,
    EntityType,
    ConfidenceLevel,
    ConfidenceScore,
)

logger = get_logger(__name__)


class QueryOrchestrator:
    """
    Orchestrates the query analysis and SQL generation process.
    
    Uses a set of MCP tools to:
    - Identify entities, relationships, context, and filters
    - Navigate the entity graph
    - Validate and refine results
    - Generate SQL query plans
    """
    
    def __init__(
        self,
        embedding_manager: EmbeddingManager,
        app_config: Optional[Dict[str, Any]] = None,
        max_refinement_iterations: int = 3
    ):
        """
        Initialize the orchestrator.
        
        Args:
            embedding_manager: EmbeddingManager instance for semantic search
            app_config: Application configuration (relationships, metrics, etc.)
            max_refinement_iterations: Maximum number of refinement iterations
        """
        self.embedding_manager = embedding_manager
        self.app_config = app_config or {}
        self.max_refinement_iterations = max_refinement_iterations
        
        # Initialize MCP tools
        tool_config = {
            "app_id": self.app_config.get("application", {}).get("id", "fund_accounting"),
            "relationships": self.app_config.get("relationships", []),
        }
        
        self.entity_tool = EntityIdentificationTool(embedding_manager, tool_config)
        self.relationship_tool = RelationshipDiscoveryTool(embedding_manager, tool_config)
        self.context_tool = ContextExtractionTool(embedding_manager, tool_config)
        self.filter_tool = FilterIdentificationTool(embedding_manager, tool_config)
        self.navigation_tool = GraphNavigationTool(embedding_manager, tool_config)
        
        logger.info("Initialized QueryOrchestrator")
    
    def analyze_query(self, user_query: str) -> QueryAnalysisResult:
        """
        Analyze a natural language query.
        
        Args:
            user_query: Natural language query from user
            
        Returns:
            QueryAnalysisResult with entities, relationships, filters, and context
        """
        logger.info(f"Analyzing query: {user_query}")
        
        iteration = 0
        best_analysis = None
        
        while iteration < self.max_refinement_iterations:
            iteration += 1
            logger.info(f"Analysis iteration {iteration}")
            
            # Step 1: Identify entities
            entities = self.entity_tool.execute(query=user_query, top_k=10)
            logger.info(f"Identified {len(entities)} entities")
            
            # Step 2: Extract context
            context = self.context_tool.execute(query=user_query, entities=entities)
            logger.info(f"Extracted context: {context}")
            
            # Step 3: Identify filters
            filters = self.filter_tool.execute(query=user_query, entities=entities)
            logger.info(f"Identified {len(filters)} filters")
            
            # Step 4: Get relevant tables
            tables = self._extract_tables(entities)
            logger.info(f"Relevant tables: {tables}")
            
            # Step 5: Discover relationships
            relationships = self.relationship_tool.execute(
                tables=tables,
                config=self.app_config
            )
            logger.info(f"Discovered {len(relationships)} relationships")
            
            # Step 6: Navigate graph
            navigation_paths = self._find_navigation_paths(tables, relationships)
            logger.info(f"Found {len(navigation_paths)} navigation paths")
            
            # Step 7: Calculate confidence
            confidence = self._calculate_analysis_confidence(
                entities, relationships, filters, navigation_paths
            )
            
            # Create analysis result
            analysis = QueryAnalysisResult(
                user_query=user_query,
                entities=entities,
                relationships=relationships,
                filters=filters,
                context=context,
                navigation_paths=navigation_paths,
                confidence=confidence,
                iteration_count=iteration
            )
            
            # Check if we should refine
            if confidence.level == ConfidenceLevel.HIGH:
                logger.info("High confidence achieved, stopping refinement")
                return analysis
            
            # Store best analysis
            if best_analysis is None or confidence.score > best_analysis.confidence.score:
                best_analysis = analysis
            
            # Generate refinement suggestions
            refinement_suggestions = self._generate_refinement_suggestions(analysis)
            analysis.refinement_suggestions = refinement_suggestions
            
            if not refinement_suggestions:
                logger.info("No refinement suggestions, stopping")
                break
            
            logger.info(f"Refinement suggestions: {refinement_suggestions}")
        
        logger.info(f"Analysis complete after {iteration} iterations")
        return best_analysis or analysis
    
    def generate_query_plan(self, analysis: QueryAnalysisResult) -> QueryPlan:
        """
        Generate SQL query plan from analysis results.
        
        Args:
            analysis: Query analysis result
            
        Returns:
            QueryPlan with SQL generation details
        """
        logger.info("Generating query plan")
        
        # Identify primary table (most relevant entity)
        primary_table = self._identify_primary_table(analysis.entities)
        logger.info(f"Primary table: {primary_table}")
        
        # Collect all required tables
        required_tables = list(set([primary_table] + [
            e.table_name for e in analysis.entities
            if e.table_name and e.entity_type in [EntityType.TABLE, EntityType.COLUMN]
        ]))
        
        # Select columns
        selected_columns = self._select_columns(analysis.entities, analysis.context)
        
        # Generate JOIN clauses
        join_clauses = self._generate_join_clauses(
            primary_table, required_tables, analysis.navigation_paths
        )
        
        # Generate WHERE clauses
        where_clauses = self._generate_where_clauses(analysis.filters)
        
        # Generate GROUP BY clauses
        group_by_clauses = []
        if analysis.context.grouping_columns:
            group_by_clauses = analysis.context.grouping_columns
        
        # Generate ORDER BY clauses
        order_by_clauses = self._generate_order_by_clauses(analysis.user_query, analysis.entities)
        
        # Generate LIMIT clause
        limit_clause = self._extract_limit_clause(analysis.user_query)
        
        # Generate SQL
        sql_query = self._generate_sql(
            primary_table=primary_table,
            selected_columns=selected_columns,
            join_clauses=join_clauses,
            where_clauses=where_clauses,
            group_by_clauses=group_by_clauses,
            order_by_clauses=order_by_clauses,
            limit_clause=limit_clause
        )
        
        # Calculate plan confidence
        plan_confidence = self._calculate_plan_confidence(analysis)
        
        plan = QueryPlan(
            analysis=analysis,
            primary_table=primary_table,
            required_tables=required_tables,
            selected_columns=selected_columns,
            join_clauses=join_clauses,
            where_clauses=where_clauses,
            group_by_clauses=group_by_clauses,
            order_by_clauses=order_by_clauses,
            limit_clause=limit_clause,
            sql_query=sql_query,
            confidence=plan_confidence
        )
        
        logger.info(f"Generated query plan with confidence: {plan_confidence.level}")
        return plan
    
    def validate_and_refine(self, plan: QueryPlan) -> QueryPlan:
        """
        Validate query plan and refine if needed.
        
        Args:
            plan: Initial query plan
            
        Returns:
            Refined query plan
        """
        logger.info("Validating and refining query plan")
        
        # Validate against user query
        validation_results = self._cross_check_plan(plan)
        
        if validation_results["is_valid"]:
            logger.info("Plan is valid")
            return plan
        
        logger.warning(f"Plan validation issues: {validation_results['issues']}")
        
        # Apply refinements
        refined_plan = self._apply_refinements(plan, validation_results["issues"])
        
        return refined_plan
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _extract_tables(self, entities: List[EntityInfo]) -> List[str]:
        """Extract unique table names from entities."""
        tables = set()
        for entity in entities:
            if entity.table_name:
                tables.add(entity.table_name)
        return list(tables)
    
    def _find_navigation_paths(self, tables: List[str], relationships) -> List:
        """Find navigation paths between tables."""
        if len(tables) <= 1:
            return []
        
        # Find paths between all table pairs
        start_tables = [tables[0]]
        target_tables = tables[1:]
        
        paths = self.navigation_tool.execute(
            start_tables=start_tables,
            target_tables=target_tables,
            relationships=relationships,
            max_hops=3
        )
        
        return paths
    
    def _calculate_analysis_confidence(self, entities, relationships, filters, paths) -> ConfidenceScore:
        """Calculate overall confidence in the analysis."""
        # Simple scoring based on what we found
        entity_score = min(len(entities) / 5.0, 1.0)
        relationship_score = min(len(relationships) / 3.0, 1.0) if len(entities) > 1 else 1.0
        filter_score = min(len(filters) / 2.0, 1.0)
        path_score = min(len(paths) / 2.0, 1.0) if len(entities) > 1 else 1.0
        
        avg_entity_relevance = sum(e.relevance_score for e in entities) / len(entities) if entities else 0.0
        
        overall_score = (
            avg_entity_relevance * 0.4 +
            entity_score * 0.2 +
            relationship_score * 0.2 +
            filter_score * 0.1 +
            path_score * 0.1
        )
        
        if overall_score >= 0.8:
            level = ConfidenceLevel.HIGH
            reasoning = "Strong entity matches and clear relationships"
        elif overall_score >= 0.6:
            level = ConfidenceLevel.MEDIUM
            reasoning = "Good entity matches, some ambiguity"
        else:
            level = ConfidenceLevel.LOW
            reasoning = "Weak entity matches or unclear relationships"
        
        return ConfidenceScore(level=level, score=overall_score, reasoning=reasoning)
    
    def _generate_refinement_suggestions(self, analysis: QueryAnalysisResult) -> List[str]:
        """Generate suggestions for refining the analysis."""
        suggestions = []
        
        if analysis.confidence.level == ConfidenceLevel.LOW:
            if len(analysis.entities) < 3:
                suggestions.append("Consider adding more context to identify relevant tables")
            if len(analysis.filters) == 0:
                suggestions.append("No filters identified - consider specifying filter criteria")
            if len(analysis.navigation_paths) == 0 and len(analysis.entities) > 1:
                suggestions.append("No clear path between tables - verify table relationships")
        
        return suggestions
    
    def _identify_primary_table(self, entities: List[EntityInfo]) -> str:
        """Identify the primary/main table for the query."""
        # Use the first table entity with highest relevance
        table_entities = [e for e in entities if e.entity_type in [EntityType.TABLE, EntityType.COLUMN]]
        if table_entities:
            return table_entities[0].table_name or "unknown"
        return "unknown"
    
    def _select_columns(self, entities: List[EntityInfo], context) -> List[str]:
        """Select columns to include in SELECT clause."""
        columns = []
        for entity in entities:
            if entity.entity_type == EntityType.COLUMN and entity.table_name and entity.column_name:
                columns.append(f"{entity.table_name}.{entity.column_name}")
        
        # Add aggregations if specified
        if context.aggregations:
            # This would be more sophisticated in real implementation
            pass
        
        return columns[:10]  # Limit to 10 columns
    
    def _generate_join_clauses(self, primary_table: str, required_tables: List[str], paths) -> List[str]:
        """Generate JOIN clauses."""
        if not paths:
            return []
        
        # Use the first (shortest) path
        best_path = paths[0] if paths else None
        if best_path:
            return best_path.joins
        
        return []
    
    def _generate_where_clauses(self, filters) -> List[str]:
        """Generate WHERE clauses from filters."""
        clauses = []
        for filter_info in filters:
            if filter_info.value:
                if isinstance(filter_info.value, str):
                    clause = f"{filter_info.table}.{filter_info.column} {filter_info.operator} '{filter_info.value}'"
                else:
                    clause = f"{filter_info.table}.{filter_info.column} {filter_info.operator} {filter_info.value}"
                clauses.append(clause)
        return clauses
    
    def _generate_order_by_clauses(self, query: str, entities: List[EntityInfo]) -> List[str]:
        """Generate ORDER BY clauses."""
        query_lower = query.lower()
        clauses = []
        
        if "top" in query_lower:
            # Find numeric columns for sorting
            for entity in entities:
                if entity.column_name and any(
                    word in entity.column_name.lower()
                    for word in ["amount", "aum", "value", "total", "sum"]
                ):
                    clauses.append(f"{entity.table_name}.{entity.column_name} DESC")
                    break
        
        return clauses
    
    def _extract_limit_clause(self, query: str) -> Optional[str]:
        """Extract LIMIT clause from query."""
        import re
        match = re.search(r'\b(top|first|limit)\s+(\d+)\b', query.lower())
        if match:
            return f"LIMIT {match.group(2)}"
        return None
    
    def _generate_sql(
        self,
        primary_table: str,
        selected_columns: List[str],
        join_clauses: List[str],
        where_clauses: List[str],
        group_by_clauses: List[str],
        order_by_clauses: List[str],
        limit_clause: Optional[str]
    ) -> str:
        """Generate SQL query."""
        sql_parts = ["SELECT"]
        
        if selected_columns:
            sql_parts.append("    " + ",\n    ".join(selected_columns))
        else:
            sql_parts.append(f"    {primary_table}.*")
        
        sql_parts.append(f"FROM {primary_table}")
        
        if join_clauses:
            for join in join_clauses:
                sql_parts.append(join)
        
        if where_clauses:
            sql_parts.append("WHERE")
            sql_parts.append("    " + "\n    AND ".join(where_clauses))
        
        if group_by_clauses:
            sql_parts.append("GROUP BY")
            sql_parts.append("    " + ", ".join(group_by_clauses))
        
        if order_by_clauses:
            sql_parts.append("ORDER BY")
            sql_parts.append("    " + ", ".join(order_by_clauses))
        
        if limit_clause:
            sql_parts.append(limit_clause)
        
        return "\n".join(sql_parts)
    
    def _calculate_plan_confidence(self, analysis: QueryAnalysisResult) -> ConfidenceScore:
        """Calculate confidence in the query plan."""
        # Base confidence on analysis confidence
        base_score = analysis.confidence.score
        
        # Adjust based on plan completeness
        if analysis.entities and analysis.relationships:
            base_score *= 1.1
        
        if analysis.filters:
            base_score *= 1.05
        
        # Cap at 1.0
        score = min(base_score, 1.0)
        
        if score >= 0.8:
            level = ConfidenceLevel.HIGH
        elif score >= 0.6:
            level = ConfidenceLevel.MEDIUM
        else:
            level = ConfidenceLevel.LOW
        
        return ConfidenceScore(
            level=level,
            score=score,
            reasoning=f"Based on analysis confidence ({analysis.confidence.level})"
        )
    
    def _cross_check_plan(self, plan: QueryPlan) -> Dict[str, Any]:
        """Cross-check the plan against the user query."""
        issues = []
        
        # Check if primary table makes sense
        if plan.primary_table == "unknown":
            issues.append("Could not identify primary table")
        
        # Check if we have columns to select
        if not plan.selected_columns:
            issues.append("No columns selected")
        
        # Check if joins are needed but missing
        if len(plan.required_tables) > 1 and not plan.join_clauses:
            issues.append("Multiple tables but no JOIN clauses")
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues
        }
    
    def _apply_refinements(self, plan: QueryPlan, issues: List[str]) -> QueryPlan:
        """Apply refinements to the plan based on issues."""
        logger.info(f"Applying refinements for issues: {issues}")
        
        # For now, just return the original plan
        # In a real implementation, this would attempt to fix the issues
        
        return plan
