import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("POSTGRES_HOST", "127.0.0.1")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "unit_test")
os.environ.setdefault("POSTGRES_USER", "unit_test")
os.environ.setdefault("POSTGRES_PASSWORD", "unit_test")

from repositories.response_action_repository import ActionCreateResult  # noqa: E402
from schemas.security_event import SecurityEventInput  # noqa: E402
from services.risk_policy_evaluator import RiskPolicy  # noqa: E402
from services.security_response_orchestrator import (  # noqa: E402
    SecurityResponseOrchestrator,
    prototype_policy_from_env,
)


NOW = datetime(2026, 8, 6, 20, 0, tzinfo=timezone.utc)


class MemoryRepository:
    def __init__(self):
        self.values = []

    def create_if_not_exists(self, values):
        key = tuple(values[name] for name in ("event_id", "device_id", "action", "policy_version"))
        for existing in self.values:
            if tuple(existing[name] for name in ("event_id", "device_id", "action", "policy_version")) == key:
                return ActionCreateResult("duplicate", existing)
        self.values.append(values)
        return ActionCreateResult("created", values)


def payload(event_type="credential_attack", risk=85):
    return SecurityEventInput(
        event_id="evt-roundtrip-001",
        timestamp="2026-08-06T19:59:00Z",
        source_ip="192.0.2.10",
        destination_port=22,
        protocol="ssh",
        event_type=event_type,
        command="simulation",
        tactic="credential_access",
        input_risk_score=risk,
        esp32_risk_score=risk,
        esp32_decision="warning",
        esp32_processed=True,
        device_id="esp32-cyberhunter-01",
    )


class SecurityResponseOrchestratorTests(unittest.TestCase):
    def orchestrator(self, policy):
        repository = MemoryRepository()
        service = SecurityResponseOrchestrator(
            repository,
            policy_provider=lambda: policy,
            now_provider=lambda: NOW,
            ttl_seconds=300,
        )
        return service, repository

    def test_safe_default_policy_requires_approval(self):
        policy = prototype_policy_from_env()
        self.assertFalse(policy.automatic_shutdown_allowed)
        self.assertTrue(policy.manual_approval_required)
        service, repository = self.orchestrator(policy)
        service.process(payload())
        self.assertEqual(repository.values[0]["status"], "awaiting_approval")

    def test_school_policy_writes_pending_isolate_device(self):
        policy = RiskPolicy("school", 40, 80, 80, True, False, 1)
        service, repository = self.orchestrator(policy)
        service.process(payload())
        action = repository.values[0]
        self.assertEqual((action["action"], action["status"]), ("isolate_device", "pending"))

    def test_duplicate_decision_creates_one_action(self):
        policy = RiskPolicy("school", 40, 80, 80, True, False, 1)
        service, repository = self.orchestrator(policy)
        self.assertEqual(service.process(payload()).status, "created")
        self.assertEqual(service.process(payload()).status, "duplicate")
        self.assertEqual(len(repository.values), 1)

    def test_action_status_mapping(self):
        cases = (
            (RiskPolicy("p", 40, 80, 80, False, False, 1), 20, "log_only", "recorded"),
            (RiskPolicy("p", 40, 80, 80, False, False, 1), 55, "alert", "recorded"),
            (RiskPolicy("p", 40, 80, 80, False, True, 1), 85, "request_approval", "awaiting_approval"),
            (RiskPolicy("p", 40, 80, 80, True, False, 1), 85, "isolate_device", "pending"),
        )
        for policy, risk, action, status in cases:
            with self.subTest(action=action):
                service, repository = self.orchestrator(policy)
                service.process(payload(risk=risk))
                self.assertEqual((repository.values[0]["action"], repository.values[0]["status"]), (action, status))

    def test_unknown_never_isolates(self):
        policy = RiskPolicy("school", 40, 80, 80, True, False, 1)
        service, repository = self.orchestrator(policy)
        service.process(payload("unknown", 90))
        self.assertEqual((repository.values[0]["action"], repository.values[0]["status"]), ("alert", "recorded"))


if __name__ == "__main__":
    unittest.main()
