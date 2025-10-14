# Robust Dimension Handling - Edge Cases & Solutions

## Your Critical Insights

### 1. **Implicit Dimensions (No Explicit Dimension Table)**
### 2. **Case Sensitivity Issues** 
### 3. **Cascading Table Discovery**

These make or break real-world implementation!

---

## Problem 1: Implicit Dimensions

### The Issue

```yaml
# Schema says:
funds:
  fund_type:
    type: varchar
    is_dimension: true  # Marked as dimension
    # But NO dictionary_table defined!
```

**Current State:**
- Column is marked as dimension
- But no dictionary table exists
- LLM has no way to know valid values
- Pattern matching (LIKE 'Equity%') might fail

**Your Solution:** Query for distinct values dynamically!

---

## Solution 1A: Dynamic Dimension Value Discovery

### Query Actual Database Values

```python
class ImplicitDimensionHandler:
    """
    Handles columns marked as dimensions but without explicit dimension tables.
    Queries database for actual values and caches them.
    """
    
    def __init__(self):
        self.dimension_cache = {}  # Cache discovered values
        self.cache_ttl = timedelta(hours=1)  # Refresh hourly
        self.cache_timestamps = {}
    
    def get_dimension_values(
        self, 
        table: str, 
        column: str,
        force_refresh: bool = False
    ) -> Dict:
        """
        Get dimension values for a column, even without dimension table.
        
        Strategy:
        1. Check if there's explicit dimension table → use it
        2. If not, query for DISTINCT values from main table
        3. Cache results for performance
        4. Auto-detect patterns and groupings
        """
        
        cache_key = f"{table}.{column}"
        
        # Check cache first
        if not force_refresh and cache_key in self.dimension_cache:
            cached_time = self.cache_timestamps.get(cache_key)
            if cached_time and (datetime.now() - cached_time) < self.cache_ttl:
                logger.debug(f"Using cached dimension values for {cache_key}")
                return self.dimension_cache[cache_key]
        
        # Check for explicit dimension table
        column_def = self.config_mgr.get_column_definition(table, column)
        
        if column_def.get('dictionary_table'):
            # Has explicit dimension table
            result = self._query_dimension_table(column_def)
        else:
            # Implicit dimension - query distinct values
            logger.info(f"No dimension table for {cache_key}, querying distinct values")
            result = self._query_distinct_values(table, column)
        
        # Cache the result
        self.dimension_cache[cache_key] = result
        self.cache_timestamps[cache_key] = datetime.now()
        
        return result
    
    def _query_distinct_values(self, table: str, column: str) -> Dict:
        """
        Query database for distinct values in a column.
        Also analyze patterns for smart matching.
        """
        
        # Query distinct values with counts
        query = f"""
            SELECT 
                {column} as value,
                COUNT(*) as count,
                COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
            FROM {table}
            WHERE {column} IS NOT NULL
            GROUP BY {column}
            ORDER BY count DESC
        """
        
        results = self.db_manager.execute_query(query)
        
        if not results:
            return {
                'type': 'implicit',
                'values': [],
                'count': 0,
                'patterns': []
            }
        
        # Analyze the values for patterns
        values = [r['value'] for r in results]
        patterns = self._detect_patterns(values)
        
        # Detect case variations
        case_analysis = self._analyze_case_sensitivity(values)
        
        return {
            'type': 'implicit',
            'source': 'distinct_query',
            'table': table,
            'column': column,
            'values': results,
            'count': len(results),
            'patterns': patterns,
            'case_analysis': case_analysis,
            'cached_at': datetime.now().isoformat()
        }
    
    def _detect_patterns(self, values: List[str]) -> List[Dict]:
        """
        Detect common patterns in dimension values.
        
        Examples:
        - ['Equity Growth', 'Equity Income', 'Equity Value'] → prefix 'Equity'
        - ['USD', 'EUR', 'GBP'] → 3-letter codes
        - ['Active', 'Closed', 'Suspended'] → status states
        """
        patterns = []
        
        # Pattern 1: Common prefix
        if len(values) > 1:
            common_prefix = self._find_common_prefix(values)
            if len(common_prefix) > 2:
                matching_values = [v for v in values if v.startswith(common_prefix)]
                if len(matching_values) >= 2:
                    patterns.append({
                        'type': 'prefix',
                        'pattern': common_prefix,
                        'matching_values': matching_values,
                        'sql_pattern': f"{common_prefix}%",
                        'confidence': len(matching_values) / len(values)
                    })
        
        # Pattern 2: Common suffix
        common_suffix = self._find_common_suffix(values)
        if len(common_suffix) > 2:
            matching_values = [v for v in values if v.endswith(common_suffix)]
            if len(matching_values) >= 2:
                patterns.append({
                    'type': 'suffix',
                    'pattern': common_suffix,
                    'matching_values': matching_values,
                    'confidence': len(matching_values) / len(values)
                })
        
        # Pattern 3: Fixed-length codes
        lengths = [len(v) for v in values]
        if len(set(lengths)) == 1 and lengths[0] <= 10:
            patterns.append({
                'type': 'fixed_length_code',
                'length': lengths[0],
                'all_values': values,
                'note': 'Looks like fixed-length codes (use exact match)'
            })
        
        # Pattern 4: Hierarchical (contains separator like -, _, /)
        if any('/' in v or '-' in v or '_' in v for v in values):
            patterns.append({
                'type': 'hierarchical',
                'note': 'Contains separators, might be hierarchical codes',
                'examples': [v for v in values if '/' in v or '-' in v or '_' in v][:5]
            })
        
        return patterns
    
    def _analyze_case_sensitivity(self, values: List[str]) -> Dict:
        """
        Analyze case variations in values.
        Critical for proper matching!
        """
        
        # Check if all values are same case
        all_upper = all(v.isupper() for v in values if v.isalpha())
        all_lower = all(v.islower() for v in values if v.isalpha())
        all_title = all(v.istitle() for v in values if v.replace(' ', '').isalpha())
        
        # Check for mixed case within values
        mixed_case = any(
            any(c.isupper() for c in v) and any(c.islower() for c in v)
            for v in values
        )
        
        # Find case variations of same logical value
        case_variations = {}
        normalized_values = {}
        for v in values:
            normalized = v.lower()
            if normalized in normalized_values:
                if v not in case_variations:
                    case_variations[normalized] = []
                case_variations[normalized].append(v)
            normalized_values[normalized] = v
        
        return {
            'all_upper': all_upper,
            'all_lower': all_lower,
            'all_title': all_title,
            'mixed_case': mixed_case,
            'case_variations': case_variations,
            'recommendation': self._get_case_recommendation(
                all_upper, all_lower, all_title, mixed_case
            )
        }
    
    def _get_case_recommendation(
        self, 
        all_upper: bool, 
        all_lower: bool, 
        all_title: bool, 
        mixed_case: bool
    ) -> str:
        """Recommend how to handle case in queries."""
        
        if all_upper:
            return "use_upper_case"  # WHERE UPPER(column) = UPPER(value)
        elif all_lower:
            return "use_lower_case"  # WHERE LOWER(column) = LOWER(value)
        elif all_title:
            return "use_title_case"  # WHERE INITCAP(column) = INITCAP(value)
        elif mixed_case:
            return "case_sensitive"  # Exact match required
        else:
            return "case_insensitive"  # Safe to normalize
```

