"""Energy Demand API Pydantic Schemas."""

from typing import Optional, List
from pydantic import BaseModel, Field


class EnergyDataDTO(BaseModel):
    timestamp: str
    region: str
    demand_mw: float
    peak_demand_flag: Optional[bool] = False
    source: Optional[str] = "PJM_OpenData_Historical"


class EnergySummaryDTO(BaseModel):
    region: str
    current_demand_mw: float
    avg_demand_mw: float
    max_demand_mw: float
    min_demand_mw: float
    peak_incidents_count: int
    records_analyzed: int
