"""Automated Unit & Integration Tests for Stage 6 Energy & Weather Anomaly Detection Module."""

import pytest
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np
from pathlib import Path

from app.models.base import AnomalyResult, EnergyForecastResult
from app.models.anomaly_detection.scoring import calculate_anomaly_score, classify_severity
from app.models.anomaly_detection.demand_anomalies import detect_demand_anomalies
from app.models.anomaly_detection.forecast_anomalies import detect_forecast_anomalies
from app.models.anomaly_detection.weather_anomalies import detect_weather_anomalies
from app.models.anomaly_detection.multivariate_anomalies import detect_multivariate_anomalies
from app.models.anomaly_detection.summary import calculate_anomaly_summary
from app.models.anomaly_detector import AnomalyDetector
from app.services.anomaly_detection_service import AnomalyDetectionService


@pytest.fixture
def sample_anomaly_dataset():
    """Generates synthetic historical time-series with known injected anomalies for testing."""
    now = datetime.now(timezone.utc)
    timestamps = pd.date_range(end=now, periods=168, freq="1h", tz="UTC")
    n = len(timestamps)

    hours = np.array(timestamps.hour, dtype=float)
    base_demand = 2800.0 + 600.0 * np.sin((hours - 4) * np.pi / 12) + 300.0 * np.cos((hours - 14) * np.pi / 6)
    demands = np.round(base_demand + np.random.normal(0, 30, n), 2)
    temps = np.round(18.0 + 5.0 * np.sin((hours - 8) * np.pi / 12) + np.random.normal(0, 1.0, n), 2)

    # Inject synthetic anomalies
    demands[30] += 2500.0   # Severe load spike anomaly
    demands[90] -= 2000.0   # Severe load dip anomaly
    temps[50] += 20.0       # Severe heatwave anomaly

    df_e = pd.DataFrame({
        "timestamp": timestamps,
        "region": "Grid_Alpha",
        "demand_mw": demands
    })

    df_w = pd.DataFrame({
        "timestamp": timestamps,
        "location": "London",
        "temperature_c": temps,
        "humidity_pct": 60.0,
        "pressure_hpa": 1013.25,
        "wind_speed_ms": 3.5,
        "cloud_cover_pct": 40.0,
        "precipitation_mm": 0.0
    })

    return df_e, df_w


def test_anomaly_scoring_and_severity():
    """Verify calculate_anomaly_score and classify_severity bounds."""
    score_normal = calculate_anomaly_score(1.0)
    assert 0.0 <= score_normal <= 0.30
    assert classify_severity(score_normal) == "NORMAL"

    score_high = calculate_anomaly_score(3.8)
    assert 0.70 <= score_high < 0.88
    assert classify_severity(score_high) == "HIGH"

    score_critical = calculate_anomaly_score(5.0)
    assert score_critical >= 0.88
    assert classify_severity(score_critical) == "CRITICAL"


def test_demand_anomaly_detection(sample_anomaly_dataset):
    """Verify detect_demand_anomalies identifies injected demand spike and dip."""
    df_e, _ = sample_anomaly_dataset
    anomalies = detect_demand_anomalies(df_e, region="Grid_Alpha", z_threshold=2.5)

    assert len(anomalies) >= 2
    spike_found = any(a.deviation > 1000.0 and a.severity in ["HIGH", "CRITICAL"] for a in anomalies)
    assert spike_found
    for a in anomalies:
        assert isinstance(a, AnomalyResult)
        assert a.anomaly_type == "demand_zscore"
        assert len(a.description) > 10


def test_forecast_interval_breach_detection():
    """Verify detect_forecast_anomalies catches actual demand breaching forecast bounds."""
    now = datetime.now(timezone.utc)
    target_time = now + timedelta(hours=1)

    f_res = [
        EnergyForecastResult(
            timestamp=now,
            forecast_target_time=target_time,
            region="Grid_Alpha",
            forecasted_demand_mw=2800.0,
            confidence_lower_mw=2650.0,
            confidence_upper_mw=2950.0,
            forecast_horizon="24h"
        )
    ]

    actual_df = pd.DataFrame({
        "timestamp": [target_time],
        "demand_mw": [3500.0]  # Breaches upper bound 2950.0
    })

    anomalies = detect_forecast_anomalies(actual_df, f_res, region="Grid_Alpha")
    assert len(anomalies) == 1
    anom = anomalies[0]
    assert anom.anomaly_type == "forecast_deviation"
    assert anom.actual_value == 3500.0
    assert "breached" in anom.description


def test_weather_extreme_detection(sample_anomaly_dataset):
    """Verify detect_weather_anomalies catches injected heatwave temperature extreme."""
    _, df_w = sample_anomaly_dataset
    anomalies = detect_weather_anomalies(df_w, region="Grid_Alpha")

    assert len(anomalies) >= 1
    temp_anom = [a for a in anomalies if a.variable == "temperature_c"]
    assert len(temp_anom) >= 1
    assert temp_anom[0].actual_value > 35.0
    assert temp_anom[0].severity in ["HIGH", "CRITICAL"]


def test_multivariate_isolation_forest_detection(sample_anomaly_dataset):
    """Verify detect_multivariate_anomalies fits Isolation Forest and returns results."""
    df_e, df_w = sample_anomaly_dataset
    combined_df = pd.merge_asof(df_e.sort_values("timestamp"), df_w.sort_values("timestamp"), on="timestamp")

    anomalies = detect_multivariate_anomalies(combined_df, region="Grid_Alpha")
    assert isinstance(anomalies, list)
    if anomalies:
        for a in anomalies:
            assert a.anomaly_type == "multivariate_isolation"
            assert a.detection_method == "isolation_forest"


def test_anomaly_summary_calculation(sample_anomaly_dataset):
    """Verify calculate_anomaly_summary computes correct aggregated counts."""
    df_e, _ = sample_anomaly_dataset
    anomalies = detect_demand_anomalies(df_e, region="Grid_Alpha")
    summary = calculate_anomaly_summary(anomalies)

    assert summary["total_anomalies"] == len(anomalies)
    assert "high_severity_count" in summary
    assert "severity_breakdown" in summary


def test_anomaly_detector_orchestrator(sample_anomaly_dataset):
    """Verify production AnomalyDetector class orchestrates detect_all()."""
    df_e, df_w = sample_anomaly_dataset
    detector = AnomalyDetector()
    all_anoms = detector.detect_all(df_energy=df_e, df_weather=df_w, region="Grid_Alpha")

    assert len(all_anoms) >= 3
    types = {a.anomaly_type for a in all_anoms}
    assert "demand_zscore" in types
    assert "weather_extreme" in types


def test_anomaly_service_execution():
    """Verify AnomalyDetectionService runs full pipeline without errors."""
    service = AnomalyDetectionService()
    results = service.run_full_detection(region="Grid_Alpha", location="London", hours=48, save_to_db=False)

    assert results["region"] == "Grid_Alpha"
    assert "summary" in results
    assert "anomalies" in results


def test_empty_dataframe_handling():
    """Verify anomaly detectors return empty list gracefully for empty dataframes."""
    empty_df = pd.DataFrame()
    assert detect_demand_anomalies(empty_df) == []
    assert detect_weather_anomalies(empty_df) == []
    assert detect_multivariate_anomalies(empty_df) == []
