from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from uuid import uuid4
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.dialects.postgresql import JSONB

from database import Base


class LedLog(Base):
    __tablename__ = "LedLoglari"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)
    led = Column(String)
    sequence = Column(BigInteger)
    device_timestamp = Column(BigInteger)
    nonce = Column(String)
    server_received_at = Column(BigInteger)
    message = Column(Text, nullable=True)
    encryption_version = Column(Integer, nullable=False, server_default="0")
    md5_checksum = Column(String(32), nullable=True)


class DeviceCommand(Base):
    __tablename__ = "CihazEmirleri"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)
    komut = Column(String)
    durum = Column(String, default="bekliyor")
    olusturulma_zamani = Column(BigInteger)
    message = Column(Text, nullable=True)
    encryption_version = Column(Integer, nullable=False, server_default="0")
    md5_checksum = Column(String(32), nullable=True)


class SecurityEvent(Base):
    __tablename__ = "security_events"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(event_id)) > 0",
            name="ck_security_events_event_id_nonempty",
        ),
        CheckConstraint(
            "destination_port BETWEEN 1 AND 65535",
            name="ck_security_events_destination_port",
        ),
        CheckConstraint(
            "length(btrim(protocol)) > 0",
            name="ck_security_events_protocol_nonempty",
        ),
        CheckConstraint(
            "protocol = lower(protocol)",
            name="ck_security_events_protocol_lowercase",
        ),
        CheckConstraint(
            "length(btrim(event_type)) > 0",
            name="ck_security_events_event_type_nonempty",
        ),
        CheckConstraint(
            "input_risk_score BETWEEN 0 AND 100",
            name="ck_security_events_input_risk_score",
        ),
        CheckConstraint(
            "octet_length(payload_hash) = 32",
            name="ck_security_events_payload_hash",
        ),
        CheckConstraint(
            "hash_version > 0",
            name="ck_security_events_hash_version",
        ),
        Index(
            "ix_security_events_event_timestamp",
            text("event_timestamp DESC"),
        ),
        Index(
            "ix_security_events_source_ip_timestamp",
            "source_ip",
            text("event_timestamp DESC"),
        ),
        Index(
            "ix_security_events_protocol_timestamp",
            "protocol",
            text("event_timestamp DESC"),
        ),
        Index(
            "ix_security_events_event_type_timestamp",
            "event_type",
            text("event_timestamp DESC"),
        ),
    )

    event_id = Column(String(128), primary_key=True)
    event_timestamp = Column(DateTime(timezone=True), nullable=False)
    source_ip = Column(INET, nullable=False)
    destination_port = Column(Integer, nullable=False)
    protocol = Column(String(32), nullable=False)
    event_type = Column(String(64), nullable=False)
    command = Column(Text, nullable=True)
    tactic = Column(String(64), nullable=True)
    input_risk_score = Column(SmallInteger, nullable=False)
    payload_hash = Column(LargeBinary, nullable=False)
    hash_version = Column(
        SmallInteger,
        nullable=False,
        server_default=text("1"),
    )
    received_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class Esp32Assessment(Base):
    __tablename__ = "esp32_assessments"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(device_id)) > 0",
            name="ck_esp32_assessments_device_id_nonempty",
        ),
        CheckConstraint(
            "esp32_risk_score BETWEEN 0 AND 100",
            name="ck_esp32_assessments_risk_score",
        ),
        CheckConstraint(
            "length(btrim(esp32_decision)) > 0",
            name="ck_esp32_assessments_decision_nonempty",
        ),
        CheckConstraint(
            "esp32_decision = lower(esp32_decision)",
            name="ck_esp32_assessments_decision_lowercase",
        ),
        CheckConstraint(
            "octet_length(payload_hash) = 32",
            name="ck_esp32_assessments_payload_hash",
        ),
        CheckConstraint(
            "hash_version > 0",
            name="ck_esp32_assessments_hash_version",
        ),
        Index("ix_esp32_assessments_device_id", "device_id"),
        Index("ix_esp32_assessments_decision", "esp32_decision"),
        Index(
            "ix_esp32_assessments_risk_score",
            text("esp32_risk_score DESC"),
        ),
    )

    event_id = Column(
        String(128),
        ForeignKey(
            "security_events.event_id",
            name="fk_esp32_assessments_event",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    device_id = Column(String(128), nullable=False)
    esp32_risk_score = Column(SmallInteger, nullable=False)
    esp32_decision = Column(String(32), nullable=False)
    esp32_processed = Column(Boolean, nullable=False)
    assessed_at = Column(DateTime(timezone=True), nullable=True)
    payload_hash = Column(LargeBinary, nullable=False)
    hash_version = Column(
        SmallInteger,
        nullable=False,
        server_default=text("1"),
    )
    received_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class ResponseAction(Base):
    __tablename__ = "response_actions"
    __table_args__ = (
        CheckConstraint(
            "action IN ('log_only', 'alert', 'request_approval', 'isolate_device')",
            name="ck_response_actions_action",
        ),
        CheckConstraint(
            "severity IN ('normal', 'warning', 'critical')",
            name="ck_response_actions_severity",
        ),
        CheckConstraint(
            "status IN ('recorded', 'awaiting_approval', 'pending', 'dispatched', "
            "'executed', 'failed', 'expired', 'cancelled')",
            name="ck_response_actions_status",
        ),
        CheckConstraint(
            "risk_score BETWEEN 0 AND 100",
            name="ck_response_actions_risk_score",
        ),
        CheckConstraint(
            "policy_version > 0",
            name="ck_response_actions_policy_version",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_response_actions_attempt_count",
        ),
        CheckConstraint(
            "expires_at > created_at",
            name="ck_response_actions_expiry",
        ),
        UniqueConstraint(
            "event_id",
            "device_id",
            "action",
            "policy_version",
            name="uq_response_actions_decision",
        ),
        Index(
            "ix_response_actions_pending_claim",
            "device_id",
            "status",
            "expires_at",
            "created_at",
        ),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    event_id = Column(
        String(128),
        ForeignKey(
            "security_events.event_id",
            name="fk_response_actions_event",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    device_id = Column(String(128), nullable=False)
    action = Column(String(32), nullable=False)
    severity = Column(String(16), nullable=False)
    status = Column(String(32), nullable=False)
    risk_score = Column(SmallInteger, nullable=False)
    policy_version = Column(Integer, nullable=False)
    decision_reason = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    dispatched_at = Column(DateTime(timezone=True), nullable=True)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    ack_received_at = Column(DateTime(timezone=True), nullable=True)
    ack_message = Column(Text, nullable=True)
    relay_state = Column(String(64), nullable=True)
    attempt_count = Column(Integer, nullable=False, server_default=text("0"))
    last_error = Column(Text, nullable=True)


class SystemComponentStatus(Base):
    __tablename__ = "system_component_status"
    __table_args__ = (
        CheckConstraint(
            "component_type IN ('raspberry_pi', 'esp32')",
            name="ck_system_component_status_component_type",
        ),
        CheckConstraint(
            "reported_status IN ('healthy', 'degraded', 'error', 'starting')",
            name="ck_system_component_status_reported_status",
        ),
        CheckConstraint(
            "sequence >= 0",
            name="ck_system_component_status_sequence_nonnegative",
        ),
        Index("ix_system_component_status_last_seen", text("last_seen DESC")),
    )

    component_type = Column(String(32), primary_key=True)
    component_id = Column(String(128), primary_key=True)
    reported_status = Column(String(32), nullable=False)
    sequence = Column(BigInteger, nullable=False)
    last_seen = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    reported_by = Column(String(128), nullable=True)
    software_version = Column(String(64), nullable=True)
    device_timestamp = Column(DateTime(timezone=True), nullable=True)
    metadata_json = Column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
