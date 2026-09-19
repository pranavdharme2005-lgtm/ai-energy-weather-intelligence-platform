"""Rain and humidity impact analysis submodule for energy demand platform."""

from typing import Dict, Any
import pandas as pd
import numpy as np
from app.utils.logger import get_logger

logger = get_logger(__name__)


def analyze_rain_impact(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyzes energy demand during rain vs no-rain periods and rain probability.

    Calculates:
        - average demand
        - median demand
        - demand deviation from overall baseline normal demand
        - observation counts
    """
    if df.empty or "demand_mw" not in df.columns:
        return {"rain_stats": {}, "sufficient_data": False}

    df_clean = df.dropna(subset=["demand_mw"]).copy()
    if df_clean.empty:
        return {"rain_stats": {}, "sufficient_data": False}

    baseline_mean = float(df_clean["demand_mw"].mean())

    # Identify rain condition
    is_rain = pd.Series(False, index=df_clean.index)
    if "precipitation_mm" in df_clean.columns:
        is_rain = is_rain | (df_clean["precipitation_mm"] > 0.1)
    if "weather_condition" in df_clean.columns:
        is_rain = is_rain | df_clean["weather_condition"].astype(str).str.contains("Rain|Storm|Drizzle", case=False, na=False)

    df_clean["is_rain"] = is_rain

    rain_group = df_clean[df_clean["is_rain"]]
    no_rain_group = df_clean[~df_clean["is_rain"]]

    rain_count = len(rain_group)
    no_rain_count = len(no_rain_group)

    rain_mean = float(rain_group["demand_mw"].mean()) if rain_count > 0 else 0.0
    no_rain_mean = float(no_rain_group["demand_mw"].mean()) if no_rain_count > 0 else 0.0

    rain_dev_mw = rain_mean - baseline_mean if rain_count > 0 else 0.0
    rain_dev_pct = (rain_dev_mw / baseline_mean * 100.0) if baseline_mean > 0 and rain_count > 0 else 0.0

    prob_correlation = 0.0
    if "probability" in df_clean.columns:
        corr = df_clean["probability"].corr(df_clean["demand_mw"])
        prob_correlation = 0.0 if np.isnan(corr) else round(float(corr), 4)

    return {
        "baseline_mean_mw": round(baseline_mean, 2),
        "rain_periods": {
            "observation_count": rain_count,
            "mean_demand_mw": round(rain_mean, 2),
            "median_demand_mw": round(float(rain_group["demand_mw"].median()), 2) if rain_count > 0 else 0.0,
            "deviation_from_baseline_mw": round(rain_dev_mw, 2),
            "deviation_pct": round(rain_dev_pct, 2),
        },
        "no_rain_periods": {
            "observation_count": no_rain_count,
            "mean_demand_mw": round(no_rain_mean, 2),
            "median_demand_mw": round(float(no_rain_group["demand_mw"].median()), 2) if no_rain_count > 0 else 0.0,
        },
        "rain_probability_correlation": prob_correlation,
        "sufficient_data": (rain_count + no_rain_count) >= 10,
    }


def analyze_humidity_impact(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyzes relationship between relative humidity (%) and energy demand.

    Calculates:
        - linear correlation
        - binned demand statistics (Low, Moderate, High, Very High)
        - humidity x temperature interaction effect
    """
    if df.empty or "humidity_pct" not in df.columns or "demand_mw" not in df.columns:
        return {"humidity_bins": {}, "correlation": 0.0, "sufficient_data": False}

    df_clean = df.dropna(subset=["humidity_pct", "demand_mw"]).copy()
    if df_clean.empty:
        return {"humidity_bins": {}, "correlation": 0.0, "sufficient_data": False}

    corr = df_clean["humidity_pct"].corr(df_clean["demand_mw"])
    corr_val = 0.0 if np.isnan(corr) else round(float(corr), 4)

    # Bin humidity into 4 readable ranges
    humidity_labels = ["Low (<40%)", "Moderate (40-60%)", "High (60-80%)", "Very High (>80%)"]
    df_clean["humidity_bin"] = pd.cut(
        df_clean["humidity_pct"],
        bins=[-1, 40, 60, 80, 101],
        labels=humidity_labels
    )

    binned_stats = {}
    grouped = df_clean.groupby("humidity_bin", observed=False)

    for bin_name, group in grouped:
        count = int(len(group))
        if count == 0:
            continue
        binned_stats[str(bin_name)] = {
            "observation_count": count,
            "mean_demand_mw": round(float(group["demand_mw"].mean()), 2),
            "median_demand_mw": round(float(group["demand_mw"].median()), 2),
            "std_demand_mw": round(float(group["demand_mw"].std()), 2) if count > 1 else 0.0,
        }

    # Temperature interaction (Heat index proxy: T * Humidity)
    interaction_corr = 0.0
    if "temperature_c" in df_clean.columns:
        df_clean["temp_humidity_interaction"] = df_clean["temperature_c"] * df_clean["humidity_pct"]
        int_c = df_clean["temp_humidity_interaction"].corr(df_clean["demand_mw"])
        interaction_corr = 0.0 if np.isnan(int_c) else round(float(int_c), 4)

    return {
        "correlation": corr_val,
        "temp_humidity_interaction_correlation": interaction_corr,
        "humidity_bins": binned_stats,
        "sufficient_data": len(df_clean) >= 10,
    }
