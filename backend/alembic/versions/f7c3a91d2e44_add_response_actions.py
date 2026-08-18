"""add response actions

Revision ID: f7c3a91d2e44
Revises: e482165f0daa
Create Date: 2026-08-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7c3a91d2e44"
down_revision: Union[str, Sequence[str], None] = "e482165f0daa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "response_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("risk_score", sa.SmallInteger(), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("decision_reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ack_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ack_message", sa.Text(), nullable=True),
        sa.Column("relay_state", sa.String(length=64), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "action IN ('log_only', 'alert', 'request_approval', 'isolate_device')",
            name="ck_response_actions_action",
        ),
        sa.CheckConstraint(
            "severity IN ('normal', 'warning', 'critical')",
            name="ck_response_actions_severity",
        ),
        sa.CheckConstraint(
            "status IN ('recorded', 'awaiting_approval', 'pending', 'dispatched', "
            "'executed', 'failed', 'expired', 'cancelled')",
            name="ck_response_actions_status",
        ),
        sa.CheckConstraint("risk_score BETWEEN 0 AND 100", name="ck_response_actions_risk_score"),
        sa.CheckConstraint("policy_version > 0", name="ck_response_actions_policy_version"),
        sa.CheckConstraint("attempt_count >= 0", name="ck_response_actions_attempt_count"),
        sa.CheckConstraint("expires_at > created_at", name="ck_response_actions_expiry"),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["security_events.event_id"],
            name="fk_response_actions_event",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_response_actions"),
        sa.UniqueConstraint(
            "event_id",
            "device_id",
            "action",
            "policy_version",
            name="uq_response_actions_decision",
        ),
    )
    op.create_index(
        "ix_response_actions_pending_claim",
        "response_actions",
        ["device_id", "status", "expires_at", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_response_actions_pending_claim",
        table_name="response_actions",
    )
    op.drop_table("response_actions")
