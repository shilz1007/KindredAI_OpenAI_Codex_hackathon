"""SQLite implementation of the Security MCP persistence port."""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from kindred_ai.domain.security import PhoneMessage, SecurityAlert, SecurityEvent

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[4] / "data" / "security.sqlite3"
MIGRATIONS_PATH = Path(__file__).with_name("migrations")


class SqliteSecurityRepository:
    """Repository backed only by the Security MCP SQLite database."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    @classmethod
    def from_environment(cls) -> "SqliteSecurityRepository":
        configured_path = os.getenv("KINDRED_SECURITY_DB_PATH")
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
        """Apply migrations and idempotently insert fictitious security events."""
        with self._connection() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
            applied = {row["version"] for row in connection.execute("SELECT version FROM schema_migrations")}
            for migration_path in sorted(MIGRATIONS_PATH.glob("*.sql")):
                if migration_path.name not in applied:
                    connection.executescript(migration_path.read_text(encoding="utf-8"))
                    connection.execute(
                        "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                        (migration_path.name, _timestamp_text(datetime.now(UTC))),
                    )
            connection.execute(
                """INSERT OR IGNORE INTO security_events
                (id, message, risk_level, matched_signals, created_at) VALUES (?, ?, ?, ?, ?)""",
                ("demo-security-event-scam", "Urgent: send gift card details to unlock your bank account.", "high", '["gift card", "urgent", "bank account"]', "2026-07-17T10:00:00+00:00"),
            )
            connection.execute(
                """INSERT OR IGNORE INTO security_events
                (id, message, risk_level, matched_signals, created_at) VALUES (?, ?, ?, ?, ?)""",
                ("demo-security-event-safe", "Your daughter Sara will call this evening.", "low", "[]", "2026-07-17T11:00:00+00:00"),
            )

    def add_event(
        self, *, event_id: str, message: str, risk_level: str, matched_signals: tuple[str, ...], created_at: datetime,
    ) -> SecurityEvent:
        timestamp = _timestamp_text(created_at)
        with self._connection() as connection:
            connection.execute(
                """INSERT INTO security_events (id, message, risk_level, matched_signals, created_at)
                VALUES (?, ?, ?, ?, ?)""",
                (event_id, message, risk_level, json.dumps(matched_signals), timestamp),
            )
        return SecurityEvent(event_id, message, risk_level, matched_signals, _parse_timestamp(timestamp))

    def get_event(self, event_id: str) -> SecurityEvent | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT id, message, risk_level, matched_signals, created_at FROM security_events WHERE id = ?", (event_id,),
            ).fetchone()
        return None if row is None else _event_from_row(row)

    def add_alert(
        self, *, alert_id: str, event_id: str, severity: str, status: str, created_at: datetime,
    ) -> SecurityAlert:
        timestamp = _timestamp_text(created_at)
        with self._connection() as connection:
            connection.execute(
                """INSERT INTO security_alerts (id, event_id, severity, status, created_at)
                VALUES (?, ?, ?, ?, ?)""",
                (alert_id, event_id, severity, status, timestamp),
            )
        return SecurityAlert(alert_id, event_id, severity, status, _parse_timestamp(timestamp))

    def get_events(self, limit: int) -> list[SecurityEvent]:
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT id, message, risk_level, matched_signals, created_at FROM security_events
                ORDER BY created_at DESC, id DESC LIMIT ?""", (limit,),
            ).fetchall()
        return [_event_from_row(row) for row in rows]

    def add_phone_message(self, *, message_id: str, message: str, received_at: datetime) -> PhoneMessage:
        timestamp = _timestamp_text(received_at)
        with self._connection() as connection:
            connection.execute("INSERT INTO phone_messages (id, message, received_at, analysis_status) VALUES (?, ?, ?, 'pending')", (message_id, message, timestamp))
        return PhoneMessage(message_id, message, _parse_timestamp(timestamp), "pending", None, None, (), None)

    def complete_phone_message(self, *, message_id: str, risk_level: str, explanation: str, signals: tuple[str, ...], event_id: str | None) -> PhoneMessage:
        with self._connection() as connection:
            connection.execute("UPDATE phone_messages SET analysis_status='completed', risk_level=?, explanation=?, signals=?, security_event_id=? WHERE id=?", (risk_level, explanation, json.dumps(signals), event_id, message_id))
            row = connection.execute("SELECT * FROM phone_messages WHERE id=?", (message_id,)).fetchone()
        return _phone_message_from_row(row)

    def fail_phone_message(self, *, message_id: str) -> PhoneMessage:
        with self._connection() as connection:
            connection.execute("UPDATE phone_messages SET analysis_status='failed' WHERE id=?", (message_id,))
            row = connection.execute("SELECT * FROM phone_messages WHERE id=?", (message_id,)).fetchone()
        return _phone_message_from_row(row)

    def get_phone_messages(self, limit: int) -> list[PhoneMessage]:
        with self._connection() as connection:
            rows = connection.execute("SELECT * FROM phone_messages ORDER BY received_at DESC, id DESC LIMIT ?", (limit,)).fetchall()
        return [_phone_message_from_row(row) for row in rows]


def _event_from_row(row: sqlite3.Row) -> SecurityEvent:
    return SecurityEvent(row["id"], row["message"], row["risk_level"], tuple(json.loads(row["matched_signals"])), _parse_timestamp(row["created_at"]))

def _phone_message_from_row(row: sqlite3.Row) -> PhoneMessage:
    return PhoneMessage(row["id"], row["message"], _parse_timestamp(row["received_at"]), row["analysis_status"], row["risk_level"], row["explanation"], tuple(json.loads(row["signals"])), row["security_event_id"])


def _timestamp_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat() if value.tzinfo else value.replace(tzinfo=UTC).isoformat()


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)
