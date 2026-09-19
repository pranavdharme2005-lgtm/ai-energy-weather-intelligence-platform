"""Rain Prediction API Router."""

from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import pandas as pd

from app.config.settings import settings
from app.backend.api.dependencies import get_database_session, PaginationParams
from app.backend.api.schemas.rain import RainPredictionDTO, RainHistoryItemDTO
from app.database.repository import WeatherRepository
from app.models.rain_predictor import RainPredictor

router = APIRouter(prefix="/rain", tags=["Rain Prediction Analytics"])


@router.get("/current", response_model=RainPredictionDTO, summary="Current Rain Probability & Prediction")
def get_current_rain_prediction(
    location: str = Query(default=settings.DEFAULT_LOCATION, description="Target location/station name"),
    db: Session = Depends(get_database_session)
):
    """Evaluates Stage 4 XGBoost model on latest weather observation to predict rain probability."""
    records = WeatherRepository.get_latest(db, location=location, limit=1)
    if not records:
        raise HTTPException(status_code=404, detail=f"No weather observations found for location '{location}'.")

    latest_w = records[0]
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
    result = predictor.predict(w_df)

    return RainPredictionDTO(
        prediction="Rain Likely" if result.rain_predicted else "No Rain Expected",
        probability=round(result.probability, 4),
        rain_predicted=result.rain_predicted,
        confidence_level="High",
        timestamp=latest_w.timestamp.isoformat() if hasattr(latest_w.timestamp, 'isoformat') else str(latest_w.timestamp),
        model_version=result.model_version
    )


@router.get("/prediction", response_model=RainPredictionDTO, summary="Alias for Current Rain Prediction")
def get_rain_prediction_alias(
    location: str = Query(default=settings.DEFAULT_LOCATION),
    db: Session = Depends(get_database_session)
):
    """Alias for /rain/current."""
    return get_current_rain_prediction(location=location, db=db)


@router.get("/history", response_model=List[RainHistoryItemDTO], summary="Rain & Moisture Historical Trace")
def get_rain_history(
    location: str = Query(default=settings.DEFAULT_LOCATION),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_database_session)
):
    """Retrieves recent precipitation and humidity history."""
    records = WeatherRepository.get_latest(db, location=location, limit=pagination.limit)
    return [
        RainHistoryItemDTO(
            timestamp=r.timestamp.isoformat() if hasattr(r.timestamp, 'isoformat') else str(r.timestamp),
            precipitation_mm=r.precipitation_mm,
            humidity_pct=r.humidity_pct,
            rain_predicted=bool(r.precipitation_mm > 0.1 or r.humidity_pct > 80.0)
        ) for r in records
    ]
