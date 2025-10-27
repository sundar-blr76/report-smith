"""
Hybrid Query Intent Analyzer for ReportSmith

Combines local entity mappings with LLM-based analysis for optimal results:
1. Check local term mappings first (fast, precise, free)
2. Use LLM for unknown terms and general understanding
3. Merge results for best accuracy

This gives you control over domain-specific terms while maintaining
flexibility for natural language queries.
"""

from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import yaml
from pathlib import Path

from ..logger import get_logger
from ..schema_intelligence.embedding_manager import EmbeddingManager
from .llm_intent_analyzer import LLMIntentAnalyzer, LLMQueryIntent, IntentType, TimeScope, AggregationType

logger = get_logger(__name__)


@dataclass
class LocalEntityMapping:
    """Local mapping for a known term."""
    term: str  # User's term (e.g., "AUM", "fees")
    canonical_name: str  # Database name
    entity_type: str  # table, column, dimension_value, metric
    table: Optional[str] = None
    column: Optional[str] = None
    value: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    description: Optional[str] = None
    context: Optional[str] = None


@dataclass
class EntityMappingConfig:
    """Configuration for local entity mappings."""
    tables: Dict[str, LocalEntityMapping] = field(default_factory=dict)
    columns: Dict[str, LocalEntityMapping] = field(default_factory=dict)
    dimension_values: Dict[str, LocalEntityMapping] = field(default_factory=dict)
    metrics: Dict[str, LocalEntityMapping] = field(default_factory=dict)
    business_terms: Dict[str, LocalEntityMapping] = field(default_factory=dict)


@dataclass
class EnrichedEntity:
    """Entity enriched with both local mappings and LLM/semantic search."""
    text: str
    entity_type: str
    canonical_name: Optional[str] = None  # From local mapping
    table: Optional[str] = None
    column: Optional[str] = None
    value: Optional[str] = None
    source: str = "llm"  # "local" or "llm" or "semantic"
    confidence: float = 0.0
    semantic_matches: List[Dict[str, Any]] = field(default_factory=list)
    local_mapping: Optional[LocalEntityMapping] = None
    
    def __str__(self):
        source_emoji = {"local": "📌", "llm": "🤖", "semantic": "🔍"}.get(self.source, "❓")
        parts = [f"{source_emoji} {self.text}"]
        if self.canonical_name and self.canonical_name != self.text:
            parts.append(f"→ {self.canonical_name}")
        parts.append(f"({self.entity_type}, conf: {self.confidence:.2f})")
        return " ".join(parts)


@dataclass
class HybridQueryIntent:
    """Query intent with hybrid analysis results."""
    original_query: str
    intent_type: IntentType
    entities: List[EnrichedEntity]
    time_scope: TimeScope
    aggregations: List[AggregationType]
    filters: List[str]
    limit: Optional[int]
    order_by: Optional[str]
    order_direction: str
    llm_reasoning: Optional[str] = None
    local_mappings_used: int = 0
    llm_entities_found: int = 0
    
    def __str__(self) -> str:
        parts = [
            f"Query: {self.original_query}",
            f"Intent: {self.intent_type.value}",
            f"Time Scope: {self.time_scope.value}",
            f"Analysis: {self.local_mappings_used} local + {self.llm_entities_found} LLM entities",
        ]
        
        if self.entities:
            parts.append(f"\nEntities ({len(self.entities)}):")
            for entity in self.entities:
                parts.append(f"  {entity}")
        
        if self.aggregations:
            parts.append(f"\nAggregations: {', '.join([a.value for a in self.aggregations])}")
        
        if self.filters:
            parts.append(f"Filters: {', '.join(self.filters)}")
        
        if self.llm_reasoning:
            parts.append(f"\nLLM Reasoning: {self.llm_reasoning}")
        
        return "\n".join(parts)


