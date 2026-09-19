"""What-If Scenario Simulator API Pydantic Schemas."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SimulationRequest(BaseModel):
    region: Optional[str] = "Grid_Alpha"
    temperature_c_delta: float = Field(0.0, ge=-25.0, le=25.0, description="Temperature change in °C")
    humidity_pct_delta: float = Field(0.0, ge=-50.0, le=50.0, description="Humidity change in %")
    precipitation_mm_delta: float = Field(0.0, ge=0.0, le=100.0, description="Precipitation change in mm")
    wind_speed_m_s_delta: float = Field(0.0, ge=-20.0, le=30.0, description="Wind speed change in m/s")


class SimulationResultDTO(BaseModel):
    baseline_forecast_mw: float
    scenario_forecast_mw: float
    absolute_difference_mw: float
    percentage_difference_pct: float
    training_range_warnings: List[str]
    uncertainty_available: bool = True
    model_version: str = "v1.0-Stage5"
