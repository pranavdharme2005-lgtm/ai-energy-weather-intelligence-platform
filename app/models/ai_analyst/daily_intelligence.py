"""Daily Intelligence report generator module."""

import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.ai_analyst.schemas import DailyIntelligenceReport, EvidenceItem, AnalystContext
from app.models.ai_analyst.context_builder import build_analyst_context
from app.models.ai_analyst.providers import AIAnalystProvider, get_ai_provider, FallbackAnalystProvider
from app.models.ai_analyst.prompts import SYSTEM_PROMPT_ANALYST, PROMPT_DAILY_INTELLIGENCE
from app.models.ai_analyst.grounding import validate_numerical_grounding
from app.models.ai_analyst.cache import analyst_cache
from app.utils.logger import get_logger

logger = get_logger(__name__)


def generate_deterministic_daily_report(context: AnalystContext) -> DailyIntelligenceReport:
    """Generates a 100% deterministic fallback Daily Intelligence Report directly from verified context."""
    e_curr = context.current_situation
    e_fore = context.forecast
    w_curr = context.weather
    r_curr = context.rain
    anoms = context.anomalies
    impact = context.weather_impact
    quality = context.data_quality

    demand_val = e_curr.get("latest_demand_mw", 2850.0)
    trend = e_curr.get("recent_trend", "STABLE")
    curr_text = f"Current grid energy demand is {demand_val:.1f} MW in region {context.region} [FORECAST] [WEATHER]. Recent load trend is {trend}."

    next_mw = e_fore.get("next_period_demand_mw", 2910.0)
    peak_mw = e_fore.get("peak_forecast_mw", 3450.0)
    fore_text = f"The model predicts 24h next-period demand of {next_mw:.1f} MW and peak load of {peak_mw:.1f} MW [FORECAST]."

    temp_c = w_curr.get("temperature_c", 22.5)
    hum_pct = w_curr.get("humidity_pct", 60.0)
    r_prob = r_curr.get("rain_probability", 0.15) * 100.0
    w_cond = w_curr.get("weather_condition", "Clear")
    weath_text = f"Ambient weather is {w_cond} at {temp_c:.1f} deg C, {hum_pct:.1f}% relative humidity [WEATHER]. Rain model estimates {r_prob:.1f}% rain probability [RAIN]."

    anom_count = len(anoms)
    if anom_count > 0:
        top_anom = anoms[0]
        anom_text = f"Detected {anom_count} active anomalies [ANOMALY]. Highest severity: {top_anom.get('severity', 'MEDIUM')} on {top_anom.get('variable', 'demand_mw')}."
    else:
        anom_text = "Grid operations are currently NORMAL with 0 active anomalies detected [ANOMALY]."

    imp_level = impact.get("impact_level", "MODERATE")
    score_val = impact.get("weather_impact_score", 38.8)
    insight_text = f"Grid weather sensitivity score is {score_val:.1f} / 100.0 ({imp_level} level) [WEATHER_IMPACT]."

    warnings_list = []
    if quality.get("outlier_count", 0) > 0:
        warnings_list.append(f"Data quality engine flagged {quality.get('outlier_count')} outliers [DATA_QUALITY].")
    if quality.get("timestamp_gaps_count", 0) > 0:
        warnings_list.append(f"Timestamp gaps detected in ingestion pipeline: {quality.get('timestamp_gaps_count')} gaps [DATA_QUALITY].")

    evidence_list = [
        EvidenceItem(source="FORECAST", value=f"Latest Load: {demand_val:.1f} MW, 24h Peak: {peak_mw:.1f} MW"),
        EvidenceItem(source="WEATHER", value=f"Temp: {temp_c:.1f} C, Condition: {w_cond}"),
        EvidenceItem(source="RAIN", value=f"Rain Prob: {r_prob:.1f}%"),
    ]

    return DailyIntelligenceReport(
        current_situation=curr_text,
        forecast_summary=fore_text,
        weather_context=weath_text,
        anomaly_summary=anom_text,
        key_insight=insight_text,
        warnings=warnings_list,
        evidence=evidence_list,
        ai_available=False,
        ai_provider="deterministic_fallback",
        generated_at=datetime.now(timezone.utc).isoformat()
    )


def generate_daily_intelligence(
    context_or_db: Any = None,
    region: str = "Grid_Alpha",
    provider: Optional[AIAnalystProvider] = None,
    bypass_cache: bool = False,
    force_refresh: bool = False
) -> DailyIntelligenceReport:
    """Generates structured Daily Intelligence report for specified region.

    Accepts either an existing AnalystContext instance or a database Session.
    """
    if isinstance(context_or_db, AnalystContext):
        context = context_or_db
    else:
        context = build_analyst_context(context_or_db, region=region)

    ctx_hash = context.context_hash
    should_bypass = bypass_cache or force_refresh

    # Check Cache
    if not should_bypass and ctx_hash:
        cached_dict = analyst_cache.get(ctx_hash, "daily_intelligence")
        if cached_dict:
            return DailyIntelligenceReport(**cached_dict)

    prov = provider or get_ai_provider()
    context_json = json.dumps(context.model_dump(), indent=2)
    prompt = PROMPT_DAILY_INTELLIGENCE.format(context_json=context_json)

    response_text, is_ai_available = prov.generate_completion(prompt, SYSTEM_PROMPT_ANALYST)

    if is_ai_available and response_text:
        try:
            data = json.loads(response_text)
            is_grounded, ungrounded = validate_numerical_grounding(response_text, context)

            if is_grounded:
                evidence_items = [
                    EvidenceItem(source="FORECAST", value=f"Peak Forecast: {context.forecast.get('peak_forecast_mw', 3450.0)} MW"),
                    EvidenceItem(source="WEATHER", value=f"Temp: {context.weather.get('temperature_c', 22.5)} C"),
                    EvidenceItem(source="RAIN", value=f"Rain Prob: {context.rain.get('rain_probability', 0.15)}")
                ]

                report = DailyIntelligenceReport(
                    current_situation=data.get("current_situation", ""),
                    forecast_summary=data.get("forecast_summary", ""),
                    weather_context=data.get("weather_context", ""),
                    anomaly_summary=data.get("anomaly_summary", ""),
                    key_insight=data.get("key_insight", ""),
                    warnings=data.get("warnings", []),
                    evidence=evidence_items,
                    ai_available=True,
                    ai_provider=getattr(prov, "__class__", {}).__name__,
                    generated_at=datetime.now(timezone.utc).isoformat()
                )

                if ctx_hash:
                    analyst_cache.set(ctx_hash, "daily_intelligence", report.model_dump())

                return report
        except Exception as e:
            logger.error(f"Failed parsing LLM daily intelligence JSON response: {e}")

    # Fallback execution
    logger.info("Executing deterministic fallback Daily Intelligence Report.")
    fallback_report = generate_deterministic_daily_report(context)
    if ctx_hash:
        analyst_cache.set(ctx_hash, "daily_intelligence", fallback_report.model_dump())

    return fallback_report
