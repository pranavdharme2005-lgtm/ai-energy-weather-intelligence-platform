"""Weather Impact Analytics REST API Client wrapper."""

from typing import Dict, Any, Optional
import pandas as pd
from app.frontend.api.client import BaseAPIClient
from app.config.settings import settings
from app.database.session import SessionLocal
from app.database.repository import WeatherRepository, EnergyRepository
from app.services.weather_energy_impact import WeatherEnergyImpactAnalyzer


class AnalyticsAPIClient:
    """API Client for Weather Impact Analytics endpoints with fallback to service."""

    def __init__(self, base_client: BaseAPIClient):
        self.client = base_client

    def get_correlations(self, region: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Queries /analytics/correlations endpoint."""
        reg = region or settings.DEFAULT_REGION
        res = self.client.get("/analytics/correlations", params={"region": reg})
        if res:
            return res

        summary = self.get_analytics_summary(region=reg)
        return summary.get("correlations", {}) if summary else {}

    def get_analytics_summary(self, region: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Queries /analytics/summary endpoint."""
        reg = region or settings.DEFAULT_REGION
        res = self.client.get("/analytics/summary", params={"region": reg})
        if res:
            return res

        db = SessionLocal()
        try:
            w_recs = WeatherRepository.get_latest(db, limit=200)
            e_recs = EnergyRepository.get_latest(db, region=reg, limit=200)
            if not w_recs or not e_recs:
                return {}

            df_w = pd.DataFrame([{
                "timestamp": r.timestamp,
                "temperature_c": r.temperature_c,
                "humidity_pct": r.humidity_pct,
                "precipitation_mm": getattr(r, 'precipitation_mm', 0.0),
                "wind_speed_ms": getattr(r, 'wind_speed_ms', 0.0)
            } for r in w_recs])

            df_e = pd.DataFrame([{
                "timestamp": r.timestamp,
                "demand_mw": r.demand_mw
            } for r in e_recs])

            df_merged = pd.merge(df_w, df_e, on="timestamp", how="inner")
            if df_merged.empty:
                return {}

            corrs = WeatherEnergyImpactAnalyzer.calculate_correlations(df_merged)
            return {"region": reg, "correlations": corrs}
        except Exception:
            return {}
        finally:
            db.close()
