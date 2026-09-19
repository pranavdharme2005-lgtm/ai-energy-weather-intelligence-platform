"""Pydantic schemas for what-if scenario simulation engine."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ScenarioInput(BaseModel):
    """User-supplied hypothetical weather scenario input modifications.
    
    Only supplied non-None variables override baseline weather features.
    """
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    pressure_hpa: Optional[float] = None
    wind_speed_ms: Optional[float] = None
    cloud_cover_pct: Optional[float] = None
    precipitation_mm: Optional[float] = None
    rain_probability: Optional[float] = None  # Accepts [0.0, 1.0] or [0.0, 100.0]


class ScenarioValidationResult(BaseModel):
    """Result of validating scenario inputs."""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    sanitized_input: Dict[str, float] = Field(default_factory=dict)


class ScenarioComparisonPoint(BaseModel):
    """Single-timestamp baseline vs scenario forecast comparison point."""
    timestamp: str
    baseline_demand_mw: float
    scenario_demand_mw: float
    absolute_change_mw: float
    percentage_change: float
    confidence_lower_mw: Optional[float] = None
    confidence_upper_mw: Optional[float] = None


class SensitivityPoint(BaseModel):
    """Single evaluation point in 1-variable model sensitivity sweep."""
    input_value: float
    predicted_demand_mw: float
    percentage_change_from_baseline: float


class ScenarioExplanation(BaseModel):
    """Deterministic, rule-based scenario explanation metadata."""
    summary: str
    percentage_change_formatted: str
    primary_driving_variable: str
    out_of_range_warning: Optional[str] = None
    disclaimer: str = "Model-based scenario estimate. Indicates model sensitivity, NOT proof of causal effect."


class ScenarioResultSchema(BaseModel):
    """Standardized result structure for what-if scenario simulations."""
    scenario_id: str
    region: str = "Grid_Alpha"
    forecast_timestamp: str
    baseline_inputs: Dict[str, float]
    scenario_inputs: Dict[str, float]
    baseline_demand_mw: float
    scenario_demand_mw: float
    absolute_change_mw: float
    percentage_change: float
    trajectory: List[ScenarioComparisonPoint] = Field(default_factory=list)
    input_range_status: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    out_of_range_warning: bool = False
    uncertainty_available: bool = True
    explanation: ScenarioExplanation
    model_version: str = "v1.0.0"
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
