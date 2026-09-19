"""Weather Impact Score engine summarizing overall weather sensitivity."""

from typing import Dict, Any
import pandas as pd
import numpy as np
from app.utils.logger import get_logger

logger = get_logger(__name__)


def calculate_weather_impact_score(
    df: pd.DataFrame,
    temp_corr: float = 0.0,
    humidity_corr: float = 0.0,
    rain_deviation_pct: float = 0.0,
    forecasting_improvement_pct: float = 0.0
) -> Dict[str, Any]:
    """Calculates a transparent Weather Impact Score (0.0 to 100.0) summarizing weather-driven demand sensitivity.

    Formula Components:
        1. Temperature Correlation Weight (40%): Magnitude of linear temperature-demand association (0.0 to 40 pts).
        2. Rain Demand Deviation Weight (20%): Percentage shift in demand during rain events (0.0 to 20 pts).
        3. Humidity Correlation Weight (20%): Magnitude of humidity-demand association (0.0 to 20 pts).
        4. Forecasting Value Weight (20%): MAE improvement % when weather features are added to demand forecaster (0.0 to 20 pts).

    Score Range & Classification:
        - 0.0 - 25.0:  LOW (Weather has minimal measurable relationship with grid demand)
        - 25.1 - 50.0: MODERATE (Moderate temperature & seasonal load sensitivity)
        - 50.1 - 75.0: HIGH (Strong weather sensitivity; cooling/heating degree days drive major load swings)
        - 75.1 - 100.0: SEVERE (Extreme meteorological sensitivity; major weather events cause severe demand shifts)
    """
    w_temp = min(abs(temp_corr) * 40.0, 40.0)
    w_hum = min(abs(humidity_corr) * 20.0, 20.0)
    w_rain = min(abs(rain_deviation_pct) * 2.0, 20.0)  # 10% deviation -> 20 pts
    w_fore = min(max(forecasting_improvement_pct, 0.0) * 2.0, 20.0)  # 10% MAE improvement -> 20 pts

    raw_score = w_temp + w_hum + w_rain + w_fore
    final_score = round(float(min(max(raw_score, 0.0), 100.0)), 1)

    if final_score <= 25.0:
        level = "LOW"
        desc = "Grid energy demand shows low sensitivity to immediate meteorological fluctuations."
    elif final_score <= 50.0:
        level = "MODERATE"
        desc = "Moderate weather sensitivity. Temperature and humidity influence HVAC and industrial loads."
    elif final_score <= 75.0:
        level = "HIGH"
        desc = "High weather sensitivity. Temperature extremes (CDD/HDD) strongly dictate peak grid loading."
    else:
        level = "SEVERE"
        desc = "Severe weather sensitivity. Extreme weather shifts cause drastic demand surges."

    return {
        "weather_impact_score": final_score,
        "impact_level": level,
        "description": desc,
        "score_components": {
            "temperature_correlation_points": round(w_temp, 1),
            "humidity_correlation_points": round(w_hum, 1),
            "rain_deviation_points": round(w_rain, 1),
            "forecasting_value_points": round(w_fore, 1),
        },
        "formula_documentation": (
            "Score = min(100, 40*|corr_temp| + 20*|corr_humidity| + 2.0*|rain_dev_%| + 2.0*|forecast_mae_improve_%|)"
        ),
        "limitations": (
            "Observational metric summarizing statistical association strength. "
            "Does not prove direct causation or account for unobserved economic confounding variables."
        ),
    }