---

## Problem 2: Case Sensitivity Issues

### The Issue

```python
# Database has: 'Equity Growth', 'Bond Fund', 'Money Market'
# User queries: "equity funds"
# LLM generates: WHERE fund_type LIKE 'Equity%'
# ❌ FAILS if database is case-sensitive!

# Database might have:
# - 'Equity Growth'  (title case)
# - 'EQUITY GROWTH'  (upper case)
# - 'equity growth'  (lower case)
# - 'Equity growth'  (mixed case)
```

### Solution 2A: Case-Insensitive Matching

```python
class CaseSensitiveQueryBuilder:
    """
    Builds queries that handle case sensitivity properly.
    """
    
    def build_dimension_filter(
        self,
        table: str,
        column: str,
        search_value: str,
        dimension_info: Dict
    ) -> str:
        """
        Build WHERE clause that handles case sensitivity.
        """
        
        case_analysis = dimension_info.get('case_analysis', {})
        recommendation = case_analysis.get('recommendation', 'case_insensitive')
        
        if recommendation == 'use_upper_case':
            # All values are uppercase
            return f"UPPER({table}.{column}) = UPPER('{search_value}')"
        
        elif recommendation == 'use_lower_case':
            # All values are lowercase
            return f"LOWER({table}.{column}) = LOWER('{search_value}')"
        
        elif recommendation == 'case_sensitive':
            # Mixed case, exact match required
            return f"{table}.{column} = '{search_value}'"
        
        else:  # case_insensitive (default)
            # Safe to use case-insensitive match
            return f"UPPER({table}.{column}) = UPPER('{search_value}')"
    
    def build_pattern_filter(
        self,
        table: str,
        column: str,
        pattern: str,
        dimension_info: Dict
    ) -> str:
        """
        Build LIKE pattern with proper case handling.
        """
        
        case_analysis = dimension_info.get('case_analysis', {})
        recommendation = case_analysis.get('recommendation', 'case_insensitive')
        
        if recommendation == 'case_sensitive':
            # Exact case required
            return f"{table}.{column} LIKE '{pattern}'"
        else:
            # Case-insensitive pattern matching
            # Use ILIKE (PostgreSQL) or UPPER/LOWER
            if self.db_type == 'postgresql':
                return f"{table}.{column} ILIKE '{pattern}'"
            else:
                return f"UPPER({table}.{column}) LIKE UPPER('{pattern}')"
```

