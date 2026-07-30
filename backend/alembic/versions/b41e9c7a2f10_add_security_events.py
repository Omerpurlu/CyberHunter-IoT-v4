"""add security events and esp32 assessments

Revision ID: b41e9c7a2f10
Revises: 6b9850c2d44d
Create Date: 2026-07-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b41e9c7a2f10"
down_revision: Union[str, Sequence[str], None] = "6b9850c2d44d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "security_events",
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column(
            "event_timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("source_ip", postgresql.INET(), nullable=False),
        sa.Column("destination_port", sa.Integer(), nullable=False),
        sa.Column("protocol", sa.String(length=32), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("command", sa.Text(), nullable=True),
        sa.Column("tactic", sa.String(length=64), nullable=True),
        sa.Column("input_risk_score", sa.SmallInteger(), nullable=False),
        sa.Column("payload_hash", sa.LargeBinary(), nullable=False),
        sa.Column(
            "hash_version",
            sa.SmallInteger(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(btrim(event_id)) > 0",
            name="ck_security_events_event_id_nonempty",
        ),
        sa.CheckConstraint(
            "destination_port BETWEEN 1 AND 65535",
            name="ck_security_events_destination_port",
        ),
        sa.CheckConstraint(
            "length(btrim(protocol)) > 0",
            name="ck_security_events_protocol_nonempty",
        ),
        sa.CheckConstraint(
            "protocol = lower(protocol)",
            name="ck_security_events_protocol_lowercase",
        ),
        sa.CheckConstraint(
            "length(btrim(event_type)) > 0",
            name="ck_security_events_event_type_nonempty",
        ),
        sa.CheckConstraint(
            "input_risk_score BETWEEN 0 AND 100",
            name="ck_security_events_input_risk_score",
        ),
        sa.CheckConstraint(
            "octet_length(payload_hash) = 32",
            name="ck_security_events_payload_hash",
        ),
        sa.CheckConstraint(
            "hash_version > 0",
            name="ck_security_events_hash_version",
        ),
        sa.PrimaryKeyConstraint("event_id", name="pk_security_events"),
    )
    op.create_index(
        "ix_security_events_event_timestamp",
        "security_events",
        [sa.literal_column("event_timestamp DESC")],
        unique=False,
    )
    op.create_index(
        "ix_security_events_source_ip_timestamp",
        "security_events",
        ["source_ip", sa.literal_column("event_timestamp DESC")],
        unique=False,
    )
    op.create_index(
        "ix_security_events_protocol_timestamp",
        "security_events",
        ["protocol", sa.literal_column("event_timestamp DESC")],
        unique=False,
    )
    op.create_index(
        "ix_security_events_event_type_timestamp",
        "security_events",
        ["event_type", sa.literal_column("event_timestamp DESC")],
        unique=False,
    )

    op.create_table(
        "esp32_assessments",
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("esp32_risk_score", sa.SmallInteger(), nullable=False),
        sa.Column("esp32_decision", sa.String(length=32), nullable=False),
        sa.Column("esp32_processed", sa.Boolean(), nullable=False),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload_hash", sa.LargeBinary(), nullable=False),
        sa.Column(
            "hash_version",
            sa.SmallInteger(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(btrim(device_id)) > 0",
            name="ck_esp32_assessments_device_id_nonempty",
        ),
        sa.CheckConstraint(
            "esp32_risk_score BETWEEN 0 AND 100",
            name="ck_esp32_assessments_risk_score",
        ),
        sa.CheckConstraint(
            "length(btrim(esp32_decision)) > 0",
            name="ck_esp32_assessments_decision_nonempty",
        ),
        sa.CheckConstraint(
            "esp32_decision = lower(esp32_decision)",
            name="ck_esp32_assessments_decision_lowercase",
        ),
        sa.CheckConstraint(
            "octet_length(payload_hash) = 32",
            name="ck_esp32_assessments_payload_hash",
        ),
        sa.CheckConstraint(
            "hash_version > 0",
            name="ck_esp32_assessments_hash_version",
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["security_events.event_id"],
            name="fk_esp32_assessments_event",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("event_id", name="pk_esp32_assessments"),
    )
    op.create_index(
        "ix_esp32_assessments_device_id",
        "esp32_assessments",
        ["device_id"],
        unique=False,
    )
    op.create_index(
        "ix_esp32_assessments_decision",
        "esp32_assessments",
        ["esp32_decision"],
        unique=False,
    )
    op.create_index(
        "ix_esp32_assessments_risk_score",
        "esp32_assessments",
        [sa.literal_column("esp32_risk_score DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_esp32_assessments_risk_score",
        table_name="esp32_assessments",
    )
    op.drop_index(
        "ix_esp32_assessments_decision",
        table_name="esp32_assessments",
    )
    op.drop_index(
        "ix_esp32_assessments_device_id",
        table_name="esp32_assessments",
    )
    op.drop_table("esp32_assessments")

    op.drop_index(
        "ix_security_events_event_type_timestamp",
        table_name="security_events",
    )
    op.drop_index(
        "ix_security_events_protocol_timestamp",
        table_name="security_events",
    )
    op.drop_index(
        "ix_security_events_source_ip_timestamp",
        table_name="security_events",
    )
    op.drop_index(
        "ix_security_events_event_timestamp",
        table_name="security_events",
    )
    op.drop_table("security_events")
