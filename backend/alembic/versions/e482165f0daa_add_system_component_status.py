"""add system component status

Revision ID: e482165f0daa
Revises: b41e9c7a2f10
Create Date: 2026-08-02 22:15:09.846535

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e482165f0daa'
down_revision: Union[str, Sequence[str], None] = 'b41e9c7a2f10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "system_component_status",
        sa.Column("component_type", sa.String(length=32), nullable=False),
        sa.Column("component_id", sa.String(length=128), nullable=False),
        sa.Column("reported_status", sa.String(length=32), nullable=False),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column(
            "last_seen",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("reported_by", sa.String(length=128), nullable=True),
        sa.Column("software_version", sa.String(length=64), nullable=True),
        sa.Column("device_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "component_type IN ('raspberry_pi', 'esp32')",
            name="ck_system_component_status_component_type",
        ),
        sa.CheckConstraint(
            "reported_status IN ('healthy', 'degraded', 'error', 'starting')",
            name="ck_system_component_status_reported_status",
        ),
        sa.CheckConstraint(
            "sequence >= 0",
            name="ck_system_component_status_sequence_nonnegative",
        ),
        sa.PrimaryKeyConstraint(
            "component_type",
            "component_id",
            name="pk_system_component_status",
        ),
    )
    op.create_index(
        "ix_system_component_status_last_seen",
        "system_component_status",
        [sa.literal_column("last_seen DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_system_component_status_last_seen",
        table_name="system_component_status",
    )
    op.drop_table("system_component_status")
