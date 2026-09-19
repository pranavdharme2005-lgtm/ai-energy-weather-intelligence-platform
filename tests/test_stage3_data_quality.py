"""Automated Unit & Integration Tests for Stage 3 Data Quality Engine, Feature Engineering & EDA."""

import pytest
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np

from app.data.quality_engine import DataQualityEngine
from app.data.cleaner import DataCleaner
from app.data.features import add_calendar_features, create_lag_features, create_rolling_features, merge_weather_energy
from app.services.eda import EDAEngine


def test_quality_score_methodology():
    """Verify DataQualityEngine calculates component sub-scores and overall score correctly."""
    data = {
        "timestamp": pd.date_range(start="2026-09-19 00:00", periods=10, freq="1h"),
        "location": ["London"] * 10,
        "source": ["Open-Meteo-API"] * 10,
        "temperature_c": [20.0, 21.0, 22.0, None, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0],  # 1 missing cell
        "humidity_pct": [50.0] * 10,
        "pressure_hpa": [1013.25] * 10,
        "wind_speed_ms": [3.0] * 10,
        "precipitation_mm": [0.0] * 10
    }
    df = pd.DataFrame(data)
    report = DataQualityEngine.evaluate_weather_dataframe(df)

    assert report.total_records == 10
    assert report.missing_cells == 1
    assert report.scores.overall_quality_score > 90.0
    assert 0.0 <= report.scores.completeness_score <= 100.0


def test_column_specific_imputation():
    """Verify continuous variables use linear/median interpolation while precipitation defaults to 0.0."""
    data = {
        "timestamp": pd.date_range(start="2026-09-19 00:00", periods=5, freq="1h"),
        "location": ["London"] * 5,
        "temperature_c": [20.0, None, 22.0, 23.0, 24.0],
        "precipitation_mm": [None, 1.5, None, 0.0, None]
    }
    df = pd.DataFrame(data)
    cleaned = DataCleaner.clean_weather_data(df)

    assert cleaned["temperature_c"].isnull().sum() == 0
    assert cleaned["temperature_c"].iloc[1] == 21.0  # Linear interpolation
    assert cleaned["precipitation_mm"].isnull().sum() == 0
    assert cleaned["precipitation_mm"].iloc[0] == 0.0  # Sparse 0.0 fill


def test_outlier_classification():
    """Verify outliers are classified into VALID_EXTREME, SUSPICIOUS, or INVALID without data loss."""
    df = pd.DataFrame({
        "temperature_c": [20.0, 21.0, 22.0, 21.5, 20.5, 22.5, 45.0, 99.0]  # 45=Extreme, 99=Invalid (>65)
    })
    classified = DataCleaner.detect_and_classify_outliers(df, "temperature_c", z_threshold=2.0)

    assert len(classified) == 8
    assert classified["temperature_c_outlier_class"].iloc[-1] == "INVALID"
    assert classified["temperature_c_outlier_class"].iloc[-2] in ["VALID_EXTREME", "SUSPICIOUS"]


def test_timestamp_gap_detection():
    """Verify gap detection identifies missing hourly intervals."""
    # Skip hour 02:00
    times = pd.to_datetime(["2026-09-19 00:00", "2026-09-19 01:00", "2026-09-19 03:00", "2026-09-19 04:00"])
    df = pd.DataFrame({"timestamp": times, "region": ["Grid_Alpha"] * 4, "demand_mw": [3000.0] * 4, "source": ["PJM"] * 4})

    report = DataQualityEngine.evaluate_energy_dataframe(df)
    assert report.timestamp_gaps_count >= 1


def test_feature_engineering_zero_future_leakage():
    """Verify lag and rolling features look strictly backward (shift(1) / shift(lag))."""
    df = pd.DataFrame({
        "timestamp": pd.date_range(start="2026-09-19 00:00", periods=5, freq="1h"),
        "demand_mw": [1000.0, 2000.0, 3000.0, 4000.0, 5000.0]
    })

    feat_df = create_lag_features(df, target_col="demand_mw", lags=[1])
    feat_df = create_rolling_features(feat_df, target_col="demand_mw", windows=[2])

    # Lag 1 at index 1 must equal value at index 0 (1000.0)
    assert feat_df["demand_mw_lag_1h"].iloc[1] == 1000.0
    # Rolling mean at index 2 (t=3000) shifted 1 period must be mean of [1000, 2000] = 1500.0 (NO leakage of 3000.0)
    assert feat_df["demand_mw_rolling_mean_2h"].iloc[2] == 1500.0


def test_weather_energy_time_aligned_merge():
    """Verify pd.merge_asof time-aware alignment with tolerance matching."""
    w_df = pd.DataFrame({
        "timestamp": pd.to_datetime(["2026-09-19 10:02:00", "2026-09-19 11:00:00"]),
        "temperature_c": [22.0, 25.0]
    })
    e_df = pd.DataFrame({
        "timestamp": pd.to_datetime(["2026-09-19 10:00:00", "2026-09-19 11:00:00"]),
        "demand_mw": [3100.0, 3400.0]
    })

    merged = merge_weather_energy(w_df, e_df, tolerance_minutes=15)
    assert len(merged) == 2
    assert "temperature_c" in merged.columns
    assert "demand_mw" in merged.columns


def test_eda_statistical_engine():
    """Verify EDAEngine calculates percentiles, correlations, and structured narrative."""
    df = pd.DataFrame({
        "timestamp": pd.date_range(start="2026-09-19 00:00", periods=24, freq="1h"),
        "demand_mw": [2500 + i * 50 for i in range(24)],
        "temperature_c": [20 + i * 0.5 for i in range(24)]
    })

    summary = EDAEngine.analyze_dataset(df)
    assert summary.dataset_records == 24
    assert summary.demand_stats is not None
    assert summary.demand_stats.mean > 0
    assert len(summary.correlations) >= 1
    assert summary.correlations[0].pearson_corr > 0.9  # Strong positive mock correlation
