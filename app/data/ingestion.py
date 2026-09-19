"""Data Ingestion Pipeline Orchestrator for Stage 2 Data Ingestion."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.data.providers.open_meteo import OpenMeteoWeatherProvider
from app.data.providers.open_energy import OpenEnergyProvider
from app.data.validator import DataValidator, DataQualityReport
from app.database.repository import WeatherRepository, EnergyRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BaseDataIngestor(ABC):
    """Abstract interface for weather and energy data ingestors (Stage 1 backward compatibility)."""

    @abstractmethod
    def fetch_weather_data(self, location: str, start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """Fetch weather observations dataframe."""
        pass

    @abstractmethod
    def fetch_energy_data(self, region: str, start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """Fetch energy demand observations dataframe."""
        pass


class SyntheticDataIngestor(BaseDataIngestor):
    """Fallback synthetic data generator for UI & backend testing."""

    def fetch_weather_data(self, location: str, start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """Generates realistic structured weather time-series data."""
        timestamps = pd.date_range(start=start_time, end=end_time, freq="1h")
        n = len(timestamps)

        if n == 0:
            return pd.DataFrame(columns=[
                "timestamp", "location", "temperature_c", "humidity_pct",
                "pressure_hpa", "wind_speed_ms", "cloud_cover_pct", "precipitation_mm"
            ])

        hours = timestamps.hour
        base_temp = 20.0 + 8.0 * np.sin((hours - 8) * np.pi / 12) + np.random.normal(0, 1.5, n)
        humidity = 60.0 - 15.0 * np.sin((hours - 8) * np.pi / 12) + np.random.normal(0, 3.0, n)
        humidity = np.clip(humidity, 10.0, 100.0)

        df = pd.DataFrame({
            "timestamp": timestamps,
            "location": location,
            "temperature_c": np.round(base_temp, 2),
            "humidity_pct": np.round(humidity, 2),
            "pressure_hpa": np.round(1013.25 + np.random.normal(0, 4, n), 2),
            "wind_speed_ms": np.round(np.abs(3.5 + np.random.normal(0, 2, n)), 2),
            "cloud_cover_pct": np.round(np.clip(40.0 + np.random.normal(0, 25, n), 0, 100), 2),
            "precipitation_mm": np.round(np.clip(np.random.choice([0.0, 0.5, 2.0, 5.0], size=n, p=[0.8, 0.1, 0.07, 0.03]), 0, 50), 2)
        })
        return df

    def fetch_energy_data(self, region: str, start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """Generates realistic energy demand time-series data."""
        timestamps = pd.date_range(start=start_time, end=end_time, freq="1h")
        n = len(timestamps)

        if n == 0:
            return pd.DataFrame(columns=["timestamp", "region", "demand_mw", "peak_demand_flag"])

        hours = timestamps.hour
        load_curve = 2500 + 800 * np.sin((hours - 4) * np.pi / 12) + 400 * np.cos((hours - 14) * np.pi / 6)
        noise = np.random.normal(0, 80, n)
        demand = load_curve + noise

        df = pd.DataFrame({
            "timestamp": timestamps,
            "region": region,
            "demand_mw": np.round(demand, 2),
            "peak_demand_flag": demand > 3200
        })
        return df


class PipelineSummaryReport(BaseModel):
    """Consolidated summary report schema for ingestion pipeline runs."""
    weather_received: int = 0
    weather_valid: int = 0
    weather_invalid: int = 0
    weather_inserted: int = 0
    weather_duplicates: int = 0

    energy_received: int = 0
    energy_valid: int = 0
    energy_invalid: int = 0
    energy_inserted: int = 0
    energy_duplicates: int = 0


class DataIngestionService:
    """Orchestrates data fetching, quality validation, and database upsert persistence."""

    def __init__(self, weather_provider=None, energy_provider=None):
        self.weather_provider = weather_provider or OpenMeteoWeatherProvider()
        self.energy_provider = energy_provider or OpenEnergyProvider()

    def ingest_weather(
        self,
        db: Session,
        location: str = "London",
        latitude: float = 51.5074,
        longitude: float = -0.1278,
        mode: str = "current"
    ) -> Tuple[DataQualityReport, int, int]:
        """Runs weather data ingestion pipeline."""
        logger.info(f"Starting weather data ingestion for location={location} (mode={mode})...")

        if mode == "current":
            raw_records = self.weather_provider.fetch_current_weather(
                location=location, latitude=latitude, longitude=longitude
            )
        else:
            raw_records = self.weather_provider.fetch_historical_weather(
                location=location, latitude=latitude, longitude=longitude
            )

        valid_records, quality_report = DataValidator.validate_weather_batch(raw_records)

        inserted_count, duplicate_count = 0, 0
        if valid_records and db is not None:
            inserted_count, duplicate_count = WeatherRepository.upsert_weather_records(db, valid_records)

        quality_report.duplicate_count = duplicate_count
        logger.info(
            f"Weather Ingestion Finished: Received {quality_report.total_records}, Valid {quality_report.valid_count}, "
            f"Inserted {inserted_count}, Duplicates {duplicate_count}"
        )
        return quality_report, inserted_count, duplicate_count

    def ingest_energy(
        self,
        db: Session,
        region: str = "Grid_Alpha"
    ) -> Tuple[DataQualityReport, int, int]:
        """Runs energy load data ingestion pipeline."""
        logger.info(f"Starting energy load data ingestion for region={region}...")

        raw_records = self.energy_provider.fetch_energy_demand(region=region)
        valid_records, quality_report = DataValidator.validate_energy_batch(raw_records)

        inserted_count, duplicate_count = 0, 0
        if valid_records and db is not None:
            inserted_count, duplicate_count = EnergyRepository.upsert_energy_records(db, valid_records)

        quality_report.duplicate_count = duplicate_count
        logger.info(
            f"Energy Ingestion Finished: Received {quality_report.total_records}, Valid {quality_report.valid_count}, "
            f"Inserted {inserted_count}, Duplicates {duplicate_count}"
        )
        return quality_report, inserted_count, duplicate_count

    def run_pipeline(
        self,
        db: Session,
        location: str = "London",
        latitude: float = 51.5074,
        longitude: float = -0.1278,
        region: str = "Grid_Alpha"
    ) -> PipelineSummaryReport:
        """Runs full ingestion pipeline for weather and energy streams."""
        w_report, w_inserted, w_dups = self.ingest_weather(db, location=location, latitude=latitude, longitude=longitude)
        e_report, e_inserted, e_dups = self.ingest_energy(db, region=region)

        return PipelineSummaryReport(
            weather_received=w_report.total_records,
            weather_valid=w_report.valid_count,
            weather_invalid=w_report.invalid_count,
            weather_inserted=w_inserted,
            weather_duplicates=w_dups,
            energy_received=e_report.total_records,
            energy_valid=e_report.valid_count,
            energy_invalid=e_report.invalid_count,
            energy_inserted=e_inserted,
            energy_duplicates=e_dups
        )
