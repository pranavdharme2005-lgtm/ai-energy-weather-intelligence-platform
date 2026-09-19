"""Peak demand weather context, time-of-day, and regional analysis submodule."""

from typing import Dict, Any, List
import pandas as pd
import numpy as np
from app.utils.logger import get_logger

logger = get_logger(__name__)


def analyze_peak_demand_weather_context(
    df: pd.DataFrame, peak_percentile: float = 90.0
) -> Dict[str, Any]:
    """Analyzes meteorological conditions during high-demand peak periods (>90th percentile).

    Calculates:
        - peak demand threshold MW
        - proportion of peak events occurring under different weather conditions
        - average weather values during peak demand vs non-peak periods
    """
    if df.empty or "demand_mw" not in df.columns:
        return {"peak_context": {}, "sufficient_data": False}

    df_clean = df.dropna(subset=["demand_mw"]).copy()
    if len(df_clean) < 10:
        return {"peak_context": {}, "sufficient_data": False}

    threshold_mw = float(np.percentile(df_clean["demand_mw"], peak_percentile))
    df_clean["is_peak"] = df_clean["demand_mw"] >= threshold_mw

    peak_df = df_clean[df_clean["is_peak"]]
    non_peak_df = df_clean[~df_clean["is_peak"]]

    weather_vars = [c for c in ["temperature_c", "humidity_pct", "pressure_hpa", "wind_speed_ms", "precipitation_mm", "probability", "cdd", "hdd"] if c in df_clean.columns]

    peak_means = {}
    non_peak_means = {}

    for var in weather_vars:
        if not peak_df[var].dropna().empty:
            peak_means[var] = round(float(peak_df[var].mean()), 2)
        if not non_peak_df[var].dropna().empty:
            non_peak_means[var] = round(float(non_peak_df[var].mean()), 2)

    # Condition distribution during peak
    condition_proportions = {}
    cond_col = None
    for col in ["weather_condition", "condition", "derived_weather_condition"]:
        if col in df_clean.columns:
            cond_col = col
            break

    if cond_col and not peak_df[cond_col].dropna().empty:
        counts = peak_df[cond_col].value_counts()
        total_peaks = len(peak_df)
        for cond_name, count in counts.items():
            condition_proportions[str(cond_name)] = {
                "count": int(count),
                "percentage": round(float(count / total_peaks * 100.0), 1),
            }

    return {
        "peak_threshold_percentile": peak_percentile,
        "peak_threshold_mw": round(threshold_mw, 2),
        "total_peak_observations": len(peak_df),
        "total_non_peak_observations": len(non_peak_df),
        "peak_weather_averages": peak_means,
        "non_peak_weather_averages": non_peak_means,
        "peak_condition_proportions": condition_proportions,
        "sufficient_data": True,
    }


def analyze_time_of_day_weather_impact(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyzes weather-demand relationships across time-of-day blocks.

    Time contexts:
        - Morning: 06:00 - 11:59
        - Afternoon: 12:00 - 17:59
        - Evening: 18:00 - 22:59
        - Night: 23:00 - 05:59
    """
    if df.empty or "demand_mw" not in df.columns:
        return {"time_of_day_blocks": {}, "sufficient_data": False}

    df_clean = df.copy()

    if "hour" not in df_clean.columns and "timestamp" in df_clean.columns:
        df_clean["timestamp"] = pd.to_datetime(df_clean["timestamp"])
        df_clean["hour"] = df_clean["timestamp"].dt.hour

    if "hour" not in df_clean.columns:
        return {"time_of_day_blocks": {}, "sufficient_data": False}

    def assign_time_block(hour):
        if 6 <= hour < 12:
            return "Morning (06-12)"
        elif 12 <= hour < 18:
            return "Afternoon (12-18)"
        elif 18 <= hour < 23:
            return "Evening (18-23)"
        else:
            return "Night (23-06)"

    df_clean["time_block"] = df_clean["hour"].apply(assign_time_block)

    blocks_dict = {}
    grouped = df_clean.groupby("time_block", observed=False)

    for block_name, group in grouped:
        count = int(len(group))
        if count == 0:
            continue

        temp_corr = 0.0
        if "temperature_c" in group.columns and count >= 5:
            c = group["temperature_c"].corr(group["demand_mw"])
            temp_corr = 0.0 if np.isnan(c) else round(float(c), 4)

        blocks_dict[str(block_name)] = {
            "observation_count": count,
            "mean_demand_mw": round(float(group["demand_mw"].mean()), 2),
            "median_demand_mw": round(float(group["demand_mw"].median()), 2),
            "mean_temperature_c": round(float(group["temperature_c"].mean()), 1) if "temperature_c" in group.columns else 0.0,
            "temperature_demand_correlation": temp_corr,
        }

    return {
        "time_of_day_blocks": blocks_dict,
        "sufficient_data": len(blocks_dict) > 0,
    }


def analyze_regional_weather_impact(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyzes weather-demand relationships across regions if multiple exist."""
    if df.empty or "demand_mw" not in df.columns:
        return {"regions": {}, "multi_region_supported": False}

    region_col = "region" if "region" in df.columns else ("location" if "location" in df.columns else None)

    if not region_col:
        return {"regions": {"Grid_Alpha": {"observation_count": len(df)}}, "multi_region_supported": False}

    regional_dict = {}
    grouped = df.groupby(region_col, observed=False)

    for reg_name, group in grouped:
        count = int(len(group))
        if count == 0:
            continue

        temp_corr = 0.0
        if "temperature_c" in group.columns and count >= 5:
            c = group["temperature_c"].corr(group["demand_mw"])
            temp_corr = 0.0 if np.isnan(c) else round(float(c), 4)

        regional_dict[str(reg_name)] = {
            "observation_count": count,
            "mean_demand_mw": round(float(group["demand_mw"].mean()), 2),
            "median_demand_mw": round(float(group["demand_mw"].median()), 2),
            "mean_temperature_c": round(float(group["temperature_c"].mean()), 1) if "temperature_c" in group.columns else 0.0,
            "temp_demand_correlation": temp_corr,
        }

    return {
        "regions": regional_dict,
        "region_count": len(regional_dict),
        "multi_region_supported": len(regional_dict) > 1,
    }
