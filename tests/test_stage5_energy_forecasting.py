"""Automated Unit & Integration Tests for Stage 5 Energy Demand Forecasting Module."""

import pytest
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np
from pathlib import Path

from app.models.energy_forecasting.features import create_forecasting_target, extract_forecasting_features
from app.models.energy_forecasting.baselines import NaiveForecaster, SeasonalNaiveForecaster
from app.models.energy_forecasting.backtesting import ExpandingWindowCV, calculate_smape
from app.models.energy_forecasting.peak_analysis import analyze_peak_demand
from app.models.energy_forecasting.train import EnergyModelTrainer, SAVED_MODELS_DIR
from app.models.energy_forecasting.inference import EnergyForecastingInference
from app.models.energy_forecaster import EnergyForecaster
from app.services.energy_forecasting_service import EnergyForecastingService
from app.models.base import EnergyForecastResult


@pytest.fixture
def sample_energy_sequence():
    """Generates synthetic historical energy & weather time series for testing."""
    now = datetime.now(timezone.utc)
    timestamps = pd.date_range(end=now, periods=168, freq="1h", tz="UTC")
    n = len(timestamps)

    hours = timestamps.hour
    base_load = 2800.0 + 600.0 * np.sin((hours - 4) * np.pi / 12) + 300.0 * np.cos((hours - 14) * np.pi / 6)
    demands = np.round(base_load + np.random.normal(0, 30, n), 2)
    temps = np.round(18.0 + 5.0 * np.sin((hours - 8) * np.pi / 12), 2)

    df = pd.DataFrame({
        "timestamp": timestamps,
        "region": "Grid_Alpha",
        "demand_mw": demands,
        "temperature_c": temps,
        "humidity_pct": 60.0,
        "pressure_hpa": 1013.25,
        "wind_speed_ms": 3.5,
        "cloud_cover_pct": 40.0,
        "precipitation_mm": 0.0,
        "rain_probability": 0.05
    })
    return df


def test_forecasting_target_creation(sample_energy_sequence):
    """Verify create_forecasting_target creates target_demand_next_24h and drops trailing rows."""
    df_target = create_forecasting_target(sample_energy_sequence, horizon_hours=24)
    assert "target_demand_next_24h" in df_target.columns
    assert len(df_target) == len(sample_energy_sequence) - 24


def test_zero_rolling_feature_leakage(sample_energy_sequence):
    """Verify rolling statistics shift(1) prevents current/future target leakage."""
    df_target = create_forecasting_target(sample_energy_sequence, horizon_hours=24)
    X, feature_names = extract_forecasting_features(df_target)

    assert "target_demand_next_24h" not in feature_names
    assert "demand_mw" not in feature_names
    assert "demand_mw_lag_1h" in feature_names
    assert "demand_mw_rolling_mean_24h" in feature_names

    # Check first valid rolling mean matches expected past-only calculation
    first_past_mean = sample_energy_sequence["demand_mw"].iloc[:24].mean()
    assert abs(X["demand_mw_rolling_mean_24h"].iloc[24] - first_past_mean) < 1.0


def test_cyclical_time_encodings(sample_energy_sequence):
    """Verify sine and cosine cyclical encodings lie in [-1, 1] range."""
    X, feature_names = extract_forecasting_features(sample_energy_sequence)
    assert "hour_sin" in feature_names
    assert "hour_cos" in feature_names
    assert "day_sin" in feature_names
    assert "day_cos" in feature_names

    assert X["hour_sin"].min() >= -1.0 and X["hour_sin"].max() <= 1.0
    assert X["hour_cos"].min() >= -1.0 and X["hour_cos"].max() <= 1.0


def test_baseline_forecasters(sample_energy_sequence):
    """Verify Naive and Seasonal Naive baseline predictions."""
    df_target = create_forecasting_target(sample_energy_sequence, horizon_hours=24)
    X, _ = extract_forecasting_features(df_target)
    y = df_target["target_demand_next_24h"]

    naive = NaiveForecaster()
    naive.fit(X, y)
    naive_preds = naive.predict(X)
    assert len(naive_preds) == len(X)
    assert np.all(naive_preds == X["demand_mw_lag_1h"].values)

    snaive = SeasonalNaiveForecaster(season_lag=24)
    snaive.fit(X, y)
    snaive_preds = snaive.predict(X)
    assert len(snaive_preds) == len(X)
    assert np.all(snaive_preds == X["demand_mw_lag_24h"].values)


def test_expanding_window_backtester(sample_energy_sequence):
    """Verify ExpandingWindowCV executes multi-fold time-series evaluation."""
    df_target = create_forecasting_target(sample_energy_sequence, horizon_hours=24)
    X, _ = extract_forecasting_features(df_target)
    y = df_target["target_demand_next_24h"]

    cv = ExpandingWindowCV(initial_train_ratio=0.50, n_splits=3, horizon_hours=24)
    res = cv.evaluate(lambda: NaiveForecaster(), X, y)

    assert res["folds"] > 0
    assert res["mae"] > 0.0
    assert res["rmse"] > 0.0
    assert res["smape"] > 0.0


def test_peak_demand_analysis_helper():
    """Verify analyze_peak_demand correctly extracts peak timestamp, MW, and severity."""
    records = [
        {"forecast_target_time": "2026-09-19T10:00:00Z", "forecasted_demand_mw": 2800.0},
        {"forecast_target_time": "2026-09-19T11:00:00Z", "forecasted_demand_mw": 3500.0},
        {"forecast_target_time": "2026-09-19T12:00:00Z", "forecasted_demand_mw": 2900.0}
    ]

    metrics = analyze_peak_demand(records)
    assert metrics["peak_demand_mw"] == 3500.0
    assert metrics["peak_timestamp"] == "2026-09-19T11:00:00Z"
    assert metrics["peak_severity"] in ["ELEVATED", "HIGH_CRITICAL"]


def test_energy_model_training_and_serialization(sample_energy_sequence):
    """Verify EnergyModelTrainer trains candidates, evaluates metrics, and serializes artifacts."""
    model, metadata = EnergyModelTrainer.train_and_evaluate(sample_energy_sequence, horizon_hours=24, model_type="random_forest")

    assert model is not None
    assert "data_frequency" in metadata
    assert metadata["data_frequency"] == "hourly (1h)"
    assert metadata["forecast_horizon"] == "24h"
    assert (SAVED_MODELS_DIR / "energy_forecaster_v1.joblib").exists()
    assert (SAVED_MODELS_DIR / "energy_forecaster_v1_meta.json").exists()


def test_energy_forecaster_inference_service(sample_energy_sequence):
    """Verify EnergyForecaster inference service outputs valid 24-hour demand trajectory."""
    service = EnergyForecastingService()
    result = service.generate_forecast(region="Grid_Alpha", horizon_hours=24, save_to_db=False)

    assert result["region"] == "Grid_Alpha"
    assert result["forecast_horizon"] == "24h"
    assert len(result["forecasts"]) == 24
    assert "peak_analysis" in result

    first_pred = result["forecasts"][0]
    assert "forecasted_demand_mw" in first_pred
    assert first_pred["confidence_lower_mw"] <= first_pred["forecasted_demand_mw"] <= first_pred["confidence_upper_mw"]


def test_insufficient_data_error_handling():
    """Verify inference engine raises ValueError when input history is empty."""
    engine = EnergyForecastingInference()
    empty_df = pd.DataFrame()

    with pytest.raises(ValueError, match="cannot be empty"):
        engine.predict_horizon(empty_df, horizon_hours=24)
