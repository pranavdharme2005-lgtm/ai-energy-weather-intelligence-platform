"""Forecast deviation rule evaluator comparing actual vs predicted demand."""

from typing import Dict, Any, List
from datetime import datetime, timezone
import hashlib

from app.models.smart_alerts.rules.base import AlertRuleEvaluator
from app.models.smart_alerts.schemas import AlertItem


class ForecastDeviationRule(AlertRuleEvaluator):
    """Evaluates FORECAST_DEVIATION condition comparing observed vs predicted load."""

    def evaluate(self, context_dict: Dict[str, Any]) -> List[AlertItem]:
        alerts = []
        e_curr = context_dict.get("current_situation", {})
        e_fore = context_dict.get("forecast", {})

        actual = e_curr.get("latest_demand_mw")
        expected = e_fore.get("next_period_demand_mw")
        lower_bound = e_fore.get("confidence_lower_mw")
        upper_bound = e_fore.get("confidence_upper_mw")

        if actual is None or expected is None or expected == 0:
            return []

        dev_mw = actual - expected
        pct_dev = abs(dev_mw / expected) * 100.0

        outside_confidence = False
        if lower_bound is not None and upper_bound is not None:
            if actual < lower_bound or actual > upper_bound:
                outside_confidence = True

        threshold_pct = self.config.forecast_deviation_threshold_pct

        if pct_dev >= threshold_pct or outside_confidence:
            severity = "MEDIUM"
            if pct_dev >= 25.0 or (outside_confidence and pct_dev >= 20.0):
                severity = "HIGH"
            elif pct_dev >= 35.0:
                severity = "CRITICAL"

            region = context_dict.get("region", "Grid_Alpha")
            ts = e_curr.get("timestamp", datetime.now(timezone.utc).isoformat())

            fp_raw = f"FORECAST_DEVIATION:{region}:{int(actual / 100)}"
            alert_id = "alt_fdev_" + hashlib.md5(fp_raw.encode("utf-8")).hexdigest()[:8]

            bound_note = f" (outside 95% interval {lower_bound:.1f}–{upper_bound:.1f} MW)" if outside_confidence else ""

            alerts.append(AlertItem(
                alert_id=alert_id,
                alert_type="FORECAST_DEVIATION",
                severity=severity,
                status="ACTIVE",
                timestamp=ts,
                region=region,
                title="Forecast Residual Deviation Alert",
                message=f"Observed demand ({actual:.1f} MW) deviated by {pct_dev:.1f}% from expected forecast ({expected:.1f} MW){bound_note}.",
                reason=f"Forecast residual is {dev_mw:+.1f} MW ({pct_dev:.1f}%), exceeding {threshold_pct:.1f}% deviation limit.",
                observed_value=float(actual),
                expected_value=float(expected),
                deviation=float(dev_mw),
                source="stage_5_forecasting",
                detection_method="residual_threshold",
                model_version=e_fore.get("model_version", "v1.0.0")
            ))

        return alerts
