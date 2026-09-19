"""Pydantic Data Transfer Objects (DTOs) for API request validation & response serialization."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class HealthCheckResponse(BaseModel):
    """Health check endpoint status schema."""
    status: str
    app_name: str
    environment: str
    version: str
    timestamp: datetime


class WeatherDataDTO(BaseModel):
    """Weather record output DTO."""
    id: Optional[int] = None
    timestamp: datetime
    location: str
    temperature_c: float
    humidity_pct: float
    pressure_hpa: float
    wind_speed_ms: float
    cloud_cover_pct: float = 0.0
    precipitation_mm: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class EnergyDataDTO(BaseModel):
    """Energy demand observation output DTO."""
    id: Optional[int] = None
    timestamp: datetime
    region: str
    demand_mw: float
    peak_demand_flag: bool

    model_config = ConfigDict(from_attributes=True)


class ForecastDTO(BaseModel):
    """Energy demand forecast output DTO."""
    id: Optional[int] = None
    timestamp: datetime
    forecast_target_time: datetime
    forecasted_demand_mw: float
    confidence_lower_mw: Optional[float] = None
    confidence_upper_mw: Optional[float] = None
    model_version: str

    model_config = ConfigDict(from_attributes=True)


class AnomalyDTO(BaseModel):
    """Grid anomaly event DTO."""
    id: Optional[int] = None
    timestamp: datetime
    metric_name: str
    actual_value: float
    expected_value: float
    severity: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AlertDTO(BaseModel):
    """System notification alert DTO."""
    id: Optional[int] = None
    timestamp: datetime
    alert_type: str
    severity: str
    title: str
    message: str
    is_acknowledged: bool

    model_config = ConfigDict(from_attributes=True)

