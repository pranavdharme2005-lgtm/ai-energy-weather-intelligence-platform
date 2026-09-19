"""Open-Meteo Weather API Provider Implementation with Retries and Schema Normalization."""

import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx

from app.config.settings import settings
from app.data.providers.base import WeatherProvider
from app.utils.logger import get_logger

logger = get_logger(__name__)

WMO_CODE_MAP = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail"
}


class OpenMeteoWeatherProvider(WeatherProvider):
    """Concrete provider fetching live and historical meteorological data from Open-Meteo API."""

    def __init__(self, base_url: Optional[str] = None, timeout: int = 10, retries: int = 3):
        self.base_url = base_url or settings.WEATHER_API_BASE_URL
        self.timeout = timeout or settings.INGESTION_TIMEOUT_SECONDS
        self.retries = retries or settings.INGESTION_RETRY_ATTEMPTS

    def _execute_request_with_retry(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Executes HTTP GET request to Open-Meteo API with exponential backoff retries."""
        last_exception = None
        for attempt in range(1, self.retries + 1):
            try:
                logger.info(f"Open-Meteo API Request Attempt {attempt}/{self.retries} to {self.base_url}")
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(self.base_url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    logger.info("Open-Meteo API Request successful.")
                    return data
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt} failed with error: {e}")
                if attempt < self.retries:
                    time.sleep(2 ** (attempt - 1))  # Exponential backoff: 1s, 2s, 4s...

        logger.error(f"Open-Meteo API failed after {self.retries} attempts.")
        raise RuntimeError(f"Open-Meteo Weather API request failed: {last_exception}")

    def fetch_current_weather(
        self, location: str = "London", latitude: float = 51.5074, longitude: float = -0.1278
    ) -> List[Dict[str, Any]]:
        """Fetches current weather telemetry from Open-Meteo API."""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,cloud_cover,precipitation,weather_code",
            "timezone": "UTC"
        }

        raw_data = self._execute_request_with_retry(params)
        return [self._parse_current_record(raw_data, location, latitude, longitude)]

    def fetch_historical_weather(
        self, location: str = "London", latitude: float = 51.5074, longitude: float = -0.1278,
        start_time: Optional[datetime] = None, end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Fetches hourly weather forecast/historical telemetry from Open-Meteo API."""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,cloud_cover,precipitation,weather_code",
            "timezone": "UTC",
            "forecast_days": 1
        }

        raw_data = self._execute_request_with_retry(params)
        return self._parse_hourly_records(raw_data, location, latitude, longitude)

    def _parse_current_record(
        self, raw: Dict[str, Any], location: str, lat: float, lon: float
    ) -> Dict[str, Any]:
        """Parses current weather raw payload into normalized schema record."""
        current = raw.get("current", {})
        ts_str = current.get("time")

        if ts_str:
            ts = datetime.fromisoformat(ts_str.replace("Z", "")).replace(tzinfo=timezone.utc)
        else:
            ts = datetime.now(timezone.utc)

        w_code = current.get("weather_code", 0)
        condition = WMO_CODE_MAP.get(w_code, "Clear")

        return {
            "timestamp": ts,
            "location": location,
            "latitude": lat,
            "longitude": lon,
            "temperature_c": round(float(current.get("temperature_2m", 20.0)), 2),
            "humidity_pct": round(float(current.get("relative_humidity_2m", 60.0)), 2),
            "pressure_hpa": round(float(current.get("surface_pressure", 1013.25)), 2),
            "wind_speed_ms": round(float(current.get("wind_speed_10m", 3.5)), 2),
            "cloud_cover_pct": round(float(current.get("cloud_cover", 0.0)), 2),
            "precipitation_mm": round(float(current.get("precipitation", 0.0)), 2),
            "weather_condition": condition,
            "source": "Open-Meteo-API"
        }

    def _parse_hourly_records(
        self, raw: Dict[str, Any], location: str, lat: float, lon: float
    ) -> List[Dict[str, Any]]:
        """Parses hourly weather array raw payload into normalized schema records."""
        hourly = raw.get("hourly", {})
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        humids = hourly.get("relative_humidity_2m", [])
        pressures = hourly.get("surface_pressure", [])
        winds = hourly.get("wind_speed_10m", [])
        clouds = hourly.get("cloud_cover", [])
        precips = hourly.get("precipitation", [])
        w_codes = hourly.get("weather_code", [])

        records = []
        for i in range(len(times)):
            ts_str = times[i]
            ts = datetime.fromisoformat(ts_str.replace("Z", "")).replace(tzinfo=timezone.utc)
            w_code = w_codes[i] if i < len(w_codes) else 0

            records.append({
                "timestamp": ts,
                "location": location,
                "latitude": lat,
                "longitude": lon,
                "temperature_c": round(float(temps[i]), 2) if i < len(temps) and temps[i] is not None else 20.0,
                "humidity_pct": round(float(humids[i]), 2) if i < len(humids) and humids[i] is not None else 50.0,
                "pressure_hpa": round(float(pressures[i]), 2) if i < len(pressures) and pressures[i] is not None else 1013.25,
                "wind_speed_ms": round(float(winds[i]), 2) if i < len(winds) and winds[i] is not None else 2.5,
                "cloud_cover_pct": round(float(clouds[i]), 2) if i < len(clouds) and clouds[i] is not None else 0.0,
                "precipitation_mm": round(float(precips[i]), 2) if i < len(precips) and precips[i] is not None else 0.0,
                "weather_condition": WMO_CODE_MAP.get(w_code, "Clear"),
                "source": "Open-Meteo-API"
            })

        return records
