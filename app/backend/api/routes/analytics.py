"""Weather Impact and Peak Demand Analytics API Router."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import pandas as pd

from app.config.settings import settings
from app.backend.api.dependencies import get_database_session
from app.backend.api.schemas.analytics import WeatherImpactDTO, PeakDemandDTO
from app.database.repository import WeatherRepository, EnergyRepository
from app.services.weather_energy_impact import WeatherEnergyImpactAnalyzer
from app.models.energy_forecasting.peak_analysis import analyze_peak_demand

router = APIRouter(prefix="/analytics", tags=["Analytics & Impact Engine"])


@router.get("/weather-impact", response_model=WeatherImpactDTO, summary="Weather vs Energy Demand Correlations")
def get_weather_impact_analytics(db: Session = Depends(get_database_session)):
    """Computes Stage 7 Pearson and Spearman correlations between weather metrics and load."""
    w_records = WeatherRepository.get_latest(db, limit=200)
    e_records = EnergyRepository.get_latest(db, limit=200)

    if not w_records or not e_records:
        raise HTTPException(status_code=404, detail="Insufficient records to compute weather impact analytics.")

    df_w = pd.DataFrame([{
        "timestamp": r.timestamp,
        "temperature_c": r.temperature_c,
        "humidity_pct": r.humidity_pct,
        "precipitation_mm": getattr(r, 'precipitation_mm', 0.0),
        "wind_speed_ms": getattr(r, 'wind_speed_ms', 0.0)
    } for r in w_records])

    df_e = pd.DataFrame([{
        "timestamp": r.timestamp,
        "demand_mw": r.demand_mw
    } for r in e_records])

    df_merged = pd.merge(df_w, df_e, on="timestamp", how="inner")
    if df_merged.empty:
        raise HTTPException(status_code=404, detail="No time-aligned weather and energy records found.")

    corrs = WeatherEnergyImpactAnalyzer.calculate_correlations(df_merged)

    return WeatherImpactDTO(
        correlations=corrs,
        sample_size=len(df_merged),
        disclaimer="Correlation metrics indicate statistical association and do not prove direct causation."
    )


@router.get("/peak-demand", response_model=PeakDemandDTO, summary="Historical Peak Load Analysis")
def get_peak_demand_analytics(
    region: str = Query(default=settings.DEFAULT_REGION),
    db: Session = Depends(get_database_session)
):
    """Calculates historical peak demand, min demand, and peak time-of-day."""
    records = EnergyRepository.get_latest(db, region=region, limit=168)
    if not records:
        raise HTTPException(status_code=404, detail=f"No energy demand records available for region '{region}'.")

    demands = [r.demand_mw for r in records]
    max_rec = max(records, key=lambda x: x.demand_mw)
    min_rec = min(records, key=lambda x: x.demand_mw)

    peak_hour = max_rec.timestamp.hour if hasattr(max_rec.timestamp, 'hour') else 14

    return PeakDemandDTO(
        region=region,
        peak_demand_mw=round(max_rec.demand_mw, 2),
        peak_timestamp=max_rec.timestamp.isoformat() if hasattr(max_rec.timestamp, 'isoformat') else str(max_rec.timestamp),
        min_demand_mw=round(min_rec.demand_mw, 2),
        min_timestamp=min_rec.timestamp.isoformat() if hasattr(min_rec.timestamp, 'isoformat') else str(min_rec.timestamp),
        peak_hour_of_day=peak_hour
    )
