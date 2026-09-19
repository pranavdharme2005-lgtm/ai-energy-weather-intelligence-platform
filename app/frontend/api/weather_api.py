"""Weather REST API Client wrapper."""

from typing import Dict, Any, List, Optional
from app.frontend.api.client import BaseAPIClient
from app.config.settings import settings
from app.database.session import SessionLocal
from app.database.repository import WeatherRepository


class WeatherAPIClient:
    """API Client for Weather Telemetry endpoints with fallback to repository."""

    def __init__(self, base_client: BaseAPIClient):
        self.client = base_client

    def get_current_weather(self, location: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Queries /weather/current endpoint."""
        loc = location or settings.DEFAULT_LOCATION
        res = self.client.get("/weather/current", params={"location": loc})
        if res:
            return res

        # Fallback to local repository
        db = SessionLocal()
        try:
            records = WeatherRepository.get_latest(db, location=loc, limit=1)
            if records:
                r = records[0]
                return {
                    "timestamp": r.timestamp.isoformat() if hasattr(r.timestamp, 'isoformat') else str(r.timestamp),
                    "location": r.location,
                    "temperature_c": r.temperature_c,
                    "humidity_pct": r.humidity_pct,
                    "pressure_hpa": r.pressure_hpa,
                    "wind_speed_ms": r.wind_speed_ms,
                    "cloud_cover_pct": r.cloud_cover_pct,
                    "precipitation_mm": r.precipitation_mm,
                    "weather_condition": r.weather_condition,
                    "source": r.source or "Local DB"
                }
        except Exception:
            pass
        finally:
            db.close()
        return None

    def get_weather_history(self, location: Optional[str] = None, limit: int = 48) -> List[Dict[str, Any]]:
        """Queries /weather/history endpoint."""
        loc = location or settings.DEFAULT_LOCATION
        res = self.client.get("/weather/history", params={"location": loc, "limit": limit})
        if res and isinstance(res, list):
            return res

        db = SessionLocal()
        try:
            records = WeatherRepository.get_latest(db, location=loc, limit=limit)
            return [
                {
                    "timestamp": r.timestamp.isoformat() if hasattr(r.timestamp, 'isoformat') else str(r.timestamp),
                    "location": r.location,
                    "temperature_c": r.temperature_c,
                    "humidity_pct": r.humidity_pct,
                    "pressure_hpa": r.pressure_hpa,
                    "wind_speed_ms": r.wind_speed_ms,
                    "cloud_cover_pct": r.cloud_cover_pct,
                    "precipitation_mm": r.precipitation_mm,
                    "weather_condition": r.weather_condition,
                    "source": r.source or "Local DB"
                } for r in records
            ]
        except Exception:
            return []
        finally:
            db.close()

    def get_weather_summary(self, location: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Queries /weather/summary endpoint with local repository fallback."""
        loc = location or settings.DEFAULT_LOCATION
        res = self.client.get("/weather/summary", params={"location": loc})
        if res:
            return res

        db = SessionLocal()
        try:
            recs = WeatherRepository.get_latest(db, location=loc, limit=48)
            if recs:
                temps = [r.temperature_c for r in recs]
                hums = [r.humidity_pct for r in recs]
                precips = [r.precipitation_mm for r in recs]
                return {
                    "location": loc,
                    "avg_temperature_c": round(sum(temps) / len(temps), 2),
                    "min_temperature_c": round(min(temps), 2),
                    "max_temperature_c": round(max(temps), 2),
                    "avg_humidity_pct": round(sum(hums) / len(hums), 2),
                    "total_precipitation_mm": round(sum(precips), 2),
                    "latest_condition": recs[0].weather_condition if recs else "Clear",
                    "sample_count": len(recs)
                }
        except Exception:
            pass
        finally:
            db.close()
        return None

