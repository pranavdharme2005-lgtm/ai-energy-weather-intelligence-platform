"""
AI Energy Analyst Module (Stage 9)
==================================

Combines outputs from ingestion, forecasting, rain prediction, anomaly detection,
weather analytics, and scenario simulation into concise, grounded AI insights.
"""

from app.models.ai_analyst.schemas import (
    AnalystContext,
    DailyIntelligenceReport,
    AnalystResponseSchema,
    EvidenceItem,
)
from app.models.ai_analyst.context_builder import build_analyst_context
from app.models.ai_analyst.grounding import validate_numerical_grounding
from app.models.ai_analyst.cache import AnalystCache, analyst_cache
from app.models.ai_analyst.providers import (
    AIAnalystProvider,
    OpenAIAnalystProvider,
    FallbackAnalystProvider,
    MockAnalystProvider,
    get_ai_provider,
)
from app.models.ai_analyst.daily_intelligence import (
    generate_daily_intelligence,
    generate_deterministic_daily_report,
)
from app.models.ai_analyst.qa_engine import (
    ask_energy_analyst,
    generate_deterministic_qa_fallback,
)

__all__ = [
    "AnalystContext",
    "DailyIntelligenceReport",
    "AnalystResponseSchema",
    "EvidenceItem",
    "build_analyst_context",
    "validate_numerical_grounding",
    "AnalystCache",
    "analyst_cache",
    "AIAnalystProvider",
    "OpenAIAnalystProvider",
    "FallbackAnalystProvider",
    "MockAnalystProvider",
    "get_ai_provider",
    "generate_daily_intelligence",
    "generate_deterministic_daily_report",
    "ask_energy_analyst",
    "generate_deterministic_qa_fallback",
]
