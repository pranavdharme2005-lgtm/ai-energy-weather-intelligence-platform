"""Weather Impact Analytics API Pydantic Schemas."""

from typing import Optional, List, Dict
from pydantic import BaseModel


class WeatherImpactDTO(BaseModel):
    correlations: Dict[str, float]
    sample_size: int
    disclaimer: str = "Correlation metrics indicate statistical association and do not prove direct causation."


class PeakDemandDTO(BaseModel):
    region: str
    peak_demand_mw: float
    peak_timestamp: str
    min_demand_mw: float
    min_timestamp: str
    peak_hour_of_day: int
