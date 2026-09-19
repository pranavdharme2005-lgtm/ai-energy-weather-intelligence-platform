"""
Smart Alert Service (Stage 10)
==============================

Service orchestrator linking database contexts, rule evaluation engine,
cooldown management, persistence accumulation, escalation, automatic resolution,
notification dispatch, and UI card preparation.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.database.repository import AlertRepository
from app.models.ai_analyst.context_builder import build_analyst_context
from app.models.smart_alerts.schemas import AlertItem, AlertSummary, AlertCardView, AlertRuleConfig
from app.models.smart_alerts.engine import SmartAlertEngine
from app.models.smart_alerts.ai_explainer import generate_alert_ai_explanation
from app.models.smart_alerts.notifications import ConsoleNotificationProvider
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SmartAlertService:
    """Service layer managing Smart Alert Center evaluation and lifecycle workflows."""

    def __init__(self, db: Optional[Session] = None, config: Optional[AlertRuleConfig] = None):
        self._db = db
        self.config = config or AlertRuleConfig()
        self.engine = SmartAlertEngine(self.config)
        self.notifier = ConsoleNotificationProvider()

    def evaluate_and_sync_alerts(
        self,
        region: str = "Grid_Alpha",
        attach_ai_explanation: bool = False,
        dispatch_notifications: bool = True
    ) -> List[AlertItem]:
        """Evaluates system state, resolves cleared alerts, persists new/escalated alerts, and dispatches notifications.

        Returns:
            List[AlertItem]: List of active triggered or updated alerts.
        """
        db_context = self._db
        close_session = False
        if db_context is None:
            db_context = SessionLocal()
            close_session = True

        try:
            # 1. Build unified system context
            context_obj = build_analyst_context(db_context, region=region)
            context_dict = context_obj.model_dump()

            # 2. Check for active alerts eligible for automatic resolution
            db_active = AlertRepository.get_active_alerts(db_context, region=region)
            active_dicts = [
                {
                    "id": a.id,
                    "alert_id": a.alert_id,
                    "alert_type": a.alert_type,
                    "severity": a.severity,
                    "status": a.status,
                    "last_seen_at": a.last_seen_at
                }
                for a in db_active
            ]

            to_resolve_ids = self.engine.evaluate_resolutions(active_dicts, context_dict)
            for res_id in to_resolve_ids:
                AlertRepository.resolve_alert(db_context, res_id)

            # 3. Evaluate context against rule engine
            candidate_alerts = self.engine.evaluate_context(context_dict)
            synced_alerts: List[AlertItem] = []

            # 4. Deduplicate, cooldown check, escalate, and persist
            cooldown_delta = timedelta(minutes=self.config.cooldown_minutes)
            now_utc = datetime.now(timezone.utc)

            for cand in candidate_alerts:
                existing_record = next((a for a in active_dicts if a["alert_id"] == cand.alert_id), None)

                in_cooldown = False
                if existing_record and existing_record.get("last_seen_at"):
                    last_seen = existing_record["last_seen_at"]
                    if isinstance(last_seen, str):
                        last_seen = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                    if last_seen.tzinfo is None:
                        last_seen = last_seen.replace(tzinfo=timezone.utc)

                    if now_utc - last_seen < cooldown_delta:
                        # Severities hierarchy index comparison
                        sevs = ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
                        old_sev_idx = sevs.index(existing_record.get("severity", "MEDIUM")) if existing_record.get("severity") in sevs else 2
                        new_sev_idx = sevs.index(cand.severity) if cand.severity in sevs else 2

                        if new_sev_idx <= old_sev_idx:
                            in_cooldown = True

                # Attach optional AI explanation
                if attach_ai_explanation and not cand.ai_explanation:
                    cand.ai_explanation = generate_alert_ai_explanation(cand, context_dict)

                # Persist or update in database
                record_dict = cand.model_dump()
                db_id = AlertRepository.save_or_update_alert(db_context, record_dict)

                if not in_cooldown and dispatch_notifications:
                    self.notifier.send_notification(cand)

                synced_alerts.append(cand)

            logger.info(f"SmartAlertService synced {len(synced_alerts)} alerts for region '{region}'.")
            return synced_alerts

        finally:
            if close_session and db_context is not None:
                db_context.close()

    def get_active_alerts(self, region: str = "Grid_Alpha") -> List[AlertItem]:
        """Retrieves active alerts from database."""
        db_context = self._db or SessionLocal()
        try:
            records = AlertRepository.get_active_alerts(db_context, region=region)
            return [
                AlertItem(
                    alert_id=r.alert_id,
                    alert_type=r.alert_type,
                    severity=r.severity,
                    status=r.status,
                    timestamp=r.timestamp.isoformat() if r.timestamp else datetime.now(timezone.utc).isoformat(),
                    region=r.region,
                    title=r.title,
                    message=r.message,
                    reason=r.reason,
                    observed_value=r.observed_value,
                    expected_value=r.expected_value,
                    deviation=r.deviation,
                    source=r.source or "rule_engine",
                    detection_method=r.detection_method or "threshold_rule",
                    model_version=r.model_version or "v1.0.0",
                    occurrence_count=r.occurrence_count
                )
                for r in records
            ]
        finally:
            if self._db is None:
                db_context.close()

    def acknowledge_alert(self, alert_db_id: int) -> bool:
        """Acknowledges an alert by database ID."""
        db_context = self._db or SessionLocal()
        try:
            return AlertRepository.acknowledge_alert(db_context, alert_db_id)
        finally:
            if self._db is None:
                db_context.close()

    def resolve_alert(self, alert_db_id: int) -> bool:
        """Resolves an alert by database ID."""
        db_context = self._db or SessionLocal()
        try:
            return AlertRepository.resolve_alert(db_context, alert_db_id)
        finally:
            if self._db is None:
                db_context.close()

    def get_alert_summary(self, region: str = "Grid_Alpha") -> AlertSummary:
        """Retrieves aggregated alert summary metrics."""
        db_context = self._db or SessionLocal()
        try:
            sum_dict = AlertRepository.get_alert_summary(db_context, region=region)
            return AlertSummary(**sum_dict)
        finally:
            if self._db is None:
                db_context.close()

    def get_alert_card_views(self, region: str = "Grid_Alpha") -> List[AlertCardView]:
        """Prepares reusable data structures for UI card components."""
        db_context = self._db or SessionLocal()
        try:
            records = AlertRepository.get_recent_alerts(db_context, region=region, limit=50)
            badge_map = {
                "CRITICAL": "red",
                "HIGH": "orange",
                "MEDIUM": "yellow",
                "LOW": "blue",
                "INFO": "gray"
            }
            card_views = []
            for r in records:
                m_display = f"{r.observed_value:.1f}" if r.observed_value is not None else "N/A"
                if r.expected_value is not None:
                    m_display += f" (Exp: {r.expected_value:.1f})"

                ts_str = r.timestamp.strftime("%Y-%m-%d %H:%M UTC") if r.timestamp else ""

                card_views.append(AlertCardView(
                    id=r.id,
                    alert_id=r.alert_id,
                    alert_type=r.alert_type,
                    severity=r.severity,
                    status=r.status,
                    title=r.title,
                    message=r.message,
                    reason=r.reason,
                    metric_display=m_display,
                    timestamp_display=ts_str,
                    badge_color=badge_map.get(r.severity, "gray"),
                    occurrence_count=r.occurrence_count
                ))
            return card_views
        finally:
            if self._db is None:
                db_context.close()
