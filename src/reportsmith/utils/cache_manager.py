"""
Cache Manager - Comprehensive caching solution for ReportSmith

Provides multi-level caching for:
1. LLM responses (intent extraction, domain value matching, SQL refinement)
2. Semantic search results (embeddings + search results)
3. SQL query results
4. Schema metadata lookups

Cache Layers:
- L1: In-memory LRU cache (per-request, fastest)
- L2: Redis cache (persistent, cross-request)
- L3: Disk cache (fallback, large objects)
"""

import hashlib
import json
import os
import pickle
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from ..logger import get_logger

logger = get_logger(__name__)

# Try to import redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.debug("Redis not available - persistent caching disabled")


@dataclass
class CacheStats:
    """Statistics for cache performance."""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    evictions: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def __str__(self) -> str:
        return (
            f"CacheStats(hits={self.hits}, misses={self.misses}, "
            f"hit_rate={self.hit_rate:.2%}, sets={self.sets}, evictions={self.evictions})"
        )


class LRUCache:
    """Thread-safe LRU cache with TTL support."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize LRU cache.
        
        Args:
            max_size: Maximum number of entries
            default_ttl: Default TTL in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict = OrderedDict()
        self.expiry: Dict[str, float] = {}
        self.stats = CacheStats()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self.cache:
            self.stats.misses += 1
            return None
        
        # Check expiry
        if key in self.expiry and time.time() > self.expiry[key]:
            self.cache.pop(key)
            self.expiry.pop(key)
            self.stats.misses += 1
            self.stats.evictions += 1
            return None
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        self.stats.hits += 1
        return self.cache[key]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache."""
        if key in self.cache:
            self.cache.pop(key)
        
        self.cache[key] = value
        self.cache.move_to_end(key)
        
        # Set expiry
        ttl = ttl or self.default_ttl
        self.expiry[key] = time.time() + ttl
        
        self.stats.sets += 1
        
        # Evict oldest if over capacity
        if len(self.cache) > self.max_size:
            oldest_key = next(iter(self.cache))
            self.cache.pop(oldest_key)
            self.expiry.pop(oldest_key, None)
            self.stats.evictions += 1
    
    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        self.expiry.clear()
    
    def size(self) -> int:
        """Get current cache size."""
        return len(self.cache)


