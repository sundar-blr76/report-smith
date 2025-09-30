"""
Embedding Manager for ReportSmith

Manages embeddings for:
1. Schema metadata (tables, columns from YAML configs)
2. Dimension values (actual values from database dimension tables)
3. Business context (metrics, rules, sample queries)

Uses ChromaDB in-memory mode for fast semantic search.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
import hashlib

from ..logger import get_logger

logger = get_logger(__name__)


@dataclass
class SearchResult:
    """Search result from vector database."""
    content: str
    metadata: Dict[str, Any]
    distance: float
    score: float  # 1 - distance (higher is better)


class EmbeddingManager:
    """
    Manages embeddings using ChromaDB in-memory mode.
    
    Collections:
    - schema_metadata: Table and column metadata from YAML
    - dimension_values: Actual values from dimension tables
    - business_context: Metrics, rules, and sample queries
    """
    
    def __init__(self, embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize embedding manager.
        
        Args:
            embedding_model: Name of sentence-transformer model to use
        """
        self.embedding_model = embedding_model
        
        # Initialize ChromaDB in-memory client
        self.client = chromadb.Client(ChromaSettings(
            anonymized_telemetry=False,
            allow_reset=True
        ))
        
        # Initialize embedding function
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embedding_model
        )
        
        # Create collections
        self.collections: Dict[str, chromadb.Collection] = {}
        self._init_collections()
        
        # Cache for dimension embeddings (to track staleness)
        self._dimension_cache: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(hours=24)  # 24-hour staleness acceptable
        
        logger.info(f"Initialized EmbeddingManager with model: {embedding_model}")
    
    def _init_collections(self):
        """Initialize ChromaDB collections."""
        collection_configs = {
            "schema_metadata": "Table and column metadata",
            "dimension_values": "Dimension value embeddings",
            "business_context": "Business metrics and rules"
        }
        
        for name, description in collection_configs.items():
            self.collections[name] = self.client.get_or_create_collection(
                name=name,
                embedding_function=self.embedding_fn,
                metadata={"description": description}
            )
            logger.debug(f"Initialized collection: {name}")
    
    def reset(self):
        """Reset all collections (useful for testing or refresh)."""
        logger.warning("Resetting all embedding collections")
        self.client.reset()
        self._init_collections()
        self._dimension_cache.clear()
    
    # ==========================================================================
    # SCHEMA METADATA EMBEDDINGS
    # ==========================================================================
    
    def load_schema_metadata(self, app_id: str, schema_config: Dict[str, Any]):
        """
        Load schema metadata from application YAML config.
        
        Args:
            app_id: Application identifier (e.g., 'fund_accounting')
            schema_config: Parsed schema section from YAML
        """
        collection = self.collections["schema_metadata"]
        
        documents = []
        metadatas = []
        ids = []
        
        tables = schema_config.get("tables", {})
        
        for table_name, table_def in tables.items():
            # Embed table-level metadata
            table_doc = self._create_table_document(app_id, table_name, table_def)
            table_id = self._generate_id(f"table_{app_id}_{table_name}")
            
            documents.append(table_doc)
            metadatas.append({
                "type": "table",
                "application": app_id,
                "table": table_name,
                "description": table_def.get("description", ""),
                "primary_key": table_def.get("primary_key", ""),
                "estimated_rows": table_def.get("estimated_rows", 0)
            })
            ids.append(table_id)
            
            # Embed column-level metadata
            columns = table_def.get("columns", {})
            for col_name, col_def in columns.items():
                col_doc = self._create_column_document(
                    app_id, table_name, col_name, col_def
                )
                col_id = self._generate_id(f"column_{app_id}_{table_name}_{col_name}")
                
                documents.append(col_doc)
                metadatas.append({
                    "type": "column",
                    "application": app_id,
                    "table": table_name,
                    "column": col_name,
                    "data_type": col_def.get("type", ""),
                    "description": col_def.get("description", ""),
                    "nullable": col_def.get("nullable", True),
                    "examples": str(col_def.get("examples", []))
                })
                ids.append(col_id)
        
        # Add to collection in batch
        if documents:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(
                f"Loaded {len(documents)} schema embeddings for app: {app_id}"
            )
    
    def _create_table_document(
        self, app_id: str, table_name: str, table_def: Dict[str, Any]
    ) -> str:
        """Create searchable document for table."""
        parts = [
            f"Table: {table_name}",
            f"Application: {app_id}",
            f"Description: {table_def.get('description', 'No description')}",
            f"Primary Key: {table_def.get('primary_key', 'Not specified')}",
        ]
        
        if "common_queries" in table_def:
            parts.append(f"Common queries: {', '.join(table_def['common_queries'])}")
        
        return " | ".join(parts)
    
    def _create_column_document(
        self, app_id: str, table_name: str, col_name: str, col_def: Dict[str, Any]
    ) -> str:
        """Create searchable document for column."""
        parts = [
            f"Column: {table_name}.{col_name}",
            f"Application: {app_id}",
            f"Type: {col_def.get('type', 'unknown')}",
            f"Description: {col_def.get('description', 'No description')}",
        ]
        
        if "examples" in col_def:
            examples = col_def["examples"]
            if isinstance(examples, list):
                parts.append(f"Example values: {', '.join(map(str, examples))}")
        
        if col_def.get("unique"):
            parts.append("Unique identifier")
        
        if col_def.get("nullable") is False:
            parts.append("Required field")
        
        return " | ".join(parts)
    
    # ==========================================================================
    # DIMENSION VALUE EMBEDDINGS
    # ==========================================================================
    
    def load_dimension_values(
        self,
        app_id: str,
        table: str,
        column: str,
        values: List[Dict[str, Any]],
        context: Optional[str] = None
    ):
        """
        Load dimension values from database query results.
        
        Args:
            app_id: Application identifier
            table: Table name
            column: Column name
            values: List of dicts with 'value' and 'count' keys
            context: Optional business context/description
        """
        collection = self.collections["dimension_values"]
        
        documents = []
        metadatas = []
        ids = []
        
        for item in values:
            value = item["value"]
            count = item.get("count", 0)
            
            doc = self._create_dimension_document(
                app_id, table, column, value, count, context
            )
            doc_id = self._generate_id(f"dim_{app_id}_{table}_{column}_{value}")
            
            documents.append(doc)
            metadatas.append({
                "type": "dimension",
                "application": app_id,
                "table": table,
                "column": column,
                "value": str(value),
                "count": count,
                "full_path": f"{table}.{column}"
            })
            ids.append(doc_id)
        
        if documents:
            # Check if already exists and update
            try:
                collection.upsert(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                
                # Update cache timestamp
                cache_key = f"{app_id}_{table}_{column}"
                self._dimension_cache[cache_key] = datetime.now()
                
                logger.info(
                    f"Loaded {len(documents)} dimension values for "
                    f"{app_id}.{table}.{column}"
                )
            except Exception as e:
                logger.error(f"Failed to load dimension values: {e}")
    
    def _create_dimension_document(
        self,
        app_id: str,
        table: str,
        column: str,
        value: Any,
        count: int,
        context: Optional[str] = None
    ) -> str:
        """Create searchable document for dimension value."""
        parts = [
            f"Field: {table}.{column}",
            f"Value: {value}",
            f"Application: {app_id}",
        ]
        
        if context:
            parts.append(f"Context: {context}")
        
        if count > 0:
            parts.append(f"Appears in {count} records")
        
        return " | ".join(parts)
    
    def is_dimension_stale(self, app_id: str, table: str, column: str) -> bool:
        """Check if dimension cache is stale."""
        cache_key = f"{app_id}_{table}_{column}"
        if cache_key not in self._dimension_cache:
            return True
        
        age = datetime.now() - self._dimension_cache[cache_key]
        return age > self._cache_ttl
    
    # ==========================================================================
    # BUSINESS CONTEXT EMBEDDINGS
    # ==========================================================================
    
    def load_business_context(self, app_id: str, context_config: Dict[str, Any]):
        """
        Load business context (metrics, rules, sample queries).
        
        Args:
            app_id: Application identifier
            context_config: Parsed business_context section from YAML
        """
        collection = self.collections["business_context"]
        
        documents = []
        metadatas = []
        ids = []
        
        # Load metrics
        metrics = context_config.get("metrics", {})
        for metric_name, metric_def in metrics.items():
            doc = self._create_metric_document(app_id, metric_name, metric_def)
            doc_id = self._generate_id(f"metric_{app_id}_{metric_name}")
            
            documents.append(doc)
            metadatas.append({
                "type": "metric",
                "application": app_id,
                "metric_name": metric_name,
                "description": metric_def.get("description", "")
            })
            ids.append(doc_id)
        
        # Load sample queries
        sample_queries = context_config.get("sample_queries", [])
        for idx, query_def in enumerate(sample_queries):
            doc = self._create_sample_query_document(app_id, query_def)
            doc_id = self._generate_id(f"query_{app_id}_{idx}")
            
            documents.append(doc)
            metadatas.append({
                "type": "sample_query",
                "application": app_id,
                "query_name": query_def.get("name", f"Query {idx}"),
                "description": query_def.get("description", "")
            })
            ids.append(doc_id)
        
        if documents:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(
                f"Loaded {len(documents)} business context embeddings for app: {app_id}"
            )
    
    def _create_metric_document(
        self, app_id: str, metric_name: str, metric_def: Dict[str, Any]
    ) -> str:
        """Create searchable document for business metric."""
        parts = [
            f"Metric: {metric_name}",
            f"Application: {app_id}",
            f"Description: {metric_def.get('description', '')}",
        ]
        
        if "formula" in metric_def:
            parts.append(f"Formula: {metric_def['formula']}")
        
        if "tables" in metric_def:
            tables = metric_def["tables"]
            if isinstance(tables, list):
                parts.append(f"Uses tables: {', '.join(tables)}")
        
        return " | ".join(parts)
    
    def _create_sample_query_document(
        self, app_id: str, query_def: Dict[str, Any]
    ) -> str:
        """Create searchable document for sample query."""
        parts = [
            f"Query: {query_def.get('name', 'Unnamed')}",
            f"Application: {app_id}",
            f"Description: {query_def.get('description', '')}",
        ]
        
        if "use_case" in query_def:
            parts.append(f"Use case: {query_def['use_case']}")
        
        return " | ".join(parts)
    
    # ==========================================================================
    # SEARCH OPERATIONS
    # ==========================================================================
    
    def search_schema(
        self, query: str, app_id: Optional[str] = None, top_k: int = 5
    ) -> List[SearchResult]:
        """
        Search for relevant schema elements (tables/columns).
        
        Args:
            query: Natural language query
            app_id: Filter by application (optional)
            top_k: Number of results to return
            
        Returns:
            List of SearchResult objects
        """
        collection = self.collections["schema_metadata"]
        
        where = {"application": app_id} if app_id else None
        
        results = collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where
        )
        
        return self._format_results(results)
    
    def search_dimensions(
        self,
        query: str,
        app_id: Optional[str] = None,
        column_hint: Optional[str] = None,
        top_k: int = 3
    ) -> List[SearchResult]:
        """
        Search for dimension values.
        
        Args:
            query: Search term (e.g., "equity")
            app_id: Filter by application
            column_hint: Filter by column path (e.g., "funds.fund_type")
            top_k: Number of results
            
        Returns:
            List of SearchResult objects
        """
        collection = self.collections["dimension_values"]
        
        # ChromaDB requires where clause with single level dict
        where = None
        if app_id and column_hint:
            # Use $and operator for multiple conditions
            where = {
                "$and": [
                    {"application": app_id},
                    {"full_path": column_hint}
                ]
            }
        elif app_id:
            where = {"application": app_id}
        elif column_hint:
            where = {"full_path": column_hint}
        
        results = collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where
        )
        
        return self._format_results(results)
    
    def search_business_context(
        self, query: str, app_id: Optional[str] = None, top_k: int = 3
    ) -> List[SearchResult]:
        """
        Search business context (metrics, sample queries).
        
        Args:
            query: Natural language query
            app_id: Filter by application
            top_k: Number of results
            
        Returns:
            List of SearchResult objects
        """
        collection = self.collections["business_context"]
        
        where = {"application": app_id} if app_id else None
        
        results = collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where
        )
        
        return self._format_results(results)
    
    def _format_results(self, raw_results: Dict) -> List[SearchResult]:
        """Format ChromaDB results into SearchResult objects."""
        formatted = []
        
        if not raw_results["ids"] or not raw_results["ids"][0]:
            return formatted
        
        for idx, doc_id in enumerate(raw_results["ids"][0]):
            distance = raw_results["distances"][0][idx]
            score = 1.0 - distance  # Convert distance to similarity score
            
            formatted.append(SearchResult(
                content=raw_results["documents"][0][idx],
                metadata=raw_results["metadatas"][0][idx],
                distance=distance,
                score=score
            ))
        
        return formatted
    
    # ==========================================================================
    # UTILITIES
    # ==========================================================================
    
    def _generate_id(self, key: str) -> str:
        """Generate deterministic ID from key."""
        return hashlib.md5(key.encode()).hexdigest()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded embeddings."""
        stats = {}
        for name, collection in self.collections.items():
            stats[name] = collection.count()
        
        stats["dimension_cache_size"] = len(self._dimension_cache)
        stats["model"] = self.embedding_model
        
        return stats
