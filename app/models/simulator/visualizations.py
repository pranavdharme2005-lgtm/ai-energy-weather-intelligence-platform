"""Reusable Matplotlib visualization utilities for what-if scenario simulations."""

from typing import Dict, Any, List
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from app.models.simulator.schemas import ScenarioResultSchema
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Modern theme styling
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
PRIMARY_COLOR = "#1f77b4"
SCENARIO_COLOR = "#d62728"
ACCENT_COLOR = "#2ca02c"


def plot_baseline_vs_scenario_trajectory(result: ScenarioResultSchema) -> plt.Figure:
    """1. Baseline vs Scenario forecast trajectory line chart."""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    if not result.trajectory:
        ax.text(0.5, 0.5, "No Trajectory Points Available", ha="center", va="center")
        return fig

    timestamps = [p.timestamp[-8:-3] for p in result.trajectory]
    base_mw = [p.baseline_demand_mw for p in result.trajectory]
    scen_mw = [p.scenario_demand_mw for p in result.trajectory]

    ax.plot(timestamps, base_mw, label="Baseline Forecast", color=PRIMARY_COLOR, linewidth=2, linestyle="--")
    ax.plot(timestamps, scen_mw, label=f"Scenario Forecast ({result.percentage_change:+.1f}%)", color=SCENARIO_COLOR, linewidth=2.5)

    ax.set_title(f"Energy Demand Forecast: Baseline vs. Scenario ({result.region})", fontsize=12, fontweight="bold")
    ax.set_xlabel("Forecast Target Time", fontsize=10)
    ax.set_ylabel("Demand (MW)", fontsize=10)
    ax.legend(loc="upper left")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    return fig


def plot_forecast_difference(result: ScenarioResultSchema) -> plt.Figure:
    """2. Forecast difference curve (Scenario - Baseline MW)."""
    fig, ax = plt.subplots(figsize=(8, 4.0))
    if not result.trajectory:
        ax.text(0.5, 0.5, "No Difference Points Available", ha="center", va="center")
        return fig

    timestamps = [p.timestamp[-8:-3] for p in result.trajectory]
    diffs = [p.absolute_change_mw for p in result.trajectory]

    colors = [SCENARIO_COLOR if d >= 0 else ACCENT_COLOR for d in diffs]
    ax.bar(timestamps, diffs, color=colors, alpha=0.85, edgecolor="black")
    ax.axhline(0, color="black", linewidth=1, linestyle="-")

    ax.set_title("Forecast Demand Difference (Scenario - Baseline MW)", fontsize=12, fontweight="bold")
    ax.set_xlabel("Forecast Target Time", fontsize=10)
    ax.set_ylabel("Delta Demand (MW)", fontsize=10)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    return fig


def plot_sensitivity_curve(sensitivity_res: Dict[str, Any]) -> plt.Figure:
    """3. One-variable sensitivity curve chart."""
    fig, ax = plt.subplots(figsize=(7, 4.5))
    points = sensitivity_res.get("sensitivity_curve", [])
    if not points:
        ax.text(0.5, 0.5, "No Sensitivity Points Available", ha="center", va="center")
        return fig

    x_vals = [p["input_value"] for p in points]
    y_vals = [p["predicted_demand_mw"] for p in points]
    var_name = sensitivity_res.get("target_variable", "Feature")

    ax.plot(x_vals, y_vals, marker="o", color="#8e44ad", linewidth=2, label="Model Output")
    base_demand = sensitivity_res.get("baseline_demand_mw", y_vals[0])
    ax.axhline(base_demand, color="gray", linestyle="--", label="Baseline Forecast")

    ax.set_title(f"Model Sensitivity: Demand vs. {var_name}", fontsize=12, fontweight="bold")
    ax.set_xlabel(f"{var_name}", fontsize=10)
    ax.set_ylabel("Predicted Demand (MW)", fontsize=10)
    ax.legend()
    plt.tight_layout()
    return fig


