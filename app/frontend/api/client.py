"""
Base REST API Client infrastructure for Stage 13 Frontend Integration.
"""

import os
import time
import requests
from typing import Dict, Any, Optional
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BaseAPIClient:
    """Base class providing HTTP request utilities, error handling, timeout management, and fast offline detection."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 3.0):
        url_override = base_url or os.getenv("API_BASE_URL") or getattr(settings, "API_BASE_URL", "")
        if url_override:
            self.base_url = url_override.rstrip("/")
        else:
            self.base_url = f"http://localhost:{settings.PORT}{settings.API_PREFIX}".rstrip("/")

        # Determine health check URL
        if "/api/" in self.base_url:
            self.health_url = f"{self.base_url.rsplit('/api/', 1)[0]}/health"
        else:
            self.health_url = f"{self.base_url}/health"

        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "EnergyControlRoom-Frontend/1.0",
            "Accept": "application/json"
        })
        self._is_online: Optional[bool] = None
        self._last_check_time: float = 0

    def is_api_online(self) -> bool:
        """Fast-checks whether FastAPI backend is reachable, caching status for 30s."""
        now = time.time()
        if self._is_online is not None and (now - self._last_check_time) < 30.0:
            return self._is_online

        # If pointing to localhost/127.0.0.1, use a very short 0.2s probe timeout to avoid UI lag
        probe_timeout = 0.2 if ("localhost" in self.base_url or "127.0.0.1" in self.base_url) else min(1.0, self.timeout)
        try:
            resp = self.session.get(self.health_url, timeout=probe_timeout)
            self._is_online = (resp.status_code == 200)
        except Exception:
            self._is_online = False

        self._last_check_time = now
        return self._is_online

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """Performs HTTP GET request with fast offline detection and error handling."""
        if not self.is_api_online():
            return None

        url = f"{self.base_url}{endpoint}" if endpoint.startswith("/") else f"{self.base_url}/{endpoint}"
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            logger.warning(f"GET {url} returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.debug(f"HTTP GET {url} failed: {e}")
            self._is_online = False
        return None

    def post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """Performs HTTP POST request with fast offline detection and error handling."""
        if not self.is_api_online():
            return None

        url = f"{self.base_url}{endpoint}" if endpoint.startswith("/") else f"{self.base_url}/{endpoint}"
        try:
            resp = self.session.post(url, json=json_data, params=params, timeout=self.timeout)
            if resp.status_code in (200, 201):
                return resp.json()
            logger.warning(f"POST {url} returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.debug(f"HTTP POST {url} failed: {e}")
            self._is_online = False
        return None

    def check_health(self) -> Dict[str, Any]:
        """Checks API server health status."""
        if self.is_api_online():
            try:
                resp = self.session.get(self.health_url, timeout=1.5)
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                pass
        return {"status": "UNAVAILABLE", "environment": settings.APP_ENV, "error": "API server offline"}

