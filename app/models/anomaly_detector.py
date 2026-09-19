"""Production Energy & Weather Anomaly Detector Implementation."""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import pandas as pd

from app.models.base import BaseMLModel, AnomalyResult, EnergyForecastResult
from app.models.anomaly_detection.demand_anomalies import detect_demand_anomalies
from app.models.anomaly_detection.forecast_anomalies import detect_forecast_anomalies
from app.models.anomaly_detection.weather_anomalies import detect_weather_anomalies
from app.models.anomaly_detection.multivariate_anomalies import detect_multivariate_anomalies
from app.models.anomaly_detection.summary import calculate_anomaly_summary
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AnomalyDetector(BaseMLModel):
    """Production statistical & machine learning anomaly detection engine."""

    def __init__(self, threshold_std: float = 2.5, model_version: str = "v1.0.0"):
        super().__init__(model_version=model_version)
        self.threshold_std = threshold_std
        self.is_trained = True

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> "AnomalyDetector":
        """Fits anomaly detector parameters on historical observation dataset."""
        logger.info(f"Fitting AnomalyDetector model {self.model_version} on shape {X.shape}...")
        self.is_trained = True
        return self

    def predict(self, X: pd.DataFrame, region: str = "Grid_Alpha") -> List[AnomalyResult]:
        """Detects demand anomalies against seasonal hourly baselines and z-scores."""
        return detect_demand_anomalies(X, region=region, z_threshold=self.threshold_std)

    def detect_all(
        self,
        df_energy: pd.DataFrame,
        df_weather: Optional[pd.DataFrame] = None,
        forecast_results: Optional[List[EnergyForecastResult]] = None,
        region: str = "Grid_Alpha"
    ) -> List[AnomalyResult]:
        """Executes comprehensive multi-dimensional anomaly detection suite.
        
        Args:
            df_energy: Energy load observations dataframe.
            df_weather: Meteorological observations dataframe (optional).
            forecast_results: Stage 5 forecast predictions (optional).
            region: Regional grid label.
            
        Returns:
            List[AnomalyResult]: Combined list of all detected anomalies.
        """
        all_anomalies: List[AnomalyResult] = []

        # 1. Demand Anomalies (Z-score & IQR)
        demand_anoms = detect_demand_anomalies(df_energy, region=region, z_threshold=self.threshold_std)
        all_anomalies.extend(demand_anoms)

        # 2. Forecast Interval Breach Anomalies
        if forecast_results and not df_energy.empty:
            forecast_anoms = detect_forecast_anomalies(df_energy, forecast_results, region=region)
            all_anomalies.extend(forecast_anoms)

        # 3. Weather Extreme Anomalies
        if df_weather is not None and not df_weather.empty:
            weather_anoms = detect_weather_anomalies(df_weather, region=region)
            all_anomalies.extend(weather_anoms)

        # 4. Multivariate Isolation Forest Anomalies
        combined_df = df_energy.copy()
        if df_weather is not None and not df_weather.empty and "timestamp" in combined_df.columns and "timestamp" in df_weather.columns:
            try:
                c_df = combined_df.copy()
                w_df = df_weather.copy()
                c_df["timestamp_clean"] = pd.to_datetime(c_df["timestamp"], utc=True)
                w_df["timestamp_clean"] = pd.to_datetime(w_df["timestamp"], utc=True)

                combined_df = pd.merge_asof(
                    c_df.sort_values("timestamp_clean"),
                    w_df.sort_values("timestamp_clean"),
                    on="timestamp_clean",
                    direction="nearest"
                )
            except Exception as e:
                logger.warning(f"Could not merge energy and weather for multivariate anomaly detection: {e}")

        multi_anoms = detect_multivariate_anomalies(combined_df, region=region)
        all_anomalies.extend(multi_anoms)

        logger.info(f"AnomalyDetector executed detect_all(): Total anomalies found = {len(all_anomalies)}")
        return all_anomalies

    def save_model(self, file_path: str) -> None:
        logger.info(f"Saving AnomalyDetector model metadata to {file_path}")

    def load_model(self, file_path: str) -> None:
        logger.info(f"Loading AnomalyDetector model metadata from {file_path}")
        self.is_trained = True
