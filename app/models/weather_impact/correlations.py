"""Correlation analysis submodule for weather variables and energy demand."""

from typing import Dict, Any, List
import pandas as pd
import numpy as np
from app.utils.logger import get_logger

logger = get_logger(__name__)


def calculate_weather_correlations(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculates Pearson and Spearman correlation matrices between demand and weather variables.

    - Pearson Correlation: Measures linear relationship strength. Sensitive to outliers and extreme spikes.
    - Spearman Correlation: Measures monotonic rank association. Robust to non-linear monotonic shifts and non-normal distributions.

    IMPORTANT: Correlation indicates association, NOT direct causation.
    """
    if df.empty or "demand_mw" not in df.columns:
        return {"pearson": {}, "spearman": {}, "variables_analyzed": [], "note": "Insufficient data"}

    candidate_vars = [
        "temperature_c", "humidity_pct", "pressure_hpa", "wind_speed_ms",
        "cloud_cover_pct", "precipitation_mm", "probability", "cdd", "hdd"
    ]
    available_vars = [col for col in candidate_vars if col in df.columns]

    if not available_vars:
        return {"pearson": {}, "spearman": {}, "variables_analyzed": [], "note": "No weather variables found"}

    cols_to_analyze = ["demand_mw"] + available_vars
    df_clean = df[cols_to_analyze].dropna()

    if len(df_clean) < 5:
        return {"pearson": {}, "spearman": {}, "variables_analyzed": available_vars, "note": "Fewer than 5 observations"}

    # Filter out zero-variance columns to avoid warnings/NaNs
    valid_cols = []
    for col in cols_to_analyze:
        if df_clean[col].nunique() > 1:
            valid_cols.append(col)

    if "demand_mw" not in valid_cols:
        return {"pearson": {}, "spearman": {}, "variables_analyzed": [], "note": "Demand column has zero variance"}

    sub_df = df_clean[valid_cols]

    pearson_corr = sub_df.corr(method="pearson")
    spearman_corr = sub_df.corr(method="spearman")

    pearson_dict = {}
    spearman_dict = {}

    for var in valid_cols:
        if var == "demand_mw":
            continue
        p_val = pearson_corr.loc["demand_mw", var]
        s_val = spearman_corr.loc["demand_mw", var]

        pearson_dict[var] = 0.0 if np.isnan(p_val) else round(float(p_val), 4)
        spearman_dict[var] = 0.0 if np.isnan(s_val) else round(float(s_val), 4)

    # Convert full matrices to nested dicts for visualization/API
    full_pearson = pearson_corr.fillna(0.0).round(4).to_dict()
    full_spearman = spearman_corr.fillna(0.0).round(4).to_dict()

    return {
        "demand_correlations_pearson": pearson_dict,
        "demand_correlations_spearman": spearman_dict,
        "matrix_pearson": full_pearson,
        "matrix_spearman": full_spearman,
        "variables_analyzed": [v for v in valid_cols if v != "demand_mw"],
        "statistical_explanation": (
            "Pearson correlation measures strictly linear relationships. "
            "Spearman rank correlation assesses monotonic relationships and is less sensitive to extreme outliers. "
            "A high Spearman correlation with a lower Pearson correlation indicates a non-linear but monotonic association."
        ),
    }
