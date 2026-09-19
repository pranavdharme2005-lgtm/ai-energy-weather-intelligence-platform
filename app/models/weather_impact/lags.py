"""Lagged weather impact analysis submodule."""

from typing import Dict, Any, List
import pandas as pd
import numpy as np
from app.utils.logger import get_logger

logger = get_logger(__name__)


def generate_lagged_weather_features(
    df: pd.DataFrame, lags: List[int] = [1, 2, 3, 24], weather_cols: List[str] = None
) -> pd.DataFrame:
    """Generates lagged weather features using backward shifts ONLY to eliminate look-ahead leakage.

    Args:
        df: DataFrame sorted chronologically by timestamp.
        lags: List of lag periods (hours/steps).
        weather_cols: Weather column names to lag.

    Returns:
        DataFrame containing original columns plus new lagged features.
    """
    if df.empty:
        return df

    res = df.copy()

    # Ensure chronological sorting
    if "timestamp" in res.columns:
        res = res.sort_values("timestamp").reset_index(drop=True)

    if weather_cols is None:
        candidate_cols = ["temperature_c", "humidity_pct", "precipitation_mm", "cdd", "hdd"]
        weather_cols = [c for c in candidate_cols if c in res.columns]

    for col in weather_cols:
        for lag in lags:
            if lag > 0:  # Enforce positive shift (backward in time)
                res[f"{col}_lag_{lag}h"] = res[col].shift(lag)

    return res


def analyze_lagged_impacts(
    df: pd.DataFrame, lags: List[int] = [1, 2, 3, 24]
) -> Dict[str, Any]:
    """Analyzes the correlation between historical lagged weather conditions and current energy demand."""
    if df.empty or "demand_mw" not in df.columns:
        return {"lagged_correlations": {}, "selected_lags": lags, "sufficient_data": False}

    df_lagged = generate_lagged_weather_features(df, lags=lags)
    lag_cols = [col for col in df_lagged.columns if "_lag_" in col]

    if not lag_cols:
        return {"lagged_correlations": {}, "selected_lags": lags, "sufficient_data": False}

    correlations = {}
    for col in lag_cols:
        sub = df_lagged[["demand_mw", col]].dropna()
        if len(sub) >= 10:
            corr = sub["demand_mw"].corr(sub[col])
            correlations[col] = 0.0 if np.isnan(corr) else round(float(corr), 4)

    return {
        "lagged_correlations": correlations,
        "selected_lags_hours": lags,
        "sufficient_data": len(correlations) > 0,
        "documentation": "Lagged features reflect weather persistence and thermal inertia of buildings (e.g. past 24h temperature impact on cooling load).",
    }
