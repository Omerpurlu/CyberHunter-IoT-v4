from typing import Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    IPvAnyAddress,
    StrictBool,
)


class SecurityEventInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event_id: str = Field(min_length=1, max_length=128)
    event_timestamp: AwareDatetime = Field(alias="timestamp")
    source_ip: IPvAnyAddress
    destination_port: int = Field(ge=1, le=65535)
    protocol: str = Field(min_length=1, max_length=32)
    event_type: str = Field(min_length=1, max_length=64)
    command: str | None = None
    tactic: str | None = Field(default=None, max_length=64)
    input_risk_score: int = Field(ge=0, le=100)
    esp32_risk_score: int = Field(ge=0, le=100)
    esp32_decision: str = Field(min_length=1, max_length=32)
    esp32_processed: StrictBool
    device_id: str = Field(min_length=1, max_length=128)

class PersistenceResult(BaseModel):
    success: bool
    event_id: str
    status: Literal[
        "created",
        "duplicate",
        "conflict",
        "rejected",
        "temporarily_unavailable",
        "error",
    ]
    duplicate: bool = False
    retryable: bool = False
    error_code: str | None = None


class Esp32AssessmentRead(BaseModel):
    device_id: str
    risk_score: int
    decision: str
    processed: bool
    assessed_at: AwareDatetime | None
    received_at: AwareDatetime


class SecurityEventRead(BaseModel):
    event_id: str
    event_timestamp: AwareDatetime
    source_ip: str
    destination_port: int
    protocol: str
    event_type: str
    command: str | None
    tactic: str | None
    input_risk_score: int
    received_at: AwareDatetime
    assessment: Esp32AssessmentRead | None


class SecurityEventListResponse(BaseModel):
    items: list[SecurityEventRead]
    limit: int
    offset: int
    count: int
