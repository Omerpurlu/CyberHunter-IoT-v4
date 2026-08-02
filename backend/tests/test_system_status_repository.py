import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import OperationalError


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("POSTGRES_HOST", "127.0.0.1")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "unit_test")
os.environ.setdefault("POSTGRES_USER", "unit_test")
os.environ.setdefault("POSTGRES_PASSWORD", "unit_test")

from repositories.system_status_repository import SystemStatusRepository  # noqa: E402


NOW = datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc)


def values(sequence=2, status="healthy"):
    return {
        "component_type": "esp32",
        "component_id": "esp-1",
        "reported_status": status,
        "sequence": sequence,
        "last_seen": NOW,
        "reported_by": "pi-1",
        "software_version": "1.0",
        "device_timestamp": NOW,
        "metadata_json": {"count": 1},
        "created_at": NOW,
        "updated_at": NOW,
    }


def result_with(*, row=None, scalar=None):
    result = MagicMock()
    result.one_or_none.return_value = row
    result.scalar_one_or_none.return_value = scalar
    return result


def record(sequence=2, status="healthy", last_seen=NOW):
    return SimpleNamespace(
        component_type="esp32",
        component_id="esp-1",
        reported_status=status,
        sequence=sequence,
        last_seen=last_seen,
        reported_by="pi-1",
        software_version="1.0",
        device_timestamp=NOW,
        metadata_json={"count": 1},
    )


class SystemStatusRepositoryTests(unittest.TestCase):
    def test_insert_commits_and_returns_created(self):
        session = MagicMock()
        session.execute.return_value = result_with(row=(2, NOW, True))
        outcome = SystemStatusRepository(session).upsert(values())
        self.assertEqual(outcome.status, "created")
        session.commit.assert_called_once_with()

    def test_higher_sequence_returns_updated(self):
        session = MagicMock()
        session.execute.return_value = result_with(row=(3, NOW, False))
        outcome = SystemStatusRepository(session).upsert(values(sequence=3))
        self.assertEqual(outcome.status, "updated")

    def test_equal_identical_payload_is_duplicate(self):
        session = MagicMock()
        session.execute.side_effect = [result_with(row=None), result_with(scalar=record())]
        outcome = SystemStatusRepository(session).upsert(values())
        self.assertEqual(outcome.status, "duplicate")
        session.commit.assert_called_once_with()

    def test_equal_or_lower_different_payload_is_conflict(self):
        for sequence in (2, 1):
            with self.subTest(sequence=sequence):
                session = MagicMock()
                session.execute.side_effect = [
                    result_with(row=None),
                    result_with(scalar=record(sequence=2, status="degraded")),
                ]
                outcome = SystemStatusRepository(session).upsert(values(sequence=sequence))
                self.assertEqual(outcome.status, "conflict")

    def test_stale_heartbeat_does_not_supply_an_update_result(self):
        old_seen = NOW.replace(hour=11)
        session = MagicMock()
        session.execute.side_effect = [
            result_with(row=None),
            result_with(scalar=record(sequence=5, last_seen=old_seen)),
        ]
        outcome = SystemStatusRepository(session).upsert(values(sequence=4))
        self.assertEqual(outcome.last_seen, old_seen)
        self.assertEqual(outcome.status, "conflict")

    def test_database_failure_rolls_back(self):
        session = MagicMock()
        session.execute.side_effect = OperationalError("statement", {}, Exception("password=bad"))
        outcome = SystemStatusRepository(session).upsert(values())
        self.assertEqual(outcome.status, "database_unavailable")
        session.rollback.assert_called_once_with()

    def test_upsert_sql_is_atomic_and_sequence_guarded(self):
        session = MagicMock()
        session.execute.return_value = result_with(row=(2, NOW, True))
        SystemStatusRepository(session).upsert(values())
        statement = session.execute.call_args.args[0]
        sql = str(statement.compile(dialect=postgresql.dialect()))
        self.assertIn("ON CONFLICT", sql)
        self.assertIn("DO UPDATE", sql)
        self.assertIn("excluded.sequence > system_component_status.sequence", sql)


if __name__ == "__main__":
    unittest.main()
