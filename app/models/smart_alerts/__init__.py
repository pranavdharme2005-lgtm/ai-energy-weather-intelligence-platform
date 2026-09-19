"""
Smart Alert Center Module (Stage 10)
=====================================

Centralized rule evaluation engine, severity hierarchy, alert deduplication,
cooldown management, persistence accumulation, escalation, automatic resolution,
and UI visualization preparation.
"""

from app.models.smart_alerts.schemas import (
    AlertItem,
    AlertRuleConfig,
    AlertSummary,
    AlertCardView,
    NotificationMessage,
)
from app.models.smart_alerts.engine import SmartAlertEngine
from app.models.smart_alerts.ai_explainer import generate_alert_ai_explanation
from app.models.smart_alerts.notifications import NotificationProvider, ConsoleNotificationProvider
from app.models.smart_alerts.rules.base import AlertRuleEvaluator
from app.models.smart_alerts.rules.energy_rules import EnergySpikeRule, EnergyDropRule, PredictedPeakRule
from app.models.smart_alerts.rules.forecast_rules import ForecastDeviationRule
from app.models.smart_alerts.rules.rain_rules import RainEventRule
from app.models.smart_alerts.rules.weather_rules import ExtremeWeatherRule
from app.models.smart_alerts.rules.quality_rules import DataQualityRule
from app.models.smart_alerts.rules.model_rules import ModelConfidenceRule

__all__ = [
    "AlertItem",
    "AlertRuleConfig",
    "AlertSummary",
    "AlertCardView",
    "NotificationMessage",
    "SmartAlertEngine",
    "generate_alert_ai_explanation",
    "NotificationProvider",
    "ConsoleNotificationProvider",
    "AlertRuleEvaluator",
    "EnergySpikeRule",
    "EnergyDropRule",
    "PredictedPeakRule",
    "ForecastDeviationRule",
    "RainEventRule",
    "ExtremeWeatherRule",
    "DataQualityRule",
    "ModelConfidenceRule",
]
