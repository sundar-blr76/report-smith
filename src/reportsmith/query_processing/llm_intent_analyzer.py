"""
LLM-based Query Intent Analyzer for ReportSmith

Uses OpenAI/Anthropic with structured output for robust intent extraction.
Much simpler and more maintainable than pattern-based approach.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
from pydantic import BaseModel, Field
import json
import os

from ..logger import get_logger
from ..schema_intelligence.embedding_manager import EmbeddingManager

logger = get_logger(__name__)


class IntentType(str, Enum):
    """Types of query intents."""
    RETRIEVAL = "retrieval"
    AGGREGATION = "aggregation"
    FILTERING = "filtering"
    COMPARISON = "comparison"
    RANKING = "ranking"
    TREND = "trend"


class TimeScope(str, Enum):
    """Time-based scopes for queries."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    YTD = "year_to_date"
    MTD = "month_to_date"
    CUSTOM = "custom"
    NONE = "none"


class AggregationType(str, Enum):
    """Types of aggregations."""
    SUM = "sum"
    COUNT = "count"
    AVERAGE = "avg"
    MIN = "min"
    MAX = "max"
    DISTINCT_COUNT = "count_distinct"


class EntityMatch(BaseModel):
    """An entity matched from the query."""
    text: str = Field(description="The text that matched")
    entity_type: str = Field(description="Type: table, column, dimension_value, metric")
    table: Optional[str] = Field(None, description="Table name if applicable")
    column: Optional[str] = Field(None, description="Column name if applicable")
    value: Optional[str] = Field(None, description="Value if dimension")
    confidence: float = Field(description="Confidence score 0-1")


class LLMQueryIntent(BaseModel):
    """Structured query intent from LLM."""
    intent_type: IntentType = Field(description="Primary intent of the query")
    entities: List[str] = Field(default_factory=list, description="Key entities mentioned (tables, columns, values)")
    time_scope: TimeScope = Field(default=TimeScope.NONE, description="Temporal scope if any")
    aggregations: List[AggregationType] = Field(default_factory=list, description="Aggregation operations needed")
    filters: List[str] = Field(default_factory=list, description="Filter conditions")
    limit: Optional[int] = Field(None, description="Limit/TOP N if specified")
    order_by: Optional[str] = Field(None, description="What to order by")
    order_direction: str = Field(default="ASC", description="ASC or DESC")
    reasoning: str = Field(description="Brief explanation of the analysis")


@dataclass
class EnrichedEntity:
    """Entity enriched with semantic search results."""
    text: str
    entity_type: str
    semantic_matches: List[Dict[str, Any]]
    confidence: float
    
    def __str__(self):
        return f"{self.text} ({self.entity_type}, conf: {self.confidence:.2f})"


@dataclass
class QueryIntent:
    """Final query intent with enriched entities."""
    original_query: str
    intent_type: IntentType
    entities: List[EnrichedEntity]
    time_scope: TimeScope
    aggregations: List[AggregationType]
    filters: List[str]
    limit: Optional[int]
    order_by: Optional[str]
    order_direction: str
    llm_reasoning: str
    
    def __str__(self) -> str:
        parts = [
            f"Query: {self.original_query}",
            f"Intent: {self.intent_type.value}",
            f"Time Scope: {self.time_scope.value}",
        ]
        
        if self.entities:
            parts.append(f"\nEntities ({len(self.entities)}):")
            for entity in self.entities:
                parts.append(f"  - {entity}")
        
        if self.aggregations:
            parts.append(f"\nAggregations: {', '.join([a.value for a in self.aggregations])}")
        
        if self.filters:
            parts.append(f"Filters: {', '.join(self.filters)}")
        
        if self.limit:
            parts.append(f"Limit: {self.limit}")
        
        if self.llm_reasoning:
            parts.append(f"\nReasoning: {self.llm_reasoning}")
        
        return "\n".join(parts)


