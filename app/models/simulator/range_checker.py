"""Historical training-range validation checker for scenario inputs."""

from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Default empirical training feature bounds derived from project analytical dataset
DEFAULT_HISTORICAL_BOUNDS = {
    "temperature_c": {"min": -5.0, "p05": 5.0, "p95": 32.0, "max": 38.0},
    "humidity_pct": {"min": 15.0, "p05": 30.0, "p95": 95.0, "max": 100.0},
    "pressure_hpa": {"min": 980.0, "p05": 995.0, "p95": 1030.0, "max": 1045.0},
    "wind_speed_ms": {"min": 0.0, "p05": 0.5, "p95": 15.0, "max": 25.0},
    "cloud_cover_pct": {"min": 0.0, "p05": 0.0, "p95": 100.0, "max": 100.0},
    "precipitation_mm": {"min": 0.0, "p05": 0.0, "p95": 10.0, "max": 50.0},
    "rain_probability": {"min": 0.0, "p05": 0.0, "p95": 0.95, "max": 1.0},
}


def check_training_ranges(
    scenario_inputs: Dict[str, float],
    historical_df: pd.DataFrame = None
) -> Tuple[Dict[str, Dict[str, Any]], bool, str]:
    """Benchmarks scenario inputs against historical training feature ranges.

    Args:
        scenario_inputs: User-supplied scenario inputs.
        historical_df: Optional historical DataFrame to compute dynamic training bounds.

    Returns:
        Tuple:
            - Dict mapping feature -> status info (status, min, max, user_val, inside_range)
            - bool: True if any feature is outside historical training range
            - str: Warning message if any feature is out of bounds
    """
    range_status = {}
    any_out_of_range = False
    warning_messages = []

    for var_name, value in scenario_inputs.items():
        if value is None:
            continue

        # Dynamic bounds if historical_df supplied
        if historical_df is not None and var_name in historical_df.columns:
            series = historical_df[var_name].dropna()
            if not series.empty:
                h_min = float(series.min())
                h_max = float(series.max())
                h_p05 = float(series.quantile(0.05))
                h_p95 = float(series.quantile(0.95))
            else:
                bounds = DEFAULT_HISTORICAL_BOUNDS.get(var_name, {"min": 0, "max": 100})
                h_min, h_max = bounds["min"], bounds["max"]
        else:
            bounds = DEFAULT_HISTORICAL_BOUNDS.get(var_name, {"min": -50, "max": 100})
            h_min, h_max = bounds["min"], bounds["max"]

        is_inside = (h_min <= value <= h_max)

        if not is_inside:
            any_out_of_range = True
            status = "OUTSIDE_TRAINING_RANGE"
            warning_messages.append(
                f"Feature '{var_name}' value {value} is outside historical training bounds [{h_min}, {h_max}]."
            )
        elif value < h_p05 or value > h_p95:
            status = "NEAR_HISTORICAL_BOUNDARY"
        else:
            status = "WITHIN_TRAINING_RANGE"

        range_status[var_name] = {
            "status": status,
            "within_range": is_inside,
            "user_value": value,
            "historical_min": h_min,
            "historical_max": h_max,
        }

    overall_warning = ""
    if any_out_of_range:
        overall_warning = (
            "Scenario input is outside historical training feature range. "
            "Model forecast uncertainty may be higher for extreme inputs."
        )

    return range_status, any_out_of_range, overall_warning
