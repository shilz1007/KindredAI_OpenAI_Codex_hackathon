"""SQLite implementation of the Memory MCP persistence port."""

import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from kindred_ai.domain.memory import ConversationEntry, MemoryItem, UserProfile

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[4] / "data" / "memory.sqlite3"
MIGRATIONS_PATH = Path(__file__).with_name("migrations")
DEMO_USER_ID = "demo-user"


class SqliteMemoryRepository:
    """Repository backed only by the Memory MCP SQLite database."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    @classmethod
    def from_environment(cls) -> "SqliteMemoryRepository":
        configured_path = os.getenv("KINDRED_MEMORY_DB_PATH")
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
        """Apply migrations and insert fixed fictitious records once."""
        with self._connection() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            applied = {row["version"] for row in connection.execute("SELECT version FROM schema_migrations")}
            for migration_path in sorted(MIGRATIONS_PATH.glob("*.sql")):
                if migration_path.name not in applied:
                    connection.executescript(migration_path.read_text(encoding="utf-8"))
                    connection.execute(
                        "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                        (migration_path.name, _timestamp_text(datetime.now(UTC))),
                    )
            self._seed_demo_data(connection)

    def _seed_demo_data(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """INSERT OR IGNORE INTO memory_users
            (id, preferred_name, preferred_language, timezone, preferences) VALUES (?, ?, ?, ?, ?)""",
            (DEMO_USER_ID, "Anita", "Bengali", "Europe/Oslo", "Enjoys poetry and talking about family."),
        )
        for memory in (
            ("demo-memory-poetry", "Anita enjoys Bengali poetry.", "interest", "seed", 4, "2026-07-15T10:00:00+00:00"),
            ("demo-memory-calls", "Anita prefers family calls in the evening.", "preference", "seed", 5, "2026-07-16T18:00:00+00:00"),
            ("demo-memory-son-birthday", "Anita's son Karim has a birthday on 14 April.", "important_date", "seed", 5, "2026-07-18T08:00:00+00:00"),
            ("demo-memory-daughter-birthday", "Anita's daughter Sara has a birthday on 23 September.", "important_date", "seed", 5, "2026-07-18T08:00:01+00:00"),
            ("demo-memory-anniversary", "Anita's wedding anniversary is on 15 June.", "important_date", "seed", 5, "2026-07-18T08:00:02+00:00"),
            ("demo-memory-own-birthday", "Anita's birthday is on 8 November.", "important_date", "seed", 5, "2026-07-18T08:00:03+00:00"),
            ("demo-memory-pension", "Anita's pension is expected on the 25th of every month.", "financial_routine", "seed", 5, "2026-07-18T08:00:04+00:00"),
            ("demo-memory-world-cup", "The 2026 FIFA World Cup final is on 19 July 2026.", "event_date", "seed", 4, "2026-07-18T08:00:05+00:00"),
            ("demo-memory-music-event", "A fictional Bengali music evening is scheduled for 2 August 2026 at 18:30 in Oslo.", "event_date", "seed", 3, "2026-07-18T08:00:06+00:00"),
        ):
            connection.execute(
                """INSERT OR IGNORE INTO memories
                (id, user_id, content, category, source, importance, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (memory[0], DEMO_USER_ID, *memory[1:]),
            )
        for entry in (
            ("demo-history-1", "user", "I would like to hear a poem today.", "2026-07-17T09:00:00+00:00"),
            ("demo-history-2", "assistant", "Of course, Anita. I can share a short poem.", "2026-07-17T09:00:05+00:00"),
        ):
            connection.execute(
                """INSERT OR IGNORE INTO conversation_history
                (id, user_id, speaker, content, occurred_at) VALUES (?, ?, ?, ?, ?)""",
                (entry[0], DEMO_USER_ID, *entry[1:]),
            )

    def get_user_profile(self, user_id: str) -> UserProfile | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT id, preferred_name, preferred_language, timezone, preferences FROM memory_users WHERE id = ?",
                (user_id,),
            ).fetchone()
        return None if row is None else UserProfile(**dict(row))

    def add_memory(
        self, *, memory_id: str, user_id: str, content: str, category: str,
        source: str, importance: int, created_at: datetime,
    ) -> MemoryItem:
        timestamp = _timestamp_text(created_at)
        with self._connection() as connection:
            connection.execute(
                """INSERT INTO memories (id, user_id, content, category, source, importance, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (memory_id, user_id, content, category, source, importance, timestamp),
            )
        return MemoryItem(memory_id, content, category, source, importance, _parse_timestamp(timestamp))

    def get_history(self, user_id: str, limit: int) -> list[ConversationEntry]:
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT id, speaker, content, occurred_at FROM conversation_history
                WHERE user_id = ? ORDER BY occurred_at DESC, id DESC LIMIT ?""",
                (user_id, limit),
            ).fetchall()
        return [ConversationEntry(row["id"], row["speaker"], row["content"], _parse_timestamp(row["occurred_at"])) for row in rows]


def _timestamp_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat() if value.tzinfo else value.replace(tzinfo=UTC).isoformat()


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)
