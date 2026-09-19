"""Abstract base rule evaluator for Smart Alert Center."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from app.models.smart_alerts.schemas import AlertItem, AlertRuleConfig


class AlertRuleEvaluator(ABC):
    """Abstract interface for modular alert rule evaluators."""

    def __init__(self, config: Optional[AlertRuleConfig] = None):
        self.config = config or AlertRuleConfig()

    @abstractmethod
    def evaluate(self, context_dict: Dict[str, Any]) -> List[AlertItem]:
        """Evaluates system context dictionary against rule criteria.

        Returns:
            List[AlertItem]: Generated alert objects, or empty list if no rule triggered.
        """
        pass
