import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from repositories.security_event_repository import (
    RepositoryResult,
    SecurityEventRepository,
)
from schemas.security_event import PersistenceResult, SecurityEventInput


HASH_VERSION = 1
logger = logging.getLogger(__name__)


def _canonical_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timestamp must include timezone information")
    normalized = value.astimezone(timezone.utc)
    return normalized.isoformat(timespec="microseconds").replace("+00:00", "Z")


def canonical_sha256(values: dict[str, Any]) -> bytes:
    canonical = json.dumps(
        values,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).digest()


class SecurityEventService:
    def __init__(self, repository: SecurityEventRepository):
        self.repository = repository

    def persist(
        self,
        payload: SecurityEventInput | dict[str, Any],
    ) -> PersistenceResult:
        event_id = "<unknown>"
        try:
            event_id = self._safe_event_id(payload)
            return self._persist_with_validation(payload)
        except Exception as exc:
            logger.error(
                "Persistence service failed "
                "layer=%s event_id=%s error_code=%s exception_type=%s",
                "service",
                event_id,
                "INTERNAL_PERSISTENCE_ERROR",
                type(exc).__name__,
            )
            return PersistenceResult(
                success=False,
                event_id=event_id,
                status="error",
                error_code="INTERNAL_PERSISTENCE_ERROR",
            )

    def _persist_with_validation(
        self,
        payload: SecurityEventInput | dict[str, Any],
    ) -> PersistenceResult:
        if isinstance(payload, dict):
            event_id = str(payload.get("event_id", ""))
            try:
                payload = SecurityEventInput.model_validate(payload)
            except ValidationError:
                return PersistenceResult(
                    success=False,
                    event_id=event_id,
                    status="rejected",
                    error_code="VALIDATION_ERROR",
                )

        protocol = payload.protocol.strip().lower()
        event_type = payload.event_type.strip()
        decision = payload.esp32_decision.strip().lower()
        event_id = payload.event_id.strip()
        device_id = payload.device_id.strip()
        timestamp = _canonical_timestamp(payload.event_timestamp)

        event_projection = {
            "event_id": event_id,
            "timestamp": timestamp,
            "source_ip": str(payload.source_ip),
            "destination_port": payload.destination_port,
            "protocol": protocol,
            "event_type": event_type,
            "command": payload.command,
            "tactic": payload.tactic,
            "input_risk_score": payload.input_risk_score,
        }
        assessment_projection = {
            "event_id": event_id,
            "device_id": device_id,
            "esp32_risk_score": payload.esp32_risk_score,
            "esp32_decision": decision,
            "esp32_processed": payload.esp32_processed,
        }

        event_values = {
            "event_id": event_id,
            "event_timestamp": payload.event_timestamp,
            "source_ip": str(payload.source_ip),
            "destination_port": payload.destination_port,
            "protocol": protocol,
            "event_type": event_type,
            "command": payload.command,
            "tactic": payload.tactic,
            "input_risk_score": payload.input_risk_score,
            "payload_hash": canonical_sha256(event_projection),
            "hash_version": HASH_VERSION,
        }
        assessment_values = {
            "event_id": event_id,
            "device_id": device_id,
            "esp32_risk_score": payload.esp32_risk_score,
            "esp32_decision": decision,
            "esp32_processed": payload.esp32_processed,
            "assessed_at": None,
            "payload_hash": canonical_sha256(assessment_projection),
            "hash_version": HASH_VERSION,
        }

        repository_result = self.repository.persist(
            event_values,
            assessment_values,
        )
        return self._to_result(event_id, repository_result)

    @staticmethod
    def _safe_event_id(
        payload: SecurityEventInput | dict[str, Any],
    ) -> str:
        if isinstance(payload, SecurityEventInput):
            return payload.event_id
        event_id = payload.get("event_id")
        return event_id if isinstance(event_id, str) else "<unknown>"

    @staticmethod
    def _to_result(
        event_id: str,
        result: RepositoryResult,
    ) -> PersistenceResult:
        if result.status == "created":
            return PersistenceResult(
                success=True,
                event_id=event_id,
                status="created",
            )
        if result.status == "duplicate":
            return PersistenceResult(
                success=True,
                event_id=event_id,
                status="duplicate",
                duplicate=True,
            )

        mappings = {
            "event_conflict": ("conflict", "EVENT_ID_CONFLICT"),
            "assessment_conflict": ("conflict", "ASSESSMENT_CONFLICT"),
            "integrity_error": ("rejected", "INTEGRITY_ERROR"),
            "database_unavailable": (
                "temporarily_unavailable",
                "DATABASE_UNAVAILABLE",
            ),
            "database_timeout": (
                "temporarily_unavailable",
                "DATABASE_TIMEOUT",
            ),
            "database_error": ("error", "DATABASE_ERROR"),
            "internal_persistence_error": (
                "error",
                "INTERNAL_PERSISTENCE_ERROR",
            ),
        }
        status, error_code = mappings[result.status]
        return PersistenceResult(
            success=False,
            event_id=event_id,
            status=status,
            error_code=error_code,
            retryable=result.retryable,
        )
