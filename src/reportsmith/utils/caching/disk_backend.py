import time
import pickle
from pathlib import Path
from typing import Any, Optional
from reportsmith.logger import get_logger

logger = get_logger(__name__)

class DiskBackend:
    """Disk cache backend (L3)."""

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir or "/tmp/reportsmith_cache")
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.enabled = True
        except Exception as e:
            logger.warning(f"Failed to create disk cache dir: {e}")
            self.enabled = False

    def get(self, category: str, key: str, ttl: int) -> Optional[Any]:
        if not self.enabled: return None
        try:
            path = self.cache_dir / category / f"{key}.pkl"
            if path.exists():
                age = time.time() - path.stat().st_mtime
                if age < ttl:
                    with open(path, "rb") as f:
                        return pickle.load(f)
        except Exception as e:
            logger.warning(f"Disk cache read error: {e}")
        return None

    def set(self, category: str, key: str, value: Any):
        if not self.enabled: return
        try:
            cat_dir = self.cache_dir / category
            cat_dir.mkdir(parents=True, exist_ok=True)
            path = cat_dir / f"{key}.pkl"
            with open(path, "wb") as f:
                pickle.dump(value, f)
        except Exception as e:
            logger.warning(f"Disk cache write error: {e}")

    def invalidate_category(self, category: str):
        if not self.enabled: return
        try:
            cat_dir = self.cache_dir / category
            if cat_dir.exists():
                for f in cat_dir.glob("*.pkl"):
                    f.unlink()
        except Exception as e:
            logger.warning(f"Disk cache invalidate error: {e}")

    def count_entries(self, category: str, ttl: int) -> int:
        if not self.enabled: return 0
        try:
            cat_dir = self.cache_dir / category
            if not cat_dir.exists(): return 0
            count = 0
            now = time.time()
            for f in cat_dir.glob("*.pkl"):
                if (now - f.stat().st_mtime) < ttl:
                    count += 1
            return count
        except Exception:
            return 0
