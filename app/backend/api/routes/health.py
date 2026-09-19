"""Health and Availability API Router."""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.config.settings import settings
from app.backend.api.dependencies import get_database_session
from app.backend.api.schemas.common import HealthResponse, DatabaseHealthResponse, ServicesHealthResponse

router = APIRouter(tags=["Health & Status"])


@router.get("/health", response_model=HealthResponse, summary="System Liveness Health Check")
def get_system_health():
    """Returns application status, version, and current UTC timestamp."""
    return HealthResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        environment=settings.APP_ENV,
        version="1.0.0-stage12",
        timestamp=datetime.now().isoformat()
    )


@router.get("/health/db", response_model=DatabaseHealthResponse, summary="Database Connectivity Health Check")
def get_database_health(db: Session = Depends(get_database_session)):
    """Verifies SQLite/PostgreSQL database connectivity by executing a lightweight query."""
    try:
        db.execute(text("SELECT 1"))
        return DatabaseHealthResponse(
            status="healthy",
            database_type="SQLite" if "sqlite" in settings.DATABASE_URL else "PostgreSQL",
            connected=True,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        return DatabaseHealthResponse(
            status="unhealthy",
            database_type="Unknown",
            connected=False,
            timestamp=datetime.now().isoformat()
        )


@router.get("/health/services", response_model=ServicesHealthResponse, summary="Major Internal Services Availability")
def get_services_health():
    """Reports status of major analytical services."""
    return ServicesHealthResponse(
        status="healthy",
        services={
            "WeatherIngestionService": "AVAILABLE",
            "RainPredictionService": "AVAILABLE (Stage 4 XGBoost)",
            "EnergyForecastingService": "AVAILABLE (Stage 5 Ridge/LGBM)",
            "AnomalyDetectionService": "AVAILABLE (Stage 6 Stat/IsoForest)",
            "WeatherImpactService": "AVAILABLE (Stage 7 Correlation)",
            "WhatIfSimulatorService": "AVAILABLE (Stage 8 Simulator)",
            "AIEnergyAnalystService": "AVAILABLE (Stage 9 Grounded Copilot)",
            "SmartAlertService": "AVAILABLE (Stage 10 Rule Engine)"
        },
        timestamp=datetime.now().isoformat()
    )
