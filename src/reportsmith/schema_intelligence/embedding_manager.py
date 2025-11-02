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
    
    def __init__(self, embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2", provider: str = "local", openai_api_key: Optional[str] = None):
        """
        Initialize embedding manager.
        
        Args:
            embedding_model: Name of embedding model to use
            provider: 'local' to use sentence-transformers, 'openai' to use OpenAI embeddings
            openai_api_key: API key for OpenAI when provider='openai'
        """
        self.embedding_model = embedding_model
        self.provider = provider
        
        # Initialize ChromaDB in-memory client
        self.client = chromadb.Client(ChromaSettings(
            anonymized_telemetry=False,
            allow_reset=True
        ))
        
        # Initialize embedding function based on provider
        if provider == "openai":
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY is required when provider='openai'")
            self.embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
                api_key=openai_api_key,
                model_name=embedding_model
            )
        else:
            self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=embedding_model
            )
        
        # Create collections
        self.collections: Dict[str, chromadb.Collection] = {}
        self._init_collections()
        
        # Cache for dimension embeddings (to track staleness)
        self._dimension_cache: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(hours=24)  # 24-hour staleness acceptable
        
        logger.info(f"Initialized EmbeddingManager with provider={provider} model={embedding_model}")
    
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
        
        **NEW STRATEGY**: Embed ONLY entity/synonym names (minimal text)
        Store all context, relationships, hints in metadata.
        Multiple embeddings per entity for better matching:
        - Primary name
        - Each synonym/alias
        - Description-based variants (if hints provided)
        
        Args:
            app_id: Application identifier (e.g., 'fund_accounting')
            schema_config: Parsed schema section from YAML
        """
        collection = self.collections["schema_metadata"]
        
        documents = []
        metadatas = []
        ids = []
        
        tables = schema_config.get("tables", {})
        relationships = schema_config.get("relationships", [])
        
        # Build relationship map for context
        rel_map = {}  # table -> list of related tables
        for rel in relationships:
            from_t = rel.get("from_table", "")
            to_t = rel.get("to_table", "")
            rel_map.setdefault(from_t, []).append({
                "to_table": to_t,
                "type": rel.get("type", ""),
                "from_column": rel.get("from_column", ""),
                "to_column": rel.get("to_column", "")
            })
            # bidirectional
            rel_map.setdefault(to_t, []).append({
                "to_table": from_t,
                "type": rel.get("type", ""),
                "from_column": rel.get("to_column", ""),
                "to_column": rel.get("from_column", "")
            })
        
        for table_name, table_def in tables.items():
            # Base metadata: full schema info + relationships
            related_tables = rel_map.get(table_name, [])
            # Serialize lists to JSON strings for ChromaDB compatibility
            import json as json_module
            base_table_meta = {
                "entity_type": "table",
                "entity_name": table_name,
                "application": app_id,
                "table": table_name,
                "description": table_def.get("description", ""),
                "primary_key": table_def.get("primary_key", ""),
                "estimated_rows": table_def.get("estimated_rows", 0),
                # Store as JSON strings (ChromaDB doesn't support list metadata)
                "related_tables_json": json_module.dumps([r["to_table"] for r in related_tables]),
                "relationships_json": json_module.dumps(related_tables)
            }
            
            # Embedding 1: Table name ONLY (exact match)
            documents.append(table_name)
            metadatas.append({**base_table_meta, "match_type": "primary", "embedded_text": table_name})
            ids.append(self._generate_id(f"table_{app_id}_{table_name}_primary"))
            
            # Embedding 2-N: Each synonym (one embedding each)
            synonyms = table_def.get("synonyms") or table_def.get("aliases") or []
            if isinstance(synonyms, list):
                for idx, syn in enumerate(synonyms):
                    syn_str = str(syn).strip()
                    if syn_str:
                        documents.append(syn_str)
                        metadatas.append({
                            **base_table_meta,
                            "match_type": "synonym",
                            "synonym": syn_str,
                            "embedded_text": syn_str
                        })
                        ids.append(self._generate_id(f"table_{app_id}_{table_name}_syn{idx}"))
            
            # Embed each column with same minimal strategy
            columns = table_def.get("columns", {})
            for col_name, col_def in columns.items():
                # Gather column metadata (NOT in embedding text)
                # ChromaDB doesn't support list metadata, so we serialize to JSON
                base_col_meta = {
                    "entity_type": "column",
                    "entity_name": col_name,
                    "application": app_id,
                    "table": table_name,
                    "column": col_name,
                    "full_path": f"{table_name}.{col_name}",
                    "data_type": col_def.get("type", ""),
                    "description": col_def.get("description", ""),
                    "nullable": col_def.get("nullable", True),
                    "is_dimension": col_def.get("is_dimension", False),
                    "related_tables_json": json_module.dumps([r["to_table"] for r in related_tables])
                }
                
                # Embedding 1: Column name ONLY
                documents.append(col_name)
                metadatas.append({**base_col_meta, "match_type": "primary", "embedded_text": col_name})
                ids.append(self._generate_id(f"column_{app_id}_{table_name}_{col_name}_primary"))
                
                # Embedding 2-N: Each synonym (minimal)
                col_synonyms = col_def.get("synonyms") or col_def.get("aliases") or []
                if isinstance(col_synonyms, list):
                    for idx, syn in enumerate(col_synonyms):
                        syn_str = str(syn).strip()
                        if syn_str:
                            documents.append(syn_str)
                            metadatas.append({
                                **base_col_meta,
                                "match_type": "synonym",
                                "synonym": syn_str,
                                "embedded_text": syn_str
                            })
                            ids.append(self._generate_id(f"column_{app_id}_{table_name}_{col_name}_syn{idx}"))
        
        # Add to collection in batch
        if documents:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(
                f"Loaded {len(documents)} minimal name-only embeddings for app: {app_id}"
            )
    
    # ==========================================================================
    # DIMENSION VALUE EMBEDDINGS
    # ==========================================================================
    
    def load_dimension_values(
        self,
        app_id: str,
        table: str,
        column: str,
        values: List[Dict[str, Any]],
        context: Optional[str] = None,
        synonyms: Optional[Dict[str, List[str]]] = None
    ):
        """
        Load dimension values from database query results.
        
        **NEW STRATEGY**: Embed ONLY the value name (minimal)
        Store domain metadata and column/table context in metadata.
        Support synonym embeddings for common variations.
        
        Args:
            app_id: Application identifier
            table: Table name
            column: Column name
            values: List of dicts with 'value' and 'count' keys
            context: Optional business context/description
            synonyms: Optional dict mapping value -> list of synonyms
        """
        collection = self.collections["dimension_values"]
        
        documents = []
        metadatas = []
        ids = []
        
        for item in values:
            value = item["value"]
            count = item.get("count", 0)
            value_str = str(value).strip()
            
            if not value_str:
                continue
            
            # Base metadata (full context, NOT in embedding)
            base_meta = {
                "entity_type": "dimension_value",
                "entity_name": value_str,
                "application": app_id,
                "table": table,
                "column": column,
                "value": value_str,
                "count": count,
                "full_path": f"{table}.{column}",
                "context": context or ""
            }
            
            # Embedding 1: Value name ONLY (primary)
            documents.append(value_str)
            metadatas.append({**base_meta, "match_type": "primary", "embedded_text": value_str})
            ids.append(self._generate_id(f"dim_{app_id}_{table}_{column}_{value}_primary"))
            
            # Embedding 2-N: Synonyms (if provided)
            if synonyms and value_str in synonyms:
                for idx, syn in enumerate(synonyms[value_str]):
                    syn_str = str(syn).strip()
                    if syn_str and syn_str != value_str:
                        documents.append(syn_str)
                        metadatas.append({
                            **base_meta,
                            "match_type": "synonym",
                            "synonym": syn_str,
                            "embedded_text": syn_str
                        })
                        ids.append(self._generate_id(f"dim_{app_id}_{table}_{column}_{value}_syn{idx}"))
        
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
                    f"Loaded {len(documents)} minimal name-only dimension embeddings for "
                    f"{app_id}.{table}.{column}"
                )
            except Exception as e:
                logger.error(f"Failed to load dimension values: {e}")
    
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
        
        **NEW STRATEGY**: Embed ONLY metric/query names (minimal),
        store full definitions and formulas in metadata.
        
        Args:
            app_id: Application identifier
            context_config: Parsed business_context section from YAML
        """
        collection = self.collections["business_context"]
        
        documents = []
        metadatas = []
        ids = []
        
        # Load metrics - embed ONLY metric name
        metrics = context_config.get("metrics", {})
        for metric_name, metric_def in metrics.items():
            # ChromaDB doesn't support list metadata, serialize to JSON
            import json as json_module
            base_meta = {
                "entity_type": "metric",
                "entity_name": metric_name,
                "application": app_id,
                "metric_name": metric_name,
                "description": metric_def.get("description", ""),
                "formula": metric_def.get("formula", ""),
                "tables_json": json_module.dumps(metric_def.get("tables", []))
            }
            
            # Embedding 1: Metric name ONLY
            documents.append(metric_name)
            metadatas.append({**base_meta, "match_type": "primary", "embedded_text": metric_name})
            ids.append(self._generate_id(f"metric_{app_id}_{metric_name}_primary"))
            
            # Embedding 2-N: Each synonym
            synonyms = metric_def.get("synonyms") or metric_def.get("aliases") or []
            if isinstance(synonyms, list):
                for idx, syn in enumerate(synonyms):
                    syn_str = str(syn).strip()
                    if syn_str:
                        documents.append(syn_str)
                        metadatas.append({
                            **base_meta,
                            "match_type": "synonym",
                            "synonym": syn_str,
                            "embedded_text": syn_str
                        })
                        ids.append(self._generate_id(f"metric_{app_id}_{metric_name}_syn{idx}"))
        
        # Load sample queries - embed ONLY query name
        sample_queries = context_config.get("sample_queries", [])
        for idx, query_def in enumerate(sample_queries):
            query_name = query_def.get("name", f"Query {idx}")
            documents.append(query_name)
            metadatas.append({
                "entity_type": "sample_query",
                "entity_name": query_name,
                "application": app_id,
                "query_name": query_name,
                "description": query_def.get("description", ""),
                "match_type": "primary",
                "embedded_text": query_name
            })
            ids.append(self._generate_id(f"query_{app_id}_{idx}"))
        
        if documents:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(
                f"Loaded {len(documents)} minimal name-only business embeddings for app: {app_id}"
            )
    
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