class LLMIntentAnalyzer:
    """
    LLM-based intent analyzer using structured output.
    
    Much simpler and more maintainable than pattern-based approach.
    Uses OpenAI or Anthropic with JSON schema for reliable extraction.
    """
    
    SYSTEM_PROMPT = """You are a SQL query intent analyzer for a financial data system.

Your task is to analyze natural language queries and extract structured information:
1. Primary intent (retrieval, aggregation, filtering, comparison, ranking, trend)
2. Key entities mentioned (tables, columns, dimension values)
3. Time scope (daily, monthly, yearly, etc.)
4. Aggregation operations (sum, count, average, etc.)
5. Filter conditions
6. Limit/ordering requirements

Be precise and extract only what's explicitly mentioned or clearly implied.
For entities, use the exact terms from the query when possible."""

    def __init__(
        self, 
        embedding_manager: EmbeddingManager,
        llm_provider: str = "gemini",  # "openai", "anthropic", or "gemini"
        model: str = None,
        api_key: str = None,
        max_search_results: int = 100,
        schema_score_threshold: float = 0.3,
        dimension_score_threshold: float = 0.3,
        context_score_threshold: float = 0.4,
        max_matches_warning: int = 20
    ):
        """
        Initialize LLM-based intent analyzer.
        
        Args:
            embedding_manager: Embedding manager for semantic search
            llm_provider: "openai", "anthropic", or "gemini"
            model: Model name (defaults based on provider)
            api_key: API key (or uses env var)
            max_search_results: Maximum results to retrieve from semantic search (default: 100)
            schema_score_threshold: Minimum score for schema matches (default: 0.3)
            dimension_score_threshold: Minimum score for dimension matches (default: 0.3)
            context_score_threshold: Minimum score for business context matches (default: 0.4)
            max_matches_warning: Warn user if matches exceed this count (default: 20)
        """
        self.embedding_manager = embedding_manager
        self.llm_provider = llm_provider
        
        # Search configuration
        self.max_search_results = max_search_results
        # Observability settings
        self.debug_prompts = (os.getenv("LLM_DEBUG_PROMPTS", "false").lower() in ("1", "true", "yes"))
        self.max_log_chars = int(os.getenv("LLM_DEBUG_MAX_CHARS", "500") or 500)
        self.metrics_events: list[dict] = []

        self.schema_score_threshold = schema_score_threshold
        self.dimension_score_threshold = dimension_score_threshold
        self.context_score_threshold = context_score_threshold
        self.max_matches_warning = max_matches_warning
        
        # Setup LLM client
        if llm_provider == "openai":
            import openai
            self.model = model or "gpt-4o-mini"  # Fast and cheap
            self.client = openai.OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        elif llm_provider == "anthropic":
            import anthropic
            self.model = model or "claude-3-haiku-20240307"  # Fast and cheap
            self.client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        elif llm_provider == "gemini":
            import google.generativeai as genai
            api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            genai.configure(api_key=api_key)
            self.model = model or "gemini-2.5-flash"  # Fast and FREE!
            self.client = genai.GenerativeModel(self.model)
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")
        
        logger.info(f"Initialized LLM Intent Analyzer with {llm_provider}/{self.model}")
    
    def analyze(self, query: str) -> QueryIntent:
        """
        Analyze a natural language query using LLM.
        
        Args:
            query: Natural language query
            
        Returns:
            QueryIntent with extracted and enriched information
        """
        logger.info(f"Analyzing query with LLM: {query}")
        
        # Step 1: Get structured intent from LLM
        llm_intent = self._extract_with_llm(query)
        
        # Step 2: Enrich entities with semantic search
        enriched_entities = self._enrich_entities(llm_intent.entities, query)
        
        # Step 3: Build final intent object
        intent = QueryIntent(
            original_query=query,
            intent_type=llm_intent.intent_type,
            entities=enriched_entities,
            time_scope=llm_intent.time_scope,
            aggregations=llm_intent.aggregations,
            filters=llm_intent.filters,
            limit=llm_intent.limit,
            order_by=llm_intent.order_by,
            order_direction=llm_intent.order_direction,
            llm_reasoning=llm_intent.reasoning
        )
        
        logger.info(f"Extracted: {llm_intent.intent_type.value}, {len(enriched_entities)} entities")
        return intent
    
    def _extract_with_llm(self, query: str) -> LLMQueryIntent:
        """Extract intent using LLM with structured output."""
        import time
        t0 = time.perf_counter()
        prompt_chars = 0
        self.last_metrics = None
        
        logger.info(f"LLM Intent Extraction Request for query: '{query}'")
        logger.debug(f"Request - Provider: {self.llm_provider}, Model: {self.model}")
        
        if self.llm_provider == "openai":
            def _trunc(s: str) -> str:
                if not isinstance(s, str):
                    return str(s)
                if len(s) <= getattr(self, 'max_log_chars', 500):
                    return s
                return s[: getattr(self, 'max_log_chars', 500)] + f"... [truncated {len(s) - getattr(self, 'max_log_chars', 500)} chars]"
            request_payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": f"Analyze this query: {query}"}
                ],
                "response_format": "LLMQueryIntent (structured output)",
                "temperature": 0
            }
            prompt_chars = sum(len(m["content"]) for m in request_payload["messages"]) if request_payload.get("messages") else 0
            if self.debug_prompts:
                logger.debug(f"OpenAI Prompt (trunc): {_trunc(json.dumps(request_payload, indent=2))}")
            
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": f"Analyze this query: {query}"}
                ],
                response_format=LLMQueryIntent,
                temperature=0
            )
            
            logger.debug(f"OpenAI Intent Extraction Response Metadata - Model: {response.model}, Usage: {response.usage}")
            parsed_result = response.choices[0].message.parsed
            dt_ms = (time.perf_counter() - t0) * 1000.0
            metrics = {
                "stage": "intent",
                "provider": "openai",
                "model": self.model,
                "prompt_chars": prompt_chars,
                "latency_ms": round(dt_ms, 2),
                "tokens": getattr(response, "usage", None),
            }
            self.last_metrics = metrics
            self.metrics_events.append(metrics)
            logger.info(f"LLM summary: provider=openai model={self.model} prompt_chars={prompt_chars} latency_ms={dt_ms:.1f}")
            if self.debug_prompts:
                logger.debug(f"OpenAI Parsed (trunc): {_trunc(parsed_result.model_dump_json(indent=2))}")
            
            return parsed_result
        
        elif self.llm_provider == "anthropic":
            # Anthropic doesn't have native structured output yet, so we use JSON mode
            schema_description = LLMQueryIntent.model_json_schema()
            
            user_content = f"""Analyze this query and return a JSON object matching this schema:
{json.dumps(schema_description, indent=2)}

Query: {query}

Return only valid JSON, no other text."""
            
            request_payload = {
                "model": self.model,
                "max_tokens": 1024,
                "temperature": 0,
                "system": self.SYSTEM_PROMPT,
                "messages": [{
                    "role": "user",
                    "content": user_content
                }]
            }
            logger.debug(f"Anthropic Intent Extraction Request Payload: {json.dumps({k: v if k != 'messages' else '[see user_content]' for k, v in request_payload.items()}, indent=2)}")
            if self.debug_prompts:
                logger.debug(f"Anthropic Prompt (trunc): {_trunc(user_content)}")
            prompt_chars = len(user_content) + len(self.SYSTEM_PROMPT)
            
            response = self.client.messages.create(**request_payload)
            
            # Parse JSON response
            json_text = response.content[0].text
            logger.debug(f"Anthropic Raw Response: {json_text}")
            logger.debug(f"Anthropic Response Metadata - Model: {response.model}, Usage: {response.usage}")
            
            # Clean up markdown if present
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            
            intent_data = json.loads(json_text)
            logger.info(f"Anthropic Intent Extraction Result: {json.dumps(intent_data, indent=2)}")
            dt_ms = (time.perf_counter() - t0) * 1000.0
            metrics = {
                "stage": "intent",
                "provider": "anthropic",
                "model": self.model,
                "prompt_chars": prompt_chars,
                "latency_ms": round(dt_ms, 2),
                "tokens": getattr(response, "usage", None),
            }
            self.last_metrics = metrics
            self.metrics_events.append(metrics)
            logger.info(f"LLM summary: provider=anthropic model={self.model} prompt_chars={prompt_chars} latency_ms={dt_ms:.1f}")
            
            return LLMQueryIntent(**intent_data)
        
        elif self.llm_provider == "gemini":
            # Gemini uses JSON schema for structured output
            schema_description = LLMQueryIntent.model_json_schema()
            
            prompt = f"""{self.SYSTEM_PROMPT}

Analyze this query and return a JSON object matching this schema:
{json.dumps(schema_description, indent=2)}

Query: {query}

Return only valid JSON, no other text."""
            
            generation_config = {
                "temperature": 0,
                "response_mime_type": "application/json",
            }
            prompt_chars = len(prompt)
            logger.debug(f"Gemini Intent Extraction Request - Prompt length: {len(prompt)} chars")
            logger.debug(f"Gemini Intent Extraction Request - Generation config: {json.dumps(generation_config, indent=2)}")
            if self.debug_prompts:
                logger.debug(f"Gemini Prompt (trunc): {_trunc(prompt)}")
            
            response = self.client.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Parse JSON response
            json_text = response.text
            logger.debug(f"Gemini Raw Response: {json_text}")
            logger.debug(f"Gemini Response Metadata - Candidates: {len(response.candidates)}")
            if hasattr(response, 'usage_metadata'):
                logger.debug(f"Gemini Usage: {response.usage_metadata}")
            
            intent_data = json.loads(json_text)
            logger.info(f"Gemini Intent Extraction Result: {json.dumps(intent_data, indent=2)}")
            dt_ms = (time.perf_counter() - t0) * 1000.0
            # Gemini has usage_metadata with token counts sometimes
            tokens = getattr(response, "usage_metadata", None)
            metrics = {
                "stage": "intent",
                "provider": "gemini",
                "model": self.model,
                "prompt_chars": prompt_chars,
                "latency_ms": round(dt_ms, 2),
                "tokens": tokens,
                "response_chars": len(json_text) if isinstance(json_text, str) else None,
            }
            self.last_metrics = metrics
            self.metrics_events.append(metrics)
            logger.info(f"LLM summary: provider=gemini model={self.model} prompt_chars={prompt_chars} latency_ms={dt_ms:.1f}")
            if self.debug_prompts:
                logger.debug(f"Gemini Parsed (trunc): {_trunc(json.dumps(intent_data, indent=2))}")
            
            return LLMQueryIntent(**intent_data)
    
    def _enrich_entities(self, entity_texts: List[str], query: str) -> List[EnrichedEntity]:
        """
        Enrich LLM-extracted entities with semantic search.
        
        Uses a large search limit and filters by semantic score thresholds
        rather than arbitrary top_k limits. This ensures we don't miss
        relevant matches due to artificial cutoffs.
        
        Args:
            entity_texts: List of entity texts extracted by LLM
            query: Original user query for context
            
        Returns:
            List of enriched entities with semantic matches
        """
        enriched = []
        
        # For each entity, do semantic search
        for entity_text in entity_texts:
            search_text = f"{query} {entity_text}"  # Use full query context
            
            # Cast a wide net with max_search_results, then filter by score
            # This avoids missing relevant matches due to arbitrary limits
            schema_results = self.embedding_manager.search_schema(
                search_text, top_k=self.max_search_results
            )
            dim_results = self.embedding_manager.search_dimensions(
                search_text, top_k=self.max_search_results
            )
            context_results = self.embedding_manager.search_business_context(
                search_text, top_k=self.max_search_results
            )
            
            # Filter by score thresholds - only keep semantically relevant matches
            all_matches = []
            best_confidence = 0.0
            best_type = "unknown"
            
            # Process schema results
            for result in schema_results:
                if result.score >= self.schema_score_threshold:
                    all_matches.append({
                        'content': result.content,
                        'metadata': result.metadata,
                        'score': result.score,
                        'type': 'schema'
                    })
                    if result.score > best_confidence:
                        best_confidence = result.score
                        best_type = result.metadata.get('type', 'schema')
            
            # Process dimension results
            for result in dim_results:
                if result.score >= self.dimension_score_threshold:
                    all_matches.append({
                        'content': result.content,
                        'metadata': result.metadata,
                        'score': result.score,
                        'type': 'dimension_value'
                    })
                    if result.score > best_confidence:
                        best_confidence = result.score
                        best_type = 'dimension_value'
            
            # Process business context results
            for result in context_results:
                if result.score >= self.context_score_threshold:
                    all_matches.append({
                        'content': result.content,
                        'metadata': result.metadata,
                        'score': result.score,
                        'type': 'business_context'
                    })
                    if result.score > best_confidence:
                        best_confidence = result.score
                        best_type = 'business_context'
            
            if all_matches:
                # Sort matches by score
                all_matches.sort(key=lambda x: x['score'], reverse=True)
                
                # Refine matches using LLM to drop contextually irrelevant ones
                # Example: "equity products" should not match "equity derivatives"
                refined_matches = self._llm_refine_matches(
                    entity_text=entity_text,
                    query=query,
                    matches=all_matches
                )
                
                # Warn if too many matches (query might be too broad)
                if len(refined_matches) > self.max_matches_warning:
                    logger.warning(
                        f"Entity '{entity_text}' has {len(refined_matches)} matches "
                        f"(>{self.max_matches_warning}). Query may be too broad. "
                        f"Consider being more specific."
                    )
                
                if refined_matches:  # Only add if we have matches after LLM filtering
                    enriched.append(EnrichedEntity(
                        text=entity_text,
                        entity_type=best_type,
                        semantic_matches=refined_matches,
                        confidence=best_confidence
                    ))
        
        # Sort by confidence
        enriched.sort(key=lambda x: x.confidence, reverse=True)
        return enriched
    
    def _llm_refine_matches(
        self, 
        entity_text: str, 
        query: str, 
        matches: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Use LLM to refine semantic matches and drop contextually irrelevant ones.
        
        Semantic similarity alone can match related but incorrect items.
        For example: "equity products" might semantically match "equity derivatives",
        but in context, the user might want general equity funds, not derivatives.
        
        The LLM can understand context and filter out such false positives.
        
        Args:
            entity_text: The entity being searched for
            query: The original user query
            matches: List of semantic matches with scores
            
        Returns:
            Filtered list of matches that are contextually relevant
        """
        if not matches:
            return matches
        
        # Prepare match descriptions for LLM
        match_descriptions = []
        for idx, match in enumerate(matches):
            match_descriptions.append({
                'index': idx,
                'content': match['content'],
                'type': match['type'],
                'score': match['score']
            })
        
        # Build prompt for LLM refinement
        refinement_prompt = f"""Given the user's query: "{query}"

They are looking for: "{entity_text}"

Here are the semantic matches found (sorted by similarity score):

{json.dumps(match_descriptions, indent=2)}

Your task: Identify which matches are TRULY relevant to what the user is asking for.

Some matches may be semantically similar but contextually wrong. For example:
- If user asks for "equity products", matches for "equity derivatives" might be too specific
- If user asks for "bond funds", matches for "bond ETFs" might not be what they want
- Consider the full query context, not just the entity in isolation

Return a JSON object with:
{{
  "relevant_indices": [list of indices that are truly relevant],
  "reasoning": "brief explanation of your filtering decisions"
}}

Be conservative - when in doubt, keep the match. Only drop clearly irrelevant ones."""

        try:
            # Log the request payload
            logger.info(f"LLM Refinement Request for entity: '{entity_text}'")
            logger.debug(f"Request - Provider: {self.llm_provider}, Model: {self.model}")
            logger.debug(f"Request - Query: {query}")
            logger.debug(f"Request - Matches count: {len(matches)}")
            logger.debug(f"Request - Prompt:\n{refinement_prompt}")
            
            if self.llm_provider == "openai":
                request_payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a semantic match filter for a database query system."},
                        {"role": "user", "content": refinement_prompt}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0
                }
                logger.debug(f"OpenAI Request Payload: {json.dumps(request_payload, indent=2)}")
                
                response = self.client.chat.completions.create(**request_payload)
                
                response_content = response.choices[0].message.content
                logger.debug(f"OpenAI Raw Response: {response_content}")
                logger.debug(f"OpenAI Response Metadata - Model: {response.model}, Usage: {response.usage}")
                
                result = json.loads(response_content)
                
            elif self.llm_provider == "anthropic":
                request_payload = {
                    "model": self.model,
                    "max_tokens": 1000,
                    "messages": [
                        {"role": "user", "content": refinement_prompt}
                    ],
                    "temperature": 0
                }
                logger.debug(f"Anthropic Request Payload: {json.dumps(request_payload, indent=2)}")
                
                response = self.client.messages.create(**request_payload)
                
                # Extract JSON from response
                content = response.content[0].text
                logger.debug(f"Anthropic Raw Response: {content}")
                logger.debug(f"Anthropic Response Metadata - Model: {response.model}, Usage: {response.usage}")
                
                # Find JSON in the response
                start = content.find('{')
                end = content.rfind('}') + 1
                if start >= 0 and end > start:
                    result = json.loads(content[start:end])
                else:
                    result = json.loads(content)
                    
            elif self.llm_provider == "gemini":
                generation_config = {
                    'temperature': 0,
                    'response_mime_type': 'application/json'
                }
                logger.debug(f"Gemini Request - Prompt length: {len(refinement_prompt)} chars")
                logger.debug(f"Gemini Request - Generation config: {json.dumps(generation_config, indent=2)}")
                
                response = self.client.generate_content(
                    refinement_prompt,
                    generation_config=generation_config
                )
                
                logger.debug(f"Gemini Raw Response: {response.text}")
                logger.debug(f"Gemini Response Metadata - Candidates: {len(response.candidates)}")
                if hasattr(response, 'usage_metadata'):
                    logger.debug(f"Gemini Usage: {response.usage_metadata}")
                
                result = json.loads(response.text)
            
            # Log the parsed result
            logger.info(f"LLM Refinement Result: {json.dumps(result, indent=2)}")
            
            # Filter matches based on LLM decision
            relevant_indices = set(result.get('relevant_indices', []))
            reasoning = result.get('reasoning', 'No reasoning provided')
            
            logger.info(
                f"LLM refinement for '{entity_text}': kept {len(relevant_indices)}/{len(matches)} matches. "
                f"Reasoning: {reasoning}"
            )
            
            # Return only relevant matches
            refined = [matches[i] for i in relevant_indices if i < len(matches)]
            
            if not refined:
                logger.warning(
                    f"LLM filtered out ALL matches for '{entity_text}'. "
                    f"Falling back to original {len(matches)} matches."
                )
                return matches
            
            logger.debug(f"Returning {len(refined)} refined matches out of {len(matches)} original matches")
            return refined
            
        except Exception as e:
            # If LLM refinement fails, log warning and return original matches
            logger.error(f"LLM refinement failed for '{entity_text}': {e}")
            logger.debug(f"Exception details:", exc_info=True)
            logger.warning(f"Using all {len(matches)} original matches due to LLM failure")
            return matches


# Example usage
EXAMPLE_QUERIES = [
    "Show monthly fees for all TruePotential equity funds",
    "What is the total AUM for bond funds?",
    "List top 10 clients by account balance",
    "Compare performance of equity vs bond funds",
    "Show daily transactions for account 12345",
    "What are the average fees by fund type?",
    "Find all high risk funds with AUM over 100M",
]
