import hashlib
import json
from typing import Any, Dict, Optional, Union, List

from reportsmith.logger import get_logger
from .stats import CacheStats
from .lru import LRUCache
from .redis_backend import RedisBackend
from .disk_backend import DiskBackend

logger = get_logger(__name__)

class CacheManager:
    """
    Comprehensive cache manager for ReportSmith.
    
    Provides multi-level caching with automatic fallback:
    1. L1: In-memory LRU cache (fastest, per-instance)
    2. L2: Redis cache (persistent, cross-instance)
    3. L3: Disk cache (fallback for large objects)
    """
    
    CACHE_CATEGORIES = {
        "llm_intent": 3600,      # 1 hour
        "llm_domain": 7200,      # 2 hours
        "llm_sql": 1800,         # 30 min
        "semantic": 7200,        # 2 hours
        "embedding": 86400,      # 24 hours
        "sql_result": 300,       # 5 min
        "schema": 86400,         # 24 hours
    }
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        enable_redis: bool = True,
        enable_disk: bool = True,
        disk_cache_dir: Optional[str] = None,
        l1_max_size: int = 1000,
    ):
        # L1
        self.l1_caches: Dict[str, LRUCache] = {
            cat: LRUCache(max_size=l1_max_size, default_ttl=ttl)
            for cat, ttl in self.CACHE_CATEGORIES.items()
        }
        
        # L2
        self.redis = RedisBackend(redis_url) if enable_redis else None
        
        # L3
        self.disk = DiskBackend(disk_cache_dir) if enable_disk else None
        
        # Stats
        self.global_stats = {cat: CacheStats() for cat in self.CACHE_CATEGORIES}
        
        logger.info(
            f"CacheManager initialized: L1=enabled, "
            f"L2={'enabled' if self.redis and self.redis.enabled else 'disabled'}, "
            f"L3={'enabled' if self.disk and self.disk.enabled else 'disabled'}"
        )
        self._print_persistent_cache_entries()

    def _generate_key(self, category: str, *args, **kwargs) -> str:
        key_parts = [category]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        key_str = "|".join(key_parts)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(self, category: str, *args, **kwargs) -> Optional[Any]:
        if category not in self.CACHE_CATEGORIES:
            logger.warning(f"Unknown cache category: {category}")
            return None
        
        key = self._generate_key(category, *args, **kwargs)
        
        # L1
        val = self.l1_caches[category].get(key)
        if val is not None:
            self.global_stats[category].hits += 1
            logger.info(f"[cache-hit] {category} [L1 memory] key={key[:16]}...")
            self._print_cache_payload(category, val, "L1 memory")
            return val
        
        # L2
        if self.redis and self.redis.enabled:
            val = self.redis.get(category, key)
            if val is not None:
                self.l1_caches[category].set(key, val) # Populate L1
                self.global_stats[category].hits += 1
                logger.info(f"[cache-hit] {category} [L2 Redis] key={key[:16]}...")
                self._print_cache_payload(category, val, "L2 Redis")
                return val
        
        # L3
        if self.disk and self.disk.enabled:
            ttl = self.CACHE_CATEGORIES[category]
            val = self.disk.get(category, key, ttl)
            if val is not None:
                self.l1_caches[category].set(key, val)
                if self.redis and self.redis.enabled:
                    self.redis.set(category, key, val, ttl)
                self.global_stats[category].hits += 1
                logger.info(f"[cache-hit] {category} [L3 disk] key={key[:16]}...")
                self._print_cache_payload(category, val, "L3 disk")
                return val
        
        self.global_stats[category].misses += 1
        logger.debug(f"[cache-miss] {category}: key={key[:16]}...")
        return None

    def set(self, category: str, value: Any, *args, ttl: Optional[int] = None, **kwargs):
        if category not in self.CACHE_CATEGORIES:
            return
        
        key = self._generate_key(category, *args, **kwargs)
        ttl = ttl or self.CACHE_CATEGORIES[category]
        
        self.l1_caches[category].set(key, value, ttl=ttl)
        
        if self.redis and self.redis.enabled:
            self.redis.set(category, key, value, ttl)
            
        if self.disk and self.disk.enabled:
            self.disk.set(category, key, value)
            
        self.global_stats[category].sets += 1
        logger.info(f"[cache-set] {category} key={key[:16]}... ttl={ttl}s")

    def invalidate(self, category: Optional[str] = None):
        cats = [category] if category else list(self.CACHE_CATEGORIES.keys())
        for c in cats:
            if c in self.l1_caches:
                self.l1_caches[c].clear()
            if self.redis:
                self.redis.invalidate_category(c)
            if self.disk:
                self.disk.invalidate_category(c)
        logger.info(f"Cache invalidated: {', '.join(cats)}")

    def get_stats(self, category: Optional[str] = None) -> Union[CacheStats, Dict[str, CacheStats]]:
        if category:
            combined = CacheStats()
            combined.hits = self.global_stats[category].hits
            combined.misses = self.global_stats[category].misses
            combined.sets = self.global_stats[category].sets
            combined.evictions = self.l1_caches[category].stats.evictions
            return combined
        return {cat: self.get_stats(cat) for cat in self.CACHE_CATEGORIES}
        
    def _print_persistent_cache_entries(self):
        logger.info("=" * 80)
        logger.info("PERSISTENT CACHE ENTRIES")
        logger.info("=" * 80)
        total_l2 = 0
        total_l3 = 0
        for cat in self.CACHE_CATEGORIES:
            l2 = self.redis.count_entries(cat) if self.redis else 0
            l3 = self.disk.count_entries(cat, self.CACHE_CATEGORIES[cat]) if self.disk else 0
            total_l2 += l2
            total_l3 += l3
            if l2 > 0 or l3 > 0:
                logger.info(f"{cat:20s} L2={l2:4d}, L3={l3:4d}")
        logger.info("-" * 80)
        logger.info(f"{'TOTAL':20s} L2={total_l2:4d}, L3={total_l3:4d}")
        logger.info("=" * 80)

    def _print_cache_payload(self, category: str, value: Any, source: str):
        # Concise logging for payload
        logger.debug(f"CACHE PAYLOAD ({source}): {str(value)[:200]}...")

# Global instance
_cache_manager: Optional[CacheManager] = None

def get_cache_manager() -> CacheManager:
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager

def init_cache_manager(**kwargs) -> CacheManager:
    global _cache_manager
    _cache_manager = CacheManager(**kwargs)
    return _cache_manager
