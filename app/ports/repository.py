from abc import ABC, abstractmethod
from typing import Optional
from app.domain.models import NotificationRequest


class RequestRepository(ABC):
    """Abstract base class for request repository."""

    @abstractmethod
    async def save(self, request: NotificationRequest) -> None:
        """Save a notification request."""
        pass

    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[NotificationRequest]:
        """Get a notification request by id."""
        pass

    @abstractmethod
    async def update(self, request: NotificationRequest) -> None:
        """Update a notification request."""
        pass

    @abstractmethod
    async def delete(self, id: str) -> None:
        """Delete a notification request."""
        pass
