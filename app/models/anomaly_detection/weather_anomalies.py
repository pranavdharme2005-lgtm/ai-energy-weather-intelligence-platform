"""Meteorological Extreme Weather Anomaly Detector."""

from typing import List, Dict, Any
from datetime import datetime, timezone
import pandas as pd
import numpy as np

from app.models.base import AnomalyResult
from app.models.anomaly_detection.scoring import calculate_anomaly_score, classify_severity
from app.utils.logger import get_logger

logger = get_logger(__name__)

WEATHER_VARIABLES = {
    "temperature_c": {"name": "Temperature (°C)", "z_thresh": 2.8, "max_z": 5.0},
    "humidity_pct": {"name": "Humidity (%)", "z_thresh": 3.0, "max_z": 5.0},
    "pressure_hpa": {"name": "Atmospheric Pressure (hPa)", "z_thresh": 2.8, "max_z": 5.0},
    "wind_speed_ms": {"name": "Wind Speed (m/s)", "z_thresh": 3.2, "max_z": 5.0},
    "precipitation_mm": {"name": "Precipitation (mm)", "z_thresh": 3.5, "max_z": 6.0}
}


def detect_weather_anomalies(
    df: pd.DataFrame, region: str = "Grid_Alpha", z_threshold: float = 2.8
) -> List[AnomalyResult]:
    """Detects unusual weather events deviating from historical distribution.
    
    Args:
        df: Weather observations dataframe.
        region: Regional grid identifier.
        z_threshold: Default z-score threshold for weather anomaly detection.
        
    Returns:
        List[AnomalyResult]: Standardized weather anomaly results.
    """
    anomalies = []
    if df.empty or "timestamp" not in df.columns:
        return anomalies

    res_df = df.copy()

    for col, cfg in WEATHER_VARIABLES.items():
        if col not in res_df.columns or res_df[col].dropna().empty:
            continue

        series = res_df[col].astype(float)
        mean_val = float(series.mean())
        std_val = float(series.std()) if len(series) > 1 else 1.0
        if std_val == 0.0:
            std_val = 1.0

        for idx, row in res_df.iterrows():
            val = float(row[col])
            if pd.isna(val):
                continue

            dev = float(val - mean_val)
            z = abs(dev) / std_val
            target_thresh = cfg.get("z_thresh", z_threshold)

            # Precipitation is event-driven; trigger only for significant rain spikes
            if col == "precipitation_mm" and val < 5.0:
                continue

            if z > target_thresh:
                score = calculate_anomaly_score(z, max_z=cfg["max_z"])
                severity = classify_severity(score, z_score=z)
                if severity == "NORMAL":
                    continue

                ts = row["timestamp"]
                if not isinstance(ts, datetime):
                    ts = pd.to_datetime(ts).to_pydatetime()
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)

                var_title = cfg["name"]
                direction = "high" if dev > 0 else "low"
                reason = (
                    f"Meteorological extreme: {var_title} of {round(val, 2)} was unusually {direction} "
                    f"relative to historical mean ({round(mean_val, 2)}) by {round(abs(dev), 2)} (z-score: {round(z, 2)})."
                )

                anomalies.append(
                    AnomalyResult(
                        timestamp=ts,
                        region=region,
                        metric_name=col,
                        variable=col,
                        actual_value=round(val, 2),
                        expected_value=round(mean_val, 2),
                        deviation=round(dev, 2),
                        anomaly_score=score,
                        severity=severity,
                        anomaly_type="weather_extreme",
                        description=reason,
                        detection_method="meteorological_zscore",
                        model_version="v1.0.0"
                    )
                )

    logger.info(f"Weather Anomaly Detector found {len(anomalies)} extreme weather events.")
    return anomalies
