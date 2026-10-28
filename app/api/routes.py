from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from app.api.schemas import (
    CreateRequestInput,
    CreateRequestOutput,
    RequestStatusOutput,
    ProcessRequestOutput,
)
from app.api.dependencies import get_request_service
from app.application.request_service import RequestService
from app.domain.models import RequestStatus

router = APIRouter(prefix="/v1/requests", tags=["Requests"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateRequestOutput,
    summary="Ingest natural language intent",
    description="Receives a user prompt and queues it for asynchronous processing.",
)
async def create_request(
    payload: CreateRequestInput,
    service: RequestService = Depends(get_request_service),
) -> CreateRequestOutput:
    request_id = await service.create_request(payload.user_input)
    return CreateRequestOutput(id=request_id)


@router.post(
    "/{request_id}/process",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ProcessRequestOutput,
    summary="Trigger asynchronous extraction and notification",
    description="Dispatches cognitive extraction and notification delivery to a background task.",
)
async def process_request(
    request_id: str,
    background_tasks: BackgroundTasks,
    service: RequestService = Depends(get_request_service),
) -> ProcessRequestOutput:
    existing = await service.get_request(request_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Request with id '{request_id}' not found",
        )

    # Dispatch to background task to maintain ultra-fast API response time (<400ms)
    background_tasks.add_task(service.process_request, request_id)

    return ProcessRequestOutput(id=request_id, status=RequestStatus.PROCESSING)


@router.get(
    "/{request_id}",
    status_code=status.HTTP_200_OK,
    response_model=RequestStatusOutput,
    summary="Query request processing status",
    description="Retrieves the current status of the request (queued, processing, sent, failed).",
)
async def get_request_status(
    request_id: str,
    service: RequestService = Depends(get_request_service),
) -> RequestStatusOutput:
    request = await service.get_request(request_id)
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Request with id '{request_id}' not found",
        )

    return RequestStatusOutput(id=request.id, status=request.status)
