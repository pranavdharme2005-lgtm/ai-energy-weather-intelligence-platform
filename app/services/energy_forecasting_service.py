"""Energy Demand Forecasting Application Service."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np

from app.database.session import SessionLocal
from app.database.repository import EnergyRepository, WeatherRepository
from app.models.energy_forecaster import EnergyForecaster
from app.models.rain_predictor import RainPredictor
from app.models.energy_forecasting.peak_analysis import analyze_peak_demand
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EnergyForecastingService:
    """Orchestrates historical data fetching, feature construction, forecast execution, peak analysis, and persistence."""

    def __init__(self):
        self.forecaster = EnergyForecaster()
        self.rain_predictor = RainPredictor()

    def generate_forecast(
        self, region: str = "Grid_Alpha", location: str = "London", horizon_hours: int = 24, save_to_db: bool = False
    ) -> Dict[str, Any]:
        """Generates multi-step grid load forecast for specified region."""
        logger.info(f"Generating {horizon_hours}-hour Energy Demand Forecast for region={region}...")

        # 1. Fetch recent historical data from DB or generate fallback series
        history_df = self._load_recent_analytical_history(region=region, location=location)

        # 2. Enrich history with rain probability prediction
        try:
            rain_res = self.rain_predictor.predict(history_df)
            history_df["rain_probability"] = rain_res.probability
        except Exception as e:
            logger.warning(f"Could not calculate rain probability for forecasting enrichment: {e}")
            history_df["rain_probability"] = 0.0

        # 3. Execute Forecasting Inference
        forecast_results = self.forecaster.predict_horizon(history_df, region=region, horizon_hours=horizon_hours)
        if not isinstance(forecast_results, list):
            forecast_results = [forecast_results]

        forecast_dicts = [f.model_dump() for f in forecast_results]

        # 4. Perform Peak Demand Analysis
        peak_metrics = analyze_peak_demand(forecast_dicts)

        # 5. Optionally Persist to Database
        persisted_count = 0
        if save_to_db:
            db = SessionLocal()
            try:
                persisted_count = EnergyRepository.save_forecasts(db, forecast_dicts)
            finally:
                db.close()

        return {
            "region": region,
            "forecast_horizon": f"{horizon_hours}h",
            "predictions_count": len(forecast_dicts),
            "peak_analysis": peak_metrics,
            "forecasts": forecast_dicts,
            "persisted_count": persisted_count,
            "model_version": self.forecaster.model_version
        }

    def _load_recent_analytical_history(self, region: str, location: str, hours: int = 168) -> pd.DataFrame:
        """Retrieves or generates synthetic historical time series for feature calculation."""
        db = SessionLocal()
        try:
            energy_recs = EnergyRepository.get_latest(db, region=region, limit=hours)
            weather_recs = WeatherRepository.get_latest(db, location=location, limit=hours)
        finally:
            db.close()

        if len(energy_recs) >= 24:
            e_df = pd.DataFrame([{
                "timestamp": r.timestamp,
                "region": r.region,
                "demand_mw": r.demand_mw
            } for r in energy_recs]).sort_values("timestamp").reset_index(drop=True)

            if len(weather_recs) >= 24:
                w_df = pd.DataFrame([{
                    "timestamp": r.timestamp,
                    "temperature_c": r.temperature_c,
                    "humidity_pct": r.humidity_pct,
                    "pressure_hpa": r.pressure_hpa,
                    "wind_speed_ms": r.wind_speed_ms,
                    "cloud_cover_pct": r.cloud_cover_pct,
                    "precipitation_mm": r.precipitation_mm
                } for r in weather_recs]).sort_values("timestamp").reset_index(drop=True)

                merged_df = pd.merge_asof(e_df, w_df, on="timestamp", direction="nearest")
                return merged_df
            return e_df

        # Fallback synthetic historical sequence
        logger.info("Generating realistic historical time series sequence for forecasting engine...")
        now = datetime.now(timezone.utc)
        timestamps = pd.date_range(end=now, periods=hours, freq="1h", tz="UTC")
        n = len(timestamps)

        h_idx = timestamps.hour
        base_demand = 2800.0 + 600.0 * np.sin((h_idx - 4) * np.pi / 12) + 300.0 * np.cos((h_idx - 14) * np.pi / 6)
        demands = np.round(base_demand + np.random.normal(0, 40, n), 2)
        temps = np.round(18.0 + 6.0 * np.sin((h_idx - 8) * np.pi / 12) + np.random.normal(0, 1.5, n), 2)
        humids = np.clip(np.round(65.0 - 18.0 * np.sin((h_idx - 8) * np.pi / 12) + np.random.normal(0, 4.0, n), 2), 10.0, 100.0)
        pressures = np.round(1013.25 + np.random.normal(0, 5.0, n), 2)
        winds = np.round(np.abs(4.0 + np.random.normal(0, 1.5, n)), 2)
        clouds = np.clip(np.round(45.0 + np.random.normal(0, 25.0, n), 2), 0.0, 100.0)
        precips = np.where(np.random.rand(n) < 0.15, np.random.exponential(2.0, n), 0.0)

        return pd.DataFrame({
            "timestamp": timestamps,
            "region": region,
            "demand_mw": demands,
            "temperature_c": temps,
            "humidity_pct": humids,
            "pressure_hpa": pressures,
            "wind_speed_ms": winds,
            "cloud_cover_pct": clouds,
            "precipitation_mm": precips
        })
