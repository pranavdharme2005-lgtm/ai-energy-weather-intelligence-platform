"""Data quality alert rule evaluator using Stage 3 Quality Engine metrics."""

from typing import Dict, Any, List
from datetime import datetime, timezone
import hashlib

from app.models.smart_alerts.rules.base import AlertRuleEvaluator
from app.models.smart_alerts.schemas import AlertItem


class DataQualityRule(AlertRuleEvaluator):
    """Evaluates DATA_QUALITY rule condition from Stage 3 Quality Engine metrics."""

    def evaluate(self, context_dict: Dict[str, Any]) -> List[AlertItem]:
        alerts = []
        quality = context_dict.get("data_quality", {})

        quality_score = quality.get("overall_quality_score")
        gaps_count = quality.get("timestamp_gaps_count", 0)
        outlier_count = quality.get("outlier_count", 0)

        if quality_score is None:
            return []

        if quality_score < 90.0 or gaps_count > 0 or outlier_count >= 5:
            severity = "LOW"
            if quality_score < 80.0 or gaps_count >= 3:
                severity = "MEDIUM"
            elif quality_score < 60.0:
                severity = "HIGH"

            region = context_dict.get("region", "Grid_Alpha")
            ts = datetime.now(timezone.utc).isoformat()

            fp_raw = f"DATA_QUALITY:{region}:{gaps_count}:{outlier_count}"
            alert_id = "alt_dq_" + hashlib.md5(fp_raw.encode("utf-8")).hexdigest()[:8]

            alerts.append(AlertItem(
                alert_id=alert_id,
                alert_type="DATA_QUALITY",
                severity=severity,
                status="ACTIVE",
                timestamp=ts,
                region=region,
                title="Data Pipeline Integrity Alert",
                message=f"Stage 3 Data Quality score is {quality_score:.1f}% with {gaps_count} timestamp gaps and {outlier_count} outliers.",
                reason=f"Data pipeline ingestion metrics degraded below optimal 90.0% quality baseline.",
                observed_value=float(quality_score),
                expected_value=100.0,
                deviation=float(quality_score - 100.0),
                source="stage_3_data_quality",
                detection_method="quality_score_threshold"
            ))

        return alerts
