import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from sqlalchemy.exc import (
    IntegrityError,
    OperationalError,
    SQLAlchemyError,
    TimeoutError as SQLAlchemyTimeoutError,
)


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("POSTGRES_HOST", "127.0.0.1")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "unit_test")
os.environ.setdefault("POSTGRES_USER", "unit_test")
os.environ.setdefault("POSTGRES_PASSWORD", "unit_test")

from repositories.security_event_repository import (  # noqa: E402
    SecurityEventRepository,
)


EVENT_HASH = b"e" * 32
ASSESSMENT_HASH = b"a" * 32


def values():
    return (
        {
            "event_id": "evt-1",
            "event_timestamp": "2026-07-22T13:13:06.909Z",
            "source_ip": "192.168.137.54",
            "destination_port": 22,
            "protocol": "ssh",
            "event_type": "command_executed",
            "command": "sudo cat /etc/shadow",
            "tactic": "credential_access",
            "input_risk_score": 65,
            "payload_hash": EVENT_HASH,
            "hash_version": 1,
        },
        {
            "event_id": "evt-1",
            "device_id": "esp32-cyberhunter-01",
            "esp32_risk_score": 65,
            "esp32_decision": "warning",
            "esp32_processed": True,
            "assessed_at": None,
            "payload_hash": ASSESSMENT_HASH,
            "hash_version": 1,
        },
    )


def scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