### Solution 2B: LLM Learns Case Patterns

```python
def _llm_match_with_case_handling(
    self,
    entity_text: str,
    dimension_info: Dict
) -> Dict:
    """
    LLM matches entity to dimension values with case awareness.
    """
    
    prompt = f"""
Entity: "{entity_text}"

Available dimension values:
{json.dumps(dimension_info['values'], indent=2)}

Case Analysis:
{json.dumps(dimension_info['case_analysis'], indent=2)}

Patterns detected:
{json.dumps(dimension_info['patterns'], indent=2)}

Your task: Find best match(es) for "{entity_text}"

Consider:
1. Case variations (user said lowercase, data might be Title Case)
2. Prefix patterns (user said "equity" → match "Equity Growth", "Equity Income")
3. Plural vs singular (user said "funds" → ignore the 's')

Return:
{{
  "matched_values": ["Equity Growth", "Equity Income"],  // Actual DB values
  "match_type": "prefix_pattern",  // exact, prefix_pattern, fuzzy
  "sql_filter": "UPPER(fund_type) LIKE UPPER('Equity%')",  // Case-safe SQL
  "reasoning": "User said 'equity' (lowercase), DB has Title Case values starting with 'Equity'"
}}
"""
    
    return self.llm_client.generate(prompt)
```

---

## Problem 3: Cascading Table Discovery

### The Issue

```python
# Initial query: "Show AUM for equity funds"
# Maps to: funds table

# LLM adds context column: funds.name
# LLM sees: funds.management_company_id (FK)

# ❓ Should we JOIN to management_companies to get company name?
# ❓ If we do, what if management_companies has MORE FKs?
# ❓ How deep do we go?
```

### The Problem: Infinite Cascade

