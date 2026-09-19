"""Weather to Energy Load Sensitivity & Correlation Analysis Service."""

from typing import Dict, Any, List
import os
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sqlalchemy.orm import Session

from app.database.repository import EnergyRepository, WeatherRepository, WeatherImpactRepository
from app.models.weather_impact import (
    generate_weather_impact_summary,
    calculate_cdd_hdd,
    calculate_weather_correlations,
)
from app.models.weather_impact.visualizations import (
    plot_temperature_vs_demand,
    plot_temperature_bins,
    plot_weather_condition_demand,
    plot_rain_vs_no_rain,
    plot_humidity_vs_demand,
    plot_weather_correlation_matrix,
    plot_weather_feature_importance,
    plot_peak_demand_weather_context,
    plot_forecasting_comparison,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class WeatherEnergyImpactAnalyzer:
    """Calculates weather sensitivity factors (temperature elasticity, precipitation impact).

    Preserved for backward compatibility with earlier stages.
    """

    @staticmethod
    def calculate_correlations(merged_df: pd.DataFrame) -> Dict[str, float]:
        """Calculates Pearson correlation coefficients between weather variables and demand."""
        res = calculate_weather_correlations(merged_df)
        return res.get("demand_correlations_pearson", {})

    @staticmethod
    def calculate_cooling_heating_degree_days(df: pd.DataFrame, base_temp_c: float = 18.3) -> pd.DataFrame:
        """Calculates Cooling Degree Days (CDD) and Heating Degree Days (HDD)."""
        return calculate_cdd_hdd(df, base_temp_c=base_temp_c)


class WeatherImpactService:
    """High-level service orchestrating Stage 7 Weather Impact Analytics."""

    @staticmethod
    def load_merged_dataset(db: Session, region: str = "Grid_Alpha", location: str = "London", hours: int = 168) -> pd.DataFrame:
        """Loads time-aligned weather and energy data from database repositories."""
        try:
            energy_recs = EnergyRepository.get_latest(db, region=region, limit=hours)
            weather_recs = WeatherRepository.get_latest(db, location=location, limit=hours)

            if len(energy_recs) >= 10 and len(weather_recs) >= 10:
                e_df = pd.DataFrame([{
                    "timestamp": pd.to_datetime(r.timestamp, utc=True),
                    "region": r.region,
                    "demand_mw": r.demand_mw
                } for r in energy_recs]).sort_values("timestamp").reset_index(drop=True)

                w_df = pd.DataFrame([{
                    "timestamp": pd.to_datetime(r.timestamp, utc=True),
                    "temperature_c": r.temperature_c,
                    "humidity_pct": r.humidity_pct,
                    "pressure_hpa": r.pressure_hpa,
                    "wind_speed_ms": r.wind_speed_ms,
                    "cloud_cover_pct": r.cloud_cover_pct,
                    "precipitation_mm": r.precipitation_mm,
                    "weather_condition": r.weather_condition
                } for r in weather_recs]).sort_values("timestamp").reset_index(drop=True)

                merged_df = pd.merge_asof(e_df, w_df, on="timestamp", direction="nearest")
                return merged_df
        except Exception as e:
            logger.warning(f"Failed loading DB records for weather impact: {e}")

        return WeatherImpactService.get_synthetic_merged_dataset(region=region, hours=hours)

    @staticmethod
    def get_synthetic_merged_dataset(region: str = "Grid_Alpha", hours: int = 168) -> pd.DataFrame:
        """Generates realistic synthetic merged dataset for fallback analytics."""
        now = datetime.now(timezone.utc)
        timestamps = pd.date_range(end=now, periods=hours, freq="1h", tz="UTC")
        n = len(timestamps)

        h_idx = timestamps.hour
        temps = np.round(18.0 + 8.0 * np.sin((h_idx - 8) * np.pi / 12) + np.random.normal(0, 1.5, n), 2)
        cdd = np.maximum(temps - 18.3, 0.0)
        hdd = np.maximum(18.3 - temps, 0.0)

        base_demand = 2800.0 + 500.0 * np.sin((h_idx - 4) * np.pi / 12) + 40.0 * cdd + 35.0 * hdd
        demands = np.round(base_demand + np.random.normal(0, 30, n), 2)
        humids = np.clip(np.round(65.0 - 18.0 * np.sin((h_idx - 8) * np.pi / 12) + np.random.normal(0, 4.0, n), 2), 10.0, 100.0)
        pressures = np.round(1013.25 + np.random.normal(0, 5.0, n), 2)
        winds = np.round(np.abs(4.0 + np.random.normal(0, 1.5, n)), 2)
        clouds = np.clip(np.round(45.0 + np.random.normal(0, 25.0, n), 2), 0.0, 100.0)
        precips = np.where(np.random.rand(n) < 0.15, np.random.exponential(2.0, n), 0.0)
        conds = np.where(precips > 0.5, "Rain", np.where(clouds > 60, "Cloudy", "Clear"))

        return pd.DataFrame({
            "timestamp": timestamps,
            "region": region,
            "demand_mw": demands,
            "temperature_c": temps,
            "humidity_pct": humids,
            "pressure_hpa": pressures,
            "wind_speed_ms": winds,
            "cloud_cover_pct": clouds,
            "precipitation_mm": precips,
            "weather_condition": conds,
            "probability": np.where(precips > 0, 0.85, 0.1),
        })

    @staticmethod
    def analyze_dataset(df: pd.DataFrame) -> Dict[str, Any]:
        """Runs full Stage 7 weather impact analysis on provided time-aligned DataFrame."""
        return generate_weather_impact_summary(df)

    @staticmethod
    def analyze_and_persist(db: Session, region: str = "Grid_Alpha") -> Dict[str, Any]:
        """Loads cleaned analytical dataset, performs weather impact analysis, and persists metrics to DB."""
        df = WeatherImpactService.load_merged_dataset(db, region=region)
        summary = generate_weather_impact_summary(df)

        # Prepare DB records
        records_to_save = []

        # Temp correlation
        pearson_map = summary.get("correlation_analysis", {}).get("demand_correlations_pearson", {})
        if "temperature_c" in pearson_map:
            records_to_save.append({
                "region": region,
                "analysis_type": "correlation",
                "weather_variable": "temperature_c",
                "metric_name": "pearson_correlation",
                "metric_value": float(pearson_map["temperature_c"]),
                "sample_count": len(df),
            })

        # Weather Impact Score
        score_info = summary.get("weather_impact_score", {})
        if "weather_impact_score" in score_info:
            records_to_save.append({
                "region": region,
                "analysis_type": "scoring",
                "weather_variable": "composite",
                "metric_name": "weather_impact_score",
                "metric_value": float(score_info["weather_impact_score"]),
                "sample_count": len(df),
                "details_json": str(score_info.get("impact_level", "NORMAL")),
            })

        # Forecast MAE improvement
        fore_val = summary.get("weather_forecast_value", {})
        if "mae_improvement_pct" in fore_val:
            records_to_save.append({
                "region": region,
                "analysis_type": "forecast_eval",
                "weather_variable": "all_weather",
                "metric_name": "mae_improvement_pct",
                "metric_value": float(fore_val["mae_improvement_pct"]),
                "sample_count": len(df),
            })

        if records_to_save:
            WeatherImpactRepository.save_impact_records(db, records_to_save)

        return summary

    @staticmethod
    def generate_all_plots(df: pd.DataFrame, output_dir: str = "docs/images/stage7") -> List[str]:
        """Generates and saves all 9 required Matplotlib figures for Stage 7."""
        os.makedirs(output_dir, exist_ok=True)
        saved_paths = []

        summary = generate_weather_impact_summary(df)

        plots = [
            ("01_temp_vs_demand.png", plot_temperature_vs_demand(df)),
            ("02_temp_bins.png", plot_temperature_bins(summary.get("temperature_relationship", {}).get("binned_analysis", {}))),
            ("03_weather_condition.png", plot_weather_condition_demand(summary.get("weather_condition_comparison", {}))),
            ("04_rain_vs_norain.png", plot_rain_vs_no_rain(summary.get("rain_relationship", {}))),
            ("05_humidity_vs_demand.png", plot_humidity_vs_demand(df)),
            ("06_correlation_matrix.png", plot_weather_correlation_matrix(summary.get("correlation_analysis", {}))),
            ("07_feature_importance.png", plot_weather_feature_importance(summary.get("weather_forecast_value", {}).get("top_weather_features", {}))),
            ("08_peak_weather_context.png", plot_peak_demand_weather_context(summary.get("peak_weather_context", {}))),
            ("09_forecasting_comparison.png", plot_forecasting_comparison(summary.get("weather_forecast_value", {}))),
        ]

        for filename, fig in plots:
            filepath = os.path.join(output_dir, filename)
            fig.savefig(filepath, bbox_inches="tight", dpi=150)
            plt.close(fig)
            saved_paths.append(filepath)

        logger.info(f"Saved {len(saved_paths)} Stage 7 visualization plots to {output_dir}")
        return saved_paths
