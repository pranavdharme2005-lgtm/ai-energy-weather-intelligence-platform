"""What-If Simulation Engine Service for Energy Demand Scenario Analysis."""

from typing import Dict, Any, List, Optional
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.energy_forecaster import EnergyForecaster
from app.models.simulator import (
    ScenarioInput,
    ScenarioResultSchema,
    WhatIfEngine,
    run_one_variable_sensitivity,
    get_scenario_templates,
    plot_baseline_vs_scenario_trajectory,
    plot_forecast_difference,
    plot_sensitivity_curve,
    plot_scenario_input_comparison,
    plot_prediction_interval_comparison,
    plot_training_range_warning,
)
from app.database.repository import ScenarioRepository
from app.services.weather_energy_impact import WeatherImpactService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SimulationScenario(ScenarioInput):
    """Backward compatibility alias for ScenarioInput."""
    temperature_delta_c: float = 0.0
    humidity_delta_pct: float = 0.0
    precipitation_scenario_mm: float = 0.0
    industrial_demand_modifier_pct: float = 0.0


class SimulationResult(BaseModel):
    """Backward compatibility result container."""
    scenario: Any
    baseline_demand_mw: float
    simulated_demand_mw: float
    percentage_change: float
    risk_level: str


class WhatIfSimulator:
    """Production What-If Simulator wrapper preserving backward compatibility."""

    def __init__(self):
        self.engine = WhatIfEngine()

    def run_simulation(
        self,
        history_df: pd.DataFrame,
        scenario_overrides: Dict[str, Any],
        region: str = "Grid_Alpha",
        horizon_hours: int = 24
    ) -> ScenarioResultSchema:
        """Runs baseline vs scenario prediction comparison using Stage 5 forecaster."""
        return self.engine.run_simulation(
            history_df=history_df,
            scenario_overrides=scenario_overrides,
            region=region,
            horizon_hours=horizon_hours
        )

    @staticmethod
    def simulate_scenario(baseline_demand: float, scenario: SimulationScenario) -> SimulationResult:
        """Legacy placeholder simulator method preserved for backward compatibility."""
        temp_effect = scenario.temperature_delta_c * 0.035
        humidity_effect = (scenario.humidity_delta_pct / 10.0) * 0.012
        ind_effect = scenario.industrial_demand_modifier_pct / 100.0

        total_multiplier = 1.0 + temp_effect + humidity_effect + ind_effect
        simulated = baseline_demand * total_multiplier
        pct_change = ((simulated - baseline_demand) / baseline_demand) * 100.0

        risk = "NORMAL"
        if pct_change > 15.0 or pct_change < -15.0:
            risk = "CRITICAL"
        elif pct_change > 7.0 or pct_change < -7.0:
            risk = "MODERATE"

        return SimulationResult(
            scenario=scenario,
            baseline_demand_mw=round(baseline_demand, 2),
            simulated_demand_mw=round(simulated, 2),
            percentage_change=round(pct_change, 2),
            risk_level=risk
        )


class WhatIfSimulatorService:
    """High-level orchestration service for Stage 8 What-If Scenario Simulations."""

    @staticmethod
    def run_scenario(
        db: Optional[Session],
        scenario_overrides: Dict[str, Any],
        region: str = "Grid_Alpha",
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        """Runs scenario simulation using historical database records (or fallback data) and optionally persists result."""
        df_history = WeatherImpactService.load_merged_dataset(db, region=region) if db else WeatherImpactService.get_synthetic_merged_dataset(region=region)

        simulator = WhatIfSimulator()
        res_schema = simulator.run_simulation(df_history, scenario_overrides, region=region)
        res_dict = res_schema.model_dump()

        if save_to_db and db is not None:
            ScenarioRepository.save_scenario_run(db, {
                "scenario_id": res_schema.scenario_id,
                "region": region,
                "baseline_demand_mw": res_schema.baseline_demand_mw,
                "scenario_demand_mw": res_schema.scenario_demand_mw,
                "absolute_change_mw": res_schema.absolute_change_mw,
                "percentage_change": res_schema.percentage_change,
                "baseline_inputs": res_schema.baseline_inputs,
                "scenario_inputs": res_schema.scenario_inputs,
                "out_of_range_warning": res_schema.out_of_range_warning,
                "model_version": res_schema.model_version,
            })

        return res_dict

    @staticmethod
    def run_sensitivity(
        db: Optional[Session],
        variable_name: str = "temperature_c",
        min_val: float = 10.0,
        max_val: float = 40.0,
        steps: int = 10,
        region: str = "Grid_Alpha"
    ) -> Dict[str, Any]:
        """Executes 1-variable sensitivity sweep."""
        df_history = WeatherImpactService.load_merged_dataset(db, region=region) if db else WeatherImpactService.get_synthetic_merged_dataset(region=region)
        engine = WhatIfEngine()
        return run_one_variable_sensitivity(engine, df_history, variable_name, min_val, max_val, steps, region)

    @staticmethod
    def generate_all_plots(res_schema: ScenarioResultSchema, sensitivity_res: Dict[str, Any], output_dir: str = "docs/images/stage8") -> List[str]:
        """Generates and saves all 6 required Stage 8 Matplotlib figures."""
        os.makedirs(output_dir, exist_ok=True)
        saved_paths = []

        plots = [
            ("01_baseline_vs_scenario_trajectory.png", plot_baseline_vs_scenario_trajectory(res_schema)),
            ("02_forecast_difference.png", plot_forecast_difference(res_schema)),
            ("03_one_variable_sensitivity.png", plot_sensitivity_curve(sensitivity_res)),
            ("04_scenario_input_comparison.png", plot_scenario_input_comparison(res_schema)),
            ("05_prediction_interval_comparison.png", plot_prediction_interval_comparison(res_schema)),
            ("06_training_range_warning.png", plot_training_range_warning(res_schema)),
        ]

        for filename, fig in plots:
            filepath = os.path.join(output_dir, filename)
            fig.savefig(filepath, bbox_inches="tight", dpi=150)
            plt.close(fig)
            saved_paths.append(filepath)

        logger.info(f"Saved {len(saved_paths)} Stage 8 visualization plots to {output_dir}")
        return saved_paths
