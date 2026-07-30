import asyncio
import json
import os
import sys
import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import FastAPI
from sqlalchemy.exc import OperationalError


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
from routers.security_events import (  # noqa: E402
    get_security_event_repository,
    router,
)


@dataclass(frozen=True)
class AsgiResponse:
    status_code: int
    body: bytes

    def json(self):
        return json.loads(self.body)


def asgi_get(app: FastAPI, path: str, query_string: str = "") -> AsgiResponse:
    request_sent = False
    messages = []

    async def receive():
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": query_string.encode("ascii"),
        "root_path": "",
        "headers": [(b"host", b"testserver")],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
    }
    asyncio.run(app(scope, receive, send))
    start = next(
        message
        for message in messages
        if message["type"] == "http.response.start"
    )
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return AsgiResponse(start["status"], body)


def event(event_id="evt-001"):
    timestamp = datetime(2026, 7, 29, 12, 53, tzinfo=timezone.utc)
    return SimpleNamespace(
        event_id=event_id,
        event_timestamp=timestamp,
        source_ip="192.0.2.10",
        destination_port=22,
        protocol="ssh",
        event_type="command_executed",
        command="whoami",
        tactic="discovery",
        input_risk_score=25,
        received_at=timestamp,
    )


def assessment():
    timestamp = datetime(2026, 7, 29, 13, 0, tzinfo=timezone.utc)
    return SimpleNamespace(
        device_id="esp32-cyberhunter-01",
        esp32_risk_score=30,
        esp32_decision="warning",
        esp32_processed=True,
        assessed_at=None,
        received_at=timestamp,
    )


class StubRepository:
    def __init__(self, rows=None, error=None):
        self.rows = rows or []
        self.error = error
        self.calls = []

    def list_security_events(self, *, limit, offset):
        self.calls.append((limit, offset))
        if self.error:
            raise self.error
        return self.rows


class SecurityEventReadEndpointTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router)

    def request_with(self, repository, query_string="limit=50&offset=0"):
        self.app.dependency_overrides[get_security_event_repository] = (
            lambda: repository
        )
        return asgi_get(
            self.app,
            "/api/security-events",
            query_string,
        )

    def test_get_returns_contract_and_joined_assessment(self):
        repository = StubRepository([(event(), assessment())])
        response = self.request_with(repository)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(set(body), {"items", "limit", "offset", "count"})
        self.assertEqual(body["limit"], 50)
        self.assertEqual(body["offset"], 0)
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["items"][0]["source_ip"], "192.0.2.10")
        self.assertEqual(body["items"][0]["assessment"]["risk_score"], 30)
        self.assertEqual(
            body["items"][0]["assessment"]["device_id"],
            "esp32-cyberhunter-01",
        )
        self.assertEqual(repository.calls, [(50, 0)])

    def test_event_without_assessment_returns_null(self):
        response = self.request_with(StubRepository([(event(), None)]))

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["items"][0]["assessment"])

    def test_empty_result_is_safe(self):
        response = self.request_with(StubRepository())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"], [])
        self.assertEqual(response.json()["count"], 0)

    def test_limit_zero_is_rejected(self):
        response = self.request_with(StubRepository(), "limit=0&offset=0")
        self.assertEqual(response.status_code, 422)

    def test_limit_over_200_is_rejected(self):
        response = self.request_with(StubRepository(), "limit=201&offset=0")
        self.assertEqual(response.status_code, 422)

    def test_negative_offset_is_rejected(self):
        response = self.request_with(StubRepository(), "limit=50&offset=-1")
        self.assertEqual(response.status_code, 422)

    def test_postgresql_error_returns_sanitized_503(self):
        error = OperationalError("SELECT secret", {}, RuntimeError("password"))
        response = self.request_with(StubRepository(error=error))

        self.assertEqual(response.status_code, 503)
        self.assertNotIn("secret", response.body.decode())
        self.assertNotIn("password", response.body.decode())

    def test_unexpected_error_returns_sanitized_500(self):
        response = self.request_with(
            StubRepository(error=RuntimeError("database password"))
        )

        self.assertEqual(response.status_code, 500)
        self.assertNotIn("password", response.body.decode())

    def test_repository_read_does_not_commit_or_rollback(self):
        session = MagicMock()
        session.execute.return_value.all.return_value = []
        repository = SecurityEventRepository(session)

        rows = repository.list_security_events(limit=10, offset=5)

        self.assertEqual(rows, [])
        session.commit.assert_not_called()
        session.rollback.assert_not_called()
        statement = session.execute.call_args.args[0]
        sql = str(statement)
        self.assertIn("LEFT OUTER JOIN", sql)
        self.assertIn("ORDER BY security_events.event_timestamp DESC", sql)
        self.assertIn("security_events.event_id DESC", sql)


if __name__ == "__main__":
    unittest.main()
