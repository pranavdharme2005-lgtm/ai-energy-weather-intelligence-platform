"""Descriptive weather analysis submodule for energy demand platform."""

from typing import Dict, Any
import pandas as pd
import numpy as np
from app.utils.logger import get_logger

logger = get_logger(__name__)


def analyze_weather_conditions(df: pd.DataFrame, min_samples: int = 5) -> Dict[str, Any]:
    """Calculates demand statistics across different weather conditions (Clear, Cloudy, Rain, etc.).

    Args:
        df: Time-aligned DataFrame containing 'demand_mw' and weather variables.
        min_samples: Minimum sample threshold required for confident statistical inference.

    Returns:
        Dict containing per-condition demand statistics and metadata.
    """
    if df.empty or "demand_mw" not in df.columns:
        logger.warning("Empty dataframe or missing 'demand_mw' column in weather condition analysis.")
        return {"conditions": {}, "total_observations": 0, "sufficient_data": False}

    # Determine weather condition column
    cond_col = None
    for col in ["weather_condition", "condition", "weather_code"]:
        if col in df.columns:
            cond_col = col
            break

    if not cond_col:
        logger.info("No explicit weather condition column found. Deriving basic categories from cloud cover & precipitation.")
        df_analysis = df.copy()
        cond_col = "derived_weather_condition"

        def derive_condition(row):
            precip = row.get("precipitation_mm", 0.0)
            cloud = row.get("cloud_cover_pct", 0.0)
            if precip > 2.0:
                return "Rain / Heavy Precip"
            elif precip > 0.1:
                return "Light Rain"
            elif cloud > 60:
                return "Cloudy"
            elif cloud > 20:
                return "Partly Cloudy"
            else:
                return "Clear"

        df_analysis[cond_col] = df_analysis.apply(derive_condition, axis=1)
    else:
        df_analysis = df.copy()

    grouped = df_analysis.groupby(cond_col)["demand_mw"]
    conditions_dict = {}

    for name, group in grouped:
        count = int(len(group))
        if count == 0:
            continue

        is_sufficient = count >= min_samples
        stats = {
            "observation_count": count,
            "mean_demand_mw": round(float(group.mean()), 2),
            "median_demand_mw": round(float(group.median()), 2),
            "min_demand_mw": round(float(group.min()), 2),
            "max_demand_mw": round(float(group.max()), 2),
            "std_demand_mw": round(float(group.std()), 2) if count > 1 else 0.0,
            "data_sufficient": is_sufficient,
        }
        conditions_dict[str(name)] = stats

    return {
        "conditions": conditions_dict,
        "total_observations": len(df_analysis),
        "sufficient_data": len(df_analysis) >= min_samples,
    }
