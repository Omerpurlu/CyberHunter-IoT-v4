import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

from sqlalchemy.dialects import postgresql


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("POSTGRES_HOST", "127.0.0.1")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "unit_test")
os.environ.setdefault("POSTGRES_USER", "unit_test")
os.environ.setdefault("POSTGRES_PASSWORD", "unit_test")

from repositories.response_action_repository import ResponseActionRepository  # noqa: E402
from schemas.response_action import CommandAckInput  # noqa: E402


COMMAND_ID = UUID("11111111-1111-1111-1111-111111111111")
NOW = datetime(2026, 8, 6, 20, 0, tzinfo=timezone.utc)


def scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def record(status="pending", device_id="esp32-1"):
    return SimpleNamespace(
        id=COMMAND_ID,
        device_id=device_id,
        status=status,
        dispatched_at=None,
        attempt_count=0,
        executed_at=None,
        ack_received_at=None,
        relay_state=None,
        ack_message=None,
        last_error=None,
    )


def ack(result="executed", device_id="esp32-1", message="done"):
    return CommandAckInput(
        device_id=device_id,
        result=result,
        executed_at=NOW,
        relay_state="simulated_isolated",
        ack_message=message,
    )


class ResponseActionRepositoryTests(unittest.TestCase):
    def test_claim_uses_skip_locked_pending_device_and_expiry_filters(self):
        session = MagicMock()
        session.execute.return_value = scalar_result(None)
        repository = ResponseActionRepository(session)
        self.assertIsNone(repository.claim_next(device_id="esp32-1", now=NOW))
        statement = session.execute.call_args.args[0]
        sql = str(statement.compile(dialect=postgresql.dialect()))
        self.assertIn("FOR UPDATE SKIP LOCKED", sql)
        self.assertIn("response_actions.status", sql)
        self.assertIn("response_actions.device_id", sql)
        self.assertIn("response_actions.expires_at", sql)

    def test_claim_dispatches_and_increments_attempt(self):
        action = record()
        session = MagicMock()
        session.execute.return_value = scalar_result(action)
        claimed = ResponseActionRepository(session).claim_next(device_id="esp32-1", now=NOW)
        self.assertEqual(claimed.status, "dispatched")
        self.assertEqual(claimed.dispatched_at, NOW)
        self.assertEqual(claimed.attempt_count, 1)
        session.commit.assert_called_once_with()

    def test_valid_ack_is_persisted(self):
        action = record("dispatched")
        session = MagicMock()
        session.execute.return_value = scalar_result(action)
        result = ResponseActionRepository(session).acknowledge(
            action_id=COMMAND_ID,
            payload=ack(),
            received_at=NOW,
        )
        self.assertEqual(result.status, "updated")
        self.assertEqual(action.status, "executed")
        self.assertEqual(action.ack_received_at, NOW)

    def test_identical_ack_is_duplicate(self):
        action = record("executed")
        action.executed_at = NOW
        action.relay_state = "simulated_isolated"
        action.ack_message = "done"
        action.ack_received_at = NOW
        session = MagicMock()
        session.execute.return_value = scalar_result(action)
        result = ResponseActionRepository(session).acknowledge(
            action_id=COMMAND_ID,
            payload=ack(),
            received_at=NOW,
        )
        self.assertEqual(result.status, "duplicate")

    def test_different_ack_is_conflict(self):
        action = record("executed")
        action.executed_at = NOW
        action.relay_state = "simulated_isolated"
        action.ack_message = "original"
        session = MagicMock()
        session.execute.return_value = scalar_result(action)
        result = ResponseActionRepository(session).acknowledge(
            action_id=COMMAND_ID,
            payload=ack(message="different"),
            received_at=NOW,
        )
        self.assertEqual(result.status, "conflict")
        session.rollback.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
