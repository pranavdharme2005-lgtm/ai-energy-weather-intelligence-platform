"""Smart Alert Center API Router."""

from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.backend.api.dependencies import get_database_session, PaginationParams
from app.backend.api.schemas.alert import AlertDTO, AcknowledgeAlertRequest, ResolveAlertRequest, AlertSummaryDTO
from app.services.alert_service import SmartAlertService
from app.database.repository import AlertRepository

router = APIRouter(prefix="/alerts", tags=["Smart Alert Center"])


def _model_to_alert_dto(r) -> AlertDTO:
    """Helper converting Alert ORM model to AlertDTO."""
    return AlertDTO(
        id=int(r.id),
        alert_type=str(r.alert_type or "System Alert"),
        severity=str(r.severity or "INFO").upper(),
        status=str(r.status or "ACTIVE").upper(),
        timestamp=r.timestamp.isoformat() if hasattr(r.timestamp, 'isoformat') else str(r.timestamp),
        region=str(r.region or settings.DEFAULT_REGION),
        title=str(r.title or "Alert"),
        message=str(r.message or ""),
        reason=str(r.reason or ""),
        observed_value=float(r.observed_value) if r.observed_value is not None else None,
        expected_value=float(r.expected_value) if r.expected_value is not None else None,
        fingerprint=str(r.alert_id) if r.alert_id else None,
        occurrence_count=int(getattr(r, "occurrence_count", 1) or 1),
        ai_explanation=None
    )


@router.get("", response_model=List[AlertDTO], summary="List Filtered Alerts")
def get_alerts(
    status: Optional[str] = Query(None, description="Filter status: ACTIVE, ACKNOWLEDGED, RESOLVED"),
    severity: Optional[str] = Query(None, description="Filter severity: CRITICAL, HIGH, MEDIUM, LOW, INFO"),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_database_session)
):
    """Retrieves alert records from database filtered by status or severity."""
    records = AlertRepository.get_recent_alerts(db, limit=pagination.limit)

    results = []
    for r in records:
        st_val = str(r.status or "ACTIVE").upper()
        sev_val = str(r.severity or "INFO").upper()

        if status and st_val != status.upper():
            continue
        if severity and sev_val != severity.upper():
            continue

        results.append(_model_to_alert_dto(r))

    return results


@router.get("/active", response_model=List[AlertDTO], summary="Active Unresolved Alerts")
def get_active_alerts(db: Session = Depends(get_database_session)):
    """Retrieves all active un-resolved alerts."""
    records = AlertRepository.get_active_alerts(db, region=settings.DEFAULT_REGION)
    return [_model_to_alert_dto(r) for r in records]


@router.get("/history", response_model=List[AlertDTO], summary="Historical Alert Audit Trail")
def get_alert_history(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_database_session)
):
    """Retrieves historical alerts audit trail."""
    return get_alerts(status=None, severity=None, pagination=pagination, db=db)


@router.get("/summary", response_model=AlertSummaryDTO, summary="Alert Engine Summary Metrics")
def get_alert_summary(db: Session = Depends(get_database_session)):
    """Calculates active alert counts, resolved counts, and severity breakdown."""
    service = SmartAlertService(db)
    summary_obj = service.get_alert_summary(region=settings.DEFAULT_REGION)

    sev_breakdown = summary_obj.severity_breakdown if hasattr(summary_obj, 'severity_breakdown') else {}
    return AlertSummaryDTO(
        total_persisted=int(getattr(summary_obj, 'total_alerts_persisted', 0)),
        active_count=int(getattr(summary_obj, 'active_alerts_count', 0)),
        acknowledged_count=int(getattr(summary_obj, 'acknowledged_alerts_count', 0)),
        resolved_count=int(getattr(summary_obj, 'resolved_alerts_count', 0)),
        critical_count=int(sev_breakdown.get("CRITICAL", 0)),
        high_count=int(sev_breakdown.get("HIGH", 0))
    )


@router.post("/{alert_id}/acknowledge", response_model=AlertDTO, summary="Acknowledge Alert State Transition")
def acknowledge_alert(
    alert_id: int = Path(..., ge=1, description="Target Alert Record ID"),
    body: Optional[AcknowledgeAlertRequest] = None,
    db: Session = Depends(get_database_session)
):
    """Transitions alert status from ACTIVE to ACKNOWLEDGED."""
    service = SmartAlertService(db)
    success = service.acknowledge_alert(alert_db_id=alert_id)
    
    # Retrieve updated alert ORM record
    from app.database.models import Alert
    updated = db.query(Alert).filter(Alert.id == alert_id).first()
    if not updated and not success:
        raise HTTPException(status_code=404, detail=f"Alert record #{alert_id} not found.")

    if updated:
        return _model_to_alert_dto(updated)

    raise HTTPException(status_code=404, detail=f"Alert record #{alert_id} not found.")


@router.post("/{alert_id}/resolve", response_model=AlertDTO, summary="Resolve Alert State Transition")
def resolve_alert(
    alert_id: int = Path(..., ge=1, description="Target Alert Record ID"),
    body: Optional[ResolveAlertRequest] = None,
    db: Session = Depends(get_database_session)
):
    """Transitions alert status from ACTIVE/ACKNOWLEDGED to RESOLVED."""
    service = SmartAlertService(db)
    success = service.resolve_alert(alert_db_id=alert_id)
    
    from app.database.models import Alert
    updated = db.query(Alert).filter(Alert.id == alert_id).first()
    if not updated and not success:
        raise HTTPException(status_code=404, detail=f"Alert record #{alert_id} not found.")

    if updated:
        return _model_to_alert_dto(updated)

    raise HTTPException(status_code=404, detail=f"Alert record #{alert_id} not found.")
