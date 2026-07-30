from dataclasses import dataclass
import logging
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import (
    IntegrityError,
    OperationalError,
    SQLAlchemyError,
    TimeoutError as SQLAlchemyTimeoutError,
)
from sqlalchemy.orm import Session

from models import Esp32Assessment, SecurityEvent


logger = logging.getLogger(__name__)

RepositoryStatus = Literal[
    "created",
    "duplicate",
    "event_conflict",
    "assessment_conflict",
    "integrity_error",
    "database_unavailable",
    "database_timeout",
    "database_error",
    "internal_persistence_error",
]


@dataclass(frozen=True)
class RepositoryResult:
    status: RepositoryStatus
    retryable: bool = False


class SecurityEventRepository:
    def __init__(self, session: Session):
        self.session = session

    def persist(
        self,
        event_values: dict[str, Any],
        assessment_values: dict[str, Any],
    ) -> RepositoryResult:
        event_id = "<unknown>"
        try:
            event_id = self._safe_event_id(event_values)
            event_created = self._insert_event(event_values)
            if not event_created:
                existing_event_hash = self._event_hash(event_values["event_id"])
                if existing_event_hash != event_values["payload_hash"]:
                    self._safe_rollback(event_id)
                    return RepositoryResult("event_conflict")

            assessment_created = self._insert_assessment(assessment_values)
            if not assessment_created:
                existing_assessment_hash = self._assessment_hash(
                    assessment_values["event_id"]
                )
                if existing_assessment_hash != assessment_values["payload_hash"]:
                    self._safe_rollback(event_id)
                    return RepositoryResult("assessment_conflict")

            self.session.commit()
            if event_created or assessment_created:
                return RepositoryResult("created")
            return RepositoryResult("duplicate")
        except SQLAlchemyTimeoutError as exc:
            self._safe_rollback(event_id)
            self._log_failure(event_id, "DATABASE_TIMEOUT", exc)
            return RepositoryResult("database_timeout", retryable=True)
        except OperationalError as exc:
            self._safe_rollback(event_id)
            self._log_failure(event_id, "DATABASE_UNAVAILABLE", exc)
            return RepositoryResult("database_unavailable", retryable=True)
        except IntegrityError as exc:
            self._safe_rollback(event_id)
            self._log_failure(event_id, "INTEGRITY_ERROR", exc)
            return RepositoryResult("integrity_error")
        except SQLAlchemyError as exc:
            self._safe_rollback(event_id)
            self._log_failure(event_id, "DATABASE_ERROR", exc)
            return RepositoryResult("database_error")
        except Exception as exc:
            self._safe_rollback(event_id)
            self._log_failure(
                event_id,
                "INTERNAL_PERSISTENCE_ERROR",
                exc,
            )
            return RepositoryResult("internal_persistence_error")

    def list_security_events(
        self,
        *,
        limit: int,
        offset: int,
    ):
        statement = (
            select(SecurityEvent, Esp32Assessment)
            .outerjoin(
                Esp32Assessment,
                Esp32Assessment.event_id == SecurityEvent.event_id,
            )
            .order_by(
                SecurityEvent.event_timestamp.desc(),
                SecurityEvent.event_id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        return self.session.execute(statement).all()

    def _safe_rollback(self, event_id: str) -> None:
        try:
            self.session.rollback()
        except Exception as exc:
            logger.error(
                "Persistence rollback failed "
                "layer=%s event_id=%s error_code=%s exception_type=%s",
                "repository",
                event_id,
                "ROLLBACK_FAILED",
                type(exc).__name__,
            )

    @staticmethod
    def _safe_event_id(values: dict[str, Any]) -> str:
        event_id = values.get("event_id")
        return event_id if isinstance(event_id, str) else "<unknown>"

    @staticmethod
    def _log_failure(
        event_id: str,
        error_code: str,
        exc: Exception,
    ) -> None:
        logger.error(
            "Persistence operation failed "
            "layer=%s event_id=%s error_code=%s exception_type=%s",
            "repository",
            event_id,
            error_code,
            type(exc).__name__,
        )

    def _insert_event(self, values: dict[str, Any]) -> bool:
        statement = (
            insert(SecurityEvent)
            .values(**values)
            .on_conflict_do_nothing(index_elements=[SecurityEvent.event_id])
            .returning(SecurityEvent.event_id)
        )
        return self.session.execute(statement).scalar_one_or_none() is not None

    def _insert_assessment(self, values: dict[str, Any]) -> bool:
        statement = (
            insert(Esp32Assessment)
            .values(**values)
            .on_conflict_do_nothing(index_elements=[Esp32Assessment.event_id])
            .returning(Esp32Assessment.event_id)
        )
        return self.session.execute(statement).scalar_one_or_none() is not None

    def _event_hash(self, event_id: str) -> bytes | None:
        statement = select(SecurityEvent.payload_hash).where(
            SecurityEvent.event_id == event_id
        )
        return self.session.execute(statement).scalar_one_or_none()

    def _assessment_hash(self, event_id: str) -> bytes | None:
        statement = select(Esp32Assessment.payload_hash).where(
            Esp32Assessment.event_id == event_id
        )
        return self.session.execute(statement).scalar_one_or_none()