def plot_scenario_input_comparison(result: ScenarioResultSchema) -> plt.Figure:
    """4. Scenario input comparison bar chart (Baseline vs Modified Inputs)."""
    fig, ax = plt.subplots(figsize=(7, 4.0))
    scen_inputs = result.scenario_inputs
    base_inputs = result.baseline_inputs

    vars_to_show = list(scen_inputs.keys())
    if not vars_to_show:
        ax.text(0.5, 0.5, "No Modified Inputs in Scenario", ha="center", va="center")
        return fig

    x = np.arange(len(vars_to_show))
    width = 0.35

    base_vals = [base_inputs.get(v, 0.0) for v in vars_to_show]
    scen_vals = [scen_inputs.get(v, 0.0) for v in vars_to_show]

    ax.bar(x - width/2, base_vals, width, label="Baseline Input", color=PRIMARY_COLOR, edgecolor="black")
    ax.bar(x + width/2, scen_vals, width, label="Scenario Input", color=SCENARIO_COLOR, edgecolor="black")

    ax.set_title("Input Variable Comparison: Baseline vs. Scenario", fontsize=12, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(vars_to_show, fontsize=9)
    ax.legend()
    plt.tight_layout()
    return fig


def plot_prediction_interval_comparison(result: ScenarioResultSchema) -> plt.Figure:
    """5. Prediction interval bounds comparison chart."""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    if not result.trajectory:
        ax.text(0.5, 0.5, "No Interval Data Available", ha="center", va="center")
        return fig

    timestamps = [p.timestamp[-8:-3] for p in result.trajectory]
    scen_mw = [p.scenario_demand_mw for p in result.trajectory]
    lower = [p.confidence_lower_mw if p.confidence_lower_mw is not None else p.scenario_demand_mw * 0.95 for p in result.trajectory]
    upper = [p.confidence_upper_mw if p.confidence_upper_mw is not None else p.scenario_demand_mw * 1.05 for p in result.trajectory]

    ax.plot(timestamps, scen_mw, label="Scenario Forecast", color=SCENARIO_COLOR, linewidth=2)
    ax.fill_between(timestamps, lower, upper, color=SCENARIO_COLOR, alpha=0.2, label="95% Residual Prediction Interval")

    ax.set_title("Scenario Forecast with 95% Residual Prediction Intervals", fontsize=12, fontweight="bold")
    ax.set_xlabel("Forecast Target Time", fontsize=10)
    ax.set_ylabel("Demand (MW)", fontsize=10)
    ax.legend()
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    return fig


def plot_training_range_warning(result: ScenarioResultSchema) -> plt.Figure:
    """6. Training range status visualization chart."""
    fig, ax = plt.subplots(figsize=(7, 4.0))
    status_dict = result.input_range_status
    if not status_dict:
        ax.text(0.5, 0.5, "No Range Status Data Available", ha="center", va="center")
        return fig

    vars_list = list(status_dict.keys())
    statuses = [status_dict[v]["status"] for v in vars_list]

    color_map = {
        "WITHIN_TRAINING_RANGE": "#2ecc71",
        "NEAR_HISTORICAL_BOUNDARY": "#f39c12",
        "OUTSIDE_TRAINING_RANGE": "#e74c3c"
    }
    colors = [color_map.get(s, "#95a5a6") for s in statuses]

    y_pos = np.arange(len(vars_list))
    ax.barh(y_pos, [1]*len(vars_list), color=colors, edgecolor="black", height=0.5)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(vars_list, fontsize=9)
    ax.set_xticks([])

    for i, s in enumerate(statuses):
        ax.text(0.5, i, s.replace("_", " "), ha="center", va="center", color="white", fontweight="bold", fontsize=9)

    ax.set_title("Historical Training-Range Status Check", fontsize=12, fontweight="bold")
    plt.tight_layout()
    return fig
