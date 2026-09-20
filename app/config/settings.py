"""Centralized Application Configuration System."""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

CITY_COORDINATES = {
    "Mumbai": {"latitude": 19.0760, "longitude": 72.8777, "country": "India"},
    "Pune": {"latitude": 18.5204, "longitude": 73.8567, "country": "India"},
    "Nagpur": {"latitude": 21.1458, "longitude": 79.0882, "country": "India"},
    "Delhi": {"latitude": 28.6139, "longitude": 77.2090, "country": "India"},
    "Bengaluru": {"latitude": 12.9716, "longitude": 77.5946, "country": "India"},
    "Hyderabad": {"latitude": 17.3850, "longitude": 78.4867, "country": "India"},
    "Chennai": {"latitude": 13.0827, "longitude": 80.2707, "country": "India"},
    "London": {"latitude": 51.5074, "longitude": -0.1278, "country": "UK"},
    "New York": {"latitude": 40.7128, "longitude": -74.0060, "country": "USA"},
    "Tokyo": {"latitude": 35.6762, "longitude": 139.6503, "country": "Japan"}
}

SUPPORTED_LOCATIONS = list(CITY_COORDINATES.keys())


class Settings(BaseSettings):
    """Centralized configuration reading environment variables with sensible defaults."""

    # Application Configuration
    APP_NAME: str = "AI-Powered Energy Intelligence & Weather Analytics Platform"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    STREAMLIT_PORT: int = 8501
    API_PREFIX: str = "/api/v1"
    API_BASE_URL: str = ""
    CORS_ALLOWED_ORIGINS: str = "http://localhost:8501,http://127.0.0.1:8501"
    LOG_LEVEL: str = "INFO"

    # Database Configuration (Defaults to local SQLite to prevent unreachable localhost PostgreSQL connection attempts)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///energy_intelligence.db")

    # Weather API Configuration (Open-Meteo as high-accuracy open default)
    WEATHER_API_BASE_URL: str = "https://api.open-meteo.com/v1/forecast"
    WEATHER_API_KEY: Optional[str] = None

    # Energy API Configuration
    ENERGY_API_BASE_URL: str = "https://api.eia.gov/v2/"
    ENERGY_API_KEY: Optional[str] = None

    # Default Region & Meteorological Coordinates (Mumbai as primary neutral default)
    DEFAULT_LOCATION: str = "Mumbai"
    DEFAULT_LATITUDE: float = 19.0760
    DEFAULT_LONGITUDE: float = 72.8777
    DEFAULT_REGION: str = "Grid_Alpha"

    # Data Ingestion Resilience & Retry Parameters
    INGESTION_RETRY_ATTEMPTS: int = 3
    INGESTION_TIMEOUT_SECONDS: int = 10

    # AI / LLM Configuration
    AI_PROVIDER: str = "openai"  # openai, mock, or fallback
    AI_API_KEY: Optional[str] = None
    AI_MODEL: str = "gpt-4o-mini"
    AI_MAX_TOKENS: int = 500
    AI_TEMPERATURE: float = 0.2
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-4o-mini"

    # Data Refresh Configuration (in seconds)
    DATA_REFRESH_INTERVAL_SECONDS: int = 300

    # Smart Alert Center Thresholds & Parameters
    ALERT_COOLDOWN_MINUTES: int = 30
    ALERT_PERSISTENCE_COUNT: int = 2
    ENERGY_SPIKE_THRESHOLD_MW: float = 3500.0
    ENERGY_DROP_THRESHOLD_MW: float = 1500.0
    FORECAST_DEVIATION_THRESHOLD_PCT: float = 15.0
    RAIN_ALERT_THRESHOLD_PCT: float = 60.0
    EXTREME_TEMP_HIGH_C: float = 35.0
    EXTREME_TEMP_LOW_C: float = 0.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
