import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import uuid4

from repositories.response_action_repository import (
    ActionCreateResult,
    ResponseActionRepository,
)
from schemas.security_event import SecurityEventInput
from services.risk_policy_evaluator import (
    RiskEvent,
    RiskPolicy,
    RiskPolicyEvaluator,
)
from services.security_event_service import normalize_event_type


logger = logging.getLogger(__name__)
STATUS_BY_ACTION = {
    "log_only": "recorded",
    "alert": "recorded",
    "request_approval": "awaiting_approval",
    "isolate_device": "pending",
}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")


def prototype_policy_from_env() -> RiskPolicy:
    return RiskPolicy(
        organization_type=os.getenv("POLICY_ORGANIZATION_TYPE", "prototype"),
        warning_threshold=int(os.getenv("POLICY_WARNING_THRESHOLD", "40")),
        critical_threshold=int(os.getenv("POLICY_CRITICAL_THRESHOLD", "80")),
        auto_isolate_threshold=int(
            os.getenv("POLICY_AUTO_ISOLATE_THRESHOLD", "80")
        ),
        automatic_shutdown_allowed=_env_bool(
            "POLICY_AUTOMATIC_SHUTDOWN_ALLOWED", False
        ),
        manual_approval_required=_env_bool(
            "POLICY_MANUAL_APPROVAL_REQUIRED", True
        ),
        policy_version=int(os.getenv("POLICY_VERSION", "1")),
    )


class SecurityResponseOrchestrator:
    def __init__(
        self,
        repository: ResponseActionRepository,
        *,
        policy_provider: Callable[[], RiskPolicy] = prototype_policy_from_env,
        now_provider: Callable[[], datetime] | None = None,
        ttl_seconds: int | None = None,
    ):
        self.repository = repository
        self.policy_provider = policy_provider
        self.now_provider = now_provider or (lambda: datetime.now(timezone.utc))
        self.ttl_seconds = ttl_seconds or int(
            os.getenv("RESPONSE_ACTION_TTL_SECONDS", "300")
        )
        if self.ttl_seconds <= 0:
            raise ValueError("RESPONSE_ACTION_TTL_SECONDS must be positive")

    def process(self, payload: SecurityEventInput) -> ActionCreateResult:
        policy = self.policy_provider()
        decision = RiskPolicyEvaluator.evaluate(
            policy,
            RiskEvent(
                event_type=normalize_event_type(payload.event_type),
                risk_score=payload.input_risk_score,
            ),
        )
        now = self.now_provider()
        return self.repository.create_if_not_exists(
            {
                "id": uuid4(),
                "event_id": payload.event_id.strip(),
                "device_id": payload.device_id.strip(),
                "action": decision.action,
                "severity": decision.severity,
                "status": STATUS_BY_ACTION[decision.action],
                "risk_score": decision.risk_score,
                "policy_version": decision.policy_version,
                "decision_reason": decision.reason,
                "created_at": now,
                "expires_at": now + timedelta(seconds=self.ttl_seconds),
                "attempt_count": 0,
            }
        )
