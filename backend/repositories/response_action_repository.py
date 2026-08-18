from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from models import ResponseAction
from schemas.response_action import CommandAckInput


CreateStatus = Literal["created", "duplicate"]
AckStatus = Literal[
    "updated",
    "duplicate",
    "conflict",
    "wrong_device",
    "not_found",
    "not_acknowledgeable",
]


@dataclass(frozen=True)
class ActionCreateResult:
    status: CreateStatus
    action: ResponseAction


@dataclass(frozen=True)
class ActionAckResult:
    status: AckStatus
    action: ResponseAction | None = None


class ResponseActionRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_if_not_exists(self, values: dict[str, Any]) -> ActionCreateResult:
        statement = (
            insert(ResponseAction)
            .values(**values)
            .on_conflict_do_nothing(
                constraint="uq_response_actions_decision"
            )
            .returning(ResponseAction)
        )
        created = self.session.execute(statement).scalar_one_or_none()
        if created is not None:
            self.session.commit()
            return ActionCreateResult("created", created)

        existing = self.session.execute(
            select(ResponseAction).where(
                ResponseAction.event_id == values["event_id"],
                ResponseAction.device_id == values["device_id"],
                ResponseAction.action == values["action"],
                ResponseAction.policy_version == values["policy_version"],
            )
        ).scalar_one()
        self.session.commit()
        return ActionCreateResult("duplicate", existing)

    def get_by_id(self, action_id: UUID) -> ResponseAction | None:
        return self.session.execute(
            select(ResponseAction).where(ResponseAction.id == action_id)
        ).scalar_one_or_none()

    def list_actions(
        self,
        *,
        event_id: str | None,
        device_id: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> list[ResponseAction]:
        statement = select(ResponseAction)
        if event_id is not None:
            statement = statement.where(ResponseAction.event_id == event_id)
        if device_id is not None:
            statement = statement.where(ResponseAction.device_id == device_id)
        if status is not None:
            statement = statement.where(ResponseAction.status == status)
        statement = (
            statement.order_by(
                ResponseAction.created_at.desc(),
                ResponseAction.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.execute(statement).scalars().all())

    def claim_next(
        self,
        *,
        device_id: str,
        now: datetime,
    ) -> ResponseAction | None:
        statement = (
            select(ResponseAction)
            .where(
                ResponseAction.device_id == device_id,
                ResponseAction.status == "pending",
                ResponseAction.expires_at > now,
            )
            .order_by(ResponseAction.created_at.asc(), ResponseAction.id.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        action = self.session.execute(statement).scalar_one_or_none()
        if action is None:
            self.session.commit()
            return None
        action.status = "dispatched"
        action.dispatched_at = now
        action.attempt_count += 1
        self.session.commit()
        self.session.refresh(action)
        return action

    def acknowledge(
        self,
        *,
        action_id: UUID,
        payload: CommandAckInput,
        received_at: datetime,
    ) -> ActionAckResult:
        action = self.session.execute(
            select(ResponseAction)
            .where(ResponseAction.id == action_id)
            .with_for_update()
        ).scalar_one_or_none()
        if action is None:
            self.session.rollback()
            return ActionAckResult("not_found")
        if action.device_id != payload.device_id:
            self.session.rollback()
            return ActionAckResult("wrong_device", action)
        if action.status in {"executed", "failed"}:
            if self._same_ack(action, payload):
                self.session.commit()
                return ActionAckResult("duplicate", action)
            self.session.rollback()
            return ActionAckResult("conflict", action)
        if action.status != "dispatched":
            self.session.rollback()
            return ActionAckResult("not_acknowledgeable", action)

        action.status = payload.result
        action.executed_at = payload.executed_at
        action.ack_received_at = received_at
        action.relay_state = payload.relay_state
        action.ack_message = payload.ack_message
        action.last_error = payload.ack_message if payload.result == "failed" else None
        self.session.commit()
        self.session.refresh(action)
        return ActionAckResult("updated", action)

    @staticmethod
    def _same_ack(action: ResponseAction, payload: CommandAckInput) -> bool:
        return (
            action.status == payload.result
            and action.executed_at == payload.executed_at
            and action.relay_state == payload.relay_state
            and action.ack_message == payload.ack_message
        )