```
funds
  ↓ management_company_id
management_companies
  ↓ country_id
countries
  ↓ region_id
regions
  ↓ continent_id
continents
  ...

When do we stop?!
```

### Solution 3A: Iterative Table Discovery with Depth Limits

```python
class CascadingTableDiscovery:
    """
    Handles cascading table joins with intelligent depth control.
    """
    
    def __init__(self, max_depth: int = 3, max_tables: int = 5):
        self.max_depth = max_depth
        self.max_tables = max_tables
        self.discovered_tables = set()
    
    def discover_related_tables(
        self,
        initial_tables: List[str],
        required_columns: List[str],
        query_context: str
    ) -> Dict:
        """
        Iteratively discover related tables based on what columns we need.
        
        Strategy:
        1. Start with required columns
        2. Check if we need to JOIN to get them
        3. For each new table, check if we need MORE context
        4. Stop at max_depth or when LLM says "complete"
        """
        
        discovered = {
            'tables': set(initial_tables),
            'joins': [],
            'columns': set(required_columns),
            'depth': 0
        }
        
        while discovered['depth'] < self.max_depth:
            discovered['depth'] += 1
            
            logger.info(f"Table discovery iteration {discovered['depth']}")
            
            # Ask LLM if we need more tables
            decision = self._llm_check_completeness(discovered, query_context)
            
            if decision['is_complete']:
                logger.info("LLM determined schema is complete")
                break
            
            if decision['needs_tables']:
                new_tables = self._discover_related_tables_for_columns(
                    discovered['tables'],
                    decision['needed_columns']
                )
                
                if new_tables:
                    discovered['tables'].update(new_tables)
                    discovered['joins'].extend(self._find_join_paths(new_tables))
                    
                    # Check if adding new tables triggers more needs
                    additional_context = self._check_new_table_context(new_tables)
                    if additional_context:
                        discovered['columns'].update(additional_context)
                else:
                    # Can't find tables for needed columns, stop
                    break
            else:
                # No more tables needed
                break
            
            # Safety: Don't exceed max tables
            if len(discovered['tables']) >= self.max_tables:
                logger.warning(f"Reached max tables limit ({self.max_tables})")
                break
        
        return discovered
    
    def _llm_check_completeness(
        self,
        current_mapping: Dict,
        query_context: str
    ) -> Dict:
        """
        LLM decides if current mapping is complete or needs more tables.
        """
        
        prompt = f"""
User Query: "{query_context}"

Current Mapping:
Tables: {list(current_mapping['tables'])}
Columns: {list(current_mapping['columns'])}
Joins: {current_mapping['joins']}
Depth: {current_mapping['depth']}/{self.max_depth}

Question: Is this mapping COMPLETE to answer the user's query?

Consider:
1. Do we have all data columns needed?
2. Do we have identifier/name columns for context?
3. Are there obvious missing pieces?
4. Would adding another table significantly improve the result?

IMPORTANT: Don't go too deep! 
- If we have basic data + identifiers, that's enough
- Don't add tables "just in case"
- Prefer simpler queries

Return:
{{
  "is_complete": true/false,
  "reasoning": "...",
  "needs_tables": false,
  "needed_columns": [],  // What columns do we still need?
  "confidence": 0.9
}}

If is_complete=false, specify EXACTLY what columns are missing and why.
"""
        
        response = self.llm_client.generate(prompt)
        result = json.loads(response)
        
        logger.info(f"LLM completeness check: {result['reasoning']}")
        
        return result
    
    def _check_new_table_context(self, new_tables: List[str]) -> List[str]:
        """
        When we add new tables, check if they have context columns we should include.
        """
        
        additional_columns = []
        
        for table in new_tables:
            schema = self.config_mgr.get_table_schema(table)
            
            # Look for common context columns
            for col_name, col_def in schema.columns.items():
                # Name columns are usually good context
                if 'name' in col_name.lower():
                    additional_columns.append(f"{table}.{col_name}")
                
                # Description columns
                elif 'description' in col_name.lower():
                    additional_columns.append(f"{table}.{col_name}")
                
                # Code/ID columns that are displayable
                elif col_name.endswith('_code') and not col_name.endswith('_id'):
                    additional_columns.append(f"{table}.{col_name}")
        
        return additional_columns
```

