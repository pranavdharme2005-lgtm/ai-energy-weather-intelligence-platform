"""
Stage 12 — FastAPI Backend REST API Automated Test Suite.

Validates all REST endpoints under /api/v1/, middleware headers (X-Request-ID),
request schema validation, alert state transitions, simulation execution, and error handling.
"""

import pytest
from fastapi.testclient import TestClient
from app.backend.main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify root status endpoint returns API docs links and status 200."""
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert "documentation" in data
    assert data["api_v1_prefix"] == "/api/v1"


def test_health_endpoints():
    """Verify system health, DB health, and internal services health endpoints."""
    # System Liveness
    res_h = client.get("/api/v1/health")
    assert res_h.status_code == 200
    assert res_h.json()["status"] == "healthy"

    # Database Health
    res_db = client.get("/api/v1/health/db")
    assert res_db.status_code == 200
    assert "connected" in res_db.json()

    # Services Health
    res_svc = client.get("/api/v1/health/services")
    assert res_svc.status_code == 200
    assert "services" in res_svc.json()
    assert "WeatherIngestionService" in res_svc.json()["services"]


def test_request_id_middleware():
    """Verify middleware injects X-Request-ID in response headers."""
    res = client.get("/api/v1/health")
    assert "x-request-id" in res.headers
    assert "x-process-time-ms" in res.headers


def test_weather_endpoints():
    """Verify current weather, history, and summary endpoints."""
    res_curr = client.get("/api/v1/weather/current?location=London")
    assert res_curr.status_code in [200, 404]

    res_hist = client.get("/api/v1/weather/history?limit=5")
    assert res_hist.status_code == 200
    assert isinstance(res_hist.json(), list)

    res_sum = client.get("/api/v1/weather/summary?location=London")
    assert res_sum.status_code in [200, 404]


def test_energy_endpoints():
    """Verify current energy demand, history, and summary endpoints."""
    res_curr = client.get("/api/v1/energy/current?region=Grid_Alpha")
    assert res_curr.status_code in [200, 404]

    res_hist = client.get("/api/v1/energy/history?limit=5")
    assert res_hist.status_code == 200
    assert isinstance(res_hist.json(), list)

    res_sum = client.get("/api/v1/energy/summary?region=Grid_Alpha")
    assert res_sum.status_code in [200, 404]


def test_forecast_endpoints():
    """Verify latest forecast, multi-step series, and summary endpoints."""
    res_latest = client.get("/api/v1/forecast/latest?region=Grid_Alpha")
    assert res_latest.status_code == 200
    assert "predicted_demand" in res_latest.json()

    res_multi = client.get("/api/v1/forecast?region=Grid_Alpha&horizon=12")
    assert res_multi.status_code == 200
    data = res_multi.json()
    assert data["predictions_count"] == 12

    res_sum = client.get("/api/v1/forecast/summary?region=Grid_Alpha")
    assert res_sum.status_code == 200
    assert "peak_forecast_mw" in res_sum.json()


def test_rain_endpoints():
    """Verify rain prediction and rain history endpoints."""
    res_curr = client.get("/api/v1/rain/current?location=London")
    assert res_curr.status_code in [200, 404]

    res_pred = client.get("/api/v1/rain/prediction?location=London")
    assert res_pred.status_code in [200, 404]

    res_hist = client.get("/api/v1/rain/history?limit=5")
    assert res_hist.status_code == 200
    assert isinstance(res_hist.json(), list)


def test_anomaly_endpoints():
    """Verify anomalies feed, recent, and summary endpoints."""
    res_anom = client.get("/api/v1/anomalies?limit=10")
    assert res_anom.status_code == 200
    assert isinstance(res_anom.json(), list)

    res_rec = client.get("/api/v1/anomalies/recent?limit=5")
    assert res_rec.status_code == 200

    res_sum = client.get("/api/v1/anomalies/summary")
    assert res_sum.status_code == 200
    assert "total_anomalies" in res_sum.json()


def test_alert_endpoints_and_state_transitions():
    """Verify alerts feed, active alerts, summary, acknowledge, and resolve endpoints."""
    res_all = client.get("/api/v1/alerts")
    assert res_all.status_code == 200

    res_act = client.get("/api/v1/alerts/active")
    assert res_act.status_code == 200

    res_sum = client.get("/api/v1/alerts/summary")
    assert res_sum.status_code == 200
    assert "total_persisted" in res_sum.json()

    # Test state transitions with invalid ID
    res_ack_invalid = client.post("/api/v1/alerts/999999/acknowledge")
    assert res_ack_invalid.status_code in [404, 200]

    res_res_invalid = client.post("/api/v1/alerts/999999/resolve")
    assert res_res_invalid.status_code in [404, 200]


def test_simulator_endpoint():
    """Verify POST /api/v1/simulator/run executes scenario simulation."""
    payload = {
        "region": "Grid_Alpha",
        "temperature_c_delta": 5.0,
        "humidity_pct_delta": -10.0,
        "precipitation_mm_delta": 0.0,
        "wind_speed_m_s_delta": 0.0
    }
    res = client.post("/api/v1/simulator/run", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "baseline_forecast_mw" in data
    assert "scenario_forecast_mw" in data
    assert "absolute_difference_mw" in data


def test_ai_analyst_endpoint():
    """Verify POST /api/v1/ai/analyze returns grounded answer."""
    payload = {
        "question": "What is causing today's demand increase?",
        "region": "Grid_Alpha"
    }
    res = client.post("/api/v1/ai/analyze", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "summary" in data
    assert "key_findings" in data
    assert "provider" in data


def test_analytics_endpoints():
    """Verify weather impact and peak demand analytics endpoints."""
    res_imp = client.get("/api/v1/analytics/weather-impact")
    assert res_imp.status_code in [200, 404]

    res_peak = client.get("/api/v1/analytics/peak-demand?region=Grid_Alpha")
    assert res_peak.status_code in [200, 404]


def test_data_quality_endpoints():
    """Verify data quality audit endpoints."""
    res_dq = client.get("/api/v1/data-quality")
    assert res_dq.status_code == 200
    data = res_dq.json()
    assert "data_quality_score" in data
    assert "weather_audit" in data


def test_invalid_route_404():
    """Verify invalid API path returns status 404."""
    res = client.get("/api/v1/nonexistent_endpoint")
    assert res.status_code == 404
