"""Preset realistic scenario templates derived from analytical dataset distributions."""

from typing import Dict, Any
import pandas as pd
from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_scenario_templates(history_df: pd.DataFrame = None) -> Dict[str, Dict[str, Any]]:
    """Generates preset scenario templates with realistic input values derived from project dataset quantiles.

    Templates:
        - Hot Heatwave Day (Temp ~ 35C, Humidity ~ 70%, Rain Prob ~ 10%)
        - Cold Snap Day (Temp ~ 2C, Humidity ~ 85%, Rain Prob ~ 20%)
        - Heavy Rainstorm (Temp ~ 18C, Humidity ~ 95%, Precip ~ 15mm, Rain Prob ~ 90%)
        - High Humidity Summer (Temp ~ 30C, Humidity ~ 90%, Rain Prob ~ 40%)
    """
    if history_df is not None and not history_df.empty:
        # Dynamic bounds from actual data
        t_95 = float(history_df["temperature_c"].quantile(0.95)) if "temperature_c" in history_df else 35.0
        t_05 = float(history_df["temperature_c"].quantile(0.05)) if "temperature_c" in history_df else 2.0
        h_90 = float(history_df["humidity_pct"].quantile(0.90)) if "humidity_pct" in history_df else 90.0
    else:
        t_95, t_05, h_90 = 35.0, 2.0, 90.0

    return {
        "hot_heatwave": {
            "name": "Hot Heatwave Day",
            "description": "Simulates extreme summer peak temperatures driving air-conditioning load.",
            "inputs": {
                "temperature_c": round(t_95, 1),
                "humidity_pct": 65.0,
                "precipitation_mm": 0.0,
                "rain_probability": 0.10,
            }
        },
        "cold_snap": {
            "name": "Cold Snap Day",
            "description": "Simulates winter freezing conditions driving resistive and heat pump space heating.",
            "inputs": {
                "temperature_c": round(t_05, 1),
                "humidity_pct": 80.0,
                "precipitation_mm": 0.5,
                "rain_probability": 0.25,
            }
        },
        "heavy_rainstorm": {
            "name": "Heavy Rainstorm",
            "description": "Simulates intense thunderstorm precipitation with high humidity.",
            "inputs": {
                "temperature_c": 18.0,
                "humidity_pct": round(h_90, 1),
                "precipitation_mm": 12.5,
                "rain_probability": 0.95,
            }
        },
        "high_humidity_summer": {
            "name": "High Humidity Summer Day",
            "description": "Simulates high heat index (warm temperature + high humidity).",
            "inputs": {
                "temperature_c": 30.0,
                "humidity_pct": 88.0,
                "precipitation_mm": 2.0,
                "rain_probability": 0.45,
            }
        }
    }
