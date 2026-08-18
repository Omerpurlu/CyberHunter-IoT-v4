import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("POSTGRES_HOST", "127.0.0.1")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "unit_test")
os.environ.setdefault("POSTGRES_USER", "unit_test")
os.environ.setdefault("POSTGRES_PASSWORD", "unit_test")

from repositories.security_event_repository import RepositoryResult  # noqa: E402
from schemas.security_event import SecurityEventInput  # noqa: E402
from services.security_event_service import (  # noqa: E402
    SecurityEventService,
    canonical_sha256,
    normalize_event_type,
    normalize_protocol,
    normalize_tactic,
)


class StubRepository:
    def __init__(self, result: RepositoryResult):
        self.result = result
        self.event_values = None
        self.assessment_values = None

    def persist(self, event_values, assessment_values):
        self.event_values = event_values
        self.assessment_values = assessment_values
        return self.result


def input_payload() -> SecurityEventInput:
    return SecurityEventInput(
        event_id="evt-20260722T131306Z-a7c9f2",
        timestamp=datetime(
            2026,
            7,
            22,
            13,
            13,
            6,
            909000,
            tzinfo=timezone.utc,
        ),
        source_ip="192.168.137.54",
        destination_port=22,
        protocol="SSH",
        event_type="command_executed",
        command="sudo cat /etc/shadow",
        tactic="credential_access",
        input_risk_score=65,
        esp32_risk_score=65,
        esp32_decision="WARNING",
        esp32_processed=True,
        device_id="esp32-cyberhunter-01",
    )


class SecurityEventServiceTests(unittest.TestCase):
    def test_protocol_normalization_uses_controlled_ssh_mapping(self):
        for value in ("SSH", " ssh ", "ssh"):
            with self.subTest(value=value):
                self.assertEqual(normalize_protocol(value), "ssh")

    def test_ai_event_type_normalization(self):
        cases = {
            "Credential_Attack": "credential_attack",
            "Web_Attack": "web_attack",
            "DoS_DDoS": "dos_ddos",
            "Malware_Botnet": "malware_botnet",
            "Spoofing_MITM": "spoofing_mitm",
            "Normal_Benign": "normal_benign",
            "Unknown": "unknown",
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(normalize_event_type(value), expected)

    def test_tactic_normalization(self):
        cases = {
            "Credential Access": "credential_access",
            "Initial Access": "initial_access",
            "Command and Control": "command_and_control",
            "Reconnaissance": "reconnaissance",
            "Impact": "impact",
            "Benign": "benign",
            "Unknown": "unknown",
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(normalize_tactic(value), expected)

    def test_unrecognized_values_keep_legacy_behavior(self):
        self.assertEqual(normalize_protocol(" HTTPS "), "https")
        self.assertEqual(normalize_event_type(" Custom_Event "), "Custom_Event")
        self.assertEqual(normalize_tactic(" Custom Tactic "), " Custom Tactic ")

    def test_canonical_hash_is_order_independent(self):
        first = canonical_sha256({"b": 2, "a": 1})
        second = canonical_sha256({"a": 1, "b": 2})

        self.assertEqual(first, second)
        self.assertEqual(len(first), 32)

    def test_created_result_and_separate_hashes(self):
        repository = StubRepository(RepositoryResult("created"))
        result = SecurityEventService(repository).persist(input_payload())

        self.assertTrue(result.success)
        self.assertEqual(result.status, "created")
        self.assertFalse(result.duplicate)
        self.assertEqual(repository.event_values["protocol"], "ssh")
        self.assertEqual(
            repository.assessment_values["esp32_decision"],
            "warning",
        )
        self.assertEqual(len(repository.event_values["payload_hash"]), 32)
        self.assertEqual(
            len(repository.assessment_values["payload_hash"]),
            32,
        )
        self.assertNotEqual(
            repository.event_values["payload_hash"],
            repository.assessment_values["payload_hash"],
        )

    def test_normalized_values_are_used_in_event_hash(self):
        first_repository = StubRepository(RepositoryResult("created"))
        first = input_payload()
        first.event_type = "Credential_Attack"
        first.tactic = "Credential Access"
        SecurityEventService(first_repository).persist(first)

        second_repository = StubRepository(RepositoryResult("created"))
        second = input_payload()
        second.protocol = "ssh"
        second.event_type = "credential_attack"
        second.tactic = "credential_access"
        SecurityEventService(second_repository).persist(second)

        self.assertEqual(first_repository.event_values["protocol"], "ssh")
        self.assertEqual(
            first_repository.event_values["event_type"],
            "credential_attack",
        )
        self.assertEqual(
            first_repository.event_values["tactic"],
            "credential_access",
        )
        self.assertEqual(
            first_repository.event_values["payload_hash"],
            second_repository.event_values["payload_hash"],
        )

    def test_duplicate_result(self):
        repository = StubRepository(RepositoryResult("duplicate"))
        result = SecurityEventService(repository).persist(input_payload())

        self.assertTrue(result.success)
        self.assertEqual(result.status, "duplicate")
        self.assertTrue(result.duplicate)
        self.assertFalse(result.retryable)

    def test_event_conflict_result(self):
        repository = StubRepository(RepositoryResult("event_conflict"))
        result = SecurityEventService(repository).persist(input_payload())

        self.assertFalse(result.success)
        self.assertEqual(result.status, "conflict")
        self.assertEqual(result.error_code, "EVENT_ID_CONFLICT")
        self.assertFalse(result.retryable)

    def test_database_unavailable_is_retryable(self):
        repository = StubRepository(
            RepositoryResult("database_unavailable", retryable=True)
        )
        result = SecurityEventService(repository).persist(input_payload())

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "DATABASE_UNAVAILABLE")
        self.assertTrue(result.retryable)

    def test_invalid_dictionary_returns_controlled_validation_error(self):
        repository = StubRepository(RepositoryResult("created"))

        result = SecurityEventService(repository).persist(
            {"event_id": "evt-invalid"}
        )

        self.assertFalse(result.success)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.error_code, "VALIDATION_ERROR")
        self.assertFalse(result.retryable)
        self.assertIsNone(repository.event_values)

    def test_unexpected_hash_error_is_controlled_and_sanitized(self):
        repository = StubRepository(RepositoryResult("created"))

        with patch(
            "services.security_event_service.canonical_sha256",
            side_effect=RuntimeError("sudo cat /etc/shadow"),
        ), self.assertLogs(
            "services.security_event_service",
            level="ERROR",
        ) as captured:
            result = SecurityEventService(repository).persist(input_payload())

        self.assertFalse(result.success)
        self.assertEqual(result.status, "error")
        self.assertEqual(
            result.error_code,
            "INTERNAL_PERSISTENCE_ERROR",
        )
        self.assertFalse(result.duplicate)
        self.assertFalse(result.retryable)
        self.assertIsNone(repository.event_values)
        logs = "\n".join(captured.output)
        self.assertNotIn("sudo cat /etc/shadow", logs)
        self.assertIn("RuntimeError", logs)
        self.assertIn("INTERNAL_PERSISTENCE_ERROR", logs)

    def test_repository_internal_error_maps_to_service_contract(self):
        repository = StubRepository(
            RepositoryResult("internal_persistence_error")
        )

        result = SecurityEventService(repository).persist(input_payload())

        self.assertFalse(result.success)
        self.assertEqual(result.status, "error")
        self.assertEqual(
            result.error_code,
            "INTERNAL_PERSISTENCE_ERROR",
        )
        self.assertFalse(result.retryable)


if __name__ == "__main__":
    unittest.main()
