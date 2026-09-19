"""FastAPI API v1 Routers."""

from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.session import get_db
from app.backend.schemas import (
    HealthCheckResponse,
    WeatherDataDTO,
    EnergyDataDTO,
    ForecastDTO,
    AnomalyDTO,
    AlertDTO
)
from app.data.ingestion import SyntheticDataIngestor
from app.models.rain_predictor import RainPredictor
from app.models.energy_forecaster import EnergyForecaster
from app.models.anomaly_detector import AnomalyDetector
from app.services.simulator import WhatIfSimulator, SimulationScenario, SimulationResult

router = APIRouter(prefix="/api/v1", tags=["V1 Analytics API"])

ingestor = SyntheticDataIngestor()
rain_model = RainPredictor()
forecaster = EnergyForecaster()
anomaly_detector = AnomalyDetector()


@router.get("/health", response_model=HealthCheckResponse)
def get_system_health():
    """System liveness and environment health check endpoint."""
    return HealthCheckResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        environment=settings.APP_ENV,
        version="1.0.0-stage1",
        timestamp=datetime.now(timezone.utc)
    )


@router.get("/weather/current", response_model=WeatherDataDTO)
def get_current_weather(location: str = Query("Region_1", description="Target meteorological station zone")):
    """Returns the latest weather observation for a location."""
    now = datetime.now(timezone.utc)
    df = ingestor.fetch_weather_data(location=location, start_time=now - timedelta(hours=1), end_time=now)
    if df.empty:
        raise HTTPException(status_code=404, detail="Weather data not found.")
    row = df.iloc[-1].to_dict()
    return WeatherDataDTO(**row)


@router.get("/energy/latest", response_model=EnergyDataDTO)
def get_latest_energy_demand(region: str = Query("Grid_Alpha", description="Target electrical grid region")):
    """Returns the latest grid load observation."""
    now = datetime.now(timezone.utc)
    df = ingestor.fetch_energy_data(region=region, start_time=now - timedelta(hours=1), end_time=now)
    if df.empty:
        raise HTTPException(status_code=404, detail="Energy data not found.")
    row = df.iloc[-1].to_dict()
    return EnergyDataDTO(**row)


@router.get("/forecast/load", response_model=ForecastDTO)
def get_load_forecast(region: str = Query("Grid_Alpha")):
    """Generates next-hour energy demand forecast."""
    now = datetime.utcnow()
    df = ingestor.fetch_energy_data(region=region, start_time=now - timedelta(hours=24), end_time=now)
    result = forecaster.predict(df)
    return ForecastDTO(
        timestamp=result.timestamp,
        forecast_target_time=result.forecast_target_time,
        forecasted_demand_mw=result.forecasted_demand_mw,
        confidence_lower_mw=result.confidence_lower_mw,
        confidence_upper_mw=result.confidence_upper_mw,
        model_version=result.model_version
    )


@router.get("/anomalies/active", response_model=List[AnomalyDTO])
def get_active_anomalies(region: str = Query("Grid_Alpha")):
    """Identifies active demand anomalies in the grid."""
    now = datetime.utcnow()
    df = ingestor.fetch_energy_data(region=region, start_time=now - timedelta(hours=24), end_time=now)
    results = anomaly_detector.predict(df)
    return [
        AnomalyDTO(
            timestamp=r.timestamp,
            metric_name=r.metric_name,
            actual_value=r.actual_value,
            expected_value=r.expected_value,
            severity=r.severity,
            description=r.description
        ) for r in results
    ]


@router.post("/simulation/what-if", response_model=SimulationResult)
def run_simulation(scenario: SimulationScenario, baseline_demand_mw: float = 2800.0):
    """Executes what-if grid load simulation for scenario planning."""
    return WhatIfSimulator.simulate_scenario(baseline_demand=baseline_demand_mw, scenario=scenario)
