"""Weather Impact Analytics Package Initialization."""

from app.models.weather_impact.descriptive import analyze_weather_conditions
from app.models.weather_impact.temperature import (
    calculate_cdd_hdd,
    analyze_temperature_impact,
    evaluate_nonlinear_temperature_relationship,
)
from app.models.weather_impact.rain_humidity import (
    analyze_rain_impact,
    analyze_humidity_impact,
)
from app.models.weather_impact.correlations import calculate_weather_correlations
from app.models.weather_impact.lags import generate_lagged_weather_features, analyze_lagged_impacts
from app.models.weather_impact.forecast_experiment import evaluate_weather_forecasting_value
from app.models.weather_impact.peak_context import (
    analyze_peak_demand_weather_context,
    analyze_time_of_day_weather_impact,
    analyze_regional_weather_impact,
)
from app.models.weather_impact.scoring import calculate_weather_impact_score
from app.models.weather_impact.summary import generate_weather_impact_summary

__all__ = [
    "analyze_weather_conditions",
    "calculate_cdd_hdd",
    "analyze_temperature_impact",
    "evaluate_nonlinear_temperature_relationship",
    "analyze_rain_impact",
    "analyze_humidity_impact",
    "calculate_weather_correlations",
    "generate_lagged_weather_features",
    "analyze_lagged_impacts",
    "evaluate_weather_forecasting_value",
    "analyze_peak_demand_weather_context",
    "analyze_time_of_day_weather_impact",
    "analyze_regional_weather_impact",
    "calculate_weather_impact_score",
    "generate_weather_impact_summary",
]
