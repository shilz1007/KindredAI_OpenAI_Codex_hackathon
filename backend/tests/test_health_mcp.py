"""Integration tests for the isolated Health MCP SQLite MVP."""

import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from kindred_ai.application.health.service import DEMO_USER_ID, HealthService
from kindred_ai.infrastructure.health.sqlite_repository import SqliteHealthRepository


class HealthMcpTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self._temporary_directory.name) / "health.sqlite3"
        self.repository = SqliteHealthRepository(self.database_path)
        self.repository.initialize()
        self.service = HealthService(self.repository)

    def tearDown(self) -> None:
        self._temporary_directory.cleanup()

    def test_migrations_create_schema_and_are_recorded(self) -> None:
        with closing(sqlite3.connect(self.database_path)) as connection:
            versions = connection.execute("SELECT version FROM schema_migrations").fetchall()
            tables = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'medication_schedules'"
            ).fetchall()
        self.assertEqual([("001_initial.sql",), ("002_rename_demo_user.sql",)], versions)
        self.assertEqual([("medication_schedules",)], tables)

    def test_seed_is_idempotent(self) -> None:
        self.repository.initialize()
        with closing(sqlite3.connect(self.database_path)) as connection:
            schedule_count = connection.execute("SELECT COUNT(*) FROM medication_schedules").fetchone()[0]
            event_count = connection.execute("SELECT COUNT(*) FROM health_events").fetchone()[0]
        self.assertEqual(2, schedule_count)
        self.assertEqual(2, event_count)

    def test_schedule_and_event_retrieval_returns_seeded_data(self) -> None:
        schedules = self.service.get_medication_schedule()
        events = self.service.get_health_events()
        self.assertEqual(2, len(schedules))
        self.assertEqual(("08:00", "20:00"), schedules[0].daily_times)
        self.assertGreaterEqual(len(events), 2)
        self.assertGreaterEqual(events[0].occurred_at, events[1].occurred_at)

    def test_record_medication_taken_persists_record(self) -> None:
        record = self.service.record_medication_taken(
            schedule_id="demo-schedule-metformin",
            taken_at=datetime(2026, 7, 18, 8, 0, tzinfo=UTC),
            note="Taken after breakfast",
        )
        with closing(sqlite3.connect(self.database_path)) as connection:
            stored = connection.execute(
                "SELECT schedule_id, note FROM medication_taken_records WHERE id = ?", (record.id,)
            ).fetchone()
        self.assertEqual(("demo-schedule-metformin", "Taken after breakfast"), stored)

    def test_invalid_schedule_does_not_insert_record(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown or inactive"):
            self.service.record_medication_taken(schedule_id="missing", taken_at=None, note=None)
        with closing(sqlite3.connect(self.database_path)) as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM medication_taken_records WHERE user_id = ?", (DEMO_USER_ID,)
            ).fetchone()[0]
        self.assertEqual(1, count)


if __name__ == "__main__":
    unittest.main()
