"""Feature Engineering & Time-Aware Weather-Energy Merging Engine (Zero Future-Leakage)."""

import pandas as pd
import numpy as np
from typing import List, Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)


def add_calendar_features(df: pd.DataFrame, timestamp_col: str = "timestamp") -> pd.DataFrame:
    """Extracts calendar and cyclical temporal encodings without future data leakage."""
    if df.empty or timestamp_col not in df.columns:
        return df

    feat_df = df.copy()
    dt = pd.to_datetime(feat_df[timestamp_col])

    feat_df["hour"] = dt.dt.hour
    feat_df["day"] = dt.dt.day
    feat_df["day_of_week"] = dt.dt.dayofweek
    feat_df["day_of_month"] = dt.dt.day
    feat_df["month"] = dt.dt.month
    feat_df["is_weekend"] = (dt.dt.dayofweek >= 5).astype(int)

    # Meteorological season mapping (1: Winter, 2: Spring, 3: Summer, 4: Autumn)
    def _get_season(month):
        if month in [12, 1, 2]:
            return 1
        elif month in [3, 4, 5]:
            return 2
        elif month in [6, 7, 8]:
            return 3
        else:
            return 4

    feat_df["season"] = dt.dt.month.apply(_get_season)

    # Continuous Cyclical Time Encodings
    feat_df["hour_sin"] = np.sin(2 * np.pi * feat_df["hour"] / 24.0)
    feat_df["hour_cos"] = np.cos(2 * np.pi * feat_df["hour"] / 24.0)
    feat_df["month_sin"] = np.sin(2 * np.pi * feat_df["month"] / 12.0)
    feat_df["month_cos"] = np.cos(2 * np.pi * feat_df["month"] / 12.0)

    return feat_df


def create_lag_features(df: pd.DataFrame, target_col: str = "demand_mw", lags: List[int] = None) -> pd.DataFrame:
    """Creates backward-shifted lag features ensuring zero future data leakage."""
    if df.empty or target_col not in df.columns:
        return df

    lags = lags or [1, 2, 24]
    feat_df = df.copy()

    for lag in lags:
        feat_df[f"{target_col}_lag_{lag}h"] = feat_df[target_col].shift(lag)

    return feat_df


def create_rolling_features(
    df: pd.DataFrame, target_col: str = "demand_mw", windows: List[int] = None
) -> pd.DataFrame:
    """Creates rolling mean and standard deviation features strictly looking backward."""
    if df.empty or target_col not in df.columns:
        return df

    windows = windows or [6, 24]
    feat_df = df.copy()

    for w in windows:
        # Shift 1 period first to guarantee no current-step/future leakage in rolling window
        feat_df[f"{target_col}_rolling_mean_{w}h"] = feat_df[target_col].shift(1).rolling(window=w, min_periods=1).mean()
        feat_df[f"{target_col}_rolling_std_{w}h"] = feat_df[target_col].shift(1).rolling(window=w, min_periods=1).std().fillna(0.0)

    return feat_df


def merge_weather_energy(
    weather_df: pd.DataFrame, energy_df: pd.DataFrame, tolerance_minutes: int = 30
) -> pd.DataFrame:
    """Performs time-aware alignment between weather observation and energy demand streams.
    
    Uses `pd.merge_asof` on sorted timestamps with a strict tolerance bound.
    """
    if weather_df.empty or energy_df.empty:
        logger.warning("One or both DataFrames are empty. Cannot perform time-aligned merge.")
        return pd.DataFrame()

    w_df = weather_df.copy()
    e_df = energy_df.copy()

    w_df["timestamp"] = pd.to_datetime(w_df["timestamp"])
    e_df["timestamp"] = pd.to_datetime(e_df["timestamp"])

    w_df = w_df.sort_values(by="timestamp").reset_index(drop=True)
    e_df = e_df.sort_values(by="timestamp").reset_index(drop=True)

    tolerance = pd.Timedelta(minutes=tolerance_minutes)

    # Perform time-aware nearest match merge
    merged_df = pd.merge_asof(
        e_df,
        w_df,
        on="timestamp",
        direction="nearest",
        tolerance=tolerance,
        suffixes=("_energy", "_weather")
    )

    logger.info(f"Merged {len(e_df)} energy records with {len(w_df)} weather records -> {len(merged_df)} aligned records.")
    return merged_df
