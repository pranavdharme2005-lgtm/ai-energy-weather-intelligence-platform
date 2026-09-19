"""AI Explanation module adding concise human-readable explanations to deterministic alerts."""

from typing import Optional, Dict, Any
from app.models.smart_alerts.schemas import AlertItem
from app.models.ai_analyst.providers import get_ai_provider, FallbackAnalystProvider
from app.models.ai_analyst.prompts import SYSTEM_PROMPT_ANALYST
from app.utils.logger import get_logger

logger = get_logger(__name__)


def generate_alert_ai_explanation(alert: AlertItem, context_dict: Dict[str, Any]) -> str:
    """Generates concise 1-sentence grounded explanation for a deterministically triggered alert.

    NOTE: The AI Analyst ONLY provides explanatory text. It NEVER decides whether an alert triggers or changes severity.
    """
    provider = get_ai_provider()
    if isinstance(provider, FallbackAnalystProvider):
        return f"{alert.title}: {alert.message}"

    prompt = f"""An operational alert has been deterministically triggered by rule engine:

ALERT TYPE: {alert.alert_type}
SEVERITY: {alert.severity}
TITLE: {alert.title}
OBSERVED VALUE: {alert.observed_value}
EXPECTED VALUE: {alert.expected_value}
MESSAGE: {alert.message}

Provide a 1-sentence executive explanation for the grid operator explaining why this alert requires operational monitoring.
STRICT RULE: Do NOT invent numbers. Use only verified figures provided above.
"""
    try:
        completion_text, is_available = provider.generate_completion(prompt, SYSTEM_PROMPT_ANALYST)
        if is_available and completion_text:
            cleaned = completion_text.strip().replace("\n", " ")
            return cleaned[:300]
    except Exception as e:
        logger.warning(f"AI explanation generation failed: {e}. Falling back to rule message.")

    return f"{alert.title}: {alert.message}"
