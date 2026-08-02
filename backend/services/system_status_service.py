from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Any

from repositories.system_status_repository import SystemStatusRepository
from schemas.system_status import (
    ComponentStatusRead,
    HeartbeatInput,
    HeartbeatResponse,
    SystemStatusResponse,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HeartbeatServiceResult:
    response: HeartbeatResponse
    http_status: int


def compute_component_status(
    *,
    now: datetime,
    last_seen: datetime | None,
    online_threshold: int,
    offline_threshold: int,
) -> tuple[str, float | None]:
    validate_heartbeat_thresholds(online_threshold, offline_threshold)
    if last_seen is None:
        return "waiting", None
    age = max(0.0, (now - last_seen).total_seconds())
    if age < online_threshold:
        return "online", age
    if age <= offline_threshold:
        return "delayed", age
    return "offline", age


def validate_heartbeat_thresholds(online_threshold: int, offline_threshold: int) -> None:
    if not 0 < online_threshold < offline_threshold:
        raise RuntimeError("Heartbeat thresholds must satisfy 0 < online < offline")


class SystemStatusService:
    def __init__(self, repository: SystemStatusRepository, *, now_provider=None):
        self.repository = repository
        self.now_provider = now_provider or (lambda: datetime.now(timezone.utc))

    def heartbeat(self, payload: HeartbeatInput) -> HeartbeatServiceResult:
        now = self.now_provider()
        values: dict[str, Any] = {
            "component_type": payload.component_type,
            "component_id": payload.component_id,
            "reported_status": payload.reported_status,
            "sequence": payload.sequence,
            "last_seen": now,
            "reported_by": payload.reported_by,
            "software_version": payload.software_version,
            "device_timestamp": payload.device_timestamp,
            "metadata_json": payload.metadata,
            "created_at": now,
            "updated_at": now,
        }
        result = self.repository.upsert(values)
        status_codes = {
            "created": 201,
            "updated": 200,
            "duplicate": 200,
            "conflict": 409,
            "database_unavailable": 503,
            "database_error": 500,
        }
        error_codes = {
            "conflict": "SEQUENCE_CONFLICT",
            "database_unavailable": "DATABASE_UNAVAILABLE",
            "database_error": "INTERNAL_PERSISTENCE_ERROR",
        }
        response_result = {
            "database_unavailable": "temporarily_unavailable",
            "database_error": "error",
        }.get(result.status, result.status)
        return HeartbeatServiceResult(
            HeartbeatResponse(
                component_type=payload.component_type,
                component_id=payload.component_id,
                accepted_sequence=result.sequence,
                result=response_result,
                last_seen=result.last_seen,
                error_code=error_codes.get(result.status),
            ),
            status_codes[result.status],
        )

    def status(
        self,
        *,
        expected: list[tuple[str, str]],
        online_threshold: int,
        offline_threshold: int,
    ) -> SystemStatusResponse:
        validate_heartbeat_thresholds(online_threshold, offline_threshold)
        now = self.now_provider()
        records = self.repository.get_expected(expected)
        components = []
        for component_type, component_id in expected:
            record = records.get((component_type, component_id))
            computed, age = compute_component_status(
                now=now,
                last_seen=record.last_seen if record else None,
                online_threshold=online_threshold,
                offline_threshold=offline_threshold,
            )
            components.append(
                ComponentStatusRead(
                    component_type=component_type,
                    component_id=component_id,
                    computed_status=computed,
                    reported_status=record.reported_status if record else None,
                    last_seen=record.last_seen if record else None,
                    age_seconds=age,
                    sequence=record.sequence if record else None,
                    software_version=record.software_version if record else None,
                )
            )
        return SystemStatusResponse(generated_at=now, components=components)
