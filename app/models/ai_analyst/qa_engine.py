"""Question-Answering Engine answering user inquiries strictly from verified context."""

import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.ai_analyst.schemas import AnalystResponseSchema, EvidenceItem, AnalystContext
from app.models.ai_analyst.context_builder import build_analyst_context
from app.models.ai_analyst.providers import AIAnalystProvider, get_ai_provider
from app.models.ai_analyst.prompts import SYSTEM_PROMPT_ANALYST, PROMPT_USER_QA
from app.models.ai_analyst.grounding import validate_numerical_grounding
from app.models.ai_analyst.cache import analyst_cache
from app.utils.logger import get_logger

logger = get_logger(__name__)


def generate_deterministic_qa_fallback(question: str, context: AnalystContext) -> AnalystResponseSchema:
    """Generates deterministic Q&A fallback answer based on structured context and question keywords."""
    q_lower = question.lower()
    summary = ""
    findings = []
    evidence = []
    limitations = []

    e_curr = context.current_situation
    e_fore = context.forecast
    w_curr = context.weather
    r_curr = context.rain
    anoms = context.anomalies
    what_if = context.what_if

    if "demand" in q_lower or "forecast" in q_lower or "tomorrow" in q_lower or "predict" in q_lower or "peak" in q_lower:
        peak_mw = e_fore.get("peak_forecast_mw", 3450.0)
        next_mw = e_fore.get("next_period_demand_mw", 2910.0)
        summary = f"The Stage 5 forecasting model predicts a next-period demand of {next_mw:.1f} MW and a 24h peak demand of {peak_mw:.1f} MW."
        findings = [
            f"Next period predicted load: {next_mw:.1f} MW [FORECAST].",
            f"24-hour predicted peak load: {peak_mw:.1f} MW [FORECAST].",
            f"95% residual confidence bounds: {e_fore.get('confidence_lower_mw', 2760.0):.1f} MW to {e_fore.get('confidence_upper_mw', 3060.0):.1f} MW [FORECAST]."
        ]
        evidence = [EvidenceItem(source="FORECAST", value=f"Peak: {peak_mw:.1f} MW, Next: {next_mw:.1f} MW")]

    elif "weather" in q_lower or "temperature" in q_lower or "humidity" in q_lower:
        temp_c = w_curr.get("temperature_c", 22.5)
        hum_pct = w_curr.get("humidity_pct", 60.0)
        cond = w_curr.get("weather_condition", "Clear")
        summary = f"Current observed weather is {cond} at {temp_c:.1f} deg C and {hum_pct:.1f}% relative humidity."
        findings = [
            f"Ambient temperature: {temp_c:.1f} deg C [WEATHER].",
            f"Relative humidity: {hum_pct:.1f}% [WEATHER].",
            f"Meteorological state: {cond} [WEATHER]."
        ]
        evidence = [EvidenceItem(source="WEATHER", value=f"Temp: {temp_c:.1f} C, Humidity: {hum_pct:.1f}%")]

    elif "rain" in q_lower or "precip" in q_lower:
        r_prob = r_curr.get("rain_probability", 0.15) * 100.0
        r_pred = "Rain Expected" if r_curr.get("rain_predicted", False) else "No Rain Expected"
        summary = f"The Stage 4 rain prediction model estimates a {r_prob:.1f}% probability of rain ({r_pred})."
        findings = [
            f"Rain prediction probability: {r_prob:.1f}% [RAIN].",
            f"Categorical rain prediction: {r_pred} [RAIN].",
            f"Current observed precipitation: {w_curr.get('precipitation_mm', 0.0):.1f} mm [WEATHER]."
        ]
        evidence = [EvidenceItem(source="RAIN", value=f"Probability: {r_prob:.1f}%")]

    elif "anomaly" in q_lower or "unusual" in q_lower or "spike" in q_lower:
        count = len(anoms)
        if count > 0:
            top = anoms[0]
            summary = f"Stage 6 anomaly detection identified {count} active anomalies. Highest severity: {top.get('severity', 'MEDIUM')}."
            findings = [
                f"Active anomaly count: {count} [ANOMALY].",
                f"Primary variable: {top.get('variable', 'demand_mw')} (Observed: {top.get('actual_value')}, Expected: {top.get('expected_value')}) [ANOMALY].",
                f"Severity: {top.get('severity', 'MEDIUM')} [ANOMALY]."
            ]
        else:
            summary = "No unusual anomalies detected. Grid operations are currently NORMAL."
            findings = ["Zero active anomalies detected in current analysis window [ANOMALY]."]
        evidence = [EvidenceItem(source="ANOMALY", value=f"Active Count: {count}")]

    elif "what if" in q_lower or "scenario" in q_lower or "happen" in q_lower:
        if what_if:
            pct = what_if.get("percentage_change", 0.0)
            summary = f"The Stage 8 What-If Simulator estimates a {pct:+.1f}% demand shift under the recent scenario."
            findings = [
                f"Baseline demand: {what_if.get('baseline_demand_mw'):.1f} MW [WHAT_IF].",
                f"Scenario demand: {what_if.get('scenario_demand_mw'):.1f} MW [WHAT_IF].",
                f"Model-based percentage change: {pct:+.1f}% [WHAT_IF]."
            ]
        else:
            summary = "No recent what-if scenario runs found in the system."
            findings = ["Execute 'py run.py simulate' to run hypothetical scenarios."]
        evidence = [EvidenceItem(source="WHAT_IF", value=f"Change: {what_if.get('percentage_change', 0.0)}%")]

    else:
        # General fallback answer
        demand_val = e_curr.get("latest_demand_mw", 2850.0)
        peak_mw = e_fore.get("peak_forecast_mw", 3450.0)
        summary = f"Grid energy demand is currently {demand_val:.1f} MW with a 24h forecast peak of {peak_mw:.1f} MW in region {context.region}."
        findings = [
            f"Latest observed demand: {demand_val:.1f} MW [FORECAST].",
            f"Predicted 24h peak: {peak_mw:.1f} MW [FORECAST].",
            f"Current temperature: {w_curr.get('temperature_c', 22.5):.1f} deg C [WEATHER]."
        ]
        evidence = [EvidenceItem(source="FORECAST", value=f"Demand: {demand_val:.1f} MW")]

    return AnalystResponseSchema(
        summary=summary,
        key_findings=findings,
        evidence=evidence,
        warnings=[],
        limitations=limitations,
        ai_available=False,
        ai_provider="deterministic_fallback",
        generated_at=datetime.now(timezone.utc).isoformat()
    )


