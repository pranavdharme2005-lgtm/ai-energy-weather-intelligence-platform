"""Rain Prediction API Pydantic Schemas."""

from typing import Optional, List
from pydantic import BaseModel, Field


class RainPredictionDTO(BaseModel):
    prediction: str = Field(..., description="'Rain Likely' or 'No Rain Expected'")
    probability: float = Field(..., ge=0.0, le=1.0, description="Estimated rain probability between 0.0 and 1.0")
    rain_predicted: bool
    confidence_level: Optional[str] = "High"
    timestamp: str
    model_version: str = "v1.0-Stage4-XGBoost"


class RainHistoryItemDTO(BaseModel):
    timestamp: str
    precipitation_mm: float
    humidity_pct: float
    rain_predicted: bool