### Solution 3B: Smart Depth Control

```python
class SmartDepthControl:
    """
    Intelligent rules for when to stop cascading.
    """
    
    def should_stop_cascading(
        self,
        current_depth: int,
        current_tables: List[str],
        potential_next_table: str,
        query_context: str
    ) -> Tuple[bool, str]:
        """
        Decide if we should stop cascading to more tables.
        
        Returns: (should_stop, reason)
        """
        
        # Rule 1: Hard limit on depth
        if current_depth >= self.max_depth:
            return True, f"Reached max depth ({self.max_depth})"
        
        # Rule 2: Hard limit on table count
        if len(current_tables) >= self.max_tables:
            return True, f"Reached max tables ({self.max_tables})"
        
        # Rule 3: Check if table is "too far" from core tables
        distance = self._calculate_relationship_distance(
            current_tables[0],  # Initial table
            potential_next_table
        )
        if distance > 3:
            return True, f"Table '{potential_next_table}' is too distant (distance={distance})"
        
        # Rule 4: Check if table adds meaningful data
        table_info = self.config_mgr.get_table_schema(potential_next_table)
        meaningful_columns = self._count_meaningful_columns(table_info)
        
        if meaningful_columns < 2:
            return True, f"Table '{potential_next_table}' has too few meaningful columns"
        
        # Rule 5: Check query context
        # If user asked for simple data, don't over-join
        if self._is_simple_query(query_context) and current_depth >= 2:
            return True, "Query is simple, don't over-complicate"
        
        # Don't stop - continue cascading
        return False, "Continue discovery"
    
    def _is_simple_query(self, query: str) -> bool:
        """
        Detect if query is simple (doesn't need deep joins).
        """
        simple_patterns = [
            'show', 'list', 'get', 'what is', 'total', 'sum', 'count'
        ]
        
        query_lower = query.lower()
        return any(pattern in query_lower for pattern in simple_patterns)
```

---

## Integrated Solution: Robust Dimension Handler

### Complete Implementation

```python
class RobustDimensionHandler:
    """
    Handles all dimension-related challenges:
    1. Implicit dimensions (no explicit table)
    2. Case sensitivity
    3. Cascading table discovery
    """
    
    def __init__(
        self,
        db_manager,
        config_manager,
        llm_client,
        max_cascade_depth: int = 3,
        max_tables: int = 5,
        cache_ttl_hours: int = 1
    ):
        self.db = db_manager
        self.config = config_manager
        self.llm = llm_client
        
        # Implicit dimension handling
        self.implicit_handler = ImplicitDimensionHandler()
        
        # Case sensitivity handling
        self.case_handler = CaseSensitiveQueryBuilder()
        
        # Cascading table discovery
        self.cascade_handler = CascadingTableDiscovery(
            max_depth=max_cascade_depth,
            max_tables=max_tables
        )
        
        # Cache
        self.dimension_cache = {}
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
    
    def get_dimension_info(
        self,
        table: str,
        column: str,
        force_refresh: bool = False
    ) -> Dict:
        """
        Get dimension information, handling all edge cases.
        
        Returns enriched dimension info with:
        - Actual values (from table or distinct query)
        - Case analysis
        - Pattern detection
        - Caching metadata
        """
        
        # Try implicit dimension handler (queries DB if needed)
        dim_info = self.implicit_handler.get_dimension_values(
            table, column, force_refresh
        )
        
        # Enrich with additional analysis
        if dim_info['values']:
            dim_info['query_builder'] = self.case_handler
            dim_info['recommended_sql'] = self._generate_recommended_sql(
                table, column, dim_info
            )
        
        return dim_info
    
    def match_entity_to_dimension(
        self,
        entity_text: str,
        table: str,
        column: str,
        query_context: str
    ) -> Dict:
        """
        Match entity to dimension values with case/pattern handling.
        """
        
        # Get dimension info (cached if available)
        dim_info = self.get_dimension_info(table, column)
        
        # LLM matches with case awareness
        match_result = self._llm_match_with_case_handling(
            entity_text, dim_info, query_context
        )
        
        return match_result
    
    def discover_complete_schema(
        self,
        initial_mapping: Dict,
        query_context: str
    ) -> Dict:
        """
        Discover complete schema with controlled cascading.
        """
        
        complete_mapping = self.cascade_handler.discover_related_tables(
            initial_tables=initial_mapping['tables'],
            required_columns=initial_mapping['columns'],
            query_context=query_context
        )
        
        return complete_mapping
```

