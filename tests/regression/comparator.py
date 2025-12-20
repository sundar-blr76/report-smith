"""
SQL Comparison and Normalization

Provides utilities for comparing SQL queries in a normalized way.
"""

import re
from typing import Set, List, Tuple
import sqlparse


class SQLNormalizer:
    """Normalizes SQL queries for comparison."""
    
    @staticmethod
    def normalize(sql: str) -> str:
        """
        Normalize SQL query for comparison.
        
        - Removes extra whitespace
        - Standardizes formatting
        - Converts to uppercase keywords
        - Removes comments
        """
        if not sql:
            return ""
        
        # Parse and format SQL
        try:
            formatted = sqlparse.format(
                sql,
                keyword_case='upper',
                identifier_case='lower',
                strip_comments=True,
                reindent=True,
                indent_width=2
            )
            
            # Remove extra whitespace
            normalized = re.sub(r'\s+', ' ', formatted).strip()
            
            return normalized
        except Exception:
            # Fallback: basic normalization
            normalized = re.sub(r'\s+', ' ', sql).strip()
            return normalized.upper()
    
    @staticmethod
    def extract_tables(sql: str) -> Set[str]:
        """Extract table names from SQL query."""
        tables = set()
        
        # Simple regex-based extraction
        # Matches: FROM table, JOIN table
        from_pattern = r'(?:FROM|JOIN)\s+([a-z_][a-z0-9_]*)'
        matches = re.findall(from_pattern, sql, re.IGNORECASE)
        tables.update(matches)
        
        return tables
    
    @staticmethod
    def extract_columns(sql: str) -> Set[str]:
        """Extract column references from SQL query."""
        columns = set()
        
        # Match table.column patterns
        col_pattern = r'([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)'
        matches = re.findall(col_pattern, sql, re.IGNORECASE)
        
        for table, column in matches:
            columns.add(f"{table}.{column}")
        
        return columns


class Comparator:
    """Compares actual vs expected results."""
    
    def __init__(self):
        self.normalizer = SQLNormalizer()
    
    def compare_sql(self, expected: str, actual: str) -> Tuple[bool, List[str]]:
        """
        Compare SQL queries.
        
        Returns:
            (is_match, differences)
        """
        differences = []
        
        # Normalize both
        norm_expected = self.normalizer.normalize(expected)
        norm_actual = self.normalizer.normalize(actual)
        
        if norm_expected == norm_actual:
            return True, []
        
        # Check structural differences
        exp_tables = self.normalizer.extract_tables(expected)
        act_tables = self.normalizer.extract_tables(actual)
        
        if exp_tables != act_tables:
            missing = exp_tables - act_tables
            extra = act_tables - exp_tables
            if missing:
                differences.append(f"Missing tables: {', '.join(missing)}")
            if extra:
                differences.append(f"Extra tables: {', '.join(extra)}")
        
        exp_cols = self.normalizer.extract_columns(expected)
        act_cols = self.normalizer.extract_columns(actual)
        
        if exp_cols != act_cols:
            missing = exp_cols - act_cols
            extra = act_cols - exp_cols
            if missing:
                differences.append(f"Missing columns: {', '.join(missing)}")
            if extra:
                differences.append(f"Extra columns: {', '.join(extra)}")
        
        # If no specific differences found, just note they're different
        if not differences:
            differences.append("SQL structure differs")
        
        return False, differences
    
    def compare_entities(self, expected: List[dict], actual: List[dict]) -> Tuple[bool, List[str]]:
        """
        Compare entity lists (order-independent).
        
        Returns:
            (is_match, differences)
        """
        differences = []
        
        # Extract canonical names for comparison
        exp_names = {e.get('canonical_name', e.get('text', '')) for e in expected}
        act_names = {e.get('canonical_name', e.get('text', '')) for e in actual}
        
        if exp_names == act_names:
            return True, []
        
        missing = exp_names - act_names
        extra = act_names - exp_names
        
        if missing:
            differences.append(f"Missing entities: {', '.join(missing)}")
        if extra:
            differences.append(f"Extra entities: {', '.join(extra)}")
        
        return False, differences
    
    def compare_columns(self, expected: List[str], actual: List[str]) -> Tuple[bool, List[str]]:
        """
        Compare column lists.
        
        Returns:
            (is_match, differences)
        """
        if expected == actual:
            return True, []
        
        differences = []
        
        # Check for missing/extra columns
        exp_set = set(expected)
        act_set = set(actual)
        
        missing = exp_set - act_set
        extra = act_set - exp_set
        
        if missing:
            differences.append(f"Missing columns: {', '.join(missing)}")
        if extra:
            differences.append(f"Extra columns: {', '.join(extra)}")
        
        # Check order if same columns
        if exp_set == act_set and expected != actual:
            differences.append(f"Column order differs: {actual} vs {expected}")
        
        return False, differences
    
    def compare_row_count(self, expected: int, actual: int, tolerance: float = 0.1) -> Tuple[bool, List[str]]:
        """
        Compare row counts with tolerance.
        
        Returns:
            (is_match, differences)
        """
        if expected == actual:
            return True, []
        
        # Allow 10% tolerance
        diff_pct = abs(expected - actual) / max(expected, 1)
        
        if diff_pct <= tolerance:
            return True, [f"Row count within tolerance: {actual} vs {expected} ({diff_pct*100:.1f}% diff)"]
        
        return False, [f"Row count mismatch: {actual} vs {expected} ({diff_pct*100:.1f}% diff)"]
