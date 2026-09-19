"""Automated Unit and Integration Tests for Stage 2 Ingestion Pipeline."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.models import Base, WeatherData, EnergyData
from app.database.repository import WeatherRepository, EnergyRepository
from app.data.providers.open_meteo import OpenMeteoWeatherProvider
from app.data.providers.open_energy import OpenEnergyProvider
from app.data.validator import DataValidator
from app.data.ingestion import DataIngestionService


@pytest.fixture
def db_session():
    """In-memory SQLite DB session fixture for isolated repository testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_open_meteo_parser_mock():
    """Test Open-Meteo API response parsing logic with mock API JSON response."""
    provider = OpenMeteoWeatherProvider()
    mock_payload = {
        "current": {
            "time": "2026-09-19T12:00",
            "temperature_2m": 22.4,
            "relative_humidity_2m": 58.0,
            "surface_pressure": 1014.5,
            "wind_speed_10m": 4.2,
            "cloud_cover": 20.0,
            "precipitation": 0.0,
            "weather_code": 1
        }
    }

    parsed = provider._parse_current_record(mock_payload, "London", 51.5074, -0.1278)

    assert parsed["location"] == "London"
    assert parsed["temperature_c"] == 22.4
    assert parsed["humidity_pct"] == 58.0
    assert parsed["weather_condition"] == "Mainly clear"
    assert parsed["source"] == "Open-Meteo-API"
    assert parsed["timestamp"].tzinfo == timezone.utc


def test_open_energy_parser():
    """Test Open Energy Provider load record parsing."""
    provider = OpenEnergyProvider()
    now = datetime.now(timezone.utc)
    records = provider.fetch_energy_demand(region="Grid_Alpha", start_time=now - timedelta(hours=3), end_time=now)

    assert len(records) >= 3
    assert records[0]["region"] == "Grid_Alpha"
    assert "demand_mw" in records[0]
    assert records[0]["source"] == "PJM_OpenData_Historical"


def test_data_validator_bounds():
    """Test DataValidator with physical bounds and out-of-range values."""
    valid_weather = {
        "timestamp": datetime.now(timezone.utc),
        "location": "London",
        "temperature_c": 25.0,
        "humidity_pct": 50.0,
        "pressure_hpa": 1013.25,
        "wind_speed_ms": 3.0,
        "precipitation_mm": 0.0
    }
    is_valid, issues = DataValidator.validate_weather_record(valid_weather)
    assert is_valid is True
    assert len(issues) == 0

    # Test out-of-bounds temperature (-100 °C)
    invalid_weather = valid_weather.copy()
    invalid_weather["temperature_c"] = -100.0
    is_valid_inv, issues_inv = DataValidator.validate_weather_record(invalid_weather)
    assert is_valid_inv is False
    assert any("Temperature" in i for i in issues_inv)


def test_duplicate_prevention(db_session):
    """Test repository duplicate record prevention ON CONFLICT behavior."""
    now = datetime.now(timezone.utc)
    record = {
        "timestamp": now,
        "location": "London",
        "latitude": 51.5074,
        "longitude": -0.1278,
        "temperature_c": 20.0,
        "humidity_pct": 60.0,
        "pressure_hpa": 1013.0,
        "wind_speed_ms": 4.0,
        "source": "Open-Meteo-API"
    }

    # First insert
    inserted1, dups1 = WeatherRepository.upsert_weather_records(db_session, [record])
    assert inserted1 == 1
    assert dups1 == 0

    # Second insert with identical location, timestamp, and source
    inserted2, dups2 = WeatherRepository.upsert_weather_records(db_session, [record])
    assert inserted2 == 0
    assert dups2 == 1


def test_utc_timestamp_strategy():
    """Verify timestamps are normalized with UTC timezone awareness."""
    now_utc = datetime.now(timezone.utc)
    provider = OpenEnergyProvider()
    records = provider.fetch_energy_demand("Grid_Alpha", start_time=now_utc - timedelta(hours=1), end_time=now_utc)
    assert records[0]["timestamp"].tzinfo == timezone.utc


@patch("httpx.Client.get")
def test_open_meteo_retry_handling(mock_get):
    """Test retry policy handles temporary HTTP network failures gracefully."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = RuntimeError("Internal Server Error")
    mock_get.return_value = mock_response

    provider = OpenMeteoWeatherProvider(retries=2, timeout=1)

    with pytest.raises(RuntimeError) as exc_info:
        provider.fetch_current_weather("London", 51.5074, -0.1278)

    assert "failed" in str(exc_info.value).lower()
    assert mock_get.call_count == 2
