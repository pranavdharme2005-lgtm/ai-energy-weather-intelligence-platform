"""Scenario input validation module enforcing physical limits and data types."""

from typing import Dict, Any
from app.models.simulator.schemas import ScenarioInput, ScenarioValidationResult
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Supported model weather variables and physical valid bounds
SUPPORTED_WEATHER_BOUNDS = {
    "temperature_c": (-30.0, 55.0, "deg C"),
    "humidity_pct": (0.0, 100.0, "%"),
    "pressure_hpa": (850.0, 1080.0, "hPa"),
    "wind_speed_ms": (0.0, 75.0, "m/s"),
    "cloud_cover_pct": (0.0, 100.0, "%"),
    "precipitation_mm": (0.0, 200.0, "mm"),
    "rain_probability": (0.0, 1.0, "probability"),
}


def validate_scenario_inputs(inputs: Dict[str, Any]) -> ScenarioValidationResult:
    """Validates user-supplied scenario inputs against supported features and physical bounds.

    Args:
        inputs: Dictionary of scenario feature overrides.

    Returns:
        ScenarioValidationResult: Validation status, error list, warnings, and sanitized dictionary.
    """
    errors = []
    warnings = []
    sanitized = {}

    if not isinstance(inputs, dict):
        return ScenarioValidationResult(is_valid=False, errors=["Scenario inputs must be a valid JSON dictionary."])

    for var_name, value in inputs.items():
        if value is None:
            continue

        if var_name not in SUPPORTED_WEATHER_BOUNDS:
            warnings.append(f"Ignored unsupported feature '{var_name}'. Supported features: {list(SUPPORTED_WEATHER_BOUNDS.keys())}")
            continue

        # Type conversion check
        try:
            val_float = float(value)
        except (ValueError, TypeError):
            errors.append(f"Invalid data type for feature '{var_name}': expected numeric value, got '{value}'")
            continue

        # Rain probability scale normalization if user provides 0-100%
        if var_name == "rain_probability" and val_float > 1.0 and val_float <= 100.0:
            val_float = val_float / 100.0
            warnings.append("Scaled rain_probability from percentage [0-100] to probability scale [0.0-1.0]")

        min_val, max_val, unit = SUPPORTED_WEATHER_BOUNDS[var_name]

        # Physical boundary check
        if val_float < min_val or val_float > max_val:
            errors.append(
                f"Feature '{var_name}' value {val_float} {unit} is outside physically reasonable bounds [{min_val}, {max_val}] {unit}."
            )
            continue

        sanitized[var_name] = round(val_float, 2)

    is_valid = len(errors) == 0
    return ScenarioValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        sanitized_input=sanitized
    )
