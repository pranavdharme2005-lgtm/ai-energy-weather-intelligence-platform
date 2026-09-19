"""Smart Alerts API Pydantic Schemas."""

from typing import Optional, List
from pydantic import BaseModel, Field


class AlertDTO(BaseModel):
    id: int
    alert_type: str
    severity: str
    status: str = Field(..., description="ACTIVE, ACKNOWLEDGED, or RESOLVED")
    timestamp: str
    region: str
    title: str
    message: str
    reason: str
    observed_value: Optional[float] = None
    expected_value: Optional[float] = None
    fingerprint: Optional[str] = None
    occurrence_count: int = 1
    ai_explanation: Optional[str] = None


class AcknowledgeAlertRequest(BaseModel):
    acknowledged_by: Optional[str] = "Operator"
    notes: Optional[str] = None


class ResolveAlertRequest(BaseModel):
    resolved_by: Optional[str] = "Operator"
    resolution_reason: Optional[str] = "Restored to normal operating threshold"


class AlertSummaryDTO(BaseModel):
    total_persisted: int
    active_count: int
    acknowledged_count: int
    resolved_count: int
    critical_count: int
    high_count: int
