"""SQLite implementation of the Health MCP persistence port."""

import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from kindred_ai.domain.health import HealthEvent, MedicationSchedule, MedicationTakenRecord

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[4] / "data" / "health.sqlite3"
MIGRATIONS_PATH = Path(__file__).with_name("migrations")
DEMO_USER_ID = "demo-user"


class SqliteHealthRepository:
    """Repository backed only by the Health MCP SQLite database."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    @classmethod
    def from_environment(cls) -> "SqliteHealthRepository":
        """Build a repository from the environment or the local runtime default."""
        configured_path = os.getenv("KINDRED_HEALTH_DB_PATH")
        return cls(Path(configured_path) if configured_path else DEFAULT_DATABASE_PATH)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        """Apply migrations and idempotently insert development-only demo records."""
        with self._connection() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )"""
            )
            applied = {
                row["version"]
                for row in connection.execute("SELECT version FROM schema_migrations")
            }
            for migration_path in sorted(MIGRATIONS_PATH.glob("*.sql")):
                if migration_path.name not in applied:
                    connection.executescript(migration_path.read_text(encoding="utf-8"))
                    connection.execute(
                        "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                        (migration_path.name, _timestamp_text(datetime.now(UTC))),
                    )
            self._seed_demo_data(connection)

    def _seed_demo_data(self, connection: sqlite3.Connection) -> None:
        """Insert fixed fictitious records without duplicating them on later startups."""
        connection.execute(
            """INSERT OR IGNORE INTO health_users (id, display_name, timezone)
            VALUES (?, ?, ?)""",
            (DEMO_USER_ID, "Anita Rahman (demo)", "Europe/Oslo"),
        )
        schedules = (
            ("demo-schedule-metformin", "Metformin", "500 mg with food", "Europe/Oslo"),
            ("demo-schedule-vitamin-d", "Vitamin D", "20 micrograms", "Europe/Oslo"),
        )
        for schedule in schedules:
            connection.execute(
                """INSERT OR IGNORE INTO medication_schedules
                (id, user_id, medication_name, dose_instructions, timezone, is_active)
                VALUES (?, ?, ?, ?, ?, 1)""",
                (schedule[0], DEMO_USER_ID, *schedule[1:]),
            )
        for schedule_id, local_time in (
            ("demo-schedule-metformin", "08:00"),
            ("demo-schedule-metformin", "20:00"),
            ("demo-schedule-vitamin-d", "09:00"),
        ):
            connection.execute(
                """INSERT OR IGNORE INTO medication_schedule_times
                (schedule_id, local_time) VALUES (?, ?)""",
                (schedule_id, local_time),
            )
        connection.execute(
            """INSERT OR IGNORE INTO medication_taken_records
            (id, user_id, schedule_id, taken_at, note) VALUES (?, ?, ?, ?, ?)""",
            ("demo-dose-metformin-1", DEMO_USER_ID, "demo-schedule-metformin", "2026-07-17T08:05:00+00:00", "Demo record"),
        )
        for event in (
            ("demo-event-wellness", "wellness_check", "2026-07-16T10:00:00+00:00", "Fictitious routine wellness check.", "low"),
            ("demo-event-bp", "blood_pressure", "2026-07-17T09:30:00+00:00", "Fictitious reading logged for demo purposes.", "medium"),
        ):
            connection.execute(
                """INSERT OR IGNORE INTO health_events
                (id, user_id, event_type, occurred_at, details, severity)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (event[0], DEMO_USER_ID, *event[1:]),
            )

    def get_active_medication_schedules(self, user_id: str) -> list[MedicationSchedule]:
        """Retrieve active schedules and their named local daily times."""
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT schedules.id, schedules.medication_name, schedules.dose_instructions,
                          schedules.timezone, schedules.is_active, times.local_time
                   FROM medication_schedules AS schedules
                   JOIN medication_schedule_times AS times ON times.schedule_id = schedules.id
                   WHERE schedules.user_id = ? AND schedules.is_active = 1
                   ORDER BY schedules.medication_name, times.local_time""",
                (user_id,),
            ).fetchall()
        schedules: dict[str, MedicationSchedule] = {}
        for row in rows:
            existing = schedules.get(row["id"])
            times = (*existing.daily_times, row["local_time"]) if existing else (row["local_time"],)
            schedules[row["id"]] = MedicationSchedule(
                id=row["id"], medication_name=row["medication_name"],
                dose_instructions=row["dose_instructions"], timezone=row["timezone"],
                daily_times=times, is_active=bool(row["is_active"]),
            )
        return list(schedules.values())

    def get_active_schedule(self, user_id: str, schedule_id: str) -> MedicationSchedule | None:
        """Get an active schedule only when it belongs to the requested user."""
        return next(
            (schedule for schedule in self.get_active_medication_schedules(user_id) if schedule.id == schedule_id),
            None,
        )

    def add_medication_schedule(
        self,
        *,
        schedule_id: str,
        user_id: str,
        medication_name: str,
        dose_instructions: str,
        timezone: str,
        daily_times: tuple[str, ...],
    ) -> MedicationSchedule:
        """Store one active medication plan and its named local daily times."""
        with self._connection() as connection:
            connection.execute(
                """INSERT INTO medication_schedules
                (id, user_id, medication_name, dose_instructions, timezone, is_active)
                VALUES (?, ?, ?, ?, ?, 1)""",
                (schedule_id, user_id, medication_name, dose_instructions, timezone),
            )
            connection.executemany(
                "INSERT INTO medication_schedule_times (schedule_id, local_time) VALUES (?, ?)",
                ((schedule_id, local_time) for local_time in daily_times),
            )
        return MedicationSchedule(
            id=schedule_id,
            medication_name=medication_name,
            dose_instructions=dose_instructions,
            timezone=timezone,
            daily_times=daily_times,
            is_active=True,
        )

    def add_medication_taken_record(
        self, *, record_id: str, user_id: str, schedule_id: str, taken_at: datetime, note: str | None,
    ) -> MedicationTakenRecord:
        """Persist and return a medication-taken record."""
        timestamp = _timestamp_text(taken_at)
        with self._connection() as connection:
            connection.execute(
                """INSERT INTO medication_taken_records (id, user_id, schedule_id, taken_at, note)
                VALUES (?, ?, ?, ?, ?)""",
                (record_id, user_id, schedule_id, timestamp, note),
            )
        return MedicationTakenRecord(record_id, schedule_id, _parse_timestamp(timestamp), note)

    def get_health_events(self, user_id: str) -> list[HealthEvent]:
        """Retrieve events in newest-first occurrence order."""
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT id, event_type, occurred_at, details, severity
                   FROM health_events WHERE user_id = ?
                   ORDER BY occurred_at DESC, id DESC""",
                (user_id,),
            ).fetchall()
        return [
            HealthEvent(row["id"], row["event_type"], _parse_timestamp(row["occurred_at"]), row["details"], row["severity"])
            for row in rows
        ]


def _timestamp_text(value: datetime) -> str:
    """Persist all timestamps as timezone-aware ISO 8601 strings."""
    return value.astimezone(UTC).isoformat() if value.tzinfo else value.replace(tzinfo=UTC).isoformat()


def _parse_timestamp(value: str) -> datetime:
    """Parse timestamps stored by this repository."""
    return datetime.fromisoformat(value)
