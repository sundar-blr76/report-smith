import time
from collections import OrderedDict
from typing import Any, Dict, Optional
from .stats import CacheStats

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
