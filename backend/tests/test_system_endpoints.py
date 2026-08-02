import asyncio
import json
import os
import sys
import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("POSTGRES_HOST", "127.0.0.1")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "unit_test")
os.environ.setdefault("POSTGRES_USER", "unit_test")
os.environ.setdefault("POSTGRES_PASSWORD", "unit_test")

from routers.system import get_system_status_service, router  # noqa: E402
from schemas.system_status import HeartbeatResponse, SystemStatusResponse  # noqa: E402
from services.system_status_service import HeartbeatServiceResult  # noqa: E402


NOW = datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc)
VALID_PAYLOAD = {
    "component_type": "esp32",
    "component_id": "esp-1",
    "reported_status": "healthy",
    "sequence": 1,
    "device_timestamp": "2026-08-02T11:59:59Z",
    "metadata": {},
}


@dataclass(frozen=True)
class AsgiResponse:
    status_code: int
    body: bytes

    def json(self):
        return json.loads(self.body)


def request(app, method, path, payload=None):
    sent = False
    messages = []
    body = json.dumps(payload).encode() if payload is not None else b""

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
        "query_string": b"",
        "root_path": "",
        "headers": [(b"content-type", b"application/json")],
        "client": ("127.0.0.1", 1),
        "server": ("testserver", 80),
    }
    asyncio.run(app(scope, receive, send))
    start = next(item for item in messages if item["type"] == "http.response.start")
    response_body = b"".join(item.get("body", b"") for item in messages if item["type"] == "http.response.body")
    return AsgiResponse(start["status"], response_body)


class StubService:
    def heartbeat(self, payload):
        return HeartbeatServiceResult(
            HeartbeatResponse(
                component_type=payload.component_type,
                component_id=payload.component_id,
                accepted_sequence=payload.sequence,
                result="created",
                last_seen=NOW,
            ),
            201,
        )

    def status(self, **kwargs):
        return SystemStatusResponse(
            generated_at=NOW,
            components=[
                {
                    "component_type": "raspberry_pi",
                    "component_id": "raspberry-pi-01",
                    "computed_status": "waiting",
                    "reported_status": None,
                    "last_seen": None,
                    "age_seconds": None,
                    "sequence": None,
                    "software_version": None,
                },
                {
                    "component_type": "esp32",
                    "component_id": "esp32-cyberhunter-01",
                    "computed_status": "waiting",
                    "reported_status": None,
                    "last_seen": None,
                    "age_seconds": None,
                    "sequence": None,
                    "software_version": None,
                },
            ],
        )


class RaisingService:
    def heartbeat(self, payload):
        raise RuntimeError("postgresql://user:password@secret-host/db")


class SystemEndpointTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.dependency_overrides[get_system_status_service] = lambda: StubService()

    def test_first_heartbeat_returns_201(self):
        response = request(self.app, "POST", "/api/system/heartbeat", VALID_PAYLOAD)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["result"], "created")

    def test_invalid_heartbeat_returns_422(self):
        response = request(self.app, "POST", "/api/system/heartbeat", {**VALID_PAYLOAD, "sequence": -1})
        self.assertEqual(response.status_code, 422)

    def test_status_returns_both_expected_components(self):
        response = request(self.app, "GET", "/api/system/status")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["components"]), 2)

    def test_openapi_discloses_missing_authentication(self):
        operation = self.app.openapi()["paths"]["/api/system/heartbeat"]["post"]
        self.assertIn("Authentication is not implemented", operation["description"])
        self.assertIn("201", operation["responses"])
        input_schema = self.app.openapi()["components"]["schemas"]["HeartbeatInput"]
        self.assertNotIn("last_seen", input_schema["properties"])
        self.assertNotIn("created_at", input_schema["properties"])

    def test_unexpected_heartbeat_error_is_sanitized(self):
        self.app.dependency_overrides[get_system_status_service] = lambda: RaisingService()
        response = request(self.app, "POST", "/api/system/heartbeat", VALID_PAYLOAD)
        serialized = response.body.decode()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error_code"], "INTERNAL_PERSISTENCE_ERROR")
        self.assertNotIn("password", serialized)
        self.assertNotIn("secret-host", serialized)


if __name__ == "__main__":
    unittest.main()
