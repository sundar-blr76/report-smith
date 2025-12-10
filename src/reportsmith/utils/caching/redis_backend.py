import os
import pickle
from typing import Any, Optional
from reportsmith.logger import get_logger

logger = get_logger(__name__)

class RedisBackend:
    """Redis cache backend (L2)."""
    
    def __init__(self, redis_url: Optional[str] = None):
        try:
            import redis
            self.client = None
            if redis_url:
                self.client = redis.from_url(redis_url, decode_responses=False)
            else:
                redis_host = os.environ.get("REDIS_HOST", "localhost")
                redis_port = int(os.environ.get("REDIS_PORT", "6379"))
                redis_db = int(os.environ.get("REDIS_DB", "1"))
                self.client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    decode_responses=False,
                )
            # Test
            self.client.ping()
            self.enabled = True
            logger.info("Redis cache (L2) initialized successfully")
        except ImportError:
            self.enabled = False
            logger.debug("redis package not installed")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis: {e}")
            self.enabled = False
            self.client = None

    def get(self, category: str, key: str) -> Optional[Any]:
        if not self.enabled or not self.client: return None
        try:
            redis_key = f"reportsmith:{category}:{key}"
            data = self.client.get(redis_key)
            if data:
                return pickle.loads(data)
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
        return None

    def set(self, category: str, key: str, value: Any, ttl: int):
        if not self.enabled or not self.client: return
        try:
            redis_key = f"reportsmith:{category}:{key}"
            data = pickle.dumps(value)
            self.client.setex(redis_key, ttl, data)
        except Exception as e:
            logger.warning(f"Redis set error: {e}")

    def invalidate_category(self, category: str):
        if not self.enabled or not self.client: return
        try:
            pattern = f"reportsmith:{category}:*"
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis invalidate error: {e}")

    def count_entries(self, category: str) -> int:
        if not self.enabled or not self.client: return 0
        try:
            pattern = f"reportsmith:{category}:*"
            keys = self.client.keys(pattern)
            return len(keys) if keys else 0
        except Exception:
            return 0
