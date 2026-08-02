import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from pydantic import ValidationError


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("POSTGRES_HOST", "127.0.0.1")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "unit_test")
os.environ.setdefault("POSTGRES_USER", "unit_test")
os.environ.setdefault("POSTGRES_PASSWORD", "unit_test")

from repositories.system_status_repository import SystemStatusRepositoryResult  # noqa: E402
from schemas.system_status import HeartbeatInput  # noqa: E402
from services.system_status_service import SystemStatusService, compute_component_status  # noqa: E402


NOW = datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc)


def payload(**overrides):
    values = {
        "component_type": "esp32",
        "component_id": " esp32-01 ",
        "reported_status": "healthy",
        "sequence": 1,
        "reported_by": " gateway-01 ",
        "software_version": " 1.2.3 ",
        "device_timestamp": "2026-08-02T11:59:59Z",
        "metadata": {"queue_depth": 2},
    }
    values.update(overrides)
    return values


class StubRepository:
    def __init__(self, result=None, records=None):
        self.result = result
        self.records = records or {}
        self.values = None

    def upsert(self, values):
        self.values = values
        return self.result

    def get_expected(self, identities):
        return self.records


class HeartbeatSchemaTests(unittest.TestCase):
    def test_identity_fields_are_trimmed(self):
        parsed = HeartbeatInput.model_validate(payload())
        self.assertEqual(parsed.component_id, "esp32-01")
        self.assertEqual(parsed.reported_by, "gateway-01")

    def test_invalid_component_type_is_rejected(self):
        with self.assertRaises(ValidationError):
            HeartbeatInput.model_validate(payload(component_type="led"))

    def test_empty_component_id_is_rejected(self):
        with self.assertRaises(ValidationError):
            HeartbeatInput.model_validate(payload(component_id="   "))

    def test_negative_sequence_is_rejected(self):
        with self.assertRaises(ValidationError):
            HeartbeatInput.model_validate(payload(sequence=-1))

    def test_naive_device_timestamp_is_rejected(self):
        with self.assertRaises(ValidationError):
            HeartbeatInput.model_validate(payload(device_timestamp="2026-08-02T12:00:00"))

    def test_timezone_aware_timestamp_is_accepted(self):
        parsed = HeartbeatInput.model_validate(payload())
        self.assertIsNotNone(parsed.device_timestamp.tzinfo)

    def test_sensitive_metadata_key_is_rejected_recursively(self):
        with self.assertRaises(ValidationError):
            HeartbeatInput.model_validate(payload(metadata={"nested": {"Token": "no"}}))


class SystemStatusServiceTests(unittest.TestCase):
    def test_created_heartbeat_uses_backend_time(self):
        repository = StubRepository(SystemStatusRepositoryResult("created", 1, NOW))
        result = SystemStatusService(repository, now_provider=lambda: NOW).heartbeat(
            HeartbeatInput.model_validate(payload())
        )
        self.assertEqual(result.http_status, 201)
        self.assertEqual(result.response.result, "created")
        self.assertEqual(repository.values["last_seen"], NOW)

    def test_updated_and_duplicate_are_successful(self):
        for name in ("updated", "duplicate"):
            with self.subTest(name=name):
                repository = StubRepository(SystemStatusRepositoryResult(name, 2, NOW))
                result = SystemStatusService(repository, now_provider=lambda: NOW).heartbeat(
                    HeartbeatInput.model_validate(payload(sequence=2))
                )
                self.assertEqual(result.http_status, 200)
                self.assertEqual(result.response.result, name)

    def test_conflict_is_409(self):
        repository = StubRepository(SystemStatusRepositoryResult("conflict", 4, NOW))
        result = SystemStatusService(repository).heartbeat(HeartbeatInput.model_validate(payload()))
        self.assertEqual(result.http_status, 409)
        self.assertEqual(result.response.accepted_sequence, 4)

    def test_status_boundaries_and_negative_age_clamp(self):
        cases = [
            (None, "waiting", None),
            (NOW - timedelta(seconds=29), "online", 29),
            (NOW - timedelta(seconds=30), "delayed", 30),
            (NOW - timedelta(seconds=60), "delayed", 60),
            (NOW - timedelta(seconds=61), "offline", 61),
            (NOW + timedelta(seconds=5), "online", 0),
        ]
        for last_seen, expected, age in cases:
            with self.subTest(expected=expected, age=age):
                status, calculated_age = compute_component_status(
                    now=NOW, last_seen=last_seen, online_threshold=30, offline_threshold=60
                )
                self.assertEqual(status, expected)
                self.assertEqual(calculated_age, age)

    def test_status_always_returns_two_expected_components(self):
        record = SimpleNamespace(
            last_seen=NOW,
            reported_status="healthy",
            sequence=3,
            software_version="1.0",
        )
        repository = StubRepository(records={("esp32", "esp-1"): record})
        result = SystemStatusService(repository, now_provider=lambda: NOW).status(
            expected=[("raspberry_pi", "pi-1"), ("esp32", "esp-1")],
            online_threshold=30,
            offline_threshold=60,
        )
        self.assertEqual(len(result.components), 2)
        self.assertEqual(result.components[0].computed_status, "waiting")
        self.assertEqual(result.components[1].computed_status, "online")


if __name__ == "__main__":
    unittest.main()
