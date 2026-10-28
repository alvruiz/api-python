import asyncio
from typing import Dict, Optional
from app.domain.models import NotificationRequest
from app.ports.repository import RequestRepository


class InMemoryRequestRepository(RequestRepository):
    """In-memory implementation of the request repository."""

    def __init__(self) -> None:
        self._storage: Dict[str, NotificationRequest] = {}
        self._lock = asyncio.Lock()

    async def save(self, request: NotificationRequest) -> None:
        async with self._lock:
            if request.id in self._storage:
                raise ValueError(f"Request with id {request.id} already exists")
            self._storage[request.id] = request

    async def get_by_id(self, id: str) -> Optional[NotificationRequest]:
        async with self._lock:
            return self._storage.get(id)

    async def update(self, request: NotificationRequest) -> None:
        async with self._lock:
            if request.id not in self._storage:
                raise ValueError(f"Request with id {request.id} does not exist")
            self._storage[request.id] = request

    async def delete(self, id: str) -> None:
        async with self._lock:
            if id not in self._storage:
                raise ValueError(f"Request with id {id} does not exist")
            self._storage.pop(id, None)
