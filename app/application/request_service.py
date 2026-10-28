import uuid
import logging
from typing import Optional
from app.domain.models import NotificationRequest, RequestStatus
from app.ports.repository import RequestRepository
from app.ports.ai_extractor import AIExtractor
from app.ports.notification_sender import NotificationSender
from app.application.guardrails import GuardrailsService, AIRefusalError, GuardrailValidationError

logger = logging.getLogger("RequestService")


class RequestNotFoundError(Exception):
    """Exception raised when a request is not found."""
    pass


class RequestService:
    """
    Application Service orchestrating the notification processing pipeline:
    1. Ingestion of user intent.
    2. Asynchronous cognitive extraction via AI.
    3. Defensive guardrails validation & normalization.
    4. Resilient notification delivery.
    """

    def __init__(
        self,
        repository: RequestRepository,
        ai_extractor: AIExtractor,
        notification_sender: NotificationSender,
    ) -> None:
        self.repository = repository
        self.ai_extractor = ai_extractor
        self.notification_sender = notification_sender

    async def create_request(self, user_input: str) -> str:
        """Creates and stores a new request in QUEUED state."""
        request_id = str(uuid.uuid4())
        request = NotificationRequest(
            id=request_id,
            user_input=user_input,
            status=RequestStatus.QUEUED,
        )
        await self.repository.save(request)
        logger.info(f"Created request {request_id} in QUEUED status")
        return request_id

    async def get_request(self, request_id: str) -> Optional[NotificationRequest]:
        """Retrieves a request by its ID."""
        return await self.repository.get_by_id(request_id)

    async def process_request(self, request_id: str) -> None:
        """
        Executes the extraction and notification pipeline.
        Designed to be run as an asynchronous background task.
        """
        request = await self.repository.get_by_id(request_id)
        if not request:
            logger.warning(f"Cannot process non-existent request: {request_id}")
            return

        # 1. Transition to PROCESSING state
        request.status = RequestStatus.PROCESSING
        await self.repository.update(request)
        logger.info(f"Request {request_id} transitioned to PROCESSING")

        try:
            # 2. Extract intent via LLM
            raw_ai_response = await self.ai_extractor.extract_intent(request.user_input)

            # 3. Clean, repair and validate through Guardrails
            payload = GuardrailsService.process_and_validate(
                raw_content=raw_ai_response,
                user_input=request.user_input,
            )
            request.extracted_data = payload

            # 4. Dispatch notification through resilient sender
            await self.notification_sender.send_notification(payload)

            # 5. Mark as successfully SENT
            request.status = RequestStatus.SENT
            logger.info(f"Request {request_id} successfully delivered and marked as SENT")

        except (AIRefusalError, GuardrailValidationError) as e:
            logger.warning(f"Request {request_id} failed cognitive validation: {e}")
            request.status = RequestStatus.FAILED
            request.error = str(e)

        except Exception as e:
            logger.error(f"Request {request_id} failed during processing: {e}")
            request.status = RequestStatus.FAILED
            request.error = str(e)

        finally:
            await self.repository.update(request)
