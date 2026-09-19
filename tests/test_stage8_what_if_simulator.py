"""Automated test suite for Stage 8 — What-If Energy Scenario Simulator."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

from app.models.simulator import (
    ScenarioInput,
    validate_scenario_inputs,
    check_training_ranges,
    WhatIfEngine,
    run_one_variable_sensitivity,
    get_scenario_templates,
)
from app.services.simulator import WhatIfSimulatorService, WhatIfSimulator
from app.database.session import SessionLocal, init_db
from app.database.models import ScenarioRun


@pytest.fixture
def sample_sim_history_df():
    """Generates synthetic time-aligned historical dataset for simulation testing."""
    np.random.seed(42)
    n = 168
    now = datetime.now(timezone.utc)
    timestamps = [now - timedelta(hours=i) for i in reversed(range(n))]

    temp = np.random.uniform(10.0, 30.0, n)
    humidity = np.random.uniform(30.0, 90.0, n)
    demands = 2500.0 + 30.0 * temp + 5.0 * humidity + np.random.normal(0, 30, n)

    return pd.DataFrame({
        "timestamp": timestamps,
        "region": "Grid_Alpha",
        "demand_mw": demands,
        "temperature_c": temp,
        "humidity_pct": humidity,
        "pressure_hpa": np.random.normal(1013.25, 5, n),
        "wind_speed_ms": np.random.uniform(1.0, 10.0, n),
        "cloud_cover_pct": np.random.uniform(0, 100, n),
        "precipitation_mm": np.where(np.random.rand(n) > 0.8, np.random.uniform(0.5, 5.0, n), 0.0),
        "rain_probability": np.where(humidity > 75, 0.7, 0.1),
    })


def test_baseline_generation_and_inference(sample_sim_history_df):
    """Verifies baseline forecast generation using Stage 5 model."""
    engine = WhatIfEngine()
    res = engine.run_simulation(sample_sim_history_df, {}, region="Grid_Alpha", horizon_hours=24)

    assert res.baseline_demand_mw > 0
    assert res.scenario_demand_mw == res.baseline_demand_mw
    assert res.absolute_change_mw == 0.0
    assert res.percentage_change == 0.0
    assert len(res.trajectory) == 24


def test_scenario_input_validation():
    """Verifies input validation, boundary checks, and scale normalizations."""
    # Valid input
    valid_res = validate_scenario_inputs({"temperature_c": 34.5, "humidity_pct": 70.0})
    assert valid_res.is_valid is True
    assert valid_res.sanitized_input["temperature_c"] == 34.5

    # Out of physical bound
    invalid_res = validate_scenario_inputs({"temperature_c": 120.0})  # 120C is physically invalid
    assert invalid_res.is_valid is False
    assert len(invalid_res.errors) > 0

    # Auto-scale rain_probability percentage (e.g. 80 -> 0.8)
    scaled_res = validate_scenario_inputs({"rain_probability": 80.0})
    assert scaled_res.is_valid is True
    assert scaled_res.sanitized_input["rain_probability"] == 0.80


def test_single_and_multivariable_scenarios(sample_sim_history_df):
    """Verifies single and multi-variable scenario predictions."""
    engine = WhatIfEngine()

    # Single variable
    res_single = engine.run_simulation(sample_sim_history_df, {"temperature_c": 36.0})
    assert res_single.scenario_inputs["temperature_c"] == 36.0

    # Multi variable
    res_multi = engine.run_simulation(
        sample_sim_history_df,
        {"temperature_c": 36.0, "humidity_pct": 85.0, "rain_probability": 0.75}
    )
    assert res_multi.scenario_inputs["temperature_c"] == 36.0
    assert res_multi.scenario_inputs["humidity_pct"] == 85.0
    assert res_multi.scenario_inputs["rain_probability"] == 0.75


def test_multi_horizon_trajectory_and_delta(sample_sim_history_df):
    """Verifies multi-horizon trajectory (24h) and delta calculations."""
    engine = WhatIfEngine()
    res = engine.run_simulation(sample_sim_history_df, {"temperature_c": 35.0}, horizon_hours=24)

    assert len(res.trajectory) == 24
    for pt in res.trajectory:
        assert pt.timestamp is not None
        assert pt.baseline_demand_mw > 0
        assert pt.scenario_demand_mw > 0
        assert pt.absolute_change_mw == round(pt.scenario_demand_mw - pt.baseline_demand_mw, 2)


def test_one_variable_sensitivity_analysis(sample_sim_history_df):
    """Verifies 1-variable sensitivity sweep generation."""
    engine = WhatIfEngine()
    sens_res = run_one_variable_sensitivity(
        engine, sample_sim_history_df, variable_name="temperature_c", min_val=15.0, max_val=35.0, steps=5
    )

    assert sens_res["target_variable"] == "temperature_c"
    assert len(sens_res["sensitivity_curve"]) == 5
    assert "disclaimer" in sens_res


def test_historical_training_range_checker(sample_sim_history_df):
    """Verifies historical training range checking and boundary flags."""
    range_status, out_of_range, warning = check_training_ranges({"temperature_c": 25.0}, sample_sim_history_df)
    assert out_of_range is False
    assert range_status["temperature_c"]["status"] in ["WITHIN_TRAINING_RANGE", "NEAR_HISTORICAL_BOUNDARY"]

    # Out-of-range value
    range_status_out, out_of_range_out, warning_out = check_training_ranges({"temperature_c": 50.0}, sample_sim_history_df)
    assert out_of_range_out is True
    assert "outside historical training" in warning_out.lower()


def test_unchanged_features_identical_to_baseline(sample_sim_history_df):
    """Verifies that non-supplied features remain identical to baseline inputs."""
    engine = WhatIfEngine()
    res = engine.run_simulation(sample_sim_history_df, {"temperature_c": 32.0})

    # Humidity was not modified in scenario, so baseline_inputs and scenario_inputs should match baseline
    latest_humidity = sample_sim_history_df["humidity_pct"].iloc[-1]
    assert res.scenario_inputs["temperature_c"] == 32.0
    assert "humidity_pct" not in res.scenario_inputs


def test_zero_model_retraining(sample_sim_history_df):
    """Verifies that the simulator reuses the existing Stage 5 forecaster without retraining."""
    engine = WhatIfEngine()
    initial_version = engine.model_version

    res = engine.run_simulation(sample_sim_history_df, {"temperature_c": 30.0})
    assert res.model_version == initial_version


def test_scenario_storage_database_persistence(sample_sim_history_df):
    """Verifies scenario run ORM record persistence in database."""
    init_db()
    db = SessionLocal()
    try:
        res_dict = WhatIfSimulatorService.run_scenario(
            db, {"temperature_c": 34.0, "humidity_pct": 75.0}, region="Grid_Alpha", save_to_db=True
        )

        assert res_dict["scenario_id"] is not None

        records = db.query(ScenarioRun).filter(ScenarioRun.region == "Grid_Alpha").all()
        assert len(records) > 0
        first_rec = records[0]
        assert first_rec.scenario_id is not None
        assert first_rec.baseline_demand_mw > 0
    finally:
        db.close()


def test_preset_templates(sample_sim_history_df):
    """Verifies scenario template generation."""
    templates = get_scenario_templates(sample_sim_history_df)
    assert "hot_heatwave" in templates
    assert "cold_snap" in templates
    assert "heavy_rainstorm" in templates
    assert "high_humidity_summer" in templates
    assert "temperature_c" in templates["hot_heatwave"]["inputs"]
