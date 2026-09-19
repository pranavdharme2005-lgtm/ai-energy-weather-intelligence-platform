"""Energy & Weather Anomaly Detection Application Service."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np

from app.database.session import SessionLocal
from app.database.repository import EnergyRepository, WeatherRepository, AnomalyRepository
from app.models.anomaly_detector import AnomalyDetector
from app.services.energy_forecasting_service import EnergyForecastingService
from app.models.anomaly_detection.summary import calculate_anomaly_summary
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AnomalyDetectionService:
    """Orchestrates historical dataset loading, multi-dimensional anomaly detection, summary generation, and persistence."""

    def __init__(self):
        self.detector = AnomalyDetector()
        self.forecasting_service = EnergyForecastingService()

    def run_full_detection(
        self, region: str = "Grid_Alpha", location: str = "London", hours: int = 168, save_to_db: bool = False
    ) -> Dict[str, Any]:
        """Runs full multi-dimensional anomaly detection suite over historical window.
        
        Args:
            region: Regional grid identifier.
            location: Weather station location.
            hours: Historical analysis window in hours.
            save_to_db: Option to persist detected anomalies to database.
            
        Returns:
            Dict[str, Any]: Complete detection results and summary statistics.
        """
        logger.info(f"Executing AnomalyDetectionService for region={region}, location={location} (past {hours} hours)...")

        # 1. Fetch observations from DB or generate historical fallbacks
        df_energy, df_weather = self._load_recent_observations(region=region, location=location, hours=hours)

        # 2. Generate Stage 5 forecast predictions for forecast-deviation anomaly detection
        forecast_results = []
        try:
            fc_output = self.forecasting_service.generate_forecast(region=region, location=location, horizon_hours=24, save_to_db=False)
            from app.models.base import EnergyForecastResult
            forecast_results = [EnergyForecastResult(**f) for f in fc_output.get("forecasts", [])]
        except Exception as e:
            logger.warning(f"Could not generate forecast predictions for anomaly detection: {e}")

        # 3. Detect All Anomalies
        anomalies = self.detector.detect_all(
            df_energy=df_energy,
            df_weather=df_weather,
            forecast_results=forecast_results,
            region=region
        )

        anom_dicts = [a.model_dump() for a in anomalies]

        # 4. Calculate Summary Statistics
        summary = calculate_anomaly_summary(anomalies)

        # 5. Optionally Persist to Database
        persisted_count = 0
        if save_to_db and anom_dicts:
            db = SessionLocal()
            try:
                persisted_count = AnomalyRepository.save_anomalies(db, anom_dicts)
            finally:
                db.close()

        return {
            "region": region,
            "location": location,
            "window_hours": hours,
            "total_records_analyzed": len(df_energy),
            "summary": summary,
            "anomalies": anom_dicts,
            "persisted_count": persisted_count
        }

    def _load_recent_observations(self, region: str, location: str, hours: int = 168):
        """Loads historical energy & weather observations from repository or fallback synthetic generators."""
        db = SessionLocal()
        try:
            e_recs = EnergyRepository.get_latest(db, region=region, limit=hours)
            w_recs = WeatherRepository.get_latest(db, location=location, limit=hours)
        finally:
            db.close()

        now = datetime.now(timezone.utc)
        timestamps = pd.date_range(end=now, periods=hours, freq="1h", tz="UTC")
        n = len(timestamps)

        if len(e_recs) >= 24:
            df_e = pd.DataFrame([{
                "timestamp": r.timestamp,
                "region": r.region,
                "demand_mw": r.demand_mw
            } for r in e_recs]).sort_values("timestamp").reset_index(drop=True)
        else:
            h_idx = np.array(timestamps.hour, dtype=float)
            base_demand = 2800.0 + 600.0 * np.sin((h_idx - 4) * np.pi / 12) + 300.0 * np.cos((h_idx - 14) * np.pi / 6)
            demands = np.round(base_demand + np.random.normal(0, 40, n), 2)
            # Inject 2 synthetic test anomalies for validation
            demands[25] += 1200.0  # Demand spike anomaly
            demands[80] -= 950.0   # Demand dip anomaly

            df_e = pd.DataFrame({
                "timestamp": timestamps,
                "region": region,
                "demand_mw": demands
            })

        if len(w_recs) >= 24:
            df_w = pd.DataFrame([{
                "timestamp": r.timestamp,
                "location": r.location,
                "temperature_c": r.temperature_c,
                "humidity_pct": r.humidity_pct,
                "pressure_hpa": r.pressure_hpa,
                "wind_speed_ms": r.wind_speed_ms,
                "cloud_cover_pct": r.cloud_cover_pct,
                "precipitation_mm": r.precipitation_mm
            } for r in w_recs]).sort_values("timestamp").reset_index(drop=True)
        else:
            h_idx = np.array(timestamps.hour, dtype=float)
            temps = np.round(18.0 + 6.0 * np.sin((h_idx - 8) * np.pi / 12) + np.random.normal(0, 1.5, n), 2)
            humids = np.clip(np.round(65.0 - 18.0 * np.sin((h_idx - 8) * np.pi / 12) + np.random.normal(0, 4.0, n), 2), 10.0, 100.0)
            pressures = np.round(1013.25 + np.random.normal(0, 5.0, n), 2)
            winds = np.round(np.abs(4.0 + np.random.normal(0, 1.5, n)), 2)
            precips = np.where(np.random.rand(n) < 0.15, np.random.exponential(2.0, n), 0.0)

            # Inject 1 weather extreme anomaly
            temps[45] += 18.5  # Extreme heatwave anomaly

            df_w = pd.DataFrame({
                "timestamp": timestamps,
                "location": location,
                "temperature_c": temps,
                "humidity_pct": humids,
                "pressure_hpa": pressures,
                "wind_speed_ms": winds,
                "cloud_cover_pct": 40.0,
                "precipitation_mm": precips
            })

        return df_e, df_w
