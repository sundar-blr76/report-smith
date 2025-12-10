from typing import List, Dict, Any, Set, Tuple
import re
import difflib

from reportsmith.schema_intelligence.knowledge_graph import SchemaKnowledgeGraph
from reportsmith.logger import get_logger

logger = get_logger(__name__)

class FilterBuilder:
    """Builds WHERE conditions for SQL queries."""

    def __init__(self, knowledge_graph: SchemaKnowledgeGraph):
        self.kg = knowledge_graph

    def build_where_conditions(
        self,
        entities: List[Dict[str, Any]],
        filters: List[str],
    ) -> List[str]:
        """Build WHERE clause conditions"""
        conditions = []
        
        logger.info(f"[sql-gen][where] Building WHERE conditions from {len(filters)} filter(s)")

        # Parse intent filters first to detect negations
        filter_metadata = {}  # Maps column to (operator, values)
        explicitly_filtered_columns = set()  # Track columns explicitly filtered by user

        for filter_str in filters:
            try:
                filter_str = filter_str.strip()
                
                # Log each filter being processed
                is_temporal = any(keyword in filter_str.upper() for keyword in 
                                 ['EXTRACT', 'QUARTER', 'MONTH', 'YEAR', 'CAST', 'DATE_TRUNC', 'BETWEEN'])
                filter_type = "TEMPORAL" if is_temporal else "STANDARD"
                logger.debug(f"[sql-gen][where] Processing [{filter_type}] filter: {filter_str}")

                # Parse filter to detect column, operator, and value
                pattern = r"([\w.]+)\s*(\bNOT\s+IN\b|\bNOT\s+LIKE\b|!=|=|>|<|>=|<=|\bIN\b|\bLIKE\b)\s*(.+)"
                match = re.match(pattern, filter_str, re.IGNORECASE)

                if match:
                    col_ref = match.group(1).strip()
                    operator = match.group(2).strip().upper()
                    value_part = match.group(3).strip()

                    # Normalize column reference (remove table prefix if present)
                    if "." in col_ref:
                        table_name = col_ref.split(".")[0]
                        col_name = col_ref.split(".")[-1]
                        explicitly_filtered_columns.add(f"{table_name}.{col_name}")
                    else:
                        col_name = col_ref
                        explicitly_filtered_columns.add(col_name)

                    # Store filter metadata to check for negations
                    filter_metadata[col_name] = {
                        "operator": operator,
                        "value": value_part,
                        "original": filter_str,
                    }
                    logger.debug(
                        f"[sql-gen][where] parsed filter: column={col_name}, op={operator}, value={value_part}"
                    )
                else:
                    logger.debug(
                        f"[sql-gen][where] could not parse filter pattern: {filter_str}"
                    )

            except Exception as e:
                logger.warning(
                    f"[sql-gen][where] failed to parse filter '{filter_str}': {e}"
                )

        # Process domain value entities
        dimension_entities = [
            e for e in entities if e.get("entity_type") == "domain_value"
        ]

        # Group dimension entities by table.column to handle multiple values (OR/IN)
        dim_groups: Dict[str, List[str]] = {}
        dim_negations: Dict[str, bool] = {}  # Track which columns have negations

        for ent in dimension_entities:
            table = ent.get("table")
            column = ent.get("column")
            
            # Try to get value from entity metadata
            md = (ent.get("top_match") or {}).get("metadata") or {}
            if not table:
                table = md.get("table")
            if not column:
                column = md.get("column")
            
            if not (table and column):
                continue
            
            key = f"{table}.{column}"
            
            # Check if this column has a negation filter from intent
            filter_info = filter_metadata.get(column, {})
            operator = filter_info.get("operator", "=")
            is_negation = operator in ("!=", "NOT IN", "NOT LIKE")
            
            if key not in dim_groups:
                dim_groups[key] = []
                dim_negations[key] = is_negation
            
            # Get ALL semantic matches for this entity
            semantic_matches = ent.get("semantic_matches", [])
            
            top_score = (ent.get("top_match") or {}).get("score", 0.0)
            score_threshold = max(0.3, top_score * 0.8)
            
            values_added = set()
            for match in semantic_matches:
                match_table = match.get("metadata", {}).get("table")
                match_column = match.get("metadata", {}).get("column")
                match_value = match.get("metadata", {}).get("value") or match.get("content")
                match_score = match.get("score", 0.0)
                
                if (match_table == table and match_column == column and 
                    match_value and match_score >= score_threshold and
                    match_value not in values_added):
                    
                    safe_value = match_value.replace("'", "''")
                    dim_groups[key].append(safe_value)
                    values_added.add(match_value)
                    
                    logger.debug(
                        f"[sql-gen][where] added domain value for partial match: "
                        f"{key} = '{match_value}' (score={match_score:.3f})"
                    )
            
            if not values_added:
                value = (
                    ent.get("value") or 
                    ent.get("canonical_name") or
                    md.get("value") or 
                    ent.get("text")
                )
                if value:
                    safe_value = value.replace("'", "''")
                    dim_groups[key].append(safe_value)
                    values_added.add(value)
                    
                    if ent.get("value"):
                        logger.info(
                            f"[sql-gen][where] ✓ Using domain value from entity.value: "
                            f"{key} = '{value}'"
                        )
                    elif ent.get("canonical_name"):
                        logger.info(
                            f"[sql-gen][where] ✓ Using domain value from entity.canonical_name: "
                            f"{key} = '{value}'"
                        )
            
            if values_added:
                explicitly_filtered_columns.add(key)
                explicitly_filtered_columns.add(column)

        # Build conditions from grouped dimensions
        for key, values in dim_groups.items():
            is_negation = dim_negations.get(key, False)
            
            column_name = key.split(".")[-1] if "." in key else key
            use_partial_match = any(keyword in column_name.lower() for keyword in 
                                   ['name', 'title', 'description', 'code', 'company'])

            if len(values) == 1:
                if is_negation:
                    if use_partial_match:
                        condition = f"{key} NOT ILIKE '%{values[0]}%'"
                    else:
                        condition = f"{key} != '{values[0]}'"
                else:
                    if use_partial_match:
                        condition = f"{key} ILIKE '%{values[0]}%'"
                    else:
                        condition = f"{key} = '{values[0]}'"
                conditions.append(condition)
            else:
                if use_partial_match:
                    if is_negation:
                        condition = "(" + " AND ".join(f"{key} NOT ILIKE '%{v}%'" for v in values) + ")"
                    else:
                        condition = "(" + " OR ".join(f"{key} ILIKE '%{v}%'" for v in values) + ")"
                    conditions.append(condition)
                else:
                    values_str = ", ".join(f"'{v}'" for v in values)
                    if is_negation:
                        condition = f"{key} NOT IN ({values_str})"
                    else:
                        condition = f"{key} IN ({values_str})"
                    conditions.append(condition)

        # Process explicit filters
        processed_columns = {key.split(".")[-1] for key in dim_groups.keys()}
        filters_by_column: Dict[str, List[Tuple[str, str, str]]] = {}

        for filter_str in filters:
            try:
                filter_str = filter_str.strip()

                # Check if this filter is for a column we already handled
                covered = False
                for col_name in processed_columns:
                    if col_name in filter_str:
                        covered = True
                        break

                if not covered:
                    # Check for complex SQL expressions
                    if any(keyword in filter_str.upper() for keyword in ['EXTRACT(', 'CAST(', 'DATE_TRUNC(', 'TO_DATE(', 'TO_CHAR(', 'BETWEEN']):
                        logger.info(f"[predicate-resolution][sql-gen][where] ✓ Detected SQL expression filter: {filter_str}")
                        conditions.append(filter_str)
                        continue

                    pattern = r"([\w.]+)\s*(\bNOT\s+IN\b|\bNOT\s+LIKE\b|!=|=|>|<|>=|<=|\bIN\b|\bLIKE\b)\s*(.+)"
                    match = re.match(pattern, filter_str, re.IGNORECASE)

                    if match:
                        col_ref = match.group(1).strip()
                        operator = match.group(2).strip()
                        value_part = match.group(3).strip()
                        
                        col_name = col_ref.split(".")[-1] if "." in col_ref else col_ref
                        value_cleaned = value_part.strip("'\"")

                        # Check coverage by dimensions
                        skip_filter = False
                        for ent in dimension_entities:
                            ent_text = (ent.get("text") or "").lower()
                            ent_value = (ent.get("top_match", {}).get("metadata", {}).get("value") or "").lower()
                            if value_cleaned.lower() in [ent_text, ent_value]:
                                skip_filter = True
                                break
                        
                        if skip_filter:
                            continue
                        
                        if col_name not in filters_by_column:
                            filters_by_column[col_name] = []
                        filters_by_column[col_name].append((operator, value_cleaned, filter_str))

                    else:
                        # Check coverage by dimensions for unparsable filters
                        filter_terms = filter_str.lower().split()
                        is_covered = False
                        for ent in entities:
                            if ent.get("entity_type") == "domain_value":
                                ent_text = (ent.get("text") or "").lower()
                                if ent_text and ent_text in filter_terms:
                                    is_covered = True
                                    break
                        if not is_covered:
                            logger.warning(f"[sql-gen][where] skipping unparsable filter '{filter_str}'")

            except Exception as e:
                logger.warning(f"[sql-gen][where] failed to process filter '{filter_str}': {e}")
        
        # Merge contradictory filters and add to conditions
        for col_name, col_filters in filters_by_column.items():
            equality_filters = [(op, val, fs) for op, val, fs in col_filters if op == "="]
            
            if len(equality_filters) > 1:
                # Merge into IN clause
                values = list(set(val for op, val, fs in equality_filters))
                
                col_ref = col_name
                for op, val, fs in equality_filters:
                    match = re.match(r"([\w.]+)\s*=", fs)
                    if match and "." in match.group(1):
                        col_ref = match.group(1)
                        break
                
                values_str = ", ".join(f"'{v}'" for v in values)
                merged_condition = f"{col_ref} IN ({values_str})"
                conditions.append(merged_condition)
                logger.warning(f"[sql-gen][where] merged equality filters into: {merged_condition}")
            else:
                for operator, value, filter_str in col_filters:
                    # Normalize column reference
                    normalized_col = None
                    for op, val, fs in col_filters:
                        match = re.match(r"([\w.]+)\s*" + re.escape(operator), fs)
                        if match:
                            normalized_col = self._normalize_column_reference(match.group(1), entities)
                            break
                    
                    if not normalized_col:
                        normalized_col = self._normalize_column_reference(col_name, entities)
                    
                    normalized_value = self._normalize_filter_value(f"'{value}'")
                    conditions.append(f"{normalized_col} {operator} {normalized_value}")

        # Apply auto-filters
        auto_conditions = self._build_auto_filter_conditions(entities, explicitly_filtered_columns)
        conditions.extend(auto_conditions)

        # Merge any lingering equality filters
        conditions = self._merge_equality_filters(conditions)
        
        logger.info(f"[sql-gen][where] Built {len(conditions)} WHERE condition(s)")
        return conditions

    def _normalize_filter_value(self, value_str: str) -> str:
        """Normalize filter values to valid SQL format."""
        value_str = value_str.strip()

        shorthand_pattern = r"^(\d+(?:\.\d+)?)\s*([KMBT])$"
        match = re.match(shorthand_pattern, value_str, re.IGNORECASE)

        if match:
            number = float(match.group(1))
            suffix = match.group(2).upper()
            multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000, "T": 1_000_000_000_000}
            result = number * multipliers[suffix]
            
            if result == int(result):
                return str(int(result))
            else:
                return str(result)

        return value_str

    def _normalize_column_reference(self, col_ref: str, entities: List[Dict[str, Any]]) -> str:
        """Normalize column references to actual schema names."""
        if "." in col_ref:
            table_ref, col_name = col_ref.split(".", 1)
            for ent in entities:
                if ent.get("text", "").lower() == table_ref.lower():
                    actual_table = ent.get("table")
                    if actual_table:
                        return f"{actual_table}.{col_name}"
            return col_ref

        # Check column/table entities
        for ent in entities:
            text = ent.get("text", "").lower()
            entity_type = ent.get("entity_type")
            if text == col_ref.lower():
                if entity_type == "column":
                    return f"{ent.get('table')}.{ent.get('column')}"
                elif entity_type == "table":
                    return ent.get("table")

        # Fuzzy match in KG
        col_lower = col_ref.lower()
        candidates = []
        for node in self.kg.nodes.values():
            if node.type == "column" and node.name:
                ratio = difflib.SequenceMatcher(None, col_lower, node.name.lower()).ratio()
                if ratio > 0.7:
                    candidates.append((node, ratio))
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Check against active query tables
        entity_tables = {ent.get("table") for ent in entities if ent.get("table")}
        for node, _ in candidates[:3]:
            if node.table in entity_tables:
                return f"{node.table}.{node.name}"
        
        return col_ref

    def _merge_equality_filters(self, conditions: List[str]) -> List[str]:
        """Merge multiple equality filters for same column."""
        equality_groups: Dict[str, List[str]] = {}
        other_conditions = []

        for condition in conditions:
            match = re.match(r"^([\w.]+)\s*=\s*'([^']*)'$", condition.strip())
            if match:
                column = match.group(1)
                value = match.group(2)
                if column not in equality_groups:
                    equality_groups[column] = []
                equality_groups[column].append(value)
            else:
                other_conditions.append(condition)

        merged_conditions = other_conditions.copy()
        for column, values in equality_groups.items():
            if len(values) == 1:
                merged_conditions.append(f"{column} = '{values[0]}'")
            else:
                values_str = ", ".join(f"'{v}'" for v in values)
                merged_conditions.append(f"{column} IN ({values_str})")

        return merged_conditions

    def _build_auto_filter_conditions(
        self,
        entities: List[Dict[str, Any]],
        explicitly_filtered_columns: Set[str],
    ) -> List[str]:
        """Build auto-filter conditions."""
        auto_conditions = []
        tables = set()
        for ent in entities:
            table = ent.get("table") or (ent.get("top_match") or {}).get("metadata", {}).get("table")
            if table:
                tables.add(table)

        for table in tables:
            table_node = self.kg.nodes.get(table)
            if not table_node:
                continue

            for node in self.kg.nodes.values():
                if node.type == "column" and node.table == table:
                    auto_filter = node.metadata.get("auto_filter_on_default", False)
                    default_value = node.metadata.get("default")
                    
                    if auto_filter and default_value is not None:
                        col_name = node.name
                        full_col_ref = f"{table}.{col_name}"
                        
                        if full_col_ref in explicitly_filtered_columns or col_name in explicitly_filtered_columns:
                            continue
                        
                        data_type = node.metadata.get("data_type", "").lower()
                        if data_type in ["boolean", "bool"]:
                            value_str = "true" if default_value else "false"
                            condition = f"{full_col_ref} = {value_str}"
                        elif data_type in ["varchar", "text", "string"]:
                            safe_value = str(default_value).replace("'", "''")
                            condition = f"{full_col_ref} = '{safe_value}'"
                        else:
                            condition = f"{full_col_ref} = {default_value}"
                        
                        auto_conditions.append(condition)
                        logger.info(f"[sql-gen][auto-filter] applied default filter: {condition}")
        
        return auto_conditions
