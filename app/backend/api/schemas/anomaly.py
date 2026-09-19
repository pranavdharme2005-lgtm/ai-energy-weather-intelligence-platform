"""Anomaly Detection API Pydantic Schemas."""

from typing import Optional, List
from pydantic import BaseModel, Field


class AnomalyDTO(BaseModel):
    id: Optional[int] = None
    timestamp: str
    region: Optional[str] = "Grid_Alpha"
    variable_name: str = Field(..., description="Metric or variable experiencing anomaly")
    observed_value: float
    expected_value: float
    deviation: float
    anomaly_score: float
    severity: str = Field(..., description="CRITICAL, HIGH, MEDIUM, LOW, or INFO")
    detection_method: str
    reason: str


class AnomalySummaryDTO(BaseModel):
    total_anomalies: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    avg_anomaly_score: float
