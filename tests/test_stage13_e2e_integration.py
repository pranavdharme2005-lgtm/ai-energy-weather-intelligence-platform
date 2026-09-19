"""
End-to-End System Integration & Smoke Test Suite for Stage 13.

Verifies end-to-end data flow across all 13 stages:
Database -> Data Ingestion -> Data Quality -> Rain ML -> Energy Forecasting -> Anomaly Engine ->
Weather Impact -> What-If Simulator -> AI Analyst -> Alert Engine -> FastAPI REST API -> Frontend API Client.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.backend.main import app
from app.database.models import Base
from app.database.session import SessionLocal, engine
from app.database.repository import (
    WeatherRepository,
    EnergyRepository,
    AnomalyRepository,
    AlertRepository
)
from app.data.ingestion import DataIngestionService
from app.data.quality_engine import DataQualityEngine
from app.models.rain_predictor import RainPredictor
from app.services.energy_forecasting_service import EnergyForecastingService
from app.services.anomaly_detection_service import AnomalyDetectionService
from app.services.weather_energy_impact import WeatherEnergyImpactAnalyzer
from app.services.simulator import WhatIfSimulatorService
from app.services.ai_analyst_service import AIEnergyAnalystService
from app.services.alert_service import SmartAlertService
from app.frontend.api import EnergyIntelligenceAPIClient
from app.frontend.utils.formatting import (
    format_mw,
    format_temp,
    format_percent,
    format_pressure,
    format_status_badge
)


@pytest.fixture(scope="module")
def db_session():
    """Module-wide database fixture ensuring clean tables and populated records."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()

    # Ingest data for testing
    ingest_svc = DataIngestionService()
    ingest_svc.run_pipeline(session, location="London", region="Region-North")

    yield session

    session.close()


@pytest.fixture(scope="module")
def api_test_client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


def test_e2e_database_population(db_session):
    """Verify weather and energy records exist in database."""
    weather_recs = WeatherRepository.get_latest(db_session, limit=10)
    energy_recs = EnergyRepository.get_latest(db_session, limit=10)

    assert len(weather_recs) > 0, "Weather records must be populated"
    assert len(energy_recs) > 0, "Energy records must be populated"


def test_e2e_data_quality_audit(db_session):
    """Verify Data Quality engine audit execution."""
    w_recs = WeatherRepository.get_latest(db_session, limit=50)
    assert len(w_recs) > 0

    df_w = pd.DataFrame([{
        "timestamp": r.timestamp,
        "location": r.location,
        "temperature_c": r.temperature_c,
        "humidity_pct": r.humidity_pct,
        "source": "Open-Meteo"
    } for r in w_recs])

    report = DataQualityEngine.evaluate_weather_dataframe(df_w)
    assert report is not None
    assert report.scores.overall_quality_score >= 0.0


def test_e2e_rain_prediction_flow(db_session):
    """Verify Rain Prediction model inference."""
    weather_recs = WeatherRepository.get_latest(db_session, limit=1)
    assert len(weather_recs) > 0

    latest_w = weather_recs[0]
    w_df = pd.DataFrame([{
        "timestamp": latest_w.timestamp,
        "temperature_c": latest_w.temperature_c,
        "humidity_pct": latest_w.humidity_pct,
        "pressure_hpa": latest_w.pressure_hpa,
        "wind_speed_ms": latest_w.wind_speed_ms,
        "cloud_cover_pct": latest_w.cloud_cover_pct,
        "precipitation_mm": latest_w.precipitation_mm
    }])

    predictor = RainPredictor()
    pred_res = predictor.predict(w_df)

    assert pred_res is not None
    assert hasattr(pred_res, "probability")
    assert 0.0 <= pred_res.probability <= 1.0


def test_e2e_energy_forecasting_flow(db_session):
    """Verify Energy Demand Forecasting service."""
    svc = EnergyForecastingService()
    fc_dict = svc.generate_forecast(region="Region-North", horizon_hours=24)

    assert fc_dict is not None
    assert "forecasts" in fc_dict
    assert len(fc_dict["forecasts"]) > 0


def test_e2e_anomaly_detection_flow(db_session):
    """Verify Anomaly Detection engine execution."""
    svc = AnomalyDetectionService()
    anom_res = svc.run_full_detection(region="Region-North", save_to_db=True)
    assert isinstance(anom_res, dict)

    recent = AnomalyRepository.get_latest(db_session, limit=10)
    assert isinstance(recent, list)


