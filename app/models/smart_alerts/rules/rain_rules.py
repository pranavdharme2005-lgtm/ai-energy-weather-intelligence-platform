"""Rain event alert rule evaluator using Stage 4 rain model outputs."""

from typing import Dict, Any, List
from datetime import datetime, timezone
import hashlib

from app.models.smart_alerts.rules.base import AlertRuleEvaluator
from app.models.smart_alerts.schemas import AlertItem


class RainEventRule(AlertRuleEvaluator):
    """Evaluates RAIN_EVENT rule condition from Stage 4 rain prediction model."""

    def evaluate(self, context_dict: Dict[str, Any]) -> List[AlertItem]:
        alerts = []
        r_curr = context_dict.get("rain", {})
        rain_prob = r_curr.get("rain_probability")

        if rain_prob is None:
            return []

        # Convert to percentage if stored as probability ratio [0, 1]
        rain_prob_pct = rain_prob * 100.0 if rain_prob <= 1.0 else rain_prob

        threshold_pct = self.config.rain_alert_threshold_pct

        if rain_prob_pct >= threshold_pct:
            severity = "LOW"
            if rain_prob_pct >= 80.0:
                severity = "MEDIUM"
            elif rain_prob_pct >= 95.0:
                severity = "HIGH"

            region = context_dict.get("region", "Grid_Alpha")
            ts = r_curr.get("timestamp", datetime.now(timezone.utc).isoformat())

            fp_raw = f"RAIN_EVENT:{region}:{int(rain_prob_pct / 10)}"
            alert_id = "alt_rain_" + hashlib.md5(fp_raw.encode("utf-8")).hexdigest()[:8]

            alerts.append(AlertItem(
                alert_id=alert_id,
                alert_type="RAIN_EVENT",
                severity=severity,
                status="ACTIVE",
                timestamp=ts,
                region=region,
                title="High Probability of Rain",
                message=f"Stage 4 rain prediction model estimates a {rain_prob_pct:.1f}% probability of precipitation over the upcoming period.",
                reason=f"Estimated rain probability ({rain_prob_pct:.1f}%) exceeds alert threshold ({threshold_pct:.1f}%).",
                observed_value=float(rain_prob_pct),
                expected_value=float(threshold_pct),
                deviation=float(rain_prob_pct - threshold_pct),
                source="stage_4_rain_model",
                detection_method="probabilistic_classifier",
                model_version=r_curr.get("model_version", "v1.0.0")
            ))

        return alerts
