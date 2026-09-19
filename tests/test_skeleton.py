"""Automated Unit and Integration Tests for Stage 1 Skeleton Architecture."""

import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import pandas as pd

from app.config.settings import settings
from app.backend.main import app
from app.database.models import WeatherData, EnergyData, RainPrediction, EnergyForecast, Anomaly, Alert
from app.data.ingestion import SyntheticDataIngestor
from app.data.validator import DataValidator
from app.data.cleaner import DataCleaner
from app.models.rain_predictor import RainPredictor
from app.models.energy_forecaster import EnergyForecaster
from app.models.anomaly_detector import AnomalyDetector
from app.services.simulator import WhatIfSimulator, SimulationScenario

client = TestClient(app)


def test_settings_initialization():
    """Verify pydantic settings load with non-empty application name."""
    assert settings.APP_NAME is not None
    assert settings.PORT == 8000


def test_health_check_endpoint():
    """Verify system health liveness router responds with status 200."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_weather_api_v1_endpoint():
    """Verify weather API route returns valid payload."""
    response = client.get("/api/v1/weather/current?location=Region_1")
    assert response.status_code == 200
    data = response.json()
    assert "temperature_c" in data


def test_energy_api_v1_endpoint():
    """Verify energy API route returns valid payload."""
    response = client.get("/api/v1/energy/latest?region=Grid_Alpha")
    assert response.status_code == 200
    data = response.json()
    assert "demand_mw" in data


def test_synthetic_data_ingestor():
    """Verify data ingestor yields structured dataframes."""
    ingestor = SyntheticDataIngestor()
    now = datetime.now(timezone.utc)
    df_w = ingestor.fetch_weather_data("Region_1", now - timedelta(hours=5), now)
    df_e = ingestor.fetch_energy_data("Grid_Alpha", now - timedelta(hours=5), now)

    assert not df_w.empty
    assert not df_e.empty
    assert "temperature_c" in df_w.columns
    assert "demand_mw" in df_e.columns


def test_data_validator():
    """Verify data quality validator rules."""
    ingestor = SyntheticDataIngestor()
    now = datetime.now(timezone.utc)
    df_w = ingestor.fetch_weather_data("Region_1", now - timedelta(hours=5), now)
    report = DataValidator.validate_weather_data(df_w)
    assert report.total_records > 0
    assert report.passed_validation is True


def test_data_cleaner():
    """Verify data cleaning temporal feature addition."""
    df = pd.DataFrame({"timestamp": [datetime.now(timezone.utc)]})
    cleaned = DataCleaner.add_temporal_features(df)
    assert "hour" in cleaned.columns
    assert "hour_sin" in cleaned.columns


def test_ml_model_interfaces():
    """Verify RainPredictor, EnergyForecaster, and AnomalyDetector contracts."""
    ingestor = SyntheticDataIngestor()
    now = datetime.now(timezone.utc)
    df_w = ingestor.fetch_weather_data("Region_1", now - timedelta(hours=5), now)
    df_e = ingestor.fetch_energy_data("Grid_Alpha", now - timedelta(hours=5), now)

    rain_res = RainPredictor().predict(df_w)
    assert 0.0 <= rain_res.probability <= 1.0

    forecast_res = EnergyForecaster().predict(df_e)
    assert forecast_res.forecasted_demand_mw > 0

    anomalies = AnomalyDetector().predict(df_e)
    assert isinstance(anomalies, list)


def test_whatif_simulator():
    """Verify What-If Simulator returns valid percentage shifts."""
    scenario = SimulationScenario(temperature_delta_c=5.0)
    res = WhatIfSimulator.simulate_scenario(baseline_demand=3000.0, scenario=scenario)
    assert res.simulated_demand_mw > 3000.0
    assert res.percentage_change > 0.0
