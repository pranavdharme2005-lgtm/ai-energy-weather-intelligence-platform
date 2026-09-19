"""
Base REST API Client infrastructure for Stage 13 Frontend Integration.
"""

import requests
from typing import Dict, Any, Optional
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BaseAPIClient:
    """Base class providing HTTP request utilities, error handling, and timeout management."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 3.0):
        self.base_url = (base_url or f"http://localhost:{settings.PORT}{settings.API_PREFIX}").rstrip("/")
        self.health_url = f"http://localhost:{settings.PORT}/health"
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "EnergyControlRoom-Frontend/1.0",
            "Accept": "application/json"
        })

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """Performs HTTP GET request with error handling."""
        url = f"{self.base_url}{endpoint}" if endpoint.startswith("/") else f"{self.base_url}/{endpoint}"
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            logger.warning(f"GET {url} returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.debug(f"HTTP GET {url} failed: {e}")
        return None

    def post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """Performs HTTP POST request with error handling."""
        url = f"{self.base_url}{endpoint}" if endpoint.startswith("/") else f"{self.base_url}/{endpoint}"
        try:
            resp = self.session.post(url, json=json_data, params=params, timeout=self.timeout)
            if resp.status_code in (200, 201):
                return resp.json()
            logger.warning(f"POST {url} returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.debug(f"HTTP POST {url} failed: {e}")
        return None

    def check_health(self) -> Dict[str, Any]:
        """Checks API server health status."""
        try:
            resp = self.session.get(self.health_url, timeout=1.5)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.debug(f"API health check failed: {e}")
        return {"status": "UNAVAILABLE", "environment": settings.APP_ENV, "error": "API server offline"}
