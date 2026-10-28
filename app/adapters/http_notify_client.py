import os
import logging
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception, before_sleep_log
from app.domain.models import NotificationPayload
from app.ports.notification_sender import NotificationSender

logger = logging.getLogger("NotificationSender")


def is_transient_error(exception: BaseException) -> bool:
    """Check if the exception is a transient error (429 Rate Limit, 5xx Server Error or network issue)."""
    if isinstance(exception, httpx.HTTPStatusError):
        return exception.response.status_code in [429, 500, 502, 503, 504]
    if isinstance(exception, (httpx.TimeoutException, httpx.NetworkError)):
        return True
    return False


class HttpNotificationSender(NotificationSender):
    """HTTP implementation of the notification sender with resilience."""

    def __init__(
        self,
        base_url: str = os.getenv("PROVIDER_BASE_URL", "http://localhost:3001"),
        api_key: str = os.getenv("PROVIDER_API_KEY", "test-dev-2026"),
        client: httpx.AsyncClient | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = client

    @retry(
        retry=retry_if_exception(is_transient_error),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.2, min=0.2, max=1.5),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _send_with_retry(self, url: str, payload_dict: dict, headers: dict) -> dict:
        if self._client:
            response = await self._client.post(url, json=payload_dict, headers=headers, timeout=5.0)
        else:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=payload_dict, headers=headers)
        response.raise_for_status()
        return response.json()

    async def send_notification(self, payload: NotificationPayload) -> dict:
        url = f"{self.base_url}/v1/notify"
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }
        payload_dict = {
            "to": payload.to,
            "message": payload.message,
            "type": payload.type.value if hasattr(payload.type, "value") else str(payload.type),
        }
        try:
            return await self._send_with_retry(url, payload_dict, headers)
        except Exception as e:
            logger.error(f"Failed to send notification to {payload.to}: {e}")
            raise
