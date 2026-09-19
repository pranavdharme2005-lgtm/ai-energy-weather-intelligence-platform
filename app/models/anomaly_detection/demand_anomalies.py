"""Energy Demand Anomaly Detection Module (Z-score & IQR)."""

from typing import List, Dict, Any
from datetime import datetime, timezone
import pandas as pd
import numpy as np

from app.models.base import AnomalyResult
from app.models.anomaly_detection.scoring import calculate_anomaly_score, classify_severity
from app.utils.logger import get_logger

logger = get_logger(__name__)


def detect_demand_anomalies(
    df: pd.DataFrame, region: str = "Grid_Alpha", z_threshold: float = 2.5, iqr_factor: float = 1.5
) -> List[AnomalyResult]:
    """Detects energy demand spikes and dips using seasonal hourly baselines and rolling Z-scores.
    
    Args:
        df: Energy observations dataframe containing 'timestamp' and 'demand_mw'.
        region: Regional grid identifier.
        z_threshold: Z-score threshold for anomaly flag.
        iqr_factor: Interquartile range multiplier.
        
    Returns:
        List[AnomalyResult]: Standardized demand anomaly results.
    """
    anomalies = []
    if df.empty or "demand_mw" not in df.columns:
        return anomalies

    res_df = df.copy()
    if "timestamp" not in res_df.columns:
        return anomalies

    timestamps = pd.to_datetime(res_df["timestamp"])
    hours = timestamps.dt.hour

    # Calculate hourly seasonal baseline statistics (median, IQR, robust std)
    hourly_stats = res_df.groupby(hours)["demand_mw"].agg(
        ["median", "mean", "std", lambda x: np.percentile(x, 25), lambda x: np.percentile(x, 75)]
    ).rename(columns={"median": "hourly_median", "mean": "hourly_mean", "std": "hourly_std", "<lambda_0>": "q1", "<lambda_1>": "q3"})

    hourly_stats["iqr"] = hourly_stats["q3"] - hourly_stats["q1"]
    # Robust standard deviation estimate from IQR (IQR / 1.349) to prevent outlier masking
    hourly_stats["robust_std"] = np.maximum(25.0, hourly_stats["iqr"] / 1.349)
    hourly_stats["lower_iqr"] = hourly_stats["q1"] - iqr_factor * hourly_stats["iqr"]
    hourly_stats["upper_iqr"] = hourly_stats["q3"] + iqr_factor * hourly_stats["iqr"]

    # Merge statistics back into observation dataframe
    res_df["hour_idx"] = hours
    merged = pd.merge(res_df, hourly_stats, left_on="hour_idx", right_index=True, how="left")

    for idx, row in merged.iterrows():
        val = float(row["demand_mw"])
        expected = float(row["hourly_median"])
        std_val = float(row["robust_std"])
        dev = float(val - expected)
        z = abs(dev) / (std_val + 1e-6)

        is_z_outlier = z > z_threshold
        is_iqr_outlier = (val < row["lower_iqr"]) or (val > row["upper_iqr"])

        if is_z_outlier or is_iqr_outlier:
            score = calculate_anomaly_score(z)
            severity = classify_severity(score, z_score=z)
            if severity == "NORMAL":
                continue

            direction = "spike" if dev > 0 else "dip"
            ts = row["timestamp"]
            if not isinstance(ts, datetime):
                ts = pd.to_datetime(ts).to_pydatetime()
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            hour_str = f"{ts.hour:02d}:00 UTC"
            reason = (
                f"Energy demand {direction} of {round(val, 1)} MW at {hour_str} "
                f"deviated from seasonal hourly baseline ({round(expected, 1)} MW) by {round(abs(dev), 1)} MW (z-score: {round(z, 2)})."
            )

            anomalies.append(
                AnomalyResult(
                    timestamp=ts,
                    region=region,
                    metric_name="demand_mw",
                    variable="demand_mw",
                    actual_value=round(val, 2),
                    expected_value=round(expected, 2),
                    deviation=round(dev, 2),
                    anomaly_score=score,
                    severity=severity,
                    anomaly_type="demand_zscore",
                    description=reason,
                    detection_method="hourly_seasonal_zscore",
                    model_version="v1.0.0"
                )
            )

    logger.info(f"Demand Anomaly Detector found {len(anomalies)} anomalies across {len(df)} records.")
    return anomalies