---

## Configuration Updates

### Enhanced YAML Schema

```yaml
tables:
  funds:
    columns:
      fund_type:
        type: varchar
        is_dimension: true
        # No dictionary_table - will query distinct values!
        dimension_config:
          cache_values: true
          case_sensitive: false
          pattern_matching: true
          
      status:
        type: varchar
        is_dimension: true
        # Could query distinct, OR use dimension table if it exists
        dimension_config:
          prefer_dimension_table: true  # Create one if doesn't exist
          case_sensitive: false
          
  # Discovery control
  discovery_rules:
    max_cascade_depth: 3
    max_tables: 5
    stop_at_lookup_tables: true  # Don't cascade beyond lookups
    required_column_types: ['name', 'description', 'code']
```

---

## Summary: Three Critical Enhancements

### 1. **Implicit Dimensions**
```python
✓ Query DISTINCT values when no dimension table exists
✓ Cache results for performance
✓ Auto-detect patterns (prefix, suffix, fixed-length)
✓ Analyze case sensitivity
```

### 2. **Case Sensitivity**
```python
✓ Detect case patterns in data
✓ Use case-insensitive matching (UPPER, ILIKE)
✓ LLM learns case conventions
✓ Generate case-safe SQL
```

### 3. **Cascading Control**
```python
✓ Iterative table discovery (not all at once)
✓ Depth limits (max 3 levels)
✓ Table count limits (max 5 tables)
✓ LLM decides when "complete"
✓ Smart stopping rules
```

---

## Example: Complete Flow

```python
Query: "Show AUM for equity funds"

# Iteration 1: Initial Discovery
Entity: "equity"
Column: funds.fund_type (VARCHAR, no dimension table)

# Iteration 2: Get Implicit Dimension Values
Action: Query DISTINCT fund_type FROM funds
Results: ['Equity Growth', 'Equity Income', 'Bond Fund', 'Money Market']
Case Analysis: Title Case, prefix pattern detected ('Equity')

# Iteration 3: Match with Case Handling
LLM: "User said 'equity' (lowercase), DB has 'Equity Growth', 'Equity Income'"
LLM: "Use pattern: UPPER(fund_type) LIKE UPPER('Equity%')"

# Iteration 4: Check for Context Columns
LLM: "Need funds.name for identification"
LLM: "See funds.management_company_id FK - should I get company name?"

# Iteration 5: Cascading Decision
LLM: "Query is simple, company name would be helpful but not essential"
Decision: Add management_companies.name, but STOP there (depth=2)

# Final Result:
SELECT 
  f.name,
  f.fund_type,
  f.total_aum,
  mc.name as company_name
FROM funds f
LEFT JOIN management_companies mc ON f.management_company_id = mc.id
WHERE UPPER(f.fund_type) LIKE UPPER('Equity%')  -- Case-insensitive!
  AND f.is_active = true
```

---

Your insights make this system production-ready! 🎯
