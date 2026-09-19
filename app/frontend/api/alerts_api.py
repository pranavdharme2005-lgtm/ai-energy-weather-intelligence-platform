"""Smart Alert Center REST API Client wrapper."""

from typing import Dict, Any, List, Optional
from app.frontend.api.client import BaseAPIClient
from app.database.session import SessionLocal
from app.database.repository import AlertRepository


class AlertsAPIClient:
    """API Client for Smart Alert Center endpoints with fallback to repository."""

    def __init__(self, base_client: BaseAPIClient):
        self.client = base_client

    def get_alerts(self, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Queries /alerts endpoint."""
        params = {"limit": limit}
        if status:
            params["status"] = status
        res = self.client.get("/alerts", params=params)
        if res and isinstance(res, list):
            return res

        # Check legacy /alerts/active endpoint fallback
        if status == "ACTIVE":
            active_res = self.client.get("/alerts/active")
            if active_res and isinstance(active_res, list):
                return active_res

        db = SessionLocal()
        try:
            records = AlertRepository.get_all(db, status=status, limit=limit)
            return [
                {
                    "id": r.id,
                    "title": r.title,
                    "message": r.message,
                    "severity": r.severity.value if hasattr(r.severity, 'value') else str(r.severity),
                    "category": r.category.value if hasattr(r.category, 'value') else str(r.category),
                    "status": r.status.value if hasattr(r.status, 'value') else str(r.status),
                    "timestamp": r.timestamp.isoformat() if hasattr(r.timestamp, 'isoformat') else str(r.timestamp),
                    "acknowledged_at": r.acknowledged_at.isoformat() if r.acknowledged_at and hasattr(r.acknowledged_at, 'isoformat') else None,
                    "resolved_at": r.resolved_at.isoformat() if r.resolved_at and hasattr(r.resolved_at, 'isoformat') else None,
                } for r in records
            ]
        except Exception:
            return []
        finally:
            db.close()

    def get_alert_summary(self) -> Optional[Dict[str, Any]]:
        """Queries /alerts/summary endpoint."""
        return self.client.get("/alerts/summary")

    def acknowledge_alert(self, alert_id: int) -> bool:
        """Posts to /alerts/{alert_id}/acknowledge endpoint."""
        res = self.client.post(f"/alerts/{alert_id}/acknowledge")
        if res is not None:
            return True

        db = SessionLocal()
        try:
            acc = AlertRepository.acknowledge(db, alert_id)
            return acc is not None
        except Exception:
            return False
        finally:
            db.close()

    def resolve_alert(self, alert_id: int) -> bool:
        """Posts to /alerts/{alert_id}/resolve endpoint."""
        res = self.client.post(f"/alerts/{alert_id}/resolve")
        if res is not None:
            return True

        db = SessionLocal()
        try:
            res_item = AlertRepository.resolve(db, alert_id)
            return res_item is not None
        except Exception:
            return False
        finally:
            db.close()