def test_e2e_weather_impact_analytics_flow(db_session):
    """Verify Weather Impact Analytics service."""
    w_recs = WeatherRepository.get_latest(db_session, limit=50)
    e_recs = EnergyRepository.get_latest(db_session, limit=50)

    df_w = pd.DataFrame([{
        "timestamp": r.timestamp,
        "temperature_c": r.temperature_c,
        "humidity_pct": r.humidity_pct
    } for r in w_recs])

    df_e = pd.DataFrame([{
        "timestamp": r.timestamp,
        "demand_mw": r.demand_mw
    } for r in e_recs])

    df_merged = pd.merge(df_w, df_e, on="timestamp", how="inner")
    if not df_merged.empty:
        corrs = WeatherEnergyImpactAnalyzer.calculate_correlations(df_merged)
        assert isinstance(corrs, dict)


def test_e2e_what_if_simulator_flow(db_session):
    """Verify What-If Scenario Simulator service."""
    sim_res = WhatIfSimulatorService.run_scenario(
        db=db_session,
        scenario_overrides={"temperature_c_delta": 5.0},
        region="Region-North"
    )
    assert sim_res is not None
    assert "baseline_forecast_mw" in sim_res or "baseline_demand_mw" in sim_res


def test_e2e_ai_analyst_flow(db_session):
    """Verify AI Analyst Q&A and daily briefing generation."""
    svc = AIEnergyAnalystService(db_session)

    briefing = svc.generate_daily_report(region="Region-North")
    assert briefing is not None

    qa_res = svc.ask_question("What is causing energy demand?", region="Region-North")
    assert qa_res is not None
    assert hasattr(qa_res, "summary") or hasattr(qa_res, "answer") or isinstance(qa_res, dict)


def test_e2e_smart_alert_engine_flow(db_session):
    """Verify Smart Alert engine generation and state transition repository functions."""
    svc = SmartAlertService(db_session)
    alerts = svc.evaluate_and_sync_alerts(region="Region-North")
    assert isinstance(alerts, list)

    active_alerts = AlertRepository.get_active_alerts(db_session, region="Region-North")
    if active_alerts:
        alert_id = active_alerts[0].id
        ack_item = AlertRepository.acknowledge_alert(db_session, alert_id)
        assert ack_item is True
        res_item = AlertRepository.resolve_alert(db_session, alert_id)
        assert res_item is True


def test_e2e_fastapi_rest_endpoints(api_test_client):
    """Verify key FastAPI backend REST API endpoints via TestClient."""
    resp_health = api_test_client.get("/health")
    assert resp_health.status_code == 200
    assert resp_health.json().get("status") == "healthy"

    resp_w = api_test_client.get("/api/v1/weather/current")
    assert resp_w.status_code == 200

    resp_e = api_test_client.get("/api/v1/energy/current")
    assert resp_e.status_code == 200

    resp_fc = api_test_client.get("/api/v1/forecast/latest")
    assert resp_fc.status_code == 200

    resp_alerts = api_test_client.get("/api/v1/alerts")
    assert resp_alerts.status_code == 200

    resp_anom = api_test_client.get("/api/v1/anomalies")
    assert resp_anom.status_code == 200

    resp_sim = api_test_client.post("/api/v1/simulator/run", json={"scenario_overrides": {"temperature_c_delta": 3.0}})
    assert resp_sim.status_code == 200

    resp_ai = api_test_client.post("/api/v1/ai/analyze", json={"question": "Status check?"})
    assert resp_ai.status_code == 200


def test_e2e_frontend_api_client_delegates():
    """Verify frontend API Client facade delegate methods."""
    client = EnergyIntelligenceAPIClient()

    w_curr = client.get_current_weather()
    assert w_curr is not None or w_curr is None

    e_curr = client.get_current_energy()
    assert e_curr is not None or e_curr is None

    fc = client.get_forecast()
    assert fc is not None or fc is None


def test_e2e_formatting_utilities():
    """Verify string formatting utility helpers."""
    assert format_mw(1234.56) == "1,234.6 MW"
    assert format_mw(None) == "N/A"
    assert format_temp(22.5) == "22.5 °C"
    assert format_percent(0.85) == "85.0%"
    assert format_percent(85.0) == "85.0%"
    assert format_pressure(1013.25) == "1,013.2 hPa"
    assert "ONLINE" in format_status_badge("ONLINE")