class HybridIntentAnalyzer:
    """
    Hybrid analyzer combining local mappings with LLM intelligence.
    
    Strategy:
    1. Load local entity mappings from YAML config
    2. Check query against local mappings first (fast, precise)
    3. Use LLM for intent classification and unknown entities
    4. Enrich with semantic search from embeddings
    5. Merge results prioritizing local mappings
    """
    
    def __init__(
        self,
        embedding_manager: EmbeddingManager,
        llm_analyzer: Optional[LLMIntentAnalyzer] = None,
        mappings_file: Optional[Path] = None
    ):
        """
        Initialize hybrid analyzer.
        
        Args:
            embedding_manager: Embedding manager for semantic search
            llm_analyzer: Optional LLM analyzer (created if not provided)
            mappings_file: Path to local entity mappings YAML
        """
        self.embedding_manager = embedding_manager
        self.llm_analyzer = llm_analyzer
        
        # Load local entity mappings
        self.mappings = self._load_mappings(mappings_file)
        
        # Build lookup indices for fast matching
        self._build_lookup_indices()
        
        logger.info(f"Initialized HybridIntentAnalyzer with {self._count_mappings()} local mappings")
    
    def _load_mappings(self, mappings_file: Optional[Path]) -> EntityMappingConfig:
        """Load local entity mappings from YAML file."""
        if not mappings_file:
            # Use default location
            project_root = Path(__file__).parent.parent.parent.parent
            mappings_file = project_root / "config" / "entity_mappings.yaml"
        else:
            # Convert to Path if string
            if isinstance(mappings_file, str):
                mappings_file = Path(mappings_file)
        
        if not mappings_file.exists():
            logger.warning(f"Entity mappings file not found: {mappings_file}")
            return EntityMappingConfig()
        
        try:
            with open(mappings_file, 'r') as f:
                data = yaml.safe_load(f) or {}
            
            config = EntityMappingConfig()
            
            # Parse mappings by type
            for entity_type in ['tables', 'columns', 'dimension_values', 'metrics', 'business_terms']:
                type_data = data.get(entity_type, {})
                mapping_dict = getattr(config, entity_type)
                
                for term, mapping_data in type_data.items():
                    mapping = LocalEntityMapping(
                        term=term,
                        canonical_name=mapping_data.get('canonical_name', term),
                        entity_type=entity_type.rstrip('s'),  # Remove plural
                        table=mapping_data.get('table'),
                        column=mapping_data.get('column'),
                        value=mapping_data.get('value'),
                        aliases=mapping_data.get('aliases', []),
                        description=mapping_data.get('description'),
                        context=mapping_data.get('context')
                    )
                    mapping_dict[term.lower()] = mapping
            
            # Count mappings for logging
            total_count = sum([
                len(config.tables),
                len(config.columns),
                len(config.dimension_values),
                len(config.metrics),
                len(config.business_terms)
            ])
            
            logger.info(f"Loaded {total_count} entity mappings from {mappings_file}")
            return config
            
        except Exception as e:
            logger.error(f"Failed to load entity mappings: {e}", exc_info=True)
            return EntityMappingConfig()
    
    def _build_lookup_indices(self):
        """Build fast lookup indices including aliases."""
        self.term_to_mapping: Dict[str, LocalEntityMapping] = {}
        
        for entity_type in ['tables', 'columns', 'dimension_values', 'metrics', 'business_terms']:
            mapping_dict = getattr(self.mappings, entity_type)
            
            for term, mapping in mapping_dict.items():
                # Add primary term
                self.term_to_mapping[term.lower()] = mapping
                
                # Add aliases
                for alias in mapping.aliases:
                    self.term_to_mapping[alias.lower()] = mapping
    
    def _count_mappings(self) -> int:
        """Count total mappings."""
        return sum([
            len(self.mappings.tables),
            len(self.mappings.columns),
            len(self.mappings.dimension_values),
            len(self.mappings.metrics),
            len(self.mappings.business_terms)
        ])
    
    def analyze(self, query: str, use_llm: bool = True) -> HybridQueryIntent:
        """
        Analyze query using hybrid approach.
        
        Args:
            query: Natural language query
            use_llm: Whether to use LLM (set False to use only local+semantic)
            
        Returns:
            HybridQueryIntent with merged results
        """
        logger.info(f"Analyzing query with hybrid approach: {query}")
        
        # Step 1: Extract local mappings from query
        local_entities = self._extract_local_entities(query)
        logger.info(f"Found {len(local_entities)} entities from local mappings")
        if local_entities:
            try:
                formatted = [
                    f"  - {e.text} -> {e.canonical_name or ''} ({e.entity_type})"
                    + (f" [table={e.table}, column={e.column}]" if (e.table or e.column) else "")
                    for e in local_entities
                ]
                logger.info("Local mapping hits:\n" + "\n".join(formatted))
            except Exception:
                logger.debug("Local mapping hits: (unserializable)")
        
        # Step 2: Get LLM analysis (if enabled and available)
        llm_intent = None
        if use_llm and self.llm_analyzer:
            try:
                llm_intent = self.llm_analyzer._extract_with_llm(query)
                # Capture latest LLM call metrics if available
                self.last_metrics = getattr(self.llm_analyzer, "last_metrics", None)
                self.metrics_events = getattr(self.llm_analyzer, "metrics_events", [])
                if self.last_metrics:
                    logger.info(
                        f"[llm] summary provider={self.last_metrics.get('provider')} model={self.last_metrics.get('model')} prompt_chars={self.last_metrics.get('prompt_chars')} latency_ms={self.last_metrics.get('latency_ms')}"
                    )
                logger.info(f"LLM found intent: {llm_intent.intent_type}, {len(llm_intent.entities)} entities")
            except Exception as e:
                self.last_metrics = {"error": str(e)}
                logger.warning(f"LLM analysis failed, using local only: {e}")
        
        # Step 3: Merge and enrich entities
        merged_entities = self._merge_entities(
            local_entities=local_entities,
            llm_entities=llm_intent.entities if llm_intent else [],
            query=query
        )
        
        # Step 4: Build final intent
        intent = HybridQueryIntent(
            original_query=query,
            intent_type=llm_intent.intent_type if llm_intent else IntentType.RETRIEVAL,
            entities=merged_entities,
            time_scope=llm_intent.time_scope if llm_intent else TimeScope.NONE,
            aggregations=llm_intent.aggregations if llm_intent else [],
            filters=llm_intent.filters if llm_intent else [],
            limit=llm_intent.limit if llm_intent else None,
            order_by=llm_intent.order_by if llm_intent else None,
            order_direction=llm_intent.order_direction if llm_intent else "ASC",
            llm_reasoning=llm_intent.reasoning if llm_intent else None,
            local_mappings_used=len(local_entities),
            llm_entities_found=len(llm_intent.entities) if llm_intent else 0
        )
        
        logger.info(f"Hybrid analysis complete: {len(merged_entities)} total entities")
        return intent
    
    def _extract_local_entities(self, query: str) -> List[EnrichedEntity]:
        """Extract entities using local mappings."""
        entities = []
        query_lower = query.lower()
        
        # Check for each known term in the query
        matched_terms = set()
        
        for term, mapping in self.term_to_mapping.items():
            # Check if term appears in query (whole word match)
            import re
            pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(pattern, query_lower):
                # Avoid duplicates from aliases
                key = (mapping.canonical_name, mapping.entity_type)
                if key not in matched_terms:
                    matched_terms.add(key)
                    
                    entities.append(EnrichedEntity(
                        text=term,
                        entity_type=mapping.entity_type,
                        canonical_name=mapping.canonical_name,
                        table=mapping.table,
                        column=mapping.column,
                        value=mapping.value,
                        source="local",
                        confidence=1.0,  # Local mappings are 100% confident
                        local_mapping=mapping
                    ))
        
        return entities
    
    def _merge_entities(
        self, 
        local_entities: List[EnrichedEntity],
        llm_entities: List[str],
        query: str
    ) -> List[EnrichedEntity]:
        """
        Merge local and LLM entities, enriching with semantic search.
        
        Priority: Local > LLM > Semantic
        """
        merged = []
        
        # Build set of all terms covered by local mappings (including variations)
        local_covered_terms = set()
        for entity in local_entities:
            # Add the matched term
            local_covered_terms.add(entity.text.lower())
            # Add canonical name
            if entity.canonical_name:
                local_covered_terms.add(entity.canonical_name.lower())
            # Add aliases from mapping
            if entity.local_mapping and entity.local_mapping.aliases:
                for alias in entity.local_mapping.aliases:
                    local_covered_terms.add(alias.lower())
        
        # Add all local entities first (highest priority)
        merged.extend(local_entities)
        
        # Process LLM entities that aren't already covered by local
        for llm_entity in llm_entities:
            llm_lower = llm_entity.lower()
            
            # Check if this entity (or close variant) is already covered
            is_covered = False
            for covered in local_covered_terms:
                # Exact match or substring match
                if llm_lower == covered or llm_lower in covered or covered in llm_lower:
                    is_covered = True
                    break
            
            if not is_covered:
                # Enrich with semantic search
                enriched = self._enrich_with_semantic_search(llm_entity, query)
                enriched.source = "llm"
                merged.append(enriched)
        
        # Sort by confidence (local=1.0 always first)
        merged.sort(key=lambda x: x.confidence, reverse=True)
        return merged
    
    def _enrich_with_semantic_search(self, entity_text: str, query: str) -> EnrichedEntity:
        """Enrich entity with semantic search results."""
        search_text = f"{query} {entity_text}"
        
        # Search across all collections
        schema_results = self.embedding_manager.search_schema(search_text, top_k=3)
        dim_results = self.embedding_manager.search_dimensions(search_text, top_k=3)
        
        all_matches = []
        best_confidence = 0.0
        best_type = "unknown"
        
        for result in schema_results:
            if result.score > 0.3:
                all_matches.append({
                    'content': result.content,
                    'metadata': result.metadata,
                    'score': result.score
                })
                if result.score > best_confidence:
                    best_confidence = result.score
                    best_type = result.metadata.get('type', 'schema')
        
        for result in dim_results:
            if result.score > 0.3:
                all_matches.append({
                    'content': result.content,
                    'metadata': result.metadata,
                    'score': result.score
                })
                if result.score > best_confidence:
                    best_confidence = result.score
                    best_type = 'dimension_value'
        
        return EnrichedEntity(
            text=entity_text,
            entity_type=best_type,
            source="semantic",
            confidence=best_confidence,
            semantic_matches=sorted(all_matches, key=lambda x: x['score'], reverse=True)
        )


