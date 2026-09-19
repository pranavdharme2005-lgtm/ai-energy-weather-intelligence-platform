"""Production Energy Demand Forecaster Implementation."""

from datetime import datetime, timezone, timedelta
from typing import List, Union, Optional, Dict, Any
from pathlib import Path
import pandas as pd
import numpy as np

from app.models.base import BaseMLModel, EnergyForecastResult
from app.models.energy_forecasting.inference import EnergyForecastingInference
from app.models.energy_forecasting.train import EnergyModelTrainer
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EnergyForecaster(BaseMLModel):
    """Production forecaster for regional grid load demand."""

    def __init__(self, model_version: str = "v1.0.0"):
        super().__init__(model_version=model_version)
        self.inference_engine = EnergyForecastingInference()
        self.is_trained = self.inference_engine.model is not None

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> "EnergyForecaster":
        """Trains energy forecaster pipeline on historical observations dataframe X."""
        logger.info(f"Fitting EnergyForecaster model {self.model_version} on shape {X.shape}...")
        model, metadata = EnergyModelTrainer.train_and_evaluate(X, horizon_hours=24)
        self.inference_engine._load_artifact()
        self.is_trained = True
        return self

    def predict(
        self, X: pd.DataFrame, region: str = "Grid_Alpha", horizon_hours: int = 24, return_list: bool = False
    ) -> Union[EnergyForecastResult, List[EnergyForecastResult]]:
        """Runs model inference predicting future energy demand.
        
        Returns EnergyForecastResult by default, or List[EnergyForecastResult] if return_list=True.
        """
        results = self.inference_engine.predict_horizon(X, region=region, horizon_hours=horizon_hours)
        if return_list:
            return results
        return results[0] if results else None

    def predict_horizon(
        self, X: pd.DataFrame, region: str = "Grid_Alpha", horizon_hours: int = 24
    ) -> List[EnergyForecastResult]:
        """Generates sequence of horizon_hours forecasts."""
        return self.inference_engine.predict_horizon(X, region=region, horizon_hours=horizon_hours)

    def save_model(self, file_path: str) -> None:
        logger.info(f"Saving EnergyForecaster model artifact to {file_path}")

    def load_model(self, file_path: str) -> None:
        logger.info(f"Loading EnergyForecaster model artifact from {file_path}")
        self.inference_engine = EnergyForecastingInference(artifact_path=Path(file_path))
        self.is_trained = self.inference_engine.model is not None
