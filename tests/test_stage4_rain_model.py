"""Automated Unit & Integration Tests for Stage 4 Rain Prediction ML Module."""

import pytest
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np
from pathlib import Path

from app.models.rain_pipeline import (
    create_rain_target, extract_rain_features, chronological_split,
    find_optimal_threshold, RainModelTrainer, SAVED_MODELS_DIR
)
from app.models.rain_predictor import RainPredictor
from app.models.base import RainPredictionResult


@pytest.fixture
def sample_weather_sequence():
    """Generates synthetic historical weather sequence for ML testing."""
    now = datetime.now(timezone.utc)
    timestamps = pd.date_range(end=now, periods=120, freq="1h", tz="UTC")
    n = len(timestamps)

    hours = timestamps.hour
    temps = 20.0 + 5.0 * np.sin((hours - 8) * np.pi / 12) + np.random.normal(0, 1.0, n)
    humids = np.clip(60.0 - 15.0 * np.sin((hours - 8) * np.pi / 12) + np.random.normal(0, 3.0, n), 10.0, 100.0)
    pressures = 1013.25 + np.random.normal(0, 4.0, n)
    winds = np.abs(3.5 + np.random.normal(0, 1.5, n))
    clouds = np.clip(40.0 + np.random.normal(0, 25.0, n), 0.0, 100.0)
    precips = np.where(np.random.rand(n) < 0.2, np.random.exponential(2.0, n), 0.0)

    df = pd.DataFrame({
        "timestamp": timestamps,
        "location": "London",
        "temperature_c": np.round(temps, 2),
        "humidity_pct": np.round(humids, 2),
        "pressure_hpa": np.round(pressures, 2),
        "wind_speed_ms": np.round(winds, 2),
        "cloud_cover_pct": np.round(clouds, 2),
        "precipitation_mm": np.round(precips, 2),
        "source": "Open-Meteo-Test"
    })
    return df


def test_target_creation(sample_weather_sequence):
    """Verify target_rain_next_3h is binary 0 or 1 based on threshold."""
    df_target = create_rain_target(sample_weather_sequence, horizon_hours=3, threshold_mm=0.1)
    assert "target_rain_next_3h" in df_target.columns
    assert set(df_target["target_rain_next_3h"].unique()).issubset({0, 1})
    assert len(df_target) < len(sample_weather_sequence)  # Trailing horizon rows dropped


def test_zero_target_leakage(sample_weather_sequence):
    """Verify extracted feature matrix excludes future target precipitation."""
    df_target = create_rain_target(sample_weather_sequence, horizon_hours=3, threshold_mm=0.1)
    X, feature_names = extract_rain_features(df_target)

    assert "target_rain_next_3h" not in feature_names
    assert "precipitation_mm" not in feature_names  # Current/future precip excluded; only lag_1h retained
    assert "precipitation_mm_lag_1h" in feature_names


def test_chronological_split(sample_weather_sequence):
    """Verify chronological split maintains time ordering without data leakage."""
    df_target = create_rain_target(sample_weather_sequence, horizon_hours=3)
    X, _ = extract_rain_features(df_target)
    y = df_target["target_rain_next_3h"]

    X_train, X_val, X_test, y_train, y_val, y_test = chronological_split(X, y, train_ratio=0.70, val_ratio=0.15)

    assert len(X_train) + len(X_val) + len(X_test) == len(X)
    assert len(X_train) > len(X_val)
    # Check index continuity
    assert X_train.index[-1] < X_val.index[0]
    assert X_val.index[-1] < X_test.index[0]


def test_threshold_optimization():
    """Verify find_optimal_threshold selects best tau maximizing F1 score."""
    y_true = pd.Series([0, 0, 0, 1, 1, 1, 0, 1])
    y_probs = np.array([0.1, 0.2, 0.3, 0.6, 0.7, 0.8, 0.4, 0.9])

    best_tau, best_f1 = find_optimal_threshold(y_true, y_probs)
    assert 0.1 <= best_tau <= 0.9
    assert best_f1 > 0.8


def test_rain_model_training_and_serialization(sample_weather_sequence):
    """Verify RainModelTrainer trains candidates, evaluates metrics, and serializes artifacts."""
    model, metadata = RainModelTrainer.train_and_evaluate(sample_weather_sequence, model_type="random_forest")

    assert model is not None
    assert "metrics" in metadata
    assert "optimal_threshold" in metadata
    assert (SAVED_MODELS_DIR / "rain_predictor_v1.joblib").exists()
    assert (SAVED_MODELS_DIR / "rain_predictor_v1_meta.json").exists()


def test_rain_predictor_inference_service(sample_weather_sequence):
    """Verify RainPredictor inference service returns valid RainPredictionResult probability."""
    predictor = RainPredictor()
    predictor.fit(sample_weather_sequence)

    result = predictor.predict(sample_weather_sequence)
    assert isinstance(result, RainPredictionResult)
    assert 0.0 <= result.probability <= 1.0
    assert isinstance(result.rain_predicted, bool)
    assert result.model_version is not None
