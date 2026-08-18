from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


ActionName = Literal["log_only", "alert", "request_approval", "isolate_device"]
SeverityName = Literal["normal", "warning", "critical"]
ActionStatus = Literal[
    "recorded",
    "awaiting_approval",
    "pending",
    "dispatched",
    "executed",
    "failed",
    "expired",
    "cancelled",
]


class CommandRead(BaseModel):
    command_id: UUID
    event_id: str
    device_id: str
    action: ActionName
    severity: SeverityName
    risk_score: int
    expires_at: datetime
    policy_version: int


class CommandAckInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(min_length=1, max_length=128)
    result: Literal["executed", "failed"]
    executed_at: AwareDatetime
    relay_state: str | None = Field(default=None, max_length=64)
    ack_message: str | None = None


class CommandAckResponse(BaseModel):
    command_id: UUID
    status: Literal["executed", "failed"]
    duplicate: bool
    ack_received_at: datetime


class ResponseActionRead(BaseModel):
    id: UUID
    event_id: str
    device_id: str
    action: ActionName
    severity: SeverityName
    status: ActionStatus
    risk_score: int
    policy_version: int
    decision_reason: str
    created_at: datetime
    expires_at: datetime
    dispatched_at: datetime | None
    executed_at: datetime | None
    ack_received_at: datetime | None
    ack_message: str | None
    relay_state: str | None
    attempt_count: int
    last_error: str | None

    model_config = ConfigDict(from_attributes=True)


class ResponseActionListResponse(BaseModel):
    items: list[ResponseActionRead]
    limit: int
    offset: int
    count: int
