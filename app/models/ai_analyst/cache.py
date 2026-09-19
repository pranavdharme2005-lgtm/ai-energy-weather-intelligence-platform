"""In-memory & hash-based cache manager for cost control and latency reduction."""

from typing import Dict, Any, Optional, Union
import hashlib
from pydantic import BaseModel
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AnalystCache:
    """Cache manager storing generated daily reports and Q&A responses."""

    def __init__(self, max_entries: int = 100):
        self.max_entries = max_entries
        self._cache: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _compute_key(context_hash: str, query: str = "daily_intelligence") -> str:
        """Computes composite cache key."""
        combined = f"{context_hash}:{query.lower().strip()}"
        return hashlib.md5(combined.encode("utf-8")).hexdigest()

    def get(self, context_hash: str, query: str = "daily_intelligence") -> Optional[Dict[str, Any]]:
        """Retrieves cached response if present."""
        if not context_hash:
            return None
        key = self._compute_key(context_hash, query)
        if key in self._cache:
            logger.info(f"AnalystCache HIT for query='{query[:30]}...' key={key[:8]}")
            return self._cache[key]
        return None

    def set(self, context_hash: str, query_or_response: Any, response: Optional[Any] = None) -> None:
        """Stores response in cache. Can be called set(hash, query, resp) or set(hash, resp)."""
        if not context_hash:
            return

        if response is None:
            query = "daily_intelligence"
            resp = query_or_response
        else:
            query = query_or_response
            resp = response

        if hasattr(resp, "model_dump"):
            resp = resp.model_dump()

        if len(self._cache) >= self.max_entries:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        key = self._compute_key(context_hash, query)
        self._cache[key] = resp
        logger.info(f"AnalystCache STORED for query='{query[:30]}...' key={key[:8]}")

    def clear(self) -> None:
        """Clears all cached entries."""
        self._cache.clear()


# Global singleton instance
analyst_cache = AnalystCache()
