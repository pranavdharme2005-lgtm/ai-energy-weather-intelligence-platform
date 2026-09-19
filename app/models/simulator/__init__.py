"""What-If Energy Scenario Simulator Package Initialization."""

from app.models.simulator.schemas import (
    ScenarioInput,
    ScenarioValidationResult,
    ScenarioComparisonPoint,
    SensitivityPoint,
    ScenarioExplanation,
    ScenarioResultSchema,
)
from app.models.simulator.validator import validate_scenario_inputs
from app.models.simulator.range_checker import check_training_ranges
from app.models.simulator.engine import WhatIfEngine
from app.models.simulator.sensitivity import run_one_variable_sensitivity
from app.models.simulator.templates import get_scenario_templates
from app.models.simulator.explanation import generate_scenario_explanation
from app.models.simulator.visualizations import (
    plot_baseline_vs_scenario_trajectory,
    plot_forecast_difference,
    plot_sensitivity_curve,
    plot_scenario_input_comparison,
    plot_prediction_interval_comparison,
    plot_training_range_warning,
)

__all__ = [
    "ScenarioInput",
    "ScenarioValidationResult",
    "ScenarioComparisonPoint",
    "SensitivityPoint",
    "ScenarioExplanation",
    "ScenarioResultSchema",
    "validate_scenario_inputs",
    "check_training_ranges",
    "WhatIfEngine",
    "run_one_variable_sensitivity",
    "get_scenario_templates",
    "generate_scenario_explanation",
    "plot_baseline_vs_scenario_trajectory",
    "plot_forecast_difference",
    "plot_sensitivity_curve",
    "plot_scenario_input_comparison",
    "plot_prediction_interval_comparison",
    "plot_training_range_warning",
]
