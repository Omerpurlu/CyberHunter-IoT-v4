import sys
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.risk_policy_evaluator import (  # noqa: E402
    EventValidationError,
    PolicyValidationError,
    RiskEvent,
    RiskPolicy,
    RiskPolicyEvaluator,
)


SCHOOL_POLICY = RiskPolicy(
    organization_type="school",
    warning_threshold=40,
    critical_threshold=80,
    auto_isolate_threshold=80,
    automatic_shutdown_allowed=True,
    manual_approval_required=False,
    policy_version=1,
)

HOSPITAL_POLICY = RiskPolicy(
    organization_type="hospital",
    warning_threshold=30,
    critical_threshold=50,
    auto_isolate_threshold=70,
    automatic_shutdown_allowed=False,
    manual_approval_required=True,
    policy_version=3,
)


def evaluate(policy, risk_score, event_type="credential_attack"):
    return RiskPolicyEvaluator.evaluate(
        policy,
        RiskEvent(event_type=event_type, risk_score=risk_score),
    )


class RiskPolicyEvaluatorTests(unittest.TestCase):
    def assertDecision(self, policy, risk, severity, action, event_type="credential_attack"):
        decision = evaluate(policy, risk, event_type)
        self.assertEqual((decision.severity, decision.action), (severity, action))
        self.assertEqual(decision.risk_score, risk)
        self.assertEqual(decision.event_type, event_type)
        self.assertEqual(decision.policy_version, policy.policy_version)

    def test_school_risk_25(self):
        self.assertDecision(SCHOOL_POLICY, 25, "normal", "log_only")

    def test_school_risk_55(self):
        self.assertDecision(SCHOOL_POLICY, 55, "warning", "alert")

    def test_school_risk_85(self):
        self.assertDecision(SCHOOL_POLICY, 85, "critical", "isolate_device")

    def test_school_malware_botnet_risk_90(self):
        self.assertDecision(
            SCHOOL_POLICY,
            90,
            "critical",
            "isolate_device",
            "malware_botnet",
        )

    def test_school_unknown_risk_15_alerts_without_isolation(self):
        decision = evaluate(SCHOOL_POLICY, 15, "unknown")
        self.assertEqual((decision.severity, decision.action), ("normal", "alert"))
        self.assertIn("additional review", decision.reason)

    def test_hospital_risk_20(self):
        self.assertDecision(HOSPITAL_POLICY, 20, "normal", "log_only")

    def test_hospital_risk_35(self):
        self.assertDecision(HOSPITAL_POLICY, 35, "warning", "alert")

    def test_hospital_risk_55(self):
        self.assertDecision(
            HOSPITAL_POLICY, 55, "critical", "request_approval"
        )

    def test_hospital_risk_75(self):
        self.assertDecision(
            HOSPITAL_POLICY, 75, "critical", "request_approval"
        )

    def test_hospital_risk_90(self):
        self.assertDecision(
            HOSPITAL_POLICY, 90, "critical", "request_approval"
        )

    def test_threshold_boundaries(self):
        cases = (
            (39, "normal", "log_only"),
            (40, "warning", "alert"),
            (79, "warning", "alert"),
            (80, "critical", "isolate_device"),
        )
        for risk, severity, action in cases:
            with self.subTest(risk=risk):
                self.assertDecision(SCHOOL_POLICY, risk, severity, action)

    def test_risk_zero_and_one_hundred(self):
        self.assertDecision(SCHOOL_POLICY, 0, "normal", "log_only")
        self.assertDecision(SCHOOL_POLICY, 100, "critical", "isolate_device")

    def test_negative_risk_is_rejected(self):
        with self.assertRaisesRegex(EventValidationError, "between 0 and 100"):
            RiskEvent(event_type="credential_attack", risk_score=-1)

    def test_risk_above_one_hundred_is_rejected(self):
        with self.assertRaisesRegex(EventValidationError, "between 0 and 100"):
            RiskEvent(event_type="credential_attack", risk_score=101)

    def test_warning_above_critical_is_rejected(self):
        with self.assertRaisesRegex(PolicyValidationError, "must not exceed"):
            self.policy(warning_threshold=81)

    def test_negative_threshold_is_rejected(self):
        for field in (
            "warning_threshold",
            "critical_threshold",
            "auto_isolate_threshold",
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(PolicyValidationError, "between 0 and 100"):
                    self.policy(**{field: -1})

    def test_threshold_above_one_hundred_is_rejected(self):
        for field in (
            "warning_threshold",
            "critical_threshold",
            "auto_isolate_threshold",
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(PolicyValidationError, "between 0 and 100"):
                    self.policy(**{field: 101})

    def test_policy_version_zero_is_rejected(self):
        with self.assertRaisesRegex(PolicyValidationError, "positive integer"):
            self.policy(policy_version=0)

    def test_normal_benign_zero_is_logged(self):
        self.assertDecision(
            SCHOOL_POLICY,
            0,
            "normal",
            "log_only",
            "normal_benign",
        )

    def test_normal_benign_high_risk_uses_policy_and_reports_inconsistency(self):
        decision = evaluate(SCHOOL_POLICY, 85, "normal_benign")
        self.assertEqual(
            (decision.severity, decision.action),
            ("critical", "isolate_device"),
        )
        self.assertIn("inconsistent", decision.reason)

    def test_noncanonical_or_unknown_event_type_is_rejected(self):
        for event_type in ("Credential_Attack", "new_attack"):
            with self.subTest(event_type=event_type):
                with self.assertRaisesRegex(EventValidationError, "canonical AI class"):
                    RiskEvent(event_type=event_type, risk_score=55)

    def test_default_rules_never_produce_isolate_network(self):
        for policy in (SCHOOL_POLICY, HOSPITAL_POLICY):
            for event_type in (
                "normal_benign",
                "unknown",
                "reconnaissance",
                "credential_attack",
                "web_attack",
                "spoofing_mitm",
                "dos_ddos",
                "malware_botnet",
            ):
                for risk in (0, 25, 40, 50, 70, 80, 100):
                    with self.subTest(
                        organization=policy.organization_type,
                        event_type=event_type,
                        risk=risk,
                    ):
                        self.assertNotEqual(
                            evaluate(policy, risk, event_type).action,
                            "isolate_network",
                        )

    def test_evaluator_is_deterministic_and_results_are_immutable(self):
        event = RiskEvent(event_type="credential_attack", risk_score=85)
        first = RiskPolicyEvaluator.evaluate(SCHOOL_POLICY, event)
        second = RiskPolicyEvaluator.evaluate(SCHOOL_POLICY, event)
        self.assertEqual(first, second)
        with self.assertRaises(FrozenInstanceError):
            first.action = "alert"

    def test_module_has_no_framework_or_database_dependency(self):
        module = sys.modules[RiskPolicyEvaluator.__module__]
        source = Path(module.__file__).read_text(encoding="utf-8")
        for forbidden in ("fastapi", "sqlalchemy", "database", "requests", "httpx"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(f"import {forbidden}", source.casefold())
                self.assertNotIn(f"from {forbidden}", source.casefold())

    @staticmethod
    def policy(**overrides):
        values = {
            "organization_type": "school",
            "warning_threshold": 40,
            "critical_threshold": 80,
            "auto_isolate_threshold": 80,
            "automatic_shutdown_allowed": True,
            "manual_approval_required": False,
            "policy_version": 1,
        }
        values.update(overrides)
        return RiskPolicy(**values)


if __name__ == "__main__":
    unittest.main()