class CacheManager:
    """
    Comprehensive cache manager for ReportSmith.
    
    Provides multi-level caching with automatic fallback:
    1. L1: In-memory LRU cache (fastest, per-instance)
    2. L2: Redis cache (persistent, cross-instance)
    3. L3: Disk cache (fallback for large objects)
    """
    
    # Cache categories with different TTLs
    CACHE_CATEGORIES = {
        "llm_intent": 3600,      # 1 hour - intent extraction results
        "llm_domain": 7200,      # 2 hours - domain value matching
        "llm_sql": 1800,         # 30 min - SQL refinement
        "semantic": 7200,        # 2 hours - semantic search results
        "embedding": 86400,      # 24 hours - embedding vectors
        "sql_result": 300,       # 5 min - SQL query results
        "schema": 86400,         # 24 hours - schema metadata
    }
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        enable_redis: bool = True,
        enable_disk: bool = True,
        disk_cache_dir: Optional[str] = None,
        l1_max_size: int = 1000,
    ):
        """
        Initialize cache manager.
        
        Args:
            redis_url: Redis connection URL
            enable_redis: Enable Redis L2 cache
            enable_disk: Enable disk L3 cache
            disk_cache_dir: Directory for disk cache
            l1_max_size: Max size for L1 cache
        """
        # L1: In-memory LRU caches (one per category)
        self.l1_caches: Dict[str, LRUCache] = {}
        for category, ttl in self.CACHE_CATEGORIES.items():
            self.l1_caches[category] = LRUCache(max_size=l1_max_size, default_ttl=ttl)
        
        # L2: Redis cache
        self.redis_client: Optional[redis.Redis] = None
        self.redis_enabled = False
        if enable_redis and REDIS_AVAILABLE:
            self._init_redis(redis_url)
        
        # L3: Disk cache
        self.disk_enabled = enable_disk
        if enable_disk:
            self.disk_cache_dir = Path(disk_cache_dir or "/tmp/reportsmith_cache")
            self.disk_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Global stats
        self.global_stats = {cat: CacheStats() for cat in self.CACHE_CATEGORIES}
        
        logger.info(
            f"CacheManager initialized: L1=enabled, L2={'enabled' if self.redis_enabled else 'disabled'}, "
            f"L3={'enabled' if self.disk_enabled else 'disabled'}"
        )
    
    def _init_redis(self, redis_url: Optional[str] = None):
        """Initialize Redis connection."""
        try:
            if redis_url:
                self.redis_client = redis.from_url(redis_url, decode_responses=False)
            else:
                redis_host = os.environ.get("REDIS_HOST", "localhost")
                redis_port = int(os.environ.get("REDIS_PORT", "6379"))
                redis_db = int(os.environ.get("REDIS_DB", "1"))  # Use DB 1 for cache
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    decode_responses=False,
                )
            
            # Test connection
            self.redis_client.ping()
            self.redis_enabled = True
            logger.info("Redis cache (L2) initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis: {e}. Using L1 + L3 only.")
            self.redis_client = None
            self.redis_enabled = False
    
    def _generate_key(self, category: str, *args, **kwargs) -> str:
        """Generate cache key from category and parameters."""
        # Create stable key from args and kwargs
        key_parts = [category]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        key_str = "|".join(key_parts)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def get(
        self,
        category: str,
        *args,
        **kwargs
    ) -> Optional[Any]:
        """
        Get value from cache.
        
        Tries L1 -> L2 -> L3 in order.
        
        Args:
            category: Cache category (e.g., "llm_intent")
            args, kwargs: Parameters to generate cache key
            
        Returns:
            Cached value or None
        """
        if category not in self.CACHE_CATEGORIES:
            logger.warning(f"Unknown cache category: {category}")
            return None
        
        key = self._generate_key(category, *args, **kwargs)
        
        # Try L1
        value = self.l1_caches[category].get(key)
        if value is not None:
            self.global_stats[category].hits += 1
            logger.debug(f"Cache hit [L1] {category}: {key[:16]}...")
            return value
        
        # Try L2 (Redis)
        if self.redis_enabled:
            try:
                redis_key = f"reportsmith:{category}:{key}"
                data = self.redis_client.get(redis_key)
                if data:
                    value = pickle.loads(data)
                    # Populate L1
                    self.l1_caches[category].set(key, value)
                    self.global_stats[category].hits += 1
                    logger.debug(f"Cache hit [L2] {category}: {key[:16]}...")
                    return value
            except Exception as e:
                logger.warning(f"Redis get error: {e}")
        
        # Try L3 (Disk)
        if self.disk_enabled:
            try:
                disk_path = self.disk_cache_dir / category / f"{key}.pkl"
                if disk_path.exists():
                    # Check TTL
                    age = time.time() - disk_path.stat().st_mtime
                    if age < self.CACHE_CATEGORIES[category]:
                        with open(disk_path, "rb") as f:
                            value = pickle.load(f)
                        # Populate L1 and L2
                        self.l1_caches[category].set(key, value)
                        if self.redis_enabled:
                            self._set_redis(category, key, value)
                        self.global_stats[category].hits += 1
                        logger.debug(f"Cache hit [L3] {category}: {key[:16]}...")
                        return value
            except Exception as e:
                logger.warning(f"Disk cache read error: {e}")
        
        # Cache miss
        self.global_stats[category].misses += 1
        logger.debug(f"Cache miss {category}: {key[:16]}...")
        return None
    
    def set(
        self,
        category: str,
        value: Any,
        *args,
        ttl: Optional[int] = None,
        **kwargs
    ):
        """
        Set value in cache.
        
        Writes to L1, L2, and L3.
        
        Args:
            category: Cache category
            value: Value to cache
            args, kwargs: Parameters to generate cache key
            ttl: Optional TTL override
        """
        if category not in self.CACHE_CATEGORIES:
            logger.warning(f"Unknown cache category: {category}")
            return
        
        key = self._generate_key(category, *args, **kwargs)
        ttl = ttl or self.CACHE_CATEGORIES[category]
        
        # Set L1
        self.l1_caches[category].set(key, value, ttl=ttl)
        
        # Set L2 (Redis)
        if self.redis_enabled:
            self._set_redis(category, key, value, ttl)
        
        # Set L3 (Disk)
        if self.disk_enabled:
            try:
                disk_dir = self.disk_cache_dir / category
                disk_dir.mkdir(parents=True, exist_ok=True)
                disk_path = disk_dir / f"{key}.pkl"
                with open(disk_path, "wb") as f:
                    pickle.dump(value, f)
            except Exception as e:
                logger.warning(f"Disk cache write error: {e}")
        
        self.global_stats[category].sets += 1
        logger.debug(f"Cache set {category}: {key[:16]}... (ttl={ttl}s)")
    
    def _set_redis(self, category: str, key: str, value: Any, ttl: int):
        """Set value in Redis."""
        try:
            redis_key = f"reportsmith:{category}:{key}"
            data = pickle.dumps(value)
            self.redis_client.setex(redis_key, ttl, data)
        except Exception as e:
            logger.warning(f"Redis set error: {e}")
    
    def invalidate(self, category: Optional[str] = None):
        """
        Invalidate cache entries.
        
        Args:
            category: Category to invalidate (all if None)
        """
        if category:
            categories = [category]
        else:
            categories = list(self.CACHE_CATEGORIES.keys())
        
        for cat in categories:
            # Clear L1
            self.l1_caches[cat].clear()
            
            # Clear L2 (Redis) - delete by pattern
            if self.redis_enabled:
                try:
                    pattern = f"reportsmith:{cat}:*"
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        self.redis_client.delete(*keys)
                except Exception as e:
                    logger.warning(f"Redis invalidate error: {e}")
            
            # Clear L3 (Disk)
            if self.disk_enabled:
                try:
                    disk_dir = self.disk_cache_dir / cat
                    if disk_dir.exists():
                        for file in disk_dir.glob("*.pkl"):
                            file.unlink()
                except Exception as e:
                    logger.warning(f"Disk cache invalidate error: {e}")
        
        logger.info(f"Cache invalidated: {', '.join(categories)}")
    
    def get_stats(self, category: Optional[str] = None) -> Union[CacheStats, Dict[str, CacheStats]]:
        """Get cache statistics."""
        if category:
            # Combine L1 stats with global stats
            combined = CacheStats()
            combined.hits = self.global_stats[category].hits
            combined.misses = self.global_stats[category].misses
            combined.sets = self.global_stats[category].sets
            combined.evictions = self.l1_caches[category].stats.evictions
            return combined
        else:
            return {cat: self.get_stats(cat) for cat in self.CACHE_CATEGORIES}
    
    def print_stats(self):
        """Print cache statistics."""
        logger.info("=" * 80)
        logger.info("CACHE STATISTICS")
        logger.info("=" * 80)
        for category in self.CACHE_CATEGORIES:
            stats = self.get_stats(category)
            l1_size = self.l1_caches[category].size()
            logger.info(f"{category:20s} L1_size={l1_size:4d} {stats}")
        logger.info("=" * 80)


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def init_cache_manager(**kwargs) -> CacheManager:
    """Initialize global cache manager with custom config."""
    global _cache_manager
    _cache_manager = CacheManager(**kwargs)
    return _cache_manager
