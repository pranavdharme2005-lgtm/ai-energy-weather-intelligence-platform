"""Advanced Data Cleaning, Imputation, Outlier Classification, and Normalization Engine."""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from app.data.features import add_calendar_features
from app.utils.logger import get_logger

logger = get_logger(__name__)

WEATHER_CONDITION_MAPPING = {
    "clear sky": "Clear",
    "clear": "Clear",
    "sunny": "Clear",
    "mainly clear": "Mainly clear",
    "partly cloudy": "Partly cloudy",
    "scattered clouds": "Partly cloudy",
    "overcast": "Overcast",
    "cloudy": "Overcast",
    "fog": "Fog",
    "drizzle": "Light drizzle",
    "light rain": "Slight rain",
    "moderate rain": "Moderate rain",
    "heavy rain": "Heavy rain",
    "thunderstorm": "Thunderstorm"
}

DEFAULT_PHYSICAL_BOUNDS = {
    "temperature_c": (-50.0, 65.0),
    "humidity_pct": (0.0, 100.0),
    "pressure_hpa": (800.0, 1100.0),
    "wind_speed_ms": (0.0, 120.0),
    "cloud_cover_pct": (0.0, 100.0),
    "precipitation_mm": (0.0, 500.0),
    "demand_mw": (0.0, 50000.0)
}


