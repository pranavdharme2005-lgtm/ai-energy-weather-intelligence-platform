"""Energy Forecasting API Router."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.backend.api.dependencies import get_database_session
from app.backend.api.schemas.forecast import ForecastPointDTO, ForecastResponseDTO, ForecastSummaryDTO
from app.services.energy_forecasting_service import EnergyForecastingService

router = APIRouter(prefix="/forecast", tags=["Energy Load Forecasting"])


@router.get("/latest", response_model=ForecastPointDTO, summary="Latest Next-Hour Load Forecast")
def get_latest_forecast(
    region: str = Query(default=settings.DEFAULT_REGION, description="Target electrical grid region")
):
    """Generates next-hour energy demand forecast point using Stage 5 models."""
    service = EnergyForecastingService()
    res = service.generate_forecast(region=region, horizon_hours=1)
    
    forecasts = res.get("forecasts", [])
    if not forecasts:
        raise HTTPException(status_code=503, detail="Forecast service failed to generate predictions.")

    fp = forecasts[0]
    return ForecastPointDTO(
        timestamp=str(fp.get("timestamp", "")),
        region=region,
        predicted_demand=float(fp.get("forecasted_demand_mw", 0.0)),
        lower_bound=float(fp["confidence_lower_mw"]) if fp.get("confidence_lower_mw") is not None else None,
        upper_bound=float(fp["confidence_upper_mw"]) if fp.get("confidence_upper_mw") is not None else None,
        model_version=str(res.get("model_version", "v1.0-Stage5"))
    )


@router.get("", response_model=ForecastResponseDTO, summary="Multi-Step Load Forecast Series")
def get_multi_step_forecast(
    region: str = Query(default=settings.DEFAULT_REGION, description="Target electrical grid region"),
    horizon: int = Query(default=24, ge=1, le=168, description="Forecast horizon in hours (1 to 168)")
):
    """Generates multi-step energy demand forecast trajectory for specified horizon."""
    service = EnergyForecastingService()
    res = service.generate_forecast(region=region, horizon_hours=horizon)

    points = []
    for fp in res.get("forecasts", []):
        points.append(ForecastPointDTO(
            timestamp=str(fp.get("timestamp", "")),
            region=region,
            predicted_demand=float(fp.get("forecasted_demand_mw", 0.0)),
            lower_bound=float(fp["confidence_lower_mw"]) if fp.get("confidence_lower_mw") is not None else None,
            upper_bound=float(fp["confidence_upper_mw"]) if fp.get("confidence_upper_mw") is not None else None,
            model_version=str(res.get("model_version", "v1.0-Stage5"))
        ))

    return ForecastResponseDTO(
        region=region,
        forecast_horizon=f"{horizon}h",
        predictions_count=len(points),
        uncertainty_level="Moderate",
        model_version=str(res.get("model_version", "v1.0-Stage5")),
        forecasts=points
    )


@router.get("/summary", response_model=ForecastSummaryDTO, summary="Forecast Peak and Uncertainty Metrics")
def get_forecast_summary(
    region: str = Query(default=settings.DEFAULT_REGION, description="Target electrical grid region")
):
    """Calculates peak forecast load, min forecast load, and uncertainty assessment."""
    service = EnergyForecastingService()
    res = service.generate_forecast(region=region, horizon_hours=24)

    forecasts = res.get("forecasts", [])
    if not forecasts:
        raise HTTPException(status_code=503, detail="Forecast service unavailable.")

    demands = [float(f.get("forecasted_demand_mw", 0.0)) for f in forecasts]
    next_val = demands[0]

    return ForecastSummaryDTO(
        region=region,
        next_hour_demand_mw=round(next_val, 2),
        peak_forecast_mw=round(max(demands), 2),
        min_forecast_mw=round(min(demands), 2),
        uncertainty_level="Moderate",
        model_version=str(res.get("model_version", "v1.0-Stage5"))
    )