class SecurityEventRepositoryTests(unittest.TestCase):
    def test_new_event_and_assessment_commit_once(self):
        session = MagicMock()
        session.execute.side_effect = [
            scalar_result("evt-1"),
            scalar_result("evt-1"),
        ]
        event_values, assessment_values = values()

        result = SecurityEventRepository(session).persist(
            event_values,
            assessment_values,
        )

        self.assertEqual(result.status, "created")
        session.commit.assert_called_once_with()
        session.rollback.assert_not_called()

    def test_identical_existing_rows_return_duplicate(self):
        session = MagicMock()
        session.execute.side_effect = [
            scalar_result(None),
            scalar_result(EVENT_HASH),
            scalar_result(None),
            scalar_result(ASSESSMENT_HASH),
        ]
        event_values, assessment_values = values()

        result = SecurityEventRepository(session).persist(
            event_values,
            assessment_values,
        )

        self.assertEqual(result.status, "duplicate")
        session.commit.assert_called_once_with()
        session.rollback.assert_not_called()

    def test_event_hash_conflict_rolls_back(self):
        session = MagicMock()
        session.execute.side_effect = [
            scalar_result(None),
            scalar_result(b"x" * 32),
        ]
        event_values, assessment_values = values()

        result = SecurityEventRepository(session).persist(
            event_values,
            assessment_values,
        )

        self.assertEqual(result.status, "event_conflict")
        session.rollback.assert_called_once_with()
        session.commit.assert_not_called()

    def test_existing_event_without_assessment_creates_assessment(self):
        session = MagicMock()
        session.execute.side_effect = [
            scalar_result(None),
            scalar_result(EVENT_HASH),
            scalar_result("evt-1"),
        ]
        event_values, assessment_values = values()

        result = SecurityEventRepository(session).persist(
            event_values,
            assessment_values,
        )

        self.assertEqual(result.status, "created")
        session.commit.assert_called_once_with()
        session.rollback.assert_not_called()

    def test_assessment_hash_conflict_rolls_back(self):
        session = MagicMock()
        session.execute.side_effect = [
            scalar_result(None),
            scalar_result(EVENT_HASH),
            scalar_result(None),
            scalar_result(b"x" * 32),
        ]
        event_values, assessment_values = values()

        result = SecurityEventRepository(session).persist(
            event_values,
            assessment_values,
        )

        self.assertEqual(result.status, "assessment_conflict")
        session.rollback.assert_called_once_with()
        session.commit.assert_not_called()

    def test_operational_error_is_controlled_and_retryable(self):
        session = MagicMock()
        session.execute.side_effect = OperationalError(
            "statement",
            {},
            Exception("connection lost"),
        )
        event_values, assessment_values = values()

        result = SecurityEventRepository(session).persist(
            event_values,
            assessment_values,
        )

        self.assertEqual(result.status, "database_unavailable")
        self.assertTrue(result.retryable)
        session.rollback.assert_called_once_with()

    def test_timeout_is_controlled_and_retryable(self):
        session = MagicMock()
        session.execute.side_effect = SQLAlchemyTimeoutError("pool timeout")
        event_values, assessment_values = values()

        result = SecurityEventRepository(session).persist(
            event_values,
            assessment_values,
        )

        self.assertEqual(result.status, "database_timeout")
        self.assertTrue(result.retryable)
        session.rollback.assert_called_once_with()

    def test_integrity_error_is_controlled(self):
        session = MagicMock()
        session.execute.side_effect = IntegrityError(
            "statement",
            {},
            Exception("constraint failed"),
        )
        event_values, assessment_values = values()

        result = SecurityEventRepository(session).persist(
            event_values,
            assessment_values,
        )

        self.assertEqual(result.status, "integrity_error")
        self.assertFalse(result.retryable)
        session.rollback.assert_called_once_with()

    def test_general_sqlalchemy_error_is_controlled(self):
        session = MagicMock()
        session.execute.side_effect = SQLAlchemyError("database details")
        event_values, assessment_values = values()

        result = SecurityEventRepository(session).persist(
            event_values,
            assessment_values,
        )

        self.assertEqual(result.status, "database_error")
        self.assertFalse(result.retryable)
        session.rollback.assert_called_once_with()

    def test_unexpected_execute_error_does_not_escape(self):
        session = MagicMock()
        session.execute.side_effect = RuntimeError(
            "sudo cat /etc/shadow"
        )
        event_values, assessment_values = values()

        with self.assertLogs(
            "repositories.security_event_repository",
            level="ERROR",
        ) as captured:
            result = SecurityEventRepository(session).persist(
                event_values,
                assessment_values,
            )

        self.assertEqual(result.status, "internal_persistence_error")
        self.assertFalse(result.retryable)
        session.rollback.assert_called_once_with()
        logs = "\n".join(captured.output)
        self.assertNotIn("sudo cat /etc/shadow", logs)
        self.assertIn("RuntimeError", logs)
        self.assertIn("INTERNAL_PERSISTENCE_ERROR", logs)

    def test_unexpected_commit_error_rolls_back_and_does_not_escape(self):
        session = MagicMock()
        session.execute.side_effect = [
            scalar_result("evt-1"),
            scalar_result("evt-1"),
        ]
        session.commit.side_effect = RuntimeError("commit failed")
        event_values, assessment_values = values()

        result = SecurityEventRepository(session).persist(
            event_values,
            assessment_values,
        )

        self.assertEqual(result.status, "internal_persistence_error")
        session.commit.assert_called_once_with()
        session.rollback.assert_called_once_with()

    def test_rollback_error_is_suppressed(self):
        session = MagicMock()
        session.execute.side_effect = RuntimeError(
            "sensitive-operation-detail"
        )
        session.rollback.side_effect = RuntimeError(
            "sensitive-rollback-detail"
        )
        event_values, assessment_values = values()

        with self.assertLogs(
            "repositories.security_event_repository",
            level="ERROR",
        ) as captured:
            result = SecurityEventRepository(session).persist(
                event_values,
                assessment_values,
            )

        self.assertEqual(result.status, "internal_persistence_error")
        session.rollback.assert_called_once_with()
        logs = "\n".join(captured.output)
        self.assertIn("ROLLBACK_FAILED", logs)
        self.assertNotIn("sensitive-operation-detail", logs)
        self.assertNotIn("sensitive-rollback-detail", logs)


if __name__ == "__main__":
    unittest.main()
