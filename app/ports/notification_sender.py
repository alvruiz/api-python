from abc import ABC, abstractmethod
from app.domain.models import NotificationPayload


class NotificationSender(ABC):
    """" Abstract base class for notification sender """
    @abstractmethod
    async def send_notification(self, payload: NotificationPayload) -> dict:
        """Send a notification to the recipient and return the response"""
        pass