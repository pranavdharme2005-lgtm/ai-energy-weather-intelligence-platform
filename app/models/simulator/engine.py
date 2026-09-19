"""Core What-If Energy Scenario Simulation Engine reusing Stage 5 forecaster."""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np

from app.models.energy_forecaster import EnergyForecaster
from app.models.energy_forecasting.features import extract_forecasting_features
from app.models.simulator.schemas import (
    ScenarioResultSchema,
    ScenarioComparisonPoint,
)
from app.models.simulator.validator import validate_scenario_inputs
from app.models.simulator.range_checker import check_training_ranges
from app.models.simulator.explanation import generate_scenario_explanation
from app.utils.logger import get_logger

logger = get_logger(__name__)


class WhatIfEngine:
    """Production What-If Scenario Simulation Engine reusing serialized Stage 5 forecaster.

    Zero model retraining. Reuses trained Stage 5 Random Forest Regressor artifact.
    """

    def __init__(self, forecaster: Optional[EnergyForecaster] = None):
        self.forecaster = forecaster or EnergyForecaster()
        self.model_version = self.forecaster.model_version

    def run_simulation(
        self,
        history_df: pd.DataFrame,
        scenario_overrides: Dict[str, Any],
        region: str = "Grid_Alpha",
        horizon_hours: int = 24
    ) -> ScenarioResultSchema:
        """Executes a controlled baseline vs. scenario prediction comparison.

        Args:
            history_df: Analytical history DataFrame containing past demand and weather observations.
            scenario_overrides: User-supplied weather feature modifications (e.g. {'temperature_c': 34.0}).
            region: Regional grid identifier.
            horizon_hours: Forecast horizon in hours (default 24h).

        Returns:
            ScenarioResultSchema: Standardized scenario result.
        """
        if history_df.empty:
            raise ValueError("Historical dataset for scenario simulation cannot be empty.")

        # 1. Input Validation
        val_res = validate_scenario_inputs(scenario_overrides)
        if not val_res.is_valid:
            raise ValueError(f"Scenario input validation failed: {'; '.join(val_res.errors)}")

        sanitized_inputs = val_res.sanitized_input

        # 2. Historical Training Range Validation
        range_status, out_of_range, range_warning = check_training_ranges(sanitized_inputs, history_df)

        # 3. Baseline Forecasting Execution (Stage 5 model)
        baseline_results = self.forecaster.predict_horizon(history_df, region=region, horizon_hours=horizon_hours)

        # Extract baseline input values from latest historical row
        latest_row = history_df.iloc[-1]
        baseline_inputs = {}
        for k in sanitized_inputs.keys():
            baseline_inputs[k] = float(latest_row.get(k, 0.0)) if k in latest_row else 0.0

        # 4. Construct Scenario History DataFrame (Overriding only specified features)
        scenario_history_df = history_df.copy()
        last_idx = scenario_history_df.index[-1]
        for k, v in sanitized_inputs.items():
            scenario_history_df.loc[last_idx, k] = v

        # 5. Scenario Forecasting Execution (SAME Stage 5 model)
        scenario_results = self.forecaster.predict_horizon(scenario_history_df, region=region, horizon_hours=horizon_hours)

        # 6. Build Multi-Horizon Trajectory Comparison
        trajectory = []
        tot_base_mw = 0.0
        tot_scen_mw = 0.0

        for b_res, s_res in zip(baseline_results, scenario_results):
            b_val = b_res.forecasted_demand_mw
            s_val = s_res.forecasted_demand_mw
            tot_base_mw += b_val
            tot_scen_mw += s_val

            diff_mw = round(s_val - b_val, 2)
            pct_chg = round((diff_mw / b_val * 100.0) if b_val > 0 else 0.0, 2)

            ts_str = b_res.forecast_target_time.isoformat() if isinstance(b_res.forecast_target_time, datetime) else str(b_res.forecast_target_time)

            trajectory.append(
                ScenarioComparisonPoint(
                    timestamp=ts_str,
                    baseline_demand_mw=b_val,
                    scenario_demand_mw=s_val,
                    absolute_change_mw=diff_mw,
                    percentage_change=pct_chg,
                    confidence_lower_mw=s_res.confidence_lower_mw,
                    confidence_upper_mw=s_res.confidence_upper_mw,
                )
            )

        avg_base_mw = round(tot_base_mw / len(trajectory), 2) if trajectory else 0.0
        avg_scen_mw = round(tot_scen_mw / len(trajectory), 2) if trajectory else 0.0
        abs_diff_mw = round(avg_scen_mw - avg_base_mw, 2)
        overall_pct_chg = round((abs_diff_mw / avg_base_mw * 100.0) if avg_base_mw > 0 else 0.0, 2)

        # 7. Generate Deterministic Explanation
        explanation = generate_scenario_explanation(
            baseline_demand_mw=avg_base_mw,
            scenario_demand_mw=avg_scen_mw,
            percentage_change=overall_pct_chg,
            scenario_inputs=sanitized_inputs,
            baseline_inputs=baseline_inputs,
            out_of_range_warning=range_warning if out_of_range else None
        )

        scenario_id = f"sim_{uuid.uuid4().hex[:8]}"
        now_str = datetime.now(timezone.utc).isoformat()

        return ScenarioResultSchema(
            scenario_id=scenario_id,
            region=region,
            forecast_timestamp=now_str,
            baseline_inputs=baseline_inputs,
            scenario_inputs=sanitized_inputs,
            baseline_demand_mw=avg_base_mw,
            scenario_demand_mw=avg_scen_mw,
            absolute_change_mw=abs_diff_mw,
            percentage_change=overall_pct_chg,
            trajectory=trajectory,
            input_range_status=range_status,
            out_of_range_warning=out_of_range,
            uncertainty_available=True,
            explanation=explanation,
            model_version=self.model_version,
            generated_at=now_str
        )
