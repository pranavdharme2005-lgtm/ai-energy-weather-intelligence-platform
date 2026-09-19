"""Smart Alert Engine coordinating rule evaluation, deduplication, cooldown, escalation, and resolution."""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from app.models.smart_alerts.schemas import AlertItem, AlertRuleConfig
from app.models.smart_alerts.rules.base import AlertRuleEvaluator
from app.models.smart_alerts.rules.energy_rules import EnergySpikeRule, EnergyDropRule, PredictedPeakRule
from app.models.smart_alerts.rules.forecast_rules import ForecastDeviationRule
from app.models.smart_alerts.rules.rain_rules import RainEventRule
from app.models.smart_alerts.rules.weather_rules import ExtremeWeatherRule
from app.models.smart_alerts.rules.quality_rules import DataQualityRule
from app.models.smart_alerts.rules.model_rules import ModelConfidenceRule
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SmartAlertEngine:
    """Central engine orchestrating modular alert rules, deduplication, and resolution lifecycle."""

    def __init__(self, config: Optional[AlertRuleConfig] = None):
        self.config = config or AlertRuleConfig()
        self.rules: List[AlertRuleEvaluator] = [
            EnergySpikeRule(self.config),
            EnergyDropRule(self.config),
            PredictedPeakRule(self.config),
            ForecastDeviationRule(self.config),
            RainEventRule(self.config),
            ExtremeWeatherRule(self.config),
            DataQualityRule(self.config),
            ModelConfidenceRule(self.config),
        ]

    def evaluate_context(self, context_dict: Dict[str, Any]) -> List[AlertItem]:
        """Evaluates all registered rule evaluators against system context dictionary.

        Returns:
            List[AlertItem]: All generated candidate alert objects.
        """
        raw_alerts: List[AlertItem] = []
        for r in self.rules:
            try:
                evaluated = r.evaluate(context_dict)
                raw_alerts.extend(evaluated)
            except Exception as e:
                logger.error(f"Rule evaluator '{r.__class__.__name__}' execution error: {e}")

        logger.info(f"SmartAlertEngine evaluated {len(self.rules)} rules -> generated {len(raw_alerts)} candidate alerts.")
        return raw_alerts

    def evaluate_resolutions(
        self,
        active_alerts: List[Dict[str, Any]],
        context_dict: Dict[str, Any]
    ) -> List[int]:
        """Determines which active database alerts are eligible for resolution.

        Args:
            active_alerts: List of currently ACTIVE alert records from database.
            context_dict: Fresh system context dictionary.

        Returns:
            List[int]: Database IDs of alerts that should be resolved.
        """
        to_resolve_ids = []
        e_curr = context_dict.get("current_situation", {})
        w_curr = context_dict.get("weather", {})
        r_curr = context_dict.get("rain", {})

        latest_demand = e_curr.get("latest_demand_mw")
        temp_c = w_curr.get("temperature_c")
        rain_prob = r_curr.get("rain_probability")
        if rain_prob is not None and rain_prob <= 1.0:
            rain_prob *= 100.0

        for a in active_alerts:
            db_id = a.get("id")
            alert_type = a.get("alert_type")

            if alert_type == "ENERGY_DEMAND_SPIKE" and latest_demand is not None:
                if latest_demand < self.config.energy_spike_threshold_mw and latest_demand < 3300.0:
                    to_resolve_ids.append(db_id)

            elif alert_type == "ENERGY_DEMAND_DROP" and latest_demand is not None:
                if latest_demand > self.config.energy_drop_threshold_mw and latest_demand > 1800.0:
                    to_resolve_ids.append(db_id)

            elif alert_type == "RAIN_EVENT" and rain_prob is not None:
                if rain_prob < self.config.rain_alert_threshold_pct - 10.0:
                    to_resolve_ids.append(db_id)

            elif alert_type == "EXTREME_WEATHER" and temp_c is not None:
                if 5.0 < temp_c < self.config.extreme_temp_high_c - 2.0:
                    to_resolve_ids.append(db_id)

        if to_resolve_ids:
            logger.info(f"SmartAlertEngine identified {len(to_resolve_ids)} alerts for automatic resolution.")
        return to_resolve_ids
