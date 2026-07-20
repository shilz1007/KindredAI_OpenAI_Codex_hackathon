"""Integration tests for the isolated Memory MCP SQLite MVP."""

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from kindred_ai.application.memory.service import MemoryService
from kindred_ai.infrastructure.memory.sqlite_repository import SqliteMemoryRepository


class MemoryMcpTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self._temporary_directory.name) / "memory.sqlite3"
        self.repository = SqliteMemoryRepository(self.database_path)
        self.repository.initialize()
        self.service = MemoryService(self.repository)

    def tearDown(self) -> None:
        self._temporary_directory.cleanup()

    def test_migrations_and_seed_are_idempotent(self) -> None:
        self.repository.initialize()
        with closing(sqlite3.connect(self.database_path)) as connection:
            versions = connection.execute("SELECT version FROM schema_migrations").fetchall()
            memory_count = connection.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        self.assertEqual([("001_initial.sql",), ("002_rename_demo_user.sql",)], versions)
        self.assertEqual(9, memory_count)

    def test_get_user_profile_returns_demo_context(self) -> None:
        profile = self.service.get_user_profile()
        self.assertEqual("Anita", profile.preferred_name)
        self.assertEqual("Bengali", profile.preferred_language)

    def test_save_memory_persists_a_memory_item(self) -> None:
        item = self.service.save_memory(
            content="Anita likes jasmine tea.", category="preference", source="conversation", importance=3,
        )
        with closing(sqlite3.connect(self.database_path)) as connection:
            stored = connection.execute("SELECT content, importance FROM memories WHERE id = ?", (item.id,)).fetchone()
        self.assertEqual(("Anita likes jasmine tea.", 3), stored)

    def test_retrieve_history_is_newest_first_and_bounded(self) -> None:
        history = self.service.retrieve_history(limit=1)
        self.assertEqual(1, len(history))
        self.assertEqual("assistant", history[0].speaker)

    def test_retrieve_memories_filters_by_category(self) -> None:
        dates = self.service.retrieve_memories(category="important_date")
        self.assertGreaterEqual(len(dates), 1)
        self.assertTrue(all(item.category == "important_date" for item in dates))
        self.assertIn("birthday", dates[0].content.lower())

    def test_invalid_memory_requests_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            self.service.save_memory(content="   ", category="general", source="conversation", importance=1)
        with self.assertRaisesRegex(ValueError, "between 1 and 100"):
            self.service.retrieve_history(limit=0)


if __name__ == "__main__":
    unittest.main()
