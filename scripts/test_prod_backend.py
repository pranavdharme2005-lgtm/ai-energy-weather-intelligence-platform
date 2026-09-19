"""Production FastAPI & Live Endpoint Audit Script."""

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Force production mode
os.environ["APP_ENV"] = "production"
os.environ["DEBUG"] = "False"

from fastapi.testclient import TestClient
from app.backend.main import app
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

client = TestClient(app)


def test_production_endpoints():
    logger.info("Starting Live Production API & Health Verification...")
    logger.info(f"App Environment: {settings.APP_ENV} | Debug Mode: {settings.DEBUG}")

    # 1. Health checks
    r = client.get("/health")
    assert r.status_code == 200, f"/health failed: {r.status_code} {r.text}"
    logger.info(f"GET /health: {r.json()}")

    r = client.get("/api/v1/health/db")
    assert r.status_code in [200, 503], f"/api/v1/health/db failed: {r.status_code}"
    logger.info(f"GET /api/v1/health/db: {r.json()}")

    # 2. Weather endpoints
    r = client.get("/api/v1/weather/current?location=London")
    assert r.status_code == 200, f"/api/v1/weather/current failed: {r.status_code}"
    logger.info("GET /api/v1/weather/current: OK")

    # 3. Energy endpoints
    r = client.get("/api/v1/energy/current?region=Grid_Alpha")
    assert r.status_code == 200, f"/api/v1/energy/current failed: {r.status_code}"
    logger.info("GET /api/v1/energy/current: OK")

    # 4. Forecast endpoints
    r = client.get("/api/v1/forecast/latest?region=Grid_Alpha")
    assert r.status_code == 200, f"/api/v1/forecast/latest failed: {r.status_code}"
    logger.info("GET /api/v1/forecast/latest: OK")

    # 5. Rain endpoints
    r = client.get("/api/v1/rain/current?location=London")
    assert r.status_code == 200, f"/api/v1/rain/current failed: {r.status_code}"
    logger.info("GET /api/v1/rain/current: OK")

    # 6. Anomalies endpoints
    r = client.get("/api/v1/anomalies/recent?limit=10")
    assert r.status_code == 200, f"/api/v1/anomalies/recent failed: {r.status_code}"
    logger.info("GET /api/v1/anomalies/recent: OK")

    # 7. Alerts endpoints
    r = client.get("/api/v1/alerts?limit=10")
    assert r.status_code == 200, f"/api/v1/alerts failed: {r.status_code}"
    logger.info("GET /api/v1/alerts: OK")

    # 8. Simulator POST endpoint
    r = client.post("/api/v1/simulator/run", json={"region": "Grid_Alpha", "scenario_name": "Test Heatwave", "temperature_delta_c": 5.0})
    assert r.status_code == 200, f"/api/v1/simulator/run failed: {r.status_code}"
    logger.info("POST /api/v1/simulator/run: OK")

    # 9. AI Analyst POST endpoint
    r = client.post("/api/v1/ai/analyze", json={"question": "What is the peak energy demand risk today?", "region": "Grid_Alpha"})
    assert r.status_code == 200, f"/api/v1/ai/analyze failed: {r.status_code}"
    logger.info("POST /api/v1/ai/analyze: OK")

    # 10. Data Quality GET endpoint
    r = client.get("/api/v1/data-quality")
    assert r.status_code == 200, f"/api/v1/data-quality failed: {r.status_code}"
    logger.info("GET /api/v1/data-quality: OK")

    logger.info("ALL PRODUCTION API ENDPOINTS & HEALTH CHECKS PASSED CLEANLY.")


if __name__ == "__main__":
    test_production_endpoints()
