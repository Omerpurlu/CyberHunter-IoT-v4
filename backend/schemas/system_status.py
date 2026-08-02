import json
from datetime import datetime
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


ComponentType = Literal["raspberry_pi", "esp32"]
ReportedStatus = Literal["healthy", "degraded", "error", "starting"]
ComputedStatus = Literal["waiting", "online", "delayed", "offline"]
HeartbeatResultName = Literal[
    "created",
    "updated",
    "duplicate",
    "conflict",
    "temporarily_unavailable",
    "error",
]

SENSITIVE_METADATA_KEYS = {"password", "secret", "token", "api_key", "authorization"}
MAX_METADATA_BYTES = 4096
MAX_METADATA_DEPTH = 5
MAX_METADATA_ITEMS = 64


def _validate_json_value(value: Any, *, depth: int = 0) -> None:
    if depth > MAX_METADATA_DEPTH:
        raise ValueError("metadata nesting is too deep")
    if value is None or isinstance(value, (str, int, float, bool)):
        return
    if isinstance(value, list):
        if len(value) > MAX_METADATA_ITEMS:
            raise ValueError("metadata contains too many items")
        for item in value:
            _validate_json_value(item, depth=depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > MAX_METADATA_ITEMS:
            raise ValueError("metadata contains too many items")
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("metadata keys must be strings")
            if key.strip().casefold() in SENSITIVE_METADATA_KEYS:
                raise ValueError("metadata contains a sensitive key")
            _validate_json_value(item, depth=depth + 1)
        return
    raise ValueError("metadata must contain JSON-compatible values")


class HeartbeatInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_type: ComponentType
    component_id: str = Field(min_length=1, max_length=128)
    reported_status: ReportedStatus
    sequence: int = Field(ge=0)
    reported_by: str | None = Field(default=None, max_length=128)
    software_version: str | None = Field(default=None, max_length=64)
    device_timestamp: AwareDatetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("component_type", "reported_status", mode="before")
    @classmethod
    def trim_controlled_values(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("component_id", "reported_by", "software_version", mode="before")
    @classmethod
    def trim_strings(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("value must not be empty")
        return value

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        _validate_json_value(value)
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(encoded) > MAX_METADATA_BYTES:
            raise ValueError("metadata is too large")
        return value


class HeartbeatResponse(BaseModel):
    component_type: ComponentType
    component_id: str
    accepted_sequence: int
    result: HeartbeatResultName
    last_seen: datetime | None
    error_code: str | None = None


class ComponentStatusRead(BaseModel):
    component_type: ComponentType
    component_id: str
    computed_status: ComputedStatus
    reported_status: ReportedStatus | None
    last_seen: datetime | None
    age_seconds: float | None
    sequence: int | None
    software_version: str | None
    source: Literal["heartbeat"] = "heartbeat"


class SystemStatusResponse(BaseModel):
    generated_at: datetime
    components: list[ComponentStatusRead]


class HealthComponent(BaseModel):
    status: str
    query_ms: float | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded"]
    generated_at: datetime
    fastapi: HealthComponent
    postgresql: HealthComponent
