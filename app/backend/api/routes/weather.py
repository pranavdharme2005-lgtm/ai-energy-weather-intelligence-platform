"""Weather Telemetry API Router."""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.backend.api.dependencies import get_database_session, PaginationParams
from app.backend.api.schemas.weather import WeatherDataDTO, WeatherSummaryDTO
from app.database.repository import WeatherRepository
from app.data.ingestion import SyntheticDataIngestor

router = APIRouter(prefix="/weather", tags=["Weather Telemetry"])
ingestor = SyntheticDataIngestor()


@router.get("/current", response_model=WeatherDataDTO, summary="Current Weather Telemetry")
def get_current_weather(
    location: str = Query(default=settings.DEFAULT_LOCATION, description="Target location/station name"),
    db: Session = Depends(get_database_session)
):
    """Retrieves latest ambient weather telemetry for specified location."""
    records = WeatherRepository.get_latest(db, location=location, limit=1)
    if records:
        r = records[0]
        return WeatherDataDTO(
            timestamp=r.timestamp.isoformat() if hasattr(r.timestamp, 'isoformat') else str(r.timestamp),
            location=r.location,
            temperature_c=r.temperature_c,
            humidity_pct=r.humidity_pct,
            pressure_hpa=r.pressure_hpa,
            wind_speed_ms=r.wind_speed_ms,
            cloud_cover_pct=r.cloud_cover_pct,
            precipitation_mm=r.precipitation_mm,
            weather_condition=r.weather_condition,
            latitude=r.latitude,
            longitude=r.longitude,
            source=r.source
        )

    # Fallback to ingestion provider if DB lacks records for this location
    now = datetime.now()
    df = ingestor.fetch_weather_data(location=location, start_time=now - timedelta(hours=1), end_time=now)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No weather observations found for location '{location}'.")

    row = df.iloc[-1].to_dict()
    return WeatherDataDTO(
        timestamp=str(row.get("timestamp", now.isoformat())),
        location=location,
        temperature_c=float(row.get("temperature_c", 22.0)),
        humidity_pct=float(row.get("humidity_pct", 55.0)),
        pressure_hpa=float(row.get("pressure_hpa", 1013.25)),
        wind_speed_ms=float(row.get("wind_speed_ms", 4.0)),
        cloud_cover_pct=float(row.get("cloud_cover_pct", 20.0)),
        precipitation_mm=float(row.get("precipitation_mm", 0.0)),
        weather_condition=str(row.get("weather_condition", "Clear")),
        latitude=row.get("latitude"),
        longitude=row.get("longitude"),
        source="Open-Meteo-API"
    )


@router.get("/history", response_model=List[WeatherDataDTO], summary="Historical Weather Telemetry Feed")
def get_weather_history(
    location: str = Query(default=settings.DEFAULT_LOCATION, description="Target location/station name"),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_database_session)
):
    """Retrieves recent historical weather telemetry records."""
    records = WeatherRepository.get_latest(db, location=location, limit=pagination.limit)
    if records:
        return [
            WeatherDataDTO(
                timestamp=r.timestamp.isoformat() if hasattr(r.timestamp, 'isoformat') else str(r.timestamp),
                location=r.location,
                temperature_c=r.temperature_c,
                humidity_pct=r.humidity_pct,
                pressure_hpa=r.pressure_hpa,
                wind_speed_ms=r.wind_speed_ms,
                cloud_cover_pct=r.cloud_cover_pct,
                precipitation_mm=r.precipitation_mm,
                weather_condition=r.weather_condition,
                latitude=r.latitude,
                longitude=r.longitude,
                source=r.source
            ) for r in records
        ]

    # Fallback to ingestion feed
    now = datetime.now()
    df = ingestor.fetch_weather_data(location=location, start_time=now - timedelta(hours=pagination.limit), end_time=now)
    results = []
    for _, row in df.iterrows():
        results.append(WeatherDataDTO(
            timestamp=str(row["timestamp"]),
            location=location,
            temperature_c=float(row["temperature_c"]),
            humidity_pct=float(row["humidity_pct"]),
            pressure_hpa=float(row["pressure_hpa"]),
            wind_speed_ms=float(row["wind_speed_ms"]),
            cloud_cover_pct=float(row.get("cloud_cover_pct", 0.0)),
            precipitation_mm=float(row.get("precipitation_mm", 0.0)),
            weather_condition=str(row.get("weather_condition", "Clear")),
            latitude=row.get("latitude"),
            longitude=row.get("longitude"),
            source="Open-Meteo-API"
        ))
    return results


@router.get("/summary", response_model=WeatherSummaryDTO, summary="Aggregated Weather Summary Analytics")
def get_weather_summary(
    location: str = Query(default=settings.DEFAULT_LOCATION, description="Target location/station name"),
    db: Session = Depends(get_database_session)
):
    """Computes summary statistics across recent weather observations."""
    records = WeatherRepository.get_latest(db, location=location, limit=48)
    if not records:
        # Fallback to current weather check
        curr = get_current_weather(location=location, db=db)
        return WeatherSummaryDTO(
            location=location,
            avg_temperature_c=curr.temperature_c,
            max_temperature_c=curr.temperature_c,
            min_temperature_c=curr.temperature_c,
            avg_humidity_pct=curr.humidity_pct,
            total_precipitation_mm=curr.precipitation_mm,
            latest_condition=curr.weather_condition,
            records_analyzed=1
        )

    temps = [r.temperature_c for r in records]
    humids = [r.humidity_pct for r in records]
    precips = [r.precipitation_mm for r in records]

    return WeatherSummaryDTO(
        location=location,
        avg_temperature_c=round(sum(temps) / len(temps), 2),
        max_temperature_c=round(max(temps), 2),
        min_temperature_c=round(min(temps), 2),
        avg_humidity_pct=round(sum(humids) / len(humids), 2),
        total_precipitation_mm=round(sum(precips), 2),
        latest_condition=records[0].weather_condition,
        records_analyzed=len(records)
    )
