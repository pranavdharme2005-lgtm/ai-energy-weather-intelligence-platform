"""Notification provider abstraction interface for Smart Alert Center."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from app.models.smart_alerts.schemas import NotificationMessage, AlertItem
from app.utils.logger import get_logger

logger = get_logger(__name__)


class NotificationProvider(ABC):
    """Abstract interface for dispatching alert notifications."""

    @abstractmethod
    def send_notification(self, alert: AlertItem) -> NotificationMessage:
        """Sends alert notification through provider channel.

        Returns:
            NotificationMessage: Dispatched message payload.
        """
        pass


class ConsoleNotificationProvider(NotificationProvider):
    """Internal console and log notification provider."""

    def send_notification(self, alert: AlertItem) -> NotificationMessage:
        body = f"[{alert.severity}] {alert.title} — {alert.message}"
        logger.info(f"[NOTIFICATION DISPATCH] Channel=Console AlertID={alert.alert_id} :: {body}")
        return NotificationMessage(
            alert_id=alert.alert_id,
            severity=alert.severity,
            channel="console",
            title=alert.title,
            body=body
        )
