"""Time-Series Feature Engineering for Energy Demand Forecasting.

Strictly enforces zero future leakage:
- Lags use backward shift(k).
- Rolling features use past-only history: demand_mw.shift(1).rolling(w).
- Weather variables use past observed meteorological data up to prediction origin t.
"""

from typing import Tuple, List, Optional
import numpy as np
import pandas as pd
from app.data.features import add_calendar_features
from app.utils.logger import get_logger

logger = get_logger(__name__)


def create_forecasting_target(df: pd.DataFrame, horizon_hours: int = 24) -> pd.DataFrame:
    """Creates target variable for direct multi-step or lead-time energy demand forecasting.
    
    Target at row t represents demand_mw at timestamp t + horizon_hours.
    Trailing horizon_hours rows with unknown future demand are dropped.
    """
    if df.empty or "demand_mw" not in df.columns:
        return df

    res_df = df.copy()
    target_col = f"target_demand_next_{horizon_hours}h"
    res_df[target_col] = res_df["demand_mw"].shift(-horizon_hours)

    # Drop trailing rows where future horizon target cannot be observed
    res_df = res_df.dropna(subset=[target_col]).reset_index(drop=True)
    return res_df


def extract_forecasting_features(
    df: pd.DataFrame, rain_probs: Optional[pd.Series] = None
) -> Tuple[pd.DataFrame, List[str]]:
    """Extracts predictor feature matrix X for time-series energy load forecasting.
    
    Returns:
        Tuple[pd.DataFrame, List[str]]: Feature matrix X and list of feature column names.
    """
    feat_df = df.copy()

    # 1. Historical Demand Lags (strictly backward shift)
    if "demand_mw" in feat_df.columns:
        demand = feat_df["demand_mw"]
        lag_intervals = [1, 2, 3, 6, 12, 24, 48, 168]
        for lag in lag_intervals:
            feat_df[f"demand_mw_lag_{lag}h"] = demand.shift(lag)

        # 2. Past-Only Rolling Features (shift(1) shield prevents current/future target leakage)
        past_demand = demand.shift(1)
        feat_df["demand_mw_rolling_mean_6h"] = past_demand.rolling(window=6, min_periods=1).mean()
        feat_df["demand_mw_rolling_std_6h"] = past_demand.rolling(window=6, min_periods=1).std().fillna(0.0)

        feat_df["demand_mw_rolling_mean_24h"] = past_demand.rolling(window=24, min_periods=1).mean()
        feat_df["demand_mw_rolling_std_24h"] = past_demand.rolling(window=24, min_periods=1).std().fillna(0.0)
        feat_df["demand_mw_rolling_min_24h"] = past_demand.rolling(window=24, min_periods=1).min()
        feat_df["demand_mw_rolling_max_24h"] = past_demand.rolling(window=24, min_periods=1).max()

        feat_df["demand_mw_rolling_mean_168h"] = past_demand.rolling(window=168, min_periods=1).mean()

    # 3. Calendar & Cyclical Features
    feat_df = add_calendar_features(feat_df)
    if "day_of_week" in feat_df.columns:
        dow = feat_df["day_of_week"]
        feat_df["day_sin"] = np.sin(2 * np.pi * dow / 7.0)
        feat_df["day_cos"] = np.cos(2 * np.pi * dow / 7.0)
    else:
        feat_df["day_sin"] = 0.0
        feat_df["day_cos"] = 1.0

    # 4. Rain Probability Feature (from Stage 4 Rain Predictor)
    if rain_probs is not None:
        feat_df["rain_probability"] = rain_probs.values
    elif "rain_probability" not in feat_df.columns:
        feat_df["rain_probability"] = 0.0

    feature_cols = [
        # Demand Lags
        "demand_mw_lag_1h", "demand_mw_lag_2h", "demand_mw_lag_3h",
        "demand_mw_lag_6h", "demand_mw_lag_12h", "demand_mw_lag_24h",
        "demand_mw_lag_48h", "demand_mw_lag_168h",
        # Rolling Statistics
        "demand_mw_rolling_mean_6h", "demand_mw_rolling_std_6h",
        "demand_mw_rolling_mean_24h", "demand_mw_rolling_std_24h",
        "demand_mw_rolling_min_24h", "demand_mw_rolling_max_24h",
        "demand_mw_rolling_mean_168h",
        # Temporal & Cyclical
        "hour_sin", "hour_cos", "day_sin", "day_cos", "month_sin", "month_cos",
        "is_weekend", "season",
        # Weather
        "temperature_c", "humidity_pct", "pressure_hpa", "wind_speed_ms",
        "cloud_cover_pct", "precipitation_mm", "rain_probability"
    ]

    # Ensure all feature columns exist with fallbacks
    for col in feature_cols:
        if col not in feat_df.columns:
            feat_df[col] = 0.0

    X = feat_df[feature_cols].copy()
    # Backfill/forward fill initial NaN values resulting from lags
    X = X.bfill().ffill().fillna(0.0)

    return X, feature_cols