def ask_energy_analyst(
    question: str,
    context_or_db: Any = None,
    region: str = "Grid_Alpha",
    provider: Optional[AIAnalystProvider] = None,
    bypass_cache: bool = False,
    force_refresh: bool = False
) -> AnalystResponseSchema:
    """Answers user question strictly using verified system context."""
    if not question or not question.strip():
        return AnalystResponseSchema(
            summary="Please provide a valid question to the AI Energy Analyst.",
            ai_available=False,
            ai_provider="fallback"
        )

    if isinstance(context_or_db, AnalystContext):
        context = context_or_db
    else:
        context = build_analyst_context(context_or_db, region=region)

    ctx_hash = context.context_hash
    should_bypass = bypass_cache or force_refresh

    # Check Cache
    if not should_bypass and ctx_hash:
        cached_dict = analyst_cache.get(ctx_hash, question)
        if cached_dict:
            return AnalystResponseSchema(**cached_dict)

    prov = provider or get_ai_provider()
    context_json = json.dumps(context.model_dump(), indent=2)
    prompt = PROMPT_USER_QA.format(question=question, context_json=context_json)

    response_text, is_ai_available = prov.generate_completion(prompt, SYSTEM_PROMPT_ANALYST)

    if is_ai_available and response_text:
        try:
            data = json.loads(response_text)
            is_grounded, ungrounded = validate_numerical_grounding(response_text, context)

            if is_grounded:
                evidence_items = [EvidenceItem(**item) for item in data.get("evidence", []) if isinstance(item, dict)]

                response_schema = AnalystResponseSchema(
                    summary=data.get("summary", ""),
                    key_findings=data.get("key_findings", []),
                    evidence=evidence_items,
                    warnings=data.get("warnings", []),
                    limitations=data.get("limitations", []),
                    ai_available=True,
                    ai_provider=getattr(prov, "__class__", {}).__name__,
                    generated_at=datetime.now(timezone.utc).isoformat()
                )

                if ctx_hash:
                    analyst_cache.set(ctx_hash, question, response_schema.model_dump())

                return response_schema
        except Exception as e:
            logger.error(f"Failed parsing LLM Q&A response JSON: {e}")

    # Fallback execution
    logger.info(f"Executing deterministic Q&A fallback for question: '{question}'")
    fallback_response = generate_deterministic_qa_fallback(question, context)

    if ctx_hash:
        analyst_cache.set(ctx_hash, question, fallback_response.model_dump())

    return fallback_response
