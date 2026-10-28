from fastapi import Request
from app.application.request_service import RequestService


def get_request_service(request: Request) -> RequestService:
    """Dependency provider for RequestService."""
    return request.app.state.request_service
