"""Energy Demand Forecasting API Pydantic Schemas."""

from typing import Optional, List
from pydantic import BaseModel, Field


class ForecastPointDTO(BaseModel):
    timestamp: str
    region: str
    predicted_demand: float = Field(..., description="Forecasted load in MW")
    lower_bound: Optional[float] = Field(None, description="Lower 95% confidence bound in MW")
    upper_bound: Optional[float] = Field(None, description="Upper 95% confidence bound in MW")
    model_version: Optional[str] = "v1.0-Stage5"


class ForecastResponseDTO(BaseModel):
    region: str
    forecast_horizon: str
    predictions_count: int
    uncertainty_level: Optional[str] = "Moderate"
    model_version: str
    forecasts: List[ForecastPointDTO]


class ForecastSummaryDTO(BaseModel):
    region: str
    next_hour_demand_mw: float
    peak_forecast_mw: float
    min_forecast_mw: float
    uncertainty_level: str
    model_version: str
