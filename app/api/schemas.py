from pydantic import BaseModel, Field
from app.domain.models import RequestStatus


class CreateRequestInput(BaseModel):
    user_input: str = Field(..., example="Manda un mail a feda@test.com diciendo hola")


class CreateRequestOutput(BaseModel):
    id: str = Field(..., example="550e8400-e29b-41d4-a716-446655440000")


class RequestStatusOutput(BaseModel):
    id: str = Field(..., example="550e8400-e29b-41d4-a716-446655440000")
    status: RequestStatus = Field(..., example=RequestStatus.QUEUED)


class ProcessRequestOutput(BaseModel):
    id: str
    status: RequestStatus
