"""Forecast Deviation Anomaly Detector utilizing Stage 5 Prediction Intervals."""

from typing import List, Dict, Any
from datetime import datetime, timezone
import pandas as pd
import numpy as np

from app.models.base import AnomalyResult, EnergyForecastResult
from app.models.anomaly_detection.scoring import calculate_anomaly_score, classify_severity
from app.utils.logger import get_logger

logger = get_logger(__name__)


def detect_forecast_anomalies(
    actual_df: pd.DataFrame, forecast_results: List[EnergyForecastResult], region: str = "Grid_Alpha"
) -> List[AnomalyResult]:
    """Detects observations where actual demand significantly breaches Stage 5 forecast prediction intervals.
    
    Args:
        actual_df: DataFrame containing 'timestamp' and 'demand_mw'.
        forecast_results: List of Stage 5 EnergyForecastResult objects.
        region: Regional grid identifier.
        
    Returns:
        List[AnomalyResult]: Detected forecast deviation anomalies.
    """
    anomalies = []
    if actual_df.empty or not forecast_results or "demand_mw" not in actual_df.columns:
        return anomalies

    # Convert forecast results into a DataFrame indexed by target time
    f_dicts = []
    for f in forecast_results:
        f_dicts.append({
            "forecast_target_time": pd.to_datetime(f.forecast_target_time, utc=True),
            "forecasted_demand_mw": f.forecasted_demand_mw,
            "confidence_lower_mw": f.confidence_lower_mw,
            "confidence_upper_mw": f.confidence_upper_mw
        })
    f_df = pd.DataFrame(f_dicts)

    a_df = actual_df.copy()
    a_df["timestamp"] = pd.to_datetime(a_df["timestamp"], utc=True)

    # Time-aligned merge between actuals and predictions
    merged = pd.merge_asof(
        a_df.sort_values("timestamp"),
        f_df.sort_values("forecast_target_time"),
        left_on="timestamp",
        right_on="forecast_target_time",
        direction="nearest",
        tolerance=pd.Timedelta("30min")
    ).dropna(subset=["forecasted_demand_mw"])

    for idx, row in merged.iterrows():
        actual = float(row["demand_mw"])
        pred = float(row["forecasted_demand_mw"])
        lower = float(row["confidence_lower_mw"]) if pd.notnull(row["confidence_lower_mw"]) else pred * 0.90
        upper = float(row["confidence_upper_mw"]) if pd.notnull(row["confidence_upper_mw"]) else pred * 1.10

        dev = float(actual - pred)
        abs_dev = abs(dev)
        interval_width = (upper - lower) / 2.0 + 1e-6

        is_breach_upper = actual > upper
        is_breach_lower = actual < lower
        z_equiv = abs_dev / interval_width

        if is_breach_upper or is_breach_lower or z_equiv > 1.5:
            score = calculate_anomaly_score(z_equiv, max_z=3.0)
            severity = classify_severity(score, z_score=z_equiv * 1.5)
            if severity == "NORMAL":
                continue

            ts = row["timestamp"]
            if not isinstance(ts, datetime):
                ts = pd.to_datetime(ts).to_pydatetime()
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            bound_breach = f"upper bound ({round(upper, 1)} MW)" if is_breach_upper else f"lower bound ({round(lower, 1)} MW)"
            reason = (
                f"Actual demand ({round(actual, 1)} MW) breached Stage 5 forecast {bound_breach} "
                f"by {round(abs_dev, 1)} MW relative to predicted expectation ({round(pred, 1)} MW)."
            )

            anomalies.append(
                AnomalyResult(
                    timestamp=ts,
                    region=region,
                    metric_name="demand_mw",
                    variable="demand_mw",
                    actual_value=round(actual, 2),
                    expected_value=round(pred, 2),
                    deviation=round(dev, 2),
                    anomaly_score=score,
                    severity=severity,
                    anomaly_type="forecast_deviation",
                    description=reason,
                    detection_method="forecast_residual_interval_breach",
                    model_version="v1.0.0"
                )
            )

    logger.info(f"Forecast Anomaly Detector found {len(anomalies)} deviation anomalies.")
    return anomalies
