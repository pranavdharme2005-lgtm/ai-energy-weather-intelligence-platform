"""Data Quality API Pydantic Schemas."""

from typing import Optional, Dict, Any
from pydantic import BaseModel


class DataQualityAuditDTO(BaseModel):
    data_quality_score: float
    missing_values_count: int
    duplicate_count: int
    data_gap_count: int
    last_updated: str
    weather_audit: Dict[str, Any]
    energy_audit: Dict[str, Any]
