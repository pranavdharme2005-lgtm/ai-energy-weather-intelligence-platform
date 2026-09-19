"""Temperature impact analysis submodule for energy demand platform."""

from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np
from app.utils.logger import get_logger

logger = get_logger(__name__)


def calculate_cdd_hdd(df: pd.DataFrame, base_temp_c: float = 18.3) -> pd.DataFrame:
    """Calculates Cooling Degree Days (CDD) and Heating Degree Days (HDD) for temperature series."""
    if df.empty or "temperature_c" not in df.columns:
        return df

    res = df.copy()
    res["cdd"] = np.maximum(res["temperature_c"] - base_temp_c, 0.0)
    res["hdd"] = np.maximum(base_temp_c - res["temperature_c"], 0.0)
    return res


def analyze_temperature_impact(
    df: pd.DataFrame, num_bins: int = 4, custom_labels: List[str] = None
) -> Dict[str, Any]:
    """Analyzes energy demand across temperature ranges/bins.

    Args:
        df: DataFrame containing 'demand_mw' and 'temperature_c'.
        num_bins: Number of dynamic bins (quantiles) if labels not matched.
        custom_labels: Preferred bin names (e.g., ['Cold', 'Mild', 'Warm', 'Hot']).

    Returns:
        Dict summarizing demand stats across temperature bins.
    """
    if df.empty or "temperature_c" not in df.columns or "demand_mw" not in df.columns:
        logger.warning("Empty df or missing columns in analyze_temperature_impact.")
        return {"temperature_bins": {}, "total_count": 0}

    df_clean = df.dropna(subset=["temperature_c", "demand_mw"]).copy()
    if df_clean.empty:
        return {"temperature_bins": {}, "total_count": 0}

    min_temp = float(df_clean["temperature_c"].min())
    max_temp = float(df_clean["temperature_c"].max())

    # Build temperature bins based on dataset distribution
    if custom_labels is None:
        custom_labels = ["Cold", "Mild", "Warm", "Hot"]

    n_labels = len(custom_labels)
    try:
        # Try qcut for quantile-based bins to handle non-uniform distributions
        df_clean["temp_bin"] = pd.qcut(
            df_clean["temperature_c"], q=n_labels, labels=custom_labels, duplicates="drop"
        )
    except Exception:
        # Fallback to cut for equal-width bins if qcut fails due to low variance
        df_clean["temp_bin"] = pd.cut(
            df_clean["temperature_c"], bins=n_labels, labels=custom_labels[:n_labels]
        )

    binned_stats = {}
    grouped = df_clean.groupby("temp_bin", observed=False)

    for bin_name, group in grouped:
        count = int(len(group))
        if count == 0:
            continue

        temp_min = float(group["temperature_c"].min()) if count > 0 else 0.0
        temp_max = float(group["temperature_c"].max()) if count > 0 else 0.0

        binned_stats[str(bin_name)] = {
            "observation_count": count,
            "temp_range_c": [round(temp_min, 1), round(temp_max, 1)],
            "mean_demand_mw": round(float(group["demand_mw"].mean()), 2),
            "median_demand_mw": round(float(group["demand_mw"].median()), 2),
            "std_demand_mw": round(float(group["demand_mw"].std()), 2) if count > 1 else 0.0,
            "min_demand_mw": round(float(group["demand_mw"].min()), 2),
            "max_demand_mw": round(float(group["demand_mw"].max()), 2),
        }

    return {
        "temperature_bins": binned_stats,
        "overall_min_temp_c": round(min_temp, 1),
        "overall_max_temp_c": round(max_temp, 1),
        "total_count": len(df_clean),
    }


def evaluate_nonlinear_temperature_relationship(df: pd.DataFrame) -> Dict[str, Any]:
    r"""Evaluates whether the temperature-demand relationship exhibits a non-linear (e.g. U-shaped) curve.

    Fits linear ($MW = a \cdot T + b$) vs quadratic ($MW = a \cdot T^2 + b \cdot T + c$) models.
    """
    if df.empty or "temperature_c" not in df.columns or "demand_mw" not in df.columns:
        return {"is_nonlinear": False, "r2_linear": 0.0, "r2_quadratic": 0.0, "pattern": "Insufficient data"}

    df_clean = df.dropna(subset=["temperature_c", "demand_mw"])
    if len(df_clean) < 10:
        return {"is_nonlinear": False, "r2_linear": 0.0, "r2_quadratic": 0.0, "pattern": "Insufficient data samples"}

    x = df_clean["temperature_c"].values
    y = df_clean["demand_mw"].values

    # Fit linear
    p_lin = np.polyfit(x, y, 1)
    pred_lin = np.polyval(p_lin, x)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    ss_res_lin = np.sum((y - pred_lin) ** 2)
    r2_lin = 1.0 - (ss_res_lin / ss_tot) if ss_tot > 0 else 0.0

    # Fit quadratic
    p_quad = np.polyfit(x, y, 2)
    pred_quad = np.polyval(p_quad, x)
    ss_res_quad = np.sum((y - pred_quad) ** 2)
    r2_quad = 1.0 - (ss_res_quad / ss_tot) if ss_tot > 0 else 0.0

    a_coef = float(p_quad[0])
    r2_improvement = r2_quad - r2_lin
    is_nonlinear = r2_improvement > 0.03  # Noticeable improvement (>3%)

    if is_nonlinear and a_coef > 0:
        pattern = "U-shaped non-linear relationship (demand increases at both extreme cold and extreme heat)"
    elif is_nonlinear and a_coef < 0:
        pattern = "Inverted U-shaped non-linear relationship"
    elif p_lin[0] > 0:
        pattern = "Monotonic positive linear relationship (higher temp correlates with higher demand)"
    else:
        pattern = "Monotonic negative linear relationship (lower temp correlates with higher demand)"

    return {
        "is_nonlinear": bool(is_nonlinear),
        "r2_linear": round(float(r2_lin), 4),
        "r2_quadratic": round(float(r2_quad), 4),
        "r2_improvement": round(float(r2_improvement), 4),
        "quadratic_a_coefficient": round(a_coef, 4),
        "pattern_description": pattern,
    }
