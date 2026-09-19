"""Peak Demand Analysis Utility for Forecasting & Downstream Alerting Engine."""

from typing import Dict, Any, List
import pandas as pd
import numpy as np


def analyze_peak_demand(forecast_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyzes a sequence of forecasted demand values for peak load metrics.
    
    Args:
        forecast_records: List of forecast dicts containing 'forecast_target_time' and 'forecasted_demand_mw'.
        
    Returns:
        Dict[str, Any]: Detailed peak load metrics.
    """
    if not forecast_records:
        return {
            "peak_demand_mw": 0.0,
            "peak_timestamp": None,
            "min_demand_mw": 0.0,
            "avg_demand_mw": 0.0,
            "peak_to_avg_ratio": 1.0,
            "peak_severity": "NORMAL"
        }

    df = pd.DataFrame(forecast_records)
    demands = df["forecasted_demand_mw"].values

    peak_idx = int(np.argmax(demands))
    min_idx = int(np.argmin(demands))

    peak_mw = float(demands[peak_idx])
    min_mw = float(demands[min_idx])
    avg_mw = float(np.mean(demands))

    peak_to_avg = round(peak_mw / (avg_mw + 1e-6), 2)
    peak_ts = df["forecast_target_time"].iloc[peak_idx]

    severity = "NORMAL"
    if peak_to_avg > 1.35 or peak_mw > 3400.0:
        severity = "HIGH_CRITICAL"
    elif peak_to_avg > 1.20 or peak_mw > 3100.0:
        severity = "ELEVATED"

    return {
        "peak_demand_mw": round(peak_mw, 2),
        "peak_timestamp": peak_ts if isinstance(peak_ts, str) else str(peak_ts),
        "min_demand_mw": round(min_mw, 2),
        "avg_demand_mw": round(avg_mw, 2),
        "peak_to_avg_ratio": peak_to_avg,
        "peak_severity": severity
    }
