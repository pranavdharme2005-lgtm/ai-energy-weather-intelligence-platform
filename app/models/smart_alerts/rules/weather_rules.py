"""Extreme weather alert rule evaluator using Stage 2 real meteorological observations."""

from typing import Dict, Any, List
from datetime import datetime, timezone
import hashlib

from app.models.smart_alerts.rules.base import AlertRuleEvaluator
from app.models.smart_alerts.schemas import AlertItem


class ExtremeWeatherRule(AlertRuleEvaluator):
    """Evaluates EXTREME_WEATHER rule condition from real weather observations."""

    def evaluate(self, context_dict: Dict[str, Any]) -> List[AlertItem]:
        alerts = []
        w_curr = context_dict.get("weather", {})
        temp_c = w_curr.get("temperature_c")

        if temp_c is None:
            return []

        precip_mm = w_curr.get("precipitation_mm", 0.0)
        condition = w_curr.get("weather_condition", "Clear")

        high_temp_thresh = self.config.extreme_temp_high_c
        low_temp_thresh = self.config.extreme_temp_low_c

        is_extreme_heat = temp_c >= high_temp_thresh
        is_freezing = temp_c <= low_temp_thresh
        is_heavy_precip = precip_mm >= 25.0
        is_storm = condition in ["Storm", "Severe Heatwave", "Blizzard"]

        if is_extreme_heat or is_freezing or is_heavy_precip or is_storm:
            severity = "MEDIUM"
            if temp_c >= 40.0 or temp_c <= -10.0 or is_storm:
                severity = "HIGH"

            region = context_dict.get("region", "Grid_Alpha")
            ts = w_curr.get("timestamp", datetime.now(timezone.utc).isoformat())

            if is_extreme_heat:
                title = "Extreme Heat Warning"
                msg = f"Ambient temperature of {temp_c:.1f} deg C exceeds extreme heat threshold ({high_temp_thresh:.1f} deg C)."
                reason = f"Extreme heat observed; expected to drive substantial HVAC cooling load."
                observed_val = float(temp_c)
                expected_val = float(high_temp_thresh)
            elif is_freezing:
                title = "Freezing Temperature Warning"
                msg = f"Ambient temperature of {temp_c:.1f} deg C is below freezing threshold ({low_temp_thresh:.1f} deg C)."
                reason = f"Freezing weather observed; expected to drive high heating demand."
                observed_val = float(temp_c)
                expected_val = float(low_temp_thresh)
            else:
                title = f"Extreme Weather Condition: {condition}"
                msg = f"Observed meteorological state is {condition} with {precip_mm:.1f} mm precipitation."
                reason = f"Severe meteorological condition observed in region."
                observed_val = float(precip_mm)
                expected_val = 0.0

            fp_raw = f"EXTREME_WEATHER:{region}:{title}"
            alert_id = "alt_weath_" + hashlib.md5(fp_raw.encode("utf-8")).hexdigest()[:8]

            alerts.append(AlertItem(
                alert_id=alert_id,
                alert_type="EXTREME_WEATHER",
                severity=severity,
                status="ACTIVE",
                timestamp=ts,
                region=region,
                title=title,
                message=msg,
                reason=reason,
                observed_value=observed_val,
                expected_value=expected_val,
                deviation=float(observed_val - expected_val),
                source="stage_2_weather",
                detection_method="threshold_rule"
            ))

        return alerts
