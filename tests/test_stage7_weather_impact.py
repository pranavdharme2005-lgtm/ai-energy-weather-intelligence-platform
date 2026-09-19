"""Automated test suite for Stage 7 — Weather Impact Analytics Module."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

from app.models.weather_impact.descriptive import analyze_weather_conditions
from app.models.weather_impact.temperature import (
    calculate_cdd_hdd,
    analyze_temperature_impact,
    evaluate_nonlinear_temperature_relationship,
)
from app.models.weather_impact.rain_humidity import analyze_rain_impact, analyze_humidity_impact
from app.models.weather_impact.correlations import calculate_weather_correlations
from app.models.weather_impact.lags import generate_lagged_weather_features, analyze_lagged_impacts
from app.models.weather_impact.forecast_experiment import evaluate_weather_forecasting_value
from app.models.weather_impact.peak_context import (
    analyze_peak_demand_weather_context,
    analyze_time_of_day_weather_impact,
    analyze_regional_weather_impact,
)
from app.models.weather_impact.scoring import calculate_weather_impact_score
from app.models.weather_impact.summary import generate_weather_impact_summary
from app.services.weather_energy_impact import WeatherImpactService, WeatherEnergyImpactAnalyzer
from app.database.session import SessionLocal, init_db
from app.database.models import WeatherImpactRecord


@pytest.fixture
def sample_impact_df():
    """Generates synthetic time-aligned weather and energy demand dataset for unit testing."""
    np.random.seed(42)
    n = 200
    start_time = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    timestamps = [start_time + timedelta(hours=i) for i in range(n)]

    # Temperature with U-shaped relationship (cooling and heating demand)
    temp = np.random.uniform(5.0, 35.0, n)
    cdd = np.maximum(temp - 18.3, 0.0)
    hdd = np.maximum(18.3 - temp, 0.0)

    # Demand driven by temp, humidity, plus random noise
    humidity = np.random.uniform(30.0, 95.0, n)
    precip = np.where(np.random.rand(n) > 0.8, np.random.uniform(0.5, 10.0, n), 0.0)
    weather_cond = np.where(precip > 0.1, "Rain", np.where(humidity > 70, "Cloudy", "Clear"))

    base_demand = 100.0 + 3.0 * cdd + 2.5 * hdd + 0.2 * humidity + np.random.normal(0, 5, n)

    df = pd.DataFrame({
        "timestamp": timestamps,
        "region": "Grid_Alpha",
        "demand_mw": base_demand,
        "temperature_c": temp,
        "humidity_pct": humidity,
        "pressure_hpa": np.random.normal(1013, 5, n),
        "wind_speed_ms": np.random.uniform(1.0, 10.0, n),
        "cloud_cover_pct": np.random.uniform(0, 100, n),
        "precipitation_mm": precip,
        "weather_condition": weather_cond,
        "probability": np.where(precip > 0, 0.9, 0.1),
    })
    return df


def test_temperature_binning_and_degree_days(sample_impact_df):
    """Verifies CDD/HDD degree day calculations and temperature binning."""
    df_deg = calculate_cdd_hdd(sample_impact_df)
    assert "cdd" in df_deg.columns
    assert "hdd" in df_deg.columns
    assert (df_deg["cdd"] >= 0).all()
    assert (df_deg["hdd"] >= 0).all()

    bins_res = analyze_temperature_impact(df_deg, custom_labels=["Cold", "Mild", "Warm", "Hot"])
    assert "temperature_bins" in bins_res
    assert bins_res["total_count"] == len(sample_impact_df)
    assert len(bins_res["temperature_bins"]) > 0

    nonlinear_res = evaluate_nonlinear_temperature_relationship(df_deg)
    assert "is_nonlinear" in nonlinear_res
    assert "r2_quadratic" in nonlinear_res
    assert nonlinear_res["r2_quadratic"] >= nonlinear_res["r2_linear"]


def test_weather_condition_descriptive_analysis(sample_impact_df):
    """Verifies demand statistics grouped by weather condition."""
    res = analyze_weather_conditions(sample_impact_df)
    assert res["sufficient_data"] is True
    assert res["total_observations"] == len(sample_impact_df)
    assert "conditions" in res
    assert len(res["conditions"]) > 0

    for cond_name, stats in res["conditions"].items():
        assert "mean_demand_mw" in stats
        assert "observation_count" in stats
        assert stats["mean_demand_mw"] > 0


def test_rain_and_humidity_impact_analysis(sample_impact_df):
    """Verifies rain vs no-rain contrast and humidity binned statistics."""
    rain_res = analyze_rain_impact(sample_impact_df)
    assert rain_res["sufficient_data"] is True
    assert "rain_periods" in rain_res
    assert "no_rain_periods" in rain_res
    assert rain_res["rain_periods"]["observation_count"] > 0
    assert rain_res["no_rain_periods"]["observation_count"] > 0

    hum_res = analyze_humidity_impact(sample_impact_df)
    assert hum_res["sufficient_data"] is True
    assert "correlation" in hum_res
    assert "humidity_bins" in hum_res


def test_pearson_and_spearman_correlations(sample_impact_df):
    """Verifies Pearson (linear) and Spearman (rank) correlation computations."""
    corr_res = calculate_weather_correlations(sample_impact_df)
    assert "demand_correlations_pearson" in corr_res
    assert "demand_correlations_spearman" in corr_res
    assert "temperature_c" in corr_res["demand_correlations_pearson"]
    assert "humidity_pct" in corr_res["demand_correlations_pearson"]

    # Verify no NaN correlations
    for val in corr_res["demand_correlations_pearson"].values():
        assert isinstance(val, float)
        assert -1.0 <= val <= 1.0


def test_lagged_weather_feature_generation_zero_leakage(sample_impact_df):
    """Verifies historical weather lag feature generation with zero future leakage."""
    lags = [1, 2, 24]
    lagged_df = generate_lagged_weather_features(sample_impact_df, lags=lags)

    for lag in lags:
        assert f"temperature_c_lag_{lag}h" in lagged_df.columns
        # Verify shift direction (first 'lag' rows must be NaN)
        assert pd.isna(lagged_df[f"temperature_c_lag_{lag}h"].iloc[0])

    lag_analysis = analyze_lagged_impacts(sample_impact_df, lags=lags)
    assert lag_analysis["sufficient_data"] is True
    assert len(lag_analysis["lagged_correlations"]) > 0


def test_forecasting_evaluation_experiment(sample_impact_df):
    """Verifies Model A (Baseline) vs Model B (+Weather) vs Model C (+RainProb) forecasting experiment."""
    eval_res = evaluate_weather_forecasting_value(sample_impact_df, test_ratio=0.2)
    assert eval_res["sufficient_data"] is True
    assert "model_A_baseline" in eval_res["models"]
    assert "model_B_weather_enhanced" in eval_res["models"]
    assert "mae_improvement_pct" in eval_res
    assert "top_weather_features" in eval_res
    assert eval_res["models"]["model_A_baseline"]["mae_mw"] >= 0.0
    assert eval_res["models"]["model_B_weather_enhanced"]["mae_mw"] >= 0.0


def test_peak_demand_weather_context_and_time_of_day(sample_impact_df):
    """Verifies peak demand weather context and time-of-day block analysis."""
    peak_res = analyze_peak_demand_weather_context(sample_impact_df, peak_percentile=90.0)
    assert peak_res["sufficient_data"] is True
    assert peak_res["total_peak_observations"] > 0
    assert "peak_weather_averages" in peak_res

    tod_res = analyze_time_of_day_weather_impact(sample_impact_df)
    assert tod_res["sufficient_data"] is True
    assert "time_of_day_blocks" in tod_res
    assert len(tod_res["time_of_day_blocks"]) > 0

    reg_res = analyze_regional_weather_impact(sample_impact_df)
    assert "regions" in reg_res


def test_weather_impact_scoring(sample_impact_df):
    """Verifies Weather Impact Score formula, normalization, and bounds [0.0, 100.0]."""
    score_res = calculate_weather_impact_score(
        df=sample_impact_df,
        temp_corr=0.75,
        humidity_corr=0.30,
        rain_deviation_pct=5.0,
        forecasting_improvement_pct=12.5
    )
    score = score_res["weather_impact_score"]
    assert 0.0 <= score <= 100.0
    assert score_res["impact_level"] in ["LOW", "MODERATE", "HIGH", "SEVERE"]
    assert "score_components" in score_res


def test_summary_aggregator(sample_impact_df):
    """Verifies overall generate_weather_impact_summary aggregator function."""
    summary = generate_weather_impact_summary(sample_impact_df)
    assert "temperature_relationship" in summary
    assert "rain_relationship" in summary
    assert "humidity_relationship" in summary
    assert "weather_condition_comparison" in summary
    assert "correlation_analysis" in summary
    assert "top_predictive_weather_features" in summary
    assert "weather_forecast_value" in summary
    assert "weather_impact_score" in summary


def test_edge_cases_missing_data_zero_variance():
    """Verifies graceful handling of empty DataFrames, missing weather columns, and zero-variance features."""
    empty_df = pd.DataFrame()
    empty_summary = generate_weather_impact_summary(empty_df)
    assert "error" in empty_summary

    # Constant temperature (zero variance)
    n = 50
    const_df = pd.DataFrame({
        "timestamp": [datetime.now(timezone.utc) + timedelta(hours=i) for i in range(n)],
        "demand_mw": np.random.uniform(100, 200, n),
        "temperature_c": np.full(n, 20.0),
        "humidity_pct": np.random.uniform(40, 80, n),
    })

    corr_res = calculate_weather_correlations(const_df)
    assert "temperature_c" not in corr_res["demand_correlations_pearson"]  # Filtered out zero variance
    assert "humidity_pct" in corr_res["demand_correlations_pearson"]


def test_service_and_database_persistence(sample_impact_df):
    """Verifies WeatherImpactService execution and database ORM record persistence."""
    init_db()
    db = SessionLocal()
    try:
        summary = WeatherImpactService.analyze_and_persist(db, region="Grid_Alpha")
        assert "weather_impact_score" in summary

        # Query database to confirm persisted records
        records = db.query(WeatherImpactRecord).filter(WeatherImpactRecord.region == "Grid_Alpha").all()
        assert len(records) > 0
        first_rec = records[0]
        assert first_rec.region == "Grid_Alpha"
        assert first_rec.metric_name is not None
    finally:
        db.close()


def test_weather_energy_impact_analyzer_compatibility(sample_impact_df):
    """Verifies WeatherEnergyImpactAnalyzer backward compatibility."""
    corrs = WeatherEnergyImpactAnalyzer.calculate_correlations(sample_impact_df)
    assert isinstance(corrs, dict)
    assert "temperature_c" in corrs

    df_cdd = WeatherEnergyImpactAnalyzer.calculate_cooling_heating_degree_days(sample_impact_df)
    assert "cdd" in df_cdd.columns
    assert "hdd" in df_cdd.columns
