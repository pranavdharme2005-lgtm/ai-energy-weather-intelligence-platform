"""Model confidence alert rule evaluator for Stage 5 & Stage 8 uncertainty conditions."""

from typing import Dict, Any, List
from datetime import datetime, timezone
import hashlib

from app.models.smart_alerts.rules.base import AlertRuleEvaluator
from app.models.smart_alerts.schemas import AlertItem


class ModelConfidenceRule(AlertRuleEvaluator):
    """Evaluates MODEL_CONFIDENCE rule condition."""

    def evaluate(self, context_dict: Dict[str, Any]) -> List[AlertItem]:
        alerts = []
        what_if = context_dict.get("what_if", {})
        forecast = context_dict.get("forecast", {})

        out_of_range = what_if.get("out_of_range_warning", False)
        confidence_lower = forecast.get("confidence_lower_mw")
        confidence_upper = forecast.get("confidence_upper_mw")

        wide_interval = False
        interval_width = 0.0
        if confidence_lower is not None and confidence_upper is not None:
            interval_width = confidence_upper - confidence_lower
            if interval_width >= 800.0:
                wide_interval = True

        if out_of_range or wide_interval:
            severity = "LOW"
            if out_of_range and wide_interval:
                severity = "MEDIUM"

            region = context_dict.get("region", "Grid_Alpha")
            ts = datetime.now(timezone.utc).isoformat()

            if out_of_range:
                title = "Model Feature Input Out-of-Range"
                msg = "Scenario parameters or weather input features exceed historical ML training boundaries."
                reason = "Out-of-range historical feature warning flag triggered in scenario engine."
                obs_val = 1.0
            else:
                title = "Wide Forecast Confidence Interval"
                msg = f"Stage 5 demand forecaster 95% confidence interval width ({interval_width:.1f} MW) indicates elevated prediction uncertainty."
                reason = f"Forecast confidence interval width ({interval_width:.1f} MW) exceeds 800 MW tolerance limit."
                obs_val = float(interval_width)

            fp_raw = f"MODEL_CONFIDENCE:{region}:{title}"
            alert_id = "alt_mconf_" + hashlib.md5(fp_raw.encode("utf-8")).hexdigest()[:8]

            alerts.append(AlertItem(
                alert_id=alert_id,
                alert_type="MODEL_CONFIDENCE",
                severity=severity,
                status="ACTIVE",
                timestamp=ts,
                region=region,
                title=title,
                message=msg,
                reason=reason,
                observed_value=obs_val,
                expected_value=0.0,
                deviation=obs_val,
                source="stage_5_or_8_model",
                detection_method="uncertainty_bounds"
            ))

        return alerts
