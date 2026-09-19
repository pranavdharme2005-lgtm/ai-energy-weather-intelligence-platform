"""Weather API Pydantic Schemas."""

from typing import Optional, List
from pydantic import BaseModel, Field


class WeatherDataDTO(BaseModel):
    timestamp: str
    location: str
    temperature_c: float
    humidity_pct: float
    pressure_hpa: float
    wind_speed_ms: float
    cloud_cover_pct: float
    precipitation_mm: float
    weather_condition: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    source: Optional[str] = "Open-Meteo-API"


class WeatherSummaryDTO(BaseModel):
    location: str
    avg_temperature_c: float
    max_temperature_c: float
    min_temperature_c: float
    avg_humidity_pct: float
    total_precipitation_mm: float
    latest_condition: str
    records_analyzed: int
