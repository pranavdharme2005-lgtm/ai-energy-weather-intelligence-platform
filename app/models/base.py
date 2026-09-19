"""Base Interfaces and Schemas for Machine Learning Components."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class RainPredictionResult(BaseModel):
    """Output structure for rain probability inference."""
    timestamp: datetime
    prediction_target_time: datetime
    rain_predicted: bool
    probability: float = Field(..., ge=0.0, le=1.0)
    model_version: str = "v1.0.0-skeleton"


class EnergyForecastResult(BaseModel):
    """Output structure for energy demand forecasting inference."""
    timestamp: datetime
    forecast_target_time: datetime
    region: str = "Grid_Alpha"
    forecasted_demand_mw: float
    confidence_lower_mw: Optional[float] = None
    confidence_upper_mw: Optional[float] = None
    forecast_horizon: str = "24h"
    model_version: str = "v1.0.0"


class AnomalyResult(BaseModel):
    """Output structure for anomaly detection inference."""
    timestamp: datetime
    region: str = "Grid_Alpha"
    metric_name: str = "demand_mw"
    variable: str = "demand_mw"
    actual_value: float
    expected_value: float
    deviation: float = 0.0
    anomaly_score: float = Field(0.5, ge=0.0, le=1.0)
    severity: str = "MEDIUM"  # NORMAL, LOW, MEDIUM, HIGH, CRITICAL
    anomaly_type: str = "demand_zscore"
    description: str
    detection_method: str = "rolling_zscore"
    model_version: str = "v1.0.0"


class BaseMLModel(ABC):
    """Abstract base class for all machine learning models in the platform."""

    def __init__(self, model_version: str = "v1.0.0"):
        self.model_version = model_version
        self.is_trained = False

    @abstractmethod
    def fit(self, X: Any, y: Any = None) -> Any:
        """Trains the underlying model on feature matrix X and target y."""
        pass

    @abstractmethod
    def predict(self, X: Any) -> Any:
        """Runs model inference on input features X."""
        pass

    @abstractmethod
    def save_model(self, file_path: str) -> None:
        """Serializes model artifacts to storage."""
        pass

    @abstractmethod
    def load_model(self, file_path: str) -> None:
        """Loads serialized model artifacts from storage."""
        pass
