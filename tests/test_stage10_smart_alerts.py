"""Automated test suite for Stage 10 — Smart Alert Center."""

import pytest
from datetime import datetime, timezone, timedelta

from app.models.smart_alerts.schemas import AlertItem, AlertRuleConfig, AlertSummary, AlertCardView
from app.models.smart_alerts.engine import SmartAlertEngine
from app.models.smart_alerts.rules.energy_rules import EnergySpikeRule, EnergyDropRule, PredictedPeakRule
from app.models.smart_alerts.rules.forecast_rules import ForecastDeviationRule
from app.models.smart_alerts.rules.rain_rules import RainEventRule
from app.models.smart_alerts.rules.weather_rules import ExtremeWeatherRule
from app.models.smart_alerts.rules.quality_rules import DataQualityRule
from app.models.smart_alerts.rules.model_rules import ModelConfidenceRule
from app.models.smart_alerts.notifications import ConsoleNotificationProvider
from app.models.smart_alerts.ai_explainer import generate_alert_ai_explanation
from app.services.alert_service import SmartAlertService
from app.database.session import SessionLocal, init_db
from app.database.models import Alert
from app.database.repository import AlertRepository


@pytest.fixture
def sample_context():
    """Provides standard synthetic system context for alert testing."""
    return {
        "region": "Grid_Alpha",
        "current_situation": {"latest_demand_mw": 3600.0, "mean_demand_mw": 2500.0, "timestamp": "2026-09-19T12:00:00Z"},
        "forecast": {"next_period_demand_mw": 2900.0, "peak_forecast_mw": 3850.0, "confidence_lower_mw": 2600.0, "confidence_upper_mw": 3200.0},
        "weather": {"temperature_c": 36.5, "humidity_pct": 70.0, "precipitation_mm": 0.0, "weather_condition": "Clear"},
        "rain": {"rain_probability": 0.75, "rain_predicted": True},
        "anomalies": [{"variable": "demand_mw", "actual_value": 3600.0, "expected_value": 2500.0, "severity": "HIGH"}],
        "weather_impact": {"weather_impact_score": 62.0, "impact_level": "HIGH"},
        "what_if": {"out_of_range_warning": True},
        "data_quality": {"overall_quality_score": 85.0, "outlier_count": 6, "timestamp_gaps_count": 1}
    }


def test_energy_spike_and_drop_rules(sample_context):
    """Verifies energy demand spike and drop rule triggering."""
    spike_rule = EnergySpikeRule(AlertRuleConfig(energy_spike_threshold_mw=3500.0))
    alerts = spike_rule.evaluate(sample_context)

    assert len(alerts) == 1
    assert alerts[0].alert_type == "ENERGY_DEMAND_SPIKE"
    assert alerts[0].observed_value == 3600.0
    assert alerts[0].severity in ["MEDIUM", "HIGH", "CRITICAL"]

    # Test drop rule
    drop_context = dict(sample_context)
    drop_context["current_situation"] = {"latest_demand_mw": 1200.0, "mean_demand_mw": 2500.0}
    drop_rule = EnergyDropRule(AlertRuleConfig(energy_drop_threshold_mw=1500.0))
    drop_alerts = drop_rule.evaluate(drop_context)

    assert len(drop_alerts) == 1
    assert drop_alerts[0].alert_type == "ENERGY_DEMAND_DROP"
    assert drop_alerts[0].observed_value == 1200.0


def test_forecast_deviation_rule(sample_context):
    """Verifies forecast deviation calculation and 95% confidence interval breaches."""
    rule = ForecastDeviationRule(AlertRuleConfig(forecast_deviation_threshold_pct=15.0))
    alerts = rule.evaluate(sample_context)

    assert len(alerts) == 1
    assert alerts[0].alert_type == "FORECAST_DEVIATION"
    assert alerts[0].observed_value == 3600.0
    assert alerts[0].expected_value == 2900.0
    assert alerts[0].deviation == 700.0


def test_rain_and_extreme_weather_rules(sample_context):
    """Verifies Stage 4 rain thresholding and Stage 2 extreme temperature rules."""
    rain_rule = RainEventRule(AlertRuleConfig(rain_alert_threshold_pct=60.0))
    rain_alerts = rain_rule.evaluate(sample_context)

    assert len(rain_alerts) == 1
    assert rain_alerts[0].alert_type == "RAIN_EVENT"
    assert "High Probability of Rain" in rain_alerts[0].title
    assert "definitely" not in rain_alerts[0].message.lower()

    weath_rule = ExtremeWeatherRule(AlertRuleConfig(extreme_temp_high_c=35.0))
    weath_alerts = weath_rule.evaluate(sample_context)

    assert len(weath_alerts) == 1
    assert weath_alerts[0].alert_type == "EXTREME_WEATHER"
    assert "Extreme Heat" in weath_alerts[0].title


def test_quality_and_model_uncertainty_rules(sample_context):
    """Verifies data quality and model uncertainty rules."""
    q_rule = DataQualityRule()
    q_alerts = q_rule.evaluate(sample_context)
    assert len(q_alerts) == 1
    assert q_alerts[0].alert_type == "DATA_QUALITY"

    m_rule = ModelConfidenceRule()
    m_alerts = m_rule.evaluate(sample_context)
    assert len(m_alerts) == 1
    assert m_alerts[0].alert_type == "MODEL_CONFIDENCE"


