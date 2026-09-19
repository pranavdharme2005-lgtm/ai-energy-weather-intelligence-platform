"""One-variable and multi-variable model sensitivity analysis module."""

from typing import Dict, Any, List
import numpy as np
import pandas as pd
from app.models.simulator.schemas import SensitivityPoint
from app.models.simulator.engine import WhatIfEngine
from app.utils.logger import get_logger

logger = get_logger(__name__)


def run_one_variable_sensitivity(
    engine: WhatIfEngine,
    history_df: pd.DataFrame,
    variable_name: str = "temperature_c",
    min_val: float = 10.0,
    max_val: float = 40.0,
    steps: int = 10,
    region: str = "Grid_Alpha"
) -> Dict[str, Any]:
    """Executes a 1-variable sensitivity sweep across a range of values.

    IMPORTANT:
    This measures model sensitivity, NOT proof of a causal physical relationship.

    Args:
        engine: WhatIfEngine instance.
        history_df: Historical dataset.
        variable_name: Feature name to sweep (e.g. 'temperature_c').
        min_val: Start value of range.
        max_val: End value of range.
        steps: Number of evaluation points (default 10).
        region: Regional grid identifier.

    Returns:
        Dict containing list of SensitivityPoint results and metadata.
    """
    if history_df.empty:
        raise ValueError("History DataFrame cannot be empty for sensitivity analysis.")

    sweep_values = np.linspace(min_val, max_val, steps)
    sensitivity_curve = []

    # Run baseline once
    base_res = engine.run_simulation(history_df, {}, region=region, horizon_hours=24)
    base_demand = base_res.baseline_demand_mw

    for val in sweep_values:
        val_float = round(float(val), 2)
        scenario_dict = {variable_name: val_float}

        try:
            res = engine.run_simulation(history_df, scenario_dict, region=region, horizon_hours=24)
            scen_demand = res.scenario_demand_mw
            pct_chg = round(((scen_demand - base_demand) / base_demand * 100.0) if base_demand > 0 else 0.0, 2)

            sensitivity_curve.append(
                SensitivityPoint(
                    input_value=val_float,
                    predicted_demand_mw=scen_demand,
                    percentage_change_from_baseline=pct_chg
                )
            )
        except Exception as e:
            logger.error(f"Error during sensitivity step {variable_name}={val_float}: {e}")

    return {
        "analysis_title": f"Model Sensitivity Analysis: {variable_name}",
        "target_variable": variable_name,
        "baseline_demand_mw": base_demand,
        "sweep_min": min_val,
        "sweep_max": max_val,
        "steps_count": len(sensitivity_curve),
        "sensitivity_curve": [p.model_dump() for p in sensitivity_curve],
        "disclaimer": "Model Sensitivity Analysis. Shows how model predictions vary with input changes; does NOT prove physical causation."
    }
