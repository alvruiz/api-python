from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class RequestStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"


class NotificationType(str, Enum):
    EMAIL = "email"
    SMS = "sms"


class NotificationPayload(BaseModel):
    to: str = Field(..., description="The recipient of the notification")
    message: str = Field(..., description="The message of the notification")
    type: NotificationType = Field(..., description="The type of the notification")


class NotificationRequest(BaseModel):
    id: str
    user_input: str
    status: RequestStatus = RequestStatus.QUEUED
    extracted_data: Optional[NotificationPayload] = None
    error: Optional[str] = None
