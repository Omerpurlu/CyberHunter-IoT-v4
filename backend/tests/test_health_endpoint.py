import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from sqlalchemy.exc import OperationalError, SQLAlchemyError


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("POSTGRES_HOST", "127.0.0.1")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "unit_test")
os.environ.setdefault("POSTGRES_USER", "unit_test")
os.environ.setdefault("POSTGRES_PASSWORD", "unit_test")

from routers.health import health  # noqa: E402


def body(response):
    return json.loads(response.body)


class HealthEndpointTests(unittest.TestCase):
    @patch("routers.health.engine")
    def test_postgresql_success_and_query_ms(self, mocked_engine):
        connection = MagicMock()
        connection.execute.return_value.scalar_one.return_value = 1
        mocked_engine.connect.return_value.__enter__.return_value = connection
        response = health()
        payload = body(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "healthy")
        self.assertIsInstance(payload["postgresql"]["query_ms"], float)
        mocked_engine.connect.return_value.__exit__.assert_called_once()

    @patch("routers.health.engine")
    def test_database_unavailable_is_sanitized(self, mocked_engine):
        mocked_engine.connect.side_effect = OperationalError(
            "postgresql://user:password@secret-host/db", {}, Exception("password=secret")
        )
        response = health()
        serialized = response.body.decode()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(body(response)["postgresql"]["error"], "database_unavailable")
        self.assertNotIn("password", serialized)
        self.assertNotIn("secret-host", serialized)

    @patch("routers.health.engine")
    def test_unexpected_sqlalchemy_error_is_sanitized(self, mocked_engine):
        mocked_engine.connect.side_effect = SQLAlchemyError("sensitive URL")
        response = health()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("sensitive URL", response.body.decode())

    @patch("routers.health.engine")
    def test_unexpected_error_is_sanitized(self, mocked_engine):
        mocked_engine.connect.side_effect = RuntimeError("token=private")
        response = health()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private", response.body.decode())


if __name__ == "__main__":
    unittest.main()
