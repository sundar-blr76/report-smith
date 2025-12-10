from dataclasses import dataclass

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
