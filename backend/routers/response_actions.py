from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from dependencies import get_db
from repositories.response_action_repository import ResponseActionRepository
from schemas.response_action import (
    ActionStatus,
    CommandAckInput,
    CommandAckResponse,
    CommandRead,
    ResponseActionListResponse,
    ResponseActionRead,
)


router = APIRouter(tags=["response-actions"])


def get_response_action_repository(
    db: Session = Depends(get_db),
) -> ResponseActionRepository:
    return ResponseActionRepository(db)


def require_future_device_authentication() -> None:
    """Extension point for production device HMAC and replay protection."""


@router.get(
    "/api/iot/commands/next",
    response_model=CommandRead,
    responses={204: {"description": "No pending command."}},
    description=(
        "Atomically claims the oldest non-expired pending command. "
        "Device authentication is not implemented; add HMAC and replay "
        "protection before production exposure."
    ),
)
def next_command(
    device_id: str = Query(min_length=1, max_length=128),
    repository: ResponseActionRepository = Depends(
        get_response_action_repository
    ),
    _auth: None = Depends(require_future_device_authentication),
):
    action = repository.claim_next(
        device_id=device_id.strip(),
        now=datetime.now(timezone.utc),
    )
    if action is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return CommandRead(
        command_id=action.id,
        event_id=action.event_id,
        device_id=action.device_id,
        action=action.action,
        severity=action.severity,
        risk_score=action.risk_score,
        expires_at=action.expires_at,
        policy_version=action.policy_version,
    )


@router.post(
    "/api/iot/commands/{command_id}/ack",
    response_model=CommandAckResponse,
)
def acknowledge_command(
    command_id: UUID,
    payload: CommandAckInput,
    repository: ResponseActionRepository = Depends(
        get_response_action_repository
    ),
    _auth: None = Depends(require_future_device_authentication),
):
    result = repository.acknowledge(
        action_id=command_id,
        payload=payload,
        received_at=datetime.now(timezone.utc),
    )
    if result.status == "not_found":
        return JSONResponse(status_code=404, content={"detail": "Command not found"})
    if result.status == "wrong_device":
        return JSONResponse(status_code=403, content={"detail": "Command belongs to another device"})
    if result.status == "conflict":
        return JSONResponse(
            status_code=409,
            content={"detail": "ACK payload conflicts with the stored result", "error_code": "ACK_CONFLICT"},
        )
    if result.status == "not_acknowledgeable":
        return JSONResponse(
            status_code=409,
            content={"detail": "Expired, cancelled, or undispatched command cannot be acknowledged", "error_code": "ACTION_NOT_ACKNOWLEDGEABLE"},
        )
    action = result.action
    return CommandAckResponse(
        command_id=action.id,
        status=action.status,
        duplicate=result.status == "duplicate",
        ack_received_at=action.ack_received_at,
    )


@router.get(
    "/api/response-actions",
    response_model=ResponseActionListResponse,
)
def list_response_actions(
    event_id: str | None = Query(default=None, min_length=1, max_length=128),
    device_id: str | None = Query(default=None, min_length=1, max_length=128),
    action_status: ActionStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    repository: ResponseActionRepository = Depends(
        get_response_action_repository
    ),
) -> ResponseActionListResponse:
    actions = repository.list_actions(
        event_id=event_id,
        device_id=device_id,
        status=action_status,
        limit=limit,
        offset=offset,
    )
    return ResponseActionListResponse(
        items=[ResponseActionRead.model_validate(item) for item in actions],
        limit=limit,
        offset=offset,
        count=len(actions),
    )
