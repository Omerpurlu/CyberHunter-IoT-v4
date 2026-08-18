import importlib
import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("POSTGRES_HOST", "127.0.0.1")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "unit_test")
os.environ.setdefault("POSTGRES_USER", "unit_test")
os.environ.setdefault("POSTGRES_PASSWORD", "unit_test")

from models import ResponseAction  # noqa: E402
from sqlalchemy import CheckConstraint  # noqa: E402


MIGRATION_PATH = (
    BACKEND_DIR
    / "alembic"
    / "versions"
    / "f7c3a91d2e44_add_response_actions.py"
)


def load_migration():
    spec = importlib.util.spec_from_file_location("response_actions_migration", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ResponseActionModelMigrationTests(unittest.TestCase):
    def test_model_targets_response_actions(self):
        self.assertEqual(ResponseAction.__tablename__, "response_actions")

    def test_required_checks_are_declared(self):
        constraints = {
            item.name: str(item.sqltext)
            for item in ResponseAction.__table__.constraints
            if isinstance(item, CheckConstraint)
        }
        self.assertIn("BETWEEN 0 AND 100", constraints["ck_response_actions_risk_score"])
        self.assertIn("> 0", constraints["ck_response_actions_policy_version"])
        for name in ("action", "severity", "status"):
            self.assertIn(f"ck_response_actions_{name}", constraints)

    def test_idempotency_unique_constraint(self):
        constraint = next(item for item in ResponseAction.__table__.constraints if item.name == "uq_response_actions_decision")
        self.assertEqual(
            [column.name for column in constraint.columns],
            ["event_id", "device_id", "action", "policy_version"],
        )

    def test_upgrade_only_creates_response_actions(self):
        migration = load_migration()
        fake_op = MagicMock()
        with patch.object(migration, "op", fake_op):
            migration.upgrade()
        fake_op.create_table.assert_called_once()
        self.assertEqual(fake_op.create_table.call_args.args[0], "response_actions")
        fake_op.drop_table.assert_not_called()

    def test_downgrade_only_drops_response_actions(self):
        migration = load_migration()
        fake_op = MagicMock()
        with patch.object(migration, "op", fake_op):
            migration.downgrade()
        fake_op.drop_table.assert_called_once_with("response_actions")
        fake_op.create_table.assert_not_called()

    def test_revision_chain(self):
        migration = load_migration()
        self.assertEqual(migration.revision, "f7c3a91d2e44")
        self.assertEqual(migration.down_revision, "e482165f0daa")


if __name__ == "__main__":
    unittest.main()
