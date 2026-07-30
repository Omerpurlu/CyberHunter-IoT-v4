import asyncio
import json
import os
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi import FastAPI


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DEVICE_SECRET", "unit-test-device-secret")
os.environ.setdefault("POSTGRES_HOST", "127.0.0.1")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "unit_test")
os.environ.setdefault("POSTGRES_USER", "unit_test")
os.environ.setdefault("POSTGRES_PASSWORD", "unit_test")

from dependencies import get_db  # noqa: E402
from routers.security_events import (  # noqa: E402
    get_security_event_service,
    router,
)
from schemas.security_event import PersistenceResult  # noqa: E402


VALID_PAYLOAD = {
    "event_id": "evt-20260722T131306Z-a7c9f2",
    "timestamp": "2026-07-22T13:13:06.909Z",
    "source_ip": "192.168.137.54",
    "destination_port": 22,
    "protocol": "ssh",
    "event_type": "command_executed",
    "command": "sudo cat /etc/shadow",
    "tactic": "credential_access",
    "input_risk_score": 65,
    "esp32_risk_score": 65,
    "esp32_decision": "warning",
    "esp32_processed": True,
    "device_id": "esp32-cyberhunter-01",
}


class StubService:
    def __init__(self, result: PersistenceResult):
        self.result = result
        self.calls = 0

    def persist(self, payload):
        self.calls += 1
        return self.result


class RaisingService:
    def persist(self, payload):
        raise RuntimeError("sudo cat /etc/shadow")


@dataclass(frozen=True)
class AsgiResponse:
    status_code: int
    body: bytes

    def json(self):
        return json.loads(self.body)


def asgi_post(app: FastAPI, path: str, payload: dict) -> AsgiResponse:
    request_sent = False
    messages = []
    body = json.dumps(payload).encode("utf-8")

    async def receive():
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {
                "type": "http.request",
                "body": body,
                "more_body": False,
            }
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "root_path": "",
        "headers": [
            (b"host", b"testserver"),
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode("ascii")),
        ],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
    }
    asyncio.run(app(scope, receive, send))
    start = next(
        message
        for message in messages
        if message["type"] == "http.response.start"
    )
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return AsgiResponse(start["status"], response_body)


def result_for(
    *,
    success: bool,
    status: str,
    duplicate: bool = False,
    retryable: bool = False,
    error_code: str | None = None,
) -> PersistenceResult:
    return PersistenceResult(
        success=success,
        event_id=VALID_PAYLOAD["event_id"],
        status=status,
        duplicate=duplicate,
        retryable=retryable,
        error_code=error_code,
    )


class SecurityEventEndpointTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router)

    def request_with(self, result: PersistenceResult):
        service = StubService(result)
        self.app.dependency_overrides[get_security_event_service] = (
            lambda: service
        )
        response = asgi_post(
            self.app,
            "/api/security-events",
            VALID_PAYLOAD,
        )
        return response, service

    def test_created_returns_201(self):
        response, service = self.request_with(
            result_for(success=True, status="created")
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "created")
        self.assertFalse(response.json()["duplicate"])
        self.assertEqual(service.calls, 1)

    def test_duplicate_returns_200(self):
        response, _ = self.request_with(
            result_for(
                success=True,
                status="duplicate",
                duplicate=True,
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "duplicate")
        self.assertTrue(response.json()["duplicate"])

    def test_event_conflict_returns_409(self):
        response, _ = self.request_with(
            result_for(
                success=False,
                status="conflict",
                error_code="EVENT_ID_CONFLICT",
            )
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["error_code"],
            "EVENT_ID_CONFLICT",
        )
        self.assertFalse(response.json()["retryable"])

    def test_assessment_conflict_returns_409(self):
        response, _ = self.request_with(
            result_for(
                success=False,
                status="conflict",
                error_code="ASSESSMENT_CONFLICT",
            )
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["error_code"],
            "ASSESSMENT_CONFLICT",
        )

    def test_database_unavailable_returns_503(self):
        response, _ = self.request_with(
            result_for(
                success=False,
                status="temporarily_unavailable",
                retryable=True,
                error_code="DATABASE_UNAVAILABLE",
            )
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["error_code"],
            "DATABASE_UNAVAILABLE",
        )
        self.assertTrue(response.json()["retryable"])

    def test_database_timeout_returns_503(self):
        response, _ = self.request_with(
            result_for(
                success=False,
                status="temporarily_unavailable",
                retryable=True,
                error_code="DATABASE_TIMEOUT",
            )
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["error_code"],
            "DATABASE_TIMEOUT",
        )

    def test_internal_persistence_error_returns_500(self):
        response, _ = self.request_with(
            result_for(
                success=False,
                status="error",
                error_code="INTERNAL_PERSISTENCE_ERROR",
            )
        )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()["error_code"],
            "INTERNAL_PERSISTENCE_ERROR",
        )

    def test_integrity_error_returns_422(self):
        response, _ = self.request_with(
            result_for(
                success=False,
                status="rejected",
                error_code="INTEGRITY_ERROR",
            )
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error_code"], "INTEGRITY_ERROR")

    def test_service_validation_error_returns_422(self):
        response, _ = self.request_with(
            result_for(
                success=False,
                status="rejected",
                error_code="VALIDATION_ERROR",
            )
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error_code"], "VALIDATION_ERROR")

    def test_database_error_returns_500(self):
        response, _ = self.request_with(
            result_for(
                success=False,
                status="error",
                error_code="DATABASE_ERROR",
            )
        )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error_code"], "DATABASE_ERROR")

    def test_unknown_error_code_defaults_to_500(self):
        response, _ = self.request_with(
            result_for(
                success=False,
                status="error",
                error_code="UNKNOWN_ERROR",
            )
        )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error_code"], "UNKNOWN_ERROR")

    def test_invalid_request_returns_422_without_service_call(self):
        service = StubService(result_for(success=True, status="created"))
        self.app.dependency_overrides[get_security_event_service] = (
            lambda: service
        )

        response = asgi_post(
            self.app,
            "/api/security-events",
            {"event_id": "evt-invalid"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(service.calls, 0)

    def test_endpoint_does_not_commit_or_rollback(self):
        session = MagicMock()

        def override_db():
            yield session

        self.app.dependency_overrides[get_db] = override_db
        service = StubService(result_for(success=True, status="created"))
        with patch(
            "routers.security_events.SecurityEventService",
            return_value=service,
        ):
            response = asgi_post(
                self.app,
                "/api/security-events",
                VALID_PAYLOAD,
            )

        self.assertEqual(response.status_code, 201)
        session.commit.assert_not_called()
        session.rollback.assert_not_called()

    def test_unexpected_error_is_sanitized(self):
        self.app.dependency_overrides[get_security_event_service] = (
            lambda: RaisingService()
        )

        with self.assertLogs(
            "routers.security_events",
            level="ERROR",
        ) as captured:
            response = asgi_post(
                self.app,
                "/api/security-events",
                VALID_PAYLOAD,
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()["error_code"],
            "INTERNAL_PERSISTENCE_ERROR",
        )
        logs = "\n".join(captured.output)
        self.assertNotIn(VALID_PAYLOAD["command"], logs)
        self.assertNotIn("sudo cat /etc/shadow", logs)
        self.assertIn("RuntimeError", logs)

    def test_existing_route_and_new_route_are_registered(self):
        import main

        paths = {route.path for route in main.app.routes}
        self.assertIn("/api/logs", paths)
        self.assertIn("/api/security-events", paths)

    def test_openapi_documents_security_event_contract(self):
        schema = self.app.openapi()
        self.assertIn("/api/security-events", schema["paths"])

        operation = schema["paths"]["/api/security-events"]["post"]
        request_schema = operation["requestBody"]["content"][
            "application/json"
        ]["schema"]
        self.assertEqual(
            request_schema["$ref"],
            "#/components/schemas/SecurityEventInput",
        )

        input_schema = schema["components"]["schemas"][
            "SecurityEventInput"
        ]
        self.assertIn("timestamp", input_schema["properties"])
        self.assertNotIn("event_timestamp", input_schema["properties"])
        self.assertEqual(
            set(operation["responses"]),
            {"200", "201", "409", "422", "500", "503"},
        )
        self.assertEqual(
            operation["summary"],
            "Store a validated CyberHunter security event",
        )
        self.assertTrue(operation["description"].strip())
        self.assertIn("security-events", operation["tags"])


if __name__ == "__main__":
    unittest.main()
