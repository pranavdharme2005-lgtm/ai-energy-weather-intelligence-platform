"""Weather impact summary generator aggregator module."""

from typing import Dict, Any
import pandas as pd
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
from app.models.weather_impact.lags import analyze_lagged_impacts
from app.models.weather_impact.forecast_experiment import evaluate_weather_forecasting_value
from app.models.weather_impact.peak_context import (
    analyze_peak_demand_weather_context,
    analyze_time_of_day_weather_impact,
    analyze_regional_weather_impact,
)
from app.models.weather_impact.scoring import calculate_weather_impact_score
from app.utils.logger import get_logger

logger = get_logger(__name__)


def generate_weather_impact_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """Generates comprehensive, structured weather impact analytics summary for energy demand.

    Returns:
        Structured dictionary matching Stage 7 specification:
        {
            "temperature_relationship": {...},
            "rain_relationship": {...},
            "humidity_relationship": {...},
            "weather_condition_comparison": {...},
            "top_predictive_weather_features": [...],
            "weather_forecast_value": {...},
            "peak_weather_context": {...},
            "weather_impact_score": {...}
        }
    """
    if df.empty:
        logger.warning("Empty dataframe provided to generate_weather_impact_summary.")
        return {"error": "Empty dataframe provided"}

    # Process CDD/HDD degree days
    df_proc = calculate_cdd_hdd(df)

    # 1. Descriptive weather condition analysis
    cond_analysis = analyze_weather_conditions(df_proc)

    # 2. Temperature analysis
    temp_bins_analysis = analyze_temperature_impact(df_proc)
    temp_nonlinear = evaluate_nonlinear_temperature_relationship(df_proc)

    # 3. Rain analysis
    rain_analysis = analyze_rain_impact(df_proc)

    # 4. Humidity analysis
    humidity_analysis = analyze_humidity_impact(df_proc)

    # 5. Correlation analysis
    corr_analysis = calculate_weather_correlations(df_proc)

    # 6. Lagged analysis
    lag_analysis = analyze_lagged_impacts(df_proc)

    # 7. Weather forecasting contribution experiment
    forecast_eval = evaluate_weather_forecasting_value(df_proc)

    # 8. Peak demand weather context & Time-of-day
    peak_context = analyze_peak_demand_weather_context(df_proc)
    time_of_day = analyze_time_of_day_weather_impact(df_proc)
    regional = analyze_regional_weather_impact(df_proc)

    # Top predictive weather features from forecast experiment or correlations
    top_features = list(forecast_eval.get("top_weather_features", {}).keys())
    if not top_features:
        pearson_map = corr_analysis.get("demand_correlations_pearson", {})
        top_features = sorted(pearson_map.keys(), key=lambda k: abs(pearson_map[k]), reverse=True)

    # Extract correlation scalar values safely for scoring
    temp_corr = corr_analysis.get("demand_correlations_pearson", {}).get("temperature_c", 0.0)
    hum_corr = corr_analysis.get("demand_correlations_pearson", {}).get("humidity_pct", 0.0)
    rain_dev_pct = rain_analysis.get("rain_periods", {}).get("deviation_pct", 0.0)
    forecast_improve_pct = forecast_eval.get("mae_improvement_pct", 0.0)

    # Calculate overall Weather Impact Score
    impact_score = calculate_weather_impact_score(
        df=df_proc,
        temp_corr=temp_corr,
        humidity_corr=hum_corr,
        rain_deviation_pct=rain_dev_pct,
        forecasting_improvement_pct=forecast_improve_pct,
    )

    return {
        "temperature_relationship": {
            "binned_analysis": temp_bins_analysis,
            "non_linear_evaluation": temp_nonlinear,
            "degree_days_summary": {
                "total_cdd_degree_days": round(float(df_proc["cdd"].sum()), 2) if "cdd" in df_proc.columns else 0.0,
                "total_hdd_degree_days": round(float(df_proc["hdd"].sum()), 2) if "hdd" in df_proc.columns else 0.0,
            },
        },
        "rain_relationship": rain_analysis,
        "humidity_relationship": humidity_analysis,
        "weather_condition_comparison": cond_analysis,
        "correlation_analysis": corr_analysis,
        "lagged_weather_impact": lag_analysis,
        "top_predictive_weather_features": top_features,
        "weather_forecast_value": forecast_eval,
        "peak_weather_context": peak_context,
        "time_of_day_analysis": time_of_day,
        "regional_analysis": regional,
        "weather_impact_score": impact_score,
    }
