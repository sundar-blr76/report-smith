"""
Schema Validator - Validates SQL queries against schema metadata.

This module validates generated SQL queries against the database schema
to ensure correctness and prevent runtime errors.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from reportsmith.schema_intelligence.knowledge_graph import SchemaKnowledgeGraph
from reportsmith.logger import get_logger

logger = get_logger(__name__)


class SchemaValidator:
    """
    Validates SQL queries against schema metadata.
    
    This validator checks:
    - All referenced tables exist in the schema
    - All referenced columns exist in their respective tables
    - Column data types are compatible with operations
    - Join relationships are valid
    - Aggregations are appropriate for column types
    """
    
    def __init__(self, knowledge_graph: SchemaKnowledgeGraph):
        """
        Initialize schema validator.
        
        Args:
            knowledge_graph: Schema knowledge graph with metadata
        """
        self.kg = knowledge_graph
        logger.info("[schema-validator] initialized")
    
    def validate(
        self,
        sql: str,
        plan: Dict[str, Any],
        entities: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Validate SQL query against schema metadata.
        
        Args:
            sql: SQL query to validate
            plan: Query execution plan
            entities: Extracted entities
        
        Returns:
            Dict with:
                - is_valid: bool - Whether query is valid
                - errors: List[str] - Schema validation errors
                - warnings: List[str] - Schema validation warnings
                - corrected_sql: Optional[str] - Auto-corrected SQL if possible
                - corrections_applied: List[str] - List of corrections made
        """
        logger.info("[schema-validator] validating SQL against schema metadata")
        
        errors: List[str] = []
        warnings: List[str] = []
        corrections_applied: List[str] = []
        corrected_sql = sql
        
        try:
            # 1. Validate tables exist
            table_errors = self._validate_tables(plan)
            errors.extend(table_errors)
            
            # 2. Validate columns exist and extract column references
            column_errors, column_refs = self._validate_columns(sql, plan)
            errors.extend(column_errors)
            
            # 3. Validate data types for operations
            type_warnings = self._validate_data_types(column_refs, sql)
            warnings.extend(type_warnings)
            
            # 4. Validate join relationships
            join_errors = self._validate_joins(plan)
            errors.extend(join_errors)
            
            # 5. Validate aggregations
            agg_warnings = self._validate_aggregations(sql, column_refs)
            warnings.extend(agg_warnings)
            
            # 6. Attempt auto-corrections for common issues
            if errors or warnings:
                corrected_sql, auto_corrections = self._attempt_corrections(
                    sql, errors, warnings, plan, entities
                )
                corrections_applied.extend(auto_corrections)
                
                # Re-validate corrected SQL
                if auto_corrections:
                    logger.info(
                        f"[schema-validator] applied {len(auto_corrections)} "
                        f"auto-correction(s), re-validating"
                    )
                    # Clear errors that were corrected
                    errors = [e for e in errors if not any(c in e for c in auto_corrections)]
            
            is_valid = len(errors) == 0
            
            # Log results
            if errors:
                logger.error(f"[schema-validator] found {len(errors)} error(s)")
                for i, error in enumerate(errors, 1):
                    logger.error(f"[schema-validator] error #{i}: {error}")
            
            if warnings:
                logger.warning(f"[schema-validator] found {len(warnings)} warning(s)")
                for i, warning in enumerate(warnings, 1):
                    logger.warning(f"[schema-validator] warning #{i}: {warning}")
            
            if corrections_applied:
                logger.info(
                    f"[schema-validator] applied {len(corrections_applied)} correction(s)"
                )
                for i, correction in enumerate(corrections_applied, 1):
                    logger.info(f"[schema-validator] correction #{i}: {correction}")
            
            logger.info(
                f"[schema-validator] validation complete: valid={is_valid}, "
                f"errors={len(errors)}, warnings={len(warnings)}, "
                f"corrections={len(corrections_applied)}"
            )
            
            return {
                "is_valid": is_valid,
                "errors": errors,
                "warnings": warnings,
                "corrected_sql": corrected_sql if corrections_applied else None,
                "corrections_applied": corrections_applied,
            }
            
        except Exception as e:
            logger.error(f"[schema-validator] validation failed: {e}", exc_info=True)
            return {
                "is_valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": [],
                "corrected_sql": None,
                "corrections_applied": [],
            }
    
    def _validate_tables(self, plan: Dict[str, Any]) -> List[str]:
        """Validate all tables in plan exist in schema."""
        errors = []
        tables = plan.get("tables", [])
        
        for table in tables:
            # Check if table exists in knowledge graph
            table_node = self.kg.nodes.get(table)
            if not table_node or table_node.type != "table":
                errors.append(f"Table '{table}' not found in schema")
                logger.debug(f"[schema-validator] table '{table}' not found in KG")
            else:
                logger.debug(f"[schema-validator] table '{table}' validated")
        
        return errors
    
    def _validate_columns(
        self, sql: str, plan: Dict[str, Any]
    ) -> Tuple[List[str], List[Dict[str, str]]]:
        """
        Validate columns referenced in SQL exist.
        
        Returns:
            Tuple of (errors, column_references)
        """
        errors = []
        column_refs = []
        
        # Extract column references from SQL
        # Pattern: table.column or column
        pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\.\s*([a-zA-Z_][a-zA-Z0-9_]*)\b'
        matches = re.findall(pattern, sql)
        
        for table, column in matches:
            # Check if this column exists in the knowledge graph
            col_node = self.kg.nodes.get(f"{table}.{column}")
            
            if not col_node or col_node.type != "column":
                errors.append(f"Column '{table}.{column}' not found in schema")
                logger.debug(f"[schema-validator] column '{table}.{column}' not found")
            else:
                # Store column reference with metadata
                column_refs.append({
                    "table": table,
                    "column": column,
                    "data_type": col_node.metadata.get("data_type", "unknown"),
                })
                logger.debug(
                    f"[schema-validator] column '{table}.{column}' validated "
                    f"(type={col_node.metadata.get('data_type')})"
                )
        
        return errors, column_refs
    
    def _validate_data_types(
        self, column_refs: List[Dict[str, str]], sql: str
    ) -> List[str]:
        """Validate data types are compatible with operations."""
        warnings = []
        
        # Check for numeric operations on non-numeric columns
        for col_ref in column_refs:
            table = col_ref["table"]
            column = col_ref["column"]
            data_type = col_ref["data_type"].lower()
            
            col_pattern = f"{table}\\.{column}"
            
            # Check if column is used in numeric operations
            if re.search(rf"{col_pattern}\s*[+\-*/]", sql):
                if data_type not in ["numeric", "integer", "decimal", "float", "double", "money", "bigint", "smallint", "int"]:
                    warnings.append(
                        f"Column '{table}.{column}' (type={data_type}) used in "
                        f"arithmetic operation - may cause type error"
                    )
        
        return warnings
    
    def _validate_joins(self, plan: Dict[str, Any]) -> List[str]:
        """Validate join relationships are valid."""
        errors = []
        
        path_edges = plan.get("path_edges", [])
        
        for edge in path_edges:
            from_node = edge.get("from")
            to_node = edge.get("to")
            from_col = edge.get("from_column")
            to_col = edge.get("to_column")
            
            # Validate join columns exist
            from_col_node = self.kg.nodes.get(f"{from_node}.{from_col}")
            to_col_node = self.kg.nodes.get(f"{to_node}.{to_col}")
            
            if not from_col_node:
                errors.append(
                    f"Join column '{from_node}.{from_col}' not found in schema"
                )
            
            if not to_col_node:
                errors.append(
                    f"Join column '{to_node}.{to_col}' not found in schema"
                )
            
            # Check if data types are compatible for join
            if from_col_node and to_col_node:
                from_type = from_col_node.metadata.get("data_type", "").lower()
                to_type = to_col_node.metadata.get("data_type", "").lower()
                
                # Simple type compatibility check
                if from_type and to_type and from_type != to_type:
                    # Allow some compatible types
                    compatible_pairs = [
                        ("integer", "bigint"),
                        ("bigint", "integer"),
                        ("varchar", "text"),
                        ("text", "varchar"),
                    ]
                    if (from_type, to_type) not in compatible_pairs:
                        errors.append(
                            f"Join type mismatch: {from_node}.{from_col} "
                            f"({from_type}) != {to_node}.{to_col} ({to_type})"
                        )
        
        return errors
    
    def _validate_aggregations(
        self, sql: str, column_refs: List[Dict[str, str]]
    ) -> List[str]:
        """Validate aggregations are appropriate for column types."""
        warnings = []
        
        # Check for aggregations on non-numeric columns
        agg_pattern = r'(SUM|AVG|MIN|MAX|COUNT)\s*\(\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\.\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\)'
        matches = re.findall(agg_pattern, sql, re.IGNORECASE)
        
        for agg_func, table, column in matches:
            agg_func = agg_func.upper()
            
            # Find column metadata
            col_ref = next(
                (c for c in column_refs if c["table"] == table and c["column"] == column),
                None
            )
            
            if col_ref:
                data_type = col_ref["data_type"].lower()
                
                # SUM and AVG should only be used on numeric columns
                if agg_func in ["SUM", "AVG"]:
                    if data_type not in ["numeric", "integer", "decimal", "float", "double", "money", "bigint", "smallint", "int"]:
                        warnings.append(
                            f"Aggregation {agg_func} on non-numeric column "
                            f"'{table}.{column}' (type={data_type})"
                        )
        
        return warnings
    
    def _attempt_corrections(
        self,
        sql: str,
        errors: List[str],
        warnings: List[str],
        plan: Dict[str, Any],
        entities: List[Dict[str, Any]],
    ) -> Tuple[str, List[str]]:
        """
        Attempt automatic corrections for common schema issues.
        
        Returns:
            Tuple of (corrected_sql, corrections_applied)
        """
        corrected_sql = sql
        corrections = []
        
        # Auto-correction strategies:
        # 1. Fix common column name variations (e.g., id vs ID)
        # 2. Add missing table prefixes
        # 3. Fix case sensitivity issues
        
        # For now, we'll implement basic case corrections
        # More sophisticated corrections can be added later
        
        for error in errors:
            # Check for case sensitivity issues
            if "not found in schema" in error:
                # Extract the problematic identifier
                match = re.search(r"'([^']+)'", error)
                if match:
                    identifier = match.group(1)
                    
                    # Try to find a case-insensitive match in KG
                    if "." in identifier:
                        # It's a column reference
                        table, column = identifier.split(".", 1)
                        
                        # Check all column nodes for case-insensitive match
                        for node_name, node in self.kg.nodes.items():
                            if node.type == "column":
                                if (node.table and node.table.lower() == table.lower() and
                                    node.name and node.name.lower() == column.lower()):
                                    # Found a match - replace in SQL
                                    corrected_sql = re.sub(
                                        rf"\b{re.escape(table)}\.{re.escape(column)}\b",
                                        f"{node.table}.{node.name}",
                                        corrected_sql,
                                        flags=re.IGNORECASE
                                    )
                                    corrections.append(
                                        f"Fixed case: {identifier} → {node.table}.{node.name}"
                                    )
                                    break
                    else:
                        # It's a table reference
                        for node_name, node in self.kg.nodes.items():
                            if node.type == "table" and node.name and node.name.lower() == identifier.lower():
                                # Found a match - replace in SQL
                                corrected_sql = re.sub(
                                    rf"\b{re.escape(identifier)}\b",
                                    node.name,
                                    corrected_sql,
                                    flags=re.IGNORECASE
                                )
                                corrections.append(
                                    f"Fixed case: {identifier} → {node.name}"
                                )
                                break
        
        return corrected_sql, corrections
