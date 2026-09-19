"""Anomaly Detection API Router."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.backend.api.dependencies import get_database_session, PaginationParams
from app.backend.api.schemas.anomaly import AnomalyDTO, AnomalySummaryDTO
from app.database.repository import AnomalyRepository
from app.services.anomaly_detection_service import AnomalyDetectionService

router = APIRouter(prefix="/anomalies", tags=["Grid Incident & Anomaly Analytics"])


@router.get("", response_model=List[AnomalyDTO], summary="List Filtered Anomaly Incidents")
def get_anomalies(
    severity: Optional[str] = Query(None, description="Filter by severity: CRITICAL, HIGH, MEDIUM, LOW, INFO"),
    variable: Optional[str] = Query(None, description="Filter by variable name e.g. demand_mw, temperature_c"),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_database_session)
):
    """Retrieves detected anomaly incidents filtered by severity or metric variable."""
    # Ensure anomalies exist by executing service run if DB is empty
    anomalies = AnomalyRepository.get_latest(db, limit=pagination.limit)
    if not anomalies:
        service = AnomalyDetectionService()
        service.run_full_detection(save_to_db=True)
        anomalies = AnomalyRepository.get_latest(db, limit=pagination.limit)

    results = []
    for a in anomalies:
        sev = (getattr(a, "severity", "MEDIUM") or "MEDIUM").upper()
        var_name = getattr(a, "variable_name", getattr(a, "metric_name", "demand_mw"))

        if severity and sev != severity.upper():
            continue
        if variable and str(var_name).lower() != variable.lower():
            continue

        results.append(AnomalyDTO(
            id=int(getattr(a, "id")) if getattr(a, "id", None) is not None else None,
            timestamp=a.timestamp.isoformat() if hasattr(a.timestamp, 'isoformat') else str(a.timestamp),
            region=str(getattr(a, "region", settings.DEFAULT_REGION)),
            variable_name=str(var_name),
            observed_value=float(getattr(a, "observed_value", getattr(a, "actual_value", 0.0))),
            expected_value=float(getattr(a, "expected_value", 0.0)),
            deviation=float(getattr(a, "deviation", 0.0)),
            anomaly_score=float(getattr(a, "anomaly_score", getattr(a, "z_score", 0.0))),
            severity=str(sev),
            detection_method=str(getattr(a, "detection_method", "Z-Score / Isolation Forest")),
            reason=str(getattr(a, "reason", getattr(a, "description", "Spike detected")))
        ))

    return results


@router.get("/recent", response_model=List[AnomalyDTO], summary="Recent Unresolved Anomalies")
def get_recent_anomalies(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_database_session)
):
    """Retrieves top N recent anomaly records."""
    pagination = PaginationParams(limit=limit, offset=0)
    return get_anomalies(severity=None, variable=None, pagination=pagination, db=db)


@router.get("/summary", response_model=AnomalySummaryDTO, summary="Anomaly Metric Breakdown")
def get_anomaly_summary(db: Session = Depends(get_database_session)):
    """Computes total counts, severity breakdown, and average anomaly score."""
    anomalies = AnomalyRepository.get_latest(db, limit=100)

    if not anomalies:
        service = AnomalyDetectionService()
        service.run_full_detection(save_to_db=True)
        anomalies = AnomalyRepository.get_latest(db, limit=100)

    if not anomalies:
        return AnomalySummaryDTO(
            total_anomalies=0, critical_count=0, high_count=0,
            medium_count=0, low_count=0, avg_anomaly_score=0.0
        )

    records = [
        ((getattr(a, "severity", "MEDIUM") or "MEDIUM").upper(),
         float(getattr(a, "anomaly_score", getattr(a, "z_score", 0.0))))
        for a in anomalies
    ]

    total = len(records)
    crit = sum(1 for s, _ in records if s == "CRITICAL")
    high = sum(1 for s, _ in records if s == "HIGH")
    med = sum(1 for s, _ in records if s == "MEDIUM")
    low = sum(1 for s, _ in records if s in ["LOW", "INFO"])
    avg_score = sum(score for _, score in records) / total if total > 0 else 0.0

    return AnomalySummaryDTO(
        total_anomalies=total,
        critical_count=crit,
        high_count=high,
        medium_count=med,
        low_count=low,
        avg_anomaly_score=round(avg_score, 2)
    )
