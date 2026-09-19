"""Inference Engine for Energy Demand Forecasting."""

from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
import joblib

from app.models.base import EnergyForecastResult
from app.models.energy_forecasting.features import extract_forecasting_features
from app.utils.logger import get_logger

logger = get_logger(__name__)

SAVED_MODELS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "saved_models"


class EnergyForecastingInference:
    """Production inference engine executing multi-step grid demand forecasting."""

    def __init__(self, artifact_path: Optional[Path] = None):
        self.artifact_path = artifact_path or (SAVED_MODELS_DIR / "energy_forecaster_v1.joblib")
        self.model = None
        self.feature_names = []
        self.horizon_hours = 24
        self.margin_95 = 150.0
        self.model_version = "v1.0.0"
        self._load_artifact()

    def _load_artifact(self):
        """Loads serialized joblib artifact if present on disk."""
        if self.artifact_path.exists():
            try:
                artifact = joblib.load(self.artifact_path)
                self.model = artifact.get("model")
                self.feature_names = artifact.get("feature_names", [])
                self.horizon_hours = artifact.get("horizon_hours", 24)
                self.margin_95 = artifact.get("margin_95", 150.0)
                self.model_version = artifact.get("model_version", "v1.0.0")
                logger.info(f"Loaded Energy Forecaster artifact from {self.artifact_path}")
            except Exception as e:
                logger.error(f"Failed loading Energy Forecaster artifact: {e}")

    def predict_horizon(
        self, df_history: pd.DataFrame, region: str = "Grid_Alpha", horizon_hours: int = 24
    ) -> List[EnergyForecastResult]:
        """Generates future demand forecasts over horizon_hours.
        
        Args:
            df_history: Historical observations dataframe containing timestamps, demand_mw, and weather.
            region: Regional grid label.
            horizon_hours: Forecasting horizon in hours.
            
        Returns:
            List[EnergyForecastResult]: Sequence of structured forecast outputs.
        """
        if df_history.empty:
            raise ValueError("Historical dataframe for energy demand forecasting cannot be empty.")

        now = datetime.now(timezone.utc)
        latest_ts = df_history["timestamp"].iloc[-1] if "timestamp" in df_history.columns else now
        if isinstance(latest_ts, str):
            latest_ts = datetime.fromisoformat(latest_ts.replace("Z", "+00:00"))

        # Extract features from latest history
        X, _ = extract_forecasting_features(df_history)

        results = []

        # If model is loaded, predict using ML model; otherwise fallback to baseline lag predictor
        if self.model is not None and not X.empty:
            last_row_X = X.iloc[[-1]]
            pred_base = float(self.model.predict(last_row_X)[0])
        else:
            pred_base = float(df_history["demand_mw"].iloc[-1]) if "demand_mw" in df_history.columns else 2800.0

        # Multi-step trajectory curve simulation
        for h in range(1, horizon_hours + 1):
            target_time = latest_ts + timedelta(hours=h)
            hour_of_day = target_time.hour
            # Diurnal factor variation relative to base forecast
            diurnal_factor = 1.0 + 0.12 * np.sin((hour_of_day - 8) * np.pi / 12)
            pred_val = round(float(pred_base * diurnal_factor), 2)

            lower_bound = round(max(0.0, pred_val - self.margin_95), 2)
            upper_bound = round(pred_val + self.margin_95, 2)

            results.append(
                EnergyForecastResult(
                    timestamp=now,
                    forecast_target_time=target_time,
                    region=region,
                    forecasted_demand_mw=pred_val,
                    confidence_lower_mw=lower_bound,
                    confidence_upper_mw=upper_bound,
                    forecast_horizon=f"{horizon_hours}h",
                    model_version=self.model_version
                )
            )

        return results
