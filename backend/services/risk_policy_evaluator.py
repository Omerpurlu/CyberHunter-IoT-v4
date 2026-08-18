from dataclasses import dataclass
from typing import Literal


Severity = Literal["normal", "warning", "critical"]
Action = Literal[
    "log_only",
    "alert",
    "request_approval",
    "isolate_device",
    "isolate_network",
]
EventType = Literal[
    "normal_benign",
    "unknown",
    "reconnaissance",
    "credential_attack",
    "web_attack",
    "spoofing_mitm",
    "dos_ddos",
    "malware_botnet",
]

SUPPORTED_EVENT_TYPES = frozenset(
    {
        "normal_benign",
        "unknown",
        "reconnaissance",
        "credential_attack",
        "web_attack",
        "spoofing_mitm",
        "dos_ddos",
        "malware_botnet",
    }
)


class PolicyValidationError(ValueError):
    """Raised when a risk policy cannot be evaluated safely."""


class EventValidationError(ValueError):
    """Raised when an event is outside the evaluator contract."""


def _validate_score(name: str, value: int, error_type: type[ValueError]) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise error_type(f"{name} must be an integer")
    if not 0 <= value <= 100:
        raise error_type(f"{name} must be between 0 and 100")


@dataclass(frozen=True)
class RiskPolicy:
    organization_type: str
    warning_threshold: int
    critical_threshold: int
    auto_isolate_threshold: int
    automatic_shutdown_allowed: bool
    manual_approval_required: bool
    policy_version: int

    def __post_init__(self) -> None:
        if not isinstance(self.organization_type, str) or not self.organization_type.strip():
            raise PolicyValidationError("organization_type must not be empty")
        _validate_score(
            "warning_threshold",
            self.warning_threshold,
            PolicyValidationError,
        )
        _validate_score(
            "critical_threshold",
            self.critical_threshold,
            PolicyValidationError,
        )
        _validate_score(
            "auto_isolate_threshold",
            self.auto_isolate_threshold,
            PolicyValidationError,
        )
        if self.warning_threshold > self.critical_threshold:
            raise PolicyValidationError(
                "warning_threshold must not exceed critical_threshold"
            )
        if not isinstance(self.automatic_shutdown_allowed, bool):
            raise PolicyValidationError(
                "automatic_shutdown_allowed must be a boolean"
            )
        if not isinstance(self.manual_approval_required, bool):
            raise PolicyValidationError(
                "manual_approval_required must be a boolean"
            )
        if (
            isinstance(self.policy_version, bool)
            or not isinstance(self.policy_version, int)
            or self.policy_version <= 0
        ):
            raise PolicyValidationError("policy_version must be a positive integer")


@dataclass(frozen=True)
class RiskEvent:
    event_type: EventType
    risk_score: int

    def __post_init__(self) -> None:
        if self.event_type not in SUPPORTED_EVENT_TYPES:
            raise EventValidationError(
                "event_type must be a supported canonical AI class"
            )
        _validate_score("risk_score", self.risk_score, EventValidationError)


@dataclass(frozen=True)
class PolicyDecision:
    severity: Severity
    action: Action
    risk_score: int
    event_type: EventType
    policy_version: int
    reason: str


class RiskPolicyEvaluator:
    """Deterministically evaluates canonical events without side effects."""

    @staticmethod
    def evaluate(policy: RiskPolicy, event: RiskEvent) -> PolicyDecision:
        severity = RiskPolicyEvaluator._severity(policy, event.risk_score)

        if event.event_type == "unknown":
            action: Action = "alert"
            reason = (
                "Unknown events require manual or additional review; "
                "automatic isolation is disabled"
            )
        elif severity == "normal":
            action = "log_only"
            reason = "Risk is below the warning threshold"
        elif severity == "warning":
            action = "alert"
            reason = "Risk reached the warning threshold"
        elif policy.manual_approval_required:
            action = "request_approval"
            reason = "Critical risk requires manual approval for this organization"
        elif (
            event.risk_score >= policy.auto_isolate_threshold
            and policy.automatic_shutdown_allowed
        ):
            action = "isolate_device"
            reason = "Critical risk reached the approved device isolation threshold"
        else:
            action = "alert"
            reason = "Critical risk does not permit automatic device isolation"

        if event.event_type == "normal_benign" and event.risk_score > 0:
            reason += "; normal_benign classification is inconsistent with non-zero risk"

        return PolicyDecision(
            severity=severity,
            action=action,
            risk_score=event.risk_score,
            event_type=event.event_type,
            policy_version=policy.policy_version,
            reason=reason,
        )

    @staticmethod
    def _severity(policy: RiskPolicy, risk_score: int) -> Severity:
        if risk_score < policy.warning_threshold:
            return "normal"
        if risk_score < policy.critical_threshold:
            return "warning"
        return "critical"
