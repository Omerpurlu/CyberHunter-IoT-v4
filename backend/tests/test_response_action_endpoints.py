import asyncio
import json
import os
import sys
import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode
from uuid import UUID

from fastapi import FastAPI


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("POSTGRES_HOST", "127.0.0.1")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "unit_test")
os.environ.setdefault("POSTGRES_USER", "unit_test")
os.environ.setdefault("POSTGRES_PASSWORD", "unit_test")

from repositories.response_action_repository import ActionAckResult  # noqa: E402
from routers.response_actions import (  # noqa: E402
    get_response_action_repository,
    router,
)


COMMAND_ID = UUID("11111111-1111-1111-1111-111111111111")
NOW = datetime(2026, 8, 6, 20, 0, tzinfo=timezone.utc)


def action(status="pending", device_id="esp32-cyberhunter-01"):
    return SimpleNamespace(
        id=COMMAND_ID,
        event_id="evt-roundtrip-001",
        device_id=device_id,
        action="isolate_device",
        severity="critical",
        status=status,
        risk_score=85,
        policy_version=1,
        decision_reason="test decision",
        created_at=NOW,
        expires_at=datetime(2026, 8, 6, 20, 5, tzinfo=timezone.utc),
        dispatched_at=NOW if status != "pending" else None,
        executed_at=NOW if status in {"executed", "failed"} else None,
        ack_received_at=NOW if status in {"executed", "failed"} else None,
        ack_message="done" if status in {"executed", "failed"} else None,
        relay_state="simulated_isolated" if status == "executed" else None,
        attempt_count=1 if status != "pending" else 0,
        last_error=None,
    )


class StubRepository:
    def __init__(self):
        self.next_action = action()
        self.ack_result = ActionAckResult("updated", action("executed"))
        self.listed = []
        self.claim_calls = []
        self.list_calls = []

    def claim_next(self, **kwargs):
        self.claim_calls.append(kwargs)
        return self.next_action

    def acknowledge(self, **kwargs):
        return self.ack_result

    def list_actions(self, **kwargs):
        self.list_calls.append(kwargs)
        return self.listed


@dataclass(frozen=True)
class AsgiResponse:
    status_code: int
    body: bytes

    def json(self):
        return json.loads(self.body)


def request(app, method, path, payload=None, query=None):
    sent = False
    messages = []
    body = json.dumps(payload).encode() if payload is not None else b""
    query_string = urlencode(query or {}).encode()

    async def receive():
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query_string,
        "root_path": "",
        "headers": [(b"content-type", b"application/json")],
        "client": ("127.0.0.1", 1),
        "server": ("testserver", 80),
    }
    asyncio.run(app(scope, receive, send))
    start = next(item for item in messages if item["type"] == "http.response.start")
    response_body = b"".join(item.get("body", b"") for item in messages if item["type"] == "http.response.body")
    return AsgiResponse(start["status"], response_body)


class ResponseActionEndpointTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router)
        self.repository = StubRepository()
        self.app.dependency_overrides[get_response_action_repository] = lambda: self.repository

    def test_pending_command_is_returned_and_claimed_for_device(self):
        response = request(self.app, "GET", "/api/iot/commands/next", query={"device_id": "esp32-cyberhunter-01"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["command_id"], str(COMMAND_ID))
        self.assertEqual(self.repository.claim_calls[0]["device_id"], "esp32-cyberhunter-01")

    def test_no_command_returns_204(self):
        self.repository.next_action = None
        response = request(self.app, "GET", "/api/iot/commands/next", query={"device_id": "esp32-cyberhunter-01"})
        self.assertEqual(response.status_code, 204)

    def test_valid_ack_returns_executed(self):
        response = self.ack()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "executed")
        self.assertFalse(response.json()["duplicate"])

    def test_duplicate_ack_returns_200_duplicate(self):
        self.repository.ack_result = ActionAckResult("duplicate", action("executed"))
        response = self.ack()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["duplicate"])

    def test_ack_conflict_returns_409(self):
        self.repository.ack_result = ActionAckResult("conflict", action("executed"))
        response = self.ack()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error_code"], "ACK_CONFLICT")

    def test_wrong_device_ack_is_rejected(self):
        self.repository.ack_result = ActionAckResult("wrong_device", action("dispatched"))
        self.assertEqual(self.ack().status_code, 403)

    def test_unknown_command_returns_404(self):
        self.repository.ack_result = ActionAckResult("not_found")
        self.assertEqual(self.ack().status_code, 404)

    def test_cancelled_or_expired_command_ack_returns_409(self):
        self.repository.ack_result = ActionAckResult("not_acknowledgeable", action("cancelled"))
        response = self.ack()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error_code"], "ACTION_NOT_ACKNOWLEDGEABLE")

    def test_naive_executed_at_returns_422(self):
        response = self.ack(executed_at="2026-08-06T20:00:00")
        self.assertEqual(response.status_code, 422)

    def test_read_filters_and_payload(self):
        self.repository.listed = [action("executed")]
        response = request(
            self.app,
            "GET",
            "/api/response-actions",
            query={"event_id": "evt-roundtrip-001", "device_id": "esp32-cyberhunter-01", "status": "executed", "limit": 10, "offset": 2},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["ack_message"], "done")
        self.assertEqual(self.repository.list_calls[0]["status"], "executed")
        self.assertEqual((response.json()["limit"], response.json()["offset"]), (10, 2))

    def ack(self, executed_at="2026-08-06T20:00:00Z"):
        return request(
            self.app,
            "POST",
            f"/api/iot/commands/{COMMAND_ID}/ack",
            {
                "device_id": "esp32-cyberhunter-01",
                "result": "executed",
                "executed_at": executed_at,
                "relay_state": "simulated_isolated",
                "ack_message": "done",
            },
        )


if __name__ == "__main__":
    unittest.main()