class DataCleaner:
    """Cleaning and transformation pipeline utilities for raw datasets."""

    @staticmethod
    def clean_weather_data(df: pd.DataFrame) -> pd.DataFrame:
        """Cleans weather dataframe using column-specific imputation policies and normalization."""
        if df.empty:
            return df

        cleaned_df = df.copy()

        # Deduplicate on location + timestamp + source if present
        dedup_cols = [c for c in ["location", "timestamp", "source"] if c in cleaned_df.columns]
        if dedup_cols:
            cleaned_df = cleaned_df.drop_duplicates(subset=dedup_cols).copy()

        # Sort chronologically
        if "timestamp" in cleaned_df.columns:
            cleaned_df = cleaned_df.sort_values(by="timestamp").reset_index(drop=True)

        # 1. Continuous Meteorological Measurement Imputation (Temp, Humidity, Pressure, Wind)
        continuous_cols = ["temperature_c", "humidity_pct", "pressure_hpa", "wind_speed_ms"]
        for col in continuous_cols:
            if col in cleaned_df.columns and cleaned_df[col].isnull().any():
                # Linear time-aware interpolation for short gaps (<3 consecutive)
                cleaned_df[col] = cleaned_df[col].interpolate(method="linear", limit=3)
                # Rolling median imputation for remaining longer gaps
                if cleaned_df[col].isnull().any():
                    rolling_med = cleaned_df[col].rolling(window=7, min_periods=1, center=True).median()
                    cleaned_df[col] = cleaned_df[col].fillna(rolling_med).bfill().ffill()

        # 2. Event-based Sparse Variable Imputation (Precipitation)
        if "precipitation_mm" in cleaned_df.columns:
            cleaned_df["precipitation_mm"] = cleaned_df["precipitation_mm"].fillna(0.0)

        # 3. Categorical Normalization (Weather Condition)
        if "weather_condition" in cleaned_df.columns:
            cleaned_df["weather_condition"] = cleaned_df["weather_condition"].fillna("Clear")
            cleaned_df["weather_condition"] = DataCleaner.normalize_weather_conditions(cleaned_df["weather_condition"])

        logger.info(f"Cleaned weather dataframe ({len(cleaned_df)} records remaining).")
        return cleaned_df

    @staticmethod
    def clean_energy_data(df: pd.DataFrame) -> pd.DataFrame:
        """Cleans energy load dataframe using time-series load curve interpolation."""
        if df.empty:
            return df

        cleaned_df = df.copy()

        # Deduplicate on region + timestamp + source if present
        dedup_cols = [c for c in ["region", "timestamp", "source"] if c in cleaned_df.columns]
        if dedup_cols:
            cleaned_df = cleaned_df.drop_duplicates(subset=dedup_cols).copy()

        # Sort chronologically
        if "timestamp" in cleaned_df.columns:
            cleaned_df = cleaned_df.sort_values(by="timestamp").reset_index(drop=True)

        # Energy Demand Imputation
        if "demand_mw" in cleaned_df.columns and cleaned_df["demand_mw"].isnull().any():
            cleaned_df["demand_mw"] = cleaned_df["demand_mw"].interpolate(method="linear", limit=4)
            if cleaned_df["demand_mw"].isnull().any():
                if "timestamp" in cleaned_df.columns:
                    hourly_median = cleaned_df.groupby(pd.to_datetime(cleaned_df["timestamp"]).dt.hour)["demand_mw"].transform("median")
                    cleaned_df["demand_mw"] = cleaned_df["demand_mw"].fillna(hourly_median).bfill().ffill()

        logger.info(f"Cleaned energy load dataframe ({len(cleaned_df)} records remaining).")
        return cleaned_df

    @staticmethod
    def normalize_weather_conditions(series: pd.Series) -> pd.Series:
        """Normalizes categorical weather condition strings to standard titles."""
        def _norm(val):
            if not isinstance(val, str):
                return "Clear"
            s = val.strip().lower()
            return WEATHER_CONDITION_MAPPING.get(s, val.strip().title())

        return series.apply(_norm)

    @staticmethod
    def add_temporal_features(df: pd.DataFrame, timestamp_col: str = "timestamp") -> pd.DataFrame:
        """Stage 1 compatibility helper delegating to add_calendar_features."""
        return add_calendar_features(df, timestamp_col=timestamp_col)

    @staticmethod
    def detect_and_classify_outliers(
        df: pd.DataFrame,
        col_name: str,
        z_threshold: float = 2.0,
        lower_physical: Optional[float] = None,
        upper_physical: Optional[float] = None
    ) -> pd.DataFrame:
        """Evaluates and classifies outliers into VALID_EXTREME, SUSPICIOUS, or INVALID without deleting them."""
        if df.empty or col_name not in df.columns:
            return df

        # Determine physical bounds per column
        default_min, default_max = DEFAULT_PHYSICAL_BOUNDS.get(col_name, (-1e9, 1e9))
        min_bound = lower_physical if lower_physical is not None else default_min
        max_bound = upper_physical if upper_physical is not None else default_max

        result_df = df.copy()
        series = result_df[col_name]

        # Calculate IQR and z-scores on valid physical subset
        valid_mask = (series >= min_bound) & (series <= max_bound)
        valid_series = series[valid_mask]

        q1 = valid_series.quantile(0.25) if not valid_series.empty else 0.0
        q3 = valid_series.quantile(0.75) if not valid_series.empty else 100.0
        iqr = q3 - q1

        mean_val = valid_series.mean() if not valid_series.empty else 0.0
        std_val = valid_series.std() if len(valid_series) > 1 else 1.0

        def _classify(val):
            if pd.isnull(val):
                return "NORMAL"
            if val < min_bound or val > max_bound:
                return "INVALID"

            z = abs(val - mean_val) / (std_val + 1e-6)
            is_iqr_outlier = (val < (q1 - 1.5 * iqr)) or (val > (q3 + 1.5 * iqr))

            if z > z_threshold or is_iqr_outlier:
                return "VALID_EXTREME" if z < (z_threshold + 1.5) else "SUSPICIOUS"
            else:
                return "NORMAL"

        result_df[f"{col_name}_outlier_class"] = series.apply(_classify)

        outlier_counts = result_df[f"{col_name}_outlier_class"].value_counts().to_dict()
        logger.info(f"Outlier Classification for '{col_name}': {outlier_counts}")
        return result_df
