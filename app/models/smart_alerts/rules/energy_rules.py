"""Energy demand spike, drop, and peak load alert rule evaluators."""

from typing import Dict, Any, List
from datetime import datetime, timezone
import hashlib

from app.models.smart_alerts.rules.base import AlertRuleEvaluator
from app.models.smart_alerts.schemas import AlertItem


class EnergySpikeRule(AlertRuleEvaluator):
    """Evaluates ENERGY_DEMAND_SPIKE rule condition."""

    def evaluate(self, context_dict: Dict[str, Any]) -> List[AlertItem]:
        alerts = []
        e_curr = context_dict.get("current_situation", {})
        latest_demand = e_curr.get("latest_demand_mw")

        if latest_demand is None:
            return []

        spike_threshold = self.config.energy_spike_threshold_mw
        mean_demand = e_curr.get("mean_demand_mw", 2500.0)

        if latest_demand >= spike_threshold or (latest_demand > mean_demand * 1.30 and latest_demand > 3000.0):
            severity = "HIGH"
            if latest_demand >= 4000.0:
                severity = "CRITICAL"
            elif latest_demand < 3600.0:
                severity = "MEDIUM"

            region = context_dict.get("region", "Grid_Alpha")
            ts = e_curr.get("timestamp", datetime.now(timezone.utc).isoformat())

            # Generate deterministic fingerprint ID
            fp_raw = f"ENERGY_DEMAND_SPIKE:{region}:{int(latest_demand / 100)}"
            alert_id = "alt_spike_" + hashlib.md5(fp_raw.encode("utf-8")).hexdigest()[:8]

            deviation = latest_demand - mean_demand

            alerts.append(AlertItem(
                alert_id=alert_id,
                alert_type="ENERGY_DEMAND_SPIKE",
                severity=severity,
                status="ACTIVE",
                timestamp=ts,
                region=region,
                title="Energy Demand Spike Alert",
                message=f"Current demand of {latest_demand:.1f} MW exceeds operational threshold ({spike_threshold:.1f} MW).",
                reason=f"Observed demand is {deviation:+.1f} MW relative to rolling baseline ({mean_demand:.1f} MW).",
                observed_value=float(latest_demand),
                expected_value=float(mean_demand),
                deviation=float(deviation),
                source="stage_2_ingestion",
                detection_method="threshold_rule"
            ))

        return alerts


class EnergyDropRule(AlertRuleEvaluator):
    """Evaluates ENERGY_DEMAND_DROP rule condition."""

    def evaluate(self, context_dict: Dict[str, Any]) -> List[AlertItem]:
        alerts = []
        e_curr = context_dict.get("current_situation", {})
        latest_demand = e_curr.get("latest_demand_mw")

        if latest_demand is None:
            return []

        drop_threshold = self.config.energy_drop_threshold_mw
        mean_demand = e_curr.get("mean_demand_mw", 2500.0)

        if latest_demand <= drop_threshold or (latest_demand < mean_demand * 0.65 and latest_demand < 1800.0):
            severity = "MEDIUM"
            if latest_demand <= 1000.0:
                severity = "HIGH"

            region = context_dict.get("region", "Grid_Alpha")
            ts = e_curr.get("timestamp", datetime.now(timezone.utc).isoformat())

            fp_raw = f"ENERGY_DEMAND_DROP:{region}:{int(latest_demand / 100)}"
            alert_id = "alt_drop_" + hashlib.md5(fp_raw.encode("utf-8")).hexdigest()[:8]

            deviation = latest_demand - mean_demand

            alerts.append(AlertItem(
                alert_id=alert_id,
                alert_type="ENERGY_DEMAND_DROP",
                severity=severity,
                status="ACTIVE",
                timestamp=ts,
                region=region,
                title="Energy Demand Drop Alert",
                message=f"Current demand of {latest_demand:.1f} MW is below low threshold ({drop_threshold:.1f} MW).",
                reason=f"Observed demand is {deviation:+.1f} MW relative to baseline ({mean_demand:.1f} MW).",
                observed_value=float(latest_demand),
                expected_value=float(mean_demand),
                deviation=float(deviation),
                source="stage_2_ingestion",
                detection_method="threshold_rule"
            ))

        return alerts


class PredictedPeakRule(AlertRuleEvaluator):
    """Evaluates PREDICTED_PEAK rule condition from Stage 5 demand forecast."""

    def evaluate(self, context_dict: Dict[str, Any]) -> List[AlertItem]:
        alerts = []
        e_fore = context_dict.get("forecast", {})
        peak_forecast = e_fore.get("peak_forecast_mw")

        if peak_forecast is None:
            return []

        if peak_forecast >= 3400.0:
            severity = "MEDIUM"
            if peak_forecast >= 3800.0:
                severity = "HIGH"
            elif peak_forecast >= 4200.0:
                severity = "CRITICAL"

            region = context_dict.get("region", "Grid_Alpha")
            ts = e_fore.get("timestamp", datetime.now(timezone.utc).isoformat())

            fp_raw = f"PREDICTED_PEAK:{region}:{int(peak_forecast / 100)}"
            alert_id = "alt_peak_" + hashlib.md5(fp_raw.encode("utf-8")).hexdigest()[:8]

            alerts.append(AlertItem(
                alert_id=alert_id,
                alert_type="PREDICTED_PEAK",
                severity=severity,
                status="ACTIVE",
                timestamp=ts,
                region=region,
                title="High Predicted Peak Load",
                message=f"Stage 5 model predicts 24-hour peak demand of {peak_forecast:.1f} MW for region {region}.",
                reason=f"Predicted peak load exceeds standard generation headroom threshold.",
                observed_value=float(peak_forecast),
                expected_value=3000.0,
                deviation=float(peak_forecast - 3000.0),
                source="stage_5_forecasting",
                detection_method="forecast_model"
            ))

        return alerts
