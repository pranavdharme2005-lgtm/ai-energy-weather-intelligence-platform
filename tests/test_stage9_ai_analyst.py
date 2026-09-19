"""Automated test suite for Stage 9 — AI Energy Analyst Module."""

import pytest
from app.models.ai_analyst.schemas import AnalystContext, DailyIntelligenceReport, AnalystResponseSchema
from app.models.ai_analyst.context_builder import build_analyst_context
from app.models.ai_analyst.grounding import validate_numerical_grounding
from app.models.ai_analyst.providers import (
    get_ai_provider,
    MockAnalystProvider,
    FallbackAnalystProvider,
    OpenAIAnalystProvider
)
from app.models.ai_analyst.daily_intelligence import (
    generate_daily_intelligence,
    generate_deterministic_daily_report
)
from app.models.ai_analyst.qa_engine import (
    ask_energy_analyst,
    generate_deterministic_qa_fallback
)
from app.models.ai_analyst.cache import AnalystCache
from app.services.ai_analyst_service import AIEnergyAnalystService
from app.database.session import SessionLocal, init_db
from app.database.models import AIInsight


@pytest.fixture
def mock_analyst_context():
    """Returns a realistic synthetic AnalystContext for unit testing."""
    return AnalystContext(
        region="Grid_Alpha",
        current_situation={"latest_demand_mw": 2650.0, "peak_demand_mw": 3100.0, "recent_trend": "STABLE"},
        forecast={"next_period_demand_mw": 2910.0, "peak_forecast_mw": 3250.0, "confidence_lower_mw": 2760.0, "confidence_upper_mw": 3060.0},
        weather={"temperature_c": 28.5, "humidity_pct": 65.0, "precipitation_mm": 0.0, "weather_condition": "Clear"},
        rain={"rain_probability": 0.15, "rain_predicted": False},
        anomalies=[{
            "variable": "demand_mw",
            "actual_value": 3100.0,
            "expected_value": 2500.0,
            "anomaly_score": 0.88,
            "severity": "HIGH",
            "reason": "Demand spike detected"
        }],
        weather_impact={"weather_impact_score": 45.0, "impact_level": "MODERATE"},
        what_if={"baseline_demand_mw": 2650.0, "scenario_demand_mw": 2900.0, "percentage_change": 9.4},
        data_quality={"overall_quality_score": 100.0, "outlier_count": 0, "timestamp_gaps_count": 0}
    )


def test_provider_factory_and_mock(mock_analyst_context):
    """Verifies AI provider instantiation, mock provider execution, and fallback selection."""
    # Test Mock provider
    provider = get_ai_provider(provider_type="mock")
    assert isinstance(provider, MockAnalystProvider)

    # Test Fallback provider
    fallback_prov = get_ai_provider(provider_type="fallback")
    assert isinstance(fallback_prov, FallbackAnalystProvider)

    # Test default provider selection
    default_prov = get_ai_provider()
    assert isinstance(default_prov, (MockAnalystProvider, FallbackAnalystProvider, OpenAIAnalystProvider))

    # Test Mock report response
    res = provider.generate_report(mock_analyst_context)
    assert "current_situation" in res or "executive_summary" in res
    assert "summary" in res or "key_findings" in res


def test_numerical_grounding_validator(mock_analyst_context):
    """Verifies that validate_numerical_grounding enforces strict data source alignment."""
    grounded_claim = "The forecasted peak demand is 3250.0 MW and current demand is 2650.0 MW with temperature 28.5 C."
    is_valid, bad_nums = validate_numerical_grounding(grounded_claim, mock_analyst_context)
    assert is_valid is True
    assert len(bad_nums) == 0

    # Hallucinated claim (numbers 9999.0 and 888.8 are not present in context)
    hallucinated_claim = "The grid is consuming 9999.0 MW with an unexpected surge of 888.8 MW."
    is_valid_h, bad_nums_h = validate_numerical_grounding(hallucinated_claim, mock_analyst_context)
    assert is_valid_h is False
    assert len(bad_nums_h) > 0
    assert "9999.0" in bad_nums_h or "888.8" in bad_nums_h


def test_daily_intelligence_generation(mock_analyst_context):
    """Verifies daily intelligence report generation with mock provider."""
    mock_prov = MockAnalystProvider()
    report = generate_daily_intelligence(mock_analyst_context, provider=mock_prov, force_refresh=True)

    assert isinstance(report, DailyIntelligenceReport)
    assert report.region == "Grid_Alpha"
    assert report.grounding_passed is True
    assert len(report.key_findings) > 0
    assert report.anomaly_risk_assessment.severity in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert len(report.evidence_used) > 0


def test_qa_engine_ask_energy_analyst(mock_analyst_context):
    """Verifies Q&A engine handling of user questions."""
    mock_prov = MockAnalystProvider()
    question = "What is the peak energy demand expected in the next 24 hours?"

    response = ask_energy_analyst(question, mock_analyst_context, provider=mock_prov, force_refresh=True)

    assert isinstance(response, AnalystResponseSchema)
    assert response.grounding_passed is True
    assert len(response.summary) > 0
    assert len(response.key_highlights) > 0


def test_deterministic_fallback(mock_analyst_context):
    """Verifies fallback report and Q&A engine when external AI API is disabled or fails."""
    # Deterministic Daily Report
    report = generate_deterministic_daily_report(mock_analyst_context)
    assert isinstance(report, DailyIntelligenceReport)
    assert report.provider_used == "deterministic_fallback"
    assert report.grounding_passed is True
    assert "2650.0" in report.executive_summary or "3250.0" in report.executive_summary

    # Deterministic Q&A Fallback
    question = "Is rain expected today?"
    qa_resp = generate_deterministic_qa_fallback(question, mock_analyst_context)
    assert isinstance(qa_resp, AnalystResponseSchema)
    assert qa_resp.provider_used == "deterministic_fallback"
    assert qa_resp.grounding_passed is True


def test_cache_mechanism(mock_analyst_context):
    """Verifies in-memory cache hit and bypass features."""
    cache = AnalystCache()
    hash_key = mock_analyst_context.get_context_hash()

    assert cache.get(hash_key) is None

    sample_report = generate_deterministic_daily_report(mock_analyst_context)
    cache.set(hash_key, sample_report)

    cached_item = cache.get(hash_key)
    assert cached_item is not None
    assert cached_item.get("context_hash") == hash_key or cached_item.get("ai_provider") == "deterministic_fallback"

    cache.clear()
    assert cache.get(hash_key) is None


def test_service_and_database_persistence():
    """Verifies service orchestration and SQLite ORM AIInsight persistence."""
    init_db()
    db = SessionLocal()
    try:
        service = AIEnergyAnalystService(db=db)

        # Generate daily report via service
        report = service.generate_daily_report(region="Grid_Alpha", force_refresh=True, save_to_db=True)
        assert report is not None

        # Check DB persistence
        latest_db_record = service.get_latest_daily_report(region="Grid_Alpha")
        assert latest_db_record is not None
        assert latest_db_record["summary_text"] == report.executive_summary

        # Ask Q&A question via service
        qa_res = service.ask_question(question="Explain grid status.", region="Grid_Alpha", save_to_db=True)
        assert qa_res is not None

        records_count = db.query(AIInsight).filter(AIInsight.region == "Grid_Alpha").count()
        assert records_count >= 2

    finally:
        db.close()
