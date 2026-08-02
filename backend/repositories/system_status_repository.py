from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any, Literal

from sqlalchemy import literal_column, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import OperationalError, SQLAlchemyError, TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.orm import Session

from models import SystemComponentStatus


logger = logging.getLogger(__name__)
RepositoryStatus = Literal["created", "updated", "duplicate", "conflict", "database_unavailable", "database_error"]


@dataclass(frozen=True)
class SystemStatusRepositoryResult:
    status: RepositoryStatus
    sequence: int
    last_seen: datetime | None = None
    retryable: bool = False


class SystemStatusRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert(self, values: dict[str, Any]) -> SystemStatusRepositoryResult:
        identity = (values["component_type"], values["component_id"])
        try:
            statement = insert(SystemComponentStatus).values(**values)
            statement = statement.on_conflict_do_update(
                index_elements=[
                    SystemComponentStatus.component_type,
                    SystemComponentStatus.component_id,
                ],
                set_={
                    "reported_status": statement.excluded.reported_status,
                    "sequence": statement.excluded.sequence,
                    "last_seen": statement.excluded.last_seen,
                    "reported_by": statement.excluded.reported_by,
                    "software_version": statement.excluded.software_version,
                    "device_timestamp": statement.excluded.device_timestamp,
                    "metadata": statement.excluded["metadata"],
                    "updated_at": statement.excluded.updated_at,
                },
                where=statement.excluded.sequence > SystemComponentStatus.sequence,
            ).returning(
                SystemComponentStatus.sequence,
                SystemComponentStatus.last_seen,
                literal_column("xmax = 0"),
            )
            row = self.session.execute(statement).one_or_none()
            if row is not None:
                self.session.commit()
                return SystemStatusRepositoryResult(
                    "created" if row[2] else "updated",
                    sequence=row[0],
                    last_seen=row[1],
                )

            current = self._get(*identity)
            if current is None:
                raise RuntimeError("upsert returned no row for a missing identity")
            status = "duplicate" if self._same_client_payload(current, values) else "conflict"
            self.session.commit()
            return SystemStatusRepositoryResult(status, current.sequence, current.last_seen)
        except (OperationalError, SQLAlchemyTimeoutError) as exc:
            self._rollback()
            self._log("DATABASE_UNAVAILABLE", exc)
            return SystemStatusRepositoryResult("database_unavailable", values["sequence"], retryable=True)
        except SQLAlchemyError as exc:
            self._rollback()
            self._log("DATABASE_ERROR", exc)
            return SystemStatusRepositoryResult("database_error", values["sequence"])
        except Exception as exc:
            self._rollback()
            self._log("DATABASE_ERROR", exc)
            return SystemStatusRepositoryResult("database_error", values["sequence"])

    def get_expected(self, identities: list[tuple[str, str]]) -> dict[tuple[str, str], SystemComponentStatus]:
        if not identities:
            return {}
        statement = select(SystemComponentStatus).where(
            tuple_(SystemComponentStatus.component_type, SystemComponentStatus.component_id).in_(identities)
        )
        records = self.session.execute(statement).scalars().all()
        return {(record.component_type, record.component_id): record for record in records}

    def _get(self, component_type: str, component_id: str):
        statement = select(SystemComponentStatus).where(
            SystemComponentStatus.component_type == component_type,
            SystemComponentStatus.component_id == component_id,
        )
        return self.session.execute(statement).scalar_one_or_none()

    @staticmethod
    def _same_client_payload(record, values: dict[str, Any]) -> bool:
        return all(
            getattr(record, attribute) == values[key]
            for attribute, key in (
                ("component_type", "component_type"),
                ("component_id", "component_id"),
                ("reported_status", "reported_status"),
                ("sequence", "sequence"),
                ("reported_by", "reported_by"),
                ("software_version", "software_version"),
                ("device_timestamp", "device_timestamp"),
                ("metadata_json", "metadata_json"),
            )
        )

    def _rollback(self) -> None:
        try:
            self.session.rollback()
        except Exception:
            logger.error("System status rollback failed error_code=ROLLBACK_FAILED")

    @staticmethod
    def _log(code: str, exc: Exception) -> None:
        logger.error("System status persistence failed error_code=%s exception_type=%s", code, type(exc).__name__)
