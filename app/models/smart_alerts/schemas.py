"""Pydantic schemas and data structures for Smart Alert Center (Stage 10)."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class AlertItem(BaseModel):
    """Standardized alert object schema matching Section 16 specification."""
    alert_id: str
    alert_type: str  # ENERGY_DEMAND_SPIKE, ENERGY_DEMAND_DROP, FORECAST_DEVIATION, PREDICTED_PEAK, RAIN_EVENT, EXTREME_WEATHER, DATA_QUALITY, MODEL_CONFIDENCE, SYSTEM_HEALTH
    severity: str = "MEDIUM"  # INFO, LOW, MEDIUM, HIGH, CRITICAL
    status: str = "ACTIVE"  # ACTIVE, ACKNOWLEDGED, RESOLVED

    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    region: str = "Grid_Alpha"

    title: str
    message: str
    reason: Optional[str] = None

    observed_value: Optional[float] = None
    expected_value: Optional[float] = None
    deviation: Optional[float] = None

    source: str = "rule_engine"
    detection_method: str = "threshold_rule"
    model_version: str = "v1.0.0"

    occurrence_count: int = 1
    ai_explanation: Optional[str] = None

    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_seen_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: Optional[str] = None


class AlertRuleConfig(BaseModel):
    """Configurable rule evaluation thresholds."""
    cooldown_minutes: int = 30
    persistence_count: int = 2
    energy_spike_threshold_mw: float = 3500.0
    energy_drop_threshold_mw: float = 1500.0
    forecast_deviation_threshold_pct: float = 15.0
    rain_alert_threshold_pct: float = 60.0
    extreme_temp_high_c: float = 35.0
    extreme_temp_low_c: float = 0.0


class AlertSummary(BaseModel):
    """Aggregated alert summary metrics."""
    total_alerts: int = 0
    active_alerts: int = 0
    acknowledged_alerts: int = 0
    resolved_alerts: int = 0
    severity_counts: Dict[str, int] = Field(default_factory=lambda: {
        "CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0
    })
    by_type: Dict[str, int] = Field(default_factory=dict)
    as_of: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AlertCardView(BaseModel):
    """UI preparation data structure for alert timeline and card components."""
    id: Optional[int] = None
    alert_id: str
    alert_type: str
    severity: str
    status: str
    title: str
    message: str
    reason: Optional[str] = None
    metric_display: str = ""
    timestamp_display: str = ""
    badge_color: str = "orange"
    occurrence_count: int = 1
    ai_explanation: Optional[str] = None


class NotificationMessage(BaseModel):
    """Abstract notification message payload."""
    alert_id: str
    severity: str
    channel: str = "console"
    title: str
    body: str
    sent_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