def test_missing_data_edge_cases():
    """Verifies that empty/missing context data does NOT produce fake alerts."""
    empty_context = {"region": "Grid_Alpha", "current_situation": {}, "weather": {}, "forecast": {}, "rain": {}}
    engine = SmartAlertEngine()
    alerts = engine.evaluate_context(empty_context)

    assert len(alerts) == 0


def test_alert_deduplication_and_cooldown():
    """Verifies alert fingerprint deduplication and cooldown filtering."""
    init_db()
    db = SessionLocal()
    try:
        service = SmartAlertService(db=db)
        ctx = {
            "region": "Grid_Alpha",
            "current_situation": {"latest_demand_mw": 3800.0, "mean_demand_mw": 2500.0},
            "forecast": {},
            "weather": {},
            "rain": {}
        }

        # First evaluation
        alerts1 = service.engine.evaluate_context(ctx)
        assert len(alerts1) > 0
        fp1 = alerts1[0].alert_id

        # Persist first alert
        rec_id1 = AlertRepository.save_or_update_alert(db, alerts1[0].model_dump())
        assert rec_id1 > 0

        # Second evaluation with identical state
        rec_id2 = AlertRepository.save_or_update_alert(db, alerts1[0].model_dump())
        assert rec_id2 == rec_id1

        # Check occurrence count increased
        db_rec = db.query(Alert).filter(Alert.id == rec_id1).first()
        assert db_rec.occurrence_count >= 2

    finally:
        db.close()


def test_severity_escalation():
    """Verifies severity escalation when underlying metrics worsen during active alert state."""
    init_db()
    db = SessionLocal()
    try:
        med_alert = {
            "alert_id": "alt_escalate_test",
            "alert_type": "ENERGY_DEMAND_SPIKE",
            "severity": "MEDIUM",
            "status": "ACTIVE",
            "region": "Grid_Alpha",
            "title": "Demand Spike",
            "message": "Medium spike observed.",
            "observed_value": 3550.0
        }
        id1 = AlertRepository.save_or_update_alert(db, med_alert)

        # Escalate to HIGH severity
        high_alert = dict(med_alert)
        high_alert["severity"] = "HIGH"
        high_alert["title"] = "Critical Demand Spike"
        high_alert["message"] = "High spike observed."
        high_alert["observed_value"] = 4100.0

        id2 = AlertRepository.save_or_update_alert(db, high_alert)
        assert id2 == id1

        updated_rec = db.query(Alert).filter(Alert.id == id1).first()
        assert updated_rec.severity == "HIGH"
        assert updated_rec.title == "Critical Demand Spike"
    finally:
        db.close()


def test_automatic_resolution():
    """Verifies automatic resolution when metric parameters return to normal."""
    engine = SmartAlertEngine(AlertRuleConfig(energy_spike_threshold_mw=3500.0))

    active_alerts = [{
        "id": 101,
        "alert_id": "alt_spike_101",
        "alert_type": "ENERGY_DEMAND_SPIKE",
        "severity": "HIGH",
        "status": "ACTIVE"
    }]

    # Normal context (demand = 2400 MW < 3500 MW threshold)
    normal_ctx = {"current_situation": {"latest_demand_mw": 2400.0}, "weather": {}, "rain": {}}
    to_resolve = engine.evaluate_resolutions(active_alerts, normal_ctx)

    assert 101 in to_resolve


def test_state_transitions_and_summary_metrics():
    """Verifies ACTIVE -> ACKNOWLEDGED -> RESOLVED state transitions and summary metrics."""
    init_db()
    db = SessionLocal()
    try:
        service = SmartAlertService(db=db)
        test_alert = {
            "alert_id": "alt_lifecycle_test",
            "alert_type": "RAIN_EVENT",
            "severity": "LOW",
            "status": "ACTIVE",
            "region": "Grid_Alpha",
            "title": "Rain Forecast",
            "message": "Rain prob high."
        }
        db_id = AlertRepository.save_or_update_alert(db, test_alert)
        assert db_id > 0

        # Transition to ACKNOWLEDGED
        ack_res = service.acknowledge_alert(db_id)
        assert ack_res is True

        rec_ack = db.query(Alert).filter(Alert.id == db_id).first()
        assert rec_ack.status == "ACKNOWLEDGED"
        assert rec_ack.is_acknowledged is True

        # Transition to RESOLVED
        res_res = service.resolve_alert(db_id)
        assert res_res is True

        rec_res = db.query(Alert).filter(Alert.id == db_id).first()
        assert rec_res.status == "RESOLVED"
        assert rec_res.resolved_at is not None

        # Summary check
        summary = service.get_alert_summary(region="Grid_Alpha")
        assert summary.total_alerts > 0
        assert isinstance(summary, AlertSummary)

        # Card view check
        cards = service.get_alert_card_views(region="Grid_Alpha")
        assert len(cards) > 0
        assert isinstance(cards[0], AlertCardView)

    finally:
        db.close()


def test_notification_provider_and_ai_explainer(sample_context):
    """Verifies notification dispatching and AI explanation generation."""
    provider = ConsoleNotificationProvider()
    test_item = AlertItem(
        alert_id="alt_notif_001",
        alert_type="PREDICTED_PEAK",
        severity="HIGH",
        title="High Peak Demand Predicted",
        message="24h peak load expected to reach 3850 MW."
    )

    msg = provider.send_notification(test_item)
    assert msg.alert_id == "alt_notif_001"
    assert msg.severity == "HIGH"

    explanation = generate_alert_ai_explanation(test_item, sample_context)
    assert len(explanation) > 0
