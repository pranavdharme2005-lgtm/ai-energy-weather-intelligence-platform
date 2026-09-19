"""Anomaly Detection REST API Client wrapper."""

from typing import Dict, Any, List, Optional
from app.frontend.api.client import BaseAPIClient
from app.config.settings import settings
from app.services.anomaly_detection_service import AnomalyDetectionService
from app.database.session import SessionLocal


class AnomaliesAPIClient:
    """API Client for Anomaly Detection endpoints with fallback to service."""

    def __init__(self, base_client: BaseAPIClient):
        self.client = base_client

    def detect_anomalies(self, region: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Queries /anomalies/detect endpoint."""
        reg = region or settings.DEFAULT_REGION
        res = self.client.get("/anomalies/detect", params={"region": reg})
        if res:
            return res

        db = SessionLocal()
        try:
            svc = AnomalyDetectionService(db)
            return svc.detect_and_store_anomalies(limit=100)
        except Exception:
            return None
        finally:
            db.close()

    def get_recent_anomalies(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Queries /anomalies/recent endpoint."""
        res = self.client.get("/anomalies/recent", params={"limit": limit})
        if res and isinstance(res, list):
            return res

        db = SessionLocal()
        try:
            svc = AnomalyDetectionService(db)
            records = svc.get_recent_anomalies(limit=limit)
            results = []
            for a in records:
                results.append({
                    "id": getattr(a, "id", None),
                    "timestamp": a.timestamp.isoformat() if hasattr(a.timestamp, 'isoformat') else str(a.timestamp),
                    "variable_name": getattr(a, "variable_name", getattr(a, "metric_name", "demand_mw")),
                    "severity": getattr(a, "severity", "MEDIUM"),
                    "observed_value": getattr(a, "observed_value", getattr(a, "actual_value", 0.0)),
                    "expected_value": getattr(a, "expected_value", 0.0),
                    "deviation": getattr(a, "deviation", 0.0),
                    "anomaly_score": getattr(a, "anomaly_score", getattr(a, "z_score", 0.0)),
                    "detection_method": getattr(a, "detection_method", "Z-Score / Isolation Forest"),
                    "reason": getattr(a, "reason", getattr(a, "description", "Spike detected"))
                })
            return results
        except Exception:
            return []
        finally:
            db.close()
