"""SQLite storage for a bounded history of public research answers."""

import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from kindred_ai.domain.research import ResearchAnswer

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[4] / "data" / "research.sqlite3"
MIGRATIONS_PATH = Path(__file__).with_name("migrations")
MAX_HISTORY_ITEMS = 20


class SqliteResearchHistoryRepository:
    """Owns only non-personal public-search history."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    @classmethod
    def from_environment(cls) -> "SqliteResearchHistoryRepository":
        configured_path = os.getenv("KINDRED_RESEARCH_DB_PATH")
        return cls(Path(configured_path) if configured_path else DEFAULT_DATABASE_PATH)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
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
                        (migration_path.name, _timestamp(datetime.now(UTC))),
                    )

    def add(self, answer: ResearchAnswer) -> ResearchAnswer:
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO research_answers (query, answer, provider, researched_at) VALUES (?, ?, ?, ?)",
                (answer.query, answer.answer, answer.provider, _timestamp(answer.researched_at)),
            )
            connection.execute(
                """DELETE FROM research_answers WHERE id NOT IN (
                    SELECT id FROM research_answers ORDER BY researched_at DESC, id DESC LIMIT ?
                )""",
                (MAX_HISTORY_ITEMS,),
            )
        return answer

    def recent(self, *, limit: int = MAX_HISTORY_ITEMS) -> list[ResearchAnswer]:
        safe_limit = max(1, min(limit, MAX_HISTORY_ITEMS))
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT query, answer, provider, researched_at FROM research_answers
                ORDER BY researched_at DESC, id DESC LIMIT ?""",
                (safe_limit,),
            ).fetchall()
        return [
            ResearchAnswer(row["query"], row["answer"], row["provider"], datetime.fromisoformat(row["researched_at"]))
            for row in rows
        ]


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat() if value.tzinfo else value.replace(tzinfo=UTC).isoformat()