# Example local mappings structure
EXAMPLE_MAPPINGS_YAML = """
# Entity Mappings for ReportSmith
# Define your domain-specific terms here for precise, fast matching

tables:
  funds:
    canonical_name: funds
    aliases: [fund, portfolio, portfolios]
    description: "Fund master table"
  
  clients:
    canonical_name: clients
    aliases: [client, customer, customers, investor, investors]
    description: "Client master data"

columns:
  aum:
    canonical_name: total_aum
    table: funds
    column: total_aum
    aliases: [assets, "assets under management", "managed assets"]
    description: "Total assets under management"
  
  fees:
    canonical_name: fee_amount
    table: fee_transactions
    column: fee_amount
    aliases: [fee, charges, "management fees"]
    description: "Fee amounts"

dimension_values:
  equity:
    canonical_name: Equity Growth
    table: funds
    column: fund_type
    value: Equity Growth
    aliases: [equities, stocks, "equity funds"]
    description: "Equity type funds"
  
  bond:
    canonical_name: Bond
    table: funds
    column: fund_type
    value: Bond
    aliases: [bonds, fixed-income, "bond funds"]
    description: "Bond funds"

metrics:
  total_aum:
    canonical_name: total_aum_metric
    entity_type: metric
    aliases: ["total assets", "total managed assets"]
    description: "Sum of all AUM across funds"
    context: "SUM(total_aum) FROM funds WHERE is_active = true"

business_terms:
  truepotential:
    canonical_name: TruePotential
    entity_type: company
    table: management_companies
    column: company_name
    value: TruePotential
    aliases: ["true potential", "tp"]
    description: "TruePotential management company"
"""
