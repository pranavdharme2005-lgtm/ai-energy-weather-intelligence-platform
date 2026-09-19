"""Deterministic explanation generator for what-if scenario simulations."""

from typing import Dict, Any, Optional
from app.models.simulator.schemas import ScenarioExplanation
from app.utils.logger import get_logger

logger = get_logger(__name__)


def generate_scenario_explanation(
    baseline_demand_mw: float,
    scenario_demand_mw: float,
    percentage_change: float,
    scenario_inputs: Dict[str, float],
    baseline_inputs: Dict[str, float],
    out_of_range_warning: Optional[str] = None
) -> ScenarioExplanation:
    """Generates rule-based, deterministic explanation metadata for scenario results.

    Does NOT use LLMs or generative AI. Purely deterministic.
    """
    diff_mw = scenario_demand_mw - baseline_demand_mw
    abs_pct = abs(percentage_change)

    # Determine primary driving variable (largest relative change)
    primary_var = "None"
    max_var_shift = -1.0

    for var_name, sc_val in scenario_inputs.items():
        base_val = baseline_inputs.get(var_name, sc_val)
        if base_val != 0:
            rel_shift = abs(sc_val - base_val) / abs(base_val)
        else:
            rel_shift = abs(sc_val)

        if rel_shift > max_var_shift:
            max_var_shift = rel_shift
            primary_var = var_name

    # Direction narrative
    if percentage_change > 0.5:
        dir_text = "higher"
        verb = "increases"
    elif percentage_change < -0.5:
        dir_text = "lower"
        verb = "decreases"
    else:
        dir_text = "nearly unchanged"
        verb = "remains stable"

    summary = (
        f"Under this hypothetical scenario, the trained forecasting model predicts {dir_text} energy demand "
        f"({scenario_demand_mw:.1f} MW vs. baseline {baseline_demand_mw:.1f} MW, a {percentage_change:+.1f}% shift). "
        f"The primary driver of this shift is the modified '{primary_var}' input."
    )

    formatted_pct = f"{percentage_change:+.1f}%"

    return ScenarioExplanation(
        summary=summary,
        percentage_change_formatted=formatted_pct,
        primary_driving_variable=primary_var,
        out_of_range_warning=out_of_range_warning,
        disclaimer="Model-based scenario estimate. Indicates model sensitivity, NOT proof of causal effect."
    )
