"""AI Analyst Provider abstraction layer supporting OpenAI, Fallback, and Mock engines."""

import json
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional

from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AIAnalystProvider(ABC):
    """Abstract interface for AI Analyst LLM providers."""

    @abstractmethod
    def generate_completion(self, prompt: str, system_prompt: str) -> Tuple[str, bool]:
        """Generates LLM completion response text.

        Returns:
            Tuple[str, bool]: (response_text, is_ai_available)
        """
        pass


class FallbackAnalystProvider(AIAnalystProvider):
    """Deterministic fallback provider used when external LLM API is unconfigured or unavailable."""

    def generate_completion(self, prompt: str, system_prompt: str) -> Tuple[str, bool]:
        """Returns empty string requiring deterministic fallback construction."""
        logger.info("FallbackAnalystProvider active (ai_available = False). Using deterministic rule engine.")
        return "", False


class MockAnalystProvider(AIAnalystProvider):
    """Mock LLM provider for fast, offline unit testing without network API calls."""

    def __init__(self, mock_response_dict: Optional[Dict[str, Any]] = None):
        self.mock_response_dict = mock_response_dict or {
            "current_situation": "Current grid load is 2850.0 MW [FORECAST] [WEATHER]. Recent demand trend is STABLE.",
            "forecast_summary": "The model predicts 24h peak demand of 3450.0 MW [FORECAST].",
            "weather_context": "Current temperature is 22.5 deg C with 60.0% humidity [WEATHER]. Rain probability is 15.0% [RAIN].",
            "anomaly_summary": "Grid operations are currently NORMAL with 0 high-severity anomalies detected [ANOMALY].",
            "key_insight": "Temperature exhibits strong positive correlation with cooling load [WEATHER_IMPACT].",
            "warnings": [],
            "summary": "Current demand is 2850.0 MW with predicted 24h peak of 3450.0 MW.",
            "key_findings": [
                "Predicted peak demand is 3450.0 MW [FORECAST].",
                "Current temperature is 22.5 deg C with rain probability of 15.0% [WEATHER] [RAIN].",
                "Weather impact score is 38.8 / 100.0 [WEATHER_IMPACT]."
            ],
            "evidence": [
                {"source": "FORECAST", "value": "24h Peak: 3450.0 MW"},
                {"source": "WEATHER", "value": "Temp: 22.5 C"}
            ],
            "limitations": []
        }

    def generate_completion(self, prompt: str, system_prompt: str) -> Tuple[str, bool]:
        return json.dumps(self.mock_response_dict), True

    def generate_report(self, context: Any = None) -> Dict[str, Any]:
        """Generates mock report dictionary for unit tests."""
        return self.mock_response_dict


class OpenAIAnalystProvider(AIAnalystProvider):
    """OpenAI API Provider executing LLM calls using configured API keys."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 500
    ):
        self.api_key = api_key or settings.AI_API_KEY or settings.LLM_API_KEY
        self.model_name = model_name or settings.AI_MODEL or settings.LLM_MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens

    def generate_completion(self, prompt: str, system_prompt: str) -> Tuple[str, bool]:
        if not self.api_key or self.api_key == "your_llm_api_key_here":
            logger.warning("No valid AI API key configured. Falling back to FallbackAnalystProvider.")
            return "", False

        try:
            import urllib.request
            import urllib.error

            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "response_format": {"type": "json_object"}
            }

            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                content = resp_data["choices"][0]["message"]["content"]
                return content, True

        except Exception as e:
            logger.error(f"OpenAI API execution error: {e}. Reverting to fallback mode.")
            return "", False


def get_ai_provider(provider_type: Optional[str] = None) -> AIAnalystProvider:
    """Factory function returning configured AIAnalystProvider instance."""
    p_type = (provider_type or settings.AI_PROVIDER).lower()

    if p_type == "mock":
        return MockAnalystProvider()
    elif p_type in ["openai", "llm"]:
        api_key = settings.AI_API_KEY or settings.LLM_API_KEY
        if not api_key or api_key == "your_llm_api_key_here":
            return FallbackAnalystProvider()
        return OpenAIAnalystProvider()
    else:
        return FallbackAnalystProvider()
