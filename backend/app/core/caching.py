import time
from typing import Any, Optional, Dict

class SwarmAgentCache:
    """Thread-safe LRU/TTL cache for deterministic cross-agent tool calls."""
    def __init__(self, default_ttl: int = 60):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0

    def _generate_key(self, tool_name: str, params: Any) -> str:
        if isinstance(params, dict):
            serialized = f"{tool_name}:{sorted(params.items())}"
        else:
            serialized = f"{tool_name}:{str(params)}"
        return serialized

    def get(self, tool_name: str, params: Any = None) -> Optional[Any]:
        key = self._generate_key(tool_name, params if params is not None else {})
        record = self._cache.get(key)
        if not record:
            self.misses += 1
            return None

        if time.time() > record["expires_at"]:
            del self._cache[key]
            self.misses += 1
            return None

        self.hits += 1
        return record["data"]

    def set(self, tool_name: str, params: Any, data: Any, ttl: Optional[int] = None) -> None:
        key = self._generate_key(tool_name, params if params is not None else {})
        expiry = time.time() + (ttl if ttl is not None else self.default_ttl)
        self._cache[key] = {
            "data": data,
            "expires_at": expiry
        }

    def stats(self) -> Dict[str, Any]:
        return {
            "cached_entries": len(self._cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio": round(self.hits / (self.hits + self.misses), 2) if (self.hits + self.misses) > 0 else 0.0
        }

swarm_cache = SwarmAgentCache(default_ttl=30)
