import json
import time
import hashlib
from typing import List, Dict, Any, Optional

from reportsmith.schema_intelligence.knowledge_graph import SchemaKnowledgeGraph
from reportsmith.logger import get_logger
from .structures import SQLColumn

logger = get_logger(__name__)

class ContextEnricher:
    """Enriches SQL queries using LLM for context, transformations, and ordering."""

    def __init__(
        self,
        knowledge_graph: SchemaKnowledgeGraph,
        llm_client=None,
        cache_manager=None,
        fail_on_llm_error: bool = False,
    ):
        self.kg = knowledge_graph
        self.llm_client = llm_client
        self.cache = cache_manager
        self.fail_on_llm_error = fail_on_llm_error
        
        # Detect and store LLM provider/model info
        if llm_client:
            self.llm_provider = self._detect_llm_provider()
            self.llm_model = self._detect_llm_model()
            logger.info(f"[sql-gen][enricher] LLM client detected: {self.llm_provider}/{self.llm_model}")
        else:
            self.llm_provider = None
            self.llm_model = None

    def enrich_with_context_columns(
        self,
        *,
        question: str,
        intent_type: str,
        select_columns: List[SQLColumn],
        plan: Dict[str, Any],
        entities: List[Dict[str, Any]],
        filters: List[str] = None,
    ) -> List[SQLColumn]:
        """Use LLM to identify and add implicit context columns."""
        logger.info("[sql-gen][llm-enrich] analyzing query for implicit context columns")

        if not self.llm_client or intent_type == "list":
            logger.debug("[sql-gen][llm-enrich] skipping (no LLM client or list query)")
            return select_columns

        # Check cache
        if self.cache:
            cols_key = json.dumps([{
                "table": col.table,
                "column": col.column,
                "aggregation": col.aggregation,
            } for col in select_columns], sort_keys=True)
            tables_key = json.dumps(sorted(plan.get("tables", [])))
            
            cached = self.cache.get(
                "llm_sql",
                "enrich_context",
                question.lower(),
                intent_type,
                cols_key,
                tables_key,
            )
            if cached:
                logger.info("[cache-hit] llm_sql: enrichment result")
                enriched_columns = []
                for col_data in cached:
                    enriched_columns.append(SQLColumn(
                        table=col_data["table"],
                        column=col_data["column"],
                        alias=col_data.get("alias"),
                        aggregation=col_data.get("aggregation"),
                        transformation=col_data.get("transformation"),
                    ))
                return enriched_columns

        try:
            # Prepare context for LLM
            tables = plan.get("tables", [])
            available_columns = {}
            for table in tables:
                table_node = self.kg.nodes.get(table)
                if table_node:
                    cols = []
                    for node in self.kg.nodes.values():
                        if node.type == "column" and node.table == table:
                            cols.append({
                                "name": node.name,
                                "data_type": node.metadata.get("data_type", "unknown"),
                                "description": node.metadata.get("description", ""),
                                "is_pk": node.metadata.get("is_primary_key", False),
                                "is_fk": node.metadata.get("is_foreign_key", False),
                            })
                    available_columns[table] = cols

            current_cols = [{
                "table": col.table,
                "column": col.column,
                "aggregation": col.aggregation,
                "alias": col.alias,
            } for col in select_columns]

            # Filter columns logic
            filter_columns = set()
            if filters:
                import re
                for filter_str in filters:
                    match = re.search(r"(\w+\.)?(\w+)\s*=\s*['\"]", filter_str)
                    if match:
                        filter_columns.add(match.group(2))

            filters_info = ""
            if filter_columns:
                filters_info = f"\n\nFilter Columns (DO NOT add these to SELECT):\n{list(filter_columns)}\nThese columns are used only for filtering with equality conditions."

            # Prompts
            ranking_entity_hint = ""
            if intent_type in ["ranking", "top_n"]:
                import re
                patterns = [r'top\s+\d+\s+(\w+)', r'list.*?(\w+)\s+by', r'show.*?(\w+)\s+by', r'rank.*?(\w+)\s+by']
                for pattern in patterns:
                    match = re.search(pattern, question.lower())
                    if match:
                        entity = match.group(1)
                        ranking_entity_hint = f"\nRANKING ENTITY: '{entity}' - MUST include identifying columns!"
                        break
            
            # Detect aggregation/comparison grouping level from question
            aggregation_level_hint = ""
            grouping_dimension = None
            is_aggregation_query = intent_type in ["aggregation", "aggregate", "comparison"]
            
            if is_aggregation_query:
                import re
                
                # For "by X" patterns
                by_match = re.search(r'\bby\s+(\w+(?:\s+\w+)?)', question.lower())
                if by_match:
                    # Normalize: replace spaces with underscores for column name matching
                    grouping_dimension = by_match.group(1).strip().replace(' ', '_')
                
                # For comparison "between X and Y" patterns - extract the comparison dimension
                between_match = re.search(r'\bbetween\s+(\w+)\s+and\s+(\w+)', question.lower())
                if between_match and not grouping_dimension:
                    # The comparison is between values, not columns - detect what dimension they belong to
                    val1, val2 = between_match.group(1), between_match.group(2)
                    # Common patterns: "conservative and aggressive" → risk_rating
                    if any(x in val1 or x in val2 for x in ['conservative', 'aggressive', 'moderate']):
                        grouping_dimension = "risk_rating"
                    elif any(x in val1 or x in val2 for x in ['equity', 'bond', 'balanced', 'money']):
                        grouping_dimension = "fund_type"
                    else:
                        grouping_dimension = f"{val1}/{val2}"
                
                if grouping_dimension:
                    aggregation_level_hint = f"""

**CRITICAL - {'COMPARISON' if intent_type == 'comparison' else 'AGGREGATION'} QUERY DETECTED**:
User wants results grouped BY '{grouping_dimension}' ONLY.

⚠️ DO NOT ADD ANY COLUMNS THAT WOULD CREATE FINER GRANULARITY!

Examples of FORBIDDEN columns:
- fund_name, fund_code (breaks grouping - shows each fund individually)
- fund_type (if comparing by risk_rating, do NOT add fund_type)
- risk_rating (if comparing by fund_type, do NOT add risk_rating)
- Any unique identifier columns

✓ ALLOWED: The comparison dimension column + aggregated metrics
✗ FORBIDDEN: Other dimension columns that would multiply rows
"""

            prompt = f"""You are a SQL expert helping to make query results more meaningful by identifying implicit context columns.

User Question: "{question}"
Query Intent: {intent_type}{ranking_entity_hint}{aggregation_level_hint}

Currently Selected Columns:
{json.dumps(current_cols, indent=2)}

Available Schema (columns per table):
{json.dumps(available_columns, indent=2)}{filters_info}

Task: Identify additional columns that would make the query output more meaningful for human consumption.

**CRITICAL RULES**:
1. For AGGREGATION queries: NEVER add columns that would break the grouping granularity!
   - If grouping "by fund type", do NOT add fund_name, fund_code, fund_id
   - If grouping "by client", do NOT add individual transaction columns
2. For RANKING/TOP_N queries: DO add identifying columns (name, code, ID)
3. For LIST queries: Add helpful context columns

Return a JSON object with:
{{
  "add_columns": [
    {{
      "table": "table_name",
      "column": "column_name",
      "reason": "why this column makes output more meaningful"
    }}
  ],
  "reasoning": "overall explanation"
}}
"""
            # Execute LLM
            logger.debug(f"[sql-gen][llm-enrich] submitting prompt to {self.llm_provider}...")
            result_text = self._call_llm(prompt)
            
            # Parse response
            result = json.loads(result_text)
            add_columns = result.get("add_columns", [])
            reasoning = result.get("reasoning", "")
            
            logger.info(f"[sql-gen][llm-enrich] suggested {len(add_columns)} columns; reasoning: {reasoning}")

            # Columns that typically break aggregation granularity
            granularity_breaking_suffixes = ['_name', '_code', '_id', 'name', 'code', 'id']
            
            # Dimension columns that should not mix (e.g., don't add fund_type when grouping by risk_rating)
            dimension_columns = {'fund_type', 'risk_rating', 'client_type', 'account_type', 'fee_type'}
            
            # Add columns with aggregation guard
            for col_suggestion in add_columns:
                table = col_suggestion.get("table")
                column = col_suggestion.get("column")
                
                # Verify column exists
                if table not in available_columns: continue
                if not any(c["name"] == column for c in available_columns[table]): continue
                
                # Verify not already selected
                if any(c.table == table and c.column == column for c in select_columns): continue

                # AGGREGATION GUARD: Skip columns that would break grouping granularity
                if is_aggregation_query and grouping_dimension:
                    col_lower = column.lower()
                    
                    # Check 1: Skip if column ends with name/code/id patterns (breaks granularity)
                    if any(col_lower.endswith(suffix) for suffix in granularity_breaking_suffixes):
                        # Exception: if the column IS the grouping dimension, allow it
                        if grouping_dimension not in col_lower:
                            logger.info(f"[sql-gen][llm-enrich] SKIPPED {table}.{column} - would break aggregation granularity (identifier)")
                            continue
                    
                    # Check 2: Skip if column is a different dimension than the grouping dimension
                    if col_lower in dimension_columns:
                        # Only allow if this IS the grouping dimension
                        if col_lower != grouping_dimension and grouping_dimension not in col_lower:
                            logger.info(f"[sql-gen][llm-enrich] SKIPPED {table}.{column} - would break aggregation granularity (different dimension)")
                            continue

                select_columns.append(SQLColumn(
                    table=table,
                    column=column,
                    alias=column,
                ))
                logger.debug(f"[sql-gen][llm-enrich] added: {table}.{column}")

            # POST-ENRICHMENT FILTER: For aggregation/comparison queries, ensure we don't have conflicting dimensions
            if is_aggregation_query and grouping_dimension:
                columns_to_remove = []
                for col in select_columns:
                    col_lower = col.column.lower()
                    # Skip aggregated columns - they're fine
                    if col.aggregation:
                        continue
                    # Check if this is a conflicting dimension column
                    if col_lower in dimension_columns:
                        if col_lower != grouping_dimension and grouping_dimension not in col_lower:
                            columns_to_remove.append(col)
                            logger.info(f"[sql-gen][llm-enrich] POST-FILTER: Removed conflicting dimension {col.table}.{col.column}")
                
                for col in columns_to_remove:
                    select_columns.remove(col)
                
                # Ensure the grouping dimension IS in the select columns (important for aggregation/comparison queries)
                has_grouping_dimension = any(
                    col.column.lower() == grouping_dimension or grouping_dimension in col.column.lower()
                    for col in select_columns if not col.aggregation
                )
                logger.info(f"[sql-gen][llm-enrich] POST-FILTER: grouping_dimension='{grouping_dimension}', has_it={has_grouping_dimension}")
                
                if not has_grouping_dimension:
                    # Try to find and add the grouping dimension column from available tables
                    added = False
                    for table in plan.get("tables", []):
                        table_cols = available_columns.get(table, [])
                        col_names = [c["name"].lower() for c in table_cols]
                        logger.debug(f"[sql-gen][llm-enrich] POST-FILTER: checking table '{table}', columns: {col_names[:5]}...")
                        
                        if grouping_dimension in col_names:
                            # Find the exact column name (preserving case)
                            exact_name = next(c["name"] for c in table_cols if c["name"].lower() == grouping_dimension)
                            select_columns.insert(0, SQLColumn(
                                table=table,
                                column=exact_name,
                                alias=exact_name,
                            ))
                            logger.info(f"[sql-gen][llm-enrich] POST-FILTER: Added missing grouping dimension {table}.{exact_name}")
                            added = True
                            break
                    
                    if not added:
                        logger.warning(f"[sql-gen][llm-enrich] POST-FILTER: Could not find grouping dimension '{grouping_dimension}' in available tables")

            # Cache result
            if self.cache:
                tables_key = json.dumps(sorted(plan.get("tables", [])))
                cached_data = [{
                    "table": col.table,
                    "column": col.column,
                    "alias": col.alias,
                    "aggregation": col.aggregation,
                    "transformation": col.transformation,
                } for col in select_columns]
                
                self.cache.set(
                    "llm_sql", cached_data, "enrich_context",
                    question.lower(), intent_type, cols_key, tables_key
                )

            return select_columns

        except Exception as e:
            logger.warning(f"[sql-gen][llm-enrich] failed: {e}")
            if self.fail_on_llm_error:
                raise
            
            # Fallback
            if intent_type in ["ranking", "top_n"]:
                return self._fallback_add_ranking_identifiers(select_columns, plan, question)
            return select_columns

    def refine_column_transformations(
        self,
        question: str,
        intent_type: str,
        select_columns: List[SQLColumn],
    ) -> List[SQLColumn]:
        """Refine existing column selections with SQL transformations."""
        if not self.llm_client: return select_columns

        # Cache check omitted for brevity but should be here similar to enrich
        
        try:
            current_cols = [{
                "table": col.table,
                "column": col.column,
                "aggregation": col.aggregation,
                "data_type": self._get_column_data_type(col.table, col.column),
            } for col in select_columns]

            prompt = f"""You are a SQL expert helping to refine column selections based on user intent.

User Question: "{question}"
Query Intent: {intent_type}

Currently Selected Columns:
{json.dumps(current_cols, indent=2)}

Task: Identify if any columns should be transformed (e.g. date conversions) to better match the user's request.

Return JSON:
{{
  "transform_columns": [
    {{
      "table": "table_name",
      "column": "original_column_name",
      "transformation": "SQL expression",
      "new_alias": "alias",
      "reason": "reason"
    }}
  ]
}}
"""
            result_text = self._call_llm(prompt)
            result = json.loads(result_text)
            transform_columns = result.get("transform_columns", [])

            new_columns = []
            for col in select_columns:
                transform = next((t for t in transform_columns if t.get("table") == col.table and t.get("column") == col.column), None)
                if transform:
                    new_columns.append(SQLColumn(
                        table=col.table,
                        column=col.column,
                        alias=transform.get("new_alias", col.alias),
                        aggregation=col.aggregation,
                        transformation=transform.get("transformation")
                    ))
                    logger.info(f"[sql-gen][llm-refine] transform: {col.table}.{col.column} -> {transform.get('transformation')}")
                else:
                    new_columns.append(col)
            
            return new_columns

        except Exception as e:
            logger.warning(f"[sql-gen][llm-refine] failed: {e}")
            return select_columns

    def apply_column_ordering(
        self,
        select_columns: List[SQLColumn],
        ordered_column_names: List[str],
    ) -> List[SQLColumn]:
        """Apply LLM-determined column ordering."""
        column_map = {f"{col.table}.{col.column}": col for col in select_columns}
        reordered = []
        seen = set()
        
        for name in ordered_column_names:
            if name in column_map and name not in seen:
                reordered.append(column_map[name])
                seen.add(name)
        
        for col in select_columns:
            key = f"{col.table}.{col.column}"
            if key not in seen:
                reordered.append(col)
        
        return reordered

    def _call_llm(self, prompt: str) -> str:
        """Helper to call diverse LLM providers"""
        if self.llm_provider == "openai":
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0,
            )
            return response.choices[0].message.content
        elif self.llm_provider == "anthropic":
            response = self.llm_client.messages.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0,
            )
            text = response.content[0].text
            # Simple JSON extraction
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start: return text[start:end]
            return text
        else:
            # Gemini
            response = self.llm_client.generate_content(
                prompt, generation_config={"response_mime_type": "application/json", "temperature": 0}
            )
            return response.text

    def _detect_llm_provider(self) -> str:
        if not self.llm_client: return "none"
        if hasattr(self.llm_client, "chat") and hasattr(self.llm_client.chat, "completions"): return "openai"
        if hasattr(self.llm_client, "messages"): return "anthropic"
        return "gemini"

    def _detect_llm_model(self) -> str:
        provider = self._detect_llm_provider()
        if provider == "openai": return "gpt-4o-mini"
        if provider == "anthropic": return "claude-3-haiku-20240307"
        if provider == "gemini": return "gemini-2.5-flash"
        return "unknown"

    def _get_column_data_type(self, table: str, column: str) -> str:
        node = self.kg.nodes.get(f"{table}.{column}")
        return node.metadata.get("data_type", "unknown") if node else "unknown"

    def _fallback_add_ranking_identifiers(self, select_columns, plan, question):
        """Heuristic fallback for ranking queries"""
        import re
        tables = plan.get("tables", [])
        if not tables: return select_columns
        
        # Try to guess entity
        entity_kw = None
        for pattern in [r'top\s+\d+\s+(\w+)', r'rank.*?(\w+)']:
            m = re.search(pattern, question.lower())
            if m:
                entity_kw = m.group(1).rstrip('s')
                break
        
        candidate = next((t for t in tables if entity_kw and entity_kw in t.lower()), tables[0])
        
        # Add basic identifiers
        for suffix in ["_name", "name", "_id", "id", "_code"]:
            potential_col = f"{candidate[:-1]}{suffix}" if suffix.startswith("_") else suffix
            # Logic to check KG and add... (simplified here for brevity)
            # In real impl, check KG for existence
            col_node = self.kg.nodes.get(f"{candidate}.{potential_col}")
            if col_node and not any(c.table == candidate and c.column == potential_col for c in select_columns):
                select_columns.append(SQLColumn(table=candidate, column=potential_col, alias=potential_col))
                break # Just add one identifier
        
        return select_columns
