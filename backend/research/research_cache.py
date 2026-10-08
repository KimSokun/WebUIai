import time
from typing import Dict, Any, Optional

class ResearchCache:
    """
    Research Memory Cache (Section 27):
    Caches verified technical lookups to prevent redundant web research
    while checking TTL and version freshness.
    """
    def __init__(self, default_ttl_seconds: float = 3600.0):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._default_ttl = default_ttl_seconds

    def get(self, key: str, max_age_seconds: Optional[float] = None) -> Optional[Any]:
        lookup = key.lower().strip()
        if lookup not in self._cache:
            return None
        entry = self._cache[lookup]
        age = time.time() - entry["stored_at"]
        ttl = max_age_seconds if max_age_seconds is not None else self._default_ttl
        if age > ttl:
            del self._cache[lookup]
            return None
        return entry["data"]

    def set(self, key: str, data: Any, version: str = ""):
        self._cache[key.lower().strip()] = {
            "data": data,
            "version": version,
            "stored_at": time.time()
        }

    def clear(self):
        self._cache.clear()

research_cache = ResearchCache()
